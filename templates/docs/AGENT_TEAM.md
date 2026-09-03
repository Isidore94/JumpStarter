# The agent team: one lead, its builders, its reviewers

Document role: **active runbook.** How a session in this repo plans, builds, reviews and
integrates work using project-defined sub-agents instead of pasting prompts between
windows. The agent definitions live in `.claude/agents/` (tracked); this file is the
contract they share with the lead session and with {{OWNER}}.

## The roles

| Agent | Model | Where it runs | What it may do | What it must never do |
|---|---|---|---|---|
| **lead** (the session {{OWNER}} talks to) | session model | the main checkout | ask {{OWNER}}, write packets, spawn the others, merge, run the full suite, reconcile the ledgers | build a packet itself when a builder could; restart {{PROJECT}} without {{OWNER}}'s word |
| **tester** (`.claude/agents/tester.md`) | strong, high effort | its own worktree, on the packet's branch | write the packet's tests, prove each FAILS on the current code, commit them red | write the fix; weaken or skip a test |
| **builder** (`.claude/agents/builder.md`) | strong, high effort | its own worktree, branch `{{BRANCH_PREFIX}}<slug>` | edit, test, commit, push its branch, reconcile docs on its branch | touch the main checkout, merge, delete branches, edit an ask-first file without a recorded yes |
| **reviewer** (`.claude/agents/reviewer.md`) | strong, high effort | its own worktree, on the branch under review | run tests, revert-and-rerun to prove fail-before-fix, reproduce claims on COPIES of real data | write, edit, commit, push, touch live stores |
| **recon** (`.claude/agents/recon.md`) | cheap, medium effort | the main checkout, read-only | map code with `file:line`, count real rows, find gaps | write anything, propose designs unasked |

Built-in exploration agents remain available for one-off lookups; `recon` is the same
job with this repo's rules baked in.

## The loop

1. **Recon first.** Before the lead writes a packet it spawns `recon` on the premises
   ("does X exist, where, what does the real file show"). A packet is written only from
   verified premises. *(Principle 5: two claims in one packet were refuted at code level
   by the builder.)*
2. **The packet.** The lead writes it as a numbered list: {{OWNER}}'s decision quoted,
   the facts with `file:line`, the exact change per item, the tests that must fail
   first, the invariants that bind, the docs to reconcile, the gate.
   `.claude/packets/PACKET_TEMPLATE.md` is the shape.
3. **Tests first, for anything that matters.** For a packet with more than one item, or
   any item touching {{CRITICAL_AREA}} or an {{OWNER}}-facing surface, the lead spawns
   `tester` FIRST. It writes one test per item that drives the real path, proves each
   fails on the current code, and commits them red. The builder then makes them pass and
   may only ADD tests. *(One review round found four tests that could not fail, all
   written by the agent that wrote the fix. This is the cure.)*
4. **Build.** The lead spawns `builder` with the packet and the branch slug. One builder
   per packet. **Two packets that touch the same files run one after the other, not in
   parallel** — parallel branches over shared files cost more in conflict resolution
   than they save.
   **The lead checks the handoff against the diff before believing it.** `git diff
   --stat <base>..<branch>` and the item list must agree: an item marked "done" with no
   file behind it, or a file changed that no item names, is a question for the builder
   before any reviewer is spawned. *(Two handoffs in one evening said "built" for items
   that had no code.)*
5. **Review by reproduction.** The lead spawns `reviewer` with the branch, the packet and
   the builder's handoff. GO / NO-GO, blockers separated from advisories. Never skipped
   for a packet that touches evidence or a user-facing surface: green suites have
   shipped real defects that only running the code found.
6. **Fix round.** Blockers go back to a builder as a small fix packet on the same
   branch. Sending them to the SAME builder keeps its context; a fresh builder gets the
   reviewer's blockers verbatim. Advisories are batched into a later packet.
7. **Integrate.** The lead merges in a **scratch worktree**, never in the main checkout
   while {{PROJECT}} runs from it, then runs the full suite, lint and any build
   self-test, and refreshes the "Active state at a glance" block. Merge order is packet
   order.
8. **The handover.** A merged commit reaches {{OWNER}} only at the next restart, and the
   restart is their call. The lead says in one line that it is owed and why.

## Rules that exist because something broke

- **One checkout, many agents.** {{PROJECT}} runs from the main checkout. Testers,
  builders and reviewers work in worktrees under `.claude/worktrees/`, which the
  `.gitignore` snippet already covers. Nobody switches the main checkout's branch while
  it is running: a mid-merge working tree under a running application takes it down.
- **Assume another session is in the repository.** Verify the branch immediately before
  staging and immediately before pushing; stage explicitly by path, never `git add -A`;
  never `git stash`, which takes the other session's in-flight work with it; after
  committing, confirm your work landed. Three collisions in one afternoon produced this
  rule: one commit carried two unrelated packets, one swallowed a third session's
  uncommitted code, and a pushed branch was deleted underneath the session that made it.
- **Name the condition under which the suite is NOT a baseline** — a nightly job holding
  a lock, a service that must be up, a fixture that must be rebuilt — and probe it before
  quoting a number. {{WHEN_THE_SUITE_IS_NOT_A_BASELINE}}.
- **A probe that RUNS the system writes wherever the system is configured to write.**
  Point it at a copy and say which. One reviewer's probe of a build command put thirteen
  unprovenanced rows into a live store.
- **Fail-before-fix is proven, not claimed.** The builder restores the pre-change file
  and watches the new test fail; the reviewer does it again independently.
- **Old rows have the key PRESENT and EMPTY, not absent.** A fixture modelling an old
  record with the key missing does not model the real file.
- **A fixture generated by the code it is meant to pin is a self-portrait.** Pin from the
  old code and record the commit.
- **Live stores are read-only to every agent** except a builder whose packet names the
  write — and that takes a backup first.
- **Ask-first files** ({{ASK_FIRST_FILES}}) need {{OWNER}}'s decision quoted in the
  packet for the exact functions. Otherwise the builder stops and the question goes in
  the handoff.
- **Chat is short.** Detail lives in commits, docs and handoffs. A handoff states what
  was NOT built as plainly as what was.

## Delegation policy for the lead

The lead's job is routing, not typing. The cheapest correct agent does each job.

- **Do it yourself:** reading; a lookup under a minute; `git status/log/diff`; committing
  and pushing work that already exists on a branch; merging in a scratch worktree;
  doc-only edits under about 40 lines; answering {{OWNER}}.
- **Spawn `recon` (the cheap model):** any question needing more than three files read,
  or a count from a real store. Never the expensive model for a lookup.
- **Spawn `tester` then `builder`:** any packet with more than one item, or any item
  touching {{CRITICAL_AREA}} or an {{OWNER}}-facing surface.
- **Spawn `builder` alone:** a one-item packet the lead can verify by running one test.
  For a small packet — one file, under about 80 lines — the cheap model is enough.
- **Spawn `reviewer`:** every builder branch touching {{CRITICAL_AREA}} or an
  {{OWNER}}-facing surface. Skip it for docs-only branches and for one-line fixes the
  lead verified by running the test.
- **Packets live in `.claude/packets/<name>.md`. The lead hands an agent the file path,
  never the pasted text**, so the lead's own context stays small.
- **Between jobs, {{OWNER}} clears the session.** The checkpoint block is the memory, not
  the chat.

## How {{OWNER}} uses it

- "Recon: <question>" — the lead spawns `recon` and reports the answer.
- "Build packet <name>" — the lead writes or reuses the packet, spawns `tester` then
  `builder` per the delegation policy, checks the handoff against the diff, and reports
  it when it lands.
- "Review <branch>" — the lead spawns `reviewer` and reports GO / NO-GO.
- "Integrate" — the lead merges in order, runs the gates, and says whether a restart is
  owed.

Costs: recon is cheap; testers, builders and reviewers are not, and each packet-sized
run is a real spend. The lead does not spawn a reviewer for a docs-only branch, and never
two builders on the same files.

## Setup on a machine

1. The agent files are tracked under `.claude/agents/` — `.gitignore` un-ignores that
   folder while the rest of `.claude/` stays machine-local. A fresh checkout has them.
2. `.claude/settings.json` (machine-local, not tracked) allow-lists the commands the
   agents run without a prompt: tests, lint, `git worktree`,
   `git checkout -b {{BRANCH_PREFIX}}*`, `git commit`, `git push` to
   `{{BRANCH_PREFIX}}*`. Anything unlisted prompts, which is intended for destructive
   commands. **Spell each command every way your shell and paths write it** — one
   command commonly needs six entries — and keep `git stash` in the deny list. Because
   the file is machine-local it is never in a fresh checkout: its absence from a clone is
   not evidence a project has no allow-list.
3. No flag or restart is needed: a new or changed file in `.claude/agents/` is picked up
   by the running session.

## For Codex

Codex reads `AGENTS.md` (the generated copy of `CLAUDE.md`) and does **not** read
`.claude/`. The roles above still apply — see `docs/CODEX_NOTES.md` for how the same
packet and role brief are handed to a Codex session.
