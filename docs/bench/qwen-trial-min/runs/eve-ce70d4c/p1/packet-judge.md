# BRIEF
Goal: in hauling, a pair whose route is cut by the operator's own avoid list comes back ROUTE_BLOCKED_SECURITY, because the probe re-runs the route with the default profile and no avoid list. Ask the two questions separately, both through the route cache: does it connect without the avoid list? then the avoid list is the blocker: NO_ROUTE with a detail that names the avoid list. Else, does it connect on the shortest profile? then it is ROUTE_BLOCKED_SECURITY. Neither: NO_ROUTE, the pair is genuinely disconnected.
Done when: tests/test_hauling.py has a test for each of the three outcomes; `PYTHONPATH=src python -m pytest -q tests/test_hauling.py` green, ruff clean.
Files: src/evescreener/hauling.py (_route and _trip, around the ROUTE_BLOCKED_SECURITY line); find the rest.
Don't touch: the route cache format, HaulProfile fields, the ranking.
Pattern: the existing reason / detail fields on the plan objects in hauling.py.

# CANDIDATE DIFF
```diff
diff --git a/src/evescreener/hauling.py b/src/evescreener/hauling.py
index 929b828..41d155e 100644
--- a/src/evescreener/hauling.py
+++ b/src/evescreener/hauling.py
@@ -40,7 +40,7 @@ import pandas as pd
 from .books import DepthCurve, DepthLevel, DepthSnapshot, q_walk
 from .config import Config
 from .costs import CostModel
-from .routes import HIGHSEC, PROFILES, RouteFacts, RouteGraph
+from .routes import HIGHSEC, PROFILES, SHORTEST, RouteFacts, RouteGraph
 from .timeutil import ensure_utc, iso, utcnow
 
 __all__ = [
@@ -611,21 +611,38 @@ class _Trip:
     detail: str = ""
 
 
-def _route(graph, cache, origin, destination, profile: HaulProfile) -> RouteFacts:
+def _route(
+    graph,
+    cache,
+    origin,
+    destination,
+    profile: HaulProfile,
+    *,
+    avoid=None,
+    security_profile=None,
+) -> RouteFacts:
+    """One route under the profile's constraints, one or both of which the
+    probes in `_trip` ask about with an override. Both dispatches stay on the
+    same path as the trip itself: through the route cache when there is one, so
+    a question already answered in a scan is not searched again."""
+    if avoid is None:
+        avoid = profile.avoid_systems
+    if security_profile is None:
+        security_profile = profile.security_profile
     if cache is not None:
         return cache.route(
             graph,
             origin,
             destination,
-            profile=profile.security_profile,
-            avoid=profile.avoid_systems,
+            profile=security_profile,
+            avoid=avoid,
             safer_penalty=profile.safer_penalty,
         )
     return graph.route(
         origin,
         destination,
-        profile=profile.security_profile,
-        avoid=profile.avoid_systems,
+        profile=security_profile,
+        avoid=avoid,
         safer_penalty=profile.safer_penalty,
     )
 
@@ -647,21 +664,47 @@ def _trip(
         )
     )
     if not haul.known:
-        # A security profile that blocks an otherwise-connected pair is a
-        # different fact from a pair that is not connected at all, and the
-        # operator can act on the first one by changing the profile.
-        blocked = (
-            profile.security_profile == HIGHSEC
-            and graph.route(source.system_id, destination.system_id).known
+        # Which of the operator's own inputs cuts the route is a different
+        # question from whether anything cuts it, so ask them separately — and
+        # ask both of the cache, the way the trip itself was asked. Drop the
+        # avoid list under his own profile first: if that connects, the avoid
+        # list is what cut the route, and only the operator can drop it. Then
+        # drop the profile itself: if the shortest profile connects, the
+        # security profile is the blocker, and only the operator can change it.
+        # Neither connects and the pair is simply not there.
+        without_avoid = _route(
+            graph, cache, source.system_id, destination.system_id, profile, avoid=()
         )
+        if without_avoid.known:
+            reason, detail = (
+                NO_ROUTE,
+                f"the pair connects under the {profile.security_profile} profile without "
+                f"the avoid list — the {len(profile.avoid_systems)} system(s) on it cut the route",
+            )
+        elif _route(
+            graph,
+            cache,
+            source.system_id,
+            destination.system_id,
+            profile,
+            avoid=(),
+            security_profile=SHORTEST,
+        ).known:
+            reason, detail = (
+                ROUTE_BLOCKED_SECURITY,
+                f"the pair connects on the shortest profile — the {profile.security_profile} "
+                "security profile is what blocks it",
+            )
+        else:
+            reason, detail = NO_ROUTE, haul.reason
         return _Trip(
             pickup=pickup,
             haul=haul,
             total_jumps=None,
             detour_jumps=None,
             active_minutes=None,
-            reason=ROUTE_BLOCKED_SECURITY if blocked else NO_ROUTE,
-            detail=haul.reason,
+            reason=reason,
+            detail=detail,
         )
 
     detour_jumps = None
diff --git a/tests/test_haul_detour.py b/tests/test_haul_detour.py
index 41efd9b..dd75cab 100644
--- a/tests/test_haul_detour.py
+++ b/tests/test_haul_detour.py
@@ -23,10 +23,19 @@ import pytest
 pytestmark = pytest.mark.gui
 
 from evescreener.crossregion import FreightQuote  # noqa: E402
-from evescreener.haulfreight import attach_freight, freight_comparison
-from evescreener.hauling import ALONG_ROUTE, NO_ROUTE, Station, scan_hauls
-from evescreener.routes import RouteGraph
-from test_hauling import DEST, DOMAIN, FORGE, NOW, SOURCE, _orders, _profile, _snapshot
+from evescreener.haulfreight import attach_freight, freight_comparison  # noqa: E402
+from evescreener.hauling import ALONG_ROUTE, NO_ROUTE, Station, scan_hauls  # noqa: E402
+from evescreener.routes import RouteGraph  # noqa: E402
+from test_hauling import (  # noqa: E402
+    DEST,
+    DOMAIN,
+    FORGE,
+    NOW,
+    SOURCE,
+    _orders,
+    _profile,
+    _snapshot,
+)
 
 RENS_SYS, RENS_STATION, HEIMATAR = 30002510, 60004588, 10000030
 STAGING = Station(60099999, 30002510, HEIMATAR, "Rens", None)
diff --git a/tests/test_hauling.py b/tests/test_hauling.py
index 017e6d1..0a2fb02 100644
--- a/tests/test_hauling.py
+++ b/tests/test_hauling.py
@@ -272,6 +272,127 @@ def test_a_low_sec_corridor_is_blocked_by_security_not_called_disconnected(confi
     assert not scan.rejected_for(NO_ROUTE)
 
 
+def test_the_avoid_list_that_cuts_the_route_is_named_not_blamed_on_security(config, worked):
+    """A pair whose route is cut by the operator's own avoid list used to come
+    back ROUTE_BLOCKED_SECURITY: the probe re-ran the route with the default
+    profile and no avoid list, so it blamed the security profile for what the
+    operator's list did. The avoid list is the blocker, and it is the operator's
+    to drop — which is not what 'blocked by security' says."""
+    graph = _graph(jumps=2, security=0.9)  # Jita — 90000 — Amarr, all high-sec
+    scan = _scan(
+        config,
+        worked,
+        graph=graph,
+        profile=_profile(security_profile="highsec", avoid_systems=(90_000,)),
+    )
+    assert scan.plans == []
+    assert not scan.rejected_for(ROUTE_BLOCKED_SECURITY)
+    rejections = scan.rejected_for(NO_ROUTE)
+    assert rejections, f"expected NO_ROUTE; got {scan.rejection_counts}"
+    assert "avoid" in rejections[0].detail, "the detail says which input cuts the route"
+
+
+def test_a_security_profile_that_blocks_the_route_names_the_shortest_profile(config, worked):
+    """No avoid list involved: the profile itself empties the graph. Dropping
+    the avoid list changes nothing, the shortest profile connects, so this is
+    ROUTE_BLOCKED_SECURITY — and the detail says what the operator can do
+    about it."""
+    scan = _scan(
+        config,
+        worked,
+        graph=_graph(jumps=2, security=0.2),
+        profile=_profile(security_profile="highsec"),
+    )
+    assert scan.plans == []
+    rejections = scan.rejected_for(ROUTE_BLOCKED_SECURITY)
+    assert rejections, f"expected ROUTE_BLOCKED_SECURITY; got {scan.rejection_counts}"
+    assert not scan.rejected_for(NO_ROUTE)
+    assert "shortest" in rejections[0].detail
+
+
+def test_a_pair_disconnected_under_every_profile_is_plain_no_route(config, worked):
+    """Neither question connects: even the shortest profile finds no route
+    through, so the pair is genuinely disconnected rather than cut by anything
+    the operator owns. Both probes fail, and the detail stays the route's own
+    reason."""
+    graph = RouteGraph(
+        [(JITA, 90_000)],
+        {JITA: 0.9, 90_000: 0.9, AMARR: 0.9},
+        sde_build=3478781,
+    )
+    scan = _scan(
+        config,
+        worked,
+        graph=graph,
+        profile=_profile(security_profile="highsec", avoid_systems=(90_000,)),
+    )
+    assert scan.plans == []
+    assert not scan.rejected_for(ROUTE_BLOCKED_SECURITY)
+    rejections = scan.rejected_for(NO_ROUTE)
+    assert rejections, f"expected NO_ROUTE; got {scan.rejection_counts}"
+    assert "no high-sec route" in rejections[0].detail
+
+
+class _RecordingCache:
+    """Stands in for `route_cache`: records what the scan asks of it, then
+    defers to the bare graph exactly `RouteCache.route` does on a miss. The
+    probes have to be asked here, where the trip was asked, or a cached answer
+    is recomputed for nothing and a stored NO_ROUTE is searched again."""
+
+    def __init__(self, graph):
+        self.graph = graph
+        self.calls: list[tuple] = []
+
+    def route(
+        self,
+        graph,
+        origin,
+        destination,
+        *,
+        profile="shortest",
+        avoid=(),
+        safer_penalty=50.0,
+    ):
+        self.calls.append((origin, destination, profile, tuple(avoid), safer_penalty))
+        return graph.route(
+            origin, destination, profile=profile, avoid=avoid, safer_penalty=safer_penalty
+        )
+
+
+def test_the_route_probes_are_asked_of_the_cache_not_the_bare_graph(config, worked):
+    """The old probe ran `graph.route` directly with its defaults: no avoid
+    list, default profile, and a cache the scan is already paying for. Both
+    questions go through the cache the trip does."""
+    graph = _graph(jumps=2, security=0.9)
+    cache = _RecordingCache(graph)
+    scan = _scan(
+        config,
+        worked,
+        graph=graph,
+        route_cache=cache,
+        profile=_profile(security_profile="highsec", avoid_systems=(90_000,)),
+    )
+    assert scan.rejected_for(NO_ROUTE)
+    # The trip itself, with the operator's avoid list...
+    assert (JITA, AMARR, "highsec", (90_000,), 50.0) in cache.calls
+    # ...then question one: the same pair, the operator's profile, no avoid.
+    assert (JITA, AMARR, "highsec", (), 50.0) in cache.calls
+    assert (JITA, AMARR, "shortest", (), 50.0) not in cache.calls, "question one already connected"
+
+    cache = _RecordingCache(graph)
+    scan = _scan(
+        config,
+        worked,
+        graph=_graph(jumps=2, security=0.2),
+        route_cache=cache,
+        profile=_profile(security_profile="highsec"),
+    )
+    assert scan.rejected_for(ROUTE_BLOCKED_SECURITY)
+    # Question one connects nothing, so question two is asked on shortest.
+    assert (JITA, AMARR, "highsec", (), 50.0) in cache.calls
+    assert (JITA, AMARR, "shortest", (), 50.0) in cache.calls
+
+
 def test_too_many_jumps_and_too_few_minutes_are_different_refusals(config, worked):
     far = _scan(config, worked, graph=_graph(jumps=9), profile=_profile(max_jumps=3))
     assert far.rejected_for(OVER_JUMPS) and far.plans == []
```

# LEAD TEST RESULTS
## builder's own test command (exit 0)
```
........................................................................ [  6%]
........................................................................ [ 13%]
........................................................................ [ 20%]
........................................................................ [ 27%]
........................................................................ [ 34%]
........................................................................ [ 41%]
........................................................................ [ 47%]
........................................................................ [ 54%]
........................................................................ [ 61%]
........................................................................ [ 68%]
........................................................................ [ 75%]
........................................................................ [ 82%]
........................................................................ [ 88%]
........................................................................ [ 95%]
............................................                             [100%]
1052 passed, 7 deselected in 43.98s
```
## lint (exit 0)
```
All checks passed!
```
## hidden reference tests (exit 0)
```
.............................                                            [100%]
29 passed in 1.18s
```

# BUILDER SELF-REVIEW
```json
{
  "verdict": "GO",
  "blockers": [],
  "advisories": [
    "The cache test uses a recording stub in the route_cache= slot, not a real RouteCache: it proves the probes are asked of the cache with the right (profile, avoid) keys, while RouteCache's own storage semantics are covered by tests/test_routes.py. Within the 'don't touch the cache format' scope this is the right division of labor.",
    "test_haul_detour.py needed four `# noqa: E402` markers (pre-existing lint debt: pytestmark sits between imports and only the first import was suppressed) to make `ruff check .` green. No behaviour change, but it is a file outside the task's stated scope; flagged so the integrator can drop it if unwanted.",
    "Behaviour change beyond the stated defect: the old probe only fired for security_profile == HIGHSEC, so a SAFER-profile pair whose no-avoid route failed was never labelled ROUTE_BLOCKED_SECURITY. The new logic labels it when the shortest profile connects. Consistent with the label's purpose ('the operator can act on it'), and the task's question 2 is unconditional, but it is a widening, not just a fix."
  ],
  "summary": "Both probe questions are now asked through the route cache via _route with keyword overrides: Q1 keeps the operator's security profile and safer penalty and drops only the avoid list; Q2 asks the shortest profile. Outcomes: Q1 known -> NO_ROUTE naming the avoid list; else Q2 known -> ROUTE_BLOCKED_SECURITY naming the shortest profile; else plain NO_ROUTE with the route's own reason. The three pre-existing outcomes are pinned by tests (avoid-cut -> NO_ROUTE 'avoid' detail [red pre-fix]; low-sec corridor highsec -> ROUTE_BLOCKED_SECURITY 'shortest' detail [red pre-fix]; disconnected -> plain NO_ROUTE [regression pin]), plus a recording-cache test asserting the probes reach the cache slot with avoid=() and that Q2 is skipped when Q1 connects [red pre-fix]. 30/30 green in test_hauling.py, 47/47 in the neighboring haul/route files, ruff check . and ruff format --check clean on all touched files. No changes to the route cache format, HaulProfile, or the ranking."
}
```

# REFERENCE DIFF (the merged change, for comparison)
```diff
diff --git a/src/evescreener/hauling.py b/src/evescreener/hauling.py
index 929b828..2ba920a 100644
--- a/src/evescreener/hauling.py
+++ b/src/evescreener/hauling.py
@@ -40,7 +40,7 @@ import pandas as pd
 from .books import DepthCurve, DepthLevel, DepthSnapshot, q_walk
 from .config import Config
 from .costs import CostModel
-from .routes import HIGHSEC, PROFILES, RouteFacts, RouteGraph
+from .routes import HIGHSEC, PROFILES, SHORTEST, RouteFacts, RouteGraph
 from .timeutil import ensure_utc, iso, utcnow
 
 __all__ = [
@@ -611,21 +611,38 @@ class _Trip:
     detail: str = ""
 
 
-def _route(graph, cache, origin, destination, profile: HaulProfile) -> RouteFacts:
+def _route(
+    graph,
+    cache,
+    origin,
+    destination,
+    profile: HaulProfile,
+    *,
+    security: str | None = None,
+    avoid: Iterable[int] | None = None,
+) -> RouteFacts:
+    """One route under the operator's profile, or a named variation of it.
+
+    `security` and `avoid` override the profile so the diagnostic probes below
+    can ask "would this pair connect *without* that constraint" — through the
+    same cache, because a probe is as expensive as a route.
+    """
+    security = security if security is not None else profile.security_profile
+    avoid = tuple(profile.avoid_systems if avoid is None else avoid)
     if cache is not None:
         return cache.route(
             graph,
             origin,
             destination,
-            profile=profile.security_profile,
-            avoid=profile.avoid_systems,
+            profile=security,
+            avoid=avoid,
             safer_penalty=profile.safer_penalty,
         )
     return graph.route(
         origin,
         destination,
-        profile=profile.security_profile,
-        avoid=profile.avoid_systems,
+        profile=security,
+        avoid=avoid,
         safer_penalty=profile.safer_penalty,
     )
 
@@ -647,21 +664,39 @@ def _trip(
         )
     )
     if not haul.known:
-        # A security profile that blocks an otherwise-connected pair is a
-        # different fact from a pair that is not connected at all, and the
-        # operator can act on the first one by changing the profile.
-        blocked = (
-            profile.security_profile == HIGHSEC
-            and graph.route(source.system_id, destination.system_id).known
-        )
+        # **Which constraint severed this pair?** Both answers are actionable
+        # and they are different actions, so the probe asks each question
+        # separately instead of one loose "would it connect with nothing
+        # applied" — which reported anything the operator's own avoid list cut
+        # as blocked by security, a reason he cannot act on describing a
+        # constraint he set.
+        reason, detail = NO_ROUTE, haul.reason
+        if (
+            profile.avoid_systems
+            and _route(
+                graph, cache, source.system_id, destination.system_id, profile, avoid=()
+            ).known
+        ):
+            detail = (
+                f"{haul.reason} — the {len(profile.avoid_systems)}-system avoid list is "
+                "what severs this pair; it connects without it"
+            )
+        elif (
+            profile.security_profile != SHORTEST
+            and _route(
+                graph, cache, source.system_id, destination.system_id, profile, security=SHORTEST
+            ).known
+        ):
+            reason = ROUTE_BLOCKED_SECURITY
+            detail = f"{haul.reason} — a route exists, but not one this security profile will fly"
         return _Trip(
             pickup=pickup,
             haul=haul,
             total_jumps=None,
             detour_jumps=None,
             active_minutes=None,
-            reason=ROUTE_BLOCKED_SECURITY if blocked else NO_ROUTE,
-            detail=haul.reason,
+            reason=reason,
+            detail=detail,
         )
 
     detour_jumps = None
diff --git a/tests/test_hauling.py b/tests/test_hauling.py
index 017e6d1..dcee544 100644
--- a/tests/test_hauling.py
+++ b/tests/test_hauling.py
@@ -102,6 +102,7 @@ DEST = Station(AMARR_8, AMARR, DOMAIN, "Amarr")
 
 
 def _profile(**overrides) -> HaulProfile:
+    """A profile with test-friendly defaults; every field is overridable."""
     ship = ShipProfile(
         name="test hauler",
         usable_cargo_m3=overrides.pop("cargo_m3", 1_000_000.0),
@@ -653,3 +654,63 @@ def test_a_plan_with_no_measurable_minutes_is_counted_not_deleted(config):
     scan = _pair_scan(config, [(100.0, 1000.0)], [(300.0, 1000.0)], profile=profile)
     assert scan.plans == []
     assert scan.dropped_unrankable == {"ACTIVE_MINUTES_UNKNOWN": 1}
+
+
+# -- 6. name the blocker correctly -----------------------------------------
+
+
+def _blocked_scan(config, graph, profile):
+    depths = {
+        FORGE: _snapshot(
+            _orders([(100.0, 1000.0)], buy=False, station=JITA_44, system=JITA),
+            region=FORGE,
+            station=JITA_44,
+            system=JITA,
+        ),
+        DOMAIN: _snapshot(
+            _orders([(300.0, 1000.0)], buy=True, station=AMARR_8, system=AMARR),
+            region=DOMAIN,
+            station=AMARR_8,
+            system=AMARR,
+        ),
+    }
+    return scan_hauls(
+        config,
+        profile,
+        stations=[SOURCE, DEST],
+        depths=depths,
+        graph=graph,
+        names={34: "Tritanium"},
+        packaged_volume={34: 0.01},
+        now=NOW,
+    )
+
+
+def test_a_pair_severed_by_the_operators_avoid_list_is_not_a_security_block(config):
+    """The probe re-ran the route with the DEFAULT profile and no avoid list,
+    so anything the avoid list severed came back as blocked by security — a
+    reason the operator cannot act on, describing a constraint he set."""
+    # A corridor that is entirely high-sec, so the security profile cannot be
+    # what severs it — only the operator's own avoid list can.
+    graph = _graph(jumps=2)  # Jita — 90000 — Amarr, all 0.9
+    middle = 90_000
+    profile = _profile(security_profile="highsec", avoid_systems=(middle,))
+    scan = _blocked_scan(config, graph, profile)
+    assert scan.plans == []
+    assert not scan.rejected_for(ROUTE_BLOCKED_SECURITY)
+    rejection = scan.rejected_for(NO_ROUTE)[0]
+    assert "avoid list" in rejection.detail
+
+
+def test_a_pair_severed_by_the_security_profile_still_says_security(config):
+    profile = _profile(security_profile="highsec")
+    scan = _blocked_scan(config, _graph(jumps=2, security=0.2), profile)
+    assert scan.rejected_for(ROUTE_BLOCKED_SECURITY)
+    assert not scan.rejected_for(NO_ROUTE)
+
+
+def test_a_pair_with_no_route_at_all_is_neither(config):
+    graph = RouteGraph([], {JITA: 0.9, AMARR: 0.9}, sde_build=1)
+    scan = _blocked_scan(config, graph, _profile(security_profile="shortest"))
+    rejection = scan.rejected_for(NO_ROUTE)[0]
+    assert "avoid list" not in rejection.detail
```
