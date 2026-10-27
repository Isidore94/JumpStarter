# Plan — reload the SDE when a map table is empty, even if the stored build matches

## Change (smallest that satisfies the task)

One code file, one test file, plus the two control files.

### 1. `src/evescreener/sde.py`

a. Add a module constant `SDE_TABLES` — the five tables the load fills
   (`sde_types`, `sde_market_groups`, `sde_solar_systems`, `sde_stargates`,
   `sde_npc_stations`). The task's note: treat *any* SDE table the load fills
   as "empty means reload", not only the stargate/station pair.

b. Add `_tables_populated(db)` — `False` if any of the five tables holds no
   row. Docstring records the why: the build stamp alone is not proof the load
   is complete; a release that adds a table (H1a did, with `sde_stargates`
   and `sde_npc_stations`) leaves a previously-loaded lake stamped with the
   current build and the new tables empty, and the build-equality no-op
   refuses to fix it forever — the silent symptom being `NO_ROUTE` on every
   hauling scan.

c. Gate the no-op on it: `if stored and int(stored) == build and not force and
   _tables_populated(db):` (sde.py:277). Empty table ⇒ fall through to
   `download_bundle` + full load. `download_bundle` already reuses an
   on-disk bundle for that build without a request (sde.py:92–93), so the
   reload costs a parse, not a fetch, when the bundle is cached.

d. Fail loudly after a full load: if the loaded bundle still yields zero
   stargates or zero NPC stations, raise `SdeError` **before**
   `db.set_meta("sde_build", ...)` — an empty map answers "no route" to
   everything, and the stamp must not advance or the next refresh would no-op
   over the emptiness again. (types/groups are already guarded at sde.py:301;
   `parse_stargates` already guards records-present/none-resolvable, not
   records-absent.)

e. Update the two docstrings that say "same build = a no-op" (module doc,
   `load_sde`) to state the exception.

### 2. `tests/test_sde_map.py` (extend, do not rewrite)

Extend `_bundle` with `stations=` and `name=` keyword parameters
(back-compatible: existing callers untouched; both default to current
behaviour). New section, all offline — `latest_build` and `download_bundle`
monkeypatched, `config`/`db` fixtures, bundle built by `_bundle`:

- **T1 reload on empty stargates:** load a full bundle (stamps the build),
  `DELETE FROM sde_stargates`, same-build refresh with a recording
  `download_bundle` stub ⇒ download *is* attempted with build 3478781,
  `result.downloaded is True`, `result.stargates == 2`,
  `db.stargate_edges()` repopulated. **Fails before the fix** (no-op returns
  `stargates == 0`).
- **T2 reload on empty NPC stations:** same against `sde_npc_stations` ⇒
  `result.npc_stations == 2`, `db.station_systems()` repopulated. **Fails
  before the fix.**
- **T3 no-op stays cheap:** fully populated same-build refresh with a
  `download_bundle` stub that raises ⇒ not called; `result.downloaded is
  False`, counts intact. Passes before *and* after (regression guard against
  over-fixing).
- **T4 reloaded bundle with no gates fails loudly:** empty stargates table,
  stubbed download returns a bundle whose `mapStargates.jsonl` is empty ⇒
  `SdeError` (match "no stargates"); `sde_build` meta unchanged, table still
  empty. **Fails before the fix** (no-op, no error).
- **T5 reloaded bundle with no stations fails loudly:** mirror of T4 on
  `npcStations.jsonl` ⇒ `SdeError` (match "no NPC stations"). **Fails before
  the fix.**

### 3. Control files (required by the repo's CLAUDE.md)

- `CHANGELOG.md`: new dated entry at the top (status line + what changed +
  gate stamp).
- `CURRENT_CHECKPOINT.md`: short dated section recording the fix
  (IMPLEMENTED + GREEN + gate stamp), no restructuring; "Notes for the next
  session" gains nothing — the entry itself is enough.

## Unclear points and how they were resolved (decisions, recorded per the job rules)

1. **Which tables count as "required"?** Task note's sensible default: all
   five tables the load fills. If any is empty at a matching build, reload.
2. **Fail-loud scope:** the task names "gates or stations", so the new
   SdeError covers stargates and NPC stations (types/groups already guarded).
   An empty `mapSolarSystems.jsonl` still loads without error — it would make
   high-sec reads UNKNOWN, never a wrong price, and the next refresh reloads
   again because the table is empty. Recorded as an advisory in the review,
   not silently widened.
3. **Stamp on failure:** raised *before* `set_meta`, so a failed reload leaves
   the previous stamp; the following refresh retries instead of no-opping.
4. **`bundle_path` entry (CLI `sde --bundle`):** the loud check applies to it
   too — a locally supplied bundle with an empty map table is broken in the
   same way, and "never report success with empty tables" should not depend on
   which door the load came in through.
5. **Test home:** `tests/test_sde_map.py` (the module that owns this load and
   already avoids the network); no new test file.

## Commands (job-pinned interpreter; the worktree override from recon is needed
because the venv's editable install points at the main checkout)

- Baseline (before touching anything): full suite green.
- Red: `pytest -q tests/test_sde_map.py` with the new tests → save to
  `.qo/tests-red.txt`.
- Green: `pytest -q` (full) + `ruff check .` + `ruff format --check .` →
  save to `.qo/build.txt`.

`PYTHONPATH=C:/Users/Aaron/llm-harness/wt/qo-91eb9b8/src`
`C:/Users/Aaron/EveTradingbot/.venv/Scripts/python.exe -m pytest -q`

## Done means

- T1–T5 pass; T1/T2/T4/T5 failed before the fix (red output saved).
- Full suite green offline; ruff check + format clean.
- No file outside this directory touched; no git history commands; no network.
- `CURRENT_CHECKPOINT.md` and `CHANGELOG.md` updated; `.qo/report.md` written.
