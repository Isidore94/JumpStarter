TASK

Goal: Codex cannot pick our roles natively. Add a lead config template templates/.codex/config.toml that sets the lead model to Astra at high effort with Terra/high as the fallback subagent, and give each of the four templates/.codex/agents/*.toml a top-level name and description. init installs the config like the other files (never overwriting without --force). check and retrofit report a missing config, a missing native role file, or a missing or empty name/description in the four role TOMLs as gaps, reading only top-level TOML fields and writing nothing.
Done when: new tests cover install-without-overwrite, the gap reports and the metadata audit; `python -m pytest tests/ -q` green, `ruff check .` clean, `python tools/jumpstart.py check .` green on this repo.
Files: tools/jumpstart.py (the audit_* functions and the file tables near the top), templates/.codex/; find the rest.
Don't touch: templates/.claude/agents/, the existing tests.
Pattern: copy how the existing audits build a Finding and how the file tables map templates to repo paths.

You already worked on this task in this checkout: your earlier changes are in the working tree and your notes are in
`.qo/`. The lead ran the tests and found this:

Your previous pass stopped at the turn cap while editing CHANGELOG.md; the code and tests are in the worktree. Finish the job:
1. `ruff check .` fails with one error: tests/test_codex_lead_config.py:228 uses the alias `re.M` (FURB167); use `re.MULTILINE`.
2. Finish the CHANGELOG/docs edits you had started, keep them short.
3. Run `python -m pytest tests/ -q`, `ruff check .` and `python tools/jumpstart.py check .` and make all three green.
4. Then do the self-review and write .qo/review.json and .qo/report.md as the instructions say.

Fix it: change code and tests as needed, run the test files you touched and lint (Commands in CLAUDE.md), then
rewrite `.qo/report.md`. Stop when it is written.
