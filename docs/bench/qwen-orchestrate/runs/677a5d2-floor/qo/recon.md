# Recon — `check` verifies INTERNALS citations

Task: `check` fails when CLAUDE.md cites an INTERNALS entry that does not exist.

## What exists today

`check` runs exactly three audit families (`tools/jumpstart.py:929-937`, `cmd_check`):
- `audit_agents_identical(repo)` — `CLAUDE == AGENTS` sha256 (`:413`).
- `audit_sizes(repo)` — the four size limits (`:269`).
- `audit_placeholders(repo)` — unfilled `{{TOKEN}}` (`:450`).

It never reads `docs/INTERNALS.md`. The only place `check`/`retrofit` mentions INTERNALS
is `audit_structure` (`:675-694`), which is used **only by `retrofit`** and only checks the
*file exists* ("rules carry evidence") — it never looks at the citations.

## The citation format (evidence)

Citations appear in CLAUDE.md as `*(INTERNALS: "<name>")*`, one per rule:
- `CLAUDE.md:104` `*(INTERNALS: "retrofit is report-only")*`
- `CLAUDE.md:109` `*(INTERNALS: "An advisory is not a gap")*`
- `CLAUDE.md:112` `*(INTERNALS: "init does not overwrite")*`
- `CLAUDE.md:115` `*(INTERNALS: "unfilled placeholders are visible")*`
- `CLAUDE.md:117` `*(INTERNALS: "one source for two tools")*`
- `CLAUDE.md:120` `*(INTERNALS: "bound the section, not the file")*`
- `CLAUDE.md:123` `*(INTERNALS: "templates by nature")*`
- `CLAUDE.md:126` `*(INTERNALS: "A placeholder name is an identifier")*`
- `CLAUDE.md:149-150` `*(INTERNALS: "An unpinned linter is not a\n  gate")*` — **spans two
  lines**; a line-oriented extraction would miss the name.

Case differs from the heading: citation `unfilled placeholders are visible` vs heading
`## Unfilled placeholders are visible (…)` (`docs/INTERNALS.md:59`). Headings carry a
trailing suffix, e.g. `## retrofit is report-only (2026-09-03, first build)`
(`docs/INTERNALS.md:17`). Matching must be case-insensitive against the heading's leading
text (the part before the trailing ` (…)`).

The template `templates/CLAUDE.md` also has one citation **inside an HTML comment**:
`templates/CLAUDE.md:88-90`
`- <!-- … *(INTERNALS: "Completed records only")* -->`. That must be skipped.
Template citations that are real (not commented): `templates/CLAUDE.md:40`
(`The control file itself goes stale`), `:113` (`A suite run under a known condition is
not a baseline`), `:144` (`Another session is in this repository`) — each has a matching
heading in `templates/docs/INTERNALS.md:52,77,101`.

## Where a new check plugs in

`cmd_check` (`:929-937`) builds a `list[Finding]` and hands it to `_print_report`
(`:239`), which exits 1 if any finding has `ok == False`. The `Finding` class and its
statuses are at `:205-236` (`OK`, `ADVISORY`, `MISSING`, `DRIFT`, `OVERSIZE`, `UNFILLED`).
The existing "list N things, one Finding" pattern to copy is `audit_placeholders`
(`:450-474`). Helpers live near `find_placeholders` (`:184`); the regexes are module-level
(`:130` `PLACEHOLDER_RE`). `section_line_count` (`:157`) already walks headings, so heading
parsing is an established idiom.

## The invariant being enforced

"Every rule in `CLAUDE.md` has an entry in `docs/INTERNALS.md`" is a hard invariant
(`plan.md:92`) and is currently "enforced by nobody" (`CURRENT_CHECKPOINT.md:156-158` names
it as one of the three things the audit "still cannot check"). This task closes that.

## Current state of this checkout (measured)

`check .` is **red for pre-existing reasons, not the task's**: the harness added
orchestration rules to `CLAUDE.md` but not `AGENTS.md` (→ `DRIFT`), and the
`.claude/agents/*.md` files have unfilled placeholders (→ 4× `UNFILLED`). 5 gaps of 9.
Consequently `pytest tests/ -q` is **48 passed, 1 failed** — the failure is
`test_jumpstarter_passes_its_own_check` (`tests/test_jumpstart.py:395`), which runs
`check .` and asserts 0. `ruff check .` is green. I must not touch `CLAUDE.md` or
`.claude/`, so those gaps stay; the task's "stays green" therefore reads as **my change adds
no new gap and no new test failure**.

## Tests that touch this area

`tests/test_jumpstart.py`:
- `test_check_is_green_on_a_filled_repo` (`:272`) — `filled_repo` fixture (`:251`) replaces
  every `{{...}}` with `filled`; its CLAUDE.md citations all resolve, so it stays green.
- `test_jumpstarter_passes_its_own_check` (`:395`) — `check .` on this repo.
- The check tests use the `filled_repo` fixture; the "Units behind the checks" section
  (`:343`) is where unit tests for new helpers belong.
