#!/usr/bin/env bash
# Qwen minimal-brief trial runner. Adapted from docs/bench/qwen-trial-10/run-task.sh (commit 88406c8):
# - OpenRouter through proxy.js (fp4 providers only, cheapest first, reasoning low, exact per-request cost)
# - hidden reference tests also get the ref commit's fixtures and helpers under tests/
# - pass mode: PASS_FEEDBACK=<file> reuses the worktree and feeds the lead's findings back (test failures or a NO-GO)
# - no seed patch, no separate Qwen self-review pass (Haiku medium is the gate, run by the lead)
# usage: run-task.sh <repo> <base> <ref> <brief.md> <outdir>
#   env: PASS_FEEDBACK=<file> (rework pass), SKIP_OWN=1 (skip the repo's own suite, e.g. TBV3 before 13:00),
#        POST_ONLY=1 (the build already ran, e.g. the runner shell was reaped: do only steps 6-9 on the existing worktree)
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
MODEL=qwen/qwen3.8-27b
if [ $# -lt 5 ]; then echo "usage: $0 <repo> <base> <ref> <brief.md> <outdir>" >&2; exit 2; fi
repo=$1; base=$2; ref=$3
[ -f "$4" ] || { echo "setup: no brief at $4" >&2; exit 1; }
brief=$(cd "$(dirname "$4")" && pwd)/$(basename "$4")
mkdir -p "$5" || exit 1
OUT=$(cd "$5" && pwd) || exit 1
[ -n "$OUT" ] || exit 1
feedback=${PASS_FEEDBACK:-}; post=${POST_ONLY:-0}
if [ -n "$feedback" ]; then [ -f "$feedback" ] || { echo "setup: no feedback file at $feedback" >&2; exit 1; }; fi
EXCL=(. ':!.qo' ':!.claude' ':!CLAUDE.md')

# render <template> <out> <placeholder> <value>: literal replace (split/join, so a $ in the value is safe).
render() {
  F_T=$(cygpath -m "$1") F_O=$(cygpath -m "$2") F_K="$3" F_V="$4" bun -e 'const fs=require("fs"),e=process.env;fs.writeFileSync(e.F_O,fs.readFileSync(e.F_T,"utf8").split(e.F_K).join(e.F_V))'
}

# 1. Worktree from the base tree, no history, with a baseline commit (reused in pass mode).
sha=$(git -C "$repo" rev-parse "$ref") || { echo "setup: ref $ref not found in $repo" >&2; exit 1; }
sha7=${sha:0:7}
wt=${HOME:?}/llm-harness/wt/qtm-$sha7
if [ "$post" = 1 ]; then
  [ -d "$wt/.git" ] || { echo "setup: POST_ONLY but no worktree at $wt" >&2; exit 1; }
elif [ -z "$feedback" ]; then
  rm -rf "${wt:?}" && mkdir -p "$wt" || exit 1
  git -C "$repo" archive "$base" | tar -x -C "$wt" || { echo "setup: archive of $base failed" >&2; exit 1; }
  git -C "$wt" init -q && git -C "$wt" add -A && git -C "$wt" -c user.name=bench -c user.email=bench@local commit -qm baseline \
    || { echo "setup: baseline commit failed" >&2; exit 1; }
else
  [ -d "$wt/.git" ] || { echo "setup: pass mode but no worktree at $wt" >&2; exit 1; }
fi
if [ "$post" != 1 ]; then rm -rf "${OUT:?}/home" && rm -f "$OUT/summary.json" "$OUT/usage.jsonl" && mkdir -p "$OUT/home" || exit 1; fi

# 2. Runtime table, keyed on the repo's basename (same as trial-10).
case "$(basename "$repo")" in
  TradingBotV3)
    PY=C:/Users/Aaron/TradingBotV3/.venv/Scripts/python.exe
    OWN="$PY scripts/run_tests.py"; [ -f "$wt/scripts/run_tests.py" ] || OWN="$PY -m pytest tests/ -q -n 4 -p no:cacheprovider"
    LINT="$PY -m ruff check scripts tests"
    REFKIND=pytest; TEST_DIR=tests; PKG=""; LOCK="$HOME/llm-harness/tbv3-suite.lock"
    NOTE="Never run the whole suite (needs 20 GB RAM, 12 min). Run only the test files you touched. Qt needs QT_QPA_PLATFORM=offscreen."
    export QT_QPA_PLATFORM=offscreen ;;
  TraderTaxHelper)
    PY=C:/Users/Aaron/TraderTaxHelper/.venv/Scripts/python.exe
    OWN="$PY -m pytest -q"; LINT="$PY -m ruff check tradertax tests"
    REFKIND=pytest; TEST_DIR=tests; PKG=tradertax; LOCK=""; NOTE=""
    export QT_QPA_PLATFORM=offscreen ;;
  EveTradingbot)
    PY=C:/Users/Aaron/EveTradingbot/.venv/Scripts/python.exe
    OWN="$PY -m pytest -q"; LINT="$PY -m ruff check ."
    REFKIND=pytest; TEST_DIR=tests; PKG=evescreener; LOCK=""; NOTE="Always run tests with PYTHONPATH=src."
    export PYTHONPATH=src ;;
  ContentSummarizer)
    PY=C:/Users/Aaron/ContentSummarizer/.venv/Scripts/python.exe
    OWN="$PY -m unittest discover -s tests -v"; LINT=""
    REFKIND=unittest; TEST_DIR=tests; PKG=pipeline; LOCK=""; NOTE="No pytest, no ruff: python -m unittest." ;;
  *)
    PY=C:/Users/Aaron/TraderTaxHelper/.venv/Scripts/python.exe
    OWN="$PY -m pytest -q"; LINT="$PY -m ruff check ."
    REFKIND=pytest; TEST_DIR=tests; PKG=""; LOCK=""; NOTE="" ;;
esac
case "$REFKIND" in
  pytest) REFPAT='test_*.py'; TEST_ONE="$PY -m pytest -q <test file>" ;;
  unittest) REFPAT='test_*.py'; TEST_ONE="$PY -m unittest tests.<test module>" ;;
esac
[ -x "$PY" ] || { echo "setup: no python at $PY" >&2; exit 1; }

# 3. Role files and CLAUDE.md (orchestration rules, then the repo's own), first pass only.
if [ -z "$feedback" ] && [ "$post" != 1 ]; then
  mkdir -p "$wt/.claude/agents" && cp C:/Users/Aaron/JumpStarter/templates/.claude/agents/*.md "$wt/.claude/agents/" \
    || { echo "setup: role files not copied" >&2; exit 1; }
  render "$HERE/prompts/orchestrator-CLAUDE.md" "$OUT/orchestrator-CLAUDE.md" "{{PY}}" "$PY" \
    && render "$OUT/orchestrator-CLAUDE.md" "$OUT/orchestrator-CLAUDE.md" "{{TEST_ONE}}" "$TEST_ONE" \
    && render "$OUT/orchestrator-CLAUDE.md" "$OUT/orchestrator-CLAUDE.md" "{{LINT}}" "${LINT:-no linter in this repo}" \
    && render "$OUT/orchestrator-CLAUDE.md" "$OUT/orchestrator-CLAUDE.md" "{{NOTE}}" "$NOTE" \
    || { echo "setup: orchestrator CLAUDE.md not rendered" >&2; exit 1; }
  { cat "$OUT/orchestrator-CLAUDE.md"; if [ -f "$wt/CLAUDE.md" ]; then echo; cat "$wt/CLAUDE.md"; fi; } > "$OUT/CLAUDE.new" \
    && mv "$OUT/CLAUDE.new" "$wt/CLAUDE.md" || { echo "setup: CLAUDE.md not written" >&2; exit 1; }
  mkdir -p "$wt/.qo" || exit 1
fi

# 4. Main prompt (first pass) or rework prompt (pass mode).
if [ "$post" = 1 ]; then
  max_turns=0
elif [ -z "$feedback" ]; then
  render "$HERE/prompts/main-prompt.md" "$OUT/prompt.md" "{{BRIEF}}" "$(cat "$brief")" || exit 1
  max_turns=80
else
  render "$HERE/prompts/main-prompt-pass.md" "$OUT/prompt.md" "{{BRIEF}}" "$(cat "$brief")" \
    && render "$OUT/prompt.md" "$OUT/prompt.md" "{{FEEDBACK}}" "$(cat "$feedback")" || exit 1
  max_turns=50
fi

# 5. Proxy (fp4 pin, usage log), then the orchestrator run. The key is read into the environment and never printed.
got=0; proxy_pid=""
cleanup() { [ -n "$proxy_pid" ] && kill $proxy_pid 2>/dev/null; if [ -n "$LOCK" ] && [ "$got" = 1 ]; then rm -rf "${LOCK:?}"; fi; return 0; }
trap cleanup EXIT; trap 'cleanup; exit 143' INT TERM HUP
if [ "$post" = 1 ]; then
  # Build already ran: exit code and elapsed from the transcript's result event (or "reaped" if it never ended).
  read -r exit_code elapsed_s < <(TR=$(cygpath -m "$OUT/transcript.jsonl") bun -e 'const l=require("fs").readFileSync(process.env.TR,"utf8").trim().split("\n");let r=null;for(const x of l){try{const j=JSON.parse(x);if(j.type==="result")r=j}catch(e){}}console.log(r?(r.is_error?1:0)+" "+Math.round((r.duration_ms||0)/1000):"reaped 0")')
else
key="$HOME/llm-harness/openrouter.key"
[ -f "$key" ] || { echo "setup: no OpenRouter key file" >&2; exit 1; }
PORT=0 USAGE_LOG=$(cygpath -m "$OUT/usage.jsonl") REASONING=low bun "$HERE/proxy.js" > "$OUT/proxy.out" 2>&1 &
proxy_pid=$!
port=""
for _ in $(seq 1 40); do port=$(sed -n 's/^proxy listening on //p' "$OUT/proxy.out"); [ -n "$port" ] && break; sleep 0.25; done
[ -n "$port" ] || { echo "setup: proxy did not start" >&2; kill $proxy_pid 2>/dev/null; exit 1; }
export CLAUDE_CONFIG_DIR="$OUT/home" ANTHROPIC_BASE_URL="http://127.0.0.1:$port"
ANTHROPIC_AUTH_TOKEN=$(tr -d '\r\n ' < "$key")
export ANTHROPIC_AUTH_TOKEN ANTHROPIC_MODEL=$MODEL ANTHROPIC_DEFAULT_HAIKU_MODEL=$MODEL \
  ANTHROPIC_DEFAULT_SONNET_MODEL=$MODEL ANTHROPIC_DEFAULT_OPUS_MODEL=$MODEL \
  CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_TELEMETRY=1
unset ANTHROPIC_API_KEY
timeout 60 llm key 2>&1 | sed "s/sk-or[^ ]*/<key>/" > "$OUT/key-before.txt"
cd "$wt" || exit 1
t0=$(date +%s)
timeout 2700 claude -p "$(cat "$OUT/prompt.md")" --model "$MODEL" --allowedTools "Read,Edit,Write,Bash,Glob,Grep,Agent" \
  --permission-mode acceptEdits --output-format stream-json --verbose --max-turns $max_turns \
  > "$OUT/transcript.jsonl" 2> "$OUT/stderr.txt"
exit_code=$?
elapsed_s=$(( $(date +%s) - t0 ))
timeout 60 llm key 2>&1 | sed "s/sk-or[^ ]*/<key>/" > "$OUT/key-after.txt"
kill $proxy_pid 2>/dev/null
fi

# 6. Diff of the orchestrator's work (cumulative over passes), and a copy of its .qo/ stages.
git -C "$wt" add -A -N -- "${EXCL[@]}"
git -C "$wt" diff -- "${EXCL[@]}" > "$OUT/diff.patch"
rm -rf "${OUT:?}/qo" && cp -r "$wt/.qo" "$OUT/qo"

# 7. Own tests (TradingBotV3 under the suite lock), lint, import check, then the hidden reference tests: the ref
# commit's test files under ref_ names, plus its fixtures and helpers under tests/ (restored afterwards).
cd "$wt" || exit 1
own_rc=none
if [ "${SKIP_OWN:-0}" = 1 ]; then
  echo "own suite skipped (SKIP_OWN=1)" > "$OUT/own-tests.txt"
elif [ -n "$LOCK" ]; then
  waited=0
  while :; do
    if mkdir "$LOCK" 2>/dev/null; then got=1; echo $$ > "$LOCK/pid"; break; fi
    op=$(cat "$LOCK/pid" 2>/dev/null); if [ -n "$op" ] && ! kill -0 "$op" 2>/dev/null; then rm -rf "${LOCK:?}"; continue; fi
    [ "$waited" -ge 2400 ] && break
    sleep 15; waited=$((waited + 15))
  done
  if [ "$got" = 1 ]; then
    eval "$OWN" > "$OUT/own-tests.txt" 2>&1; own_rc=$?
    rm -rf "${LOCK:?}"; got=0
  else
    echo "lock: $LOCK held for 40 min, own suite not run" > "$OUT/own-tests.txt"
  fi
else
  eval "$OWN" > "$OUT/own-tests.txt" 2>&1; own_rc=$?
fi
ruff_rc=none
if [ -n "$LINT" ]; then eval "$LINT" > "$OUT/ruff.txt" 2>&1; ruff_rc=$?; fi
import_ok=n/a
if [ -n "$PKG" ]; then
  if "$PY" -c "import $PKG; print($PKG.__file__)" > "$OUT/import-check.txt" 2>&1; then
    p=$(cygpath -m "$(tail -n 1 "$OUT/import-check.txt")" 2>/dev/null | tr "[:upper:]" "[:lower:]")
    w=$(cygpath -m "$wt" | tr "[:upper:]" "[:lower:]"); case "$p" in "$w"/*) import_ok=true ;; *) import_ok=false ;; esac
  else
    import_ok=false
  fi
else
  echo "no import check for $(basename "$repo")" > "$OUT/import-check.txt"
fi
refs=(); fx=(); bak=$(mktemp -d); mkdir -p "$wt/$TEST_DIR"
while IFS= read -r p; do
  [ -n "$p" ] || continue
  git -C "$repo" cat-file -e "$ref:$p" 2>/dev/null || continue
  case "$(basename "$p")" in
    $REFPAT) n="$TEST_DIR/ref_$(basename "$p")"; git -C "$repo" show "$ref:$p" > "$wt/$n" && refs+=("$n") ;;
    *) mkdir -p "$wt/$(dirname "$p")" "$bak/$(dirname "$p")"
       if [ -e "$wt/$p" ]; then cp "$wt/$p" "$bak/$p"; fi
       git -C "$repo" show "$ref:$p" > "$wt/$p" && fx+=("$p") ;;
  esac
done < <(git -C "$repo" diff --name-only "$base" "$ref" -- "$TEST_DIR")
if [ ${#refs[@]} -gt 0 ]; then
  ref_rc=0
  case "$REFKIND" in
    pytest) "$PY" -m pytest -q -rf -p no:cacheprovider "${refs[@]}" > "$OUT/ref-tests.txt" 2>&1; ref_rc=$? ;;
    unittest)
      : > "$OUT/ref-tests.txt"
      for n in "${refs[@]}"; do m=${n%.py}; m=${m//\//.}; "$PY" -m unittest "$m" >> "$OUT/ref-tests.txt" 2>&1 || ref_rc=1; done ;;
  esac
  for n in "${refs[@]}"; do rm -f "$wt/$n"; done
  for p in "${fx[@]}"; do if [ -e "$bak/$p" ]; then cp "$bak/$p" "$wt/$p"; else rm -f "$wt/$p"; fi; done
else
  echo "no reference test files in $base..$ref" > "$OUT/ref-tests.txt"; ref_rc=none
fi
rm -rf "${bak:?}"
printf '%s\n' "${fx[@]}" > "$OUT/ref-fixtures.txt"

# 8. Leak audit (git history, climbing out, the source repo).
if [ -f "$OUT/transcript.jsonl" ]; then
  rp=$(basename "$repo")
  a=$(grep -c -E 'git (log|show|reflog)|\.\./\.\.' "$OUT/transcript.jsonl")
  b=$(grep -v -E '\.venv|qwen-trial-min.{1,2}runs' "$OUT/transcript.jsonl" | grep -c -E "Users.{1,2}Aaron.{1,2}$rp")
  echo $((a + b)) > "$OUT/leak.txt"
else
  echo missing > "$OUT/leak.txt"
fi
leak_count=$(cat "$OUT/leak.txt")

# Mask the key everywhere (the orchestrator has Bash with ANTHROPIC_AUTH_TOKEN exported).
find "$OUT" -type f -exec sed -i -E 's/sk-or[-_A-Za-z0-9]{8,}/<key>/g' {} +

# 9. Summary and the one-line report. cost_usd = sum of OpenRouter's per-request cost from the proxy log.
OUTW=$(cygpath -m "$OUT") SHA7=$sha7 REPO=$repo BASE=$base REF=$ref PASS="${feedback:+rework}" \
  EXIT=$exit_code ELAPSED=$elapsed_s OWN_RC=$own_rc RUFF=$ruff_rc REF_RC=$ref_rc LEAK=$leak_count \
  OWN_CMD="$OWN" LINT_CMD="$LINT" IMPORT_OK=$import_ok REFKIND=$REFKIND \
  bun -e '
const fs=require("fs"),e=process.env,o=e.OUTW;
const rd=(f)=>{try{return fs.readFileSync(f,"utf8")}catch(x){return ""}};
let verdict="unparsed";
try{const v=JSON.parse(rd(o+"/qo/review.json")).verdict;if(typeof v==="string")verdict=v}catch(x){}
let turns=0;for(const line of rd(o+"/transcript.jsonl").split("\n")){try{if(JSON.parse(line).type==="assistant")turns++}catch(x){}}
const n=(v)=>/^\d+$/.test(v)?Number(v):null;
const t=rd(o+"/ref-tests.txt");
let rp=null,rt=null;
if(e.REFKIND==="pytest"){
  const line=t.split("\n").filter((x)=>/\d+ (passed|failed|errors?)\b/.test(x)).pop();
  if(line){const c=(w)=>{const m=new RegExp("(\\d+) "+w+"\\b").exec(line);return m?Number(m[1]):0};rp=c("passed");rt=rp+c("failed")+c("errors?")}
}else if(e.REFKIND==="unittest"){
  const ran=[...t.matchAll(/^Ran (\d+) tests?/gm)];
  if(ran.length){
    rt=ran.reduce((s,m)=>s+Number(m[1]),0);
    const bad=[...t.matchAll(/^FAILED \((.*)\)\s*$/gm)].reduce((s,m)=>s+[...m[1].matchAll(/(?:failures|errors)=(\d+)/g)].reduce((u,k)=>u+Number(k[1]),0),0);
    rp=rt-bad;
  }
}
const u={requests:0,input:0,output:0,thinking:0,cache_read:0,cost:0,errors:0,providers:{}};
for(const line of rd(o+"/usage.jsonl").split("\n")){let j;try{j=JSON.parse(line)}catch(x){continue}
  u.requests++; if(j.error||j.status!==200){u.errors++;continue}
  const g=j.usage||{}; u.input+=g.input_tokens||0; u.output+=g.output_tokens||0; u.thinking+=g.output_tokens_details?.thinking_tokens||0;
  u.cache_read+=g.cache_read_input_tokens||0; u.cost+=g.cost||0; if(j.provider)u.providers[j.provider]=(u.providers[j.provider]||0)+1}
u.cost=Number(u.cost.toFixed(6));
const used=(f)=>{const m=/used \$([\d.]+)/.exec(rd(f));return m?Number(m[1]):null};
const u0=used(o+"/key-before.txt"),u1=used(o+"/key-after.txt");
const keyDelta=u0===null||u1===null?null:Number((u1-u0).toFixed(6));
const s={sha7:e.SHA7,repo:e.REPO,base:e.BASE,ref:e.REF,pass:e.PASS||"first",
  exit_code:n(e.EXIT),elapsed_s:n(e.ELAPSED),turns,own_tests_rc:n(e.OWN_RC),ruff_rc:n(e.RUFF),
  ref_tests_rc:n(e.REF_RC),leak_count:n(e.LEAK),self_review_verdict:verdict,
  own_cmd:e.OWN_CMD||null,lint_cmd:e.LINT_CMD||null,
  import_ok:e.IMPORT_OK==="n/a"?"n/a":e.IMPORT_OK==="true",
  ref_pass:rp,ref_total:rt,cost_usd:u.cost,usage:u,key_delta_usd:keyDelta,
  key_before:rd(o+"/key-before.txt").trim(),key_after:rd(o+"/key-after.txt").trim()};
fs.writeFileSync(o+"/summary.json",JSON.stringify(s,null,2)+"\n");
const z=(v)=>v===null?"none":String(v);
console.log(`${s.sha7} ${s.pass} exit=${z(s.exit_code)} turns=${turns} own=${z(s.own_tests_rc)} ref=${z(s.ref_tests_rc)} ref_pass=${z(rp)}/${z(rt)} ${s.ruff_rc===null?"lint: none":"ruff="+s.ruff_rc} import=${s.import_ok} leak=${z(s.leak_count)} self=${verdict} cost=$${u.cost} (key delta ${z(keyDelta)}) elapsed=${z(s.elapsed_s)}s`);
'
exit 0
