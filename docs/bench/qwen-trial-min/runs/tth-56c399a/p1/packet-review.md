# BRIEF
Goal: IBKR statement fixes. (1) Assigned or exercised options (IBKR codes A / Ex, Questrade ASN / EXE) roll their premium into the cost or proceeds of the resulting share trade instead of being realised as a gain. (2) An IBKR commission rebate (positive Comm/Fee) is money in, not a cost. (3) IBKR O/C codes: an opening short sale no longer warns, and a closing trade with no open position warns for options too. (4) Self-employed CPP credits the job's payroll CPP first (Schedule 8), so a salary above the YAMPE leaves no CPP on trading income. (5) The Summary page gets a "Job income this year" box, the same setting as in Settings, which sets the marginal rate.
Done when: tests in tests/test_gains.py, tests/test_parsers.py and tests/test_tax_and_expenses.py cover 1-4; `python -m pytest -q` green; ruff clean.
Files: tradertax/gains.py (compute_gains), tradertax/parsers/ibkr.py, tradertax/taxrules.py (compute_tax), tradertax/ui/pages.py; find the rest.
Don't touch: the export format, the database schema.
Pattern: the Settings page's job-income field, for the summary box.

# CANDIDATE DIFF
```diff
diff --git a/tests/test_gains.py b/tests/test_gains.py
index 38c1a5f..53ba4ca 100644
--- a/tests/test_gains.py
+++ b/tests/test_gains.py
@@ -7,7 +7,7 @@ from tradertax.gains import compute_gains
 from tradertax.models import Transaction, fingerprint_rows
 
 
-def tx(d, qty, price, *, symbol="AAPL", broker="questrade", account="1", acct_type="MARGIN", currency="USD", commission=1.0, asset_class="STK"):
+def tx(d, qty, price, *, symbol="AAPL", broker="questrade", account="1", acct_type="MARGIN", currency="USD", commission=1.0, asset_class="STK", raw=None):
     mult = 100.0 if asset_class == "OPT" else 1.0
     gross = -qty * price * mult
     return Transaction(
@@ -24,6 +24,7 @@ def tx(d, qty, price, *, symbol="AAPL", broker="questrade", account="1", acct_ty
         net=gross - commission,
         currency=currency,
         account_type=acct_type,
+        raw=raw or {},
     )
 
 
@@ -78,6 +79,133 @@ def test_taxable_accounts_pool_across_brokers_but_tfsa_is_separate(fx):
     assert len(tfsa) == 1 and tfsa[0].gain_cad == pytest.approx(10 * 2)
 
 
+CALL = "AAPL 2027-01-15 C 150.00"
+PUT = "AAPL 2027-01-15 P 150.00"
+
+
+def test_exercised_long_call_premium_rolls_into_share_cost(fx):
+    # Exercise a long call: the premium paid becomes part of the shares' cost;
+    # the option row (code "Ex") is not a separate realised disposition.
+    rows = [
+        tx(date(2026, 1, 5), 1, 3.0, symbol=CALL, asset_class="OPT", commission=0, raw={"code": "O"}),
+        tx(date(2026, 3, 1), 100, 150.0, commission=0, raw={"code": "Ex", "seq": 1}),
+        tx(date(2026, 3, 1), -1, 3.0, symbol=CALL, asset_class="OPT", commission=0, raw={"code": "Ex", "seq": 2}),
+        tx(date(2026, 3, 2), -100, 160.0, commission=0),
+    ]
+    res = run(rows, fx)
+    assert all(e.symbol != CALL for e in res.events), "the option must not be realised separately"
+    (e,) = res.events
+    assert e.symbol == "AAPL" and e.side == "LONG"
+    assert e.acb_cad == pytest.approx((15000 + 300) * 2)
+    assert e.proceeds_cad == pytest.approx(16000 * 2)
+    assert e.gain_cad == pytest.approx(16000 * 2 - (15000 + 300) * 2)
+    assert res.open_positions == []
+
+
+def test_assigned_short_put_premium_reduces_share_cost(fx):
+    # Assignment of a short put: the premium received reduces the cost of the
+    # shares taken over (IBKR code "A"). Option row comes first in the file.
+    rows = [
+        tx(date(2026, 1, 5), -1, 4.0, symbol=PUT, asset_class="OPT", commission=0, raw={"code": "O"}),
+        tx(date(2026, 3, 1), 1, 4.0, symbol=PUT, asset_class="OPT", commission=0, raw={"code": "A", "seq": 1}),
+        tx(date(2026, 3, 1), 100, 90.0, commission=0, raw={"code": "A", "seq": 2}),
+        tx(date(2026, 3, 2), -100, 95.0, commission=0),
+    ]
+    res = run(rows, fx)
+    assert res.open_positions == []
+    (e,) = res.events
+    assert e.acb_cad == pytest.approx((9000 - 400) * 2)
+    assert e.gain_cad == pytest.approx((9500 - (9000 - 400)) * 2)
+
+
+def test_assignment_roll_is_order_independent_and_not_the_row_price(fx):
+    # Same assignment with the share row first in the file, and with the option
+    # row priced at 4.50: the roll is the premium from the option pool, not the
+    # row's price. Both orders must give the same result.
+    rows = [
+        tx(date(2026, 1, 5), -1, 4.0, symbol=PUT, asset_class="OPT", commission=0, raw={"code": "O"}),
+        tx(date(2026, 3, 1), 100, 90.0, commission=0, raw={"code": "A", "seq": 1}),
+        tx(date(2026, 3, 1), 1, 4.5, symbol=PUT, asset_class="OPT", commission=0, raw={"code": "A", "seq": 2}),
+        tx(date(2026, 3, 2), -100, 95.0, commission=0),
+    ]
+    res = run(rows, fx)
+    (e,) = res.events
+    assert e.acb_cad == pytest.approx((9000 - 400) * 2)
+    assert e.gain_cad == pytest.approx((9500 - (9000 - 400)) * 2)
+
+
+def test_exercised_long_put_premium_adds_to_sold_shares_acb(fx):
+    # Exercise a long put: deliver the shares at the strike; the premium paid
+    # adds to the ACB of the shares sold (the share row is processed first).
+    rows = [
+        tx(date(2026, 1, 5), 100, 80.0, commission=0, raw={"code": "O"}),
+        tx(date(2026, 1, 6), 1, 4.0, symbol=PUT, asset_class="OPT", commission=0, raw={"code": "O"}),
+        tx(date(2026, 3, 1), -100, 90.0, commission=0, raw={"code": "Ex", "seq": 1}),
+        tx(date(2026, 3, 1), -1, 4.0, symbol=PUT, asset_class="OPT", commission=0, raw={"code": "Ex", "seq": 2}),
+    ]
+    res = run(rows, fx)
+    (e,) = res.events
+    assert e.symbol == "AAPL" and e.proceeds_cad == pytest.approx(9000 * 2)
+    assert e.acb_cad == pytest.approx((8000 + 400) * 2)
+    assert e.gain_cad == pytest.approx((9000 - 8000 - 400) * 2)
+    assert res.open_positions == []
+
+
+def test_questrade_assignment_rolls_premium(fx):
+    # Questrade flags the option row with action "ASN" (no O/C codes at all).
+    be = "BE 2026-07-02 P 260.00"
+    rows = [
+        tx(date(2026, 1, 5), -1, 4.0, symbol=be, asset_class="OPT", commission=0, raw={"action": "BUY"}),
+        tx(date(2026, 3, 1), 1, 4.0, symbol=be, asset_class="OPT", commission=0, raw={"action": "ASN", "seq": 1}),
+        tx(date(2026, 3, 1), 100, 260.0, symbol="BE", commission=0, raw={"action": "BUY", "seq": 2}),
+    ]
+    res = run(rows, fx)
+    assert res.events == []
+    (p,) = res.open_positions
+    assert (p.symbol, p.quantity) == ("BE", 100)
+    assert p.acb_cad == pytest.approx((26000 - 400) * 2)
+
+
+def test_assignment_without_share_row_is_ordinary_close(fx):
+    # An assignment row with no matching share trade that day keeps the old
+    # treatment: the option is realised in its own pool.
+    rows = [
+        tx(date(2026, 1, 5), -1, 4.0, symbol=PUT, asset_class="OPT", commission=0, raw={"code": "O"}),
+        tx(date(2026, 3, 1), 1, 5.0, symbol=PUT, asset_class="OPT", commission=0, raw={"code": "A"}),
+    ]
+    res = run(rows, fx)
+    (e,) = res.events
+    assert e.symbol == PUT and e.side == "SHORT"
+    assert e.gain_cad == pytest.approx((400 - 500) * 2)
+    assert res.open_positions == []
+    assert res.warnings == []
+
+
+def test_ibkr_open_short_sale_no_warning(fx):
+    # IBKR code "O" says the short was deliberately opened: no warning.
+    rows = [tx(date(2026, 2, 3), -20, 200.0, commission=0, raw={"code": "O"})]
+    res = run(rows, fx)
+    assert res.warnings == []
+    assert res.open_positions[0].quantity == -20
+
+
+def test_ibkr_orphan_close_warns_for_options(fx):
+    # A closing row (code "C") with no open position warns - now for options too.
+    rows = [tx(date(2026, 2, 10), -1, 3.0, symbol=CALL, asset_class="OPT", commission=0, raw={"code": "C"})]
+    res = run(rows, fx)
+    assert res.warnings and "nothing held" in res.warnings[0]
+
+
+def test_ibkr_close_with_open_position_no_warning(fx):
+    rows = [
+        tx(date(2026, 1, 5), 100, 10.0, commission=0, raw={"code": "O"}),
+        tx(date(2026, 1, 20), -100, 12.0, commission=0, raw={"code": "C"}),
+    ]
+    res = run(rows, fx)
+    assert res.warnings == []
+    assert res.events[0].gain_cad == pytest.approx((1200 - 1000) * 2)
+
+
 def test_option_expiry_closes_at_zero(fx):
     rows = [tx(date(2026, 2, 10), 2, 3.5, symbol="AAPL 2027-01-15 C 150.00", asset_class="OPT", commission=9.95), tx(date(2027, 1, 15), -2, 0.0, symbol="AAPL 2027-01-15 C 150.00", asset_class="OPT", commission=0)]
     res = run(rows, fx)
diff --git a/tests/test_parsers.py b/tests/test_parsers.py
index b67bdf9..a81b912 100644
--- a/tests/test_parsers.py
+++ b/tests/test_parsers.py
@@ -54,6 +54,30 @@ def test_ibkr_statement():
     assert [r.kind for r in parsed.rows if r.net == 10000] == ["DEPOSIT"]
 
 
+IB_REBATE = """Statement,Header,Field Name,Field Value
+Statement,Data,BrokerName,Interactive Brokers Canada Inc.
+Statement,Data,Period,"January 1, 2026 - March 31, 2026"
+Account Information,Header,Field Name,Field Value
+Account Information,Data,Account,U7654321
+Account Information,Data,Account Type,Individual
+Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
+Trades,Data,Order,Stocks,USD,IBM,"2026-02-01, 10:00:00",10,100,99,-1000,-1,-1001,0,0,O
+Trades,Data,Order,Stocks,USD,GE,"2026-02-02, 10:00:00",-10,110,109,1100,1.25,1098.75,0,0,C
+"""
+
+
+def test_ibkr_commission_rebate_is_money_in():
+    # In the file fees are negative; a positive Comm/Fee is a rebate - money in, not a cost.
+    rows = rows_from_bytes(IB_REBATE.encode())
+    assert detect(rows) == "ibkr"
+    parsed = parse_rows(rows, "ibkr_rebate.csv")
+    ibm, ge = [r for r in parsed.rows if r.kind == "TRADE"]
+    assert ibm.commission == 1 and ibm.net == pytest.approx(-1001)  # ordinary fee stays a cost
+    assert ge.commission == pytest.approx(-1.25)  # rebate: negative cost
+    assert ge.net == pytest.approx(1100 + 1.25)
+    assert ibm.raw["code"] == "O" and ge.raw["code"] == "C"
+
+
 def test_ibkr_flex():
     rows = rows_from_bytes(IB_FLEX.encode())
     assert detect(rows) == "ibkr_flex"
diff --git a/tests/test_summary.py b/tests/test_summary.py
index 5c9a5e0..6ba8bfe 100644
--- a/tests/test_summary.py
+++ b/tests/test_summary.py
@@ -19,6 +19,32 @@ def load_all(ledger):
     ledger.commit_import(ib, account_type="MARGIN", period_start=ib.period_start, period_end=ib.period_end)
 
 
+IB_ASSIGNMENT = """Statement,Header,Field Name,Field Value
+Statement,Data,BrokerName,Interactive Brokers Canada Inc.
+Statement,Data,Period,"January 1, 2026 - March 31, 2026"
+Account Information,Header,Field Name,Field Value
+Account Information,Data,Account,U88877766
+Account Information,Data,Account Type,Individual
+Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
+Trades,Data,Order,Equity and Index Options,USD,AAPL 15JAN27 150 P,"2026-01-10, 11:00:00",-1,4,4.1,400,-0.65,-400.65,0,0,O
+Trades,Data,Order,Equity and Index Options,USD,AAPL 15JAN27 150 P,"2026-03-01, 09:30:00",1,4,4,-400,0,400,0,0,A
+Trades,Data,Order,Stocks,USD,AAPL,"2026-03-01, 09:30:00",100,150,150,-15000,-1,15001,0,0,A
+"""
+
+
+def test_ibkr_assignment_rolls_premium_end_to_end(ledger):
+    # A short put assigned at 150: the premium net of commission reduces the ACB of
+    # the forced 100-share buy; the option must not open or close as its own position.
+    ib = parse_rows(rows_from_bytes(IB_ASSIGNMENT.encode()), "ib_assign.csv")
+    ledger.commit_import(ib, account_type="MARGIN", period_start=ib.period_start, period_end=ib.period_end)
+    ledger.set_setting("tax_year", 2026)
+    rep = build_report(ledger, 2026, as_of=date(2026, 4, 1))
+    (p,) = rep.open_taxable
+    assert p.symbol == "AAPL" and p.quantity == 100
+    assert p.acb_cad == pytest.approx((15000 + 1 - 400 + 0.65) * 1.37)
+    assert not any("nothing held" in w for w in rep.warnings)
+
+
 def test_business_report_end_to_end(ledger):
     load_all(ledger)
     ledger.set_setting("tax_year", 2026)
diff --git a/tests/test_tax_and_expenses.py b/tests/test_tax_and_expenses.py
index fde0cf5..a8c403f 100644
--- a/tests/test_tax_and_expenses.py
+++ b/tests/test_tax_and_expenses.py
@@ -30,6 +30,25 @@ def test_business_income_adds_cpp_and_tax(rules):
     assert t.total > t.federal_tax + t.provincial_tax
 
 
+def test_cpp_credits_job_pensionable_first(rules):
+    # Schedule 8: the job's payroll CPP is credited against the YMP/YAMPE first, so a
+    # salary above the YAMPE leaves no CPP on the trading income.
+    t = compute_tax(rules, "BC", Income(other_income=90000, business_income=50000))
+    assert t.cpp_contribution == 0
+    assert t.cpp_deduction == 0
+    # a salary inside the YMP: only the YMP room the job did not use is pensionable at the
+    # base rate; the business still holds the full CPP2 band (YAMPE - YMP)
+    biz_base = 74600 - 3500 - (60000 - 3500)  # 14600
+    biz_cpp2 = 85000 - 74600  # 10400
+    t = compute_tax(rules, "BC", Income(other_income=60000, business_income=50000))
+    assert t.cpp_contribution == pytest.approx(biz_base * 0.119 + biz_cpp2 * 0.08)
+    share = rules["cpp"]["employee_base_rate"] / rules["cpp"]["self_employed_base_rate"]
+    assert t.cpp_deduction == pytest.approx(biz_base * 0.119 * (1 - share) + biz_cpp2 * 0.08)
+    # a salary below the basic exemption: the business keeps the full YMP room
+    t = compute_tax(rules, "BC", Income(other_income=40000, business_income=50000))
+    assert t.cpp_contribution == pytest.approx((74600 - 3500 - (40000 - 3500)) * 0.119 + biz_cpp2 * 0.08)
+
+
 def test_capital_gains_half_included_no_cpp(rules):
     t = compute_tax(rules, "BC", Income(taxable_capital_gains=50000))
     assert t.cpp_contribution == 0
diff --git a/tests/test_ui_smoke.py b/tests/test_ui_smoke.py
index 33a4a8e..f8852db 100644
--- a/tests/test_ui_smoke.py
+++ b/tests/test_ui_smoke.py
@@ -49,4 +49,8 @@ def test_main_window_refreshes(qapp, ledger):
     settings.save()
     assert state.report.treatment == "CAPITAL"
     assert state.last_error == ""
+    # the summary card mirrors the Settings > Other income field
+    ledger.set_setting("other_income", 60000)
+    state.rebuild()
+    assert summary.cards["job_income"].value.text() == "60,000.00"
     win.close()
diff --git a/tradertax/gains.py b/tradertax/gains.py
index 5abc8f0..5b1a29d 100644
--- a/tradertax/gains.py
+++ b/tradertax/gains.py
@@ -14,6 +14,12 @@ when the same security is bought in ANY account within 30 days before or after
 and is still held 30 days after. The denied part is added back to the ACB of
 the repurchased shares in a taxable pool; a repurchase inside a TFSA/RRSP loses
 the deduction for good.
+
+Options converted by assignment or exercise (IBKR codes A/Ex, Questrade actions
+ASN/EXE) are not separate dispositions: the premium (the option pool's cost for
+the closed portion) moves into the resulting same-day share trade - up the ACB
+when the premium was paid, down the cost when it was received - and the option
+row produces no realised event.
 """
 
 from __future__ import annotations
@@ -28,6 +34,17 @@ from .fx import FxTable
 from .models import REGISTERED_ACCOUNT_TYPES, Transaction
 
 SUPERFICIAL_WINDOW = timedelta(days=30)
+# O/C codes (IBKR) or actions (Questrade) that mark an option closed by conversion.
+ASSIGN_EXERCISE_CODES = {"A", "Ex", "ASN", "EXE"}
+
+
+def _roll_code(t: Transaction) -> str:
+    return str(t.raw.get("code") or t.raw.get("action") or "")
+
+
+def _base_symbol(symbol: str) -> str:
+    # "AAPL 2027-01-15 C 150.00" -> "AAPL"; "SHOP.TO" -> "SHOP"
+    return symbol.split(" ")[0].upper().removesuffix(".TO")
 
 
 def pool_group(tx: Transaction) -> str:
@@ -132,6 +149,23 @@ def compute_gains(
     )
     if as_of is not None:
         trades = [t for t in trades if t.trade_date <= as_of]
+    # Pair each assignment/exercise option row with the share trade it resulted in:
+    # first unused STK trade the same day, same broker and account, same underlying.
+    roll_pairs: dict[int, Transaction] = {}
+    stk_by_day: dict[tuple, list[Transaction]] = defaultdict(list)
+    for t in trades:
+        if t.asset_class == "STK":
+            stk_by_day[(t.trade_date, t.broker, t.account_id)].append(t)
+    paired_shares: set[int] = set()
+    for t in trades:
+        if t.asset_class == "OPT" and _roll_code(t) in ASSIGN_EXERCISE_CODES:
+            under = _base_symbol(t.symbol)
+            for st in stk_by_day.get((t.trade_date, t.broker, t.account_id), []):
+                if id(st) not in paired_shares and _base_symbol(st.symbol) == under:
+                    roll_pairs[id(t)] = st
+                    paired_shares.add(id(st))
+                    break
+    order = {id(t): i for i, t in enumerate(trades)}
     last_data_date = max((t.trade_date for t in trades), default=None)
     pools: dict[tuple[str, str], _Pool] = defaultdict(_Pool)
     events: list[Realized] = []
@@ -163,7 +197,7 @@ def compute_gains(
     def foreign_cost_now() -> float:
         return sum(p.cost for (g, _), p in pools.items() if g == "TAXABLE" and p.qty > 0 and p.currency != "CAD")
 
-    for t in trades:
+    for i, t in enumerate(trades):
         group = pool_group(t)
         key = (group, t.symbol)
         pool = pools[key]
@@ -176,6 +210,7 @@ def compute_gains(
         pool.last_date = t.trade_date
         if qty == 0:
             continue
+        roll_delta = t.raw.pop("_roll_cad", 0.0)  # same-day assignment/exercise premium stamped onto this share row, in CAD
         # Apply any ACB add-back waiting for this repurchase.
         if group == "TAXABLE" and qty > 0 and pending.get(t.symbol):
             due = [p for p in pending[t.symbol] if p[0] <= t.trade_date]
@@ -186,7 +221,17 @@ def compute_gains(
         if qty > 0:
             # Cover a short first, then go long with any remainder.
             cover = min(qty, -pool.qty) if pool.qty < 0 else 0.0
-            if cover > 0:
+            st = roll_pairs.get(id(t))
+            if cover > 0 and st is not None:
+                # Assignment: the premium received (the option pool) reduces the cost of the
+                # shares we are forced to buy - no realised event on the option itself.
+                delta = pool.cost * (cover / -pool.qty)
+                pool.cost -= delta
+                pool.qty += cover
+                if abs(pool.qty) < 1e-9:
+                    pool.qty, pool.cost = 0.0, 0.0
+                _attach_premium(st, -delta, t, i, order, pools, events, warnings)
+            elif cover > 0:
                 frac = cover / -pool.qty
                 proceeds = pool.cost * frac
                 cost_cad = (-gross_cad) * (cover / qty) + comm_cad * (cover / qty)
@@ -203,27 +248,42 @@ def compute_gains(
                 share = remainder / qty
                 pool.cost += (-gross_cad) * share + comm_cad * share
                 pool.qty += remainder
+            if roll_delta and abs(pool.qty) > 1e-9:
+                pool.cost += roll_delta
+            elif roll_delta:
+                warnings.append(f"{t.trade_date} {t.symbol} in {t.broker} {t.account_id}: assignment/exercise premium had no share position to attach to")
         else:
             sell = -qty
             close = min(sell, pool.qty) if pool.qty > 0 else 0.0
+            st = roll_pairs.get(id(t))
             if close > 0:
                 share = close / sell
                 frac = close / pool.qty
-                acb = pool.cost * frac
-                proceeds = gross_cad * share
-                outlays = comm_cad * share
-                gain = proceeds - outlays - acb
-                ev = _event(t, "LONG", close, proceeds, outlays, acb, gain, rate, source, group)
-                if superficial and group == "TAXABLE" and gain < 0:
-                    _apply_superficial(ev, t, close, buys_by_symbol, buy_dates, cum_by_symbol, cum_dates, pending, pools, last_data_date, warnings)
-                events.append(ev)
-                pool.cost -= acb
-                pool.qty -= close
-                if abs(pool.qty) < 1e-9:
-                    pool.qty, pool.cost = 0.0, 0.0
+                base_acb = pool.cost * frac
+                if st is not None:
+                    # Exercise: the premium paid (the option pool) adds to the cost of the
+                    # resulting share trade - no realised event on the option itself.
+                    pool.cost -= base_acb
+                    pool.qty -= close
+                    if abs(pool.qty) < 1e-9:
+                        pool.qty, pool.cost = 0.0, 0.0
+                    _attach_premium(st, base_acb, t, i, order, pools, events, warnings)
+                else:
+                    acb = base_acb + roll_delta
+                    proceeds = gross_cad * share
+                    outlays = comm_cad * share
+                    gain = proceeds - outlays - acb
+                    ev = _event(t, "LONG", close, proceeds, outlays, acb, gain, rate, source, group)
+                    if superficial and group == "TAXABLE" and gain < 0:
+                        _apply_superficial(ev, t, close, buys_by_symbol, buy_dates, cum_by_symbol, cum_dates, pending, pools, last_data_date, warnings)
+                    events.append(ev)
+                    pool.cost -= base_acb
+                    pool.qty -= close
+                    if abs(pool.qty) < 1e-9:
+                        pool.qty, pool.cost = 0.0, 0.0
             remainder = sell - close
             if remainder > 0:
-                if close == 0 and pool.qty == 0 and t.asset_class == "STK":
+                if close == 0 and pool.qty == 0 and t.asset_class in ("STK", "OPT") and _roll_code(t) != "O":
                     warnings.append(
                         f"{t.trade_date} sold {remainder:g} {t.symbol} in {t.broker} {t.account_id} with nothing held: "
                         "a short sale, or an opening position is missing (add it under Trades > Add manual row)"
@@ -268,6 +328,41 @@ def _event(t: Transaction, side: str, qty: float, proceeds: float, outlays: floa
     )
 
 
+def _attach_premium(st: Transaction, delta: float, t: Transaction, i: int, order: dict[int, int], pools: dict, events: list[Realized], warnings: list[str]) -> None:
+    """Attach an assignment/exercise premium (CAD, signed) to the resulting share trade.
+
+    If the share row comes later in file order, stamp it; otherwise fold it into the
+    pool that row left, or into the event that row produced.
+    """
+    if order[id(st)] > i:
+        st.raw["_roll_cad"] = st.raw.get("_roll_cad", 0.0) + delta
+        return
+    if st.quantity > 0:
+        p = pools.get((pool_group(st), st.symbol))
+        if p is not None and abs(p.qty) > 1e-9:
+            p.cost += delta
+            return
+        ev = _last_event_for(st.fingerprint, events)
+        if ev is not None:  # the row only covered a short position
+            ev.outlays_cad += delta
+            ev.gain_cad = ev.proceeds_cad - ev.outlays_cad - ev.acb_cad
+            return
+    else:
+        ev = _last_event_for(st.fingerprint, events)
+        if ev is not None:  # the row sold open shares: the premium belongs to their ACB
+            ev.acb_cad += delta
+            ev.gain_cad = ev.proceeds_cad - ev.outlays_cad - ev.acb_cad
+            return
+    warnings.append(f"{t.trade_date} {t.symbol} in {t.broker} {t.account_id}: assignment/exercise premium had no share position to attach to")
+
+
+def _last_event_for(fingerprint: str, events: list[Realized]) -> Realized | None:
+    for ev in reversed(events):
+        if ev.fingerprint == fingerprint:
+            return ev
+    return None
+
+
 def _held_at(symbol: str, d: date, cum_by_symbol, cum_dates) -> float:
     dates = cum_dates.get(symbol, [])
     i = bisect.bisect_right(dates, d)
diff --git a/tradertax/parsers/ibkr.py b/tradertax/parsers/ibkr.py
index 9eef3f2..e3ca0fc 100644
--- a/tradertax/parsers/ibkr.py
+++ b/tradertax/parsers/ibkr.py
@@ -128,7 +128,7 @@ def parse_activity_statement(rows: list[list[str]]) -> ParsedFile:
         qty = to_float(cell(r, idx, "Quantity"))
         price = to_float(cell(r, idx, "T. Price"))
         proceeds = to_float(cell(r, idx, "Proceeds"))
-        comm = abs(to_float(cell(r, idx, "Comm/Fee")))
+        comm = -to_float(cell(r, idx, "Comm/Fee"))  # negative in the file: a cost; positive: a rebate (money in)
         raw_symbol = cell(r, idx, "Symbol")
         if category.lower().startswith("forex") or category.lower() == "cash":
             out.append(
diff --git a/tradertax/taxrules.py b/tradertax/taxrules.py
index 794aa9a..2e7c06a 100644
--- a/tradertax/taxrules.py
+++ b/tradertax/taxrules.py
@@ -41,7 +41,7 @@ def marginal_rate(income: float, brackets: list[list[Any]]) -> float:
 
 @dataclass
 class Income:
-    other_income: float = 0.0  # employment, pensions, anything already taxed elsewhere
+    other_income: float = 0.0  # employment, pensions, anything already taxed elsewhere (pensionable for the CPP credit)
     business_income: float = 0.0  # net T2125 income (negative = loss)
     taxable_capital_gains: float = 0.0  # after the inclusion rate; never negative
     interest: float = 0.0
@@ -83,12 +83,17 @@ def compute_tax(rules: dict[str, Any], province: str, inc: Income) -> TaxBreakdo
     cpp = rules["cpp"]
     out = TaxBreakdown()
 
-    # CPP on self-employment income.
+    # CPP on self-employment income: the job's payroll pensionable is credited against the
+    # YMP and YAMPE first (Schedule 8), so a salary above the YAMPE leaves no CPP on the business.
     cpp_base = cpp_2 = 0.0
     if inc.cpp_on_business and inc.business_income > 0:
-        pensionable = max(0.0, min(inc.business_income, cpp["ympe"]) - cpp["exemption"])
-        cpp_base = pensionable * cpp["self_employed_base_rate"]
-        cpp_2 = max(0.0, min(inc.business_income, cpp["yampe"]) - cpp["ympe"]) * cpp["self_employed_cpp2_rate"]
+        total = inc.other_income + inc.business_income
+        emp_base = max(0.0, min(inc.other_income, cpp["ympe"]) - cpp["exemption"])
+        biz_base = max(0.0, min(total, cpp["ympe"]) - cpp["exemption"] - emp_base)
+        emp_cpp2 = max(0.0, min(inc.other_income, cpp["yampe"]) - cpp["ympe"])
+        biz_cpp2 = max(0.0, min(total, cpp["yampe"]) - cpp["ympe"] - emp_cpp2)
+        cpp_base = biz_base * cpp["self_employed_base_rate"]
+        cpp_2 = biz_cpp2 * cpp["self_employed_cpp2_rate"]
     creditable_share = cpp["employee_base_rate"] / cpp["self_employed_base_rate"]
     cpp_creditable = cpp_base * creditable_share
     cpp_deduction = cpp_base - cpp_creditable + cpp_2
diff --git a/tradertax/ui/pages.py b/tradertax/ui/pages.py
index 58d13ef..07c653a 100644
--- a/tradertax/ui/pages.py
+++ b/tradertax/ui/pages.py
@@ -80,6 +80,7 @@ class SummaryPage(Page):
             ("bill", "Total tax bill incl. other income (est.)"),
             ("rate", "Effective rate on trading"),
             ("alt", "Other treatment would owe"),
+            ("job_income", "Job income this year"),
         ]
         self.cards: dict[str, KpiCard] = {}
         for i, (key, label) in enumerate(names):
@@ -146,6 +147,7 @@ class SummaryPage(Page):
         c["rate"].set(f"{rep.effective_rate:.1%}", f"marginal rate now {rep.tax_final.marginal_rate:.1%}" if rep.tax_final else "")
         other = "capital gains" if rep.treatment == "BUSINESS" else "business income"
         c["alt"].set(money(rep.taxes_owed_alt), f"if treated as {other}")
+        c["job_income"].set(money(float(self.state.ledger.get_setting("other_income") or 0)), "same setting as Settings > Other income; it sets the marginal rate")
 
         self.ufile_model.set_rows([[u.section, u.field, u.amount, u.note] for u in rep.ufile])
         self.ufile_table.resizeRowsToContents()
```

# LEAD TEST RESULTS
## builder's own test command (exit 0)
```
.......................................................                  [100%]
55 passed in 1.19s
```
## lint (exit 0)
```
All checks passed!
```
