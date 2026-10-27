# Recon — tape speed light (SPY M5 range vs session-hour norm, TICK fallback)

Read-only survey of everything the task touches. All line numbers from this worktree.

## 1. The existing TICK range light (the pattern to generalize)

`scripts/technical_integrity.py`:

- Constants block, lines 621–643:
  - `TICK_LIGHT_SCHEMA = "technical_integrity_tick_light_v1"` (622)
  - `SESSION_HOUR_TICK_RANGE_NORMS = {0: 389, 1: 415, 2: 385, 3: 371, 4: 350, 5: 354, 6: 401}` (639) — absolute TICK points, "same 25 sessions"
  - `TICK_LIGHT_WINDOW_MINUTES = 30`, `TICK_LIGHT_STALE_MINUTES = 15`, `TICK_LIGHT_MIN_BARS = 3`, `TICK_CONTRACT_SYMBOL = "TICK-NYSE"` (640–643)
- `_session_hour_index(moment)` (651–654): whole hours since that session's `open_local`; requires an aware datetime (naive−aware raises `TypeError`); `None` before the open.
- `_tick_bar(row)` (753–780): ledger row → `(start_local, end_local, high-low, stamped_end)` or `None`; requires `event_type == "breadth_bar"`, `contract.symbol == "TICK-NYSE"`, tz-aware `bar_start` ("a naive stamp is ambiguous: unknown, never a guess", line 763).
- `tick_range_light(tick_rows, *, as_of, window_minutes=30)` (783–833): window = completed bars with `start < bar_end <= moment` (800); per-bar hour norm looked up at `bar_start` (802–805); result dict: `schema, as_of, bar_count, range_mean, expected_range, ratio, light, last_bar_end` (+ `reason` when unknown); rounding: `range_mean`/`expected_range` to 1 decimal, `ratio` to 4; light = "calm" if ratio < 0.8, "wide" if > 1.25, else "normal" (832); reasons: "no TICK bars in the window" / "newest TICK bar is older than 15 minutes" / "fewer than 3 TICK bars in the window".
- Module docstring (1–11): decision-support only; nothing here may change watchlists/alerts/order state.

## 2. The monitor and the snapshot publish (fail-open pattern)

`scripts/technical_integrity.py`:

- `TechnicalIntegrityMonitor.__init__` (1403–1433): keyword-only; `tick_rows_provider: Callable[[], Iterable[Mapping[str, Any]]] | None = None` (1411), stored as `self.tick_rows_provider = tick_rows_provider or _default_tick_rows` (1413).
- `_publish_snapshot(self, as_of, market_environment)` (1667–1697):
  - comment 1677–1678: "The 'now' reading and the TICK light ride on the published snapshot only … Both fail open: a bad read never costs the snapshot."
  - rolling try/except (1679–1684, `note_swallowed(...)` non-quiet); tick try/except (1685–1695, `note_swallowed(..., quiet=True)`), fallback dict `{"schema": TICK_LIGHT_SCHEMA, "as_of": str(as_of), "bar_count": 0, "light": "unknown", "reason": f"TICK read failed: {exc}"}`; then `_atomic_write_json(self.snapshot_path, snapshot)` (1696).
- `note_swallowed` imported from `swallowed` at line 38.

## 3. The chip and tooltip (the "tape fast/normal/calm" surface)

`scripts/technical_integrity.py`:

- `_rolling_now_view(market)` (2850–2910) builds the chip: `chip = f"Technicals now: {part('D1', d1)} · {part('M5', m5)}"` (2882) then the tick block (2889–2903): `chip += f" · TICK {light}"` when known; tooltip line `f"TICK (last {TICK_LIGHT_WINDOW_MINUTES} min): range {…:.0f} vs {…:.0f} usual = {light} (levels fail more when TICK is wide)."`; unknown line `f"TICK (last 30 min): unknown (+ reason)."`.
- Returned chip/tooltip/headline are consumed at `scripts/ui/app.py:793` and `scripts/ui/panels/bounce_panel.py:404` (both just display the returned strings).
- Day-cumulative path (`_day_cumulative_view`, 2913+) does not read `market.tick`/`market.tape` at all, so old snapshots without a tape block are unaffected.

## 4. The legacy call site and the SPY bar cache

`scripts/bounce_bot_lib/legacy.py`:

- `_get_technical_integrity_monitor()` (3253–3266): lazily creates `TechnicalIntegrityMonitor()` with no providers — this is the one-line wiring site; `self.latest_bars` is a plain dict created at 3168.
- SPY M5 cache key read as `self.latest_bars.get("SPY|5 D|5 mins")` at lines 7422, 8272, 12352 (cache only, never IB).
- `IbBar` dataclass (2143–2149): fields `dt, open, high, low, close, volume=0.0`; `dt` is naive market-local time. So the spy provider will be called with `IbBar` objects (attribute access) — the parser must handle both attribute rows and Mapping rows.

## 5. The chip/tooltip test and the golden fixture

- `tests/test_technical_integrity_rolling.py`:
  - `_snapshot_at(fixture, case)` (43–55) sets `snapshot["market"]["rolling"]` and `["tick"]` only.
  - `test_chip_and_tooltip_lead_with_the_now_reading_golden` (87–105) pins `case["chip"]` and `case["tooltip_head"]` line-by-line.
  - Monitor wiring tests: `test_publish_snapshot_survives_a_raising_tick_provider` (229–242), `test_publish_snapshot_reads_the_vold_ledger_by_default` (245–258); `_monitor(tmp_path, **kwargs)` helper (218–226).
  - `test_tick_light_thresholds` (268–285): parametrized 300→calm, 415→normal, 530→wide at as_of `2026-10-05T10:55:00-04:00` — these pin the wrapper contract and must keep passing.
- `tests/fixtures/technical_integrity_rolling_v1.json`:
  - raw inputs = `events` + `tick_rows` only (`raw_input_keys`, line 4–6); `raw_input_sha256` (line 8) is recomputed over the raw inputs on every load (`tests/conftest.py:708` `load_fixture_contract`), so **expected values may be edited, raw inputs may not**.
  - case 1 (as_of 11:00): tick `{bar_count: 6, range_mean: 566.7, expected_range: 415.0, ratio: 1.3655, light: "wide", last_bar_end: …11:00}`; chip `"Technicals now: D1 VERY WEAK 2.2/10 · M5 STRONG 9.1/10 · TICK wide"`; tooltip_head[3] `"TICK (last 30 min): range 567 vs 415 usual = wide (levels fail more when TICK is wide)."`; head[4] is `"Today so far:"`.
  - case 2 (11:50): tick `{bar_count: 0, light: "unknown"}`, chip without a light part; no tooltip_head.
  - case 3 (11:25): tick `{bar_count: 2, light: "unknown", …}`; no chip/tooltip.
- `tests/test_technical_integrity.py` formatter tests (720–735, 831–882, 901–918) use the day-cumulative path (no `rolling` key → `_rolling_now_view` returns None at 2855–2856); they never read `market.tick`/`market.tape`. Unaffected.

## 6. Timezone conventions (verified in `scripts/market_session.py`)

- `normalize_market_local_datetime` (114–131): naive → stamped with the market-local (machine) tz; aware → `astimezone(local_tz)`.
- `get_market_session_window` (134–151): normalizes the reference to the local tz, converts to `America/New_York` for `market_date`, returns `open_local/close_local` in the local tz.
- Consequence: **all comparisons are instant-based, so tz-aware ET (`-04:00`) stamps in tests are machine-tz independent**; naive stamps are machine-dependent (existing tests therefore use aware `-04:00` stamps throughout).
- `_parse_datetime` (`technical_integrity.py:214–234`) handles `datetime`, pandas stamps, ISO strings; returns `None` when unparseable.

## 7. SPY per-session-hour norm derivation (task: "30 sessions ending 2026-10-05, derive or stub them clearly")

Local SPY M5 history exists only for **4 sessions** in the read-only live store
`C:\TradingBotData\data\runtime\m5_bars\` (daily files 2026-09-30 → 2026-10-27, but only
2026-09-30, 10-01, 10-02, 10-05 have full 78-bar SPY sessions; the rest are empty/partial).
The 30-session window cannot be derived locally; the norms below are derived from the 4
available sessions and will be clearly labeled as a short-window stub.

Method: per session, per session hour h (bar start in [09:30+h, 10:30+h) ET; hour 6 =
15:30–16:00), mean of `(high-low)/close*100` over completed M5 bars with finite OHLC,
`close > 0`, `low <= high`, inside the regular session; then mean across the 4 sessions.
(78 bars per session, all 7 hours present in every session.)

| hour | per-session means | constant |
|---|---|---|
| 0 | 0.1094, 0.1942, 0.1188, 0.0889 | 0.1278 |
| 1 | 0.1087, 0.1342, 0.1231, 0.0574 | 0.1058 |
| 2 | 0.0833, 0.1104, 0.0896, 0.0417 | 0.0813 |
| 3 | 0.0676, 0.1084, 0.0871, 0.0386 | 0.0754 |
| 4 | 0.0602, 0.1141, 0.0675, 0.0357 | 0.0694 |
| 5 | 0.0585, 0.0726, 0.0458, 0.0493 | 0.0566 |
| 6 | 0.1224, 0.0872, 0.0641, 0.0727 | 0.0866 |

Units: percent of close per completed M5 bar, matching the task's "(high-low)/close*100".

## 8. Docs / rules

- `CHANGELOG.md` line 3 (2026-10-05) documents the original TICK light. No `docs/RULES.md`
  line governs the Technical Integrity range lights (the `docs/RULES.md` "TICK" mentions are
  the unrelated UVXY signal rule), so no RULES.md change is needed; a CHANGELOG.md line is
  still required by AGENTS.md "After a change".
- Task's "don't touch" list honored: no order/sizing code, no IB connection code (the
  provider reads the in-memory `latest_bars` cache only), TICK thresholds unchanged, other
  snapshot fields untouched.
