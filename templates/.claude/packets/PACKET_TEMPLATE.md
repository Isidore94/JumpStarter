# Packet {{ID}} — {{TITLE}}

Date written: {{DATE}} · Branch: `{{BRANCH_PREFIX}}{{SLUG}}` off `{{MAIN_BRANCH}}` ·
Builder: one · Reviewer: required / not required (docs-only)

**A packet is written only from premises verified in the code.** Every `file:line` below
was read on the date above. **If the code disagrees with this packet, the code is the
fact** — the builder reports the difference and does not force the change.

---

## {{OWNER}}'s decision, quoted

> "{{VERBATIM_QUOTE}}"
> — {{OWNER}}, {{DATE}}

Source: `docs/decisions/{{NNNN}}.md` / the conversation of {{DATE}}. If a packet cannot
quote a decision for a change to an ask-first file, that item stops and becomes a
question in the handoff.

## Premises, verified

Facts this packet is built on, each with evidence. Verified by `recon` on {{DATE}}.

| # | Premise | Evidence |
|---|---|---|
| 1 | {{WHAT_IS_TRUE_TODAY}} | `{{path}}:{{line}}` |
| 2 | {{WHAT_DOES_NOT_EXIST}} | not found: searched {{WHERE}} |
| 3 | {{WHAT_THE_REAL_DATA_SHOWS}} | {{COUNT}} rows in {{STORE}}, read {{DATE}} |

## Inventory check

Searched `CHANGELOG.md`'s "Current implemented inventory" for: {{TERMS}}. Result:
{{WHAT_ALREADY_EXISTS_AND_MUST_NOT_BE_REBUILT}}.

---

## Items

### 1. {{ITEM_TITLE}}

**Change.** Exactly what to do, in one or two sentences. Name the file and the function.

**Where.** `{{path}}:{{line}}` — {{WHAT_IS_THERE_NOW}}.

**Test that must fail first.** `{{test_path}}::{{test_name}}` — asserts
{{THE_BEHAVIOUR}}. On the un-fixed code it must fail with {{THE_EXPECTED_FAILURE}}.
Restore the pre-change file, run it, watch it fail, restore.

**Invariants that bind.** {{WHICH_INVARIANTS}}.

**Out of scope for this item.** {{WHAT_NOT_TO_TOUCH}} — a wider change is a separate
packet.

### 2. {{ITEM_TITLE}}

...

---

## Docs to reconcile (same branch)

- `CURRENT_CHECKPOINT.md` — refresh the "Active state at a glance" block; add the gate.
- `CHANGELOG.md` — inventory entry for {{WHAT_LANDED}}.
- `plan.md` — advance or narrow {{ITEM}}; keep any gate still owed.
- `docs/INTERNALS.md` — an entry for any new rule, with the incident behind it.
- `docs/README.md` — only if a Markdown file was added or reclassified.
- `CLAUDE.md` / `AGENTS.md` — byte-identical (`jumpstart.py sync-agents .`).

## Gate

**{{WHAT_MUST_BE_OBSERVED_IN_THE_REAL_WORLD}}** — not a test. Who observes it, on what
run, and what exactly they must see. Record it as a row in the checkpoint's gates table.

## Not in this packet

State plainly what was considered and deliberately left out, so it is not rediscovered
as a gap.
