# JumpStarter documentation index

Last reconciled: **2026-09-03** (second pass)

Start here when a supporting detail is not in the root control set. This index classifies
**every** maintained Markdown file, so a historical plan can never be mistaken for
current status.

Rule: a Markdown file that is not listed here does not exist as far as an agent is
concerned. Adding, renaming, removing or reclassifying a file updates this table in the
same commit.

Files under `templates/` are **payload**, not documentation about this repo: they are
listed once at the bottom, not classified individually.

## Root control documents

| File | Purpose |
|---|---|
| [`README.md`](../README.md) | What JumpStarter is, the two workflows, the "apply JumpStarter here" instruction, the sixteen lessons in plain words |
| [`PRINCIPLES.md`](../PRINCIPLES.md) | The sixteen lessons with the incident behind each. The source of everything in `templates/` |
| [`CHANGELOG.md`](../CHANGELOG.md) | Authoritative implemented inventory and revision history |
| [`plan.md`](../plan.md) | Authoritative remaining work, invariants, gates and order |
| [`CURRENT_CHECKPOINT.md`](../CURRENT_CHECKPOINT.md) | Active item, branch, working state and verification stamp |
| [`WISHLIST.md`](../WISHLIST.md) | Candidate ideas; never an implementation queue |
| [`CLAUDE.md`](../CLAUDE.md) / [`AGENTS.md`](../AGENTS.md) | Agent operating context; kept as byte-identical copies |

If a supporting document claims a different implementation status, the root
`CHANGELOG.md` / `plan.md` pair wins.

## Active runbooks

Describe actions someone may perform **now**.

| File | Use |
|---|---|
| [`../playbooks/new-project.md`](../playbooks/new-project.md) | Bootstrap a new project: questionnaire, `init`, placeholders, commands, first checkpoint |
| [`../playbooks/retrofit.md`](../playbooks/retrofit.md) | Retrofit an existing repo: audit, report, add what is missing without rewriting history |
| [`../playbooks/build-review-loop.md`](../playbooks/build-review-loop.md) | The recon → packet → **tests-first** → build → review → fix → integrate loop, with the exact prompts |
| [`../playbooks/review-by-reproduction.md`](../playbooks/review-by-reproduction.md) | The reviewer checklist and the eight traps |
| [`../playbooks/packet-writing.md`](../playbooks/packet-writing.md) | How to write a packet from verified premises |
| [`AGENT_TEAM.md`](AGENT_TEAM.md) | How a session in *this* repo plans, builds, reviews and integrates |
| [`CODEX_NOTES.md`](CODEX_NOTES.md) | What a Codex session reads here, what it cannot do, how packets reach it |
| [`prompts/VERIFY_AND_EXERCISE_THE_TEAM_PROMPT.md`](prompts/VERIFY_AND_EXERCISE_THE_TEAM_PROMPT.md) | Paste-ready brief for a lead session: adversarially verify the 2026-09-03 second pass by reproduction, then run the four-agent loop on one real packet so the owner can see whether the subagent system works. **Not yet run** |
| [`prompts/REFRESH_FROM_SOURCE_PROMPT.md`](prompts/REFRESH_FROM_SOURCE_PROMPT.md) | Paste-ready brief for a session with access to the source project: re-harvest from it and reconcile the templates. **Executed once, 2026-09-03** — the four sources it names were read, and gates 1 and 3 and the OPEN questionnaire answers closed with it. Reusable as-is for the next refresh; the gate list inside it is spent |

## Active references

Retain detailed contracts. They do **not** own roadmap order or status.

| File | Role |
|---|---|
| [`INTERNALS.md`](INTERNALS.md) | The incident behind every `CLAUDE.md` rule, verbatim. Read the matching entry before changing what a rule governs |

## Decision records

| File | Decision |
|---|---|
| [`decisions/0000-template.md`](decisions/0000-template.md) | The template for a new record. Keeps its placeholders on purpose |
| [`decisions/0001-owner-goals-and-priorities.md`](decisions/0001-owner-goals-and-priorities.md) | `SUPERSEDED` by 0002. Kept as evidence of what was *assumed* before anyone asked — two of the assumptions were wrong |
| [`decisions/0002-owner-goals-asked-properly.md`](decisions/0002-owner-goals-asked-properly.md) | **The owner's goals in their own words, asked one question at a time — the tie-breaker for every prioritisation call** |

## Agent definitions

Not prose: front-mattered role briefs the harness loads. Listed so the rule above holds
— every Markdown file is classified.

| File | Role |
|---|---|
| [`../.claude/agents/tester.md`](../.claude/agents/tester.md) | Writes the packet's tests, proves each fails, commits them red. **Never writes the fix** |
| [`../.claude/agents/builder.md`](../.claude/agents/builder.md) | Builds one packet on its own branch, with fail-before-fix tests |
| [`../.claude/agents/reviewer.md`](../.claude/agents/reviewer.md) | Reviews one branch by reproduction. GO / NO-GO. Never edits |
| [`../.claude/agents/recon.md`](../.claude/agents/recon.md) | Read-only reconnaissance with `file:line` evidence |

These are generated from `templates/.claude/agents/` — JumpStarter runs its own control
set, so a template change that does not reach them is stale dogfood.

## Historical evidence

**Evidence, not authority.** Nothing yet — this repo is three days old at most. When
`CURRENT_CHECKPOINT.md` or `CHANGELOG.md` is archived, the archive is listed here.

## Payload, not documentation

`templates/` holds the files JumpStarter installs into other projects. They are
classified by `templates/docs/README.md` **in the project they land in**, not here. Do
not read them as statements about JumpStarter itself: `templates/CLAUDE.md` describes the
project being started, not this one.
