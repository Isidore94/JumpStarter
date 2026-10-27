# Recon — trader-fit rank step 4: flag the M30 extended pullback

Branch `main`, single commit `2a44ed5 baseline`. All evidence file:line.

## What already exists (no change needed)

- `scripts/master_avwap_lib/trader_fit.py`
  - `EXTENDED_PULLBACK_POINTS = 20.0` (`trader_fit.py:55`); rule names 77-79;
    `WAIVABLE_RULES = frozenset({above_third_band, extended_3_closes})` (`:81`);
    `FLAG_EXTENDED_PULLBACK = "extended_pullback"` (`:83`).
  - `hard_no_rules(row) -> (fired, unknown)` (`:151`): `above_third_band` fires on
    `current_band_zone` UPPER_3/LOWER_3 per side; `below_prior_day_low` on
    `last_close` vs `previous_day_low`/`previous_day_high`; `extended_3_closes` on
    `extended_closes_outside_band2 >= 3`. Missing input -> unknown, never fired.
  - Bonus term when `row.get("m30_extended_pullback") is True` (`:252-253`);
    waiver + flag in `compute_trader_fit` (`:271-274`); `below_prior_day_low`
    survives the waiver (`:273` only removes `WAIVABLE_RULES`).
  - `apply_trader_fit_ranking(rows, ai_state, feature_rows)` (`:323`) merges inputs
    via `_fit_inputs(row, symbol_entry, feature_row)` (`:308-320`, row wins) —
    **private, one caller** (`:344`). This is the merge the stamp must reuse, so it
    gets renamed public `fit_input`.
- `scripts/master_avwap_lib/setup_tagging.py`: `EXTENDED_PULLBACK_TAG =
  "EXTENDED_PULLBACK_M30_LRSI_65_SMA"` (`:19`); tag + evidence added right after
  the primary tag when the flag is True (`:182-187`).
- `scripts/indicators/pullback_sma_reclaim.py` (reused, untouched):
  - `M30_SMA_LENGTH = 65` (`:99`), `STALE_AFTER = timedelta(hours=24)` (`:110`),
    `TRIGGERS` incl. `sma_reclaim_lrsi` / `reclaim_then_lrsi` / `sma_retest` (`:84`).
  - `evaluate(bars, *, side, sma_length, bar_minutes, armed_at, now,
    episode_state, companion_bars, companion_minutes, daily_bars, d1_atr)`
    (`:481`). Staleness check on the last completed bar (`:511`); completed-bar
    filter via `completed_bars.is_completed_bar`; dip gate = touch within
    0.2 × D1 Wilder ATR(20) or close-break+reclaim within 15 bars, bear flip;
    `now` is the only clock, so it is replay-invariant.
  - `Fire` fields: `trigger` (`:140`), `bar_dt` (`:142`), `sma` (`:143`),
    `cross_bar_dt` (`:152`), `dip_bar_dt` (`:158`), `d1_atr` (`:160`).
- `scripts/master_avwap_lib/legacy.py`:
  - STABLE replay `build_completed_bar_priority_rows` (`:28017`) calls
    `apply_trader_fit_ranking` at `:28082` with comment at `:28066-28068`
    ("must not spend another broker budget ... pretend an intraday enrichment
    was completed-bar D1 evidence").
  - Tracker backfill `backfill_setup_tracker_from_recent_sessions` (`:28089`)
    calls it at `:28279`.
  - `sync_study_row_ranking_fields` already copies both m30 fields to study rows
    (`:30129-30130`); canonical payload already carries them (`:35663-35664`).
- `scripts/intraday_history.py` (reused, untouched):
  - `_download(symbols, *, period, interval)` (`:120`) -> `{symbol: frame|None}`,
    one guarded `yahoo_download.download` per chunk, `prepost=False`.
  - `DOWNLOAD_CHUNK_SYMBOLS = 50` (`:110`), `DEFAULT_PERIOD = "1mo"` (`:92`),
    `interval_label(30) == "30m"` (`:101-103`).
  - `frame_to_bars(frame, *, now, interval_minutes)` (`:286`): yfinance frame ->
    completed naive market-local bar dicts, filtered through the one
    completed-bar rule.
- `scripts/market_calendar.py`: `is_session`, `previous_session` (weekend +
  holiday aware, ET), `SessionCalendarError`; valid 2000-01-01..2032-12-31.
- `scripts/market_session.py`: `get_market_session_window(reference)` (`:134`)
  returns `market_date` (ET date) + aware `open_local`/`close_local`;
  `get_market_session_open_naive/close_naive` (`:218/:226`). Session 06:30-13:00
  market-local (Pacific test env).
- `scripts/completed_bars.py`: `is_completed_bar` — `bar_start + bar_minutes <= now`
  (inclusive boundary).

## What the runner has at the Fit pass (the only call-site change)

`_run_master_impl` (`scripts/master_avwap_lib/runner.py:566`-ish; the whole region
lines 1185-3035 is one function):

- `daily_frames_by_symbol` built per symbol at `runner.py:1228`
  (`daily_frames_by_symbol[sym] = df.copy()`; the daily frame has a `datetime`
  column, `runner.py:1230-1231`).
- Fit pass at `runner.py:2642-2651`:
  ```python
  apply_expected_r_ranking(priority_rows, ai_state, feature_rows_by_symbol, ...)
  # Trader fit (trader 2026-10-05): `score` becomes the Fit; ...
  apply_trader_fit_ranking(priority_rows, ai_state, feature_rows_by_symbol)
  ```
  The stamp call goes immediately before line 2651, on the scan worker thread.
- Priority rows carry `current_band_zone` (`:2171`),
  `extended_closes_outside_band2` (`:2172`), `last_close` (`:2173`) — but NOT
  `previous_day_high/low` (those live only in the symbol entry, `:1905-1906`, and
  the feature row, `:2283-2284`; `runner.py:3072-3073` is just the CSV
  `feature_columns` list). => "extended-only" classification must use the merged
  view, exactly as `_fit_inputs` does.
- `_d1_environment_bars(frame)` (`:391`) converts the daily frame to dict bars
  (`dt` from the `datetime` column).

## Test assets

- `tests/fixtures/pullback_dip_gate_real_tapes_v1.json` +
  `tests/test_pullback_dip_gate_golden.py`: QDEL SHORT fires
  `sma_reclaim_lrsi`, `fire.bar_dt = 2026-09-23 06:30` (market-local naive),
  `fire.sma = 10.9233`, cross 09-22 12:30, dip 09-21 07:30, bear flip 09-21
  08:00, `d1_atr = 0.9149`; fixture `now = 2026-09-23T07:07:24`; 275 M30 bars
  (last 09-23 07:00 close 10.675), 341 D1 bars. 09-23 is a Wednesday. Verified by
  replaying `evaluate` on the fixture with `armed_at=None`: exactly one fire,
  same numbers.
- Fake-frame idiom: `_Frame` (iterrows -> (stamp, {Open,High,Low,Close}),
  `empty`, `columns=None`) + fake downloader `(symbols, **kwargs) ->
  {sym: frame}` as in `tests/test_pct1_pullback_cache.py` /
  `tests/test_rv_h1_history_refresh.py`. Naive market-local stamps are fine:
  `intraday_history._market_local` keeps naive stamps as-is.
- Source-scan pin idiom: `test_trader_fit.py:88-97`
  (`inspect.getsource(runner)`).

## Facts the design hinges on

1. `evaluate` with `now=cap` only reports fires on bars completed <= cap, so
   "judge the session" = "pick the latest fire with `bar_dt >= session open`".
2. Staleness: last completed M30 bar + 30 min must be within 24 h of `now`
   (`pullback_sma_reclaim.py:511`) or `evaluate` returns None (unknown).
3. `market_calendar.previous_session` handles weekends/holidays; a plain
   "yesterday" walk would land on a Sunday. The previous session's close is
   always strictly before the reference moment (ET date == market-local date for
   US markets), so no extra guard is needed beyond fail-closed on error.
4. Neither STABLE replay nor backfill has an M30 fetch path of its own, and the
   Fit pass they run receives rows with no `m30_extended_pullback` key, so they
   stay hard no's there for free; the pin is a source-scan that
   `stamp_m30_extended_pullbacks` appears nowhere in `legacy.py`.
