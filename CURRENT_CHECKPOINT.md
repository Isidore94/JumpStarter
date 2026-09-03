# Current checkpoint

This file is the frequently refreshed active-work, branch and verification stamp.

- Implemented inventory and revision history: [`CHANGELOG.md`](CHANGELOG.md)
- Remaining work and gates: [`plan.md`](plan.md)
- Supporting-document roles: [`docs/README.md`](docs/README.md)
- Older entries: nothing archived yet — see the archive rule at the bottom.

---

## Active state at a glance

**Read this block first. It is the answer to "where are we?" — the dated entries below
are the working record behind it. Refresh this block on every handoff; if it disagrees
with the newest dated entry, the dated entry wins and this block is stale.**

| | |
|---|---|
| Working branch | **`claude/jumpstarter-repo-setup-dn3rof`** — the first build. Nothing has been merged to `main`; `main` does not exist yet |
| Also in flight | **NOTHING unmerged.** No other branch, no worktree |
| Active items | `plan.md` **Phase 0 item 1** — run `retrofit` against a real existing repository and record what the audit gets wrong. Not started |
| Last verified baseline | `python -m pytest tests/ -q` **38 passed, process exit 0, 0.3 s** (2026-09-03, on the first-build tree). `ruff check .` **All checks passed**, exit 0. `python tools/jumpstart.py check .` **9 checks, no gaps**, exit 0 |
| Artifact state | There is no build artifact. `tools/jumpstart.py` runs from source, standard library only, on the Python in `PATH`. Verified on **Python 3.11.15**; the declared floor is 3.9 and **that floor has not been tested** — see gate 3 |
| Restart owed | **No.** Nothing runs continuously from this checkout |

Rules for this block:

- Numbers, not adjectives. "Tests green" is a memory of state; "38 passed, exit 0" is
  state.
- Check the **process** exit code, not a piped tail's.
- If a number was not measured this handoff, say so and say when it was.

### Open gates, newest first

Each is owed before the work it belongs to can be called validated. Detail lives in the
dated entry named beside it.

| # | Gate | Owed by |
|---|---|---|
| 3 | **The declared Python floor is real** — `pytest` and all four subcommands run on a 3.9 interpreter. Everything so far was measured on 3.11.15; the floor in `README.md` and `plan.md` is a claim, not a measurement | 2026-09-03 first-build entry |
| 2 | **One new project bootstrapped end to end** — a human answers the questionnaire, fills every placeholder, and `check` is green on a repo that was empty this morning. Record which questions were hard to answer and which placeholders had no good answer | `plan.md` Phase 1 item 1 |
| 1 | **One real existing repository audited** — **PARTLY MET 2026-09-03**: audited a clone of one mature repo (22 checks, 3 gaps, 1 of them a false positive — see the entry below). Still owed: a repo that grew *without* a control set, which is the case the audit was written for, and a run against a working copy rather than a clone | `plan.md` Phase 0 item 1 |

A gate is closed by striking its row through and writing what was observed — never by
deleting the row.

---

### 2026-09-03 — First retrofit dry run, on a clone of the source project

**Report only. Nothing was changed in that repository, and nothing could be:** it was a
read-only clone, and `retrofit` writes nothing by invariant.

`python tools/jumpstart.py retrofit <clone>` → **22 checks, 3 gaps, exit 1.**

Seventeen checks passed, which is the expected result: this repo's templates were
distilled from that project, so the audit is partly checking its own homework. The three
gaps are the useful part.

**Two real gaps, both the size rule:**

- `CURRENT_CHECKPOINT.md` is **4,284 lines** against a limit of 1,500 — the file carries
  its own archive-at-1,500 rule and is nearly three times over it.
- `CHANGELOG.md`'s "Recent changes" section is **1,341 lines** against a limit of 800,
  in a file whose header says the section holds "the last two build days".

Both are the principle-1 failure in its natural habitat: the rule is written down, it is
correct, and nothing enforces it, so the file grows until the mandatory read stops being
followable. This is the strongest argument found so far for wiring `check` into CI
(`plan.md` Phase 2 item 1).

**One false positive:**

- `command allow-list: .claude/settings.json not found`. That file is **deliberately
  machine-local** in that project — its own `docs/AGENT_TEAM.md` says so, and its
  `.gitignore` tracks `.claude/agents/` while ignoring the rest. The file exists on the
  owner's machine and cannot exist in a clone.

  The audit cannot tell "absent" from "correctly untracked" by looking at a checkout. The
  fix is not to drop the check — a project with no allow-list at all is a real finding —
  but to read `.gitignore` and downgrade the result to an advisory when `.claude/*` is
  ignored. Not yet built; recorded here so gate 1's record is honest rather than tidy.

**What this run did NOT establish.** The audited repo already had a full control set, so
this exercised the *pass* path, not the path the audit was written for: a repo that grew
without one. Gate 1 stays open for that.

---

### 2026-09-03 — First build: templates, playbooks, CLI, tests, and its own control set

**Branch `claude/jumpstarter-repo-setup-dn3rof`.** No merge target yet.

Distilled the control-set shape and the twelve principles from a mature project built
almost entirely by AI agents, generalised: no domain content reached `templates/`. Built
the eighteen templates, the five playbooks, `tools/jumpstart.py` (four subcommands,
standard library only) and 38 tests. Then ran `init` on this repo and filled the result
by hand, which is how the last two defects below were found.

**What was NOT built.**

- **Nothing has been run against a real repository.** The suite exercises the CLI against
  fixtures the tests themselves construct. That is gate 1, and it is the difference
  between "the code parses what I gave it" and "the audit is right".
- **No CI.** `check` is not wired into anything; it is run by hand. `plan.md` Phase 2.
- **The Python 3.9 floor is unverified** (gate 3).
- **The questionnaire was not put to the owner one question at a time**, which is what
  `playbooks/new-project.md` requires. Four of the twelve answers in
  `docs/decisions/0001-owner-goals-and-priorities.md` are recorded as **OPEN** rather
  than guessed at. Re-asking properly is that record's reopen trigger.
- **`retrofit`'s twelve check families are heuristics over file names and headings.** A
  repo whose active-state block lives under a different heading will be reported as
  missing one. That is the expected class of false positive, and gate 1 exists to measure
  it rather than assume it.

**Two defects found by dogfooding, both fixed on this branch.**

1. `check` was red on a correctly set-up project, because
   `docs/decisions/0000-template.md` and `.claude/packets/PACKET_TEMPLATE.md` exist *to
   be copied and filled in later* — their placeholders are the product.
   `TEMPLATES_BY_NATURE` exempts them. *(INTERNALS: "Templates by nature")*
2. `check` reported an unfilled placeholder in a fully-filled file, because this repo's
   own `CLAUDE.md` writes a token-shaped example in prose while describing the rule.
   Placeholder names are now identifiers only, prose writes `{{...}}`, and two dotted
   template tokens were renamed. *(INTERNALS: "A placeholder name is an identifier")*

Both are the same lesson: a check that fires on correct work is a check that gets
ignored, and it takes the real findings with it.

**Proof.** `python -m pytest tests/ -q` → 38 passed, process exit 0, 0.3 s.
`ruff check .` → All checks passed, exit 0. `python tools/jumpstart.py check .` → 9
checks, no gaps, exit 0.

**Fail-before-fix.** Not applicable to most of this build — there was no prior code to
restore. The two defects above are the exceptions and both have a test that fails on the
un-fixed code: `test_check_is_green_on_a_filled_repo` fails without `TEMPLATES_BY_NATURE`,
and `test_a_placeholder_name_is_an_identifier` fails with `.` in the character class.

**Gates recorded.** 1, 2 and 3 above.

---

## Archive rule

When this file passes **~1,500 lines**, move the entries older than the oldest open gate
into `docs/CHECKPOINT_ARCHIVE_<YYYY-MM>.md` and leave a pointer at the top of this file.
The archive is evidence for one specific question; it is never loaded as context.
Archiving is maintenance, not a new document.

`python tools/jumpstart.py check .` enforces the limit.
