# qwen-trial-min: Qwen 3.8 27B fp4, minimal brief, Haiku medium gate

Job `qwen-trial-min`, 2026-10-27, lead Claude Fable 5.1. Ten replay tasks, each sourced from a merged commit
with tests and checked out at its parent; the real diff is the reference. The builder got a 5-8 line brief
written without lead recon (`briefs/`, `requests.md`), Qwen 3.8 27B fp4 via OpenRouter (ModelRun, throughput
sort), up to 4 passes, Haiku 5.5 medium as the gate, Opus 5.5 high as the blind judge. Harness: `run-task.sh`,
`proxy.js`, `packet.sh`; prompts in `prompts/`; every run's transcript, diff, tests and verdicts in `runs/`.

## Per-task table

| # | task | repo | ref size | brief lines | brief cost | Qwen passes | Haiku medium | Haiku high (rerun) | hidden ref | Opus | Qwen $ | min |
|---|------|------|----------|-------------|------------|-------------|--------------|--------------------|------------|------|--------|-----|
| 1 | cs-108c631 | ContentSummarizer | 4 files +231/-6 | 6 | 0.9 min | 1 | GO | GO | 29/36 (naming) | MINOR | 0.28 | 6.2 |
| 2 | eve-66905ff | EveTradingbot | 2 files +111/-2 | 5 | 0.9 min | 1 | GO | GO | 20/24 (private name) | MERGE | 0.51 | 10 |
| 3 | eve-ce70d4c | EveTradingbot | 2 files +111/-15 | 5 | 0.9 min | 1 | GO | GO | 29/29 | MERGE | 0.23 | 4 |
| 4 | js-96eb4eb | JumpStarter | 32 files +738/-66 | 5 | 0.9 min | 2 (turn cap, rework) | GO | NO-GO | 6/11 | MAJOR | 1.26 | 14+3 |
| 5 | tth-56c399a | TraderTaxHelper | 7 files +109/-11 | 5 | 0.9 min | 1 | GO | NO-GO | 35/37 (2 behavioural) | MAJOR | 0.67 | 11 |
| 6 | tbv3-243279e2 | TradingBotV3 | 5 files +355/-50 | 6 | 0.5 min | 1 | GO (5 adv) | – | 14/18 (as_of kwarg) | MINOR | 1.01 | 12.6 |
| 7 | tbv3-b4c56626 | TradingBotV3 | 4 files +461/-3 | 5 | 0.5 min | 2 | NO-GO / NO-GO / NO-GO (r1, r3 false; r2 real, fixed) | – | 5/21 (names, date fmt) | MINOR -> MINOR | 1.01 | 12.5 + 2.8 |
| 8 | tbv3-4b830d03 | TradingBotV3 | 12 files +4283/-3 | 6 | 0.5 min | 1 | GO (5 adv) | – | 0/3 (import name; point table guessed) | MAJOR | 0.93 | 17.2 |
| 9 | tbv3-51c27bf1 | TradingBotV3 | 8 files +598/-68 | 5 | 0.5 min | 1 (cut off: OpenRouter 402) | NO-GO (3 real: own tests red) | – | 397/459 (HOLDING vs NORMAL rule, helper signature, wording) | MAJOR | 0.78 | 11.5 |
| 10 | tbv3-697d8828 | TradingBotV3 | (swing Focus SMA guard) | 5 | 0.5 min | skipped: $7.50 cap ($7.04 spent) and OpenRouter credits exhausted on run 9 | – | – | – | – | 0 | – |

Brief cost: batch 1 took 4.5 min of lead time for five briefs, batch 2 (TBV3) 2.5 min for five; about 1k
tokens read and under 1k written per brief, no recon. Qwen $ is OpenRouter spend per run from the proxy's
usage log; $0.36 of Darkbloom timeouts on tasks 1-2 (before the throughput sort) is counted in the total but
not in the rows. Hidden ref = the reference commit's own tests run against Qwen's code, never fed back.
Haiku high column: Aaron asked at 11:15 PT for the finished tasks to be re-reviewed at effort high on the
same packets (`review-high.json`); the medium verdicts (`review-r1.json`) were the live gate.

## Comparison with qwen-trial-10 (full brief, Haiku high gate)

| | qwen-trial-10 (full brief, lead recon) | qwen-trial-min (5-8 line brief, no recon) |
|---|---|---|
| runs | 10 | 9 (run 10 skipped for the $7.50 cap) |
| Opus verdicts | 2 MERGE / 7 MINOR / 1 MAJOR | 2 MERGE / 3 MINOR / 4 MAJOR over 9 (other repos: 2 MERGE, 1 MINOR, 2 MAJOR; TBV3: 2 MINOR, 2 MAJOR) |
| gate | Haiku high: 6 GO / 4 NO-GO | Haiku medium: 7 GO / 2 NO-GO (run 7 three rounds, two false; run 9 three real blockers) |
| OpenRouter | $5.16, about $0.52 a run | $7.04, about $0.78 a run (incl. $0.36 timeouts) |
| wall time | S 3-12 min, M 6-17 min | S/M other repos 4-14 min, TBV3 12-17 min first pass, rework about 3 min |
| brief cost | full recon + packet (tens of minutes of lead time) | 0.5-0.9 min of lead time each, no recon |

Reading: the minimal brief costs about a tenth of the lead time and loses about one grade on the harder
tasks. Where the full brief carried public names, formats and tables, Qwen matched the reference; where
the minimal brief left them out, Qwen invented its own and the hidden tests failed on interfaces, not logic.

## Failures by cause

**Brief too thin (the dominant cause, 5 of 9 runs lost a grade to it).**
- Public names the hidden tests import: `tape_light(as_of=)` (run 6), `stamp_m30_extended_pullbacks` /
  `evaluate_extended_pullback` (run 7), `setup_tier` with `setup_score`/`setup_reasons` (run 8), the
  private helper name in run 2, the ContentSummarizer naming in run 1.
- Return and date formats: run 7 returned datetimes where the reference returns (date, evaluate_at).
- Concrete tables and ids: run 8's point table (hour 7/8 +2, hour 12 -2, regime +2, A>=4/B>=2/C>=0) was
  never in the brief, so Qwen guessed a +/-1 table and locked it in with 35 passing tests; the only
  MAJOR on TBV3 that is not a harness problem.
- Files outside the brief's list that the change must touch (run 4's 32-file diff; run 8's two pinned
  s9 tests).
**Qwen error (behaviour wrong despite a sufficient brief).**
- Run 5: two behavioural misses in TraderTaxHelper that the brief did cover (Opus MAJOR).
- Run 7: per-symbol conversion and judge outside the try block (real NO-GO, fixed in one rework).
- Run 8: `regime` substring match instead of the exact `regime_pause_rs`; hour from `signal_time` instead
  of the bounce bar. Neither flagged in its self-review.
- Qwen never says "the brief does not give X"; it picks a value and moves on (brief_awareness 0-2 on every
  TBV3 run). That is the trait a minimal brief cannot survive without a gate.
**Harness / provider (not the builder).**
- Darkbloom timeouts before the throughput sort ($0.36).
- 80-turn cap hit on runs 4 and 7 (no self-review on those first passes).
- CLAUDE.md and `.claude/agents` edits are harness setup but show in the diff (one Haiku false flag).
- Leak audit false positives when Qwen quotes rule text.
- OpenRouter 402 (account credits exhausted) cut run 9 at turn 135: 3 of its own tests red, no rework
  possible, and run 10 could not start. The harness has no per-run cost cap or credit check.
- TBV3 parents predate `scripts/run_tests.py`, so the harness ran the whole suite under `-n 4`: 0 GB free on
  run 6, a Windows access violation in an unrelated Qt test on run 7, 17-20 minute suites. Worktrees lack
  git history, so 3 history-reading tests fail on every TBV3 run.

## Gate: Haiku medium vs high

- Other repos (runs 1-5): medium GO 5/5; the high rerun flagged runs 4 and 5 NO-GO, and Opus judged both
  MAJOR. Medium missed both real failures.
- TBV3 (runs 6-9): medium GO on runs 6, 8; NO-GO on run 9 with 3 real blockers (its own red tests, build cut off by a 402); NO-GO three rounds on run 7, of which two rounds were
  false (claimed code missing that already existed at the parent; claimed a False-vs-None defect that
  matches the reference). Run 8 was a GO on a build Opus called MAJOR.
- Net: Haiku medium caught real blockers on runs 7 and 9 (both were red own tests, the easy case) and
  produced 2 false blockers; it passed the MAJORs on runs 4, 5 and 8, where the code ran but did the
  wrong thing. As the only gate on a minimal brief it is too weak; the lead reproduced every NO-GO before
  any rework and that reproduction is what kept the false flags from costing a pass.

## What the minimal brief must always include

1. Every public name the change exports or the callers use (function, kwargs, dict keys, event names,
   file names). One line, copied from the issue or decided by the lead; this is the cheapest line and
   it was behind most hidden-test failures.
2. Return shapes and date/number formats (date vs datetime, string vs tuple).
3. Any table of constants verbatim (points, thresholds, norms). Never "derive or stub it".
4. Every file the change must touch, including existing tests that will change.
5. "If the brief does not give a value you need, stop and say so" plus the don't-touch list.
Five to eight lines still fit; the lead reads the issue, not the code.

## Cost

| | |
|---|---|
| OpenRouter, 9 runs + timeouts | $7.04 of the $7.50 cap (run 10 skipped) |
| Claude, lead session (Fable 5.1, 545 turns, list price) | about $74.89, mostly cache reads |
| Claude, subagents (Haiku medium gates, Haiku high reruns, Opus judges, Opus test setup) | at least $2.56 visible in this session's task transcripts; the rest is not attributable per session |

The Claude figure is a list-price equivalent from the session transcript using usage-attrib's price
table; `usage-attrib.js` has no per-session view, so the project-wide 7-day row mixes this job with others.
The lead cost went into reproducing blockers, reading diffs and running TBV3 suites, not into briefs.

## Verdict

**No, not as the default builder; yes as a cheap first try on small non-trading jobs in the other repos.**

- Other repos, S/M tasks (runs 1-5): 2 MERGE, 1 MINOR, 2 MAJOR. The two MAJORs were a 32-file JumpStarter change
  (too big for 5 lines and for 80 turns) and a tax-rule change where Qwen got two behaviours wrong. The three
  good ones cost $0.23-0.51 and 4-10 minutes. With the brief rules above, this tier works.
- TradingBotV3 (runs 6-9): 0 MERGE, 2 MINOR, 2 MAJOR, $0.78-1.01 each, 12-17 minutes a first pass. The plumbing
  was right every time; the content (a point table, a verdict rule, public names, date formats) was guessed
  whenever the brief left it out, and Qwen never said it was guessing. A reviewer reading the diff cannot tell
  a guessed table from a given one, so the gate does not recover this. TBV3 needs the full brief (or the lead
  pastes the issue text verbatim, which carries the tables) and an Opus builder for anything with a rule in it.
- The gate: Haiku medium is not enough on its own. It passed two MAJORs the Haiku high rerun caught, and it
  false-flagged two rounds on run 7. Keep Haiku high (or Opus for trading logic) as the gate, and keep the
  lead reproducing every blocker before a rework; that reproduction took 5-10 minutes a round and saved two
  wasted passes.
- One rework pass is the right budget: it fixed the only real NO-GO that could be reworked (run 7) for $0.14
  in 3 minutes.
- Cloud backup: it was needed on 4 of 9 runs. The minimal brief moves lead time from writing (0.5 min a brief)
  to verifying (hours of reproduction and babysitting across the day). It is cheaper in Claude usage only if
  the lead does not have to read the diff; with Haiku medium as the gate, it did.
- Harness before any rerun: a per-run cost cap and a credit check (run 9 died on a 402 at $7.04), targeted own
  tests when the parent lacks run_tests.py, and git-show access to history in the worktree.

Caveats: nine runs, one per task, run on one day; three TBV3 first passes were cut short by the turn cap or the
402, so TBV3 scores are a floor, not a measurement of a finished build.
