# Recon — reload the SDE when a map table is empty

Read-only recon, 2026-10-26. All paths relative to the repo root.

## The failure chain

1. **The router reads only the SDE map tables.** `RouteGraph.from_db` builds the
   gate graph from `db.stargate_edges()` and the build stamp from the
   `sde_build` meta — `src/evescreener/routes.py:209-216`. A system that is not
   in `known_systems` gets `RouteFacts.unknown(...)` with the reason
   `"… is not in the stargate graph — run `sde` to rebuild the map"` —
   `src/evescreener/routes.py:267-276`.
2. **Hauling turns that into NO_ROUTE.** `hauling.py:908-918`: when
   `not graph.knows(profile.current_system)` the scan is rejected with
   `NO_ROUTE` and the detail
   `"current system {id} is not in the stargate graph — run `sde` …"` —
   `src/evescreener/hauling.py:910`. Same message in `tests/test_hauling.py:220`
   and `tests/test_routes.py:145`.
3. **The refresh that could fix it skips.** `load_sde` —
   `src/evescreener/sde.py:258-320` — when the stored build equals the latest
   build and `force` is not set, returns a no-op immediately
   (`sde.py:276-277`), reporting only the current table counts
   (`sde.py:280-292`). It never checks whether those counts are non-zero, so a
   build stamp set by a load that left `sde_stargates` / `sde_npc_stations`
   (or any other SDE table) empty survives every later refresh.

## How the state gets that way (verified in the test suite, not just asserted)

- `sde_stargates` and `sde_npc_stations` were added to the schema after the
  operator's deployed `state.db` existed. `CREATE TABLE IF NOT EXISTS` creates
  them **empty** on an existing database — demonstrated by
  `test_an_existing_database_gains_the_new_column_without_losing_a_row`
  (`tests/test_sde_map.py:179-201`, asserts `db.stargate_edges() == []` and
  `db.station_systems() == {}` after the migration).
- A load that ran before those tables existed stamped `sde_build` with the
  then-current build. When the build number still matches, `load_sde`
  no-ops forever and the map can never fill. This matches the reported
  symptom exactly.

## The five tables the load fills

All in the `Database` schema — `src/evescreener/store/db.py:57-101`:
`sde_types` (57), `sde_solar_systems` (72), `sde_stargates` (84),
`sde_npc_stations` (94), `sde_market_groups` (132). `load_sde` fills all five
and then stamps the build — `src/evescreener/sde.py:303-309`:
`replace_types`, `replace_market_groups`, `replace_solar_systems`,
`replace_stargates`, `replace_npc_stations`, then `db.set_meta("sde_build", …)`.

Replacers: `db.py:416-471` — each deletes and re-inserts inside one
transaction and returns the resulting count.

## Existing guards, and the gap

- `parse_stargates` raises `SdeError` when the member has gates but **none
  resolve** — `sde.py:219-223`. But when the member is **empty** (`raw == []`)
  it returns `([], 0)` silently — `sde.py:219` guards only on `raw and not
  rows`.
- `parse_npc_stations` can return `[]` with no error at all —
  `sde.py:227-255`.
- `load_sde` raises on empty types or market groups from the bundle —
  `sde.py:301-302` — but has **no check that the map (stargates, stations,
  systems) came back non-empty**.
- The no-op path's correctness claim, "same build = the load already happened,"
  is therefore false for any table the stamping load never filled.

## The network doors (what tests must close)

- `latest_build` — `sde.py:70-83` — GETs `config.sde.latest_url`.
- `download_bundle` — `sde.py:86-111` — streams the build's zip; **an existing
  bundle for that build is reused** without a request (`sde.py:91-93`:
  `if target.exists() and target.stat().st_size > 0: return target`). This is
  the constraint "a reload reuses an already-downloaded bundle for that build":
  the reload path already routes through `download_bundle`, so reuse is free.
- Existing SDE tests stay offline by passing `bundle_path=` (which bypasses
  both doors — `sde.py:267-273`): `tests/test_sde_map.py:141-151`. The new
  tests need the network path *without* network, so they stub
  `evescreener.sde.latest_build` and `evescreener.sde.download_bundle`
  (monkeypatch), keeping `load_sde(config, db)` on its normal entry.
- `tests/test_network_smoke.py:191-201` drives `load_sde` with a real bundle
  (marked `network`, deselected by default); a real bundle carries gates and
  stations, so the new loud-fail check cannot trip it.

## Callers of `load_sde`

- `cli.py:421-429` — `_cmd_sde`: `load_sde(config, db, force=args.force,
  bundle_path=…)` then prints `result.as_dict()`. The CLI surfaces a raised
  `SdeError` as a traceback exit; that is the "fail loudly" surface.
- `tests/test_sde_map.py:142,156` and `tests/test_network_smoke.py:200`
  (above). No other callers.

## Fixtures available to the new tests

- `db` — `tests/conftest.py:43-47`: a `Database` on a fresh tmp path, full
  schema. `config` — `tests/conftest.py:30-34`: example config with
  `data_dir` under `tmp_path`, so `config.paths.ensure().sde` is a tmp dir and
  `config.paths.sde` is a pure `Path` build. No network fixture exists or is
  needed.
- `tests/test_sde_map.py:42-88` — `TYPES`/`GROUPS`/`SYSTEMS`/`STARGATES`/
  `STATIONS` record shapes (verified against build 3478781) and `_bundle()`
  (76-88), which writes a zip containing all five members; `_bundle` today
  accepts only a `stargates=` override.

## Baseline

`pytest tests/test_sde_map.py -q` → **9 passed** (1.14 s), pre-change.

## What the change must do (evidence-backed)

1. In `load_sde`, replace the no-op condition's blind trust in the stamp with
   a count of every table the load fills; an empty one forces the same
   download-and-load path a new build would take (reusing `download_bundle`'s
   existing-bundle reuse).
2. In the shared load tail, treat a bundle whose parsed stargates **or**
   stations are empty as a loud `SdeError` (before any table write, next to
   the existing no-types/no-groups check at `sde.py:301-302`).
3. Tests: (a) same-build refresh with empty `sde_stargates` reloads and the
   router then finds the system; (b) same with empty `sde_npc_stations`;
   (c) same-build refresh with all tables populated still skips the download;
   (d) a reloaded bundle with an empty stargate/station member raises
   `SdeError` and writes nothing.
