# Recon — `net_edge_pct` prices wide books too well

Recon done read-only by the lead (no agent needed: one source file, one test
file, one config file).

## Where the number comes from today

- `src/evescreener/screen.py:342` — the line to change:
  `net_edge_pct=(expected_move - smallest.breakeven_move_pct)` inside
  `Candidate(...)` in `run_screen`.
- `expected_move` — `screen.py:254-256`:
  `(bands.vwap / reference - 1.0) * 100.0` where
  `reference = float(last["close"])` (`screen.py:241`). Measured against the
  **close**. `bands` = `anchored_vwap_bands(frame, anchors[-1])`
  (`screen.py:248-251`); `anchor_grid` over 200 daily bars with
  `anchor_lookback_days=90` puts the live anchor at bar 180, so the segment is
  the last 20 bars.
- `smallest.breakeven_move_pct` — `screen.py:242-247` calls
  `costs.tier_breakevens(ask_prices, bid_prices, reference_price=reference, ...)`
  → `costs.py:145-168` `breakeven_move_pct`: `required_exit = entry/(1-fee)`;
  `(required_exit / exit_price - 1) * 100` — the move the price must make from
  the **bid** (the exit walk) to break even. Any missing input → None (UNKNOWN).
- So the two subtracted percentages use different reference points (close vs
  bid); the spread cost is the difference `ask/bid` and it is not charged
  multiplicatively. Empirically (probe, `.qo/scratch/probe2.py`): same
  expected move, wide book vs tight book → old net `+30.49%` vs `+29.57%`,
  the wide book flattered and ranked first.

## The target formula (task)

```
target_bid = vwap * (bid_walk / close)          # book keeps its shape as price reverts
net_edge   = sell_proceeds(target_bid) / ask_walk - 1
```
- Helper already exists: `CostModel.sell_proceeds` — `costs.py:117-120`
  (`gross * (1 - (sales_tax + broker)/100)`; taker exit → tax only).
- Flat book at value: `target_bid = close`, `ask_walk = close` →
  `net_edge = -(sales_tax_pct)` exactly (tax 3.375% at Accounting V,
  `config.example.toml:61-81`).

## Call-site guarantees (so the new line stays simple)

`run_screen` only reaches line 342 after:
- the smallest-tier breakeven is not None (`screen.py:291-298`), which requires
  `ask_prices[tiers[0]]`, `bid_prices[tiers[0]]` and `reference > 0`
  (`costs.py:160-163`);
- `expected_move` is not None (`screen.py:299`), which requires `bands.known`
  and `reference > 0` (`screen.py:255`) → `bands.vwap > 0`.
So all four formula inputs are positive known floats at the call site.

## Consumers of `net_edge_pct` (must not change behaviour contract)

- `Candidate.net_edge_pct` field `screen.py:52`, `as_dict` `screen.py:78`.
- Sort: `screen.py:366` `candidates.sort(key=lambda item: -(item.net_edge_pct or 0.0))` —
  **don't touch** (task).
- Digest display: `digest.py:129` prints it as "net edge" — format **don't touch**.
- `config.screen.min_net_edge_pct` (`config.py:122`, `config.example.toml:139`) is
  defined but unused by `run_screen` — not a gate today; leave it.
- `costs.py:240-243` `price_round_trip` computes `net_edge_pct_taker` at the
  *current* bid walk (no reversion) — a different quantity, feeds
  `entry_price`/`exit_price` display fields; not the candidate's
  `net_edge_pct`. Leave alone.

## The gate (must keep passing, must not touch)

- Setup gates: `setup.py:135-173` tri-state; `is_setup` = all four true.
  `below_anchored_value`: `dip_sigma <= -1` (`entry_band_sigma=1.0`);
  `relative_strength_intact`: `rrs >= -0.5`;
  `participation_intact`: `participation >= 0.7`;
  `measurable`: `atr20 > 0`, `order_count > 0`, `bar_number >= 120`
  (`min_bars=120`, `config.example.toml:164-175`).
- Breakeven gate: `screen.py:299-301` `expected_move <= smallest.breakeven_move_pct`
  → `below_breakeven`. Note the gate is `r > u/(1-fee)` with
  `r = vwap/close`, `u = ask/bid` — the *same* inequality that makes the new
  multiplicative net edge positive, so candidates keep `net_edge_pct > 0`
  after the change (existing test at `tests/test_screen_digest.py:103` relies
  on that).

## Tests

- `tests/test_screen_digest.py` is the file the task names:
  - `bars_for` (line 29): seeded random walk, optional step dip.
  - `book_for` (line 55): per-type sell/buy rows, flat depth fills on all
    three tiers, `top_order_volume_share=0.05`, `station_volume_share=1.0`
    (no flags).
  - `seeded_db` fixture (line 80): registers type ids 34..49.
  - `test_a_dip_that_clears_costs_becomes_a_candidate` (line 95): asserts
    `net_edge_pct > 0` and `expected_move_pct > breakeven_move_pct` — stays
    green under the new formula (see gate note above); otherwise defensive
    (`if result.candidates:`) because the seed rarely clears a 4.88% breakeven.
  - Digest/delivery tests (lines 150+): only read `net_edge_pct` for display
    via `build_digest`; no numeric assumption.
- `tests/test_costs.py:72-100`: pins `sell_proceeds`/`price_round_trip`
  semantics (tax 3.375%, maker tax+broker 4.375%) — no change planned there.
- Baseline verified green: `pytest -q tests/test_screen_digest.py tests/test_costs.py`
  → 33 passed.

## Scenario verified for the ranking test (probe2, deterministic — no RNG)

Screened bars (200 daily, `high=1.01*close`, `low=0.99*close`, volume 100k,
order_count 400):
- type 37 (WIDE): close = 700,000 (bars 0–179 and 190–199), 1,300,000
  (bars 180–189) → segment vwap = 1,000,000 = (10/7)·close, and the 20-day
  close move is exactly 0 (close[199] == close[179]).
- type 38 (TIGHT): close = 753,000 / 1,255,000 → vwap = 1,004,000 =
  (4/3)·close.
- types 34, 35, 36, 39–43: constant 500,000 → sigma = 0 → dip UNKNOWN → no
  setup, never a candidate.
- Composite (separate frame, same stamps): all 10 types on
  `1e6·(1 + 0.01·sin(πt/10))` (period 20 bars) → 20-day move exactly 0,
  positive ATR → power index 0 → RRS = 0 for both candidates.
- Books: 37 ask 760,000 / bid 700,000 (u = 38/35); 38 ask 757,000 /
  bid 755,000 (u ≈ 1.00265).

Probe result through the live `run_screen` (old formula): both pass every
gate (`setups_found=2`, `unknown_cost=0`, `below_breakeven=0`, rrs 0.0000,
band LOWER_1_2, no flags); order `[37, 38]` — the wide book currently ranks
first (+30.4934 vs +29.5663). Under the task's multiplicative formula the
order becomes `[38, 37]` (+28.4930 vs +27.1382). Margins ≈ 0.93pp (old) and
≈ 1.35pp (new), on exact fixed-point numbers (all sums < 2^53), so the
inversion is stable.
