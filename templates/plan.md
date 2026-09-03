# {{PROJECT}} remaining roadmap

Authoritative for: **what is not built yet, in what order, and what gates it.**
What exists: [`CHANGELOG.md`](CHANGELOG.md). Where we are right now:
[`CURRENT_CHECKPOINT.md`](CURRENT_CHECKPOINT.md).

Only unfinished work belongs in this file.

## 1. Mission and product boundary

{{PROJECT}} is {{ONE_LINE_DESCRIPTION}}.

It does: {{IN_SCOPE}}.

It never does: {{OUT_OF_SCOPE}}. That is a boundary, not a backlog item — work that
crosses it is refused, not deferred.

**What the program is for, in {{OWNER}}'s words.** The record is
[`docs/decisions/0001-owner-goals-and-priorities.md`](docs/decisions/0001-owner-goals-and-priorities.md)
and it is the tie-breaker for every prioritisation call. Summarise its short form here
in a few numbered lines, and update this summary whenever that record is amended.

## 2. Status vocabulary

These labels must not be collapsed:

| Status | Meaning | Production authority |
|---|---|---|
| `PLANNED` | Designed; no implementation exists. | None |
| `IMPLEMENTED` | Code exists. | None by itself |
| `GREEN` | Deterministic tests pass. | Only existing champion behaviour |
| `SHADOW` | Runs on live inputs but cannot affect production decisions. | None |
| `VALIDATED` | Passed the documented real-world or operational checks. | None by itself |
| `ADVISORY` | Visible as labelled decision support. | No gating or ranking authority |
| `PROMOTED` | Explicitly approved as the production champion, with rollback. | Yes |
| `RETIRED` | Intentionally disabled or replaced. | None |

Current code and test status belongs in `CHANGELOG.md`. The current branch and exact
test counts belong in `CURRENT_CHECKPOINT.md`.

## 3. Current-state summary

As of {{DATE}}: {{CURRENT_STATE}}

Keep this to a handful of lines. The measured version lives in the checkpoint's
"Active state at a glance" block.

## 4. Authority and change control

When documents disagree, use this order:

1. this roadmap, for remaining-work order, invariants and promotion policy;
2. accepted decision records under `docs/decisions/`;
3. active implementation specifications listed in `docs/README.md`;
4. historical reviews, handoffs, proposals and superseded plans.

Do not infer current status from a historical plan; reconcile it through `CHANGELOG.md`
and this file. `WISHLIST.md` is deliberately outside the authority chain: it never
authorizes implementation. Only an explicit decision by {{OWNER}} promotes an item here.

## 5. Non-negotiable invariants

These bind every packet. Violating one is a defect, not a trade-off. Each should also
appear in `CLAUDE.md`'s "Hard invariants" in the same words.

- Uncertainty never deletes: missing data is uncertainty, never confirmation.
- One component owns each timer, thread, job and mutable shared output; a failed publish
  never destroys the last verified artifact.
- No behaviour change to {{CRITICAL_AREA}} without golden fixtures first.
- Every statistic carries its sample size and is not shown as a verdict below its floor.
- {{ADD_YOUR_OWN}}

## 6. Validation program

Green automated tests do not satisfy a gate. A **gate** is a named real-world check,
owed by a specific item, that a human or a scheduled run performs and records.

For the first real run of a new build, record:

- branch and commit, environment, versions, configuration and date;
- the full test exit code, lint result, and any packaging or build self-test;
- the real artifacts produced, and their counts;
- behaviour under failure and restart;
- every failure or unknown as evidence, without rewriting the acceptance result.

Open gates live in `CURRENT_CHECKPOINT.md`'s gates table, newest first, each naming the
dated entry that describes it.

## 7. Promotion ladder

Promotion is a separate decision from implementation and from validation. Every
challenger requires, in order:

1. a versioned configuration and a stable identity;
2. golden/replay fixtures and a declared evidence window **frozen before inspection**;
3. complete coverage and data-quality accounting;
4. comparison with the active champion on the same inputs and outcome definition;
5. representative real sessions across the conditions that matter;
6. explicit success, non-inferiority and rollback criteria;
7. a bounded canary and a one-switch rollback that does not require a code revert;
8. explicit approval by {{OWNER}}, recorded in the revision history.

Reading a cell of the evidence window before it closes is a refusal, not a check —
including by the agent that built it, and including if an early cell looks good.

## 8. Specifications retained under `docs/`

This roadmap owns priority and status. Detailed contracts live under `docs/` and are
classified in `docs/README.md`. Their own phase lists never reorder section 12.

## 12. Remaining work, in execution order

The phases below are dependency order, not a menu. `CURRENT_CHECKPOINT.md` names the one
active item. Finish it before moving down the list unless {{OWNER}} explicitly redirects.

| Order | Phase | Plain-English outcome |
|---:|---|---|
| **0 — NOW** | {{PHASE_0}} | {{PHASE_0_OUTCOME}} |
| **1 — NEXT** | {{PHASE_1}} | {{PHASE_1_OUTCOME}} |
| **2** | {{PHASE_2}} | {{PHASE_2_OUTCOME}} |
| **3 — LATER** | {{PHASE_3}} | {{PHASE_3_OUTCOME}} |

### Phase 0 — NOW: {{PHASE_0}}

State the outcome in one sentence, then the numbered items. Each item names: what
changes, the test that must fail first, the invariants that bind it, the docs to
reconcile, and the gate it owes.

1. {{ITEM}} — *status:* `PLANNED`. Gate: {{GATE}}.

### Phase 1 — NEXT: {{PHASE_1}}

1. {{ITEM}}

## 13. Definition of done

The roadmap is complete when:

1. {{DONE_1}};
2. {{DONE_2}};
3. every rule in `CLAUDE.md` has an evidence entry in `docs/INTERNALS.md`;
4. the supported test, lint and build gates are green and recorded in the checkpoint;
5. no gate in the checkpoint's table is open;
6. {{PROJECT}} still performs no {{OUT_OF_SCOPE}}.
