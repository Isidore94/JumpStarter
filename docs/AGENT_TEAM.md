# The agent team: one lead, its builders, its reviewers

Document role: **active runbook.** How a session in *this* repo plans, builds, reviews
and integrates. The generic version that ships to other projects is
`templates/docs/AGENT_TEAM.md`; this one is filled in for JumpStarter.

The loop, the roles and the prompts are in
[`../playbooks/build-review-loop.md`](../playbooks/build-review-loop.md). This file
records what is specific here.

## The roles

| Agent | Where it runs | What it may do | What it must never do |
|---|---|---|---|
| **lead** (the session the owner talks to) | the main checkout | ask the owner, write packets, spawn the others, merge, run the suite, reconcile the ledgers | build a packet itself when a builder could |
| **builder** (`.claude/agents/builder.md`) | its own worktree, branch `claude/<slug>` | edit, test, commit, push its branch, reconcile docs | touch the main checkout, merge, edit an ask-first file without a recorded yes |
| **reviewer** (`.claude/agents/reviewer.md`) | its own worktree, on the branch under review | run tests, revert-and-rerun to prove fail-before-fix, run the CLI against fixture repos | write, edit, commit, push |
| **recon** (`.claude/agents/recon.md`) | the main checkout, read-only | map code with `file:line`, count things, find gaps | write anything, propose designs unasked |

## What is specific to JumpStarter

- **The gates are real repositories.** A green suite here proves the CLI parses what the
  tests give it. It proves nothing about a repo that grew on its own. Every phase-0 and
  phase-1 item in `plan.md` is gated on running against a real one and recording what the
  audit got wrong.
- **The ask-first files are the ones that land in other people's repos**:
  `templates/CLAUDE.md`, `templates/plan.md`, `templates/.claude/agents/*.md`, and the
  limit constants in `tools/jumpstart.py`. A change there propagates silently to every
  project initialised afterwards. Ask before changing one.
- **A template, its playbook and its check change together.** If they disagree, the next
  agent has no way to tell which is authoritative — and will pick the one that suits the
  change it wanted to make.
- **No live stores.** Nothing here reads or writes production data. The reviewer's
  "reproduce against copies of real data" step becomes: run the CLI against a copy of a
  real repository, in a temp directory.
- **Three gates before a commit**: `python -m pytest tests/ -q`, `ruff check .`, and
  `python tools/jumpstart.py check .`. The third is the dogfood check — a red self-check
  means the tool does not believe its own rules.

## Rules that exist because something broke

The general ones are in [`../PRINCIPLES.md`](../PRINCIPLES.md); the ones specific to this
code are in [`INTERNALS.md`](INTERNALS.md). Both are short. Read them before changing a
rule, not after.

## Setup on a machine

1. `.claude/agents/` is tracked; the rest of `.claude/` is machine-local, except
   `.claude/packets/` if this project chooses to track its packets.
2. `.claude/settings.json` allow-lists pytest, ruff, the CLI, `git worktree`, and commits
   and pushes to `claude/*`. It also **denies** the destructive git verbs outright.
3. No flag or restart is needed: a changed file in `.claude/agents/` is picked up by the
   running session.

## For Codex

Codex reads `AGENTS.md` (the generated copy of `CLAUDE.md`) and not `.claude/`. See
[`CODEX_NOTES.md`](CODEX_NOTES.md).
