# {{PROJECT}} internals — the incident behind every rule

Document role: **active reference.** Verbatim source text for the `Core rules` in
[`CLAUDE.md`](../CLAUDE.md).

**`CLAUDE.md` keeps the rule; this file keeps the reason.** The rules are binding from
`CLAUDE.md` alone — nothing here is optional context that weakens them. What is here is
why each rule exists: the incident, the measurements and {{OWNER}}'s own words, kept
unchanged.

**Read the matching entry here before you change the behaviour a rule governs**, and
whenever the one-line form in `CLAUDE.md` is not enough to act safely.

**A rule with no entry here is a draft.** A rule whose entry has been lost gets "fixed"
by the next agent who finds it inconvenient, and the incident happens again.

If you change a rule, change it in both places, in the same commit.

---

## Native role definitions are adapted, never mechanically converted

**The rule:** Claude Code and Codex keep one shared rules source and one packet format,
but each harness gets a native role definition. Changes to
`templates/.codex/agents/*.toml` are ask-first and must preserve the Claude role's scope,
branch convention, safety clauses, and handoff interface.

**What happened.** A global Claude-to-Codex text substitution produced plausible TOML
that was operationally unsafe. It turned the parity check into `AGENTS.md == AGENTS.md`,
invented a `Codex/<slug>` branch family instead of retaining the configured branch
prefix, and changed ask-first paths to names that did not exist. Familiar wording hid
the damaged instructions.

**What is deliberately NOT done.** The `.claude/agents/*.md` files and their model
routing remain independent and unchanged. Native Codex roles preserve their semantics;
they are not global search-and-replace copies.

**Reopen trigger.** Revisit the native TOML only when Codex changes its agent schema or
the owner changes the strong/cheap routing. Never update it with global substitution.

---

## {{RULE_NAME}} ({{DATE}}, {{WHAT_PROMPTED_IT}})

**The rule, as it appears in `CLAUDE.md`:** {{THE_ONE_LINE}}

**What happened.** The incident, in the order it happened. Include what was believed at
the time and why that belief was reasonable — a rule that reads as obvious in hindsight
is the kind that gets deleted.

**What was measured.** The numbers. Sizes, durations, counts, exit codes, dates. If a
number is the reason for a threshold, name it here and nowhere else, so the threshold
has exactly one source.

**{{OWNER}}'s words, verbatim.** Quote rather than paraphrase. A paraphrased decision is
a decision that has already begun to drift.

**What is deliberately NOT done, and why.** The alternatives that were considered and
rejected, so they are not re-proposed as discoveries.

**Reopen trigger.** The condition under which this rule should be revisited. Without
one, a rule outlives its reason and nobody can tell.

---

<!-- Add one entry per rule. Newest first, or grouped by area — pick one and keep it. -->

The three entries below arrive with the templates. They are the evidence for the three
rules `CLAUDE.md` ships with that were not learned in this project. Keep them, or delete
the rule with them — never the entry alone.

---

## Another session is in this repository (inherited with the templates)

**The rule, as it appears in `CLAUDE.md`:** *Assume another session is in this
repository. Verify the branch immediately before staging and immediately before pushing;
stage explicitly by path, never `git add -A`; never `git stash`; after committing,
confirm your work landed.*

**What happened.** Several agent sessions ran against one working tree at the same time.
In a single afternoon: one commit carried two unrelated packets; a second session's
commit swallowed a third session's uncommitted code; and a pushed branch was deleted
underneath the session that had created it, while its work reached the trunk by another
route. Staging explicit paths was not enough protection — another session can switch
`HEAD`, commit, or delete a branch between your edits and your push.

**What was measured.** Three collisions, one afternoon, three sessions.

**What is deliberately NOT done, and why.** `git stash` is not used to get a clean test
count: it stashes the other session's in-flight work too. Restore the single file with
`git checkout <base> -- <path>` instead. A full-suite test count is not isolated either
— report the number measured and say which part is yours.

**Reopen trigger.** One session per checkout, enforced rather than assumed.

---

## The control file itself goes stale (inherited with the templates)

**The rule, as it appears in `CLAUDE.md`:** *This file is one of those docs. A line in
`CLAUDE.md` that the code contradicts is not authority; leave a dated note saying which
line is wrong and what the code does instead.*

**What happened.** A `CLAUDE.md` bullet described a screen layout that had been changed
the same day it was written, on the owner's own instruction. The wrong line survived
because nothing reads a control file looking for defects — it is read for authority. A
week later a design proposal built one of its three decisions on that line: a refuted
premise, from the file every session trusts most.

**What was measured.** One stale bullet; one downstream proposal; the source disagreed
at a single, findable call site the whole time.

**What is deliberately NOT done, and why.** The stale line is not silently deleted by
whoever notices. It is corrected, or tombstoned with a dated note saying what the code
actually does, and the owner is told. A silent fix leaves nobody able to tell whether the
old line was wrong or the new behaviour was unauthorised.

**Reopen trigger.** None — this one holds as long as a file is read for authority.

---

## A suite run under a known condition is not a baseline (inherited with the templates)

**The rule, as it appears in `CLAUDE.md`:** *When the suite is NOT a baseline:
{{WHEN_THE_SUITE_IS_NOT_A_BASELINE}}. Probe that condition before quoting a number.*

**What happened.** A nightly job held a writer lock from about 22:00 until it finished —
six hours on one occasion. While it was held, a set of tests stood down. Suites run in
that window printed a smaller number that looked like a pass, and the checkpoint recorded
it as the baseline.

**What was measured.** 32 tests stood down; one run of six hours.

**What is deliberately NOT done, and why.** The tests are not deleted or marked expected
failures. They are correct; the window is the problem. The probe is cheap and the wait is
honest.

**Reopen trigger.** The blocking condition is removed, or made not to block.
