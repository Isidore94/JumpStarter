# Plan — `check` verifies INTERNALS citations

## What the task is

`check` must report every `*(INTERNALS: "<name>")*` citation in `CLAUDE.md` that has no
matching heading in the repo's `docs/INTERNALS.md`, and exit 1. When all citations resolve,
`check` passes as before. This closes the invariant "every rule in CLAUDE.md has an entry
in docs/INTERNALS.md" (`plan.md:92`), which `CURRENT_CHECKPOINT.md:156-158` names as
"enforced by nobody."

## Decisions on the unclear points

1. **Match rule.** A citation resolves if its name, after collapsing whitespace and
   lowercasing, equals the leading text of any `##`-or-deeper heading in
   `docs/INTERNALS.md`, also after collapsing whitespace and lowercasing. The heading's
   trailing ` (…)` suffix (date / origin) is stripped first, per the task's suggested
   default. This is what makes `unfilled placeholders are visible` match
   `## Unfilled placeholders are visible (2026-09-03, first build)`.
2. **Multi-line citations.** One citation in this repo's own CLAUDE.md
   (`CLAUDE.md:149-150`) wraps across two lines. Extraction therefore runs on the whole
   text and normalises whitespace, not line by line.
3. **HTML comments.** A citation inside `<!-- … -->` is skipped (the template has one,
   `templates/CLAUDE.md:88-90`). Comments are stripped before extraction.
4. **Missing `docs/INTERNALS.md`.** Not reported by this check — the structure audit
   (`retrofit`, `audit_structure:675`) owns "the file exists." The new check only fires
   when the file is present but an entry is absent. This matches the task's note.
5. **Status.** A missing entry is `MISSING` (`ok == False` → exit 1), the closest fit;
   one `Finding` names every missing entry (cap 6 shown, as `audit_placeholders` does).
6. **"Stays green" / "tests stay green" — the pre-existing redness.** This checkout's
   `check .` is already red for reasons outside the task: the harness added rules to
   `CLAUDE.md` but not `AGENTS.md` (→ DRIFT) and the `.claude/agents/*.md` files have
   unfilled placeholders (→ 4× UNFILLED), which makes
   `test_jumpstarter_passes_its_own_check` fail (48 passed, 1 failed at baseline). I must
   not touch `CLAUDE.md` or `.claude/`, so those gaps stay. **Decision:** the task's
   "stays green" reads as *my change adds no new gap to `check .` and no new test
   failure*. I verify that by diffing the gap/failure sets before and after.

## Files changed

1. **`tools/jumpstart.py`** (the only code file):
   - Module level, next to `PLACEHOLDER_RE` (`:130`): `INTERNALS_CITATION_RE`.
   - Helpers near `find_placeholders` (`:184`): `_norm`, `_strip_html_comments`,
     `find_internals_citations`, `internals_heading_texts`.
   - Audit near `audit_placeholders` (`:450`): `audit_internals_citations(repo)`.
   - `cmd_check` (`:936`): add `findings.extend(audit_internals_citations(repo))`.
   - No limit constants touched; `templates/` untouched; `retrofit` untouched (report-only
     invariant preserved).
2. **`tests/test_jumpstart.py`** (tests first):
   - `test_check_fails_on_a_missing_internals_entry` (integration; **fails before**).
   - `test_check_is_green_when_all_citations_resolve` (integration; passes before & after).
   - `test_find_internals_citations_handles_multi_line_and_comments` (unit).
   - `test_internals_heading_texts_strips_suffix_and_normalises` (unit).
   - `test_citation_check_does_not_fire_when_internals_file_is_absent` (unit; pins
     decision 4).
3. **`CHANGELOG.md`** — add the check to `Current implemented inventory` (CLI section) and
   a `Recent changes` entry.
4. **`CURRENT_CHECKPOINT.md`** — refresh the "Active state at a glance" block's measured
   baseline line to reflect the new check count and re-measured suite.

Not touched: `templates/`, `CLAUDE.md`, `AGENTS.md`, `docs/INTERNALS.md` (no new CLAUDE.md
rule → no new entry, no `sync-agents`), `plan.md`, `WISHLIST.md`, `docs/README.md`,
`.claude/`.

## Ordered steps

1. Write the failing tests in `tests/test_jumpstart.py`; run them, save the red output to
   `.qo/tests-red.txt`.
2. Implement in `tools/jumpstart.py`; run the whole suite + ruff; save to `.qo/build.txt`.
3. Re-run `check .` before/after to prove no new gap; verify the new check reports the
   missing entry and exits 1 on a constructed repo and 0 on a clean one.
4. Self-review the diff → `.qo/review.json`.
5. Update CHANGELOG.md + CURRENT_CHECKPOINT.md; write `.qo/report.md`.

## "Done" means

- `check` on a repo whose CLAUDE.md cites a missing INTERNALS entry exits 1 and names it;
  a repo whose citations all match exits 0. Both proven by tests; the missing-entry test
  is red on the un-fixed code.
- `check .` gains no new gap on this repo (the 5 pre-existing gaps remain, nothing more)
  and stays 0-gap on a filled `init` repo.
- `pytest tests/ -q` has no new failure (still exactly the 1 pre-existing
  `test_jumpstarter_passes_its_own_check`), `ruff check .` clean, exit codes 0/1/2 intact.
