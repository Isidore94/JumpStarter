# Recon — Codex lead config + top-level role metadata

Task: add `templates/.codex/config.toml` (lead astra/high, fallback subagent
terra/high), give the four `templates/.codex/agents/*.toml` a top-level
`name`/`description`, install the config in `init` (never overwrite without
`--force`), and have `check` and `retrofit` report a missing config, a missing
native role file, or a missing/empty `name`/`description` — reading only
top-level TOML fields, writing nothing.

## The tool (`tools/jumpstart.py`)

- `INSTALL_MAP` (lines 34–58): template-rel → repo-rel dict. Has the four
  `.codex/agents/*.toml` (lines 55–58); **no config entry**. Drives
  `cmd_init`'s copy loop (lines 936–953: skip-if-exists unless `--force`,
  line 940–944) and `audit_placeholders`'s target list
  (`[*list(INSTALL_MAP.values()), "AGENTS.md"]`, lines 469–470).
- `CODEX_AGENT_FILES` (lines 87–92): the four `.codex/agents/*.toml` repo paths.
- `CODEX_ROLE_TEMPLATES` (lines 99–104): template-side paths; consumed only by
  `cmd_init`'s `--codex-strong-model`/`--codex-cheap-model` fill
  (lines 956–977).
- `CONTROL_FILES` (lines 70–78): seven control files, **including
  `docs/README.md`**. Its presence finding is a duplicate of the "docs
  classified" finding (`audit_doc_classification`, lines 538–550) which checks
  the same file. No pinned test names "control file docs/README.md"
  (verified against `tests/test_jumpstart.py` bare-repo assertions,
  lines 166–189).
- `audit_structure` (lines 703–883) is `retrofit`'s full audit and emits
  **exactly 25 findings** on this repo — pinned by
  `tests/test_i1_rules_carry_evidence.py:247–267` (`"No gaps: 25 checks passed."`
  in `retrofit REPO_ROOT` output, exit 0). Breakdown: 7 control files,
  CLAUDE==AGENTS, bounded read, active state block, implemented inventory,
  rules carry evidence, docs classified, owner goals record, 4 ×
  "agent <role>" (zip loop over `AGENT_FILES`/`CODEX_AGENT_FILES`,
  lines 823–837 — the missing-file detail is
  `"; ".join(f"{rel} not found" ...)`, so deleting one Codex toml yields
  `.codex/agents/recon.toml not found`, asserted by
  `tests/test_c1_native_codex_subagents.py:297`), command allow-list
  (`audit_allow_list`, lines 552–573), stray ledgers, gitignore rules
  (`_claude_dir_is_gitignored`, lines 610–620), 4 size checks.
- `cmd_check` (lines 1038–1047): `audit_agents_identical` + `audit_sizes` (4)
  + `audit_placeholders` (1 aggregate when clean) + `audit_rule_evidence`
  = 7 findings green. **No pinned count for check anywhere**
  (`tests/test_jumpstart.py` asserts only exit codes and substrings;
  `docs/CHANGELOG.md` says "7 checks on this repo" — docs, not a test).
- `Finding` class: statuses OK/ADVISORY/MISSING/DRIFT/OVERSIZE/UNFILLED;
  `ok` = OK+ADVISORY (lines 131–153). Report lines are
  `  [STATUS] name: detail` — pinned regex
  `^  \[[A-Z ]+\] ([^:]+):` in `test_c1...:298`, so finding names must stay
  ASCII and stay **distinct** per finding (C1 asserts uniqueness).
- `jumpstart.main` is the importable entry (`tests` call
  `jumpstart.main([...])`); `__file__` pinning at lines 1072–1079 keeps
  `TEMPLATE_ROOT`/`PLAYBOOK_ROOT` repo-relative.
- No TOML parsing anywhere; Python floor is 3.9 (no `tomllib` — the repo
  itself runs on a bare 3.9 per gate 3). The C1 test ships its own
  string-only parser (`_parse_codex_agent`, lines 99–134) that rejects
  duplicate keys and unknown syntax; extra top-level `name`/`description`
  scalar lines are compatible with it (regex
  `^([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"([^"\\]*)"\s*$` — values must contain no
  backslashes).

## Templates (`templates/.codex/`)

- Four role files, shape `model` / `model_reasoning_effort` /
  `developer_instructions = """..."""`. tester `model = "{{CODEX_STRONG_MODEL}}"`
  (line 1, high line 2); builder `{{CODEX_STRONG_MODEL}}`/high; reviewer
  `{{CODEX_STRONG_MODEL}}`/high; recon `{{CODEX_CHEAP_MODEL}}`/medium
  (templates/.codex/agents/{tester,builder,reviewer,recon}.toml:1-2).
  **None carries a top-level `name` or `description`.**
- `templates/.codex/config.toml` **does not exist**.
- `templates/CLAUDE.md` (read in full) is an ask-first file and is not
  required by the task; leave it untouched.

## Dogfood (root)

- `.codex/agents/{tester,builder,reviewer}.toml`: `model = "gpt-5.6-terra"`,
  high. `.codex/agents/recon.toml`: `gpt-5.6-luna`, medium. No
  name/description. Pinned by `test_c1...:188–192` (models/efforts) and the
  tracked-set assertion `git ls-files -- .codex/agents` == exactly the four
  tomls (lines 171–181) — a root `.codex/config.toml` is outside that scope.
- `.codex/config.toml` does not exist. `.gitignore`'s JumpStarter block
  un-ignores `.codex/agents/` only; `.codex` itself is not ignored, so a
  root `config.toml` is trackable (C1 lines 259–279 assert
  `/.codex/*` is not in gitignore and `git check-ignore` stays quiet for
  `.codex/config.toml` in an initialized repo).

## Pinned test shapes the design must keep

1. i1: `retrofit REPO_ROOT` exit 0, exactly one "rules carry evidence" line,
   "No gaps: 25 checks passed." (test_i1...:247–267).
2. C1: root + template `.claude/agents/*.md` sha256 pinned
   (CLAUDE_ROLE_SHA256, lines 20–45); dogfood model routing (188–192);
   init-installed role files parse with `_parse_codex_agent` and keep their
   model/effort/instruction content (194–225); initialized repo with codex
   models unfilled → check 1 naming the placeholders (236–249); filled
   init → check 0 and retrofit 0 (251–256); `approval_policy` config written
   after init must exist to overwrite (270); non-force init never overwrites
   a project-owned role file (281–287); deleting `.codex/agents/recon.toml`
   → retrofit 1, output contains `.codex/agents/recon.toml not found`,
   finding names distinct, tree bytes unchanged (291–301).
3. jumpstart: bare-repo retrofit names ("agent builder|reviewer|recon",
   "command allow-list", "docs classified", … lines 166–189 — none names
   "control file docs/README.md"); `test_every_installed_template_exists`
   walks `jumpstart.INSTALL_MAP` (every key needs a template file);
   `test_jumpstarter_passes_its_own_check` = `check REPO_ROOT` exit 0
   (398–400); retrofit report must be ASCII-encodable; init fills
   placeholders into `.toml` files via `fill` on `.md/.json/.toml`
   suffixes (my config template must be placeholder-free so the codex-model
   unfilled path keeps working: retrofit must still exit 0 after a
   no-model init, C1 236–249 / i1-style fills).
4. codex guidance test (C1 304–349): root + installed `docs/CODEX_NOTES.md`
   keep substrings `.codex/agents/`, `gpt-5.6-terra`, `gpt-5.6-luna`,
   `.claude/packets/`, `handoff`; no "paste the body" / "there are no
   automatic"; five repo docs keep `.codex/agents/`; root CLAUDE.md ==
   AGENTS.md and contain `.claude/agents/`, `.codex/agents/`,
   `templates/.codex/agents/*.toml`; root + installed `docs/INTERNALS.md`
   keep `AGENTS.md == AGENTS.md`, `Codex/<slug>`,
   `templates/.codex/agents/*.toml`.

## Pre-existing worktree damage (baseline suite is red, not my doing)

`git status`: `M .claude/agents/{builder,recon,reviewer,tester}.md`,
`M CLAUDE.md`. `git diff` (content-only changes; line endings already match
the committed bytes, so reversing the hunks restores byte-exact files):

- `CLAUDE.md`: a 27-line harness "Orchestration rules for this job" block
  prepended before `# JumpStarter — AI context index` (from
  `# Orchestration rules...` through the `---` line and two blanks). This
  makes `check`/`retrofit` report `CLAUDE.md` DRIFT vs `AGENTS.md`.
- Root `.claude/agents/*.md`: template placeholder content planted over the
  filled dogfood content — `{{PROJECT}}`→`JumpStarter`,
  `{{MAIN_BRANCH}}`→`main`, `{{OWNER}}`→`the owner`, `{{TOOLCHAIN}}`→
  `any Python 3.9+ on PATH (standard library only; no venv, no install)`,
  `{{CRITICAL_AREA}}`→`templates/ or the limit constants in
  tools/jumpstart.py`, `{{ASK_FIRST_FILES}}`→
  `templates/CLAUDE.md, templates/plan.md, templates/.claude/agents/*.md, and
  the limit constants in tools/jumpstart.py`, etc. (`git diff` `-` lines are
  the originals.) This trips four UNFILLED `{{...}}` findings in `check`.
- Confirmed baseline state: `pytest -q` → **4 failed, 53 passed** (all four
  failures are damage-driven: i1 retrofit-25, C1 sha256/dogfood, C1
  retrofit/ASCII, dogfood self-check); `ruff check .` clean;
  `python tools/jumpstart.py check .` exit 1 (DRIFT + 4 UNFILLED).
- The four damaged root role files are exactly the ones C1 pins by sha256
  (CLAUDE_ROLE_SHA256 root entries) — restoring the `-` side of the diff
  byte-exactly is both the repair and the pinned target. `CLAUDE.md` must
  end with `sha256(CLAUDE.md) == sha256(AGENTS.md)` (i1 + C1
  `test_codex_guidance...` line 338); strip the block, verify, fall back to
  `sync-agents` if not equal.

## Docs that must be reconciled (repo doc workflow)

- `CLAUDE.md` (root): one new **Rules** bullet + `*(INTERNALS: "...")*`
  citation → then `sync-agents` (AGENTS.md generated). Citation is enforced
  by `audit_rule_evidence` on root + every init'd repo.
- `docs/INTERNALS.md`: 11 entries, format `## <Rule> (<date>, <packet>)`
  with rule-as-stated / incident / measured / deliberately-NOT-done /
  reopen-trigger; append one entry for the new rule.
- `CHANGELOG.md`: inventory "Codex" bullets (~33–36) gain config +
  name/description; CLI bullets "retrofit audits **25 checks**" (composition
  note: codex config replaces the docs/README control-file finding; role
  metadata rides the four "agent <role>" findings) and "**check** … **7
  checks** on this repo" → 15; `Last reconciled` date; new
  `## Recent changes` dated entry.
- `CURRENT_CHECKPOINT.md`: refresh the "Active state at a glance" block
  (working branch main; worktree rules forbid commits, so the packet stays
  uncommitted; measured baseline numbers); add a dated entry.
- `docs/README.md` "## Agent definitions" table (lines ~74–79): add a
  `.codex/config.toml` row.
- `docs/AGENT_TEAM.md` "For Codex" (lines ~62–66): one line about the config.
- `docs/CODEX_NOTES.md` + `templates/codex/CODEX_NOTES.md`: "Native roles
  and model routing" — replace "The lead keeps the session model." with the
  config-driven statement (keep all pinned substrings).
- `playbooks/new-project.md`: ~44 "This writes both native role sets" → add
  the config; fill-in table ~95; `git add` list ~130 gains
  `.codex/config.toml`.
- `playbooks/retrofit.md`: audit table (~30–42) — "Control files present"
  row drops `docs/README.md` (covered by Docs classified); "Agent
  definitions" row gains name/description; new "Codex lead config" row;
  step 8 copy list gains `.codex/config.toml`.

## Design conclusion (carried into the plan)

- `check`: +5 findings (`codex config` + 4 × `codex role <role>`), 7 → 15
  green; count unpinned.
- `retrofit`: stays at 25 — `codex config` (1) **replaces** the duplicate
  `control file docs/README.md` (drop from `CONTROL_FILES`; the stray-ledger
  `known` set already names `README.MD` explicitly), and the four
  `agent <role>` findings **also** carry the Codex metadata check (missing
  file short-circuits to the existing `… not found` detail, keeping the C1
  assertion).
- Top-level-only scanner (hand-rolled, stdlib): `key = "value"` scalars only,
  stop at first `[` table header, skip multi-line `"""`/`'''` bodies, ignore
  non-string scalars. Python 3.9 has no `tomllib`; the audit only ever asks
  "does this file carry a top-level name/description".
- Template `name`/`description` are **literal** (no placeholders) so the
  no-codex-model init → retrofit-0 path stays green; ASCII so reports stay
  ASCII-encodable.
- Config template fields: `model = "astra"`,
  `model_reasoning_effort = "high"`, `fallback_subagent_model = "terra"`,
  `fallback_subagent_reasoning_effort = "high"` — flat top level, no
  `[table]` sections (the audit reads top level only).
