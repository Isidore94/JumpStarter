"""Per-run OpenRouter cost for qwen-trial-10, priced from tokens.

Concurrent runs inflate each run's `llm key` delta (summary.json cost_usd), so this prices the
tokens the Claude Code transcript reports (build + self-review + seeded self-review) at the
OpenRouter list price for qwen/qwen3.8-27b and cross-checks the sum against the account delta.
Usage: python cost.py [used_now baseline]
"""
import glob
import json
import os
import sys

P_IN, P_OUT, P_CACHE = 0.20e-6, 2.50e-6, 0.09e-6  # openrouter.ai/api/v1/models, 2026-10-27
RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs")


def result_usage(path):
    """Tokens from the last `result` line of a Claude Code stream-json transcript or json output."""
    if not os.path.exists(path):
        return None
    res = None
    for line in open(path, encoding="utf-8", errors="replace"):
        if '"type":"result"' not in line and '"type": "result"' not in line:
            continue
        try:
            j = json.loads(line)
        except ValueError:
            continue
        if j.get("type") == "result":
            res = j
    if res is None:
        try:
            res = json.load(open(path, encoding="utf-8", errors="replace"))
        except ValueError:
            return None
    mu = res.get("modelUsage") or {}
    tot = {"in": 0, "out": 0, "cache": 0}
    for u in mu.values():
        tot["in"] += u.get("inputTokens", 0)
        tot["out"] += u.get("outputTokens", 0)
        tot["cache"] += u.get("cacheReadInputTokens", 0)
    return tot if any(tot.values()) else None


def session_usage(run):
    """Fallback for truncated transcripts: sum assistant usage in the session copy, one per message id."""
    seen = {}
    for f in glob.glob(os.path.join(run, "home", "projects", "*", "*.jsonl")):
        for line in open(f, encoding="utf-8", errors="replace"):
            try:
                j = json.loads(line)
            except ValueError:
                continue
            m = j.get("message") or {}
            u = m.get("usage")
            if j.get("type") == "assistant" and u:
                seen[m.get("id") or j.get("uuid")] = u
    if not seen:
        return None
    return {
        "in": sum(u.get("input_tokens", 0) for u in seen.values()),
        "out": sum(u.get("output_tokens", 0) for u in seen.values()),
        "cache": sum(u.get("cache_read_input_tokens", 0) for u in seen.values()),
    }


def price(t):
    return t["in"] * P_IN + t["out"] * P_OUT + t["cache"] * P_CACHE


def main():
    rows, total = [], 0.0
    for d in sorted(glob.glob(os.path.join(RUNS, "*", ""))):
        run = os.path.basename(d.rstrip("/\\"))
        parts = {}
        build = result_usage(os.path.join(d, "transcript.jsonl"))
        src = "transcript"
        if build is None:
            build, src = session_usage(d), "session"
        if build:
            parts["build"] = build
        for name, f in (("self-review", "review-raw.json"), ("seeded self-review", "review-seeded-raw.json")):
            u = result_usage(os.path.join(d, f))
            if u:
                parts[name] = u
        cost = sum(price(t) for t in parts.values())
        total += cost
        b = parts.get("build", {"in": 0, "out": 0, "cache": 0})
        rows.append((run, src, b["in"], b["out"], b["cache"], price(b), cost))
    scale = 1.0
    if len(sys.argv) == 3:
        delta = float(sys.argv[1]) - float(sys.argv[2])
        scale = delta / total  # :nitro routes below list price; apportion the real delta by priced share
    print(f"{'run':22} {'src':10} {'in':>8} {'out':>8} {'cache':>9} {'build$':>7} {'all$':>7} {'scaled$':>8}")
    for r in rows:
        print(f"{r[0]:22} {r[1]:10} {r[2]:8d} {r[3]:8d} {r[4]:9d} {r[5]:7.3f} {r[6]:7.3f} {r[6] * scale:8.3f}")
    print(f"priced total: ${total:.3f}")
    if scale != 1.0:
        print(f"account delta: ${delta:.3f}  scale {scale:.3f} (list price / actual; nitro provider is cheaper)")


if __name__ == "__main__":
    main()
