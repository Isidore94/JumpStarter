# Plan — price the screen's net edge multiplicatively

Task in one line: replace the candidate's `net_edge_pct`
(`expected_move_pct - breakeven_move_pct`, two percentages measured against
different references) with the real multiplicative round trip
`sell_proceeds(vwap · bid_walk / close) / ask_walk - 1`, keeping the book's
shape through the reversion (stated in a comment).

## What is unclear or wrong in the task, and how it was resolved

1. **"A flat book already at value must net exactly minus the tax."** A flat
   book at value can never become a *candidate* through `run_screen` (expected
   move 0 < breakeven ~3.375%, gate at `screen.py:299`), so the flat-book
   assertion cannot be tested through the pipeline. Resolved: the formula is
   exposed as a named module-level function in `screen.py` and the flat-book
   test calls it directly.
2. **"Find the helpers it needs."** The only helper needed already exists:
   `CostModel.sell_proceeds` (`costs.py:117`, taker exit → tax only). No
   changes to `costs.py`.
3. **Where the formula lives.** Decided: a public function
   `net_edge_pct(*, vwap, close, ask_walk, bid_walk, costs)` in `screen.py`,
   added to `__all__`. It is a screen-level thesis (the book keeps its shape
   as price reverts to anchored value), not a fee/impact primitive, so it does
   not belong on `CostModel`. At the one call site all inputs are known
   positive (gate guarantees, see recon), so the function just guards against
   non-positive/None input and returns None (UNKNOWN, the codebase idiom).

## Files

| File | Change |
| --- | --- |
| `src/evescreener/screen.py` | Add `net_edge_pct(...)` helper; in `run_screen` compute it from `bands.vwap`, `reference` (close), `ask_prices[tiers[0]]`, `bid_prices[tiers[0]]`, `costs` and use it for the `Candidate.net_edge_pct` field (replaces line 342). |
| `tests/test_screen_digest.py` | Two new tests (below). No existing test edited. |

Explicitly **not** touched: the other gates (`screen.py:291-301`), the
`expected_move_pct` field and gate, `tier_breakevens`, `digest.py` output
format, the sort at `screen.py:366`, `costs.py`, all config keys.

## Tests (written first, red before the fix)

Both in `tests/test_screen_digest.py`, reusing the module's existing
`NOW`/fixtures and local helpers for the hand-crafted bars (see recon's
verified scenario — no RNG, every number exact):

1. `test_flat_book_at_value_nets_exactly_minus_the_tax`
   - `net_edge_pct(vwap=V, close=V, ask_walk=V, bid_walk=V, costs)`
     `== pytest.approx(-costs.sales_tax_pct, abs=1e-12)` → −3.375.
   - Also the asymmetric-but-flat case `ask_walk == bid_walk == close != vwap`
     is *not* asserted here; the spec's flat case is the one pinned.
2. `test_a_wide_spread_no_longer_ranks_first`
   - Bars: type 37 (WIDE) close 700k/1.3M/700k, type 38 (TIGHT)
     close 753k/1.255M/753k (bars 180–189 the high leg), eight fillers
     constant at 500k. Composite: 10 types on a 20-bar sine wobble (20-day
     move exactly 0 → power index 0 → RRS 0). Books: 37 @ 760k/700k,
     38 @ 757k/755k.
   - Asserts: exactly two candidates; order `[38, 37]` (the wide book no
     longer ranks first); each row's `net_edge_pct` equals the task's formula
     re-derived in the test from that row's own `close`, the known book walk
     prices and the known vwap (`target_bid = vwap·(bid/close)`,
     `proceeds = target_bid·(1 − tax/100)`, `edge = proceeds/ask − 1`),
     `pytest.approx` tight; and the wide book's edge is strictly below the
     tight book's.
   - Comment records the old behaviour: under `expected_move − breakeven`
     this exact scenario ranked 37 first (+30.4934 vs +29.5663).

Redness mechanism: test 1 fails on `ImportError` (the helper does not exist)
and test 2 fails on order + values (old formula gives `[37, 38]`).

## Build

1. Add the helper (with the shape-preservation assumption in its docstring/
   comment, per the task) and the call in `run_screen`; update `__all__`.
2. Run: `PYTHONPATH=src python -m pytest -q tests/test_screen_digest.py
   tests/test_costs.py` then the full `PYTHONPATH=src python -m pytest -q`,
   then `python -m ruff check .` and `python -m ruff format --check .`
   (the repo gate, `CLAUDE.md`). Save outputs to `.qo/build.txt`.

## Done means

- `.qo/tests-red.txt` captured before the fix; both new tests red, all others
  green.
- After the fix: full suite green, ruff clean, both new tests green.
- `.qo/review.json` GO (self-review by reproduction: revert the one-line
  change to prove the new tests fail; re-derive the wide/tight numbers by
  hand from the scenario inputs).
- `.qo/report.md` written; then stop.
