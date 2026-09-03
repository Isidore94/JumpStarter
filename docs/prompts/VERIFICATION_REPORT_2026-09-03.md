# Verification report — 2026-09-03, the second pass checked by reproduction

Document role: **historical evidence.** What a lead session found when it re-derived the
claims of the 2026-09-03 second pass (`81f41fd`..`f1fc5cf`) and then ran the four-agent
loop on one real packet. The brief it answers is
[`VERIFY_AND_EXERCISE_THE_TEAM_PROMPT.md`](VERIFY_AND_EXERCISE_THE_TEAM_PROMPT.md).
Nothing here is authority: the fixes it led to are in the commits it names.

Interpreter for every command below: CPython 3.9.25 at
`C:/Users/Aaron/AppData/Roaming/uv/python/cpython-3.9-windows-x86_64-none/python.exe`,
tests via `uv run --python 3.9 --with pytest python -m pytest`. Exit codes are the
**process** exit code (`${PIPESTATUS[0]}`), never a piped tail's.

---

## Part A — the second pass, re-derived

### A1. Baseline numbers — held

| Command | Claimed | Measured | Exit |
|---|---|---|---|
| `pytest tests/ -q` | 49 passed | **49 passed in 1.96s** | 0 |
| `ruff check .` (`uvx ruff`, 0.16.6) | clean | **All checks passed!** | 0 |
| `jumpstart.py check .` | 6 checks, no gaps | **No gaps: 6 checks passed** | 0 |
| `jumpstart.py retrofit .` | 25 checks, 1 advisory | **No gaps: 25 checks passed. 1 advisory** | 0 |

One thing the checkpoint does not say: the bare 3.9 interpreter has no `pytest`, and
there is no `python` on `PATH` in this shell at all (Windows resolves it to the Store
alias). Every agent role file says "any Python 3.9+ on PATH". On this machine that
sentence is false — see A5.

### A2. Fail-before-fix — every test fails on the un-fixed code, but seven fail for the weak reason

Method as briefed: `git worktree add --detach <scratch> <parent>`, copy the current
`tests/test_jumpstart.py` in, run only the named tests, remove the worktree.

**`3935613` (two tests) against `d610afb`:** both fail.

```
FAILED test_the_team_has_a_tester_that_is_not_the_builder
FAILED test_no_agent_template_tells_an_agent_to_stash
      AssertionError: .claude/agents/builder.md mentions stashing without forbidding it:
      '... stash or restore the pre-change file, run the test, see it fail ...'
2 failed, 47 deselected — exit 1
```

**`2c716c7` (nine tests) against `db7c987`:** all nine fail — exit 1. But look at *why*:

| Test | Fails with |
|---|---|
| `test_a_gitignored_allow_list_is_an_advisory_not_a_gap` | `AttributeError: no attribute 'audit_allow_list'` |
| `test_an_untracked_allow_list_with_no_gitignore_rule_is_still_a_gap` | `AttributeError: no attribute 'audit_allow_list'` |
| `test_an_active_state_block_under_another_heading_is_an_advisory` | `AttributeError: no attribute 'audit_active_state'` |
| `test_a_checkpoint_with_no_state_block_at_all_is_still_a_gap` | `AttributeError: no attribute 'audit_active_state'` |
| `test_stray_root_ledgers_are_reported_by_name` | `AttributeError: no attribute 'audit_stray_ledgers'` |
| `test_the_control_set_and_a_readme_are_not_stray_ledgers` | `AttributeError: no attribute 'audit_stray_ledgers'` |
| `test_an_oversized_plan_is_a_gap` | `AttributeError: no attribute 'PLAN_MAX_LINES'` |
| `test_a_changelog_with_no_recent_section_is_measured_whole` | `assert 'whole file' in "no 'Recent changes' heading in CHANGELOG.md"` |
| `test_the_report_is_ascii_so_a_console_can_print_it` | `UnicodeEncodeError: 'ascii' codec can't encode '\u2014'` |

**No test passes on the un-fixed code.** The claim in `CURRENT_CHECKPOINT.md` and
`plan.md` ("all nine proven to fail on the previous commit") is literally true. It is
also weaker than it reads: seven of the nine fail because they call a function or
constant that did not exist yet. That proves the code was absent, not that the test can
tell correct behaviour from wrong. Three of those seven are the negative controls (an
untracked allow-list *is still* a gap; no state block *is still* a gap; the control set
*is not* a stray ledger), which on old code would have passed if the old code had been
called through the old entry point. Only two of nine — the whole-file changelog
measurement and the ASCII report — fail on behaviour. The packet for Part B was written
with this in mind: its fail-before-fix test asserts the `check` exit code **before** it
touches the new function name.

Worktrees removed: `git worktree list` shows only the main checkout; `git status` clean.

### A3. Hard invariants — one violated, one bug found on the way

1. **No third-party dependency in `tools/`.** Holds. `grep -nE '^\s*(import|from)'
   tools/*.py`: `__future__`, `argparse`, `datetime`, `hashlib`, `re`, `sys`,
   `collections.abc`, `pathlib`. All standard library.
2. **`retrofit` never writes.** Holds, reproduced: a detached worktree at `db7c987` (54
   files), `sha256sum` of every non-`.git` file before and after `retrofit .`, `diff`
   empty. Exit 1 on that older tree (it lacks the tester agent), as expected.
3. **`init` never overwrites without `--force`.** Holds, reproduced: a scratch dir with
   `CLAUDE.md` = `MY OWN RULES`; `init . --name Scratch` exit 0; `CLAUDE.md` unchanged and
   `AGENTS.md` generated from it (both sha `5be56ed4…`, 1 line). `check` on the result:
   13 gaps, all `UNFILLED` placeholders, exit 1 — as designed.
4. **No domain content in `templates/`.** Holds. `grep -rniE 'trading|desk|ticker|Qt|
   PySide|warehouse|avwap|trader|TradingBot|pytest'` over `templates/`: **zero hits**
   (the `pytest` grep separately: zero). `Claude` outside `templates/.claude/` and
   `templates/codex/`: zero. The only model names are the `model: opus` / `model: sonnet`
   front-matter lines in `templates/.claude/agents/*.md`. **Ruling: not a violation of
   record 0002 answer 2.** Those lines pick the tier each *sub-agent* runs on inside a
   Claude Code harness — the cost lever answer 12 cares about — and say nothing about
   who leads; a Codex lead never reads `.claude/`. What *would* violate it is a template
   sentence assuming the orchestrator is a Claude model, and there is none.
5. **Every rule in `CLAUDE.md` has an entry in `docs/INTERNALS.md`.** **VIOLATED** at
   `f1fc5cf`. By hand: `CLAUDE.md` Core rules carry nine bolded bullets; eight cite an
   `INTERNALS` name and all eight names resolve (case-insensitively; one citation at
   `CLAUDE.md:122-123` is wrapped across a line break). The ninth, *Templates stay short
   enough to read in one sitting*, cites nothing and has no heading. `docs/INTERNALS.md`
   has nine `##` headings; the ninth is *An unpinned linter is not a gate*, cited from
   the Commands section. **Fixed in this pass**: entry added to `docs/INTERNALS.md`,
   citation added to `CLAUDE.md`, `AGENTS.md` re-synced. In `templates/`, the citation
   `"Completed records only"` at `templates/CLAUDE.md:90` has no heading in
   `templates/docs/INTERNALS.md` — but it sits inside an HTML comment as the example
   shape, so packet I1 excludes comments; not a defect.
6. **`sha256(CLAUDE.md) == sha256(AGENTS.md)`.** Holds: `e94ba24d…` both, at `f1fc5cf`;
   `templates/CLAUDE.md` == `templates/AGENTS.md`: `df565b4d…` both. After this pass's
   `CLAUDE.md` edit and `sync-agents`: `cc3de1ab…` both.
7. **Template, playbook and check change together.** `git show --stat`:
   - `b463b4f`: `templates/.claude/packets/PACKET_TEMPLATE.md` + `playbooks/packet-writing.md`. Mirrored.
   - `d610afb`: `templates/.claude/settings.json` + `playbooks/new-project.md`. Mirrored.
   - `3935613`: seven template files + `playbooks/build-review-loop.md`,
     `playbooks/retrofit.md`, and a two-line `tools/jumpstart.py` change adding
     `tester.md` to the copy list — the check that *requires* the agent (`agent tester:
     present`) landed in `2c716c7`, one commit later. **Minor finding**: the template and
     its check were split across two commits, against the rule as written.
   - `2c716c7`: no template touched; `.claude/agents/*` + `playbooks/retrofit.md` +
     tools + tests. Mirrored.

**A bug found while re-deriving A4, recorded here because it is a `tools/` defect:**
`section_line_count` (`tools/jumpstart.py`, the "Recent changes" measurement) treats any
line whose stripped text starts with `#` as a heading. `TradingBotV3/CHANGELOG.md:2540`
begins `#19. Also fixed en route:` — prose — and the section measurement stops there.
The tool reports "Recent changes" as **1,583** lines; counting to the next real `##`
heading (line 4739) it is **3,782**. The checkpoint's 1,549 was under-measured the same
way. Named in packet I1's "Still owed" as I2; not built in this pass.

### A4. The other repositories — read-only, re-derived

**TradingBotV3** — `retrofit` exit 1. The checkpoint says "3 gaps"; today it is **4 gaps
+ 1 advisory**: checkpoint 4,608 (doc: 4,587), plan **1,835 (limit 1,200) — the fourth
gap, which the checkpoint's "re-run afterwards … 3 gaps" line cannot have seen**,
changelog "Recent changes" 1,583 as measured by the tool (doc: 1,549; true size 3,782,
see the bug above), `CLAUDE.md` 418 (doc: 418). `wc -l`: 4608 / 4759 / 418. The live
repo has moved by ~20 lines since the doc was written; the plan-size miss is a doc
defect, not drift.

**EveTradingbot** — `retrofit` exit 1, **15 gaps + 2 advisories**, matches. The seven
stray root files by `wc -l`: 320 + 226 + 210 + 204 + 196 + 172 + 177 = **1,505**, matches.
`VENDORED.md` (85 lines) and `README.md` are not flagged, which is right.

Nothing was written to either repository.

### A5. Judgement calls

- **`PLAN_MAX_LINES = 1200`.** Keep it. Both real plans (1,835; 2,960) exceed it, which
  is the point: they are past where the phase you need can be found, and both have
  finished phases that belong in the changelog. A limit under 1,000 would fire on a
  healthy mid-project plan; 1,200 fires only on the two shapes it was measured against.
  The one thing I would add is what the remedy already says — the fix is to move
  finished phases out, not to argue about the number.
- **The three advisories.** Two are right (gitignored allow-list; renamed state block —
  the block exists, and the remedy says rename it). The third, **stray root ledgers, I
  would reverse for the EveTradingbot shape**: seven prompt/brief files, 1,505 lines, at
  the root of a repo whose own `CLAUDE.md` forbids them, is the disease this tool exists
  to treat, and CI shrugging at it is the failure mode the INTERNALS entry warns about
  ("if an advisory is ever the thing that should have blocked a merge, it was the wrong
  status"). A defensible rule: advisory for one or two files, gap at three or more, or at
  more than 500 lines total. Not changed — it is a limit constant, so ask-first.
- **`git stash` on the deny-list.** Nothing in `templates/` still assumes stashing:
  every mention (`builder.md:41-42`, `settings.json:16-17,46`, `CLAUDE.md:142`,
  `AGENT_TEAM.md:68,136`, `INTERNALS.md:56,68`) is a prohibition. Holds.
- **Can a real agent follow `tester.md` without a question?** Two places it cannot, and
  both showed up in Part B: (1) "branch off `main`" — `main` does not exist in this repo;
  the lead had to name the base in the prompt. (2) "Toolchain: any Python 3.9+ on PATH"
  — there is no `python` on PATH here, and the bare 3.9 has no `pytest`; the lead had to
  hand over the `uv run` line. Both are placeholder fills (`{{MAIN_BRANCH}}`,
  `{{TOOLCHAIN}}`) that were filled with a wish rather than a measurement. The rest of
  the file is followable as written; its handoff format was returned verbatim.

### Other things found on the way

- `CHANGELOG.md` had a dated entry ("The questionnaire, asked one question at a time")
  appended **under "Retired or superseded implementations"**, outside the measured
  "Recent changes" section. Moved into "Recent changes" in this pass.
- `.claude/packets/` was gitignored, so no worktree agent could read a packet placed
  there. The `.gitignore` comment recommended tracking packets; un-ignored in `85b8474`.
- An untracked `.codex/agents/{builder,recon}.toml` pair exists at the repo root (created
  2026-09-03 13:12, not by this session). Not touched; the owner should say whether it is
  meant to be tracked.

---

## Part B — the loop on packet I1

The packet is [`.claude/packets/I1.md`](../../.claude/packets/I1.md): one item, a new
`audit_rule_evidence` finding under `check` (and in place of `retrofit`'s presence-only
one), with four tests specified and the fail-before-fix proof named. The ask-first ruling
is in its opening paragraph: **does not apply** — no limit constant changes, the rule is
already what `templates/CLAUDE.md:63` tells every downstream repo, and the owner
authorised the item in the committed brief. The packet template was usable as-is; the one
thing it lacked a slot for was "the base branch, because `main` does not exist", which
went into the opening paragraph.

### Recon (`recon`, cheap model)

One question, answered in 60 lines with `file:line` for every claim. Two facts it
surfaced that changed the packet: `check` and `retrofit` share no audit list (two attach
points, not one), and the only unmatched template citation sits inside an HTML comment
(so the check must strip comments or it fires on a correct template). Cost: ~42k tokens,
16 tool calls, 55 s.

### Tester (`tester`)

- **Read its role file and followed it**: the tests are in a file named for the packet,
  one per item, named for behaviour; the handoff came back in the role file's exact
  format with a `PASSES ALREADY (why)` line for the regression guard; it recorded each
  failure line in the commit message; it verified every `file:line` the packet cited
  and reported "premises that did not hold: none".
- **Where it went past its brief**: it built a throwaway prototype of the fix in a
  scratch directory to confirm the red tests *can* pass. Not on the branch, not
  committed, but it is the fix, written by the tester, and it cost tokens. The role file
  says "never write the fix"; the prototype is arguably the strongest check that a red
  test is red for the right reason, so this is a judgement for the owner: allow it
  explicitly, or forbid it explicitly. Today it is neither.
- **Genuinely red, reproduced by the lead** in a detached worktree at `e404283`:

  ```
  test_i1_rules_carry_evidence.py:123: AssertionError: assert 0 == 1
  test_i1_rules_carry_evidence.py:181: AttributeError: ... no attribute 'audit_rule_evidence'
  test_i1_rules_carry_evidence.py:217: AttributeError: ... no attribute 'audit_rule_evidence'
  3 failed, 50 passed in 2.91s — exit 1
  ```

  The fail-before-fix proof fails on **behaviour** (`check` exits 0 on a repo with a
  cited rule that has no entry), exactly as the packet required. The 49 existing tests
  stayed green.
- **Handoff vs diff**: `git diff --stat 85b8474..e404283` = one file, 264 lines,
  `tests/test_i1_rules_carry_evidence.py`. The handoff claimed exactly that.
- **Two things the lead had to do for it**: name the base branch (no `main`), and hand
  it the `uv run` test command (no `python` on PATH). After the tester finished, its
  worktree stayed registered with the packet branch checked out, which would have
  blocked the builder's checkout; the lead removed it.
- Cost: ~62k tokens, 32 tool calls, 5 min 51 s.

### Builder (`builder`)

- **Read its role file and followed it**: gave the pre-edit statement (item, what
  exists, what remains, files, ask-first ruling re-verified against the rule as
  written); restored the single file by path for the revert-and-rerun, never stashed;
  reconciled the docs on its branch in a second commit; handoff in the role file's
  format with `DEVIATIONS` and `BUILD TRIGGER` lines; pushed.
- **Where it did not**: the role file says "First command: `git checkout -b`"; the
  branch already existed, so the lead had to override that in the prompt. And one
  self-reported process error: `git checkout -- tools/jumpstart.py` after the revert
  discarded its own uncommitted fix, which it re-applied. No lasting effect, but it is
  exactly the kind of mistake the "restore by path" rule invites when the fix is not yet
  committed — worth one sentence in `builder.md`: commit the fix before proving it.
- **Did it weaken a tester's test? No.** `git diff e404283..6972b9f -- tests/`:
  28 insertions, **0 deletions**; the four tester tests are byte-identical. It added a
  fifth (`test_the_same_rule_cited_twice_counts_once`) for a case the packet left open,
  and said so.
- **Two deviations from the packet, both reported, both right**: it kept the
  presence-only finding as a fallback so `retrofit`'s check count cannot drop to 24 on
  a repo with `INTERNALS.md` but no `CLAUDE.md`; and it counts rules, not citations.
- **Handoff vs diff**: `677a5d2` = `tools/jumpstart.py` (+88/-1) and the test file
  (+28); `6972b9f` = `CHANGELOG.md`, `CURRENT_CHECKPOINT.md`, `plan.md`. The handoff
  named exactly those five files.
- **Green, reproduced by the lead** in a detached worktree at `677a5d2`:
  `54 passed` exit 0; `check .` **7 checks, no gaps** exit 0 with
  `[OK] rules carry evidence: 9 cited rule(s), each with an entry in docs/INTERNALS.md`;
  `retrofit .` 25 checks, 1 advisory, exit 0; ruff clean.
- **Gate 5, run by the lead with the branch's code** against a temp copy of this repo's
  `CLAUDE.md`/`AGENTS.md`/`docs/INTERNALS.md` with the `## Templates by nature` heading
  removed:

  ```
  [MISSING ] rules carry evidence: 1 cited rule(s) with no docs/INTERNALS.md entry: "templates by nature"
  ```

  exit 1 from both `check` and `retrofit`. Against the two live repositories, read-only:
  neither `CLAUDE.md` contains an `INTERNALS:` citation, so the finding stays where it
  was (`found DESK_INTERNALS.md` / `no docs/INTERNALS.md`) and nothing new fires. **Gate 5
  observed; the checkpoint row can close when the branch is merged.**
- Cost: ~92k tokens, 65 tool calls, 10 min 13 s.

### Reviewer (`reviewer`)

**Verdict: GO, blockers none, four advisories.** Branch `6972b9f`, left unmodified.

- **Reproduced, did not read.** Every number in its report is its own: 54 passed / exit
  0; 7 checks; 25 checks; `grep -c` 9 citations vs 9 headings independently of the tool;
  fail-before-fix re-proved by restoring `tools/jumpstart.py` from base by path (4
  failed, 1 passed, with the exit-code failure named as the behavioural proof); the
  test diff (28 insertions, 0 deletions); a sha256 manifest of its copy before and after
  `retrofit` to prove writes-nothing; and a probe the suite does not have — a raw
  `init` repo with placeholders unfilled reports `3 cited rule(s)` OK, proving the
  HTML-comment exclusion works on the shipped template.
- **It ran gate 5 its own way**: removed the `## An unpinned linter is not a gate`
  heading — chosen because that citation is the one wrapped across `CLAUDE.md:122-123`
  — and got the MISSING finding with the joined name and exit 1 from both commands.
  Better test data than the lead's.
- **It found something both the tester and the builder missed**: a tautology at
  `tests/test_i1_rules_carry_evidence.py:191` (`assert expected == 5` over two literals
  in the same file — trap 4). Harmless, since the load-bearing assertion is the next
  line, but it is exactly the kind of line principle 6 exists for. Also: heading
  extraction from `INTERNALS.md` does not strip comments the way citation extraction
  does (unreachable today), and the test re-derives the citation regex in a second
  spelling (guarded, but two spellings of one grammar).
- **Followed its role file**: GO/NO-GO block, blockers separated from advisories, ask-first
  re-checked by `git diff --name-only` (no `templates/`, no constant), docs checklist.
- Cost: ~72k tokens, 32 tool calls, 6 min 20 s.

### What prompted for permission

The lead ran in auto mode, and every agent ran in the harness's worktree isolation, so no
prompt reached the lead's transcript. The owner's terminal is the only record of what
prompted. **What the agents actually ran**, which is the allow-list a
`.claude/settings.json` on this machine should carry:

```
Bash(uv run --python 3.9 --with pytest python -m pytest*)
Bash(uvx ruff check*)
Bash(C:/Users/Aaron/AppData/Roaming/uv/python/cpython-3.9-windows-x86_64-none/python.exe tools/jumpstart.py*)
Bash(git status*)   Bash(git log*)   Bash(git diff*)   Bash(git show*)   Bash(git rev-parse*)
Bash(git checkout -b claude/*)   Bash(git checkout claude/*)   Bash(git checkout <sha> -- <path>)
Bash(git add *)   Bash(git commit *)   Bash(git push origin claude/*)   Bash(git push -u origin claude/*)
Bash(git worktree add*)   Bash(git worktree remove*)   Bash(git worktree prune)
Bash(sha256sum*)   Bash(grep*)   Bash(wc*)   Bash(cp *)   Bash(mkdir *)   Bash(sed -n*)
```

Deny, as `templates/.claude/settings.json` already does: `git stash*`, `git push --force*`,
`git reset --hard*`, `git clean*`, `git branch -D*`. Note the toolchain lines: the real
allow-list must name the `uv` and `uvx` forms, because the `python` and `ruff` forms the
role files assume do not exist on this machine's PATH.

### What it cost

| Run | Model tier | Tokens | Tool calls | Wall time | Could a cheaper agent have done it? |
|---|---|---|---|---|---|
| recon | sonnet | ~42k | 16 | 55 s | No — it was the cheap one, and it was enough |
| tester | opus | ~62k | 32 | 5 m 51 s | Partly: the prototype-of-the-fix step was extra |
| builder | opus | ~92k | 65 | 10 m 13 s | No; ~15 calls went to the self-inflicted revert |
| reviewer | opus | ~72k | 32 | 6 m 20 s | No — reproduction is the point, and it found the tautology |
| **total** | | **~268k** | **145** | **~23 min** | |

Plus the lead: Part A entirely by hand (worktrees, greps, hashes, two live-repo audits),
the packet, the file-path handoffs, and this report. Four agent runs for one packet is the
loop as designed; the one I would cut next time is nothing — but I would tell the tester
not to prototype, and the builder to commit before proving. Both are one sentence in a
role file, and both are ask-first (`templates/.claude/agents/*.md`), so they are
recorded here and not made.

### What was NOT done

- **Not merged.** `claude/i1-rules-carry-evidence` is at `6972b9f` on origin, GO from the
  reviewer, unmerged. Merging is the owner's call.
- **The reviewer's four advisories are not fixed** on the branch (the tautology at
  test line 191 is a one-line delete; the others are hardening). They belong in the fix
  round, if the owner wants one before merge.
- **Packet I2 is not written**: uncited bolded rules, and the `#19.` heading bug in
  `section_line_count`. Both are recorded in I1's "Still owed" and in the checkpoint.
- **No template or role file was changed** (ask-first). The three defects found in them
  are recorded above: `main` assumed, `python` on PATH assumed, tester prototyping
  unaddressed.
- **The stray-ledgers advisory is not promoted to a gap** — a limit-constant decision.
- **`.codex/agents/*.toml`** at the root is untracked and unexplained; left alone.
- **`main` still does not exist.** Every branch here is `claude/*` off
  `claude/jumpstarter-repo-setup-dn3rof`.
