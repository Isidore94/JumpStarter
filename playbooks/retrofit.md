# Playbook: retrofit an existing repo

Use this when the repo already has history, docs and habits. The goal is to add what is
missing **without rewriting what is there**.

## The one rule

**Archive, do not delete. Never rewrite history.**

An existing repo's docs are evidence of what the project believed and when. A retrofit
that deletes them destroys the record that makes the rules defensible, and it destroys
the owner's trust in the change. Everything that is superseded gets moved under `docs/`
and classified as historical evidence, with a pointer left where it used to be.

Corollary: do not reformat, re-voice or "tidy" documents you are not otherwise changing.
A diff that touches every line hides the three lines that matter.

---

## Step 1 — Audit. Report. Change nothing.

```
python tools/jumpstart.py retrofit /path/to/repo
```

This writes nothing. It prints a gap report over these checks:

| Check | What a gap means |
|---|---|
| Control files present | `CLAUDE.md`, `AGENTS.md`, `plan.md`, `CURRENT_CHECKPOINT.md`, `CHANGELOG.md`, `WISHLIST.md`, `docs/README.md` |
| `CLAUDE.md` == `AGENTS.md` | The two tools are running on different rules |
| Bounded read | `CLAUDE.md` names a *block* to read, not whole files |
| Active state block | One block answers "where are we?", with measured numbers |
| Implemented inventory | A searchable contract, so landed work is not rebuilt |
| Rules carry evidence | An internals file holds the incident behind each rule |
| Docs classified | Every Markdown file is active runbook / reference / historical evidence |
| Owner goals record | The owner's priorities exist in their own words |
| Agent definitions | Claude `.claude/agents/*.md` and Codex `.codex/agents/*.toml` |
| Command allow-list | `.claude/settings.json` |
| Stray ledgers | Root-level files that read like a second roadmap, handoff or status log |
| `.gitignore` rules | `.claude/*` ignored; `.claude/agents/` and `.codex/agents/` tracked |
| Size limits | Checkpoint ≤ 1,500 lines; `plan.md` ≤ 1,200; changelog recent section bounded (or, with no such section, the whole file); `CLAUDE.md` ≤ 400 |

**`ADVISORY` is not `MISSING`.** Two results are advisories, and neither fails the run:

- **the allow-list, when `.gitignore` keeps `.claude/` out.** That file is machine-local
  by design; it cannot be in a checkout. Confirm it on the machine that runs the agents
  instead. This was the one false positive of the first real dry run, against a clone.
- **an active-state block under a different heading** — `## Active item` and the like.
  The block exists; it is simply not findable by the name `CLAUDE.md` sends agents to.
  Either rename it or point the mandatory read at the name it has.
- **stray root ledgers.** A repo is allowed its own file names; this matches on words in
  a filename. It names each file with its line count so a human can judge. One real
  repository had seven of them, 1,505 lines — forbidden by that repo's own `CLAUDE.md`,
  and invisible to the audit until this check existed.

A check that fires on correct work is a check that gets ignored, and it takes the real
findings with it. That is why these are advisories rather than gaps.

Show the report to the owner before you write anything. A retrofit that starts by
editing is a retrofit that gets reverted.

## Step 2 — Fix drift before adding anything

If `CLAUDE.md` and `AGENTS.md` differ, **that is the first thing to fix**, because
everything else you write lands in one of them.

Read both. Merge by hand into `CLAUDE.md` — deliberately, since the divergence usually
contains real rules someone added to only one file — then:

```
python tools/jumpstart.py sync-agents /path/to/repo
```

Commit that alone, so the merge is reviewable.

## Step 3 — Add the active-state block

Do not rewrite the existing checkpoint or status file. Add the block **at the top of the
file the repo already uses** for current state, in the shape from
`templates/CURRENT_CHECKPOINT.md`. If the repo has no such file, create
`CURRENT_CHECKPOINT.md` and point the existing status file at it.

Fill it with numbers **you measure now**:

- run the repo's test command and record the count and the **process** exit code;
- run its lint and record the result;
- record the branch, and what the application actually runs from;
- record what is owed.

If the suite is red, record it red. The first honest baseline is the most valuable
artifact a retrofit produces, and an inherited red suite is not your defect to hide.

## Step 4 — Extract the inventory from what exists

Do not write it from the code. Read the existing changelog, release notes and roadmap,
and pull out one entry per capability that exists **today**, by area. Where the docs and
the code disagree, **the code is the fact** — fix the doc and say so in the commit.

Then bound the file: keep the last two build days under "Recent changes", move the rest
to `docs/CHANGELOG_ARCHIVE_<period>.md`, and leave a pointer. The archive is evidence;
it is never loaded as context.

## Step 5 — Recover the rules and their evidence

Existing repos usually have rules scattered through comments, PR discussions, commit
messages and long doc sections. For each rule you can find:

1. write the one-line binding form in `CLAUDE.md`'s "Core rules";
2. write the incident behind it in `docs/INTERNALS.md`, verbatim where you have the
   source (a commit message, an issue, the owner's words);
3. where you cannot find the incident, write **"Evidence not recovered"** and say where
   you looked.

"Evidence not recovered" is honest and useful: it marks the rules that are least
defensible and most likely to be wrongly "fixed" later. Inventing a plausible incident is
much worse than admitting one is missing.

If a rules section has grown past a few pages, this step is also how it gets bounded:
rules stay in `CLAUDE.md`, reasons move to `docs/INTERNALS.md`, and both files say the
other exists.

## Step 6 — Classify every Markdown file

Write `docs/README.md` listing **every** maintained Markdown file as active runbook,
active reference, decision record, or historical evidence. This is usually where a
retrofit finds three competing roadmaps.

When it does: pick the one that is true, mark the others historical **in place**, and add
a line at the top of each saying what superseded it and when. Do not delete them.

## Step 7 — Ask the owner the questionnaire

`templates/docs/decisions/0001-owner-goals-and-priorities.md`, one question at a time,
verbatim answers. On an existing project this usually reorders the roadmap and retires
finished work — expect that, and record what it retires under "Consequences".

Then add `docs/decisions/0000-template.md` and backfill records for the big choices that
are already load-bearing (the storage model, the framework, the boundary). A backfilled
record says `Date: backfilled <today>` and states what was true when the choice was made.

## Step 8 — Add the agent team

Copy both `.claude/agents/{tester,builder,reviewer,recon}.md` and
`.codex/agents/{tester,builder,reviewer,recon}.toml`, plus `.claude/settings.json`. Fill
the placeholders with this repo's real toolchain, live stores, ask-first files, and
current Codex strong/cheap model choices; add
`docs/AGENT_TEAM.md`, and add the `.gitignore` lines from `templates/.gitignore.snippet`.

The ask-first file list is the part to get right: the files where an edit can change
behaviour that someone depends on. Ask the owner which they are rather than guessing.

## Step 9 — Leave `check` green, and wire it into CI

```
python tools/jumpstart.py check /path/to/repo
```

If a file is already over its size limit, archive it now — the whole retrofit is about
making the mandatory read followable again.

---

## What a retrofit must not do

- **Rewrite history.** No rebase, no amend, no force-push on a shared branch.
- **Delete a document.** Archive it and classify it.
- **Reformat what it is not otherwise changing.**
- **Invent an incident** to justify a rule.
- **Record a baseline it did not measure.**
- **Promote a wishlist item** into the plan. That is the owner's move alone.
- **Land in one commit.** One commit per step, so the owner can revert one piece.
