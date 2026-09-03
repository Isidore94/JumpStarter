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
