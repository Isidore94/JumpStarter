# JumpStarter

JumpStarter sets up any repo, new or existing, for AI coding with Claude Code,
Codex/ChatGPT or a local model. It ships templates, one setup guide (`SETUP.md`) and a
small CLI (`tools/jumpstart.py`). What it never does is in `plan.md` `## Out of scope`.

These are the rules for every agent working here. `CLAUDE.md` only imports this file.

## Talking to the owner

- Plain words, short. A TL;DR first; detail only when asked.
- Say what you did, what is broken, and what they need to decide. About five lines.
- Detail goes in commits and docs, not chat.

## Start of every task: read small

1. `plan.md` `## Now`. It is the brief.
2. Search `CHANGELOG.md` `## What exists` for what you are about to build.
3. Open only the files the task needs. If docs and code disagree, the code is the fact;
   fix the doc and say so.
4. A question about prior work, decisions, dates, people or preferences: route through
   `MEMORY.md` first, then read the one matching detail file. Rules: `memory/README.md`.
   *(LESSONS: "Workspace memory is request-grounded")*

The owner's goals are the tie-breaker: `docs/decisions/0002-owner-goals-asked-properly.md`
and `0003-lite-default-and-one-source.md`. **The agent is the reader**, and **cost is the
trust signal**: the wrong (expensive) agent on a cheap job is the failure mode.

## While working

- Do only what was asked. Ideas go under `plan.md` `## Ideas`; never build from there.
- **Ask first** before editing anything that changes what a *downstream project* is
  told: `templates/**`, `SETUP.md`, and the limit constants in `tools/jumpstart.py`.
  Those land in other people's repos.
- A template change is mirrored in `SETUP.md`, the check that enforces it, and its
  tests, in the same commit.
- Branch per task as `claude/<slug>`; `main` is the trunk. Commit small and green; push
  after each commit.

## Core rules

- **`retrofit` writes nothing, ever.** It audits and prints.
  *(LESSONS: "retrofit is report-only")*
- **An `ADVISORY` is reported and is not a gap.** `Finding.ok` is true and the exit code
  does not move. A check that fires on correct work gets ignored.
  *(LESSONS: "An advisory is not a gap")*
- **`init` never overwrites without `--force`**, and prints what it skipped.
  *(LESSONS: "init does not overwrite")*
- **Unfilled `{{...}}` blanks stay in place and `check` reports them.** A plausible
  default ships a control file that lies. *(LESSONS: "Unfilled placeholders are visible")*
- **`AGENTS.md` is the one source of rules; `CLAUDE.md` is a one-line `@AGENTS.md`
  import.** *(LESSONS: "One source of rules")*
- **Older file names are accepted.** They are read as aliases and reported as
  advisories; the size limits apply to every layout.
  *(LESSONS: "Older file names are accepted")*
- **Size checks measure a section where the rule is about a section.**
  *(LESSONS: "Bound the section, not the file")*
- **A template that exists to be copied keeps its blanks** (`TEMPLATES_BY_NATURE`).
  *(LESSONS: "Templates by nature")*
- **A blank's name is an identifier** (`[A-Za-z0-9_]+`). Prose writes `{{...}}`, which
  is not a match. *(LESSONS: "A placeholder name is an identifier")*
- **Templates stay short and plain.** Lite is under 8 KB; tests enforce it.
  *(LESSONS: "Templates stay short enough to read in one sitting")*
- **Helper roles have one instruction file each** (`docs/agents/<role>.md`); the Claude
  and Codex files are thin wrappers that set the model.
  *(LESSONS: "Native role definitions are adapted, never mechanically converted")*

## Hard invariants (never cross)

- No third-party dependency in `tools/`. Bare Python 3.9+.
- `retrofit` never writes to the audited repo. `init` never overwrites without `--force`.
- No project-specific content in `templates/`.
- Every rule here that cites a lesson has a `## ` entry in `docs/LESSONS.md`.
- `CLAUDE.md` imports `AGENTS.md`.

## Before you say "done"

- Tests: `python -m pytest tests/ -q`, fully green. Check the process exit code.
- Lint: `ruff check .`, clean. Fix the code, not the config. `ruff.toml` pins the rules
  and `target-version`, which must match the Python floor in `README.md`.
  *(LESSONS: "An unpinned linter is not a gate")*
- Self-check: `python tools/jumpstart.py check .`, no gaps.
- Update `plan.md` `## Now`, `CHANGELOG.md`, a decision record for a real owner choice,
  and `docs/LESSONS.md` for any new rule.

## Save usage

- Helper agents: follow `docs/AGENT_TEAM.md`. Cheap model for lookups; do small edits
  yourself; hand helpers a packet path under `docs/packets/`, never pasted text.
  *(LESSONS: "Codex routing is explicit")*
- Codex here: `.codex/config.toml` picks the lead; role TOMLs pick strong/high for
  tester, builder, reviewer and cheap/medium for recon. Defaults never switch a running
  session or override an explicit UI choice.

## Files

| File | What it is for |
|---|---|
| `plan.md` | goal, `## Now`, next, ideas, out of scope |
| `CHANGELOG.md` | what exists, and the log |
| `SETUP.md` | what an agent follows to set up another repo |
| `templates/lite/`, `templates/team/` | the payload |
| `tools/jumpstart.py`, `tests/` | the CLI and its tests |
| `docs/decisions/` | the owner's goals and choices |
| `docs/LESSONS.md` | what broke and the rule it produced |
| `docs/PRINCIPLES.md` | the sixteen lessons the templates come from |
| `docs/archive/` | history; evidence for one question, never a read |
| `MEMORY.md`, `memory/` | workspace recall routing |

Do not add other status, roadmap, todo or handoff files.
