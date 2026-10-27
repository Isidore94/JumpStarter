TASK

Goal: M5 bounce alerts get a setup tier A/B/C/D from a rule on four facts: bar hour, bounce family, sector RRS present, and internals tape vs side. The learning letter from learning.evaluate_bounce_quality does not separate outcomes (23-28% for every letter) but those four facts do; keep the old letter beside the new one as learning_tier. The tier is a point table: tier boundaries 4/3/2/1/0/-1 -> A/B/C/D, the reason text listed in table order, side case-insensitive, when=None allowed, bounce types as a list or a ";" string, neutral tapes score 0, regime beats h1_green_to_yellow.
_evaluate_bounce_alert_quality shows the setup tier, keeps the learning letter as learning_tier, leaves muted / mute_reasons / shadow_s9 and the rest unchanged, and falls back to learning_tier B with the rule's tier when learning raises; record_alert_tier's row carries learning_tier.
Done when: tests/test_setup_tier.py covers every table term and boundary, a legacy-hook test covers the alert dict and the recorded row, and run_tests.py/pytest plus ruff are green.
Files: new scripts/bounce_bot_lib/setup_tier.py; scripts/bounce_bot_lib/legacy.py (_evaluate_bounce_alert_quality, record_alert_tier); scripts/bounce_bot_lib/learning.py (read only).
Don't touch: order/sizing code, the muting rules, learning.py's letter, the alert payload keys other than the tier fields.
Pattern: learning.evaluate_bounce_quality's shape (tier, reasons) and the existing legacy hook tests.

Follow the procedure at the top of CLAUDE.md (recon, plan, tests first, build, self-review, report). Stop when
`.qo/report.md` is written.
