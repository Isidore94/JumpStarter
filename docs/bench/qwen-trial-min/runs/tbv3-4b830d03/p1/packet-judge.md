# BRIEF
Goal: M5 bounce alerts get a setup tier A/B/C/D from a rule on four facts: bar hour, bounce family, sector RRS present, and internals tape vs side. The learning letter from learning.evaluate_bounce_quality does not separate outcomes (23-28% for every letter) but those four facts do; keep the old letter beside the new one as learning_tier. The tier is a point table: tier boundaries 4/3/2/1/0/-1 -> A/B/C/D, the reason text listed in table order, side case-insensitive, when=None allowed, bounce types as a list or a ";" string, neutral tapes score 0, regime beats h1_green_to_yellow.
_evaluate_bounce_alert_quality shows the setup tier, keeps the learning letter as learning_tier, leaves muted / mute_reasons / shadow_s9 and the rest unchanged, and falls back to learning_tier B with the rule's tier when learning raises; record_alert_tier's row carries learning_tier.
Done when: tests/test_setup_tier.py covers every table term and boundary, a legacy-hook test covers the alert dict and the recorded row, and run_tests.py/pytest plus ruff are green.
Files: new scripts/bounce_bot_lib/setup_tier.py; scripts/bounce_bot_lib/legacy.py (_evaluate_bounce_alert_quality, record_alert_tier); scripts/bounce_bot_lib/learning.py (read only).
Don't touch: order/sizing code, the muting rules, learning.py's letter, the alert payload keys other than the tier fields.
Pattern: learning.evaluate_bounce_quality's shape (tier, reasons) and the existing legacy hook tests.

# CANDIDATE DIFF
```diff
diff --git a/scripts/bounce_bot_lib/legacy.py b/scripts/bounce_bot_lib/legacy.py
index 9421e6d..eeda142 100644
--- a/scripts/bounce_bot_lib/legacy.py
+++ b/scripts/bounce_bot_lib/legacy.py
@@ -4189,7 +4189,13 @@ class BounceBot(EWrapper, EClient):
         }
 
     def _evaluate_bounce_alert_quality(self, direction, levels, event_row):
-        """Tier + mute verdict for a confirmed bounce, from the learning state."""
+        """Setup tier + learning letter + mute verdict for a confirmed bounce.
+
+        The alert shows the four-facts setup tier; the learning letter stays
+        beside it as `learning_tier` and still owns the mute.
+        """
+        row = event_row if isinstance(event_row, dict) else {}
+        setup = self._setup_tier_for_alert(direction, levels, row)
         try:
             from bounce_bot_lib.learning import (
                 evaluate_bounce_quality,
@@ -4197,7 +4203,6 @@ class BounceBot(EWrapper, EClient):
                 time_bucket_for,
             )
 
-            row = event_row if isinstance(event_row, dict) else {}
             bounce_type_keys = _bounce_type_keys_from_levels(levels or {})
             state = load_bounce_learning_state()
             when = _bounce_quality_time(row) or get_market_local_now()
@@ -4220,10 +4225,37 @@ class BounceBot(EWrapper, EClient):
             )
         except Exception as exc:  # learning must never block an alert
             logging.warning("Bounce learning evaluation failed (alerting anyway): %s", exc)
-            return {"tier": "B", "muted": False, "mute_reasons": [], "reasons": []}
-        quality["shadow_s9"] = self._shadow_s9_tier(state, context, when)
+            quality = {"tier": "B", "muted": False, "mute_reasons": [], "reasons": []}
+        else:
+            quality["shadow_s9"] = self._shadow_s9_tier(state, context, when)
+        quality["learning_tier"] = quality["tier"]
+        if setup:
+            quality["setup_tier"] = setup
+            quality["tier"] = setup["tier"]
         return quality
 
+    @staticmethod
+    def _setup_tier_for_alert(direction, levels, row):
+        """The four-facts setup tier for this alert. `{}` when the rule cannot score it."""
+        try:
+            from bounce_bot_lib.setup_tier import evaluate_setup_tier
+
+            bounce_types = str(row.get("bounce_types") or "").strip()
+            if not bounce_types:
+                bounce_types = ";".join(_bounce_type_keys_from_levels(levels or {}))
+            return evaluate_setup_tier(
+                side=str(direction or ""),
+                # The bar time is a fact about the bar: no fallback to now, an
+                # unknown hour simply scores 0.
+                when=_bounce_quality_time(row),
+                bounce_types=bounce_types,
+                sector_rrs_present=bool(str(row.get("rrs_sector") or "").strip()),
+                tape=str(row.get("internals_tape") or ""),
+            )
+        except Exception as exc:
+            logging.debug("Setup tier skipped (advisory only): %s", exc)
+            return {}
+
     @staticmethod
     def _shadow_s9_tier(state, context, when) -> dict:
         """S9 shadow tier, evidence only: `{}` on any failure, never read by a live decision."""
@@ -5449,6 +5481,8 @@ class BounceBot(EWrapper, EClient):
                     "event_type": "tier_assigned",
                     "event_id": event_id,
                     "tier": tier,
+                    # The learning letter beside the setup tier the alert showed.
+                    "learning_tier": str(verdict.get("learning_tier") or "").strip(),
                     "muted": bool(verdict.get("muted")),
                     "proven": bool(verdict.get("proven")),
                     # S9 shadow tier beside the live one (evidence only).
diff --git a/scripts/bounce_bot_lib/setup_tier.py b/scripts/bounce_bot_lib/setup_tier.py
new file mode 100644
index 0000000..35a6f35
--- /dev/null
+++ b/scripts/bounce_bot_lib/setup_tier.py
@@ -0,0 +1,138 @@
+"""Setup tier for M5 bounce alerts: a point rule over four measured facts.
+
+The learning letter (learning.evaluate_bounce_quality) does not separate
+outcomes - every letter shows up in 23-28% of winners. Four facts on the
+event row do: the bar hour, the bounce family, whether a sector RRS is
+present, and the internals tape vs. the side. This module scores those four
+facts into an A/B/C/D letter that the alert shows, while the hook keeps the
+learning letter beside it as `learning_tier`.
+
+The rule is advisory evidence: it never mutes, never raises into the alert
+path, and an unknown fact scores 0 - missing data is "unknown", never
+"confirmed".
+"""
+
+from __future__ import annotations
+
+from datetime import datetime
+
+from market_session import get_market_session_window
+
+#: The boundary map, highest first: 4/3/2/1/0/-1 -> A/B/C/D/D/D.
+TIER_BOUNDARIES = ((4, "A"), (3, "B"), (2, "C"), (1, "D"), (0, "D"), (-1, "D"))
+
+_BAR_HOUR_UNKNOWN_REASON = "bar hour unknown: 0"
+
+
+def tier_for_points(points: int) -> str:
+    """Map a fact total onto the letter ladder (4/3/2 -> A/B/C, 1 and below -> D)."""
+    for threshold, tier in TIER_BOUNDARIES:
+        if points >= threshold:
+            return tier
+    return "D"
+
+
+def _bar_hour_points(when: datetime | None) -> tuple[int, str]:
+    """Fact 1: the bar hour in its session. Opening -1, mid-session +1, last hour 0.
+
+    A naive bar time is market-local (the zone the session window is
+    expressed in); an aware one is converted into it. Off-window or missing
+    time is unknown, which scores 0.
+    """
+    try:
+        if when is None:
+            return 0, _BAR_HOUR_UNKNOWN_REASON
+        session = get_market_session_window(reference=when)
+        moment = when
+        if moment.tzinfo is None:
+            moment = moment.replace(tzinfo=session.open_local.tzinfo)
+        else:
+            moment = moment.astimezone(session.open_local.tzinfo)
+        if moment < session.open_local or moment >= session.close_local:
+            return 0, _BAR_HOUR_UNKNOWN_REASON
+        hour = moment.hour
+    except Exception:
+        return 0, _BAR_HOUR_UNKNOWN_REASON
+    if hour == session.open_local.hour:
+        return -1, f"opening bar (hour {hour}): -1"
+    if hour >= session.last_hour_start_local.hour:
+        return 0, f"last-hour bar (hour {hour}): 0"
+    return 1, f"mid-session bar (hour {hour}): +1"
+
+
+def _bounce_family_points(bounce_types: list[str] | tuple | str | None) -> tuple[int, str]:
+    """Fact 2: the bounce family. Regime types +1, h1_green_to_yellow -1, else 0.
+
+    Accepts a list or a ";" string, case-insensitive; with several types the
+    best row wins, so regime beats h1_green_to_yellow.
+    """
+    if isinstance(bounce_types, str):
+        raw = (part for part in str(bounce_types).split(";"))
+    else:
+        raw = (bounce_types or [])
+    types = {str(type).strip().lower() for type in raw if str(type or "").strip()}
+    if not types:
+        return 0, "bounce family: unknown: 0"
+    if any("regime" in type for type in types):
+        return 1, "bounce family: regime: +1"
+    if "h1_green_to_yellow" in types:
+        return -1, "bounce family: h1_green_to_yellow: -1"
+    return 0, "bounce family: neutral: 0"
+
+
+def _sector_rrs_points(sector_rrs_present: bool) -> tuple[int, str]:
+    """Fact 3: a sector RRS present is +1; absence is unknown, not negative."""
+    if sector_rrs_present:
+        return 1, "sector RRS present: +1"
+    return 0, "sector RRS absent: 0"
+
+
+def _tape_points(tape: str, side: str) -> tuple[int, str]:
+    """Fact 4: the internals tape vs. the side, both case-insensitive.
+
+    risk_on* with long and risk_off* with short score +1, the opposite
+    combination -1, the neutral mixed tape 0, and an unknown tape or side 0.
+    """
+    tape_value = str(tape or "").strip().lower()
+    side_value = str(side or "").strip().lower()
+    if tape_value in ("risk_on", "risk_on_tilt"):
+        if side_value == "long":
+            return 1, f"internals tape {tape_value} supports long: +1"
+        if side_value == "short":
+            return -1, f"internals tape {tape_value} opposes short: -1"
+        return 0, f"internals tape {tape_value}, side unknown: 0"
+    if tape_value in ("risk_off", "risk_off_tilt"):
+        if side_value == "short":
+            return 1, f"internals tape {tape_value} supports short: +1"
+        if side_value == "long":
+            return -1, f"internals tape {tape_value} opposes long: -1"
+        return 0, f"internals tape {tape_value}, side unknown: 0"
+    if tape_value == "mixed":
+        return 0, "internals tape mixed is neutral: 0"
+    return 0, "internals tape unknown: 0"
+
+
+def evaluate_setup_tier(
+    *,
+    side: str = "",
+    when: datetime | None = None,
+    bounce_types: list[str] | tuple | str = (),
+    sector_rrs_present: bool = False,
+    tape: str = "",
+) -> dict:
+    """Score the four measured facts of a bounce alert into a setup tier.
+
+    Returns `{"tier", "points", "reasons"}`: one reason per table row, in
+    table order (bar hour, bounce family, sector RRS, internals tape). The
+    reachable total is -3..+4; the letter follows TIER_BOUNDARIES.
+    """
+    hour_points, hour_reason = _bar_hour_points(when)
+    family_points, family_reason = _bounce_family_points(bounce_types)
+    rrs_points, rrs_reason = _sector_rrs_points(bool(sector_rrs_present))
+    tape_points, tape_reason = _tape_points(tape, side)
+    total = hour_points + family_points + rrs_points + tape_points
+    return {
+        "tier": tier_for_points(total),
+        "points": total,
+        "reasons": [hour_reason, family_reason, rrs_reason, tape_reason],
+    }
diff --git a/tests/test_s9_p14_tier_golden.py b/tests/test_s9_p14_tier_golden.py
index f67f94c..81adc87 100644
--- a/tests/test_s9_p14_tier_golden.py
+++ b/tests/test_s9_p14_tier_golden.py
@@ -142,6 +142,7 @@ def test_the_bot_seam_keeps_live_tier_text_and_mutes_with_extreme_regime_segment
     state = _state_with_extreme_regime_segments()
     monkeypatch.setattr(learning, "load_bounce_learning_state", lambda path=None: state)
     monkeypatch.setattr(learning, "structural_regime_on", lambda day: REGIME)
+    monkeypatch.setenv("TRADINGBOT_MARKET_TIMEZONE", "America/New_York")
     shadow_differs = 0
     for case in CASES:
         inputs = case["inputs"]
@@ -160,11 +161,38 @@ def test_the_bot_seam_keeps_live_tier_text_and_mutes_with_extreme_regime_segment
         )
         shadow = quality.pop("shadow_s9")
         expected = EXPECTED[case["id"]]
-        assert quality == expected["quality"], case["id"]  # tier, composite, mutes, reasons
+        setup = quality.pop("setup_tier")
+
+        def _prefix_swap(message, new_tier, learning_tier=expected["quality"]["tier"]):
+            prefix = f"[{learning_tier}-TIER] "
+            assert message.startswith(prefix)
+            return f"[{new_tier}-TIER] " + message[len(prefix):]
+
+        # The message body stays byte-identical; only the tier prefix moves
+        # (the formatter reads quality["tier"], which is now the setup letter).
         if quality.get("proven_reasons"):
-            assert _message(case, quality) == _p14_text(case), case["id"]
+            assert _message(case, quality) == _prefix_swap(_p14_text(case), setup["tier"]), case["id"]
         else:
-            assert _message(case, quality) == expected["message"], case["id"]
+            assert _message(case, quality) == _prefix_swap(expected["message"], setup["tier"]), case["id"]
+
+        learning_tier = quality.pop("learning_tier")
+        shown_tier = quality.pop("tier")
+        # The learning verdict is untouched; only the shown tier moved.
+        assert learning_tier == expected["quality"]["tier"], case["id"]
+        rest = dict(expected["quality"])
+        rest.pop("tier")
+        assert quality == rest, case["id"]
+        assert shown_tier == setup["tier"], case["id"]
+        # These rows carry no RRS and no tape: the 10:00 bar scores +1 and the
+        # family at most +/-1, so the total is 0/1/2.
+        types = {bounce_type.lower() for bounce_type in inputs["bounce_types"]}
+        family = 1 if any("regime" in value for value in types) else (
+            -1 if "h1_green_to_yellow" in types else 0
+        )
+        points = 1 + family
+        assert setup["points"] == points, case["id"]
+        assert setup["tier"] == ("C" if points == 2 else "D"), case["id"]
+        assert len(setup["reasons"]) == 4, case["id"]
         plain = learning.evaluate_shadow_tier(STATE, **{k: v for k, v in inputs.items() if k != "swing_traits"})
         shadow_differs += int(shadow != plain)
     # The regime segments DO move the shadow, so the seam really fed it the regime.
diff --git a/tests/test_s9_shadow_tier.py b/tests/test_s9_shadow_tier.py
index 4c3e43f..448c532 100644
--- a/tests/test_s9_shadow_tier.py
+++ b/tests/test_s9_shadow_tier.py
@@ -154,18 +154,38 @@ def test_alert_quality_carries_the_shadow_beside_the_unchanged_live_verdict(monk
     state = learning.build_learning_state([_row("bounce_type", "long", "vwap", 400, 0.3)])
     monkeypatch.setattr(learning, "load_bounce_learning_state", lambda path=None: state)
     monkeypatch.setattr(learning, "structural_regime_on", lambda day: "")
+    monkeypatch.setenv("TRADINGBOT_MARKET_TIMEZONE", "America/New_York")
     row = {"market_environment": "", "signal_time": "2026-09-25 10:15:00"}
     quality = legacy.BounceBot._evaluate_bounce_alert_quality(
         legacy.BounceBot, "long", {"vwap": 1.0}, row
     )
     shadow = quality.pop("shadow_s9")
-    assert quality == learning.evaluate_bounce_quality(
+    shown_tier = quality.pop("tier")
+    learning_tier = quality.pop("learning_tier")
+    setup = quality.pop("setup_tier")
+    expected = learning.evaluate_bounce_quality(
         state,
         direction="long",
         bounce_types=["vwap"],
         time_bucket=learning.time_bucket_for(legacy._bounce_quality_time(row)),
         bounce_combo="vwap",
     )
+    assert learning_tier == "S" == expected.pop("tier")
+    # The learning verdict (mutes, reasons, proven, composite) is untouched;
+    # only the shown tier moved to the rule's letter.
+    assert quality == expected
+    # No RRS and no tape on this row, so only the bar hour can score.
+    assert setup == {
+        "tier": "D",
+        "points": 1,
+        "reasons": [
+            "mid-session bar (hour 10): +1",
+            "bounce family: neutral: 0",
+            "sector RRS absent: 0",
+            "internals tape unknown: 0",
+        ],
+    }
+    assert shown_tier == "D"
     assert shadow == {"tier": "S", "composite_r": 0.3}
 
 
diff --git a/tests/test_setup_tier.py b/tests/test_setup_tier.py
new file mode 100644
index 0000000..e756de9
--- /dev/null
+++ b/tests/test_setup_tier.py
@@ -0,0 +1,409 @@
+"""The M5 setup tier: a point rule over four measured facts, beside the learning letter.
+
+The learning letter does not separate outcomes (23-28% for every letter); four
+facts on the event row do: the bar hour, the bounce family, whether a sector
+RRS is present, and the internals tape vs. the side. The rule scores them into
+an A/B/C/D letter the alert shows, while the learning letter is kept beside it
+as `learning_tier`. Unknown facts score 0 - missing data is "unknown", never
+"confirmed".
+"""
+
+import sys
+from datetime import datetime
+from pathlib import Path
+from zoneinfo import ZoneInfo
+
+import pytest
+
+ROOT_DIR = Path(__file__).resolve().parents[1]
+SCRIPTS_DIR = ROOT_DIR / "scripts"
+if str(SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(SCRIPTS_DIR))
+
+from bounce_bot_lib import setup_tier  # noqa: E402
+
+
+@pytest.fixture(autouse=True)
+def _pin_the_market_timezone(monkeypatch):
+    """Naive bar times are market-local; pin the zone so hour expectations are stable."""
+    monkeypatch.setenv("TRADINGBOT_MARKET_TIMEZONE", "America/New_York")
+
+
+def tier(**kwargs) -> dict:
+    return setup_tier.evaluate_setup_tier(**kwargs)
+
+
+# --------------------------------------------------------------------------- the boundary map
+def test_every_boundary_of_the_point_table():
+    assert setup_tier.tier_for_points(4) == "A"
+    assert setup_tier.tier_for_points(3) == "B"
+    assert setup_tier.tier_for_points(2) == "C"
+    assert setup_tier.tier_for_points(1) == "D"
+    assert setup_tier.tier_for_points(0) == "D"
+    assert setup_tier.tier_for_points(-1) == "D"
+
+
+def test_below_the_table_stays_d():
+    assert setup_tier.tier_for_points(-2) == "D"
+    assert setup_tier.tier_for_points(-3) == "D"
+
+
+# --------------------------------------------------------------------------- fact 1: bar hour
+def test_the_opening_hour_bar_scores_minus_one():
+    result = tier(when=datetime(2026, 9, 25, 9, 45))
+    assert result["points"] == -1
+    assert result["tier"] == "D"
+    assert result["reasons"][0] == "opening bar (hour 9): -1"
+
+
+def test_the_opening_hour_starts_at_the_session_open():
+    assert tier(when=datetime(2026, 9, 25, 9, 30))["points"] == -1
+    assert tier(when=datetime(2026, 9, 25, 9, 29))["points"] == 0
+
+
+def test_the_mid_session_hours_score_plus_one():
+    for hour in (10, 11, 12, 13, 14):
+        result = tier(when=datetime(2026, 9, 25, hour, 30))
+        assert result["points"] == 1
+        assert result["reasons"][0] == f"mid-session bar (hour {hour}): +1"
+
+
+def test_the_last_hour_scores_zero():
+    result = tier(when=datetime(2026, 9, 25, 15, 45))
+    assert result["points"] == 0
+    assert result["reasons"][0] == "last-hour bar (hour 15): 0"
+
+
+def test_an_off_window_or_missing_time_is_unknown_never_confirmed():
+    assert tier(when=None)["points"] == 0
+    assert tier(when=datetime(2026, 9, 25, 8, 0))["points"] == 0
+    assert tier(when=datetime(2026, 9, 25, 16, 15))["points"] == 0
+    assert tier(when=datetime(2026, 9, 25, 7, 59))["reasons"][0] == "bar hour unknown: 0"
+    assert tier(when=None)["reasons"][0] == "bar hour unknown: 0"
+
+
+def test_an_aware_bar_time_is_converted_into_the_session_zone():
+    aware_ny = datetime(2026, 9, 25, 10, 30, tzinfo=ZoneInfo("America/New_York"))
+    assert tier(when=aware_ny)["points"] == 1
+    aware_utc = datetime(2026, 9, 25, 14, 30, tzinfo=ZoneInfo("UTC"))  # 10:30 EDT
+    assert tier(when=aware_utc)["points"] == 1
+
+
+# --------------------------------------------------------------------------- fact 2: bounce family
+def test_a_regime_family_scores_plus_one():
+    result = tier(bounce_types=["regime_pause_rs"])
+    assert result["points"] == 1
+    assert result["reasons"][1] == "bounce family: regime: +1"
+
+
+def test_h1_green_to_yellow_scores_minus_one():
+    result = tier(bounce_types=["h1_green_to_yellow"])
+    assert result["points"] == -1
+    assert result["reasons"][1] == "bounce family: h1_green_to_yellow: -1"
+
+
+def test_the_family_rule_is_case_insensitive():
+    assert tier(bounce_types=["REGIME_PAUSE_RS"])["points"] == 1
+    assert tier(bounce_types=["H1_GREEN_TO_YELLOW"])["points"] == -1
+
+
+def test_bounce_types_accept_a_semicolon_string():
+    assert tier(bounce_types="vwap;regime_break")["points"] == 1
+    assert tier(bounce_types="vwap;h1_green_to_yellow")["points"] == -1
+    assert tier(bounce_types="vwap;ema_15")["points"] == 0
+
+
+def test_regime_beats_h1_green_to_yellow():
+    assert tier(bounce_types=["h1_green_to_yellow", "regime_pause_rs"])["points"] == 1
+    assert tier(bounce_types="regime_pause_rs;h1_green_to_yellow")["points"] == 1
+
+
+def test_other_or_missing_families_score_zero():
+    neutral = tier(bounce_types=["vwap"])
+    assert neutral["points"] == 0
+    assert neutral["reasons"][1] == "bounce family: neutral: 0"
+    unknown = tier()
+    assert unknown["points"] == 0
+    assert unknown["reasons"][1] == "bounce family: unknown: 0"
+    assert tier(bounce_types=";;")["reasons"][1] == "bounce family: unknown: 0"
+    assert tier(bounce_types=None)["reasons"][1] == "bounce family: unknown: 0"
+
+
+# --------------------------------------------------------------------------- fact 3: sector RRS present
+def test_a_present_sector_rrs_scores_plus_one():
+    result = tier(sector_rrs_present=True)
+    assert result["points"] == 1
+    assert result["reasons"][2] == "sector RRS present: +1"
+
+
+def test_an_absent_sector_rrs_scores_zero():
+    result = tier()
+    assert result["points"] == 0
+    assert result["reasons"][2] == "sector RRS absent: 0"
+
+
+# --------------------------------------------------------------------------- fact 4: internals tape vs side
+def test_the_aligned_tape_scores_plus_one():
+    assert tier(side="long", tape="risk_on")["points"] == 1
+    assert tier(side="long", tape="risk_on_tilt")["points"] == 1
+    assert tier(side="short", tape="risk_off")["points"] == 1
+    assert tier(side="short", tape="risk_off_tilt")["points"] == 1
+
+
+def test_the_aligned_reasons_name_the_tape():
+    assert tier(side="long", tape="risk_on")["reasons"][3] == "internals tape risk_on supports long: +1"
+    assert tier(side="short", tape="risk_off_tilt")["reasons"][3] == "internals tape risk_off_tilt supports short: +1"
+
+
+def test_the_opposite_tape_scores_minus_one():
+    assert tier(side="short", tape="risk_on")["points"] == -1
+    assert tier(side="short", tape="risk_on_tilt")["points"] == -1
+    assert tier(side="long", tape="risk_off")["points"] == -1
+    assert tier(side="long", tape="risk_off_tilt")["points"] == -1
+
+
+def test_the_side_is_case_insensitive():
+    assert tier(side="LONG", tape="risk_on")["points"] == 1
+    assert tier(side="Short", tape="risk_off")["points"] == 1
+    assert tier(side="SHORT", tape="risk_on")["points"] == -1
+
+
+def test_neutral_and_unknown_tapes_score_zero():
+    mixed = tier(side="long", tape="mixed")
+    assert mixed["points"] == 0
+    assert mixed["reasons"][3] == "internals tape mixed is neutral: 0"
+    blank = tier(side="long", tape="")
+    assert blank["points"] == 0
+    assert blank["reasons"][3] == "internals tape unknown: 0"
+    assert tier(side="long", tape="unknown")["points"] == 0
+    assert tier(side="long", tape="sideways")["points"] == 0
+
+
+def test_a_known_tape_with_an_unknown_side_scores_zero():
+    result = tier(side="", tape="risk_on")
+    assert result["points"] == 0
+    assert result["reasons"][3] == "internals tape risk_on, side unknown: 0"
+    assert tier(side="up", tape="risk_off")["points"] == 0
+
+
+# --------------------------------------------------------------------------- totals and reason order
+def test_all_four_facts_aligned_score_a():
+    result = tier(
+        side="long",
+        when=datetime(2026, 9, 25, 10, 30),
+        bounce_types=["regime_pause_rs"],
+        sector_rrs_present=True,
+        tape="risk_on",
+    )
+    assert result["points"] == 4
+    assert result["tier"] == "A"
+    assert result["reasons"] == [
+        "mid-session bar (hour 10): +1",
+        "bounce family: regime: +1",
+        "sector RRS present: +1",
+        "internals tape risk_on supports long: +1",
+    ]
+
+
+def test_the_reasons_follow_table_order_with_mixed_signs():
+    result = tier(
+        side="short",
+        when=datetime(2026, 9, 25, 12, 0),
+        bounce_types="regime_break;ema_15",
+        sector_rrs_present=True,
+        tape="risk_off",
+    )
+    assert result["points"] == 4
+    assert result["reasons"] == [
+        "mid-session bar (hour 12): +1",
+        "bounce family: regime: +1",
+        "sector RRS present: +1",
+        "internals tape risk_off supports short: +1",
+    ]
+
+
+def test_three_aligned_facts_score_b():
+    result = tier(side="long", when=datetime(2026, 9, 25, 10, 30), sector_rrs_present=True, tape="risk_on")
+    assert (result["points"], result["tier"]) == (3, "B")
+
+
+def test_two_aligned_facts_score_c():
+    result = tier(side="long", when=datetime(2026, 9, 25, 10, 30), sector_rrs_present=True)
+    assert (result["points"], result["tier"]) == (2, "C")
+
+
+def test_one_aligned_fact_scores_d():
+    result = tier(side="long", when=datetime(2026, 9, 25, 10, 30))
+    assert (result["points"], result["tier"]) == (1, "D")
+
+
+def test_no_aligned_facts_score_d():
+    result = tier(side="long", when=datetime(2026, 9, 25, 15, 30), bounce_types=["vwap"], tape="mixed")
+    assert (result["points"], result["tier"]) == (0, "D")
+
+
+def test_conflicting_facts_can_reach_minus_three():
+    result = tier(
+        side="long",
+        when=datetime(2026, 9, 25, 9, 45),
+        bounce_types=["h1_green_to_yellow"],
+        tape="risk_off",
+    )
+    assert result["points"] == -3
+    assert result["tier"] == "D"
+    assert result["reasons"] == [
+        "opening bar (hour 9): -1",
+        "bounce family: h1_green_to_yellow: -1",
+        "sector RRS absent: 0",
+        "internals tape risk_off opposes long: -1",
+    ]
+
+
+def test_the_result_shape_is_tier_points_and_four_reasons():
+    result = tier()
+    assert set(result) == {"tier", "points", "reasons"}
+    assert result["tier"] in {"A", "B", "C", "D"}
+    assert len(result["reasons"]) == 4
+
+
+# --------------------------------------------------------------------------- the legacy hook
+def _learning_state():
+    from bounce_bot_lib import learning
+
+    def _row(dimension, direction, segment, n, avg_r):
+        return {
+            "dimension": dimension,
+            "direction": direction,
+            "segment": segment,
+            "sample_count": n,
+            "avg_close_r": avg_r,
+            "std_close_r": 1.0,
+            "session_count": 20,
+        }
+
+    return learning.build_learning_state([_row("bounce_type", "long", "regime_pause_rs", 400, 0.3)])
+
+
+def _aligned_row() -> dict:
+    return {
+        "market_environment": "",
+        "signal_time": "2026-09-25 10:15:00",
+        "bounce_types": "regime_pause_rs",
+        "rrs_sector": "XLK",
+        "internals_tape": "risk_on",
+    }
+
+
+ALIGNED_SETUP = {
+    "tier": "A",
+    "points": 4,
+    "reasons": [
+        "mid-session bar (hour 10): +1",
+        "bounce family: regime: +1",
+        "sector RRS present: +1",
+        "internals tape risk_on supports long: +1",
+    ],
+}
+
+
+def test_the_alert_dict_shows_the_setup_tier_and_keeps_the_learning_letter(monkeypatch):
+    from bounce_bot_lib import legacy, learning
+
+    state = _learning_state()
+    monkeypatch.setattr(learning, "load_bounce_learning_state", lambda path=None: state)
+    monkeypatch.setattr(learning, "structural_regime_on", lambda day: "")
+    row = _aligned_row()
+    quality = legacy.BounceBot._evaluate_bounce_alert_quality(legacy.BounceBot, "long", {"regime_pause_rs": 1.0}, row)
+
+    expected_learning = learning.evaluate_bounce_quality(
+        state,
+        direction="long",
+        bounce_types=["regime_pause_rs"],
+        time_bucket=learning.time_bucket_for(legacy._bounce_quality_time(row)),
+        market_environment="",
+        priority_bucket="",
+        focus_label="",
+        bounce_combo="regime_pause_rs",
+        setup_family="",
+    )
+    assert expected_learning["tier"] == "S"
+
+    shadow = quality.pop("shadow_s9")
+    assert shadow == {"tier": "S", "composite_r": 0.3}
+    assert quality.pop("tier") == "A"
+    assert quality.pop("learning_tier") == expected_learning.pop("tier")
+    assert quality.pop("setup_tier") == ALIGNED_SETUP
+    # mutes, mute_reasons, reasons, proven, proven_reasons, composite_r: untouched
+    assert quality == expected_learning
+
+
+def test_the_learning_fallback_still_carries_the_setup_tier(monkeypatch):
+    from bounce_bot_lib import legacy, learning
+
+    def _explode(path=None):
+        raise RuntimeError("state unreadable")
+
+    monkeypatch.setattr(learning, "load_bounce_learning_state", _explode)
+    quality = legacy.BounceBot._evaluate_bounce_alert_quality(legacy.BounceBot, "long", {"regime_pause_rs": 1.0}, _aligned_row())
+    assert quality["tier"] == "A"  # the rule's tier, from the event row alone
+    assert quality["learning_tier"] == "B"  # the fallback letter
+    assert quality["muted"] is False
+    assert quality["mute_reasons"] == []
+    assert quality["reasons"] == []
+    assert quality["setup_tier"]["points"] == 4
+    assert "shadow_s9" not in quality
+
+
+def test_a_rule_that_cannot_score_leaves_the_learning_verdict_untouched(monkeypatch):
+    from bounce_bot_lib import legacy, learning, setup_tier
+
+    state = _learning_state()
+    monkeypatch.setattr(learning, "load_bounce_learning_state", lambda path=None: state)
+    monkeypatch.setattr(learning, "structural_regime_on", lambda day: "")
+
+    def _broken(**kwargs):
+        raise RuntimeError("no facts")
+
+    monkeypatch.setattr(setup_tier, "evaluate_setup_tier", _broken)
+    quality = legacy.BounceBot._evaluate_bounce_alert_quality(legacy.BounceBot, "long", {"regime_pause_rs": 1.0}, _aligned_row())
+    assert quality["tier"] == "S"
+    assert quality["learning_tier"] == "S"
+    assert "setup_tier" not in quality
+    assert "shadow_s9" in quality
+
+
+# --------------------------------------------------------------------------- the recorded row
+def _tier_host(tmp_path):
+    import evidence_ledger as el
+
+    from bounce_bot_lib.legacy import BounceBot
+
+    class _Host:
+        pass
+
+    host = _Host.__new__(_Host)
+    host._outcome_ledger_obj = el.intraday_outcome_ledger(tmp_path)
+    host._outcome_ledger_failed = False
+    host._outcome_ledger = (lambda: host._outcome_ledger_obj)
+    host.record_alert_tier = BounceBot.record_alert_tier.__get__(host, _Host)
+    return host
+
+
+def test_the_recorded_tier_row_carries_the_learning_tier(tmp_path):
+    host = _tier_host(tmp_path)
+    host.record_alert_tier("eid", {"tier": "A", "learning_tier": "S", "muted": False, "proven": False})
+    rows = list(host._outcome_ledger_obj.read())
+    assert len(rows) == 1
+    assert rows[0]["event_type"] == "tier_assigned"
+    assert rows[0]["event_id"] == "eid"
+    assert rows[0]["tier"] == "A"
+    assert rows[0]["learning_tier"] == "S"
+
+
+def test_the_recorded_row_survives_a_verdict_without_a_learning_tier(tmp_path):
+    host = _tier_host(tmp_path)
+    host.record_alert_tier("eid", {"tier": "C", "muted": False})
+    rows = list(host._outcome_ledger_obj.read())
+    assert len(rows) == 1
+    assert rows[0]["tier"] == "C"
+    assert rows[0]["learning_tier"] == ""
```

# LEAD TEST RESULTS
## builder's own test command (exit 1)
```
E            +    where <built-in method width of PySide6.QtWidgets.QWidget object at 0x000001F34670CFC0> = <PySide6.QtWidgets.QWidget(0x1f3d53dfb20) at 0x000001F34670CFC0>.width
E            +  and   1036 = <built-in method width of PySide6.QtCore.QRect object at 0x000001F3472A6B40>()
E            +    where <built-in method width of PySide6.QtCore.QRect object at 0x000001F3472A6B40> = PySide6.QtCore.QRect(0, 39, 1036, 340).width

tests\test_tj1l_day_review_layout.py:355: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_tj1l_day_review_layout.py::test_the_name_chart_sits_beside_the_table_and_takes_the_rest
1 failed, 2121 passed, 5 subtests passed in 110.27s (0:01:50)
== chunk 8/8 (140 files)
bringing up nodes...
bringing up nodes...

........................................................................ [  3%]
........................................................................ [  7%]
........................................................................ [ 11%]
........................................................................ [ 14%]
........................................................................ [ 18%]
........................................................................ [ 22%]
........................................................................ [ 25%]
........................................................................ [ 29%]
........................................................................ [ 33%]
........................................................................ [ 37%]
........................................................................ [ 40%]
........................................................................ [ 44%]
........................................................................ [ 48%]
........................................................................ [ 51%]
........................................................................ [ 55%]
........................................................................ [ 59%]
........................................................................ [ 63%]
........................................................................ [ 66%]
........................................................................ [ 70%]
........................................................................ [ 74%]
........................................................................ [ 77%]
........................................................................ [ 81%]
........................................................................ [ 85%]
........................................................................ [ 89%]
........................................................................ [ 92%]
........................................................................ [ 96%]
...................................................................      [100%]
1939 passed in 92.48s (0:01:32)
```
## lint (exit 0)
```
All checks passed!
```
## hidden reference tests (exit 2)
```

=================================== ERRORS ====================================
____________ ERROR collecting tests/ref_test_s9_p14_tier_golden.py ____________
ImportError while importing test module 'C:\Users\Aaron\llm-harness\wt\qtm-4b830d0\tests\ref_test_s9_p14_tier_golden.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\ref_test_s9_p14_tier_golden.py:24: in <module>
    from bounce_bot_lib.setup_tier import setup_tier  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ImportError: cannot import name 'setup_tier' from 'bounce_bot_lib.setup_tier' (C:\Users\Aaron\llm-harness\wt\qtm-4b830d0\scripts\bounce_bot_lib\setup_tier.py)
________________ ERROR collecting tests/ref_test_setup_tier.py ________________
ImportError while importing test module 'C:\Users\Aaron\llm-harness\wt\qtm-4b830d0\tests\ref_test_setup_tier.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\ref_test_setup_tier.py:14: in <module>
    from bounce_bot_lib.setup_tier import setup_tier  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ImportError: cannot import name 'setup_tier' from 'bounce_bot_lib.setup_tier' (C:\Users\Aaron\llm-harness\wt\qtm-4b830d0\scripts\bounce_bot_lib\setup_tier.py)
____________ ERROR collecting tests/ref_test_setup_tier_golden.py _____________
ImportError while importing test module 'C:\Users\Aaron\llm-harness\wt\qtm-4b830d0\tests\ref_test_setup_tier_golden.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
..\..\..\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\Lib\importlib\__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\ref_test_setup_tier_golden.py:15: in <module>
    from bounce_bot_lib.setup_tier import setup_tier  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ImportError: cannot import name 'setup_tier' from 'bounce_bot_lib.setup_tier' (C:\Users\Aaron\llm-harness\wt\qtm-4b830d0\scripts\bounce_bot_lib\setup_tier.py)
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!
3 errors in 2.21s
```

# BUILDER SELF-REVIEW
```json
{
  "verdict": "GO",
  "blockers": [],
  "advisories": [
    "M5 alert text and the INTRADAY_BOUNCES_CSV tier column now carry the setup letter (A-D); the learning letter can no longer be S on an M5 alert - it lives beside it as learning_tier in the quality dict and the tier_assigned ledger row. Downstream letter rankers (evening catchup, away recap, tracker CSV) see the setup letter from the cutover on. Intended by the task, but the CSV column's meaning changes for rows written after the cutover while old rows keep the learning letter.",
    "The bar-hour fact is scored session-relative (opening hour -1, last hour 0, mid-session +1) instead of hard-coding NY hours 9/10-14/15. On a desk configured in the market-local zone these are identical; on a desk configured in another zone the bucketing shifts with the session window, exactly matching learning.time_bucket_for's naive/aware convention. Tests pin the zone via TRADINGBOT_MARKET_TIMEZONE.",
    "quality['setup_tier'] stores the same dict object the helper returned; nothing mutates it today, noted for the future.",
    "The golden seam test (test_s9_p14_tier_golden) now pins the bar-time expectation with the timezone env pinned to America/New_York; the learning verdict, mutes, reasons, proven floor and the whole message body are still asserted byte-identical - only the [X-TIER] prefix moves."
  ],
  "summary": "Diff does what the task asks: new pure rule scripts/bounce_bot_lib/setup_tier.py (four facts, +/-1 each, 4/3/2/1/0/-1 -> A/B/C/D, reasons in table order, unknown facts 0, when=None allowed, side case-insensitive, bounce types list-or-';'-string, regime beats h1_green_to_yellow, mixed tape 0); the legacy hook shows the setup tier as quality['tier'], keeps the learning letter as learning_tier, leaves muted/mute_reasons/shadow_s9/reasons/proven/composite untouched, falls back to learning_tier 'B' with the rule's tier when learning raises, and drops the setup_tier key entirely if the rule itself fails; record_alert_tier's tier_assigned row carries learning_tier additively. No order/sizing, mute-rule, learning.py or payload-key changes. Tests: 35 new (every table term, every boundary, reason order, hook incl. fallback and recorded row) plus the two pinned tests updated minimally. All four touched test files green (66 passed), neighboring learning-chain files green (85 passed), ruff check scripts tests green; exit codes checked."
}
```

# REFERENCE DIFF (the merged change, for comparison)
```diff
diff --git a/scripts/bounce_bot_lib/legacy.py b/scripts/bounce_bot_lib/legacy.py
index 9421e6d5..ffa4f409 100644
--- a/scripts/bounce_bot_lib/legacy.py
+++ b/scripts/bounce_bot_lib/legacy.py
@@ -4220,10 +4220,38 @@ class BounceBot(EWrapper, EClient):
             )
         except Exception as exc:  # learning must never block an alert
             logging.warning("Bounce learning evaluation failed (alerting anyway): %s", exc)
-            return {"tier": "B", "muted": False, "mute_reasons": [], "reasons": []}
-        quality["shadow_s9"] = self._shadow_s9_tier(state, context, when)
+            quality = {"tier": "B", "muted": False, "mute_reasons": [], "reasons": []}
+        else:
+            quality["shadow_s9"] = self._shadow_s9_tier(state, context, when)
+        # The shown letter is the setup tier; the learning letter is kept beside it.
+        quality["learning_tier"] = quality.get("tier", "B")
+        quality.update(self._setup_tier_fields(direction, levels, event_row))
         return quality
 
+    @staticmethod
+    def _setup_tier_fields(direction, levels, event_row) -> dict:
+        """Setup tier fields for the alert; `{}` on any failure so the alert still goes out."""
+        try:
+            from bounce_bot_lib.setup_tier import setup_tier
+
+            row = event_row if isinstance(event_row, dict) else {}
+            # The rule was measured on the bounce-bar hour, which only the event_id carries.
+            match = re.search(r"_(\d{8})_(\d{2})_(\d{2})_(\d{2})_", str(row.get("event_id") or ""))
+            if match:
+                when = datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S")
+            else:
+                when = _bounce_quality_time(row) or get_market_local_now()
+            return setup_tier(
+                bounce_types=_bounce_type_keys_from_levels(levels or {}),
+                direction=direction,
+                when=when,
+                rrs_sector=row.get("rrs_sector"),
+                internals_tape=row.get("internals_tape"),
+            )
+        except Exception as exc:
+            logging.warning("Setup tier failed (keeping the learning letter): %s", exc)
+            return {}
+
     @staticmethod
     def _shadow_s9_tier(state, context, when) -> dict:
         """S9 shadow tier, evidence only: `{}` on any failure, never read by a live decision."""
@@ -5453,6 +5481,8 @@ class BounceBot(EWrapper, EClient):
                     "proven": bool(verdict.get("proven")),
                     # S9 shadow tier beside the live one (evidence only).
                     "shadow_tier": str((verdict.get("shadow_s9") or {}).get("tier") or ""),
+                    # The learning letter kept beside the shown setup letter.
+                    "learning_tier": str(verdict.get("learning_tier") or ""),
                     # RETIRED 2026-09-01. The learning verdict has never
                     # carried this key, so the column has always been False;
                     # it is left in place unchanged so the tier_assigned row
diff --git a/scripts/bounce_bot_lib/setup_tier.py b/scripts/bounce_bot_lib/setup_tier.py
new file mode 100644
index 00000000..3bba312e
--- /dev/null
+++ b/scripts/bounce_bot_lib/setup_tier.py
@@ -0,0 +1,35 @@
+"""Setup tier (A/B/C/D) for M5 bounce alerts: bar hour, bounce family, sector RRS, tape vs side."""
+
+
+def setup_tier(*, bounce_types, direction, when, rrs_sector, internals_tape) -> dict:
+    """Return {"tier": "A"|"B"|"C"|"D", "setup_score": int, "setup_reasons": [str, ...]}."""
+    if isinstance(bounce_types, str):
+        bounce_types = bounce_types.split(";")
+    keys = {str(key).strip().lower() for key in bounce_types or ()}
+    side = str(direction or "").strip().lower()
+    tape = str(internals_tape or "").strip().lower()
+    terms = []
+    hour = getattr(when, "hour", None)
+    if hour in (7, 8):
+        terms.append((f"hour {hour:02d}", 2))
+    elif hour == 12:
+        terms.append(("hour 12", -2))
+    elif hour == 11:
+        terms.append(("hour 11", -1))
+    if "regime_pause_rs" in keys:
+        terms.append(("regime_pause_rs", 2))
+    elif "h1_green_to_yellow" in keys:
+        terms.append(("h1_green_to_yellow", -1))
+    if str(rrs_sector or "").strip() != "":
+        terms.append(("sector RRS", 1))
+    if side == "short" and tape == "risk_off":
+        terms.append(("short vs risk_off", 1))
+    elif side == "long" and tape in ("risk_on", "risk_on_tilt"):
+        terms.append((f"long vs {tape}", 1))
+    elif side == "long" and tape == "risk_off":
+        terms.append(("long vs risk_off", -1))
+    elif side == "short" and tape == "risk_on":
+        terms.append(("short vs risk_on", -1))
+    score = sum(points for _, points in terms)
+    tier = "A" if score >= 4 else "B" if score >= 2 else "C" if score >= 0 else "D"
+    return {"tier": tier, "setup_score": score, "setup_reasons": [f"{text} {points:+d}" for text, points in terms]}
diff --git a/tests/build_setup_tier_golden_fixture.py b/tests/build_setup_tier_golden_fixture.py
new file mode 100644
index 00000000..28c6278b
--- /dev/null
+++ b/tests/build_setup_tier_golden_fixture.py
@@ -0,0 +1,165 @@
+"""Build the setup-tier golden (`tests/fixtures/setup_tier_golden_v1.json`).
+
+    python tests/build_setup_tier_golden_fixture.py [intraday_bounce_candidates.csv]
+
+The source CSV is only READ (default: the live runtime copy). Nothing under `scripts/` is
+imported, so no live store can be written. Cases are `confirmed` rows from 2026-09 and
+2026-10, stratified so every bar hour 06..12 x bounce family (regime_pause_rs /
+h1_green_to_yellow / other) x sector RRS present/blank cell, and every internals tape x
+direction cell, is represented. ``expected`` comes from this script's OWN copy of the
+packet's rule table, never from `bounce_bot_lib.setup_tier`.
+"""
+
+from __future__ import annotations
+
+import csv
+import hashlib
+import json
+import random
+import re
+import sys
+from collections import defaultdict
+from datetime import datetime, timezone
+from pathlib import Path
+
+ROOT = Path(__file__).resolve().parents[1]
+FIXTURE = ROOT / "tests" / "fixtures" / "setup_tier_golden_v1.json"
+SOURCE = Path(r"C:\TradingBotData\data\runtime\intraday_bounce_candidates.csv")
+MONTHS = ("202609", "202610")
+PER_CELL = 7
+PER_TAPE_SIDE = 3
+BOTH_FAMILIES = 5
+SEED = "setup-tier-golden-v1"
+EVENT_TIME = re.compile(r"_(?:long|short)_(\d{8})_(\d{2})_(\d{2})_(\d{2})(?:_|$)", re.IGNORECASE)
+
+
+def rule(bounce_types: str, direction: str, when: datetime | None, rrs_sector: str, tape: str) -> dict:
+    """The packet's table, written out independently of the module under test."""
+    keys = {part.strip().lower() for part in str(bounce_types or "").split(";") if part.strip()}
+    side = str(direction or "").strip().lower()
+    tape = str(tape or "").strip().lower()
+    score = 0
+    if when is not None:
+        if when.hour in (7, 8):
+            score += 2
+        elif when.hour == 12:
+            score -= 2
+        elif when.hour == 11:
+            score -= 1
+    if "regime_pause_rs" in keys:
+        score += 2
+    elif "h1_green_to_yellow" in keys:
+        score -= 1
+    if str(rrs_sector or "").strip() != "":
+        score += 1
+    if side == "short" and tape == "risk_off":
+        score += 1
+    if side == "long" and tape in ("risk_on", "risk_on_tilt"):
+        score += 1
+    if side == "long" and tape == "risk_off":
+        score -= 1
+    if side == "short" and tape == "risk_on":
+        score -= 1
+    tier = "A" if score >= 4 else "B" if score >= 2 else "C" if score >= 0 else "D"
+    return {"tier": tier, "setup_score": score}
+
+
+def family(bounce_types: str) -> str:
+    keys = {part.strip().lower() for part in bounce_types.split(";")}
+    if "regime_pause_rs" in keys:
+        return "regime_pause_rs"
+    if "h1_green_to_yellow" in keys:
+        return "h1_green_to_yellow"
+    return "other"
+
+
+def main(argv: list[str]) -> int:
+    source = Path(argv[1]) if len(argv) > 1 else SOURCE
+    csv.field_size_limit(2**31 - 1)
+    pool: dict[str, dict] = {}
+    with source.open("r", encoding="utf-8", newline="") as handle:
+        for row in csv.DictReader(handle):
+            if row.get("event_type") != "confirmed":
+                continue
+            event_id = row.get("event_id") or ""
+            match = EVENT_TIME.search(event_id)
+            if not match or match.group(1)[:6] not in MONTHS or event_id in pool:
+                continue
+            day, hh, mm, ss = match.groups()
+            pool[event_id] = {
+                "event_id": event_id,
+                "direction": row.get("direction") or "",
+                "bounce_types": row.get("bounce_types") or "",
+                "rrs_sector": row.get("rrs_sector") or "",
+                "internals_tape": row.get("internals_tape") or "",
+                "when": f"{day[:4]}-{day[4:6]}-{day[6:]} {hh}:{mm}:{ss}",
+            }
+
+    cells: dict[tuple, list[str]] = defaultdict(list)
+    tape_sides: dict[tuple, list[str]] = defaultdict(list)
+    both: list[str] = []
+    for event_id in sorted(pool):
+        case = pool[event_id]
+        hour = int(case["when"][11:13])
+        rrs = case["rrs_sector"].strip() != ""
+        cells[(hour, family(case["bounce_types"]), rrs)].append(event_id)
+        tape_sides[(case["internals_tape"], case["direction"].lower())].append(event_id)
+        keys = {part.strip() for part in case["bounce_types"].split(";")}
+        if {"regime_pause_rs", "h1_green_to_yellow"} <= keys:
+            both.append(event_id)
+
+    rng = random.Random(SEED)
+    kept: set[str] = set()
+    for cell in sorted(cells, key=str):
+        ids = list(cells[cell])
+        rng.shuffle(ids)
+        kept.update(ids[:PER_CELL])
+    for cell in sorted(tape_sides, key=str):
+        have = [event_id for event_id in tape_sides[cell] if event_id in kept]
+        ids = [event_id for event_id in tape_sides[cell] if event_id not in kept]
+        rng.shuffle(ids)
+        kept.update(ids[:max(0, PER_TAPE_SIDE - len(have))])
+    rng.shuffle(both)
+    kept.update(both[:BOTH_FAMILIES])
+
+    cases = [pool[event_id] for event_id in sorted(kept)]
+    expected = {
+        case["event_id"]: rule(
+            case["bounce_types"],
+            case["direction"],
+            datetime.strptime(case["when"], "%Y-%m-%d %H:%M:%S"),
+            case["rrs_sector"],
+            case["internals_tape"],
+        )
+        for case in cases
+    }
+    last = max(case["when"] for case in cases)
+    payload = {
+        "schema": "setup_tier_golden_v1",
+        "feature_version": "bounce_bot_lib.setup_tier.setup_tier, first cut (trader, 2026-10-20): "
+                           "hour + family + sector RRS + tape vs side",
+        "universe_version": (f"{len(cases)} of {len(pool)} confirmed M5 bounce rows dated 2026-09/2026-10: "
+                             f"up to {PER_CELL} per hour x family x RRS cell, at least {PER_TAPE_SIDE} per "
+                             f"tape x side, up to {BOTH_FAMILIES} carrying both families, seed {SEED!r}"),
+        "provider_assumptions": "intraday_bounce_candidates.csv as logged by the live bot (read-only); "
+                                "bar time from the event_id, naive market-local",
+        "acquired_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
+        "as_of": f"{last[:10]}T{last[11:]}-07:00",
+        "raw_input_keys": ["cases"],
+        "expected_keys": ["expected"],
+        "numeric_tolerance": 0.0,
+        "intentional_difference": "",
+        "cases": cases,
+        "raw_input_sha256": hashlib.sha256(
+            json.dumps(cases, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
+        "expected": expected,
+    }
+    FIXTURE.write_text(json.dumps(payload, sort_keys=True, indent=1) + "\n", encoding="utf-8")
+    tiers = [value["tier"] for value in expected.values()]
+    print(FIXTURE, FIXTURE.stat().st_size, "cases", len(cases), "pool", len(pool),
+          {tier: tiers.count(tier) for tier in "ABCD"})
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main(sys.argv))
diff --git a/tests/test_s9_p14_tier_golden.py b/tests/test_s9_p14_tier_golden.py
index f67f94cf..da53fe82 100644
--- a/tests/test_s9_p14_tier_golden.py
+++ b/tests/test_s9_p14_tier_golden.py
@@ -21,6 +21,7 @@ if str(SCRIPTS_DIR) not in sys.path:
     sys.path.insert(0, str(SCRIPTS_DIR))
 
 from bounce_bot_lib import learning  # noqa: E402
+from bounce_bot_lib.setup_tier import setup_tier  # noqa: E402
 
 GOLDEN = load_fixture_contract("s9_p14_tier_golden_v1")
 STATE = GOLDEN["raw"]["learning_state"]
@@ -159,6 +160,11 @@ def test_the_bot_seam_keeps_live_tier_text_and_mutes_with_extreme_regime_segment
             legacy.BounceBot, inputs["direction"], levels, row
         )
         shadow = quality.pop("shadow_s9")
+        # The shown letter is the setup tier; the learning verdict this golden pins is `learning_tier`.
+        setup = setup_tier(bounce_types=legacy._bounce_type_keys_from_levels(levels), direction=inputs["direction"],
+                           when=legacy._bounce_quality_time(row), rrs_sector=None, internals_tape=None)
+        assert {key: quality.pop(key) for key in ("tier", "setup_score", "setup_reasons")} == setup, case["id"]
+        quality["tier"] = quality.pop("learning_tier")
         expected = EXPECTED[case["id"]]
         assert quality == expected["quality"], case["id"]  # tier, composite, mutes, reasons
         if quality.get("proven_reasons"):
diff --git a/tests/test_s9_shadow_tier.py b/tests/test_s9_shadow_tier.py
index 4c3e43ff..5a753b35 100644
--- a/tests/test_s9_shadow_tier.py
+++ b/tests/test_s9_shadow_tier.py
@@ -159,6 +159,10 @@ def test_alert_quality_carries_the_shadow_beside_the_unchanged_live_verdict(monk
         legacy.BounceBot, "long", {"vwap": 1.0}, row
     )
     shadow = quality.pop("shadow_s9")
+    # The shown letter is the setup tier (10:15, vwap, no RRS/tape = C); the learning letter sits beside it.
+    assert {key: quality.pop(key) for key in ("tier", "setup_score", "setup_reasons")} == {
+        "tier": "C", "setup_score": 0, "setup_reasons": []}
+    quality["tier"] = quality.pop("learning_tier")
     assert quality == learning.evaluate_bounce_quality(
         state,
         direction="long",
diff --git a/tests/test_setup_tier.py b/tests/test_setup_tier.py
new file mode 100644
index 00000000..5bec180b
--- /dev/null
+++ b/tests/test_setup_tier.py
@@ -0,0 +1,176 @@
+"""The setup tier (A/B/C/D): bar hour + bounce family + sector RRS + tape vs side."""
+
+import sys
+from datetime import datetime
+from pathlib import Path
+
+import pytest
+
+ROOT_DIR = Path(__file__).resolve().parents[1]
+SCRIPTS_DIR = ROOT_DIR / "scripts"
+if str(SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(SCRIPTS_DIR))
+
+from bounce_bot_lib.setup_tier import setup_tier  # noqa: E402
+
+NEUTRAL_HOUR = datetime(2026, 10, 15, 9, 35)
+
+
+def _tier(*, bounce_types=("vwap",), direction="long", when=NEUTRAL_HOUR, rrs_sector="", internals_tape="mixed"):
+    return setup_tier(
+        bounce_types=list(bounce_types) if not isinstance(bounce_types, str) else bounce_types,
+        direction=direction,
+        when=when,
+        rrs_sector=rrs_sector,
+        internals_tape=internals_tape,
+    )
+
+
+def _at(hour):
+    return datetime(2026, 10, 15, hour, 35)
+
+
+def test_a_neutral_alert_scores_zero_with_no_reasons():
+    assert _tier() == {"tier": "C", "setup_score": 0, "setup_reasons": []}
+
+
+@pytest.mark.parametrize("hour, score, reason", [(7, 2, "hour 07 +2"), (8, 2, "hour 08 +2"),
+                                                 (12, -2, "hour 12 -2"), (11, -1, "hour 11 -1")])
+def test_each_scored_hour_moves_the_score(hour, score, reason):
+    result = _tier(when=_at(hour))
+    assert result["setup_score"] == score
+    assert result["setup_reasons"] == [reason]
+
+
+@pytest.mark.parametrize("hour", [6, 9, 10])
+def test_the_other_session_hours_add_nothing(hour):
+    result = _tier(when=_at(hour))
+    assert result["setup_score"] == 0
+    assert result["setup_reasons"] == []
+
+
+def test_regime_pause_rs_adds_two():
+    result = _tier(bounce_types=["regime_pause_rs"])
+    assert result["setup_score"] == 2
+    assert result["setup_reasons"] == ["regime_pause_rs +2"]
+
+
+def test_h1_green_to_yellow_takes_one():
+    result = _tier(bounce_types=["h1_green_to_yellow", "vwap"])
+    assert result["setup_score"] == -1
+    assert result["setup_reasons"] == ["h1_green_to_yellow -1"]
+
+
+def test_regime_wins_over_h1_green_to_yellow_when_both_are_present():
+    result = _tier(bounce_types=["h1_green_to_yellow", "regime_pause_rs"])
+    assert result["setup_score"] == 2
+    assert result["setup_reasons"] == ["regime_pause_rs +2"]
+
+
+@pytest.mark.parametrize("rrs", [0.42, -2.9963174223479108, "-2.9963174223479108", "0.5"])
+def test_a_sector_rrs_value_adds_one(rrs):
+    result = _tier(rrs_sector=rrs)
+    assert result["setup_score"] == 1
+    assert result["setup_reasons"] == ["sector RRS +1"]
+
+
+@pytest.mark.parametrize("rrs", ["", "   ", None])
+def test_a_blank_sector_rrs_adds_nothing(rrs):
+    result = _tier(rrs_sector=rrs)
+    assert result["setup_score"] == 0
+    assert result["setup_reasons"] == []
+
+
+@pytest.mark.parametrize("direction, tape, score, reason", [
+    ("short", "risk_off", 1, "short vs risk_off +1"),
+    ("long", "risk_on", 1, "long vs risk_on +1"),
+    ("long", "risk_on_tilt", 1, "long vs risk_on_tilt +1"),
+    ("long", "risk_off", -1, "long vs risk_off -1"),
+    ("short", "risk_on", -1, "short vs risk_on -1"),
+])
+def test_each_tape_versus_side_term(direction, tape, score, reason):
+    result = _tier(direction=direction, internals_tape=tape)
+    assert result["setup_score"] == score
+    assert result["setup_reasons"] == [reason]
+
+
+@pytest.mark.parametrize("direction, tape", [
+    ("short", "risk_on_tilt"), ("long", "risk_off_tilt"), ("short", "risk_off_tilt"),
+    ("long", "mixed"), ("short", "mixed"), ("long", "unknown"), ("short", "unknown"),
+    ("long", ""), ("short", ""), ("long", None), ("short", "something_new"),
+])
+def test_the_other_tapes_are_neutral(direction, tape):
+    result = _tier(direction=direction, internals_tape=tape)
+    assert result["setup_score"] == 0
+    assert result["setup_reasons"] == []
+
+
+@pytest.mark.parametrize("facts, score, tier", [
+    ({"when": _at(7), "bounce_types": ["regime_pause_rs"]}, 4, "A"),
+    ({"when": _at(8), "rrs_sector": 0.3}, 3, "B"),
+    ({"bounce_types": ["regime_pause_rs"]}, 2, "B"),
+    ({"rrs_sector": 0.3}, 1, "C"),
+    ({}, 0, "C"),
+    ({"when": _at(11)}, -1, "D"),
+])
+def test_tier_boundaries(facts, score, tier):
+    result = _tier(**facts)
+    assert result["setup_score"] == score
+    assert result["tier"] == tier
+
+
+def test_the_best_and_worst_setups_and_their_reasons_in_table_order():
+    best = _tier(bounce_types="ema_15;regime_pause_rs;vwap", direction="short", when=_at(7),
+                 rrs_sector=1.25, internals_tape="risk_off")
+    assert best == {
+        "tier": "A",
+        "setup_score": 6,
+        "setup_reasons": ["hour 07 +2", "regime_pause_rs +2", "sector RRS +1", "short vs risk_off +1"],
+    }
+    worst = _tier(bounce_types=["h1_green_to_yellow"], direction="long", when=_at(12),
+                  rrs_sector="", internals_tape="risk_off")
+    assert worst == {
+        "tier": "D",
+        "setup_score": -4,
+        "setup_reasons": ["hour 12 -2", "h1_green_to_yellow -1", "long vs risk_off -1"],
+    }
+
+
+def test_the_score_is_a_plain_int():
+    score = _tier(when=_at(7))["setup_score"]
+    assert type(score) is int and score == 2
+
+
+@pytest.mark.parametrize("direction", ["LONG", "Long", " long "])
+def test_direction_is_case_insensitive(direction):
+    result = _tier(direction=direction, internals_tape="risk_on")
+    assert result["setup_score"] == 1
+    assert result["setup_reasons"] == ["long vs risk_on +1"]
+
+
+def test_short_direction_in_capitals():
+    assert _tier(direction="SHORT", internals_tape="risk_on")["setup_score"] == -1
+
+
+def test_no_time_adds_nothing_for_the_hour():
+    result = _tier(when=None, bounce_types=["regime_pause_rs"], rrs_sector=0.2)
+    assert result["setup_score"] == 3
+    assert result["tier"] == "B"
+    assert result["setup_reasons"] == ["regime_pause_rs +2", "sector RRS +1"]
+
+
+def test_a_csv_string_of_bounce_types_matches_the_key_list():
+    as_list = _tier(bounce_types=["ema_15", "ema_8", "regime_pause_rs"], when=_at(8))
+    as_text = _tier(bounce_types="ema_15; EMA_8 ;Regime_Pause_RS", when=_at(8))
+    assert as_text == as_list
+    assert as_text["setup_score"] == 4 and as_text["tier"] == "A"
+
+
+def test_h1_green_to_yellow_in_a_csv_string():
+    result = _tier(bounce_types="h1_green_to_yellow;vwap", when=_at(12))
+    assert result["setup_score"] == -3 and result["tier"] == "D"
+
+
+def test_empty_bounce_types_add_nothing():
+    assert _tier(bounce_types="")["setup_score"] == 0
+    assert _tier(bounce_types=[])["setup_score"] == 0
diff --git a/tests/test_setup_tier_golden.py b/tests/test_setup_tier_golden.py
new file mode 100644
index 00000000..7857d380
--- /dev/null
+++ b/tests/test_setup_tier_golden.py
@@ -0,0 +1,55 @@
+"""The setup tier on ~300 real confirmed M5 bounces (2026-09/10), frozen by its own rule copy."""
+
+import sys
+from collections import Counter
+from datetime import datetime
+from pathlib import Path
+
+from conftest import load_fixture_contract
+
+ROOT_DIR = Path(__file__).resolve().parents[1]
+SCRIPTS_DIR = ROOT_DIR / "scripts"
+if str(SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(SCRIPTS_DIR))
+
+from bounce_bot_lib.setup_tier import setup_tier  # noqa: E402
+
+GOLDEN = load_fixture_contract("setup_tier_golden_v1")
+
+
+def _run(case):
+    return setup_tier(
+        bounce_types=case["bounce_types"],
+        direction=case["direction"],
+        when=datetime.strptime(case["when"], "%Y-%m-%d %H:%M:%S"),
+        rrs_sector=case["rrs_sector"],
+        internals_tape=case["internals_tape"],
+    )
+
+
+def test_every_frozen_case_gets_its_frozen_tier_and_score():
+    expected = GOLDEN["expected"]
+    cases = GOLDEN["cases"]
+    assert len(cases) == len(expected) == 302
+    wrong = []
+    for case in cases:
+        result = _run(case)
+        got = {"tier": result["tier"], "setup_score": result["setup_score"]}
+        if got != expected[case["event_id"]]:
+            wrong.append((case["event_id"], got, expected[case["event_id"]]))
+    assert wrong == []
+
+
+def test_the_golden_covers_every_hour_family_rrs_and_tape():
+    cases = GOLDEN["cases"]
+    hours = Counter(int(case["when"][11:13]) for case in cases)
+    assert sorted(hours) == [6, 7, 8, 9, 10, 11, 12]
+    assert sum(1 for case in cases if "regime_pause_rs" in case["bounce_types"]) >= 20
+    assert sum(1 for case in cases if "h1_green_to_yellow" in case["bounce_types"]) >= 20
+    assert sum(1 for case in cases if case["rrs_sector"] == "") >= 100
+    assert sum(1 for case in cases if case["rrs_sector"] != "") >= 100
+    tapes = {case["internals_tape"] for case in cases}
+    assert tapes == {"risk_off", "risk_off_tilt", "risk_on", "risk_on_tilt", "mixed", "unknown", ""}
+    assert Counter(value["tier"] for value in GOLDEN["expected"].values()) == {
+        "A": 36, "B": 93, "C": 97, "D": 76,
+    }
diff --git a/tests/test_setup_tier_legacy_hook.py b/tests/test_setup_tier_legacy_hook.py
new file mode 100644
index 00000000..d09ed508
--- /dev/null
+++ b/tests/test_setup_tier_legacy_hook.py
@@ -0,0 +1,162 @@
+"""The alert's shown tier is the setup tier; the learning letter rides beside it as `learning_tier`."""
+
+import sys
+from pathlib import Path
+
+ROOT_DIR = Path(__file__).resolve().parents[1]
+SCRIPTS_DIR = ROOT_DIR / "scripts"
+if str(SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(SCRIPTS_DIR))
+
+import evidence_ledger as el  # noqa: E402
+from bounce_bot_lib import learning  # noqa: E402
+
+EVENT_ID = "AAPL_long_20261015_07_15_00_vwap"
+SETUP_KEYS = ("tier", "setup_score", "setup_reasons", "learning_tier", "shadow_s9")
+
+
+def _row(dimension, direction, segment, n, avg_r, std=1.0):
+    return {
+        "dimension": dimension,
+        "direction": direction,
+        "segment": segment,
+        "sample_count": n,
+        "avg_close_r": avg_r,
+        "std_close_r": std,
+        "session_count": 20,
+    }
+
+
+def _evaluate(monkeypatch, state, direction, levels, row):
+    from bounce_bot_lib import legacy
+
+    monkeypatch.setattr(learning, "load_bounce_learning_state", lambda path=None: state)
+    monkeypatch.setattr(learning, "structural_regime_on", lambda day: "")
+    return legacy, legacy.BounceBot._evaluate_bounce_alert_quality(legacy.BounceBot, direction, levels, row)
+
+
+def _learning_verdict(legacy, state, direction, keys, row):
+    return learning.evaluate_bounce_quality(
+        state,
+        direction=direction,
+        bounce_types=keys,
+        time_bucket=learning.time_bucket_for(legacy._bounce_quality_time(row)),
+        bounce_combo="+".join(keys),
+    )
+
+
+def test_the_shown_tier_is_the_setup_tier_and_the_learning_letter_is_kept(monkeypatch):
+    state = learning.build_learning_state([_row("bounce_type", "long", "vwap", 400, 0.3)])
+    row = {"market_environment": "", "signal_time": "2026-10-15 07:15:00",
+           "rrs_sector": 0.84, "internals_tape": "risk_on_tilt"}
+    legacy, quality = _evaluate(monkeypatch, state, "long", {"vwap": 1.0}, row)
+    live = _learning_verdict(legacy, state, "long", ["vwap"], row)
+    assert live["tier"] == "S"
+
+    assert quality["tier"] == "A"
+    assert quality["setup_score"] == 4
+    assert quality["setup_reasons"] == ["hour 07 +2", "sector RRS +1", "long vs risk_on_tilt +1"]
+    assert quality["learning_tier"] == "S"
+    assert quality["shadow_s9"] == {"tier": "S", "composite_r": 0.3}
+    rest = {key: value for key, value in quality.items() if key not in SETUP_KEYS}
+    assert rest == {key: value for key, value in live.items() if key != "tier"}
+
+
+def test_a_late_h1_green_to_yellow_long_into_risk_off_shows_d(monkeypatch):
+    state = learning.build_learning_state([_row("bounce_type", "long", "h1_green_to_yellow", 400, 0.3)])
+    row = {"market_environment": "", "signal_time": "2026-10-15 12:40:00",
+           "rrs_sector": "", "internals_tape": "risk_off"}
+    legacy, quality = _evaluate(monkeypatch, state, "long", {"h1_green_to_yellow": 101.5}, row)
+    assert quality["tier"] == "D"
+    assert quality["setup_score"] == -4
+    assert quality["setup_reasons"] == ["hour 12 -2", "h1_green_to_yellow -1", "long vs risk_off -1"]
+    assert quality["learning_tier"] == _learning_verdict(
+        legacy, state, "long", ["h1_green_to_yellow"], row)["tier"] == "S"
+
+
+def test_a_muted_learning_verdict_still_shows_the_setup_tier_and_stays_muted(monkeypatch):
+    state = learning.build_learning_state([_row("bounce_type", "short", "regime_pause_rs", 400, -0.5)])
+    row = {"market_environment": "", "signal_time": "2026-10-15 08:05:00",
+           "rrs_sector": -1.7, "internals_tape": "risk_off"}
+    legacy, quality = _evaluate(monkeypatch, state, "short", {"regime_pause_rs": 55.0}, row)
+    live = _learning_verdict(legacy, state, "short", ["regime_pause_rs"], row)
+    assert live["muted"] is True and live["tier"] == "D"
+
+    assert quality["tier"] == "A"
+    assert quality["setup_score"] == 6
+    assert quality["learning_tier"] == "D"
+    assert quality["muted"] is True
+    assert quality["mute_reasons"] == live["mute_reasons"] != []
+
+
+def test_a_learning_failure_keeps_b_as_the_learning_letter_and_shows_the_setup_tier(monkeypatch):
+    from bounce_bot_lib import legacy
+
+    def broken(path=None):
+        raise RuntimeError("state file unreadable")
+
+    monkeypatch.setattr(learning, "load_bounce_learning_state", broken)
+    row = {"market_environment": "", "signal_time": "2026-10-15 12:10:00",
+           "rrs_sector": "", "internals_tape": "risk_off"}
+    quality = legacy.BounceBot._evaluate_bounce_alert_quality(
+        legacy.BounceBot, "long", {"h1_green_to_yellow": 10.0}, row
+    )
+    assert quality["learning_tier"] == "B"
+    assert quality["tier"] == "D"
+    assert quality["setup_score"] == -4
+    assert quality["muted"] is False
+    assert quality["mute_reasons"] == []
+
+
+class _Host:
+    """A minimal host for `record_alert_tier`."""
+
+
+def _host(tmp_path):
+    from bounce_bot_lib.legacy import BounceBot
+
+    host = _Host.__new__(_Host)
+    host._outcome_ledger_obj = el.intraday_outcome_ledger(tmp_path)
+    host._outcome_ledger = lambda: host._outcome_ledger_obj
+    host.record_alert_tier = BounceBot.record_alert_tier.__get__(host, _Host)
+    return host
+
+
+def test_the_tier_ledger_row_carries_the_learning_letter_beside_the_shadow(tmp_path):
+    host = _host(tmp_path)
+    host.record_alert_tier(EVENT_ID, {"tier": "A", "learning_tier": "D", "muted": True, "proven": False,
+                                      "shadow_s9": {"tier": "C", "composite_r": -0.02}})
+    rows = list(host._outcome_ledger_obj.read())
+    assert len(rows) == 1
+    row = rows[0]
+    assert row["tier"] == "A"
+    assert row["learning_tier"] == "D"
+    assert row["shadow_tier"] == "C"
+    # The ledger stores keys sorted, so only "nothing dropped, one key added" is observable.
+    assert row["event_type"] == "tier_assigned" and row["event_id"] == EVENT_ID
+    assert row["muted"] is True and row["proven"] is False
+    assert row["banger"] is False and row["reason"] == ""
+
+
+def test_an_old_verdict_without_a_learning_letter_records_it_blank(tmp_path):
+    host = _host(tmp_path)
+    host.record_alert_tier(EVENT_ID, {"tier": "B", "learning_tier": None})
+    rows = list(host._outcome_ledger_obj.read())
+    assert len(rows) == 1
+    assert rows[0]["learning_tier"] == ""
+
+
+def test_the_setup_hour_comes_from_the_bounce_bar_in_the_event_id(monkeypatch):
+    # The rule was measured on the bounce-bar hour (event_id), not the confirmation bar (signal_time).
+    from datetime import datetime
+
+    from bounce_bot_lib.setup_tier import setup_tier
+
+    state = learning.build_learning_state([_row("bounce_type", "long", "vwap", 400, 0.3)])
+    row = {"market_environment": "", "event_id": "ABC_long_20261015_08_55_00_vwap",
+           "signal_time": "2026-10-15 09:05:00", "rrs_sector": "", "internals_tape": "mixed"}
+    _, quality = _evaluate(monkeypatch, state, "long", {"vwap": 1.0}, row)
+    expected = setup_tier(bounce_types=["vwap"], direction="long", when=datetime(2026, 10, 15, 8, 55),
+                          rrs_sector="", internals_tape="mixed")
+    assert (quality["tier"], quality["setup_score"]) == (expected["tier"], expected["setup_score"]) == ("B", 2)
+    assert quality["setup_reasons"] == ["hour 08 +2"]
```

## Lead note
Measured facts (the lead ran these; the builder did not see the reference):
- Builder: 1 pass, 202 turns, finished normally with its own self-review (GO).
- Own tests: tests/test_setup_tier.py 35 new, plus 2 pinned tests updated; all 4 touched test files pass (66). Whole suite under -n 4: 4 failures, all environmental (3 tests read git history this worktree lacks, 1 Qt layout test passes 29/29 in isolation).
- Hidden reference tests: 0/3 modules collect. All three `from bounce_bot_lib.setup_tier import setup_tier`; the builder named it `evaluate_setup_tier` with kwargs side/when/bounce_types/sector_rrs_present/tape and returns {tier, points, reasons}; the reference uses kwargs bounce_types/direction/when/rrs_sector/internals_tape and returns {tier, setup_score, setup_reasons}. The brief gave none of those names.
- The brief gave no point values per fact. The reference table is hour 7/8 +2, hour 12 -2, hour 11 -1, regime_pause_rs +2, h1_green_to_yellow -1, sector RRS +1, tape vs side +/-1, tiers A>=4 / B>=2 / C>=0 / D<0. The builder's table is +/-1 per fact with a session-relative bar hour and tiers 4->A, 3->B, 2->C, <=1->D. The brief said only "tier boundaries 4/3/2/1/0/-1 -> A/B/C/D".
- ruff clean. The .claude/agents/* and CLAUDE.md hunks are harness setup, not builder edits.
