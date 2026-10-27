TASK

Goal: the "bounces failing" levels read must work for shorts too and say whether levels hold IN GENERAL, not just long bounces. The rolling D1/M5 readings gain support (approach side above) and resistance (below) sub-reads scored against side norms per session hour (m5_above/m5_below/d1_above/d1_below; derive or stub the norm table clearly); the pooled numbers and the "all" read stay unchanged. technicals_verdict returns LEVELS FAILING / LEVELS HOLDING / SUPPORT FAILING / RESISTANCE FAILING / LEVELS NORMAL / BUILDING: both sides scored decide, a fast tape overrides, a building side or an older snapshot without sub-reads falls back to the pooled M5 rule; BOUNCES FAILING/WORKING are gone. Chip "Levels: V · M5 sup n res n · D1 sup n res n · tape x", tooltip side lines after each pooled line. The Mentor int:levels row carries side keys and "; support n, resistance n" in its text, older snapshot text unchanged; the lens names the failing side and says "levels are holding" for the firm bucket.
Done when: tests cover the sub-reads, every verdict word, the fallback for old snapshots, the chip and Mentor text, and a trend hour (supports hold, resistances break) reads RESISTANCE FAILING end to end; run_tests.py/pytest and ruff green.
Files: scripts/technical_integrity.py (rolling readings, technicals_verdict, chip); find the Mentor int:levels row and the lens.
Don't touch: order/sizing code, the pooled numbers, the golden fixture's events and raw_input_sha256, other Mentor rows.
Pattern: the existing pooled M5/D1 read and its golden fixture tests (tests/test_technical_integrity_rolling.py).

Follow the procedure at the top of CLAUDE.md (recon, plan, tests first, build, self-review, report). Stop when
`.qo/report.md` is written.
