# Report — M5 bounce alerts get a setup tier A/B/C/D beside the learning letter

## What changed

- **NEW `scripts/bounce_bot_lib/setup_tier.py`** — the pure four-facts rule
  (`evaluate_setup_tier`, `tier_for_points`):
  - **bar hour** (session-local, via `market_session.get_market_session_window`, same
    naive/aware handling as `learning.time_bucket_for`): opening hour −1,
    mid-session +1, last hour 0, off-window/None/unresolvable 0 (unknown, never
    confirmed);
  - **bounce family** (list or ";" string, case-insensitive): any type containing
    `regime` +1, exactly `h1_green_to_yellow` −1, else 0; with several types the best
    wins — regime beats h1_green_to_yellow;
  - **sector RRS present** (the `rrs_sector` threshold-crosser field, not the
    measurement twin): +1 / 0;
  - **internals tape vs side** (both case-insensitive): risk_on\*/long and
    risk_off\*/short +1, the opposite −1, `mixed` 0, unknown tape or side 0.
  - Points sum over the table (reachable −3..+4); boundaries 4/3/2/1/0/−1 →
    A/B/C/D/D/D; exactly one reason per table row, in table order. No I/O, no
    learning state, never raises.
- **`scripts/bounce_bot_lib/legacy.py`**:
  - `_evaluate_bounce_alert_quality` now shows the setup tier: `quality["tier"]` is
    the rule's letter; the learning letter is kept as `quality["learning_tier"]`;
    `quality["setup_tier"]` carries the full rule result. `muted`, `mute_reasons`,
    `shadow_s9`, `reasons`, `proven`, `proven_reasons`, `composite_r` are untouched.
    When learning raises, the dict falls back to `learning_tier` "B" **with the
    rule's tier** (the rule needs no state); if the rule itself fails, the dict
    keeps the learning tier and has no `setup_tier` key. `shadow_s9` still attaches
    only on the learning-success path.
  - new `_setup_tier_for_alert` static helper (staticmethod to match the
    `_shadow_s9_tier` calling convention used by the pinned tests): reads the four
    facts from the event row, falls back to the level keys when `bounce_types` is
    blank, and deliberately does **not** fall back to "now" for the bar time — an
    unknown bar hour scores 0.
  - `record_alert_tier`: the `tier_assigned` row carries `learning_tier` (additive
    JSONL key, no migration).
- **`tests/test_setup_tier.py` (NEW, 35 tests)** — every table term (all four facts,
  every branch incl. neutral/unknown/case/";"-string/regime-beats/aware time),
  every boundary (4→A, 3→B, 2→C, 1→D, 0→D, −1→D, plus −2/−3), the reason-order
  invariant, the result shape, and the legacy hook: the alert dict (setup tier
  shown, learning letter kept, muted/mute_reasons/shadow_s9/reasons/proven/
  composite asserted identical to a direct `learning.evaluate_bounce_quality`
  call), the learning-raise fallback (learning_tier "B" + the rule's tier), the
  rule-failure path (learning verdict untouched, no `setup_tier` key), and the
  recorded row carrying `learning_tier` (plus a verdict without one).
- **`tests/test_s9_shadow_tier.py`, `tests/test_s9_p14_tier_golden.py`** (the two
  tests pinning the old hook shape, listed per AGENTS.md) — updated minimally:
  the learning verdict, its mutes/reasons/proven floor and the whole message body
  stay asserted byte-identical; only the two new tier fields and the `[X-TIER]`
  prefix move. The golden seam test additionally pins the setup points per case
  (the 10:00 bar +1, the family ±1, no RRS/tape on the rows).

## Test results (exit codes checked, not piped tails)

- Red first: `tests/test_setup_tier.py` failed at collection
  (`ImportError: cannot import name 'setup_tier'`), exit 2 — saved to
  `.qo/tests-red.txt`.
- Green: `pytest -q tests/test_setup_tier.py tests/test_s9_shadow_tier.py
  tests/test_s9_p14_tier_golden.py tests/test_outcome_registration_context.py`
  → **66 passed**, exit 0.
- Neighboring areas (extra): `tests/test_bounce_learning.py
  tests/test_learning_shadow_refresh.py` → **85 passed**, exit 0.
- Lint: `ruff check scripts tests` → clean, exit 0.
- Saved to `.qo/build.txt`.

All runs used the TradingBotV3 venv python (worktrees have no `.venv`) and
`QT_QPA_PLATFORM=offscreen`. Full suite not run (forbidden in this job: 20 GB /
12 min).

## What was skipped / not in scope

- Order/sizing code, the muting rules, `learning.py`'s letter/thresholds, and
  alert payload keys other than the tier fields — off-limits per the task.
- CHANGELOG/STATUS edits, commit and push — this job must not run git history,
  stash, checkout or commit commands.
- Frozen-exe build — no new dependency, asset or packaging trigger touched.

## Open doubts

- The task fixes the boundary map but not the per-fact points; ±1 per fact and
  the session-relative hour buckets are recorded as decisions 1–2 in
  `.qo/plan.md` (research basis TODO.md F2–F5, F15). If the trader wants
  different weights, only `setup_tier.py` and its tests move.
- From the cutover on, the M5 alert letter and the CSV `tier` column no longer
  include "S"; historical rows keep the learning letter (append-only stores
  stay as written).
