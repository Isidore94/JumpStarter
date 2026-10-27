# Plan — setup tier A/B/C/D for M5 bounce alerts

Active work item: the TASK packet ("M5 bounce alerts get a setup tier A/B/C/D"). No matching
`STATUS.md`/`TODO.md` line; the research basis is TODO.md "Phase S" findings F2-F5 and F15
(learning letter does not separate outcomes; bar hour, family, tape-vs-side do). Governing
rules: no detector/scoring/alert behaviour change without fixtures first — authorized here by
the task itself; `legacy.py` is ask-first — authorized by the task naming it. Ask-first:
satisfied (task is the trader's word).

## Decisions where the task was open (recorded, no one to ask)

1. **Point values.** The task fixes the boundary map `4/3/2/1/0/-1 -> A/B/C/D` but not the
   per-fact points. I assign **±1 per fact** (neutral/unknown 0): max total 4 means A = all
   four facts aligned, and `>=4 A, >=3 B, >=2 C, <=1 D` makes the listed boundaries exact
   (4→A, 3→B, 2→C, 1/0/-1 and below→D). Reachable totals: -3..+4.
2. **Bar hour (fact 1).** Session-local hour via `market_session.get_market_session_window`
   (same naive/aware handling as `learning.time_bucket_for`, learning.py:283-309):
   - hour 9 (09:00-09:59) → **-1** — the opening hour is the worst slice (TODO.md F5:
     36.3% win, EOD -0.31R);
   - hour 10-14 → **+1** — mid-session 47-48% (F5);
   - hour 15, off-window hours, unresolvable day, `when=None` → **0** — unknown is never
     confirmed (invariant).
3. **Bounce family (fact 2).** From the bounce types (list or ";" string, case-insensitive):
   - any type containing `regime` (`regime_pause_rs/rw/...`) → **+1** — fastest producer
     (F15/F3);
   - any type exactly `h1_green_to_yellow` → **-1** — slowest producer (F15: 5% reach +1R
     inside the hour);
   - otherwise → 0.
   - With several types, the best row wins: **regime beats h1_green_to_yellow** (the task's
     exact ordering requirement).
4. **Sector RRS present (fact 3).** The event row's `rrs_sector` (the threshold-crosser
   field scoring already treats as "a presence check worth +4", legacy.py:4139) is non-blank
   → **+1**; blank/absent → 0 (absence is unknown, not negative). NOT the
   `rrs_sector_measured` twin, which is "never read by scoring" (legacy.py:4141-4143).
5. **Internals tape vs side (fact 4).** The row's `internals_tape`
   (market_internals.py:153-160) against the side (case-insensitive):
   - `risk_on`/`risk_on_tilt` with long, `risk_off`/`risk_off_tilt` with short → **+1**;
   - `risk_on*` with short, `risk_off*` with long → **-1**;
   - `mixed` (the neutral tape) → **0** ("neutral tapes score 0");
   - `""`/`unknown`/unrecognized tape or missing/unrecognized side → 0.
6. **Reason text.** Exactly one reason per table row, in table order
   (bar hour, bounce family, sector RRS, internals tape), e.g.
   `"mid-session bar (10:xx-14:xx): +1"`.
7. **Hook shape.** The returned quality dict gains two tier fields; `tier` becomes the
   setup letter; everything else (muted, mute_reasons, shadow_s9, reasons, proven,
   proven_reasons, composite_r) is untouched:
   - `quality["learning_tier"]` = the learning letter (the old `tier` value, "B" on the
     failure fallback — "falls back to learning_tier B");
   - `quality["setup_tier"]` = the rule result `{"tier", "points", "reasons"}`;
   - `quality["tier"]` = the rule's tier, **computed from the event row even when learning
     raises** (the rule needs no state) — "with the rule's tier" on the fallback;
   - if the rule itself throws, the dict keeps the learning `tier` and has no
     `setup_tier` key (learning must never block an alert; the rule is advisory).
   - `shadow_s9` still attaches only on the learning-success path, as today.
8. **record_alert_tier.** The `tier_assigned` row gains `learning_tier` (after `tier`;
   JSONL ledger, additive, no migration). The row's `tier` now carries the setup letter.
9. **Tests that pin the old hook shape** (AGENTS.md: list them when a word reverses a rule):
   - `tests/test_s9_shadow_tier.py::test_alert_quality_carries_the_shadow_beside_the_unchanged_live_verdict`
   - `tests/test_s9_p14_tier_golden.py::test_the_bot_seam_keeps_live_tier_text_and_mutes_with_extreme_regime_segments`
   Both assert `quality == learning-output` after popping `shadow_s9`, and the golden one
   additionally pins the message prefix to the learning letter. Updated minimally: the
   learning verdict, its mutes/reasons/proven/composite and the whole message body stay
   asserted byte-identical; only the two new tier fields and the `[X-TIER]` prefix move.
   All other hook-touching tests stub the hook or call learning directly — untouched.

## Files

- NEW `scripts/bounce_bot_lib/setup_tier.py` — pure rule, no I/O, no learning state.
- `scripts/bounce_bot_lib/legacy.py` — `_evaluate_bounce_alert_quality`,
  `record_alert_tier`, new private helper `_setup_tier_for_alert`.
- NEW `tests/test_setup_tier.py` — table terms, boundaries, shapes, hook tests.
- UPDATED `tests/test_s9_shadow_tier.py`, `tests/test_s9_p14_tier_golden.py` (decision 9).
- `scripts/bounce_bot_lib/learning.py` — read only, not touched.

## Steps

1. Write `tests/test_setup_tier.py` (failing): every table term and boundary + the hook
   tests (alert dict: setup tier shown, learning_tier kept, muted/mute_reasons/shadow_s9/
   reasons unchanged; fallback path; recorded row carries learning_tier). Run, save red
   output to `.qo/tests-red.txt`.
2. Implement `scripts/bounce_bot_lib/setup_tier.py` (`evaluate_setup_tier`).
3. Wire the hook + ledger row in `legacy.py`.
4. Update the two pinned tests (decision 9).
5. Run: `pytest -q tests/test_setup_tier.py tests/test_s9_shadow_tier.py
   tests/test_s9_p14_tier_golden.py tests/test_outcome_registration_context.py`
   (QT_QPA_PLATFORM=offscreen, the TradingBotV3 venv — worktrees have no .venv) and
   `ruff check scripts tests`. Save to `.qo/build.txt`. Never the full suite.
6. Self-review the diff; write `.qo/review.json`.
7. `.qo/report.md`, stop.

## Done means

- `tests/test_setup_tier.py` passes and covers: every table term (all four facts, every
  branch including neutral/unknown/case/";" string/regime-beats), every boundary
  (4→A, 3→B, 2→C, 1→D, 0→D, -1→D), the reason-order invariant, and the legacy hook
  (alert dict + recorded row + fallback).
- The two updated golden tests pass with the learning letter, mutes, reasons, proven
  floor and message body still asserted identical.
- `pytest` (the four files above) and `ruff check scripts tests` green; exit codes checked,
  not piped tails.

## Skipped / not in scope

- Order/sizing code, mute rules, `learning.py`'s letter/thresholds, alert payload keys other
  than the tier fields (all off-limits per the task).
- No CHANGELOG/STATUS edit (no commit from this sandbox; the desk checkout stays untouched).
- Full-suite run (forbidden here), frozen exe build (no dependency/asset changes).
