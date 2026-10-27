# Report — `check` fails when CLAUDE.md cites a nonexistent INTERNALS entry

## What changed

**`tools/jumpstart.py`** (the only code change):
- `INTERNALS_CITATION_RE` — matches only the full quoted pointer form, so prose about
  citations is not a citation (same discipline as "a placeholder name is an identifier").
- `HTML_COMMENT_RE` + `_strip_html_comments` — commented-out citations are examples and
  are stripped before matching (the shipped template carries one citing an entry that
  never exists).
- `find_internals_citations` — cited names, first-seen, deduplicated, whitespace-folded
  (one of this repo's own citations wraps across two lines).
- `internals_headings` — leading text of each `##` heading, trailing `(date, reason)`
  suffix stripped; `###` sub-headings are not entries.
- `audit_internals_citations` — one `MISSING` finding per dangling citation, each
  naming the entry; one `OK` when all resolve; silent when `CLAUDE.md` is absent (the
  drift check's job) or when `docs/INTERNALS.md` is absent (the structure audit's job).
- Wired into `cmd_check` after the placeholder audit; module docstring and the `check`
  subparser help updated. `retrofit` untouched.

**Tests** (`tests/test_jumpstart.py`): six new tests, written and proven red before the
fix (`.qo/tests-red.txt`): a dangling citation fails `check` and is named; a
fully-resolving repo passes and prints exactly one OK citation finding; unit tests for
folding + comment skipping, case-insensitive suffix-stripped matching, the named gap,
and missing-file silence. No existing test was weakened, skipped or deleted.

**Repo docs** (the repo's own workflow): `CLAUDE.md` gains the rule
"An INTERNALS citation must resolve" (worded so its own text contains no pointer-shaped
string besides its genuine citation — verified: `check .` finds exactly 10 citations,
not 11); `docs/INTERNALS.md` gains `A citation must resolve (2026-10-26, ...)`;
`AGENTS.md` regenerated via `sync-agents` (sha256 identical); `CHANGELOG.md` inventory
and a dated entry; `CURRENT_CHECKPOINT.md` active-state block refreshed and a dated
entry recording the pre-existing red.

## Results (measured 2026-10-26, CPython 3.12.13)

| Command | Result |
|---|---|
| `pytest tests/ -q` | **54 passed, 1 failed, exit 1** — the failure is the pre-existing `test_jumpstarter_passes_its_own_check` (see below) |
| `ruff check .` | All checks passed, exit 0 |
| `check .` (this repo) | exit 1, 4 gaps of 10 checks — all four pre-existing; the new check prints `INTERNALS citations: all 10 citations resolve to docs/INTERNALS.md headings` |
| `check` on a freshly `init`-ed, filled repo | exit 0, no gaps, `all 3 citations resolve` (the commented-out 4th template citation is skipped) |

Fail-before-fix: `.qo/tests-red.txt` shows the six new tests red on the un-fixed code
(7 failed, 48 passed); `.qo/build.txt` holds the final suite, lint and both `check`
runs.

## Pre-existing red, unchanged by this work

The harness that prepared this worktree (a) prepended a 27-line orchestration block to
`CLAUDE.md` and (b) rewrote `.claude/agents/{tester,builder,reviewer,recon}.md` back to
template shape with live `{{...}}` tokens (evidence: `.qo/recon.md`, "Baseline").
Consequences:

- The block alone made `CLAUDE == AGENTS` drift; cleared with the sanctioned
  `sync-agents` (the task's own workflow names it) — the check report now shows
  `CLAUDE == AGENTS: byte-identical`.
- The four `UNFILLED` gaps in `.claude/agents/*.md` cannot be cleared without either
  editing under `.claude/` (forbidden by the task rules) or weakening the placeholder
  check (forbidden by "without weakening them"). They stay, and with them the one test
  that asserts `check .` is green on this worktree stays red. All other gaps and
  failures were 0 at baseline and remain 0.

## What was skipped, and why

- **`retrofit` adoption.** The task scopes the check to `check` only; retrofit's
  documented "25 checks" contract (three files) stays intact. `audit_internals_citations`
  is ready-made to add to `audit_structure` if the owner wants it in the full standard.
- **`templates/*`, the limit constants, `plan.md`, `WISHLIST.md`, `docs/README.md`.**
  Ask-first / no-change surfaces; none needed touching.
- **`.claude/agents/*.md`.** Forbidden to edit; the pre-existing UNFILLED gaps stay.
- **Commit/push.** Task rules forbid git history, stash, checkout and commit commands;
  the work is left in the working tree.

## Open doubts

1. If a `##` heading ever carried a non-suffix paren group
   (`## Rule (a) (date, reason)`), the match text keeps `(a)` — recorded as an advisory
   in `.qo/review.json`; no such heading exists today.
2. An unterminated `<!--` in `CLAUDE.md` is not stripped (non-greedy comment match),
   so a citation inside it would still count. Accepted: unterminated comments are
   already malformed Markdown.
3. The repo's own `check .` is red here solely for the harness's `.claude/` state; on
   a clean checkout of this work the suite and the self-check would be fully green
   (55/55, exit 0 expected — the one red test is green everywhere else, as the 54
   passing tests and the filled-repo runs show).
