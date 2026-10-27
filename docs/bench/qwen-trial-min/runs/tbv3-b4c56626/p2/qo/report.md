# Report — trader-fit rank step 4: flag the M30 extended pullback

## What changed

1. **NEW `scripts/master_avwap_lib/m30_extended_pullback.py`** — all new behaviour:
   - `target_session(moment)` — today's session (market-local naive bounds) once it
     has opened, else the last completed session via `market_calendar.previous_session`;
     any calendar/session failure -> `None` (fail closed, rows stay unknown).
   - `judge(bars, side, *, opened, closed, now, daily_bars)` — the Pullback alert's own
     rule, `indicators.pullback_sma_reclaim.evaluate` on the M30 65-SMA with the dip
     gate's ATR from D1 bars, completed bars only, capped at the session close;
     `True` = latest qualifying fire inside the session, `False` = measured no,
     `None` = unknown (short/stale tape, missing data).
   - `stamp_m30_extended_pullbacks(rows, *, ai_state, feature_rows_by_symbol,
     daily_frames_by_symbol, now, downloader) -> (flagged, unknown)` — only rows whose
     ONLY hard no's are the two extension rules (judged on `trader_fit.fit_input`, the
     same merged view the Fit pass uses) are touched; they ride ONE batched M30 fetch
     (`intraday_history._download` by default, chunks of
     `intraday_history.DOWNLOAD_CHUNK_SYMBOLS` = 50, `period="1mo"`, `interval="30m"`,
     on the scan worker). Flag lands on the row as `m30_extended_pullback`
     (`True`/`False`/`None`) plus `m30_extended_pullback_note` evidence when flagged.
     Non-extended rows are never touched and never fetched.
   - **Error containment (review blocker, fixed this round):** previously only the
     downloader call was guarded; `frame_to_bars`, `_daily_bars` and `judge` could
     raise out of the stamp and fail the whole scan. Now the per-symbol conversion
     (`frame_to_bars` + `_daily_bars`) is wrapped: a malformed tape sets every row of
     that symbol to `None`, counts them unknown, logs ONE warning naming the symbol,
     and moves on to the next symbol. Each per-row `judge` call is wrapped separately:
     one unreadable row is `None` + one warning, sibling rows of the same symbol are
     judged normally. Neither guard weakens the fetch guard (chunk failure still
     leaves the whole chunk unknown with one warning).
2. **EDIT `scripts/master_avwap_lib/trader_fit.py`** — `_fit_inputs` renamed to public
   `fit_input` (single caller updated in `apply_trader_fit_ranking`; body unchanged) so
   the stamp and the Fit classify "only hard no's" on the identical merged input.
   No other rule, waiver, bonus or fixture expectation changed — the waiver of
   `above_third_band`/`extended_3_closes`, the `FLAG_EXTENDED_PULLBACK` flag and the
   `EXTENDED_PULLBACK_POINTS` bonus already existed and are driven by the flag.
3. **EDIT `scripts/master_avwap_lib/runner.py`** — one import plus one call block in
   `_run_master_impl` immediately before `apply_trader_fit_ranking(priority_rows, ...)`,
   on the scan worker, passing `daily_frames_by_symbol`; an INFO line when anything
   was flagged or unknown. STABLE replay and the tracker backfill live in `legacy.py`,
   which never imports or calls the stamp, so they never fetch.

## Untouched (task constraints)

`scripts/indicators/pullback_sma_reclaim.py` (reused, unmodified), the Pullback alert
itself, order/sizing code, `tests/test_trader_fit.py` and the existing trader-fit
fixtures/expected ranks, `setup_tagging.py`, `legacy.py`.

## Test results

- `tests/test_m30_extended_pullback.py` (new, 19 tests): **19 passed in 2.01s, exit 0**
  (`QT_QPA_PLATFORM=offscreen`, TradingBotV3 venv). Covers: fire in the open session
  (flag + waiver + 20-point bonus + `EXTENDED_PULLBACK_M30_LRSI_65_SMA` tag with the
  note as evidence, against the QDEL fixture tape: `sma_reclaim_lrsi 2026-09-23 06:30
  SMA65 10.92`), fire yesterday (measured False, no waiver/bonus), short tape
  (None, still a hard no, negative score), failed fetch (both symbols None, exactly
  one warning), **malformed tape (this round's blocker): a downloader frame whose
  `iterrows` raises ValueError -> that row None + one warning naming the symbol, the
  other symbol judged True, stamp does not raise, `(flagged, unknown) == (1, 1)`**,
  non-extended rows untouched (no key, zero downloader calls), extended-only check on
  the merged Fit input (`below_prior_day_low` disqualifies), one batched fetch in
  chunks of 50/5 and one fetch for 3 symbols, no extended rows -> zero fetches,
  `target_session` clock cases (pre-market/open/after-bell/Saturday/Friday pre-market,
  expected bounds from the `market_session` helpers, not hardcoded), end-to-end clock
  cases (pre-market -> last completed session, after-close -> today, forming 06:30
  bucket -> measured False), and the scan-placement pin (stamp called exactly once,
  immediately before the Fit pass; absent from `legacy.py`).
- Lint: `ruff check scripts tests` -> **All checks passed (exit 0)**. Note:
  `runner.py` is in the project's `extend-exclude` (it pulls ~1,591 names from
  `legacy` into `globals()` at import time, `runner.py:57-63`), so passing it as an
  explicit ruff argument produces hundreds of false F821s; the project-standard
  `ruff check scripts tests` is the correct gate and is clean.

## What was skipped

- No full-suite run (forbidden by the job rules: 20 GB / 12 min); the touched test
  file plus the untouched existing `test_trader_fit.py` expectations (exercised
  inside the new file via `compute_trader_fit`) cover the change.
- No commit/push (job rules: no git history/commit commands here).
- The Fail-before-fix evidence for the original build is in `.qo/tests-red.txt`.

## Open doubts

- `target_session`'s "has opened" test uses `moment >= opened` on the market-local
  clock; a machine clock badly skewed backwards would judge on the previous session
  instead of failing — acceptable because it still only ever judges completed
  sessions.
- The per-row `judge` guard logs one warning per failing row of a symbol (not per
  symbol); a deterministically failing `evaluate` on an N-row symbol would log N
  lines. Kept per-row so one bad side string cannot poison its siblings; no known
  input currently triggers it.
- The runner logs the `(flagged, unknown)` summary at INFO only when non-zero;
  quiet scans log nothing, by design.
