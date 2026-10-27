#!/usr/bin/env bash
# usage: packet.sh <run-dir> <review|judge> [repo base ref]  -> writes <run-dir>/packet-<kind>.md
# review packet: brief + diff + lead test results (no reference). judge packet adds the self-review and the reference diff.
set -u
OUT=$1; kind=$2
brief=$(dirname "$OUT")/../../briefs/$(basename "$(dirname "$OUT")").md
P="$OUT/packet-$kind.md"
{
  echo "# BRIEF"; cat "$brief"; echo
  echo "# CANDIDATE DIFF"; echo '```diff'; cat "$OUT/diff.patch"; echo '```'; echo
  echo "# LEAD TEST RESULTS"
  echo "## builder's own test command (exit $(grep -o "\"own_tests_rc\": *[-0-9a-z]*" "$OUT/summary.json" | sed "s/.*: *//"))"; echo '```'; tail -40 "$OUT/own-tests.txt" 2>/dev/null; echo '```'
  echo "## lint (exit $(grep -o "\"ruff_rc\": *[-0-9a-z]*" "$OUT/summary.json" | sed "s/.*: *//"))"; echo '```'; tail -20 "$OUT/ruff.txt" 2>/dev/null; echo '```'
  if [ "$kind" = judge ]; then
    echo "## hidden reference tests (exit $(grep -o "\"ref_tests_rc\": *[-0-9a-z]*" "$OUT/summary.json" | sed "s/.*: *//"))"; echo '```'; tail -60 "$OUT/ref-tests.txt" 2>/dev/null; echo '```'
    echo; echo "# BUILDER SELF-REVIEW"; echo '```json'; cat "$OUT/qo/review.json" 2>/dev/null || echo "(none)"; echo '```'
    echo; echo "# REFERENCE DIFF (the merged change, for comparison)"; echo '```diff'
    git -C "$3" diff "$4" "$5" -- . ':!*.json' ':!*.md' | head -1500; echo '```'
  fi
} | sed -E 's/sk-or[-_A-Za-z0-9]{8,}/<key>/g' > "$P"
wc -c "$P"
