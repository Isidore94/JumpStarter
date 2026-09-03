# The sixteen principles, and the incident behind each

Every rule in JumpStarter was learned by something breaking. A rule without its
incident gets "fixed" by the next agent who finds it inconvenient, so the incident
is written down beside the rule and travels with it.

The incidents below are generalised from one long-running project built almost
entirely by AI agents. The domain specifics are deliberately stripped; the shape of
each failure is what repeats.

Twelve were distilled on 2026-09-03 from that project's documentation. Four more
(13-16) were added the same day from its **session memory notes** - written at the
moment something broke, and not readable by the session that wrote the first twelve.
Each of the four sharpens one of the twelve rather than standing alone.

---

## 1. Documentation must be readable in bounded time

**Rule.** The mandatory read before any work is a small, named block — not a set of
files. Every file in the mandatory read has a size limit. A file that passes its
limit is archived with a pointer left behind.

**Incident.** The instruction was "read the changelog, the plan and the checkpoint."
Those three files reached about 1 MB combined (~260k tokens). The instruction was
still there, still mandatory, and no longer followable. **An agent that cannot read
its brief skims it and then appends to it** — which is precisely what grew the files.
The unbounded read was the cause of its own impossibility.

**In practice.** Name the block, not the file: "the Active state block", "sections 5,
6 and 7", "search the inventory". Set a line limit per file and enforce it in CI.
Archiving is maintenance, not a new document.

---

## 2. One "active state" block is the thing the next agent trusts

**Rule.** Exactly one block, at the top of one file, answers "where are we?". It is
refreshed on every handoff and it carries measured numbers: branch, active items,
test count with the process exit code, lint result, the artifact the application
actually runs from, and what is owed.

**Incident.** With state spread across dated entries, two agents read the same repo
and disagreed about which branch was live. The application had been running from an
unmerged branch for hours while the docs described the trunk. A stale block is worse
than no block, because it is the one thing the next agent trusts — so the rule is
that the block is refreshed on every handoff, and that when it disagrees with the
newest dated entry, **the dated entry wins and the block is declared stale**.

**In practice.** Numbers, not adjectives. "6310 passed, exit 0, 5 min 42 s" is state;
"tests green" is a memory of state. Say which commit the number was measured on.

---

## 3. The implemented inventory is a contract to search before building

**Rule.** One bounded section lists what exists, by area. It is searched — never read
end to end — before anything is built, so landed work is not rebuilt.

**Incident.** Features were rebuilt because a changelog had become a chronological
dump nobody could search. The fix was to split the file: a short inventory at the top
that answers "does this exist?", a bounded recent-changes section for the last couple
of build days, and everything older moved to a dated archive that is evidence for one
specific question and is **never loaded as context**.

**In practice.** The inventory entry states what exists and the one thing about it
that is easy to get wrong. It is a contract, not a history.

---

## 4. Every rule carries its evidence

**Rule.** The binding one-line form of a rule lives in the control file. The incident,
the measurements and the owner's own words behind it live verbatim in an internals
document, and the matching entry is read before the behaviour a rule governs is
changed.

**Incident.** The rules section of the control file grew to 42 KB — 65% of a file that
loads into *every* session — because each rule carried its whole backstory. Splitting
them let the rules stay short and the reasons stay complete. The alternative had
already been tried: rules with no reasons attached were "cleaned up" by later agents
who could not see what they were load-bearing for, and the same bugs came back.

**In practice.** Rule in the control file, reason in the internals file, and a line in
both saying the other exists. Change a rule in both places or not at all.

---

## 5. Build from packets whose premises were verified in the code

**Rule.** Before a work packet is written, a cheap read-only pass verifies its
premises against the code, with `file:line` for every claim. Line numbers in a packet
are stamped with the date they were read, and the builder re-verifies each before
editing. **When the code disagrees with the packet, the code is the fact.**

**Incident.** A review produced a packet whose claims were taken as given. Two of them
were refuted at code level by the builder — the described code did not exist in that
form. Everything downstream of an unverified premise is wasted work, and the waste is
discovered at the most expensive moment.

**In practice.** Recon is cheap; run it first. A packet built on "I believe X" instead
of "X, at path:line, read today" is a draft, not a packet.

---

## 6. Every fix ships with a test proven to fail on the un-fixed code

**Rule.** The builder restores the pre-change file, runs the new test, watches it
fail, restores the fix, and says so in the commit message. The reviewer proves it
again independently.

**Incident.** Tests written after a fix routinely pass on the broken code. They
document the author's belief about the bug, not the bug. Two independent proofs exist
because the first one is done by the person most motivated to see it succeed.

**In practice.** "Fail-before-fix: restored `x.py` at `<base>`, test failed with
`<assertion>`, restored." A test that cannot fail proves nothing.

---

## 7. Review by reproduction, not by reading

**Rule.** The reviewer runs the branch: runs the new tests, reverts the fix to prove
they fail, re-derives every number the builder quoted, and reproduces claims about
live data against **copies** of it. The verdict is GO / NO-GO with blockers separated
from advisories.

**Incident.** A fully green suite shipped: a missing-number read as a category
literally named `"NAN"`; a link tag that evicted the real tags it was meant to sit
beside; a summary card printing 100% where the truth was 30%. Reading the diff found
none of these. Running the code against copies of real data found all three, in two
review rounds, on branches whose tests all passed.

**In practice.** A blocker is something that makes a number wrong, a gate
unsatisfiable, a rule broken, or a user-facing surface misleading. Everything else is
advisory. A clean branch gets "BLOCKERS: none" — never padding.

---

## 8. The eight traps

These are the specific ways a green suite lies. Scan for them on every review.

1. **Old rows have the key PRESENT and EMPTY, not absent.** A fixture modelling an
   old record with the field missing does not model the real file. This is how a
   missing number became a category named `"NAN"`.
2. **A fixture generated by the code it is meant to pin is a self-portrait.** Pin
   fixtures from the OLD code and record the commit they were generated at.
3. **A test that asserts on source text proves nothing.** Asserting that a file
   contains a string is not asserting that the behaviour happens.
4. **`assert x or True` is a tautology.** So is any assertion whose failure branch
   cannot be reached. Run the test against the un-fixed code to find out.
5. **A positional lookup breaks when a field is prepended.** Index-based reads of
   rows, tuples and CSV columns are time bombs; key by name.
6. **A magic window repeated in three files is three different windows.** Read the
   number from one constant; a "20-session window" that is `20` in two places and
   `21` in a third is a silent divergence.
7. **A version, vocabulary or schema id asserted as a literal in a test** freezes the
   test to today's data. Assert against the loaded definition.
8. **A derived value re-derived differently in two places will disagree.** One
   implementation, read by every surface — a headline number computed twice is a
   number that will eventually lie on one screen and not the other.

---

## 9. One checkout, many agents

**Rule.** Builders and reviewers work in their own git worktrees. Nobody switches the
main checkout's branch while the application runs from it. The lead merges in a
scratch worktree. **Restarts are the owner's call**, and a merged commit reaches the
running application only at its next restart.

**Incident.** The running application died mid-session with the working tree in a
half-merged state under it, because a merge was performed in the checkout it was
running from. Separately, seven branches built in parallel against the same files
cost an evening of conflict resolution — so two packets that touch the same files run
one after the other, not at the same time.

**In practice.** The lead says in one line that a restart is owed and why. It never
performs one unasked.

---

## 10. The owner's goals are written down in their own words

**Rule.** One decision record holds the owner's answers to a fixed questionnaire, in
their own words, dated. It is the tie-breaker for every prioritisation call, and
every prioritisation cites it.

**Incident.** The build had grown faster than the statement of what it was for.
Features were correct, tested and delivered onto screens the owner never opened. The
questionnaire — what to get right first, how success is scored, which screens are
actually used, what is never automated — reordered the entire roadmap in one
afternoon and retired several finished features.

**In practice.** Ask one question at a time and record the answer verbatim. An answer
you paraphrase is an answer you have already begun to overwrite.

---

## 11. Chat is short; detail lives in commits, docs and handoffs

**Rule.** Messages to the owner are short and plain: what was done, what is broken,
what they need to do. Detail belongs in the commit message, the docs and the handoff.
**A handoff states what was NOT built as plainly as what was.**

**Incident.** Long chat summaries became the de-facto record. They are unsearchable,
unversioned, and lost when the session ends — so the next agent rebuilt context from
the one place that had it: the files. A handoff that only lists what was built leaves
the next agent to discover the gaps by running into them.

**In practice.** If a message runs past about ten short lines, cut it. This rule is
for chat only; docs, code comments and commit messages keep their normal depth.

---

## 12. Shadow first, fixtures before behaviour, floors on every statistic

**Rule.** Anything that changes a live decision runs in shadow first, emitting
evidence and influencing nothing. Behaviour with consumers gets golden fixtures
before it is changed. Every statistic carries its sample size and a floor below which
it is not shown as a verdict. **Uncertainty never deletes** — missing data is
uncertainty, never confirmation.

**Incident.** A challenger promoted on a plausible-looking early result was reading a
window it shared with nothing else. Sample floors and a declared evidence window
frozen *before* inspection turned a "promising" cell into an honest "n too low". The
matching rule — no behaviour change without fixtures first — exists because ordinary
unit tests cannot prove a refactor preserved exact output.

**In practice.** Declare the evidence window before you look at a single cell, and
treat reading one early as a refusal, not a check. Promotion is a separate decision
from implementation and from validation, and it is the owner's.

---

# Four more, learned since

These come from the source project's session memory — notes written at the moment
something broke, which the first distillation of these principles never read. They
are not a thirteenth through sixteenth principle; each sharpens one above.

---

## 13. Capped instrumentation goes blind, and its silence reads as calm (sharpens 2)

**Rule.** Any log, counter or watchdog with a cap on how much it will record needs a
cap that **rolls**. A per-session or per-day cap is spent by the quietest hours and
gone by the time something happens.

**Incident.** A stall watchdog wrote at most 2,000 records per session. An idle
machine left on overnight burned about 500 an hour on sub-second stalls that mattered
to nobody, and the budget ran out at 06:03. The worst freeze on record happened that
morning — 30 to 60 minutes of an unusable application, four times a day — and the log
for it is empty. Nobody noticed, because an empty log looks exactly like a quiet one.
A per-**day** cap would have gone blind at the same minute.

**In practice.** Roll the cap on an hour, not a session or a day. And when a
diagnostic file is the evidence for a question, check that it was still writing at
the time you are asking about, before concluding anything from its silence.

---

## 14. A probe that RUNS the system writes to it (sharpens 7 and 12)

**Rule.** "Read-only" is a property of the path you hand a process, not of your
intention. A reviewer reproducing a claim by *running* a build, a CLI or a batch job
points it at a **copy** of the store, and says in the report which copy.

**Incident.** A reviewer probing a build command ran it against the live store. It did
what it was built to do: thirteen unprovenanced rows landed in the real data, and a
human then had to decide whether to keep or unpick them. Everything about that review
was correct except where it pointed.

**In practice.** Every packet touching a store says, in the packet, that the reviewer's
probe uses a copy. Principle 7 already said reproduce against copies; this is the
sentence that stops a "probe" being read as an exception to it.

---

## 15. Assume another session is in the repository (sharpens 9)

**Rule.** Verify the branch immediately before staging **and** immediately before
pushing. Stage explicitly by path; never `git add -A`. Never `git stash` — restore the
one file instead. After committing, confirm your work is in the commit you think it is.

**Incident.** Several agent sessions ran against one working tree. In one afternoon:
one commit carried two unrelated packets; a second session's commit swallowed a third's
uncommitted code; and a pushed branch was deleted underneath the session that created
it, while its work reached the trunk by another route. Staging explicit paths was not
enough — another session can switch `HEAD`, commit, or delete a branch between your
edits and your push.

**In practice.** Expect `git status` to list files you did not touch. A full-suite test
count is not isolated: report the number you measured and say which part is yours. Say
the collision plainly in the commit message and the checkpoint — the next agent trusts
that block.

---

## 16. The control file itself goes stale (sharpens 4 and 5)

**Rule.** The rule that "the code is the fact, the doc is the defect" applies to
`CLAUDE.md` too. A line there that the code contradicts is not authority. Correct it,
or leave a **dated tombstone** saying which line is wrong and what the code does
instead — and tell the owner. Never fix it silently.

**Incident.** A control-file bullet described a layout that had been changed the same
day it was written, on the owner's own instruction. The line survived because nothing
reads a control file looking for defects — it is read for authority. A week later a
design proposal built one of its three decisions on that line: a refuted premise, out
of the one file every session trusts most. The tombstone that caught it was a session
memory note, not the file itself.

**In practice.** A silent correction leaves nobody able to tell whether the old line
was wrong or the new behaviour was unauthorised. Date the note, name the source that
disagrees, and say when the note can be deleted.
