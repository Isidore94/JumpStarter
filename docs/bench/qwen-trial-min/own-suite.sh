#!/usr/bin/env bash
# Rerun only the own-suite step of run-task.sh on a finished TradingBotV3 worktree whose parent predates
# scripts/run_tests.py, then rewrite own_tests_rc in summary.json. usage: own-suite.sh <run dir name, e.g. ada1557f>
set -u
run=$1; sha7=${run:0:7}; wt=$HOME/llm-harness/wt/qt10-$sha7; OUT=$(dirname "$0")/runs/$run
PY=C:/Users/Aaron/TradingBotV3/.venv/Scripts/python.exe; LOCK=$HOME/llm-harness/tbv3-suite.lock
export QT_QPA_PLATFORM=offscreen
[ -d "$wt" ] && [ -f "$OUT/summary.json" ] || { echo "no worktree or summary for $sha7" >&2; exit 2; }
got=0
for _ in $(seq 240); do
  if mkdir "$LOCK" 2>/dev/null; then got=1; echo $$ > "$LOCK/pid"; break; fi
  op=$(cat "$LOCK/pid" 2>/dev/null); if [ -n "$op" ] && ! kill -0 "$op" 2>/dev/null; then rm -rf "$LOCK"; continue; fi
  sleep 10
done
[ $got = 1 ] || { echo "lock held 40 min" >&2; exit 3; }
trap 'rm -rf "$LOCK" 2>/dev/null; exit 143' INT TERM HUP; trap 'rm -rf "$LOCK" 2>/dev/null' EXIT
echo "$(date -u +%FT%TZ) own suite start $sha7" >> "$OUT/runner.log"
( cd "$wt" && "$PY" -m pytest tests/ -q -n 4 -p no:cacheprovider ) > "$OUT/own-tests.txt" 2>&1; rc=$?
rm -rf "$LOCK"; trap - EXIT INT TERM HUP
bun -e 'const f=process.argv[1],s=JSON.parse(require("fs").readFileSync(f,"utf8"));s.own_tests_rc=+process.argv[2];s.own_cmd="pytest tests/ -q -n 4 -p no:cacheprovider (own-suite.sh rerun)";require("fs").writeFileSync(f,JSON.stringify(s,null,2)+"\n")' "$OUT/summary.json" "$rc"
echo "$(date -u +%FT%TZ) own suite done $sha7 rc=$rc $(tail -1 "$OUT/own-tests.txt")" >> "$OUT/runner.log"
echo "$sha7 own_rc=$rc"
