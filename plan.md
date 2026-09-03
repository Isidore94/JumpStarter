# JumpStarter remaining roadmap

Authoritative for: **what is not built yet, in what order, and what gates it.**
What exists: [`CHANGELOG.md`](CHANGELOG.md). Where we are right now:
[`CURRENT_CHECKPOINT.md`](CURRENT_CHECKPOINT.md).

Only unfinished work belongs in this file.

## 1. Mission and product boundary

JumpStarter is a reusable foundation for running software projects with AI agents. It
carries the control-file templates, the playbooks and a small CLI that bootstraps a new
project or retrofits an existing one, for Claude Code and for Codex.

It does: templates for the control set, an audit of an existing repo against that
standard, placeholder filling, `CLAUDE.md` ↔ `AGENTS.md` synchronisation, and size and
drift enforcement.

It never does: generate project content, edit a repo it was asked only to audit, take a
third-party dependency in `tools/`, or carry domain specifics from the project it was
distilled from. Those are boundaries, not backlog items.

**What the program is for, in the owner's words.** The record is
[`docs/decisions/0001-owner-goals-and-priorities.md`](docs/decisions/0001-owner-goals-and-priorities.md).
Short form: a fresh session in any repo can be told "apply JumpStarter here" and knows
what to do; the templates are short enough to read in one sitting; the two tools never
drift; and nothing in the templates is specific to the project they came from.

## 2. Status vocabulary

These labels must not be collapsed:

| Status | Meaning | Production authority |
|---|---|---|
| `PLANNED` | Designed; no implementation exists. | None |
| `IMPLEMENTED` | Code exists. | None by itself |
| `GREEN` | Deterministic tests pass. | Only existing behaviour |
| `VALIDATED` | Passed the documented real-world checks. | None by itself |
| `PROMOTED` | Explicitly approved by the owner, with rollback. | Yes |
| `RETIRED` | Intentionally disabled or replaced. | None |

Current code and test status belongs in `CHANGELOG.md`. The current branch and exact test
counts belong in `CURRENT_CHECKPOINT.md`.

## 3. Current-state summary

As of 2026-09-03 (second pass): the templates, the five playbooks, the CLI and its test
suite are `IMPLEMENTED` and `GREEN`. JumpStarter runs its own control set (`check .` is
green; `retrofit .` is exit 0 with one advisory).

**Gate 1 is met and gate 3 is met.** Three real repositories have been audited, report
only — the source project's working copy, a repo with partial control files, and a repo
with no control set at all. The two false positives and four misses that produced are
fixed, each with a test built from the shape that produced it. The Python floor is a
measurement (CPython 3.9.25) rather than a claim.

`retrofit` is therefore `VALIDATED` for the audit path. **Nothing is `PROMOTED`**: gate 2
— a new project bootstrapped end to end by a human — is still open, so no template has
yet been proven by being used from empty.

## 4. Authority and change control

When documents disagree, use this order:

1. this roadmap, for remaining-work order, invariants and promotion policy;
2. `PRINCIPLES.md`, for why a rule exists;
3. accepted decision records under `docs/decisions/`;
4. the playbooks;
5. historical notes.

`WISHLIST.md` is outside the authority chain: it never authorizes implementation.

## 5. Non-negotiable invariants

- No third-party dependency in `tools/`. It runs on a bare Python 3.9+ — **measured on
  CPython 3.9.25, 2026-09-03**, not assumed.
- `retrofit` never writes to the audited repo.
- `init` never overwrites an existing file without `--force`.
- No domain-specific content in `templates/`.
- Every rule in `CLAUDE.md` has an entry in `docs/INTERNALS.md`.
- `sha256(CLAUDE.md) == sha256(AGENTS.md)`.
- A change to a template is mirrored in its playbook and its check in the same commit.

## 6. Validation program

Green tests do not satisfy a gate. A **gate** here is a real repository, audited or
initialised by a human, with the result recorded.

For each gate record: the repo, the command, the exit code, what the report said, and —
the part that matters — **what the report got wrong**: a gap it named that was not a gap,
or a gap it missed.

## 7. Promotion ladder

A template or check is `PROMOTED` — recommended as the default — only after:

1. it has run against at least one real existing repository;
2. its false positives are recorded and either fixed or documented as accepted;
3. the owner has approved it, recorded in the revision history.

Until then it ships as the default but is described in the playbook as unproven.

## 12. Remaining work, in execution order

| Order | Phase | Plain-English outcome |
|---:|---|---|
| **0 — DONE** | First real retrofit | Run the audit against a real repo and fix what it gets wrong — three repos, 2026-09-03 |
| **1 — NOW** | Close the loop on the templates | Every template proven by being used once |
| **2** | CI and distribution | `check` runs in CI; the tool is easy to fetch |
| **3 — LATER** | More tools, only if asked for | Nothing here is authorized |

### Phase 0 — DONE: first real retrofit

1. **Audit a real existing repository, report only.** — `VALIDATED`, **gate 1 CLOSED
   2026-09-03**. Three real repositories, working copies not clones: the source project
   (25 checks, 3 gaps, all three real), one with partial control files (15 gaps, 2
   advisories), one with no control set (22 of 22). The findings, false positives and
   misses are in `CURRENT_CHECKPOINT.md`.
2. **Fix what the audit gets wrong.** — `GREEN`, done 2026-09-03. Two false positives
   became advisories (gitignored allow-list; active-state block under another heading);
   four misses became checks (stray root ledgers, `PLAN_MAX_LINES`, whole-file changelog
   measurement, the empty-repo report). Nine tests, each from the shape that produced its
   finding, all nine proven to fail on the previous commit.

### Phase 1 — NEXT: close the loop on the templates

1. **Bootstrap one real new project from the templates.** — `PLANNED`. Every placeholder
   filled by a human answering the questionnaire; note which questions were hard to
   answer and which placeholders had no good answer. **Gate 2 — the only gate still
   open.** The templates changed materially on 2026-09-03 (a fourth agent, a reshaped
   packet, four new limits and advisories); none of that has been used from empty.
2. **Hand one packet to a Codex session and one to Claude Code from the same packet
   file.** — `PLANNED`. Prove the handoff and verdict formats survive the crossing.
   Gate 4.
3. **Exercise the `tester` role once, for real.** — `PLANNED`. It was added from the
   source project's runbook, not from a run in this repo. Until a tester has written a
   red test here and a builder has made it green without weakening it, the role is
   documented rather than proven. No gate number until the owner authorises the work
   that would use it.

### Phase 2 — CI and distribution

1. **`check` in CI on this repo.** — `PLANNED`.
2. **A one-line fetch-and-run for a repo that does not vendor JumpStarter.** — `PLANNED`;
   needs the owner's decision on how they want to distribute it.

## 13. Definition of done

The roadmap is complete when:

1. the audit has run against at least one real existing repository and its false
   positives are fixed or documented — **done 2026-09-03, three repositories**;
2. at least one new project has been bootstrapped end to end from the templates;
3. one packet has been built by one tool and reviewed by the other;
4. every rule in `CLAUDE.md` has an evidence entry in `docs/INTERNALS.md`;
5. tests, lint and `check .` are green and recorded in the checkpoint;
6. no gate in the checkpoint's table is open;
7. `templates/` still contains nothing specific to any one project.
