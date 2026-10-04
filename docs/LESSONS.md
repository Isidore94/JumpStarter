# Lessons

What broke, why, and the rule it produced. Each `## ` heading is cited by a rule in
`AGENTS.md`; `jumpstart.py check` fails if one is missing. The full incident text for
entries dated before 2026-10-04 is in `docs/archive/INTERNALS_v1.md`.

## retrofit is report-only
- Date: 2026-09-03, first build.
- What broke: the first design added missing files directly. Twelve new files would
  appear, the owner could not tell theirs from ours, and the whole change would be
  reverted, right parts included.
- Rule now: `retrofit` writes nothing, ever. There is no `--fix` and no `doctor`.

## An advisory is not a gap
- Date: 2026-09-03, first audit of three real repos.
- What broke: two findings were literally true and practically false: a machine-local
  allow-list reported as missing, and a status block found under another heading
  reported as absent. A check that fires on correct work gets ignored, and takes the
  real findings with it.
- Rule now: `ADVISORY` is printed with its remedy, counts as `ok`, and does not move the
  exit code.

## init does not overwrite
- Date: 2026-09-03, first build.
- What broke (designed out): the likeliest `init` mistake is running it where a real
  `CLAUDE.md` already holds the project's rules.
- Rule now: skip existing files unless `--force`, and print every skip. Since
  2026-10-04 `init` also refuses to write `AGENTS.md` beside rules that live only in
  `CLAUDE.md`, because that would split them.

## Unfilled placeholders are visible
- Date: 2026-09-03, first build.
- Why: a plausible default (a guessed test command) gets acted on and records a
  baseline that means nothing. An obvious hole does not.
- Rule now: `fill()` replaces only what it was told; `check` reports the rest.

## One source of rules
- Date: 2026-10-04, owner decision 0003.
- What broke: `CLAUDE.md` and `AGENTS.md` were kept as byte-identical copies. That
  doubled every edit, needed a sync step people forgot, and still spoke only to Claude
  and Codex. Local-model tools and most others read `AGENTS.md`.
- Rule now: `AGENTS.md` is the source. `CLAUDE.md` is a one-line `@AGENTS.md` import,
  which Claude Code expands. Supersedes "One source for two tools" (2026-09-03).

## Older file names are accepted
- Date: 2026-10-04, the lite refactor.
- Why: real projects (the source project among them) use the older names. A tool
  upgrade that fails them for a name alone is a check people learn to ignore.
- Measured: this repo's own pre-refactor tree, audited with the new tool, gave two
  advisories and one real gap: its 221-line rules file is over the new 200-line limit.
  Limits are the product (0002 answer 4), so they are not relaxed for old layouts.
- Rule now: `CURRENT_CHECKPOINT.md`'s "Active state" block, "Current implemented
  inventory", "Recent changes", `docs/INTERNALS.md` and `(INTERNALS: ...)` citations
  are read as aliases. Identical copies and a checkpoint brief are advisories.

## Bound the section, not the file
- Date: 2026-09-03, first build.
- Why: an archive below the log, or a long inventory, would trip a whole-file limit on
  a correctly kept changelog and push people to raise the limit.
- Rule now: the log bound is measured from its heading to the next same-level heading.
  A changelog with no log heading is measured whole.

## Templates by nature
- Date: 2026-09-03, found by dogfooding.
- What broke: JumpStarter's own `check` was red forever because the packet and decision
  templates are meant to keep their blanks.
- Rule now: files in `TEMPLATES_BY_NATURE` are exempt from the blanks check. Add any new
  copy-me template to that tuple in the same commit.

## A placeholder name is an identifier
- Date: 2026-09-03, found by dogfooding.
- What broke: prose that described a placeholder was reported as an unfilled one.
  Skipping code spans would also skip real blanks inside commands.
- Rule now: a blank's name matches `[A-Za-z0-9_]+`. Prose writes `{{...}}`. No dotted
  names, which would never be filled or reported.

## Templates stay short enough to read in one sitting
- Date: 2026-09-03; tightened 2026-10-04.
- What broke: three real repos had 1,800 to 4,600-line control files nobody read to the
  end. On 2026-10-04 a fresh `init` still wrote 23 files (about 100 KB) with 85 blanks:
  too much for vibe coding and for small local models.
- Rule now: the lite set stays under 8 KB, `AGENTS.md` under 90 lines, each role file
  under 60. Tests enforce it.

## Native role definitions are adapted, never mechanically converted
- Date: 2026-09-04.
- What broke: a global Claude-to-Codex text swap produced plausible but unsafe Codex
  roles: wrong branch names, ask-first paths that did not exist, no model set.
- Rule now: since 2026-10-04 each role's instructions live once in `docs/agents/`. The
  Claude and Codex files are thin wrappers that only set name, model and effort.

## An unpinned linter is not a gate
- Date: 2026-09-03.
- What broke: "lint clean" turned into 75 findings under a different ruff version on
  the same tree.
- Rule now: `ruff.toml` pins the rules and `target-version = "py39"`, matching the
  Python floor. Fix the code, not the config.

## Codex routing is explicit
- Date: 2026-09-10, packet C2.
- What broke: Codex role files lacked `name` and `description`, so Codex CLI ignored all
  four roles while the tests passed.
- Rule now: every Codex role has non-empty `name`, `description` and
  `developer_instructions` (checked). The lead picks named roles; a host without native
  role selection says so and passes the TOML's model, effort and instructions itself.

## Workspace memory is request-grounded
- Date: 2026-09-11, packet M1.
- Why: the owner asked for a hierarchical Markdown memory and for memory to be searched
  before answering about prior work. A request, not an incident.
- Rule now: see `memory/README.md`. Moved out of the rules file on 2026-10-04 to keep it
  small; the policy is unchanged.
