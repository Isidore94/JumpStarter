# {{PROJECT}} — AI context index

{{PROJECT}} is {{ONE_LINE_DESCRIPTION}}. Its product boundary is in `plan.md` section 1;
anything outside it is out of scope, not "not yet built".

## How to talk to {{OWNER}}

**Short.** One idea per sentence. Say what you did, what is broken, and what they need
to do — nothing else. If a message runs past about ten short lines, cut it. Detail
belongs in the docs and the commit message, not in the chat. This rule is for chat
output only; docs, code comments and commit messages keep their normal depth.

## Mandatory documentation workflow for every AI

**Read narrow, not everything.** An agent that cannot read its brief skims it and then
appends to it, which is what grows these files past the point of being followable. The
bounded read below is the instruction — widen it only when the narrow read leaves a
real question open.

Before proposing, planning, or changing anything:

1. `CURRENT_CHECKPOINT.md` — read the **"Active state at a glance"** block at the top:
   branch, active items, last verified baseline, open gates, next action. That block is
   the brief. Read the dated entries below it only for the item you are actually
   touching; if a dated entry contradicts the block, the dated entry wins.
2. `plan.md` — sections 5 (invariants), 6 (validation) and 7 (promotion), then the
   phase order in section 12. Read the body of your phase only.
3. `CHANGELOG.md` — **search** `Current implemented inventory` for the feature you are
   about to touch, so you do not rebuild landed work. Search it; do not read it end to
   end.
4. `docs/README.md` — open only the active specification, runbook and decision records
   relevant to the selected item. Historical documents are evidence, not authority.
5. Inspect the source, tests, git status/history and runtime artifacts needed to verify
   that the documentation still matches reality. **When the docs and the code disagree,
   the code is the fact and the doc is the defect** — fix the doc, and say so. **This
   file is one of those docs.** A line in `CLAUDE.md` that the code contradicts is not
   authority; when you cannot fix it in the same change, leave a dated note saying which
   line is wrong and what the code does instead, and say so to {{OWNER}}. A stale rule
   here is read by every session and becomes the premise of the next proposal.
   *(INTERNALS: "The control file itself goes stale")*

Archived history is deliberately outside this read and must never be pulled into it
wholesale. It is evidence for one specific question, not context to load.

`WISHLIST.md` contains ideas, not authorized work. Never implement directly from it. An
item enters the build sequence only when {{OWNER}} explicitly moves it into `plan.md`.

Before editing, state the exact plan/checkpoint item, what already exists, what remains,
the governing documents, expected files, tests, and whether the ask-first rule applies.
Do not skip to a later phase because it is easier or more interesting.

After every repository change, reconcile the documentation before handoff:

- always update `CURRENT_CHECKPOINT.md` with the active item, working state and
  verification result (or explicitly state why the baseline is unchanged);
- update `CHANGELOG.md` when behavior, contracts, architecture, operations or an
  implementation status changed;
- remove, narrow or advance the corresponding `plan.md` work, retaining any gate
  still owed;
- update the governing spec or decision record when its contract or rationale changed;
- update `WISHLIST.md` only for owner-directed additions, removals or promotions;
- update `docs/README.md` whenever a Markdown file is added, removed or reclassified;
- add a `docs/INTERNALS.md` entry for any new rule, with the incident behind it;
- keep `CLAUDE.md` and `AGENTS.md` identical whenever operating instructions change;
- **refresh the "Active state at a glance" block** — a stale block is worse than none,
  because it is the one thing the next agent trusts;
- **keep the active files small.** When `CURRENT_CHECKPOINT.md` passes ~1,500 lines,
  move entries older than the oldest open gate into a dated archive under `docs/` and
  leave a pointer. Same rule for `CHANGELOG.md`'s recent-changes section. Archiving is
  maintenance, not a new document.

Do not create another roadmap, progress ledger, handoff or status file. The root control
set is `CLAUDE.md`/`AGENTS.md`, `CHANGELOG.md`, `plan.md`, `CURRENT_CHECKPOINT.md`,
`WISHLIST.md` and `docs/README.md`.

## Core rules / data flow

Each rule below is binding as written. The incident, measurements and owner
conversation behind every one are preserved verbatim in
[`docs/INTERNALS.md`](docs/INTERNALS.md) — **read the matching entry there before
changing the behaviour a rule governs.**

Format: one bolded rule, then the shortest statement that makes it actionable, then the
pointer to its evidence entry. A rule with no evidence entry is a draft.

**Shape**
- Entry point: `{{ENTRYPOINT}}`.
- <!-- Add rules as they are learned. Example shape:
- **A forming record is a preview, never a state transition.** Only completed records
  move state; a partial one is labelled. *(INTERNALS: "Completed records only")* -->

**{{AREA_2}}**
- <!-- one rule per line, same shape -->

## Hard invariants (plan.md sec 5 — never violate)
- <!-- The short list that no packet may cross. Keep it to things that would be a
     defect in production, not preferences. Example shapes: -->
- Uncertainty never deletes: missing data is uncertainty, never confirmation.
- One component owns each timer, thread, job and mutable shared output; a failed
  publish never destroys the last verified artifact.
- No behaviour change to {{CRITICAL_AREA}} without golden fixtures first.
- Every statistic carries its sample size and is not shown as a verdict below its floor.

## Tech stack + key deps
- {{STACK}}

## Commands
- Test (before every commit): `{{TEST_CMD}}` — must be fully green; the current
  baseline lives in `CURRENT_CHECKPOINT.md`. **Check the process exit code, not a
  piped tail's.**
- **When the suite is NOT a baseline:** {{WHEN_THE_SUITE_IS_NOT_A_BASELINE}}. Probe that
  condition before quoting a number; a run made under it is not the baseline, whatever
  it printed. *(INTERNALS: "A suite run under a known condition is not a baseline")*
- Lint (before every commit): `{{LINT_CMD}}` — must be clean. **Fix the code, not the
  config**; a suppression needs its reason beside it. **Pin the linter's version and
  configuration in the repo**, or "clean" means whatever is installed today.
- Self-check (before every commit): `{{SELFCHECK_CMD}}` — this project's own control set
  checked by its own rules. A red self-check means the project does not believe its rules.
- Run: `{{RUN_CMD}}`.
- {{EXTRA_COMMANDS}}

## Working agreement for agents
- **The agent team.** A session builds and reviews through the sub-agents in
  `.claude/agents/` (`tester`, `builder`, `reviewer`, `recon`); the contract, the loop
  and the delegation policy are in [`docs/AGENT_TEAM.md`](docs/AGENT_TEAM.md). Read it
  before spawning one. They work in their own worktrees under `.claude/worktrees/` and
  never touch the main checkout; the lead session merges.
- Follow the mandatory documentation workflow above. `plan.md` owns build order;
  `CURRENT_CHECKPOINT.md` owns the active item. Do not re-implement anything in
  `CHANGELOG.md` or implement anything directly from `WISHLIST.md`.
- `{{MAIN_BRANCH}}` is the trunk; branch per packet as `{{BRANCH_PREFIX}}<slug>`, merge
  back after the packet's gate passes.
- Commit small and green; push after each commit. If a task will exceed usage limits,
  commit and push so another agent can take over from a green state.
- **File-scoped ask-first rule.** Any edit to a file housing {{ASK_FIRST_AREA}} is asked
  about BEFORE it is made — even for a change that only adds. Ambiguity is the trigger
  to ask, not a license to judge. The files: {{ASK_FIRST_FILES}}.
- Never switch the main checkout's branch while {{PROJECT}} is running from it, and
  never restart it without {{OWNER}}'s word.
- **Assume another session is in this repository.** Verify the branch immediately before
  staging and immediately before pushing; stage explicitly by path, never `git add -A`;
  **never `git stash`** — it takes the other session's in-flight work with it; restore
  one file with `git checkout <base> -- <path>` instead. After committing, confirm your
  work landed. *(INTERNALS: "Another session is in this repository")*

## Where to read more
- `CHANGELOG.md` — **`Current implemented inventory` is the contract: search it before
  building.** `Recent changes` holds the last two build days; older entries are
  archived under `docs/`.
- `docs/INTERNALS.md` — the incident and measurements behind every `Core rules` rule,
  verbatim. Read the matching entry before changing what a rule governs.
- `plan.md` — remaining work and the single source of truth for what is unfinished.
- `CURRENT_CHECKPOINT.md` — **read the `Active state at a glance` block.**
- `WISHLIST.md` — candidate ideas; never an implementation queue.
- `docs/README.md` — classifies every Markdown file as active runbook, reference or
  historical evidence.
- `docs/decisions/` — decision records; read before changing a library, storage or
  architecture choice.
- **`docs/decisions/0001-owner-goals-and-priorities.md` — {{OWNER}}'s goals and
  priorities in their own words: the tie-breaker for every prioritisation call. Read it
  before proposing or ordering work.**
- `docs/CODEX_NOTES.md` — what a Codex session reads here and what it cannot do.

`AGENTS.md` is a generated copy of this file (symlinks do not survive every checkout) —
**edit CLAUDE.md, then re-copy**: `python tools/jumpstart.py sync-agents .`
