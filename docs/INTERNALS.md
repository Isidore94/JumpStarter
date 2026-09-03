# JumpStarter internals — the incident behind every rule

Document role: **active reference.** Verbatim source text for the `Core rules` in
[`CLAUDE.md`](../CLAUDE.md).

**`CLAUDE.md` keeps the rule; this file keeps the reason.** The rules are binding from
`CLAUDE.md` alone. **A rule with no entry here is a draft.**

If you change a rule, change it in both places, in the same commit.

The sixteen principles these rules serve, with the incidents behind them, are in
[`PRINCIPLES.md`](../PRINCIPLES.md). This file holds the incidents specific to
JumpStarter's own code.

---

## retrofit is report-only (2026-09-03, first build)

**The rule:** `retrofit` writes nothing, ever. It audits and prints.

**Why.** A retrofit lands in a repo with history, habits and an owner who did not ask for
their docs to be rearranged. The first version of this tool was going to add the missing
files directly. The failure mode is not subtle: an agent runs it, twelve files appear,
the owner cannot tell what was theirs and what was generated, and the whole change gets
reverted — including the parts that were right.

Reporting first also makes the tool honest about its own accuracy. The audit will have
false positives (a repo with an active-state block under a different name, an inventory
inside a differently-titled section). A report is a conversation; a write is a defect.

**Deliberately NOT done.** No `--fix`, no `--write`, no `doctor` subcommand. It is a hard
invariant in `plan.md` section 5, and `WISHLIST.md` records the auto-fix idea as
`PERMANENT_NO` so it is not rediscovered as an obvious improvement.

**Reopen trigger.** Never, for `retrofit`. A separate command with a different name and
an explicit confirmation could exist; it would not be this one.

---

## init does not overwrite (2026-09-03, first build)

**The rule:** `init` skips any file that already exists unless `--force`, and prints what
it skipped.

**Why.** The most likely `init` mistake is running it in a repo that already has a
`CLAUDE.md` — which is precisely the case where that file is the project's real rules and
the template is worth nothing. Silently overwriting it destroys the thing the tool exists
to protect.

Printing the skips matters as much as the skipping: an agent that does not see "skipped
CLAUDE.md" will assume the template landed and will look for placeholders that are not
there.

**Reopen trigger.** If `--force` turns out to be used routinely, the default is wrong and
the two paths should be separate commands.

---

## Unfilled placeholders are visible (2026-09-03, first build)

**The rule:** `fill()` replaces only the tokens it was given a value for. Unknown
`{{...}}` placeholders are left in place, and `check` reports them as `UNFILLED`.

**Why.** The alternative is filling a placeholder with a plausible default — "run the
tests", `main`, "the owner". A control file with a plausible-looking wrong command is
worse than one with an obvious hole, because an agent will act on it: it will run the
wrong test command, record a baseline that means nothing, and the checkpoint will carry a
number that was never measured.

A visible, unfilled test-command placeholder is unmissable. An invented `pytest` is not.

**What this costs.** `init` alone never produces a `check`-green repo, which is
deliberate: `check` green means a human answered the questions.

**Reopen trigger.** None expected. If defaults are ever added they must be flagged in the
file itself, not silently substituted.

---

## One source for two tools (2026-09-03, first build)

**The rule:** `AGENTS.md` is generated from `CLAUDE.md` by `sync-agents` and verified by
sha256. Never hand-edited.

**Why.** Two files that say almost the same thing drift, and the drift is invisible until
two agents disagree about a rule. The failure is not that one file is stale — it is that
each tool is confidently following different instructions, and neither can see the other
file.

Symlinks were rejected: they do not survive every checkout, notably on Windows.

The sha256 check is what makes it enforceable. Comparing content "semantically" would let
a whitespace-only edit through, and a whitespace-only edit is how a hand-edit starts.

**Deliberately NOT done.** No Codex-specific variant of the rules. If Codex ever needs a
rule Claude Code does not, it goes in `docs/CODEX_NOTES.md`, which is a separate document
about the tool — not a second copy of the rules.

**Reopen trigger.** If a tool appears that cannot read a file at the repo root, this
becomes three files and the sync grows a target list.

---

## Bound the section, not the file (2026-09-03, first build)

**The rule:** where the rule is about a section, the check measures the section.
`CHANGELOG.md`'s 800-line limit applies to "Recent changes", found by
`section_line_count`, which runs from the heading to the next same-or-higher heading.

**Why.** The archive of old entries lives in the same file until someone moves it out, and
often the inventory at the top is long by design. Measuring the whole file would fire on
a correctly-maintained changelog and would push people to raise the limit — the exact
wrong response, since the limit exists so that the *mandatory read* stays bounded, and
the mandatory read is the inventory and the recent section, not the archive.

`test_check_measures_the_recent_section_not_the_whole_changelog` pins this: 2000 lines
appended after the section must not fail the check.

**Reopen trigger.** If a project's inventory itself grows past a readable size, that needs
its own limit — a different rule, not a wider version of this one.

---

## Templates by nature (2026-09-03, first build)

**The rule:** `docs/decisions/0000-template.md` and `.claude/packets/PACKET_TEMPLATE.md`
keep their placeholders and are exempt from the placeholder check
(`TEMPLATES_BY_NATURE`).

**Why.** These two files are installed into a project *in order to be copied and filled
in later*. Their placeholders are the product. Without the exemption, `check` is red in
every correctly-set-up project forever, and a check that is always red is a check that
gets ignored — taking the real findings with it.

Found by dogfooding: JumpStarter's own `check` was red for exactly this reason on the
first run.

**Reopen trigger.** Any new template installed to be copied later must be added to the
tuple in the same commit.

---

## A placeholder name is an identifier (2026-09-03, first build)

**The rule:** `PLACEHOLDER_RE` matches a double-braced name of `[A-Za-z0-9_]+` — letters,
digits and underscores only. Documentation that talks *about* placeholders writes them
with an ellipsis inside the braces, or names them without braces at all; neither is a
match.

**Why.** Found by dogfooding. This repo's own `CLAUDE.md` describes the rule "unfilled
placeholders are left in place" and, in doing so, wrote a token-shaped example in prose.
`check` reported it as an unfilled placeholder in a file that was completely filled in.
This entry did it again, in the paragraph you are reading, and had to be rewritten.

A check that fires on correct documentation is a check that gets ignored, and it takes
the real findings with it.

**Why not skip code spans instead.** The obvious fix — ignore a token inside backticks —
is wrong here: real placeholders appear inside backticks in the templates too, because
that is where a command or a path goes. Excluding code spans would miss them. So the rule
went the other way: the *names* are constrained, and the prose forms fall outside.

Two template tokens carried a dot in their names and were renamed in the same commit; a
dotted name would never have been filled and never reported, so it would have sat in the
installed file forever. `test_no_template_uses_a_dotted_placeholder_name` pins that.

**Reopen trigger.** If a template ever genuinely needs a dotted or hyphenated placeholder
name, this constraint and the prose convention have to change together.

---

## An advisory is not a gap (2026-09-03, second pass)

**The rule, as it appears in `CLAUDE.md`:** *An `ADVISORY` is reported and is not a gap.*

**What happened.** `retrofit` ran against three real repositories for the first time. Two
of its findings were wrong in a specific and expensive way: they were **literally true
and practically false**.

1. `command allow-list: .claude/settings.json not found`. That file is machine-local by
   design — `.gitignore` keeps `.claude/` out of the repository — so it cannot be in a
   checkout, ever. The finding first appeared against a clone of the source project on
   2026-09-03, and then against **this repository itself**.
2. `active state block: no 'Active state at a glance' block`, against a repo that keeps
   exactly that block under the heading `## Active item`, complete with a measured gate
   stamp. The report read as "this repo has no idea where it is". It knew perfectly well.

**What was measured.** Three audits, 22 checks each. On the source project's working copy
the three gaps found were all real and all size violations (4,587/1,500; 1,549/800;
418/400). The false positives were the two above.

**What is deliberately NOT done, and why.** Neither check was dropped. A project with no
allow-list at all is a real finding, and a project with no active-state block anywhere is
the finding this whole tool exists to make. What changed is the *status*: `ADVISORY` is
printed with its own remedy, `Finding.ok` is true for it, and the exit code does not
move. The report prints a count of advisories separately, so they are visible without
failing CI.

The third advisory, stray root ledgers, is an advisory for a different reason: it matches
on words in a filename, which is a heuristic, and a repo is allowed its own names.

The principle underneath all three: **a check that fires on correct work is a check that
gets ignored, and it takes the real findings with it.** That is also why
`TEMPLATES_BY_NATURE` and the identifier-only placeholder rule exist — same lesson,
third and fourth time.

**Reopen trigger.** If an advisory is ever the thing that should have blocked a merge,
it was the wrong status; promote it and say what it missed.

---

## An unpinned linter is not a gate (2026-09-03, second pass)

**The rule, as it appears in `CLAUDE.md`:** *The rules and the target version are pinned
in `ruff.toml`; an unpinned linter is not a gate, and `target-version` must match the
floor `README.md` declares.*

**What happened.** `CURRENT_CHECKPOINT.md` recorded the lint baseline as
`ruff check .` → "All checks passed, exit 0", measured hours earlier. Re-run on the same
tree with ruff 0.16.6 it reported **75 findings**. Nothing in the code had changed. There
was no ruff configuration in the repository at all, so "clean" meant whatever rule set
the installed ruff defaulted to that day.

**What was measured.** 75 findings: 46 UP032, 17 UP006, 4 UP035, 2 UP045, 2 FURB105, and
one each of UP037, RUF100, I001 and DTZ011. All 74 style findings were fixed in the code;
DTZ011 is suppressed with its reason beside it.

**The trap inside the fix.** UP006 rewrites `List[str]` to `list[str]`, which is not
legal at runtime on the 3.9 floor this project declares — *unless*
`from __future__ import annotations` is present, which it is (`tools/jumpstart.py:17`).
So `target-version = "py39"` is in `ruff.toml` beside the rule selection: a linter told
to assume a newer Python will suggest code the declared floor cannot run. Change the
floor and that line changes with it, or the gate quietly starts lying in the other
direction.

**What is deliberately NOT done, and why.** The findings were not configured away. The
rule is fix the code, not the config; pinning the version and the rule list is not a
suppression, it is a statement of what the gate *is*.

**Reopen trigger.** A ruff release that changes the meaning of a selected rule set, or a
change to the Python floor.
