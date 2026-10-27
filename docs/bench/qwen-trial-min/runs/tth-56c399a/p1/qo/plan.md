# Plan — IBKR statement fixes

Decision (no user available; recorded per the job rules): where the task was
ambiguous I picked the behaviour that preserves total P&L and matches the
CRA "not wholly and fundamentally different" treatment of an option and the
shares it converts into — the premium (option pool ACB for the closed
portion) moves into the resulting share trade, and the option row produces no
realised event.

## Step 1 — `tradertax/gains.py`: roll assigned/exercised option premium (item 1)

In `compute_gains`:
- `ASSIGN_EXERCISE_CODES = {"A", "Ex", "ASN", "EXE"}`; helper
  `_roll_code(t) = str(t.raw.get("code") or t.raw.get("action") or "")`.
- Pairing pass (after the `as_of` filter): for each OPT trade with a roll
  code, pair it with the first unused STK trade on the same
  `(trade_date, broker, account_id)` whose underlying matches
  (`option_parts(t.symbol)[0]` vs the share symbol with `.TO` stripped).
  No match → the option row is processed exactly as today (no roll).
- Main loop: when a paired option row closes part of its option pool
  (long close or short cover), instead of a `Realized` event:
  - `delta = pool.cost * frac`, signed `+` (option pool long) / `−` (short);
  - update the option pool as usual (no event);
  - attach `delta` to the paired share trade:
    - share trade not yet processed → stamp
      `st.raw["_roll_cad"]` (cumulative, in CAD);
    - share trade already processed → if it was a buy and the share pool
      still holds qty, `pool.cost += delta`; else adjust the most recent
      `Realized` event for that fingerprint (LONG sell: `acb_cad += delta`;
      SHORT cover: `outlays_cad += delta`), recomputing `gain_cad`; else add
      a warning that the premium had nowhere to attach.
  - When the share trade is processed, a `_roll_cad` stamp is consumed:
    - buy: after cover/remainder handling, `pool.cost += delta` if the pool
      is non-empty (guard: flat pool → warning, premium dropped);
    - sell with `close > 0`: `acb = pool.cost * frac + delta`.
- Order-independence: both file orders (option row before/after the share
  row) must give identical results — covered by tests.
- Edge notes (accepted, documented): partial assignment rolls the closed
  fraction only; commission on the assignment row itself is not rolled
  (assignment rows carry no execution fee); a same-day option row without a
  matching share row falls back to the ordinary realised event.

## Step 2 — `tradertax/gains.py`: O/C codes on the "nothing held" warning (item 3)

Replace the warning condition at `gains.py:226-230`: warn when the pool is
empty and the sell cannot close anything, and only if
`asset_class in ("STK", "OPT")` **and** `_roll_code(t) != "O"`. (Opening
short sales flagged `O` by IBKR no longer warn; orphan closes — code `C` or
no code, e.g. Questrade — now warn for options too.) Wording of the message
is unchanged.

## Step 3 — `tradertax/parsers/ibkr.py`: signed commission (item 2)

`gains.py`… no: at `ibkr.py:131` replace
`comm = abs(to_float(cell(r, idx, "Comm/Fee")))` with
`comm = -to_float(cell(r, idx, "Comm/Fee"))` so costs stay positive and
rebates become negative (money in; `net = proceeds - comm` already correct).
Flex parser left alone (task names the activity statement only; advisory).

## Step 4 — `tradertax/taxrules.py`: CPP Schedule 8 crediting (item 4)

Rewrite the CPP block (`taxrules.py:86-96`) to the recon formulas:
employment (`other_income`) pensionable is credited first against YMP (net of
the basic exemption) and YAMPE (CPP2); the remainder is the business
pensionable that earns `cpp_base` / `cpp_2`. Update the
`Income.other_income` docstring note. No rules-JSON change (ympe/yampe/
exemption already present).

## Step 5 — `tradertax/ui/pages.py`: Summary "Job income this year" card (item 5)

- `SummaryPage.build`: add `("job_income", "Job income this year")` to the
  KPI `names` list (11th card, grid handles the wrap).
- `SummaryPage.refresh`: `c["job_income"].set(money(other_income), ...)`
  where `other_income = self.state.ledger.get_setting("other_income") or 0`
  — the same setting the Settings page field writes
  (`ui/pages.py:628`) and `summary.py:98` feeds into the tax scenarios;
  sub-line: "from Settings > Other income; it sets the marginal rate".

## Tests (written first, red)

`tests/test_gains.py`
- extend `tx()` with a `raw` parameter.
- item 1:
  1. `test_exercised_long_call_premium_rolls_into_share_cost` — buy call
     (premium 300 USD), exercise: share BUY 100 @ 150 + option close row
     `code="Ex"`; assert open AAPL ACB = (15000+300)×2, no option event, no
     open option; sell @160 → gain 1400 CAD.
  2. `test_assigned_short_put_premium_reduces_share_cost` — sell put
     (premium 400), assignment: share BUY 100 @ 90 + option row
     `code="A"`; ACB = (9000−400)×2; total P&L equal to the old
     option-gain + share-gain split (1800 CAD on the later sell).
  3. `test_assignment_roll_is_order_independent` — both same-day row orders
     give identical ACB/gain.
  4. `test_exercised_long_put_premium_adds_to_sold_shares_acb` — 100 shares
     @80, buy put @4, exercise: sell 100 @90 + option `code="Ex"` → gain
     (9000−8000−400)×2 = 1200 CAD (share row first, option row second:
     retroactive event path).
  5. `test_questrade_assignment_rolls_premium` — same as (2) with
     `raw={"action": "ASN"}` instead of `code`.
  6. `test_assignment_without_share_row_is_ordinary_close` — option row with
     code `A` but no share row that day → ordinary realised event.
- item 3:
  7. `test_ibkr_open_short_sale_no_warning` — `code="O"` short sell → no
     warning, short open position.
  8. `test_ibkr_orphan_close_warns_for_options` — OPT sell with `code="C"`,
     nothing held → warning containing "nothing held".
  9. `test_ibkr_close_with_open_position_no_warning` — O buy, C sell →
     warnings empty.
  (existing `test_short_sale_then_cover` keeps asserting the Questrade
  warning)

`tests/test_parsers.py`
- item 2: `test_ibkr_commission_rebate_is_money_in` — small activity
  statement fragment, one trade with `Comm/Fee=1.25` (rebate) and one with
  `−1` (cost): assert `commission == -1.25`, `net == proceeds + 1.25`, cost
  row `commission == 1`; also assert `raw["code"]` is captured (`"O"`).

`tests/test_tax_and_expenses.py`
- item 4: `test_cpp_credits_job_pensionable_first`:
  salary 90000 (> YAMPE) + business 50000 → `cpp_contribution == 0`;
  salary 60000 → only (71100 − 56500) = 14600 pensionable →
  `14600 * 0.119`; salary 40000 → 34600 pensionable. Plus the
  existing tests staying green.

`tests/test_ui_smoke.py`
- item 5: set `other_income` = 60000, rebuild, assert
  `summary.cards["job_income"].value.text() == "60,000.00"`.

`tests/test_summary.py` (integration, optional-but-done)
- item 1 through the real pipeline: an IBKR statement with a short-put
  assignment imported via `commit_import` → `build_report` shows AAPL open
  ACB = (strike×100 − premium)×1.37 and no open OPT position.

## Files changed

- `tradertax/gains.py` (items 1, 3)
- `tradertax/parsers/ibkr.py` (item 2)
- `tradertax/taxrules.py` (item 4)
- `tradertax/ui/pages.py` (item 5)
- tests: `tests/test_gains.py`, `tests/test_parsers.py`,
  `tests/test_tax_and_expenses.py`, `tests/test_ui_smoke.py`,
  `tests/test_summary.py`

Not touched: `tradertax/export.py` (export format), `tradertax/db.py`
(schema), `config/`, flex parser, Questrade parser (raw already carries
the actions).

## Done means

- items 1-4 covered by tests in `tests/test_gains.py`,
  `tests/test_parsers.py`, `tests/test_tax_and_expenses.py` (item 5 in
  `tests/test_ui_smoke.py`);
- `python -m pytest -q` green (full suite, including pre-existing tests);
- `python -m ruff check tradertax tests` clean.
