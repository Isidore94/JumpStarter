# Agent team

How the lead session (the one {{OWNER}} talks to) splits work across helper agents so
the expensive model does only the thinking. Works the same in Claude Code and Codex;
a tool with no helper agents just has the lead do every step itself.

## Roles

| Role | Model tier | Does | Never does |
|---|---|---|---|
| lead | whatever {{OWNER}} picked | asks {{OWNER}}, writes packets, spawns helpers, merges, reports | build a whole packet itself when a builder could |
| `recon` | cheap | finds how things work today, with `file:line` | edit anything |
| `tester` | strong | writes the failing tests for a packet, commits them red | write the fix |
| `builder` | strong | makes the packet's change and its tests pass | merge, or weaken a tester's test |
| `reviewer` | strong | runs the branch to prove it works; GO / NO-GO | edit the branch |

Instructions for each role are in `docs/agents/<role>.md`, shared by both tools. Claude
Code loads `.claude/agents/<role>.md`; Codex loads `.codex/agents/<role>.toml`. Both are
thin wrappers that set the model and point at the shared file.

## Who does what (cost rules)

- **Lead does it alone:** reading a few files, quick lookups, git commands, doc edits
  under about 40 lines, answering {{OWNER}}.
- **`recon`:** any question that needs more than three files read. Never use the strong
  model for a lookup.
- **`builder` alone:** a one-item change the lead can check by running one test.
- **`tester` then `builder`:** a packet with more than one item, or anything {{OWNER}}
  will see.
- **`reviewer`:** a builder branch that changes behaviour {{OWNER}} relies on. Skip it
  for docs-only changes and one-line fixes the lead already tested.
- Never two builders on the same files at once.
- Hand helpers the packet's file path, not pasted text. It keeps the lead's context
  small.

## The loop

1. `recon` checks the facts the packet will rely on.
2. The lead writes `docs/packets/<id>.md` from `docs/packets/TEMPLATE.md`.
3. `tester` commits failing tests (when the rules above call for it).
4. `builder` makes them pass on branch `{{BRANCH_PREFIX}}<slug>` and hands back a short
   report.
5. The lead compares the report with `git diff --stat`. A "done" item with no changed
   file is a question, not a result.
6. `reviewer` proves it by running it (when the rules above call for it).
7. The lead merges, runs the tests, updates `## Now` in `plan.md`, and tells {{OWNER}}
   in a few lines.

## Safety rules

- Helpers that edit work in their own git worktree, never in the main checkout.
- Assume another session is in the repo. Check the branch before staging and before
  pushing. Stage files by path. Never `git stash`, `git reset --hard` or force-push.
- A command that runs the app can write real data. Point it at a copy.
- Anything under `## Ask first` in `AGENTS.md` needs {{OWNER}}'s answer quoted in the
  packet. Without it, the builder stops and asks.

## Models

- Claude Code: the model is set in each `.claude/agents/<role>.md` file (`haiku` for
  recon, `sonnet` for the rest). Change it there.
- Codex: `.codex/config.toml` sets the lead and default helper model; each
  `.codex/agents/<role>.toml` sets its own. If a Codex host cannot pick a named role,
  say so once and pass the TOML's model, effort and instructions to the generic
  spawner yourself.
- Not using one of the tools? Delete its folder (`.claude/agents/` or `.codex/`).
