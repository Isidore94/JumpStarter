# Playbook: the build/review loop

The loop the lead session runs, with the exact prompts it gives each agent.

```
recon → packet → build → review-by-reproduction → fix → integrate → owner restarts
```

Three passes over the same work: recon verifies the premises, the builder proves the fix
fails first, the reviewer proves it again by running it. Each pass exists because the
previous one has been observed to be wrong.

---

## 0. What the lead does and does not do

The lead is the session the owner talks to. It asks the owner, writes packets, spawns the
others, merges, runs the full suite and reconciles the ledgers.

It does **not**: build a packet itself when a builder could; review its own build; switch
the main checkout's branch while the application runs from it; restart the application
without the owner's word.

---

## 1. Recon — verify the premises

Spawn `recon` before writing a packet. Cheap model, read-only.

> **Prompt to `recon`:**
> Answer this one question about how the code and the real data behave today, with
> `file:line` for every claim about code.
>
> **Question:** does `<feature>` exist, where is it implemented, and what does the real
> `<store/file>` contain for it?
>
> Specifically:
> 1. Where is `<behaviour>` implemented today? Cite `file:line`.
> 2. Does `<the thing I plan to add>` already exist anywhere? Search `<paths>` and
>    `CHANGELOG.md`'s "Current implemented inventory". "Not found" is a valid answer.
> 3. What does the real data show — how many rows, what do the fields actually contain,
>    are the keys present-and-empty or absent on old records?
> 4. What would break if `<the planned change>` landed? Name the invariant.
>
> Do not propose a design. Report: what exists (`file:line`), what the data shows
> (counts, dates, examples), the gap, and open questions.

**Rule:** a premise you did not verify is a premise that will be refuted at the most
expensive moment — by the builder, halfway through.

## 2. Packet — write it from the verified premises

See [`packet-writing.md`](packet-writing.md). Shape:
`.claude/packets/PACKET_TEMPLATE.md`.

The lead writes it; it is never dictated by the builder. If recon refuted a premise, the
packet changes before it is handed over, not after.

## 3. Build — one packet, one builder, one branch

> **Prompt to `builder`:**
> Build packet `<ID>` at `.claude/packets/<ID>.md`, on branch
> `<prefix><slug>` off `<main>`, in your own worktree.
>
> Read `docs/AGENT_TEAM.md`, then `CLAUDE.md` in full, then the packet.
>
> Before your first edit, reply with: the item, what already exists (from your search of
> `CHANGELOG.md`'s inventory), what remains, the files you will touch, the tests you will
> write, and whether the ask-first rule applies to any of them.
>
> Build exactly the packet — nothing wider. Where the code disagrees with the packet, the
> code is the fact: report it, do not force the change.
>
> Every behaviour change ships with a test proven to fail on the un-fixed code: restore
> the pre-change file, run the test, watch it fail, restore. Say so in the commit message.
>
> Reconcile the docs on your branch. Run the gates and report the process exit codes.
> Never merge; never delete a branch.
>
> Finish with the handoff block from your role file, nothing else.

**Parallelism.** One builder per packet. Two packets that touch the same files run one
after the other — parallel branches over shared files cost more in conflict resolution
than they save. Two packets in genuinely disjoint areas may run at once.

## 4. Review by reproduction

Never skipped for a packet that touches evidence, numbers, or a user-facing surface.
Skipped only for a docs-only branch.

> **Prompt to `reviewer`:**
> Review branch `<branch>` against packet `.claude/packets/<ID>.md` and the builder's
> handoff below. In your own worktree. Never commit, push or leave the branch modified.
>
> **Find what is wrong by running it, not by reading it.**
>
> 1. For every numbered item: delivered / partial / missing, with `file:line`.
> 2. Run the new and changed tests; report counts.
> 3. Prove fail-before-fix: restore each implementation file to `<base>`, run the new
>    tests, confirm they FAIL, restore. Name any test that passes on the un-fixed code.
> 4. Re-derive every number the builder quoted. Reproduce claims about real data against
>    COPIES of it.
> 5. Invariant scan, including the eight traps in
>    `playbooks/review-by-reproduction.md`.
> 6. Ask-first: if the branch edits an ask-first file, find the record that the owner
>    answered. No record is a blocker to NAME, not to decide.
> 7. Docs: checkpoint block, gate row, inventory, plan, `CLAUDE.md` == `AGENTS.md`
>    (sha256), internals entry for any new rule.
> 8. Lint.
>
> Finish with the GO / NO-GO block from your role file, nothing else. Blockers separated
> from advisories; a clean branch gets "BLOCKERS: none". Never pad.
>
> **Builder's handoff:**
> <paste it verbatim>

## 5. Fix round

Blockers go back as a **small fix packet on the same branch**. Continue the same builder
where you can — its context is the cheapest thing you own. A fresh builder gets the
reviewer's blockers **verbatim**, not summarised.

Advisories are batched into a later packet. Do not let an advisory grow the current
branch: a branch that keeps widening never gets merged.

Re-review after a fix round that touched behaviour. Two rounds is normal; a third means
the packet's premises were wrong, and the answer is a new recon, not a third fix.

## 6. Integrate

The lead merges, **in a scratch worktree**, never in the checkout the application runs
from. Merge order is packet order.

Then, on the merged tree:

1. the full test suite — record count and **process** exit code;
2. lint;
3. any build or packaging self-test the project has;
4. refresh the "Active state at a glance" block with those numbers and the commit;
5. add each packet's gate to the gates table.

A suite run under a condition that stands tests down is not a baseline. If the project
has such a condition, probe for it before the run and say in the checkpoint that it was
clear.

## 7. The owner restarts

A merged commit reaches the owner only at the next restart, and **the restart is their
call**. The lead says, in one line, that it is owed and why.

Then the gate is owed: a real-world observation, by a human or a scheduled run, recorded
against its row. Automated green does not close a gate.

---

## Reporting to the owner

Ten lines at most, at the end of a loop:

```
Built: <packet> — <one line>.
Not built: <what, and why>.
Review: GO / NO-GO, <n> blockers fixed.
Baseline: <n> passed, exit 0, lint clean, on <commit>.
Owed: <gate>. Restart owed: yes/no.
```

Detail lives in the commits, the docs and the handoffs. If the owner wants more, they
will ask — and it will already be written down.
