# Paste-ready prompt: refresh JumpStarter from the source project

Document role: **active runbook.** A paste-ready brief for a Claude Code (or Codex)
session running **on the owner's PC**, where both this repo and `TradingBotV3` are
readable.

**Why this exists.** JumpStarter's first build was done in a remote container that could
not reach `c:\Users\Aaron\TradingBotV3`. It harvested the patterns from a read-only
GitHub clone instead, which is missing four things that are gitignored or machine-local:
the real packets, `.claude/settings.json`, the worktree layout, and the session memory
notes. This prompt closes that gap and the three open checkpoint gates.

Paste everything between the rules below into a fresh session started **in the
JumpStarter repo**.

---

You are the lead session for **JumpStarter**, a reusable foundation for running software
projects with AI agents. It has two jobs: bootstrap a new project with the right control
files, and retrofit an existing repo that grew without them. It must work for Claude Code
(`CLAUDE.md`, `.claude/agents/`, `.claude/settings.json`) and for Codex (`AGENTS.md`),
and the two must never drift.

Read `CLAUDE.md` in full first, then the "Active state at a glance" block in
`CURRENT_CHECKPOINT.md`, then `PRINCIPLES.md`. They are all short on purpose.

**The source of truth for what "good" looks like is `c:\Users\Aaron\TradingBotV3`.**
Your job is to bring JumpStarter's templates up to date with what that project has
actually learned since, and to close the gates the first build left open.

## What the first build could NOT read, and you can

These are the highest-value reads. Do them before you change anything.

1. **`c:\Users\Aaron\TradingBotV3\.claude\packets\*.md`** — the real build packets
   (R4 and the P/V series are the models). `templates/.claude/packets/PACKET_TEMPLATE.md`
   was reconstructed from a *description* of a packet, not from one. Compare it against
   two or three real ones and fix the shape: what a real packet actually carries, in what
   order, and what it leaves out.
2. **`c:\Users\Aaron\TradingBotV3\.claude\settings.json`** — the real allow-list.
   `templates/.claude/settings.json` was reconstructed from the snippet quoted in
   `docs/AGENT_TEAM.md`. Reconcile: which entries exist in practice, which never got
   used, whether the deny-list JumpStarter added is right.
3. **`C:\Users\Aaron\.claude\projects\c--Users-Aaron-TradingBotV3\memory\*.md`** — the
   session memory notes. Never read. Expect lessons that are not written down anywhere
   else ("reproduce premises before packeting", "three-pass build/review loop", "agents
   share one checkout"). Any lesson there that is not in `PRINCIPLES.md` is the most
   valuable thing you will find today.
4. **`c:\Users\Aaron\TradingBotV3\.claude\worktrees\`** — how worktree isolation is
   actually laid out in practice, versus how `docs/AGENT_TEAM.md` describes it.

Also re-read, at their current state (the clone was pinned at `93732eff`):
`CLAUDE.md`, `CURRENT_CHECKPOINT.md`, `plan.md`, `CHANGELOG.md`, `WISHLIST.md`,
`docs/README.md`, `docs/DESK_INTERNALS.md`, `docs/AGENT_TEAM.md`,
`.claude/agents/{builder,reviewer,recon}.md`, and
`docs/decisions/0016-trader-vision-and-priorities.md`.

## The work, in order

### 1. Recon before you change a template

Spawn `recon` (or do it yourself, read-only) and produce a **diff report**, not a plan:
for each JumpStarter template, what the source project's equivalent now says that the
template does not, and what the template says that the source has since abandoned. Cite
`file:line` on both sides. Report it before editing.

**Anything in `templates/` is ask-first** — those files land in other people's repos.
Bring the diff report to the owner and get a yes per change before editing
`templates/CLAUDE.md`, `templates/plan.md`, `templates/.claude/agents/*.md`, or the limit
constants in `tools/jumpstart.py`.

### 2. Close gate 1 — the retrofit case the audit was written for

`retrofit` has only ever run against a repo that already had a full control set (the pass
path). Run it against:

- `c:\Users\Aaron\TradingBotV3` itself — the **working copy**, not a clone. This alone
  fixes the known false positive: `.claude/settings.json` is machine-local, so a clone
  reports it missing when it is present.
- **at least one repo that grew WITHOUT a control set.** Any older project of the
  owner's. This is the case the audit exists for and has never been tested against.

Record, separately: every finding, every **false positive** (a gap named that is not a
gap), and every **miss** (a real gap the audit did not name). The misses matter more.

`retrofit` writes nothing, by hard invariant. Do not "helpfully" fix the audited repo.

### 3. Fix what the audit gets wrong

Each false positive becomes a test with a fixture built from the shape that produced it.
One is already known and specified in `plan.md` Phase 0 item 2: the allow-list check
cannot tell "absent" from "correctly gitignored", so it should read `.gitignore` and
downgrade to an advisory when `.claude/*` is ignored.

### 4. Close gate 3 — the Python floor

`README.md` and `plan.md` claim Python 3.9+. Everything was measured on 3.11. Either run
the suite and all four subcommands on a real 3.9 interpreter, or change the claim to the
version you actually tested. **Do not leave an unverified version claim in the README.**

### 5. Ask the owner the questionnaire properly

`docs/decisions/0001-owner-goals-and-priorities.md` has **four answers recorded OPEN**
because they were never asked (questions 4 and 8 in particular). Ask all twelve, one at a
time, verbatim answers. That is the record's own reopen trigger. Then reconcile
`plan.md` section 1 with what the owner actually says.

### 6. Reconcile the docs, then commit

Per `CLAUDE.md`'s mandatory workflow: refresh the Active state block with **measured**
numbers, close or update the gate rows, update `CHANGELOG.md`'s inventory, advance
`plan.md`, add a `docs/INTERNALS.md` entry for any new rule with the incident behind it,
update `docs/README.md` if a Markdown file was added, and keep `CLAUDE.md` and `AGENTS.md`
byte-identical (`python tools/jumpstart.py sync-agents .`).

## Hard rules

- **No trading, domain or project-specific content in `templates/`.** Keep the SHAPE and
  the RULES; the specifics belong to TradingBotV3. This is a hard invariant.
- **Every template stays short enough to read in one sitting.** If a harvested pattern
  makes a template longer, the rule goes in the template and the reason goes in
  `docs/INTERNALS.md`.
- **Never write to TradingBotV3.** Read it, audit it, quote it. Nothing else.
- **`retrofit` writes nothing, ever.**
- **Every rule you add to `CLAUDE.md` gets an entry in `docs/INTERNALS.md`** with the
  incident behind it. A rule without its incident gets "fixed" by the next agent.
- Three gates before every commit, checking the **process** exit code, not a piped tail's:
  `python -m pytest tests/ -q` · `ruff check .` · `python tools/jumpstart.py check .`
- One commit per component. Branch `claude/<slug>` off `main`. Push after each commit.
- **Chat to the owner is short.** Ten lines at the end. Detail goes in the commits and
  the docs.

## What to hand back

Ten lines, no more:

```
Harvested: <what the four unreadable sources actually added>
Templates changed: <which, and the owner's yes for each>
Gate 1: <met / still open - what the audit missed on a repo with no control set>
Gate 3: <the Python version actually tested>
Questionnaire: <how many of the four OPEN answers are now real>
Baseline: <n> passed, exit 0 · ruff clean · check no gaps
NOT done: <plainly>
```

State what was NOT done as plainly as what was.
