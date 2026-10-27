# Plan: name the real blocker when a hauling pair has no route

## Task restatement

In hauling, a pair whose route is cut by the operator's own avoid list comes
back `ROUTE_BLOCKED_SECURITY`, because the probe in `_trip` re-runs the route
with the default profile and no avoid list (and bypasses the route cache).
Replace the single probe with two questions, asked separately **through the
route cache**:

1. **Does it connect without the avoid list?** (the operator's own security
   profile and safer penalty kept, only `avoid=()` dropped). If yes: the avoid
   list is the blocker → `NO_ROUTE` with a `detail` that names the avoid list.
2. **Else, does it connect on the shortest profile?** If yes:
   → `ROUTE_BLOCKED_SECURITY` (the security profile is what empties the graph).
3. **Neither:** `NO_ROUTE` — the pair is genuinely disconnected; keep the
   existing `detail = haul.reason`.

## What is unclear / wrong in the task, and how I resolved it

- *"Default profile"* — the old probe actually used `RouteGraph.route`'s
  defaults: `SHORTEST`, `avoid=()`, `safer_penalty=50.0`, and it skipped the
  cache. Q1 keeps the operator's security profile and safer penalty and only
  drops the avoid list; Q2 uses `SHORTEST` with the operator's safer penalty
  (the penalty is part of the cache key; for `shortest` it is behaviourally
  inert, BFS ignores it).
- The old gate additionally required `profile.security_profile == HIGHSEC`.
  The task's question 2 ("does it connect on the shortest profile?") is
  unconditional, so the gate is dropped: any profile whose no-avoid route fails
  while shortest succeeds is a security-profile block. This is a
  behaviour change only for `safer`-profile pairs (which used to be labelled
  `NO_ROUTE` even when only the avoid list or a profile quirk cut them); it is
  consistent with the label's own purpose ("the operator can act on it by
  changing the profile") and is covered by a new test.
- `avoid_systems` empty: Q1 then equals the main haul call; it is still asked
  (uniform code, and it is a cache hit when a cache is present), and Q2
  decides. No special-casing.

## Steps

1. **Tests first** (failing before the fix) — add to `tests/test_hauling.py`,
   next to the existing route tests:
   - `test_the_avoid_list_that_cuts_the_route_is_named_not_blamed_on_security`:
     high-sec corridor, `highsec` profile, `avoid_systems` covering the one
     intermediate system → `NO_ROUTE` (not `ROUTE_BLOCKED_SECURITY`), detail
     names the avoid list.
   - `test_a_security_profile_that_blocks_the_route_names_the_shortest_profile`:
     low-sec corridor, `highsec` profile, no avoid list →
     `ROUTE_BLOCKED_SECURITY`, detail says the pair connects on the shortest
     profile.
   - `test_a_pair_disconnected_under_every_profile_is_plain_no_route`: AMARR
     isolated in the graph, `highsec` profile with an avoid list → neither
     probe connects → plain `NO_ROUTE`, not `ROUTE_BLOCKED_SECURITY`.
   - `test_the_route_probes_go_through_the_route_cache`: a recording stub in
     the `route_cache=` slot logs every `route()` call; assert the no-avoid
     probe (Q1) and, in the security-blocked shape, the `shortest` probe (Q2)
     are asked of the cache with `avoid=()`, in addition to the main haul call.
   Run them; save the failing output to `.qo/tests-red.txt`.
2. **Build** — `src/evescreener/hauling.py` only:
   - import `SHORTEST` from `.routes` (line 43);
   - `_route` (`hauling.py:614`): add keyword-only overrides `avoid=None` and
     `security_profile=None` (default to the profile's own values) so the
     probes reuse the same cache-or-graph dispatch as the real trip;
   - `_trip` (`hauling.py:649-665`): replace the single `blocked` probe with
     the two cached probes above and the three-way reason/detail outcome.
   No changes to: the route cache format (`routes.py`), `HaulProfile` fields,
   ranking. Follow the existing reason/detail field pattern.
3. **Verify**: `PYTHONPATH=src python -m pytest -q tests/test_hauling.py` green
   (the two pre-existing route tests must still pass), then
   `python -m ruff check .` clean. Save output to `.qo/build.txt`.
4. **Self-review** the diff; write `.qo/review.json`.
5. **Report** to `.qo/report.md`.

## "Done" means

- `tests/test_hauling.py` has a test for each of the three outcomes (avoid list
  → `NO_ROUTE` naming the avoid list; security profile →
  `ROUTE_BLOCKED_SECURITY`; neither → plain `NO_ROUTE`) plus cache-routing
  coverage; all green.
- `PYTHONPATH=src python -m pytest -q tests/test_hauling.py` green,
  `python -m ruff check .` clean.
- Pre-existing route tests in `tests/test_hauling.py` unchanged and passing.
