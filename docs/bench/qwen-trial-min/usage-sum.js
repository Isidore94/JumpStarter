// bun usage-sum.js <usage.jsonl>...: per-file request count, errors, exact OpenRouter cost, tokens, avg/max ms, provider.
const fs = require("fs");
let total = 0;
for (const p of process.argv.slice(2)) {
  if (!fs.existsSync(p)) { console.log(p, "missing"); continue; }
  const L = fs.readFileSync(p, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l));
  let cost = 0, ok = 0, inp = 0, out = 0, think = 0, ms = 0, max = 0;
  const prov = new Set();
  for (const r of L) {
    const u = r.usage || {};
    cost += u.cost || 0; if (r.status === 200) ok++;
    inp += u.input_tokens || 0; out += u.output_tokens || 0; think += u.output_tokens_details?.thinking_tokens || 0;
    ms += r.ms || 0; max = Math.max(max, r.ms || 0); if (r.provider) prov.add(r.provider);
  }
  total += cost;
  console.log(`${p}: req ${L.length} ok ${ok} cost $${cost.toFixed(4)} in ${inp} out ${out} think ${think} avg ${Math.round(ms / (L.length || 1))}ms max ${max}ms ${[...prov].join(",")}`);
}
console.log(`total $${total.toFixed(4)}`);
