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

The order below is the order a real packet reads in. It was checked against packets
written by a lead session that had already run this loop for months: the ceremony an
earlier draft of this playbook asked for — a whole section for the owner's quote, another
for the inventory search — is not what those packets do. The quote is one clause of the
opening paragraph, and the inventory search moved into the builder's house rules, where
it happens every time instead of being restated every packet.

### 1. The opening paragraph carries the authorization

One paragraph, before anything else, holding all of:

- **who authorized it, on what date, in their own words** — a clause, not a section. A
  packet that cannot quote a decision for a change to an ask-first file **stops at that
  item**, and the item becomes a question in the handoff rather than a change;
- **the base sha** the line numbers were read against, and the branch to build on;
- **the governing documents** — the specs and decision records this packet must not
  contradict;
- **the line-number stamp**: read on this date, against this sha, verify each before
  editing, and **if the code disagrees with the packet, the code is the fact**;
- **an explicit ruling on the ask-first rule** — does it apply to this packet, and why.
  The lead makes that call once, in writing. Left unsaid, the builder re-derives it, and
  a builder that guesses wrong either stops for nothing or edits something it should have
  asked about;
- **any standing prohibition for this run** — do not restart the application, this store
  is not to be touched, a named process is on an older tip.

### 2. What the lead measured

The evidence, with the instrument and the window, not a summary of it. "The build is
slow" is not a premise. "That thread held the interpreter lock in 82.7% of samples over a
ten-minute window, measured with `<tool>` against pid 11612" is.

- code: `path:line`, read on a stated date;
- absence: "not found — searched `<paths>` and the inventory". Absence is a premise too,
  and it is the one most often assumed;
- data: the count, the store, the date it was read.

Verify all of it in the code before you write, per the rule above.

### 3. One block per item, in prose

Prose, not a form. Each item names the file and the symbol, says what is there now and
what it must do instead, gives the reason in one clause, and says what is out of scope.
Then the tests, lettered, and — the part that matters — **which letter is the
fail-before-fix proof and why the old code cannot pass it**. Naming a test path before
the test exists is guesswork; naming the assertion is not.

Say which existing tests must stay green untouched.

### 4. Parts, if it is more than one branch

A packet may span branches: Part A on a fresh branch, Part B on an existing one that
merges Part A in first, Part C to integrate and prove. Say the merge order.

### 5. Docs to reconcile

Name them, and for any new rule **quote the exact line to add to `CLAUDE.md`**. "Add a
rule about X" produces a paragraph; the quoted line produces the line. The builder does
this on the same branch, not in a follow-up.

### 6. Two gate blocks, not one

- **Gates before handoff** — the commands, with the expected result and any precondition
  to probe first, reported by **process** exit code.
- **The real-world gate** — what must be observed in the real world for this to count as
  validated. Who observes it, on what run, and exactly what they must see. It becomes a
  row in the checkpoint's gates table.

If an item has no meaningful real-world gate, say "no gate" and why. An invented gate
nobody can perform is worse than none: it sits open forever and drains the table of
meaning.

### 7. Still owed after this packet, as its own packet

Not just "what was left out" — **what is now queued, with its packet name**. Left as a
bare exclusion it is rediscovered later as a gap and rebuilt as a surprise; named as the
next packet it is work with an address.

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
