// Local proxy in front of OpenRouter for the Qwen minimal-brief trial.
// - pins the provider to fp4 quantisation, fastest first (like trial-10 :nitro), no fallback to other quantisations
// - sets reasoning effort low (REASONING env, empty = leave alone)
// - logs token usage per request to USAGE_LOG (jsonl); auth headers pass through untouched and are never logged
// usage: PORT=<n> USAGE_LOG=<file> [REASONING=low] bun proxy.js
const UP = "https://openrouter.ai/api";
const port = Number(process.env.PORT || 0);
const logFile = process.env.USAGE_LOG;
const provider = { quantizations: ["fp4"], sort: "throughput", allow_fallbacks: false }; // price-sorted pinned Darkbloom: ~75 tok/s, 429s, both first builds hit the 45 min timeout
const dec = new TextDecoder();
const log = (o) => { if (logFile) require("fs").appendFileSync(logFile, JSON.stringify(o) + "\n"); };

const srv = Bun.serve({
  port, idleTimeout: 255,
  async fetch(req) {
    const url = new URL(req.url);
    const headers = new Headers(req.headers);
    headers.delete("host"); headers.delete("content-length"); headers.delete("accept-encoding");
    let body = req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer();
    let model = null, stream = false;
    if (body && url.pathname.endsWith("/v1/messages")) {
      try {
        const j = JSON.parse(dec.decode(body));
        j.provider = provider;
        if (process.env.REASONING) j.reasoning = { effort: process.env.REASONING };
        model = j.model; stream = !!j.stream;
        body = JSON.stringify(j);
      } catch (e) { /* not JSON: forward as is */ }
    }
    const t0 = Date.now();
    const r = await fetch(UP + url.pathname + url.search, { method: req.method, headers, body, redirect: "manual" });
    const rh = new Headers(r.headers); rh.delete("content-encoding"); rh.delete("content-length");
    const meta = { t: new Date(t0).toISOString(), path: url.pathname, model, status: r.status,
      provider: r.headers.get("x-openrouter-provider") || null };
    if (!r.body || !url.pathname.endsWith("/v1/messages")) {
      if (url.pathname.endsWith("/v1/messages")) log({ ...meta, ms: Date.now() - t0 });
      return new Response(r.body, { status: r.status, headers: rh });
    }
    if (r.status !== 200) {
      const txt = await r.text();
      log({ ...meta, ms: Date.now() - t0, error: txt.slice(0, 400) });
      return new Response(txt, { status: r.status, headers: rh });
    }
    const [a, b] = r.body.tee();
    (async () => {
      let text = "";
      for await (const chunk of b) text += dec.decode(chunk, { stream: true });
      const usage = {};
      if (stream) {
        for (const line of text.split("\n")) {
          if (!line.startsWith("data:")) continue;
          try {
            const ev = JSON.parse(line.slice(5));
            if (ev.type === "message_start" && ev.message?.usage) Object.assign(usage, ev.message.usage);
            if (ev.type === "message_delta" && ev.usage) Object.assign(usage, ev.usage);
            if (ev.type === "message_start" && ev.message) { meta.served_model = ev.message.model; meta.provider = ev.message.provider || meta.provider; }
          } catch (e) {}
        }
      } else {
        try { const j = JSON.parse(text); Object.assign(usage, j.usage || {}); meta.served_model = j.model; } catch (e) {}
      }
      log({ ...meta, ms: Date.now() - t0, usage });
    })();
    return new Response(a, { status: r.status, headers: rh });
  },
});
console.log("proxy listening on " + srv.port);
