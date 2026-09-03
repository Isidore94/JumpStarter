# 0001 — The owner's goals and priorities, in their own words

Date: 2026-09-03

Status: `ACCEPTED` — partially answered. The unanswered questions are marked **OPEN**.

**This record is the tie-breaker for every prioritisation call**, until the owner says
otherwise. `CLAUDE.md`'s mandatory read points here; `plan.md` section 1 summarises it.

An **OPEN** answer below is information, not a gap to be filled in by an agent. Do not
guess one. Ask.

## Context

JumpStarter was built on 2026-09-03 in one session, distilled from a mature project that
had been built almost entirely by AI agents over about ten months. The brief for that
session was detailed and is the source of the answers recorded here; the questionnaire
was not put to the owner one question at a time, which is what the playbook asks for.
That is why several answers below are **OPEN** — they were not asked.

## The goals, in priority order

1. **A fresh session in any repo can be told "apply JumpStarter here" and know what to
   do** — for Claude Code and for Codex alike.
2. **Bootstrap a new project with the right control files and agent setup from day one.**
3. **Retrofit an existing repo that grew without them**, without rewriting its history.
4. **The two tools never drift** — `CLAUDE.md` and `AGENTS.md` stay identical by a
   checked rule, not by discipline.
5. **Every template is short enough to read in one sitting.** Bounded reads are the whole
   point.
6. **Keep the shape and the rules; carry no domain specifics** from the project it was
   distilled from.

## The questionnaire

### 1. What must this get right FIRST?

> The two workflows: bootstrap a new project, and retrofit an existing one. Both must
> work for Claude Code (`CLAUDE.md`, `.claude/agents`, `.claude/settings.json`) and for
> Codex (`AGENTS.md`), and the two must never drift.

### 2. How is success scored?

> A fresh Claude Code or Codex session, handed this repo in any project and told "apply
> JumpStarter here", knows what to do. That instruction is in the README with the steps
> it triggers.

The number that would look good while the system failed: green tests. The suite proves
the CLI parses its own fixtures. It says nothing about a real repository — which is why
every gate in `plan.md` is a real repo, not a test.

### 3. What does "right" mean for the main output?

> Distil the lessons — they were each learned by something breaking. Keep the SHAPE and
> the RULES; generalise away the specifics. Every template short enough to read in one
> sitting.

### 4. Which screens, files or reports do you ACTUALLY use?

**OPEN** — not asked. Provisionally: the CLI's own output, and the playbooks.

### 5. Where should the answer appear?

> Chat to the owner is short. Ten lines. Detail lives in commits, docs and handoffs.

### 6. What is the slow part of your work right now?

> Repos that grew without control files, and agents that cannot read their brief so they
> skim it and append to it.

### 7. What is never automated?

> Restarts are the owner's call. Promotion is the owner's call. An item enters the plan
> only when the owner moves it there — ideas are not authorized work.

For JumpStarter's own code this became the hard invariant: **`retrofit` writes nothing.**

### 8. What would make you stop trusting it?

**OPEN** — not asked. The design assumes: a tool that rearranged an existing repo's docs
without being asked, or a control file filled with plausible defaults that were never
measured.

### 9. What does it never do?

> No ticker, trading, UI-framework or warehouse specifics in a template; those belong to
> the project it came from.

Extended in `plan.md` section 1: never generate project content, never edit a repo it was
asked only to audit, never take a third-party dependency in `tools/`.

### 10. How do you want to be told things?

> Chat to me: short. Ten lines at the end: what exists, how to use it on a new repo, how
> to use it on the source project as the first retrofit dry run.

### 11. What do you already do by hand that the system should match?

> The mature project's own control set: the bounded documentation workflow, the
> rules-with-evidence style, the active-state block, the implemented-inventory contract,
> the open-gates table, the archive-at-~1,500-lines rule, the agent team and its loop,
> the packet shape, the permission allow-list.

That is the specification. JumpStarter's templates are that set, generalised.

### 12. What is the one thing you would fix today?

> Tests green, lint clean, one commit per component, and a first `CURRENT_CHECKPOINT.md`
> for JumpStarter itself using its own template — eat the dog food.

## Decision

- Prioritise the two workflows over everything else. When two items compete, the one that
  makes "apply JumpStarter here" work on a **real** repo beats the one that adds a
  feature to the tool.
- **Real-repository evidence** is the headline measure, not test count. Tests stay beside
  it, never replacing it.
- Bounded reads are enforced by the tool, not by discipline: the size limits are in
  `check`, and `check` runs in CI.
- Nothing domain-specific enters `templates/`. That is a hard invariant.

## Consequences

- `plan.md` phase 0 is a real retrofit against a real repo, ahead of any new feature.
- The auto-fixing `doctor` idea is `PERMANENT_NO` in `WISHLIST.md`.
- `init` alone can never produce a `check`-green repo: green means a human answered the
  questions.

## Reopen trigger

Put the twelve questions to the owner properly, one at a time, before phase 1 — the
**OPEN** answers above are the immediate reason. Amend with a new dated record rather
than editing these answers: they are evidence of what was true on 2026-09-03.
