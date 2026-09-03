# JumpStarter implemented history

Last reconciled: **2026-09-03**

Authoritative for: **what exists, and the historical sequence of revisions.**
Remaining work: [`plan.md`](plan.md). Where we are now:
[`CURRENT_CHECKPOINT.md`](CURRENT_CHECKPOINT.md).

Exact current test counts live in `CURRENT_CHECKPOINT.md`.

## Current implemented inventory

**This is the contract: what exists, by area. Search it before building anything so you
do not rebuild landed work.**

### Templates (`templates/`)

- **The control set** — `CLAUDE.md`, `AGENTS.md` (byte-identical copy), `plan.md`,
  `CURRENT_CHECKPOINT.md`, `CHANGELOG.md`, `WISHLIST.md`, with `{{...}}` placeholders.
  The trap: `templates/AGENTS.md` is a byte-identical copy of `templates/CLAUDE.md` and a
  test enforces it — edit `templates/CLAUDE.md` and re-copy, never the other one.
- **The docs set** — `docs/README.md` (classification table), `docs/INTERNALS.md` (the
  incident behind every rule), `docs/AGENT_TEAM.md` (roles, loop, handoff and verdict
  formats), `docs/decisions/0000-template.md`, and
  `docs/decisions/0001-owner-goals-and-priorities.md` (a twelve-question questionnaire).
- **The agent set** — `.claude/agents/{builder,reviewer,recon}.md` with front matter,
  `.claude/settings.json` (allow-list plus a deny-list for the destructive git verbs),
  `.claude/packets/PACKET_TEMPLATE.md`, `.gitignore.snippet`.
- **Codex** — `codex/CODEX_NOTES.md`, installed as `docs/CODEX_NOTES.md`. What Codex
  reads, what it cannot do, and how the same packet reaches it.
- The two files that keep their placeholders on purpose are
  `docs/decisions/0000-template.md` and `.claude/packets/PACKET_TEMPLATE.md`.

### Playbooks (`playbooks/`)

- **`new-project.md`** — eight steps, questionnaire first, `check` green last.
- **`retrofit.md`** — nine steps under one rule: archive, do not delete; never rewrite
  history. Ends with what a retrofit must not do.
- **`build-review-loop.md`** — the loop with the exact prompts the lead gives `recon`,
  `builder` and `reviewer`, plus the ten-line owner report.
- **`review-by-reproduction.md`** — the reviewer checklist and the eight traps.
- **`packet-writing.md`** — how to write a packet from verified premises, and sizing.

### CLI (`tools/jumpstart.py`)

- **Four subcommands** — `init`, `retrofit`, `sync-agents`, `check`. Standard library
  only. Exit codes 0 / 1 / 2 are the interface: 0 success or no gaps, 1 gaps or failure,
  2 usage error.
- **`init`** copies `INSTALL_MAP`, fills the placeholders it was given, generates
  `AGENTS.md` from `CLAUDE.md`, and appends the `.gitignore` block idempotently. It
  skips files that exist unless `--force`.
- **`retrofit`** audits twelve check families and **writes nothing**.
- **`check`** enforces `CLAUDE == AGENTS` (sha256), the three size limits, and unfilled
  placeholders.
- **The limits** — `CHECKPOINT_MAX_LINES` 1500, `CHANGELOG_RECENT_MAX_LINES` 800,
  `CLAUDE_MAX_LINES` 400. The trap: the changelog limit measures the "Recent changes"
  *section*, via `section_line_count`, not the file — an archive in the same file must
  not trip it.

### Tests (`tests/test_jumpstart.py`)

- Covers `init` (control set, placeholders, gitignore ordering and idempotency, overwrite
  refusal), `retrofit` (gaps on a bare repo, writes-nothing, clean after init, drift),
  `sync-agents`, `check` (each limit, drift, the section-not-file rule), the unit
  functions, and JumpStarter's own `check`.

### Root

- `README.md` carries the exact instruction "apply JumpStarter here" and the steps it
  triggers. `PRINCIPLES.md` holds the twelve lessons with the incident behind each.

## Recent changes (2026-09-03 onward)

The last two build days only. When this section passes ~800 lines, archive the older
entries under `docs/` and leave a pointer.

### 2026-09-03 — First build

- Distilled the twelve principles and the control-set shape from a mature agent-built
  project, generalised: no domain content in `templates/`.
- Wrote the templates, the five playbooks, the CLI and 36 tests.
- Ran `init` on this repo to produce its own control set, then filled it by hand.
- `TEMPLATES_BY_NATURE` added to the placeholder check: two files exist to be copied, so
  their placeholders are the product, not an omission.
- `docs/prompts/REFRESH_FROM_SOURCE_PROMPT.md` — paste-ready brief for a session on the
  owner's machine to re-harvest from the source project and close gates 1 and 3. It is a
  prompt, not work done: no gate closes on it.
- First retrofit dry run against a clone of a mature repo: 22 checks, 3 gaps — two
  real size violations and one false positive (a correctly-gitignored allow-list read
  as absent). Recorded in `CURRENT_CHECKPOINT.md`; the fix is `plan.md` Phase 0 item 2.

## Retired or superseded implementations

Nothing yet.
