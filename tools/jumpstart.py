#!/usr/bin/env python3
"""JumpStarter CLI: bootstrap, audit and enforce a project's agent control set.

Four commands:

    init <path> --name X    copy the templates in and fill the placeholders
    retrofit <path>         audit an existing repo and print a gap report (writes nothing)
    sync-agents <path>      copy CLAUDE.md to AGENTS.md and verify sha256 equality
    check <path>            enforce the size limits, CLAUDE == AGENTS, and no unfilled
                            placeholders

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

#: template path (relative to templates/) -> destination path (relative to the repo).
INSTALL_MAP: dict[str, str] = {
    "CLAUDE.md": "CLAUDE.md",
    "plan.md": "plan.md",
    "CURRENT_CHECKPOINT.md": "CURRENT_CHECKPOINT.md",
    "CHANGELOG.md": "CHANGELOG.md",
    "WISHLIST.md": "WISHLIST.md",
    "docs/README.md": "docs/README.md",
    "docs/INTERNALS.md": "docs/INTERNALS.md",
    "docs/AGENT_TEAM.md": "docs/AGENT_TEAM.md",
    "docs/decisions/0000-template.md": "docs/decisions/0000-template.md",
    "docs/decisions/0001-owner-goals-and-priorities.md": (
        "docs/decisions/0001-owner-goals-and-priorities.md"
    ),
    "codex/CODEX_NOTES.md": "docs/CODEX_NOTES.md",
    ".claude/agents/builder.md": ".claude/agents/builder.md",
    ".claude/agents/reviewer.md": ".claude/agents/reviewer.md",
    ".claude/agents/recon.md": ".claude/agents/recon.md",
    ".claude/settings.json": ".claude/settings.json",
    ".claude/packets/PACKET_TEMPLATE.md": ".claude/packets/PACKET_TEMPLATE.md",
}

#: Files whose whole purpose is to be copied and filled in later. Their
#: ``{{TOKEN}}``s are the product, not an omission, so the placeholder check skips them.
TEMPLATES_BY_NATURE: tuple[str, ...] = (
    "docs/decisions/0000-template.md",
    ".claude/packets/PACKET_TEMPLATE.md",
)

GITIGNORE_SNIPPET = "templates/.gitignore.snippet"
GITIGNORE_MARKER = "--- JumpStarter: agent control files ---"

CONTROL_FILES: tuple[str, ...] = (
    "CLAUDE.md",
    "AGENTS.md",
    "plan.md",
    "CURRENT_CHECKPOINT.md",
    "CHANGELOG.md",
    "WISHLIST.md",
    "docs/README.md",
)

AGENT_FILES: tuple[str, ...] = (
    ".claude/agents/builder.md",
    ".claude/agents/reviewer.md",
    ".claude/agents/recon.md",
)

# --------------------------------------------------------------------------- #
# Limits. Principle 1: docs must be readable in bounded time.
# --------------------------------------------------------------------------- #

CHECKPOINT_MAX_LINES = 1500
CHANGELOG_RECENT_MAX_LINES = 800
CLAUDE_MAX_LINES = 400

#: The markers that carry meaning, and the check that reports each as missing.
ACTIVE_STATE_MARKER = "Active state at a glance"
INVENTORY_MARKER = "Current implemented inventory"
RECENT_CHANGES_MARKER = "Recent changes"

PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _read(path: Path) -> str:
    """Read text, tolerating a BOM and any stray bytes rather than crashing."""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _line_count(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _has_marker(text: str, marker: str) -> bool:
    return marker.lower() in text.lower()


def section_line_count(text: str, heading_marker: str) -> int | None:
    """Lines from the heading containing ``heading_marker`` to the next same-or-higher
    heading. ``None`` when no such heading exists."""
    lines = text.splitlines()
    start = None
    start_level = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        if heading_marker.lower() in stripped.lower():
            start = i
            start_level = level
            break
    if start is None:
        return None
    for j in range(start + 1, len(lines)):
        stripped = lines[j].strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        if level <= start_level:
            return j - start
    return len(lines) - start


def find_placeholders(text: str) -> list[str]:
    """Unfilled ``{{TOKEN}}`` names, in first-seen order, without duplicates."""
    seen: list[str] = []
    for match in PLACEHOLDER_RE.finditer(text):
        name = match.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def _today() -> str:
    # DTZ011 suppressed deliberately: this stamps a template with the date the human
    # filling it in reads off their own wall clock. A UTC date would be wrong for
    # anyone west of Greenwich after 16:00 local.
    return _dt.date.today().isoformat()  # noqa: DTZ011


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #

OK = "OK"
MISSING = "MISSING"
DRIFT = "DRIFT"
OVERSIZE = "OVERSIZE"
UNFILLED = "UNFILLED"


class Finding:
    """One audit result. ``ok`` findings are printed too: a report that only lists
    problems does not tell you what was checked."""

    def __init__(self, check: str, status: str, detail: str, remedy: str = "") -> None:
        self.check = check
        self.status = status
        self.detail = detail
        self.remedy = remedy

    @property
    def ok(self) -> bool:
        return self.status == OK

    def render(self) -> str:
        line = f"  [{self.status:<8}] {self.check}: {self.detail}"
        if self.remedy and not self.ok:
            line += f"\n             -> {self.remedy}"
        return line


def _print_report(title: str, findings: Sequence[Finding], repo: Path) -> int:
    gaps = [f for f in findings if not f.ok]
    print(f"{title}: {repo}")
    print("=" * 78)
    for finding in findings:
        print(finding.render())
    print("-" * 78)
    if gaps:
        print(f"{len(gaps)} gap(s) of {len(findings)} checks.")
    else:
        print(f"No gaps: {len(findings)} checks passed.")
    return 1 if gaps else 0


# --------------------------------------------------------------------------- #
# Audit (shared by retrofit and check)
# --------------------------------------------------------------------------- #


def audit_sizes(repo: Path) -> list[Finding]:
    findings: list[Finding] = []

    checkpoint = repo / "CURRENT_CHECKPOINT.md"
    if checkpoint.is_file():
        lines = _line_count(_read(checkpoint))
        if lines > CHECKPOINT_MAX_LINES:
            findings.append(
                Finding(
                    "checkpoint size",
                    OVERSIZE,
                    f"CURRENT_CHECKPOINT.md is {lines} lines (limit {CHECKPOINT_MAX_LINES})",
                    "Move the entries older than the oldest open gate into "
                    "docs/CHECKPOINT_ARCHIVE_<period>.md and leave a pointer. "
                    "Archive, do not delete.",
                )
            )
        else:
            findings.append(
                Finding(
                    "checkpoint size",
                    OK,
                    f"{lines} lines (limit {CHECKPOINT_MAX_LINES})",
                )
            )
    else:
        findings.append(
            Finding(
                "checkpoint size",
                MISSING,
                "CURRENT_CHECKPOINT.md not found",
                "Add it from templates/CURRENT_CHECKPOINT.md.",
            )
        )

    changelog = repo / "CHANGELOG.md"
    if changelog.is_file():
        text = _read(changelog)
        recent = section_line_count(text, RECENT_CHANGES_MARKER)
        if recent is None:
            findings.append(
                Finding(
                    "changelog recent section",
                    MISSING,
                    f"no '{RECENT_CHANGES_MARKER}' heading in CHANGELOG.md",
                    "Split the file: a searchable inventory at the top, a bounded "
                    "'Recent changes' section, and a dated archive under docs/.",
                )
            )
        elif recent > CHANGELOG_RECENT_MAX_LINES:
            findings.append(
                Finding(
                    "changelog recent section",
                    OVERSIZE,
                    f"'{RECENT_CHANGES_MARKER}' is {recent} lines (limit {CHANGELOG_RECENT_MAX_LINES})",
                    "Move the older entries into docs/CHANGELOG_ARCHIVE_<period>.md "
                    "and leave a pointer.",
                )
            )
        else:
            findings.append(
                Finding(
                    "changelog recent section",
                    OK,
                    f"{recent} lines (limit {CHANGELOG_RECENT_MAX_LINES})",
                )
            )
    else:
        findings.append(
            Finding(
                "changelog recent section",
                MISSING,
                "CHANGELOG.md not found",
                "Add it from templates/CHANGELOG.md.",
            )
        )

    claude = repo / "CLAUDE.md"
    if claude.is_file():
        lines = _line_count(_read(claude))
        if lines > CLAUDE_MAX_LINES:
            findings.append(
                Finding(
                    "CLAUDE.md size",
                    OVERSIZE,
                    f"{lines} lines (limit {CLAUDE_MAX_LINES})",
                    "CLAUDE.md loads into every session. Keep the rules here and move "
                    "the incident behind each into docs/INTERNALS.md.",
                )
            )
        else:
            findings.append(
                Finding(
                    "CLAUDE.md size", OK, f"{lines} lines (limit {CLAUDE_MAX_LINES})"
                )
            )
    else:
        findings.append(
            Finding(
                "CLAUDE.md size",
                MISSING,
                "CLAUDE.md not found",
                "Add it from templates/CLAUDE.md.",
            )
        )

    return findings


def audit_agents_identical(repo: Path) -> Finding:
    claude = repo / "CLAUDE.md"
    agents = repo / "AGENTS.md"
    if not claude.is_file() and not agents.is_file():
        return Finding(
            "CLAUDE == AGENTS",
            MISSING,
            "neither CLAUDE.md nor AGENTS.md exists",
            "Run `jumpstart.py init` for a new project, or add both.",
        )
    if not claude.is_file():
        return Finding(
            "CLAUDE == AGENTS",
            MISSING,
            "AGENTS.md exists but CLAUDE.md does not",
            "CLAUDE.md is the source. Copy AGENTS.md to CLAUDE.md, then "
            "`jumpstart.py sync-agents`.",
        )
    if not agents.is_file():
        return Finding(
            "CLAUDE == AGENTS",
            MISSING,
            "CLAUDE.md exists but AGENTS.md does not",
            "Run `jumpstart.py sync-agents <path>` — Codex reads AGENTS.md.",
        )
    if sha256_of(claude) != sha256_of(agents):
        return Finding(
            "CLAUDE == AGENTS",
            DRIFT,
            f"sha256 differs: {sha256_of(claude)[:12]}... vs {sha256_of(agents)[:12]}...",
            "The two tools are running on different rules. Merge by hand into "
            "CLAUDE.md (the divergence usually holds real rules), then "
            "`jumpstart.py sync-agents <path>`.",
        )
    return Finding("CLAUDE == AGENTS", OK, f"byte-identical ({sha256_of(claude)[:12]}...)")


def audit_placeholders(repo: Path) -> list[Finding]:
    findings: list[Finding] = []
    for rel in [*list(INSTALL_MAP.values()), "AGENTS.md"]:
        if rel in TEMPLATES_BY_NATURE:
            continue
        path = repo / rel
        if not path.is_file():
            continue
        names = find_placeholders(_read(path))
        if names:
            shown = ", ".join(names[:6])
            if len(names) > 6:
                shown += f", +{len(names) - 6} more"
            findings.append(
                Finding(
                    f"placeholders in {rel}",
                    UNFILLED,
                    f"{len(names)} unfilled: {shown}",
                    "Fill them, or delete the block they are in. A half-written "
                    "control file is one an agent will act on.",
                )
            )
    if not findings:
        findings.append(Finding("placeholders", OK, "no unfilled {{TOKEN}} in the control set"))
    return findings


def audit_structure(repo: Path) -> list[Finding]:
    """The full standard. Used by ``retrofit``."""
    findings: list[Finding] = []

    for rel in CONTROL_FILES:
        path = repo / rel
        if path.is_file():
            findings.append(Finding(f"control file {rel}", OK, "present"))
        else:
            findings.append(
                Finding(
                    f"control file {rel}",
                    MISSING,
                    "not found",
                    "Add it from templates/{}. Do not delete whatever the repo uses "
                    "today — point it at the new file.".format(
                        "CLAUDE.md" if rel == "AGENTS.md" else rel
                    ),
                )
            )

    findings.append(audit_agents_identical(repo))

    claude = repo / "CLAUDE.md"
    if claude.is_file():
        text = _read(claude)
        if _has_marker(text, ACTIVE_STATE_MARKER) or _has_marker(text, "Read narrow"):
            findings.append(
                Finding("bounded read", OK, "CLAUDE.md names a block to read, not whole files")
            )
        else:
            findings.append(
                Finding(
                    "bounded read",
                    MISSING,
                    "CLAUDE.md does not name a bounded block to read",
                    "An unbounded 'read these files' instruction stops being "
                    "followable as they grow. Name the block.",
                )
            )
    else:
        findings.append(
            Finding("bounded read", MISSING, "no CLAUDE.md", "Add it from templates/CLAUDE.md.")
        )

    checkpoint = repo / "CURRENT_CHECKPOINT.md"
    if checkpoint.is_file() and _has_marker(_read(checkpoint), ACTIVE_STATE_MARKER):
        findings.append(Finding("active state block", OK, "present in CURRENT_CHECKPOINT.md"))
    else:
        findings.append(
            Finding(
                "active state block",
                MISSING,
                f"no '{ACTIVE_STATE_MARKER}' block",
                "Add it at the top of the file the repo already uses for current "
                "state, with numbers you measure now — including a red suite if the "
                "suite is red.",
            )
        )

    changelog = repo / "CHANGELOG.md"
    if changelog.is_file() and _has_marker(_read(changelog), INVENTORY_MARKER):
        findings.append(Finding("implemented inventory", OK, "present in CHANGELOG.md"))
    else:
        findings.append(
            Finding(
                "implemented inventory",
                MISSING,
                f"no '{INVENTORY_MARKER}' section",
                "Extract one entry per capability that exists today, by area, from "
                "the existing docs. It is the contract to search before building.",
            )
        )

    internals = repo / "docs/INTERNALS.md"
    if internals.is_file():
        findings.append(Finding("rules carry evidence", OK, "docs/INTERNALS.md present"))
    else:
        alt = [p for p in (repo / "docs").glob("*INTERNALS*.md")] if (repo / "docs").is_dir() else []
        if alt:
            findings.append(
                Finding("rules carry evidence", OK, f"found {alt[0].name}")
            )
        else:
            findings.append(
                Finding(
                    "rules carry evidence",
                    MISSING,
                    "no docs/INTERNALS.md",
                    "A rule without the incident behind it gets 'fixed' by the next "
                    "agent. Where the incident cannot be recovered, write 'Evidence "
                    "not recovered' — never invent one.",
                )
            )

    docs_readme = repo / "docs/README.md"
    if docs_readme.is_file():
        findings.append(Finding("docs classified", OK, "docs/README.md present"))
    else:
        findings.append(
            Finding(
                "docs classified",
                MISSING,
                "no docs/README.md",
                "Classify every Markdown file as active runbook / reference / "
                "decision record / historical evidence.",
            )
        )

    decisions = repo / "docs/decisions"
    goals = list(decisions.glob("*owner-goals*.md")) + list(decisions.glob("*priorities*.md")) \
        if decisions.is_dir() else []
    if goals:
        findings.append(Finding("owner goals record", OK, f"found {goals[0].name}"))
    else:
        findings.append(
            Finding(
                "owner goals record",
                MISSING,
                "no owner-goals decision record under docs/decisions/",
                "Ask the questionnaire in templates/docs/decisions/"
                "0001-owner-goals-and-priorities.md one question at a time and "
                "record the answers verbatim.",
            )
        )

    for rel in AGENT_FILES:
        if (repo / rel).is_file():
            findings.append(Finding(f"agent {Path(rel).stem}", OK, "present"))
        else:
            findings.append(
                Finding(
                    f"agent {Path(rel).stem}",
                    MISSING,
                    f"{rel} not found",
                    f"Copy templates/{rel} and fill its placeholders.",
                )
            )

    if (repo / ".claude/settings.json").is_file():
        findings.append(Finding("command allow-list", OK, ".claude/settings.json present"))
    else:
        findings.append(
            Finding(
                "command allow-list",
                MISSING,
                ".claude/settings.json not found",
                "Copy templates/.claude/settings.json. Keep it narrow: an entry "
                "covering 'git *' covers 'git reset --hard'.",
            )
        )

    gitignore = repo / ".gitignore"
    if gitignore.is_file():
        text = _read(gitignore)
        has_ignore = ".claude/*" in text
        has_unignore = "!.claude/agents/" in text or "!/.claude/agents/" in text
        if has_ignore and has_unignore:
            findings.append(
                Finding("gitignore rules", OK, ".claude/* ignored, .claude/agents/ tracked")
            )
        else:
            findings.append(
                Finding(
                    "gitignore rules",
                    MISSING,
                    "missing {}{}".format(
                        "the .claude/* ignore " if not has_ignore else "",
                        "the !.claude/agents/ un-ignore" if not has_unignore else "",
                    ).strip(),
                    "Append templates/.gitignore.snippet. The un-ignore must come "
                    "after the ignore line or it has no effect.",
                )
            )
    else:
        findings.append(
            Finding(
                "gitignore rules",
                MISSING,
                "no .gitignore",
                "Create one from templates/.gitignore.snippet.",
            )
        )

    findings.extend(audit_sizes(repo))
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
        ("TEST_CMD", args.test_cmd),
        ("LINT_CMD", args.lint_cmd),
        ("RUN_CMD", args.run_cmd),
    ):
        if value:
            subs[key] = value
    return subs


def fill(text: str, subs: dict[str, str]) -> str:
    """Replace known ``{{TOKEN}}``s. Unknown ones are left in place on purpose: `check`
    reports them, so a half-written control set cannot quietly ship."""

    def _sub(match: re.Match[str]) -> str:
        return subs.get(match.group(1), match.group(0))

    return PLACEHOLDER_RE.sub(_sub, text)


def cmd_init(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    if not repo.is_dir():
        print(f"error: {repo} is not a directory", file=sys.stderr)
        return 2
    if not TEMPLATES_DIR.is_dir():
        print(f"error: templates not found at {TEMPLATES_DIR}", file=sys.stderr)
        return 2

    subs = _substitutions(args)
    written: list[str] = []
    skipped: list[str] = []

    for template_rel, dest_rel in sorted(INSTALL_MAP.items()):
        source = TEMPLATES_DIR / template_rel
        if not source.is_file():
            print(f"error: missing template {source}", file=sys.stderr)
            return 2
        dest = repo / dest_rel
        if dest.exists() and not args.force:
            skipped.append(dest_rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(fill(_read(source), subs), encoding="utf-8")
        written.append(dest_rel)

    # AGENTS.md is generated, never copied: one source, one sync.
    claude = repo / "CLAUDE.md"
    agents = repo / "AGENTS.md"
    if claude.is_file() and (not agents.exists() or args.force or "CLAUDE.md" in written):
        agents.write_bytes(claude.read_bytes())
        written.append("AGENTS.md")
    elif agents.exists():
        skipped.append("AGENTS.md")

    gitignore_written = _append_gitignore(repo)
    if gitignore_written:
        written.append(".gitignore (appended)")
    else:
        skipped.append(".gitignore (JumpStarter block already present)")

    print(f"Initialised {args.name} in {repo}")
    print("-" * 78)
    for rel in written:
        print(f"  wrote    {rel}")
    for rel in skipped:
        print(f"  skipped  {rel} (exists; --force to overwrite)")
    print("-" * 78)

    remaining = sorted(
        {
            name
            for rel in INSTALL_MAP.values()
            if rel not in TEMPLATES_BY_NATURE and (repo / rel).is_file()
            for name in find_placeholders(_read(repo / rel))
        }
    )
    if remaining:
        print(f"Unfilled placeholders, to complete by hand ({len(remaining)}):")
        print("  " + ", ".join(remaining))
        print()
    print("Next: playbooks/new-project.md — the owner questionnaire comes first,")
    print(f"then fill the placeholders, then `jumpstart.py check {repo}`.")
    return 0


def _append_gitignore(repo: Path) -> bool:
    snippet_path = TEMPLATES_DIR.parent / GITIGNORE_SNIPPET
    if not snippet_path.is_file():
        return False
    snippet = _read(snippet_path)
    gitignore = repo / ".gitignore"
    if gitignore.is_file():
        existing = _read(gitignore)
        if GITIGNORE_MARKER in existing:
            return False
        separator = "" if existing.endswith("\n") else "\n"
        gitignore.write_text(existing + separator + "\n" + snippet, encoding="utf-8")
    else:
        gitignore.write_text(snippet, encoding="utf-8")
    return True


def cmd_retrofit(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    if not repo.is_dir():
        print(f"error: {repo} is not a directory", file=sys.stderr)
        return 2
    findings = audit_structure(repo)
    status = _print_report("JumpStarter retrofit audit", findings, repo)
    print()
    print("This audit changed nothing. Next: playbooks/retrofit.md.")
    print("Archive, do not delete. Never rewrite history.")
    return status


def cmd_sync_agents(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    claude = repo / "CLAUDE.md"
    agents = repo / "AGENTS.md"
    if not claude.is_file():
        print(f"error: {claude} not found", file=sys.stderr)
        return 1
    agents.write_bytes(claude.read_bytes())
    claude_hash = sha256_of(claude)
    agents_hash = sha256_of(agents)
    if claude_hash != agents_hash:  # pragma: no cover - a filesystem that lied to us
        print(
            f"error: copy did not verify: {claude_hash} != {agents_hash}",
            file=sys.stderr,
        )
        return 1
    print("CLAUDE.md -> AGENTS.md")
    print(f"sha256 {claude_hash} (identical)")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    if not repo.is_dir():
        print(f"error: {repo} is not a directory", file=sys.stderr)
        return 2
    findings: list[Finding] = [audit_agents_identical(repo)]
    findings.extend(audit_sizes(repo))
    findings.extend(audit_placeholders(repo))
    return _print_report("JumpStarter check", findings, repo)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jumpstart",
        description="Bootstrap, audit and enforce a project's agent control set.",
    )
    sub = parser.add_subparsers(dest="command")

    init = sub.add_parser("init", help="copy the templates into a repo and fill placeholders")
    init.add_argument("path")
    init.add_argument("--name", required=True, help="the project name")
    init.add_argument("--owner", default="the owner", help="how the docs address the owner")
    init.add_argument("--test-cmd", default=None, help="the command that runs the tests")
    init.add_argument("--lint-cmd", default=None, help="the command that runs the linter")
    init.add_argument("--run-cmd", default=None, help="the command that runs the project")
    init.add_argument("--main-branch", default="main")
    init.add_argument("--branch-prefix", default="claude/")
    init.add_argument("--force", action="store_true", help="overwrite existing files")
    init.set_defaults(func=cmd_init)

    retrofit = sub.add_parser("retrofit", help="audit an existing repo; writes nothing")
    retrofit.add_argument("path")
    retrofit.set_defaults(func=cmd_retrofit)

    sync = sub.add_parser("sync-agents", help="copy CLAUDE.md to AGENTS.md and verify sha256")
    sync.add_argument("path")
    sync.set_defaults(func=cmd_sync_agents)

    check = sub.add_parser("check", help="enforce size limits, CLAUDE == AGENTS, placeholders")
    check.add_argument("path")
    check.set_defaults(func=cmd_check)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
