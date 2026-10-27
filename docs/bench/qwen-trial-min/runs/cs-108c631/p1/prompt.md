TASK

Goal: the web dashboard keeps itself up to date, per browser. Add a "Refresh now" button and an Auto-refresh choice Off / 15s / 30s / 60s on the home page; the choice is stored in a cookie so each browser has its own. The countdown holds (and says so) while any input field is focused or has text in it. A <noscript> meta-refresh fallback keeps a JS-less browser current. The interval is validated server-side against the offered values, so a hand-edited cookie cannot turn the page into a one-second reload loop. Only the dashboard auto-refreshes; a summary page being read sits still.
Also: cache the home page's GPU-node online badge for 30 s, display only; the routing decision in transcribe() must still probe live.
Done when: tests in tests/test_app.py cover the control, the cookie, the server-side validation and the badge cache, and `python -m unittest discover -s tests` is green.
Files: dashboard.py (home() and the settings form), pipeline.gpu_node_online() for the badge; find the rest.
Don't touch: the worker/drain logic, transcription routing, the summary page.
Pattern: the Auto-refresh control posts a form exactly like the existing /settings/transcribe mode control.

Follow the procedure at the top of CLAUDE.md (recon, plan, tests first, build, self-review, report). Stop when
`.qo/report.md` is written.
