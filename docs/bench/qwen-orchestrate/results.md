# Can Qwen 3.8 27B orchestrate? Bench results (2026-10-27)

Question (Aaron, 2026-10-26): can Qwen 3.8 27B run a whole coding job itself: recon, plan, tests first, build,
self-review. Method: three merged commits from non-trading repos replayed from a brief that Opus 5.5 wrote from
what Aaron would have typed (`requests.md`, `briefs/`). Qwen (`qwen/qwen3.8-27b` on OpenRouter, driven by Claude Code
headless with every model slot pointed at it) saw only the brief and the tree at the parent commit, in a throwaway
worktree. The real diff is the answer key. Two blind graders (Haiku 5.5 medium, Opus 5.5 high) scored each run from
`prompts/grader.md` without being told which model ran. Two runs also got a seeded bug before a second self-review.
Harness: `run-orchestrate.sh`, `seed-review.sh`, run folders under `runs/`.

## Per-task results

Scores are 0-3 in the order correctness / completeness / tests / scope / brief awareness / self-review.
Cost is the OpenRouter key delta; "main" is the orchestration run, "review" the separate self-review pass(es).

| Task | Attempt | Time | Turns | $ main | $ review | Own tests | Ref tests | Ruff | Leak | Self-review (unseeded) | Self-review (seeded) | Haiku grade | Opus grade | Agree |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 677a5d2 JumpStarter: `check` must read INTERNALS entries | 1 (`:floor` route) | 45 min, timed out | 56 | 0.29 | - | stub only | - | - | - | NO-GO | - | not graded | not graded | - |
| same | 2 (`:nitro`) | 10.8 min | 138 | 0.55 | 0.11 | pass (baseline-red self-check only, harness artefact) | 1 fail: names `audit_rule_evidence`, candidate chose another name | clean | 0 (by hand) | GO, 0 blockers | GO; names the seeded greedy regex as an advisory | MINOR 2/3/2/2/3/1 | MERGE 3/3/3/3/3/1 | verdict differs, self-review agrees |
| d756e9d TraderTaxHelper: P&L before commissions on the Summary | 1 (`:nitro`) | 7.3 min | 93 | 0.28 | 0.13 | 48 passed | 16/17: 1 fail on field name `commission_cad` vs candidate's `commissions_cad` | clean | 0 | GO, 2 true advisories (option roll-in drops commission; tautological asserts) | NO-GO, names gains.py:206 exactly, reproduces the wrong number, states the fix | MINOR 2/3/2/2/2/3 | MINOR 2/3/3/3/3/3 | verdict agrees |
| 91eb9b8 EveTradingbot: reload the SDE when a table is empty | 1, CONTAMINATED | 14.2 min | 181 | 0.74 | 0.29 | 1089 passed | 11/11 | clean | 0 reported, 11 real | GO, 2 true advisories | - | MERGE 3/3/3/3/3/3 | MERGE 3/3/3/3/3/3, flags the contamination | both MERGE; Opus alone saw the leak |
| same | 2 (rerun, PYTHONPATH pinned) | 6.3 min | 175 | 0.62 | 0.14 | 1089 passed | 11/11 | clean | 0 (by hand: no repo path, no reference names) | GO, 3 true advisories (route_cache delete beyond the letter of the task; zero-system bundle not loud; stale module docstring) | - | MERGE 3/3/3/2/3/3 | MERGE 3/3/3/3/3/3 | verdict agrees; Haiku docks scope for the route_cache delete, Opus calls it justified |

Total OpenRouter spend for the job: $3.21 of the $5 cap (includes the timed-out attempt and the contaminated run).

### What the graders found, per run

- **677a5d2.** The candidate added the INTERNALS cross-check with its own function name and a comment-stripping regex.
  Opus: as good as the reference. Haiku: minor, wanted a two-comment regex test and objected to harness text in
  CURRENT_CHECKPOINT. The seeded bug (greedy HTML-comment regex) was spotted by the self-review but filed as a
  "latent" advisory under a GO, so both graders scored self-review 1.
- **d756e9d.** Correct pro-rata commission carry on the pool, four new report fields, one Summary card with the
  "do not add them again" line. Both graders: MINOR. Opus's gap: option roll-in drops the commission (the
  self-review had already flagged it). Haiku's extra scope claim (a second card and a 6-column grid) is false: the
  pages.py hunk adds one card. Logged as a Haiku grader false flag. Seeded self-review was exact.
- **91eb9b8, attempt 1.** The EveTradingbot venv is an editable install, so `import evescreener` resolved to the main
  checkout, which already contains the reference fix. Qwen's recon followed the import, read it, noted in recon.md
  that the main checkout "already contains a partial variant of this fix", pinned PYTHONPATH to the worktree for its
  own test runs (correctly), and wrote a helper whose docstring is near-verbatim the reference's. The leak audit only
  watched for git history and `../..`, so it reported 0. The Opus grader caught it; Haiku did not. Shelved as
  `runs/91eb9b8-contaminated/`. The runner now sets `PYTHONPATH=src` and the leak audit counts any source-repo path
  in the transcript (0 on runs 1 and 2, 11 on this one).
- **91eb9b8, rerun.** Clean. Qwen wrote `_SDE_TABLES` + `_sde_table_counts` (its own names and docstring, nothing from the reference), added the
  loud-fail on an empty reloaded map that the brief asked for and the reference skipped, and invalidated `route_cache` on
  map-rewriting loads. Both graders: MERGE. Their one disagreement is that delete: Haiku scores it as scope cost (2), Opus as
  justified (3) because a cached `NO_ROUTE` keyed by build would otherwise outlive the reload. Both note the self-review
  disclosed it. Reference tests 11/11, own 1089 passed, ruff clean, 0 leak hits by hand.

## How Qwen "orchestrated"

- It followed the staged procedure (recon, plan, red tests, build, review, report) in every completed run and wrote
  every `.qo/` stage file. It did not delegate: 0 Agent-tool calls in runs 1 and 3 (both attempts), 1 in run 2. It is a solo worker
  following a checklist, not a lead spawning roles.
- Plans recorded real decisions about the brief (table scope, naming, where the card goes); brief awareness scored
  3 from Opus on every run.
- Tests were written first and shown red in every run (tests-red.txt), then kept passing; no existing test was
  weakened.
- Self-review by reproduction is real: it reverts the patch in a scratch copy, re-runs, and re-derives numbers. But
  it is not a safe sole gate: 1 of 2 seeded bugs got a NO-GO, the other was named and waved through as an advisory.
- Time and cost: 6-11 min and $0.4-0.8 per task (run plus self-review) on the `:nitro` route. Output is thinking-heavy (run 1: 90k output
  tokens, 70k of them thinking); `--effort low` changed nothing.

## Harness findings (for the next bench)

1. `:floor` (cheapest provider, ~14 tok/s) cannot finish a run inside 45 min; `:nitro` is 4-6x faster for the same price class.
2. Editable installs leak the live repo into the worktree. Pin `PYTHONPATH` and audit for the source-repo path.
3. The leak regex `git (log|show|reflog)|\.\./\.\.` false-positives on Qwen's reasoning text; verify hits by hand.
4. JumpStarter runs start red on `check .` and `test_jumpstarter_passes_its_own_check` because the harness prepends
   rules to CLAUDE.md and copies template agents with placeholders. `diff.patch` excludes CLAUDE.md for that reason
   (saved as `diff-claude-md.patch`).
5. Grader blindness is leaky: run folders name the runtime in plumbing files; graders are told to ignore them.
6. Reference tests are name-sensitive (two of three runs lost a ref test to a naming choice); graders weigh code.
7. Haiku as grader: one false scope flag in three runs and it missed the contamination; Opus caught both. Use Opus
   (or two graders and read the disagreement) when a verdict matters.
8. The `result` line of a stream-json transcript is the only reliable usage figure, and it was partial for the
   181-turn run; cost by key delta is the number to trust.

## Verdict

Qwen 3.8 27B can carry a routine, well-briefed, non-trading job end to end. All three valid `:nitro` runs produced a
diff that both graders rated mergeable or mergeable with minor fixes (MERGE/MINOR, MINOR/MINOR, MERGE/MERGE), with real
tests written first and shown red, the hidden reference tests passing in 2 of 3 runs (the third lost one test to a field
name), lint clean, and a self-review that reproduces its own numbers. Each run took 6-11 minutes and $0.4-0.8 all-in.

It does not orchestrate in the team sense. It never delegated (0 Agent-tool calls in 3 of 4 completed runs), so there was
no independent tester or reviewer: it is one worker following the staged checklist. That shows in the self-review as a
gate: of the two seeded bugs, one got an exact NO-GO and the other was named but waved through as an advisory under a GO.
It reads the brief critically (brief awareness 3/3 from Opus on every run) and records its decisions, which is the part
of orchestration it does well. Haiku as a grader was weaker than Opus (one false scope flag, missed the contamination).

## Recommended tier rule (proposal only; no live pipeline change without Aaron's word)

Proposed tier, below the existing Haiku-solo trial tier and only if Aaron adopts it:

- **Qwen-solo orchestrator** for Sonnet-tier packets: pattern-copy or small-feature jobs, no trading logic or order/sizing
  code, about 3 files or fewer, a brief that states done-when items. Runs through `run-orchestrate.sh`-style plumbing on
  the `:nitro` route with `PYTHONPATH` pinned, a 15-minute / $1 cap per run, and shelve on any leak hit.
- **The gate stays independent.** The existing Haiku 5.5 medium reviewer (Opus high for anything it doubts) reviews the
  diff plus tests by reproduction and decides GO / NO-GO. Qwen's own `review.json` is advisory only, because it names
  defects it then waves through.
- **Not for** trading logic, jobs where the brief itself might be wrong in a way that needs judgement, or anything where a
  reference-compatible name or interface matters (it picks its own names).
- Log every run in triage-log.md as `[qwen-orch]` with time, OpenRouter $ and the reviewer verdict, and reassess after
  about 10 runs against the Haiku-solo rows.
