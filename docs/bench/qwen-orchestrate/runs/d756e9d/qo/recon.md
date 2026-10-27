# Recon — P&L before commissions + commissions on closed trades

Task: Summary shows realised P&L before commissions, commissions paid on the year's closed
trades, and the taxable share of those commissions. Tax numbers must not change; display only.

## Where the numbers come from

### Gains / events — `tradertax/gains.py`
- `Realized` dataclass (`gains.py:39-67`): one per close, carries `proceeds_cad`,
  `outlays_cad` (sell commissions, `gains.py:224`), `acb_cad` (buy commissions folded in,
  `gains.py:214`), `gain_cad = proceeds - outlays - acb` (`gains.py:225`).
  **No per-event commission figure today** — buy commissions are merged into pool cost and
  cannot be separated from price afterwards.
- `_Pool` (`gains.py:81-91`): single `cost` field. Long pool: `cost` = price + buy
  commissions (`gains.py:214`). Short pool: `cost` = gross proceeds − open sell commissions
  (`gains.py:245`).
- Four pool paths in `compute_gains` (`gains.py:169-246`):
  1. cover a short, `gains.py:196-208` (event `side="SHORT"`, outlays 0.0, acb param = cover cost incl. cover commission);
  2. buy into long pool, `gains.py:209-215` (no event);
  3. close a long, `gains.py:218-233` (event `side="LONG"`);
  4. open/extend short, `gains.py:234-246` (no event).
- Assigned/exercised options (`gains.py:247-252`): the option's events are deleted and only
  `sum(e.gain_cad)` is rolled into the share trade's gross — a rolled option's commissions
  would drop out of any event-level commission sum, but the rolled value is net of them, so
  a `before − commissions == after` identity over remaining events still holds. No options
  are exercised in the test fixtures.
- `GainsResult.events_in(year)` (`gains.py:104-105`) is what `summary.py` aggregates.
- `Realized` is constructed only at `gains.py:285` (`_event`) — one construction site.

### Year report — `tradertax/summary.py`
- `YearReport` fields `summary.py:36-87`; P&L aggregation at `summary.py:107-112`:
  `total_pnl`/`taxable_pnl`/`tfsa_pnl` are `sum(e.gain_cad ...)` over `events` /
  `taxable_events` (`e.taxable` = pool `TAXABLE`, `gains.py:65-67`).
- Broker `FEE` rows (e.g. IBKR market-data fee, fixture line `Fees,Data,Other Fees,...,-4.5`)
  land in `rep.broker_fees` (`summary.py:150-155`) and are a separate expense line — not
  TRADE commissions, so they are out of scope by the task's constraint.

### UI — `tradertax/ui/pages.py`
- `SummaryPage.build` `pages.py:75-94`: 10 `KpiCard`s in a `QGridLayout`, 5 per row, keyed
  by the first element of `names`.
- `SummaryPage.refresh` `pages.py:141-156` sets each card via `c[key].set(value, sub, colour)`.
- `KpiCard` (`tradertax/ui/widgets.py:143-165`): `.title`, `.value` (QLabel, starts "-"),
  `.sub`; `.set(value, sub, colour)`.
- `money()` from `widgets.py` formats CAD for the cards.

### Tests
- `tests/conftest.py:77-79`: FX fixture is a flat 1.37 for every day of 2026 → every USD
  figure converts at 1.37; CAD figures at 1.0.
- `tests/test_summary.py:13-19` `load_all(ledger)`: Questrade margin (AAPL round trip,
  SHOP.TO buy, option buy, dividend/withholding/interest/fx rows), Questrade TFSA (NVDA
  round trip), IBKR statement (AAPL round trip, TSLA short open + cover, option buy, fees).
  Existing assertions pin the after-commission numbers, e.g. `aapl["acb"] == (15000 + 4.95 + 7600 + 1) * 1.37`
  (`test_summary.py:35`) and `tsla["gain"] == (4000 - 1 - 3800 - 1) * 1.37` (`test_summary.py:37`).
- `tests/test_ui_smoke.py:37-39`: builds `MainWindow`, checks `summary.cards["total_pnl"].value.text() != "-"`
  — the same pattern works for a new card.
- Parsers deliver `commission` as a **positive** cost (`models.py:38`, `questrade.py:115`
  `abs(...)`), so `t.commission * rate` in `gains.py:175` is positive.
- Baseline: `pytest tests -q` → **47 passed** (2026-10-26).

## Hand-computed fixture numbers (USD; CAD at 1.37)

Closes in 2026 (SHOP.TO and both option buys never close → contribute nothing):

| close | gross in | gross out | buy comm | sell comm | gain (USD) | before (USD) | comm (USD) |
|---|---|---|---|---|---|---|---|
| AAPL QT 100@160 (bought 100@150) | 16000 | 15000 | 4.95 | 4.95 | — | — | — |
| AAPL IB 50@161 (bought 50@152) | 8050 | 7600 | 1.00 | 1.00 | — | — | — |
| TSLA cover 20@190 (short @200) | 4000 | 3800 | — | 1.00 open + 1.00 cover | 198 | 200 | 2.00 |
| NVDA TFSA 10@130 (bought 10@100) | 1300 | 1000 | 4.95 | 4.95 | 290.10 | 300 | 9.90 |

AAPL pooled (one TAXABLE pool, avg cost): ACB 15000+7600+4.95+1.00 = 22605.95 incl. 5.95 buy
comm; proceeds 24050; outlays 5.95 → gain 1438.10 USD; before = 24050 − 22600 = 1450; comm = 11.90.

Totals:
- taxable: before 1650 → **2260.50 CAD**; comm 13.90 → **19.043 CAD**; pnl 1636.10 → **2241.457 CAD**
- all accounts: before 1950 → **2671.50 CAD**; comm 23.80 → **32.606 CAD**; pnl 1926.20 → **2638.894 CAD**
- identity: 2671.50 − 32.606 = 2638.894 ✓ and 2260.50 − 19.043 = 2241.457 ✓

## Gaps
- Nothing tracks per-event or per-pool commissions: must be added in `gains.py` (task note
  says not to re-derive from raw transactions).
- No report fields, no UI card, no tests for the new figures yet.
