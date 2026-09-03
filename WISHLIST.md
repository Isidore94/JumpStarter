# JumpStarter wishlist

Last reconciled: **2026-09-03**

This file is the owner's parking lot for ideas that may be useful but are **not
authorized build work**. The authoritative implementation order is `plan.md`.

## Rules

- An AI may suggest, clarify, compare or estimate a wishlist item.
- **An AI must not implement an item from this file.**
- Only the owner may promote an item into `plan.md`.
- Promotion requires a defined outcome, prerequisites, scope, invariants, tests and an
  insertion point in the roadmap.
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
| `jumpstart archive` — move a checkpoint's old entries out automatically | `CANDIDATE` | Where is the boundary? "Older than the oldest open gate" needs the tool to parse the gates table, and a wrong cut silently loses the record |
| A `--json` flag on `retrofit` for CI consumption | `CANDIDATE` | Which consumer? Exit codes already work in CI |
| Per-project overrides for the size limits | `CANDIDATE` | A limit a project can raise is a limit that gets raised instead of the file being archived. What stops that? |
| Templates for other agent tools beyond Claude Code and Codex | `TRIGGERED_LATER` | Only if the owner actually uses one |
| A `jumpstart doctor` that fixes gaps automatically | `PERMANENT_NO` | `retrofit` writes nothing, by invariant. Auto-fixing an existing repo's docs is exactly the retrofit that gets reverted |
| Vendoring JumpStarter into every project as a submodule | `CANDIDATE` | Needs the owner's decision on distribution — `plan.md` phase 2 item 2 |

## Already promoted

Nothing yet.
