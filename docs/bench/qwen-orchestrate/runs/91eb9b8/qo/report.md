# Report — reload the SDE when a map table is empty, even if the stored build matches

## What changed

**`src/evescreener/sde.py`** (the only product file touched):

1. **The no-op condition now checks the map, not just the stamp.** `load_sde`
   counts all five tables the load fills (`_sde_table_counts`, over the
   `_SDE_TABLES` tuple: types, market groups, solar systems, stargates, NPC
   stations) and skips the download only when the stored build matches *and*
   every one of them is populated. An empty table sends the refresh down the
   normal download-and-load path, which routes through `download_bundle` —
   so a same-build reload **reuses the already-downloaded
   `sde-<build>-jsonl.zip` when it is on disk** and otherwise downloads it
   once. No fetch happens against ESI's cache rules; the build lookup and the
   bundle URL are the only two network doors, unchanged.
2. **A reload that lands on an empty map fails loudly.** The load tail now
   parses all members before writing anything and raises `SdeError`
   ("…carried no stargates / no NPC stations — loading it would leave the map
   empty and the router blind") when the parsed stargates **or** stations are
   empty. The check sits next to the pre-existing no-types/no-groups guard.
   Because it raises before any write, a broken bundle leaves the stamp and
   every table untouched and the next refresh retries the same reload.
3. **The reload invalidates that build's cached routes.** `route_cache` is
   keyed by build (a cached route "must never outlive the map it was computed
   on", `store/db.py` and plan.md §23.8). A same-build reload rewrites the map
   under an unchanged key, so a `NO_ROUTE` cached against the empty map would
   otherwise survive the fix; a load that rewrites the map now deletes that
   build's `route_cache` rows. The no-op path writes nothing, cache included
   (pinned by a test).

**`tests/test_sde_map.py`** — new section 4, five tests, fully offline (the
build lookup and the download are monkeypatched; the `config`/`db` fixtures
are tmp-based, the same offline pattern the file already uses):

| test | proves |
|---|---|
| `…_reloads_when_a_map_table_is_empty[sde_stargates]` | same-build refresh reloads (1 download, reusing the stamped build), fills the tables, the `route_cache` row for the build is gone, and `RouteGraph` routes 30000142→30000144 — the task's headline outcome |
| `…_reloads_when_a_map_table_is_empty[sde_npc_stations]` | the same, for the station table |
| `…_still_no_ops_when_every_table_is_populated` | 0 downloads, `downloaded=False`, counts preserved, cache row untouched — the cheap path is unchanged |
| `…_with_no_stargates_fails_loudly` / `…_with_no_npc_stations_fails_loudly` | an empty-member bundle raises `SdeError` and writes nothing (table empty, stamp unchanged) |

**Control files**: `CHANGELOG.md` entry (2026-10-26); `CURRENT_CHECKPOINT.md`
new active item, §23 demoted to previous item. No new status files.

## Test results

- **Red, pre-change** (`.qo/tests-red.txt`): `4 failed, 10 passed` — the two
  reload tests and the two loud-fail tests fail exactly as designed; the
  no-op guard passed then too (it pins today's behaviour, which the fix must
  keep).
- **Green, post-change** (`.qo/build.txt`): full suite
  `pytest -q` → **1,089 passed, 7 deselected** (exit 0; the 7 deselected are
  `@pytest.mark.network`), `ruff check .` clean, `ruff format --check .`
  clean (165 files). Targeted: `tests/test_sde_map.py` → 14 passed.
- Baseline before any edit: `tests/test_sde_map.py` 9 passed.

## What I skipped, and why

- **No schema, CLI, router or trading-logic change** — the task's symptom is
  entirely inside `load_sde`'s skip decision and the load tail.
- **The task's named pair vs. all five tables**: per the task's own note I
  treat *any* SDE table the load fills as "empty means reload" (five tables,
  not two). An empty `sde_types`/`sde_market_groups`/`sde_solar_systems` now
  also forces the reload.
- **Loud-fail scope stays at gates + stations**, as the task's note says. An
  empty `sde_solar_systems` triggers the reload but a zero-systems bundle does
  not raise — accepted scope line, recorded in `.qo/plan.md`.
- **Pre-existing doc drift** in the `sde.py` module docstring ("reads exactly
  two members"; it has read five since H1a) was left alone to keep the diff
  small; noted as an advisory in `.qo/review.json`.
- **The stale-doc line `plan.md`** was not touched — this is a defect fix on
  the closed §23 H1a map, not a plan-level edit, and it changes no locked
  decision, formula, or detector.

## Open doubts

- **Live confirmation is the operator's**: one `sde` run on the real lake
  should now reload (reusing the on-disk bundle for the stored build) and fill
  the two map tables; the hauling scan's `NO_ROUTE` should clear. I could not
  verify against the operator's real `state.db` from this checkout — no
  network and no access to the deployment from here.
- **A real `mapStargates.jsonl`/`npcStations.jsonl` member being empty** is
  not something I could observe (the fixtures and build 3478781 both carry
  both); the guard is a defensive one, consistent with `parse_stargates`'s
  existing no-resolvable-edges error.
- **`route_cache` invalidation is broader than the task asked** (it also runs
  on `--force` and `--bundle` loads of the same build). I judge that correct
  — the map was rewritten under that build in every case — but it is the one
  behaviour beyond the letter of the task; see the advisory in
  `.qo/review.json`.

Self-review verdict: **GO**, no blockers — `.qo/review.json`.
