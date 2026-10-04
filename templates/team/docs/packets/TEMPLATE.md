# Packet {{ID}}: {{TITLE}}

- Asked for by {{OWNER}} on {{DATE}}: "{{THEIR_WORDS}}"
- Base: `{{MAIN_BRANCH}}` at `{{BASE_SHA}}`. Branch: `{{BRANCH_PREFIX}}{{SLUG}}`.
- Ask-first areas touched: {{NONE_OR_WHICH_AND_THE_QUOTED_ANSWER}}

Line numbers were read on {{DATE}}. Check each before editing. If the code disagrees,
the code is the fact: report it.

## Facts (from recon)

- {{FACT}}: `{{path}}:{{line}}`

## Items

### 1. {{ITEM_TITLE}}

- Now: `{{path}}:{{line}}` {{WHAT_IT_DOES_NOW}}.
- Change: {{WHAT_IT_MUST_DO}}, because {{WHY}}.
- Not in scope: {{WHAT_NOT_TO_TOUCH}}.
- Test that must fail first: {{TEST_AND_WHY_IT_FAILS_TODAY}}.

## Done when

- `{{TEST_CMD}}` passes and `{{LINT_CMD}}` is clean.
- `## Now` in `plan.md` and `CHANGELOG.md` are updated.
- {{WHAT_A_PERSON_MUST_SEE_WORKING}}

## Left for later

- {{WHAT_WAS_DELIBERATELY_LEFT_OUT}}
