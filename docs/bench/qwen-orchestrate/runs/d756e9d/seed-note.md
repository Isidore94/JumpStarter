# Seed note: d756e9d

## The bug

`tradertax/gains.py:206` (short-cover branch of `compute_gains`). The short open's commission held in the pool is attributed to a cover in full instead of pro rata:

```
- _event(..., group, pool.comm * frac + comm_cad * (cover / qty))
+ _event(..., group, pool.comm + comm_cad * (cover / qty))
```

The pool decrement two lines below still removes only `pool.comm * frac`, so on a partial cover the first cover takes the whole open commission and the leftover share is counted again by the next cover. `commissions_cad` per close, `commissions_on_closed` and `*_pnl_before_commissions` are overstated. `gain_cad` (after-commission P&L, the tax figure) is untouched, and "before minus commissions == after" still holds because both sides come from the same inflated field.

Why the suite misses it: the only short in the fixtures (TSLA -20 then +20) is covered in one trade, so `frac == 1` and both versions agree. The long side is unchanged (AAPL's two partial sells still pin it).

## Concrete example (CAD, rate 1)

Short 20 XYZ @200 (comm 1.00), cover 10 @190 (comm 1.00), cover 10 @190 (comm 1.00).
Correct: commissions on closed = 1.00 + 1.00 + 1.00 = 3.00; P&L before commissions = 4000 - 3800 = 200.00.
Seeded: first cover 1.00 (whole open comm) + 1.00, second cover 0.50 (leftover half) + 1.00 = 3.50; before-commissions P&L 200.50.

## One-off check

Script (kept in the scratchpad, never in the worktree): `C:\Users\Aaron\AppData\Local\Temp\claude\C--Users-Aaron-JumpStarter\19cb6605-b0ab-4251-af2c-f624eb381fbd\scratchpad\check\check_seed.py`. It calls `compute_gains` on the three trades above and sums `commissions_cad` and `gain_cad`. Run from the copy root with `PYTHONPATH=.`.

Without the seed:
```
per-close commissions: [1.5, 1.5]
commissions_on_closed=3.00 (expected 3.00)  pnl_after=197.00 (expected 197.00)  pnl_before=200.00 (expected 200.00)
```

With the seed:
```
per-close commissions: [2.0, 1.5]
commissions_on_closed=3.50 (expected 3.00)  pnl_after=197.00 (expected 197.00)  pnl_before=200.50 (expected 200.00)
```

## Suite and lint with the seed (in the scratchpad copy)

- `python -m pytest -q`: `48 passed in 1.09s`
- `python -m ruff check .`: `All checks passed!`
- `git -C C:/Users/Aaron/llm-harness/wt/qo-d756e9d apply --check seed.patch`: exit 0, no output.
- The original worktree was not modified (`git status --short` unchanged: the agent's 5 modified files plus its untracked `.claude/`, `.qo/`, `CLAUDE.md`).
