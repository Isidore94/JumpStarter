# Report — IBKR statement fixes

## What changed

1. **Premium roll for assigned/exercised options** (`tradertax/gains.py`)
   - `compute_gains` now pairs each option trade carrying a conversion code
     (IBKR `A`/`Ex`, Questrade `ASN`/`EXE`) with the first unused same-day
     share trade in the same broker/account whose underlying matches
     (`_base_symbol`); the option pool's ACB for the closed portion (in CAD)
     moves into that share trade — up the cost when the premium was paid
     (long call exercised, long put exercised), down the cost when it was
     received (short put assigned, short call assigned) — and the option row
     produces no realised event.
   - Order-independent: if the share row comes later in file order the delta
     is stamped onto it (`raw["_roll_cad"]`, in-memory only, in CAD so no
     extra `fx.rate` calls); if it came first, the delta is folded into the
     pool it left or into the event it produced (LONG sell: ACB; SHORT cover:
     outlays, gain recomputed). Both orders are tested.
   - Fallbacks: no same-day share row → ordinary pool treatment; a stamp with
     nowhere to attach → warning.
2. **IBKR commission sign** (`tradertax/parsers/ibkr.py:131`)
   - `comm = -to_float(Comm/Fee)`: the file writes fees negative, so costs
     stay positive and a rebate (positive in the file) becomes a negative
     cost = money in; `net = proceeds - comm` already stays correct.
3. **O/C codes on the "nothing held" warning** (`tradertax/gains.py`)
   - A sell against an empty pool warns only when the row is not an
     intentional opening short (code `O`) — opening IBKR shorts no longer
     warn; and the warning now extends to `OPT` as well as `STK`, so a
     closing code (`C`) with no open position warns for options too.
     Message wording unchanged (Questrade rows carry no code and keep
     warning, as `test_short_sale_then_cover` pins).
4. **CPP Schedule 8 crediting** (`tradertax/taxrules.py`)
   - Employment (`other_income`) pensionable is credited against the YMP
     (net of the basic exemption) and the YAMPE (CPP2) first; the business
     earns CPP only on the leftover room. A salary above the YAMPE now
     leaves zero CPP on trading income. `other_income = 0` gives identical
     numbers to before (existing test stays green).
5. **Summary "Job income this year" card** (`tradertax/ui/pages.py`)
   - 11th KpiCard on the Summary page, display-only, reading the same
     `other_income` setting the Settings field writes — which is what feeds
     the marginal-rate scenarios in `summary.py`. Sub-line says so.

Tests: 9 new in `tests/test_gains.py`, 1 in `tests/test_parsers.py`
(rebate + cost fragment, `raw["code"]` captured), 1 in
`tests/test_tax_and_expenses.py` (three salary bands + Schedule-8 deduction
consistency), 1 assertion in `tests/test_ui_smoke.py`, and a full-pipeline
integration test in `tests/test_summary.py` (IBKR statement with a short-put
assignment through `commit_import` → `build_report`: AAPL open ACB
`(15000 + 1 − 400 + 0.65) × 1.37`, no open option position, no warning).
`tests/test_gains.py`'s `tx()` helper gained a `raw` parameter.

## Test results

- Baseline (before any change, background run): **43 passed**, ruff clean.
- Red run (new tests, no source change): **11 failed** (all new-behaviour
  tests; two tests had a first-draft error in their own expectations and
  were corrected before the build — see `.qo/tests-red.txt` note).
- Final: **`python -m pytest -q` → 55 passed** (43 + 12 new),
  **`python -m ruff check tradertax tests` → clean** (`.qo/build.txt`).
- Self-review: `.qo/review.json` — **GO**, no blockers, 6 advisories.

## What was skipped / left alone (deliberate)

- **Flex parser** (`ibkr.py`): still `abs()` on `IBCommission`; the task
  names the activity statement's `Comm/Fee` only. Advisory.
- **Export format and DB schema**: untouched, as instructed. No schema change
  was needed — the roll reads `raw` (already persisted as JSON) and mutates
  in-memory copies only; `key_fields()` excludes `raw`, so fingerprints are
  stable.
- **`tradertax/summary.py` / `config/`**: no changes needed; `other_income`
  already feeds every tax scenario, and the rules JSON already had
  `ympe`/`yampe`/`exemption`.
- **Assignment-row commissions**: not rolled (assignment rows carry no
  execution fee; accepted edge, advisory).
- A blind independent reviewer run was not spawned; per the job procedure
  the lead did the self-review itself (`.qo/review.json`), re-deriving every
  expected number by hand.

## Open doubts

- Partial assignment rolls the *proportional* pool ACB (the closed
  fraction); an assignment that closes only part of a multi-contract pool
  leaves the rest open with a proportional cost — sensible, but not
  separately tested (no such fixture row in the data model's tests).
- If two identical share rows ever share a fingerprint, the retroactive path
  adjusts the most recent matching event. No guard; noted in review.
- The retroactive ACB adjustment runs after the superficial-loss denial
  check, so an exercised long put that flips a denied loss into a gain would
  keep the denial. Rare (put exercise of shares held inside the window);
  accepted, documented.
- `other_income` is treated as fully pensionable employment income (per the
  task). Pensions in that field are not CPP-pensionable; the number will be
  slightly high for users who park pensions in the same field — same
  assumption the Settings label already makes ("job, pension").
