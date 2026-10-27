Review blocker (fix this, nothing else):

scripts/master_avwap_lib/m30_extended_pullback.py: in stamp_m30_extended_pullbacks only the downloader call is inside try/except. frame_to_bars, _daily_bars and judge run outside it, so one malformed or odd tape (for example a frame whose rows raise ValueError while being converted) raises out of the stamp and fails the whole scan. The brief says a bad tape is None (unknown, logged once), never a failed scan. Wrap the per-symbol conversion and judge in a try/except that sets that row to None and logs once, and add one test with a downloader that returns a frame whose conversion raises, asserting the row is None, the other rows are unaffected and the stamp does not raise.

Run tests/test_m30_extended_pullback.py and ruff on the changed files, then stop.
