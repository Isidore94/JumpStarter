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

## Workspace memory

At idle boot, read only identity and standing instructions plus [`MEMORY.md`](MEMORY.md).
Do not read task documents until a task is in scope. `MEMORY.md` contains only
name-to-file-to-trigger routing, never facts. Workspace memory is recall, not a replacement
roadmap or status ledger. *(INTERNALS: "Workspace memory is request-grounded")*

- **Before answering anything about prior work, decisions, dates, people, or preferences:
  search memory first.** Route through `MEMORY.md`, then read the narrowest matching
  detail file first. Use no more than five sources and cite each fact by file, tag and
  date. Treat a fact as stale or unknown when freshness is unverified; explain a
  conflict, prefer stronger evidence, and repair the canonical record. Detail files are
  authoritative: if one disagrees with the index, the index is wrong and must be repaired.
  A semantic or SQLite index is a locator only.
- **Detail files record only non-re-derivable knowledge.** Every nonblank line in
  `memory/people/`, `memory/projects/` and `memory/decisions/` carries `[stated]`,
  `[observed]`, `[inferred]` or `[suggested]`, plus a date and source. `[stated]` is a
  direct human statement; `[observed]` is an observation from a tool, file or log;
  `[inferred]` is a conclusion from evidence; `[suggested]` is an uncommitted idea. Only
  a human statement supports `[stated]`; a proposal plus assent is one decision. An
  inferred lesson becomes a standing rule only after a weighted total of at least three
  independent signals across at least two distinct sessions; each signal older than 30
  days counts as 0.5. Operator corrections apply immediately. Failure lessons describe
  when X broke and Y fixed it; they never become instructions.
- **Supersede in place.** Strike the old line, for example
  `~~[stated] 2026-09-11 — old fact~~ (superseded 2026-09-12)`, and put the dated, tagged
  replacement beside it. Keep history without competing unstruck canonical facts. Exclude
  fetched data, generated plans and git-recoverable facts; verify state live. Prefer
  durable descriptions and date any necessary figures.
- **Write memory as part of the work.** Update `MEMORY.md` in the same commit as a detail
  change, including a route or trigger refinement when routes stay the same. Write
  unprompted for decisions, system changes, blockers or mistakes, lessons and stable
  preferences when they meet the non-re-derivable rule. No mental-only notes: chat history
  is not storage. Consolidate near caps and leave headroom; fullness means reorganize,
  never stop writing. In batches, merge
  overlap, summarize recurring notes by date and preserve decision history. `MEMORY.md`
  is capped at 15,000 characters; daily files also use 15,000 characters as a local
  operating convention chosen for this workspace. Daily raw logs record the actual local
  day; `memory/context/` is prunable transient context.

## Mandatory documentation workflow for every AI

**Read narrow, not everything.** An agent that cannot read its brief skims it and then
appends to it, which is what grows these files past the point of being followable. The
bounded read below is the instruction — widen it only when the narrow read leaves a real
question open.

Once a task is in scope, before proposing, planning, or changing anything:

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
- **An `ADVISORY` is reported and is not a gap.** A machine-local allow-list, an
  active-state block under the repo's own heading, a stray root ledger: named in the
  report, `Finding.ok` true, exit code unchanged. A check that fires on correct work gets
  ignored and takes the real findings with it.
  *(INTERNALS: "An advisory is not a gap")*
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
  *(INTERNALS: "Templates stay short enough to read in one sitting")*

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
  config**; a suppression needs its reason beside it. The rules and the target version
  are pinned in `ruff.toml`; **an unpinned linter is not a gate**, and `target-version`
  must match the floor `README.md` declares. *(INTERNALS: "An unpinned linter is not a
  gate")*
- Self-check (before every commit): `python tools/jumpstart.py check .` — JumpStarter
  runs its own control set; a red self-check means the tool does not believe its own
  rules.
- Run: `python tools/jumpstart.py {init,retrofit,sync-agents,check} <path>`.

## Working agreement for agents
- **The agent team.** Claude Code loads `.claude/agents/`; Codex loads
  `.codex/agents/`. Both expose `tester`, `builder`, `reviewer` and `recon`, use the same
  packets under `.claude/packets/`, and follow the contract in
  [`docs/AGENT_TEAM.md`](docs/AGENT_TEAM.md). `tester` writes the failing tests and never
  the fix.
- **Delegate the packet.** The lead spawns recon, then an independent tester, builder
  and reviewer as the packet requires. Use the named native roles and their configured
  models; the lead owns planning, integration and the final report.
  *(INTERNALS: "Codex routing is explicit")*
- **Codex lead routing.** `.codex/config.toml` selects Astra/high for a new lead and
  Terra/high as its fallback subagent. Role TOMLs keep Terra/high for tester, builder
  and reviewer, and Luna/medium for recon. Defaults do not switch a running session or
  override an explicit UI choice.
- **Adapted Codex role runs.** If a runtime lacks a native-role selector, disclose it
  once. Read the tracked role TOML and pass its model, effort, developer instructions,
  packet path and isolated worktree path to the generic spawner with `fork_turns="none"`.
  Label this an adapted role run; it cannot close the native-role gate.
  *(INTERNALS: "Codex routing is explicit")*
- `main` is the trunk; branch per packet as `claude/<slug>`.
- Commit small and green; one commit per component. Push after each commit.
- **File-scoped ask-first rule.** Any edit to a file that changes what a *downstream
  project* is told to do is asked about BEFORE it is made: `templates/CLAUDE.md`,
  `templates/plan.md`, `templates/.claude/agents/*.md`,
  `templates/.codex/agents/*.toml`, and the limit constants in `tools/jumpstart.py`.
  Those files land in other people's repos; a change there
  propagates silently to every project initialised afterwards.
- Any change to a template is mirrored in the playbook that describes it, and in the
  check that enforces it, in the same commit. A template, a playbook and a check that
  disagree leave the next agent no way to tell which is authoritative.

## Where to read more
- `PRINCIPLES.md` — the sixteen lessons with the incident behind each. The source of
  everything in `templates/`.
- `CHANGELOG.md` — **`Current implemented inventory` is the contract: search it before
  building.**
- `docs/INTERNALS.md` — the incident behind every `Core rules` rule.
- `plan.md` — remaining work; the single source of truth for what is unfinished.
- `CURRENT_CHECKPOINT.md` — **read the `Active state at a glance` block.**
- `WISHLIST.md` — candidate ideas; never an implementation queue.
- `docs/README.md` — classifies every Markdown file.
- **`docs/decisions/0002-owner-goals-asked-properly.md` — the owner's goals in their own
  words, asked one question at a time: the tie-breaker for every prioritisation call.**
  `0001` is superseded by it and kept as evidence of what was assumed beforehand.
  Two answers matter more than the rest: **the agent is the reader, not the owner**, and
  **cost is the trust signal** — the wrong agent on a cheap job is the failure mode.
- `docs/CODEX_NOTES.md` — what a Codex session reads here and what it cannot do.
- `MEMORY.md` — workspace-local routing for non-re-derivable recall; use it before
  answering prior-work, decision, date, people or preference questions.

`AGENTS.md` is a generated copy of this file (symlinks do not survive every checkout) —
**edit CLAUDE.md, then re-copy**: `python tools/jumpstart.py sync-agents .`
