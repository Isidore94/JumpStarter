# {{PROJECT}}

{{ONE_LINE_DESCRIPTION}}

These are the rules for every AI agent working here: Claude Code, Codex/ChatGPT, or a
local model. `CLAUDE.md` only imports this file. Edit this file, never a copy.

## Talking to {{OWNER}}

- Plain words, short sentences. Lead with the result.
- Say what you did, what is broken, and what {{OWNER}} needs to decide. Then stop.
- Aim for five lines or fewer. Detail goes in commits and docs, not chat.
- Explain any technical term in a few words the first time you use it.

## Start of every task: read small

1. `plan.md`: read the `## Now` section only. It says where things stand.
2. `CHANGELOG.md`: search `## What exists` for what you are about to build. Do not
   rebuild something that already works.
3. Open only the files the task needs. Search first; do not read whole folders.

If the docs and the code disagree, the code is right. Fix the doc and say so.

## While working

- Do only what was asked. New ideas go under `## Ideas` in `plan.md`; do not build
  them.
- Ask {{OWNER}} first before you delete files, add a dependency, change anything under
  `## Ask first` below, or do anything that is hard to undo.
- Work in small steps and run the tests after each one.
- A bug fix comes with a test that fails without the fix.
- Never commit secrets: `.env` files, keys, tokens or passwords.

## Before you say "done"

- Tests: `{{TEST_CMD}}` must pass. Report the real result ("42 passed"), not "looks
  fine".
- Lint: `{{LINT_CMD}}` must be clean.
- Update `## Now` in `plan.md`: what changed, the test result, and the next step.
- Something new works? Add one line to `## What exists` and one to `## Log` in
  `CHANGELOG.md`.
- Made a real choice with {{OWNER}}? Write `docs/decisions/NNNN-short-name.md`: the
  decision, why, what was rejected, when to revisit.
- Something broke and you learned why? Add it to `docs/LESSONS.md`.
- Commit small, with a message that says why.

## Save usage

- Read the least that answers the question. Quote the lines that matter; never paste
  whole files or logs into chat.
- If your tool has helper agents (subagents), send searches and lookups to a cheap,
  fast one. Do small edits yourself. If `docs/AGENT_TEAM.md` exists, follow it.
- Long session? Update `## Now`, then start a fresh session. The plan is the memory,
  not the chat.

## Project facts

- Stack: {{STACK}}
- Run: `{{RUN_CMD}}`
- Main branch: `{{MAIN_BRANCH}}`

## Ask first

- Nothing listed yet. Add files or areas where a mistake is costly.

## Rules learned the hard way

<!-- One line per rule, added when something breaks. Shape:
- **Short rule.** Why, in one clause. (LESSONS: "Rule name")
`jumpstart.py check` fails if the cited name has no heading in docs/LESSONS.md. -->

## Files

| File | What it is for |
|---|---|
| `plan.md` | goal, `## Now` (read first), next steps, ideas |
| `CHANGELOG.md` | what exists today, and a short log |
| `docs/decisions/` | why things were chosen; `0001` holds {{OWNER}}'s goals |
| `docs/LESSONS.md` | what broke, why, and the rule it produced |

Do not add other status, roadmap, todo or handoff files. Use the ones above.
