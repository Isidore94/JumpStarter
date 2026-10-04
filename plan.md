# JumpStarter plan

## Goal

Point any repo, new or existing, at JumpStarter and have it set up for agentic coding
with Claude, Codex/ChatGPT or a local model. The `.md` files are specific, minimal,
written in plain language, and cheap to read (decision 0003). The foundation is the
product; the CLI is how it gets into a repo (decision 0002).

## Now

- Working on: v2 "lite" refactor on `claude/jolly-maxwell-p00ntg`. Lite default, team
  add-on, `AGENTS.md` as the source, `SETUP.md` by URL. Owner approved 2026-10-04.
- Last test run: 2026-10-04: pytest 65 passed, exit 0, on CPython 3.11.15 and 3.9.23;
  ruff 0.16.6 clean, exit 0; `check .` 14 checks, no gaps, exit 0.
- Next step: the owner reviews the branch, then gate 2 below.
- Waiting on the owner: review and merge of the refactor branch.

## Next

1. **Gate 2: one real new repo set up from empty through `SETUP.md`**, by an agent,
   with the owner answering the questions. Record which questions were hard and
   which blanks had no good answer. Nothing is "proven" until this is done.
2. **Retrofit one real repo on the older layout** (the source project), report only.
   Expect advisories for its old file names, and a size gap if its rules file is over
   200 lines (it was 418 on 2026-09-03). Confirm `sync-agents` collapses its copies.
3. **`check` in CI on this repo** (GitHub Actions: pytest, ruff, `check .`).
4. **A cross-tool packet**: one tool builds it, the other reviews it, from the same
   packet file. Gate 4 (a Codex lead spawning a native role) closed 2026-09-10.

## Ideas (not approved, do not build)

- `jumpstart archive`: move old log entries out automatically. Open question: where is
  the cut, so that a wrong cut never loses the record?
- A `--json` flag on `retrofit` for CI. Which consumer needs it? Exit codes work today.
- Per-project size limits. A limit a project can raise gets raised instead of archived.
- Templates for one specific local tool (Aider, OpenCode). Only if the owner uses one.
- Never: a `doctor` that auto-fixes a repo. `retrofit` is report-only by invariant.

## Out of scope

The design's assumption, not yet the owner's words (0002 answer 9). Re-ask once they
hit a case:

- generating a project's own content (its code, its real rules, its goals);
- editing a repo it was asked only to audit;
- a third-party dependency in `tools/`;
- anything specific to one project in `templates/`.
