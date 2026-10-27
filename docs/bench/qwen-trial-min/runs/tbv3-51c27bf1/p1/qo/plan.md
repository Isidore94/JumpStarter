# Plan — side sub-reads + holding verdict for the levels "now" read

## Steps

1. **Tests first (red).** Update the expectations and add the new tests:
   - `tests/fixtures/technical_integrity_rolling_v1.json` — in `expected.cases` only: add
     `support`/`resistance` expected dicts to `rolling.m5` and `rolling.d1` of case 1 and case 2
     (values hand-computed in `.qo/recon.md`); update the two chips, `chip_without_spy` and
     `tooltip_head` of case 1. Do NOT touch `events`, `tick_rows`, `spy_bars`,
     `raw_input_sha256`, `expected_keys`, `intentional_difference`.
   - `tests/test_technical_integrity_rolling.py` — re-point the stale BOUNCES assertions
     (verdict table, chip tests) to the new words; add `test_technicals_verdict_side_reads`
     (every verdict word via side sub-reads: both weak, support only, resistance only,
     holding, normal, fast-tape override, building-side fallback, old-snapshot fallback) and
     `test_chip_and_side_tooltip_lines` (side chip parts; pooled D1 part when D1 row has no
     side keys) plus `test_trend_hour_reads_resistance_failing_end_to_end` (synthetic
     supports-hold / resistances-break events → RESISTANCE FAILING through
     rolling → verdict → chip → Mentor row).
   - `tests/test_mentor_technicals_levels.py` — fixture-snapshot text with
     "; support 500, resistance 317" + side keys + LEVELS FAILING verdict; weak wording now
     the generic "intraday levels are failing more than usual for this hour"; add
     `test_lens_names_the_failing_side` (resistance-only / support-only / both-weak / d1
     variants) and `test_lens_firm_bucket_says_levels_are_holding`; add
     `test_older_snapshot_without_side_reads_keeps_its_text`.
   - Run both files red; save output to `.qo/tests-red.txt`.
2. **Build.**
   - `scripts/technical_integrity.py`:
     - `SESSION_HOUR_SIDE_RESPECT_NORMS` (derived stub: m5_above/m5_below = m5 hour norm,
       d1_above/d1_below = d1 hour norm; comment says measured per-side rates replace it).
     - `_rolling_timeframe_reading(..., side=None)`: filter by `approach_side`, side norm key
       `f"{tf_key}_{side}"`, side norm table; side=None keeps today's behavior exactly.
     - `rolling_technical_integrity`: add `row["support"]` / `row["resistance"]` to the d1 and
       m5 rows only (never `all`).
     - `technicals_verdict`: BUILDING (both pooled scores None) first; fast tape →
       LEVELS FAILING; both M5 side sub-reads scored → both weak/very weak = LEVELS FAILING,
       support only = SUPPORT FAILING, resistance only = RESISTANCE FAILING, either
       firm/strong = LEVELS HOLDING, else LEVELS NORMAL; else (building side or older
       snapshot without sub-reads) fallback pooled M5 rule with the new words (weak →
       LEVELS FAILING, firm/strong → LEVELS HOLDING, else LEVELS NORMAL).
     - `_VERDICT_EXPLAINED`: the five new explanations (BOUNCES words removed).
     - `_rolling_now_view`: chip `Levels: V · M5 sup n res n · D1 sup n res n · tape x` when
       the m5 row carries sub-reads (D1 pooled `part` when its row does not; old pooled chip
       form when the m5 row does not — n = decisive test count per side); tooltip gains
       `D1 support`/`D1 resistance` lines after the D1 pooled line and `M5 support`/
       `M5 resistance` lines after the M5 pooled line (existing `line()` helper).
   - `scripts/mentor_packs/internals_pack.py`: `_levels_rows` adds
     `m5_support_tests`/`m5_resistance_tests`/`d1_support_tests`/`d1_resistance_tests` and
     `m5_support_state`/`m5_resistance_state`/`d1_support_state`/`d1_resistance_state` (0/""
     when the snapshot has no sub-reads) and inserts `; support n, resistance n` after the
     M5 part when sub-reads are present; `fixture_technicals` gains sub-reads mirroring the
     pooled score/state, split test counts 500/317 (m5) and 150/66 (d1).
   - `scripts/mentor_app/lens.py`: `_observe_levels` weak wording names the failing side
     (M5 support / M5 resistance / daily support / daily resistance; generic when both weak or
     no side keys); firm bucket wording = "levels are holding" for both prefixes.
3. **Verify.** `QT_QPA_PLATFORM=offscreen` + venv python: pytest
   `tests/test_technical_integrity_rolling.py`, `tests/test_mentor_technicals_levels.py` and
   `tests/test_technical_integrity.py` (safety: day-cumulative path); `ruff check scripts
   tests`. Save to `.qo/build.txt`.
4. **Self-review** the diff → `.qo/review.json`; fix blockers, re-review at most twice.
5. **Report** → `.qo/report.md`, stop.

## Decisions (recorded per procedure — no questions are asked)

- **Chip "n"** = the decisive test count of each side sub-read (`test_count`), matching the
  "N decisive tests" wording of the tooltip lines.
- **Stub norm table** (not derived data): no per-side measured rates exist yet; each side
  scores against its own timeframe's hour norm. Comment names it a stub to replace with
  measured `m5_above/m5_below/d1_above/d1_below` rates.
- **Verdict precedence**: BUILDING (no pooled read) → fast-tape override → side rule (weak
  words before holding words, so a trend hour with strong support + failing resistance reads
  RESISTANCE FAILING, not HOLDING) → pooled fallback. Side rule engages only when BOTH M5
  sub-reads carry a score; "a building side" = a sub-read without a score.
- **D1 in the chip** falls back to the pooled `part('D1', d1)` wording when the d1 row lacks
  sub-reads; the side tooltip lines appear only for rows that have sub-reads.
- **Mentor row keys** are always present (0 / "" on older snapshots) so downstream code can
  rely on them; the `; support n, resistance n` text clause is present only when the m5 row
  carries sub-reads — older snapshot text is otherwise byte-identical.
- **Lens firm wording** is the task's "levels are holding" for both m5 and d1 ("Intraday
  levels turned FIRM (…) : levels are holding" / "Daily levels turned FIRM (…) : levels are
  holding"); the "back to normal" wording is untouched.
- **Scope skips**: CHANGELOG.md/STATUS.md/docs updates (not in the task file list — noted in
  the report); the fixture's `intentional_difference`/`expected_keys` stay as-is; the
  "all" read, pooled rows, events and `raw_input_sha256` are byte-untouched; `int:tape_speed`
  and every other Mentor row are untouched; no order/sizing code anywhere.

## What "done" means

- Sub-reads present on m5/d1 rolling rows, pooled numbers and the all read unchanged (golden
  per-key asserts pass on the old keys too).
- Every verdict word covered by a test, including the fast-tape override and the fallback for
  a building side and for an older snapshot without sub-reads.
- Chip and tooltip in both forms (sub-reads present / absent).
- Mentor `int:levels` row: side keys + "; support n, resistance n"; older snapshot text
  unchanged.
- Lens: failing side named in the weak bucket; "levels are holding" in the firm bucket.
- A trend hour (supports hold, resistances break) reads RESISTANCE FAILING end to end
  (rolling → verdict → chip → Mentor row).
- The three touched test files + ruff are green (never the full suite).
