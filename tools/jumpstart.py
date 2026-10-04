#!/usr/bin/env python3
"""JumpStarter CLI: set up, audit and enforce a project's AI-agent control files.

Four commands:

    init <path> --name X [--profile lite|team]   copy the templates in, fill what it was told
    retrofit <path>                              audit an existing repo; writes nothing
    sync-agents <path>                           make CLAUDE.md a one-line import of AGENTS.md
    check <path>                                 the same audit, as a gate for CI

Pure standard library, Python 3.9+.

Exit codes: 0 success / no gaps, 1 gaps or failure, 2 usage error.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import re
import sys
from collections.abc import Sequence
from pathlib import Path

# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

#: Each profile is a stack of template folders, applied in order.
PROFILES: dict[str, tuple[str, ...]] = {
    "lite": ("lite",),
    "team": ("lite", "team"),
}

#: Not installed as a file: appended to the repo's .gitignore by the team profile.
GITIGNORE_SNIPPET = "gitignore.snippet"
GITIGNORE_MARKER = "--- JumpStarter ---"

#: Files whose whole purpose is to be copied and filled later. Their ``{{TOKEN}}``s are
#: the product, not an omission, so the placeholder check skips them.
TEMPLATES_BY_NATURE: tuple[str, ...] = (
    "docs/packets/TEMPLATE.md",
    # The older layout's names, so a repo set up before 2026-10-04 is not failed for them.
    "docs/decisions/0000-template.md",
    ".claude/packets/PACKET_TEMPLATE.md",
)

#: Control files from the older layout (CLAUDE.md as the source, a separate checkpoint,
#: wishlist and docs index). Still read by the audit so their placeholders are seen.
LEGACY_FILES: tuple[str, ...] = (
    "CURRENT_CHECKPOINT.md",
    "WISHLIST.md",
    "docs/README.md",
    "docs/INTERNALS.md",
    "docs/CODEX_NOTES.md",
)

ROLES: tuple[str, ...] = ("recon", "tester", "builder", "reviewer")
CLAUDE_AGENTS_DIR = ".claude/agents"
CODEX_AGENTS_DIR = ".codex/agents"
CODEX_CONFIG_FILE = ".codex/config.toml"
TEAM_DOC = "docs/AGENT_TEAM.md"
CODEX_METADATA_FIELDS: tuple[str, ...] = ("name", "description", "developer_instructions")

LESSONS_FILES: tuple[str, ...] = ("docs/LESSONS.md", "docs/INTERNALS.md")

# --------------------------------------------------------------------------- #
# Limits. The reader is an agent on a context budget: a file it cannot finish is a
# file it skims and then appends to.
# --------------------------------------------------------------------------- #

#: AGENTS.md loads into every session of every tool. The lite template is about 75.
AGENTS_MAX_LINES = 200
#: ``## Now`` is the one block every task reads first.
NOW_MAX_LINES = 25
#: plan.md holds only unfinished work; done items move to CHANGELOG.md.
PLAN_MAX_LINES = 400
#: CHANGELOG.md's ``## Log``. The inventory above it is searched, not read.
LOG_MAX_LINES = 400

NOW_HEADING = "Now"
INVENTORY_HEADINGS: tuple[str, ...] = ("What exists", "Current implemented inventory")
LOG_HEADINGS: tuple[str, ...] = ("Log", "Recent changes")
LEGACY_STATE_HEADING = "Active state at a glance"

#: Root-level Markdown that reads like a second ledger. Matched on the stem.
STRAY_LEDGER_WORDS: tuple[str, ...] = (
    "HANDOFF",
    "REVIEW",
    "PROMPT",
    "STATUS",
    "ROADMAP",
    "PROGRESS",
    "BRIEF",
    "NEXT",
    "TODO",
    "NOTES",
    "SUMMARY",
)
KNOWN_ROOT_FILES: frozenset[str] = frozenset(
    {
        "README.MD",
        "AGENTS.MD",
        "CLAUDE.MD",
        "PLAN.MD",
        "CHANGELOG.MD",
        "SETUP.MD",
        "MEMORY.MD",
        "LICENSE.MD",
        "CONTRIBUTING.MD",
        "CODE_OF_CONDUCT.MD",
        "SECURITY.MD",
        "CURRENT_CHECKPOINT.MD",
        "WISHLIST.MD",
    }
)

PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")
IMPORT_LINES: tuple[str, ...] = ("@AGENTS.md", "@./AGENTS.md")
#: The one-line CLAUDE.md that sync-agents writes is the lite template itself.
CLAUDE_STUB_TEMPLATE = "lite/CLAUDE.md"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _read(path: Path) -> str:
    """Read text, tolerating a BOM and any stray bytes rather than crashing."""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _line_count(text: str) -> int:
    return len(text.splitlines()) if text else 0


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _heading(line: str) -> tuple[int, str] | None:
    stripped = line.strip()
    if not stripped.startswith("#"):
        return None
    level = len(stripped) - len(stripped.lstrip("#"))
    return level, stripped[level:].strip()


def _title_matches(title: str, name: str) -> bool:
    """``## Now`` and ``## Now (read first)`` match "Now"; ``## Known issues`` does not."""
    return re.match(rf"{re.escape(name)}\b", title, re.IGNORECASE) is not None


def section_line_count(text: str, *names: str) -> int | None:
    """Lines from the first heading whose title starts with one of ``names`` to the next
    same-or-higher heading. ``None`` when no such heading exists."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        head = _heading(line)
        if head is None or not any(_title_matches(head[1], n) for n in names):
            continue
        for j in range(i + 1, len(lines)):
            nxt = _heading(lines[j])
            if nxt is not None and nxt[0] <= head[0]:
                return j - i
        return len(lines) - i
    return None


def find_placeholders(text: str) -> list[str]:
    """Unfilled ``{{TOKEN}}`` names, in first-seen order, without duplicates."""
    seen: list[str] = []
    for match in PLACEHOLDER_RE.finditer(text):
        if match.group(1) not in seen:
            seen.append(match.group(1))
    return seen


def imports_agents(text: str) -> bool:
    return any(line.strip() in IMPORT_LINES for line in text.splitlines())


def _today() -> str:
    # DTZ011 suppressed deliberately: this stamps a template with the date the human
    # filling it in reads off their own wall clock. A UTC date would be wrong for
    # anyone west of Greenwich after 16:00 local.
    return _dt.date.today().isoformat()  # noqa: DTZ011


def template_files(profile: str) -> list[tuple[Path, str]]:
    """(source, destination) for every file the profile installs, in install order."""
    out: list[tuple[Path, str]] = []
    for layer in PROFILES[profile]:
        root = TEMPLATES_DIR / layer
        for source in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = source.relative_to(root).as_posix()
            if rel != GITIGNORE_SNIPPET:
                out.append((source, rel))
    return out


def control_paths() -> list[str]:
    """Every path any profile installs, plus the older layout's files."""
    paths = {rel for profile in PROFILES for _, rel in template_files(profile)}
    return sorted(paths | set(LEGACY_FILES))


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #

OK = "OK"
ADVISORY = "ADVISORY"
MISSING = "MISSING"
DRIFT = "DRIFT"
OVERSIZE = "OVERSIZE"
UNFILLED = "UNFILLED"


class Finding:
    """One audit result. ``ok`` findings are printed too: a report that only lists
    problems does not say what was checked."""

    def __init__(self, check: str, status: str, detail: str, remedy: str = "") -> None:
        self.check = check
        self.status = status
        self.detail = detail
        self.remedy = remedy

    @property
    def ok(self) -> bool:
        """An advisory is not a gap: something to look at, not something to fail on."""
        return self.status in (OK, ADVISORY)

    def render(self) -> str:
        line = f"  [{self.status:<8}] {self.check}: {self.detail}"
        if self.remedy and self.status != OK:
            line += f"\n             -> {self.remedy}"
        return line


def _print_report(title: str, findings: Sequence[Finding], repo: Path) -> int:
    gaps = [f for f in findings if not f.ok]
    advisories = [f for f in findings if f.status == ADVISORY]
    print(f"{title}: {repo}")
    print("=" * 78)
    if not (repo / "AGENTS.md").is_file() and not (repo / "CLAUDE.md").is_file():
        print("  No agent setup here yet. Run `jumpstart.py init` or follow SETUP.md.")
        print("-" * 78)
    for finding in findings:
        print(finding.render())
    print("-" * 78)
    if gaps:
        print(f"{len(gaps)} gap(s) of {len(findings)} checks.")
    else:
        print(f"No gaps: {len(findings)} checks passed.")
    if advisories:
        print(f"{len(advisories)} advisory(ies) - worth a look, not a failure.")
    return 1 if gaps else 0


# --------------------------------------------------------------------------- #
# Audit (shared by retrofit and check)
# --------------------------------------------------------------------------- #


def _rules_file(repo: Path) -> Path | None:
    """AGENTS.md is the source. A repo on the older layout may only have CLAUDE.md."""
    for name in ("AGENTS.md", "CLAUDE.md"):
        if (repo / name).is_file():
            return repo / name
    return None


def audit_rules_files(repo: Path) -> list[Finding]:
    agents = repo / "AGENTS.md"
    claude = repo / "CLAUDE.md"
    if not agents.is_file() and not claude.is_file():
        return [
            Finding(
                "rules file",
                MISSING,
                "no AGENTS.md and no CLAUDE.md",
                "Run `jumpstart.py init <path> --name <Name>`.",
            )
        ]
    if not agents.is_file():
        return [
            Finding(
                "rules file",
                MISSING,
                "rules are only in CLAUDE.md; Codex and other tools read AGENTS.md",
                "Run `jumpstart.py sync-agents <path>`: it moves them to AGENTS.md and "
                "leaves CLAUDE.md as a one-line import.",
            )
        ]

    findings = [Finding("rules file", OK, "AGENTS.md present")]
    if not claude.is_file():
        findings.append(
            Finding(
                "CLAUDE.md imports AGENTS.md",
                MISSING,
                "no CLAUDE.md, so Claude Code will not load the rules",
                "Run `jumpstart.py sync-agents <path>` to write the one-line import.",
            )
        )
    elif imports_agents(_read(claude)):
        findings.append(Finding("CLAUDE.md imports AGENTS.md", OK, "one source of rules"))
    elif sha256_of(claude) == sha256_of(agents):
        findings.append(
            Finding(
                "CLAUDE.md imports AGENTS.md",
                ADVISORY,
                "CLAUDE.md and AGENTS.md are identical copies (the older layout)",
                "This works. To keep one copy, run `jumpstart.py sync-agents <path>`.",
            )
        )
    else:
        findings.append(
            Finding(
                "CLAUDE.md imports AGENTS.md",
                DRIFT,
                "CLAUDE.md and AGENTS.md differ, so Claude and Codex follow different rules",
                "Merge CLAUDE.md's rules into AGENTS.md by hand (the difference usually "
                "holds real rules), then run `jumpstart.py sync-agents <path>`.",
            )
        )
    return findings


def audit_sizes(repo: Path) -> list[Finding]:
    findings: list[Finding] = []

    rules = _rules_file(repo)
    if rules is not None:
        lines = _line_count(_read(rules))
        if lines > AGENTS_MAX_LINES:
            findings.append(
                Finding(
                    f"{rules.name} size",
                    OVERSIZE,
                    f"{lines} lines (limit {AGENTS_MAX_LINES})",
                    "It loads into every session. Keep one line per rule and move the "
                    "story behind each into docs/LESSONS.md.",
                )
            )
        else:
            findings.append(
                Finding(f"{rules.name} size", OK, f"{lines} lines (limit {AGENTS_MAX_LINES})")
            )

    plan = repo / "plan.md"
    if not plan.is_file():
        findings.append(
            Finding("plan", MISSING, "plan.md not found", "Add it from templates/lite/plan.md.")
        )
    else:
        text = _read(plan)
        lines = _line_count(text)
        if lines > PLAN_MAX_LINES:
            findings.append(
                Finding(
                    "plan size",
                    OVERSIZE,
                    f"plan.md is {lines} lines (limit {PLAN_MAX_LINES})",
                    "Only unfinished work belongs in plan.md. Move done items to "
                    "CHANGELOG.md and old detail to docs/archive/.",
                )
            )
        else:
            findings.append(Finding("plan size", OK, f"{lines} lines (limit {PLAN_MAX_LINES})"))
        findings.append(_audit_now(repo, text))

    changelog = repo / "CHANGELOG.md"
    if not changelog.is_file():
        findings.append(
            Finding(
                "changelog",
                MISSING,
                "CHANGELOG.md not found",
                "Add it from templates/lite/CHANGELOG.md.",
            )
        )
        return findings

    text = _read(changelog)
    if section_line_count(text, *INVENTORY_HEADINGS) is None:
        findings.append(
            Finding(
                "what exists",
                MISSING,
                "no '## What exists' section in CHANGELOG.md",
                "List one line per thing that works today. Agents search it before "
                "building so they never rebuild it.",
            )
        )
    else:
        findings.append(Finding("what exists", OK, "present in CHANGELOG.md"))

    log = section_line_count(text, *LOG_HEADINGS)
    if log is None:
        whole = _line_count(text)
        over = f"; the whole file is {whole} lines" if whole > LOG_MAX_LINES else ""
        findings.append(
            Finding(
                "changelog log",
                MISSING,
                f"no '## Log' section in CHANGELOG.md{over}",
                "Split it: '## What exists' at the top, then a bounded '## Log'. Move "
                "old entries to docs/archive/.",
            )
        )
    elif log > LOG_MAX_LINES:
        findings.append(
            Finding(
                "changelog log",
                OVERSIZE,
                f"'## Log' is {log} lines (limit {LOG_MAX_LINES})",
                "Move older entries to docs/archive/CHANGELOG_<period>.md and leave a "
                "pointer.",
            )
        )
    else:
        findings.append(Finding("changelog log", OK, f"{log} lines (limit {LOG_MAX_LINES})"))
    return findings


def _audit_now(repo: Path, plan_text: str) -> Finding:
    now = section_line_count(plan_text, NOW_HEADING)
    if now is not None:
        if now > NOW_MAX_LINES:
            return Finding(
                "## Now",
                OVERSIZE,
                f"{now} lines (limit {NOW_MAX_LINES})",
                "Every task reads it first. Keep: working on, last test result, next "
                "step, waiting on. Move history to CHANGELOG.md.",
            )
        return Finding("## Now", OK, f"{now} lines in plan.md (limit {NOW_MAX_LINES})")

    checkpoint = repo / "CURRENT_CHECKPOINT.md"
    if checkpoint.is_file() and section_line_count(_read(checkpoint), LEGACY_STATE_HEADING):
        return Finding(
            "## Now",
            ADVISORY,
            f"the brief is '{LEGACY_STATE_HEADING}' in CURRENT_CHECKPOINT.md (older layout)",
            "This works. To slim down, move it to '## Now' in plan.md and archive the "
            "rest of the checkpoint under docs/archive/.",
        )
    return Finding(
        "## Now",
        MISSING,
        "no '## Now' section in plan.md",
        "Add a short block: working on, last test result, next step, waiting on.",
    )


def audit_goals(repo: Path) -> Finding:
    decisions = repo / "docs/decisions"
    goals = sorted(decisions.glob("*goals*.md")) if decisions.is_dir() else []
    if goals:
        return Finding("owner goals", OK, f"docs/decisions/{goals[0].name}")
    return Finding(
        "owner goals",
        MISSING,
        "no docs/decisions/*goals*.md",
        "Ask the five questions in templates/lite/docs/decisions/0001-goals.md, one at a "
        "time, and record the answers word for word.",
    )


# A citation as AGENTS.md writes it: (LESSONS: "the rule name"). The older layout wrote
# (INTERNALS: "..."). The name may wrap across a line break.
CITATION_RE = re.compile(r'\((?:LESSONS|INTERNALS):\s*"([^"]*)"\s*\)')
# An example citation inside an HTML comment is documentation, not a citation.
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# A rule heading is exactly two hashes; `###` is a sub-heading, not a rule.
RULE_HEADING_RE = re.compile(r"^## +(.+?)\s*$", re.MULTILINE)
# Older entries are suffixed with `(date, what prompted it)`.
TRAILING_PARENTHETICAL_RE = re.compile(r"\s*\([^()]*\)\s*$")


def _rule_key(name: str) -> str:
    return " ".join(name.split()).lower()


def audit_lessons(repo: Path) -> Finding:
    """Every rule that cites a lesson must have that lesson written down. A citation
    is a promise that the incident is recorded; an unkept one reads as settled."""
    present = [repo / rel for rel in LESSONS_FILES if (repo / rel).is_file()]
    if not present:
        return Finding(
            "lessons",
            MISSING,
            "no docs/LESSONS.md",
            "Add it from templates/lite/docs/LESSONS.md.",
        )

    rules = _rules_file(repo)
    cited: list[str] = []
    if rules is not None:
        seen: set[str] = set()
        text = HTML_COMMENT_RE.sub("", _read(rules))
        for match in CITATION_RE.finditer(text):
            name = " ".join(match.group(1).split())
            if _rule_key(name) not in seen:
                seen.add(_rule_key(name))
                cited.append(name)

    documented = {
        _rule_key(TRAILING_PARENTHETICAL_RE.sub("", heading))
        for path in present
        for heading in RULE_HEADING_RE.findall(_read(path))
    }
    unmatched = [name for name in cited if _rule_key(name) not in documented]
    shown = ", ".join(p.relative_to(repo).as_posix() for p in present)
    if not unmatched:
        return Finding("lessons", OK, f"{len(cited)} cited rule(s), all recorded in {shown}")
    listed = ", ".join(f'"{name}"' for name in unmatched)
    return Finding(
        "lessons",
        MISSING,
        f"{len(unmatched)} cited rule(s) with no entry in {shown}: {listed}",
        "Add a '## <name>' entry with what broke and why, or fix the citation. If the "
        "cause cannot be recovered, write 'cause not found'. Never invent one.",
    )


def audit_placeholders(repo: Path) -> list[Finding]:
    findings: list[Finding] = []
    for rel in control_paths():
        if rel in TEMPLATES_BY_NATURE or not (repo / rel).is_file():
            continue
        names = find_placeholders(_read(repo / rel))
        if names:
            shown = ", ".join(names[:6]) + (f", +{len(names) - 6} more" if len(names) > 6 else "")
            findings.append(
                Finding(
                    f"blanks in {rel}",
                    UNFILLED,
                    f"{len(names)} unfilled: {shown}",
                    "Fill them, or delete the line they are in. A half-written control "
                    "file is one an agent will act on.",
                )
            )
    return findings or [Finding("blanks", OK, "no unfilled {{TOKEN}} in the control files")]


def _native_metadata_present(text: str, field: str) -> bool:
    """Check the literal string forms JumpStarter ships, not all TOML. Python 3.9 has
    no TOML parser; unfamiliar TOML becomes a visible gap rather than a guess."""
    scalar = re.compile(
        rf"^\s*{re.escape(field)}\s*=\s*(?:\"([^\"\r\n]*)\"|'([^'\r\n]*)')\s*(?:#.*)?$"
    )
    multiline_start = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(\"\"\"|''')\s*$")
    inside: str | None = None
    value: list[str] = []
    target = False
    for raw in text.splitlines():
        if inside is not None:
            if raw.strip() == inside:
                if target:
                    return bool("\n".join(value).strip())
                inside, target, value = None, False, []
                continue
            if target:
                value.append(raw)
            continue
        match = multiline_start.fullmatch(raw)
        if match:
            inside, target = match.group(2), match.group(1) == field
            continue
        match = scalar.fullmatch(raw)
        if match:
            return bool((match.group(1) or match.group(2) or "").strip())
    return False


def team_present(repo: Path) -> bool:
    return any(
        (repo / rel).exists() for rel in (TEAM_DOC, CLAUDE_AGENTS_DIR, CODEX_AGENTS_DIR)
    )


def audit_team(repo: Path) -> list[Finding]:
    """Only for a repo that uses helper agents. A lite repo has nothing to check here."""
    if not team_present(repo):
        return []
    findings: list[Finding] = []
    native = [
        (CLAUDE_AGENTS_DIR, ".md", "Claude helper agents"),
        (CODEX_AGENTS_DIR, ".toml", "Codex helper agents"),
    ]
    in_use = [(d, ext, label) for d, ext, label in native if (repo / d).is_dir()]
    if not in_use:
        findings.append(
            Finding(
                "helper agents",
                MISSING,
                f"{TEAM_DOC} exists but neither {CLAUDE_AGENTS_DIR}/ nor {CODEX_AGENTS_DIR}/",
                "Run `jumpstart.py init <path> --name <Name> --profile team`, or delete "
                f"{TEAM_DOC} if this project does not use helper agents.",
            )
        )

    for directory, ext, label in in_use:
        missing = [r for r in ROLES if not (repo / directory / f"{r}{ext}").is_file()]
        if missing:
            findings.append(
                Finding(
                    label,
                    MISSING,
                    f"{directory}/ lacks {', '.join(missing)}",
                    "Copy the missing role from templates/team/ and fill its blanks.",
                )
            )
        else:
            findings.append(Finding(label, OK, f"{len(ROLES)} roles in {directory}/"))

        # A thin wrapper that points at a shared role file is only as good as the file.
        dangling = [
            f"docs/agents/{r}.md"
            for r in ROLES
            if (repo / directory / f"{r}{ext}").is_file()
            and f"docs/agents/{r}.md" in _read(repo / directory / f"{r}{ext}")
            and not (repo / f"docs/agents/{r}.md").is_file()
        ]
        if dangling:
            findings.append(
                Finding(
                    f"{label} instructions",
                    MISSING,
                    f"wrappers point at missing {', '.join(dangling)}",
                    "Copy them from templates/team/docs/agents/.",
                )
            )

    if (repo / CODEX_AGENTS_DIR).is_dir():
        if (repo / CODEX_CONFIG_FILE).is_file():
            findings.append(Finding("Codex config", OK, f"{CODEX_CONFIG_FILE} present"))
        else:
            findings.append(
                Finding(
                    "Codex config",
                    MISSING,
                    f"{CODEX_CONFIG_FILE} not found",
                    "Add it from templates/team/.codex/config.toml and choose the lead "
                    "and helper models.",
                )
            )
        for role in ROLES:
            path = repo / CODEX_AGENTS_DIR / f"{role}.toml"
            if not path.is_file():
                continue
            text = _read(path)
            lacking = [f for f in CODEX_METADATA_FIELDS if not _native_metadata_present(text, f)]
            if lacking:
                findings.append(
                    Finding(
                        f"Codex role {role}",
                        MISSING,
                        f"{path.relative_to(repo).as_posix()} lacks {', '.join(lacking)}",
                        "Codex needs non-empty name, description and "
                        "developer_instructions in every role file.",
                    )
                )
    return findings


def audit_stray_ledgers(repo: Path) -> list[Finding]:
    """Root Markdown that reads like a second status file. A heuristic on file names,
    so an advisory that names each file, never a gap."""
    stray = [
        (path.name, _line_count(_read(path)))
        for path in sorted(repo.glob("*.md"))
        if path.name.upper() not in KNOWN_ROOT_FILES
        and any(word in path.stem.upper() for word in STRAY_LEDGER_WORDS)
    ]
    if not stray:
        return [Finding("extra status files", OK, "none at the repo root")]
    listed = ", ".join(f"{name} ({lines} lines)" for name, lines in stray)
    return [
        Finding(
            "extra status files",
            ADVISORY,
            f"{len(stray)} root file(s) reading like a second status file: {listed}",
            "Fold what is still true into plan.md or CHANGELOG.md, move the rest to "
            "docs/archive/, and delete nothing until it has been read.",
        )
    ]


def audit(repo: Path) -> list[Finding]:
    findings = audit_rules_files(repo)
    findings.extend(audit_sizes(repo))
    findings.append(audit_goals(repo))
    findings.append(audit_lessons(repo))
    findings.extend(audit_placeholders(repo))
    findings.extend(audit_team(repo))
    findings.extend(audit_stray_ledgers(repo))
    return findings


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def _substitutions(args: argparse.Namespace) -> dict[str, str]:
    subs = {
        "PROJECT": args.name,
        "OWNER": args.owner,
        "MAIN_BRANCH": args.main_branch,
        "BRANCH_PREFIX": args.branch_prefix,
        "DATE": _today(),
    }
    for key, value in (
        ("ONE_LINE_DESCRIPTION", args.description),
        ("STACK", args.stack),
        ("TEST_CMD", args.test_cmd),
        ("LINT_CMD", args.lint_cmd),
        ("RUN_CMD", args.run_cmd),
        ("CODEX_LEAD_MODEL", args.codex_lead_model),
        ("CODEX_STRONG_MODEL", args.codex_strong_model),
        ("CODEX_CHEAP_MODEL", args.codex_cheap_model),
    ):
        if value:
            subs[key] = value
    return subs


def fill(text: str, subs: dict[str, str]) -> str:
    """Replace known ``{{TOKEN}}``s. Unknown ones stay in place on purpose: `check`
    reports them, so a half-written control set cannot quietly ship."""
    return PLACEHOLDER_RE.sub(lambda m: subs.get(m.group(1), m.group(0)), text)


def _require_dir(path: str) -> Path | None:
    repo = Path(path).resolve()
    if not repo.is_dir():
        print(f"error: {repo} is not a directory", file=sys.stderr)
        return None
    return repo


def cmd_init(args: argparse.Namespace) -> int:
    repo = _require_dir(args.path)
    if repo is None:
        return 2
    if not TEMPLATES_DIR.is_dir():
        print(f"error: templates not found at {TEMPLATES_DIR}", file=sys.stderr)
        return 2

    subs = _substitutions(args)
    written: list[str] = []
    skipped: list[tuple[str, str]] = []
    exists = "exists; --force to overwrite"

    # A repo whose rules live only in CLAUDE.md: writing a template AGENTS.md beside it
    # would split the rules in two. Move them first with sync-agents.
    claude = repo / "CLAUDE.md"
    legacy_rules = (
        claude.is_file()
        and not (repo / "AGENTS.md").exists()
        and not imports_agents(_read(claude))
        and not args.force
    )

    for source, rel in template_files(args.profile):
        dest = repo / rel
        if legacy_rules and rel in ("AGENTS.md", "CLAUDE.md"):
            skipped.append((rel, "CLAUDE.md holds your rules; run sync-agents first"))
            continue
        if dest.exists() and not args.force:
            skipped.append((rel, exists))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(fill(_read(source), subs), encoding="utf-8")
        written.append(rel)

    if args.profile == "team" and _append_gitignore(repo):
        written.append(".gitignore (appended)")

    print(f"Set up {args.name} ({args.profile}) in {repo}")
    print("-" * 78)
    for rel in written:
        print(f"  wrote    {rel}")
    for rel, why in skipped:
        print(f"  skipped  {rel} ({why})")
    print("-" * 78)

    remaining = sorted(
        {
            name
            for _, rel in template_files(args.profile)
            if rel not in TEMPLATES_BY_NATURE and (repo / rel).is_file()
            for name in find_placeholders(_read(repo / rel))
        }
    )
    if remaining:
        print(f"Blanks left to fill ({len(remaining)}): {', '.join(remaining)}")
    print(f"Next: fill the blanks (SETUP.md step 4), then `jumpstart.py check {repo}`.")
    return 0


def _append_gitignore(repo: Path) -> bool:
    snippet = _read(TEMPLATES_DIR / "team" / GITIGNORE_SNIPPET)
    gitignore = repo / ".gitignore"
    if not gitignore.is_file():
        gitignore.write_text(snippet, encoding="utf-8")
        return True
    existing = _read(gitignore)
    if GITIGNORE_MARKER in existing:
        return False
    separator = "" if existing.endswith("\n") else "\n"
    gitignore.write_text(existing + separator + "\n" + snippet, encoding="utf-8")
    return True


def cmd_retrofit(args: argparse.Namespace) -> int:
    repo = _require_dir(args.path)
    if repo is None:
        return 2
    status = _print_report("JumpStarter audit", audit(repo), repo)
    print()
    print("This audit changed nothing. Next: SETUP.md, 'Existing repo'.")
    return status


def cmd_sync_agents(args: argparse.Namespace) -> int:
    """Make AGENTS.md the one source and CLAUDE.md a one-line import of it."""
    repo = _require_dir(args.path)
    if repo is None:
        return 2
    claude = repo / "CLAUDE.md"
    agents = repo / "AGENTS.md"

    if claude.is_file() and imports_agents(_read(claude)):
        if not agents.is_file():
            print("error: CLAUDE.md imports AGENTS.md, which does not exist", file=sys.stderr)
            return 1
        print("Already in sync: CLAUDE.md imports AGENTS.md.")
        return 0
    if not claude.is_file() and not agents.is_file():
        print("error: neither CLAUDE.md nor AGENTS.md exists; run init", file=sys.stderr)
        return 1
    if claude.is_file() and agents.is_file() and sha256_of(claude) != sha256_of(agents):
        print(
            "error: CLAUDE.md and AGENTS.md differ. Merge CLAUDE.md's rules into "
            "AGENTS.md by hand, then run sync-agents again.",
            file=sys.stderr,
        )
        return 1
    if claude.is_file() and not agents.is_file():
        agents.write_bytes(claude.read_bytes())
        print("moved    CLAUDE.md rules -> AGENTS.md")
    claude.write_text(_read(TEMPLATES_DIR / CLAUDE_STUB_TEMPLATE), encoding="utf-8")
    print("wrote    CLAUDE.md (one-line import of AGENTS.md)")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    repo = _require_dir(args.path)
    if repo is None:
        return 2
    return _print_report("JumpStarter check", audit(repo), repo)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jumpstart",
        description="Set up, audit and enforce a project's AI-agent control files.",
    )
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="copy the templates into a repo and fill the blanks")
    init.add_argument("path")
    init.add_argument("--name", required=True, help="the project name")
    init.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default="lite",
        help="lite (default): rules, plan, changelog. team: adds helper agents",
    )
    init.add_argument("--description", default=None, help="one line: what the project is")
    init.add_argument("--owner", default="the owner", help="how the docs address the owner")
    init.add_argument("--stack", default=None, help="languages and main libraries")
    init.add_argument("--test-cmd", default=None, help="the command that runs the tests")
    init.add_argument("--lint-cmd", default=None, help="the command that runs the linter")
    init.add_argument("--run-cmd", default=None, help="the command that runs the project")
    init.add_argument("--main-branch", default="main")
    init.add_argument("--branch-prefix", default="agent/", help="branch prefix for helpers")
    init.add_argument("--codex-lead-model", default=None, help="Codex model for the lead")
    init.add_argument(
        "--codex-strong-model", default=None, help="Codex model for tester, builder, reviewer"
    )
    init.add_argument("--codex-cheap-model", default=None, help="Codex model for recon")
    init.add_argument("--force", action="store_true", help="overwrite existing files")
    init.set_defaults(func=cmd_init)

    retrofit = sub.add_parser("retrofit", help="audit an existing repo; writes nothing")
    retrofit.add_argument("path")
    retrofit.set_defaults(func=cmd_retrofit)

    sync = sub.add_parser("sync-agents", help="make CLAUDE.md a one-line import of AGENTS.md")
    sync.add_argument("path")
    sync.set_defaults(func=cmd_sync_agents)

    check = sub.add_parser("check", help="the audit as a gate: exit 1 on any gap")
    check.add_argument("path")
    check.set_defaults(func=cmd_check)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # The printed strings are ASCII on purpose; this makes a stray character degrade
    # rather than raise UnicodeEncodeError on a console in a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:  # pragma: no cover - depends on the console
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):
                pass

    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
