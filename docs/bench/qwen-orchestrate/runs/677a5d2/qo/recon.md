# Recon — `check` fails when CLAUDE.md cites a nonexistent INTERNALS entry

Read-only recon, 2026-10-26. Evidence is file:line.

## The behaviour that exists today

- `cmd_check` (tools/jumpstart.py:929-937) assembles exactly three audit groups:
  `audit_agents_identical` (line 934), `audit_sizes` (935), `audit_placeholders` (936),
  then `_print_report` (937). Nothing in `check` ever reads `docs/INTERNALS.md`.
- `Finding` (213-236); statuses OK/ADVISORY/MISSING/DRIFT/OVERSIZE/UNFILLED (205-210);
  a finding is a gap iff status is not OK/ADVISORY (`ok` property, 223-228).
  `_print_report` exits 1 on any gap (261).
- The structure audit's "rules carry evidence" finding (675-694, inside
  `audit_structure` 614-776) only confirms `docs/INTERNALS.md` exists (or an
  alternative `*INTERNALS*.md` under `docs/`). It is used by `cmd_retrofit`
  (895-905) only — `check` does not run it.
- Precedents to mirror:
  - `find_placeholders` (184-191): unique names, first-seen order, deduplicated.
  - `PLACEHOLDER_RE` (130) + the repo rule "A placeholder name is an identifier"
    (CLAUDE.md:124-126, docs/INTERNALS.md:143-168): the token shape is constrained so
    prose examples (`{{...}}`) do not match. Any citation regex and any new CLAUDE.md
    rule line must honour the same discipline (a literal `*(INTERNALS: "...")*` shape
    in CLAUDE.md prose would self-trip the new check).
  - `audit_placeholders` (450-474): per-file finding, UNFILLED status, remedy text.
  - `section_line_count` (157-181): heading-level parsing precedent.
  - ASCII-only printed strings (docs/INTERNALS.md:212-242 incident; test at
    tests/test_jumpstart.py:569-577).

## The citations that must resolve

Repo CLAUDE.md (the working-tree file; see baseline note below) — 9 live citations:

| cited name | CLAUDE.md line | matching `##` heading in docs/INTERNALS.md |
|---|---|---|
| `retrofit is report-only` | 104 | line 17 `## retrofit is report-only (2026-09-03, first build)` |
| `An advisory is not a gap` | 109 | line 172 |
| `init does not overwrite` | 112 | line 40 |
| `unfilled placeholders are visible` | 115 | line 59 (`## Unfilled placeholders are visible ...`) — **case differs** |
| `one source for two tools` | 117 | line 80 (`## One source for two tools ...`) — **case differs** |
| `bound the section, not the file` | 120 | line 104 |
| `templates by nature` | 123 | line 124 |
| `A placeholder name is an identifier` | 126 | line 143 |
| `An unpinned linter is not a gate` | 149-150 | line 212 — **citation wraps across two lines** (`"An unpinned linter is not a\n  gate"`); matcher must fold whitespace |

All 9 resolve; case-insensitive match against the heading's leading text (text before
the first `(`) is required. Headings carry a `(date, reason)` suffix that no citation
repeats, so the suffix must be stripped before matching.

Template CLAUDE.md (what a fresh project gets; 4 citations):

| cited name | line | note |
|---|---|---|
| `The control file itself goes stale` | templates/CLAUDE.md:40 | resolves to templates/docs/INTERNALS.md:77 |
| `Completed records only` | templates/CLAUDE.md:90 | **inside HTML comment 88-90; names an entry that never exists — must be skipped** |
| `A suite run under a known condition is not a baseline` | templates/CLAUDE.md:113 | resolves to templates/docs/INTERNALS.md:101 |
| `Another session is in this repository` | templates/CLAUDE.md:144 | resolves to templates/docs/INTERNALS.md:52 |

templates/docs/INTERNALS.md:21 is the placeholder entry heading
`## {{RULE_NAME}} ({{DATE}}, {{WHAT_PROMPTED_IT}})`; in the test fixture
(`filled_repo`, tests/test_jumpstart.py:251-269) it becomes `## filled (filled, filled)`.

## The tests that constrain the change

- `test_check_is_green_on_a_filled_repo` (tests/test_jumpstart.py:272-273): the
  filled repo's 3 live citations all resolve, so the new check must report OK there.
- `test_jumpstarter_passes_its_own_check` (395-397): `check` on the repo root must
  exit 0 — the new check must resolve all 9 repo citations plus any new one this job
  adds to CLAUDE.md.
- `test_retrofit_reports_the_gaps_on_a_bare_repo` (166-189) and
  `test_retrofit_is_clean_after_a_filled_init` (200-202): retrofit must keep working;
  the task scopes the new check to `check` only (see plan).
- `test_the_report_is_ascii_so_a_console_can_print_it` (569-577): new printed strings
  must be ASCII.
- `test_check_names_the_oversized_file_and_the_remedy` (287-295): finding detail
  naming + remedy is the established report shape to follow.

## Baseline (measured 2026-10-26, CPython 3.12.13, the harness venv)

- `pytest tests/ -q`: **1 failed, 48 passed, exit 1** —
  `test_jumpstarter_passes_its_own_check`.
- `ruff check .`: clean, exit 0.
- `check .`: **exit 1, 5 gaps of 9 findings**:
  1. `[DRIFT] CLAUDE == AGENTS` — the harness worktree prepended a 27-line
     "Orchestration rules" block to CLAUDE.md (git diff: +27 lines) while AGENTS.md
     was left as committed.
  2-5. `[UNFILLED] placeholders in .claude/agents/{tester,builder,reviewer,recon}.md`
     — the harness rewrote those files from this repo's filled-in versions back to the
     template shape with live `{{PROJECT}}`, `{{OWNER}}`, `{{CRITICAL_AREA}}`, ...
     tokens (git diff shows filled text → template tokens).
- Both causes are the harness worktree's state, not this repo's committed state.
  The task rules forbid editing files under `.claude/`, so gaps 2-5 cannot be cleared
  here; the DRIFT can be cleared with the sanctioned `sync-agents` (the task's own doc
  workflow names it). Consequence: `check .` on this worktree and
  `test_jumpstarter_passes_its_own_check` stay red after the work, for pre-existing,
  out-of-scope reasons — recorded in plan.md and report.md with this evidence.

## Files the task touches, and what already exists

- `tools/jumpstart.py` — the change site: constants near `PLACEHOLDER_RE` (130),
  helpers near `find_placeholders` (184-191), an `audit_internals_citations` near
  `audit_placeholders` (450-474), wiring in `cmd_check` (929-937), module docstring
  (9-10) and the `check` subparser help (972).
- `tests/test_jumpstart.py` — `check` section (246-341) and "Units behind the checks"
  section (345-378) are the homes for the new tests.
- `CLAUDE.md` (repo, not templates) — the `**Rules**` list (102-128) is where a rule
  about the new check belongs; workflow line 78 ("add a `docs/INTERNALS.md` entry for
  any new rule") obliges the evidence entry. The repo CLAUDE.md is NOT in the ask-first
  list (163-167 names only `templates/*` and the limit constants).
- `AGENTS.md` — regenerated via `sync-agents`, never hand-edited (rule at 116-117).
- `docs/INTERNALS.md` — new entry; entries are `##` sections, newest appended at the
  end (file ends at line 241).
- `CHANGELOG.md` — inventory (52-90: CLI bullets 61-62, test coverage 84-87) and
  "Recent changes" (from 103); "Last reconciled" stamp at line 3.
- `CURRENT_CHECKPOINT.md` — active-state block (12-51) must be refreshed; baseline
  numbers at line 23; gate table 38-47 (gate 2 still open — untouched by this work).
- `plan.md` — no remaining-work item corresponds to this task; sec 5 invariant at line
  92 ("Every rule in `CLAUDE.md` has an entry in `docs/INTERNALS.md`") is exactly the
  invariant the new check enforces — it stays true. No plan.md change needed.
- `WISHLIST.md`, `docs/README.md` — no owner-directed change, no file added or
  reclassified: no change.
- `templates/*` — ask-first, task says avoid: no change. The template already ships
  resolvable citations plus the commented-out example, which doubles as the fixture.
