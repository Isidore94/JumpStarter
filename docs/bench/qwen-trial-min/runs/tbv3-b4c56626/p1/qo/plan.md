# Plan — trader-fit rank step 4: flag the M30 extended pullback

## Files

1. **NEW `scripts/master_avwap_lib/m30_extended_pullback.py`** — the whole new
   behaviour:
   - `target_session(moment) -> (opened, closed) | None` — today's session
     (market-local naive bounds, from `market_session.get_market_session_window`)
     when the market calendar says today is a session day and `moment >= opened`;
     otherwise the last COMPLETED session via
     `market_calendar.previous_session(market_date)` and its bounds. Any
     calendar/session failure -> `None` (fail closed; the caller leaves every
     row unknown).
   - `judge(bars, side, *, opened, closed, now, daily_bars)`:
     `cap = min(now, closed)`;
     `pullback_sma_reclaim.evaluate(bars, side=side,
     sma_length=pullback_sma_reclaim.M30_SMA_LENGTH, bar_minutes=30,
     armed_at=None, now=cap, daily_bars=daily_bars)`;
     `None` -> `(None, None)` (short tape, stale tape or missing data = unknown);
     else pick the LATEST fire with `bar_dt >= opened` (fires are already capped
     at `cap` by the completed-bar rule) -> `(True, fire)`; else `(False, None)`.
   - `_note(fire)` = `f"{fire.trigger} {fire.bar_dt:%Y-%m-%d %H:%M} SMA65
     {fire.sma:.2f}"` — the same shape the tag's evidence examples use.
   - `stamp_m30_extended_pullbacks(rows, *, ai_state=None,
     feature_rows_by_symbol=None, daily_frames_by_symbol=None, now=None,
     downloader=None) -> (flagged, unknown)`:
     - A row is EXTENDED when, on the merged input exactly as the Fit pass sees
       it (`trader_fit.fit_input(row, ai_state symbols entry, feature row)`),
       `trader_fit.hard_no_rules` returns `fired` non-empty and
       `set(fired) <= WAIVABLE_RULES`. Unknowns never count (missing input is
       not a hard no).
     - No extended rows -> return `(0, 0)` and make ZERO download calls.
     - Fetch the extended symbols' M30 tape with the caller's `downloader`
       (default `intraday_history._download`) in chunks of
       `intraday_history.DOWNLOAD_CHUNK_SYMBOLS` (50), `period =
       intraday_history.DEFAULT_PERIOD` ("1mo"), `interval =
       intraday_history.interval_label(30)`.
     - A chunk exception -> ONE `logging.warning` (never raised, the scan goes
       on); every row in that chunk gets `m30_extended_pullback = None`.
     - Missing/empty frame for a symbol -> that row is `None` (unknown); one
       warning per stamp call lists them.
     - Bars via `intraday_history.frame_to_bars(frame, now=cap,
       interval_minutes=30)` (completed, naive market-local); dip-gate D1 ATR
       bars from `daily_frames_by_symbol[symbol]` converted to dict bars (dt
       from the `datetime` column, NaN rows dropped, sorted) — same seam as
       the runner's `_d1_environment_bars`, no circular import.
     - Stamps: True -> `row["m30_extended_pullback"] = True` +
       `row["m30_extended_pullback_note"] = note`; False -> `... = False`
       (no note); unknown -> `... = None` (no note). Non-extended rows are
       not touched at all. Returns `(flagged_count, unknown_count)`.
2. **EDIT `scripts/master_avwap_lib/trader_fit.py`** — rename `_fit_inputs`
   (`:308`) to public `fit_input` and update its single caller (`:344`); same
   body, docstring says it is the merged input every fit read uses. Needed so
   the stamp classifies "only hard no's" on the identical view the Fit waives.
3. **EDIT `scripts/master_avwap_lib/runner.py`** — import at the top (next to
   the `.trader_fit` import, `:16`) and, immediately before
   `apply_trader_fit_ranking(priority_rows, ...)` (`:2651`, on the scan worker):
   ```python
   m30_flagged, m30_unknown = stamp_m30_extended_pullbacks(
       priority_rows,
       ai_state=ai_state,
       feature_rows_by_symbol=feature_rows_by_symbol,
       daily_frames_by_symbol=daily_frames_by_symbol,
   )
   if m30_flagged or m30_unknown:
       logging.info("M30 extended pullback: %d flagged, %d unknown.", m30_flagged, m30_unknown)
   ```
   No other runner change. STABLE replay and tracker backfill (legacy.py)
   never fetch: they call `apply_trader_fit_ranking` directly on rows that no
   stamp ever saw — pinned by a source scan.

## Untouched (task constraints)

`scripts/indicators/pullback_sma_reclaim.py` (reused as-is), the Pullback
alert, order/sizing code, `tests/test_trader_fit.py` and the existing
trader-fit fixtures and their expected ranks, `setup_tagging.py`,
`legacy.py`.

## Tests (NEW `tests/test_m30_extended_pullback.py`, all failing first)

Reuse the QDEL fixture tape (fire 09-23 06:30, SMA 10.9233) and fake
`_Frame`/downloader idiom; market-local Pacific test env, session 06:30-13:00:

1. **Fire in the open session** — now = 09-23 09:00, full QDEL tape: flag
   True, note contains `sma_reclaim_lrsi 2026-09-23 06:30 SMA65 10.92`;
   `trader_fit.compute_trader_fit` waives both extension rules, adds the
   20-point bonus, flag in `fit_flags`, score >= 0;
   `setup_tagging.derive_setup_tag_payload` carries
   `EXTENDED_PULLBACK_M30_LRSI_65_SMA` with the note as evidence.
2. **Fire yesterday -> measured False** — tape copy extended with 09-24
   M30 bars (closes kept near 10.7, below the SMA so no new fire), now =
   09-24 09:00: flag False, no waiver, no bonus, extension rule still fired.
3. **Short tape -> unknown, still a hard no** — 30-bar frame: flag None;
   `fit_rules` still contains `extended_3_closes`, `fit_waived_rules` empty,
   `fit_score < 0`.
4. **Failed fetch -> unknown, one warning** — downloader raises; two
   extended symbols both None; exactly one WARNING mentioning the M30 fetch;
   nothing raised.
5. **Non-extended rows untouched** — clean row + extended row: downloader
   called once with only the extended symbol; clean row has NO
   `m30_extended_pullback` key at all.
6. **Batched fetch** — 55 extended symbols -> exactly two downloader calls
   sized 50 and 5; 3 symbols -> one call.
7. **Session clock** — `target_session`: Wed 05:00 -> Tuesday's bounds;
   Wed 06:30 -> Wednesday's; Wed 14:00 -> Wednesday's; Sat 09:00 -> Friday's;
   Fri 05:00 -> Thursday's (expected bounds computed from
   `market_session` helpers, not hardcoded). End-to-end: pre-market
   now = 09-23 05:00 on the untouched QDEL tape -> measured False (last
   completed session = 09-22, no fire there); after-close now = 09-23 14:00
   -> True; forming-bar now = 09-23 06:45 -> False (06:30 bucket still
   printing).
8. **Scan placement pin** — runner source calls
   `stamp_m30_extended_pullbacks(` exactly once, on the line block
   immediately before the live `apply_trader_fit_ranking(priority_rows, ...)`
   call; `legacy.py` source never mentions it (STABLE replay and backfill
   therefore can't fetch).

## "Done" means

- All of the above tests pass on the new file; existing
  `tests/test_trader_fit.py` and `tests/test_pullback_dip_gate_golden.py`
  still pass (no behaviour moved out from under them).
- `ruff check scripts tests` clean.
- No whole-suite run (20 GB / 12 min forbidden by the job rules).

## Unclear points and how they were resolved (no user input allowed)

- **"Only hard no's" on which view?** The priority row lacks
  `previous_day_high/low` (only the symbol entry / feature row have them), so a
  row-level `hard_no_rules` would misclassify a row whose merged view also
  fires `below_prior_day_low`. Resolved: classify on the merged input, and to
  keep the stamp and the Fit on the same definition, `_fit_inputs` becomes
  public `fit_input` in `trader_fit.py`. (Also matches the task naming
  trader_fit.py among the touched files.)
- **Which trigger fires the flag?** The task says "the Pullback alert's own
  rule", i.e. `evaluate` — any of its three triggers. The flag is set when the
  LATEST qualifying fire in the judged session exists; its `trigger`, `bar_dt`
  and `sma` go into the note.
- **"Logged once"** = one warning per failed fetch CHUNK and one per stamp
  call listing frameless symbols — never one line per symbol in a 50-wide
  chunk, and never an exception.
- **Session walk-back** uses `market_calendar.previous_session` (holiday and
  weekend aware), not `intraday_history.last_completed_bucket`'s day-minus-one
  walk (which can land on a Sunday pseudo-session in pre-market).
- **`armed_at=None`** — the flag asks "did the pullback fire in this session",
  not "was the alert armed then"; the golden replay confirms QDEL still fires
  un-armed with identical numbers.
- **Daily bars for the dip gate** need no completion cap: `_DailyAtr.before`
  only reads sessions strictly before the dip day.
