# Recon — M5 bounce alerts get a rule setup tier (A/B/C/D) beside the learning letter

Read-only. All evidence file:line in this checkout.

## The learning letter (what the old `tier` is today)

- `scripts/bounce_bot_lib/learning.py:312-435` — `evaluate_bounce_quality(state, *, direction,
  bounce_types, time_bucket, market_environment, priority_bucket, focus_label, bounce_combo,
  setup_family, swing_traits) -> dict`. Returns `{"tier", "composite_r", "muted",
  "mute_reasons", "reasons"[:4], "proven", "proven_reasons"[:3]}` (learning.py:427-435).
  Letter ladder S/A/B/C/D from `TIER_THRESHOLDS` (learning.py:52); no-evidence fallback is B
  (learning.py:412-413); mute forces D (learning.py:410-411). This is the letter the task
  keeps as `learning_tier`.
- `learning.py` is read-only for this task (its letter, thresholds, mute and proven logic are
  off-limits per the task's Don't-touch list).

## The legacy hook to change

- `scripts/bounce_bot_lib/legacy.py:4191-4225` — `BounceBot._evaluate_bounce_alert_quality(
  self, direction, levels, event_row)`:
  - builds `context` from `event_row` (market_environment, priority bucket, focus label,
    `"+".join(bounce_type_keys)` combo, setup family) at legacy.py:4204-4215;
  - `when = _bounce_quality_time(row) or get_market_local_now()` (legacy.py:4203);
  - on ANY exception returns `{"tier": "B", "muted": False, "mute_reasons": [], "reasons": []}`
    immediately (legacy.py:4221-4223);
  - on success attaches `quality["shadow_s9"] = self._shadow_s9_tier(state, context, when)`
    (legacy.py:4224). `_shadow_s9_tier` (legacy.py:4227-4237) swallows all failures and
    returns `{}`.
- `scripts/bounce_bot_lib/legacy.py:5430-5465` — `BounceBot.record_alert_tier(self, event_id,
  quality)`: appends a `tier_assigned` row to the append-only outcome ledger
  (`self._outcome_ledger()`, legacy.py:3892-3918; JSONL stream, `evidence_ledger.py:159-226`
  — one JSON object per line, no fixed column set, so a new key is additive, no migration).
  Row keys today: `event_type, event_id, tier, muted, proven, shadow_tier, banger, reason`
  (legacy.py:5447-5462).

## The four facts are all already on the event row

`_log_bounce_candidate_event` writes the row (legacy.py:4480-4584):
- `signal_time` — the bar time, ISO seconds, `""` when unparseable (legacy.py:4530);
  `_bounce_quality_time` (legacy.py:1412-1421) reads `signal_time`/`entry_time`/`bar_time`/
  `timestamp` -> datetime or None.
- `bounce_types` — `";".join(...)` of the level keys (legacy.py:4534);
  `_bounce_type_keys_from_levels` (legacy.py:1369-1377).
- `rrs_sector` — the threshold-crosser reading, `""` when absent (legacy.py:4550). The
  measurement twin `rrs_sector_measured` (legacy.py:4552) is "Measurement-only ... Never read
  by scoring" (legacy.py:4137-4143) — not the fact to use.
- `internals_tape` — market-internals tape label (legacy.py:4554); values come from
  `market_internals.build_internals_snapshot` (market_internals.py:148-166):
  `unknown / risk_on / risk_off / mixed / risk_on_tilt / risk_off_tilt`; flat field name set at
  market_internals.py:189.
- `market_environment` (legacy.py:4561) values `bearish_strong / bearish_weak /
  bullish_strong / bullish_weak / neutral_chop` (legacy.py:453-462) — the SPY regime; the
  task's "internals tape" is the `internals_tape` fact, so this one is not the tier input.

Call sites (all follow the same two-line pattern): legacy.py:7799-7800, 8672-8673,
8815-8816, 9035-9036, 9200-9201, 9321-9322, 9436-9437, 13845-13846.

## Consumers of `quality["tier"]` (what changes when the letter moves)

- `_format_bounce_alert_message` (legacy.py:1496-1536) prints `[X-TIER] ...` from
  `quality.get("tier")` (legacy.py:1507-1508) — this is where the alert "shows" the tier.
- `log_bounce_to_file` (legacy.py:14990-15052) writes the `tier` column of
  `INTRADAY_BOUNCES_CSV` from `quality.get("tier")` (legacy.py:14996).
- `record_alert_tier` (legacy.py:5440) — intended change.
- The tier-flip path calls `learning.evaluate_bounce_quality` DIRECTLY, not the hook
  (legacy.py:6895-6905), so it is unaffected.
- No UI panel reads the `tier_assigned` ledger rows by `learning_tier` today (grep: only
  legacy.py:5449 and tests/test_outcome_registration_context.py:130 reference the event type).

## Tests that pin the OLD hook shape (the task reverses this rule)

- `tests/test_s9_shadow_tier.py:151-169` —
  `test_alert_quality_carries_the_shadow_beside_the_unchanged_live_verdict`: pops `shadow_s9`
  and asserts the remaining dict == `learning.evaluate_bounce_quality(...)` exactly.
- `tests/test_s9_p14_tier_golden.py:138-171` —
  `test_the_bot_seam_keeps_live_tier_text_and_mutes_with_extreme_regime_segments`: pops
  `shadow_s9`, asserts `quality == EXPECTED[id]["quality"]` (frozen learning verdict, 280
  cases from `tests/fixtures/s9_p14_tier_golden_v1.json`), and asserts the alert MESSAGE is
  byte-identical to the golden text (prefix `[<learning tier>-TIER]`).
- `tests/test_outcome_registration_context.py:124-150` — `record_alert_tier` rows: checks
  `event_type/event_id/tier/proven` only; a new `learning_tier` key stays green.
- Everything else stubs the hook (`bot._evaluate_bounce_alert_quality = lambda ...:
  {"tier": "B"}` in tests/audit_m5_support.py:418,659; test_bounce_learning.py:2212;
  test_bounce_h1_color_sweep_golden.py:102; test_h1_entry_time_is_the_bar_close.py:65;
  test_r5_confluence_and_orb_wiring.py:116; test_r5_lrsi_cross_wiring.py:87) or calls
  `learning.evaluate_bounce_quality` directly — unaffected.

## Timezone handling precedent

- `learning.time_bucket_for` (learning.py:283-309) takes the session window from
  `market_session.get_market_session_window(reference=when)`; naive `when` is assumed to be
  session-local (`moment.replace(tzinfo=session.open_local.tzinfo)`), aware is
  `astimezone`; any failure -> "unknown". M5 bars are naive market-local time
  (AGENTS.md "Live bot, cached M5 bars"). The new bar-hour fact follows the same handling.
- `market_session.get_market_local_timezone` (market_session.py:82-104) is the DESK's local
  zone — wrong for a bar hour on a Pacific desk; the session-local hour is the fact.

## Precedents / names

- `scripts/setup_points.py` — the D1 setup point system (different feature; presentation
  only). Its one-part-per-input + named notes shape is the closest house pattern, but its
  inputs are D1 scan fields, not this task's four M5 facts.
- `scripts/long_setups.py:548` — an unrelated `setup_tier(row)` function (D1 promotion tier);
  no collision with the new `bounce_bot_lib.setup_tier` module.
- `.qo/` exists and is empty. `scripts/bounce_bot_lib/legacy.py` is ruff-excluded
  (pyproject.toml:36) but lint must still pass for the new module and the tests
  (line-length 120, py312).
- `legacy.py` is ask-first (AGENTS.md); the task names it explicitly, so the edit is
  authorized. No order/sizing code, mute rules, or `learning.py` letter is touched.

## Gaps / open questions (resolved in plan.md)

1. The task fixes the boundary map (4/3/2/1/0/-1 -> A/B/C/D) but not the per-fact points;
   no in-repo spec of the four-facts table exists (grep: none; TODO.md F2-F5, F15 are the
   research basis).
2. `when=None` allowed, side case-insensitive, bounce types list-or-";" string, neutral
   tape 0, "regime beats h1_green_to_yellow" — all must be honored by the pure rule.
