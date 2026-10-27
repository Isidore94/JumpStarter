# Plan — `check` fails when CLAUDE.md cites a nonexistent INTERNALS entry

## What "done" means

1. `check` on a repo whose CLAUDE.md cites an entry with no matching `##` heading in
   `docs/INTERNALS.md` exits 1 and names that entry; a repo whose citations all match
   exits 0 (reporting an OK finding, not silence).
2. New tests in `tests/test_jumpstart.py` prove both cases and fail before the change.
3. `check .` on this worktree: no new gaps of any kind; the citation check reports OK
   for the repo's own 9 citations plus the one this job adds. The 4 pre-existing
   UNFILLED gaps in `.claude/agents/*.md` remain (out of scope, see
   "pre-existing red" below); the pre-existing CLAUDE↔AGENTS drift is cleared with
   `sync-agents`.
4. A freshly `init`-ed repo with its placeholders filled (the `filled_repo` fixture
   shape) passes `check` — the template's 3 live citations all resolve and the
   commented-out 4th is skipped.
5. `ruff check .` clean; `pytest tests/ -q` green except the one pre-existing failure
   named below, which this change neither causes nor worsens.
6. Docs reconciled: repo CLAUDE.md rule + INTERNALS entry + `sync-agents`, CHANGELOG
   inventory and recent-changes entry, checkpoint block refreshed.

## Decisions on the task's unclear points

- **Scope: `check` only, not `retrofit`.** The task's goal and Done-when name `check`
  exclusively. Retrofit's contract is a documented "25 checks" (CHANGELOG.md:60,
  CURRENT_CHECKPOINT.md:23, plan.md Phase 0); adopting the check there would change that
  contract and widen the doc surface. If the owner wants it in the full standard later,
  `audit_internals_citations` is a ready-made function to add to `audit_structure`.
- **Citations in HTML comments are skipped** (task default). Load-bearing:
  `templates/CLAUDE.md:88-90` ships a commented-out example citing
  "Completed records only", an entry that never exists; a check that reads comments
  would be red in every freshly initialised project.
- **A missing `docs/INTERNALS.md` is not a citation gap.** Task default: the structure
  audit ("rules carry evidence", tools/jumpstart.py:675-694) owns the file's
  existence. With the file absent there is nothing to resolve against, so
  `audit_internals_citations` returns no findings and `check` does not double-report
  what `retrofit` already names.
- **Matching rule.** Citation = the full `*(INTERNALS: "...")*` pointer form (that is
  the form the task defines and every citation in this repo and the templates uses).
  Consequences: (a) prose that merely mentions `INTERNALS:` does not read as a
  citation — same discipline as "a placeholder name is an identifier"
  (docs/INTERNALS.md:143-168), which is also why the new CLAUDE.md rule line is
  written without the literal quoted form; (b) the cited name may wrap across lines
  (CLAUDE.md:149-150 does), so it is folded to single spaces before matching;
  (c) headings are matched on their leading text — text before the first `(`, which
  strips the `(date, reason)` suffix — case-insensitively, at `##` level only
  (`###` sub-headings are not entries).
- **Report shape.** One `MISSING` finding per dangling citation, each naming the entry
  (a report that says "3 citations are wrong" without saying which is a report the
  next agent has to re-derive); one `OK` finding when every citation resolves, so a
  green report shows the check ran. Status `MISSING` — no new status constant; the
  entry is what is missing.
- **A new rule goes into this repo's CLAUDE.md, with its INTERNALS entry.** The repo's
  convention (CLAUDE.md:78, plan.md sec 5 line 92) is that a check's behaviour is a
  `Core rules` bullet with an evidence entry; the new check creates a new contract
  (a dangling citation now fails `check`) that the agent-reader should see. The repo
  CLAUDE.md is not in the ask-first list (CLAUDE.md:163-167 names only `templates/*`
  and the limit constants), so this is decided, not asked. `templates/CLAUDE.md` is
  NOT touched (task: avoid templates); downstream projects get the enforcement in the
  tool and the citation convention they already ship.
- **Pre-existing red, decided up front.** Baseline: `pytest` exit 1
  (`test_jumpstarter_passes_its_own_check`) and `check .` exit 1 with 5 gaps —
  1 DRIFT from the harness-prepended CLAUDE.md block, 4 UNFILLED in
  `.claude/agents/*.md` (harness-rewritten to template shape with live `{{...}}`
  tokens; evidence in .qo/recon.md "Baseline"). The task rules forbid editing under
  `.claude/`, and weakening the placeholder check to hide the gaps is forbidden by
  "without weakening them". So: run `sync-agents` (sanctioned; the task's workflow
  names it) to clear the DRIFT, leave the 4 UNFILLED gaps and the one test that
  asserts `check .` is green on this worktree, and record both with evidence in
  report.md. No test is weakened, skipped or deleted; nothing new is made red.

## Files to change

1. `tools/jumpstart.py`
   - `INTERNALS_CITATION_RE = re.compile(r'\*\(INTERNALS:\s*"([^"]+)"\)\*')` and a
     `HTML_COMMENT_RE` near `PLACEHOLDER_RE` (line 130).
   - `find_internals_citations(text) -> list[str]`: unique cited names, first-seen
     order, HTML comments stripped first, names whitespace-folded.
   - `internals_headings(text) -> list[str]`: leading text of each `##` heading,
     trailing `( ... )` suffix removed.
   - `audit_internals_citations(repo) -> list[Finding]`: no CLAUDE.md → no findings
     (its absence is the drift check's); no citations → one OK; INTERNALS.md absent →
     no findings (structure audit's job); else per-missing-entry MISSING findings with
     an add-the-entry-or-drop-the-citation remedy, else one OK naming the count.
   - `cmd_check`: append `findings.extend(audit_internals_citations(repo))`.
   - Module docstring (lines 9-10) and the `check` subparser help (line 972) say the
     new scope.
2. `tests/test_jumpstart.py` — six new tests (below), written before the fix.
3. `CLAUDE.md` (repo) — one new bullet at the end of the `**Rules**` list
   (after line 128), citing the new entry; worded so its own text contains no
   literal `*(INTERNALS: "...")*` shape besides its genuine citation.
4. `docs/INTERNALS.md` — new entry `## A citation must resolve (2026-10-26, ...)`
   appended after the last entry, house format (rule / what happened / measured /
   deliberately not done / reopen trigger).
5. `AGENTS.md` — via `python tools/jumpstart.py sync-agents .` after the CLAUDE.md
   edit (also clears the pre-existing drift; note: this copies the harness block into
   AGENTS.md, which is exactly what the sha256 invariant requires).
6. `CHANGELOG.md` — "Last reconciled" → 2026-10-26; CLI inventory: the `check` bullet
   gains the citation scope and a bullet for the three new functions; test-coverage
   bullet gains the citation cases; new dated entry under "Recent changes".
7. `CURRENT_CHECKPOINT.md` — refresh the active-state block (branch `main`, this
   worktree; active item; measured baseline with the pre-existing-red note) and add a
   dated entry. Gate table untouched (gate 2 still open, not closed by this work).
8. No changes: `plan.md` (no corresponding item; the sec 5 invariant it states is
   enforced, not violated), `WISHLIST.md`, `docs/README.md`, `templates/*`,
   `.claude/*`, `tools/` limit constants.

## Tests to write (all fail before the change)

In the `check` section:
1. `test_check_fails_and_names_a_dangling_internals_citation` — `filled_repo` + a rule
   appended to CLAUDE.md citing "a rule with no entry yet" + `sync-agents`; `check`
   exits 1 and the output names the entry with a MISSING status. (Red before: check
   exits 0 and never mentions citations.)
2. `test_check_passes_when_every_internals_citation_resolves` — `filled_repo` as-is;
   `check` exits 0 and exactly one `INTERNALS citations` finding prints, OK.
   (Red before: no such finding exists.)

In "Units behind the checks":
3. `test_internals_citations_fold_wrapped_names_and_skip_comments` — a commented-out
   citation is absent from the result; a citation wrapping onto the next line comes
   back whitespace-folded.
4. `test_internals_citation_matches_ignore_case_and_the_heading_suffix` — lowercase
   citation resolves a capitalized heading with a `(date, reason)` suffix → OK finding.
5. `test_a_citation_with_no_heading_is_a_named_gap` — one MISSING finding, not ok,
   detail names the entry.
6. `test_a_missing_internals_file_is_not_a_citation_gap` — CLAUDE.md with a citation,
   no `docs/` at all → no findings (structure audit's job).

## Steps

1. (done) Recon → `.qo/recon.md`; this plan.
2. Write the six tests into `tests/test_jumpstart.py`. Run
   `pytest tests/test_jumpstart.py -q`; save the failing output to
   `.qo/tests-red.txt` (expect the six new failures plus the one pre-existing
   `test_jumpstarter_passes_its_own_check` failure).
3. Implement `tools/jumpstart.py` per file list item 1.
4. Add the CLAUDE.md rule bullet, the INTERNALS.md entry; run `sync-agents`.
5. Update CHANGELOG.md and CURRENT_CHECKPOINT.md.
6. Run the full suite (`pytest tests/ -q`, check exit code), `ruff check .`,
   `check .` on this repo, and `check` on a freshly initialised+filled repo; save to
   `.qo/build.txt`.
7. Self-review `git diff` sceptically; write `.qo/review.json`; fix blockers (max two
   review rounds).
8. `.qo/report.md`, then stop.
