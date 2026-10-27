# Blind grader prompt (used verbatim for both graders; the grader is not told which model orchestrated)

You grade one orchestrated coding run against a hidden reference. You do not know which model did the run; do not
guess and do not let style sway you. Read everything under the run folder given to you:

- `prompt.md`: the task brief the orchestrator was given.
- `diff.patch`: the change it made (code + its own tests). `diff-seeded.patch` exists only in seeded runs (below).
- `qo/`: its own stage outputs (recon.md, plan.md, tests-red.txt, build.txt, review.json, report.md). Some may be missing.
- `own-tests.txt`, `ruff.txt`: its suite and lint results. `ref-tests.txt`: the HIDDEN reference tests run against its build.
- `reference.patch`: the real merged fix (diff base..ref), the answer key. Do not treat it as the only valid shape.
- `review.txt`: a separate self-review pass over the final diff. In a seeded run the reviewed diff had a known bug
  injected first (`seed.patch`, with `seed-note.md` saying what the bug is); the review should say NO-GO and name it.

Score each 0-3 (3 = as good as or better than the reference, 2 = minor gaps, 1 = major gaps, 0 = absent/wrong):

1. correctness: does the change do what the brief asks, and do the hidden reference tests pass (ref-tests.txt)?
2. completeness: every "Done when" item covered (tests, docs the brief names, lint)?
3. tests: did it write real failing-first tests (tests-red.txt shows red; the tests would fail without the fix)?
4. scope: no unrelated edits, no weakened existing tests, no invented features (3 = clean).
5. brief_awareness: did plan.md notice anything unclear or wrong in the brief and decide sensibly (3 = yes, 0 = ignored)?
6. self_review: did review.json / review.txt catch real defects? In a seeded run: NO-GO naming the seeded bug = 3,
   NO-GO for other true reasons = 2, GO = 0. Unseeded: 3 if its review is substantive and right, 0 if rubber-stamp.

Then one verdict for the run: MERGE (would merge as is), MINOR (small fixes), MAJOR (rework), REJECT.

Answer with ONLY this JSON:
{"correctness":0,"completeness":0,"tests":0,"scope":0,"brief_awareness":0,"self_review":0,"verdict":"MERGE|MINOR|MAJOR|REJECT","evidence":["file:line or quote per score, short"],"summary":"two sentences"}
