# Report — tape speed light (SPY M5 range vs session-hour norm, TICK fallback)

## What changed

**`scripts/technical_integrity.py`**
- New constants: `TAPE_LIGHT_SCHEMA`, `TAPE_LIGHT_WINDOW_MINUTES` (30),
  `TAPE_LIGHT_STALE_MINUTES` (15), `TAPE_LIGHT_MIN_BARS` (3), `TAPE_CALM_RATIO` (0.8),
  `TAPE_FAST_RATIO` (1.25), and `SESSION_HOUR_SPY_RANGE_NORMS` — SPY M5
  (high-low)/close*100 by session hour, **derived from the 4 local sessions ending
  2026-10-05** (2026-09-30, 10-01, 10-02, 10-05; 78 completed bars each) with a
  comment stating it is a stub of the 30-session target (derivation numbers in
  `.qo/recon.md` sec 7).
- `tape_speed_light(bars, *, as_of, hour_norms=SPY norms, label="SPY", window_minutes)`
  — the generic completed-M5 range light: pre-parsed `(start, end, range,
  end-as-stamped)` tuples (None skipped), 30-min completed-bar window
  (`start < bar_end <= as_of`), per-bar session-hour norm, light
  calm / normal / fast / unknown with the task's exact thresholds, reasons
  "no {label} bars in the window" / "newest {label} bar is older than 15 minutes" /
  "fewer than 3 {label} bars in the window".
- `tick_range_light()` is now a **thin wrapper** over it (`map(_tick_bar, rows)` +
  TICK norms + label "TICK"), keeping the historical schema, the "wide" label and the
  1-decimal range rounding — published snapshots stay comparable; all pre-existing
  TICK goldens pass untouched.
- `_spy_range_bar(row)` — parses both the bot's cached `IbBar` objects (attribute
  shape, naive market-local stamps) and Mapping rows (`start`/`dt`/`datetime` +
  high/low/close); unreadable / non-finite / `close <= 0` / `low > high` → None
  ("unknown, never a guess").
- `tape_light(spy_light, tick_light)` — source "SPY" when the SPY light is known;
  else source "TICK" with the TICK light (wide → fast, values copied); else source
  "none", light unknown, reason = the SPY reason (fallback "no tape reading").
- Monitor: `__init__` gains `spy_bars_provider` (default None = no SPY source);
  `_publish_snapshot` writes `market.tape` in its own fail-open try/except (a raising
  provider yields a failed-SPY light dict that falls through to the TICK light),
  after the **unchanged** `market.tick` block; guiding comment extended.
- `_rolling_now_view`: chip now reads "· tape {calm|normal|fast}" from `market.tape`
  (omitted when source is none); the tooltip line names "SPY" or "TICK fallback" and
  formats ranges in 3 decimals (SPY percent) or 0 (TICK points); unknown line carries
  the reason. Snapshots without a `tape` block render as before.

**`scripts/bounce_bot_lib/legacy.py`** — `_get_technical_integrity_monitor()` passes
`spy_bars_provider=lambda: (getattr(self, "latest_bars", None) or {}).get("SPY|5 D|5 mins") or []`
— the in-memory SPY M5 cache only, never IB (the task's explicit one-line change in an
ask-first file).

**Tests**
- New `tests/test_technical_integrity_tape.py` (25 tests): thresholds
  calm/normal/fast vs the SPY hour-1 norm; attribute- and Mapping-shaped bars;
  unknown reasons (empty / <3 bars / stale newest end / pre-open hour / unparseable
  rows); completed-bar and window edges; `tape_light` fallback order incl.
  failed-SPY and `None` inputs; wrapper contract (schema, "wide", 1-decimal
  re-round, ratio) plus generic/wrapper parity; monitor fail-open (raising SPY
  provider → TICK fallback; SPY bars → source SPY; everything unknown → source
  "none" with SPY reason, `market.tick` untouched); chip/tooltip text for SPY known,
  SPY calm, TICK fallback and source-none.
- `tests/test_technical_integrity_rolling.py`: `_snapshot_at` now publishes
  `market.tape` (no SPY bars in the fixture → TICK fallback / none).
- `tests/fixtures/technical_integrity_rolling_v1.json`: **raw inputs
  byte-identical** (sha256 stays valid); only case-1 expected chip
  ("… · tape fast") and tooltip line ("Tape (last 30 min, TICK fallback): M5 range
  567 vs 415 usual = fast …") updated, plus the `intentional_difference` note.
- `CHANGELOG.md`: one line (2026-10-27).

## Test results

- Touched files: `tests/test_technical_integrity_tape.py` +
  `tests/test_technical_integrity_rolling.py` — **41 passed** (red first: 27 failed /
  14 passed, saved in `.qo/tests-red.txt`).
- Adjacent verification (same module, not touched): `tests/test_technical_integrity.py`
  — **25 passed**.
- `ruff check scripts tests` — **All checks passed** (full log in `.qo/build.txt`).
- Whole suite not run, per the task's command rules.

## Self-review

`.qo/review.json` — verdict **GO**, no blockers. Notable advisory: the stale check
uses the newest bar's **end** (same as the original TICK light); a first-draft test
assumed the start and was corrected before going green.

## Skipped / not done

- No `STATUS.md`, `docs/RULES.md`, `docs/GATES.md`, `docs/README.md` updates: nothing
  live changed (branch work), no rule governs this light, no Markdown added/moved.
- No merge, no commit, no desk restart — out of scope for this task window.
- `test_ti_chain_backfill.py` / `test_technical_integrity_sidecar.py` /
  `test_technical_integrity_replay.py` (other monitor-construction files) were not run:
  the monitor change is a new optional kwarg with a `None` default, exercised by the
  touched files; the two most affected files were run instead.

## Open doubts

1. **4-session norm stub.** The task asked for 30 sessions ending 2026-10-05; only 4
   full SPY sessions exist in the local store. The constant is clearly labeled a stub
   ("to be re-derived when that history is available") — re-deriving is a one-command
   job once 30 sessions are on disk.
2. **Pre-change snapshots on disk** (e.g. consumed overnight) have no `market.tape`:
   they render without a light in the chip until the next publish. Transient; no chip
   strings are persisted.
3. Hour-0 SPY norm (0.1278) has the widest per-session spread (0.089–0.194) of the
   seven hours — expected for the open hour, but another reason the 30-session
   re-derivation matters.
