# Paste-ready prompt: verify the 2026-09-03 second pass, and exercise the agent team

Document role: **active runbook.** Hand this to a lead session (Fable 5.1 or whatever
model is orchestrating) running in `c:\Users\Aaron\JumpStarter`. It does two jobs at
once: adversarially verify the work of 2026-09-03's second pass, and put the four-agent
team through a real packet so the owner can see whether the subagent system actually
works.

Paste everything below the line.

---

You are the LEAD session for JumpStarter at `c:\Users\Aaron\JumpStarter`, on branch
`claude/jumpstarter-repo-setup-dn3rof`. A previous session did a large second pass on
2026-09-03 (commits `81f41fd`..`8470012`, nine commits). **Your job is to find what it
got wrong, and then to run the agent team on one real packet so the owner can see the
loop work.** You have two parts and one report at the end.

Before anything: read `CLAUDE.md` in full, the **"Active state at a glance"** block in
`CURRENT_CHECKPOINT.md`, `plan.md` sections 5/6/7 and Phase 1, and
`docs/AGENT_TEAM.md`. Do **not** read `CHANGELOG.md` end to end — search its
`Current implemented inventory`.

Two rules bind you throughout, both from `docs/decisions/0002-owner-goals-asked-properly.md`:

- **Cost is the trust signal.** The owner's stated loss of confidence is "if it used all
  my usage really fast indicating to me that subagents arent being used appropriatly".
  The cheapest correct agent does each job. Use `recon` (cheap model) for lookups. Do
  your own reading, your own `git` commands, and your own small doc edits. Hand agents a
  **file path**, never pasted text.
- **The agent is the reader, not the owner.** The owner reads only your chat message.
  Ten lines, TL;DR in plain terms, depth on request.

**Never write to `c:\Users\Aaron\TradingBotV3` or `c:\Users\Aaron\EveTradingbot`.** They
are other people's live repositories and the previous session only audited them.

---

## PART A — verify the second pass, by reproduction

Do this yourself where it is one command; spawn `recon` where it needs more than three
files read. **Reproduce, do not read.** The previous session's claims are claims until
you re-derive them.

### A1. The baseline numbers

`CURRENT_CHECKPOINT.md` claims, measured on CPython 3.9.25:

| Claim | Verify |
|---|---|
| `pytest tests/ -q` → 49 passed, process exit 0 | run it, **echo the process exit code**, not a piped tail's |
| `ruff check .` → clean, exit 0 | run it |
| `jumpstart.py check .` → 6 checks, no gaps, exit 0 | run it |
| `jumpstart.py retrofit .` → exit 0, 25 checks, 1 advisory | run it |

A 3.9 interpreter is at
`C:\Users\Aaron\AppData\Roaming\uv\python\cpython-3.9-windows-x86_64-none\python.exe`, or
use `uv run --python 3.9 --with pytest python -m pytest tests/ -q`. If any number differs,
that is a finding: **the code is the fact and the doc is the defect.**

### A2. The fail-before-fix claims — this is the one to attack hardest

Eleven tests were added across three commits, each claimed to fail on a named earlier
commit. **One of those claims was already wrong once and had to be corrected in
`db7c987`.** Assume there is another.

Method, per commit: make a scratch worktree at the parent commit, copy the *current*
`tests/test_jumpstart.py` into it, run only the new tests, and confirm each fails.

```
git worktree add --detach <scratch> <parent-sha>
cp tests/test_jumpstart.py <scratch>/tests/test_jumpstart.py
cd <scratch> && uv run --python 3.9 --with pytest python -m pytest tests/ -q -k "<names>"
```

- `3935613` added two tests, claimed to fail at `d610afb`.
- `2c716c7` added nine, claimed to fail at `db7c987`.

**Name any test that passes on the un-fixed code.** A test that cannot fail proves
nothing, and this repo's own principle 6 says so. Remove every worktree you make
(`git worktree remove --force`, then `git worktree prune`) and leave `git status` clean.

### A3. The hard invariants in `plan.md` section 5

Check each one against the code, not the docs:

1. **No third-party dependency in `tools/`.** Grep its imports.
2. **`retrofit` never writes.** There is a test; also run `retrofit` against a scratch
   copy of a real repo and diff before/after yourself.
3. **`init` never overwrites without `--force`.**
4. **No domain-specific content in `templates/`.** Grep `templates/` for anything that
   belongs to the source project: `trading`, `desk`, `ticker`, `Qt`, `PySide`, `warehouse`,
   `avwap`, `trader`, `TradingBot`, `pytest` as a hard-coded command, any model name
   (`opus`, `sonnet`, `fable`, `claude`, `codex`) used as an *assumption about who leads*
   rather than as a filename. **Record 0002 answer 2 makes this stricter than it was:**
   the orchestrating model is not fixed, so a template that assumes one is a defect.
   Note that `.claude/agents/*.md` front matter legitimately carries `model: opus` —
   decide whether that is a violation of the new rule and **say so either way**.
5. **Every rule in `CLAUDE.md` has an entry in `docs/INTERNALS.md`.** Do this by hand
   now: list the bolded rules in `CLAUDE.md`'s "Core rules" section and the `##` headings
   in `docs/INTERNALS.md`, and match them. This is Part B's packet, so a careful count
   here is not wasted.
6. **`sha256(CLAUDE.md) == sha256(AGENTS.md)`.** Also check
   `templates/CLAUDE.md` == `templates/AGENTS.md`.
7. **A template change is mirrored in its playbook and its check in the same commit.**
   Spot-check the four template commits (`b463b4f`, `d610afb`, `3935613`, `2c716c7`)
   with `git show --stat`. A template touched with no playbook beside it is a finding.

### A4. The claims about other repositories

The previous session recorded specific numbers from three audits. Re-derive the two you
can reach, **read-only**:

- `python tools/jumpstart.py retrofit c:\Users\Aaron\TradingBotV3` — the checkpoint says
  3 real gaps: checkpoint 4,587 lines, changelog "Recent changes" 1,549, `CLAUDE.md` 418.
- `python tools/jumpstart.py retrofit c:\Users\Aaron\EveTradingbot` — the checkpoint says
  15 gaps + 2 advisories, and names seven stray root files totalling 1,505 lines.

`wc -l` those files yourself. If a number is wrong, say so.

### A5. Judgement calls to second-guess

These are places the previous session decided something. You may disagree; say why.

- **`PLAN_MAX_LINES = 1200`** was the previous session's suggestion, approved by the
  owner. Is it right? The source project's `plan.md` is 1,835 lines and EveTradingbot's
  is 2,960. A limit nobody can meet gets ignored; a limit that is too loose does nothing.
- **Three findings were downgraded to `ADVISORY`** (gitignored allow-list, active-state
  block under another heading, stray root ledgers). Is any of them actually a gap the
  owner would want CI to fail on?
- **`git stash` moved to the deny-list.** Builders now restore a single file instead.
  Does anything in the templates still assume stashing is available?
- **The `tester` role was added from another project's runbook**, not from a run here.
  Read `templates/.claude/agents/tester.md` and `.claude/agents/tester.md` and say
  whether a real agent could follow them without asking a question.

---

## PART B — put the team through one real packet

This is the subagent test. It uses a **real** owed item, not a toy: one of this repo's
own hard invariants that nothing enforces.

### The work

`plan.md` section 5 says *"Every rule in `CLAUDE.md` has an entry in
`docs/INTERNALS.md`"*. Nothing checks it. `jumpstart.py check` should.

Roughly: a check that extracts the rule names `CLAUDE.md` cites — they are written as
`*(INTERNALS: "Some name")*` — and confirms each has a matching `##` heading in
`docs/INTERNALS.md`. Missing entry → a gap. It must also survive a repo that has no
INTERNALS file and one that has no such citations, without firing.

**Do not build this yourself.** Write the packet, then run the loop.

### The loop, in order

1. **`recon` first.** One question: how does `check` assemble its findings today, where
   would this one attach, what exactly does `CLAUDE.md` cite and what headings does
   `docs/INTERNALS.md` carry, and is any of this already built (search the inventory)?
   `file:line` for every claim.
2. **Write the packet** to `.claude/packets/I1.md`, using
   `templates/.claude/packets/PACKET_TEMPLATE.md` as the shape. **This is also a test of
   that template** — it was reshaped yesterday against three real packets and has never
   been used. Fill its opening paragraph properly, including the **explicit ask-first
   ruling**: decide and write down whether adding a check to `tools/jumpstart.py` is an
   ask-first change, given that the file-scoped rule names "the limit constants in
   `tools/jumpstart.py`" and this is not a limit constant but does change what every
   downstream repo is told. If you judge it ask-first, **stop and ask the owner** rather
   than proceeding.
3. **Spawn `tester`** with the packet path and branch slug `claude/i1-rules-carry-evidence`.
   It writes the failing tests, proves each fails, commits them red.
4. **Check its handoff against the diff** (`git diff --stat`) before believing it.
5. **Spawn `builder`** on the same branch: make the red tests pass without weakening them.
6. **Check that handoff against the diff too.**
7. **Spawn `reviewer`** with the branch, the packet and the builder's handoff. GO / NO-GO.
8. Do **not** merge. Leave the branch pushed and tell the owner it is there.

### What to watch for while doing it — this is the actual test

The owner wants to know whether the subagent system works. Record, as you go:

- **Did each agent read its role file and follow it?** Name a place where it did and a
  place where it did not.
- **Did `tester` genuinely commit red tests?** Check out its commit and run them.
- **Did `builder` weaken any of them?** Diff the test file across the two commits. This is
  the single most important observation in Part B: the whole reason `tester` exists is
  that tests written by the fixer pass on broken code.
- **Did `reviewer` reproduce, or did it read?** Its report should quote numbers it
  re-derived, not the builder's.
- **What prompted for permission?** There is **no `.claude/settings.json` in this repo** —
  it is gitignored and does not exist on this machine. Every agent command will prompt.
  Note which commands prompted; that list is the allow-list the owner should write, and
  producing it is a real output of this exercise.
- **What did it cost?** Roughly: how many agent runs, and could a cheaper agent have done
  any of them? Answer honestly even if the answer is "I over-spent".

---

## What to hand back

Two things.

**A file**, `docs/prompts/VERIFICATION_REPORT_<date>.md`, holding the full detail: every
Part A check with the command and its output, every finding with `file:line`, the Part B
observations, and the proposed allow-list. Reconcile `CURRENT_CHECKPOINT.md`,
`CHANGELOG.md`, `plan.md` and `docs/README.md` per `CLAUDE.md`'s mandatory workflow, and
commit. Three gates green first, by **process** exit code.

**A chat message of at most ten lines** for the owner:

1. Did the numbers hold — yes, or which one did not.
2. Any test that passes on the un-fixed code.
3. Any hard invariant that is actually violated.
4. The one judgement call from A5 you would reverse, if any.
5. Whether the loop worked: tester red → builder green → reviewer GO/NO-GO.
6. Whether the builder weakened a tester's test.
7. What the allow-list should contain.
8. What it cost, and whether that was appropriate.
9. What is still owed.
10. What you did **not** do, stated as plainly as what you did.

If Part A turns up something that makes Part B pointless — a broken baseline, a violated
invariant — **stop after Part A and say so.** Do not spend agent runs on a tree that does
not verify.
