# BRIEF
Goal: the web dashboard keeps itself up to date, per browser. Add a "Refresh now" button and an Auto-refresh choice Off / 15s / 30s / 60s on the home page; the choice is stored in a cookie so each browser has its own. The countdown holds (and says so) while any input field is focused or has text in it. A <noscript> meta-refresh fallback keeps a JS-less browser current. The interval is validated server-side against the offered values, so a hand-edited cookie cannot turn the page into a one-second reload loop. Only the dashboard auto-refreshes; a summary page being read sits still.
Also: cache the home page's GPU-node online badge for 30 s, display only; the routing decision in transcribe() must still probe live.
Done when: tests in tests/test_app.py cover the control, the cookie, the server-side validation and the badge cache, and `python -m unittest discover -s tests` is green.
Files: dashboard.py (home() and the settings form), pipeline.gpu_node_online() for the badge; find the rest.
Don't touch: the worker/drain logic, transcription routing, the summary page.
Pattern: the Auto-refresh control posts a form exactly like the existing /settings/transcribe mode control.

# CANDIDATE DIFF
```diff
diff --git a/dashboard.py b/dashboard.py
index 6c9cea7..766a4de 100644
--- a/dashboard.py
+++ b/dashboard.py
@@ -24,7 +24,7 @@ from logging.handlers import RotatingFileHandler
 
 import markdown as md
 from dotenv import load_dotenv
-from fastapi import FastAPI, Form
+from fastapi import FastAPI, Form, Request
 from fastapi.responses import HTMLResponse, RedirectResponse
 
 import drain
@@ -58,6 +58,19 @@ NO_WORKER = os.environ.get("DASHBOARD_NO_WORKER", "").strip().lower() in {
 # `git pull` brings them to disk. (No-op when there's nothing to fetch.)
 SUMMARY_PULL_SECONDS = int(os.environ.get("SUMMARY_PULL_SECONDS") or 60)
 
+# Per-browser auto-refresh for the home page. The choice lives in a cookie so
+# each browser keeps its own; the server only ever accepts the offered
+# intervals (validated on the way in AND on the way out), so a hand-edited
+# cookie can't turn the page into a fast reload loop.
+REFRESH_COOKIE = "dash_refresh"
+REFRESH_DEFAULT = "off"
+REFRESH_INTERVALS = ("off", "15", "30", "60")
+
+
+def _validated_refresh(value):
+    """The only refresh interval a page will ever be told to use."""
+    return value if value in REFRESH_INTERVALS else REFRESH_DEFAULT
+
 worker: Worker | None = None
 
 
@@ -159,14 +172,20 @@ a:hover { text-decoration: underline; }
 """
 
 
-def _page(title, body):
+def _page(title, body, meta="", refresh=0):
+    """Shared HTML skeleton. `meta` is extra head markup; `refresh` (seconds,
+    0 = off) lets ONLY the home page carry the auto-refresh hooks â€” a summary
+    page being read stays still."""
+    data = f' data-refresh="{int(refresh)}"' if refresh else ""
     return (
         "<!doctype html><html><head>"
         '<meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width, initial-scale=1">'
         f"<title>{html.escape(title)}</title>"
         f"<style>{_CSS}</style>"
-        "</head><body>"
+        f"{meta}"
+        "</head><body"
+        f"{data}>"
         '<h1><a href="/">ðŸ“¼ ContentSummarizer</a></h1>'
         f"{body}"
         "</body></html>"
@@ -202,9 +221,51 @@ def _summary_files():
     )
 
 
+# The auto-refresh countdown. It only ever reads the server-validated interval
+# off the body's data-refresh attribute, so the page can reload on no faster
+# schedule than the server offered. While any input field is focused or has
+# text in it the countdown holds (and says so) instead of reloading.
+_REFRESH_JS = """
+<script>
+(function () {
+  var secs = parseInt(document.body.dataset.refresh || "0", 10);
+  if (!secs) return;
+  var status = document.getElementById("refresh-status");
+  if (!status) return;
+  var fields = Array.prototype.slice.call(
+    document.querySelectorAll("input, textarea")
+  );
+  var next = Date.now() + secs * 1000;
+  function onHold() {
+    for (var i = 0; i < fields.length; i++) {
+      var f = fields[i];
+      if (f.type === "hidden") continue;  // the form's own hidden inputs
+      if (document.activeElement === f || f.value.length > 0) return true;
+    }
+    return false;
+  }
+  setInterval(function () {
+    if (onHold()) {
+      // Holding: never reload while the reader is typing; the countdown
+      // restarts from the full interval once every field is clear.
+      next = Date.now() + secs * 1000;
+      status.textContent = "auto-refresh on hold (editing)";
+    } else {
+      var left = Math.ceil((next - Date.now()) / 1000);
+      if (left <= 0) { location.reload(); return; }
+      status.textContent = "auto-refresh in " + left + "s";
+    }
+  }, 500);
+})();
+</script>
+"""
+
+
 @app.get("/", response_class=HTMLResponse)
-def home():
+def home(request: Request):
     s = worker.snapshot()
+    refresh = _validated_refresh(request.cookies.get(REFRESH_COOKIE, REFRESH_DEFAULT))
+    refresh_secs = 0 if refresh == REFRESH_DEFAULT else int(refresh)
 
     queue_err = None
     try:
@@ -260,7 +321,9 @@ def home():
 
     gpu_html = ""
     if pipeline._gpu_node_url():
-        online = pipeline.gpu_node_online()
+        # Display-only: the badge may be up to 30 s stale; transcribe()
+        # routing still probes live.
+        online = pipeline.gpu_node_online_cached()
         gpu_badge = (
             '<span class="badge on">online</span>'
             if online
@@ -297,6 +360,29 @@ def home():
             f"polling every {worker.poll_seconds}s</p>"
         )
 
+    refresh_seg = []
+    for value, label in (("off", "Off"), ("15", "15s"), ("30", "30s"), ("60", "60s")):
+        active = " active" if refresh == value else ""
+        refresh_seg.append(
+            f'<form method="post" action="/settings/refresh">'
+            f'<input type="hidden" name="interval" value="{value}">'
+            f'<button class="{active.strip()}">{label}</button></form>'
+        )
+    status_html = (
+        ' <span id="refresh-status" class="muted"></span>' if refresh_secs else ""
+    )
+    refresh_html = (
+        '<div class="seg"><span class="muted">Auto-refresh:</span>'
+        '<button onclick="location.reload()">Refresh now</button>'
+        f'{"".join(refresh_seg)}{status_html}</div>'
+    )
+    meta = (
+        f'<noscript><meta http-equiv="refresh" content="{refresh_secs}">'
+        "</noscript>"
+        if refresh_secs
+        else ""
+    )
+
     body = f"""
 <div class="card">
   <div class="status-line">
@@ -307,6 +393,7 @@ def home():
   </div>
   {meta_html}
   {seg_html}
+  {refresh_html}
   {controls_html}
 </div>
 
@@ -332,7 +419,9 @@ def home():
   {summaries_html}
 </div>
 """
-    return _page("ContentSummarizer", body)
+    if refresh_secs:
+        body += _REFRESH_JS
+    return _page("ContentSummarizer", body, meta=meta, refresh=refresh_secs)
 
 
 @app.get("/s/{stem}", response_class=HTMLResponse)
@@ -437,6 +526,25 @@ def set_transcribe_mode(mode: str = Form(...)):
     return RedirectResponse("/", status_code=303)
 
 
+@app.post("/settings/refresh")
+def set_refresh(interval: str = Form(REFRESH_DEFAULT)):
+    """Store this browser's auto-refresh choice in a cookie.
+
+    Mirrors /settings/transcribe, but persists per browser via a cookie
+    instead of an environment variable. The value is validated against the
+    offered intervals, so a hand-edited form or cookie can't set a faster
+    reload than the page offers (an invalid value normalizes to the default,
+    which also clears a garbage cookie).
+    """
+    value = _validated_refresh(interval.strip().lower())
+    log.info("auto-refresh set to %s", value)
+    response = RedirectResponse("/", status_code=303)
+    response.set_cookie(
+        REFRESH_COOKIE, value, max_age=60 * 60 * 24 * 365, samesite="lax", path="/"
+    )
+    return response
+
+
 @app.post("/retry/{number}")
 def retry(number: int):
     try:
diff --git a/pipeline.py b/pipeline.py
index 881ab2c..73717a2 100644
--- a/pipeline.py
+++ b/pipeline.py
@@ -18,6 +18,7 @@ import shutil
 import subprocess
 import sys
 import tempfile
+import time
 from contextlib import redirect_stderr, redirect_stdout
 from urllib.parse import urlsplit
 
@@ -398,6 +399,28 @@ def gpu_node_online():
         return False
 
 
+# Display-only badge cache: the dashboard re-probes the GPU PC at most every
+# _GPU_ONLINE_BADGE_SECONDS, so each home-page render is cheap even with the
+# node offline (an unreachable host costs the full probe timeout). Routing
+# must never use this â€” transcribe() probes live via gpu_node_online() so a
+# node that just died is not chosen for the next video.
+_GPU_ONLINE_BADGE_SECONDS = 30
+_gpu_online_badge = None  # (probe time, value) for the dashboard badge only
+
+
+def gpu_node_online_cached():
+    """gpu_node_online() with a _GPU_ONLINE_BADGE_SECONDS s display cache."""
+    global _gpu_online_badge
+    now = time.time()
+    if _gpu_online_badge is not None:
+        probed_at, value = _gpu_online_badge
+        if now - probed_at < _GPU_ONLINE_BADGE_SECONDS:
+            return value
+    value = gpu_node_online()
+    _gpu_online_badge = (now, value)
+    return value
+
+
 def transcribe_remote(url):
     """Transcribe by delegating to a gpu_node.py instance on the LAN."""
     node = _gpu_node_url()
diff --git a/tests/test_app.py b/tests/test_app.py
index dd3f7b9..00561c7 100644
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -8,6 +8,7 @@ from pathlib import Path
 from unittest import mock
 
 import app_config
+import dashboard
 import drain
 import pipeline
 
@@ -286,5 +287,196 @@ class SafetyTests(unittest.TestCase):
         self.assertEqual(result.stdout.strip(), "2026.test")
 
 
+class _FakeGitHub:
+    def open_issues(self):
+        return []
+
+
+class _FakeWorker:
+    """Just enough of worker.Worker for dashboard.home()."""
+
+    poll_seconds = 30
+
+    def __init__(self):
+        self.gh = _FakeGitHub()
+
+    def snapshot(self):
+        return {
+            "state": "idle",
+            "last_poll": None,
+            "last_result": None,
+            "ok_total": 0,
+            "failed_total": 0,
+        }
+
+    def request_drain(self):
+        pass
+
+
+class _FakeRequest:
+    """Just enough of starlette Request for a dashboard handler."""
+
+    def __init__(self, cookies=None):
+        self.cookies = cookies or {}
+
+
+class _FakeClock:
+    def __init__(self, now=1_000_000.0):
+        self.now = now
+
+    def time(self):
+        return self.now
+
+
+class RefreshControlTests(unittest.TestCase):
+    """The home page's per-browser auto-refresh: control, cookie, validation.
+
+    The venv has no httpx, so starlette's TestClient is unavailable; these
+    tests call the route handlers directly and assert on the HTML / response
+    headers they produce.
+    """
+
+    def setUp(self):
+        env = {
+            k: v
+            for k, v in os.environ.items()
+            if k not in ("GPU_NODE_URL", "TRANSCRIBE_BACKEND", "DASHBOARD_NO_WORKER")
+        }
+        self._patches = [
+            mock.patch.dict(os.environ, env, clear=True),
+            mock.patch.object(dashboard, "worker", _FakeWorker()),
+            mock.patch.object(dashboard, "_summary_files", lambda: []),
+            mock.patch.object(dashboard, "NO_WORKER", False),
+        ]
+        for patch in self._patches:
+            patch.start()
+
+    def tearDown(self):
+        for patch in reversed(self._patches):
+            patch.stop()
+
+    def home_html(self, cookies=None):
+        return dashboard.home(_FakeRequest(cookies))
+
+    def test_home_offers_refresh_now_and_the_offered_intervals(self):
+        text = self.home_html()
+        self.assertIn("Refresh now", text)
+        self.assertIn("location.reload()", text)
+        self.assertIn('action="/settings/refresh"', text)
+        for value in ("off", "15", "30", "60"):
+            self.assertIn(f'name="interval" value="{value}"', text, value)
+
+    def test_settings_refresh_route_is_registered(self):
+        routes = [
+            (route.path, set(route.methods or set())) for route in dashboard.app.routes
+        ]
+        self.assertIn(("/settings/refresh", {"POST"}), routes)
+
+    def test_refresh_post_redirects_and_sets_the_cookie(self):
+        response = dashboard.set_refresh("30")
+        self.assertEqual(response.status_code, 303)
+        self.assertEqual(response.headers["location"], "/")
+        self.assertIn("dash_refresh=30", response.headers["set-cookie"])
+
+    def test_every_offered_interval_round_trips_through_the_cookie(self):
+        for value in ("off", "15", "30", "60"):
+            cookie = dashboard.set_refresh(value).headers["set-cookie"]
+            self.assertIn(f"dash_refresh={value}", cookie, value)
+
+    def test_hand_edited_cookie_cannot_set_a_faster_interval(self):
+        for value in ("1", "0", "bogus", "15x", "  1"):
+            cookie = dashboard.set_refresh(value).headers["set-cookie"]
+            self.assertIn("dash_refresh=off", cookie, value)
+            self.assertNotIn(f"dash_refresh={value}", cookie)
+
+    def test_home_renders_the_meta_refresh_for_a_valid_cookie(self):
+        text = self.home_html({"dash_refresh": "30"})
+        self.assertIn(
+            '<noscript><meta http-equiv="refresh" content="30"></noscript>', text
+        )
+        self.assertIn('data-refresh="30"', text)
+        self.assertIn('id="refresh-status"', text)
+
+    def test_home_ignores_a_cookie_outside_the_offered_values(self):
+        # A hand-edited cookie must not turn the page into a fast reload loop.
+        for cookies in ({"dash_refresh": "1"}, {"dash_refresh": "bogus"}, {}):
+            text = self.home_html(cookies)
+            self.assertNotIn('http-equiv="refresh"', text, cookies)
+            self.assertNotIn("data-refresh=", text, cookies)
+
+    def test_home_badge_uses_the_cached_probe_not_the_live_one(self):
+        with mock.patch.dict(
+            os.environ, {"GPU_NODE_URL": "http://10.0.0.5:8788"}
+        ), mock.patch("pipeline.gpu_node_online_cached", return_value=True) as cached, \
+             mock.patch("pipeline.gpu_node_online", return_value=False) as live:
+            text = self.home_html()
+        cached.assert_called_once_with()
+        live.assert_not_called()
+        self.assertIn('class="badge on"', text)
+
+    def test_summary_page_stays_still_even_when_auto_refresh_is_on(self):
+        with tempfile.TemporaryDirectory() as tmp:
+            (Path(tmp) / "abc.txt").write_text("# T\n\nText\n", encoding="utf-8")
+            with mock.patch.object(dashboard, "_summary_dir", lambda: tmp):
+                text = dashboard.summary_page("abc")
+        self.assertNotIn('http-equiv="refresh"', text)
+        self.assertNotIn("data-refresh=", text)
+
+    def test_search_page_stays_still_even_when_auto_refresh_is_on(self):
+        text = dashboard.search("q")
+        self.assertNotIn('http-equiv="refresh"', text)
+        self.assertNotIn("data-refresh=", text)
+
+
+class GpuBadgeCacheTests(unittest.TestCase):
+    """The dashboard badge probes at most every 30 s; routing probes live."""
+
+    def _reset_cache(self):
+        pipeline._gpu_online_badge = None
+
+    def test_badge_probes_at_most_every_30_seconds(self):
+        clock = _FakeClock()
+        with mock.patch.dict(
+            os.environ, {"GPU_NODE_URL": "http://10.0.0.5:8788"}
+        ), mock.patch("pipeline.requests.get") as get, \
+             mock.patch.object(pipeline.time, "time", clock.time):
+            self._reset_cache()
+            get.return_value = mock.Mock(ok=True)
+            self.assertTrue(pipeline.gpu_node_online_cached())
+            clock.now += 29
+            self.assertTrue(pipeline.gpu_node_online_cached())
+            self.assertEqual(get.call_count, 1)
+            clock.now += 2  # exactly 30 s after the first probe -> re-probe
+            self.assertTrue(pipeline.gpu_node_online_cached())
+            self.assertEqual(get.call_count, 2)
+
+    def test_badge_cache_remembers_an_offline_node(self):
+        clock = _FakeClock()
+        with mock.patch.dict(
+            os.environ, {"GPU_NODE_URL": "http://10.0.0.5:8788"}
+        ), mock.patch("pipeline.requests.get") as get, \
+             mock.patch.object(pipeline.time, "time", clock.time):
+            self._reset_cache()
+            get.return_value = mock.Mock(ok=False)
+            self.assertFalse(pipeline.gpu_node_online_cached())
+            self.assertFalse(pipeline.gpu_node_online_cached())
+            self.assertEqual(get.call_count, 1)
+
+    def test_transcribe_routes_on_a_live_probe_not_the_badge_cache(self):
+        clock = _FakeClock()
+        with mock.patch.dict(
+            os.environ,
+            {"GPU_NODE_URL": "http://10.0.0.5:8788", "TRANSCRIBE_BACKEND": "auto"},
+        ), mock.patch("pipeline.requests.get") as get, \
+             mock.patch.object(pipeline.time, "time", clock.time), \
+             mock.patch("pipeline.transcribe_openai", return_value="text") as oai:
+            self._reset_cache()
+            get.return_value = mock.Mock(ok=False)  # node offline
+            pipeline.gpu_node_online_cached()  # badge probe (call 1)
+            self.assertEqual(pipeline.transcribe("https://youtu.be/abc"), "text")
+            self.assertEqual(get.call_count, 2)  # routing re-probed, not cached
+            oai.assert_called_once_with("https://youtu.be/abc")
+
+
 if __name__ == "__main__":
     unittest.main()
```

# LEAD TEST RESULTS
## builder's own test command (exit )
```
test_badge_probes_at_most_every_30_seconds (test_app.GpuBadgeCacheTests.test_badge_probes_at_most_every_30_seconds) ... ok
test_transcribe_routes_on_a_live_probe_not_the_badge_cache (test_app.GpuBadgeCacheTests.test_transcribe_routes_on_a_live_probe_not_the_badge_cache) ... ok
test_existing_repository_markdown_is_imported_as_text (test_app.OutputTests.test_existing_repository_markdown_is_imported_as_text) ... ok
test_filenames_include_video_id_and_do_not_collide (test_app.OutputTests.test_filenames_include_video_id_and_do_not_collide) ... ok
test_write_summary_creates_plain_text_file (test_app.OutputTests.test_write_summary_creates_plain_text_file) ... ok
test_every_offered_interval_round_trips_through_the_cookie (test_app.RefreshControlTests.test_every_offered_interval_round_trips_through_the_cookie) ... ok
test_hand_edited_cookie_cannot_set_a_faster_interval (test_app.RefreshControlTests.test_hand_edited_cookie_cannot_set_a_faster_interval) ... ok
test_home_badge_uses_the_cached_probe_not_the_live_one (test_app.RefreshControlTests.test_home_badge_uses_the_cached_probe_not_the_live_one) ... ok
test_home_ignores_a_cookie_outside_the_offered_values (test_app.RefreshControlTests.test_home_ignores_a_cookie_outside_the_offered_values) ... ok
test_home_offers_refresh_now_and_the_offered_intervals (test_app.RefreshControlTests.test_home_offers_refresh_now_and_the_offered_intervals) ... ok
test_home_renders_the_meta_refresh_for_a_valid_cookie (test_app.RefreshControlTests.test_home_renders_the_meta_refresh_for_a_valid_cookie) ... ok
test_refresh_post_redirects_and_sets_the_cookie (test_app.RefreshControlTests.test_refresh_post_redirects_and_sets_the_cookie) ... ok
test_search_page_stays_still_even_when_auto_refresh_is_on (test_app.RefreshControlTests.test_search_page_stays_still_even_when_auto_refresh_is_on) ... ok
test_settings_refresh_route_is_registered (test_app.RefreshControlTests.test_settings_refresh_route_is_registered) ... ok
test_summary_page_stays_still_even_when_auto_refresh_is_on (test_app.RefreshControlTests.test_summary_page_stays_still_even_when_auto_refresh_is_on) ... C:\Users\Aaron\llm-harness\wt\qtm-108c631\dashboard.py:439: ResourceWarning: unclosed file <_io.TextIOWrapper name='C:\\Users\\Aaron\\AppData\\Local\\Temp\\tmpc5rgucfi\\abc.txt' mode='r' encoding='utf-8'>
  text = open(path, encoding="utf-8").read()
ResourceWarning: Enable tracemalloc to get the object allocation traceback
ok
test_failure_comments_are_bounded_and_single_line (test_app.SafetyTests.test_failure_comments_are_bounded_and_single_line) ... ok
test_frozen_yt_dlp_uses_bundled_entrypoint (test_app.SafetyTests.test_frozen_yt_dlp_uses_bundled_entrypoint) ... ok
test_non_youtube_and_local_urls_are_rejected (test_app.SafetyTests.test_non_youtube_and_local_urls_are_rejected) ... ok
test_youtube_url_allowlist (test_app.SafetyTests.test_youtube_url_allowlist) ... ok
test_yt_dlp_timeout_becomes_pipeline_error (test_app.SafetyTests.test_yt_dlp_timeout_becomes_pipeline_error) ... ok
test_detail_levels_are_distinct (test_app.SummaryConfigurationTests.test_detail_levels_are_distinct) ... ok
test_prompts_are_learning_first (test_app.SummaryConfigurationTests.test_prompts_are_learning_first)
Summaries must teach the content, not mention topics (Aaron's prime ... ok
test_settings_round_trip (test_app.SummaryConfigurationTests.test_settings_round_trip) ... ok
test_settings_written_before_the_chime_option_still_load (test_app.SummaryConfigurationTests.test_settings_written_before_the_chime_option_still_load) ... ok
test_unknown_pipeline_detail_is_rejected (test_app.SummaryConfigurationTests.test_unknown_pipeline_detail_is_rejected) ... ok
test_ages_read_as_plain_english (test_app.SummaryListTests.test_ages_read_as_plain_english) ... ok
test_clipboard_only_offers_a_real_youtube_link (test_app.SummaryListTests.test_clipboard_only_offers_a_real_youtube_link) ... ok
test_filter_matches_every_word_in_any_order (test_app.SummaryListTests.test_filter_matches_every_word_in_any_order) ... ok
test_only_unseen_files_count_as_new (test_app.SummaryListTests.test_only_unseen_files_count_as_new) ... ok
test_pretty_title_drops_the_video_id_suffix (test_app.SummaryListTests.test_pretty_title_drops_the_video_id_suffix)
It must undo exactly what drain.summary_filename() builds. ... ok

----------------------------------------------------------------------
Ran 41 tests in 0.215s

OK
```
## lint (exit )
```
```
## hidden reference tests (exit )
```
AttributeError: module 'dashboard' has no attribute 'REFRESH_CHOICES'. Did you mean: 'REFRESH_COOKIE'?

======================================================================
ERROR: test_the_choice_survives_a_reload_and_can_be_turned_back_off (tests.ref_test_app.WebRefreshTests.test_the_choice_survives_a_reload_and_can_be_turned_back_off)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\Aaron\llm-harness\wt\qtm-108c631\tests\ref_test_app.py", line 343, in test_the_choice_survives_a_reload_and_can_be_turned_back_off
    self.assertEqual(self.client.cookies.get(self.dashboard.REFRESH_COOKIE), "60")
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Aaron\ContentSummarizer\.venv\Lib\site-packages\httpx2\_models.py", line 1160, in get
    raise CookieConflict(message)
httpx2.CookieConflict: Multiple cookies exist with name=dash_refresh

======================================================================
ERROR: test_the_gpu_badge_is_not_probed_on_every_reload (tests.ref_test_app.WebRefreshTests.test_the_gpu_badge_is_not_probed_on_every_reload)
A switched-off GPU PC costs a multi-second timeout. Paying it once per page
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\Aaron\llm-harness\wt\qtm-108c631\tests\ref_test_app.py", line 368, in test_the_gpu_badge_is_not_probed_on_every_reload
    self.dashboard._gpu_status["checked_at"] = 0.0
    ^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: module 'dashboard' has no attribute '_gpu_status'

======================================================================
FAIL: test_a_tampered_cookie_cannot_turn_into_a_reload_loop (tests.ref_test_app.WebRefreshTests.test_a_tampered_cookie_cannot_turn_into_a_reload_loop)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\Aaron\llm-harness\wt\qtm-108c631\tests\ref_test_app.py", line 354, in test_a_tampered_cookie_cannot_turn_into_a_reload_loop
    self.assertNotIn("location.reload", page)
AssertionError: 'location.reload' unexpectedly found in '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ContentSummarizer</title><style>\n:root { color-scheme: light dark; }\n* { box-sizing: border-box; }\nbody { font: 15px/1.55 system-ui, "Segoe UI", sans-serif; max-width: 840px;\n       margin: 0 auto; padding: 24px 16px; background: #f7f7f8; color: #1a1a1a; }\nh1 { font-size: 22px; margin: 0 0 4px; }\nh1 a { color: inherit; text-decoration: none; }\nh2 { font-size: 15px; text-transform: uppercase; letter-spacing: .04em;\n     color: #666; margin: 22px 0 8px; }\n.card { background: #fff; border: 1px solid #e3e3e6; border-radius: 10px;\n        padding: 14px 18px; margin: 10px 0; }\n.muted { color: #777; font-size: 13px; }\ninput[type=text], textarea { width: 100%; max-width: 520px; padding: 8px 10px;\n        border: 1px solid #ccc; border-radius: 8px; background: inherit; color: inherit; }\ntextarea { font: inherit; resize: vertical; min-height: 62px; margin-top: 8px; }\n.field-hint { margin: 6px 0 10px; }\nbutton { padding: 7px 14px; border: 0; border-radius: 8px; background: #2563eb;\n         color: #fff; cursor: pointer; font-size: 14px; }\nbutton:hover { background: #1d4ed8; }\nform.inline { display: inline; margin-left: 6px; }\nform.inline button { padding: 2px 10px; font-size: 12px; background: #64748b; }\n.badge { border-radius: 6px; padding: 1px 8px; font-size: 12px; margin-left: 6px; }\n.badge.fail { background: #dc2626; color: #fff; }\n.badge.on { background: #16a34a; color: #fff; }\n.badge.off { background: #6b7280; color: #fff; }\n.seg { display: inline-flex; gap: 6px; align-items: center; flex-wrap: wrap; }\n.seg form { display: inline; }\n.seg button { background: #64748b; padding: 4px 12px; font-size: 13px; }\n.seg button.active { background: #2563eb; }\nul { padding-left: 20px; margin: 6px 0; }\nli { margin: 7px 0; }\na { color: #2563eb; text-decoration: none; }\na:hover { text-decoration: underline; }\n.prose { background: #fff; border: 1px solid #e3e3e6; border-radius: 10px;\n         padding: 20px 26px; }\n.prose h1 { font-size: 20px; }\n.status-line { display: flex; gap: 18px; flex-wrap: wrap; }\n@media (prefers-color-scheme: dark) {\n  body { background: #121214; color: #e6e6e9; }\n  .card, .prose { background: #1c1c1f; border-color: #333338; }\n  h2 { color: #9a9aa3; }\n  .muted { color: #94949c; }\n  input[type=text], textarea { border-color: #44444a; }\n  a { color: #7aa2ff; }\n}\n</style></head><body><h1><a href="/">\U0001f4fc ContentSummarizer</a></h1>\n<div class="card">\n  <div class="status-line">\n    <span><b>State:</b> idle</span>\n    <span><b>Last poll:</b> never (—)</span>\n    <span><b>Lifetime:</b> 0 ok / 0 failed</span>\n    \n  </div>\n  <p class="muted">summaries via openai · polling every 120s</p>\n  <div class="seg"><span class="muted">Transcription:</span><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="auto"><button class="active">Auto</button></form><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="openai"><button class="">OpenAI API</button></form><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="remote"><button class="">GPU PC</button></form><span class="muted">(resets to .env on restart)</span></div>\n  <div class="seg"><span class="muted">Auto-refresh:</span><button onclick="location.reload()">Refresh now</button><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="off"><button class="active">Off</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="15"><button class="">15s</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="30"><button class="">30s</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="60"><button class="">60s</button></form></div>\n  <p style="margin-bottom:0"><form class="inline" method="post" action="/drain" style="margin-left:0"><button>Drain now</button></form></p>\n</div>\n\n<h2>Add a video</h2>\n<div class="card">\n  <form method="post" action="/queue">\n    <input type="text" name="url" placeholder="https://www.youtube.com/watch?v=..." required>\n    <textarea name="prompt" rows="3" placeholder="Optional: tell the AI how to summarize this one — e.g. &quot;focus on the investing advice and list every ticker mentioned&quot;"></textarea>\n    <p class="muted field-hint">Leave the prompt empty for the normal summary.</p>\n    <button>Queue it</button>\n  </form>\n</div>\n\n<h2>Queue</h2>\n<div class="card"><p class="muted">Could not reach GitHub: &#x27;NoneType&#x27; object has no attribute &#x27;open_issues&#x27;</p></div>\n\n<h2>Summaries</h2>\n<div class="card">\n  <form method="get" action="/search">\n    <input type="text" name="q" placeholder="Search summaries...">\n    <button>Search</button>\n  </form>\n  <p class="muted">No summaries yet.</p>\n</div>\n</body></html>'

======================================================================
FAIL: test_choosing_an_interval_makes_the_page_reload_itself (tests.ref_test_app.WebRefreshTests.test_choosing_an_interval_makes_the_page_reload_itself)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\Aaron\llm-harness\wt\qtm-108c631\tests\ref_test_app.py", line 337, in test_choosing_an_interval_makes_the_page_reload_itself
    self.assertIn("refreshing in 30s", page)
AssertionError: 'refreshing in 30s' not found in '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ContentSummarizer</title><style>\n:root { color-scheme: light dark; }\n* { box-sizing: border-box; }\nbody { font: 15px/1.55 system-ui, "Segoe UI", sans-serif; max-width: 840px;\n       margin: 0 auto; padding: 24px 16px; background: #f7f7f8; color: #1a1a1a; }\nh1 { font-size: 22px; margin: 0 0 4px; }\nh1 a { color: inherit; text-decoration: none; }\nh2 { font-size: 15px; text-transform: uppercase; letter-spacing: .04em;\n     color: #666; margin: 22px 0 8px; }\n.card { background: #fff; border: 1px solid #e3e3e6; border-radius: 10px;\n        padding: 14px 18px; margin: 10px 0; }\n.muted { color: #777; font-size: 13px; }\ninput[type=text], textarea { width: 100%; max-width: 520px; padding: 8px 10px;\n        border: 1px solid #ccc; border-radius: 8px; background: inherit; color: inherit; }\ntextarea { font: inherit; resize: vertical; min-height: 62px; margin-top: 8px; }\n.field-hint { margin: 6px 0 10px; }\nbutton { padding: 7px 14px; border: 0; border-radius: 8px; background: #2563eb;\n         color: #fff; cursor: pointer; font-size: 14px; }\nbutton:hover { background: #1d4ed8; }\nform.inline { display: inline; margin-left: 6px; }\nform.inline button { padding: 2px 10px; font-size: 12px; background: #64748b; }\n.badge { border-radius: 6px; padding: 1px 8px; font-size: 12px; margin-left: 6px; }\n.badge.fail { background: #dc2626; color: #fff; }\n.badge.on { background: #16a34a; color: #fff; }\n.badge.off { background: #6b7280; color: #fff; }\n.seg { display: inline-flex; gap: 6px; align-items: center; flex-wrap: wrap; }\n.seg form { display: inline; }\n.seg button { background: #64748b; padding: 4px 12px; font-size: 13px; }\n.seg button.active { background: #2563eb; }\nul { padding-left: 20px; margin: 6px 0; }\nli { margin: 7px 0; }\na { color: #2563eb; text-decoration: none; }\na:hover { text-decoration: underline; }\n.prose { background: #fff; border: 1px solid #e3e3e6; border-radius: 10px;\n         padding: 20px 26px; }\n.prose h1 { font-size: 20px; }\n.status-line { display: flex; gap: 18px; flex-wrap: wrap; }\n@media (prefers-color-scheme: dark) {\n  body { background: #121214; color: #e6e6e9; }\n  .card, .prose { background: #1c1c1f; border-color: #333338; }\n  h2 { color: #9a9aa3; }\n  .muted { color: #94949c; }\n  input[type=text], textarea { border-color: #44444a; }\n  a { color: #7aa2ff; }\n}\n</style></head><body><h1><a href="/">\U0001f4fc ContentSummarizer</a></h1>\n<div class="card">\n  <div class="status-line">\n    <span><b>State:</b> idle</span>\n    <span><b>Last poll:</b> never (—)</span>\n    <span><b>Lifetime:</b> 0 ok / 0 failed</span>\n    \n  </div>\n  <p class="muted">summaries via openai · polling every 120s</p>\n  <div class="seg"><span class="muted">Transcription:</span><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="auto"><button class="active">Auto</button></form><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="openai"><button class="">OpenAI API</button></form><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="remote"><button class="">GPU PC</button></form><span class="muted">(resets to .env on restart)</span></div>\n  <div class="seg"><span class="muted">Auto-refresh:</span><button onclick="location.reload()">Refresh now</button><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="off"><button class="active">Off</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="15"><button class="">15s</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="30"><button class="">30s</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="60"><button class="">60s</button></form></div>\n  <p style="margin-bottom:0"><form class="inline" method="post" action="/drain" style="margin-left:0"><button>Drain now</button></form></p>\n</div>\n\n<h2>Add a video</h2>\n<div class="card">\n  <form method="post" action="/queue">\n    <input type="text" name="url" placeholder="https://www.youtube.com/watch?v=..." required>\n    <textarea name="prompt" rows="3" placeholder="Optional: tell the AI how to summarize this one — e.g. &quot;focus on the investing advice and list every ticker mentioned&quot;"></textarea>\n    <p class="muted field-hint">Leave the prompt empty for the normal summary.</p>\n    <button>Queue it</button>\n  </form>\n</div>\n\n<h2>Queue</h2>\n<div class="card"><p class="muted">Could not reach GitHub: &#x27;NoneType&#x27; object has no attribute &#x27;open_issues&#x27;</p></div>\n\n<h2>Summaries</h2>\n<div class="card">\n  <form method="get" action="/search">\n    <input type="text" name="q" placeholder="Search summaries...">\n    <button>Search</button>\n  </form>\n  <p class="muted">No summaries yet.</p>\n</div>\n</body></html>'

======================================================================
FAIL: test_page_is_static_until_auto_refresh_is_turned_on (tests.ref_test_app.WebRefreshTests.test_page_is_static_until_auto_refresh_is_turned_on)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\Aaron\llm-harness\wt\qtm-108c631\tests\ref_test_app.py", line 330, in test_page_is_static_until_auto_refresh_is_turned_on
    self.assertNotIn("location.reload", page)
AssertionError: 'location.reload' unexpectedly found in '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ContentSummarizer</title><style>\n:root { color-scheme: light dark; }\n* { box-sizing: border-box; }\nbody { font: 15px/1.55 system-ui, "Segoe UI", sans-serif; max-width: 840px;\n       margin: 0 auto; padding: 24px 16px; background: #f7f7f8; color: #1a1a1a; }\nh1 { font-size: 22px; margin: 0 0 4px; }\nh1 a { color: inherit; text-decoration: none; }\nh2 { font-size: 15px; text-transform: uppercase; letter-spacing: .04em;\n     color: #666; margin: 22px 0 8px; }\n.card { background: #fff; border: 1px solid #e3e3e6; border-radius: 10px;\n        padding: 14px 18px; margin: 10px 0; }\n.muted { color: #777; font-size: 13px; }\ninput[type=text], textarea { width: 100%; max-width: 520px; padding: 8px 10px;\n        border: 1px solid #ccc; border-radius: 8px; background: inherit; color: inherit; }\ntextarea { font: inherit; resize: vertical; min-height: 62px; margin-top: 8px; }\n.field-hint { margin: 6px 0 10px; }\nbutton { padding: 7px 14px; border: 0; border-radius: 8px; background: #2563eb;\n         color: #fff; cursor: pointer; font-size: 14px; }\nbutton:hover { background: #1d4ed8; }\nform.inline { display: inline; margin-left: 6px; }\nform.inline button { padding: 2px 10px; font-size: 12px; background: #64748b; }\n.badge { border-radius: 6px; padding: 1px 8px; font-size: 12px; margin-left: 6px; }\n.badge.fail { background: #dc2626; color: #fff; }\n.badge.on { background: #16a34a; color: #fff; }\n.badge.off { background: #6b7280; color: #fff; }\n.seg { display: inline-flex; gap: 6px; align-items: center; flex-wrap: wrap; }\n.seg form { display: inline; }\n.seg button { background: #64748b; padding: 4px 12px; font-size: 13px; }\n.seg button.active { background: #2563eb; }\nul { padding-left: 20px; margin: 6px 0; }\nli { margin: 7px 0; }\na { color: #2563eb; text-decoration: none; }\na:hover { text-decoration: underline; }\n.prose { background: #fff; border: 1px solid #e3e3e6; border-radius: 10px;\n         padding: 20px 26px; }\n.prose h1 { font-size: 20px; }\n.status-line { display: flex; gap: 18px; flex-wrap: wrap; }\n@media (prefers-color-scheme: dark) {\n  body { background: #121214; color: #e6e6e9; }\n  .card, .prose { background: #1c1c1f; border-color: #333338; }\n  h2 { color: #9a9aa3; }\n  .muted { color: #94949c; }\n  input[type=text], textarea { border-color: #44444a; }\n  a { color: #7aa2ff; }\n}\n</style></head><body><h1><a href="/">\U0001f4fc ContentSummarizer</a></h1>\n<div class="card">\n  <div class="status-line">\n    <span><b>State:</b> idle</span>\n    <span><b>Last poll:</b> never (—)</span>\n    <span><b>Lifetime:</b> 0 ok / 0 failed</span>\n    \n  </div>\n  <p class="muted">summaries via openai · polling every 120s</p>\n  <div class="seg"><span class="muted">Transcription:</span><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="auto"><button class="active">Auto</button></form><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="openai"><button class="">OpenAI API</button></form><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="remote"><button class="">GPU PC</button></form><span class="muted">(resets to .env on restart)</span></div>\n  <div class="seg"><span class="muted">Auto-refresh:</span><button onclick="location.reload()">Refresh now</button><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="off"><button class="active">Off</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="15"><button class="">15s</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="30"><button class="">30s</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="60"><button class="">60s</button></form></div>\n  <p style="margin-bottom:0"><form class="inline" method="post" action="/drain" style="margin-left:0"><button>Drain now</button></form></p>\n</div>\n\n<h2>Add a video</h2>\n<div class="card">\n  <form method="post" action="/queue">\n    <input type="text" name="url" placeholder="https://www.youtube.com/watch?v=..." required>\n    <textarea name="prompt" rows="3" placeholder="Optional: tell the AI how to summarize this one — e.g. &quot;focus on the investing advice and list every ticker mentioned&quot;"></textarea>\n    <p class="muted field-hint">Leave the prompt empty for the normal summary.</p>\n    <button>Queue it</button>\n  </form>\n</div>\n\n<h2>Queue</h2>\n<div class="card"><p class="muted">Could not reach GitHub: &#x27;NoneType&#x27; object has no attribute &#x27;open_issues&#x27;</p></div>\n\n<h2>Summaries</h2>\n<div class="card">\n  <form method="get" action="/search">\n    <input type="text" name="q" placeholder="Search summaries...">\n    <button>Search</button>\n  </form>\n  <p class="muted">No summaries yet.</p>\n</div>\n</body></html>'

======================================================================
FAIL: test_reloading_holds_while_someone_is_typing (tests.ref_test_app.WebRefreshTests.test_reloading_holds_while_someone_is_typing)
A page that reloaded under a half-typed URL would throw the URL away.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\Aaron\llm-harness\wt\qtm-108c631\tests\ref_test_app.py", line 361, in test_reloading_holds_while_someone_is_typing
    self.assertIn("paused while you type", page)
AssertionError: 'paused while you type' not found in '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ContentSummarizer</title><style>\n:root { color-scheme: light dark; }\n* { box-sizing: border-box; }\nbody { font: 15px/1.55 system-ui, "Segoe UI", sans-serif; max-width: 840px;\n       margin: 0 auto; padding: 24px 16px; background: #f7f7f8; color: #1a1a1a; }\nh1 { font-size: 22px; margin: 0 0 4px; }\nh1 a { color: inherit; text-decoration: none; }\nh2 { font-size: 15px; text-transform: uppercase; letter-spacing: .04em;\n     color: #666; margin: 22px 0 8px; }\n.card { background: #fff; border: 1px solid #e3e3e6; border-radius: 10px;\n        padding: 14px 18px; margin: 10px 0; }\n.muted { color: #777; font-size: 13px; }\ninput[type=text], textarea { width: 100%; max-width: 520px; padding: 8px 10px;\n        border: 1px solid #ccc; border-radius: 8px; background: inherit; color: inherit; }\ntextarea { font: inherit; resize: vertical; min-height: 62px; margin-top: 8px; }\n.field-hint { margin: 6px 0 10px; }\nbutton { padding: 7px 14px; border: 0; border-radius: 8px; background: #2563eb;\n         color: #fff; cursor: pointer; font-size: 14px; }\nbutton:hover { background: #1d4ed8; }\nform.inline { display: inline; margin-left: 6px; }\nform.inline button { padding: 2px 10px; font-size: 12px; background: #64748b; }\n.badge { border-radius: 6px; padding: 1px 8px; font-size: 12px; margin-left: 6px; }\n.badge.fail { background: #dc2626; color: #fff; }\n.badge.on { background: #16a34a; color: #fff; }\n.badge.off { background: #6b7280; color: #fff; }\n.seg { display: inline-flex; gap: 6px; align-items: center; flex-wrap: wrap; }\n.seg form { display: inline; }\n.seg button { background: #64748b; padding: 4px 12px; font-size: 13px; }\n.seg button.active { background: #2563eb; }\nul { padding-left: 20px; margin: 6px 0; }\nli { margin: 7px 0; }\na { color: #2563eb; text-decoration: none; }\na:hover { text-decoration: underline; }\n.prose { background: #fff; border: 1px solid #e3e3e6; border-radius: 10px;\n         padding: 20px 26px; }\n.prose h1 { font-size: 20px; }\n.status-line { display: flex; gap: 18px; flex-wrap: wrap; }\n@media (prefers-color-scheme: dark) {\n  body { background: #121214; color: #e6e6e9; }\n  .card, .prose { background: #1c1c1f; border-color: #333338; }\n  h2 { color: #9a9aa3; }\n  .muted { color: #94949c; }\n  input[type=text], textarea { border-color: #44444a; }\n  a { color: #7aa2ff; }\n}\n</style></head><body><h1><a href="/">\U0001f4fc ContentSummarizer</a></h1>\n<div class="card">\n  <div class="status-line">\n    <span><b>State:</b> idle</span>\n    <span><b>Last poll:</b> never (—)</span>\n    <span><b>Lifetime:</b> 0 ok / 0 failed</span>\n    \n  </div>\n  <p class="muted">summaries via openai · polling every 120s</p>\n  <div class="seg"><span class="muted">Transcription:</span><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="auto"><button class="active">Auto</button></form><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="openai"><button class="">OpenAI API</button></form><form method="post" action="/settings/transcribe"><input type="hidden" name="mode" value="remote"><button class="">GPU PC</button></form><span class="muted">(resets to .env on restart)</span></div>\n  <div class="seg"><span class="muted">Auto-refresh:</span><button onclick="location.reload()">Refresh now</button><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="off"><button class="active">Off</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="15"><button class="">15s</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="30"><button class="">30s</button></form><form method="post" action="/settings/refresh"><input type="hidden" name="interval" value="60"><button class="">60s</button></form></div>\n  <p style="margin-bottom:0"><form class="inline" method="post" action="/drain" style="margin-left:0"><button>Drain now</button></form></p>\n</div>\n\n<h2>Add a video</h2>\n<div class="card">\n  <form method="post" action="/queue">\n    <input type="text" name="url" placeholder="https://www.youtube.com/watch?v=..." required>\n    <textarea name="prompt" rows="3" placeholder="Optional: tell the AI how to summarize this one — e.g. &quot;focus on the investing advice and list every ticker mentioned&quot;"></textarea>\n    <p class="muted field-hint">Leave the prompt empty for the normal summary.</p>\n    <button>Queue it</button>\n  </form>\n</div>\n\n<h2>Queue</h2>\n<div class="card"><p class="muted">Could not reach GitHub: &#x27;NoneType&#x27; object has no attribute &#x27;open_issues&#x27;</p></div>\n\n<h2>Summaries</h2>\n<div class="card">\n  <form method="get" action="/search">\n    <input type="text" name="q" placeholder="Search summaries...">\n    <button>Search</button>\n  </form>\n  <p class="muted">No summaries yet.</p>\n</div>\n</body></html>'

----------------------------------------------------------------------
Ran 36 tests in 0.628s

FAILED (failures=4, errors=3)
```

# BUILDER SELF-REVIEW
```json
{
  "verdict": "GO",
  "blockers": [
    "FIXED before final run: _REFRESH_JS's onHold() treated every input with a non-empty value as user editing, but the Auto-refresh and Transcription .seg controls render <input type=\"hidden\" ... value=\"...\"> which always have values - the countdown would have held permanently and auto-refresh never fired. Fix: skip f.type === \"hidden\" in onHold(). Re-verified by full suite (41/41 green) and by hand-tracing the selector against the rendered HTML."
  ],
  "advisories": [
    "Pre-existing ResourceWarning (unclosed open() in dashboard.summary_page/home) now surfaces because the new tests exercise summary_page with a real file; not introduced by this change and fixing it would touch the summary page, which is out of scope.",
    "The JS hold-while-editing behavior cannot be unit-tested in this environment (no DOM, no httpx/TestClient); it is verified by code inspection and static render checks, not by executing the script.",
    "In a JS-less browser the <noscript> meta-refresh reloads even while a field has text (inherent to meta-refresh; the task accepts this as the fallback)."
  ],
  "summary": "Per-browser auto-refresh (Refresh now + Off/15s/30s/60s posting to /settings/refresh exactly like /settings/transcribe, persisted in the dash_refresh cookie) with server-side validation on both the write and the read path, a <noscript> meta-refresh fallback on the home page only, a JS countdown that holds and says so while any visible input is focused or non-empty, and a 30 s display-only cache (pipeline.gpu_node_online_cached) for the GPU badge while transcribe() routing still probes live. 11 new tests in tests/test_app.py (10 errors + 1 failure red before the build, all green after); full suite 41/41 OK. One real defect (hidden inputs breaking the hold logic) found in self-review and fixed."
}
```

# REFERENCE DIFF (the merged change, for comparison)
```diff
diff --git a/dashboard.py b/dashboard.py
index 6c9cea7..ed64ce8 100644
--- a/dashboard.py
+++ b/dashboard.py
@@ -24,7 +24,7 @@ from logging.handlers import RotatingFileHandler
 
 import markdown as md
 from dotenv import load_dotenv
-from fastapi import FastAPI, Form
+from fastapi import Cookie, FastAPI, Form
 from fastapi.responses import HTMLResponse, RedirectResponse
 
 import drain
@@ -58,9 +58,42 @@ NO_WORKER = os.environ.get("DASHBOARD_NO_WORKER", "").strip().lower() in {
 # `git pull` brings them to disk. (No-op when there's nothing to fetch.)
 SUMMARY_PULL_SECONDS = int(os.environ.get("SUMMARY_PULL_SECONDS") or 60)
 
+# Auto-refresh: how often the home page may reload itself, in seconds (0 = never).
+# Per-device rather than a server setting, because the phone left open on the counter
+# and the PC someone is typing into want different answers.
+REFRESH_CHOICES = (0, 15, 30, 60)
+REFRESH_COOKIE = "cs_refresh"
+REFRESH_COOKIE_MAX_AGE = 400 * 24 * 3600  # remember the choice for well over a year
+
 worker: Worker | None = None
 
 
+# The GPU badge is decoration, but probing a switched-off GPU PC costs a real timeout
+# (~3s here, measured), and every home() render paid it. Auto-refresh would charge that
+# every few seconds, making the page feel broken. Cached for display only â€” the routing
+# decision in pipeline.transcribe() still probes live, because sending a job to a node
+# that died 20 seconds ago is a different kind of wrong.
+GPU_STATUS_TTL = 30
+_gpu_status = {"checked_at": 0.0, "online": False}
+
+
+def _gpu_online_cached():
+    now = time.time()
+    if now - _gpu_status["checked_at"] > GPU_STATUS_TTL:
+        _gpu_status["online"] = pipeline.gpu_node_online()
+        _gpu_status["checked_at"] = now
+    return _gpu_status["online"]
+
+
+def _refresh_seconds(raw):
+    """The refresh interval a request asked for, or 0 for off. Never trusts the value."""
+    try:
+        value = int(str(raw).strip())
+    except (TypeError, ValueError):
+        return 0
+    return value if value in REFRESH_CHOICES else 0
+
+
 def attach_worker(existing: Worker, summary_dir=None):
     """Host this UI on someone else's Worker (the desktop app embeds it).
 
@@ -140,6 +173,9 @@ form.inline button { padding: 2px 10px; font-size: 12px; background: #64748b; }
 .seg form { display: inline; }
 .seg button { background: #64748b; padding: 4px 12px; font-size: 13px; }
 .seg button.active { background: #2563eb; }
+.btn { background: #2563eb; color: #fff; padding: 4px 12px; border-radius: 8px;
+       font-size: 13px; text-decoration: none; display: inline-block; }
+.btn:hover { background: #1d4ed8; text-decoration: none; }
 ul { padding-left: 20px; margin: 6px 0; }
 li { margin: 7px 0; }
 a { color: #2563eb; text-decoration: none; }
@@ -159,20 +195,85 @@ a:hover { text-decoration: underline; }
 """
 
 
-def _page(title, body):
+# Reloading the page under someone mid-sentence would throw away a half-typed URL or
+# prompt, so the timer holds while a field is focused or has anything in it, and says so.
+# The countdown is not decoration: without it a page that reloads itself looks like a bug.
+_REFRESH_JS = """
+(function () {
+  var every = %d, left = every;
+  var out = document.getElementById("refresh-countdown");
+  function busy() {
+    var el = document.activeElement;
+    if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) return true;
+    var fields = document.querySelectorAll("input[type=text], textarea");
+    for (var i = 0; i < fields.length; i++) {
+      if (fields[i].value.trim()) return true;
+    }
+    return false;
+  }
+  setInterval(function () {
+    if (busy()) {
+      left = every;
+      if (out) out.textContent = "paused while you type";
+      return;
+    }
+    left -= 1;
+    if (left <= 0) { location.reload(); return; }
+    if (out) out.textContent = "refreshing in " + left + "s";
+  }, 1000);
+})();
+"""
+
+
+def _page(title, body, refresh=0):
+    # <noscript> carries the plain-HTML fallback: a browser without JS still keeps up,
+    # it just cannot pause for typing the way the script does.
+    head_extra = (
+        f'<noscript><meta http-equiv="refresh" content="{int(refresh)}"></noscript>'
+        if refresh
+        else ""
+    )
+    script = f"<script>{_REFRESH_JS % int(refresh)}</script>" if refresh else ""
     return (
         "<!doctype html><html><head>"
         '<meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width, initial-scale=1">'
         f"<title>{html.escape(title)}</title>"
+        f"{head_extra}"
         f"<style>{_CSS}</style>"
         "</head><body>"
         '<h1><a href="/">ðŸ“¼ ContentSummarizer</a></h1>'
         f"{body}"
+        f"{script}"
         "</body></html>"
     )
 
 
+def _refresh_controls(refresh):
+    """The Refresh-now button and the auto-refresh segmented control."""
+    seg = []
+    for value in REFRESH_CHOICES:
+        label = "Off" if value == 0 else f"{value}s"
+        active = " active" if value == refresh else ""
+        seg.append(
+            '<form method="post" action="/settings/refresh">'
+            f'<input type="hidden" name="seconds" value="{value}">'
+            f'<button class="{active.strip()}">{label}</button></form>'
+        )
+    countdown = (
+        f' <span class="muted" id="refresh-countdown">refreshing in {refresh}s</span>'
+        if refresh
+        else ""
+    )
+    return (
+        '<div class="seg" style="margin-top:10px">'
+        '<a class="btn" href="/">â†» Refresh now</a>'
+        '<span class="muted">Auto-refresh:</span>'
+        f'{"".join(seg)}{countdown}'
+        "</div>"
+    )
+
+
 def _ago(ts):
     if not ts:
         return "never"
@@ -203,7 +304,8 @@ def _summary_files():
 
 
 @app.get("/", response_class=HTMLResponse)
-def home():
+def home(cs_refresh: str = Cookie(default="0")):
+    refresh = _refresh_seconds(cs_refresh)
     s = worker.snapshot()
 
     queue_err = None
@@ -260,7 +362,7 @@ def home():
 
     gpu_html = ""
     if pipeline._gpu_node_url():
-        online = pipeline.gpu_node_online()
+        online = _gpu_online_cached()
         gpu_badge = (
             '<span class="badge on">online</span>'
             if online
@@ -296,6 +398,9 @@ def home():
             f'<p class="muted">summaries via {html.escape(provider)} Â· '
             f"polling every {worker.poll_seconds}s</p>"
         )
+    # Both modes get it: viewer mode is exactly when the page cannot know that the
+    # external runner has finished something.
+    controls_html += _refresh_controls(refresh)
 
     body = f"""
 <div class="card">
@@ -332,7 +437,7 @@ def home():
   {summaries_html}
 </div>
 """
-    return _page("ContentSummarizer", body)
+    return _page("ContentSummarizer", body, refresh=refresh)
 
 
 @app.get("/s/{stem}", response_class=HTMLResponse)
@@ -437,6 +542,22 @@ def set_transcribe_mode(mode: str = Form(...)):
     return RedirectResponse("/", status_code=303)
 
 
+@app.post("/settings/refresh")
+def set_refresh(seconds: str = Form("0")):
+    """Remember this browser's auto-refresh choice. Per-device, so the phone on the
+    kitchen counter and the PC someone is typing at can differ."""
+    value = _refresh_seconds(seconds)
+    response = RedirectResponse("/", status_code=303)
+    response.set_cookie(
+        REFRESH_COOKIE,
+        str(value),
+        max_age=REFRESH_COOKIE_MAX_AGE,
+        samesite="lax",
+        httponly=False,
+    )
+    return response
+
+
 @app.post("/retry/{number}")
 def retry(number: int):
     try:
diff --git a/desktop_gui.py b/desktop_gui.py
index 1f2042f..28d7538 100644
--- a/desktop_gui.py
+++ b/desktop_gui.py
@@ -1129,6 +1129,8 @@ def _smoke_test_lan_server():
             time.sleep(0.25)
     if 'name="prompt"' not in body:
         raise RuntimeError("the web page is missing the AI prompt box")
+    if "Auto-refresh:" not in body:
+        raise RuntimeError("the web page is missing the auto-refresh control")
 
 
 def main():
diff --git a/tests/test_app.py b/tests/test_app.py
index dd3f7b9..36875da 100644
--- a/tests/test_app.py
+++ b/tests/test_app.py
@@ -286,5 +286,101 @@ class SafetyTests(unittest.TestCase):
         self.assertEqual(result.stdout.strip(), "2026.test")
 
 
+class WebRefreshTests(unittest.TestCase):
+    """The LAN page can keep itself up to date, per browser.
+
+    Everything the worker does happens elsewhere, so the page a phone is left open on
+    goes stale silently: the summary lands, the queue empties, and the screen still
+    shows the state from whenever it was loaded.
+    """
+
+    @classmethod
+    def setUpClass(cls):
+        import dashboard
+        from fastapi.testclient import TestClient
+
+        class _StubWorker:
+            poll_seconds = 120
+            gh = None
+
+            def snapshot(self):
+                return {
+                    "state": "idle",
+                    "last_poll": None,
+                    "last_result": "",
+                    "ok_total": 0,
+                    "failed_total": 0,
+                }
+
+        cls.dashboard = dashboard
+        dashboard.attach_worker(_StubWorker(), summary_dir=tempfile.mkdtemp())
+        # The stub has no GitHub client; home() already renders the queue error path.
+        cls.client = TestClient(dashboard.app)
+
+    def test_refresh_choice_is_only_ever_one_of_the_offered_intervals(self):
+        for good in self.dashboard.REFRESH_CHOICES:
+            self.assertEqual(self.dashboard._refresh_seconds(str(good)), good)
+        for bad in ("", "  ", "7", "-30", "abc", None, "99999999", "30; drop table"):
+            self.assertEqual(self.dashboard._refresh_seconds(bad), 0)
+
+    def test_page_is_static_until_auto_refresh_is_turned_on(self):
+        page = self.client.get("/").text
+        self.assertIn("Refresh now", page)  # the manual option is always there
+        self.assertIn("Auto-refresh:", page)
+        self.assertNotIn("location.reload", page)
+        self.assertNotIn("http-equiv", page)
+
+    def test_choosing_an_interval_makes_the_page_reload_itself(self):
+        self.client.post("/settings/refresh", data={"seconds": "30"})
+        page = self.client.get("/").text
+        self.assertIn("location.reload", page)
+        self.assertIn("refreshing in 30s", page)
+        # A browser without JS still keeps up, via plain HTML.
+        self.assertIn('<meta http-equiv="refresh" content="30">', page)
+
+    def test_the_choice_survives_a_reload_and_can_be_turned_back_off(self):
+        self.client.post("/settings/refresh", data={"seconds": "60"})
+        self.assertEqual(self.client.cookies.get(self.dashboard.REFRESH_COOKIE), "60")
+        self.assertIn("refreshing in 60s", self.client.get("/").text)
+
+        self.client.post("/settings/refresh", data={"seconds": "0"})
+        page = self.client.get("/").text
+        self.assertNotIn("location.reload", page)
+        self.assertNotIn("http-equiv", page)
+
+    def test_a_tampered_cookie_cannot_turn_into_a_reload_loop(self):
+        self.client.cookies.set(self.dashboard.REFRESH_COOKIE, "1")
+        page = self.client.get("/").text
+        self.assertNotIn("location.reload", page)
+        self.client.cookies.delete(self.dashboard.REFRESH_COOKIE)
+
+    def test_reloading_holds_while_someone_is_typing(self):
+        """A page that reloaded under a half-typed URL would throw the URL away."""
+        self.client.post("/settings/refresh", data={"seconds": "15"})
+        page = self.client.get("/").text
+        self.assertIn("paused while you type", page)
+        self.assertIn("activeElement", page)
+        self.client.post("/settings/refresh", data={"seconds": "0"})
+
+    def test_the_gpu_badge_is_not_probed_on_every_reload(self):
+        """A switched-off GPU PC costs a multi-second timeout. Paying it once per page
+        load was tolerable; paying it every 15 seconds under auto-refresh is not."""
+        self.dashboard._gpu_status["checked_at"] = 0.0
+        with mock.patch(
+            "dashboard.pipeline.gpu_node_online", return_value=True
+        ) as probe:
+            for _ in range(5):
+                self.dashboard._gpu_online_cached()
+        self.assertEqual(probe.call_count, 1)
+
+    def test_other_pages_do_not_reload_themselves(self):
+        """Auto-refresh belongs to the dashboard; a summary being read must sit still."""
+        self.client.post("/settings/refresh", data={"seconds": "30"})
+        for path in ("/search?q=test", "/s/nope"):
+            page = self.client.get(path).text
+            self.assertNotIn("location.reload", page, path)
+        self.client.post("/settings/refresh", data={"seconds": "0"})
+
+
 if __name__ == "__main__":
     unittest.main()
```
