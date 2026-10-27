# Plan — P&L before commissions + commissions on closed trades

## Approach

Track commissions inside each ACB pool alongside price (display-only bookkeeping; no cost,
proceeds, gain, ACB or UFile arithmetic changes), attribute to each close event the
commissions belonging to the quantity it closes — buy commissions held in the pool pro rata
plus the trade's own commission — and aggregate two new totals (all accounts, taxable share)
in the year report, then show one new KPI card.

Because `before = gain + commissions` per event by construction, the required identities
`total_pnl_before_commissions - commissions_on_closed == total_pnl` and the taxable analogue
hold exactly (same float ops as today's `gain_cad`).

## Files

1. `tradertax/gains.py`
   - `_Pool`: add `comm: float = 0.0` (commissions held in the pool: buy commissions in a
     long pool, the open sell commission in a short pool).
   - `Realized`: add `commissions_cad: float = 0.0` (appended; default so nothing else breaks).
   - `_event(...)`: new `commissions: float = 0.0` param → `commissions_cad=commissions`.
   - Four pool paths:
     - cover short (gains.py:196-208): event commissions = `pool.comm * frac + comm_cad * (cover / qty)`;
       then `pool.comm -= pool.comm * frac`; on full close reset `pool.comm = 0.0`.
     - buy into long (gains.py:209-215): `pool.comm += comm_cad * share`.
     - close long (gains.py:218-233): event commissions = `pool.comm * frac + outlays`
       (outlays = this sale's commission on the closed qty); `pool.comm -= pool.comm * frac`;
       reset on full close.
     - open/extend short (gains.py:234-246): `pool.comm += comm_cad * share`.
2. `tradertax/summary.py`
   - `YearReport`: four new fields after `other_registered_pnl`
     (`summary.py:47`): `total_pnl_before_commissions`, `commissions_on_closed`,
     `taxable_pnl_before_commissions`, `taxable_commissions_on_closed`.
   - `build_report` (after `summary.py:112`): sum `e.gain_cad + e.commissions_cad` /
     `e.commissions_cad` over `events` and `taxable_events`.
3. `tradertax/ui/pages.py`
   - `SummaryPage.build`: insert `("before_commissions", "P&L before commissions")` after
     `total_pnl` in `names` (pages.py:78).
   - `SummaryPage.refresh`: set the card — value `money(rep.total_pnl_before_commissions)`
     (signed colour), sub: commissions (all) and the taxable share, already inside the P&L,
     do not add again as an expense.
4. Tests (written first, must fail before the build):
   - `tests/test_summary.py`: new test on the existing `load_all` fixtures proving, at the
     fixture FX rate 1.37: taxable before 1650×1.37 and comm 13.90×1.37; total before
     1950×1.37 and comm 23.80×1.37 (hand-derived in `.qo/recon.md`, per close); the two
     identities against `total_pnl`/`taxable_pnl`; and that `taxable_pnl` still equals the
     after-commission number (1636.10×1.37) — tax side unchanged.
   - `tests/test_ui_smoke.py`: assert `summary.cards["before_commissions"].value.text() != "-"`.

## Done when
- `.qo/tests-red.txt` shows the new tests failing on the unmodified code.
- New tests pass; whole suite + `ruff check .` green (offscreen); output in `.qo/build.txt`.
- Existing `total_pnl`, `taxable_pnl`, expenses and tax figures untouched (existing tests
  keep passing unmodified).
- Self-review → `.qo/review.json` GO; then `.qo/report.md`.

## Decisions on unclear points (no user available)
- **Shorts**: a cover event's "commissions on the closed trade" include the short-open sale
  commission held in the pool (pro rata to the quantity closed) plus the cover buy
  commission. This is the only reading under which the required identity holds for shorts
  (their open commission is deducted from pool cost, `gains.py:245`). Fixture has a TSLA
  short so the test pins it.
- **Broker FEE rows** (IBKR market-data fee 4.50 USD → `rep.broker_fees`): excluded — they
  are `FEE`-kind rows, already a separate expense line, per the task constraint.
- **Exercised/assigned options** (`gains.py:247-252`): the option events are deleted and only
  net gain is rolled into the share trade, so a rolled option's commission is not in
  `commissions_on_closed`; the identity still holds because the rolled value is net of
  commission. Not exercised in the fixtures; noted in the report, no code change.
- **Card placement/label**: one new card (the task says "the new card"), key
  `before_commissions`, inserted after `Total P&L`; the taxable share and the
  "do not add again as an expense" note live in the card's sub line.
- **Not touched**: `export.py` (CSV/markdown), `ufile_sheet`, Gains/Expenses pages — the task
  asks for the report fields + the Summary card only; keep the change small.
- Field names follow existing style (`total_pnl` → `total_pnl_before_commissions`); the
  commission total is named `commissions_on_closed` ("commissions on closed trades").
