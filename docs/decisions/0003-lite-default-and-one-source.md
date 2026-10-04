# 0003: A lite default, AGENTS.md as the one source, setup by URL

Date: 2026-10-04. Status: `ACCEPTED`. Amends 0002; does not replace it.

## The ask, in the owner's words

> "assess the repo. the goal is for us to point another repo at it, including a brand new
> repo and to have it perfectly setup for agentic coding with either claude or ChatGPT or
> even with local models if thats what a user wants to. refactor the code as necessary to
> ensure this project meets that goal. first plan with me and ask any questions. ensure
> our .md files are specific, minimal but are targetted towards vibe coding with simple
> lanuage outputs and efficient cloud usage"

## The four questions, and what the owner picked

1. How much structure should a new repo get by default? **"Lite default + Team opt-in"**
2. Which file is the single source of rules? **"AGENTS.md; CLAUDE.md imports it"**. This
   retires the rule that the two files are byte-identical copies.
3. How should another repo pick JumpStarter up? **"Agent reads SETUP.md by URL"**
4. Which local-model setup should we target? **"Generic, AGENTS.md only"**

## What the agent measured before asking

A fresh `init` wrote 23 files (about 100 KB) and left 85 blanks. Every session was told
to read five documents before starting. There was no path for local models, and
setting up another repo required cloning JumpStarter and running Python.

## Choices the agent made under this approval (the owner may overturn any)

- Claude helper models: `haiku` for recon, `sonnet` for tester, builder and reviewer
  (were `sonnet` and `opus`). Reason: "efficient cloud usage", and 0002 answer 8.
- The checkpoint's active-state block becomes `## Now` in `plan.md`. `WISHLIST.md` is
  folded into `plan.md` `## Ideas`. `docs/INTERNALS.md` is renamed `docs/LESSONS.md`.
  `docs/README.md` and `CODEX_NOTES.md` are dropped; the `AGENTS.md` file table replaces
  them.
- Role instructions live once in `docs/agents/<role>.md`; the native files are thin
  wrappers. Packets move to `docs/packets/`. The default helper branch prefix is now
  `agent/` (this repo keeps `claude/`).
- The five playbooks are replaced by `SETUP.md` (setup) and `docs/AGENT_TEAM.md` plus
  the role files (team work). The old text is in git history before this commit.
- Limits: `AGENTS.md` 200 lines (was 400 for `CLAUDE.md`), `## Now` 25, `plan.md` 400
  (was 1,200), log 400 (was 800).
- Older file names are accepted as advisories. The tighter limits apply to them too:
  this repo's own pre-refactor rules file (221 lines) would fail the 200-line limit.

## Revisit if

The owner names a specific local tool to support, or a project finds lite too thin and
team too heavy.
