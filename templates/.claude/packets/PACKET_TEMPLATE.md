# Packet {{ID}} — {{TITLE}}

Authorized by {{OWNER}} on {{DATE}} ("{{VERBATIM_QUOTE}}"). Base: `{{MAIN_BRANCH}}` at
`{{BASE_SHA}}`. Branch: `{{BRANCH_PREFIX}}{{SLUG}}`. Governing: {{GOVERNING_DOCS}}.
Line numbers below were read by the lead on {{DATE}} against `{{BASE_SHA}}`; verify each
before editing — **if the code disagrees with this packet, the code is the fact**: report
the difference, do not force the change.

The ask-first rule **does / does not** apply: {{WHY}}.

{{STANDING_PROHIBITION_FOR_THIS_RUN}} — e.g. never restart the application; a named
process is running an older tip; a store that must not be touched.

## What the lead measured

The evidence this packet is built on, with the instrument and the window, not a summary
of it. A claim with no measurement beside it is a draft.

- {{WHAT_WAS_MEASURED}} — {{HOW}}, {{WHEN}}: {{THE_NUMBERS}}.
- {{WHAT_EXISTS_TODAY}} — `{{path}}:{{line}}`.
- {{WHAT_DOES_NOT_EXIST}} — not found; searched {{WHERE}}.

## Items

### 1. {{ITEM_TITLE}} (`{{path}}`)

Today `{{symbol}}` at `{{path}}:{{line}}` {{WHAT_IT_DOES_NOW}}. Change it to
{{WHAT_IT_MUST_DO}}, because {{WHY_IN_ONE_CLAUSE}}. {{WHAT_NOT_TO_TOUCH}} is out of
scope — a wider change is a separate packet.

Binding invariants: {{WHICH_INVARIANTS}}.

Tests (new `{{test_path}}`): (a) {{ASSERTION}}; (b) {{ASSERTION}}; (c) {{ASSERTION}}.
**(b) is the fail-before-fix proof** — on the un-fixed code it fails with
{{THE_EXPECTED_FAILURE}}, because {{WHY_THE_OLD_CODE_CANNOT_PASS_IT}}. The existing
{{WHICH}} tests must stay green untouched.

### 2. {{ITEM_TITLE}}

...

## Parts (delete if this packet is one branch)

- **PART A** — on `{{BRANCH_PREFIX}}{{SLUG}}` off `{{MAIN_BRANCH}}`: items 1–{{N}}.
- **PART B** — on `{{OTHER_BRANCH}}`: merge `{{MAIN_BRANCH}}` (with Part A) in first,
  then items {{N}}–{{M}}.
- **PART C** — integrate and prove: merge order, the full gate list, the checkpoint
  refresh, and the one line {{OWNER}} is told at the end.

## Docs to reconcile (same branch)

- `CURRENT_CHECKPOINT.md` — a dated entry carrying the measurements above (short); the
  gate below as a row in the gates table; refresh the "Active state at a glance" block.
- `CHANGELOG.md` — inventory line(s) for {{WHAT_LANDED}}; one `Recent changes` entry.
- `plan.md` — advance or narrow {{ITEM}}; keep any gate still owed.
- `docs/INTERNALS.md` — the entry behind any new rule, with the numbers.
- `docs/README.md` — only if a Markdown file was added or reclassified.
- `CLAUDE.md` + `AGENTS.md` (byte-identical, `jumpstart.py sync-agents .`) — **exactly
  this rule line, no more**:
  > {{THE_RULE_TEXT_TO_ADD_VERBATIM}}

## Gates before handoff

{{PRECONDITION_TO_PROBE}}; `{{TEST_CMD}}` exit 0 with nothing deselected; `{{LINT_CMD}}`
clean; {{EXTRA_GATES}}. Report the **process** exit codes, not a piped tail's. Say
whether a build or packaging trigger was hit; a rebuild is the lead's call.

## The real-world gate

**{{WHAT_MUST_BE_OBSERVED_IN_THE_REAL_WORLD}}** — not a test. Who observes it, on what
run, and what exactly they must see. It goes in the checkpoint's gates table and stays
open until someone has seen it.

## Still owed after {{ID}}, as its own packet {{NEXT_ID}}

{{WHAT_WAS_CONSIDERED_AND_DELIBERATELY_LEFT_OUT}} — named here so it is queued, not
rediscovered later as a gap.
