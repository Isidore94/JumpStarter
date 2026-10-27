TASK

# Task: `check` fails when CLAUDE.md cites an INTERNALS entry that does not exist

## Goal
CLAUDE.md marks rules with citations like `*(INTERNALS: "retrofit is report-only")*`. Today nothing verifies them: the structure audit only confirms `docs/INTERNALS.md` exists and `check` never looks at it. When done, `python tools/jumpstart.py check <repo>` reports every cited entry that has no matching heading in that repo's `docs/INTERNALS.md` and exits 1; when all citations resolve, the check passes as before.

## Done when
- `check` on a repo whose CLAUDE.md cites a missing INTERNALS entry exits 1 and names the missing entry; a repo whose citations all match exits 0.
- A test in `tests/test_jumpstart.py` proves both cases, and it fails before the change.
- `python tools/jumpstart.py check .` stays green on JumpStarter itself, and on a freshly `init`-ed project.
- `python -m pytest tests/ -q` (check the exit code) and `ruff check .` stay green.

## Constraints
- Standard library only, Python 3.9+; exit codes are the interface (0 ok, 1 gaps, 2 usage).
- `retrofit` writes nothing; `check` reports, it never edits.
- The limit constants in `tools/jumpstart.py` and `templates/` files are ask-first; avoid touching them.
- Follow the repo's doc workflow: CHANGELOG inventory, CURRENT_CHECKPOINT, a `docs/INTERNALS.md` entry if a new CLAUDE.md rule is added, then `sync-agents`.
- Keep the change small; do not touch unrelated files.

## Notes
- Headings carry a suffix, e.g. `## retrofit is report-only (2026-09-03, first build)`, and citation case differs from heading case; a sensible default is to match the cited text against the heading's leading text, case-insensitively.
- Unclear: whether a citation inside an HTML comment (`templates/CLAUDE.md` has one) or a missing INTERNALS file should count. Default: skip commented-out examples; a missing file stays the structure audit's job.

Follow the procedure at the top of CLAUDE.md (recon, plan, tests first, build, self-review, report). Stop when
`.qo/report.md` is written.
