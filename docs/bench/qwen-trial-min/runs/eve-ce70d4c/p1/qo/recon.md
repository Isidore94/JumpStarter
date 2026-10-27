# Recon: hauling — avoid list mislabelled as ROUTE_BLOCKED_SECURITY

## Where the defect lives

`src/evescreener/hauling.py`:

- `_trip` (`hauling.py:633-718`) prices the movement for a pair. When the haul
  route comes back unknown, it runs one probe and labels the pair
  (`hauling.py:649-665`):
  ```python
  if not haul.known:
      blocked = (
          profile.security_profile == HIGHSEC
          and graph.route(source.system_id, destination.system_id).known
      )
      ...
      reason=ROUTE_BLOCKED_SECURITY if blocked else NO_ROUTE,
      detail=haul.reason,
  ```
- That probe calls `RouteGraph.route` **directly**, with that method's defaults:
  `profile=SHORTEST, avoid=(), safer_penalty=50.0` (`routes.py:245-253`). So it
  (a) ignores the operator's avoid list and (b) bypasses the route cache that
  every real trip call in `_trip` goes through via `_route` (`hauling.py:614-630`).

## How the mislabel happens

If the operator's avoid list is the only thing cutting the route, the probe's
no-avoid search succeeds. For a `HIGHSEC` profile the old gate then sets
`blocked=True` and the pair comes back `ROUTE_BLOCKED_SECURITY` — blaming the
security profile for what the operator's own avoid list did. For other profiles
it comes back `NO_ROUTE` with `detail=haul.reason`, which at least says
"(avoiding N system(s))" (`routes.py:302-308`) but never says the avoid list is
the actionable blocker.

The probe also only fires when `profile.security_profile == HIGHSEC`, so a pair
whose profile filter (e.g. `safer`) empties the graph but shortest does not is
never labelled `ROUTE_BLOCKED_SECURITY` at all.

## The route cache

`RouteCache.route(graph, origin, destination, *, profile, avoid, safer_penalty)`
(`routes.py:514-534`): `get` by `(sde_build, origin, destination, profile,
avoid_hash)` where `avoid_hash = sha1(sorted avoid + penalty)` (`routes.py:166-177`),
compute + `put` on miss; unknown routes are cached as unknown
(`routes.py:481-488`). `hauling.py` reaches it through the local `_route` helper
(`hauling.py:614-630`), which reads `profile.security_profile` and
`profile.avoid_systems` off the `HaulProfile`. Cache format and `HaulProfile`
fields are out of scope (task "Don't touch").

## Profiles

`PROFILES = (SHORTEST, SAFER, HIGHSEC)` (`routes.py:54-57`). `SHORTEST`/`SAFER`
never filter by security (`routes.py:235-243`); only `HIGHSEC` does. `SHORTEST`
is not imported in `hauling.py` yet (`hauling.py:43` imports
`HIGHSEC, PROFILES, RouteFacts, RouteGraph`).

## Consumers / dependents

- `_trip`'s `reason`/`detail` flow into `Rejection` in `_scan_pair`
  (`hauling.py:909-919`); `HaulScan.rejected_for` (`hauling.py:522-523`).
- `ROUTE_BLOCKED_SECURITY` is asserted only in `tests/test_hauling.py:271`
  (`test_a_low_sec_corridor_is_blocked_by_security_not_called_disconnected`,
  highsec profile, low-sec corridor, no avoid list — this outcome must survive
  the change). `tests/test_hauling.py:254-258`
  (`test_a_route_that_does_not_exist_rejects_the_pair`, empty graph, default
  `shortest` profile — must survive).
- `RouteCache` construction: `src/evescreener/cli.py:1325`,
  `src/evescreener/gui/pages/hauling.py:362`; caching tests in
  `tests/test_routes.py:203-242` (format untouched by this change).

## Test harness

`tests/test_hauling.py` builds synthetic graphs with `_graph(jumps, security)`
(line 93: Jita–…–Amarr corridor, all one security, `sde_build=3478781`),
profiles with `_profile(**overrides)` (line 104: default `security_profile=
"shortest"`, no avoid list), and scans with `_scan(config, worked, *, graph,
profile, ...)` (line 123). `scan_hauls` takes `route_cache=` as a plain object
(`hauling.py:753`) — only `.route(graph, origin, destination, *, profile, avoid,
safer_penalty)` is called on it, so a recording stub is a legitimate stand-in
for the cache.
