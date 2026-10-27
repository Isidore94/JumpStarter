#!/usr/bin/env bash
# Qwen orchestration bench runner: one brief through one orchestrator run, then checks, a leak audit, an optional
# seed patch and a separate self-review. Spec: docs/bench/qwen-orchestrate/PACKET-runner.md.
# usage: run-orchestrate.sh <repo> <base> <ref> <brief.md> <outdir> [seed.patch]
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
MODEL=qwen/qwen3.8-27b:floor
if [ $# -lt 5 ]; then echo "usage: $0 <repo> <base> <ref> <brief.md> <outdir> [seed.patch]" >&2; exit 2; fi
repo=$1; base=$2; ref=$3
[ -f "$4" ] || { echo "setup: no brief at $4" >&2; exit 1; }
brief=$(cd "$(dirname "$4")" && pwd)/$(basename "$4")
mkdir -p "$5" || exit 1
OUT=$(cd "$5" && pwd) || exit 1
seed=""
if [ $# -ge 6 ]; then
  [ -f "$6" ] || { echo "setup: no seed at $6" >&2; exit 1; }
  seed=$(cd "$(dirname "$6")" && pwd)/$(basename "$6")
fi
EXCL=(. ':!.qo' ':!.claude' ':!CLAUDE.md')

# render <template> <out> <placeholder> <value>: literal replace (split/join, so a $ in the value is safe).
render() {
  F_T=$(cygpath -m "$1") F_O=$(cygpath -m "$2") F_K="$3" F_V="$4" bun -e 'const fs=require("fs"),e=process.env;fs.writeFileSync(e.F_O,fs.readFileSync(e.F_T,"utf8").split(e.F_K).join(e.F_V))'
}

# 1. Worktree from the base tree, no history, with a baseline commit.
sha=$(git -C "$repo" rev-parse "$ref") || { echo "setup: ref $ref not found in $repo" >&2; exit 1; }
sha7=${sha:0:7}
wt=$HOME/llm-harness/wt/qo-$sha7
rm -rf "$wt" && mkdir -p "$wt" || exit 1
git -C "$repo" archive "$base" | tar -x -C "$wt" || { echo "setup: archive of $base failed" >&2; exit 1; }
git -C "$wt" init -q && git -C "$wt" add -A && git -C "$wt" -c user.name=bench -c user.email=bench@local commit -qm baseline \
  || { echo "setup: baseline commit failed" >&2; exit 1; }
rm -rf "$OUT/home" && rm -f "$OUT/summary.json" && mkdir -p "$OUT/home" || exit 1

# 2. Python for the repo under test.
case "$repo" in
  *EveTradingbot*) PY=C:/Users/Aaron/EveTradingbot/.venv/Scripts/python.exe ;;
  *) PY=C:/Users/Aaron/TraderTaxHelper/.venv/Scripts/python.exe ;;
esac
[ -x "$PY" ] || { echo "setup: no python at $PY" >&2; exit 1; }

# 3. Role files, and CLAUDE.md = the orchestration rules followed by the repo's own CLAUDE.md.
mkdir -p "$wt/.claude/agents" && cp C:/Users/Aaron/JumpStarter/templates/.claude/agents/*.md "$wt/.claude/agents/" \
  || { echo "setup: role files not copied" >&2; exit 1; }
render "$HERE/prompts/orchestrator-CLAUDE.md" "$OUT/orchestrator-CLAUDE.md" "{{PY}}" "$PY" || exit 1
{ cat "$OUT/orchestrator-CLAUDE.md"; if [ -f "$wt/CLAUDE.md" ]; then echo; cat "$wt/CLAUDE.md"; fi; } > "$OUT/CLAUDE.new" \
  && mv "$OUT/CLAUDE.new" "$wt/CLAUDE.md" || { echo "setup: CLAUDE.md not written" >&2; exit 1; }
mkdir -p "$wt/.qo" || exit 1

# 4. Main prompt.
render "$HERE/prompts/main-prompt.md" "$OUT/prompt.md" "{{BRIEF}}" "$(cat "$brief")" || exit 1

# 5. Orchestrator run, through OpenRouter. The key is read into the environment and never printed.
key="$HOME/llm-harness/openrouter.key"
[ -f "$key" ] || { echo "setup: no OpenRouter key file" >&2; exit 1; }
export CLAUDE_CONFIG_DIR="$OUT/home" ANTHROPIC_BASE_URL=https://openrouter.ai/api
ANTHROPIC_AUTH_TOKEN=$(tr -d '\r\n ' < "$key")
export ANTHROPIC_AUTH_TOKEN ANTHROPIC_MODEL=$MODEL ANTHROPIC_DEFAULT_HAIKU_MODEL=$MODEL \
  ANTHROPIC_DEFAULT_SONNET_MODEL=$MODEL ANTHROPIC_DEFAULT_OPUS_MODEL=$MODEL \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_TELEMETRY=1
unset ANTHROPIC_API_KEY
llm key > "$OUT/key-before.txt" 2>&1
cd "$wt" || exit 1
t0=$(date +%s)
timeout 2700 claude -p "$(cat "$OUT/prompt.md")" --model "$MODEL" --allowedTools "Read,Edit,Write,Bash,Glob,Grep,Agent" \
  --permission-mode acceptEdits --output-format stream-json --verbose --max-turns 80 \
  > "$OUT/transcript.jsonl" 2> "$OUT/stderr.txt"
exit_code=$?
elapsed_s=$(( $(date +%s) - t0 ))
llm key > "$OUT/key-after.txt" 2>&1

# 6. Diff of the orchestrator's work, and a copy of its .qo/ stages.
git -C "$wt" add -A -N -- "${EXCL[@]}"
git -C "$wt" diff -- "${EXCL[@]}" > "$OUT/diff.patch"
rm -rf "$OUT/qo" && cp -r "$wt/.qo" "$OUT/qo"
head -c 60000 "$OUT/diff.patch" > "$wt/.qo/diff-for-review.patch"

# 7. Own tests and lint; then the reference tests (the ref commit's test files, under names Qwen cannot clash with).
cd "$wt" || exit 1
"$PY" -m pytest -q > "$OUT/own-tests.txt" 2>&1; own_rc=$?
"$PY" -m ruff check . > "$OUT/ruff.txt" 2>&1; ruff_rc=$?
refs=(); mkdir -p "$wt/tests"
while IFS= read -r p; do
  [ -n "$p" ] || continue
  n="tests/ref_$(basename "$p")"
  git -C "$repo" show "$ref:$p" > "$wt/$n" && refs+=("$n")
done < <(git -C "$repo" diff --name-only "$base" "$ref" -- tests)
if [ ${#refs[@]} -gt 0 ]; then
  "$PY" -m pytest -q "${refs[@]}" > "$OUT/ref-tests.txt" 2>&1; ref_rc=$?
  for n in "${refs[@]}"; do rm -f "$wt/$n"; done
else
  echo "no reference test files in $base..$ref" > "$OUT/ref-tests.txt"; ref_rc=none
fi

# 8. Leak audit: the orchestrator should never have read git history or climbed out of the checkout.
if [ -f "$OUT/transcript.jsonl" ]; then
  grep -c -E 'git (log|show|reflog)|\.\./\.\.' "$OUT/transcript.jsonl" > "$OUT/leak.txt"
else
  echo missing > "$OUT/leak.txt"
fi
leak_count=$(cat "$OUT/leak.txt")

# 9. Seed: apply the seed patch if one was given, then re-capture the diff the reviewer sees.
rm -f "$OUT/diff-seeded.patch"
seed_applied=null
if [ -n "$seed" ]; then
  if git -C "$wt" apply "$seed"; then seed_applied=true; else seed_applied=false; fi
  git -C "$wt" add -A -N -- "${EXCL[@]}"
  git -C "$wt" diff -- "${EXCL[@]}" > "$OUT/diff-seeded.patch"
  head -c 60000 "$OUT/diff-seeded.patch" > "$wt/.qo/diff-for-review.patch"
fi

# 10. Separate self-review pass, same environment, verdict JSON in review.txt.
render "$HERE/prompts/self-review.md" "$OUT/review-prompt.md" "{{TASK}}" "$(cat "$brief")" \
  && render "$OUT/review-prompt.md" "$OUT/review-prompt.md" "{{PY}}" "$PY" || echo "review prompt render failed" > "$OUT/review-stderr.txt"
cd "$wt" || exit 1
timeout 900 claude -p "$(cat "$OUT/review-prompt.md")" --model "$MODEL" --allowedTools "Read,Bash,Glob,Grep" \
  --permission-mode acceptEdits --output-format json --max-turns 25 \
  > "$OUT/review-raw.json" 2> "$OUT/review-stderr.txt"
F_IN=$(cygpath -m "$OUT/review-raw.json") F_OUT=$(cygpath -m "$OUT/review.txt") bun -e '
const fs=require("fs"),e=process.env;let raw="";try{raw=fs.readFileSync(e.F_IN,"utf8")}catch(x){}
let out=raw;try{const j=JSON.parse(raw);if(typeof j.result==="string")out=j.result}catch(x){}
fs.writeFileSync(e.F_OUT,out)'

# 11. Summary and the one-line report.
OUTW=$(cygpath -m "$OUT") SHA7=$sha7 REPO=$repo BASE=$base REF=$ref SEED=$seed SEED_APPLIED=$seed_applied \
  EXIT=$exit_code ELAPSED=$elapsed_s OWN=$own_rc RUFF=$ruff_rc REF_RC=$ref_rc LEAK=$leak_count \
  bun -e '
const fs=require("fs"),e=process.env,o=e.OUTW;
const rd=(f)=>{try{return fs.readFileSync(f,"utf8")}catch(x){return ""}};
let verdict="unparsed";
const rv=rd(o+"/review.txt"),a=rv.indexOf("{"),b=rv.lastIndexOf("}");
if(a>=0&&b>a){try{const v=JSON.parse(rv.slice(a,b+1)).verdict;if(typeof v==="string")verdict=v}catch(x){}}
let turns=0;for(const line of rd(o+"/transcript.jsonl").split("\n")){try{if(JSON.parse(line).type==="assistant")turns++}catch(x){}}
const n=(v)=>/^\d+$/.test(v)?Number(v):null;
const s={sha7:e.SHA7,repo:e.REPO,base:e.BASE,ref:e.REF,seed:e.SEED||null,
  seed_applied:e.SEED_APPLIED==="null"?null:e.SEED_APPLIED==="true",
  exit_code:n(e.EXIT),elapsed_s:n(e.ELAPSED),turns,own_tests_rc:n(e.OWN),ruff_rc:n(e.RUFF),
  ref_tests_rc:n(e.REF_RC),leak_count:n(e.LEAK),review_verdict:verdict,
  key_before:rd(o+"/key-before.txt").trim(),key_after:rd(o+"/key-after.txt").trim()};
fs.writeFileSync(o+"/summary.json",JSON.stringify(s,null,2)+"\n");
const z=(v)=>v===null?"none":String(v);
console.log(`${s.sha7} exit=${z(s.exit_code)} turns=${turns} own=${z(s.own_tests_rc)} ref=${z(s.ref_tests_rc)} ruff=${z(s.ruff_rc)} leak=${z(s.leak_count)} review=${verdict} elapsed=${z(s.elapsed_s)}s`);
'
exit 0
