# Plan — reload the SDE when a map table is empty, even if the stored build matches

## What is unclear or wrong in the task, and how it was resolved

- **"The stargate and NPC station tables"** — the task names those two, but its
  own note blesses the wider default. **Decision: any of the five tables the
  load fills** (`sde_types`, `sde_market_groups`, `sde_solar_systems`,
  `sde_stargates`, `sde_npc_stations`) counts as "empty means reload". One rule
  covers the reported case and the same failure shape in any other table, and
  it costs one small helper.
- **"Reload reuses an already-downloaded bundle for that build"** — no new code
  needed: the reload path already routes through `download_bundle`, which
  returns the existing non-empty `sde-{build}-jsonl.zip` without a request
  (`sde.py:91-93`). The plan only makes the reload happen; reuse comes free.
- **Where to put the loud-fail check** — the task says "if the *reloaded*
  bundle still yields no gates or stations". The reload path and the
  new-build path share one load tail, and a bundle that parses to zero gates
  is broken on every path (the router would be blind), so the check goes in
  the **shared tail, before any table write** — next to the existing
  no-types/no-groups check (`sde.py:301-302`). Consequences:
  - no partial writes on a broken bundle (the stamp is not touched, the tables
    are not touched, and the next refresh retries the reload and fails again —
    loudly, every time);
  - `tests/test_network_smoke.py`'s real-bundle load is unaffected (a real
    build carries gates and stations).
- **"No gates or stations"** is read as **either one** (OR): zero stargates
  breaks routing outright; zero NPC stations breaks every station lookup the
  hauling track uses. Both fail loudly.
- `sde_solar_systems` being empty triggers the **reload**, but the loud-fail
  check covers only stargates/stations — the task's stated scope. A bundle
  with no systems would still load "successfully"; recorded as an accepted
  scope line, not chased.
- **No phase/gate conflict**: this is a defect fix on the closed §23 H1a track
  (the map the tab reads), not a new phase; no locked decision in plan.md §11
  is touched, no formula or detector changes, no golden fixtures involved.

## Steps

1. **Tests first** (`tests/test_sde_map.py`, new section 4, fully offline):
   - Extend `_bundle()` with a `stations=None` override (signature grows,
     existing callers unchanged).
   - Helper `_stub_sde_network(monkeypatch, tmp_path, …)` monkeypatches
     `evescreener.sde.latest_build` (returns `3478781`) and
     `evescreener.sde.download_bundle` (returns a locally built bundle and
     counts calls).
   - Helper `_prime_same_build_map_except(db, table)` stamps
     `sde_build = 3478781` and fills four of the five SDE tables, leaving
     `table` empty (`table=None` fills all five).
   - `test_a_same_build_refresh_reloads_when_a_map_table_is_empty`,
     parametrized over `sde_stargates` / `sde_npc_stations`: one download,
     `result.downloaded is True`, both map tables filled, and — for the
     stargate case — `RouteGraph.from_db(db).route(30000142, 30000144).known`
     is `True` (the router finds the system, the task's headline outcome).
   - `test_a_same_build_refresh_still_no_ops_when_every_table_is_populated`:
     zero downloads, `result.downloaded is False`, counts preserved.
     (Green before the change — it pins the cheap path the fix must not
     regress; the two tests above are the red ones.)
   - `test_a_reloaded_bundle_with_no_stargates_fails_loudly` and
     `test_a_reloaded_bundle_with_no_npc_stations_fails_loudly`: the stubbed
     download answers with an empty-member bundle; `load_sde` raises
     `SdeError` (match "no stargates" / "no NPC stations") and writes nothing
     (table still empty, stamp unchanged, so the next refresh retries).
2. **Build** (`src/evescreener/sde.py` only):
   - New private helper `_sde_table_counts(db) -> dict[str, int]` counting all
     five tables the load fills.
   - `load_sde` no-op branch: fetch counts once; the skip condition becomes
     `stored and int(stored) == build and not force and all(counts.values())`,
     and the early result is built from those counts (replacing the five
     inline COUNT queries). Comment explains the rule: the stamp records a
     build, not a completed load.
   - Load tail: parse all remaining members first (`parse_solar_systems`,
     `parse_stargates`, `parse_npc_stations`), raise `SdeError` when
     `not stargate_rows or not station_rows`, **then** write the tables.
   - Update the module docstring line "re-running against the same build is a
     no-op" and the `load_sde` docstring to state the empty-table exception.
3. **Control files** (required by the project CLAUDE.md):
   - `CHANGELOG.md`: new dated entry (2026-10-26) at the top.
   - `CURRENT_CHECKPOINT.md`: new active item for this fix; the closed §23
     item moves to "Previous item". No new status files.
4. **Verify**: full suite + lint; record outputs.

## Files changed

- `src/evescreener/sde.py` — the fix.
- `tests/test_sde_map.py` — the tests.
- `CHANGELOG.md`, `CURRENT_CHECKPOINT.md` — control-file bookkeeping.

Nothing else. No schema change, no CLI change, no router change.

## "Done" means

- The two reload tests fail on the pre-change code (red) and pass after;
  the no-op test passes both before and after.
- A same-build refresh against a database with an empty stargate or NPC
  station table reloads the SDE (reusing the on-disk bundle for that build via
  `download_bundle`) and fills those tables, so `RouteGraph` knows the
  system again.
- A same-build refresh with every table populated still skips the download.
- A reloaded bundle with no gates or no stations raises `SdeError` before
  writing anything.
- `uv run pytest -q` fully green (offline by default) and
  `uv run ruff check . && uv run ruff format --check .` clean.
