# Report — Codex lead config + top-level role metadata

Codex cannot pick the four roles natively. This packet adds a lead config template,
gives each role file the metadata Codex lists its subagents by, and makes `check`
and `retrofit` report the Codex control set.

## What changed

**`tools/jumpstart.py`:**
- `INSTALL_MAP` gains `.codex/config.toml`; new constant `CODEX_CONFIG`.
- `docs/README.md` removed from `CONTROL_FILES` — it duplicated the "docs
  classified" finding, and its slot now holds the new `codex config` finding, so
  retrofit's pinned 25-check count does not move.
- `_top_level_toml_strings` — deliberately shallow reader: top-level
  `key = "value"` scalars only, stops at the first table header, skips a
  multi-line string's body. Python 3.9 has no `tomllib` and the audit only ever
  asks "does this file carry a top-level name and description".
- `audit_codex_config` (1 finding) and `audit_codex_roles` (4 findings) — used
  by `check` outright. `retrofit` folds the metadata check into its four
  `agent <role>` findings instead, keeping its 25-check shape.
- `cmd_check` appends both; module docstring and the `check` help string updated.

**Templates (`templates/.codex/`):**
- New `config.toml`: `model = "astra"` at high effort, fallback subagent `terra`
  at high effort; flat top-level fields, no placeholders of its own.
- The four role templates gain a top-level `name` (the role) and a one-line
  `description`; no other line touched, so the C1 fill and instruction
  assertions are intact.

**Dogfood (this repo):** `.codex/config.toml` installed with `gpt-5.6-terra` lead
and `gpt-5.6-luna` fallback, both high effort; the four tracked
`.codex/agents/*.toml` carry the same metadata.

**Tests (`tests/test_codex_lead_config.py`, new file, 10 tests):** template
content; role metadata; `init` installs the config; install without overwrite
(pre-seeded config survives non-force init, `--force` replaces it); `check`
gaps for missing config, missing role file, missing and empty metadata;
`retrofit` reporting the same gaps with tree bytes unchanged before and after;
top-level-only reads (nested table not seen; key-shaped lines inside a
multi-line string not mis-read); dogfood green on this repo. Proven red before
the fix: `.qo/tests-red.txt`. No existing test touched.

**Docs (the repo's own workflow):** new rule "The Codex control set is checked
at the top level" in `CLAUDE.md` with its `docs/INTERNALS.md` entry;
`AGENTS.md` re-synced (byte-identical, verified by `check`); `CHANGELOG.md`
inventory + recent-changes entry; `docs/README.md` row; `docs/CODEX_NOTES.md`
and `docs/AGENT_TEAM.md` native-routing text; `CURRENT_CHECKPOINT.md` block
refreshed + dated entry.

## Results (measured 2026-10-27, CPython 3.12 and 3.9, both uv-managed)

| Command | Result |
|---|---|
| `python -m pytest tests/ -q` | **67 passed, exit 0** (57 + 10 new) — on both 3.12 and 3.9 |
| `ruff check .` | All checks passed, exit 0 |
| `python tools/jumpstart.py check .` | **12 checks, no gaps, exit 0** (7 + 5 new) |
| `python tools/jumpstart.py retrofit .` | **25 checks, 1 advisory, exit 0**, "changed nothing" |

Fail-before-fix: `.qo/tests-red.txt` shows the ten new tests red on the base.

## Notes

- **Not committed.** The job rules forbid committing; the packet stays in the
  working tree on `main`.
- One lint error from the previous pass (FURB167: `re.M` alias at
  `tests/test_codex_lead_config.py:228`) fixed to `re.MULTILINE`.
- The previous pass's docs claimed `check` grew to 15 findings; the measured
  count is 12 (7 + 5). Corrected in `CHANGELOG.md` and `docs/INTERNALS.md`.
- Playbook mirrors (`playbooks/new-project.md`, `playbooks/retrofit.md`) were
  not part of this pass per the lead's "keep it short" scoping; the checkpoint
  entry says so.
- Self-review: `.qo/review.json`, verdict GO, no blockers, five advisories.
