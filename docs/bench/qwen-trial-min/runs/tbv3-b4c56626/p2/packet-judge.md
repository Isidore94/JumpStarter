# BRIEF
Goal: trader-fit rank step 4: flag the M30 extended pullback (the trader's favourite setup). Rows whose only hard no's are above_third_band / extended_3_closes get one batched M30 yfinance fetch (chunks of 50, on the scan worker), then the Pullback alert's own rule (pullback_sma_reclaim.evaluate on the M30 65-SMA, D1 bars for the dip gate's ATR). Flag only when the fire's bar is in today's session once it has opened, else the last completed session (evaluate completed bars only, capped at that session's close). A failed fetch or short tape = None (unknown, logged once), never a failed scan; rows that are not extended are never touched or fetched. The runner stamps the flag right before the Fit pass, which waives the two extension rules and adds the bonus; the setup tag EXTENDED_PULLBACK_M30_LRSI_65_SMA follows. STABLE replay and tracker backfill do not fetch, so extended rows stay hard no's there.
Done when: tests on synthetic M30 tapes cover fire in session (flag + waiver + bonus + tag), fire yesterday (no flag), missing bars (None, still a hard no), failed fetch (all unknown, one warning), non-extended rows untouched, one batched fetch, and the session-clock cases; run_tests.py/pytest and ruff green.
Files: new scripts/master_avwap_lib/m30_extended_pullback.py; scripts/master_avwap_lib/trader_fit.py (the hard no's, waiver, bonus); scripts/indicators/pullback_sma_reclaim.py (evaluate, reuse, do not change); find the runner's Fit pass and intraday_history._download.
Don't touch: order/sizing code, the Pullback alert itself, the existing trader-fit fixtures and their expected ranks.
Pattern: the other trader_fit rules and how the scan worker batches yfinance downloads.

# CANDIDATE DIFF
```diff
diff --git a/scripts/master_avwap_lib/m30_extended_pullback.py b/scripts/master_avwap_lib/m30_extended_pullback.py
new file mode 100644
index 0000000..cfe65de
--- /dev/null
+++ b/scripts/master_avwap_lib/m30_extended_pullback.py
@@ -0,0 +1,283 @@
+"""Trader fit, step 4: flag the M30 extended pullback on the extended rows.
+
+A row whose ONLY hard no's are the two extension rules gets one batched M30
+fetch on the scan worker, then the Pullback alert's own rule
+(``indicators.pullback_sma_reclaim``) is judged on that session - today's
+once it has opened, else the last completed session. The verdict lands on the
+row as ``m30_extended_pullback``: ``True`` waives the two extension rules and
+earns the bonus in the Fit pass; ``False`` (measured no) and ``None``
+(unknown - short tape, stale tape, failed fetch) waive nothing and stay hard
+no's. STABLE replay and the tracker backfill call the Fit pass directly and
+never fetch, so extended rows stay hard no's there.
+"""
+
+from __future__ import annotations
+
+import logging
+from collections.abc import Iterable, Mapping
+from datetime import datetime
+from typing import Any
+
+import intraday_history
+import market_calendar
+import market_session
+from indicators.pullback_sma_reclaim import M30_SMA_LENGTH, evaluate
+from .trader_fit import WAIVABLE_RULES, fit_input, hard_no_rules
+
+_LOGGER = logging.getLogger(__name__)
+
+_FLAG_FIELD = "m30_extended_pullback"
+_NOTE_FIELD = "m30_extended_pullback_note"
+
+
+def _as_market_local(moment: datetime) -> datetime:
+    """The moment on the market-local naive clock, CONVERTED - never stripped."""
+    if moment.tzinfo is None:
+        return moment
+    try:
+        local_tz, _name = market_session.get_market_local_timezone()
+    except Exception:  # pragma: no cover - settings unavailable
+        return moment.astimezone().replace(tzinfo=None)
+    return moment.astimezone(local_tz).replace(tzinfo=None)
+
+
+def target_session(moment: datetime) -> tuple[datetime, datetime] | None:
+    """The session to judge: today's once it has opened, else the last completed.
+
+    Naive market-local ``(opened, closed)``. Today's session is used when the
+    market calendar says today is a session day and ``moment`` has reached its
+    open; otherwise the previous session, which the calendar resolves with
+    weekends and holidays already behind it. Any calendar or session failure
+    answers ``None`` and the caller fails closed (the flag stays unknown).
+    """
+    moment = _as_market_local(moment)
+    try:
+        window = market_session.get_market_session_window(moment)
+        opened = window.open_local.replace(tzinfo=None)
+        closed = window.close_local.replace(tzinfo=None)
+        if market_calendar.is_session(window.market_date) and moment >= opened:
+            return opened, closed
+        previous = market_calendar.previous_session(window.market_date)
+        reference = datetime(previous.year, previous.month, previous.day, 12, 0)
+        previous_window = market_session.get_market_session_window(reference)
+        previous_opened = previous_window.open_local.replace(tzinfo=None)
+        previous_closed = previous_window.close_local.replace(tzinfo=None)
+    except Exception:  # a broken calendar or missing settings is unknown, not a crash
+        _LOGGER.warning("M30 extended pullback: the session could not be resolved; the flag stays unknown.")
+        return None
+    if previous_closed > moment:  # the calendar is giving us a session that has not closed
+        return None
+    return previous_opened, previous_closed
+
+
+def judge(
+    bars: list[dict],
+    side: str,
+    *,
+    opened: datetime,
+    closed: datetime,
+    now: datetime,
+    daily_bars: list[dict] | None,
+) -> tuple[bool | None, Any]:
+    """``(flag, fire)``: did the pullback fire inside this session?
+
+    Completed bars only, capped at the session close. ``None`` is unknown
+    (short or stale tape, missing data) - never a failed scan.
+    """
+    cap = min(now, closed)
+    result = evaluate(
+        bars,
+        side=side,
+        sma_length=M30_SMA_LENGTH,
+        bar_minutes=30,
+        armed_at=None,
+        now=cap,
+        daily_bars=daily_bars,
+    )
+    if result is None:
+        return None, None
+    fires = [fire for fire in result.fired if fire.bar_dt >= opened]
+    if not fires:
+        return False, None
+    fire = max(fires, key=lambda fired: fired.bar_dt)
+    return True, fire
+
+
+def _note(fire: Any) -> str:
+    """The tag's evidence: trigger, fire time and the SMA it reclaimed."""
+    return f"{fire.trigger} {fire.bar_dt:%Y-%m-%d %H:%M} SMA65 {fire.sma:.2f}"
+
+
+def _daily_bars(frame: Any) -> list[dict]:
+    """The runner's daily frame as dict bars, oldest first, for the dip-gate ATR.
+
+    The same seam as ``runner._d1_environment_bars``: the indicator takes bars,
+    not a DataFrame, so the conversion stays on the caller's side of it.
+    """
+    if frame is None:
+        return []
+    rows = frame
+    if hasattr(frame, "to_dict"):
+        if getattr(frame, "empty", False):
+            return []
+        rows = frame.to_dict("records")
+    bars: list[dict] = []
+    for row in rows or ():
+        try:
+            stamp = row.get("datetime", row.get("date"))
+            open_ = float(row.get("open"))
+            high = float(row.get("high"))
+            low = float(row.get("low"))
+            close = float(row.get("close"))
+        except (AttributeError, TypeError, ValueError):
+            continue
+        if any(value != value for value in (open_, high, low, close)):
+            continue
+        if isinstance(stamp, datetime):
+            stamp = _as_market_local(stamp)
+        else:
+            try:
+                stamp = datetime.fromisoformat(str(stamp))
+            except ValueError:
+                continue
+        bars.append({"dt": stamp, "open": open_, "high": high, "low": low, "close": close})
+    bars.sort(key=lambda bar: bar["dt"])
+    return bars
+
+
+def _is_extended(row: Mapping[str, Any], symbol_entry: Any, feature_row: Any) -> bool:
+    """True when the row's ONLY hard no's are the two extension rules.
+
+    Judged on the same merged input the Fit pass uses, so a row the Fit would
+    also fail on ``below_prior_day_low`` is not an extended row. Missing inputs
+    read as unknown and never count.
+    """
+    fired, _unknown = hard_no_rules(fit_input(row, symbol_entry, feature_row))
+    return bool(fired) and set(fired) <= WAIVABLE_RULES
+
+
+def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
+    step = max(1, int(size))
+    for start in range(0, len(items), step):
+        yield items[start : start + step]
+
+
+def stamp_m30_extended_pullbacks(
+    rows: Iterable[Any],
+    *,
+    ai_state: Mapping[str, Any] | None = None,
+    feature_rows_by_symbol: Mapping[str, Any] | None = None,
+    daily_frames_by_symbol: Mapping[str, Any] | None = None,
+    now: datetime | None = None,
+    downloader: Any = None,
+) -> tuple[int, int]:
+    """Flag the extended rows with the M30 pullback verdict; return ``(flagged, unknown)``.
+
+    Only a row whose ONLY hard no's are the two extension rules is judged: all
+    of them ride ONE batched M30 fetch (chunks of the intraday history's own
+    batch size, regular hours, one month), then the Pullback rule on that
+    session. A failed fetch, a tape that cannot be read, or a symbol with no
+    usable bars leaves the flag ``None`` (unknown) and logs once; it never
+    raises and never fails the scan. Rows that are not extended are not
+    touched and are not fetched.
+    """
+    rows = [row for row in (rows or []) if isinstance(row, dict)]
+    if not rows:
+        return 0, 0
+
+    symbols = ai_state.get("symbols", {}) if isinstance(ai_state, Mapping) else {}
+    features = feature_rows_by_symbol if isinstance(feature_rows_by_symbol, Mapping) else {}
+    frames = daily_frames_by_symbol if isinstance(daily_frames_by_symbol, Mapping) else {}
+    if downloader is None:
+        downloader = intraday_history._download
+
+    extended_by_symbol: dict[str, list[dict]] = {}
+    for row in rows:
+        symbol = str(row.get("symbol") or "").strip().upper()
+        if not symbol:
+            continue
+        if _is_extended(row, symbols.get(symbol), features.get(symbol)):
+            extended_by_symbol.setdefault(symbol, []).append(row)
+    if not extended_by_symbol:
+        return 0, 0
+
+    moment = _as_market_local(now or datetime.now())
+    session = target_session(moment)
+    if session is None:
+        for symbol_rows in extended_by_symbol.values():
+            for row in symbol_rows:
+                row[_FLAG_FIELD] = None
+        return 0, sum(len(rows) for rows in extended_by_symbol.values())
+    opened, closed = session
+    cap = min(moment, closed)
+
+    flagged = 0
+    unknown = 0
+    for chunk in _chunks(sorted(extended_by_symbol), intraday_history.DOWNLOAD_CHUNK_SYMBOLS):
+        try:
+            fetched = downloader(
+                chunk,
+                period=intraday_history.DEFAULT_PERIOD,
+                interval=intraday_history.interval_label(30),
+            )
+        except Exception:  # one dead chunk is unknown rows, never a dead scan
+            _LOGGER.warning(
+                "M30 extended pullback fetch failed for %d symbol(s); the flag stays unknown.",
+                len(chunk),
+                exc_info=True,
+            )
+            fetched = {}
+        fetched = fetched if isinstance(fetched, Mapping) else {}
+
+        empty_symbols: list[str] = []
+        for symbol in chunk:
+            symbol_rows = extended_by_symbol[symbol]
+            try:
+                frame = fetched.get(symbol)
+                bars = intraday_history.frame_to_bars(frame, now=cap, interval_minutes=30) if frame is not None else []
+                if not bars:
+                    empty_symbols.append(symbol)
+                    unknown += len(symbol_rows)
+                    for target in symbol_rows:
+                        target[_FLAG_FIELD] = None
+                    continue
+                daily = _daily_bars(frames.get(symbol))
+            except Exception:  # a malformed tape is unknown rows, never a dead scan
+                _LOGGER.warning(
+                    "M30 extended pullback: the M30 tape for %s could not be read; the flag stays unknown.",
+                    symbol,
+                    exc_info=True,
+                )
+                unknown += len(symbol_rows)
+                for target in symbol_rows:
+                    target[_FLAG_FIELD] = None
+                continue
+
+            for target in symbol_rows:
+                side = str(target.get("side") or "").strip().upper()
+                try:
+                    verdict, fire = judge(bars, side, opened=opened, closed=closed, now=moment, daily_bars=daily)
+                except Exception:  # one unreadable row is unknown, never a dead scan
+                    _LOGGER.warning(
+                        "M30 extended pullback: the pullback rule failed for %s; the flag stays unknown.",
+                        symbol,
+                        exc_info=True,
+                    )
+                    target[_FLAG_FIELD] = None
+                    unknown += 1
+                    continue
+                if verdict is True:
+                    target[_FLAG_FIELD] = True
+                    target[_NOTE_FIELD] = _note(fire)
+                    flagged += 1
+                elif verdict is False:
+                    target[_FLAG_FIELD] = False
+                else:
+                    target[_FLAG_FIELD] = None
+                    unknown += 1
+        if empty_symbols:
+            _LOGGER.info(
+                "M30 extended pullback: no usable M30 bars for %s; the flag stays unknown.",
+                ", ".join(sorted(empty_symbols)),
+            )
+    return flagged, unknown
diff --git a/scripts/master_avwap_lib/runner.py b/scripts/master_avwap_lib/runner.py
index 69b9a10..b3719f0 100644
--- a/scripts/master_avwap_lib/runner.py
+++ b/scripts/master_avwap_lib/runner.py
@@ -12,6 +12,7 @@ from indicators.d1_environment import classify_environment as classify_d1_enviro
 
 from . import legacy as _legacy
 from .d1_zone_arms import build_d1_zone_arms
+from .m30_extended_pullback import stamp_m30_extended_pullbacks
 from .setup_tagging import apply_setup_tag_payload, canonicalize_priority_setup_tags
 from .trader_fit import apply_trader_fit_ranking, extension_closes_outside_second_band
 from master_avwap_shared import build_active_bounce_summary, load_master_avwap_events_for_date
@@ -2646,6 +2647,19 @@ def _run_master_impl(
         recent_family_rows=recent_family_rows,
         reference_date=today_run,
     )
+    # Trader fit step 4: rows whose only hard no's are the two extension rules get
+    # one batched M30 fetch right here on the scan worker, then the Pullback
+    # alert's own rule judges the fire's session. The flag rides on the row so
+    # the Fit pass below can waive the two rules and add the bonus. STABLE
+    # replay and the tracker backfill run the Fit pass without this stamp.
+    m30_flagged, m30_unknown = stamp_m30_extended_pullbacks(
+        priority_rows,
+        ai_state=ai_state,
+        feature_rows_by_symbol=feature_rows_by_symbol,
+        daily_frames_by_symbol=daily_frames_by_symbol,
+    )
+    if m30_flagged or m30_unknown:
+        logging.info("M30 extended pullback: %d flagged, %d unknown.", m30_flagged, m30_unknown)
     # Trader fit (trader 2026-10-05): `score` becomes the Fit; the proven-quality
     # score stays on the row as the tiebreak.
     apply_trader_fit_ranking(priority_rows, ai_state, feature_rows_by_symbol)
diff --git a/scripts/master_avwap_lib/trader_fit.py b/scripts/master_avwap_lib/trader_fit.py
index 15cbc4a..d7b7f34 100644
--- a/scripts/master_avwap_lib/trader_fit.py
+++ b/scripts/master_avwap_lib/trader_fit.py
@@ -305,12 +305,16 @@ def fit_sort_key(row: Mapping[str, Any]) -> tuple[float, float, str]:
     )
 
 
-def _fit_inputs(
+def fit_input(
     row: Mapping[str, Any],
     symbol_entry: Mapping[str, Any] | None,
     feature_row: Mapping[str, Any] | None,
 ) -> dict[str, Any]:
-    """The row's own fields, with gaps filled from the symbol entry and feature row."""
+    """The row's own fields, with gaps filled from the symbol entry and feature row.
+
+    The ONE merged input every fit read uses, so off-scan callers (like the
+    M30 extended-pullback stamp) classify rows the same way the Fit does.
+    """
     merged: dict[str, Any] = {}
     snapshot = (symbol_entry or {}).get("entry_feature_snapshot") if isinstance(symbol_entry, Mapping) else None
     for source in (snapshot, feature_row, symbol_entry):
@@ -341,7 +345,7 @@ def apply_trader_fit_ranking(
         feature_row = features.get(symbol)
         if "proven_quality_score" not in row:
             row["proven_quality_score"] = _number(row.get("score"))
-        result = compute_trader_fit(_fit_inputs(row, symbol_entry, feature_row))
+        result = compute_trader_fit(fit_input(row, symbol_entry, feature_row))
         row.update(result)
         row["score"] = result["fit_score"]
         mirror = {key: result[key] for key in FIT_FIELDS}
diff --git a/tests/test_m30_extended_pullback.py b/tests/test_m30_extended_pullback.py
new file mode 100644
index 0000000..40b33f8
--- /dev/null
+++ b/tests/test_m30_extended_pullback.py
@@ -0,0 +1,384 @@
+"""Trader-fit rank step 4: flag the M30 extended pullback on scan rows.
+
+Rows whose ONLY hard no's are the two extension rules get one batched M30
+fetch on the scan worker, then the Pullback alert's own rule judged on the
+fire's session - today's once it has opened, else the last completed session.
+True waives the two extension rules and adds the bonus; False and None
+(measured no / unknown) waive nothing.
+"""
+
+from __future__ import annotations
+
+import inspect
+import json
+import logging
+import re
+import sys
+from datetime import date, datetime
+from pathlib import Path
+
+import pandas as pd
+import pytest
+
+ROOT_DIR = Path(__file__).resolve().parents[1]
+SCRIPTS_DIR = ROOT_DIR / "scripts"
+if str(SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(SCRIPTS_DIR))
+
+from master_avwap_lib import trader_fit as tf  # noqa: E402
+from master_avwap_lib.m30_extended_pullback import (  # noqa: E402
+    stamp_m30_extended_pullbacks,
+    target_session,
+)
+
+FIXTURE = ROOT_DIR / "tests" / "fixtures" / "pullback_dip_gate_real_tapes_v1.json"
+
+
+def _load_qdel():
+    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
+    entry = payload["symbols"]["QDEL"]
+    m30 = [dict(bar, dt=datetime.fromisoformat(bar["dt"])) for bar in entry["M30"]]
+    d1 = [dict(bar, dt=datetime.fromisoformat(bar["dt"])) for bar in entry["D1"]]
+    return entry["side"], m30, d1
+
+
+SIDE, QDEL_M30, QDEL_D1 = _load_qdel()
+
+#: Bars appended for the "fire yesterday" case. Closes stay near 10.7, well
+#: under the 65-SMA (~10.9), so no new fire forms on 09-24 and the tape stays
+#: fresh for `now = 09-24 09:00`.
+EXTRA_M30 = [
+    {"dt": datetime(2026, 9, 24, 6, 30), "open": 10.68, "high": 10.75, "low": 10.64, "close": 10.70},
+    {"dt": datetime(2026, 9, 24, 7, 0), "open": 10.70, "high": 10.78, "low": 10.66, "close": 10.72},
+    {"dt": datetime(2026, 9, 24, 7, 30), "open": 10.72, "high": 10.74, "low": 10.65, "close": 10.69},
+    {"dt": datetime(2026, 9, 24, 8, 0), "open": 10.69, "high": 10.76, "low": 10.67, "close": 10.71},
+]
+
+#: Midday on the fire day: the 06:30 bucket is complete, the session is open.
+NOW = datetime(2026, 9, 23, 9, 0)
+
+
+class _Frame:
+    """The shape `intraday_history.frame_to_bars` reads, built from plain bars."""
+
+    columns = None
+
+    def __init__(self, bars):
+        self._bars = list(bars or ())
+        self.empty = not self._bars
+
+    def iterrows(self):
+        for bar in self._bars:
+            yield bar["dt"], {
+                "Open": bar["open"],
+                "High": bar["high"],
+                "Low": bar["low"],
+                "Close": bar["close"],
+            }
+
+
+class _ExplodingFrame:
+    """A tape that raises while it is converted: malformed, not usable."""
+
+    columns = None
+    empty = False
+
+    def iterrows(self):
+        raise ValueError("corrupt tape")
+
+
+def _daily_frame(d1_bars):
+    """The runner's daily frame: a DataFrame with a `datetime` column."""
+    return pd.DataFrame(
+        {
+            "datetime": [bar["dt"] for bar in d1_bars],
+            "open": [bar["open"] for bar in d1_bars],
+            "high": [bar["high"] for bar in d1_bars],
+            "low": [bar["low"] for bar in d1_bars],
+            "close": [bar["close"] for bar in d1_bars],
+        }
+    )
+
+
+class _Downloader:
+    """Records every chunk; serves `_frames` or raises `_failure`."""
+
+    def __init__(self, frames=None, failure=None):
+        self.calls: list[tuple[list[str], dict]] = []
+        self._frames = dict(frames or {})
+        self._failure = failure
+
+    def __call__(self, symbols, **kwargs):
+        self.calls.append((list(symbols), dict(kwargs)))
+        if self._failure is not None:
+            raise self._failure
+        return {symbol: self._frames.get(symbol) for symbol in symbols}
+
+
+def _extended_row(symbol="QDEL", **overrides):
+    row = {
+        "symbol": symbol,
+        "side": SIDE,
+        "setup_family": "general",
+        # LONG reads UPPER_3, SHORT reads LOWER_3; the values keep
+        # below_prior_day_low away on either side (10.4 < 10.6 < 11.2).
+        "current_band_zone": "UPPER_3" if SIDE == "LONG" else "LOWER_3",
+        "last_close": 10.6,
+        "previous_day_high": 11.2,
+        "previous_day_low": 10.4,
+        "ema21": 10.0,
+        "atr20": 0.5,
+        "extended_closes_outside_band2": 3,
+    }
+    row.update(overrides)
+    return row
+
+
+def _stamp(rows, *, now=NOW, downloader=None, ai_state=None, daily=True):
+    frames = {"QDEL": _Frame(QDEL_M30)}
+    downloader = downloader if downloader is not None else _Downloader(frames)
+    daily_frames = {"QDEL": _daily_frame(QDEL_D1)} if daily else {}
+    return stamp_m30_extended_pullbacks(
+        rows,
+        ai_state=ai_state,
+        daily_frames_by_symbol=daily_frames,
+        now=now,
+        downloader=downloader,
+    ), downloader
+
+
+def _bounds(day: date):
+    from market_session import (
+        get_market_session_close_naive,
+        get_market_session_open_naive,
+    )
+
+    reference = datetime(day.year, day.month, day.day, 12, 0)
+    return (
+        get_market_session_open_naive(reference=reference),
+        get_market_session_close_naive(reference=reference),
+    )
+
+
+# --- the flag ------------------------------------------------------------
+def test_fire_in_the_open_session_flags_waives_bonus_and_tags():
+    row = _extended_row()
+    (flagged, unknown), downloader = _stamp([row])
+    assert (flagged, unknown) == (1, 0)
+    assert downloader.calls == [
+        (["QDEL"], {"period": "1mo", "interval": "30m"})
+    ]
+    assert row["m30_extended_pullback"] is True
+    assert row["m30_extended_pullback_note"] == "sma_reclaim_lrsi 2026-09-23 06:30 SMA65 10.92"
+
+    fit = tf.compute_trader_fit(row)
+    assert fit["fit_rules"] == []
+    assert set(fit["fit_waived_rules"]) == {tf.RULE_ABOVE_THIRD_BAND, tf.RULE_EXTENDED_3_CLOSES}
+    assert tf.FLAG_EXTENDED_PULLBACK in fit["fit_flags"]
+    assert ("extended pullback (M30 LRSI @ 65 SMA)", tf.EXTENDED_PULLBACK_POINTS) in fit["fit_terms"]
+    assert fit["fit_score"] >= 0
+
+    from master_avwap_lib.setup_tagging import EXTENDED_PULLBACK_TAG, derive_setup_tag_payload
+
+    payload = derive_setup_tag_payload(row)
+    assert EXTENDED_PULLBACK_TAG in payload["setup_tags"]
+    assert payload["setup_tag_evidence"][EXTENDED_PULLBACK_TAG] == [
+        row["m30_extended_pullback_note"]
+    ]
+
+
+def test_fire_yesterday_is_a_measured_false_not_unknown():
+    tape = QDEL_M30 + EXTRA_M30
+    downloader = _Downloader({"QDEL": _Frame(tape)})
+    row = _extended_row()
+    flagged, unknown = stamp_m30_extended_pullbacks(
+        [row], daily_frames_by_symbol={"QDEL": _daily_frame(QDEL_D1)},
+        now=datetime(2026, 9, 24, 9, 0), downloader=downloader,
+    )
+    assert (flagged, unknown) == (0, 0)
+    assert row["m30_extended_pullback"] is False
+    assert "m30_extended_pullback_note" not in row
+    fit = tf.compute_trader_fit(row)
+    assert set(fit["fit_rules"]) == {tf.RULE_ABOVE_THIRD_BAND, tf.RULE_EXTENDED_3_CLOSES}
+    assert fit["fit_waived_rules"] == []
+    assert fit["fit_flags"] == []
+    assert tf.EXTENDED_PULLBACK_POINTS not in {points for _name, points in fit["fit_terms"]}
+
+
+# --- unknown: short tape and failed fetch ----------------------------------
+def test_short_tape_stays_unknown_and_a_hard_no():
+    downloader = _Downloader({"QDEL": _Frame(QDEL_M30[:30])})
+    row = _extended_row()
+    flagged, unknown = stamp_m30_extended_pullbacks(
+        [row], daily_frames_by_symbol={"QDEL": _daily_frame(QDEL_D1)},
+        now=NOW, downloader=downloader,
+    )
+    assert (flagged, unknown) == (0, 1)
+    assert row["m30_extended_pullback"] is None
+    assert "m30_extended_pullback_note" not in row
+    fit = tf.compute_trader_fit(row)
+    assert tf.RULE_EXTENDED_3_CLOSES in fit["fit_rules"]
+    assert fit["fit_waived_rules"] == []
+    assert fit["fit_score"] < 0
+
+
+def test_a_failed_fetch_is_unknown_and_logs_once(caplog):
+    downloader = _Downloader({}, failure=OSError("yahoo down"))
+    rows = [_extended_row("AAA"), _extended_row("BBB")]
+    with caplog.at_level(logging.WARNING, logger="master_avwap_lib.m30_extended_pullback"):
+        flagged, unknown = stamp_m30_extended_pullbacks(
+            rows, daily_frames_by_symbol={}, now=NOW, downloader=downloader
+        )
+    assert (flagged, unknown) == (0, 2)
+    assert all(row["m30_extended_pullback"] is None for row in rows)
+    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
+    assert len(warnings) == 1
+    assert "M30" in warnings[0].getMessage() and "fetch" in warnings[0].getMessage()
+
+
+def test_a_malformed_tape_is_unknown_and_the_scan_serves_on(caplog):
+    # The downloader serves a frame whose conversion raises: that row is
+    # unknown, the other row is judged as usual, and the stamp does not raise.
+    downloader = _Downloader({"BAD": _ExplodingFrame(), "QDEL": _Frame(QDEL_M30)})
+    bad, good = _extended_row("BAD"), _extended_row("QDEL")
+    with caplog.at_level(logging.WARNING, logger="master_avwap_lib.m30_extended_pullback"):
+        flagged, unknown = stamp_m30_extended_pullbacks(
+            [bad, good],
+            daily_frames_by_symbol={"QDEL": _daily_frame(QDEL_D1)},
+            now=NOW,
+            downloader=downloader,
+        )
+    assert (flagged, unknown) == (1, 1)
+    assert bad["m30_extended_pullback"] is None
+    assert "m30_extended_pullback_note" not in bad
+    assert good["m30_extended_pullback"] is True
+    fit = tf.compute_trader_fit(bad)
+    assert tf.RULE_EXTENDED_3_CLOSES in fit["fit_rules"]
+    assert fit["fit_waived_rules"] == []
+    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
+    assert len(warnings) == 1
+    assert "BAD" in warnings[0].getMessage()
+
+
+# --- only extended rows are touched ----------------------------------------
+def test_non_extended_rows_are_never_fetched_or_touched():
+    clean = {
+        "symbol": "CLEAN", "side": SIDE, "setup_family": "general",
+        "current_band_zone": "VWAP to UPPER_1" if SIDE == "LONG" else "VWAP to LOWER_1",
+        "last_close": 10.6, "previous_day_high": 11.2, "previous_day_low": 10.4,
+        "ema21": 10.0, "atr20": 0.5, "extended_closes_outside_band2": 0,
+    }
+    extended = _extended_row("QDEL")
+    (flagged, unknown), _downloader = _stamp([clean, extended])
+    assert (flagged, unknown) == (1, 0)
+    assert "m30_extended_pullback" not in clean
+    assert extended["m30_extended_pullback"] is True
+
+
+def test_the_extended_check_uses_the_same_merged_input_as_the_fit():
+    # `below_prior_day_low` is only measurable from the symbol entry here; with
+    # it firing, the row is NOT extended-only, so no fetch and no key at all.
+    row = _extended_row(last_close=11.5)
+    ai_state = {"symbols": {"QDEL": {"previous_day_high": 11.2, "previous_day_low": 10.4}}}
+    downloader = _Downloader({"QDEL": _Frame(QDEL_M30)})
+    flagged, unknown = stamp_m30_extended_pullbacks(
+        [row], ai_state=ai_state, daily_frames_by_symbol={"QDEL": _daily_frame(QDEL_D1)},
+        now=NOW, downloader=downloader,
+    )
+    assert (flagged, unknown) == (0, 0)
+    assert downloader.calls == []
+    assert "m30_extended_pullback" not in row
+    fit = tf.compute_trader_fit(tf.fit_input(row, ai_state["symbols"]["QDEL"], {}))
+    assert tf.RULE_BELOW_PRIOR_DAY_LOW in fit["fit_rules"]
+
+
+# --- the batched fetch -------------------------------------------------------
+def test_the_fetch_is_batched_in_chunks_of_fifty():
+    symbols = [f"S{i:02d}" for i in range(55)]
+    downloader = _Downloader({symbol: _Frame(QDEL_M30) for symbol in symbols})
+    rows = [_extended_row(symbol) for symbol in symbols]
+    flagged, unknown = stamp_m30_extended_pullbacks(
+        rows,
+        daily_frames_by_symbol={symbol: _daily_frame(QDEL_D1) for symbol in symbols},
+        now=NOW,
+        downloader=downloader,
+    )
+    assert [len(called) for called, _kwargs in downloader.calls] == [50, 5]
+    assert (flagged, unknown) == (55, 0)
+
+
+def test_a_small_set_is_one_fetch():
+    symbols = [f"S{i}" for i in range(3)]
+    downloader = _Downloader({symbol: _Frame(QDEL_M30) for symbol in symbols})
+    rows = [_extended_row(symbol) for symbol in symbols]
+    flagged, unknown = stamp_m30_extended_pullbacks(
+        rows,
+        daily_frames_by_symbol={symbol: _daily_frame(QDEL_D1) for symbol in symbols},
+        now=NOW,
+        downloader=downloader,
+    )
+    assert [len(called) for called, _kwargs in downloader.calls] == [3]
+    assert (flagged, unknown) == (3, 0)
+
+
+def test_no_extended_rows_means_no_fetch_at_all():
+    clean = _extended_row(
+        extended_closes_outside_band2=0,
+        current_band_zone="VWAP to UPPER_1" if SIDE == "LONG" else "VWAP to LOWER_1",
+    )
+    downloader = _Downloader({})
+    (flagged, unknown), _dl = _stamp([clean], downloader=downloader)
+    assert (flagged, unknown) == (0, 0)
+    assert downloader.calls == []
+    assert "m30_extended_pullback" not in clean
+
+
+# --- the session clock --------------------------------------------------------
+@pytest.mark.parametrize(
+    ("moment", "judged_day"),
+    [
+        (datetime(2026, 9, 23, 5, 0), date(2026, 9, 22)),  # pre-market -> Tuesday
+        (datetime(2026, 9, 23, 6, 30), date(2026, 9, 23)),  # the open itself -> today
+        (datetime(2026, 9, 23, 14, 0), date(2026, 9, 23)),  # after the bell -> today
+        (datetime(2026, 9, 26, 9, 0), date(2026, 9, 25)),  # Saturday -> Friday
+        (datetime(2026, 9, 25, 5, 0), date(2026, 9, 24)),  # Friday pre-market -> Thursday
+    ],
+)
+def test_target_session_picks_today_once_open_else_the_last_completed_session(
+    moment, judged_day
+):
+    assert target_session(moment) == _bounds(judged_day)
+
+
+@pytest.mark.parametrize(
+    ("now", "expected"),
+    [
+        (datetime(2026, 9, 23, 5, 0), False),  # pre-market: judged on Tuesday, no fire there
+        (datetime(2026, 9, 23, 14, 0), True),  # after the bell: the fire still counts
+        (datetime(2026, 9, 23, 6, 45), False),  # the 06:30 bucket is still printing
+    ],
+)
+def test_the_session_clock_end_to_end(now, expected):
+    row = _extended_row()
+    (flagged, unknown), _downloader = _stamp([row], now=now)
+    assert row["m30_extended_pullback"] is expected
+    if expected:
+        assert (flagged, unknown) == (1, 0)
+    else:
+        assert unknown == 0  # measured False, not unknown
+
+
+# --- where the scan runs it ---------------------------------------------------
+def test_the_runner_stamps_immediately_before_the_fit_pass_and_off_scan_runs_never_fetch():
+    from master_avwap_lib import legacy, runner
+
+    source = inspect.getsource(runner)
+    matches = [
+        match
+        for match in re.finditer(r"stamp_m30_extended_pullbacks\(\s*priority_rows", source)
+    ]
+    assert len(matches) == 1
+    tail = source[matches[0].end() : matches[0].end() + 500]
+    assert "apply_trader_fit_ranking(priority_rows, ai_state, feature_rows_by_symbol)" in tail
+    # STABLE replay and tracker backfill live in legacy.py and must never fetch.
+    assert "stamp_m30_extended_pullbacks" not in inspect.getsource(legacy)
```

# LEAD TEST RESULTS
## builder's own test command (exit null)
```
own suite skipped (SKIP_OWN=1)
```
## lint (exit 0)
```
All checks passed!
```
## hidden reference tests (exit 1)
```
E         + 2026-10-02T06:30:00

tests\ref_test_m30_extended_pullback.py:229: AssertionError
_ test_target_session_is_today_once_open_else_the_last_completed[now3-2026-10-02-evaluate_at3] _

fixed_session_hours = None, now = datetime.datetime(2026, 10, 3, 10, 0)
session = '2026-10-02', evaluate_at = datetime.datetime(2026, 10, 2, 13, 0)

    @pytest.mark.parametrize(
        "now, session, evaluate_at",
        [
            # Inside Monday's session: today, read up to now.
            (datetime(2026, 10, 5, 9, 0), "2026-10-05", datetime(2026, 10, 5, 9, 0)),
            # After Monday's close: today, capped at the close.
            (datetime(2026, 10, 5, 18, 0), "2026-10-05", datetime(2026, 10, 5, 13, 0)),
            # Monday before the open: Friday's completed session.
            (datetime(2026, 10, 5, 5, 0), "2026-10-02", datetime(2026, 10, 2, 13, 0)),
            # Saturday: Friday's completed session.
            (datetime(2026, 10, 3, 10, 0), "2026-10-02", datetime(2026, 10, 2, 13, 0)),
        ],
    )
    def test_target_session_is_today_once_open_else_the_last_completed(fixed_session_hours, now, session, evaluate_at):
        got_session, got_at = m30.target_session(now)
>       assert got_session.isoformat() == session
E       AssertionError: assert '2026-10-02T06:30:00' == '2026-10-02'
E         
E         - 2026-10-02
E         + 2026-10-02T06:30:00

tests\ref_test_m30_extended_pullback.py:229: AssertionError
_____ test_the_runner_calls_the_fit_pass_right_after_the_expected_r_pass ______

    def test_the_runner_calls_the_fit_pass_right_after_the_expected_r_pass():
        import inspect
    
        source = inspect.getsource(runner._run_master_impl)
        expected_r_at = source.index("apply_expected_r_ranking(")
>       m30_at = source.index("stamp_m30_extended_pullback(")
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       ValueError: substring not found

tests\ref_test_trader_fit_rank_golden.py:94: ValueError
=========================== short test summary info ===========================
FAILED tests/ref_test_m30_extended_pullback.py::test_a_reversal_inside_the_session_sets_the_flag
FAILED tests/ref_test_m30_extended_pullback.py::test_a_reversal_in_an_earlier_session_does_not_set_the_flag
FAILED tests/ref_test_m30_extended_pullback.py::test_missing_or_short_bars_are_unknown
FAILED tests/ref_test_m30_extended_pullback.py::test_shorts_read_the_mirrored_rule
FAILED tests/ref_test_m30_extended_pullback.py::test_flag_waiver_and_bonus_end_to_end
FAILED tests/ref_test_m30_extended_pullback.py::test_a_reversal_yesterday_leaves_the_row_a_hard_no
FAILED tests/ref_test_m30_extended_pullback.py::test_missing_bars_are_unknown_and_the_row_stays_a_hard_no
FAILED tests/ref_test_m30_extended_pullback.py::test_a_failed_fetch_is_unknown_for_every_name_and_never_raises
FAILED tests/ref_test_m30_extended_pullback.py::test_rows_that_are_not_extended_are_never_touched_or_fetched
FAILED tests/ref_test_m30_extended_pullback.py::test_one_batched_fetch_for_the_extended_subset
FAILED tests/ref_test_m30_extended_pullback.py::test_inputs_missing_on_the_row_are_read_from_the_symbol_entry
FAILED tests/ref_test_m30_extended_pullback.py::test_target_session_is_today_once_open_else_the_last_completed[now0-2026-10-05-evaluate_at0]
FAILED tests/ref_test_m30_extended_pullback.py::test_target_session_is_today_once_open_else_the_last_completed[now1-2026-10-05-evaluate_at1]
FAILED tests/ref_test_m30_extended_pullback.py::test_target_session_is_today_once_open_else_the_last_completed[now2-2026-10-02-evaluate_at2]
FAILED tests/ref_test_m30_extended_pullback.py::test_target_session_is_today_once_open_else_the_last_completed[now3-2026-10-02-evaluate_at3]
FAILED tests/ref_test_trader_fit_rank_golden.py::test_the_runner_calls_the_fit_pass_right_after_the_expected_r_pass
16 failed, 5 passed in 1.72s
```

# BUILDER SELF-REVIEW
```json
(none)
```

# REFERENCE DIFF (the merged change, for comparison)
```diff
diff --git a/scripts/master_avwap_lib/m30_extended_pullback.py b/scripts/master_avwap_lib/m30_extended_pullback.py
new file mode 100644
index 00000000..69205c51
--- /dev/null
+++ b/scripts/master_avwap_lib/m30_extended_pullback.py
@@ -0,0 +1,212 @@
+"""M30 extended pullback: the trader's favourite D1 setup (trader 2026-10-05).
+
+"My favourite setups lately are these super extended stocks that make an M30
+LRSI reversal near the m30 65 SMA (while staying above it) for longs. Make sure
+we flag these as well."
+
+The rule is the Pullback alert's own (`indicators.pullback_sma_reclaim.evaluate`
+on the M30 65-SMA): a dip to the SMA (or a close break and reclaim), an LRSI
+bear flip under 20, then the 80 up-cross. The flag is set only when that fire's
+bar is in the target session: today's once it has opened, else the last
+completed one. Shorts read the mirrored rule the module already applies.
+
+Only rows whose ONLY hard no's are `above_third_band` / `extended_3_closes`
+are evaluated, so the fetch stays small. A failed fetch leaves the flag None
+(unknown) and never fails the scan. `evaluate_extended_pullback` is pure; the
+fetch and the session clock live in the thin wrapper below it.
+"""
+
+from __future__ import annotations
+
+import logging
+from collections.abc import Callable, Iterable, Mapping, MutableMapping
+from datetime import date, datetime, timedelta
+from typing import Any
+
+from indicators.pullback_sma_reclaim import M30_SMA_LENGTH, evaluate
+
+from . import trader_fit
+
+#: The bar size the rule reads.
+M30_MINUTES = 30
+#: How much M30 history one download asks for (~22 sessions; warm-up is 75 bars).
+FETCH_PERIOD = "1mo"
+#: Most symbols in one batched download.
+FETCH_CHUNK = 50
+#: Daily bars handed to the dip gate's D1 ATR.
+DAILY_BARS_FOR_ATR = 60
+#: Rows are evaluated only when their hard no's are all in this set.
+SCOPE_RULES = frozenset({trader_fit.RULE_ABOVE_THIRD_BAND, trader_fit.RULE_EXTENDED_3_CLOSES})
+
+FIELD_FLAG = "m30_extended_pullback"
+FIELD_NOTE = "m30_extended_pullback_note"
+
+
+def in_scope(fit_inputs: Mapping[str, Any]) -> bool:
+    """True when the row is a hard no ONLY for being extended."""
+    fired, _unknown = trader_fit.hard_no_rules(fit_inputs)
+    return bool(fired) and set(fired) <= SCOPE_RULES
+
+
+def evaluate_extended_pullback(
+    m30_bars: Iterable[Mapping[str, Any]] | None,
+    *,
+    side: str,
+    now: datetime,
+    session_date: date,
+    daily_bars: Iterable[Mapping[str, Any]] | None = None,
+) -> tuple[bool | None, str]:
+    """(flag, note) for one symbol. None when the M30 tape cannot answer."""
+    bars = list(m30_bars or [])
+    if not bars:
+        return None, "M30 bars unavailable"
+    result = evaluate(
+        bars,
+        side=str(side or "").strip().lower() or "long",
+        sma_length=M30_SMA_LENGTH,
+        bar_minutes=M30_MINUTES,
+        armed_at=None,
+        now=now,
+        daily_bars=daily_bars,
+    )
+    if result is None:
+        return None, f"M30 not measured ({len(bars)} bars, needs {M30_SMA_LENGTH + 10})"
+    in_session = [fire for fire in result.fired if fire.bar_dt.date() == session_date]
+    if not in_session:
+        return False, f"no M30 {M30_SMA_LENGTH}-SMA LRSI reversal in the {session_date.isoformat()} session"
+    fire = max(in_session, key=lambda hit: hit.bar_dt)
+    return True, (
+        f"{fire.trigger} {fire.bar_dt:%Y-%m-%d %H:%M} M30 SMA{M30_SMA_LENGTH} {fire.sma:.2f}"
+    )
+
+
+def target_session(now_local: datetime) -> tuple[date, datetime]:
+    """(session date, evaluation time) on the naive market-local clock.
+
+    Today's session once it has opened; before the open or on a closed day,
+    the last completed one. The evaluation time is capped at that session's
+    close so a Monday-morning scan still reads Friday's completed bars.
+    """
+    import market_calendar
+    from market_session import get_market_session_close_naive, get_market_session_open_naive
+
+    today = now_local.date()
+    if market_calendar.is_session(today) and now_local >= get_market_session_open_naive(reference=now_local):
+        session = today
+    else:
+        session = market_calendar.previous_session(today)
+    close = get_market_session_close_naive(reference=datetime.combine(session, datetime.min.time()) + timedelta(hours=12))
+    return session, min(now_local, close)
+
+
+def fetch_m30_bars(symbols: list[str], *, now: datetime) -> dict[str, list[dict[str, Any]]]:
+    """Completed M30 bars per symbol, one batched yfinance call per chunk."""
+    from intraday_history import _download, frame_to_bars, interval_label
+
+    out: dict[str, list[dict[str, Any]]] = {}
+    for start in range(0, len(symbols), FETCH_CHUNK):
+        chunk = symbols[start:start + FETCH_CHUNK]
+        payload = _download(chunk, period=FETCH_PERIOD, interval=interval_label(M30_MINUTES))
+        for symbol, frame in (payload or {}).items():
+            bars = frame_to_bars(frame, now=now, interval_minutes=M30_MINUTES)
+            if bars:
+                out[str(symbol).upper()] = bars
+    return out
+
+
+def _daily_bar_dicts(frame: Any) -> list[dict[str, Any]] | None:
+    """The scan's daily frame as plain bar dicts for the dip gate's ATR."""
+    if frame is None:
+        return None
+    try:
+        tail = frame.tail(DAILY_BARS_FOR_ATR)
+        bars = []
+        for _, row in tail.iterrows():
+            stamp = row.get("datetime")
+            if stamp is None or stamp != stamp:
+                continue
+            bars.append({
+                "date": stamp.date().isoformat() if hasattr(stamp, "date") else str(stamp)[:10],
+                "open": float(row["open"]),
+                "high": float(row["high"]),
+                "low": float(row["low"]),
+                "close": float(row["close"]),
+            })
+        return bars
+    except Exception:  # noqa: BLE001 - no daily bars only narrows the dip gate to its close path
+        return None
+
+
+def stamp_m30_extended_pullback(
+    rows: list[dict] | None,
+    *,
+    ai_state: Mapping[str, Any] | None = None,
+    feature_rows_by_symbol: Mapping[str, MutableMapping[str, Any]] | None = None,
+    daily_frames_by_symbol: Mapping[str, Any] | None = None,
+    now_local: datetime | None = None,
+    fetch: Callable[..., Mapping[str, list]] | None = None,
+) -> dict[str, int]:
+    """Stamp the flag on extended rows only. Never raises; never touches other rows."""
+    symbols_state = ai_state.get("symbols", {}) if isinstance(ai_state, Mapping) else {}
+    features = feature_rows_by_symbol if isinstance(feature_rows_by_symbol, Mapping) else {}
+    scoped: list[dict] = []
+    for row in rows or []:
+        if not isinstance(row, dict):
+            continue
+        symbol = str(row.get("symbol") or "").strip().upper()
+        inputs = trader_fit._fit_inputs(row, symbols_state.get(symbol), features.get(symbol))
+        if symbol and in_scope(inputs):
+            scoped.append(row)
+    summary = {"scoped": len(scoped), "flagged": 0, "unknown": 0}
+    if not scoped:
+        return summary
+
+    try:
+        if now_local is None:
+            from market_session import get_market_local_now
+
+            now_local = get_market_local_now().replace(tzinfo=None)
+        session, evaluate_at = target_session(now_local)
+    except Exception as exc:  # noqa: BLE001 - no session clock = unknown, never a verdict
+        logging.warning("M30 extended pullback: session clock unavailable (%s); flags unknown.", exc)
+        session = evaluate_at = None
+
+    symbols = sorted({str(row.get("symbol") or "").strip().upper() for row in scoped})
+    bars_by_symbol: Mapping[str, list] = {}
+    if session is not None:
+        try:
+            bars_by_symbol = (fetch or fetch_m30_bars)(symbols, now=evaluate_at) or {}
+        except Exception as exc:  # noqa: BLE001 - a failed fetch is unknown, never a failed scan
+            logging.warning(
+                "M30 extended pullback: fetch failed for %d symbol(s) (%s); flags unknown.",
+                len(symbols),
+                exc,
+            )
+            bars_by_symbol = {}
+
+    for row in scoped:
+        symbol = str(row.get("symbol") or "").strip().upper()
+        if session is None:
+            flag, note = None, "session clock unavailable"
+        else:
+            try:
+                flag, note = evaluate_extended_pullback(
+                    bars_by_symbol.get(symbol),
+                    side=str(row.get("side") or ""),
+                    now=evaluate_at,
+                    session_date=session,
+                    daily_bars=_daily_bar_dicts((daily_frames_by_symbol or {}).get(symbol)),
+                )
+            except Exception as exc:  # noqa: BLE001 - one bad tape is unknown, not a failed scan
+                flag, note = None, f"M30 evaluation failed ({exc})"
+        row[FIELD_FLAG] = flag
+        row[FIELD_NOTE] = note
+        for mirror in (symbols_state.get(symbol), features.get(symbol)):
+            if isinstance(mirror, MutableMapping):
+                mirror[FIELD_FLAG] = flag
+                mirror[FIELD_NOTE] = note
+        if flag is True:
+            summary["flagged"] += 1
+        elif flag is None:
+            summary["unknown"] += 1
+    return summary
diff --git a/scripts/master_avwap_lib/runner.py b/scripts/master_avwap_lib/runner.py
index 69b9a105..debdf8f6 100644
--- a/scripts/master_avwap_lib/runner.py
+++ b/scripts/master_avwap_lib/runner.py
@@ -13,6 +13,7 @@ from indicators.d1_environment import classify_environment as classify_d1_enviro
 from . import legacy as _legacy
 from .d1_zone_arms import build_d1_zone_arms
 from .setup_tagging import apply_setup_tag_payload, canonicalize_priority_setup_tags
+from .m30_extended_pullback import stamp_m30_extended_pullback
 from .trader_fit import apply_trader_fit_ranking, extension_closes_outside_second_band
 from master_avwap_shared import build_active_bounce_summary, load_master_avwap_events_for_date
 from long_setups_store import publish_long_setups
@@ -2646,8 +2647,21 @@ def _run_master_impl(
         recent_family_rows=recent_family_rows,
         reference_date=today_run,
     )
-    # Trader fit (trader 2026-10-05): `score` becomes the Fit; the proven-quality
-    # score stays on the row as the tiebreak.
+    # Trader fit (trader 2026-10-05): extended rows first get the M30 65-SMA
+    # pullback flag (their only waiver), then `score` becomes the Fit; the
+    # proven-quality score stays on the row as the tiebreak.
+    m30_pullback_summary = stamp_m30_extended_pullback(
+        priority_rows,
+        ai_state=ai_state,
+        feature_rows_by_symbol=feature_rows_by_symbol,
+        daily_frames_by_symbol=daily_frames_by_symbol,
+    )
+    logging.info(
+        "M30 extended pullback: %d extended row(s) checked, %d flagged, %d unknown.",
+        m30_pullback_summary["scoped"],
+        m30_pullback_summary["flagged"],
+        m30_pullback_summary["unknown"],
+    )
     apply_trader_fit_ranking(priority_rows, ai_state, feature_rows_by_symbol)
     swing_quality_shadow_count = apply_swing_quality_demotion(
         priority_rows, load_swing_quality_settings()
diff --git a/tests/test_m30_extended_pullback.py b/tests/test_m30_extended_pullback.py
new file mode 100644
index 00000000..8741ba09
--- /dev/null
+++ b/tests/test_m30_extended_pullback.py
@@ -0,0 +1,230 @@
+"""M30 extended pullback flag (trader 2026-10-05), on synthetic M30 tapes."""
+
+from __future__ import annotations
+
+import sys
+from datetime import datetime, timedelta
+from pathlib import Path
+
+import pytest
+
+ROOT_DIR = Path(__file__).resolve().parents[1]
+SCRIPTS_DIR = ROOT_DIR / "scripts"
+TESTS_DIR = ROOT_DIR / "tests"
+for folder in (SCRIPTS_DIR, TESTS_DIR):
+    if str(folder) not in sys.path:
+        sys.path.insert(0, str(folder))
+
+import test_pct1_pullback_alert as tape  # noqa: E402
+from master_avwap_lib import m30_extended_pullback as m30  # noqa: E402
+from master_avwap_lib import trader_fit as tf  # noqa: E402
+from master_avwap_lib.setup_tagging import EXTENDED_PULLBACK_TAG, canonicalize_priority_setup_tags  # noqa: E402
+
+FIRE_INDEX = tape.M30_RECLAIM_INDEX
+FIRE_DT = tape.bar_dt(FIRE_INDEX, 30)
+NOW = tape.bar_end(FIRE_INDEX, 30)
+
+
+def _long_bars():
+    return tape.make_bars(tape.M30_LONG_CLOSES[: FIRE_INDEX + 1], 30)
+
+
+def _extended_long(symbol="EXT", **overrides):
+    row = {
+        "symbol": symbol,
+        "side": "LONG",
+        "setup_family": "avwap_breakout",
+        "current_band_zone": "UPPER_3",
+        "last_close": 120.0,
+        "previous_day_high": 121.0,
+        "previous_day_low": 115.0,
+        "ema21": 112.0,
+        "atr20": 4.0,
+        "extended_closes_outside_band2": 4,
+        "proven_quality_score": 70.0,
+        "score": 70.0,
+    }
+    row.update(overrides)
+    return row
+
+
+class _Daily:
+    """A daily frame stand-in whose bars open the dip gate wide (ATR ~1e9)."""
+
+    def tail(self, _count):
+        return self
+
+    def iterrows(self):
+        for index, bar in enumerate(tape.open_gate_daily_bars()):
+            yield index, {**bar, "datetime": bar["dt"]}
+
+
+@pytest.fixture
+def session_today(monkeypatch):
+    monkeypatch.setattr(m30, "target_session", lambda now_local: (FIRE_DT.date(), NOW))
+
+
+def _stamp(rows, bars_by_symbol, calls=None, **kwargs):
+    def fetch(symbols, *, now):
+        if calls is not None:
+            calls.append((list(symbols), now))
+        return {symbol: bars_by_symbol.get(symbol) for symbol in symbols}
+
+    return m30.stamp_m30_extended_pullback(
+        rows,
+        daily_frames_by_symbol={row["symbol"]: _Daily() for row in rows},
+        now_local=NOW,
+        fetch=fetch,
+        **kwargs,
+    )
+
+
+# --- the pure rule -------------------------------------------------------------
+def test_a_reversal_inside_the_session_sets_the_flag():
+    flag, note = m30.evaluate_extended_pullback(
+        _long_bars(), side="LONG", now=NOW, session_date=FIRE_DT.date(),
+        daily_bars=tape.open_gate_daily_bars(),
+    )
+    assert flag is True
+    assert "SMA65" in note and FIRE_DT.strftime("%Y-%m-%d %H:%M") in note
+
+
+def test_a_reversal_in_an_earlier_session_does_not_set_the_flag():
+    flag, note = m30.evaluate_extended_pullback(
+        _long_bars(), side="LONG", now=NOW + timedelta(days=1),
+        session_date=FIRE_DT.date() + timedelta(days=1),
+        daily_bars=tape.open_gate_daily_bars(),
+    )
+    assert flag is False
+    assert "no M30 65-SMA" in note
+
+
+def test_missing_or_short_bars_are_unknown():
+    assert m30.evaluate_extended_pullback([], side="LONG", now=NOW, session_date=FIRE_DT.date())[0] is None
+    short = _long_bars()[:40]
+    assert m30.evaluate_extended_pullback(short, side="LONG", now=NOW, session_date=FIRE_DT.date())[0] is None
+
+
+def test_shorts_read_the_mirrored_rule():
+    flag, _note = m30.evaluate_extended_pullback(
+        tape.mirror(_long_bars()), side="SHORT", now=NOW, session_date=FIRE_DT.date(),
+        daily_bars=tape.open_gate_daily_bars(),
+    )
+    assert flag is True
+
+
+def test_the_rule_reads_the_65_sma():
+    assert m30.M30_SMA_LENGTH == 65
+
+
+# --- the scan wrapper ----------------------------------------------------------
+def test_flag_waiver_and_bonus_end_to_end(session_today):
+    row = _extended_long()
+    summary = _stamp([row], {"EXT": _long_bars()})
+    assert summary == {"scoped": 1, "flagged": 1, "unknown": 0}
+    assert row["m30_extended_pullback"] is True
+    tf.apply_trader_fit_ranking([row])
+    assert row["fit_rules"] == []
+    assert set(row["fit_waived_rules"]) == {tf.RULE_ABOVE_THIRD_BAND, tf.RULE_EXTENDED_3_CLOSES}
+    assert row["score"] >= 0
+    assert "waived: M30 pullback" in row["fit_note"]
+    canonicalize_priority_setup_tags([row])
+    assert EXTENDED_PULLBACK_TAG in row["setup_tags"]
+
+
+def test_a_reversal_yesterday_leaves_the_row_a_hard_no(monkeypatch):
+    monkeypatch.setattr(
+        m30, "target_session",
+        lambda now_local: (FIRE_DT.date() + timedelta(days=1), NOW + timedelta(days=1)),
+    )
+    row = _extended_long()
+    _stamp([row], {"EXT": _long_bars()})
+    assert row["m30_extended_pullback"] is False
+    tf.apply_trader_fit_ranking([row])
+    assert row["score"] < 0
+
+
+def test_missing_bars_are_unknown_and_the_row_stays_a_hard_no(session_today):
+    row = _extended_long()
+    summary = _stamp([row], {})
+    assert summary["unknown"] == 1
+    assert row["m30_extended_pullback"] is None
+    assert row["m30_extended_pullback_note"] == "M30 bars unavailable"
+    tf.apply_trader_fit_ranking([row])
+    assert row["fit_rules"] and row["score"] < 0
+
+
+def test_a_failed_fetch_is_unknown_for_every_name_and_never_raises(session_today, caplog):
+    rows = [_extended_long("EXT"), _extended_long("EXU")]
+
+    def broken(symbols, *, now):
+        raise RuntimeError("yahoo down")
+
+    summary = m30.stamp_m30_extended_pullback(rows, now_local=NOW, fetch=broken)
+    assert summary == {"scoped": 2, "flagged": 0, "unknown": 2}
+    assert all(row["m30_extended_pullback"] is None for row in rows)
+    assert sum("fetch failed" in record.getMessage() for record in caplog.records) == 1
+
+
+def test_rows_that_are_not_extended_are_never_touched_or_fetched(session_today):
+    clean = _extended_long("CLN", current_band_zone="UPPER_1 to UPPER_2", extended_closes_outside_band2=1)
+    under_low = _extended_long("LOW", last_close=110.0)  # extended AND under yesterday's low
+    unknown = _extended_long("UNK", current_band_zone="", extended_closes_outside_band2=None)
+    calls: list = []
+    summary = _stamp([clean, under_low, unknown], {}, calls=calls)
+    assert summary["scoped"] == 0
+    assert calls == []
+    for row in (clean, under_low, unknown):
+        assert "m30_extended_pullback" not in row
+
+
+def test_one_batched_fetch_for_the_extended_subset(session_today):
+    rows = [_extended_long("EXT"), _extended_long("EXU"), _extended_long("CLN", current_band_zone="VWAP to UPPER_1",
+                                                                         extended_closes_outside_band2=0)]
+    calls: list = []
+    _stamp(rows, {"EXT": _long_bars(), "EXU": _long_bars()}, calls=calls)
+    assert [symbols for symbols, _now in calls] == [["EXT", "EXU"]]
+
+
+def test_inputs_missing_on_the_row_are_read_from_the_symbol_entry(session_today):
+    row = {"symbol": "EXT", "side": "LONG", "current_band_zone": "UPPER_3", "extended_closes_outside_band2": 4}
+    ai_state = {"symbols": {"EXT": {"last_close": 120.0, "previous_day_low": 115.0}}}
+    features: dict = {"EXT": {}}
+    _stamp([row], {"EXT": _long_bars()}, ai_state=ai_state, feature_rows_by_symbol=features)
+    assert row["m30_extended_pullback"] is True
+    assert ai_state["symbols"]["EXT"]["m30_extended_pullback"] is True
+    assert features["EXT"]["m30_extended_pullback_note"] == row["m30_extended_pullback_note"]
+
+
+# --- the session clock ---------------------------------------------------------
+@pytest.fixture
+def fixed_session_hours(monkeypatch):
+    import market_session
+
+    def opened(reference=None, local_timezone_name=None):
+        return datetime.combine(reference.date(), datetime.min.time()).replace(hour=6, minute=30)
+
+    def closed(reference=None, local_timezone_name=None):
+        return datetime.combine(reference.date(), datetime.min.time()).replace(hour=13)
+
+    monkeypatch.setattr(market_session, "get_market_session_open_naive", opened)
+    monkeypatch.setattr(market_session, "get_market_session_close_naive", closed)
+
+
+@pytest.mark.parametrize(
+    "now, session, evaluate_at",
+    [
+        # Inside Monday's session: today, read up to now.
+        (datetime(2026, 10, 5, 9, 0), "2026-10-05", datetime(2026, 10, 5, 9, 0)),
+        # After Monday's close: today, capped at the close.
+        (datetime(2026, 10, 5, 18, 0), "2026-10-05", datetime(2026, 10, 5, 13, 0)),
+        # Monday before the open: Friday's completed session.
+        (datetime(2026, 10, 5, 5, 0), "2026-10-02", datetime(2026, 10, 2, 13, 0)),
+        # Saturday: Friday's completed session.
+        (datetime(2026, 10, 3, 10, 0), "2026-10-02", datetime(2026, 10, 2, 13, 0)),
+    ],
+)
+def test_target_session_is_today_once_open_else_the_last_completed(fixed_session_hours, now, session, evaluate_at):
+    got_session, got_at = m30.target_session(now)
+    assert got_session.isoformat() == session
+    assert got_at == evaluate_at
diff --git a/tests/test_trader_fit_rank_golden.py b/tests/test_trader_fit_rank_golden.py
index b116ae89..19f51af8 100644
--- a/tests/test_trader_fit_rank_golden.py
+++ b/tests/test_trader_fit_rank_golden.py
@@ -91,9 +91,11 @@ def test_the_runner_calls_the_fit_pass_right_after_the_expected_r_pass():
 
     source = inspect.getsource(runner._run_master_impl)
     expected_r_at = source.index("apply_expected_r_ranking(")
+    m30_at = source.index("stamp_m30_extended_pullback(")
     fit_at = source.index("apply_trader_fit_ranking(")
     demotion_at = source.index("apply_swing_quality_demotion(")
-    assert expected_r_at < fit_at < demotion_at
+    tags_at = source.index("canonicalize_priority_setup_tags(")
+    assert expected_r_at < m30_at < fit_at < demotion_at < tags_at
 
 
 def test_the_legacy_replay_and_backfill_call_the_fit_pass():
```

## Lead note (measured by the lead, not by the builder)

- This is the final state after one rework pass. The first pass ended at the harness's 80-turn cap (no self-review); the rework pass fixed the one reviewer blocker that reproduced: frame_to_bars/_daily_bars/judge now sit inside per-symbol try/except so a malformed tape is None, never a failed scan, with one new test.
- Builder's own tests: 19 passed in isolation; ruff clean. Every test module importing master_avwap_lib or trader_fit: 1877 passed, 2 failed, both git-history tests in test_ws_rp_shared_report that fail in any harness worktree (no history there), unrelated to the diff. No whole-suite run on this pass; the earlier one crashed in an unrelated Qt test under memory pressure.
- Hidden reference tests: 5 passed / 16 failed, unchanged. Causes: 7 failures import `stamp_m30_extended_pullback` (builder named it `stamp_m30_extended_pullbacks`), 4 want `evaluate_extended_pullback` (not defined under that name), the rest assert session dates as `'2026-10-05'` where the builder returns `'2026-10-05T06:30:00'`.
- The waiver/bonus branch in trader_fit.py (FLAG_EXTENDED_PULLBACK, WAIVABLE_RULES, EXTENDED_PULLBACK_POINTS) and the setup tag in setup_tagging.py already existed at the parent commit; neither the builder nor the reference commit added them. The builder only renamed `_fit_inputs` to `fit_input` in trader_fit.py (no other callers).
