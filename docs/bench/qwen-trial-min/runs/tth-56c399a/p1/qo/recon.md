# Recon — IBKR statement fixes (5 items)

Broker: the app supports Questrade activity exports and IBKR files (activity
statement + flex trades). All trades are normalised to `Transaction`
(`tradertax/models.py:31-62`) and pooled in `compute_gains`
(`tradertax/gains.py:111-246`). Commission convention: `commission` is a
**positive cost**; `net = gross - commission`.

## Item 1 — assigned/exercised option premium must roll into the resulting share trade

Today every `TRADE` row is pooled independently, so an option closed by
assignment/exercise realises its premium as a separate gain
(`gains.py:206-233` sell/cover branches).

Where the codes live:
- IBKR activity statement: `Code` column is stored per trade at
  `tradertax/parsers/ibkr.py:174` (`raw={"category", "code", ...}`). No change
  needed there — codes `O`/`C`/`A`/`Ex` are already captured in `raw`.
- IBKR flex: no O/C codes (not needed).
- Questrade: the `Action` column is stored at
  `tradertax/parsers/questrade.py:160` (`raw={"action", ...}`); `ASN`/`EXE`
  map to `kind=TRADE` via `ACTION_KIND` (`questrade.py:24-25`) and get option
  symbols from the description (`questrade.py:108-111`).

Gains engine (`compute_gains`, `gains.py:111`):
- trades are sorted by `(trade_date, raw.seq, fingerprint)` (`gains.py:125-132`);
- pools are per `(pool_group, symbol)` (`gains.py:136`); long pool cost = ACB,
  short pool cost = net proceeds received (`gains.py:84`);
- closes realise `gain = proceeds - outlays - acb` (`gains.py:209-219`), covers
  realise `gain = proceeds - cost_cad` (`gains.py:188-198`);
- `option_parts` / `normalize_symbol` live in `tradertax/parsers/common.py:95-147`
  and recover the underlying ticker from an option spelling — usable to match
  the option row to its resulting share row.
- The share trade created by an assignment/exercise is a **separate TRADE row on
  the same date, same broker, same account** (IBKR: same `Code` `A`/`Ex`;
  Questrade: a normal BUY/SELL row next to the `ASN`/`EXE` row). It is already
  pooled today at full strike cost, so the premium is double-counted
  (premium realised in the option pool AND the share cost ignores it).

Roll semantics (verified against total P&L): the premium (option pool ACB for
the closed portion, in CAD) moves into the share trade:
- long option exercised: share ACB/cost **increases** by the premium paid;
- short option assigned: share cost **decreases** by the premium received
  (forced buy), or share proceeds effectively **increase** (forced delivery:
  call assignment, put exercise of shares we sell).
So: `delta = pool.cost * frac`, signed `+` when the option pool is long,
`−` when short; applied to the share trade's cost (buys) or the sell event's
ACB (sells). The option row produces **no realised event**.

## Item 2 — IBKR commission rebate (positive Comm/Fee) is money in

`tradertax/parsers/ibkr.py:131`: `comm = abs(to_float(cell(r, idx, "Comm/Fee")))`.
In IBKR files costs are negative and rebates positive; `abs()` turns a rebate
into a cost. Downstream consumers treat a **negative** commission as income:
- buys: `pool.cost += (-gross + comm) * share` (`gains.py:204`);
- sells: `outlays = comm_cad * share` (`gains.py:214`);
- summary already handles signed FEE rows (`summary.py:150-154`).
Fix: `comm = -to_float(...)` (cost −1 → +1; rebate +0.5 → −0.5). `net =
proceeds - comm` then keeps the sign right. Flex parser (`ibkr.py:254`,
`abs` on IBCommission) is **not** named by the task — left unchanged
(advisory).

## Item 3 — IBKR O/C codes and the "nothing held" warning

`gains.py:226-230`: a sell against an empty pool warns, but only when
`t.asset_class == "STK"`, and it warns even when the row is an *opening*
short (IBKR code `O`). Fixes:
- code `O` (opening short sale, deliberate) → no warning;
- closing codes / unknown brokers (no code, e.g. Questrade) with an empty pool
  → warn, extended to `OPT` as well as `STK`.
Code is read from `raw["code"]` (IBKR only; Questrade rows carry `action`
BUY/SELL, which is not an O/C code, so they keep warning — matches
`tests/test_gains.py:58-63`).

## Item 4 — self-employed CPP must credit the job's payroll CPP (Schedule 8)

`tradertax/taxrules.py:86-96`: pensionable base is computed on
`business_income` alone, so a big salary does not reduce CPP on trading
income. Schedule 8 credits employment pensionable first against the YMP
(`ympe` = 74600) net of the basic exemption (`exemption` = 3500), and CPP2
credits employment above YMP against the YAMPE (`yampe` = 85000) — see
`config/tax_rules_2026.json` `cpp` block. `other_income` is the Settings
"job, pension" field (`db.py:104`, `ui/pages.py:561-562`); treat it as
pensionable employment income (task's assumption). New formulas:

```
emp_base  = max(0, min(other_income, ympe) - exemption)
biz_base  = max(0, min(other_income + business_income, ympe) - exemption - emp_base)
emp_cpp2  = max(0, min(other_income, yampe) - ympe)
biz_cpp2  = max(0, min(other_income + business_income, yampe) - yampe - emp_cpp2)
cpp_base = biz_base * self_employed_base_rate
cpp_2    = biz_cpp2 * self_employed_cpp2_rate
```

Existing tests stay green: `test_business_income_adds_cpp_and_tax`
(other_income=0 → identical numbers), `test_marginal_tax_is_difference_of_scenarios`
(other=80000, biz=20000 → new cpp 0 instead of 16500-based; the test only
bounds the total within [0.2, 0.6]×20000, still holds).

## Item 5 — Summary "Job income this year" box

`other_income` setting is read at `summary.py:98` and fed to every
`Income(...)` scenario (`summary.py:185-194`) — it is what sets the marginal
rate. Settings page exposes it as the `other_income` money spin
(`ui/pages.py:561-563, 614, 628`). Summary page KPI grid
(`ui/pages.py:72-89`, 10 `KpiCard`s, `widgets.py:143`): add an 11th card
`("job_income", "Job income this year")` that displays the same
`other_income` setting with a sub-line saying it sets the marginal rate
(pattern: the Settings field; display-only, edited in Settings).

## Tests / files touched by tests

- `tests/test_gains.py` — direct `Transaction` fixtures via `tx()` helper
  (`:10-27`); add `raw` support for O/C codes. Covers items 1 & 3.
- `tests/test_parsers.py` — `IB_STATEMENT`/`IB_FLEX` fixtures in
  `tests/conftest.py:35-74`. Item 2 gets a small new statement fragment
  (existing fixture rows are asserted on exact numbers, so do not edit it).
- `tests/test_tax_and_expenses.py` — `compute_tax` with `load_rules(2026)`;
  item 4.
- `tests/test_ui_smoke.py` — offscreen window, `state.report`, pages by index
  (`:24-52`); item 5 assertion belongs here.
- `tests/test_summary.py` — end-to-end `build_report` via
  `commit_import`; optional integration test for item 1 (DB round-trips
  `raw` JSON, `db.py:55-56`).

## Constraints checked

- Export format (`tradertax/export.py`) and DB schema (`db.py`) untouched —
  no changes needed there.
- `compute_gains` only reads `raw` (already persisted as JSON); no schema change.
- Python: `C:/Users/Aaron/TraderTaxHelper/.venv/Scripts/python.exe`; ruff
  line-length 160, select E,F,I,B,UP (E501 ignored).
