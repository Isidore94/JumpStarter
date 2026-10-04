# JumpStarter changelog

## What exists

**Search this before building.**

### Setup

- `SETUP.md`: the steps an agent follows when told to set up a repo from this URL. It
  covers new and existing repos, questions asked one at a time, and the tool table
  (Claude Code, Codex/ChatGPT, local models).
- `README.md`: what JumpStarter is, how to use it, what lands in a repo.

### Templates

- `templates/lite/` (default, about 5 KB): `AGENTS.md` (the rules, plain words, read
  small, test before "done", save usage), `CLAUDE.md` (a one-line `@AGENTS.md` import),
  `plan.md` (goal, `## Now`, next, ideas, out of scope), `CHANGELOG.md` (`## What
  exists` and `## Log`), `docs/decisions/0001-goals.md` (five questions),
  `docs/LESSONS.md`.
- `templates/team/` (`--profile team`): `docs/AGENT_TEAM.md` (roles, cost rules, loop,
  safety, models); `docs/agents/{recon,tester,builder,reviewer}.md` (one instruction
  file per role); thin wrappers `.claude/agents/*.md` (haiku recon, sonnet others) and
  `.codex/agents/*.toml` (cheap recon, strong others); `.codex/config.toml`;
  `.claude/settings.json` (allow and deny lists, no stash, no force-push, no `.env`
  reads); `docs/packets/TEMPLATE.md`; a `.gitignore` snippet for worktrees and local
  settings.

### CLI (`tools/jumpstart.py`, standard library, Python 3.9+)

- `init <path> --name X [--profile lite|team]`, with `--description`, `--stack`,
  `--test-cmd`, `--lint-cmd`, `--run-cmd`, `--owner`, `--main-branch`,
  `--branch-prefix`, `--codex-{lead,strong,cheap}-model` and `--force`. It never
  overwrites without `--force`, and never writes `AGENTS.md` beside rules that live
  only in `CLAUDE.md`.
- `retrofit <path>` and `check <path>`: the same audit. It covers the rules file and
  the `CLAUDE.md` import, `AGENTS.md` at most 200 lines, `plan.md` at most 400, `## Now`
  at most 25, the changelog inventory, `## Log` at most 400, the goals record, cited
  lessons, unfilled blanks, team completeness, Codex role metadata and config, and
  extra status files (advisory). The older layout is read as aliases. `retrofit` writes
  nothing.
- `sync-agents <path>`: moves rules out of `CLAUDE.md` into `AGENTS.md` and makes
  `CLAUDE.md` an import. It refuses copies that differ.

### Tests

- `tests/test_jumpstart.py`: init, audit, sync, lessons, team, and the templates' own
  limits (size, no project specifics, shared role files, YAML-safe front matter).

## Log

- 2026-10-04: **v2, lite default.** Owner decision 0003. Templates went from 23 files
  (about 100 KB, 85 blanks) to a 6-file lite set (about 5 KB) plus a team add-on.
  `AGENTS.md` is now the source and `CLAUDE.md` imports it. `SETUP.md` replaces the
  five playbooks. The checkpoint, wishlist, docs index and Codex notes were folded into
  `plan.md` and `AGENTS.md`. This repo moved to the new layout, and its history is in
  `docs/archive/` (`CHECKPOINT_v1.md`, `CHANGELOG_v1.md`, `INTERNALS_v1.md`).
- Before 2026-10-04: see `docs/archive/CHANGELOG_v1.md`.
