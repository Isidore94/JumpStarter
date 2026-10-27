# Report — multiplicative net edge for the screen

## What changed

- **`src/evescreener/screen.py`**
  - New keyword-only helper `net_edge_pct(*, vwap, close, ask_walk, bid_walk, costs)`
    (`screen.py:154`, exported via `__all__`). It prices the real round trip
    multiplicatively instead of subtracting two percentages measured against
    different references: `target_bid = vwap * (bid_walk / close)`, then
    `net_edge = sell_proceeds(target_bid, maker=False) / ask_walk - 1`. The
    shape-preservation assumption — the book keeps its shape as the price
    reverts to anchored value, so the bid walk scales by the same factor the
    close does — is stated in the helper's docstring and at the call site.
    Missing/non-positive inputs return None (UNKNOWN), matching
    `breakeven_move_pct`'s guard style; `CostModel.sell_proceeds`
    (`costs.py:117`) is the only helper needed, and `costs.py` is untouched.
  - `run_screen` now uses it for the candidate's `net_edge_pct` field
    (`screen.py:381`), computed from `bands.vwap`, the close, and the
    smallest-tier ask/bid walk prices — the same inputs the gate and
    `price_round_trip` use. It replaces the old
    `net_edge_pct=(expected_move - smallest.breakeven_move_pct)`.
- **`tests/test_screen_digest.py`** — two new tests, no existing test edited:
  - `test_flat_book_at_value_nets_exactly_minus_the_tax`: a book with
    ask = bid = close = vwap nets exactly `-sales_tax_pct` (−3.375 at
    Accounting V), pinned to `abs=1e-12`.
  - `test_a_wide_spread_no_longer_ranks_first`: two hand-crafted, RNG-free
    candidates (exact fixed-point bars; see `.qo/recon.md` for the scenario)
    where the wide book (37: 700k/1.3M legs, book 760k/700k) previously
    ranked first under the old arithmetic (+30.4934 vs +29.5663). With the
    new pricing the tight book (38: 753k/1.255M legs, book 757k/755k) ranks
    first (+28.4930 vs +27.1382). The test asserts the order `[38, 37]`,
    re-derives the formula independently for each row, and asserts wide < tight.

## Explicitly not touched (per task)

The other gates (`screen.py:330-340`), the `expected_move_pct` field and its
gate, `tier_breakevens`, `digest.py`'s output format, the candidate sort
(`screen.py:405`), and all of `costs.py`. `CLAUDE.md` shows a diff only
because the harness prepended its orchestration rules before this job; it was
not edited by me.

## Test results

- Red (before the fix): `.qo/tests-red.txt` — new module import fails
  (`ImportError: cannot import name 'net_edge_pct'`), and with the import
  satisfied the ranking assertion fails against the live formula
  (`[37, 38] != [38, 37]`, verified in the probe before the fix).
- Green (after the fix), full gate:
  - `PYTHONPATH=src python -m pytest -q` → **259 passed, 7 deselected**
    (network tests excluded by the default marker).
  - `python -m ruff check .` → All checks passed.
  - `python -m ruff format --check .` → 73 files already formatted.
  - Output: `.qo/build.txt`.

## Self-review (reproduction)

- Reverting only the call site to the old subtraction makes
  `test_a_wide_spread_no_longer_ranks_first` fail with exactly
  `assert [37, 38] == [38, 37]`; the flat-book test keeps passing (it guards
  the helper directly). Restored.
- Every scenario number re-derived by hand and matched the pipeline's floats:
  wide `1,000,000 · (700,000/700,000) · (1 − 0.03375) / 760,000 − 1`
  = +27.1382%, tight +28.4930%; old +30.4934% / +29.5663%.
- Verdict: `.qo/review.json` — GO, no blockers.

## What I skipped / open doubts

- Skipped: changing the digest or any display text (format is frozen per the
  task); touching `config.screen.min_net_edge_pct` (defined but unused by
  `run_screen` today — a separate decision, not part of this task).
- Open doubt (inherent to the task's formula, not to this change): the
  shape-preservation assumption treats a 40% spread as scaling with the
  reversion just like a 2% one; for very wide books the true reversion bid
  may differ from the scaled walk. The formula is exactly what the task
  specified, and the comment states the assumption so it can be revisited
  with measured evidence.
- The scratch probes used to design the scenario (`.qo/scratch/`) were
  removed before the final gate; the scenario is fully documented in
  `.qo/recon.md` and reproducible from the test itself.
