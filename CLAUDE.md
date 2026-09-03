# JumpStarter — AI context index

JumpStarter is a reusable foundation for running software projects with AI agents: a set
of control-file templates, playbooks and a small CLI that bootstraps a new project or
retrofits an existing one. Its product boundary is in `plan.md` section 1; anything
outside it is out of scope, not "not yet built".

## How to talk to the owner

**Short.** One idea per sentence. Say what you did, what is broken, and what they need to
do — nothing else. If a message runs past about ten short lines, cut it. Detail belongs
in the docs and the commit message, not in the chat. This rule is for chat output only;
docs, code comments and commit messages keep their normal depth.

## Mandatory documentation workflow for every AI

**Read narrow, not everything.** An agent that cannot read its brief skims it and then
appends to it, which is what grows these files past the point of being followable. The
bounded read below is the instruction — widen it only when the narrow read leaves a real
question open.

Before proposing, planning, or changing anything:

1. `CURRENT_CHECKPOINT.md` — read the **"Active state at a glance"** block at the top.
   That block is the brief. Read the dated entries below it only for the item you are
   actually touching; if a dated entry contradicts the block, the dated entry wins.
2. `plan.md` — sections 5 (invariants), 6 (validation) and 7 (promotion), then the phase
   order in section 12. Read the body of your phase only.
3. `CHANGELOG.md` — **search** `Current implemented inventory` for the thing you are
   about to build, so you do not rebuild landed work. Search it; do not read it end to
   end.
4. `docs/README.md` — open only the documents relevant to the selected item.
5. Inspect the source, the tests and git history to verify the documentation still
   matches reality. **When the docs and the code disagree, the code is the fact and the
   doc is the defect** — fix the doc, and say so.

`WISHLIST.md` contains ideas, not authorized work. Never implement directly from it. An
item enters the build sequence only when the owner explicitly moves it into `plan.md`.

Before editing, state the exact plan/checkpoint item, what already exists, what remains,
the governing documents, expected files, tests, and whether the ask-first rule applies.

After every repository change, reconcile the documentation before handoff:

- update `CURRENT_CHECKPOINT.md` with the active item, working state and verification
  result (or explicitly state why the baseline is unchanged);
- update `CHANGELOG.md` when behaviour, contracts or an implementation status changed;
- advance or narrow the corresponding `plan.md` work, retaining any gate still owed;
- update `WISHLIST.md` only for owner-directed additions, removals or promotions;
- update `docs/README.md` whenever a Markdown file is added, removed or reclassified;
- add a `docs/INTERNALS.md` entry for any new rule, with the incident behind it;
- **refresh the "Active state at a glance" block** — a stale block is worse than none;
- **keep the active files small.** When `CURRENT_CHECKPOINT.md` passes ~1,500 lines,
  archive the entries older than the oldest open gate under `docs/` and leave a pointer.
  Same rule for `CHANGELOG.md`'s recent-changes section.

Do not create another roadmap, progress ledger, handoff or status file. The root control
set is `CLAUDE.md`/`AGENTS.md`, `CHANGELOG.md`, `plan.md`, `CURRENT_CHECKPOINT.md`,
`WISHLIST.md` and `docs/README.md`.

## Core rules / data flow

Each rule below is binding as written. The incident behind every one is in
[`docs/INTERNALS.md`](docs/INTERNALS.md) — **read the matching entry there before
changing the behaviour a rule governs.**

**Shape**
- Entry point: `tools/jumpstart.py`, four subcommands — `init`, `retrofit`,
  `sync-agents`, `check`. Standard library only, Python 3.9+.
- `templates/` is the payload; `tools/` copies and audits it; `playbooks/` tells a human
  or an agent what to do with the result. `PRINCIPLES.md` holds the evidence.
- Exit codes are the interface: 0 success or no gaps, 1 gaps or failure, 2 usage error.
  `retrofit` and `check` are meant to run in CI.

**Rules**
- **`retrofit` writes nothing, ever.** It audits and prints. A retrofit that starts by
  editing is a retrofit that gets reverted. *(INTERNALS: "retrofit is report-only")*
- **`init` never overwrites without `--force`.** A repo's existing `CLAUDE.md` is the
  project's own rules, not a stale copy of ours.
  *(INTERNALS: "init does not overwrite")*
- **Unfilled `{{...}}` placeholders are left in place, and `check` reports them.** Filling a
  placeholder with a plausible default ships a control file that lies.
  *(INTERNALS: "unfilled placeholders are visible")*
- **`AGENTS.md` is generated from `CLAUDE.md` and never hand-edited.** One source, one
  sync, sha256-verified. *(INTERNALS: "one source for two tools")*
- **The size checks measure a section, not a file, where the rule is about a section.**
  `CHANGELOG.md`'s bound is on "Recent changes"; an archive in the same file must not
  trip it. *(INTERNALS: "bound the section, not the file")*
- **A template that exists to be copied keeps its placeholders.**
  `docs/decisions/0000-template.md` and `.claude/packets/PACKET_TEMPLATE.md` are exempt
  from the placeholder check. *(INTERNALS: "templates by nature")*
- **A placeholder name is an identifier** (`[A-Za-z0-9_]+`). Prose about placeholders
  writes `{{...}}`, which is not a match — a check that fires on correct documentation
  is a check that gets ignored. *(INTERNALS: "A placeholder name is an identifier")*
- **Templates stay short enough to read in one sitting.** The whole point is bounded
  reads; a template nobody finishes is a template that gets skimmed and appended to.

## Hard invariants (plan.md sec 5 — never violate)
- No third-party dependency in `tools/`. It must run on a bare Python 3.9+.
- `retrofit` never writes to the audited repo.
- `init` never overwrites an existing file without `--force`.
- No trading, domain or project-specific content in `templates/` — the shape and the
  rules generalise; the specifics belong to the project being started.
- Every rule in `CLAUDE.md` has an entry in `docs/INTERNALS.md`.
- `sha256(CLAUDE.md) == sha256(AGENTS.md)`, here and in every project this touches.

## Tech stack + key deps
- Python 3.9+, standard library only. `pytest` to run the tests; `ruff` to lint.
- No packaging, no install step: `python tools/jumpstart.py <command>` from a checkout.

## Commands
- Test (before every commit): `python -m pytest tests/ -q` — must be fully green.
  **Check the process exit code, not a piped tail's.**
- Lint (before every commit): `ruff check .` — must be clean. **Fix the code, not the
  config**; a suppression needs its reason beside it.
- Self-check (before every commit): `python tools/jumpstart.py check .` — JumpStarter
  runs its own control set; a red self-check means the tool does not believe its own
  rules.
- Run: `python tools/jumpstart.py {init,retrofit,sync-agents,check} <path>`.

## Working agreement for agents
- **The agent team.** A session builds and reviews through the sub-agents in
  `.claude/agents/`; the contract is in [`docs/AGENT_TEAM.md`](docs/AGENT_TEAM.md).
- `main` is the trunk; branch per packet as `claude/<slug>`.
- Commit small and green; one commit per component. Push after each commit.
- **File-scoped ask-first rule.** Any edit to a file that changes what a *downstream
  project* is told to do is asked about BEFORE it is made: `templates/CLAUDE.md`,
  `templates/plan.md`, `templates/.claude/agents/*.md`, and the limit constants in
  `tools/jumpstart.py`. Those files land in other people's repos; a change there
  propagates silently to every project initialised afterwards.
- Any change to a template is mirrored in the playbook that describes it, and in the
  check that enforces it, in the same commit. A template, a playbook and a check that
  disagree leave the next agent no way to tell which is authoritative.

## Where to read more
- `PRINCIPLES.md` — the twelve lessons with the incident behind each. The source of
  everything in `templates/`.
- `CHANGELOG.md` — **`Current implemented inventory` is the contract: search it before
  building.**
- `docs/INTERNALS.md` — the incident behind every `Core rules` rule.
- `plan.md` — remaining work; the single source of truth for what is unfinished.
- `CURRENT_CHECKPOINT.md` — **read the `Active state at a glance` block.**
- `WISHLIST.md` — candidate ideas; never an implementation queue.
- `docs/README.md` — classifies every Markdown file.
- **`docs/decisions/0001-owner-goals-and-priorities.md` — the owner's goals in their own
  words: the tie-breaker for every prioritisation call.**
- `docs/CODEX_NOTES.md` — what a Codex session reads here and what it cannot do.

`AGENTS.md` is a generated copy of this file (symlinks do not survive every checkout) —
**edit CLAUDE.md, then re-copy**: `python tools/jumpstart.py sync-agents .`
