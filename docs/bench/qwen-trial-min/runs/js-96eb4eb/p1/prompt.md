TASK

Goal: Codex cannot pick our roles natively. Add a lead config template templates/.codex/config.toml that sets the lead model to Astra at high effort with Terra/high as the fallback subagent, and give each of the four templates/.codex/agents/*.toml a top-level name and description. init installs the config like the other files (never overwriting without --force). check and retrofit report a missing config, a missing native role file, or a missing or empty name/description in the four role TOMLs as gaps, reading only top-level TOML fields and writing nothing.
Done when: new tests cover install-without-overwrite, the gap reports and the metadata audit; `python -m pytest tests/ -q` green, `ruff check .` clean, `python tools/jumpstart.py check .` green on this repo.
Files: tools/jumpstart.py (the audit_* functions and the file tables near the top), templates/.codex/; find the rest.
Don't touch: templates/.claude/agents/, the existing tests.
Pattern: copy how the existing audits build a Finding and how the file tables map templates to repo paths.

Follow the procedure at the top of CLAUDE.md (recon, plan, tests first, build, self-review, report). Stop when
`.qo/report.md` is written.
