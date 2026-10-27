# BRIEF
Goal: the Technical Integrity "tape" light should read SPY's own completed-M5 range against a per-session-hour norm, with the TICK range light as the fallback. Measured over 139 session-hours SPY M5 range (high-low)/close*100 vs its hour norm is the cleanest tape-speed signal (leads next-hour level respect r=-0.56; TICK and VXX add nothing). Keep the thresholds: calm < 0.8, fast > 1.25 of norm, unknown under 3 bars or a bar older than 15 min.
Make a generic tape_speed_light() for a completed-M5 range against a per-hour norm; tick_range_light() becomes a thin wrapper over it. Add SPY per-session-hour range norms (30 sessions ending 2026-10-05, derive or stub them clearly). tape_light() uses SPY when known, else the TICK light (wide = fast, source "TICK"), else source "none" with the SPY reason. The monitor gets a spy_bars_provider and writes market.tape fail-open (a raising provider falls back to TICK), still writing market.tick as before; legacy.py wires it in one line reading the latest_bars cache only, never IB. The chip says "tape fast/normal/calm" (omitted when source is none) and the tooltip names SPY or "TICK fallback".
Done when: new tests cover the light, the fallback order, the fail-open monitor write and the chip text, and `python scripts/run_tests.py` (or pytest on tests/) plus ruff are green.
Files: scripts/technical_integrity.py (tick_range_light, tape light, _publish_snapshot); find the chip and legacy.py call site.
Don't touch: order/sizing code, IB connection code, the existing TICK thresholds, other snapshot fields.
Pattern: copy tick_range_light() and its existing tests; the monitor provider follows the existing bars provider hooks.

# CANDIDATE DIFF
```diff
diff --git a/CHANGELOG.md b/CHANGELOG.md
index ab95064..79c1de9 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -1,5 +1,6 @@
 # Changelog
 
+- 2026-10-27 Tape speed light (branch): the Technical Integrity tape light reads SPY's own completed-M5 range ((high-low)/close*100) against a per-session-hour norm (`SESSION_HOUR_SPY_RANGE_NORMS`, derived from the 4 local sessions ending 2026-10-05 - a stub of the 30-session window); `tape_speed_light()` is the generic 30-min completed-bar light (calm < 0.8, fast > 1.25 of the norm, unknown under 3 bars or a bar older than 15 min) with `tick_range_light()` as a thin wrapper (TICK schema, "wide" label and 1-decimal rounding preserved); `tape_light()` takes SPY when known, else the TICK light (wide = fast, source "TICK"), else source "none" with the SPY reason; the monitor writes `market.tape` fail-open from a `spy_bars_provider` (legacy feeds the SPY `latest_bars` cache only, never IB) while `market.tick` is written as before; the chip says "tape fast/normal/calm" (omitted when unknown) and the tooltip names SPY or "TICK fallback".
 - 2026-10-05 Technicals "now" (branch, scoring change on the trader's word): the Technicals chip leads with the last 60 min of level tests vs the measured norm for each session hour (`rolling_technical_integrity`, 5.5 = normal for this hour; D1 building in the last half hour) plus a NYSE TICK range light (`tick_range_light`: calm/normal/wide vs the hour's usual M5 range, unknown when stale); D1 day scores centre on 0.69 (`d1_neutral_respect_probability`) instead of 0.736; the day-cumulative read is unchanged under "Today so far"; `read_ledger_tail` moved to `vold_recorder` (re-exported by the UVXY service).
 - 2026-10-05 Trader fit (branch, trader: "I'd like these scans to mimic the things I like and prioritize and not necessarily what the data says"): the D1 Master AVWAP score and order are now the trader fit (`master_avwap_lib/trader_fit.py`, 0-100: family and feature weights signed by 1,107 D1 like/veto clicks; EMA21 distance past 2 ATR, compression, trendline in the way, adverse candle and HV levels cost points); hard no's (above the 3rd band, close under yesterday's low, 3+ closes outside the 2nd band) sit below every clean row with the rule named; an extended name with the Pullback alert's M30 LRSI reversal at the 65 SMA in the session is flagged (tag `EXTENDED_PULLBACK_M30_LRSI_65_SMA`, fetched on the scan worker for the extended subset only), waives the two extension rules and gets a bonus. The proven-quality score is kept as the tiebreak and for bucket/tier thresholds, the day-trade candidate and the D1 alert number. The Pullback alert's M30 SMA is 65 (was 75). Report: `scripts/trader_fit_report.py`. Gate #361. v2 same day: extended pullback +10 (was +20) with no EMA21 penalty on the flagged row; a hard no is never an S/A row; the D1 table keeps the Fit order under the Working-lately switch; the Auto watchlist fill follows Fit and skips hard no's.
 - 2026-10-05 Pete's brief (branch, trader: "an area beside the market forecast in Day Recap to add the daily market brief from Pete (OneOption)"): Day Review gets a "Paste Pete's brief…" button and a "Pete's market brief (OneOption)" box beside the External forecast; stored verbatim as market-journal origin `pete_brief` (one per session, a re-paste supersedes only Pete's, optional "written at"); never graded, listed, drafted as a thesis, in the econ brief or the Mentor's own reads (`market_journal.is_outside_entry`). The night Day Review story and show read it as a cited, capped, droppable `pete_brief` section labelled outside commentary; the week-final Market picture reads the week's briefs as a separate input and may add up to two lines starting "Pete" whose numbers, tickers and dates come from his text (advice words still reject; a new paste re-runs the read; no brief = unchanged). Gate #360.
diff --git a/scripts/bounce_bot_lib/legacy.py b/scripts/bounce_bot_lib/legacy.py
index 7636909..ac5ea1b 100644
--- a/scripts/bounce_bot_lib/legacy.py
+++ b/scripts/bounce_bot_lib/legacy.py
@@ -3262,7 +3262,12 @@ class BounceBot(EWrapper, EClient):
             if self._technical_integrity_monitor is None:
                 from technical_integrity import TechnicalIntegrityMonitor
 
-                self._technical_integrity_monitor = TechnicalIntegrityMonitor()
+                # Tape light: SPY's own completed-M5 bars from the cache only, never IB.
+                self._technical_integrity_monitor = TechnicalIntegrityMonitor(
+                    spy_bars_provider=lambda: (
+                        (getattr(self, "latest_bars", None) or {}).get("SPY|5 D|5 mins") or []
+                    )
+                )
             return self._technical_integrity_monitor
 
     def _observe_technical_integrity(self, symbol, full_df):
diff --git a/scripts/technical_integrity.py b/scripts/technical_integrity.py
index c53c5ff..6f12c1c 100644
--- a/scripts/technical_integrity.py
+++ b/scripts/technical_integrity.py
@@ -641,6 +641,25 @@ TICK_LIGHT_WINDOW_MINUTES = 30
 TICK_LIGHT_STALE_MINUTES = 15
 TICK_LIGHT_MIN_BARS = 3
 TICK_CONTRACT_SYMBOL = "TICK-NYSE"
+TAPE_LIGHT_SCHEMA = "technical_integrity_tape_light_v1"
+TAPE_LIGHT_WINDOW_MINUTES = 30
+TAPE_LIGHT_STALE_MINUTES = 15
+TAPE_LIGHT_MIN_BARS = 3
+TAPE_CALM_RATIO = 0.8
+TAPE_FAST_RATIO = 1.25
+#: SPY M5 (high-low)/close*100 by session hour, the usual tape speed for that hour.
+#: Derived from the 4 local sessions ending 2026-10-05 (2026-09-30, 10-01, 10-02,
+#: 10-05; 78 completed bars each, .qo/recon.md sec 7) - a stub of the 30-session
+#: target, to be re-derived when that history is available.
+SESSION_HOUR_SPY_RANGE_NORMS = {
+    0: 0.1278,
+    1: 0.1058,
+    2: 0.0813,
+    3: 0.0754,
+    4: 0.0694,
+    5: 0.0566,
+    6: 0.0866,
+}
 
 
 def _as_market_local(value: Any) -> datetime | None:
@@ -786,27 +805,62 @@ def tick_range_light(
     as_of: datetime | str | None,
     window_minutes: int = TICK_LIGHT_WINDOW_MINUTES,
 ) -> dict[str, Any]:
-    """NYSE TICK M5 range over the last ``window_minutes`` versus the usual for those hours."""
+    """NYSE TICK M5 range over the last ``window_minutes`` versus the usual for those hours.
+
+    Thin wrapper over :func:`tape_speed_light`: keeps the historical schema, the "wide"
+    label and the 1-decimal range rounding so published snapshots stay comparable.
+    """
+    light = tape_speed_light(
+        map(_tick_bar, tick_rows or ()),
+        as_of=as_of,
+        hour_norms=SESSION_HOUR_TICK_RANGE_NORMS,
+        label="TICK",
+        window_minutes=window_minutes,
+    )
+    light["schema"] = TICK_LIGHT_SCHEMA
+    if light.get("range_mean") is not None:
+        light["range_mean"] = round(light["range_mean"], 1)
+        light["expected_range"] = round(light["expected_range"], 1)
+    if light["light"] == "fast":
+        light["light"] = "wide"
+    return light
+
+
+def tape_speed_light(
+    bars: Iterable[tuple[datetime, datetime, float, datetime] | None],
+    *,
+    as_of: datetime | str | None,
+    hour_norms: Mapping[int, float] = SESSION_HOUR_SPY_RANGE_NORMS,
+    label: str = "SPY",
+    window_minutes: int = TAPE_LIGHT_WINDOW_MINUTES,
+) -> dict[str, Any]:
+    """Completed-M5 range over the last ``window_minutes`` versus the usual for those hours.
+
+    Unit-agnostic: ``bars`` are pre-parsed ``(start, end, range, end-as-stamped)`` tuples
+    (``None`` items are skipped) and ``hour_norms`` maps session hour -> the usual range
+    for that hour, in the same units as the bar ranges (TICK points, SPY percent of
+    close). Light: "calm" below :data:`TAPE_CALM_RATIO` of the norm, "fast" above
+    :data:`TAPE_FAST_RATIO`, "unknown" without at least 3 fresh bars.
+    """
     moment = _as_market_local(as_of) if as_of is not None else normalize_market_local_datetime()
     if moment is None:
         moment = normalize_market_local_datetime()
     start = moment - timedelta(minutes=int(window_minutes))
-    bars: dict[datetime, tuple[datetime, float, float, datetime]] = {}
-    for row in tick_rows or ():
-        parsed = _tick_bar(row)
+    kept: dict[datetime, tuple[datetime, float, float, datetime]] = {}
+    for parsed in bars or ():
         if parsed is None:
             continue
         bar_start, bar_end, bar_range, stamped_end = parsed
         if not start < bar_end <= moment:
             continue
         hour = _session_hour_index(bar_start)
-        norm = SESSION_HOUR_TICK_RANGE_NORMS.get(hour) if hour is not None else None
+        norm = hour_norms.get(hour) if hour is not None else None
         if norm is None:
             continue
-        bars[bar_start] = (bar_end, bar_range, float(norm), stamped_end)
-    ordered = [bars[key] for key in sorted(bars)]
+        kept[bar_start] = (bar_end, bar_range, float(norm), stamped_end)
+    ordered = [kept[key] for key in sorted(kept)]
     result: dict[str, Any] = {
-        "schema": TICK_LIGHT_SCHEMA,
+        "schema": TAPE_LIGHT_SCHEMA,
         "as_of": moment.isoformat(timespec="seconds"),
         "bar_count": len(ordered),
         "range_mean": None,
@@ -818,18 +872,93 @@ def tick_range_light(
     if ordered:
         range_mean = sum(item[1] for item in ordered) / len(ordered)
         expected = sum(item[2] for item in ordered) / len(ordered)
-        result["range_mean"] = round(range_mean, 1)
-        result["expected_range"] = round(expected, 1)
+        result["range_mean"] = round(range_mean, 4)
+        result["expected_range"] = round(expected, 4)
         result["ratio"] = round(range_mean / expected, 4) if expected > 0 else None
     if not ordered:
-        result["reason"] = "no TICK bars in the window"
-    elif ordered[-1][0] < moment - timedelta(minutes=TICK_LIGHT_STALE_MINUTES):
-        result["reason"] = f"newest TICK bar is older than {TICK_LIGHT_STALE_MINUTES} minutes"
-    elif len(ordered) < TICK_LIGHT_MIN_BARS:
-        result["reason"] = f"fewer than {TICK_LIGHT_MIN_BARS} TICK bars in the window"
+        result["reason"] = f"no {label} bars in the window"
+    elif ordered[-1][0] < moment - timedelta(minutes=TAPE_LIGHT_STALE_MINUTES):
+        result["reason"] = f"newest {label} bar is older than {TAPE_LIGHT_STALE_MINUTES} minutes"
+    elif len(ordered) < TAPE_LIGHT_MIN_BARS:
+        result["reason"] = f"fewer than {TAPE_LIGHT_MIN_BARS} {label} bars in the window"
     elif result["ratio"] is not None:
         ratio = range_mean / expected
-        result["light"] = "calm" if ratio < 0.8 else "wide" if ratio > 1.25 else "normal"
+        result["light"] = (
+            "calm" if ratio < TAPE_CALM_RATIO else "fast" if ratio > TAPE_FAST_RATIO else "normal"
+        )
+    return result
+
+
+def _spy_range_bar(row: Any) -> tuple[datetime, datetime, float, datetime] | None:
+    """(start, end, (high-low)/close*100, end as stamped) for one SPY M5 bar, else None.
+
+    Accepts the bot's cached ``IbBar`` objects (attribute shape, naive market-local
+    stamps) and Mapping rows (dicts/JSONL) with start/dt/datetime plus high/low/close.
+    Anything unreadable or inconsistent is "unknown", never a guess.
+    """
+    try:
+        if isinstance(row, Mapping):
+            stamp = row.get("start") or row.get("dt") or row.get("datetime")
+            high, low, close = row["high"], row["low"], row["close"]
+        else:
+            stamp, high, low, close = row.dt, row.high, row.low, row.close
+    except (AttributeError, KeyError, TypeError):
+        return None
+    start = _parse_datetime(stamp)
+    if start is None:
+        return None
+    try:
+        high, low, close = float(high), float(low), float(close)
+    except (TypeError, ValueError):
+        return None
+    if not all(math.isfinite(value) for value in (high, low, close)) or close <= 0.0 or low > high:
+        return None
+    raw_end = start + timedelta(minutes=5)
+    return (
+        normalize_market_local_datetime(start),
+        normalize_market_local_datetime(raw_end),
+        (high - low) / close * 100.0,
+        raw_end if start.tzinfo is not None else normalize_market_local_datetime(raw_end),
+    )
+
+
+def tape_light(
+    spy_light: Mapping[str, Any] | None,
+    tick_light: Mapping[str, Any] | None,
+) -> dict[str, Any]:
+    """The tape reading: SPY when known, else the TICK light (wide = fast), else "none"."""
+    spy = spy_light if isinstance(spy_light, Mapping) else {}
+    tick = tick_light if isinstance(tick_light, Mapping) else {}
+    result: dict[str, Any] = {
+        "schema": TAPE_LIGHT_SCHEMA,
+        "source": "none",
+        "as_of": str(spy.get("as_of") or tick.get("as_of") or ""),
+        "bar_count": 0,
+        "range_mean": None,
+        "expected_range": None,
+        "ratio": None,
+        "light": "unknown",
+        "last_bar_end": "",
+    }
+    base: Mapping[str, Any] | None = None
+    source = "none"
+    if str(spy.get("light") or "unknown") != "unknown":
+        base, source = spy, "SPY"
+    elif str(tick.get("light") or "unknown") != "unknown":
+        base = dict(tick)
+        if base.get("light") == "wide":
+            base["light"] = "fast"
+        source = "TICK"
+    if base is not None:
+        result["source"] = source
+        result["light"] = str(base.get("light") or "unknown")
+        result["bar_count"] = int(base.get("bar_count") or 0)
+        result["range_mean"] = base.get("range_mean")
+        result["expected_range"] = base.get("expected_range")
+        result["ratio"] = base.get("ratio")
+        result["last_bar_end"] = str(base.get("last_bar_end") or "")
+    else:
+        result["reason"] = str(spy.get("reason") or "no tape reading")
     return result
 
 
@@ -1409,8 +1538,10 @@ class TechnicalIntegrityMonitor:
         config: TechnicalIntegrityConfig | None = None,
         collector_started_at: datetime | None = None,
         tick_rows_provider: Callable[[], Iterable[Mapping[str, Any]]] | None = None,
+        spy_bars_provider: Callable[[], Any] | None = None,
     ) -> None:
         self.tick_rows_provider = tick_rows_provider or _default_tick_rows
+        self.spy_bars_provider = spy_bars_provider
         self.events_path = Path(events_path or technical_integrity_events_path())
         self.state_path = Path(state_path or technical_integrity_state_path())
         self.snapshot_path = Path(snapshot_path or technical_integrity_snapshot_path())
@@ -1674,8 +1805,9 @@ class TechnicalIntegrityMonitor:
         )
         if market_environment and not snapshot["market"].get("market_environment"):
             snapshot["market"]["market_environment"] = market_environment
-        # The "now" reading and the TICK light ride on the published snapshot only, so the
-        # pure aggregator stays replayable. Both fail open: a bad read never costs the snapshot.
+        # The "now" reading, the TICK light and the tape light ride on the published
+        # snapshot only, so the pure aggregator stays replayable. Each fails open:
+        # a bad read never costs the snapshot.
         try:
             snapshot["market"]["rolling"] = rolling_technical_integrity(
                 self.resolved_events, as_of=as_of, config=self.config
@@ -1693,6 +1825,34 @@ class TechnicalIntegrityMonitor:
                 "light": "unknown",
                 "reason": f"TICK read failed: {exc}",
             }
+        try:
+            spy_bars = self.spy_bars_provider() if self.spy_bars_provider is not None else []
+            spy_light = tape_speed_light(
+                map(_spy_range_bar, spy_bars or ()),
+                as_of=as_of,
+                hour_norms=SESSION_HOUR_SPY_RANGE_NORMS,
+            )
+        except Exception as exc:  # noqa: BLE001 - advisory extra, never blocks the publish
+            note_swallowed("technical integrity SPY tape light failed", exc, quiet=True)
+            spy_light = {
+                "schema": TAPE_LIGHT_SCHEMA,
+                "as_of": str(as_of),
+                "bar_count": 0,
+                "light": "unknown",
+                "reason": f"SPY read failed: {exc}",
+            }
+        try:
+            snapshot["market"]["tape"] = tape_light(spy_light, snapshot["market"]["tick"])
+        except Exception as exc:  # noqa: BLE001 - advisory extra, never blocks the publish
+            note_swallowed("technical integrity tape light failed", exc, quiet=True)
+            snapshot["market"]["tape"] = {
+                "schema": TAPE_LIGHT_SCHEMA,
+                "source": "none",
+                "as_of": str(as_of),
+                "bar_count": 0,
+                "light": "unknown",
+                "reason": f"tape read failed: {exc}",
+            }
         _atomic_write_json(self.snapshot_path, snapshot)
         return snapshot
 
@@ -2886,20 +3046,23 @@ def _rolling_now_view(
         line("D1", d1),
         line("M5", m5),
     ]
-    tick = market.get("tick") if isinstance(market.get("tick"), Mapping) else {}
-    light = str(tick.get("light") or "unknown")
-    if light != "unknown":
-        chip += f" · TICK {light}"
+    tape = market.get("tape") if isinstance(market.get("tape"), Mapping) else {}
+    light = str(tape.get("light") or "unknown")
+    if light in {"calm", "normal", "fast"}:
+        # SPY ranges are percent of close; the TICK fallback is points.
+        decimals = "0" if tape.get("source") == "TICK" else "3"
+        source_name = "TICK fallback" if tape.get("source") == "TICK" else "SPY"
+        chip += f" · tape {light}"
         lines.append(
-            f"TICK (last {TICK_LIGHT_WINDOW_MINUTES} min): range "
-            f"{float(tick.get('range_mean') or 0.0):.0f} vs "
-            f"{float(tick.get('expected_range') or 0.0):.0f} usual = {light} "
-            "(levels fail more when TICK is wide)."
+            f"Tape (last {TAPE_LIGHT_WINDOW_MINUTES} min, {source_name}): M5 range "
+            f"{float(tape.get('range_mean') or 0.0):.{decimals}f} vs "
+            f"{float(tape.get('expected_range') or 0.0):.{decimals}f} usual = {light} "
+            "(fast tape = levels fail more)."
         )
-    elif tick:
+    elif tape:
         lines.append(
-            f"TICK (last {TICK_LIGHT_WINDOW_MINUTES} min): unknown"
-            + (f" ({tick.get('reason')})." if tick.get("reason") else ".")
+            f"Tape (last {TAPE_LIGHT_WINDOW_MINUTES} min): unknown"
+            + (f" ({tape.get('reason')})." if tape.get("reason") else ".")
         )
     headline = d1 if d1.get("score") is not None else m5
     return (
diff --git a/tests/fixtures/technical_integrity_rolling_v1.json b/tests/fixtures/technical_integrity_rolling_v1.json
index eb8c632..f831477 100644
--- a/tests/fixtures/technical_integrity_rolling_v1.json
+++ b/tests/fixtures/technical_integrity_rolling_v1.json
@@ -9,7 +9,7 @@
  "acquired_at": "2026-10-05T12:00:00-04:00",
  "universe_version": "synthetic_technical_integrity_rolling_v1",
  "provider_assumptions": "Synthetic regular-session level resolutions (D1 and M5 families, chop, rows outside the 60-minute window) and NYSE TICK M5 breadth_bar rows shaped like vold_m5.jsonl.",
- "intentional_difference": "New 2026-10-05: the rolling 'now' reading (last 60 min of tests vs the measured norm for the session hour) and the TICK range light. Expected values were computed by hand from SESSION_HOUR_RESPECT_NORMS and SESSION_HOUR_TICK_RANGE_NORMS.",
+ "intentional_difference": "New 2026-10-05: the rolling 'now' reading (last 60 min of tests vs the measured norm for the session hour) and the tape speed light (chip 'tape fast/normal/calm': SPY M5 range vs the session-hour norm, TICK range light as the fallback, wide = fast). Expected values were computed by hand from SESSION_HOUR_RESPECT_NORMS and SESSION_HOUR_TICK_RANGE_NORMS.",
  "expected_keys": [
   "expected"
  ],
@@ -594,12 +594,12 @@
      "light": "wide",
      "last_bar_end": "2026-10-05T11:00:00-04:00"
     },
-    "chip": "Technicals now: D1 VERY WEAK 2.2/10 · M5 STRONG 9.1/10 · TICK wide",
+    "chip": "Technicals now: D1 VERY WEAK 2.2/10 · M5 STRONG 9.1/10 · tape fast",
     "tooltip_head": [
      "Now = last 60 min of level tests vs the usual for this time of day. 5.5 = normal for this hour.",
      "D1 now 2.2/10 (VERY WEAK): levels held 0.53 of tests vs 0.64 usual at this hour; break pressure BEARISH; 5 decisive tests / 1 chop / 4 symbols.",
      "M5 now 9.1/10 (STRONG): levels held 0.80 of tests vs 0.68 usual at this hour; break pressure BULLISH; 5 decisive tests / 2 chop / 4 symbols.",
-     "TICK (last 30 min): range 567 vs 415 usual = wide (levels fail more when TICK is wide).",
+     "Tape (last 30 min, TICK fallback): M5 range 567 vs 415 usual = fast (fast tape = levels fail more).",
      "Today so far:"
     ],
     "color": "#f85149"
diff --git a/tests/test_technical_integrity_rolling.py b/tests/test_technical_integrity_rolling.py
index 4bf6c44..5a71b9b 100644
--- a/tests/test_technical_integrity_rolling.py
+++ b/tests/test_technical_integrity_rolling.py
@@ -44,6 +44,8 @@ def _snapshot_at(fixture, case):
     from technical_integrity import (
         aggregate_technical_integrity,
         rolling_technical_integrity,
+        tape_light,
+        tape_speed_light,
         tick_range_light,
     )
 
@@ -52,6 +54,10 @@ def _snapshot_at(fixture, case):
     snapshot = aggregate_technical_integrity(known, as_of=as_of, session_date=fixture["session_date"])
     snapshot["market"]["rolling"] = rolling_technical_integrity(fixture["events"], as_of=as_of)
     snapshot["market"]["tick"] = tick_range_light(fixture["tick_rows"], as_of=as_of)
+    # No SPY bars in the fixture: the tape light carries the TICK reading (or "none").
+    snapshot["market"]["tape"] = tape_light(
+        tape_speed_light((), as_of=as_of), snapshot["market"]["tick"]
+    )
     return snapshot
 
 
diff --git a/tests/test_technical_integrity_tape.py b/tests/test_technical_integrity_tape.py
new file mode 100644
index 0000000..5a5d3c9
--- /dev/null
+++ b/tests/test_technical_integrity_tape.py
@@ -0,0 +1,438 @@
+"""The tape speed light: SPY's completed-M5 range vs the session-hour norm, TICK fallback."""
+
+import json
+import sys
+from datetime import datetime, timedelta
+from pathlib import Path
+from types import SimpleNamespace
+
+import pytest
+from conftest import load_fixture_contract
+
+ROOT_DIR = Path(__file__).resolve().parents[1]
+SCRIPTS_DIR = ROOT_DIR / "scripts"
+if str(SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(SCRIPTS_DIR))
+
+AS_OF = "2026-10-05T10:55:00-04:00"  # hour 1 (10:30-11:00 ET bars, norm 0.1058)
+
+
+def _spy_row(start, range_pct):
+    """A SPY M5 bar as a Mapping row: close 100, (high-low)/close*100 == range_pct."""
+    return {
+        "start": start,
+        "high": 100.0 + range_pct / 2,
+        "low": 100.0 - range_pct / 2,
+        "close": 100.0,
+    }
+
+
+def _spy_bars(range_pct, starts=("10:30", "10:35", "10:40")):
+    return [_spy_row(f"2026-10-05T{s}:00-04:00", range_pct) for s in starts]
+
+
+def _event(event_id, touch, resolved, outcome, weight=2.0):
+    return {
+        "event_type": "level_resolved",
+        "event_id": event_id,
+        "session_date": "2026-10-05",
+        "touch_bar_start_local": f"2026-10-05T{touch}:00-04:00",
+        "resolved_at": f"2026-10-05T{resolved}:00-04:00",
+        "symbol": "MU",
+        "sector_key": "technology",
+        "industry_key": "semiconductors",
+        "level_family": "vwap",
+        "level_timeframe": "intraday",
+        "approach_side": "above",
+        "outcome": outcome,
+        "break_direction": "",
+        "event_weight": weight,
+    }
+
+
+def _monitor(tmp_path, **kwargs):
+    from technical_integrity import TechnicalIntegrityMonitor
+
+    return TechnicalIntegrityMonitor(
+        events_path=tmp_path / "events.jsonl",
+        state_path=tmp_path / "state.json",
+        snapshot_path=tmp_path / "snapshot.json",
+        **kwargs,
+    )
+
+
+# ------------------------------------------------------------------ the generic light
+@pytest.mark.parametrize(
+    "range_pct, light",
+    [(0.05, "calm"), (0.1058, "normal"), (0.15, "fast")],
+)
+def test_tape_speed_light_thresholds_vs_spy_hour_norm(range_pct, light):
+    from technical_integrity import SESSION_HOUR_SPY_RANGE_NORMS, TAPE_LIGHT_SCHEMA, _spy_range_bar, tape_speed_light
+
+    result = tape_speed_light(map(_spy_range_bar, _spy_bars(range_pct)), as_of=AS_OF)
+    assert result["schema"] == TAPE_LIGHT_SCHEMA
+    assert result["light"] == light
+    assert result["bar_count"] == 3
+    assert datetime.fromisoformat(result["as_of"]) == datetime.fromisoformat(AS_OF)
+    assert datetime.fromisoformat(result["last_bar_end"]) == datetime.fromisoformat(
+        "2026-10-05T10:45:00-04:00"
+    )
+    # 3 bars in session hour 1: the norm is the hour-1 value, and the ratio lands
+    # exactly where the task's thresholds say it should.
+    assert result["expected_range"] == pytest.approx(SESSION_HOUR_SPY_RANGE_NORMS[1], rel=1e-9)
+    assert result["range_mean"] == pytest.approx(range_pct, rel=1e-9)
+    ratio = result["ratio"]
+    if light == "calm":
+        assert ratio < 0.8
+    elif light == "fast":
+        assert ratio > 1.25
+    else:
+        assert 0.8 <= ratio <= 1.25
+
+
+def test_tape_speed_light_accepts_attribute_bars_like_the_bot_cache():
+    from technical_integrity import _spy_range_bar, tape_speed_light
+
+    bars = [
+        SimpleNamespace(
+            dt=datetime.fromisoformat(start),
+            high=100.0 + 0.15 / 2,
+            low=100.0 - 0.15 / 2,
+            close=100.0,
+        )
+        for start in ("2026-10-05T10:30:00-04:00", "2026-10-05T10:35:00-04:00", "2026-10-05T10:40:00-04:00")
+    ]
+    result = tape_speed_light(map(_spy_range_bar, bars), as_of=AS_OF)
+    assert result["light"] == "fast"
+    assert result["bar_count"] == 3
+
+
+def test_tape_speed_light_unknown_without_enough_bars():
+    from technical_integrity import _spy_range_bar, tape_speed_light
+
+    result = tape_speed_light(map(_spy_range_bar, []), as_of=AS_OF)
+    assert result["light"] == "unknown"
+    assert result["bar_count"] == 0
+    assert result["reason"] == "no SPY bars in the window"
+
+    two = tape_speed_light(map(_spy_range_bar, _spy_bars(0.1, ("10:45", "10:50"))), as_of=AS_OF)
+    assert two["light"] == "unknown"
+    assert two["bar_count"] == 2
+    assert two["reason"] == "fewer than 3 SPY bars in the window"
+
+
+def test_tape_speed_light_unknown_when_the_newest_bar_is_stale():
+    from technical_integrity import _spy_range_bar, tape_speed_light
+
+    # One in-window bar, ended 10:35 - more than 15 min before 10:55.
+    result = tape_speed_light(
+        map(_spy_range_bar, _spy_bars(0.1, ("10:30",))), as_of="2026-10-05T10:55:00-04:00"
+    )
+    assert result["bar_count"] == 1
+    assert result["light"] == "unknown"
+    assert result["reason"] == "newest SPY bar is older than 15 minutes"
+
+
+def test_tape_speed_light_counts_completed_bars_only():
+    from technical_integrity import _spy_range_bar, tape_speed_light
+
+    rows = _spy_bars(0.1, ("10:30", "10:35", "10:40", "10:50"))  # last ends exactly at as_of
+    rows.append(_spy_row("2026-10-05T10:55:00-04:00", 0.9))  # ends after as_of: not completed
+    result = tape_speed_light(map(_spy_range_bar, rows), as_of=AS_OF)
+    assert result["bar_count"] == 4
+    assert result["range_mean"] == pytest.approx(0.1, rel=1e-9)
+
+
+def test_tape_speed_light_skips_bars_without_a_session_hour():
+    from technical_integrity import SESSION_HOUR_SPY_RANGE_NORMS, _spy_range_bar, tape_speed_light
+
+    # 09:25-09:30 is inside the 30-min window of 09:50 but before the 09:30 open.
+    rows = _spy_bars(SESSION_HOUR_SPY_RANGE_NORMS[0], ("09:30", "09:35", "09:40"))
+    rows.append(_spy_row("2026-10-05T09:25:00-04:00", 9.9))
+    result = tape_speed_light(map(_spy_range_bar, rows), as_of="2026-10-05T09:50:00-04:00")
+    assert result["bar_count"] == 3
+    assert result["light"] == "normal"
+    assert result["expected_range"] == pytest.approx(SESSION_HOUR_SPY_RANGE_NORMS[0], rel=1e-9)
+
+
+@pytest.mark.parametrize(
+    "bad_row",
+    [
+        None,
+        "not a row",
+        {"start": "2026-10-05T10:30:00-04:00", "high": 101.0, "low": 99.0},  # no close
+        {"start": "2026-10-05T10:30:00-04:00", "high": 101.0, "low": 99.0, "close": "oops"},
+        {"start": "2026-10-05T10:30:00-04:00", "high": 99.0, "low": 101.0, "close": 100.0},  # low > high
+        {"start": "2026-10-05T10:30:00-04:00", "high": 101.0, "low": 99.0, "close": 0.0},  # close <= 0
+        {"start": "garbage", "high": 101.0, "low": 99.0, "close": 100.0},
+        SimpleNamespace(dt="garbage", high=101.0, low=99.0, close=100.0),
+    ],
+)
+def test_tape_speed_light_skips_unreadable_bars(bad_row):
+    from technical_integrity import _spy_range_bar, tape_speed_light
+
+    rows = list(_spy_bars(0.1)) + [bad_row]
+    result = tape_speed_light(map(_spy_range_bar, rows), as_of=AS_OF)
+    assert result["bar_count"] == 3
+    assert result["light"] == "normal"
+
+
+# ------------------------------------------------------------------ the combiner
+def _spy_light(light, reason=None, **overrides):
+    row = {
+        "schema": "technical_integrity_tape_light_v1",
+        "as_of": AS_OF,
+        "bar_count": 3,
+        "range_mean": 0.15,
+        "expected_range": 0.1058,
+        "ratio": 1.4178,
+        "light": light,
+        "last_bar_end": "2026-10-05T10:45:00-04:00",
+    }
+    if reason is not None:
+        row["reason"] = reason
+    row.update(overrides)
+    return row
+
+
+def _tick_light(light, **overrides):
+    row = {
+        "schema": "technical_integrity_tick_light_v1",
+        "as_of": AS_OF,
+        "bar_count": 6,
+        "range_mean": 566.7,
+        "expected_range": 415.0,
+        "ratio": 1.3655,
+        "light": light,
+        "last_bar_end": "2026-10-05T11:00:00-04:00",
+    }
+    row.update(overrides)
+    return row
+
+
+def test_tape_light_prefers_spy_when_it_is_known():
+    from technical_integrity import tape_light
+
+    result = tape_light(_spy_light("fast"), _tick_light("wide"))
+    assert result["source"] == "SPY"
+    assert result["light"] == "fast"
+    assert result["bar_count"] == 3
+    assert result["range_mean"] == 0.15
+    assert result["last_bar_end"] == "2026-10-05T10:45:00-04:00"
+
+
+def test_tape_light_falls_back_to_tick_with_wide_becoming_fast():
+    from technical_integrity import tape_light
+
+    result = tape_light(_spy_light("unknown", reason="no SPY bars in the window"), _tick_light("wide"))
+    assert result["source"] == "TICK"
+    assert result["light"] == "fast"
+    assert result["bar_count"] == 6
+    assert result["range_mean"] == 566.7
+    assert result["expected_range"] == 415.0
+    assert result["ratio"] == 1.3655
+
+
+def test_tape_light_falls_back_to_tick_calm_unchanged():
+    from technical_integrity import tape_light
+
+    result = tape_light(_spy_light("unknown", reason="no SPY bars in the window"), _tick_light("calm"))
+    assert result["source"] == "TICK"
+    assert result["light"] == "calm"
+
+
+def test_tape_light_none_when_both_are_unknown_keeps_the_spy_reason():
+    from technical_integrity import tape_light
+
+    result = tape_light(
+        _spy_light("unknown", reason="no SPY bars in the window"),
+        _tick_light("unknown", reason="no TICK bars in the window"),
+    )
+    assert result["source"] == "none"
+    assert result["light"] == "unknown"
+    assert result["reason"] == "no SPY bars in the window"
+
+    both_empty = tape_light(None, None)
+    assert both_empty["source"] == "none"
+    assert both_empty["light"] == "unknown"
+    assert both_empty["reason"] == "no tape reading"
+
+
+def test_tape_light_treats_a_failed_spy_read_like_an_unknown_spy():
+    from technical_integrity import tape_light
+
+    result = tape_light(_spy_light("unknown", reason="SPY read failed: boom"), _tick_light("wide"))
+    assert result["source"] == "TICK"
+    assert result["light"] == "fast"
+
+
+# ------------------------------------------------------------------ the thin wrapper
+def _tick_rows(ranges, starts=("10:30", "10:35", "10:40")):
+    def at(stamp):
+        return f"2026-10-05T{stamp}:00-04:00"
+
+    def end_of(stamp):
+        return (datetime.fromisoformat(at(stamp)) + timedelta(minutes=5)).isoformat()
+
+    return [
+        {
+            "event_type": "breadth_bar",
+            "contract": {"symbol": "TICK-NYSE"},
+            "bar_start": at(s),
+            "bar_end": end_of(s),
+            "open": 0.0,
+            "high": r / 2,
+            "low": -r / 2,
+            "close": 0.0,
+        }
+        for s, r in zip(starts, ranges, strict=True)
+    ]
+
+
+def test_tick_wrapper_keeps_its_schema_label_and_one_decimal_rounding():
+    from technical_integrity import tick_range_light
+
+    result = tick_range_light(_tick_rows([530.0, 530.0, 530.0]), as_of=AS_OF)
+    assert result["schema"] == "technical_integrity_tick_light_v1"
+    assert result["light"] == "wide"  # the historical TICK label, never "fast"
+    assert result["range_mean"] == 530.0
+    assert result["expected_range"] == 415.0
+    assert result["ratio"] == round(530.0 / 415.0, 4)
+
+    # 500, 500, 501.4 -> mean 500.4667 -> one decimal 500.5 (the generic rounds to 4).
+    re_rounded = tick_range_light(_tick_rows([500.0, 500.0, 501.4]), as_of=AS_OF)
+    assert re_rounded["range_mean"] == 500.5
+    assert re_rounded["light"] == "normal"
+
+
+def test_tick_wrapper_is_the_generic_light_with_tick_norms_and_label():
+    from technical_integrity import SESSION_HOUR_TICK_RANGE_NORMS, _tick_bar, tape_speed_light, tick_range_light
+
+    rows = _tick_rows([530.0, 530.0, 530.0])
+    generic = tape_speed_light(
+        map(_tick_bar, rows), as_of=AS_OF, hour_norms=SESSION_HOUR_TICK_RANGE_NORMS, label="TICK"
+    )
+    wrapper = tick_range_light(rows, as_of=AS_OF)
+    assert generic["light"] == "fast" and wrapper["light"] == "wide"
+    for key in ("bar_count", "ratio", "last_bar_end"):
+        assert generic[key] == wrapper[key]
+
+
+# ------------------------------------------------------------------ monitor wiring
+@pytest.fixture()
+def rolling_fixture():
+    return load_fixture_contract("technical_integrity_rolling_v1")
+
+
+def test_publish_snapshot_tape_falls_back_to_tick_when_spy_provider_raises(tmp_path, rolling_fixture):
+    def boom():
+        raise RuntimeError("spy cache gone")
+
+    monitor = _monitor(
+        tmp_path,
+        tick_rows_provider=lambda: rolling_fixture["tick_rows"],
+        spy_bars_provider=boom,
+    )
+    monitor.session_date = "2026-10-05"
+    monitor.resolved_events = [_event(f"m{i}", "10:30", "10:45", "held") for i in range(5)]
+    monitor._publish_snapshot("2026-10-05T11:00:00-04:00", "")
+    written = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
+    market = written["market"]
+    assert market["tape"]["source"] == "TICK"
+    assert market["tape"]["light"] == "fast"
+    assert market["tape"]["bar_count"] == 6
+    assert market["tick"]["light"] == "wide"  # market.tick is written exactly as before
+    assert market["rolling"]["schema"] == "technical_integrity_rolling_v1"
+
+
+def test_publish_snapshot_tape_uses_spy_bars_when_present(tmp_path, rolling_fixture):
+    spy_bars = _spy_bars(0.05, ("10:45", "10:50", "10:55"))  # calm vs the hour-1 norm
+    monitor = _monitor(
+        tmp_path,
+        tick_rows_provider=lambda: rolling_fixture["tick_rows"],
+        spy_bars_provider=lambda: spy_bars,
+    )
+    monitor.session_date = "2026-10-05"
+    monitor.resolved_events = [_event(f"m{i}", "10:30", "10:45", "held") for i in range(5)]
+    snapshot = monitor._publish_snapshot("2026-10-05T11:00:00-04:00", "")
+    market = snapshot["market"]
+    assert market["tape"]["source"] == "SPY"
+    assert market["tape"]["light"] == "calm"
+    assert market["tape"]["range_mean"] == pytest.approx(0.05, rel=1e-9)
+    assert market["tick"]["light"] == "wide"
+
+
+def test_publish_snapshot_tape_is_none_sourced_when_everything_is_unknown(tmp_path):
+    def boom():
+        raise RuntimeError("ledger gone")
+
+    monitor = _monitor(tmp_path, tick_rows_provider=boom, spy_bars_provider=lambda: [])
+    monitor.session_date = "2026-10-05"
+    monitor._publish_snapshot("2026-10-05T11:00:00-04:00", "")
+    written = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
+    market = written["market"]
+    assert market["tape"]["source"] == "none"
+    assert market["tape"]["light"] == "unknown"
+    assert market["tape"]["reason"] == "no SPY bars in the window"
+    assert "ledger gone" in market["tick"]["reason"]
+
+
+# ------------------------------------------------------------------ chip and tooltip
+def _snapshot_at(fixture, as_of, spy_bars=(), tick_rows=None):
+    from technical_integrity import (
+        aggregate_technical_integrity,
+        rolling_technical_integrity,
+        tape_light,
+        tape_speed_light,
+        tick_range_light,
+        _spy_range_bar,
+    )
+
+    known = [row for row in fixture["events"] if row["resolved_at"] <= as_of]
+    snapshot = aggregate_technical_integrity(known, as_of=as_of, session_date=fixture["session_date"])
+    snapshot["market"]["rolling"] = rolling_technical_integrity(fixture["events"], as_of=as_of)
+    snapshot["market"]["tick"] = tick_range_light(
+        fixture["tick_rows"] if tick_rows is None else tick_rows, as_of=as_of
+    )
+    snapshot["market"]["tape"] = tape_light(
+        tape_speed_light(map(_spy_range_bar, spy_bars), as_of=as_of), snapshot["market"]["tick"]
+    )
+    return snapshot
+
+
+def test_chip_and_tooltip_name_spy_or_tick_fallback():
+    from technical_integrity import format_technical_integrity_snapshot
+
+    fixture = load_fixture_contract("technical_integrity_rolling_v1")
+    as_of = "2026-10-05T11:00:00-04:00"
+    now = datetime.fromisoformat(as_of)
+
+    # No SPY bars: the TICK light carries the reading (wide -> fast).
+    fallback = _snapshot_at(fixture, as_of)
+    chip, tooltip, _ = format_technical_integrity_snapshot(fallback, now=now)
+    assert chip == "Technicals now: D1 VERY WEAK 2.2/10 · M5 STRONG 9.1/10 · tape fast"
+    lines = tooltip.splitlines()
+    assert lines[3] == (
+        "Tape (last 30 min, TICK fallback): M5 range 567 vs 415 usual = fast "
+        "(fast tape = levels fail more)."
+    )
+
+    # SPY known: fast, 3-decimal SPY ranges.
+    fast = _snapshot_at(fixture, as_of, spy_bars=_spy_bars(0.15, ("10:45", "10:50", "10:55")))
+    chip, tooltip, _ = format_technical_integrity_snapshot(fast, now=now)
+    assert chip == "Technicals now: D1 VERY WEAK 2.2/10 · M5 STRONG 9.1/10 · tape fast"
+    assert tooltip.splitlines()[3] == (
+        "Tape (last 30 min, SPY): M5 range 0.150 vs 0.106 usual = fast "
+        "(fast tape = levels fail more)."
+    )
+
+    # SPY known: calm.
+    calm = _snapshot_at(fixture, as_of, spy_bars=_spy_bars(0.05, ("10:45", "10:50", "10:55")))
+    chip, _, _ = format_technical_integrity_snapshot(calm, now=now)
+    assert chip == "Technicals now: D1 VERY WEAK 2.2/10 · M5 STRONG 9.1/10 · tape calm"
+
+    # Both unknown: the chip omits the light, the tooltip says why.
+    none = _snapshot_at(fixture, as_of, tick_rows=[])
+    chip, tooltip, _ = format_technical_integrity_snapshot(none, now=now)
+    assert "tape" not in chip
+    assert tooltip.splitlines()[3] == "Tape (last 30 min): unknown (no SPY bars in the window)."
```

# LEAD TEST RESULTS
## builder's own test command (exit 1)
```
            annotations_path=annotations,
            picks_path=kwargs.get("picks_path"),
            now=kwargs.get("now"),
        )
        try:
            cohorts.run_like_cohort_grading(
                session_date="2026-08-24",
                picks_path=tmp_path / "picks.csv",
                outcomes_path=tmp_path / "out.csv",
                performance_path=tmp_path / "perf.csv",
                daily_bars_dir=bars,
            )
        finally:
            module.merge_like_cohort_picks = original
    
        rows = _read(tmp_path / "perf.csv")
>       assert rows
E       assert []

tests\test_like_cohort_grading.py:285: AssertionError
============================== warnings summary ===============================
tests/test_earnings_anchor_bridge.py::BridgeToCsvTests::test_rerun_appends_nothing_and_a_new_anchor_appends_at_the_end
tests/test_earnings_anchor_bridge.py::BridgeToCsvTests::test_rows_land_in_the_csv_with_the_anchor_columns
  C:\Users\Aaron\llm-harness\wt\qtm-243279e\scripts\master_avwap_lib\legacy.py:17793: FutureWarning: The behavior of DataFrame concatenation with empty or all-NA entries is deprecated. In a future version, this will no longer exclude empty or all-NA columns when determining the result dtypes. To retain the old behavior, exclude the relevant entries before the concat operation.
    combined = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_evidence_snapshot.py::test_the_ops_scripts_are_versioned_here_and_installed_there
FAILED tests/test_m5_strength_characterization.py::test_the_m5_formula_itself_has_not_been_edited
FAILED tests/test_b3_sunday_ritual_card.py::test_the_card_only_formats_and_reads_on_a_worker
FAILED tests/test_table_width_rule.py::test_the_elision_keeps_the_tail - Asse...
FAILED tests/test_tj1l_day_review_layout.py::test_the_name_chart_sits_beside_the_table_and_takes_the_rest
FAILED tests/test_qt_desk_layout.py::test_chart_pane_outgrows_the_alert_feed_in_its_column
FAILED tests/test_ws_rp_shared_report.py::test_n3s_narration_tests_are_byte_identical_to_the_branch_point
FAILED tests/test_ws_rp_shared_report.py::test_the_bounded_narration_view_itself_is_unchanged
FAILED tests/test_ws_wl_watchlist_tab.py::test_the_watchlist_tab_fits_without_a_horizontal_scrollbar[3456x2160]
FAILED tests/test_like_cohort_grading.py::test_the_slot_grades_the_history_retroactively
FAILED tests/test_like_cohort_grading.py::test_the_performance_rollup_carries_the_robust_half
11 failed, 16049 passed, 15 skipped, 2 warnings, 72 subtests passed in 1130.98s (0:18:50)
```
## lint (exit 0)
```
All checks passed!
```
## hidden reference tests (exit 1)
```

    def test_tape_fallback_order_spy_then_tick_then_none():
        from technical_integrity import tape_light
    
        as_of = "2026-10-05T11:00:00-04:00"
        fixture = _fixture()
        spy = _spy_bars(fixture, as_of)
        wide_tick = {"light": "wide", "range_mean": 600.0, "expected_range": 400.0, "bar_count": 6}
        calm_tick = {"light": "calm", "range_mean": 200.0, "expected_range": 400.0, "bar_count": 6}
        unknown_tick = {"light": "unknown", "reason": "no TICK bars in the window"}
    
        # SPY known: SPY wins even when TICK disagrees.
>       assert tape_light(spy, calm_tick, as_of=as_of)["source"] == "SPY"
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: tape_light() got an unexpected keyword argument 'as_of'

tests\ref_test_technical_integrity_rolling.py:155: TypeError
______________ test_chip_omits_the_tape_when_the_source_is_none _______________

    def test_chip_omits_the_tape_when_the_source_is_none():
        from technical_integrity import format_technical_integrity_snapshot
    
        fixture = _fixture()
        case = next(c for c in fixture["expected"]["cases"] if c.get("chip_without_spy"))
>       snapshot = _snapshot_at(fixture, case)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^

tests\ref_test_technical_integrity_rolling.py:174: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

fixture = FixtureContract(name='technical_integrity_rolling_v1', path=WindowsPath('C:/Users/Aaron/llm-harness/wt/qtm-243279e/tes... {'dt': '2026-10-05T11:00:00-04:00', 'open': 600.0, 'high': 600.05, 'low': 599.95, 'close': 600.0, 'volume': 1000.0}]})
case = {'as_of': '2026-10-05T11:00:00-04:00', 'rolling': {'all': {'score': 5.3, 'state': 'MIXED', 'pressure': 'BEARISH', 'tes...io': 1.3655, ...}, 'tape': {'source': 'SPY', 'bar_count': 6, 'range_mean': 0.1417, 'expected_range': 0.0834, ...}, ...}
with_spy = True

    def _snapshot_at(fixture, case, *, with_spy=True):
        from technical_integrity import (
            aggregate_technical_integrity,
            rolling_technical_integrity,
            tape_light,
            tick_range_light,
        )
    
        as_of = case["as_of"]
        known = [row for row in fixture["events"] if row["resolved_at"] <= as_of]
        snapshot = aggregate_technical_integrity(known, as_of=as_of, session_date=fixture["session_date"])
        market = snapshot["market"]
        market["rolling"] = rolling_technical_integrity(fixture["events"], as_of=as_of)
        market["tick"] = tick_range_light(fixture["tick_rows"], as_of=as_of)
        spy = _spy_bars(fixture, as_of) if with_spy else None
>       market["tape"] = tape_light(spy, market["tick"], as_of=as_of)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: tape_light() got an unexpected keyword argument 'as_of'

tests\ref_test_technical_integrity_rolling.py:64: TypeError
=========================== short test summary info ===========================
FAILED tests/ref_test_technical_integrity_rolling.py::test_chip_and_tooltip_lead_with_the_now_reading_golden
FAILED tests/ref_test_technical_integrity_rolling.py::test_tape_light_golden_spy_first_then_tick
FAILED tests/ref_test_technical_integrity_rolling.py::test_tape_fallback_order_spy_then_tick_then_none
FAILED tests/ref_test_technical_integrity_rolling.py::test_chip_omits_the_tape_when_the_source_is_none
4 failed, 14 passed in 14.85s
```

# BUILDER SELF-REVIEW
```json
{
  "verdict": "GO",
  "blockers": [],
  "advisories": [
    "SESSION_HOUR_SPY_RANGE_NORMS is derived from 4 local sessions (2026-09-30/10-01/10-02/10-05), not the task's 30-session target: the 30-session window does not exist locally. The constant's comment and the recon label it a short-window stub to be re-derived; the task explicitly allowed 'derive or stub them clearly'.",
    "Snapshots published before this change (on disk overnight, e.g. read by the night AI) have market.tick but no market.tape: they now render without a light in the chip instead of the old 'TICK wide' part. Transient - the next _publish_snapshot writes market.tape; no persisted chip strings exist.",
    "The stale check uses the newest bar's END (ordered[-1][0] in the kept tuple), exactly matching the pre-change TICK light; the first draft of the new stale test assumed the start and was corrected to the real semantics before going green.",
    "hour_norms defaults to the module-level SESSION_HOUR_SPY_RANGE_NORMS dict; it is only ever read (.get), never mutated - safe default, ruff-clean."
  ],
  "summary": "Diff does exactly what the task asks: generic tape_speed_light() over completed-M5 bars vs per-session-hour norms (calm < 0.8, fast > 1.25, unknown under 3 bars or a bar whose end is > 15 min old, 30-min completed-bar window), tick_range_light() as a thin wrapper preserving its historical schema, 'wide' label, 1-decimal rounding and reason strings (all pre-existing TICK goldens and the parametrized threshold test pass untouched); SESSION_HOUR_SPY_RANGE_NORMS added with a provenance comment; tape_light() fallback order SPY -> TICK (wide=fast) -> none-with-SPY-reason; monitor gains spy_bars_provider and writes market.tape in two fail-open try/except blocks after the unchanged market.tick block; legacy.py wires the provider from the latest_bars SPY M5 cache only (no IB); chip says 'tape fast/normal/calm' (omitted when source none) and the tooltip names SPY or 'TICK fallback'; fixture raw inputs byte-identical (sha256 stays valid) with only case-1 chip/tooltip expected values updated; CHANGELOG line added. Tests: 41/41 in the two touched files, 25/25 in the adjacent main module file, ruff clean. No order/sizing/IB behaviour touched; no ask-first file edited beyond the task's explicit one-line legacy.py change (which the task names)."
}
```

# REFERENCE DIFF (the merged change, for comparison)
```diff
diff --git a/scripts/bounce_bot_lib/legacy.py b/scripts/bounce_bot_lib/legacy.py
index 7636909b..afb33881 100644
--- a/scripts/bounce_bot_lib/legacy.py
+++ b/scripts/bounce_bot_lib/legacy.py
@@ -3262,7 +3262,7 @@ class BounceBot(EWrapper, EClient):
             if self._technical_integrity_monitor is None:
                 from technical_integrity import TechnicalIntegrityMonitor
 
-                self._technical_integrity_monitor = TechnicalIntegrityMonitor()
+                self._technical_integrity_monitor = TechnicalIntegrityMonitor(spy_bars_provider=lambda: self.m5_chart_bars("SPY", max_sessions=1))
             return self._technical_integrity_monitor
 
     def _observe_technical_integrity(self, symbol, full_df):
diff --git a/scripts/technical_integrity.py b/scripts/technical_integrity.py
index c53c5ff0..b822d5aa 100644
--- a/scripts/technical_integrity.py
+++ b/scripts/technical_integrity.py
@@ -641,6 +641,11 @@ TICK_LIGHT_WINDOW_MINUTES = 30
 TICK_LIGHT_STALE_MINUTES = 15
 TICK_LIGHT_MIN_BARS = 3
 TICK_CONTRACT_SYMBOL = "TICK-NYSE"
+TAPE_LIGHT_SCHEMA = "technical_integrity_tape_light_v1"
+#: SPY mean M5 range as % of close by session hour, 30 sessions ending 2026-10-05.
+SESSION_HOUR_SPY_RANGE_PCT_NORMS = {
+    0: 0.1065, 1: 0.0834, 2: 0.0710, 3: 0.0620, 4: 0.0546, 5: 0.0568, 6: 0.0707,
+}
 
 
 def _as_market_local(value: Any) -> datetime | None:
@@ -750,8 +755,8 @@ def rolling_technical_integrity(
     return result
 
 
-def _tick_bar(row: Any) -> tuple[datetime, datetime, float, datetime] | None:
-    """(start, end, high-low, end as stamped) for one TICK-NYSE breadth bar, else None."""
+def _tick_bar(row: Any) -> dict[str, Any] | None:
+    """One TICK-NYSE breadth row as a completed-M5 bar dict (aware stamps only), else None."""
     if not isinstance(row, Mapping) or row.get("event_type") != "breadth_bar":
         return None
     contract = row.get("contract") if isinstance(row.get("contract"), Mapping) else {}
@@ -770,43 +775,70 @@ def _tick_bar(row: Any) -> tuple[datetime, datetime, float, datetime] | None:
         low = float(row["low"])
     except (KeyError, TypeError, ValueError):
         return None
-    if not math.isfinite(high) or not math.isfinite(low) or high < low:
+    return {
+        "_start_local": normalize_market_local_datetime(start),
+        "bar_end": end.isoformat(timespec="seconds"),
+        "high": high,
+        "low": low,
+        "close": float(row.get("close") or 0.0),
+    }
+
+
+def _points_range(bar: Mapping[str, Any]) -> float | None:
+    return float(bar["high"]) - float(bar["low"])
+
+
+def _range_pct_of_close(bar: Mapping[str, Any]) -> float | None:
+    close = float(bar["close"])
+    if close <= 0:
         return None
-    return (
-        normalize_market_local_datetime(start),
-        normalize_market_local_datetime(end),
-        high - low,
-        end,
-    )
+    return (float(bar["high"]) - float(bar["low"])) / close * 100.0
 
 
-def tick_range_light(
-    tick_rows: Iterable[Mapping[str, Any]] | None,
+def tape_speed_light(
+    bars: Iterable[Mapping[str, Any]] | None,
     *,
     as_of: datetime | str | None,
+    norms: Mapping[int, float],
     window_minutes: int = TICK_LIGHT_WINDOW_MINUTES,
+    range_fn: Callable[[Mapping[str, Any]], float | None] = _range_pct_of_close,
+    digits: int = 4,
+    fast_word: str = "fast",
+    label: str = "M5",
+    schema: str = TAPE_LIGHT_SCHEMA,
 ) -> dict[str, Any]:
-    """NYSE TICK M5 range over the last ``window_minutes`` versus the usual for those hours."""
+    """Mean M5 range over the last ``window_minutes`` versus the norm for each bar's session hour.
+
+    ``bars`` are completed-M5 dicts (``_start_local`` aware, ``bar_end`` ISO); the default
+    range is (high - low) / close * 100. calm < 0.8 of usual, ``fast_word`` > 1.25, else
+    normal; unknown when fewer than 3 bars or the newest bar ended over 15 minutes ago.
+    """
     moment = _as_market_local(as_of) if as_of is not None else normalize_market_local_datetime()
     if moment is None:
         moment = normalize_market_local_datetime()
     start = moment - timedelta(minutes=int(window_minutes))
-    bars: dict[datetime, tuple[datetime, float, float, datetime]] = {}
-    for row in tick_rows or ():
-        parsed = _tick_bar(row)
-        if parsed is None:
+    kept: dict[datetime, tuple[datetime, float, float, datetime]] = {}
+    for bar in bars or ():
+        try:
+            bar_start = normalize_market_local_datetime(bar["_start_local"])
+            stamped_end = _parse_datetime(bar.get("bar_end"))
+            high, low = float(bar["high"]), float(bar["low"])
+            if stamped_end is None or not math.isfinite(high) or not math.isfinite(low) or high < low:
+                continue
+            bar_end = normalize_market_local_datetime(stamped_end)
+            bar_range = range_fn(bar)
+        except (KeyError, TypeError, ValueError):
             continue
-        bar_start, bar_end, bar_range, stamped_end = parsed
-        if not start < bar_end <= moment:
+        if bar_range is None or not math.isfinite(bar_range) or not start < bar_end <= moment:
             continue
         hour = _session_hour_index(bar_start)
-        norm = SESSION_HOUR_TICK_RANGE_NORMS.get(hour) if hour is not None else None
+        norm = norms.get(hour) if hour is not None else None
         if norm is None:
             continue
-        bars[bar_start] = (bar_end, bar_range, float(norm), stamped_end)
-    ordered = [bars[key] for key in sorted(bars)]
+        kept[bar_start] = (bar_end, float(bar_range), float(norm), stamped_end)
+    ordered = [kept[key] for key in sorted(kept)]
     result: dict[str, Any] = {
-        "schema": TICK_LIGHT_SCHEMA,
+        "schema": schema,
         "as_of": moment.isoformat(timespec="seconds"),
         "bar_count": len(ordered),
         "range_mean": None,
@@ -818,21 +850,81 @@ def tick_range_light(
     if ordered:
         range_mean = sum(item[1] for item in ordered) / len(ordered)
         expected = sum(item[2] for item in ordered) / len(ordered)
-        result["range_mean"] = round(range_mean, 1)
-        result["expected_range"] = round(expected, 1)
+        result["range_mean"] = round(range_mean, digits)
+        result["expected_range"] = round(expected, digits)
         result["ratio"] = round(range_mean / expected, 4) if expected > 0 else None
     if not ordered:
-        result["reason"] = "no TICK bars in the window"
+        result["reason"] = f"no {label} bars in the window"
     elif ordered[-1][0] < moment - timedelta(minutes=TICK_LIGHT_STALE_MINUTES):
-        result["reason"] = f"newest TICK bar is older than {TICK_LIGHT_STALE_MINUTES} minutes"
+        result["reason"] = f"newest {label} bar is older than {TICK_LIGHT_STALE_MINUTES} minutes"
     elif len(ordered) < TICK_LIGHT_MIN_BARS:
-        result["reason"] = f"fewer than {TICK_LIGHT_MIN_BARS} TICK bars in the window"
+        result["reason"] = f"fewer than {TICK_LIGHT_MIN_BARS} {label} bars in the window"
     elif result["ratio"] is not None:
         ratio = range_mean / expected
-        result["light"] = "calm" if ratio < 0.8 else "wide" if ratio > 1.25 else "normal"
+        result["light"] = "calm" if ratio < 0.8 else fast_word if ratio > 1.25 else "normal"
     return result
 
 
+def tick_range_light(
+    tick_rows: Iterable[Mapping[str, Any]] | None,
+    *,
+    as_of: datetime | str | None,
+    window_minutes: int = TICK_LIGHT_WINDOW_MINUTES,
+) -> dict[str, Any]:
+    """NYSE TICK M5 range (points) over the last ``window_minutes`` vs the usual for those hours."""
+    bars = [bar for bar in (_tick_bar(row) for row in tick_rows or ()) if bar is not None]
+    return tape_speed_light(
+        bars,
+        as_of=as_of,
+        norms=SESSION_HOUR_TICK_RANGE_NORMS,
+        window_minutes=window_minutes,
+        range_fn=_points_range,
+        digits=1,
+        fast_word="wide",
+        label="TICK",
+        schema=TICK_LIGHT_SCHEMA,
+    )
+
+
+def tape_light(
+    spy_bars: Iterable[Mapping[str, Any]] | None,
+    tick_light: Mapping[str, Any] | None,
+    *,
+    as_of: datetime | str | None,
+    spy_error: str = "",
+) -> dict[str, Any]:
+    """The tape light: SPY's own M5 range first, the TICK light as the fallback, else none."""
+    spy: dict[str, Any] | None = None
+    if spy_error:
+        spy_reason = f"SPY bars read failed: {spy_error}"
+    elif spy_bars is None:
+        spy_reason = "no SPY bars provider"
+    else:
+        spy = tape_speed_light(
+            spy_bars, as_of=as_of, norms=SESSION_HOUR_SPY_RANGE_PCT_NORMS, label="SPY"
+        )
+        spy_reason = str(spy.get("reason") or "")
+    if spy is not None and spy["light"] != "unknown":
+        return {**spy, "schema": TAPE_LIGHT_SCHEMA, "source": "SPY"}
+    tick = dict(tick_light or {})
+    if tick.get("light") not in (None, "", "unknown"):
+        light = "fast" if tick["light"] == "wide" else tick["light"]
+        return {**tick, "schema": TAPE_LIGHT_SCHEMA, "source": "TICK", "light": light}
+    moment = _as_market_local(as_of) if as_of is not None else None
+    return {
+        "schema": TAPE_LIGHT_SCHEMA,
+        "source": "none",
+        "as_of": (moment or normalize_market_local_datetime()).isoformat(timespec="seconds"),
+        "bar_count": int((spy or {}).get("bar_count") or 0),
+        "range_mean": None,
+        "expected_range": None,
+        "ratio": None,
+        "light": "unknown",
+        "last_bar_end": str((spy or {}).get("last_bar_end") or ""),
+        "reason": spy_reason,
+    }
+
+
 #: Last parsed breadth-ledger tail, keyed by (path, mtime_ns, size): the snapshot publishes
 #: many times per scan, the ledger grows once per 5-minute bar.
 _TICK_TAIL_CACHE: dict[str, Any] = {}
@@ -1409,8 +1501,10 @@ class TechnicalIntegrityMonitor:
         config: TechnicalIntegrityConfig | None = None,
         collector_started_at: datetime | None = None,
         tick_rows_provider: Callable[[], Iterable[Mapping[str, Any]]] | None = None,
+        spy_bars_provider: Callable[[], Iterable[Mapping[str, Any]]] | None = None,
     ) -> None:
         self.tick_rows_provider = tick_rows_provider or _default_tick_rows
+        self.spy_bars_provider = spy_bars_provider
         self.events_path = Path(events_path or technical_integrity_events_path())
         self.state_path = Path(state_path or technical_integrity_state_path())
         self.snapshot_path = Path(snapshot_path or technical_integrity_snapshot_path())
@@ -1693,6 +1787,20 @@ class TechnicalIntegrityMonitor:
                 "light": "unknown",
                 "reason": f"TICK read failed: {exc}",
             }
+        spy_bars: list[dict[str, Any]] | None = None
+        spy_error = ""
+        if self.spy_bars_provider is not None:
+            try:
+                spy_bars = completed_m5_bars(self.spy_bars_provider(), now=_as_market_local(as_of))
+            except Exception as exc:  # noqa: BLE001 - advisory extra, never blocks the publish
+                note_swallowed("technical integrity SPY tape read failed", exc, quiet=True)
+                spy_error = str(exc) or exc.__class__.__name__
+        try:
+            snapshot["market"]["tape"] = tape_light(
+                spy_bars, snapshot["market"].get("tick"), as_of=as_of, spy_error=spy_error
+            )
+        except Exception as exc:  # noqa: BLE001 - advisory extra, never blocks the publish
+            note_swallowed("technical integrity tape light failed", exc)
         _atomic_write_json(self.snapshot_path, snapshot)
         return snapshot
 
@@ -2886,20 +2994,30 @@ def _rolling_now_view(
         line("D1", d1),
         line("M5", m5),
     ]
-    tick = market.get("tick") if isinstance(market.get("tick"), Mapping) else {}
-    light = str(tick.get("light") or "unknown")
-    if light != "unknown":
-        chip += f" · TICK {light}"
+    tape = market.get("tape") if isinstance(market.get("tape"), Mapping) else {}
+    light = str(tape.get("light") or "unknown")
+    source = str(tape.get("source") or "none")
+    minutes = TICK_LIGHT_WINDOW_MINUTES
+    if light != "unknown" and source == "SPY":
+        chip += f" · tape {light}"
+        lines.append(
+            f"Tape (SPY, last {minutes} min): M5 range "
+            f"{float(tape.get('range_mean') or 0.0):.3f}% vs "
+            f"{float(tape.get('expected_range') or 0.0):.3f}% usual = {light} "
+            "(levels fail more when the tape is fast; fast now also means weaker M5 levels "
+            "next hour)."
+        )
+    elif light != "unknown" and source == "TICK":
+        chip += f" · tape {light}"
         lines.append(
-            f"TICK (last {TICK_LIGHT_WINDOW_MINUTES} min): range "
-            f"{float(tick.get('range_mean') or 0.0):.0f} vs "
-            f"{float(tick.get('expected_range') or 0.0):.0f} usual = {light} "
-            "(levels fail more when TICK is wide)."
+            f"Tape (TICK fallback, last {minutes} min): range "
+            f"{float(tape.get('range_mean') or 0.0):.0f} vs "
+            f"{float(tape.get('expected_range') or 0.0):.0f} usual = {light}."
         )
-    elif tick:
+    elif tape:
         lines.append(
-            f"TICK (last {TICK_LIGHT_WINDOW_MINUTES} min): unknown"
-            + (f" ({tick.get('reason')})." if tick.get("reason") else ".")
+            f"Tape (last {minutes} min): unknown"
+            + (f" ({tape.get('reason')})." if tape.get("reason") else ".")
         )
     headline = d1 if d1.get("score") is not None else m5
     return (
diff --git a/tests/test_technical_integrity_rolling.py b/tests/test_technical_integrity_rolling.py
index 4bf6c44c..106367d5 100644
--- a/tests/test_technical_integrity_rolling.py
+++ b/tests/test_technical_integrity_rolling.py
@@ -40,18 +40,28 @@ def _event(event_id, timeframe, touch, resolved, outcome, weight=2.5, symbol="MU
     }
 
 
-def _snapshot_at(fixture, case):
+def _spy_bars(fixture, as_of):
+    from technical_integrity import completed_m5_bars
+
+    return completed_m5_bars(fixture["spy_bars"], now=datetime.fromisoformat(as_of))
+
+
+def _snapshot_at(fixture, case, *, with_spy=True):
     from technical_integrity import (
         aggregate_technical_integrity,
         rolling_technical_integrity,
+        tape_light,
         tick_range_light,
     )
 
     as_of = case["as_of"]
     known = [row for row in fixture["events"] if row["resolved_at"] <= as_of]
     snapshot = aggregate_technical_integrity(known, as_of=as_of, session_date=fixture["session_date"])
-    snapshot["market"]["rolling"] = rolling_technical_integrity(fixture["events"], as_of=as_of)
-    snapshot["market"]["tick"] = tick_range_light(fixture["tick_rows"], as_of=as_of)
+    market = snapshot["market"]
+    market["rolling"] = rolling_technical_integrity(fixture["events"], as_of=as_of)
+    market["tick"] = tick_range_light(fixture["tick_rows"], as_of=as_of)
+    spy = _spy_bars(fixture, as_of) if with_spy else None
+    market["tape"] = tape_light(spy, market["tick"], as_of=as_of)
     return snapshot
 
 
@@ -103,6 +113,71 @@ def test_chip_and_tooltip_lead_with_the_now_reading_golden():
             assert "Scanned-market Technical Integrity:" in tooltip.split("Today so far:")[1]
         if "color" in case:
             assert color == case["color"]
+        if "chip_without_spy" in case:
+            chip, tooltip, _color = format_technical_integrity_snapshot(
+                _snapshot_at(fixture, case, with_spy=False),
+                now=datetime.fromisoformat(case["as_of"]),
+            )
+            assert chip == case["chip_without_spy"]
+            assert case["tape_line_without_spy"] in tooltip.splitlines()
+
+
+def test_tape_light_golden_spy_first_then_tick():
+    from technical_integrity import tape_light, tick_range_light
+
+    fixture = _fixture()
+    for case in fixture["expected"]["cases"]:
+        if "tape" not in case:
+            continue
+        as_of = case["as_of"]
+        tick = tick_range_light(fixture["tick_rows"], as_of=as_of)
+        tape = tape_light(_spy_bars(fixture, as_of), tick, as_of=as_of)
+        assert tape["schema"] == "technical_integrity_tape_light_v1"
+        for key, value in case["tape"].items():
+            fixture.assert_matches(tape[key], value, f"{as_of}.tape.{key}")
+        if "tape_without_spy" in case:
+            fallback = tape_light(None, tick, as_of=as_of)
+            for key, value in case["tape_without_spy"].items():
+                fixture.assert_matches(fallback[key], value, f"{as_of}.tape_without_spy.{key}")
+
+
+def test_tape_fallback_order_spy_then_tick_then_none():
+    from technical_integrity import tape_light
+
+    as_of = "2026-10-05T11:00:00-04:00"
+    fixture = _fixture()
+    spy = _spy_bars(fixture, as_of)
+    wide_tick = {"light": "wide", "range_mean": 600.0, "expected_range": 400.0, "bar_count": 6}
+    calm_tick = {"light": "calm", "range_mean": 200.0, "expected_range": 400.0, "bar_count": 6}
+    unknown_tick = {"light": "unknown", "reason": "no TICK bars in the window"}
+
+    # SPY known: SPY wins even when TICK disagrees.
+    assert tape_light(spy, calm_tick, as_of=as_of)["source"] == "SPY"
+    assert tape_light(spy, calm_tick, as_of=as_of)["light"] == "fast"
+    # SPY unknown (no provider, stale bars, or a failed read): TICK, with "wide" said as "fast".
+    for spy_input, error in ((None, ""), ([], ""), (None, "boom")):
+        fallback = tape_light(spy_input, wide_tick, as_of=as_of, spy_error=error)
+        assert (fallback["source"], fallback["light"]) == ("TICK", "fast")
+    # Both unknown: none, carrying the SPY reason.
+    none = tape_light([], unknown_tick, as_of=as_of)
+    assert (none["source"], none["light"]) == ("none", "unknown")
+    assert none["reason"] == "no SPY bars in the window"
+    failed = tape_light(None, unknown_tick, as_of=as_of, spy_error="boom")
+    assert failed["reason"] == "SPY bars read failed: boom"
+
+
+def test_chip_omits_the_tape_when_the_source_is_none():
+    from technical_integrity import format_technical_integrity_snapshot
+
+    fixture = _fixture()
+    case = next(c for c in fixture["expected"]["cases"] if c.get("chip_without_spy"))
+    snapshot = _snapshot_at(fixture, case)
+    snapshot["market"]["tape"] = {"source": "none", "light": "unknown", "reason": "no SPY bars provider"}
+    chip, tooltip, _color = format_technical_integrity_snapshot(
+        snapshot, now=datetime.fromisoformat(case["as_of"])
+    )
+    assert chip == "Technicals now: D1 VERY WEAK 2.2/10 · M5 STRONG 9.1/10"
+    assert "Tape (last 30 min): unknown (no SPY bars provider)." in tooltip.splitlines()
 
 
 # ------------------------------------------------------------------ D1 midpoint
@@ -240,6 +315,29 @@ def test_publish_snapshot_survives_a_raising_tick_provider(tmp_path):
     assert "ledger gone" in market["tick"]["reason"]
     assert market["rolling"]["schema"] == "technical_integrity_rolling_v1"
     assert market["rolling"]["m5"]["test_count"] == 5
+    assert (market["tape"]["source"], market["tape"]["light"]) == ("none", "unknown")
+
+
+def test_publish_snapshot_uses_spy_bars_and_survives_a_raising_spy_provider(tmp_path):
+    fixture = _fixture()
+    as_of = "2026-10-05T11:00:00-04:00"
+
+    def spy_boom():
+        raise RuntimeError("cache gone")
+
+    tick_rows = lambda: fixture["tick_rows"]  # noqa: E731
+    with_spy = _monitor(tmp_path / "a", tick_rows_provider=tick_rows,
+                        spy_bars_provider=lambda: fixture["spy_bars"])
+    with_spy.session_date = "2026-10-05"
+    tape = with_spy._publish_snapshot(as_of, "")["market"]["tape"]
+    assert (tape["source"], tape["light"], tape["bar_count"]) == ("SPY", "fast", 6)
+
+    raising = _monitor(tmp_path / "b", tick_rows_provider=tick_rows, spy_bars_provider=spy_boom)
+    raising.session_date = "2026-10-05"
+    raising._publish_snapshot(as_of, "")
+    written = json.loads((tmp_path / "b" / "snapshot.json").read_text(encoding="utf-8"))["market"]
+    assert (written["tape"]["source"], written["tape"]["light"]) == ("TICK", "fast")
+    assert written["tick"]["light"] == "wide"  # the TICK light is still written as before
 
 
 def test_publish_snapshot_reads_the_vold_ledger_by_default(tmp_path, monkeypatch):
```

## Lead note (facts measured by the lead, not by the builder)
- Full suite in the builder's worktree: 11 failed / 16049 passed. Of the 11, three also fail on the clean parent commit (test_evidence_snapshot ops-scripts, two test_like_cohort_grading); three need git history the harness worktree does not have (git show rc=128 there, rc=0 in the main repo: test_m5_strength_characterization R8 baseline, two test_ws_rp_shared_report); five Qt layout tests pass in isolation in both trees and failed only in the 4-worker run at 0 GB free RAM. None of the 11 touches the changed files.
- Hidden reference tests: 14 passed, 4 failed, all four because tape_light() does not accept the as_of keyword the reference tests pass.
- ruff clean; the builder's own tests pass.
