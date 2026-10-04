# Set up a repo with JumpStarter

**For an AI agent.** The owner said something like *"set this repo up with
JumpStarter: https://github.com/Isidore94/JumpStarter"*. Follow these steps in order.
Keep chat to one or two short lines per step.

## 1. Get the tool

If you can run `git` and Python 3.9 or newer, clone it **outside** the target repo:

```
git clone --depth 1 https://github.com/Isidore94/JumpStarter.git <temp-dir>/jumpstarter
python <temp-dir>/jumpstarter/tools/jumpstart.py --help
```

Below, `JS` means `python <temp-dir>/jumpstarter/tools/jumpstart.py`. Never commit the
clone into the target repo.

No Python or no git? Read the files under `templates/lite/` (and `templates/team/` if
needed) at <https://github.com/Isidore94/JumpStarter/tree/main/templates>, write them
into the target repo yourself, and replace each `{{NAME}}` blank by hand.

## 2. Look before you write

From the target repo root, run `JS retrofit .`. It only reads and prints.

- No `AGENTS.md` and no `CLAUDE.md`: this is a **new repo**.
- Either one exists: this is an **existing repo**. Read "Existing repo" below first.

Tell the owner what you found in one line.

## 3. Ask the owner, one question at a time

1. The five questions in `templates/lite/docs/decisions/0001-goals.md`. Write the
   answers word for word.
2. "Which AI tools will you use: Claude Code, Codex/ChatGPT, a local model, or more
   than one?"
3. "Do you want helper agents? A cheap model does lookups, and separate agents build
   and review. It saves usage on bigger jobs." Yes means `--profile team`. If they are
   not sure, use the default, `lite`. Team can be added later.

Do not ask what you can read from the repo: the language, the test command, the run
command.

## 4. Install and fill the blanks

```
JS init . --name "<Name>" --description "<one line>" --stack "<languages, main libraries>" \
   --test-cmd "<cmd>" --lint-cmd "<cmd>" --run-cmd "<cmd>" [--profile team] [--owner "<name>"]
```

- Take commands from the repo (`package.json` scripts, `pyproject.toml`, `Makefile`,
  `README`). **Never invent one.** If there is none yet, write that plainly, for example
  `none yet; add a test runner with the first feature`.
- Fill every remaining `{{BLANK}}` from the owner's answers. `plan.md` gets the goal,
  the first step and what is out of scope.
- Team profile:
  - Not using Codex? Delete `.codex/`.
  - Not using Claude Code? Delete `.claude/`.
  - Using Codex? Ask the owner which models to use for the lead, the strong helpers and
    the cheap helper. If they don't know, leave the blanks and say so.
- Local model only: use `lite`. Most tools read `AGENTS.md` on their own. If yours does
  not, point it there (Aider: `aider --read AGENTS.md`).

## 5. Check and hand over

Run `JS check .` until it says `No gaps`. Commit with a clear message. Tell the owner,
in five lines or fewer: what was added, which profile, and anything they must decide.

## Existing repo

- **Never overwrite or delete their files.** `init` skips files that already exist.
  Never use `--force` on a file you have not read.
- Rules only in `CLAUDE.md`: run `JS sync-agents .` first. It moves them into
  `AGENTS.md` and turns `CLAUDE.md` into a one-line import.
- `CLAUDE.md` and `AGENTS.md` both exist and differ: merge `CLAUDE.md`'s rules into
  `AGENTS.md` by hand and keep every rule. Show the owner, then run `JS sync-agents .`.
- An existing `AGENTS.md` stays as it is. Add only the sections from
  `templates/lite/AGENTS.md` that it lacks, written in its own style.
- Extra status, todo or handoff files: fold what is still true into `plan.md`
  (`## Now`, `## Next`). Move the rest to `docs/archive/`. Ask before moving anything.
- A repo on JumpStarter's older layout (`CURRENT_CHECKPOINT.md`, `WISHLIST.md`,
  `docs/INTERNALS.md`) keeps its file names. They pass `check` as advisories. The size
  limits still apply: a rules file over 200 lines needs trimming. Move the story behind
  each rule to `docs/LESSONS.md` and keep one line per rule.

## Which tool reads what

| Tool | Reads |
|---|---|
| Claude Code | `CLAUDE.md`, which imports `AGENTS.md`; helpers in `.claude/agents/` |
| Codex (CLI, IDE, ChatGPT) | `AGENTS.md`; helpers in `.codex/agents/` |
| Local models (Ollama, LM Studio) through Aider, OpenCode, Continue, Cline and similar tools | `AGENTS.md`, pointed at by hand if the tool needs it |
