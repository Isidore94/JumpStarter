# Report — reload the SDE when a map table is empty, even if the stored build matches

## What changed

**`src/evescreener/sde.py`** (the fix, +48/−9 including reflow):

- New module constant `SDE_TABLES`: the five tables `load_sde` fills
  (`sde_types`, `sde_market_groups`, `sde_solar_systems`, `sde_stargates`,
  `sde_npc_stations`).
- New helper `_tables_populated(db)`: every SDE table must hold rows. The build
  stamp alone is not proof the load is complete — a release that adds a table
  (H1a's stargates and stations did) leaves a previously loaded lake stamped
  with the current build and the new tables empty, and the build-equality no-op
  then refused to fix it forever. That was the silent `NO_ROUTE` symptom:
  routing read an empty graph, every system was "not in the stargate graph",
  and hauling scans returned nothing.
- The no-op in `load_sde` is now gated on `stored == build and not force
  and _tables_populated(db)`. An empty table sends the refresh down the
  download path, where `download_bundle` **reuses an already-downloaded bundle
  for that build** (existing behaviour, sde.py:105–106) — so a same-build
  refill costs no network traffic and nothing is fetched before expiry.
- Fail-loud: a load that yields **zero stargates or zero NPC stations** raises
  `SdeError` *before* `set_meta("sde_build", …)` — the stamp must not advance
  over an empty map, because the no-op would then trust it. This check also
  applies to the `bundle_path` (local bundle) entry point, so "success with
  empty tables" is impossible from either path.

**`tests/test_sde_map.py`** (+117/−9): the `_bundle` helper gained
`stargates=`/`stations=`/`name=` knobs, and five new offline tests — the
latest-build lookup and the download are monkeypatched, no network:

1. `test_an_empty_stargate_table_still_forces_a_reload`
2. `test_an_empty_npc_station_table_still_forces_a_reload`
3. `test_a_complete_load_at_the_same_build_stays_a_cheap_no_op` (the download
   stub *refuses* to run; the no-op must not need it)
4. `test_a_reloaded_bundle_with_no_gates_fails_loudly`
5. `test_a_reloaded_bundle_with_no_npc_stations_fails_loudly` (both assert the
   `sde_build` stamp was **not** advanced)

**Control files** (required by CLAUDE.md; no new status files created):
`CHANGELOG.md` gained the 2026-10-26 entry; `CURRENT_CHECKPOINT.md` gained the
short dated bug-fix section with the verification stamp.

## Test results

- Baseline (pre-change, worktree code): **1084 passed, 7 deselected**
- Red (new tests vs pre-fix code): **4 failed, 10 passed** in 0.60 s — the two
  reload tests and the two fail-loud tests. The no-op guard passes pre-fix by
  design (the no-op already worked; it guards against over-fixing). See
  `.qo/tests-red.txt`.
- Green (post-fix, whole suite): **1089 passed, 7 deselected** in 43.73 s
  (7 deselected = network-marked tests, deselected by the default `-m "not
  network"`).
- Lint: `ruff check .` → All checks passed; `ruff format --check .` →
  165 files already formatted.

All runs used the job-pinned interpreter
(`C:/Users/Aaron/EveTradingbot/.venv/Scripts/python.exe`) with
`PYTHONPATH=C:/Users/Aaron/llm-harness/wt/qo-91eb9b8/src` — see "Open doubts"
below for why the override was required.

## What was skipped

- No widening of the fail-loud check to `sde_solar_systems`: the task asks to
  fail loudly when the reloaded bundle "still yields no gates or stations". An
  empty `mapSolarSystems.jsonl` still loads today, but the empty table then
  blocks the no-op, so the *next* refresh reloads again instead of reporting a
  filled lake — it can never be silently trusted. Recorded as an advisory in
  `.qo/review.json`.
- No git commits, no pushes, no history-reading commands, no network — per the
  job rules. The change is left in the working tree.

## Open doubts

1. **The main checkout already carries a partial variant of this fix.**
   `C:\Users\Aaron\EveTradingbot\src\evescreener\sde.py` (the editable-install
   target the venv points at) has `SDE_TABLES` + `_tables_populated` + the
   gated no-op, but **no fail-loud check** and only two reference tests. This
   worktree's implementation is a superset. When the branch is merged back,
   reconcile so the constant and helper are not duplicated. (Advisory in
   `.qo/review.json`.)
2. **Environment gotcha (not a code defect).** The venv's editable install
   resolves `import evescreener` to the main checkout's `src`, not this
   worktree's. Every test and lint run here therefore carried the `PYTHONPATH`
   override; without it the tests would have exercised the wrong code. This
   is recorded in `.qo/recon.md` and `.qo/build.txt`.
3. **The `CLAUDE.md` modification was pre-existing** (the harness's
   orchestration header, already `M` in the first `git status` of the
   session); it is not part of this change and was not touched.

## Verdict

`.qo/review.json`: **GO**, no blockers, four advisories (the two environment /
merge items above, the harmless partial-write ordering on the error path, and
the check's applicability to locally-supplied bundles).
