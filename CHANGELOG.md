# JumpStarter implemented history

Last reconciled: **2026-09-03** (second pass)

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
- **The agent set** — `.claude/agents/{tester,builder,reviewer,recon}.md` with front
  matter, `.claude/settings.json` (allow-list plus a deny-list for the destructive git
  verbs, `git stash` among them), `.claude/packets/PACKET_TEMPLATE.md`,
  `.gitignore.snippet`. The trap: `tester` writes the failing tests and **never** the
  fix; the builder may add tests but may not weaken a tester's assertion. That split is
  the whole point of the role.
- **The packet shape** — reconciled 2026-09-03 against three real packets: the
  authorization, base sha, governing docs, line-number stamp and the explicit ask-first
  ruling all live in the opening paragraph; then what was measured; then prose items
  naming the fail-before-fix assertion; then two gate blocks (pre-handoff commands, and
  the real-world gate) and a "still owed, as packet X" tail.
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
- **`retrofit`** audits **25 checks** and **writes nothing**.
- **`check`** enforces `CLAUDE == AGENTS` (sha256), the four size limits, and unfilled
  placeholders.
- **`ADVISORY` findings** — reported, named, and **not** a gap: `Finding.ok` is true for
  them and they do not change the exit code. Three exist: a machine-local (gitignored)
  allow-list, an active-state block under a heading other than the standard one, and
  stray root-level ledger files. The trap: a check that fires on correct work gets
  ignored and takes the real findings with it — each of these was a false positive or a
  near-miss on a real repository before it became an advisory.
- **`audit_active_state`, `audit_allow_list`, `audit_stray_ledgers`** — the three
  functions behind those advisories. `_claude_dir_is_gitignored` reads `.gitignore` as
  text rather than shelling out to git, so the tool keeps its no-dependency invariant.
- **The limits** — `CHECKPOINT_MAX_LINES` 1500, `PLAN_MAX_LINES` 1200,
  `CHANGELOG_RECENT_MAX_LINES` 800, `CLAUDE_MAX_LINES` 400. Two traps: the changelog
  limit measures the "Recent changes" *section*, via `section_line_count`, not the file
  — an archive in the same file must not trip it — **but** when the file has no such
  section the whole file is measured instead, or a chronological changelog escapes the
  bound entirely.
- **ASCII output.** Every printed advice string is ASCII, and `main()` sets
  `errors="replace"` on stdout/stderr. A report that prints as mojibake is trusted less
  than one that prints plainly.

### Tests (`tests/test_jumpstart.py`)

- Covers `init` (control set, placeholders, gitignore ordering and idempotency, overwrite
  refusal), `retrofit` (gaps on a bare repo, writes-nothing, clean after init, drift),
  `sync-agents`, `check` (each limit, drift, the section-not-file rule), the unit
  functions, and JumpStarter's own `check`.
- A block at the end pins **what the audit got wrong on a real repository**: each of the
  two false positives and four misses of 2026-09-03 has a test built from the shape that
  produced it. Delete one of those and the false positive comes back.

### Root

- `README.md` carries the exact instruction "apply JumpStarter here" and the steps it
  triggers, and states the Python floor **as measured** (3.9.25, 2026-09-03) rather than
  claimed. `PRINCIPLES.md` holds **sixteen** lessons with the incident behind each —
  twelve from the source project's documentation, four more from its session memory.
- `ruff.toml` pins the lint gate: `target-version = "py39"` to match the declared floor,
  and an explicit rule selection. The trap: without it, `ruff check .` means whatever
  ruff version is installed — the same tree read "All checks passed" under one and 75
  findings under 0.16.6.

## Recent changes (2026-09-03 onward)

The last two build days only. When this section passes ~800 lines, archive the older
entries under `docs/` and leave a pointer.

### 2026-09-03 — Second pass: the four unreadable sources, and gates 1 and 3

- **Read the four sources the first build could not**: the source project's real packets,
  its real `.claude/settings.json`, its `.claude/worktrees/` layout, and its session
  memory notes. The memory notes were the richest: four lessons that were in no document.
- **`tester` joins the agent team** (templates + this repo's own `.claude/agents/`), with
  the loop, the delegation policy and the handoff-vs-diff check in `docs/AGENT_TEAM.md`.
- **`PACKET_TEMPLATE.md` reshaped** to what three real packets actually look like.
- **`git stash` moves from the allow-list to the deny-list**, and the builder's
  "stash or restore" becomes "restore".
- **PRINCIPLES.md 13-16** added from the memory notes.
- **Gate 1 closed**: three real audits — the source project's working copy (3 gaps, all
  real), a repo with partial control files (14 gaps), and one with no control set at all
  (22 of 22). Two false positives and four misses, each now a test.
- **Gate 3 closed**: CPython 3.9.25, 49 passed, exit 0, all four subcommands.
- **`ruff.toml`** added; the lint gate had never been reproducible.

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

### 2026-09-03 — The questionnaire, asked one question at a time

- `docs/decisions/0002-owner-goals-asked-properly.md` — all twelve answers verbatim.
  `0001` is `SUPERSEDED` and kept as evidence of what was assumed before anyone asked.
  No **OPEN** answer remains; two answers are explicit non-answers and stay that way.
- Two of 0001's guesses were wrong: **the agent is the reader, not the owner** (so the
  size limits are the product), and **cost is the trust signal** (so the delegation
  policy is load-bearing). Both are now the tie-breakers `plan.md` section 1 cites.
- The orchestrating model is explicitly not fixed, so nothing in `templates/` names one.
