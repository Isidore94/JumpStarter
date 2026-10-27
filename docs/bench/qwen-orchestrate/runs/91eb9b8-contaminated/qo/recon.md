# Recon — reload the SDE when a map table is empty

## Symptom chain (verified in code)

1. `load_sde` (src/evescreener/sde.py:258) is the SDE refresher. With no
   `bundle_path` it looks up the latest build (sde.py:275) and, if the stored
   `sde_build` meta equals it and `force` is off, returns a **cheap no-op**
   straight from the database table counts (sde.py:276–295). The build stamp is
   the only evidence of completeness — **nothing checks the tables**.
2. The map the router reads lives in `sde_stargates` / `sde_npc_stations`
   (schema: store/db.py:84–101). Those tables were added by H1a; on a deployed
   `state.db` they arrive via `CREATE TABLE IF NOT EXISTS` (store/db.py:256)
   — created **empty**, while the `sde_build` meta still carries the stamp of
   a pre-H1a load that only filled types/groups/systems.
3. Same stamp ⇒ no-op ⇒ the map tables stay empty forever. `RouteGraph.from_db`
   (routes.py:205–215) reads an empty graph, and hauling ends with
   `NO_ROUTE` — `hauling.py:910`: *"current system 30000142 is not in the
   stargate graph"* (same phrasing at routes.py:273).

## The load path today (sde.py)

- `latest_build` (70–83): GETs `config.sde.latest_url`, parses `buildNumber`.
- `download_bundle` (86–111): **reuses an on-disk bundle for the build**
  (lines 92–93: existing non-zero `sde-{build}-jsonl.zip` is returned without
  any request). This is what "a reload reuses an already-downloaded bundle"
  already means.
- `load_sde` (258–320): two entry paths (operator `bundle_path`, or
  latest-build + download). The full parse/replace block (299–308) fills all
  five tables: `sde_types`, `sde_market_groups`, `sde_solar_systems`,
  `sde_stargates`, `sde_npc_stations`. Loud check exists **only** for
  types/groups (301–302). `parse_stargates` (191–224) fails when records exist
  but none resolve — but an **empty** `mapStargates.jsonl` yields `([], 0)`
  silently. `parse_npc_stations` (227–255) has no empty-guard at all.
  `db.set_meta("sde_build", ...)` at 309.

## Callers / consumers

- Only production caller of `load_sde` without `bundle_path`: the `sde` CLI
  command (cli.py:421–429). `test_network_smoke.py:194–200` uses a local
  bundle under `@pytest.mark.network` (unaffected by this change; both paths
  keep working).
- Consumers of the map tables: `RouteGraph.from_db` (routes.py:205–215),
  `db.stargate_edges` / `db.station_systems` (store/db.py:495–509),
  hauling.py:873.

## Tests and fixtures

- `tests/test_sde_map.py`: parsers, end-to-end load, migration. The `_bundle`
  helper (lines 76–88) writes a build-3478781 zip with all five members;
  `stargates=` already parameterizes the gate member. No test today touches
  the build-stamp no-op or an empty map table.
- `tests/conftest.py:31–47`: `config` (data dir under `tmp_path/data`,
  example config) and `db` (real `Database` on `tmp_path/data/state.db`).
  Both offline.
- The file to extend is `tests/test_sde_map.py`; monkeypatching
  `evescreener.sde.latest_build` / `.download_bundle` keeps the new tests
  fully offline, matching how this module already avoids the network
  (`bundle_path=` in existing tests).

## Environment (verified, non-obvious)

- The job's pinned interpreter `C:/Users/Aaron/EveTradingbot/.venv` is an
  **editable** install whose `.pth` points at `C:\Users\Aaron\EveTradingbot\src`
  — the main checkout, which is **ahead of this worktree's baseline** and
  already contains a partial variant of this fix (`SDE_TABLES` +
  `_tables_populated` gating the no-op; **no** fail-loud check; tests for
  only the two reload/no-op cases). To test *this* worktree's code, the
  command needs `PYTHONPATH=<worktree>/src` ahead of the site-packages path.
  All test/lint commands below use that override; nothing outside this
  directory is modified.
- The main-checkout reference confirms the intended semantics (any of the
  five tables empty ⇒ reload) but not the task's fail-loud note; this build
  implements both.

## Invariant check

- Read-only public data: unchanged (same endpoints, same self-caps).
- Never fetch before expiry: no new fetch is introduced. The reload path uses
  `download_bundle`, which returns the on-disk bundle for that build without
  a request when one exists (sde.py:92–93).
- No detector/formula change; no golden fixtures involved.
