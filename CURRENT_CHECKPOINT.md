# Current checkpoint

This file is the frequently refreshed active-work, branch and verification stamp.

- Implemented inventory and revision history: [`CHANGELOG.md`](CHANGELOG.md)
- Remaining work and gates: [`plan.md`](plan.md)
- Supporting-document roles: [`docs/README.md`](docs/README.md)
- Older entries: nothing archived yet — see the archive rule at the bottom.

---

## Active state at a glance

**Read this block first. It is the answer to "where are we?" — the dated entries below
are the working record behind it. Refresh this block on every handoff; if it disagrees
with the newest dated entry, the dated entry wins and this block is stale.**

| | |
|---|---|
| Working branch | **`claude/jumpstarter-repo-setup-dn3rof`**. Nothing has been merged to `main`; `main` does not exist yet |
| Also in flight | **`claude/i1-rules-carry-evidence` at `6972b9f`, pushed, reviewer GO, NOT merged** — packet I1 (`.claude/packets/I1.md`): `check` gains `rules carry evidence`, 54 tests, 7 checks. Merging is the owner's call. No worktree left open |
| Active items | `plan.md` **Phase 1 item 1** — bootstrap one real new project from the templates. Not started. Phase 0 is done, and the questionnaire is now answered (record 0002) |
| Last verified baseline | Measured 2026-09-03 on **CPython 3.9.25**: `python -m pytest tests/ -q` **49 passed, process exit 0, 2.0 s**; `ruff check .` **All checks passed**, exit 0; `python tools/jumpstart.py check .` **6 checks, no gaps**, exit 0; `retrofit .` **exit 0, 25 checks, 1 advisory**. The same four re-run identically on 3.12.13 |
| Artifact state | There is no build artifact. `tools/jumpstart.py` runs from source, standard library only. The 3.9 floor is now **measured, not claimed** — see the gate 3 row |
| Restart owed | **No.** Nothing runs continuously from this checkout |

**Correction to the previous block.** It recorded `check .` as "9 checks" (it is 5, now 6
with `plan size`) and the interpreter as "Python 3.11.15" (no 3.11 exists on this
machine; the working interpreters are 3.9.25 and 3.12.13). The code is the fact.

Rules for this block:

- Numbers, not adjectives. "Tests green" is a memory of state; "38 passed, exit 0" is
  state.
- Check the **process** exit code, not a piped tail's.
- If a number was not measured this handoff, say so and say when it was.

### Open gates, newest first

Each is owed before the work it belongs to can be called validated. Detail lives in the
dated entry named beside it.

| # | Gate | Owed by |
|---|---|---|
| ~~3~~ | ~~**The declared Python floor is real**~~ — **CLOSED 2026-09-03.** Installed CPython **3.9.25** and ran it: `pytest tests/ -q` 49 passed, process exit 0; `check .`, `retrofit .`, `sync-agents .` and `init` all run and return the same exit codes as on 3.12.13. `README.md` now states the measurement, the version and the date | closed |
| 2 | **One new project bootstrapped end to end** — a human answers the questionnaire, fills every placeholder, and `check` is green on a repo that was empty this morning. Record which questions were hard to answer and which placeholders had no good answer. **Now the only open gate**, and it matters more than it did: the templates changed materially today and none of that has been used from empty | `plan.md` Phase 1 item 1 |
| ~~1~~ | ~~**One real existing repository audited**~~ — **CLOSED 2026-09-03.** Three real repositories, working copies not clones. Two false positives and four misses, all six now fixed with a test apiece. See the entry below | closed |

A gate is closed by striking its row through and writing what was observed — never by
deleting the row.

---

### 2026-09-03 — The second pass verified by reproduction, and the team run once for real

Full detail, every command and its output:
[`docs/prompts/VERIFICATION_REPORT_2026-09-03.md`](docs/prompts/VERIFICATION_REPORT_2026-09-03.md).

**Part A — the numbers held.** 49 / clean / 6 checks / 25 checks + 1 advisory, all exit 0
on CPython 3.9.25, re-measured. All eleven fail-before-fix claims reproduce (no test
passes on the un-fixed code), but seven of the nine from `2c716c7` fail on an
`AttributeError` for a not-yet-existing function, which proves absence, not behaviour.
**One hard invariant was violated**: *Templates stay short enough to read in one sitting*
was a Core rule with no `INTERNALS` entry. Fixed here — entry added, citation added,
`AGENTS.md` re-synced. Also fixed here: a dated `CHANGELOG.md` entry that had been filed
under "Retired", and `.claude/packets/` was gitignored so no worktree agent could read a
packet (now tracked). **Doc defects**: the source project audit is 4 gaps, not 3
(`plan.md` 1,835 > 1,200 was added after the count was written); `section_line_count`
stops at prose beginning `#19.`, so that repo's "Recent changes" is 3,782 lines, not the
1,583 the tool prints. Not fixed — owed as packet I2 with the uncited-rule case.

**Part B — the loop worked.** recon (sonnet, ~42k tokens) → packet I1 → tester committed
four tests red at `e404283` (lead reproduced: 3 failed, 50 passed; the proof fails on the
`check` exit code, not on a missing name) → builder green at `677a5d2` + docs at
`6972b9f`, **0 deletions in the test file** → reviewer **GO**, every number re-derived,
one tautology found at test line 191 that both earlier agents missed. Gate 5 observed by
the lead and by the reviewer with the branch's code against copies: the missing name is
printed and both commands exit 1. Total ~268k agent tokens, 145 tool calls, four runs.
**Not merged.**

**What the run showed about the role files** (all ask-first, so recorded, not changed):
`main` is assumed and does not exist; "any Python 3.9+ on PATH" is false on this machine
(the lead had to hand every agent the `uv run` line); the tester prototyped the fix in a
scratch directory, which the role file neither allows nor forbids; the builder discarded
its own uncommitted fix with `git checkout --` during revert-and-rerun — commit before
proving. The proposed allow-list is in the report.

---

### 2026-09-03 — The questionnaire, asked properly this time

All twelve questions put to the owner **one at a time**, answers recorded verbatim in
[`docs/decisions/0002-owner-goals-asked-properly.md`](docs/decisions/0002-owner-goals-asked-properly.md).
Record `0001` is `SUPERSEDED` and kept as evidence of what was assumed before anyone
asked. **No OPEN answer remains.** Two answers (9 and 12) are explicit non-answers —
*"i havent ran into this yet"*, *"not sure yet this concept is new to me"* — recorded as
such and not filled in.

**Two of 0001's assumptions were wrong, and both change how this project is judged.**

1. **The agent is the reader, not the owner.** 0001 guessed the owner reads the CLI
   output and the playbooks. Asked, they said: *"i dont use any of them but fable 5.1
   currently uses everything there."* So the size limits, the bounded read and the
   active-state block are **the product**, not housekeeping — they exist because a model
   has a context budget. The only surface the owner reads is the chat message.
2. **Cost is the trust signal.** 0001 recorded this answer as OPEN and guessed at "a tool
   that rearranged an existing repo's docs". The real answer: *"if it used all my usage
   really fast indicating to me that subagents arent being used appropriatly."* That makes
   the delegation policy in `docs/AGENT_TEAM.md` load-bearing rather than advisory, and it
   sets the failure mode to watch: **a design that is correct and expensive is a design
   this owner stops trusting.**

Three more that change something:

- **The orchestrator is not fixed.** Fable 5.1 with subagents today; possibly a Codex
  frontier model later. Nothing in `templates/` may name a model or assume which tool
  leads. Already true of `docs/AGENT_TEAM.md`; now a requirement rather than a style.
- **The slow part is the shuttle** — *"having to copy and paste fable prompts to opus"* —
  which is exactly what the packet-path handoff removes.
- **Scope discipline is the boundary**, not a list of forbidden verbs: *"as long as we are
  following my instructions and limiting scope to what i say, everything can be
  automted."* This loosens 0001's "restarts and promotion are always the owner's call".
  Recorded, flagged, and **not acted on**: the ask-first and wishlist rules survive as
  scope-limiting devices until the owner says otherwise.

**What this did NOT do.** It did not reorder the roadmap. Gate 2 was already the only open
gate and answer 3 — *"take tradingbotv3 folder and learn what i did there"* — is the same
instruction the build has been following. Nothing here authorises new work.

---

### 2026-09-03 — Gate 1 closed: three real repositories audited, report only

**Nothing was written to any of them.** `retrofit` writes nothing by hard invariant, and
the writes-nothing test pins it.

| Repo | Shape | Exit | Result |
|---|---|---|---|
| the source project, **working copy** (not a clone) | full control set, mature | 1 | 22 checks, **3 gaps** |
| a second real repo | partial control set: `CLAUDE.md`/`plan.md`/`CHANGELOG.md` present, no `docs/`, no `.claude/` | 1 | 22 checks, **14 gaps** |
| a third-party checkout | **no control set at all** | 1 | 22 checks, **22 gaps** |

(Counts as they were before today's fixes. Re-run afterwards the same three read 3 gaps,
15 gaps + 2 advisories, and 22 gaps.)

**The three gaps on the working copy were all real**, and all three are principle 1 in
its natural habitat — the rule is written down, it is correct, and nothing enforced it:
`CURRENT_CHECKPOINT.md` 4,587 lines against its own 1,500 limit; `CHANGELOG.md`'s "Recent
changes" 1,549 against 800; `CLAUDE.md` 418 against 400. **The clone run's one false
positive did not recur** — the allow-list is on that machine; its absence from a clone
was an artifact of the clone, exactly as recorded.

#### The two false positives

1. **`active state block: MISSING`** on the second repo, which keeps that block under
   `## Active item` — complete with a measured gate stamp. The finding was literally true
   and practically wrong: it reads as "this repo has no idea where it is", and that was
   not the case.
2. **`command allow-list: MISSING`**, reproduced against **this repository itself**.
   `.claude/settings.json` is machine-local by design; `.gitignore` keeps it out.

Both are now `ADVISORY`: named in the report, not counted as gaps, not changing the exit
code. A check that fires on correct work gets ignored, and takes the real findings with
it.

#### The four misses — the part that matters

1. **Seven root-level handoff, review and prompt files, 1,505 lines, on the second
   repo** — forbidden in terms by *that repo's own* `CLAUDE.md` ("do not create extra
   roadmap, status, or handoff files"), and the audit said nothing about any of them.
   That is the most visible symptom of the disease this tool exists to treat, and it was
   invisible. Now an advisory naming each file with its line count.
2. **`plan.md` was never measured.** 1,835 lines on the source project, 2,960 on the
   second, both in the mandatory read. `PLAN_MAX_LINES = 1200` — approved by the owner
   today, because a limit constant lands in every downstream repo.
3. **`CHANGELOG.md` was never measured when it had no "Recent changes" heading.** The
   second repo's is 2,047 lines and purely chronological: the audit reported the missing
   heading and then let the file through the size checks entirely.
4. **The empty-repo report was 22 undifferentiated `MISSING` lines**, three of which only
   repeated that the file was absent. It now opens with one sentence saying to run `init`.

#### One defect in the tool, found by looking at its own output

Every advice string carrying an em-dash printed as a replacement character on a Windows
console — on all three runs. Printed strings are ASCII now and `main()` sets
`errors="replace"` on the streams. A report that looks broken gets trusted less.

#### What is still owed

Gate 2. And the audit still cannot check the things it has no way to see: whether
`plan.md` actually has invariants/validation/promotion sections where `CLAUDE.md` sends
agents; whether `docs/INTERNALS.md` has an entry per rule (a hard invariant of this
repo's own `plan.md`, enforced by nobody); and whether an allow-list's *contents* are
narrow — a `settings.json` containing `Bash(git *)` passes as `OK: present` today. Named
here so they are not rediscovered as surprises.

---

### 2026-09-03 — What the four unreadable sources actually contained

The first build worked from a description of the source project. This session read four
things it could not:

- **The real packets.** `PACKET_TEMPLATE.md` was reconstructed from a *description* of a
  packet. Eight things a real packet does that it did not ask for, and two it asked for
  that no real packet has. Reshaped; `playbooks/packet-writing.md` rewritten with it.
- **The real `.claude/settings.json`.** 80 entries, **no deny list**, and one command
  spelled six ways (two shells x two slash directions x relative/absolute). The deny list
  JumpStarter invented is kept — it is the one place the template beats its source — and
  `git stash` moves into it.
- **The session memory notes**, never read before. The richest of the four: four lessons
  that appear in no document, now `PRINCIPLES.md` 13-16.
- **`.claude/worktrees/`.** Worktrees live *inside* the repo at
  `.claude/worktrees/agent-<hash>`, covered by the `/.claude/*` ignore line. The template
  said only "their own worktrees" and never said where.

The source project has also gained a **fourth agent** since: `tester`, which writes the
packet's tests, proves each fails, and commits them red without ever writing the fix. It
exists because one review round found four tests that could not fail, every one written
by the agent that had written the fix. That, the handoff-vs-diff check, and the
delegation policy are now in the templates.

---

### 2026-09-03 — A paste-ready prompt to refresh from the source project

The owner now has a local clone with access to `c:\Users\Aaron\TradingBotV3`, so the
four sources the remote build could not read are reachable:
`.claude/packets/*.md` (the real packets — `templates/.claude/packets/PACKET_TEMPLATE.md`
was reconstructed from a *description* of one), `.claude/settings.json` (the real
allow-list), `.claude/worktrees/` (the real layout), and the session memory notes under
`C:\Users\Aaron\.claude\projects\...\memory\`, which were never read at all.

`docs/prompts/REFRESH_FROM_SOURCE_PROMPT.md` is the brief for that session: recon and a
diff report before any template edit (templates are ask-first), gate 1 against the
working copy **and** against a repo with no control set, gate 3's Python floor, the four
OPEN questionnaire answers, then doc reconciliation.

**No gate is closed by this entry.** Writing the prompt is not doing the work.

---

### 2026-09-03 — First retrofit dry run, on a clone of the source project

**Report only. Nothing was changed in that repository, and nothing could be:** it was a
read-only clone, and `retrofit` writes nothing by invariant.

`python tools/jumpstart.py retrofit <clone>` → **22 checks, 3 gaps, exit 1.**

Seventeen checks passed, which is the expected result: this repo's templates were
distilled from that project, so the audit is partly checking its own homework. The three
gaps are the useful part.

**Two real gaps, both the size rule:**

- `CURRENT_CHECKPOINT.md` is **4,284 lines** against a limit of 1,500 — the file carries
  its own archive-at-1,500 rule and is nearly three times over it.
- `CHANGELOG.md`'s "Recent changes" section is **1,341 lines** against a limit of 800,
  in a file whose header says the section holds "the last two build days".

Both are the principle-1 failure in its natural habitat: the rule is written down, it is
correct, and nothing enforces it, so the file grows until the mandatory read stops being
followable. This is the strongest argument found so far for wiring `check` into CI
(`plan.md` Phase 2 item 1).

**One false positive:**

- `command allow-list: .claude/settings.json not found`. That file is **deliberately
  machine-local** in that project — its own `docs/AGENT_TEAM.md` says so, and its
  `.gitignore` tracks `.claude/agents/` while ignoring the rest. The file exists on the
  owner's machine and cannot exist in a clone.

  The audit cannot tell "absent" from "correctly untracked" by looking at a checkout. The
  fix is not to drop the check — a project with no allow-list at all is a real finding —
  but to read `.gitignore` and downgrade the result to an advisory when `.claude/*` is
  ignored. Not yet built; recorded here so gate 1's record is honest rather than tidy.

**What this run did NOT establish.** The audited repo already had a full control set, so
this exercised the *pass* path, not the path the audit was written for: a repo that grew
without one. Gate 1 stays open for that.

---

### 2026-09-03 — First build: templates, playbooks, CLI, tests, and its own control set

**Branch `claude/jumpstarter-repo-setup-dn3rof`.** No merge target yet.

Distilled the control-set shape and the twelve principles from a mature project built
almost entirely by AI agents, generalised: no domain content reached `templates/`. Built
the eighteen templates, the five playbooks, `tools/jumpstart.py` (four subcommands,
standard library only) and 38 tests. Then ran `init` on this repo and filled the result
by hand, which is how the last two defects below were found.

**What was NOT built.**

- **Nothing has been run against a real repository.** The suite exercises the CLI against
  fixtures the tests themselves construct. That is gate 1, and it is the difference
  between "the code parses what I gave it" and "the audit is right".
- **No CI.** `check` is not wired into anything; it is run by hand. `plan.md` Phase 2.
- **The Python 3.9 floor is unverified** (gate 3).
- **The questionnaire was not put to the owner one question at a time**, which is what
  `playbooks/new-project.md` requires. Four of the twelve answers in
  `docs/decisions/0001-owner-goals-and-priorities.md` are recorded as **OPEN** rather
  than guessed at. Re-asking properly is that record's reopen trigger.
- **`retrofit`'s twelve check families are heuristics over file names and headings.** A
  repo whose active-state block lives under a different heading will be reported as
  missing one. That is the expected class of false positive, and gate 1 exists to measure
  it rather than assume it.

**Two defects found by dogfooding, both fixed on this branch.**

1. `check` was red on a correctly set-up project, because
   `docs/decisions/0000-template.md` and `.claude/packets/PACKET_TEMPLATE.md` exist *to
   be copied and filled in later* — their placeholders are the product.
   `TEMPLATES_BY_NATURE` exempts them. *(INTERNALS: "Templates by nature")*
2. `check` reported an unfilled placeholder in a fully-filled file, because this repo's
   own `CLAUDE.md` writes a token-shaped example in prose while describing the rule.
   Placeholder names are now identifiers only, prose writes `{{...}}`, and two dotted
   template tokens were renamed. *(INTERNALS: "A placeholder name is an identifier")*

Both are the same lesson: a check that fires on correct work is a check that gets
ignored, and it takes the real findings with it.

**Proof.** `python -m pytest tests/ -q` → 38 passed, process exit 0, 0.3 s.
`ruff check .` → All checks passed, exit 0. `python tools/jumpstart.py check .` → 9
checks, no gaps, exit 0.

**Fail-before-fix.** Not applicable to most of this build — there was no prior code to
restore. The two defects above are the exceptions and both have a test that fails on the
un-fixed code: `test_check_is_green_on_a_filled_repo` fails without `TEMPLATES_BY_NATURE`,
and `test_a_placeholder_name_is_an_identifier` fails with `.` in the character class.

**Gates recorded.** 1, 2 and 3 above.

---

## Archive rule

When this file passes **~1,500 lines**, move the entries older than the oldest open gate
into `docs/CHECKPOINT_ARCHIVE_<YYYY-MM>.md` and leave a pointer at the top of this file.
The archive is evidence for one specific question; it is never loaded as context.
Archiving is maintenance, not a new document.

`python tools/jumpstart.py check .` enforces the limit.
