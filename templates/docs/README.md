# {{PROJECT}} documentation index

Last reconciled: **{{DATE}}**

Start here when a supporting detail is not in the root control set. This index
classifies **every** maintained Markdown file, so a historical plan can never be
mistaken for current status.

Rule: a Markdown file that is not listed here does not exist as far as an agent is
concerned. Adding, renaming, removing or reclassifying a file updates this table in the
same commit.

## Root control documents

| File | Purpose |
|---|---|
| [`README.md`](../README.md) | Setup, launch and orientation for a human |
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
| [`AGENT_TEAM.md`](AGENT_TEAM.md) | How a session plans, builds, reviews and integrates through the sub-agents |
| [`CODEX_NOTES.md`](CODEX_NOTES.md) | What a Codex session reads here, what it cannot do, how packets reach it |
| {{RUNBOOK}} | {{WHEN_TO_USE_IT}} |

## Active references

Retain detailed contracts or doctrine. They do **not** own roadmap order or status.

| File | Role |
|---|---|
| [`INTERNALS.md`](INTERNALS.md) | The incident, measurements and owner conversation behind every `CLAUDE.md` rule, verbatim |
| {{SPEC}} | {{WHAT_CONTRACT_IT_OWNS}} |

## Decision records

| File | Decision |
|---|---|
| [`decisions/0000-template.md`](decisions/0000-template.md) | The template for a new record |
| [`decisions/0001-owner-goals-and-priorities.md`](decisions/0001-owner-goals-and-priorities.md) | **{{OWNER}}'s goals in their own words — the tie-breaker for every prioritisation call** |

## Historical evidence

**Evidence, not authority.** Read one of these to answer one specific question. Never
load one as context.

| File | What it records |
|---|---|
| {{ARCHIVE}} | {{PERIOD_AND_WHAT_IT_HOLDS}} |
