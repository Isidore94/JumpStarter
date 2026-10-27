TASK

Goal: trader-fit rank step 4: flag the M30 extended pullback (the trader's favourite setup). Rows whose only hard no's are above_third_band / extended_3_closes get one batched M30 yfinance fetch (chunks of 50, on the scan worker), then the Pullback alert's own rule (pullback_sma_reclaim.evaluate on the M30 65-SMA, D1 bars for the dip gate's ATR). Flag only when the fire's bar is in today's session once it has opened, else the last completed session (evaluate completed bars only, capped at that session's close). A failed fetch or short tape = None (unknown, logged once), never a failed scan; rows that are not extended are never touched or fetched. The runner stamps the flag right before the Fit pass, which waives the two extension rules and adds the bonus; the setup tag EXTENDED_PULLBACK_M30_LRSI_65_SMA follows. STABLE replay and tracker backfill do not fetch, so extended rows stay hard no's there.
Done when: tests on synthetic M30 tapes cover fire in session (flag + waiver + bonus + tag), fire yesterday (no flag), missing bars (None, still a hard no), failed fetch (all unknown, one warning), non-extended rows untouched, one batched fetch, and the session-clock cases; run_tests.py/pytest and ruff green.
Files: new scripts/master_avwap_lib/m30_extended_pullback.py; scripts/master_avwap_lib/trader_fit.py (the hard no's, waiver, bonus); scripts/indicators/pullback_sma_reclaim.py (evaluate, reuse, do not change); find the runner's Fit pass and intraday_history._download.
Don't touch: order/sizing code, the Pullback alert itself, the existing trader-fit fixtures and their expected ranks.
Pattern: the other trader_fit rules and how the scan worker batches yfinance downloads.

You already worked on this task in this checkout: your earlier changes are in the working tree and your notes are in
`.qo/`. The lead ran the tests and found this:

Review blocker (fix this, nothing else):

scripts/master_avwap_lib/m30_extended_pullback.py: in stamp_m30_extended_pullbacks only the downloader call is inside try/except. frame_to_bars, _daily_bars and judge run outside it, so one malformed or odd tape (for example a frame whose rows raise ValueError while being converted) raises out of the stamp and fails the whole scan. The brief says a bad tape is None (unknown, logged once), never a failed scan. Wrap the per-symbol conversion and judge in a try/except that sets that row to None and logs once, and add one test with a downloader that returns a frame whose conversion raises, asserting the row is None, the other rows are unaffected and the stamp does not raise.

Run tests/test_m30_extended_pullback.py and ruff on the changed files, then stop.

Fix it: change code and tests as needed, run the test files you touched and lint (Commands in CLAUDE.md), then
rewrite `.qo/report.md`. Stop when it is written.
