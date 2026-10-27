TASK

Goal: the screen's net_edge_pct flatters wide books. It is expected_move_pct minus breakeven_move_pct, but those two are measured against different reference points (the close and the bid), so a wide spread's cost is understated and a wide book can rank first. Price the real round trip multiplicatively instead: target_bid = vwap x (bid_walk / close); net_edge = sell proceeds at target_bid / ask_walk - 1 (the book keeps its shape as price reverts; say that assumption in a comment). A flat book already at value must net exactly minus the tax.
Done when: tests/test_screen_digest.py has a wide-spread candidate that no longer ranks first and a flat-book case that nets -tax; `PYTHONPATH=src python -m pytest -q` green, ruff clean.
Files: src/evescreener/screen.py (run_screen, the net_edge_pct line); find the helpers it needs.
Don't touch: the other gates, the digest output format, the candidate sort.
Pattern: the existing breakeven_move_pct / tiers maths in screen.py.

Follow the procedure at the top of CLAUDE.md (recon, plan, tests first, build, self-review, report). Stop when
`.qo/report.md` is written.
