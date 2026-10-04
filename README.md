# JumpStarter

Sets up any repo, brand new or years old, for AI coding with **Claude Code**,
**Codex/ChatGPT** or a **local model**. It gives an agent a short rules file, a plan
with a "where are we" block, and a changelog, so that every session starts from facts
and spends little usage getting there.

## Use it

Tell an AI agent working in your repo:

> Set this repo up with JumpStarter: https://github.com/Isidore94/JumpStarter (follow SETUP.md)

The agent follows [`SETUP.md`](SETUP.md). It looks first, asks you a few questions one at
a time, writes the files, and checks them.

Or run the CLI yourself (Python 3.9+, no dependencies):

```
git clone https://github.com/Isidore94/JumpStarter.git
python JumpStarter/tools/jumpstart.py retrofit /path/to/repo                 # audit only; writes nothing
python JumpStarter/tools/jumpstart.py init /path/to/repo --name MyApp        # add what is missing
python JumpStarter/tools/jumpstart.py check /path/to/repo                    # gate: exit 1 on any gap
python JumpStarter/tools/jumpstart.py sync-agents /path/to/repo              # make CLAUDE.md import AGENTS.md
```

## What lands in your repo

**`lite`** (default, about 5 KB, works with every tool):

| File | Purpose |
|---|---|
| `AGENTS.md` | the rules: plain-language replies, read small, test before "done", save usage |
| `CLAUDE.md` | one line, `@AGENTS.md`, so Claude Code reads the same rules |
| `plan.md` | goal, `## Now` (the brief every task reads first), next steps, ideas |
| `CHANGELOG.md` | what exists today (searched before building) and a short log |
| `docs/decisions/0001-goals.md` | your goals in your own words: the tie-breaker |
| `docs/LESSONS.md` | what broke and the rule it produced |

**`team`** (`--profile team`) adds helper agents for Claude Code and Codex: `recon` on a
cheap model for lookups, plus `tester`, `builder` and `reviewer`. Each role has one
instruction file in `docs/agents/`, shared by both tools, with thin wrappers in
`.claude/agents/` and `.codex/agents/` that only pick the model. `docs/AGENT_TEAM.md`
says which agent does which job, so the expensive model only does the thinking.

Blanks the CLI was not told stay as `{{NAME}}`, and `check` lists them. A control file
never ships with a made-up value.

## What `check` enforces

`AGENTS.md` at most 200 lines; `CLAUDE.md` imports it; `## Now` at most 25 lines;
`plan.md` at most 400; the changelog's `## Log` at most 400; a goals record; every rule
that cites a lesson has one; no unfilled blanks; helper-agent files complete. Repos on
the older JumpStarter layout keep their file names; those are advisories, not failures.

## This repo

```
SETUP.md              the guide an agent follows to set up another repo
templates/lite/       the default files
templates/team/       the helper-agent add-on
tools/jumpstart.py    the CLI (standard library only)
tests/                pytest for the CLI and the templates
docs/PRINCIPLES.md    the sixteen lessons the templates come from
```

JumpStarter runs on its own rules: see `AGENTS.md`, `plan.md` and `CHANGELOG.md`.

## Requirements

Python 3.9 or newer, standard library only. The floor was measured on CPython 3.9.25 on
2026-09-03. `ruff.toml` pins `target-version = "py39"` to match. `pytest` and `ruff`
are needed only to develop JumpStarter itself.
