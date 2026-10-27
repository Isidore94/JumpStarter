# Report — per-browser auto-refresh + 30 s GPU badge cache

## What changed

**`dashboard.py`**
- New constants + validator: `REFRESH_COOKIE = "dash_refresh"`,
  `REFRESH_DEFAULT = "off"`, `REFRESH_INTERVALS = ("off", "15", "30", "60")`,
  `_validated_refresh()` — the only interval a page may ever be told to use.
- `home(request: Request)`: reads the cookie, normalizes it through
  `_validated_refresh`, and only then embeds the validated interval in the
  page — `<body data-refresh="N">` and
  `<noscript><meta http-equiv="refresh" content="N"></noscript>` (head,
  home-page only). A hand-edited cookie (`1`, `bogus`, …) renders as `off`:
  no meta refresh, no timer, no reload loop.
- Auto-refresh control on the home page, built exactly like the transcribe
  mode control: a **Refresh now** button (`location.reload()`) and a `.seg` of
  Off / 15s / 30s / 60s forms posting to `/settings/refresh` with
  `<input type="hidden" name="interval">`; the active choice is highlighted,
  and a `#refresh-status` span shows the countdown.
- `_REFRESH_JS` (home page, only when auto-refresh is on): ticks every 500 ms,
  counts down ("auto-refresh in Ns" → reload). While any *visible* input or
  textarea is focused or has text in it the countdown holds — the status says
  "auto-refresh on hold (editing)" and the timer restarts from the full
  interval when the last field is clear. Hidden form inputs are explicitly
  skipped (they carry values and would otherwise hold the timer forever —
  caught in self-review, see below).
- New `POST /settings/refresh` mirroring `/settings/transcribe`: validates the
  posted value against the offered intervals (invalid → default `off`, which
  also clears a garbage cookie), answers 303 → `/` with
  `Set-Cookie: dash_refresh=<value>; Max-Age=31536000; Path=/; SameSite=lax` —
  so the choice persists per browser.
- GPU badge now calls `pipeline.gpu_node_online_cached()` (was the live
  `gpu_node_online()`); the page notes the badge may be up to 30 s stale.

**`pipeline.py`**
- `gpu_node_online_cached()`: `gpu_node_online()` with a module-level
  30 s display cache (`_GPU_ONLINE_BADGE_SECONDS`, re-probes at the boundary),
  clearly commented as display-only. `gpu_node_online()` and `transcribe()`
  are unchanged, so routing still probes live on every call.

**`tests/test_app.py`** (11 new tests, all red before the build)
- `RefreshControlTests`: control rendering (Refresh now + every offered
  interval, route registered on `dashboard.app`); cookie set by the POST
  (303 + `dash_refresh=…`, every offered value round-trips); server-side
  validation of posted values (`1`, `0`, `bogus`, `15x`, `  1` → `off`, never
  the raw value); home honors only valid cookies (valid `30` → meta refresh +
  `data-refresh="30"` + status span; `1`/garbage/absent → no reload hooks at
  all); summary and search pages stay still even with the cookie set; home's
  badge uses the cached probe and not the live one.
- `GpuBadgeCacheTests`: with a fake clock and a mocked `requests.get` counter,
  the badge probes at most once per 30 s (re-probes exactly at the boundary),
  caches offline results too, and `transcribe()` (auto) re-probes live after
  the badge cache is warm and routes to the OpenAI path when the node is
  offline.
- No httpx in the venv, so starlette's TestClient is unusable; tests call the
  route handlers directly with a tiny fake request and assert on the HTML /
  response headers (consistent with the file's existing style).

## Test results
- Red (before build): 10 errors + 1 failure in the new tests, old tests green —
  saved to `.qo/tests-red.txt`.
- Green (after build): `python -m unittest discover -s tests` →
  **Ran 41 tests … OK** (41 = 30 pre-existing + 11 new) — saved to
  `.qo/build.txt`. Lint: none in this repo.
- Visual render check: no cookie → `Off` active, no reload hooks; cookie `30`
  → `<body data-refresh="30">` + noscript meta 30 + status span + JS, `30s`
  active; cookie `1` → treated as off; `POST /settings/refresh 15` → 303 +
  `dash_refresh=15`; summary page → no meta refresh, no `data-refresh`.

## What was skipped / open doubts
- **JS hold behavior is not unit-tested** (no DOM/httpx in this environment);
  verified by inspection and render checks instead.
- **Pre-existing `ResourceWarning`** (unclosed `open()` in `summary_page`/
  `home`) now surfaces because the new tests exercise `summary_page` with a
  real file. Not introduced here; fixing it would touch the summary page,
  which the task says not to.
- JS-less fallback: the meta refresh reloads even while a field has text —
  inherent to `<noscript>` meta refresh, accepted per the task ("keeps a
  JS-less browser current").
- The cache is process-local (module state). That matches how the dashboard
  serves (one process per UI); `attach_worker`/`serve_in_thread` share the
  same process, so there is no cross-process staleness concern.

## Self-review
One real defect found and fixed before the final run: `onHold()` originally
counted *any* input with a value as "editing", but the Auto-refresh /
Transcription controls render `<input type="hidden" value="…">` which always
have values — the countdown would have held permanently and auto-refresh would
never fire. Fixed by skipping `f.type === "hidden"`; suite re-run green after
the fix. Full skeptical pass is recorded in `.qo/review.json` (GO).
