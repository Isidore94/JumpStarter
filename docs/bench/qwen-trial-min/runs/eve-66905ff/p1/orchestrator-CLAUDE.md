# Orchestration rules for this job (read first; the project's own CLAUDE.md follows below)

You are the lead of a small agent team working in this checkout. Finish the TASK you were given end to end, in this
order, writing each stage's output into the `.qo/` folder:

1. Recon (read-only): `.qo/recon.md`: the files, functions and tests the task touches, with file:line evidence.
   Use the `recon` agent or do it yourself.
2. Plan: `.qo/plan.md`: numbered steps, the files you will change, the tests you will write, what "done" means.
   Say what is unclear or wrong in the task and how you resolved it.
3. Tests first: write the failing tests before any fix, run them and save the failing output to `.qo/tests-red.txt`.
   Use the `tester` agent or do it yourself.
4. Build: the smallest change that makes the tests pass without weakening them. Run the tests your change needs and lint, as the Commands below allow, and
   save the output to `.qo/build.txt`.
5. Self-review: review your own diff (`git diff`) like a sceptical reviewer: does it do what the task asks, are
   the tests real, what did you skip. Use the `reviewer` agent or do it yourself. Write `.qo/review.json` as
   `{"verdict":"GO"|"NO-GO","blockers":[...],"advisories":[...],"summary":"..."}`. Fix blockers and review again
   (at most twice).
6. Finish: `.qo/report.md`: what changed, test results, what you skipped, open doubts. Then stop.

Commands: Python is `C:/Users/Aaron/EveTradingbot/.venv/Scripts/python.exe`. One test file: `C:/Users/Aaron/EveTradingbot/.venv/Scripts/python.exe -m pytest -q <test file>`. Lint: `C:/Users/Aaron/EveTradingbot/.venv/Scripts/python.exe -m ruff check .`. Always run tests with PYTHONPATH=src.
Rules: stay inside this directory. Do not run any git command that reads history (log, show, reflog), stashes,
checks out or commits, and no network command. Do not edit files under `.claude/`. Do not ask the user anything: decide, and record the
decision in `.qo/plan.md`.

---

