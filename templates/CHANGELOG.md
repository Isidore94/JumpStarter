# {{PROJECT}} implemented history

Last reconciled: **{{DATE}}**

Authoritative for: **what exists, and the historical sequence of revisions.**
Remaining work: [`plan.md`](plan.md). Where we are now:
[`CURRENT_CHECKPOINT.md`](CURRENT_CHECKPOINT.md).

This is a curated product history, not a commit dump. Exact current test counts live in
`CURRENT_CHECKPOINT.md`.

The status labels keep their strict meanings from `plan.md` section 2: `IMPLEMENTED`
means code exists, `GREEN` means deterministic tests pass, `VALIDATED` requires
real-world evidence, and `PROMOTED` requires an explicit decision. A feature can be
implemented and green while its gate is still open.

## Current implemented inventory

**This is the contract: what exists, by area. Search it before building anything so you
do not rebuild landed work.** It is deliberately short — one entry per capability,
stating what exists and the one thing about it that is easy to get wrong. Everything
older than the recent-changes window below is archived under `docs/` and must not be
loaded as context.

### {{AREA_1}}

- **{{CAPABILITY}}** — {{WHAT_EXISTS}}. `{{MODULE_OR_PATH}}` is the one implementation.
  The trap: {{THE_THING_THAT_IS_EASY_TO_GET_WRONG}}.

### {{AREA_2}}

- **{{CAPABILITY}}** — {{WHAT_EXISTS}}.

### Tests, lint and build

- {{WHAT_THE_SUITE_COVERS}}; the measured count lives in `CURRENT_CHECKPOINT.md`.

## Recent changes ({{DATE}} onward)

The last two build days only. **When this section passes ~800 lines, move the older
entries into `docs/CHANGELOG_ARCHIVE_{{YYYY_MM}}.md` and leave a pointer here.**
`python tools/jumpstart.py check .` enforces the limit.

### {{DATE}} — {{WHAT_LANDED}}

- {{CHANGE}} ({{COMMIT}}). Fail-before-fix proven on {{TEST}}.

## Archived history

- `docs/CHANGELOG_ARCHIVE_{{YYYY_MM}}.md` — everything before {{DATE}}. Evidence for one
  specific question; never context to load.

## Retired or superseded implementations

Recorded so they are not accidentally resurrected.

- {{WHAT_WAS_RETIRED}} ({{DATE}}) — {{WHY}}, and what replaced it.
