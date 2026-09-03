# {{PROJECT}} wishlist

Last reconciled: **{{DATE}}**

This file is {{OWNER}}'s parking lot for ideas that may be useful but are **not
authorized build work**. The authoritative implementation order is `plan.md`.

## Rules

- An AI may suggest, clarify, compare or estimate a wishlist item.
- **An AI must not implement an item from this file.**
- Only {{OWNER}} may promote an item into `plan.md`.
- Promotion requires a defined user outcome, prerequisites, scope, invariants, tests and
  an insertion point in the roadmap.
- Moving an item to the roadmap changes its status here to `ROADMAP`; it is not deleted,
  so the decision stays visible.
- Retired ideas stay recorded to prevent accidental resurrection.

Statuses:

| Status | Meaning |
|---|---|
| `ROADMAP` | Accepted and ordered in `plan.md`; follow the roadmap, not this file |
| `CANDIDATE` | Worth discussing; not authorized |
| `TRIGGERED_LATER` | Consider only if the named condition occurs |
| `RETIRED` | Deliberately abandoned |
| `PERMANENT_NO` | Conflicts with the product boundary or a hard invariant |

## Ideas

| Idea | Status | Note |
|---|---|---|
| {{IDEA}} | `CANDIDATE` | {{THE_ONE_QUESTION_THAT_BLOCKS_IT}} |

## Already promoted

Shown here only so the decision stays visible. Their real order and requirements live in
`plan.md`.

| Idea | Status | Roadmap location |
|---|---|---|
| {{IDEA}} | `ROADMAP` | {{PHASE}} |
