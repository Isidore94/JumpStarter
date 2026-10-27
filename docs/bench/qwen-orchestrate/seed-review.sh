#!/usr/bin/env bash
# Seeded self-review after the fact: apply a seed patch to a finished Qwen worktree, run only the review pass
# (step 10 of run-orchestrate.sh), save review-seeded.txt + diff-seeded.patch, then take the seed back out.
# usage: seed-review.sh <outdir> <seed.patch>   (outdir must hold summary.json from run-orchestrate.sh)
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(cd "$1" && pwd) || exit 1
seed=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
MODEL=$(sed -n 's/^MODEL=//p' "$HERE/run-orchestrate.sh")
F_S=$(cygpath -m "$OUT/summary.json") bun -e 'const s=JSON.parse(require("fs").readFileSync(process.env.F_S,"utf8"));console.log(s.sha7,s.repo)' > "$OUT/.seed-env" || exit 1
read -r sha7 repo < "$OUT/.seed-env"; rm -f "$OUT/.seed-env"
wt=$HOME/llm-harness/wt/qo-$sha7
case "$repo" in *EveTradingbot*) PY=C:/Users/Aaron/EveTradingbot/.venv/Scripts/python.exe ;; *) PY=C:/Users/Aaron/TraderTaxHelper/.venv/Scripts/python.exe ;; esac
EXCL=(. ':!.qo' ':!.claude' ':!CLAUDE.md')
git -C "$wt" apply "$seed" || { echo "seed did not apply" >&2; exit 1; }
git -C "$wt" add -A -N -- "${EXCL[@]}"
git -C "$wt" diff -- "${EXCL[@]}" > "$OUT/diff-seeded.patch"
head -c 60000 "$OUT/diff-seeded.patch" > "$wt/.qo/diff-for-review.patch"
export CLAUDE_CONFIG_DIR="$OUT/home" ANTHROPIC_BASE_URL=https://openrouter.ai/api
ANTHROPIC_AUTH_TOKEN=$(tr -d '\r\n ' < "$HOME/llm-harness/openrouter.key")
export ANTHROPIC_AUTH_TOKEN ANTHROPIC_MODEL=$MODEL ANTHROPIC_DEFAULT_HAIKU_MODEL=$MODEL \
  ANTHROPIC_DEFAULT_SONNET_MODEL=$MODEL ANTHROPIC_DEFAULT_OPUS_MODEL=$MODEL \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_TELEMETRY=1
unset ANTHROPIC_API_KEY
cd "$wt" || exit 1
timeout 900 claude -p "$(cat "$OUT/review-prompt.md")" --model "$MODEL" --allowedTools "Read,Bash,Glob,Grep" \
  --permission-mode acceptEdits --output-format json --max-turns 25 > "$OUT/review-seeded-raw.json" 2> "$OUT/review-seeded-stderr.txt"
rc=$?
F_IN=$(cygpath -m "$OUT/review-seeded-raw.json") F_OUT=$(cygpath -m "$OUT/review-seeded.txt") bun -e '
const fs=require("fs"),e=process.env;let raw="";try{raw=fs.readFileSync(e.F_IN,"utf8")}catch(x){}
let out=raw;try{const j=JSON.parse(raw);if(typeof j.result==="string")out=j.result}catch(x){}
fs.writeFileSync(e.F_OUT,out)'
git -C "$wt" apply -R "$seed" && head -c 60000 "$OUT/diff.patch" > "$wt/.qo/diff-for-review.patch"
v=$(grep -o '"verdict":"[A-Z-]*"' "$OUT/review-seeded.txt" | head -1)
echo "$sha7 seeded-review rc=$rc $v"
