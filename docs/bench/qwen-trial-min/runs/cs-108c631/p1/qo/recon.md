# Recon — per-browser auto-refresh + 30 s GPU badge cache

## Files and functions the task touches

### dashboard.py
- `home()` — `dashboard.py:205-335`. The home page renderer (returns a plain HTML
  string; FastAPI wraps it in `HTMLResponse`).
  - Reads `worker.snapshot()` (`:207`), `worker.gh.open_issues()` (`:211`),
    `worker.poll_seconds` (`:297`).
  - **GPU badge block** `:261-269`: only when `pipeline._gpu_node_url()` is set,
    calls `pipeline.gpu_node_online()` (`:263`) **live, on every request** and
    renders `<span class="badge on|off">`. This is the call to replace with the
    cached, display-only variant.
  - **The pattern to copy** — transcribe mode control, `:279-290`: a `.seg` div of
    one `<form method="post" action="/settings/transcribe">` per value, each with
    `<input type="hidden" name="mode" value="...">` and a `<button>` (active one
    gets class `active`). The Auto-refresh choice must post the same shape.
  - `meta_html`/`seg_html`/`controls_html` composed into the first `.card`
    (`:287-308`). `NO_WORKER` (`:271`) swaps in a viewer-mode card but the
    refresh control should be present in both modes.
- `_page(title, body)` — `dashboard.py:162-173`. Shared HTML skeleton used by
  `home()`, `summary_page()` (`:338-360`) and `search()` (`:363-401`). The refresh
  hooks (noscript meta-refresh in `<head>`, `data-refresh` on `<body>`) must be
  opt-in parameters so the summary page and search page stay still.
- `/settings/transcribe` handler — `dashboard.py:428-437`: `POST`,
  `Form(...)` field, normalize + validate against a fixed set, side effect, then
  `RedirectResponse("/", status_code=303)`. The new `/settings/refresh` follows
  this exactly, plus a `Set-Cookie` on the 303 response
  (`RedirectResponse.set_cookie(...)`).
- No cookie reading anywhere today; `home()` has no `request` parameter yet.

### pipeline.py
- `gpu_node_online()` — `pipeline.py:388-398`: live probe,
  `requests.get(url + "/health", timeout=1.5).ok`, `False` when `GPU_NODE_URL`
  unset or on any exception. **Must keep probing live** — used by routing.
- `transcribe()` — `pipeline.py:424-446`: with `auto` backend it calls
  `gpu_node_online()` at `:430` on every call → routes `remote` vs `openai`.
  Untouched by this task.
- `pipeline.py` imports: no `time` import yet (needed for the cache timestamp).
- `gpu_node_online` has exactly two callers repo-wide: `dashboard.py:263` (badge)
  and `pipeline.py:430` (routing). Confirmed by grep.

### worker.py / drain.py
- `Worker` (`worker.py:39+`): `snapshot()` dict (`state`, `last_poll`,
  `last_result`, `ok_total`, `failed_total`, ...), `gh.open_issues()`,
  `poll_seconds`, `request_drain()`. Only needed to fake `dashboard.worker` in
  tests. No changes.

### tests/test_app.py
- Plain `unittest`, no pytest. Existing style: call module functions directly,
  `mock.patch.dict(os.environ, ...)`, `tempfile.TemporaryDirectory`. No
  FastAPI/TestClient usage — and the venv has **no httpx**, so
  `starlette.testclient.TestClient` is unusable here (starlette 1.7 requires
  httpx/httpx2). Tests will call the route handlers directly
  (`dashboard.home(fake_request)`, `dashboard.set_refresh(...)`) and assert on
  the returned HTML / `RedirectResponse.status_code` / `set-cookie` header, plus
  one route-wiring check against `dashboard.app.routes`.

## Environment facts
- Python: `C:/Users/Aaron/ContentSummarizer/.venv/Scripts/python.exe`
  (fastapi 0.143.0, starlette 1.7.0, requests 2.34.2, **no httpx**).
- Test command: `python -m unittest discover -s tests`. No linter in repo.
- `.env` is absent in this checkout, so `load_dotenv()` at import time is a no-op;
  tests will still set env explicitly for determinism.
- TestClient without a context manager would skip lifespan anyway, but it cannot
  be imported at all, so direct handler calls are the approach.
