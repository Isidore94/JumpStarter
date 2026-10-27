# Plan — per-browser auto-refresh + 30 s GPU badge cache

## Task restatement
1. Home page gets a **Refresh now** button and an **Auto-refresh** choice
   Off / 15 s / 30 s / 60 s; the choice is a cookie (per browser).
2. The countdown **holds (and says so)** while any input field is focused or has
   text in it.
3. A **`<noscript>` meta-refresh fallback** keeps a JS-less browser current.
4. The interval is **validated server-side** against the offered values, so a
   hand-edited cookie cannot turn the page into a one-second reload loop.
5. **Only the dashboard auto-refreshes**; the summary page stays still.
6. The home page's **GPU-node online badge is cached 30 s, display only**; the
   routing probe in `transcribe()` stays live.

## Ambiguities and how I resolved them
- **What "holds" means for the countdown.** Resolved: while any `input`/
  `textarea` on the page is focused or non-empty, the timer stops counting down,
  the status line says it is on hold ("auto-refresh on hold (editing)"), and the
  page never reloads. When the last field is cleared *and* unfocused the
  countdown restarts from the full interval (simplest safe semantics: at least a
  full interval of quiet typing before any reload).
- **Where the interval comes from.** The browser never dictates it: the server
  validates the cookie and only then embeds the seconds in the page
  (`data-refresh` attribute + `<noscript>` meta). A hand-edited cookie value
  outside {off, 15, 30, 60} renders as the default (`off`): no meta-refresh, no
  JS timer. Validation happens at both the write path (`/settings/refresh` POST)
  and the read path (home rendering), so garbage can't act through either.
- **Cookie shape.** Name `dash_refresh`, values exactly the offered ones:
  `off` (default), `15`, `30`, `60`. Persistent cookie (max-age 1 year,
  `samesite=lax`, `path=/`) so each browser remembers its own choice.
- **Which interval the noscript fallback uses.** The same validated interval;
  absent when off. In a JS-less browser the "hold while typing" behavior cannot
  exist — that is inherent to meta-refresh and accepted per the task.
- **Where the badge cache lives.** Next to the probe, in `pipeline.py`, so the
  "display-only" vs "routing" split is visible in one file:
  `gpu_node_online_cached()` (TTL 30 s) for the badge; `gpu_node_online()`
  untouched for `transcribe()` routing.
- **Testing without httpx.** `starlette.testclient` is unusable in this venv, so
  tests call the route handlers directly with a tiny fake request object and
  assert on the HTML / response headers (style already used throughout
  `tests/test_app.py`). One test additionally verifies the routes are actually
  registered on `dashboard.app`.

## Changes

### 1. `pipeline.py`
- Add `import time`.
- Add display-only cached probe:
  ```python
  _GPU_ONLINE_BADGE_SECONDS = 30
  _gpu_online_badge = None  # (probe_time, value) for the dashboard badge only

  def gpu_node_online_cached():
      """gpu_node_online() with a 30 s display cache (dashboard badge)."""
      ...reuses the cached value when now - ts < 30, else probes and stores...
  ```
  Boundary: re-probe at exactly 30 s (`<`, not `<=`).

### 2. `dashboard.py`
- `from fastapi import FastAPI, Form, Request`.
- Constants + validator (module level):
  ```python
  REFRESH_COOKIE = "dash_refresh"
  REFRESH_DEFAULT = "off"
  REFRESH_INTERVALS = ("off", "15", "30", "60")

  def _validated_refresh(value):
      return value if value in REFRESH_INTERVALS else REFRESH_DEFAULT
  ```
- `_page(title, body, meta="", refresh=0)`: inject `{meta}` into `<head>` and
  `data-refresh="{refresh}"` on `<body>` when `refresh` > 0. All existing
  callers keep working (defaults are inert); only `home()` passes values.
- Constant `_REFRESH_JS`: plain `<script>` (no interpolation) that reads
  `document.body.dataset.refresh`; every 500 ms it either counts down
  ("auto-refresh in Ns" → `location.reload()`) or, while any `input`/`textarea`
  is focused or has text, sets the status to "auto-refresh on hold (editing)"
  and resets the countdown to the full interval.
- `home(request: Request)`:
  - `refresh = _validated_refresh(request.cookies.get(REFRESH_COOKIE, REFRESH_DEFAULT))`;
  - when `refresh != "off"`: `secs = int(refresh)`,
    `meta = <noscript><meta http-equiv="refresh" content="{secs}"></noscript>`;
  - render a `.seg` **Auto-refresh** control built exactly like the transcribe
    mode control (`dashboard.py:279-290`): one form per value posting to
    `/settings/refresh` with `<input type="hidden" name="interval" value="...">`
    and a labelled button (Off / 15s / 30s / 60s, active one highlighted),
    preceded by a **Refresh now** button (`<button onclick="location.reload()">`),
    and a `<span id="refresh-status" class="muted">` when auto-refresh is on;
  - badge block: `online = pipeline.gpu_node_online_cached()` (was
    `gpu_node_online()`);
  - return `_page("ContentSummarizer", body, meta=meta, refresh=secs)`; append
    `_REFRESH_JS` to the body when auto-refresh is on.
- New endpoint, mirroring `/settings/transcribe`:
  ```python
  @app.post("/settings/refresh")
  def set_refresh(interval: str = Form(REFRESH_DEFAULT)):
      value = _validated_refresh(interval.strip().lower())
      response = RedirectResponse("/", status_code=303)
      response.set_cookie(REFRESH_COOKIE, value, max_age=31536000,
                          samesite="lax", path="/")
      return response
  ```
  An invalid posted value normalizes to the default (also clears a garbage
  cookie).
- **Not touched:** `summary_page`, `search`, `queue_video`, `drain_now`,
  `retry`, `set_transcribe_mode`, worker/drain logic, `transcribe()` routing.

### 3. `tests/test_app.py` (written red first)
- `RefreshControlTests`:
  - fake `dashboard.worker` / `_summary_files` / `NO_WORKER` in `setUp`;
    cookie-carrying fake request object; env stripped of `GPU_NODE_URL`.
  - home offers the control: `action="/settings/refresh"`, hidden
    `name="interval"` inputs for every offered value, "Refresh now" with
    `location.reload()`, and the route is registered on `dashboard.app`.
  - POST `set_refresh("30")` → 303 to `/` and `set-cookie` carries
    `dash_refresh=30`; every offered value round-trips unchanged.
  - server-side validation: `set_refresh("1")` / `set_refresh("bogus")` → cookie
    is `off`, never the raw value.
  - home honors only valid cookies: cookie `dash_refresh=30` → head contains
    `<noscript><meta http-equiv="refresh" content="30">`, body has
    `data-refresh="30"` and the status span; cookie `dash_refresh=1` (hand-edited
    one-second loop) and no cookie at all → **no** meta refresh, **no**
    `data-refresh` attribute (page sits still).
  - still pages: with the cookie set to `30`, `summary_page()` and `search()`
    HTML contain no meta refresh and no `data-refresh`.
  - badge wiring: with `GPU_NODE_URL` set, `home()` calls
    `pipeline.gpu_node_online_cached()` and not the live
    `pipeline.gpu_node_online()`.
- `GpuBadgeCacheTests`:
  - fake clock + `mock.patch("pipeline.requests.get")` counter: first call
    probes, calls at +29 s hit the cache, at +30 s it re-probes (30 s cap,
    boundary inclusive); offline probe result is cached too.
  - `transcribe()` with `auto` still probes live: warm the badge cache, then
    `transcribe()` triggers a *second* probe and routes to the OpenAI path when
    the node is offline — the display cache must not feed routing.

## Done means
- All new tests exist in `tests/test_app.py` and pass with
  `C:/Users/Aaron/ContentSummarizer/.venv/Scripts/python.exe -m unittest
  discover -s tests` (whole suite green, including the pre-existing tests).
- Diff touches only `dashboard.py`, `pipeline.py`, `tests/test_app.py`
  (plus the `.qo/` outputs). No worker/drain/routing/summary-page behavior
  changes.
