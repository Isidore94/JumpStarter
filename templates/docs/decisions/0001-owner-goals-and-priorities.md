# 0001 — {{OWNER}}'s goals and priorities, in their own words

Date: {{DATE}}

Status: `ACCEPTED`

**This record is the tie-breaker for every prioritisation call**, until {{OWNER}} says
otherwise. `CLAUDE.md`'s mandatory read points here; `plan.md` section 1 summarises it.

It exists because a build grows faster than the statement of what it is for. Features
that are correct, tested and delivered onto surfaces the owner never opens are a real
and common outcome — this record is how that is caught early.

---

## How to fill this in

**Ask one question at a time. Record the answer verbatim.** An answer you paraphrase is
an answer you have already begun to overwrite. If an answer raises a new question, ask
it and record that too. If {{OWNER}} does not have an answer yet, write
"**OPEN** — {{OWNER}} has not decided" rather than a guess; an open question is
information, an invented answer is a defect.

Do not summarise the answers into requirements in this file. That translation happens in
`plan.md`, and it cites this record.

---

## Context

{{WHAT_PROMPTED_THIS_RECORD}} — what the project looked like on the day these questions
were asked, and what was unclear.

## The goals, in priority order

{{OWNER}}'s goals, numbered, highest first. One line each, in their words.

1. {{GOAL}}
2. {{GOAL}}

## The questionnaire

### 1. What must this get right FIRST?

If only one thing worked well, what would it be? What comes second?

> {{ANSWER}}

### 2. How is success scored?

When the system does its job well, what number or observation shows it? What number
would look good while the system was actually failing?

> {{ANSWER}}

### 3. What does "right" mean for the main output?

Define it concretely enough to measure. If two definitions compete, which one leads and
which one sits beside it?

> {{ANSWER}}

### 4. Which screens, files or reports do you ACTUALLY use?

Which ones do you open every day? Which do you never open? Anything you would use if it
were better, and what would have to change?

> {{ANSWER}}

### 5. Where should the answer appear?

When the system works something out, where do you want to see it — and where would you
never look? (Whatever you must see may not live only in the place you never open.)

> {{ANSWER}}

### 6. What is the slow part of your work right now?

The part that takes the most of your time and attention for the least value.

> {{ANSWER}}

### 7. What is never automated?

What must always be your call, no matter how confident the system becomes? What may it
do on its own?

> {{ANSWER}}

### 8. What would make you stop trusting it?

The single failure that would cost the system your confidence, and what it should do
instead when it is unsure.

> {{ANSWER}}

### 9. What does it never do?

The product boundary, in your words. Not "not yet" — never.

> {{ANSWER}}

### 10. How do you want to be told things?

How much detail in a message; what you want to be interrupted for; what should wait for
a summary.

> {{ANSWER}}

### 11. What do you already do by hand that the system should match?

Your own process, in enough detail to implement: the steps, the thresholds, the order.
The system must match it before it is compared against it.

> {{ANSWER}}

### 12. What is the one thing you would fix today?

> {{ANSWER}}

## Decision

- Prioritise work in the order of the goals above, and within a goal by the answer that
  names it. When two items compete, {{THE_TIE_BREAKER_FROM_THE_ANSWERS}}.
- {{HEADLINE_MEASURE}} is the headline statistic on every {{OWNER}}-facing surface; the
  others stay beside it, never replacing it.
- {{WHERE_THE_ANSWER_LIVES}}. Nothing {{OWNER}} must see may live only in a surface they
  never open.
- Unused surfaces are candidates for removal or folding, **after {{OWNER}} confirms each
  one**; this record does not authorise their removal.

## Consequences

- {{WHAT_THIS_REORDERS_IN_THE_PLAN}}
- {{WHAT_THIS_RETIRES}}
- {{WHAT_NEW_WORK_THIS_CREATES}}

## Reopen trigger

Re-ask the questionnaire when {{OWNER}}'s use of the system changes materially, or at
{{CADENCE}}. Amend with a new dated record rather than editing the answers above —
the answers are evidence of what was true on {{DATE}}.
