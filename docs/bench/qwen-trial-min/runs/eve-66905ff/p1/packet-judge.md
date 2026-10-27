# BRIEF
Goal: the screen's net_edge_pct flatters wide books. It is expected_move_pct minus breakeven_move_pct, but those two are measured against different reference points (the close and the bid), so a wide spread's cost is understated and a wide book can rank first. Price the real round trip multiplicatively instead: target_bid = vwap x (bid_walk / close); net_edge = sell proceeds at target_bid / ask_walk - 1 (the book keeps its shape as price reverts; say that assumption in a comment). A flat book already at value must net exactly minus the tax.
Done when: tests/test_screen_digest.py has a wide-spread candidate that no longer ranks first and a flat-book case that nets -tax; `PYTHONPATH=src python -m pytest -q` green, ruff clean.
Files: src/evescreener/screen.py (run_screen, the net_edge_pct line); find the helpers it needs.
Don't touch: the other gates, the digest output format, the candidate sort.
Pattern: the existing breakeven_move_pct / tiers maths in screen.py.

# CANDIDATE DIFF
```diff
diff --git a/src/evescreener/screen.py b/src/evescreener/screen.py
index e8c2f85..27b2b7b 100644
--- a/src/evescreener/screen.py
+++ b/src/evescreener/screen.py
@@ -32,7 +32,7 @@ from .signals.setup import SetupParams, anchor_grid, evaluate_setups
 from .store.db import Database
 from .timeutil import ensure_utc, iso, parse_iso, utcnow
 
-__all__ = ["Candidate", "ScreenResult", "run_screen"]
+__all__ = ["Candidate", "ScreenResult", "net_edge_pct", "run_screen"]
 
 
 @dataclass(slots=True)
@@ -151,6 +151,36 @@ def _tier_prices(row, tiers) -> dict[float, float | None]:
     return prices
 
 
+def net_edge_pct(
+    *,
+    vwap: float | None,
+    close: float | None,
+    ask_walk: float | None,
+    bid_walk: float | None,
+    costs: CostModel,
+) -> float | None:
+    """The net edge of the real round trip at the reversion price, in percent.
+
+    Subtracting `expected_move_pct` (measured from the close) from
+    `breakeven_move_pct` (measured from the bid) understates a wide spread:
+    the two percentages do not share a reference, so the cost of the walk is
+    never fully charged. Instead price the round trip multiplicatively —
+    entry crosses at the measured ask walk, and the exit fills where the bid
+    sits once the price has reverted to anchored value. The book is assumed
+    to keep its shape through that reversion, so the bid walk scales by the
+    same factor the close does: `vwap * bid_walk / close`. A wide spread is
+    charged the cost it actually is, and a flat book already at value nets
+    exactly minus the sales tax. Any missing or non-positive input is
+    UNKNOWN, never an optimistic zero.
+    """
+    if not vwap or not close or not ask_walk or not bid_walk:
+        return None
+    if vwap <= 0 or close <= 0 or ask_walk <= 0 or bid_walk <= 0:
+        return None
+    target_bid = vwap * (bid_walk / close)
+    return (costs.sell_proceeds(target_bid, maker=False) / ask_walk - 1.0) * 100.0
+
+
 def run_screen(
     config: Config,
     db: Database,
@@ -315,6 +345,15 @@ def run_screen(
         strength = real_relative_strength(
             frame, composite_frame, length=config.signals.rrs_length, scope="forge_composite"
         )
+        # The ranking quantity: the real round trip, priced multiplicatively
+        # (the book keeps its shape as the price reverts to value).
+        net_edge = net_edge_pct(
+            vwap=bands.vwap,
+            close=reference,
+            ask_walk=ask_prices[tiers[0]],
+            bid_walk=bid_prices[tiers[0]],
+            costs=costs,
+        )
         candidates.append(
             Candidate(
                 type_id=int(type_id),
@@ -339,7 +378,7 @@ def run_screen(
                     }
                     for tier in breakevens
                 ],
-                net_edge_pct=(expected_move - smallest.breakeven_move_pct),
+                net_edge_pct=net_edge,
                 expected_move_pct=expected_move,
                 entry_price=priced.entry_price,
                 exit_price=priced.exit_price_taker,
diff --git a/tests/test_screen_digest.py b/tests/test_screen_digest.py
index 13c40c6..e5f17db 100644
--- a/tests/test_screen_digest.py
+++ b/tests/test_screen_digest.py
@@ -10,6 +10,7 @@ import numpy as np
 import pandas as pd
 import pytest
 
+from evescreener.costs import CostModel
 from evescreener.digest import (
     AMBIGUOUS,
     DELIVERED,
@@ -20,7 +21,7 @@ from evescreener.digest import (
     post_digest,
     split_content,
 )
-from evescreener.screen import run_screen
+from evescreener.screen import net_edge_pct, run_screen
 from evescreener.signals.composite import build_composite
 
 NOW = datetime(2026, 8, 20, 16, 0, tzinfo=UTC)
@@ -77,6 +78,65 @@ def book_for(type_ids, *, sweep=NOW, ask=760_000.0, bid=740_000.0):
     return pd.DataFrame(rows)
 
 
+def shaped_bars(type_ids, levels):
+    """Flat at Q, a bump to P on bars 180-189, back to Q on bars 190-199.
+
+    Per `levels: {type_id: (Q, P)}`; unlisted types stay flat at 500k and can
+    never be setups (zero sigma -> dip UNKNOWN). The anchored segment starts
+    at bar 180, so its vwap is exactly (P + Q) / 2, and close[199] ==
+    close[179] makes the 20-day move exactly zero.
+    """
+    stamps = pd.date_range("2026-01-01 11:00", periods=200, freq="D", tz="UTC")
+    rows = []
+    for type_id in type_ids:
+        close = np.full(200, 500_000.0)
+        if type_id in levels:
+            q, p = levels[type_id]
+            close[:] = q
+            close[180:190] = p
+        for index, stamp in enumerate(stamps):
+            rows.append(
+                {
+                    "type_id": type_id,
+                    "region_id": 10000002,
+                    "datetime": stamp,
+                    "high": close[index] * 1.01,
+                    "low": close[index] * 0.99,
+                    "close": close[index],
+                    "volume": 100_000.0,
+                    "order_count": 400,
+                    "isk_value": close[index] * 100_000.0,
+                    "fetched_at": "2026-08-20T00:00:00+00:00",
+                }
+            )
+    return pd.DataFrame(rows)
+
+
+def wobble_bars(type_ids):
+    """A 20-bar sine wobble for every type: the composite's 20-day move is
+    exactly 0 while its ATR stays positive, so every RRS read comes out 0."""
+    stamps = pd.date_range("2026-01-01 11:00", periods=200, freq="D", tz="UTC")
+    close = 1_000_000.0 * (1.0 + 0.01 * np.sin(np.pi * np.arange(200) / 10.0))
+    rows = []
+    for type_id in type_ids:
+        for index, stamp in enumerate(stamps):
+            rows.append(
+                {
+                    "type_id": type_id,
+                    "region_id": 10000002,
+                    "datetime": stamp,
+                    "high": close[index],
+                    "low": close[index],
+                    "close": close[index],
+                    "volume": 100_000.0,
+                    "order_count": 400,
+                    "isk_value": close[index] * 100_000.0,
+                    "fetched_at": "2026-08-20T00:00:00+00:00",
+                }
+            )
+    return pd.DataFrame(rows)
+
+
 @pytest.fixture
 def seeded_db(db):
     db.replace_types([(tid, f"Type {tid}", 1857, 1.0, 1.0, 1) for tid in range(34, 50)])
@@ -147,6 +207,58 @@ def test_a_spoofed_book_is_flagged(config, seeded_db):
         assert any("one order holds" in flag for flag in result.candidates[0]["flags"])
 
 
+def test_flat_book_at_value_nets_exactly_minus_the_tax(config):
+    costs = CostModel.from_config(config)
+    edge = net_edge_pct(
+        vwap=100_000.0, close=100_000.0, ask_walk=100_000.0, bid_walk=100_000.0, costs=costs
+    )
+    # A book already sitting at value has no reversion to harvest: crossing the
+    # ask walk in and the same level out loses exactly the sales tax — no
+    # more, no less.
+    assert edge == pytest.approx(-costs.sales_tax_pct, abs=1e-12)
+
+
+def test_a_wide_spread_no_longer_ranks_first(config, seeded_db):
+    # Both types dip below anchored value and clear every gate; the wide book
+    # dips deeper AND carries the fatter spread. Under the old
+    # `expected_move - breakeven` arithmetic — one percentage against the
+    # close minus one against the bid — the wide book's spread cost was
+    # understated and this exact scenario ranked it first (+30.4934 vs
+    # +29.5663). Priced as the real round trip (entry at the ask walk, exit
+    # at the bid that keeps the book's shape through the reversion), the
+    # order flips.
+    wide, tight = 37, 38
+    levels = {wide: (700_000.0, 1_300_000.0), tight: (753_000.0, 1_255_000.0)}
+    ids = list(range(34, 44))
+    bars = shaped_bars(ids, levels)
+    composite = build_composite(wobble_bars(ids), members=10, min_members=5)
+    book = pd.concat(
+        [
+            book_for([wide], ask=760_000.0, bid=700_000.0),
+            book_for([tight], ask=757_000.0, bid=755_000.0),
+        ],
+        ignore_index=True,
+    )
+    result = run_screen(config, seeded_db, bars, composite, book, now=NOW)
+    assert result.setups_found == 2
+    assert result.unknown_cost == 0
+    assert [row["type_id"] for row in result.candidates] == [tight, wide]
+
+    costs = CostModel.from_config(config)
+    by_id = {row["type_id"]: row for row in result.candidates}
+    # Re-derive the formula from the scenario's exact inputs:
+    # target_bid = vwap * (bid_walk / close); sell proceeds net of the sales
+    # tax; edge = proceeds / ask_walk - 1.
+    for type_id, (q, p), ask, bid in (
+        (wide, levels[wide], 760_000.0, 700_000.0),
+        (tight, levels[tight], 757_000.0, 755_000.0),
+    ):
+        vwap = (p + q) / 2.0
+        expected = ((vwap * (bid / q) * (1.0 - costs.sales_tax_pct / 100.0)) / ask - 1.0) * 100.0
+        assert by_id[type_id]["net_edge_pct"] == pytest.approx(expected, abs=1e-6)
+    assert by_id[wide]["net_edge_pct"] < by_id[tight]["net_edge_pct"]
+
+
 # -- the digest -------------------------------------------------------------
 
 
```

# LEAD TEST RESULTS
## builder's own test command (exit )
```
........................................................................ [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
...........................................                              [100%]
259 passed, 7 deselected in 11.23s
```
## lint (exit )
```
All checks passed!
```
## hidden reference tests (exit )
```
....................FFFF                                                 [100%]
================================== FAILURES ===================================
_ test_net_edge_prices_the_actual_round_trip_not_a_difference_of_percentages __

    def test_net_edge_prices_the_actual_round_trip_not_a_difference_of_percentages():
        """The naive `expected_move - breakeven` form flatters wide books.
    
        Both percentages are measured against different reference points (the close
        and the bid), so subtracting them understates the cost of a wide spread �
        the exact failure mode plan.md �9 R5 warns about. This is a real Forge
        candidate from a live sweep: a 44% spread that the naive form scored at
        +16%.
        """
        from evescreener.costs import CostModel
>       from evescreener.screen import _net_edge_pct
E       ImportError: cannot import name '_net_edge_pct' from 'evescreener.screen' (C:\Users\Aaron\llm-harness\wt\qtm-66905ff\src\evescreener\screen.py)

tests\ref_test_screen_digest.py:326: ImportError
______________________ test_a_tight_book_keeps_its_edge _______________________

    def test_a_tight_book_keeps_its_edge():
        from evescreener.costs import CostModel
>       from evescreener.screen import _net_edge_pct
E       ImportError: cannot import name '_net_edge_pct' from 'evescreener.screen' (C:\Users\Aaron\llm-harness\wt\qtm-66905ff\src\evescreener\screen.py)

tests\ref_test_screen_digest.py:346: ImportError
_________________ test_net_edge_is_unknown_without_both_walks _________________

    def test_net_edge_is_unknown_without_both_walks():
        from evescreener.costs import CostModel
>       from evescreener.screen import _net_edge_pct
E       ImportError: cannot import name '_net_edge_pct' from 'evescreener.screen' (C:\Users\Aaron\llm-harness\wt\qtm-66905ff\src\evescreener\screen.py)

tests\ref_test_screen_digest.py:361: ImportError
_______________________ test_tax_is_inside_the_net_edge _______________________

    def test_tax_is_inside_the_net_edge():
        from evescreener.costs import CostModel
>       from evescreener.screen import _net_edge_pct
E       ImportError: cannot import name '_net_edge_pct' from 'evescreener.screen' (C:\Users\Aaron\llm-harness\wt\qtm-66905ff\src\evescreener\screen.py)

tests\ref_test_screen_digest.py:371: ImportError
=========================== short test summary info ===========================
FAILED tests/ref_test_screen_digest.py::test_net_edge_prices_the_actual_round_trip_not_a_difference_of_percentages
FAILED tests/ref_test_screen_digest.py::test_a_tight_book_keeps_its_edge - Im...
FAILED tests/ref_test_screen_digest.py::test_net_edge_is_unknown_without_both_walks
FAILED tests/ref_test_screen_digest.py::test_tax_is_inside_the_net_edge - Imp...
4 failed, 20 passed in 3.13s
```

# BUILDER SELF-REVIEW
```json
{
  "verdict": "GO",
  "blockers": [],
  "advisories": [
    "The helper's input guards (None / non-positive -> None) mirror breakeven_move_pct's style and are unreachable at the single call site (the gates at screen.py guarantee positive vwap/close/ask/bid there); they exist so the function stays honest if reused.",
    "net_edge_pct is strictly positive for every candidate that passes the smallest-tier gate (gate inequality r > u/(1-fee) is algebraically identical to the new net edge being > 0), so the sort at screen.py:405 keeps its exact semantics and the existing assertion net_edge_pct > 0 stays true.",
    "The scenario in test_a_wide_spread_no_longer_ranks_first is exact fixed-point (no RNG; all sums < 2^53), so the ranking inversion it pins cannot drift with seeds or libraries; margins are ~0.93pp (old formula) and ~1.35pp (new)."
  ],
  "summary": "Diff is minimal: one keyword-only helper net_edge_pct in screen.py (multiplicative round trip: target_bid = vwap * bid_walk / close, net = sell_proceeds(target_bid, maker=False) / ask_walk - 1, shape-preservation assumption stated in the docstring and at the call site), one call replacing the expected_move - breakeven subtraction, __all__ updated. No gate, digest format, sort, or costs.py change. Reproduced: reverting the call site alone makes the ranking test fail with [37, 38] != [38, 37] (the old flattering order), and every number re-derives by hand (wide: 1,000,000 * (700,000/700,000) * 0.96625 / 760,000 - 1 = +27.1382%; tight: +28.4930%; old: +30.4934% / +29.5663%). Flat book at value nets exactly -sales tax, pinned to 1e-12. Full suite 259 passed / 7 network deselected; ruff check and ruff format --check clean on the whole repo."
}
```

# REFERENCE DIFF (the merged change, for comparison)
```diff
diff --git a/src/evescreener/screen.py b/src/evescreener/screen.py
index e8c2f85..164513c 100644
--- a/src/evescreener/screen.py
+++ b/src/evescreener/screen.py
@@ -254,6 +254,13 @@ def run_screen(
         expected_move = (
             (bands.vwap / reference - 1.0) * 100.0 if bands.known and reference > 0 else None
         )
+        net_edge = _net_edge_pct(
+            vwap=bands.vwap if bands.known else None,
+            close=reference,
+            ask_walk=ask_prices[tiers[0]],
+            bid_walk=bid_prices[tiers[0]],
+            costs=costs,
+        )
         priced = costs.price_round_trip(
             notional_isk=tiers[0],
             ask_walk_price=ask_prices[tiers[0]],
@@ -296,7 +303,7 @@ def run_screen(
             # UNKNOWN cost is never shown as an opportunity, but the count is
             # reported so an outage does not look like an absence of setups.
             continue
-        if expected_move is None or expected_move <= smallest.breakeven_move_pct:
+        if net_edge is None or net_edge <= config.screen.min_net_edge_pct:
             result.below_breakeven += 1
             continue
 
@@ -339,7 +346,7 @@ def run_screen(
                     }
                     for tier in breakevens
                 ],
-                net_edge_pct=(expected_move - smallest.breakeven_move_pct),
+                net_edge_pct=net_edge,
                 expected_move_pct=expected_move,
                 entry_price=priced.entry_price,
                 exit_price=priced.exit_price_taker,
@@ -368,6 +375,42 @@ def run_screen(
     return result
 
 
+def _net_edge_pct(
+    *,
+    vwap: float | None,
+    close: float | None,
+    ask_walk: float | None,
+    bid_walk: float | None,
+    costs: CostModel,
+) -> float | None:
+    """Net edge of the actual round trip, at the actual size.
+
+    The naive version — `expected_move_pct − breakeven_move_pct` — is wrong,
+    and wrong in the dangerous direction. Those two percentages are measured
+    against *different* reference points (the close and the bid), so
+    subtracting them systematically flatters a wide book: exactly the
+    "gorgeous margin that is really an illiquidity premium" failure §9 R5
+    warns about. On a real Forge candidate with a 44% spread the naive form
+    reported +16% where the honest form reports +8.6%.
+
+    The honest form prices the entry and the exit multiplicatively:
+
+        target_bid  = vwap x (bid_walk / close)   # the bid when value is reached
+        net_edge    = sell_proceeds(target_bid) / ask_walk − 1
+
+    **Stated assumption:** the book keeps its *proportional* shape as price
+    reverts, so the spread scales with the level. That is the defensible choice
+    for ISK prices spanning twelve orders of magnitude; it is an assumption, not
+    a measurement, and a wide book is penalised by it rather than rewarded.
+    """
+    if not vwap or not close or not ask_walk or not bid_walk:
+        return None
+    if close <= 0 or ask_walk <= 0 or bid_walk <= 0:
+        return None
+    target_bid = vwap * (bid_walk / close)
+    return (costs.sell_proceeds(target_bid, maker=False) / ask_walk - 1.0) * 100.0
+
+
 def _gate_counts(evaluated: pd.DataFrame) -> dict:
     last = evaluated.iloc[-1]
     counts = {}
diff --git a/tests/test_screen_digest.py b/tests/test_screen_digest.py
index 13c40c6..92aba81 100644
--- a/tests/test_screen_digest.py
+++ b/tests/test_screen_digest.py
@@ -308,3 +308,69 @@ def test_a_partial_send_reports_how_many_landed(repo_root, paths):
     assert result.kind == REJECTED
     assert result.messages == 1
     assert "1/" in result.detail
+
+
+# -- the net-edge metric ----------------------------------------------------
+
+
+def test_net_edge_prices_the_actual_round_trip_not_a_difference_of_percentages():
+    """The naive `expected_move - breakeven` form flatters wide books.
+
+    Both percentages are measured against different reference points (the close
+    and the bid), so subtracting them understates the cost of a wide spread —
+    the exact failure mode plan.md §9 R5 warns about. This is a real Forge
+    candidate from a live sweep: a 44% spread that the naive form scored at
+    +16%.
+    """
+    from evescreener.costs import CostModel
+    from evescreener.screen import _net_edge_pct
+
+    costs = CostModel.from_config(__import__("evescreener.config", fromlist=["x"]).example_config())
+    wide = _net_edge_pct(
+        vwap=1_496_450.47,
+        close=742_600.0,
+        ask_walk=979_080.95,
+        bid_walk=546_153.16,
+        costs=costs,
+    )
+    naive = (1_496_450.47 / 742_600.0 - 1) * 100 - (
+        979_080.95 / ((1 - 0.03375) * 546_153.16) - 1
+    ) * 100
+    assert wide == pytest.approx(8.62, abs=0.05)
+    assert naive == pytest.approx(15.98, abs=0.05)
+    assert wide < naive, "the honest form must penalise the spread, not hide it"
+
+
+def test_a_tight_book_keeps_its_edge():
+    from evescreener.costs import CostModel
+    from evescreener.screen import _net_edge_pct
+
+    costs = CostModel.from_config(__import__("evescreener.config", fromlist=["x"]).example_config())
+    tight = _net_edge_pct(
+        vwap=1_496_450.47,
+        close=742_600.0,
+        ask_walk=745_000.0,
+        bid_walk=740_000.0,
+        costs=costs,
+    )
+    assert tight > 90.0
+
+
+def test_net_edge_is_unknown_without_both_walks():
+    from evescreener.costs import CostModel
+    from evescreener.screen import _net_edge_pct
+
+    costs = CostModel.from_config(__import__("evescreener.config", fromlist=["x"]).example_config())
+    assert _net_edge_pct(vwap=100, close=50, ask_walk=None, bid_walk=50, costs=costs) is None
+    assert _net_edge_pct(vwap=100, close=50, ask_walk=60, bid_walk=None, costs=costs) is None
+    assert _net_edge_pct(vwap=None, close=50, ask_walk=60, bid_walk=50, costs=costs) is None
+
+
+def test_tax_is_inside_the_net_edge():
+    from evescreener.costs import CostModel
+    from evescreener.screen import _net_edge_pct
+
+    costs = CostModel.from_config(__import__("evescreener.config", fromlist=["x"]).example_config())
+    # A perfectly flat book already at value: the only thing left is the tax.
+    flat = _net_edge_pct(vwap=100.0, close=100.0, ask_walk=100.0, bid_walk=100.0, costs=costs)
+    assert flat == pytest.approx(-3.375, abs=1e-6)
```
