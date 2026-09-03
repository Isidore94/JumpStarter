# Playbook: writing a packet

A packet is the unit of authorized work: a numbered specification the builder implements
exactly, the reviewer reproduces exactly, and the checkpoint's gate refers back to.

Shape: `templates/.claude/packets/PACKET_TEMPLATE.md`.

---

## The rule that makes a packet worth writing

**Verify the premises in the code before you write it.** Everything downstream of an
unverified premise is wasted work, and the waste is discovered at the most expensive
moment — by the builder, halfway through, or by the reviewer, after the merge.

This is not theoretical. A packet has been handed over containing two claims that were
refuted at code level by the builder: the code described did not exist in that form.

So: recon first, `file:line` for every claim about code, real counts for every claim
about data, and the date the lines were read. Then write.

## What goes in

### 1. The owner's decision, quoted

Verbatim, with the date and the source. Not "the owner wants better X" — their words.

A packet that cannot quote a decision for a change to an ask-first file **stops at that
item**, and the item becomes a question in the handoff rather than a change.

### 2. The premises, with evidence

A table. Each row is a fact the packet is built on and the evidence for it:

- code: `path:line`, read on a stated date;
- absence: "not found — searched `<paths>` and the inventory". Absence is a premise too,
  and it is the one most often assumed;
- data: the count, the store, the date it was read.

### 3. The inventory check

State which terms you searched in `CHANGELOG.md`'s "Current implemented inventory" and
what already exists. This is how landed work stops being rebuilt, and it takes a minute.

### 4. One block per item

Each numbered item carries:

- **Change** — exactly what to do, in one or two sentences, naming the file and function.
- **Where** — `path:line` and what is there now.
- **Test that must fail first** — the test path and name, what it asserts, and the
  failure it must produce on the un-fixed code. Without this the item is a suggestion.
- **Invariants that bind** — which of the plan's section 5 invariants this item is near.
- **Out of scope for this item** — what not to touch. A packet that does not say this
  gets a wider diff than it asked for.

### 5. Docs to reconcile

Name them. The builder does this on the same branch, not in a follow-up.

### 6. The gate

**What must be observed in the real world** for this to count as validated — not a test.
Who observes it, on what run, and exactly what they must see. It becomes a row in the
checkpoint's gates table.

If an item has no meaningful gate, say "no gate" and why. An invented gate nobody can
perform is worse than none: it sits open forever and drains the table of meaning.

### 7. What is not in this packet

State plainly what was considered and deliberately left out, so it is not rediscovered
later as a gap and rebuilt as a surprise.

---

## Sizing

One packet is one branch, one builder, one review. If it does not fit in one review, it
is two packets.

Signs a packet is too big: more than about six items; items that cannot be tested
independently; a mix of areas that would need two different reviewers; "and while we're
in there".

Signs it is too small: no test can fail first because nothing observable changes. That is
a chore, not a packet — batch it.

## Sequencing

Two packets that touch the same files are sequenced, not parallelised. Order them so the
one that changes the shared file lands first, and say so.

## What a packet must never do

- **Assume.** Every claim has evidence or it is removed.
- **Say "improve" or "clean up".** Name the change and the observable difference.
- **Bundle an unauthorized change** with an authorized one because it is nearby.
- **Set a threshold without naming where the number came from.** A magic number with no
  source in the internals file is one an agent will "tune" later.
- **Promote a wishlist item.** Only the owner does that.
- **Skip the gate** because the tests are green. Green tests are not a gate.
