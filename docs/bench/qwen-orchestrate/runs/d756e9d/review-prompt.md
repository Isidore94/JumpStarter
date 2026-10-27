You are reviewing a change another agent made in this checkout. The task it was given:

# Task: Summary shows P&L before commissions and the commissions paid on the year's closed trades
## Goal
The Summary page shows realised P&L before commissions and the commissions paid on the trades closed in the tax year, plus the share of those commissions that belongs to taxable accounts.
The taxable P&L keeps deducting commissions exactly as it does now, so no tax number changes.
The new card tells the user that commissions are already in the P&L and must not be entered again as an expense.
## Done when
- The year report (tradertax/summary.py) carries the new figures, and they add up: P&L before commissions minus commissions equals today's after-commission P&L, for all accounts and for the taxable share.
- A new test in tests/test_summary.py proves those numbers on the existing fixtures (buy and sell commissions, a USD trade, a TFSA trade). It fails before the change and passes after.
- The Summary page (tradertax/ui/pages.py) shows the new card with the "do not add again as an expense" note; tests/test_ui_smoke.py checks the card has a value.
- Existing taxable P&L, expense and tax figures are unchanged.
- Suite and lint stay green, as the README says: `set QT_QPA_PLATFORM=offscreen`, then `.venv\Scripts\python.exe -m pytest tests -q` and `.venv\Scripts\python.exe -m ruff check .`
## Constraints
- The repo has no CLAUDE.md. Follow the README and the existing code style (ruff settings in pyproject.toml).
- This is tax and P&L logic: verify every number by hand in the test, in CAD at the fixture FX rate.
- Do not change how gains, ACB or the UFile sheet are computed. This is display only.
- Keep the change small; do not touch unrelated files.
## Notes
- Buy commissions are folded into ACB and sell commissions are outlays, so "commissions on closed trades" means both, pro rata to the quantity closed in the year. If gains.py does not track that per event yet, add it there; do not re-derive it from raw transactions.
- "Taxable share" here means the commissions on taxable-account (margin/cash) trades. Keep broker FEE rows out; they are already a separate expense line.

The change is in `.qo/diff-for-review.patch` (same as `git diff`). Review by reproduction: read the changed code and
tests, run the tests (`C:/Users/Aaron/TraderTaxHelper/.venv/Scripts/python.exe -m pytest -q`) and lint (`C:/Users/Aaron/TraderTaxHelper/.venv/Scripts/python.exe -m ruff check .`). Look for logic errors, tests that
would pass without the fix, behaviour that differs from the task, scope creep, missing cases. Do not edit anything.
Answer with ONLY this JSON, nothing else:
{"verdict":"GO"|"NO-GO","blockers":[{"file":"","line":0,"what":""}],"advisories":[{"file":"","line":0,"what":""}],"summary":""}
