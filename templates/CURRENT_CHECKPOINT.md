# Current checkpoint

This file is the frequently refreshed active-work, branch and verification stamp.

- Implemented inventory and revision history: [`CHANGELOG.md`](CHANGELOG.md)
- Remaining work and gates: [`plan.md`](plan.md)
- Supporting-document roles: [`docs/README.md`](docs/README.md)
- Older entries: archived under `docs/` — see the archive rule at the bottom.

---

## Active state at a glance

**Read this block first. It is the answer to "where are we?" — the dated entries below
are the working record behind it. Refresh this block on every handoff; if it disagrees
with the newest dated entry, the dated entry wins and this block is stale.**

| | |
|---|---|
| Working branch | **`{{MAIN_BRANCH}}`** — {{WHAT_IS_ON_IT}} |
| Also in flight | {{UNMERGED_BRANCHES_OR_NOTHING}} |
| Active items | {{THE_ONE_ACTIVE_ITEM}}, from `plan.md` phase {{PHASE}} |
| Last verified baseline | `{{TEST_CMD}}` **{{N}} passed, process exit {{CODE}}, {{DURATION}}** ({{DATE}}, on `{{COMMIT}}`) · lint **{{LINT_RESULT}}** · {{OTHER_GATE}} |
| Artifact state | {{WHAT_THE_APP_ACTUALLY_RUNS_FROM}} — source or build, which commit, whether a rebuild is owed and why |
| Restart owed | {{YES_WITH_REASON_OR_NO}} — a merged commit reaches {{OWNER}} only at the next restart, and the restart is their call |

Rules for this block:

- Numbers, not adjectives. "Tests green" is a memory of state; "{{N}} passed, exit 0,
  measured on `{{COMMIT}}`" is state.
- Check the **process** exit code, not a piped tail's.
- If a number was not measured this handoff, say so and say when it was.

### Open gates, newest first

Each is owed before the work it belongs to can be called validated. Detail lives in the
dated entry named beside it.

| # | Gate | Owed by |
|---|---|---|
| 1 | {{WHAT_MUST_BE_OBSERVED_IN_THE_REAL_WORLD}} | {{DATED_ENTRY}} |

A gate is closed by striking its row through and writing what was observed — never by
deleting the row.

---

### {{DATE}} — {{ENTRY_TITLE}}

**Branch `{{BRANCH}}`, off `{{MAIN_BRANCH}}`.**

What changed, in the shortest form that carries the decision and its evidence. Detail
belongs in the governing spec, not in a fourth retelling here.

**What was NOT built, and why.** State this as plainly as what was.

**Proof.** `{{TEST_CMD}}` → {{N}} passed, exit {{CODE}}. Lint {{LINT_RESULT}}.
Fail-before-fix: {{WHICH_TESTS_FAILED_ON_THE_BASE_COMMIT}}.

**Gate recorded.** {{GATE}}.

---

## Archive rule

When this file passes **~1,500 lines**, move the entries older than the oldest open gate
into `docs/CHECKPOINT_ARCHIVE_{{YYYY_MM}}.md` and leave a pointer at the top of this
file. The archive is evidence for one specific question; it is never loaded as context.
Archiving is maintenance, not a new document.

`python tools/jumpstart.py check .` enforces the limit.
