# Plan — tape speed light (SPY M5 range vs session-hour norm, TICK fallback)

## What the task asks (and where each piece lands)

1. Generic `tape_speed_light()` for a completed-M5 range against a per-hour norm;
   `tick_range_light()` becomes a thin wrapper over it. → `scripts/technical_integrity.py`
2. SPY per-session-hour range norms, clearly derived or stubbed. → new constant in
   `scripts/technical_integrity.py` (derived — see §Decisions D5).
3. `tape_light()` = SPY when known, else the TICK light (wide = fast, source "TICK"),
   else source "none" with the SPY reason. → new function in the same module.
4. Monitor gets a `spy_bars_provider`; writes `market.tape` fail-open (raising provider
   falls back to TICK); still writes `market.tick` as before. →
   `TechnicalIntegrityMonitor.__init__` + `_publish_snapshot`.
5. legacy.py wires it in one line, reading the `latest_bars` cache only, never IB. →
   `scripts/bounce_bot_lib/legacy.py:_get_technical_integrity_monitor`.
6. Chip says "tape fast/normal/calm" (omitted when source is none); tooltip names SPY or
   "TICK fallback". → `_rolling_now_view` + the golden fixture's expected chip/tooltip.

## Decisions (recorded, no user available to ask)

- **D1 — The "chip" is `format_technical_integrity_snapshot`'s now-chip** built in
  `_rolling_now_view` (`technical_integrity.py:2850`), consumed at `ui/app.py:793` and
  `ui/panels/bounce_panel.py:404`. Verified in recon; the day-cumulative path never reads
  the light, so old snapshots render unchanged.
- **D2 — Label conflict resolved.** The task says the chip reads "tape fast/normal/calm"
  while existing goldens pin "· TICK wide". Resolution: the **generic light and the
  combiner** use `calm / normal / fast / unknown`; **`tick_range_light` keeps its
  historical "wide" label, its `technical_integrity_tick_light_v1` schema, and its 1-decimal
  rounding** (thin wrapper remaps "fast"→"wide" and re-rounds `range_mean`/
  `expected_range` to 1 decimal after the generic's 4-decimal rounding — the golden pins
  `566.7` from `566.666…`, so order matters). The fixture chip/tooltip strings are updated
  to the new spec because the task explicitly changes the chip text; all raw fixture
  inputs stay byte-identical, so `raw_input_sha256` remains valid.
- **D3 — The formatter reads only `market.tape`** (the combined light); `market.tick` is
  still written and still asserted by the existing goldens, but the chip/tooltip no longer
  reads it directly. A snapshot without a `tape` block (older snapshots) renders exactly
  as it does today (`tape = {}` → no chip part, no tooltip line), which keeps
  `test_formatter_falls_back_to_the_day_chip_without_a_rolling_reading` green.
- **D4 — `tape_speed_light` takes pre-parsed bars.** Signature:
  `tape_speed_light(bars, *, as_of, hour_norms, label="SPY", window_minutes=TAPE_LIGHT_WINDOW_MINUTES)`
  where `bars` is an iterable of `(bar_start, bar_end, range_value, stamped_end)` tuples or
  `None` items (None skipped). This makes `tick_range_light` a genuinely thin wrapper
  (`tape_speed_light(map(_tick_bar, rows), …)`) and keeps the generic unit-agnostic
  (TICK: points; SPY: percent-of-close). A new `_spy_range_bar(row)` parses both the
  `IbBar` attribute shape (legacy cache) and Mapping rows (dicts/JSONL), defensive like
  `_tick_bar`: unparseable/missing/unreadable/non-finite/`close <= 0`/`low > high` → `None`.
  Naive stamps are stamped via `normalize_market_local_datetime` (module convention:
  naive = market-local wall time); range = `(high - low) / close * 100.0`.
- **D5 — Norms: 4-session stub, clearly labeled.** The task's 30-session window ending
  2026-10-05 cannot be derived locally (only 4 full SPY sessions exist in the live store:
  2026-09-30, 10-01, 10-02, 10-05; recon §7). `SESSION_HOUR_SPY_RANGE_NORMS =
  {0: 0.1278, 1: 0.1058, 2: 0.0813, 3: 0.0754, 4: 0.0694, 5: 0.0566, 6: 0.0866}` with a
  comment stating the provenance and that it is a short-window stub of the 30-session
  target to be re-derived when more history is available. The task's "derive or stub them
  clearly" permits this.
- **D6 — Thresholds kept exactly as the task states** (also the TICK light's): calm
  < 0.8, fast > 1.25, unknown under 3 bars or newest bar older than 15 min, 30-min
  completed-bar window. Encoded as `TAPE_LIGHT_*` constants + `TAPE_CALM_RATIO` /
  `TAPE_FAST_RATIO`.
- **D7 — `tape_light` combiner shape.** Result dict: `schema (technical_integrity_tape_light_v1),
  source, as_of, bar_count, range_mean, expected_range, ratio, light, last_bar_end`, plus
  `reason` only when light is unknown (mirrors the TICK light's key layout). Known SPY →
  source "SPY", SPY's values. Known TICK → source "TICK", TICK's values, light "wide"
  remapped to "fast" (calm/normal pass through). Both unknown → source "none", light
  "unknown", reason = SPY's reason (fallback "no tape reading"). A raising SPY provider
  yields an SPY light dict with `reason "SPY read failed: …"` → falls through to TICK,
  exactly the task's fail-open order.
- **D8 — Monitor fail-open mirrors the existing tick block:** SPY light computed in its
  own try/except (fallback unknown dict + `note_swallowed(..., quiet=True)`), then
  `market.tape = tape_light(spy_light, market["tick"])` in a second try/except; the
  unchanged tick block runs first, so `market.tick` is written as before. The guiding
  comment at line 1677 is extended to name the tape light.
- **D9 — Tests live in a new file `tests/test_technical_integrity_tape.py`** plus minimal
  updates to `tests/test_technical_integrity_rolling.py` (`_snapshot_at` sets
  `market["tape"]` via the public combiner; nothing else) and the fixture's expected
  case-1 chip/tooltip_head[3] (D2). The parametrized `test_tick_light_thresholds` in the
  rolling file stays untouched and must keep passing (it pins the wrapper).
- **D10 — Test determinism:** all test stamps are tz-aware ET (`-04:00`), which
  `market_session` converts instant-based, so behavior is machine-tz independent
  (recon §6). Hour-1 bars (10:30–11:00 ET, norm 0.1058) are the default test hour.
- **D11 — SPY tooltip decimals.** TICK is points → 0 decimals (unchanged numbers, "567
  vs 415"); SPY is percent → 3 decimals ("0.150 vs 0.106"). Source name in the tooltip:
  "SPY" or "TICK fallback".
- **D12 — One CHANGELOG.md line** per AGENTS.md "After a change"; no RULES.md/STATUS.md
  update needed (recon §8).

## Files changed

1. `scripts/technical_integrity.py` — new constants (`TAPE_LIGHT_SCHEMA`,
   `TAPE_LIGHT_WINDOW_MINUTES`, `TAPE_LIGHT_STALE_MINUTES`, `TAPE_LIGHT_MIN_BARS`,
   `TAPE_CALM_RATIO`, `TAPE_FAST_RATIO`, `SESSION_HOUR_SPY_RANGE_NORMS`); new
   `tape_speed_light()`, `_spy_range_bar()`, `tape_light()`; `tick_range_light()`
   rewritten as the thin wrapper; monitor `__init__` gains `spy_bars_provider`;
   `_publish_snapshot` writes `market.tape` fail-open; `_rolling_now_view` chip/tooltip
   switch to the tape light.
2. `scripts/bounce_bot_lib/legacy.py` — one line in
   `_get_technical_integrity_monitor()`: pass
   `spy_bars_provider=lambda: (getattr(self, "latest_bars", None) or {}).get("SPY|5 D|5 mins") or []`
   (cache read only; no IB).
3. `tests/test_technical_integrity_tape.py` (new) — all new tests, §Tests.
4. `tests/test_technical_integrity_rolling.py` — `_snapshot_at` adds
   `snapshot["market"]["tape"] = tape_light(tape_speed_light((), as_of=as_of),
   snapshot["market"]["tick"])` (no SPY bars in the fixture → TICK fallback path, or
   source "none" in case 2).
5. `tests/fixtures/technical_integrity_rolling_v1.json` — case 1 only:
   - chip → `"Technicals now: D1 VERY WEAK 2.2/10 · M5 STRONG 9.1/10 · tape fast"`
   - tooltip_head[3] → `"Tape (last 30 min, TICK fallback): M5 range 567 vs 415 usual = fast (fast tape = levels fail more)."`
   - every raw input and every other expected value (including all `tick` blocks and case
     2/3 chips) stays identical.
6. `CHANGELOG.md` — one line.

## Tests (written first, must fail before the build)

New `tests/test_technical_integrity_tape.py`:

1. **`tape_speed_light` thresholds** (parametrized): 3 SPY bars at 10:30/10:35/10:40 ET
   (hour 1, norm 0.1058), ranges 0.05 → `calm`, 0.1058 → `normal`, 0.15 → `fast`;
   asserts schema `technical_integrity_tape_light_v1`, light, `ratio` on the right side of
   0.8 / 1.25, `bar_count` 3, `as_of` echo.
2. **attribute-shaped bars** (SimpleNamespace `.dt/.high/.low/.close`, aware stamps):
   same light result as the Mapping rows — pins the IbBar contract legacy.py will feed.
3. **unknown cases**: empty input → `unknown`, `bar_count` 0, reason "no SPY bars in the
   window"; 2 bars → "fewer than 3 SPY bars in the window"; 3 bars ending before
   as_of − 15 min → "newest SPY bar is older than 15 minutes"; a bar ending after
   `as_of` (incomplete) is excluded from the count; a bar starting before the session
   open (hour None) is excluded.
4. **`tape_light` fallback order** (pure, hand-built light dicts):
   SPY known + TICK wide → source "SPY"; SPY unknown + TICK wide → source "TICK", light
   "fast", values copied from the TICK light; SPY unknown + TICK calm → source "TICK",
   light "calm"; SPY unknown + TICK unknown → source "none", light "unknown", reason =
   SPY reason; `None` inputs → source "none" with fallback reason.
5. **wrapper contract** (`tick_range_light`): hour-1 rows with range 530 → schema
   `technical_integrity_tick_light_v1`, light "wide" (never "fast"), `range_mean` 530.0,
   `expected_range` 415.0, `ratio` `round(530/415, 4)`; 1-decimal re-round pinned via a
   500.466… mean (ranges 500, 500, 501.4 → 500.5).
6. **monitor fail-open** (using the file's own `_monitor` helper):
   - raising `spy_bars_provider` + fixture-shaped TICK rows (via
     `tests/fixtures` through `load_fixture_contract`, as the rolling test does) →
     written snapshot has `market.tape.source == "TICK"`, `market.tape.light == "fast"`,
     `market.tick.light == "wide"` (unchanged), snapshot file written.
   - SPY provider with 3 calm SPY bars + same TICK rows → `market.tape.source == "SPY"`,
     `market.tape.light == "calm"`, `market.tick` still "wide".
   - no SPY provider + raising TICK provider → `market.tape.source == "none"`, light
     "unknown", reason contains "TICK read failed".
7. **chip/tooltip text** (public formatter, full fixture snapshot):
   - TICK fallback (fixture case 1, no SPY bars): chip ends "· tape fast"; tooltip line
     exactly `"Tape (last 30 min, TICK fallback): M5 range 567 vs 415 usual = fast (fast tape = levels fail more)."`.
   - SPY known (3 fast-range SPY bars): chip "· tape fast"; line `"Tape (last 30 min,
     SPY): M5 range 0.150 vs 0.106 usual = fast (fast tape = levels fail more)."`
   - source none (no SPY bars, TICK rows empty): chip has no "tape" part; line
     `"Tape (last 30 min): unknown (no SPY bars in the window)."`
   - calm SPY: chip "· tape calm".

Updated `tests/test_technical_integrity_rolling.py`:
- `_snapshot_at` adds the `market["tape"]` line (D9/D4 of this plan).
- `test_chip_and_tooltip_lead_with_the_now_reading_golden` now exercises the new
  chip/tooltip via the fixture's updated expected values.

## Steps

1. Write `.qo/recon.md` (done) and this plan (done at this step).
2. Write `tests/test_technical_integrity_tape.py` + the rolling-file `_snapshot_at`
   update + the fixture's expected case-1 chip/tooltip values. Run:
   `C:/Users/Aaron/TradingBotV3/.venv/Scripts/python.exe -m pytest -q
   tests/test_technical_integrity_tape.py tests/test_technical_integrity_rolling.py`
   with `QT_QPA_PLATFORM=offscreen`; save the failing output to `.qo/tests-red.txt`
   (expected failures: `tape_speed_light`/`tape_light`/`SESSION_HOUR_SPY_RANGE_NORMS`
   do not exist; chip/tooltip mismatch; monitor kwarg `spy_bars_provider` unknown).
3. Build: implement §Files 1–2, 6 in the order constants → `tape_speed_light` →
   `_spy_range_bar` → `tape_light` → `tick_range_light` wrapper → monitor →
   `_publish_snapshot` → `_rolling_now_view` → legacy line → CHANGELOG.
4. Run the two test files again (same command) +
   `C:/Users/Aaron/TradingBotV3/.venv/Scripts/python.exe -m ruff check scripts tests`;
   save to `.qo/build.txt`.
5. Self-review the `git diff` → `.qo/review.json`; fix blockers, re-review at most twice.
6. `.qo/report.md`, then stop.

## What "done" means

- `tape_speed_light` is generic (works for TICK points and SPY percent norms through
  `hour_norms` + `label`); `tick_range_light` is a thin wrapper whose public behavior is
  byte-for-byte what it was (all existing tick goldens and the parametrized threshold
  test pass unchanged).
- `tape_light` fallback order and fail-open monitor write are covered by the new tests
  and pass; `market.tick` is written exactly as before.
- Chip says "tape fast/normal/calm", omitted when source is "none"; tooltip names "SPY"
  or "TICK fallback"; goldens updated accordingly; raw fixture inputs untouched.
- legacy.py wires `spy_bars_provider` from the `latest_bars` cache only (no IB, no new
  import surface beyond the existing lazy `technical_integrity` import).
- Touched test files green, `ruff check scripts tests` green; whole suite not run (task
  rule: run only touched files).
