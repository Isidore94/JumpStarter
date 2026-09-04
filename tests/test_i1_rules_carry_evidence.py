"""Packet I1 — every rule cited in CLAUDE.md carries its INTERNALS entry.

`plan.md` section 5 has said "Every rule in `CLAUDE.md` has an entry in
`docs/INTERNALS.md`" since the first build, and nothing checked it. A rule whose
incident was never written down is a rule the next agent deletes as noise: the
citation looks like evidence, and there is no evidence behind it.

These tests drive the real paths — `jumpstart.main(["check", ...])`,
`jumpstart.main(["retrofit", ...])` and `jumpstart.audit_rule_evidence` — against
repositories built by `init`, not against hand-written dicts.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import jumpstart  # noqa: E402  (path set above)

# --------------------------------------------------------------------------- #
# Helpers and fixtures (copied from tests/test_jumpstart.py — fixtures are not
# shared across files, and a packet's tests live in one readable place)
# --------------------------------------------------------------------------- #

# A citation as `templates/CLAUDE.md` writes it. Used here only to *count* what the
# template shipped, never to decide what the audit should have matched.
CITATION_MARK = '(INTERNALS: "'

# What the template ships, counted by hand on 2026-09-03 against
# `templates/CLAUDE.md`: citations at lines 40, 90, 113 and 144, of which line 90
# sits inside the `<!-- ... -->` example block at lines 88-90. Three are live.
TEMPLATE_CITATIONS_IN_TEXT = 4
TEMPLATE_CITATIONS_LIVE = 3


def run(*argv: str) -> int:
    return jumpstart.main(list(argv))


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "widget"
    target.mkdir()
    return target


@pytest.fixture()
def filled_repo(repo: Path) -> Path:
    """A repo whose control set has no placeholders left - `check` is green on it."""
    run(
        "init",
        str(repo),
        "--name",
        "Widget",
        "--owner",
        "the owner",
        "--test-cmd",
        "pytest -q",
        "--lint-cmd",
        "ruff check .",
        "--run-cmd",
        "python -m widget",
    )
    for path in repo.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        path.write_text(jumpstart.PLACEHOLDER_RE.sub("filled", text), encoding="utf-8")
    settings = repo / ".claude/settings.json"
    settings.write_text(
        jumpstart.PLACEHOLDER_RE.sub("filled", settings.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    run("sync-agents", str(repo))
    return repo


def append(path: Path, text: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def _tracked_tree() -> list[str]:
    """Every path in this checkout that is not git plumbing or a build artefact."""
    skip = (".git/", "__pycache__/", ".pytest_cache/", ".ruff_cache/")
    out = []
    for path in REPO_ROOT.rglob("*"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if any(part in rel + "/" for part in skip):
            continue
        out.append(rel)
    return sorted(out)


# --------------------------------------------------------------------------- #
# (a) the fail-before-fix proof
# --------------------------------------------------------------------------- #


def test_a_cited_rule_with_no_internals_entry_is_a_gap(
    filled_repo: Path, capsys
) -> None:
    """A rule that cites evidence which does not exist must fail the build.

    Citing `*(INTERNALS: "...")*` is a promise that the incident is written down.
    An unkept promise is worse than no citation: the next agent reads the citation,
    does not go looking, and treats the rule as settled.
    """
    assert run("check", str(filled_repo)) == 0, "the fixture must be green to start"
    capsys.readouterr()

    append(
        filled_repo / "CLAUDE.md",
        '\n- **A rule nobody wrote down.** It cites an incident that was never '
        'recorded.\n  *(INTERNALS: "A rule nobody wrote down")*\n',
    )
    assert run("sync-agents", str(filled_repo)) == 0
    capsys.readouterr()

    assert run("check", str(filled_repo)) == 1
    out = capsys.readouterr().out
    assert "rules carry evidence" in out
    assert "A rule nobody wrote down" in out

    findings = jumpstart.audit_rule_evidence(filled_repo)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "rules carry evidence"
    assert finding.status == jumpstart.MISSING
    assert finding.ok is False
    assert "A rule nobody wrote down" in finding.detail
    assert finding.remedy, "a gap without a remedy is a complaint"


# --------------------------------------------------------------------------- #
# (b) the shapes the real files are written in
# --------------------------------------------------------------------------- #


def test_matching_survives_line_wrapping_case_and_html_comments(
    filled_repo: Path,
) -> None:
    """The three shapes this repo's own CLAUDE.md actually contains.

    `CLAUDE.md:122-123` wraps a citation across a line break; `CLAUDE.md:88` cites
    `"unfilled placeholders are visible"` against the heading
    `## Unfilled placeholders are visible`; and `templates/CLAUDE.md:90` puts a
    citation inside an HTML comment as the example shape. A check that misreads any
    of the three fires on correct work, and a check that fires on correct work gets
    ignored - taking the real findings with it.
    """
    claude = filled_repo / "CLAUDE.md"
    internals = filled_repo / "docs/INTERNALS.md"

    shipped = claude.read_text(encoding="utf-8").count(CITATION_MARK)
    assert shipped == TEMPLATE_CITATIONS_IN_TEXT, (
        "premise moved: templates/CLAUDE.md no longer ships "
        f"{TEMPLATE_CITATIONS_IN_TEXT} citations, it ships {shipped}"
    )

    append(
        claude,
        '\n- **Bound the section.** The rule is about a section, not a file.\n'
        '  *(INTERNALS: "Bound the\n  section")*\n'
        '- **Case differs.** The heading is capitalised differently.\n'
        '  *(INTERNALS: "case differs")*\n'
        '- <!-- Example shape, not a rule:\n'
        '  **Not a real rule.** *(INTERNALS: "Not a real rule")* -->\n',
    )
    append(
        internals,
        "\n## Bound The Section (2026-09-03, packet I1)\n\nThe incident.\n"
        "\n## Case Differs (2026-09-03, packet I1)\n\nThe incident.\n"
        "\n### Not a real rule\n\nA sub-heading is not a rule heading.\n",
    )
    assert run("sync-agents", str(filled_repo)) == 0

    findings = jumpstart.audit_rule_evidence(filled_repo)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "rules carry evidence"
    assert finding.status == jumpstart.OK
    assert finding.ok is True

    # Three live template citations plus the two added here. The commented-out one
    # is not a citation, and the `###` sub-heading is not a rule heading.
    expected = TEMPLATE_CITATIONS_LIVE + 2
    assert expected == 5
    assert f"{expected} cited rule(s)" in finding.detail
    assert "Not a real rule" not in finding.detail

    assert run("check", str(filled_repo)) == 0


# --------------------------------------------------------------------------- #
# (c) the two silences
# --------------------------------------------------------------------------- #


def test_no_internals_file_yields_no_finding_and_no_citations_is_not_a_gap(
    filled_repo: Path,
) -> None:
    """`check` must not fire on a repo that has no rulebook yet.

    `retrofit` already reports a missing `docs/INTERNALS.md` as its own gap. If
    `check` reported it a second time, every pre-retrofit repo would be red for a
    reason it has already been told, and `check` would stop being the green-means-go
    gate the three-gate rule relies on.
    """
    internals = filled_repo / "docs/INTERNALS.md"
    saved = internals.read_text(encoding="utf-8")
    internals.unlink()

    assert jumpstart.audit_rule_evidence(filled_repo) == []
    assert run("check", str(filled_repo)) == 0

    internals.write_text(saved, encoding="utf-8")
    claude = filled_repo / "CLAUDE.md"
    stripped = re.sub(
        r'\(INTERNALS:\s*"[^"]*"\)',
        "",
        claude.read_text(encoding="utf-8"),
    )
    assert CITATION_MARK not in stripped
    claude.write_text(stripped, encoding="utf-8")
    assert run("sync-agents", str(filled_repo)) == 0

    findings = jumpstart.audit_rule_evidence(filled_repo)
    assert len(findings) == 1
    assert findings[0].check == "rules carry evidence"
    assert findings[0].status == jumpstart.OK
    assert findings[0].detail == "no INTERNALS citations in CLAUDE.md"
    assert run("check", str(filled_repo)) == 0


# --------------------------------------------------------------------------- #
# (d) retrofit keeps its shape
# --------------------------------------------------------------------------- #


def test_retrofit_carries_one_rules_carry_evidence_finding_and_stays_at_25_checks(
    capsys,
) -> None:
    """The new audit replaces retrofit's presence-only finding; it does not add one.

    Two findings under the same name, or a 26th check, means the audit was bolted on
    beside `audit_structure` instead of into it - and a retrofit report whose count
    moves for no reason is a report nobody reconciles. Read-only: `retrofit` writes
    nothing, ever.
    """
    before = _tracked_tree()

    assert run("retrofit", str(REPO_ROOT)) == 0
    out = capsys.readouterr().out

    lines = [line for line in out.splitlines() if "rules carry evidence" in line]
    assert len(lines) == 1, lines
    assert "[OK      ]" in lines[0]
    assert "No gaps: 25 checks passed." in out

    assert _tracked_tree() == before


# --------------------------------------------------------------------------- #
# (e) added by the builder: the case the packet left open
# --------------------------------------------------------------------------- #


def test_the_same_rule_cited_twice_counts_once(filled_repo: Path) -> None:
    """The detail says "N cited rule(s)", so N counts rules and not citations.

    The packet fixed the wording and not this case. Pinning it means the next change
    to the audit decides on purpose rather than by accident: a rule referred to twice
    in CLAUDE.md is one rule with one incident behind it, and a gap report that named
    it twice would read like two rules were undocumented.
    """
    append(
        filled_repo / "CLAUDE.md",
        '\n- **Said twice.** *(INTERNALS: "Said twice")*\n'
        '- **Said twice, elsewhere.** *(INTERNALS: "said\n  TWICE")*\n',
    )
    assert run("sync-agents", str(filled_repo)) == 0

    findings = jumpstart.audit_rule_evidence(filled_repo)
    assert len(findings) == 1
    assert findings[0].status == jumpstart.MISSING
    assert findings[0].detail == (
        '1 cited rule(s) with no docs/INTERNALS.md entry: "Said twice"'
    )
