# Recon — levels read gains support/resistance sub-reads and a holding verdict

Task: the "bounces failing" levels read must work for shorts too and say whether levels hold
IN GENERAL. Support = approach side "above", resistance = approach side "below". Sub-reads per
session hour against side norms (m5_above / m5_below / d1_above / d1_below; derive or stub the
norm table clearly). Pooled numbers and the "all" read stay unchanged. New verdict words
LEVELS FAILING / LEVELS HOLDING / SUPPORT FAILING / RESISTANCE FAILING / LEVELS NORMAL /
BUILDING; BOUNCES FAILING / BOUNCES WORKING are gone.

## Files and functions the task touches

### `scripts/technical_integrity.py` (the main file)
- `SESSION_HOUR_RESPECT_NORMS` (lines 627–635): measured respect by session hour, keys
  `all`/`d1`/`m5`; hour 6 has no D1 norm. Session hours: open 09:30 ET, hour = whole hours
  since open (`_session_hour_index`, lines 656–659: hour 0 = 09:30–10:29, hour 1 = 10:30–11:29…).
- `ROLLING_RESIDUAL_FULL_SCALE = 0.15` (line 637): residual ±0.15 spans the 1–10 scale around 5.5.
- `_rolling_timeframe_reading(events, tf_key, config)` (lines 662–716): per-event norm lookup
  `SESSION_HOUR_RESPECT_NORMS.get(hour, {}).get(tf_key)` (line 690); observed = weighted mean of
  outcome values (held 1.0 / reclaimed 0.65 / broke 0.0 — `TechnicalIntegrityConfig`
  lines 97–100); chop counted never scored (`count_chop_as_evidence=False`, line 108);
  `score = round(clamp(5.5 + 4.5*residual/0.15, 1, 10), 1)` only when
  `weight_sum >= min_decisive_weight_for_score` (8.0, line 119) and test_count > 0 (line 701);
  returns `{score, state, pressure, test_count, chop_count, symbol_count, resolved_weight,
  observed_probability, expected_probability, residual}`.
  → GAINS a `side` param (None/"above"/"below"): filter events by `approach_side`, look up the
  side norm key. Pooled path (side=None) unchanged.
- `rolling_technical_integrity` (lines 719–755): 60-min window `start < resolved_at <= moment`,
  rows `{schema, as_of, window_minutes, all, d1, m5}` via `by_tf` (lines 743–747).
  → ADDS `support`/`resistance` sub-read dicts to the `d1` and `m5` rows only.
- `technicals_verdict(market)` (lines 2993–3009): BUILDING when both d1 and m5 pooled scores
  are None; else light from tape (source "none" → "unknown", line 3002); m5 weak/very weak or
  fast → "BOUNCES FAILING"; firm/strong → "BOUNCES WORKING"; else "LEVELS NORMAL".
  → REPLACED by the side-aware verdict (side sub-reads decide when both scored; fast tape
  overrides; building side / older snapshot without sub-reads falls back to the pooled M5 rule
  with the new words).
- `_VERDICT_EXPLAINED` (lines 2980–2990): BOUNCES FAILING / BOUNCES WORKING / LEVELS NORMAL
  strings → replaced with the five new verdict explanations.
- `_rolling_now_view(market)` (lines 3012–3085): `part(name,row)` = "M5 strong 9.1" /
  "M5 building"; `line(name,row)` = "M5 now 9.1/10 (STRONG): levels held … vs … usual at this
  hour; break pressure …; N decisive tests / N chop / N symbols." or
  "M5 now building: not enough decisive tests in the last 60 min (…)."; chip =
  `Levels: {verdict} · {part('M5',m5)} · {part('D1',d1)}` (+ ` · tape {light}` when tape known);
  lines = [verdict explained + " 5.5 = normal for this hour.", "Now = last …", D1 line, M5 line,
  tape line]. → GAINS the `M5 sup n res n` / `D1 sup n res n` chip parts and the side tooltip
  lines after each pooled line; headline (pressure/state → color) unchanged (line 3079–3084).
- `format_technical_integrity_snapshot` (lines 2914–2958) and `_integrity_color`
  (lines 2961–2970): no change needed (call the now-view; color from headline).
- `TechnicalIntegrityMonitor._publish_snapshot` (line 1774) just stores
  `rolling_technical_integrity(...)` — additive keys are safe.

### Side norms (new constant)
No measured per-side rates exist in the event ledger yet (one-sided counts per hour would be
thin), so the table is derived: each side scores against its own timeframe's hour norm —
`m5_above`/`m5_below` = the m5 norm, `d1_above`/`d1_below` = the d1 norm (hour 6: no D1 side).
Stated clearly in a comment as a stub to replace with measured side-specific rates.

### `scripts/mentor_packs/internals_pack.py`
- `_levels_rows(src, now, session)` (lines 526–583): builds `int:levels` (keys id/kind/verdict/
  m5_score/m5_state/d1_score/d1_state/m5_tests/d1_tests/m5_held/m5_usual/d1_held/d1_usual/
  as_of_utc/stale/text) and `int:tape_speed` (DON'T TOUCH). Text:
  `Levels now (last {window} min vs usual for this hour, 5.5 = normal): {verdict}. {M5 part};
  {D1 part}; break pressure {p}. Today so far: D1 {x}, M5 {y}.` (+ STALE tail). The unknown case
  (no rolling / session mismatch / unreadable) returns the fixed unknown row — unchanged.
  → GAINS side keys (m5/d1 support/resistance test counts + states) and the
  `; support n, resistance n` clause after the M5 part when the m5 row carries sub-reads;
  older snapshots (no sub-read keys) keep the byte-identical text (modulo the verdict word
  change, which applies to every snapshot).
- `_level_part` (lines 517–523): unchanged.
- `fixture_technicals` (lines 656–676): synthetic snapshot for the mentor tests; `tf()` helper
  builds each tf row. → GAINS support/resistance sub-reads mirroring the pooled score/state
  with split test counts (m5: 500/317 of 817; d1: 150/66 of 216), so the pack/chip/verdict path
  is exercised with sub-reads present.

### `scripts/mentor_app/lens.py`
- `_observe_levels(state, row, now)` (lines 341–368): weak bucket wording
  "bounces are failing more than usual for this hour" (m5) / "daily SMAs and S/R are breaking
  more than usual for this hour" (d1); firm bucket "bounces are holding better than usual…" /
  "daily SMAs and S/R are holding better…"; ok = "{word} back to normal ({name} now {score})";
  text = f"{word} turned {level_state} ({name} now {score:.1f}{numbers}): {what}".
  → Weak wording names the failing side from the row's side-state keys (generic "intraday
  levels are failing more than usual for this hour" / "daily levels are failing more than
  usual for this hour" when both sides weak or the row has no side keys); firm bucket says
  "levels are holding" for both prefixes.

## Tests

### `tests/test_technical_integrity_rolling.py` (435 lines)
- Golden: `test_rolling_now_reading_golden` (lines 69–83) iterates `case["rolling"]` per tf and
  asserts each expected key via `fixture.assert_matches` — additive nested keys are picked up
  when the fixture gains `support`/`resistance` expected dicts (conftest `_values_match`
  recurses into Mappings, tests/conftest.py:594–597).
- `test_chip_and_tooltip_lead_with_the_now_reading_golden` (lines 97–122): chip equality,
  tooltip_head prefix equality, "Today so far:" split check → fixture chips/heads get updated.
- `test_chip_omits_the_tape_when_the_source_is_none` (lines 169–181): asserts
  chip == "Levels: BOUNCES WORKING · M5 strong 9.1 · D1 very weak 2.2" → becomes
  "Levels: LEVELS HOLDING · M5 sup 4 res 1 · D1 sup 5 res 0".
- `test_technicals_verdict_table` (lines 401–413): `_verdict_market` (lines 392–398) builds
  rolling rows with no side keys → exercises the fallback rule; expected words change
  BOUNCES FAILING → LEVELS FAILING, BOUNCES WORKING → LEVELS HOLDING.
- `test_technicals_verdict_building_without_any_rolling_score` (lines 416–421): unchanged
  (BUILDING first).
- `test_chip_words_and_verdict_lead` (lines 424–434): no side keys → old pooled chip form with
  "LEVELS HOLDING"; tooltip line 0 starts with "LEVELS HOLDING = ".
- `test_formatter_falls_back_to_the_day_chip_without_a_rolling_reading` (lines 269–290):
  legacy path, no rolling block → unaffected.
- Monitor tests (lines 294–341) touch rolling additively → unaffected.

### `tests/test_mentor_technicals_levels.py` (277 lines)
- `test_levels_and_tape_rows_for_the_fixture_snapshot` (lines 30–47): exact `int:levels` text
  with "BOUNCES FAILING" and no side clause → gains "; support 500, resistance 317" and the
  LEVELS FAILING word; side keys asserted.
- `test_the_pack_and_the_chip_say_the_same_verdict` (lines 87–100): `chip.startswith(f"Levels:
  {verdict} · ")` and `f"5.5 = normal): {verdict}." in text` → keeps working for the new words.
- `_levels()` helper (lines 104–107): no side keys → pins the generic wording / old-snapshot
  behavior; `test_m5_fires_on_entering_weak…` (lines 139–156) asserts the exact weak text
  "bounces are failing more than usual for this hour" → becomes the generic "intraday levels
  are failing more than usual for this hour".
- `test_d1_levels_only_speak_on_80_tests_or_more` (line 196): startswith "Daily levels turned
  WEAK (D1 now 4.1" → unaffected.

### `tests/fixtures/technical_integrity_rolling_v1.json`
- `raw_input_sha256` (line 9) covers `events`/`tick_rows`/`spy_bars` (raw_input_keys line 4–8);
  conftest recomputes it on load (tests/conftest.py:696–704). Only `expected.cases` may change.
- Case 1 (as_of 2026-10-05T11:00): rolling all/d1/m5 pooled (lines 552–588) unchanged; chip /
  chip_without_spy (613–614) and tooltip_head (616–623) gain the new words, side chip parts and
  side lines; rolling gains support/resistance expected dicts for m5 and d1.
- Case 2 (as_of 2026-10-05T11:50): chip (line 675) updated; rolling gains the same keys.
- Case 3: tick only — unchanged.

Hand-computed sub-read expectations (window `start < resolved_at <= moment`; outcome values
held 1.0 / reclaimed 0.65 / broke 0.0; norm per touch hour; score needs weight ≥ 8.0):

Case 1 (m5 norm: hour 0 = 0.631, hour 1 = 0.714; d1: 0.638 / 0.653):
- m5.support: m5a,m5b (h0 held), m5c,m5e (h1 held) + 2 chop → 4 tests, w 8.0; observed 1.0;
  expected 2.0·(0.631+0.631+0.714+0.714)/8 = 0.6725; residual 0.3275 → raw 15.325 → 10.0
  STRONG; 4 symbols (chops add TSLA); no breaks → BALANCED.
- m5.resistance: m5d (broke up, w 2.0 < 8) → score None / BUILDING; observed 0.0, expected
  0.714, residual −0.714; 1 test, 1 symbol; BULLISH.
- d1.support: d1a,d1b,d1c,d1d (h0) + d1e (h1), all above; 5 tests, w 12.5; observed
  (1+0+0+1+0.65)/5 = 0.53; expected (4·0.638+0.653)/5 = 0.641; residual −0.111 → 2.2 VERY WEAK;
  4 symbols; 2 broke down → BEARISH.
- d1.resistance: empty → all null/zero, BUILDING, BALANCED.
- Verdict: resistance building → fallback: m5 STRONG + fast tape → LEVELS FAILING.
- Chip: "Levels: LEVELS FAILING · M5 sup 4 res 1 · D1 sup 5 res 0 · tape fast".

Case 2 (window (10:50, 11:50]):
- m5.support: m5e (h1 held), m5f (h1 broke down), m5g (h1 held), m5h,m5i (h2 0.764: held,
  broke down) + m5chop2 → 5 tests, w 10.0; observed 0.6; expected 0.734; residual −0.134 →
  1.5 VERY WEAK; 4 symbols; BEARISH.
- m5.resistance: empty → BUILDING/BALANCED.
- d1.support: d1d (h0 held), d1e (h1 reclaimed) → w 5.0 < 8 → None/BUILDING; observed 0.825,
  expected 0.6455, residual 0.1795; 2 tests, 2 symbols; BALANCED.
- d1.resistance: d1future (broke up, w 2.5 < 8) → None/BUILDING; observed 0.0, expected 0.653,
  residual −0.653; BULLISH.
- Verdict: fallback m5 VERY WEAK → LEVELS FAILING. Chip: "Levels: LEVELS FAILING · M5 sup 5
  res 0 · D1 sup 2 res 1".

## Consumers verified, no change needed
- `scripts/away_market.py:193–195`: reads only `levels.get("verdict")` from the row.
- `scripts/ui/app.py:804`, `scripts/ui/panels/bounce_panel.py:404`: display the returned
  chip/tooltip/color verbatim.
- `scripts/technical_integrity.py:1774` (`_publish_snapshot`): stores the rolling dict
  additively; monitor tests only check schema/test_count.
- `tests/test_technical_integrity.py` (day-cumulative views, lines 720–923): no BOUNCES
  assertions, no rolling block in those fixtures → unaffected.
- No other BOUNCES FAILING/WORKING references anywhere (grep over the repo: only
  technical_integrity.py, the two test files and the fixture above; other "BOUNCES" hits are
  the unrelated `INTRADAY_BOUNCES_FILE` CSV).
