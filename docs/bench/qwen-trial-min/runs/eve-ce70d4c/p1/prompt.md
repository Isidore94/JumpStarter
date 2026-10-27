TASK

Goal: in hauling, a pair whose route is cut by the operator's own avoid list comes back ROUTE_BLOCKED_SECURITY, because the probe re-runs the route with the default profile and no avoid list. Ask the two questions separately, both through the route cache: does it connect without the avoid list? then the avoid list is the blocker: NO_ROUTE with a detail that names the avoid list. Else, does it connect on the shortest profile? then it is ROUTE_BLOCKED_SECURITY. Neither: NO_ROUTE, the pair is genuinely disconnected.
Done when: tests/test_hauling.py has a test for each of the three outcomes; `PYTHONPATH=src python -m pytest -q tests/test_hauling.py` green, ruff clean.
Files: src/evescreener/hauling.py (_route and _trip, around the ROUTE_BLOCKED_SECURITY line); find the rest.
Don't touch: the route cache format, HaulProfile fields, the ranking.
Pattern: the existing reason / detail fields on the plan objects in hauling.py.

Follow the procedure at the top of CLAUDE.md (recon, plan, tests first, build, self-review, report). Stop when
`.qo/report.md` is written.
