# Report — P&L before commissions + commissions on closed trades

Done. `.qo/` stages: `recon.md` → `plan.md` → `tests-red.txt` → `build.txt` → `review.json` (GO) → this report.

## What changed

- **`tradertax/gains.py`** — display-only bookkeeping next to the existing cost math:
  - `_Pool.comm`: commissions held in a pool (long: buy commissions folded into ACB; short: the
    short-open's sell commission, which is already deducted from pool cost at `gains.py:249`).
  - `Realized.commissions_cad`: for each close, the pool's commission pro rata to the quantity
    closed (`frac`, the same fraction already used for ACB/proceeds) plus the closing trade's own
    commission (sell outlay, or the cover buy's commission).
  - Four pool paths updated (cover short, buy long, close long, open short); full-close resets now
    zero `comm` alongside `qty`/`cost`. No existing value (gain, ACB, proceeds, outlays, warnings)
    is computed differently.
- **`tradertax/summary.py`** — four new `YearReport` fields, filled from the same events/taxable
  events already used for `total_pnl`/`taxable_pnl`:
  `total_pnl_before_commissions = Σ(gain + commissions)`, `commissions_on_closed = Σ commissions`,
  and the taxable variants. Because `before = gain + commissions` per event, the required
  identities hold exactly. Broker `FEE` rows are `FEE`-kind, never enter `compute_gains`, and stay
  in `rep.broker_fees` (separate expense line) — excluded by construction.
- **`tradertax/ui/pages.py`** — new KPI card "P&L before commissions" after "Total P&L"; value is
  the all-accounts before-commission P&L (signed colour), sub-line shows total commissions and the
  taxable share with "are already inside the P&L - do not add them again as an expense".
- **`tests/test_summary.py`** — new `test_pnl_before_commissions_and_commissions_on_closed` on the
  existing fixtures: hand-derived per close at the 1.37 fixture rate (AAPL 1450 USD before /
  11.90 comm, TSLA short 200 / 2.00, TFSA NVDA 300 / 9.90; SHOP.TO and open options never close),
  asserting both the absolute CAD numbers (taxable 2260.50 before / 19.043 comm; total 2671.50 /
  32.606), both identities, and that `taxable_pnl` still equals the after-commission 1636.10×1.37.
- **`tests/test_ui_smoke.py`** — asserts the new card has a value (`!= "-"`).

## Test results

- Red (pre-fix), saved in `.qo/tests-red.txt`: `test_pnl_before_commissions_and_commissions_on_closed`
  → `AttributeError: 'YearReport' object has no attribute 'taxable_pnl_before_commissions'`;
  `test_main_window_refreshes` → `KeyError: 'before_commissions'`.
- Green (post-fix), saved in `.qo/build.txt`: `pytest tests -q` (offscreen) → **48 passed**
  (47 pre-existing, unmodified, + 1 new); `ruff check .` → **All checks passed!**.
- Self-review: `reviewer` agent by reproduction → **GO**, no blockers (`.qo/review.json`). It
  re-derived the fixture numbers independently, re-proved red on a baseline sandbox
  (2 failed / 46 passed), and confirmed the tax side and file scope are untouched.

## What was skipped (decisions, see `plan.md`)

- `export.py` (CSV/markdown), the UFile sheet, and the Gains page were not updated — the task asks
  for the report fields plus the Summary card; keeping the change small.
- No per-symbol breakdown of commissions in the report (`_by_symbol` untouched).

## Open doubts / notes

- **Exercised/assigned options**: when an option rolls into its share trade (`gains.py:253-258`),
  the option events are deleted and only net gain is rolled in, so a rolled option's commission is
  not in `commissions_on_closed`. The before-minus-commissions identity still holds (the rolled
  value is net of that commission). The fixtures don't exercise this; it would only affect the
  commission *total*, never the P&L.
- The identity assertions are tautological by construction (reviewer advisory); the absolute-value
  assertions are what pin the numbers, and the task explicitly required the identities.
- The 11th card leaves the last grid row with a single card — cosmetic.
- Card colour is signed on the before-commission figure itself; when commissions flip the sign
  (before positive, after negative) the two P&L cards can show different colours — that is the
  intended message (commissions are what made it worse).
