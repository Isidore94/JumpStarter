# BRIEF
Goal: the "bounces failing" levels read must work for shorts too and say whether levels hold IN GENERAL, not just long bounces. The rolling D1/M5 readings gain support (approach side above) and resistance (below) sub-reads scored against side norms per session hour (m5_above/m5_below/d1_above/d1_below; derive or stub the norm table clearly); the pooled numbers and the "all" read stay unchanged. technicals_verdict returns LEVELS FAILING / LEVELS HOLDING / SUPPORT FAILING / RESISTANCE FAILING / LEVELS NORMAL / BUILDING: both sides scored decide, a fast tape overrides, a building side or an older snapshot without sub-reads falls back to the pooled M5 rule; BOUNCES FAILING/WORKING are gone. Chip "Levels: V · M5 sup n res n · D1 sup n res n · tape x", tooltip side lines after each pooled line. The Mentor int:levels row carries side keys and "; support n, resistance n" in its text, older snapshot text unchanged; the lens names the failing side and says "levels are holding" for the firm bucket.
Done when: tests cover the sub-reads, every verdict word, the fallback for old snapshots, the chip and Mentor text, and a trend hour (supports hold, resistances break) reads RESISTANCE FAILING end to end; run_tests.py/pytest and ruff green.
Files: scripts/technical_integrity.py (rolling readings, technicals_verdict, chip); find the Mentor int:levels row and the lens.
Don't touch: order/sizing code, the pooled numbers, the golden fixture's events and raw_input_sha256, other Mentor rows.
Pattern: the existing pooled M5/D1 read and its golden fixture tests (tests/test_technical_integrity_rolling.py).

# CANDIDATE DIFF
```diff
diff --git a/scripts/mentor_app/lens.py b/scripts/mentor_app/lens.py
index c8056a6..1e4e6cc 100644
--- a/scripts/mentor_app/lens.py
+++ b/scripts/mentor_app/lens.py
@@ -359,12 +359,25 @@ def _observe_levels(state: LensState, row: Mapping[str, Any], now: datetime) ->
         held, usual = row.get(f"{prefix}_held"), row.get(f"{prefix}_usual")
         numbers = (f", held {float(held):.2f} vs {float(usual):.2f} usual"
                    if held is not None and usual is not None else "")
-        if prefix == "d1":
-            what = ("daily SMAs and S/R are breaking more than usual for this hour" if bucket == "weak"
-                    else "daily SMAs and S/R are holding better than usual for this hour")
+        if bucket == "weak":
+            # Name the failing side from the row's side-state keys; both weak (or no side
+            # reads, i.e. an older snapshot) falls back to the generic wording.
+            weak = {"WEAK", "VERY WEAK"}
+            sup = str(row.get(f"{prefix}_support_state") or "")
+            res = str(row.get(f"{prefix}_resistance_state") or "")
+            generic = ("intraday levels are failing more than usual for this hour" if prefix == "m5"
+                       else "daily levels are failing more than usual for this hour")
+            side_label = f"{name} " if prefix == "m5" else "daily "
+            if sup in weak and res in weak:
+                what = generic
+            elif sup in weak:
+                what = f"{side_label}support is failing more than usual for this hour"
+            elif res in weak:
+                what = f"{side_label}resistance is failing more than usual for this hour"
+            else:
+                what = generic
         else:
-            what = ("bounces are failing more than usual for this hour" if bucket == "weak"
-                    else "bounces are holding better than usual for this hour")
+            what = "levels are holding"
         _add_level(state, key, f"{word} turned {level_state} ({name} now {score:.1f}{numbers}): {what}", now)
 
 
diff --git a/scripts/mentor_packs/internals_pack.py b/scripts/mentor_packs/internals_pack.py
index 993da01..bf809d8 100644
--- a/scripts/mentor_packs/internals_pack.py
+++ b/scripts/mentor_packs/internals_pack.py
@@ -541,6 +541,22 @@ def _levels_rows(src: Sources, now: datetime, session: str) -> list[dict[str, An
     m5 = rolling.get("m5") if isinstance(rolling.get("m5"), Mapping) else {}
     d1 = rolling.get("d1") if isinstance(rolling.get("d1"), Mapping) else {}
     every = rolling.get("all") if isinstance(rolling.get("all"), Mapping) else {}
+    m5_sup = m5.get("support") if isinstance(m5.get("support"), Mapping) else None
+    m5_res = m5.get("resistance") if isinstance(m5.get("resistance"), Mapping) else None
+    d1_sup = d1.get("support") if isinstance(d1.get("support"), Mapping) else None
+    d1_res = d1.get("resistance") if isinstance(d1.get("resistance"), Mapping) else None
+
+    def side_tests(row: Mapping[str, Any] | None) -> int:
+        return int(row.get("test_count") or 0) if row is not None else 0
+
+    def side_state(row: Mapping[str, Any] | None) -> str:
+        if row is None or row.get("score") is None:
+            return ""
+        return str(row.get("state") or "")
+
+    # Older snapshots have no sub-reads: 0 / "" keeps the row shape stable.
+    side_clause = (f"; support {side_tests(m5_sup)}, resistance {side_tests(m5_res)}"
+                   if m5_sup is not None and m5_res is not None else "")
     as_of = _start({"start": rolling.get("as_of")}, src.market_tz())
     age_min = _age(now, as_of) if as_of is not None else float("inf")
     stale = age_min > STALE_MINUTES
@@ -558,11 +574,16 @@ def _levels_rows(src: Sources, now: datetime, session: str) -> list[dict[str, An
         "m5_tests": int(m5.get("test_count") or 0), "d1_tests": int(d1.get("test_count") or 0),
         "m5_held": m5.get("observed_probability"), "m5_usual": m5.get("expected_probability"),
         "d1_held": d1.get("observed_probability"), "d1_usual": d1.get("expected_probability"),
+        "m5_support_tests": side_tests(m5_sup), "m5_resistance_tests": side_tests(m5_res),
+        "d1_support_tests": side_tests(d1_sup), "d1_resistance_tests": side_tests(d1_res),
+        "m5_support_state": side_state(m5_sup), "m5_resistance_state": side_state(m5_res),
+        "d1_support_state": side_state(d1_sup), "d1_resistance_state": side_state(d1_res),
         "as_of_utc": as_of.astimezone(timezone.utc).isoformat(timespec="seconds") if as_of else "",
         "stale": stale,
         "text": (f"Levels now (last {int(rolling.get('window_minutes') or 60)} min vs usual for this hour, "
-                 f"5.5 = normal): {verdict}. {_level_part('Intraday M5 levels', m5, tests_word=' tests')}; "
-                 f"{_level_part('D1 levels', d1, tests_word='')}; break pressure {every.get('pressure') or 'BALANCED'}. "
+                 f"5.5 = normal): {verdict}. {_level_part('Intraday M5 levels', m5, tests_word=' tests')}"
+                 f"{side_clause}; {_level_part('D1 levels', d1, tests_word='')}; "
+                 f"break pressure {every.get('pressure') or 'BALANCED'}. "
                  f"Today so far: D1 {day('d1_score')}, M5 {day('intraday_score')}." + tail),
     }
     tape = market.get("tape") if isinstance(market.get("tape"), Mapping) else {}
@@ -661,6 +682,12 @@ def fixture_technicals(*, session: str = "2026-10-02", as_of: str = "2026-10-02T
         return {"score": score, "state": state if score is not None else "BUILDING", "test_count": tests,
                 "observed_probability": held, "expected_probability": usual, "pressure": "BEARISH"}
 
+    m5_row = tf(m5[0], m5[1], 817, 0.52, 0.63)
+    m5_row["support"] = tf(m5[0], m5[1], 500, 0.52, 0.63)
+    m5_row["resistance"] = tf(m5[0], m5[1], 317, 0.52, 0.63)
+    d1_row = tf(d1[0], d1[1], 216, 0.66, 0.64)
+    d1_row["support"] = tf(d1[0], d1[1], 150, 0.66, 0.64)
+    d1_row["resistance"] = tf(d1[0], d1[1], 66, 0.66, 0.64)
     return {
         "schema": "technical_integrity_snapshot_v1",
         "session_date": session,
@@ -668,7 +695,7 @@ def fixture_technicals(*, session: str = "2026-10-02", as_of: str = "2026-10-02T
             "d1_score": 5.5, "intraday_score": 5.4,
             "rolling": {"schema": "technical_integrity_rolling_v1", "as_of": as_of, "window_minutes": 60,
                         "all": {"pressure": "BEARISH"},
-                        "m5": tf(m5[0], m5[1], 817, 0.52, 0.63), "d1": tf(d1[0], d1[1], 216, 0.66, 0.64)},
+                        "m5": m5_row, "d1": d1_row},
             "tape": dict(tape) if tape is not None else {
                 "schema": "technical_integrity_tape_light_v1", "source": "SPY", "light": "fast",
                 "range_mean": 0.1417, "expected_range": 0.0834, "ratio": 1.699},
diff --git a/scripts/technical_integrity.py b/scripts/technical_integrity.py
index d90ba87..f97df12 100644
--- a/scripts/technical_integrity.py
+++ b/scripts/technical_integrity.py
@@ -633,6 +633,23 @@ SESSION_HOUR_RESPECT_NORMS = {
     5: {"all": 0.764, "d1": 0.708, "m5": 0.784},
     6: {"all": 0.719, "m5": 0.719},
 }
+#: Side sub-read norms, keyed m5_above / m5_below / d1_above / d1_below. STUB: no measured
+#: per-side rates exist yet, so each side scores against its own timeframe's hour norm;
+#: replace the values with measured side-specific rates once the ledger has one-sided counts.
+def _side_norms(norms: dict[str, float]) -> dict[str, float]:
+    out: dict[str, float] = {}
+    if "m5" in norms:
+        out["m5_above"] = norms["m5"]
+        out["m5_below"] = norms["m5"]
+    if "d1" in norms:
+        out["d1_above"] = norms["d1"]
+        out["d1_below"] = norms["d1"]
+    return out
+
+
+SESSION_HOUR_SIDE_RESPECT_NORMS = {
+    hour: _side_norms(norms) for hour, norms in SESSION_HOUR_RESPECT_NORMS.items()
+}
 #: 1-10 scale for the residual: 5.5 = normal for this time of day, +/-0.15 = the ends.
 ROLLING_RESIDUAL_FULL_SCALE = 0.15
 #: NYSE TICK M5 high-low by session hour, same 25 sessions.
@@ -663,7 +680,13 @@ def _rolling_timeframe_reading(
     events: list[Mapping[str, Any]],
     tf_key: str,
     config: TechnicalIntegrityConfig,
+    side: str | None = None,
 ) -> dict[str, Any]:
+    # side: None = the pooled read (unchanged); "above" = support, "below" = resistance.
+    if side is not None:
+        events = [event for event in events if str(event.get("approach_side") or "") == side]
+    norm_table = SESSION_HOUR_SIDE_RESPECT_NORMS if side is not None else SESSION_HOUR_RESPECT_NORMS
+    norm_key = f"{tf_key}_{side}" if side is not None else tf_key
     observed_sum = expected_sum = weight_sum = 0.0
     test_count = chop_count = 0
     symbols: set[str] = set()
@@ -687,7 +710,7 @@ def _rolling_timeframe_reading(
                 continue
         touch = _as_market_local(event.get("touch_bar_start_local") or event.get("touch_bar_start"))
         hour = _session_hour_index(touch) if touch is not None else None
-        norm = SESSION_HOUR_RESPECT_NORMS.get(hour, {}).get(tf_key) if hour is not None else None
+        norm = norm_table.get(hour, {}).get(norm_key) if hour is not None else None
         if norm is None:
             continue
         observed_sum += weight * value
@@ -751,7 +774,12 @@ def rolling_technical_integrity(
         "window_minutes": int(window_minutes),
     }
     for tf_key, subset in by_tf.items():
-        result[tf_key] = _rolling_timeframe_reading(subset, tf_key, active_config)
+        row = _rolling_timeframe_reading(subset, tf_key, active_config)
+        if tf_key in ("d1", "m5"):
+            # Support = approach side "above", resistance = "below"; pooled and "all" stay unchanged.
+            row["support"] = _rolling_timeframe_reading(subset, tf_key, active_config, side="above")
+            row["resistance"] = _rolling_timeframe_reading(subset, tf_key, active_config, side="below")
+        result[tf_key] = row
     return result
 
 
@@ -2978,20 +3006,34 @@ _STATE_WORDS = {
     "STRONG": "strong",
 }
 _VERDICT_EXPLAINED = {
-    "BOUNCES FAILING": (
-        "BOUNCES FAILING = intraday levels are breaking more than usual for this hour, "
+    "LEVELS FAILING": (
+        "LEVELS FAILING = intraday levels are failing more than usual for this hour, "
         "or the tape is fast."
     ),
-    "BOUNCES WORKING": (
-        "BOUNCES WORKING = intraday levels are holding better than usual for this hour "
+    "LEVELS HOLDING": (
+        "LEVELS HOLDING = intraday levels are holding better than usual for this hour "
         "and the tape is not fast."
     ),
+    "SUPPORT FAILING": (
+        "SUPPORT FAILING = levels approached from above (support) are failing more than usual "
+        "for this hour."
+    ),
+    "RESISTANCE FAILING": (
+        "RESISTANCE FAILING = levels approached from below (resistance) are breaking more than "
+        "usual for this hour."
+    ),
     "LEVELS NORMAL": "LEVELS NORMAL = intraday levels are holding about as usual for this hour.",
 }
 
 
 def technicals_verdict(market: Mapping[str, Any] | None) -> str:
-    """One verdict from the rolling M5 state and the tape light; BUILDING with no D1/M5 score."""
+    """One verdict on whether levels hold in general.
+
+    Both M5 side sub-reads scored: a failing side names itself (weak words win over holding,
+    so a trend hour reads RESISTANCE FAILING); a fast tape overrides; a building side or an
+    older snapshot without sub-reads falls back to the pooled M5 state. BUILDING with no
+    D1/M5 score at all.
+    """
     market = market if isinstance(market, Mapping) else {}
     rolling = market.get("rolling") if isinstance(market.get("rolling"), Mapping) else {}
     d1 = rolling.get("d1") if isinstance(rolling.get("d1"), Mapping) else {}
@@ -3000,12 +3042,36 @@ def technicals_verdict(market: Mapping[str, Any] | None) -> str:
         return "BUILDING"
     tape = market.get("tape") if isinstance(market.get("tape"), Mapping) else {}
     light = str(tape.get("light") or "unknown") if tape.get("source") != "none" else "unknown"
+    if light == "fast":
+        # A missing tape reading counts as "not fast": missing data never downgrades a firm read.
+        return "LEVELS FAILING"
+    support = m5.get("support") if isinstance(m5.get("support"), Mapping) else None
+    resistance = m5.get("resistance") if isinstance(m5.get("resistance"), Mapping) else None
+    if (
+        support is not None
+        and support.get("score") is not None
+        and resistance is not None
+        and resistance.get("score") is not None
+    ):
+        sup_weak = str(support.get("state") or "") in {"WEAK", "VERY WEAK"}
+        res_weak = str(resistance.get("state") or "") in {"WEAK", "VERY WEAK"}
+        if sup_weak and res_weak:
+            return "LEVELS FAILING"
+        if sup_weak:
+            return "SUPPORT FAILING"
+        if res_weak:
+            return "RESISTANCE FAILING"
+        if (
+            str(support.get("state") or "") in {"FIRM", "STRONG"}
+            or str(resistance.get("state") or "") in {"FIRM", "STRONG"}
+        ):
+            return "LEVELS HOLDING"
+        return "LEVELS NORMAL"
     m5_state = str(m5.get("state") or "BUILDING") if m5.get("score") is not None else "BUILDING"
-    if m5_state in {"WEAK", "VERY WEAK"} or light == "fast":
-        return "BOUNCES FAILING"
-    # A missing tape reading counts as "not fast": missing data never downgrades a firm read.
+    if m5_state in {"WEAK", "VERY WEAK"}:
+        return "LEVELS FAILING"
     if m5_state in {"FIRM", "STRONG"}:
-        return "BOUNCES WORKING"
+        return "LEVELS HOLDING"
     return "LEVELS NORMAL"
 
 
@@ -3042,15 +3108,36 @@ def _rolling_now_view(
             f"break pressure {row.get('pressure')}; {counts}."
         )
 
+    m5_sup = m5.get("support") if isinstance(m5.get("support"), Mapping) else None
+    m5_res = m5.get("resistance") if isinstance(m5.get("resistance"), Mapping) else None
+    d1_sup = d1.get("support") if isinstance(d1.get("support"), Mapping) else None
+    d1_res = d1.get("resistance") if isinstance(d1.get("resistance"), Mapping) else None
+    m5_sides = m5_sup is not None and m5_res is not None
+    d1_sides = d1_sup is not None and d1_res is not None
+
+    def side_part(name: str, sup: Mapping[str, Any], res: Mapping[str, Any]) -> str:
+        return f"{name} sup {int(sup.get('test_count') or 0)} res {int(res.get('test_count') or 0)}"
+
     verdict = technicals_verdict(market)
-    chip = f"Levels: {verdict} · {part('M5', m5)} · {part('D1', d1)}"
+    if m5_sides:
+        chip = f"Levels: {verdict} · {side_part('M5', m5_sup, m5_res)}"
+        chip += f" · {side_part('D1', d1_sup, d1_res)}" if d1_sides else f" · {part('D1', d1)}"
+    else:
+        # Older snapshot without sub-reads: the pooled chip form.
+        chip = f"Levels: {verdict} · {part('M5', m5)} · {part('D1', d1)}"
     lines = [
         _VERDICT_EXPLAINED.get(verdict, verdict) + " 5.5 = normal for this hour.",
         f"Now = last {window} min of level tests vs the usual for this time of day. "
         "5.5 = normal for this hour.",
         line("D1", d1),
-        line("M5", m5),
     ]
+    if d1_sides:
+        lines.append(line("D1 support", d1_sup))
+        lines.append(line("D1 resistance", d1_res))
+    lines.append(line("M5", m5))
+    if m5_sides:
+        lines.append(line("M5 support", m5_sup))
+        lines.append(line("M5 resistance", m5_res))
     tape = market.get("tape") if isinstance(market.get("tape"), Mapping) else {}
     light = str(tape.get("light") or "unknown")
     source = str(tape.get("source") or "none")
diff --git a/tests/fixtures/technical_integrity_rolling_v1.json b/tests/fixtures/technical_integrity_rolling_v1.json
index e206ed0..70c45e1 100644
--- a/tests/fixtures/technical_integrity_rolling_v1.json
+++ b/tests/fixtures/technical_integrity_rolling_v1.json
@@ -572,7 +572,31 @@
       "resolved_weight": 12.5,
       "observed_probability": 0.53,
       "expected_probability": 0.641,
-      "residual": -0.111
+      "residual": -0.111,
+      "support": {
+       "score": 2.2,
+       "state": "VERY WEAK",
+       "pressure": "BEARISH",
+       "test_count": 5,
+       "chop_count": 1,
+       "symbol_count": 4,
+       "resolved_weight": 12.5,
+       "observed_probability": 0.53,
+       "expected_probability": 0.641,
+       "residual": -0.111
+      },
+      "resistance": {
+       "score": null,
+       "state": "BUILDING",
+       "pressure": "BALANCED",
+       "test_count": 0,
+       "chop_count": 0,
+       "symbol_count": 0,
+       "resolved_weight": 0.0,
+       "observed_probability": null,
+       "expected_probability": null,
+       "residual": null
+      }
      },
      "m5": {
       "score": 9.1,
@@ -584,7 +608,31 @@
       "resolved_weight": 10.0,
       "observed_probability": 0.8,
       "expected_probability": 0.6808,
-      "residual": 0.1192
+      "residual": 0.1192,
+      "support": {
+       "score": 10.0,
+       "state": "STRONG",
+       "pressure": "BALANCED",
+       "test_count": 4,
+       "chop_count": 2,
+       "symbol_count": 4,
+       "resolved_weight": 8.0,
+       "observed_probability": 1.0,
+       "expected_probability": 0.6725,
+       "residual": 0.3275
+      },
+      "resistance": {
+       "score": null,
+       "state": "BUILDING",
+       "pressure": "BULLISH",
+       "test_count": 1,
+       "chop_count": 0,
+       "symbol_count": 1,
+       "resolved_weight": 2.0,
+       "observed_probability": 0.0,
+       "expected_probability": 0.714,
+       "residual": -0.714
+      }
      }
     },
     "tick": {
@@ -610,14 +658,18 @@
      "range_mean": 566.7,
      "expected_range": 415.0
     },
-    "chip": "Levels: BOUNCES FAILING · M5 strong 9.1 · D1 very weak 2.2 · tape fast",
-    "chip_without_spy": "Levels: BOUNCES FAILING · M5 strong 9.1 · D1 very weak 2.2 · tape fast",
+    "chip": "Levels: LEVELS FAILING · M5 sup 4 res 1 · D1 sup 5 res 0 · tape fast",
+    "chip_without_spy": "Levels: LEVELS FAILING · M5 sup 4 res 1 · D1 sup 5 res 0 · tape fast",
     "tape_line_without_spy": "Tape (TICK fallback, last 30 min): range 567 vs 415 usual = fast.",
     "tooltip_head": [
-     "BOUNCES FAILING = intraday levels are breaking more than usual for this hour, or the tape is fast. 5.5 = normal for this hour.",
+     "LEVELS FAILING = intraday levels are failing more than usual for this hour, or the tape is fast. 5.5 = normal for this hour.",
      "Now = last 60 min of level tests vs the usual for this time of day. 5.5 = normal for this hour.",
      "D1 now 2.2/10 (VERY WEAK): levels held 0.53 of tests vs 0.64 usual at this hour; break pressure BEARISH; 5 decisive tests / 1 chop / 4 symbols.",
+     "D1 support now 2.2/10 (VERY WEAK): levels held 0.53 of tests vs 0.64 usual at this hour; break pressure BEARISH; 5 decisive tests / 1 chop / 4 symbols.",
+     "D1 resistance now building: not enough decisive tests in the last 60 min (0 decisive tests / 0 chop / 0 symbols).",
      "M5 now 9.1/10 (STRONG): levels held 0.80 of tests vs 0.68 usual at this hour; break pressure BULLISH; 5 decisive tests / 2 chop / 4 symbols.",
+     "M5 support now 10.0/10 (STRONG): levels held 1.00 of tests vs 0.67 usual at this hour; break pressure BALANCED; 4 decisive tests / 2 chop / 4 symbols.",
+     "M5 resistance now building: not enough decisive tests in the last 60 min (1 decisive tests / 0 chop / 1 symbols).",
      "Tape (SPY, last 30 min): M5 range 0.142% vs 0.083% usual = fast (levels fail more when the tape is fast; fast now also means weaker M5 levels next hour).",
      "Today so far:"
     ],
@@ -648,7 +700,31 @@
       "resolved_weight": 7.5,
       "observed_probability": 0.55,
       "expected_probability": 0.648,
-      "residual": -0.098
+      "residual": -0.098,
+      "support": {
+       "score": null,
+       "state": "BUILDING",
+       "pressure": "BALANCED",
+       "test_count": 2,
+       "chop_count": 0,
+       "symbol_count": 2,
+       "resolved_weight": 5.0,
+       "observed_probability": 0.825,
+       "expected_probability": 0.6455,
+       "residual": 0.1795
+      },
+      "resistance": {
+       "score": null,
+       "state": "BUILDING",
+       "pressure": "BULLISH",
+       "test_count": 1,
+       "chop_count": 0,
+       "symbol_count": 1,
+       "resolved_weight": 2.5,
+       "observed_probability": 0.0,
+       "expected_probability": 0.653,
+       "residual": -0.653
+      }
      },
      "m5": {
       "score": 1.5,
@@ -660,7 +736,31 @@
       "resolved_weight": 10.0,
       "observed_probability": 0.6,
       "expected_probability": 0.734,
-      "residual": -0.134
+      "residual": -0.134,
+      "support": {
+       "score": 1.5,
+       "state": "VERY WEAK",
+       "pressure": "BEARISH",
+       "test_count": 5,
+       "chop_count": 1,
+       "symbol_count": 4,
+       "resolved_weight": 10.0,
+       "observed_probability": 0.6,
+       "expected_probability": 0.734,
+       "residual": -0.134
+      },
+      "resistance": {
+       "score": null,
+       "state": "BUILDING",
+       "pressure": "BALANCED",
+       "test_count": 0,
+       "chop_count": 0,
+       "symbol_count": 0,
+       "resolved_weight": 0.0,
+       "observed_probability": null,
+       "expected_probability": null,
+       "residual": null
+      }
      }
     },
     "tick": {
@@ -672,7 +772,7 @@
      "light": "unknown",
      "reason": "no SPY bars in the window"
     },
-    "chip": "Levels: BOUNCES FAILING · M5 very weak 1.5 · D1 building"
+    "chip": "Levels: LEVELS FAILING · M5 sup 5 res 0 · D1 sup 2 res 1"
    },
    {
     "as_of": "2026-10-05T11:25:00-04:00",
diff --git a/tests/test_mentor_technicals_levels.py b/tests/test_mentor_technicals_levels.py
index d21f565..beb288c 100644
--- a/tests/test_mentor_technicals_levels.py
+++ b/tests/test_mentor_technicals_levels.py
@@ -31,12 +31,16 @@ def test_levels_and_tape_rows_for_the_fixture_snapshot():
     rows = _rows(ip.fixture())
     levels, tape = rows["int:levels"], rows["int:tape_speed"]
     assert levels["text"] == (
-        "Levels now (last 60 min vs usual for this hour, 5.5 = normal): BOUNCES FAILING. Intraday M5 levels weak "
-        "4.0 (held 0.52 of 817 tests vs 0.63 usual); D1 levels ok 5.4 (held 0.66 of 216 vs 0.64 usual); break "
-        "pressure BEARISH. Today so far: D1 5.5, M5 5.4."
+        "Levels now (last 60 min vs usual for this hour, 5.5 = normal): LEVELS FAILING. Intraday M5 levels weak "
+        "4.0 (held 0.52 of 817 tests vs 0.63 usual); support 500, resistance 317; D1 levels ok 5.4 "
+        "(held 0.66 of 216 vs 0.64 usual); break pressure BEARISH. Today so far: D1 5.5, M5 5.4."
     )
-    assert (levels["verdict"], levels["m5_state"], levels["d1_state"]) == ("BOUNCES FAILING", "WEAK", "MIXED")
+    assert (levels["verdict"], levels["m5_state"], levels["d1_state"]) == ("LEVELS FAILING", "WEAK", "MIXED")
     assert (levels["m5_tests"], levels["d1_tests"], levels["stale"]) == (817, 216, False)
+    assert (levels["m5_support_tests"], levels["m5_resistance_tests"]) == (500, 317)
+    assert (levels["m5_support_state"], levels["m5_resistance_state"]) == ("WEAK", "WEAK")
+    assert (levels["d1_support_tests"], levels["d1_resistance_tests"]) == (150, 66)
+    assert (levels["d1_support_state"], levels["d1_resistance_state"]) == ("MIXED", "MIXED")
     assert levels["as_of_utc"] == "2026-10-02T17:00:00+00:00"
     assert tape["text"] == (
         "Tape (SPY M5 range, last 30 min): fast - 0.142% vs 0.083% usual. A fast tape means intraday levels "
@@ -141,8 +145,8 @@ def test_m5_fires_on_entering_weak_leaving_weak_and_entering_firm_but_not_leavin
     assert state.pending == [] and state.m5_bucket == "ok", "the first bucket after the first hour is the baseline"
     state = _hold(state, 5, [_levels("WEAK", 4.0)])
     assert state.pending[0]["text"] == (
-        "Intraday levels turned WEAK (M5 now 4.0, held 0.52 vs 0.63 usual): bounces are failing more than usual "
-        "for this hour")
+        "Intraday levels turned WEAK (M5 now 4.0, held 0.52 vs 0.63 usual): intraday levels are failing more "
+        "than usual for this hour")
     state = lens.mark_posted(state, _at(20), "")
     state = _hold(state, 40, [_levels("MIXED", 4.8)])
     assert state.pending == [] and state.m5_bucket == "weak", "4.8 is inside the dead band: still weak"
@@ -156,6 +160,70 @@ def test_m5_fires_on_entering_weak_leaving_weak_and_entering_firm_but_not_leavin
     assert state.pending == [] and state.m5_bucket == "ok", "firm -> ok is silent"
 
 
+def _weak_m5_row(**side_states):
+    row = _levels("WEAK", 4.0)
+    row.update(side_states)
+    return row
+
+
+def test_lens_names_the_failing_side():
+    state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
+    state = _hold(state, 5, [_weak_m5_row(m5_support_state="MIXED", m5_resistance_state="VERY WEAK")])
+    assert state.pending[0]["text"] == (
+        "Intraday levels turned WEAK (M5 now 4.0, held 0.52 vs 0.63 usual): M5 resistance is failing more "
+        "than usual for this hour")
+
+    state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
+    state = _hold(state, 5, [_weak_m5_row(m5_support_state="VERY WEAK", m5_resistance_state="FIRM")])
+    assert state.pending[0]["text"] == (
+        "Intraday levels turned WEAK (M5 now 4.0, held 0.52 vs 0.63 usual): M5 support is failing more "
+        "than usual for this hour")
+
+    # Both sides weak falls back to the generic wording.
+    state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
+    state = _hold(state, 5, [_weak_m5_row(m5_support_state="WEAK", m5_resistance_state="WEAK")])
+    assert state.pending[0]["text"].endswith("intraday levels are failing more than usual for this hour")
+
+    # The daily side names its failing support.
+    d1_row = _levels("MIXED", 5.5, d1_state="WEAK", d1_score=4.1)
+    d1_row.update({"d1_support_state": "VERY WEAK", "d1_resistance_state": "FIRM"})
+    state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
+    state = _hold(state, 5, [d1_row])
+    assert state.pending[0]["text"] == (
+        "Daily levels turned WEAK (D1 now 4.1, held 0.60 vs 0.70 usual): daily support is failing more "
+        "than usual for this hour")
+
+
+def test_lens_firm_bucket_says_levels_are_holding():
+    state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
+    state = _hold(state, 5, [_levels("FIRM", 6.8)])
+    assert state.pending[0]["text"] == (
+        "Intraday levels turned FIRM (M5 now 6.8, held 0.52 vs 0.63 usual): levels are holding")
+
+    state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
+    state = _hold(state, 5, [_levels("MIXED", 5.5, d1_state="FIRM", d1_score=6.8)])
+    assert state.pending[0]["text"] == (
+        "Daily levels turned FIRM (D1 now 6.8, held 0.60 vs 0.70 usual): levels are holding")
+
+
+def test_older_snapshot_without_side_reads_keeps_its_text():
+    snap = ip.fixture_technicals(tape={"source": "SPY", "light": "normal", "range_mean": 0.08,
+                                       "expected_range": 0.08, "ratio": 1.0})
+    for row in (snap["market"]["rolling"]["m5"], snap["market"]["rolling"]["d1"]):
+        row.pop("support")
+        row.pop("resistance")
+    rows = _rows(ip.build(now=ip.FIXTURE_NOW, sources=ip.fixture_sources(technicals=snap)))
+    levels = rows["int:levels"]
+    assert levels["verdict"] == "LEVELS FAILING"  # pooled M5 rule, with the new words
+    assert levels["text"] == (
+        "Levels now (last 60 min vs usual for this hour, 5.5 = normal): LEVELS FAILING. Intraday M5 levels weak "
+        "4.0 (held 0.52 of 817 tests vs 0.63 usual); D1 levels ok 5.4 (held 0.66 of 216 vs 0.64 usual); break "
+        "pressure BEARISH. Today so far: D1 5.5, M5 5.4."
+    )
+    assert (levels["m5_support_tests"], levels["m5_resistance_tests"]) == (0, 0)
+    assert levels["m5_support_state"] == "" and levels["m5_resistance_state"] == ""
+
+
 def test_dwell_keeps_a_10_minute_wobble_silent_and_fires_a_15_minute_one():
     state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
     state = _hold(state, 5, [_levels("WEAK", 4.2)], minutes=10)
diff --git a/tests/test_technical_integrity_rolling.py b/tests/test_technical_integrity_rolling.py
index 6d540ec..fb21c20 100644
--- a/tests/test_technical_integrity_rolling.py
+++ b/tests/test_technical_integrity_rolling.py
@@ -176,8 +176,8 @@ def test_chip_omits_the_tape_when_the_source_is_none():
     chip, tooltip, _color = format_technical_integrity_snapshot(
         snapshot, now=datetime.fromisoformat(case["as_of"])
     )
-    # No tape reading counts as not fast: a STRONG M5 still reads "working".
-    assert chip == "Levels: BOUNCES WORKING · M5 strong 9.1 · D1 very weak 2.2"
+    # No tape reading counts as not fast: a STRONG M5 still reads as holding.
+    assert chip == "Levels: LEVELS HOLDING · M5 sup 4 res 1 · D1 sup 5 res 0"
     assert "Tape (last 30 min): unknown (no SPY bars provider)." in tooltip.splitlines()
 
 
@@ -403,11 +403,12 @@ def _verdict_market(m5_state, light, *, d1_scored=True):
 def test_technicals_verdict_table(m5_state, light):
     from technical_integrity import technicals_verdict
 
-    if m5_state in {"WEAK", "VERY WEAK"} or light == "fast":
-        expected = "BOUNCES FAILING"
+    # No side sub-reads in this market: the verdict falls back to the pooled M5 rule.
+    if light == "fast" or m5_state in {"WEAK", "VERY WEAK"}:
+        expected = "LEVELS FAILING"
     elif m5_state in {"FIRM", "STRONG"}:
         # Not fast is enough: an unknown or missing tape never downgrades a firm read.
-        expected = "BOUNCES WORKING"
+        expected = "LEVELS HOLDING"
     else:
         expected = "LEVELS NORMAL"
     assert technicals_verdict(_verdict_market(m5_state, light)) == expected
@@ -424,11 +425,164 @@ def test_technicals_verdict_building_without_any_rolling_score():
 def test_chip_words_and_verdict_lead():
     from technical_integrity import format_technical_integrity_snapshot
 
+    # An older snapshot without side sub-reads keeps the pooled chip form.
     market = _verdict_market("FIRM", "normal")
     market["rolling"]["m5"]["score"] = 6.8
     snapshot = {"session_date": "2026-10-05", "market": market}
     chip, tooltip, _ = format_technical_integrity_snapshot(
         snapshot, now=datetime.fromisoformat("2026-10-05T11:00:00-04:00")
     )
-    assert chip == "Levels: BOUNCES WORKING · M5 firm 6.8 · D1 ok 5.4 · tape normal"
-    assert tooltip.splitlines()[0].startswith("BOUNCES WORKING = ")
+    assert chip == "Levels: LEVELS HOLDING · M5 firm 6.8 · D1 ok 5.4 · tape normal"
+    assert tooltip.splitlines()[0].startswith("LEVELS HOLDING = ")
+
+
+def _side_state(score: float) -> str:
+    if score <= 3.0:
+        return "VERY WEAK"
+    if score <= 4.5:
+        return "WEAK"
+    if score < 6.5:
+        return "MIXED"
+    if score < 8.0:
+        return "FIRM"
+    return "STRONG"
+
+
+def _side_market(support, resistance, *, m5_state="MIXED", m5_score=5.0, light=None):
+    """A rolling market whose M5 row carries support/resistance sub-reads (None = absent)."""
+    m5 = {"score": m5_score, "state": m5_state}
+    if support is not None:
+        m5["support"] = {"score": support, "state": _side_state(support)}
+    if resistance is not None:
+        m5["resistance"] = {"score": resistance, "state": _side_state(resistance)}
+    market = {"rolling": {"m5": m5, "d1": {"score": 5.4, "state": "MIXED"}}}
+    if light is not None:
+        market["tape"] = {"source": "SPY", "light": light}
+    return market
+
+
+def test_technicals_verdict_side_reads_decide_when_both_sides_are_scored():
+    from technical_integrity import technicals_verdict
+
+    assert technicals_verdict(_side_market(2.0, 1.5)) == "LEVELS FAILING"
+    assert technicals_verdict(_side_market(2.0, 8.5)) == "SUPPORT FAILING"
+    # A trend hour: supports hold, resistances break.
+    assert technicals_verdict(_side_market(9.0, 1.5)) == "RESISTANCE FAILING"
+    assert technicals_verdict(_side_market(7.0, 9.0)) == "LEVELS HOLDING"
+    assert technicals_verdict(_side_market(5.0, 5.5)) == "LEVELS NORMAL"
+    # A fast tape overrides a holding pair of sides.
+    assert technicals_verdict(_side_market(9.0, 9.0, light="fast")) == "LEVELS FAILING"
+
+
+def test_technicals_verdict_falls_back_when_a_side_builds_or_is_missing():
+    from technical_integrity import technicals_verdict
+
+    building = {"score": None, "state": "BUILDING"}
+    m5 = {"score": 5.0, "state": "MIXED", "support": {"score": 9.0, "state": "STRONG"},
+          "resistance": building}
+    market = {"rolling": {"m5": m5, "d1": {"score": 5.4, "state": "MIXED"}}}
+    assert technicals_verdict(market) == "LEVELS NORMAL", "the pooled M5 state decides"
+
+    # An older snapshot without any side sub-reads: same pooled rule, new words.
+    assert technicals_verdict(_verdict_market("WEAK", "normal")) == "LEVELS FAILING"
+    assert technicals_verdict(_verdict_market("VERY WEAK", "fast")) == "LEVELS FAILING"
+    assert technicals_verdict(_verdict_market("FIRM", "unknown")) == "LEVELS HOLDING"
+    assert technicals_verdict(_verdict_market("MIXED", None)) == "LEVELS NORMAL"
+
+
+def test_chip_counts_the_decisive_tests_per_side_and_side_lines_follow_the_pooled_lines():
+    from technical_integrity import format_technical_integrity_snapshot
+
+    market = _side_market(2.0, 8.5)
+    market["rolling"]["m5"]["support"]["test_count"] = 4
+    market["rolling"]["m5"]["resistance"]["test_count"] = 1
+    d1 = market["rolling"]["d1"]
+    d1["support"] = {"score": 2.2, "state": "VERY WEAK", "test_count": 5}
+    d1["resistance"] = {"score": None, "state": "BUILDING", "test_count": 0}
+    snapshot = {"session_date": "2026-10-05", "market": market}
+    chip, tooltip, _ = format_technical_integrity_snapshot(
+        snapshot, now=datetime.fromisoformat("2026-10-05T11:00:00-04:00")
+    )
+    assert chip == "Levels: LEVELS FAILING · M5 sup 4 res 1 · D1 sup 5 res 0"
+    lines = tooltip.splitlines()
+    assert lines[2].startswith("D1 now ")
+    assert lines[3].startswith("D1 support now ") and lines[4].startswith("D1 resistance now ")
+    assert lines[5].startswith("M5 now ")
+    assert lines[6].startswith("M5 support now ") and lines[7].startswith("M5 resistance now ")
+
+
+def test_chip_keeps_the_pooled_d1_part_when_the_d1_row_has_no_side_reads():
+    from technical_integrity import format_technical_integrity_snapshot
+
+    market = _side_market(2.0, 8.5)
+    market["rolling"]["m5"]["support"]["test_count"] = 4
+    market["rolling"]["m5"]["resistance"]["test_count"] = 1
+    # No sub-reads on the D1 row: its chip part stays the pooled reading.
+    snapshot = {"session_date": "2026-10-05", "market": market}
+    chip, tooltip, _ = format_technical_integrity_snapshot(
+        snapshot, now=datetime.fromisoformat("2026-10-05T11:00:00-04:00")
+    )
+    assert chip == "Levels: LEVELS FAILING · M5 sup 4 res 1 · D1 ok 5.4"
+    assert not any(line.startswith("D1 support") for line in tooltip.splitlines())
+
+
+def _trend_events():
+    def event(event_id, touch, resolved, side, outcome, symbol="AMD", direction=""):
+        return {
+            "event_type": "level_resolved",
+            "event_id": event_id,
+            "session_date": "2026-10-02",
+            "touch_bar_start_local": f"2026-10-02T{touch}:00-04:00",
+            "resolved_at": f"2026-10-02T{resolved}:00-04:00",
+            "symbol": symbol,
+            "sector_key": "technology",
+            "industry_key": "semiconductors",
+            "level_family": "vwap",
+            "level_timeframe": "intraday",
+            "approach_side": side,
+            "outcome": outcome,
+            "break_direction": direction,
+            "event_weight": 2.0,
+        }
+
+    supports = [event(f"sup{i}", "11:35", "11:45", "above", "held", symbol="MU") for i in range(6)]
+    resistances = [event(f"res{i}", "11:35", "11:45", "below", "broke", symbol="NVDA",
+                         direction="up") for i in range(4)]
+    return supports + resistances
+
+
+def test_trend_hour_reads_resistance_failing_end_to_end():
+    """Supports hold and resistances break: RESISTANCE FAILING through rolling, chip and Mentor."""
+    from mentor_packs import internals_pack as ip
+    from technical_integrity import (
+        format_technical_integrity_snapshot,
+        rolling_technical_integrity,
+        technicals_verdict,
+    )
+
+    as_of = "2026-10-02T13:00:00-04:00"
+    rolling = rolling_technical_integrity(_trend_events(), as_of=as_of)
+    m5 = rolling["m5"]
+    assert m5["support"]["state"] == "STRONG", "all support tests held vs the hour norm"
+    assert m5["resistance"]["state"] == "VERY WEAK", "all resistance tests broke"
+
+    market = {"d1_score": 5.5, "intraday_score": 1.0, "rolling": rolling}
+    snapshot = {"session_date": "2026-10-02", "market": market}
+    assert technicals_verdict(market) == "RESISTANCE FAILING"
+    chip, tooltip, _ = format_technical_integrity_snapshot(
+        snapshot, now=datetime.fromisoformat(as_of)
+    )
+    assert chip == "Levels: RESISTANCE FAILING · M5 sup 6 res 4 · D1 sup 0 res 0"
+    assert tooltip.splitlines()[0].startswith("RESISTANCE FAILING = ")
+
+    snap_for_mentor = dict(snapshot)
+    snap_for_mentor["market"]["tape"] = {"source": "SPY", "light": "normal", "range_mean": 0.08,
+                                         "expected_range": 0.08, "ratio": 1.0}
+    rows = {row["id"]: row for row in
+            ip.build(now=ip.FIXTURE_NOW, sources=ip.fixture_sources(technicals=snap_for_mentor)).rows}
+    levels = rows["int:levels"]
+    assert levels["verdict"] == "RESISTANCE FAILING"
+    assert levels["m5_support_state"] == "STRONG" and levels["m5_resistance_state"] == "VERY WEAK"
+    assert (levels["m5_support_tests"], levels["m5_resistance_tests"]) == (6, 4)
+    assert "RESISTANCE FAILING." in levels["text"]
+    assert "; support 6, resistance 4;" in levels["text"]
```

# LEAD TEST RESULTS
## builder's own test command (exit 1)
```
                    # read() call run on child threads, with the timeout
                    # being done in a join() on those threads.  communicate()
                    # _after_ kill() is required to collect that and add it
                    # to the exception.
                    exc.stdout, exc.stderr = process.communicate()
                else:
                    # POSIX _communicate already populated the output so
                    # far into the TimeoutExpired exception.
                    process.wait()
                raise
            except:  # Including KeyboardInterrupt, communicate handled that.
                process.kill()
                # We don't call process.wait() as .__exit__ does that for us.
                raise
            retcode = process.poll()
            if check and retcode:
>               raise CalledProcessError(retcode, process.args,
                                         output=stdout, stderr=stderr)
E               subprocess.CalledProcessError: Command '['git', '-C', 'C:\\Users\\Aaron\\llm-harness\\wt\\qtm-51c27bf', 'show', '68b1fd7b:scripts/ai_jobs/setup_research.py']' returned non-zero exit status 128.

..\..\..\AppData\Roaming\uv\python\cpython-3.12-windows-x86_64-none\Lib\subprocess.py:571: CalledProcessError
============================== warnings summary ===============================
tests/test_earnings_anchor_bridge.py::BridgeToCsvTests::test_rerun_appends_nothing_and_a_new_anchor_appends_at_the_end
tests/test_earnings_anchor_bridge.py::BridgeToCsvTests::test_rows_land_in_the_csv_with_the_anchor_columns
  C:\Users\Aaron\llm-harness\wt\qtm-51c27bf\scripts\master_avwap_lib\legacy.py:17832: FutureWarning: The behavior of DataFrame concatenation with empty or all-NA entries is deprecated. In a future version, this will no longer exclude empty or all-NA columns when determining the result dtypes. To retain the old behavior, exclude the relevant entries before the concat operation.
    combined = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_evidence_snapshot.py::test_the_ops_scripts_are_versioned_here_and_installed_there
FAILED tests/test_qt_desk_layout.py::test_chart_pane_outgrows_the_alert_feed_in_its_column
FAILED tests/test_technical_integrity_rolling.py::test_chip_counts_the_decisive_tests_per_side_and_side_lines_follow_the_pooled_lines
FAILED tests/test_technical_integrity_rolling.py::test_chip_keeps_the_pooled_d1_part_when_the_d1_row_has_no_side_reads
FAILED tests/test_technical_integrity_rolling.py::test_trend_hour_reads_resistance_failing_end_to_end
FAILED tests/test_m5_strength_characterization.py::test_the_m5_formula_itself_has_not_been_edited
FAILED tests/test_market_read_inbox.py::test_regime_infer_reads_a_phone_doc_note_as_a_trader_note
FAILED tests/test_tj1l_day_review_layout.py::test_the_name_chart_sits_beside_the_table_and_takes_the_rest
FAILED tests/test_ws_rp_shared_report.py::test_n3s_narration_tests_are_byte_identical_to_the_branch_point
FAILED tests/test_ws_rp_shared_report.py::test_the_bounded_narration_view_itself_is_unchanged
10 failed, 16622 passed, 18 skipped, 2 warnings, 72 subtests passed in 971.36s (0:16:11)
```
## lint (exit 0)
```
All checks passed!
```
## hidden reference tests (exit 1)
```
FAILED tests/ref_test_mentor_technicals_levels.py::test_the_pack_and_the_chip_say_the_same_verdict[m50-m5_sides0-normal-SUPPORT FAILING-M5 sup 3.4 res 5.8]
FAILED tests/ref_test_mentor_technicals_levels.py::test_the_pack_and_the_chip_say_the_same_verdict[m51-m5_sides1-calm-RESISTANCE FAILING-M5 sup 5.9 res 3.9]
FAILED tests/ref_test_mentor_technicals_levels.py::test_the_pack_and_the_chip_say_the_same_verdict[m52-m5_sides2-normal-LEVELS FAILING-M5 sup 3.4 res 2.9]
FAILED tests/ref_test_mentor_technicals_levels.py::test_the_pack_and_the_chip_say_the_same_verdict[m53-m5_sides3-calm-LEVELS HOLDING-M5 sup 7.1 res 8.3]
FAILED tests/ref_test_mentor_technicals_levels.py::test_the_pack_and_the_chip_say_the_same_verdict[m54-m5_sides4-normal-LEVELS NORMAL-M5 sup 5.6 res 5.4]
FAILED tests/ref_test_mentor_technicals_levels.py::test_the_pack_and_the_chip_say_the_same_verdict[m55-m5_sides5-fast-LEVELS FAILING-M5 sup 7.1 res 8.3]
FAILED tests/ref_test_mentor_technicals_levels.py::test_the_pack_and_the_chip_say_the_same_verdict[m56-None-normal-LEVELS HOLDING-M5 sup building res building]
FAILED tests/ref_test_mentor_technicals_levels.py::test_m5_fires_on_entering_weak_leaving_weak_and_entering_firm_but_not_leaving_firm
FAILED tests/ref_test_mentor_technicals_levels.py::test_m5_weak_text_names_the_failing_side[row0-support and resistance are both failing more than usual for this hour]
FAILED tests/ref_test_mentor_technicals_levels.py::test_m5_weak_text_names_the_failing_side[row1-support is failing more than usual for this hour while resistance holds (the market, not the levels)]
FAILED tests/ref_test_mentor_technicals_levels.py::test_m5_weak_text_names_the_failing_side[row2-resistance is failing more than usual for this hour while support holds (the market, not the levels)]
FAILED tests/ref_test_mentor_technicals_levels.py::test_m5_weak_text_names_the_failing_side[row3-bounces are failing more than usual for this hour]
FAILED tests/ref_test_mentor_technicals_levels.py::test_m5_weak_text_names_the_failing_side[row4-bounces are failing more than usual for this hour]
FAILED tests/ref_test_mentor_technicals_levels.py::test_m5_firm_text_says_levels_are_holding
FAILED tests/ref_test_mentor_technicals_levels.py::test_the_pack_row_drives_the_lens_side_text
FAILED tests/ref_test_technical_integrity_rolling.py::test_rolling_now_reading_golden
FAILED tests/ref_test_technical_integrity_rolling.py::test_chip_and_tooltip_lead_with_the_now_reading_golden
FAILED tests/ref_test_technical_integrity_rolling.py::test_chip_omits_the_tape_when_the_source_is_none
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_reads_support_and_resistance[FIRM-MIXED-FIRM-normal-LEVELS NORMAL]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_reads_support_and_resistance[MIXED-STRONG-STRONG-calm-LEVELS NORMAL]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-WEAK-MIXED-FIRM]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-WEAK-MIXED-STRONG]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-WEAK-FIRM-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-WEAK-STRONG-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-MIXED-MIXED-FIRM]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-MIXED-MIXED-STRONG]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-MIXED-FIRM-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-MIXED-STRONG-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-FIRM-MIXED-FIRM]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-FIRM-MIXED-STRONG]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-FIRM-FIRM-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[calm-FIRM-STRONG-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-WEAK-MIXED-FIRM]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-WEAK-MIXED-STRONG]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-WEAK-FIRM-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-WEAK-STRONG-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-MIXED-MIXED-FIRM]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-MIXED-MIXED-STRONG]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-MIXED-FIRM-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-MIXED-STRONG-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-FIRM-MIXED-FIRM]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-FIRM-MIXED-STRONG]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-FIRM-FIRM-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_technicals_verdict_never_says_bounces_and_follows_the_side_rule[unknown-FIRM-STRONG-MIXED]
FAILED tests/ref_test_technical_integrity_rolling.py::test_tooltip_head_explains_each_verdict[WEAK-WEAK-WEAK-normal-LEVELS FAILING]
FAILED tests/ref_test_technical_integrity_rolling.py::test_tooltip_head_explains_each_verdict[FIRM-STRONG-FIRM-normal-LEVELS HOLDING]
FAILED tests/ref_test_technical_integrity_rolling.py::test_tooltip_head_explains_each_verdict[WEAK-MIXED-WEAK-normal-SUPPORT FAILING]
FAILED tests/ref_test_technical_integrity_rolling.py::test_tooltip_head_explains_each_verdict[MIXED-VERY WEAK-WEAK-normal-RESISTANCE FAILING]
FAILED tests/ref_test_technical_integrity_rolling.py::test_tooltip_head_explains_each_verdict[MIXED-FIRM-MIXED-normal-LEVELS NORMAL]
FAILED tests/ref_test_technical_integrity_rolling.py::test_chip_shows_both_sides_per_timeframe_and_the_tooltip_adds_side_lines
FAILED tests/ref_test_technical_integrity_rolling.py::test_chip_words_and_verdict_lead_for_an_older_snapshot_without_side_reads
FAILED tests/ref_test_technical_integrity_rolling.py::test_a_trend_hour_reads_resistance_failing_end_to_end
FAILED tests/ref_test_technical_integrity_rolling.py::test_each_side_is_scored_against_its_own_hour_norm[0]
FAILED tests/ref_test_technical_integrity_rolling.py::test_each_side_is_scored_against_its_own_hour_norm[1]
FAILED tests/ref_test_technical_integrity_rolling.py::test_each_side_is_scored_against_its_own_hour_norm[2]
FAILED tests/ref_test_technical_integrity_rolling.py::test_each_side_is_scored_against_its_own_hour_norm[3]
FAILED tests/ref_test_technical_integrity_rolling.py::test_each_side_is_scored_against_its_own_hour_norm[4]
FAILED tests/ref_test_technical_integrity_rolling.py::test_each_side_is_scored_against_its_own_hour_norm[5]
FAILED tests/ref_test_technical_integrity_rolling.py::test_each_side_is_scored_against_its_own_hour_norm[6]
62 failed, 397 passed in 6.58s
```

# BUILDER SELF-REVIEW
```json
(none)
```

# REFERENCE DIFF (the merged change, for comparison)
```diff
diff --git a/scripts/mentor_app/lens.py b/scripts/mentor_app/lens.py
index c8056a68..e95bbdc6 100644
--- a/scripts/mentor_app/lens.py
+++ b/scripts/mentor_app/lens.py
@@ -338,6 +338,19 @@ def _add_level(state: LensState, key: str, text: str, now: datetime) -> None:
     _add(state, key, text, now)
 
 
+def _m5_weak_what(support: str, resistance: str) -> str:
+    """Which side is failing when the M5 read turns weak; the generic text when a side is unknown."""
+    weak = {"WEAK", "VERY WEAK"}
+    if support and resistance:
+        if support in weak and resistance in weak:
+            return "support and resistance are both failing more than usual for this hour"
+        if support in weak:
+            return "support is failing more than usual for this hour while resistance holds (the market, not the levels)"
+        if resistance in weak:
+            return "resistance is failing more than usual for this hour while support holds (the market, not the levels)"
+    return "bounces are failing more than usual for this hour"
+
+
 def _observe_levels(state: LensState, row: Mapping[str, Any], now: datetime) -> None:
     if row.get("stale"):
         return
@@ -362,9 +375,10 @@ def _observe_levels(state: LensState, row: Mapping[str, Any], now: datetime) ->
         if prefix == "d1":
             what = ("daily SMAs and S/R are breaking more than usual for this hour" if bucket == "weak"
                     else "daily SMAs and S/R are holding better than usual for this hour")
+        elif bucket == "firm":
+            what = "levels are holding better than usual for this hour"
         else:
-            what = ("bounces are failing more than usual for this hour" if bucket == "weak"
-                    else "bounces are holding better than usual for this hour")
+            what = _m5_weak_what(str(row.get("m5_support_state") or ""), str(row.get("m5_resistance_state") or ""))
         _add_level(state, key, f"{word} turned {level_state} ({name} now {score:.1f}{numbers}): {what}", now)
 
 
diff --git a/scripts/mentor_packs/internals_pack.py b/scripts/mentor_packs/internals_pack.py
index 993da013..183e4e44 100644
--- a/scripts/mentor_packs/internals_pack.py
+++ b/scripts/mentor_packs/internals_pack.py
@@ -519,8 +519,21 @@ def _level_part(name: str, row: Mapping[str, Any], *, tests_word: str) -> str:
     if row.get("score") is None:
         return f"{name} building ({tests} decisive tests so far)"
     word = LEVEL_WORDS.get(str(row.get("state") or ""), "ok")
+    sides = ""
+    if isinstance(row.get("support"), Mapping) or isinstance(row.get("resistance"), Mapping):
+        sup, res = (_side(row, key)[0] for key in ("support", "resistance"))
+        sides = "; support {}, resistance {}".format(
+            *("building" if score is None else f"{float(score):.1f}" for score in (sup, res)))
     return (f"{name} {word} {float(row['score']):.1f} (held {float(row.get('observed_probability') or 0.0):.2f} "
-            f"of {tests}{tests_word} vs {float(row.get('expected_probability') or 0.0):.2f} usual)")
+            f"of {tests}{tests_word} vs {float(row.get('expected_probability') or 0.0):.2f} usual{sides})")
+
+
+def _side(row: Mapping[str, Any], key: str) -> tuple[Any, str]:
+    """(score, state) of one side sub-read; (None, "") when it is absent or unscored."""
+    side = row.get(key) if isinstance(row.get(key), Mapping) else {}
+    if side.get("score") is None:
+        return None, ""
+    return side.get("score"), str(side.get("state") or "")
 
 
 def _levels_rows(src: Sources, now: datetime, session: str) -> list[dict[str, Any]]:
@@ -555,6 +568,9 @@ def _levels_rows(src: Sources, now: datetime, session: str) -> list[dict[str, An
         "id": "int:levels", "kind": "levels", "verdict": verdict,
         "m5_score": m5.get("score"), "m5_state": str(m5.get("state") or "") if m5.get("score") is not None else "",
         "d1_score": d1.get("score"), "d1_state": str(d1.get("state") or "") if d1.get("score") is not None else "",
+        **{f"{tf}_{key}_{field}": value
+           for tf, row in (("m5", m5), ("d1", d1)) for key in ("support", "resistance")
+           for field, value in zip(("score", "state"), _side(row, key), strict=True)},
         "m5_tests": int(m5.get("test_count") or 0), "d1_tests": int(d1.get("test_count") or 0),
         "m5_held": m5.get("observed_probability"), "m5_usual": m5.get("expected_probability"),
         "d1_held": d1.get("observed_probability"), "d1_usual": d1.get("expected_probability"),
@@ -655,11 +671,20 @@ def fixture_sources(*, last: Mapping[str, float] | None = None, ticks: list[tupl
 
 def fixture_technicals(*, session: str = "2026-10-02", as_of: str = "2026-10-02T13:00:00-04:00",
                        m5: tuple[float | None, str] = (4.0, "WEAK"), d1: tuple[float | None, str] = (5.4, "MIXED"),
-                       tape: Mapping[str, Any] | None = None) -> dict[str, Any]:
-    """A Technical Integrity snapshot with a rolling block and a tape block (13:00 ET by default)."""
-    def tf(score: float | None, state: str, tests: int, held: float, usual: float) -> dict[str, Any]:
-        return {"score": score, "state": state if score is not None else "BUILDING", "test_count": tests,
-                "observed_probability": held, "expected_probability": usual, "pressure": "BEARISH"}
+                       tape: Mapping[str, Any] | None = None,
+                       m5_sides: Any = ((3.4, "WEAK", 400, 0.55, 0.63), (5.8, "MIXED", 417, 0.66, 0.65)),
+                       d1_sides: Any = ((4.1, "WEAK", 110, 0.60, 0.64), (6.0, "MIXED", 106, 0.66, 0.64)),
+                       ) -> dict[str, Any]:
+    """A Technical Integrity snapshot with a rolling block and a tape block (13:00 ET by default).
+
+    ``m5_sides`` / ``d1_sides`` are (support, resistance) as (score, state, tests, held, usual); None = no sub-reads.
+    """
+    def tf(score: float | None, state: str, tests: int, held: float, usual: float, sides: Any = None) -> dict[str, Any]:
+        out = {"score": score, "state": state if score is not None else "BUILDING", "test_count": tests,
+               "observed_probability": held, "expected_probability": usual, "pressure": "BEARISH"}
+        if sides is not None:
+            out["support"], out["resistance"] = (tf(*side) for side in sides)
+        return out
 
     return {
         "schema": "technical_integrity_snapshot_v1",
@@ -668,7 +693,8 @@ def fixture_technicals(*, session: str = "2026-10-02", as_of: str = "2026-10-02T
             "d1_score": 5.5, "intraday_score": 5.4,
             "rolling": {"schema": "technical_integrity_rolling_v1", "as_of": as_of, "window_minutes": 60,
                         "all": {"pressure": "BEARISH"},
-                        "m5": tf(m5[0], m5[1], 817, 0.52, 0.63), "d1": tf(d1[0], d1[1], 216, 0.66, 0.64)},
+                        "m5": tf(m5[0], m5[1], 817, 0.52, 0.63, m5_sides),
+                        "d1": tf(d1[0], d1[1], 216, 0.66, 0.64, d1_sides)},
             "tape": dict(tape) if tape is not None else {
                 "schema": "technical_integrity_tape_light_v1", "source": "SPY", "light": "fast",
                 "range_mean": 0.1417, "expected_range": 0.0834, "ratio": 1.699},
diff --git a/scripts/technical_integrity.py b/scripts/technical_integrity.py
index d90ba87a..b70d4a0e 100644
--- a/scripts/technical_integrity.py
+++ b/scripts/technical_integrity.py
@@ -633,6 +633,21 @@ SESSION_HOUR_RESPECT_NORMS = {
     5: {"all": 0.764, "d1": 0.708, "m5": 0.784},
     6: {"all": 0.719, "m5": 0.719},
 }
+#: Per-side norms: "_above" = support (price fell into the level), "_below" = resistance.
+#: Measured 25 sessions ending 2026-10-09; hour 6 has no D1 side norms.
+_SIDE_NORMS = {
+    0: (0.633, 0.645, 0.642, 0.637),
+    1: (0.714, 0.727, 0.655, 0.631),
+    2: (0.815, 0.718, 0.804, 0.611),
+    3: (0.775, 0.788, 0.720, 0.747),
+    4: (0.785, 0.806, 0.712, 0.804),
+    5: (0.781, 0.784, 0.699, 0.733),
+    6: (0.676, 0.758, None, None),
+}
+for _hour, _sides in _SIDE_NORMS.items():
+    for _key, _norm in zip(("m5_above", "m5_below", "d1_above", "d1_below"), _sides, strict=True):
+        if _norm is not None:
+            SESSION_HOUR_RESPECT_NORMS[_hour][_key] = _norm
 #: 1-10 scale for the residual: 5.5 = normal for this time of day, +/-0.15 = the ends.
 ROLLING_RESIDUAL_FULL_SCALE = 0.15
 #: NYSE TICK M5 high-low by session hour, same 25 sessions.
@@ -752,6 +767,13 @@ def rolling_technical_integrity(
     }
     for tf_key, subset in by_tf.items():
         result[tf_key] = _rolling_timeframe_reading(subset, tf_key, active_config)
+        if tf_key != "all":
+            for side, approach in (("support", "above"), ("resistance", "below")):
+                result[tf_key][side] = _rolling_timeframe_reading(
+                    [event for event in subset if event.get("approach_side") == approach],
+                    f"{tf_key}_{approach}",
+                    active_config,
+                )
     return result
 
 
@@ -2970,28 +2992,42 @@ def _integrity_color(headline_pressure: str, headline_state: str) -> str:
     return "#c9d1d9"
 
 
-_STATE_WORDS = {
-    "VERY WEAK": "very weak",
-    "WEAK": "weak",
-    "MIXED": "ok",
-    "FIRM": "firm",
-    "STRONG": "strong",
-}
 _VERDICT_EXPLAINED = {
-    "BOUNCES FAILING": (
-        "BOUNCES FAILING = intraday levels are breaking more than usual for this hour, "
+    "LEVELS FAILING": (
+        "LEVELS FAILING = both support and resistance are breaking more than usual for this hour, "
         "or the tape is fast."
     ),
-    "BOUNCES WORKING": (
-        "BOUNCES WORKING = intraday levels are holding better than usual for this hour "
+    "LEVELS HOLDING": (
+        "LEVELS HOLDING = both support and resistance are holding better than usual for this hour "
         "and the tape is not fast."
     ),
+    "SUPPORT FAILING": (
+        "SUPPORT FAILING = support is breaking more than usual for this hour while resistance is not: "
+        "the market is pressing down, the levels still work."
+    ),
+    "RESISTANCE FAILING": (
+        "RESISTANCE FAILING = resistance is breaking more than usual for this hour while support is not: "
+        "the market is pressing up, the levels still work."
+    ),
     "LEVELS NORMAL": "LEVELS NORMAL = intraday levels are holding about as usual for this hour.",
 }
+_WEAK_STATES = {"WEAK", "VERY WEAK"}
+_FIRM_STATES = {"FIRM", "STRONG"}
+
+
+def _scored_state(row: Any) -> str:
+    """The row's state when it has a score, else BUILDING (also for a missing row)."""
+    if not isinstance(row, Mapping) or row.get("score") is None:
+        return "BUILDING"
+    return str(row.get("state") or "BUILDING")
 
 
 def technicals_verdict(market: Mapping[str, Any] | None) -> str:
-    """One verdict from the rolling M5 state and the tape light; BUILDING with no D1/M5 score."""
+    """One verdict from the rolling M5 support/resistance states and the tape light.
+
+    BUILDING with no D1/M5 score; a fast tape fails the levels; with both M5 sides scored the
+    sides decide, else the pooled M5 state does (a side still building, or an older snapshot).
+    """
     market = market if isinstance(market, Mapping) else {}
     rolling = market.get("rolling") if isinstance(market.get("rolling"), Mapping) else {}
     d1 = rolling.get("d1") if isinstance(rolling.get("d1"), Mapping) else {}
@@ -3000,12 +3036,26 @@ def technicals_verdict(market: Mapping[str, Any] | None) -> str:
         return "BUILDING"
     tape = market.get("tape") if isinstance(market.get("tape"), Mapping) else {}
     light = str(tape.get("light") or "unknown") if tape.get("source") != "none" else "unknown"
-    m5_state = str(m5.get("state") or "BUILDING") if m5.get("score") is not None else "BUILDING"
-    if m5_state in {"WEAK", "VERY WEAK"} or light == "fast":
-        return "BOUNCES FAILING"
+    if light == "fast":
+        return "LEVELS FAILING"
     # A missing tape reading counts as "not fast": missing data never downgrades a firm read.
-    if m5_state in {"FIRM", "STRONG"}:
-        return "BOUNCES WORKING"
+    sup = _scored_state(m5.get("support"))
+    res = _scored_state(m5.get("resistance"))
+    if sup != "BUILDING" and res != "BUILDING":
+        if sup in _WEAK_STATES and res in _WEAK_STATES:
+            return "LEVELS FAILING"
+        if sup in _FIRM_STATES and res in _FIRM_STATES:
+            return "LEVELS HOLDING"
+        if sup in _WEAK_STATES:
+            return "SUPPORT FAILING"
+        if res in _WEAK_STATES:
+            return "RESISTANCE FAILING"
+        return "LEVELS NORMAL"
+    m5_state = _scored_state(m5)
+    if m5_state in _WEAK_STATES:
+        return "LEVELS FAILING"
+    if m5_state in _FIRM_STATES:
+        return "LEVELS HOLDING"
     return "LEVELS NORMAL"
 
 
@@ -3022,11 +3072,34 @@ def _rolling_now_view(
         return None
     window = int(rolling.get("window_minutes") or ROLLING_WINDOW_MINUTES)
 
+    def side_score(row: Any) -> str:
+        if not isinstance(row, Mapping) or row.get("score") is None:
+            return "building"
+        return f"{float(row['score']):.1f}"
+
     def part(name: str, row: Mapping[str, Any]) -> str:
         if row.get("score") is None:
             return f"{name} building"
-        word = _STATE_WORDS.get(str(row.get("state") or ""), "ok")
-        return f"{name} {word} {float(row['score']):.1f}"
+        return f"{name} sup {side_score(row.get('support'))} res {side_score(row.get('resistance'))}"
+
+    def side_part(row: Any) -> str:
+        row = row if isinstance(row, Mapping) else {}
+        tests = int(row.get("test_count") or 0)
+        if row.get("score") is None:
+            return f"building ({tests} decisive tests)"
+        return (
+            f"{float(row['score']):.1f} ({row.get('state')}), held "
+            f"{float(row.get('observed_probability') or 0.0):.2f} of {tests} tests vs "
+            f"{float(row.get('expected_probability') or 0.0):.2f} usual"
+        )
+
+    def side_lines(name: str, row: Mapping[str, Any]) -> list[str]:
+        if row.get("score") is None:
+            return []
+        return [
+            f"{name} sides: support {side_part(row.get('support'))}; "
+            f"resistance {side_part(row.get('resistance'))}."
+        ]
 
     def line(name: str, row: Mapping[str, Any]) -> str:
         counts = (
@@ -3049,7 +3122,9 @@ def _rolling_now_view(
         f"Now = last {window} min of level tests vs the usual for this time of day. "
         "5.5 = normal for this hour.",
         line("D1", d1),
+        *side_lines("D1", d1),
         line("M5", m5),
+        *side_lines("M5", m5),
     ]
     tape = market.get("tape") if isinstance(market.get("tape"), Mapping) else {}
     light = str(tape.get("light") or "unknown")
diff --git a/tests/test_mentor_technicals_levels.py b/tests/test_mentor_technicals_levels.py
index d21f565b..564640c4 100644
--- a/tests/test_mentor_technicals_levels.py
+++ b/tests/test_mentor_technicals_levels.py
@@ -31,11 +31,15 @@ def test_levels_and_tape_rows_for_the_fixture_snapshot():
     rows = _rows(ip.fixture())
     levels, tape = rows["int:levels"], rows["int:tape_speed"]
     assert levels["text"] == (
-        "Levels now (last 60 min vs usual for this hour, 5.5 = normal): BOUNCES FAILING. Intraday M5 levels weak "
-        "4.0 (held 0.52 of 817 tests vs 0.63 usual); D1 levels ok 5.4 (held 0.66 of 216 vs 0.64 usual); break "
-        "pressure BEARISH. Today so far: D1 5.5, M5 5.4."
+        "Levels now (last 60 min vs usual for this hour, 5.5 = normal): LEVELS FAILING. Intraday M5 levels weak "
+        "4.0 (held 0.52 of 817 tests vs 0.63 usual; support 3.4, resistance 5.8); D1 levels ok 5.4 (held 0.66 of "
+        "216 vs 0.64 usual; support 4.1, resistance 6.0); break pressure BEARISH. Today so far: D1 5.5, M5 5.4."
     )
-    assert (levels["verdict"], levels["m5_state"], levels["d1_state"]) == ("BOUNCES FAILING", "WEAK", "MIXED")
+    assert (levels["verdict"], levels["m5_state"], levels["d1_state"]) == ("LEVELS FAILING", "WEAK", "MIXED")
+    assert (levels["m5_support_score"], levels["m5_support_state"]) == (3.4, "WEAK")
+    assert (levels["m5_resistance_score"], levels["m5_resistance_state"]) == (5.8, "MIXED")
+    assert (levels["d1_support_score"], levels["d1_support_state"]) == (4.1, "WEAK")
+    assert (levels["d1_resistance_score"], levels["d1_resistance_state"]) == (6.0, "MIXED")
     assert (levels["m5_tests"], levels["d1_tests"], levels["stale"]) == (817, 216, False)
     assert levels["as_of_utc"] == "2026-10-02T17:00:00+00:00"
     assert tape["text"] == (
@@ -63,6 +67,35 @@ def test_tick_fallback_building_and_stale_wording():
     assert rows["int:levels"]["stale"] and "STALE, 43 min old" in rows["int:levels"]["text"]
 
 
+def test_an_older_snapshot_without_side_reads_keeps_todays_text():
+    snap = ip.fixture_technicals(m5_sides=None, d1_sides=None)
+    levels = _rows(ip.build(now=ip.FIXTURE_NOW, sources=ip.fixture_sources(technicals=snap)))["int:levels"]
+    assert levels["text"] == (
+        "Levels now (last 60 min vs usual for this hour, 5.5 = normal): LEVELS FAILING. Intraday M5 levels weak "
+        "4.0 (held 0.52 of 817 tests vs 0.63 usual); D1 levels ok 5.4 (held 0.66 of 216 vs 0.64 usual); break "
+        "pressure BEARISH. Today so far: D1 5.5, M5 5.4."
+    )
+    for key in ("m5_support", "m5_resistance", "d1_support", "d1_resistance"):
+        assert (levels[f"{key}_score"], levels[f"{key}_state"]) == (None, "")
+
+
+def test_a_building_side_reads_building_in_the_row():
+    snap = ip.fixture_technicals(
+        m5=(5.9, "MIXED"),
+        m5_sides=((None, "BUILDING", 3, 0.5, 0.71), (6.1, "MIXED", 417, 0.68, 0.65)),
+        d1_sides=((6.0, "MIXED", 110, 0.66, 0.64), (None, "BUILDING", 2, 0.0, 0.63)),
+        tape={"source": "SPY", "light": "normal", "range_mean": 0.08, "expected_range": 0.08, "ratio": 1.0},
+    )
+    levels = _rows(ip.build(now=ip.FIXTURE_NOW, sources=ip.fixture_sources(technicals=snap)))["int:levels"]
+    assert ("Intraday M5 levels ok 5.9 (held 0.52 of 817 tests vs 0.63 usual; support building, resistance 6.1); "
+            "D1 levels ok 5.4 (held 0.66 of 216 vs 0.64 usual; support 6.0, resistance building)") in levels["text"]
+    assert (levels["m5_support_score"], levels["m5_support_state"]) == (None, "")
+    assert (levels["m5_resistance_score"], levels["m5_resistance_state"]) == (6.1, "MIXED")
+    assert (levels["d1_resistance_score"], levels["d1_resistance_state"]) == (None, "")
+    # A side building: the pooled M5 (MIXED) decides.
+    assert levels["verdict"] == "LEVELS NORMAL"
+
+
 @pytest.mark.parametrize("technicals", [
     None,
     {},
@@ -84,27 +117,47 @@ def test_a_raising_snapshot_reader_is_unknown():
     assert "unknown" in rows["int:levels"]["text"]
 
 
-def test_the_pack_and_the_chip_say_the_same_verdict():
+_WEAK_SUP = ((3.4, "WEAK", 400, 0.55, 0.63), (5.8, "MIXED", 417, 0.66, 0.65))
+_WEAK_RES = ((5.9, "MIXED", 400, 0.66, 0.63), (3.9, "WEAK", 417, 0.55, 0.65))
+_BOTH_WEAK = ((3.4, "WEAK", 400, 0.55, 0.63), (2.9, "VERY WEAK", 417, 0.52, 0.65))
+_BOTH_FIRM = ((7.1, "FIRM", 400, 0.72, 0.63), (8.3, "STRONG", 417, 0.77, 0.65))
+_BOTH_OK = ((5.6, "MIXED", 400, 0.64, 0.63), (5.4, "MIXED", 417, 0.64, 0.65))
+
+
+@pytest.mark.parametrize("m5, m5_sides, light, expected, sides_text", [
+    ((4.0, "WEAK"), _WEAK_SUP, "normal", "SUPPORT FAILING", "M5 sup 3.4 res 5.8"),
+    ((4.4, "WEAK"), _WEAK_RES, "calm", "RESISTANCE FAILING", "M5 sup 5.9 res 3.9"),
+    ((3.0, "VERY WEAK"), _BOTH_WEAK, "normal", "LEVELS FAILING", "M5 sup 3.4 res 2.9"),
+    ((6.8, "FIRM"), _BOTH_FIRM, "calm", "LEVELS HOLDING", "M5 sup 7.1 res 8.3"),
+    ((5.6, "MIXED"), _BOTH_OK, "normal", "LEVELS NORMAL", "M5 sup 5.6 res 5.4"),
+    ((6.8, "FIRM"), _BOTH_FIRM, "fast", "LEVELS FAILING", "M5 sup 7.1 res 8.3"),
+    ((6.8, "FIRM"), None, "normal", "LEVELS HOLDING", "M5 sup building res building"),
+])
+def test_the_pack_and_the_chip_say_the_same_verdict(m5, m5_sides, light, expected, sides_text):
     from technical_integrity import format_technical_integrity_snapshot, technicals_verdict
 
-    for m5, light in (((4.0, "WEAK"), "normal"), ((6.8, "FIRM"), "calm"), ((5.6, "MIXED"), "normal"),
-                      ((6.8, "FIRM"), "fast")):
-        snap = ip.fixture_technicals(m5=m5, tape={"source": "SPY", "light": light, "range_mean": 0.08,
-                                                  "expected_range": 0.08, "ratio": 1.0})
-        verdict = technicals_verdict(snap["market"])
-        chip, _tip, _color = format_technical_integrity_snapshot(
-            snap, now=datetime(2026, 10, 2, 13, 3, tzinfo=ZoneInfo("America/New_York")))
-        assert chip.startswith(f"Levels: {verdict} · ")
-        rows = _rows(ip.build(now=ip.FIXTURE_NOW, sources=ip.fixture_sources(technicals=snap)))
-        assert rows["int:levels"]["verdict"] == verdict
-        assert f"5.5 = normal): {verdict}." in rows["int:levels"]["text"]
+    snap = ip.fixture_technicals(m5=m5, m5_sides=m5_sides,
+                                 tape={"source": "SPY", "light": light, "range_mean": 0.08,
+                                       "expected_range": 0.08, "ratio": 1.0})
+    verdict = technicals_verdict(snap["market"])
+    assert verdict == expected
+    chip, _tip, _color = format_technical_integrity_snapshot(
+        snap, now=datetime(2026, 10, 2, 13, 3, tzinfo=ZoneInfo("America/New_York")))
+    assert chip.startswith(f"Levels: {verdict} · {sides_text} · D1 sup 4.1 res 6.0")
+    rows = _rows(ip.build(now=ip.FIXTURE_NOW, sources=ip.fixture_sources(technicals=snap)))
+    assert rows["int:levels"]["verdict"] == verdict
+    assert f"5.5 = normal): {verdict}." in rows["int:levels"]["text"]
+    if m5_sides is not None:
+        (sup, *_), (res, *_) = m5_sides
+        assert f"; support {sup:.1f}, resistance {res:.1f}); D1 levels" in rows["int:levels"]["text"]
 
 
 # ---------------------------------------------------------------- lens triggers
-def _levels(m5_state="MIXED", m5_score=5.5, d1_state="MIXED", d1_score=5.5, *, d1_tests=200, stale=False):
+def _levels(m5_state="MIXED", m5_score=5.5, d1_state="MIXED", d1_score=5.5, *, d1_tests=200, stale=False,
+            sup="", res=""):
     return {"id": "int:levels", "m5_state": m5_state, "m5_score": m5_score, "m5_held": 0.52, "m5_usual": 0.63,
             "d1_state": d1_state, "d1_score": d1_score, "d1_held": 0.6, "d1_usual": 0.7, "d1_tests": d1_tests,
-            "stale": stale}
+            "m5_support_state": sup, "m5_resistance_state": res, "stale": stale}
 
 
 def _tape(light, *, ratio=1.7, stale=False, source="SPY"):
@@ -156,6 +209,44 @@ def test_m5_fires_on_entering_weak_leaving_weak_and_entering_firm_but_not_leavin
     assert state.pending == [] and state.m5_bucket == "ok", "firm -> ok is silent"
 
 
+@pytest.mark.parametrize("row, what", [
+    (_levels("WEAK", 4.0, sup="WEAK", res="VERY WEAK"),
+     "support and resistance are both failing more than usual for this hour"),
+    (_levels("WEAK", 4.0, sup="VERY WEAK", res="MIXED"),
+     "support is failing more than usual for this hour while resistance holds (the market, not the levels)"),
+    (_levels("WEAK", 4.0, sup="FIRM", res="WEAK"),
+     "resistance is failing more than usual for this hour while support holds (the market, not the levels)"),
+    (_levels("WEAK", 4.0, sup="MIXED", res="MIXED"), "bounces are failing more than usual for this hour"),
+    (_levels("WEAK", 4.0, sup="WEAK", res=""), "bounces are failing more than usual for this hour"),
+])
+def test_m5_weak_text_names_the_failing_side(row, what):
+    state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
+    state = _hold(state, 5, [row])
+    assert _keys(state) == ["levels_m5"]
+    assert state.pending[0]["text"] == f"Intraday levels turned WEAK (M5 now 4.0, held 0.52 vs 0.63 usual): {what}"
+
+
+def test_m5_firm_text_says_levels_are_holding():
+    state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
+    state = _hold(state, 5, [_levels("FIRM", 6.8, sup="FIRM", res="STRONG")])
+    assert state.pending[0]["text"] == (
+        "Intraday levels turned FIRM (M5 now 6.8, held 0.52 vs 0.63 usual): levels are holding better than usual "
+        "for this hour")
+
+
+def test_the_pack_row_drives_the_lens_side_text():
+    def rows(m5, m5_sides):
+        snap = ip.fixture_technicals(m5=m5, m5_sides=m5_sides)
+        return list(ip.build(now=ip.FIXTURE_NOW, sources=ip.fixture_sources(technicals=snap)).rows)
+
+    state = lens.observe(None, now=_at(0), internals=rows((5.6, "MIXED"), _BOTH_OK))
+    state = _hold(state, 5, rows((4.0, "WEAK"), _WEAK_SUP))
+    texts = [item["text"] for item in state.pending if item["key"] == "levels_m5"]
+    assert texts == [
+        "Intraday levels turned WEAK (M5 now 4.0, held 0.52 vs 0.63 usual): support is failing more than usual "
+        "for this hour while resistance holds (the market, not the levels)"]
+
+
 def test_dwell_keeps_a_10_minute_wobble_silent_and_fires_a_15_minute_one():
     state = lens.observe(None, now=_at(0), internals=[_levels("MIXED", 5.5)])
     state = _hold(state, 5, [_levels("WEAK", 4.2)], minutes=10)
diff --git a/tests/test_technical_integrity_rolling.py b/tests/test_technical_integrity_rolling.py
index 6d540eca..00c553bd 100644
--- a/tests/test_technical_integrity_rolling.py
+++ b/tests/test_technical_integrity_rolling.py
@@ -21,7 +21,7 @@ def _fixture():
     return load_fixture_contract(FIXTURE_NAME)
 
 
-def _event(event_id, timeframe, touch, resolved, outcome, weight=2.5, symbol="MU", direction=""):
+def _event(event_id, timeframe, touch, resolved, outcome, weight=2.5, symbol="MU", direction="", side="above"):
     return {
         "event_type": "level_resolved",
         "event_id": event_id,
@@ -33,7 +33,7 @@ def _event(event_id, timeframe, touch, resolved, outcome, weight=2.5, symbol="MU
         "industry_key": "semiconductors",
         "level_family": "d1_sma_50" if timeframe == "d1" else "vwap",
         "level_timeframe": "d1" if timeframe == "d1" else "intraday",
-        "approach_side": "above",
+        "approach_side": side,
         "outcome": outcome,
         "break_direction": direction,
         "event_weight": weight,
@@ -78,6 +78,10 @@ def test_rolling_now_reading_golden():
         )
         assert result["schema"] == "technical_integrity_rolling_v1"
         assert result["window_minutes"] == 60
+        # Support/resistance sub-reads are per timeframe only; the all-levels read gets none.
+        assert "support" not in result["all"] and "resistance" not in result["all"]
+        for tf in ("d1", "m5"):
+            assert "support" in case["rolling"][tf] and "resistance" in case["rolling"][tf]
         for tf, expected in case["rolling"].items():
             for key, value in expected.items():
                 fixture.assert_matches(result[tf][key], value, f"{case['as_of']}.{tf}.{key}")
@@ -176,8 +180,8 @@ def test_chip_omits_the_tape_when_the_source_is_none():
     chip, tooltip, _color = format_technical_integrity_snapshot(
         snapshot, now=datetime.fromisoformat(case["as_of"])
     )
-    # No tape reading counts as not fast: a STRONG M5 still reads "working".
-    assert chip == "Levels: BOUNCES WORKING · M5 strong 9.1 · D1 very weak 2.2"
+    # No tape reading counts as not fast. Resistance is still building, so the pooled STRONG M5 decides.
+    assert chip == "Levels: LEVELS HOLDING · M5 sup 10.0 res building · D1 sup 2.1 res building"
     assert "Tape (last 30 min): unknown (no SPY bars provider)." in tooltip.splitlines()
 
 
@@ -387,11 +391,37 @@ def test_tick_light_thresholds(ratio_range, light):
 # ------------------------------------------------------------------ verdict
 _M5_STATES = ("VERY WEAK", "WEAK", "MIXED", "FIRM", "STRONG", None)
 _TAPES = ("calm", "normal", "fast", "unknown", None)
-
-
-def _verdict_market(m5_state, light, *, d1_scored=True):
+_STATE_SCORE = {"VERY WEAK": 2.4, "WEAK": 4.1, "MIXED": 5.6, "FIRM": 7.0, "STRONG": 8.6}
+_EXPLAINED = {
+    "LEVELS FAILING": "LEVELS FAILING = both support and resistance are breaking more than usual for this hour, "
+                      "or the tape is fast.",
+    "LEVELS HOLDING": "LEVELS HOLDING = both support and resistance are holding better than usual for this hour "
+                      "and the tape is not fast.",
+    "SUPPORT FAILING": "SUPPORT FAILING = support is breaking more than usual for this hour while resistance is "
+                       "not: the market is pressing down, the levels still work.",
+    "RESISTANCE FAILING": "RESISTANCE FAILING = resistance is breaking more than usual for this hour while support "
+                          "is not: the market is pressing up, the levels still work.",
+    "LEVELS NORMAL": "LEVELS NORMAL = intraday levels are holding about as usual for this hour.",
+}
+
+
+def _side_read(state, *, tests=40, held=0.6, usual=0.7):
+    """A rolling side sub-read as the reading writes it; ``None`` = too few tests (building)."""
+    if state is None:
+        return {"score": None, "state": "BUILDING", "pressure": "BALANCED", "test_count": 3, "chop_count": 0,
+                "symbol_count": 2, "resolved_weight": 6.0, "observed_probability": 0.5,
+                "expected_probability": 0.72, "residual": -0.22}
+    return {"score": _STATE_SCORE[state], "state": state, "pressure": "BALANCED", "test_count": tests,
+            "chop_count": 4, "symbol_count": 12, "resolved_weight": tests * 2.0, "observed_probability": held,
+            "expected_probability": usual, "residual": round(held - usual, 4)}
+
+
+def _verdict_market(m5_state, light, *, d1_scored=True, sides=None):
+    """Market block; ``sides`` = (support state, resistance state) for M5, absent = an older snapshot."""
     m5 = {"score": None, "state": "BUILDING"} if m5_state is None else {"score": 5.0, "state": m5_state}
     d1 = {"score": 5.4, "state": "MIXED"} if d1_scored else {"score": None, "state": "BUILDING"}
+    if sides is not None:
+        m5["support"], m5["resistance"] = _side_read(sides[0]), _side_read(sides[1])
     market = {"rolling": {"m5": m5, "d1": d1}}
     if light is not None:
         market["tape"] = {"source": "none" if light == "unknown" else "SPY", "light": light}
@@ -400,28 +430,145 @@ def _verdict_market(m5_state, light, *, d1_scored=True):
 
 @pytest.mark.parametrize("m5_state", _M5_STATES)
 @pytest.mark.parametrize("light", _TAPES)
-def test_technicals_verdict_table(m5_state, light):
+def test_technicals_verdict_table_without_side_reads_falls_back_to_the_pooled_m5(m5_state, light):
+    """An older snapshot (no support/resistance sub-reads) keeps today's pooled rule, in the new words."""
     from technical_integrity import technicals_verdict
 
     if m5_state in {"WEAK", "VERY WEAK"} or light == "fast":
-        expected = "BOUNCES FAILING"
+        expected = "LEVELS FAILING"
     elif m5_state in {"FIRM", "STRONG"}:
         # Not fast is enough: an unknown or missing tape never downgrades a firm read.
-        expected = "BOUNCES WORKING"
+        expected = "LEVELS HOLDING"
     else:
         expected = "LEVELS NORMAL"
     assert technicals_verdict(_verdict_market(m5_state, light)) == expected
 
 
+@pytest.mark.parametrize("support, resistance, pooled, light, expected", [
+    # Both sides scored: the sides decide.
+    ("WEAK", "VERY WEAK", "VERY WEAK", "normal", "LEVELS FAILING"),
+    ("VERY WEAK", "WEAK", "WEAK", None, "LEVELS FAILING"),
+    ("FIRM", "STRONG", "STRONG", "normal", "LEVELS HOLDING"),
+    ("STRONG", "FIRM", "MIXED", "calm", "LEVELS HOLDING"),
+    ("FIRM", "FIRM", "FIRM", "unknown", "LEVELS HOLDING"),
+    ("WEAK", "MIXED", "WEAK", "normal", "SUPPORT FAILING"),
+    ("VERY WEAK", "FIRM", "MIXED", "calm", "SUPPORT FAILING"),
+    ("WEAK", "STRONG", "FIRM", None, "SUPPORT FAILING"),
+    ("MIXED", "WEAK", "WEAK", "normal", "RESISTANCE FAILING"),
+    ("STRONG", "VERY WEAK", "MIXED", "unknown", "RESISTANCE FAILING"),
+    ("MIXED", "MIXED", "MIXED", "normal", "LEVELS NORMAL"),
+    ("FIRM", "MIXED", "FIRM", "normal", "LEVELS NORMAL"),
+    ("MIXED", "STRONG", "STRONG", "calm", "LEVELS NORMAL"),
+    # A fast tape overrides every side read.
+    ("FIRM", "FIRM", "FIRM", "fast", "LEVELS FAILING"),
+    ("WEAK", "MIXED", "WEAK", "fast", "LEVELS FAILING"),
+    ("MIXED", "WEAK", "WEAK", "fast", "LEVELS FAILING"),
+    ("MIXED", "MIXED", "MIXED", "fast", "LEVELS FAILING"),
+    # A side still building: the pooled M5 state decides, as before.
+    ("WEAK", None, "FIRM", "normal", "LEVELS HOLDING"),
+    ("STRONG", None, "VERY WEAK", "calm", "LEVELS FAILING"),
+    (None, "WEAK", "MIXED", "normal", "LEVELS NORMAL"),
+    (None, "MIXED", "WEAK", "normal", "LEVELS FAILING"),
+    (None, None, "STRONG", None, "LEVELS HOLDING"),
+    (None, "FIRM", "FIRM", "fast", "LEVELS FAILING"),
+])
+def test_technicals_verdict_reads_support_and_resistance(support, resistance, pooled, light, expected):
+    from technical_integrity import technicals_verdict
+
+    market = _verdict_market(pooled, light, sides=(support, resistance))
+    assert technicals_verdict(market) == expected
+
+
+@pytest.mark.parametrize("support", _M5_STATES)
+@pytest.mark.parametrize("resistance", _M5_STATES)
+@pytest.mark.parametrize("pooled", ("WEAK", "MIXED", "FIRM"))
+@pytest.mark.parametrize("light", ("calm", "fast", "unknown"))
+def test_technicals_verdict_never_says_bounces_and_follows_the_side_rule(support, resistance, pooled, light):
+    from technical_integrity import technicals_verdict
+
+    weak, firm = {"WEAK", "VERY WEAK"}, {"FIRM", "STRONG"}
+    if light == "fast":
+        expected = "LEVELS FAILING"
+    elif support is not None and resistance is not None:
+        if support in weak and resistance in weak:
+            expected = "LEVELS FAILING"
+        elif support in firm and resistance in firm:
+            expected = "LEVELS HOLDING"
+        elif support in weak:
+            expected = "SUPPORT FAILING"
+        elif resistance in weak:
+            expected = "RESISTANCE FAILING"
+        else:
+            expected = "LEVELS NORMAL"
+    else:
+        expected = {"WEAK": "LEVELS FAILING", "MIXED": "LEVELS NORMAL", "FIRM": "LEVELS HOLDING"}[pooled]
+    assert technicals_verdict(_verdict_market(pooled, light, sides=(support, resistance))) == expected
+
+
 def test_technicals_verdict_building_without_any_rolling_score():
     from technical_integrity import technicals_verdict
 
     assert technicals_verdict(_verdict_market(None, "fast", d1_scored=False)) == "BUILDING"
+    assert technicals_verdict(_verdict_market(None, "fast", d1_scored=False, sides=(None, None))) == "BUILDING"
     assert technicals_verdict({}) == "BUILDING"
     assert technicals_verdict(None) == "BUILDING"
+    # M5 unscored with D1 scored is a reading: normal, or failing on a fast tape.
+    assert technicals_verdict(_verdict_market(None, "normal")) == "LEVELS NORMAL"
+    assert technicals_verdict(_verdict_market(None, "fast")) == "LEVELS FAILING"
+
+
+@pytest.mark.parametrize("support, resistance, pooled, light, verdict", [
+    ("WEAK", "WEAK", "WEAK", "normal", "LEVELS FAILING"),
+    ("FIRM", "STRONG", "FIRM", "normal", "LEVELS HOLDING"),
+    ("WEAK", "MIXED", "WEAK", "normal", "SUPPORT FAILING"),
+    ("MIXED", "VERY WEAK", "WEAK", "normal", "RESISTANCE FAILING"),
+    ("MIXED", "FIRM", "MIXED", "normal", "LEVELS NORMAL"),
+])
+def test_tooltip_head_explains_each_verdict(support, resistance, pooled, light, verdict):
+    from technical_integrity import format_technical_integrity_snapshot
+
+    snapshot = {"session_date": "2026-10-05",
+                "market": _verdict_market(pooled, light, sides=(support, resistance))}
+    chip, tooltip, _ = format_technical_integrity_snapshot(
+        snapshot, now=datetime.fromisoformat("2026-10-05T11:00:00-04:00")
+    )
+    assert chip.split(" · ")[0] == f"Levels: {verdict}"
+    assert tooltip.splitlines()[0] == _EXPLAINED[verdict] + " 5.5 = normal for this hour."
+    assert "BOUNCES" not in chip and "BOUNCES" not in tooltip
 
 
-def test_chip_words_and_verdict_lead():
+def test_chip_shows_both_sides_per_timeframe_and_the_tooltip_adds_side_lines():
+    from technical_integrity import format_technical_integrity_snapshot
+
+    m5 = {"score": 4.4, "state": "WEAK", "pressure": "BEARISH", "test_count": 78, "chop_count": 9,
+          "symbol_count": 30, "resolved_weight": 160.0, "observed_probability": 0.6,
+          "expected_probability": 0.72, "residual": -0.12,
+          "support": _side_read("WEAK", tests=40, held=0.55, usual=0.714),
+          "resistance": _side_read("MIXED", tests=38, held=0.70, usual=0.727)}
+    d1 = {"score": 6.1, "state": "MIXED", "pressure": "BALANCED", "test_count": 50, "chop_count": 3,
+          "symbol_count": 20, "resolved_weight": 125.0, "observed_probability": 0.68,
+          "expected_probability": 0.65, "residual": 0.03,
+          "support": _side_read("FIRM", tests=30, held=0.75, usual=0.65),
+          "resistance": _side_read(None)}
+    market = {"rolling": {"schema": "technical_integrity_rolling_v1", "window_minutes": 60, "m5": m5, "d1": d1},
+              "tape": {"source": "SPY", "light": "normal", "range_mean": 0.08, "expected_range": 0.0834}}
+    chip, tooltip, _ = format_technical_integrity_snapshot(
+        {"session_date": "2026-10-05", "market": market}, now=datetime.fromisoformat("2026-10-05T11:00:00-04:00")
+    )
+    assert chip == "Levels: SUPPORT FAILING · M5 sup 4.1 res 5.6 · D1 sup 7.0 res building · tape normal"
+    lines = tooltip.splitlines()
+    assert lines[0] == _EXPLAINED["SUPPORT FAILING"] + " 5.5 = normal for this hour."
+    assert lines[1].startswith("Now = last 60 min")
+    assert lines[2].startswith("D1 now 6.1/10 (MIXED)")
+    assert lines[3] == ("D1 sides: support 7.0 (FIRM), held 0.75 of 30 tests vs 0.65 usual; "
+                        "resistance building (3 decisive tests).")
+    assert lines[4].startswith("M5 now 4.4/10 (WEAK)")
+    assert lines[5] == ("M5 sides: support 4.1 (WEAK), held 0.55 of 40 tests vs 0.71 usual; "
+                        "resistance 5.6 (MIXED), held 0.70 of 38 tests vs 0.73 usual.")
+    assert lines[6].startswith("Tape (SPY, last 30 min)")
+
+
+def test_chip_words_and_verdict_lead_for_an_older_snapshot_without_side_reads():
     from technical_integrity import format_technical_integrity_snapshot
 
     market = _verdict_market("FIRM", "normal")
@@ -430,5 +577,82 @@ def test_chip_words_and_verdict_lead():
     chip, tooltip, _ = format_technical_integrity_snapshot(
         snapshot, now=datetime.fromisoformat("2026-10-05T11:00:00-04:00")
     )
-    assert chip == "Levels: BOUNCES WORKING · M5 firm 6.8 · D1 ok 5.4 · tape normal"
-    assert tooltip.splitlines()[0].startswith("BOUNCES WORKING = ")
+    # No sub-reads: each side reads "building"; the verdict falls back to the pooled M5 state.
+    assert chip == "Levels: LEVELS HOLDING · M5 sup building res building · D1 sup building res building · tape normal"
+    assert tooltip.splitlines()[0] == _EXPLAINED["LEVELS HOLDING"] + " 5.5 = normal for this hour."
+
+
+def test_a_trend_hour_reads_resistance_failing_end_to_end():
+    """Supports hold and every resistance breaks: the pooled M5 is very weak, but the levels still work."""
+    from technical_integrity import format_technical_integrity_snapshot, rolling_technical_integrity
+
+    rows = [_event(f"s{i}", "m5", "10:35", "10:50", "held", 2.0, symbol=f"S{i}") for i in range(5)]
+    rows += [_event(f"r{i}", "m5", "10:35", "10:50", "broke", 2.0, symbol=f"R{i}", direction="up", side="below")
+             for i in range(5)]
+    as_of = "2026-10-05T11:00:00-04:00"
+    rolling = rolling_technical_integrity(rows, as_of=as_of)
+    m5 = rolling["m5"]
+    # Pooled is unchanged: 0.50 held vs the pooled hour-1 m5 norm 0.714 -> 1.0.
+    assert (m5["score"], m5["state"], m5["test_count"]) == (1.0, "VERY WEAK", 10)
+    assert m5["expected_probability"] == 0.714
+    support, resistance = m5["support"], m5["resistance"]
+    # Support: 5 held vs m5_above hour 1 = 0.714 -> residual 0.286 -> 10.0.
+    assert (support["score"], support["state"], support["test_count"]) == (10.0, "STRONG", 5)
+    assert (support["observed_probability"], support["expected_probability"], support["residual"]) == (
+        1.0, 0.714, 0.286)
+    assert (support["resolved_weight"], support["symbol_count"], support["pressure"]) == (10.0, 5, "BALANCED")
+    # Resistance: 5 broke vs m5_below hour 1 = 0.727 -> 1.0.
+    assert (resistance["score"], resistance["state"], resistance["test_count"]) == (1.0, "VERY WEAK", 5)
+    assert (resistance["observed_probability"], resistance["expected_probability"], resistance["residual"]) == (
+        0.0, 0.727, -0.727)
+    assert resistance["pressure"] == "BULLISH"
+    assert "support" not in rolling["all"] and "resistance" not in rolling["all"]
+
+    market = {"rolling": rolling, "tape": {"source": "SPY", "light": "normal", "range_mean": 0.08,
+                                           "expected_range": 0.0834}}
+    chip, _tooltip, _ = format_technical_integrity_snapshot(
+        {"session_date": "2026-10-05", "market": market}, now=datetime.fromisoformat(as_of)
+    )
+    assert chip == "Levels: RESISTANCE FAILING · M5 sup 10.0 res 1.0 · D1 building · tape normal"
+
+
+_SIDE_NORMS = {
+    # hour: (m5_above, m5_below, d1_above, d1_below), measured 25 sessions ending 2026-10-09.
+    0: (0.633, 0.645, 0.642, 0.637),
+    1: (0.714, 0.727, 0.655, 0.631),
+    2: (0.815, 0.718, 0.804, 0.611),
+    3: (0.775, 0.788, 0.720, 0.747),
+    4: (0.785, 0.806, 0.712, 0.804),
+    5: (0.781, 0.784, 0.699, 0.733),
+    6: (0.676, 0.758, None, None),
+}
+
+
+@pytest.mark.parametrize("hour", sorted(_SIDE_NORMS))
+def test_each_side_is_scored_against_its_own_hour_norm(hour):
+    from technical_integrity import rolling_technical_integrity
+
+    touch_minutes = 9 * 60 + 30 + 60 * hour + 5
+    touch = f"{touch_minutes // 60:02d}:{touch_minutes % 60:02d}"
+    resolved = f"{(touch_minutes + 20) // 60:02d}:{(touch_minutes + 20) % 60:02d}"
+    as_of = f"2026-10-05T{resolved}:00-04:00"
+    rows = []
+    for tf in ("m5", "d1"):
+        for side in ("above", "below"):
+            rows += [_event(f"{tf}{side}{i}", tf, touch, resolved, "held", 2.0, symbol=f"X{i}", side=side)
+                     for i in range(4)]
+    result = rolling_technical_integrity(rows, as_of=as_of)
+    m5_above, m5_below, d1_above, d1_below = _SIDE_NORMS[hour]
+    assert result["m5"]["support"]["expected_probability"] == m5_above
+    assert result["m5"]["resistance"]["expected_probability"] == m5_below
+    assert result["m5"]["support"]["residual"] == round(1.0 - m5_above, 4)
+    assert result["m5"]["support"]["score"] == round(min(10.0, 5.5 + 30.0 * (1.0 - m5_above)), 1)
+    if d1_above is None:
+        # The last half hour has no D1 norm: both D1 sides read building, however heavy.
+        for side in ("support", "resistance"):
+            assert (result["d1"][side]["score"], result["d1"][side]["state"]) == (None, "BUILDING")
+            assert result["d1"][side]["test_count"] == 0
+    else:
+        assert result["d1"]["support"]["expected_probability"] == d1_above
+        assert result["d1"]["resistance"]["expected_probability"] == d1_below
+        assert result["d1"]["resistance"]["test_count"] == 4
```

## Lead note
Measured facts (the lead ran these; the builder did not see the reference):
- Builder: 1 pass, 135 turns, cut off by an OpenRouter 402 (credits exhausted) before it finished; no self-review, no final report. Treat the diff as an interrupted build.
- Own tests: 3 of the builder's own tests in tests/test_technical_integrity_rolling.py fail (chip says "SUPPORT FAILING" where the test expects "LEVELS FAILING" twice; the trend-hour end-to-end test gets BUILDING where it expects STRONG). The rest of the touched test files pass (88). Whole suite: 7 further failures, all environmental (git history, machine-local files, Qt flakes that pass in isolation).
- Hidden reference tests: 397/459 pass, 62 fail. Causes: 26 assert 'LEVELS HOLDING' == 'LEVELS NORMAL' (the builder returns HOLDING where the reference returns NORMAL; the reference says HOLDING only when both sides hold better than usual, NORMAL when about as usual; the brief listed both words but not the rule); 10 TypeError fixture_technicals() got an unexpected keyword argument 'm5_sides' (reference test helper signature the brief never gave); the rest are Mentor/lens wording (the reference writes "intraday levels are failing" / "M5 support is failing" where the builder kept "bounces are failing") and per-side norm scoring values.
- The golden fixture tests/fixtures/technical_integrity_rolling_v1.json gained support/resistance sub-reads only; its events and raw_input_sha256 are unchanged (allowed by the brief).
- ruff clean. The .claude/agents/* and CLAUDE.md hunks are harness setup, not builder edits.
