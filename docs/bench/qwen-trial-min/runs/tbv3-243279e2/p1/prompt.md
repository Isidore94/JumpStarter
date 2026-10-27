TASK

Goal: the Technical Integrity "tape" light should read SPY's own completed-M5 range against a per-session-hour norm, with the TICK range light as the fallback. Measured over 139 session-hours SPY M5 range (high-low)/close*100 vs its hour norm is the cleanest tape-speed signal (leads next-hour level respect r=-0.56; TICK and VXX add nothing). Keep the thresholds: calm < 0.8, fast > 1.25 of norm, unknown under 3 bars or a bar older than 15 min.
Make a generic tape_speed_light() for a completed-M5 range against a per-hour norm; tick_range_light() becomes a thin wrapper over it. Add SPY per-session-hour range norms (30 sessions ending 2026-10-05, derive or stub them clearly). tape_light() uses SPY when known, else the TICK light (wide = fast, source "TICK"), else source "none" with the SPY reason. The monitor gets a spy_bars_provider and writes market.tape fail-open (a raising provider falls back to TICK), still writing market.tick as before; legacy.py wires it in one line reading the latest_bars cache only, never IB. The chip says "tape fast/normal/calm" (omitted when source is none) and the tooltip names SPY or "TICK fallback".
Done when: new tests cover the light, the fallback order, the fail-open monitor write and the chip text, and `python scripts/run_tests.py` (or pytest on tests/) plus ruff are green.
Files: scripts/technical_integrity.py (tick_range_light, tape light, _publish_snapshot); find the chip and legacy.py call site.
Don't touch: order/sizing code, IB connection code, the existing TICK thresholds, other snapshot fields.
Pattern: copy tick_range_light() and its existing tests; the monitor provider follows the existing bars provider hooks.

Follow the procedure at the top of CLAUDE.md (recon, plan, tests first, build, self-review, report). Stop when
`.qo/report.md` is written.
