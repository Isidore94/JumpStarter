#!/usr/bin/env bash
# Plumbing test for run-orchestrate.sh: no network. Stub claude and llm stand on PATH; HOME is a temp dir
# so the worktree and the OpenRouter key stay out of the real home.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RUNNER="$HERE/run-orchestrate.sh"
T=$(mktemp -d)
fail() { echo "SELFTEST FAIL: $1 (temp dir kept: $T)"; exit 1; }
jget() { F="$1" K="$2" bun -e 'const s=JSON.parse(require("fs").readFileSync(process.env.F,"utf8"));console.log(String(s[process.env.K]))'; }

export HOME="$T/home"
mkdir -p "$HOME/llm-harness" && echo "stub-key-not-real" > "$HOME/llm-harness/openrouter.key" || fail "setup home"

STUB="$T/bin"; mkdir -p "$STUB" || fail "setup stub dir"
cat > "$STUB/claude" <<'STUB_EOF'
#!/usr/bin/env bash
# Stub claude: a review call (--output-format json) prints a GO verdict; any other call writes files in cwd.
prev=""
for a in "$@"; do
  if [ "$prev" = "--output-format" ] && [ "$a" = "json" ]; then
    echo '{"result":"{\"verdict\":\"GO\"}"}'
    exit 0
  fi
  prev="$a"
done
echo "hello" > hello.txt
mkdir -p .qo && echo "# report (stub)" > .qo/report.md
echo '{"type":"assistant"}'
STUB_EOF
printf '#!/usr/bin/env bash\necho "credit: stub"\n' > "$STUB/llm"
chmod +x "$STUB/claude" "$STUB/llm" || fail "setup stubs"
export PATH="$STUB:$PATH"

# Source repo: base has tests/test_a.py and README.md; ref adds tests/test_b.py (the reference test).
SRC="$T/src"
git init -q "$SRC" && printf 'hello base\n' > "$SRC/README.md" && mkdir -p "$SRC/tests" \
  && printf 'def test_a():\n    assert 1 + 1 == 2\n' > "$SRC/tests/test_a.py" \
  && git -C "$SRC" add -A && git -C "$SRC" -c user.name=selftest -c user.email=selftest@local commit -qm base \
  || fail "setup source repo"
BASE=$(git -C "$SRC" rev-parse HEAD)
printf 'def test_b():\n    assert "b" * 2 == "bb"\n' > "$SRC/tests/test_b.py"
git -C "$SRC" add -A && git -C "$SRC" -c user.name=selftest -c user.email=selftest@local commit -qm ref || fail "setup ref commit"
REF=$(git -C "$SRC" rev-parse HEAD)

BRIEF="$T/brief.md"; echo "Make hello.txt contain hello." > "$BRIEF"
SEED="$T/seed.patch"
printf 'diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-hello base\n+hello seeded\n' > "$SEED"

# Run 1: plain.
OUT1="$T/out1"
bash "$RUNNER" "$SRC" "$BASE" "$REF" "$BRIEF" "$OUT1" > "$T/run1.log" 2>&1
[ -f "$OUT1/summary.json" ] || fail "summary.json missing after plain run (see $T/run1.log)"
[ "$(jget "$OUT1/summary.json" turns)" = "1" ] || fail "turns is not 1"
[ "$(jget "$OUT1/summary.json" review_verdict)" = "GO" ] || fail "review_verdict is not GO"
grep -q hello.txt "$OUT1/diff.patch" || fail "diff.patch does not contain hello.txt"
[ "$(jget "$OUT1/summary.json" own_tests_rc)" = "0" ] || fail "own_tests_rc is not 0"
[ "$(jget "$OUT1/summary.json" ref_tests_rc)" = "0" ] || fail "ref_tests_rc is not 0"

# Run 2: seeded.
OUT2="$T/out2"
bash "$RUNNER" "$SRC" "$BASE" "$REF" "$BRIEF" "$OUT2" "$SEED" > "$T/run2.log" 2>&1
[ -f "$OUT2/summary.json" ] || fail "summary.json missing after seeded run (see $T/run2.log)"
[ "$(jget "$OUT2/summary.json" seed_applied)" = "true" ] || fail "seed_applied is not true"
[ -f "$OUT2/diff-seeded.patch" ] || fail "diff-seeded.patch missing"

rm -rf "$T" 2>/dev/null || { chmod -R u+w "$T"; rm -rf "$T"; }
echo "SELFTEST PASS"
exit 0
