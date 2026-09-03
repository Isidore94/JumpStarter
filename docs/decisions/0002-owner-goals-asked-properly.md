# 0002 — The owner's goals, asked one question at a time

Date: 2026-09-03

Status: `ACCEPTED`

**Amends [`0001`](0001-owner-goals-and-priorities.md); does not replace it.** Record 0001
was written from a detailed brief rather than from answers, and its own reopen trigger
was "put the twelve questions to the owner properly, one at a time, before phase 1".
That was done on 2026-09-03. **This record is now the tie-breaker for every
prioritisation call**; where the two disagree, this one wins, and 0001 stays as evidence
of what was assumed on the morning of the same day.

Every answer below is the owner's own words, unedited. Where an answer changes something
the build had already assumed, that consequence is stated **beneath** the answer and
labelled as the agent's reading — never folded into the quote.

---

## The questionnaire

### 1. What must this get right FIRST?

> "the goal of this project is to have the foundation for future projects to know how to
> setup their .md files to optimize claude and codex."

*Reading.* The deliverable is the foundation itself, not the CLI. The CLI is how the
foundation gets into a repo; it is not the product. Replaces 0001's answer, which named
"the two workflows" — the workflows are the means.

### 2. How is success scored?

> "its just a setup for future projects and for existing projects to be directed to its
> contents to know how to setup up its .md files. right now I am heavily using subagents
> under Fable 5.1 to not burn my usage while still having fable direct things overhead.
> eventually new models will be released maybe even for Codex and then id want codex new
> frontier model to be the orchestrator and conductor."

*Reading.* Two things. Success is *a project being directed here and knowing what to do*.
And **the orchestrator is not fixed**: it is Fable 5.1 with subagents today and may be a
Codex frontier model later. Nothing in `templates/` may assume which model or which tool
is the lead. `docs/AGENT_TEAM.md` already writes the lead's model as "session model" and
the others as "strong" / "cheap" rather than by name; that is now a requirement, not a
style choice.

### 3. What does "right" mean for the main output?

> "i dont know im hoping you can take tradingbotv3 folder and learn what i did there with
> hte claude.md files, agent.md files etc"

*Reading.* The definition is delegated to the evidence: **the source project's own
control set is the specification.** This is the same instruction as 0001 answer 11, now
stated as the answer to "what does right mean". It also means a template change is
justified by pointing at what that project does, and a template that has no counterpart
there needs its own argument.

### 4. Which screens, files or reports do you ACTUALLY use?

> "i dont use any of them but fable 5.1 currently uses everything there"

*Reading.* **This closes 0001's first OPEN answer, and it reframes the project.** The
reader is the agent, not the owner. "Short enough to read in one sitting" means short
enough for a model working inside a context budget. The size limits are therefore not
tidiness — they are the product. And the only surface the owner actually reads is the
chat message, which is why the ten-line rule is a rule.

### 5. Where should the answer appear?

> "i wnat to see it here in the terminal/claude app. additionally all decisons and
> rationals are documented in various places we also have a /docs folder and a
> changelog.md folder so AIs can see what we did before"

*Reading.* Two audiences, two surfaces: the terminal for the owner, `docs/` +
`CHANGELOG.md` + the decision records for the agents. Consistent with 0001.

### 6. What is the slow part of your work right now?

> "having to copy and paste fable prompts to opus."

*Reading.* Sharper than 0001's answer, which named "repos that grew without control
files". The slow part is the **shuttle**: a human moving text between two model windows.
That is exactly what the agent team removes — the lead spawns a builder with a packet
*path*. It also explains why `docs/AGENT_TEAM.md`'s "hand the file path, never the pasted
text" line matters beyond context economy.

### 7. What is never automated?

> "as long as we are following my instructions and limiting scope to what i say,
> everything can be automted"

*Reading, flagged as a change.* 0001 recorded "restarts are the owner's call, promotion
is the owner's call, an item enters the plan only when the owner moves it there" as
things that are never automated. This answer says the boundary is **scope discipline**,
not a list of forbidden verbs: anything inside the stated instruction may be automated.

The conservative reading — used until the owner says otherwise — is that the ask-first
rule, the wishlist rule and "restarts are the owner's call" all survive, because each of
them *is* a scope-limiting device rather than an exception to this answer. But they now
rest on this sentence rather than on a standing prohibition, and an agent that wants to
widen scope must ask, not infer.

### 8. What would make you stop trusting it?

> "if it used all my usage really fast indicating to me that subagents arent being used
> appropriatly"

*Reading.* **This closes 0001's second OPEN answer, and it is the most actionable answer
in this record.** The trust signal is **cost**, and specifically the wrong agent doing a
job the cheap one could do. That makes `docs/AGENT_TEAM.md`'s delegation policy
load-bearing rather than advisory: cheap model for lookups, the lead does its own reading
and its own small doc edits, no reviewer for a docs-only branch, no two builders on the
same files, and packets handed over as file paths so the lead's context stays small.

It also sets the failure mode to watch for: a design that is correct and expensive is a
design this owner will stop trusting.

### 9. What does it never do?

> "i havent ran into this yet"

*Reading.* A genuine non-answer, recorded as one. The product boundary in `plan.md`
section 1 — never generate project content, never edit a repo it was asked only to audit,
never take a third-party dependency, never carry domain specifics — stays in force as
**the design's assumption**, and is labelled as such rather than attributed to the owner.
Re-ask when the owner has hit a case.

### 10. How do you want to be told things?

> "i like details in simple straightforward tl:dr terms and then i can ask questions for a
> deeper summary if needed."

*Reading.* Amends the chat rule slightly. Not "as short as possible": a TL;DR that
carries the substance in plain terms, with depth available on request. Ten lines remains
the budget; the lines must be worth reading.

### 11. What do you already do by hand that this should match?

> "currently i ask fable 5.1 (i want to do this) and then it gives me a prompt for opus to
> implement. I basically want jump starter to have the foundation for this to be automated
> while also having a solid foundation adn paper trail so future models can easily see what
> was done, why, and what lessons were learned etc."

*Reading.* The process to match, in order: the owner states an intent → the lead turns it
into a packet → a builder implements it → the result is written down. The paper trail has
three named parts and they map onto three files that already exist: **what was done** is
`CHANGELOG.md`'s inventory, **why** is `docs/decisions/`, **what was learned** is
`docs/INTERNALS.md`'s incident per rule. Their purpose is now explicitly *for future
models*, which is the same point as answer 4.

### 12. What is the one thing you would fix today?

> "not sure yet this concept is new to me"

*Reading.* Recorded as given. No priority is inferred from it.

---

## Decision

- **The foundation is the product; the CLI serves it.** When a change to `tools/` and a
  change to `templates/` compete, the template wins.
- **Nothing in `templates/` names a model or assumes which tool is the lead.** The
  orchestrator changes; answer 2 says so.
- **The agent is the reader.** Size limits, bounded reads and the active-state block are
  the product, not housekeeping (answer 4).
- **Cost is the trust signal.** The delegation policy in `docs/AGENT_TEAM.md` is
  load-bearing: the cheapest correct agent does each job, and a design that is correct
  and expensive is a failure (answer 8).
- **The paper trail is for future models**, and has three parts: what was done, why, and
  what was learned (answer 11).
- **Scope discipline is the boundary** (answer 7). The ask-first rule and the wishlist
  rule survive as scope-limiting devices; an agent that wants to widen scope asks.
- **Two answers are non-answers and stay that way** (9 and 12). Nothing is inferred from
  them, and `plan.md` section 1's boundary is labelled as the design's assumption.

## Consequences

- `plan.md` section 1's "what the program is for" summary now cites this record.
- The product boundary in `plan.md` section 1 is relabelled: it is the design's
  assumption, not the owner's stated boundary, until answer 9 is real.
- Gate 2 (a new project bootstrapped end to end) is unchanged in priority: it is still the
  only open gate, and answer 3 says the source project's control set is what it must
  reproduce.

## Reopen trigger

Re-ask answers **9** and **12** once the owner has used JumpStarter on a project they did
not build with these templates. Re-ask **2** if the orchestrating model changes. Re-ask
**7** the first time an agent's scope judgement is wrong in a way that costs something.

Amend with a new dated record rather than editing the answers above — they are evidence
of what was true on 2026-09-03.
