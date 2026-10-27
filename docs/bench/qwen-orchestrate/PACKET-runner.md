# Packet: run-orchestrate.sh (the Qwen orchestration bench runner)

Branch `claude/qo-runner` from `claude/qwen-orchestrate-test`, in your own worktree. Files you may create:
`docs/bench/qwen-orchestrate/run-orchestrate.sh` and `docs/bench/qwen-orchestrate/selftest.sh`. Nothing else.
Bash (Git Bash on Windows; `bun` is available for JSON, `jq` and `python` are NOT on PATH). Keep it to the
smallest script that does all of this; no options nobody asked for.

## run-orchestrate.sh <repo> <base> <ref> <brief.md> <outdir> [seed.patch]

`repo` is a Windows path like C:/Users/Aaron/JumpStarter; `base` and `ref` are commits in it (the orchestrator
starts from `base`; `ref` holds the reference fix and its tests, which the orchestrator must never see).
`HERE` = the script's own directory (prompts live in `$HERE/prompts/`).

1. Resolve `sha7` = first 7 chars of `git -C repo rev-parse ref`. Worktree `wt=$HOME/llm-harness/wt/qo-$sha7`:
   `rm -rf`, `mkdir -p`, then export the tree WITHOUT history: `git -C repo archive base | tar -x -C wt`, then in wt
   `git init -q && git add -A && git -c user.name=bench -c user.email=bench@local commit -qm baseline`.
   `mkdir -p outdir outdir/home` (outdir/home is an empty Claude config dir; recreate it empty each run).
2. Python per repo: `PY=C:/Users/Aaron/EveTradingbot/.venv/Scripts/python.exe` when `repo` contains `EveTradingbot`,
   else `C:/Users/Aaron/TraderTaxHelper/.venv/Scripts/python.exe`.
3. Role files: `mkdir -p wt/.claude/agents && cp C:/Users/Aaron/JumpStarter/templates/.claude/agents/*.md wt/.claude/agents/`.
   CLAUDE.md: write wt/CLAUDE.md = `$HERE/prompts/orchestrator-CLAUDE.md` with `{{PY}}` replaced by `$PY`, followed
   by the repo's original CLAUDE.md if it existed (append; if it did not exist, just the prompt). `mkdir -p wt/.qo`.
4. Main prompt: `$HERE/prompts/main-prompt.md` with `{{BRIEF}}` replaced by the contents of `brief.md`
   (use bun or awk/perl for the multi-line substitution; sed will not do). Save as outdir/prompt.md.
5. Run the orchestrator. Environment for every `claude` call (export; never print the key):
   `CLAUDE_CONFIG_DIR=outdir/home`, `ANTHROPIC_BASE_URL=https://openrouter.ai/api`,
   `ANTHROPIC_AUTH_TOKEN=$(tr -d '\r\n ' < "$HOME/llm-harness/openrouter.key")`, `ANTHROPIC_MODEL=qwen/qwen3.8-27b:floor`,
   `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL` all
   `qwen/qwen3.8-27b:floor`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, `DISABLE_TELEMETRY=1`; `unset ANTHROPIC_API_KEY`.
   Record `llm key` output (the OpenRouter credit line; `llm` is on PATH) to outdir/key-before.txt.
   Then, from inside wt, with start time recorded:
   `timeout 2700 claude -p "$(cat outdir/prompt.md)" --model qwen/qwen3.8-27b:floor --allowedTools "Read,Edit,Write,Bash,Glob,Grep,Agent" --permission-mode acceptEdits --output-format stream-json --verbose --max-turns 80 > outdir/transcript.jsonl 2> outdir/stderr.txt`
   Record the exit code and elapsed seconds. Record `llm key` to outdir/key-after.txt.
6. Capture the diff: in wt, `git add -A -N -- . ':!.qo' ':!.claude' ':!CLAUDE.md'` then
   `git diff -- . ':!.qo' ':!.claude' ':!CLAUDE.md' > outdir/diff.patch`; copy `wt/.qo` to `outdir/qo/`.
   `head -c 60000 outdir/diff.patch > wt/.qo/diff-for-review.patch`.
7. Checks, in wt: `$PY -m pytest -q > outdir/own-tests.txt 2>&1` (record rc), `$PY -m ruff check . > outdir/ruff.txt 2>&1`
   (record rc). Reference tests: for every path in `git -C repo diff --name-only base ref -- tests` write
   `git -C repo show ref:path` into wt at `tests/ref_<basename>` (so Qwen's own file of the same name is kept),
   run `$PY -m pytest -q <those files> > outdir/ref-tests.txt 2>&1`, record rc, then delete the ref_ files.
8. Leak audit: `grep -c -E 'git (log|show|reflog)|\.\./\.\.' outdir/transcript.jsonl` to outdir/leak.txt (0 is fine).
9. Seed: if seed.patch given, `git -C wt apply seed.patch`; record applied yes/no in summary; regenerate
   `wt/.qo/diff-for-review.patch` from the new `git diff` (same excludes) and save it as outdir/diff-seeded.patch.
10. Separate self-review pass, from inside wt, same environment: prompt = `$HERE/prompts/self-review.md` with
    `{{TASK}}` replaced by the brief contents and `{{PY}}` by `$PY`;
    `timeout 900 claude -p "<prompt>" --model qwen/qwen3.8-27b:floor --allowedTools "Read,Bash,Glob,Grep" --permission-mode acceptEdits --output-format json --max-turns 25 > outdir/review-raw.json 2> outdir/review-stderr.txt`.
    Extract `.result` with bun into outdir/review.txt (it should be the JSON verdict; keep whatever came back).
11. outdir/summary.json with bun: `{sha7, repo, base, ref, seed: path|null, seed_applied, exit_code, elapsed_s,
    turns (count of lines in transcript.jsonl whose JSON has type=="assistant"), own_tests_rc, ruff_rc, ref_tests_rc,
    leak_count, review_verdict (the "verdict" parsed from review.txt, or "unparsed"), key_before, key_after
    (the two llm key lines, as text)}`. Print the one-line summary `sha7 exit=<> turns=<> own=<rc> ref=<rc> ruff=<rc> leak=<n> review=<verdict> elapsed=<s>s`.

Leave the worktree in place (the lead inspects it). `set -uo pipefail`; a failing step records its rc and continues
to the next, except steps 1-5 which exit non-zero if the setup fails.

## selftest.sh

Proves the runner's plumbing without the network: creates a temp git repo with one commit (a `tests/test_a.py` that
passes and a `README.md`) as `base`, a second commit that adds `tests/test_b.py` as `ref`; puts a stub `claude`
first on PATH that ignores its arguments, writes `hello.txt` into the cwd and `.qo/report.md`, prints one
stream-json line `{"type":"assistant"}` and, when it sees `--output-format json`, prints `{"result":"{\"verdict\":\"GO\"}"}`
instead; a stub `llm` that prints `credit: stub`; then runs run-orchestrate.sh on it with a one-line brief and asserts:
summary.json exists, `turns` is 1, `review_verdict` is GO, diff.patch contains `hello.txt`, own_tests_rc is 0 and
ref_tests_rc is 0, and a seeded run (seed.patch that edits README.md) reports seed_applied true and diff-seeded.patch
exists. Exit 0 on pass, 1 with the failed assertion named. Run it: `bash docs/bench/qwen-orchestrate/selftest.sh`.
Write selftest.sh FIRST, run it (it must fail: no runner yet), then write the runner and make it pass.

## Handoff
Commit on your branch (message: what the runner does, one paragraph), then reply with: the commit sha, the selftest
output, and anything in the packet you could not do as written.
