# Playbook: bootstrap a new project

Use this when the repo has no `CLAUDE.md`/`AGENTS.md` at its root. If it has one, use
[`retrofit.md`](retrofit.md) instead.

Expect this to take one sitting. The questionnaire is the slow part and it is the part
that pays.

---

## Step 1 — Answer the owner questionnaire FIRST

Before any file is written. Open
`templates/docs/decisions/0001-owner-goals-and-priorities.md` and ask its twelve
questions **one at a time**, recording each answer **verbatim**.

Rules for this step:

- Do not batch the questions. An answer often changes the next question.
- Do not paraphrase. A paraphrased answer is an answer you have begun to overwrite.
- "**OPEN** — the owner has not decided" is a valid recorded answer. An invented one is
  a defect that will misdirect every prioritisation call that cites it.
- Do not translate answers into requirements here. That happens in `plan.md`, which
  cites this record.

The answers to questions 1, 2, 4, 5, 7 and 9 decide the roadmap order and the product
boundary. If the owner can only answer a few, take those six first.

## Step 2 — Run `init`

```
python tools/jumpstart.py init /path/to/repo \
    --name MyProject \
    --owner "the owner" \
    --test-cmd "pytest -q" \
    --lint-cmd "ruff check ." \
    --run-cmd "python -m myproject" \
    --main-branch main \
    --branch-prefix "claude/" \
    --codex-strong-model "gpt-5.6-terra" \
    --codex-cheap-model "gpt-5.6-luna"
```

This writes both native role sets (`.claude/agents/` and `.codex/agents/`) and the rest
of the control set, then appends the agent lines to `.gitignore`. It refuses
to overwrite an existing file unless you pass `--force`, and it prints exactly what it
wrote.

Anything you did not supply stays as a `{{PLACEHOLDER}}`. That is deliberate: `check`
reports unfilled placeholders, so a half-written control set cannot quietly ship.

## Step 3 — Define the test and lint commands for real

The commands in `CLAUDE.md` and `.claude/settings.json` must be the ones that actually
run in this repo. Verify each by running it:

- The test command must exit non-zero when a test fails. Check the **process** exit code,
  not a piped tail's — this is the single most common false baseline.
- The lint command must be clean on the empty project, so the first finding is a real
  one.
- If either does not exist yet, building it is Phase 0 in `plan.md`, and the checkpoint
  says so plainly rather than recording a baseline that was never measured.

Then reconcile the allow-list in `.claude/settings.json` with those commands. Keep it
narrow: an entry covering `git *` covers `git reset --hard`.

Two things that only show up once agents are actually running:

- **Spell each command every way your shell and paths write it.** An allow-list entry
  matches the text of the command, not the program it resolves to. The project these
  templates came from ended up with six entries for one test command — Bash and
  PowerShell, forward and back slashes, relative and absolute — because each spelling
  prompted separately. Cheaper to write them all now than to answer prompts for a week.
- **`git stash` belongs in the deny list, not the allow list.** On a checkout that more
  than one session touches, a stash takes the other session's in-flight work with it.
  Builders restore the one file instead: `git checkout <base> -- <path>`.

The real allow-list in that project had no deny list at all. The one in
`templates/.claude/settings.json` is the improvement over it, not a copy of it: an
allow-list carrying `git add *` and `git commit *` with nothing denied is one flag away
from a force-push over someone else's branch.

## Step 4 — Fill the placeholders

Walk each file and replace the `{{TOKENS}}`:

| File | What must be real before the first commit |
|---|---|
| `CLAUDE.md` | description, owner, commands, ask-first files, hard invariants |
| `plan.md` | mission, product boundary (what it **never** does), phases 0–3, definition of done |
| `CURRENT_CHECKPOINT.md` | the Active state block — with measured numbers or an explicit "not measured yet" |
| `CHANGELOG.md` | the inventory areas; it is allowed to be nearly empty on day one |
| `docs/README.md` | every Markdown file in the repo, classified |
| `docs/decisions/0001-...` | the verbatim answers from step 1 |
| `.claude/agents/*.md` and `.codex/agents/*.toml` | project name, toolchain path, live stores, ask-first files; current Codex strong/cheap model choices |

`python tools/jumpstart.py check /path/to/repo` lists any token you missed.

## Step 5 — Write the first real checkpoint

The Active state block, with numbers you actually measured today:

- the branch, and what is on it;
- the one active item, from `plan.md` phase 0;
- the baseline: the test command, the count, the **process exit code**, the duration, the
  date, and the commit it was measured on;
- the lint result;
- what the application actually runs from (source, or which build, and whether a rebuild
  is owed);
- whether a restart is owed.

If nothing has been measured yet because there is nothing to measure, say exactly that.
An honest empty baseline is state; an optimistic one is a lie the next agent will act on.

## Step 6 — Seed `docs/INTERNALS.md` with the first rule

Do not wait for an incident. Write the first entry for the rule you already know matters
in this project — usually the product boundary, or the thing that must never be
automated (questionnaire answers 7 and 9). The entry names the rule, what happens if it
is broken, and its reopen trigger.

A rule in `CLAUDE.md` with no entry here is a draft.

## Step 7 — Commit the control set

One commit, its own commit, before any feature work:

```
git add CLAUDE.md AGENTS.md plan.md CURRENT_CHECKPOINT.md CHANGELOG.md \
        WISHLIST.md docs/ .claude/agents/ .codex/agents/ .claude/settings.json .gitignore
git commit -m "Add the control set: bounded read, active state, inventory, agent team"
```

Verify `.gitignore` before committing: `.claude/agents/` and `.codex/agents/` tracked,
the rest of `.claude/`
ignored, and `.claude/settings.json` only tracked if this project wants it shared.

## Step 8 — Leave `check` green

```
python tools/jumpstart.py check /path/to/repo
```

Wire it into CI on day one. The rules it enforces — sizes bounded, `CLAUDE.md` ==
`AGENTS.md`, no unfilled placeholders — are cheap now and expensive to retrofit once
three agents have appended to the files.

---

## The first packet

Do not start feature work from a conversation. Write it as a packet
(`playbooks/packet-writing.md`), even if you are the only one who will build it. The
packet is what the review reproduces and what the checkpoint's gate refers back to.
