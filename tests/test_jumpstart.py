"""Tests for the JumpStarter CLI.

Each test states what would break in a real project if the behaviour regressed —
these are the guarantees the playbooks rely on.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import jumpstart  # noqa: E402  (path set above)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def run(*argv: str) -> int:
    return jumpstart.main(list(argv))


def init_repo(path: Path, **extra: str) -> int:
    argv = ["init", str(path), "--name", "Widget", "--owner", "the owner"]
    for key, value in extra.items():
        argv += ["--" + key.replace("_", "-"), value]
    return run(*argv)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "widget"
    target.mkdir()
    return target


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #


def test_init_produces_the_whole_control_set(repo: Path) -> None:
    assert init_repo(repo) == 0

    for rel in (
        "CLAUDE.md",
        "AGENTS.md",
        "plan.md",
        "CURRENT_CHECKPOINT.md",
        "CHANGELOG.md",
        "WISHLIST.md",
        "docs/README.md",
        "docs/INTERNALS.md",
        "docs/AGENT_TEAM.md",
        "docs/CODEX_NOTES.md",
        "docs/decisions/0000-template.md",
        "docs/decisions/0001-owner-goals-and-priorities.md",
        ".claude/agents/tester.md",
        ".claude/agents/builder.md",
        ".claude/agents/reviewer.md",
        ".claude/agents/recon.md",
        ".claude/settings.json",
        ".claude/packets/PACKET_TEMPLATE.md",
        ".gitignore",
    ):
        assert (repo / rel).is_file(), f"init did not write {rel}"


def test_init_fills_the_placeholders_it_was_given(repo: Path) -> None:
    init_repo(repo, test_cmd="pytest -q", lint_cmd="ruff check .")
    claude = (repo / "CLAUDE.md").read_text(encoding="utf-8")

    assert "Widget" in claude
    assert "{{PROJECT}}" not in claude
    assert "pytest -q" in claude
    assert "{{TEST_CMD}}" not in claude


def test_init_leaves_unsupplied_placeholders_for_check_to_catch(repo: Path) -> None:
    """A half-written control set must not ship quietly: what init was not told stays
    a visible token, and `check` reports it."""
    init_repo(repo)  # no --test-cmd

    assert "{{TEST_CMD}}" in (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert run("check", str(repo)) == 1


def test_init_generates_agents_as_a_byte_identical_copy(repo: Path) -> None:
    init_repo(repo, test_cmd="pytest -q")
    assert sha256(repo / "CLAUDE.md") == sha256(repo / "AGENTS.md")


def test_init_writes_the_gitignore_rules_in_the_order_that_works(repo: Path) -> None:
    init_repo(repo)
    text = (repo / ".gitignore").read_text(encoding="utf-8")

    assert "/.claude/*" in text
    assert "!/.claude/agents/" in text
    # The un-ignore has no effect unless it comes after the ignore line.
    assert text.index("/.claude/*") < text.index("!/.claude/agents/")


def test_init_appends_to_an_existing_gitignore_without_losing_it(repo: Path) -> None:
    (repo / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
    init_repo(repo)
    text = (repo / ".gitignore").read_text(encoding="utf-8")

    assert text.startswith("*.pyc")
    assert "/.claude/*" in text


def test_init_is_idempotent_on_the_gitignore_block(repo: Path) -> None:
    init_repo(repo)
    init_repo(repo)
    text = (repo / ".gitignore").read_text(encoding="utf-8")

    assert text.count(jumpstart.GITIGNORE_MARKER) == 1


def test_init_refuses_to_overwrite_without_force(repo: Path) -> None:
    (repo / "CLAUDE.md").write_text("the project's own rules\n", encoding="utf-8")
    init_repo(repo)

    assert (repo / "CLAUDE.md").read_text(encoding="utf-8") == "the project's own rules\n"


def test_init_force_overwrites(repo: Path) -> None:
    (repo / "CLAUDE.md").write_text("stale\n", encoding="utf-8")
    argv = ["init", str(repo), "--name", "Widget", "--force"]
    assert run(*argv) == 0

    assert "Widget" in (repo / "CLAUDE.md").read_text(encoding="utf-8")


def test_init_on_a_missing_directory_is_a_usage_error(tmp_path: Path) -> None:
    assert init_repo(tmp_path / "nope") == 2


# --------------------------------------------------------------------------- #
# retrofit
# --------------------------------------------------------------------------- #


@pytest.fixture()
def bare_repo(tmp_path: Path) -> Path:
    """A repo that grew without a control set: code, a README, nothing else."""
    target = tmp_path / "legacy"
    (target / "src").mkdir(parents=True)
    (target / "src" / "app.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    (target / "README.md").write_text("# legacy\n\nIt does things.\n", encoding="utf-8")
    (target / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    return target


def test_retrofit_reports_the_gaps_on_a_bare_repo(bare_repo: Path, capsys) -> None:
    assert run("retrofit", str(bare_repo)) == 1
    out = capsys.readouterr().out

    for expected in (
        "control file CLAUDE.md",
        "control file AGENTS.md",
        "control file plan.md",
        "control file CURRENT_CHECKPOINT.md",
        "control file CHANGELOG.md",
        "control file WISHLIST.md",
        "active state block",
        "implemented inventory",
        "rules carry evidence",
        "docs classified",
        "owner goals record",
        "agent builder",
        "agent reviewer",
        "agent recon",
        "command allow-list",
        "gitignore rules",
    ):
        assert expected in out, f"retrofit did not report {expected}"
    assert "MISSING" in out


def test_retrofit_writes_nothing(bare_repo: Path) -> None:
    before = sorted(p.relative_to(bare_repo).as_posix() for p in bare_repo.rglob("*"))
    run("retrofit", str(bare_repo))
    after = sorted(p.relative_to(bare_repo).as_posix() for p in bare_repo.rglob("*"))

    assert before == after


def test_retrofit_is_clean_after_a_filled_init(repo: Path) -> None:
    init_repo(repo, test_cmd="pytest -q", lint_cmd="ruff check .", run_cmd="python -m widget")
    assert run("retrofit", str(repo)) == 0


def test_retrofit_reports_drift_between_claude_and_agents(repo: Path) -> None:
    init_repo(repo, test_cmd="pytest -q")
    (repo / "AGENTS.md").write_text("a rule only Codex sees\n", encoding="utf-8")

    assert run("retrofit", str(repo)) == 1


# --------------------------------------------------------------------------- #
# sync-agents
# --------------------------------------------------------------------------- #


def test_sync_agents_makes_them_identical(repo: Path) -> None:
    init_repo(repo, test_cmd="pytest -q")
    (repo / "CLAUDE.md").write_text("# Widget\n\nA new rule.\n", encoding="utf-8")
    assert sha256(repo / "CLAUDE.md") != sha256(repo / "AGENTS.md")

    assert run("sync-agents", str(repo)) == 0
    assert sha256(repo / "CLAUDE.md") == sha256(repo / "AGENTS.md")


def test_sync_agents_creates_agents_when_it_is_absent(repo: Path) -> None:
    init_repo(repo, test_cmd="pytest -q")
    (repo / "AGENTS.md").unlink()

    assert run("sync-agents", str(repo)) == 0
    assert (repo / "AGENTS.md").is_file()


def test_sync_agents_fails_without_claude(repo: Path) -> None:
    assert run("sync-agents", str(repo)) == 1


def test_sync_agents_reports_the_hash(repo: Path, capsys) -> None:
    init_repo(repo, test_cmd="pytest -q")
    run("sync-agents", str(repo))
    out = capsys.readouterr().out

    assert sha256(repo / "CLAUDE.md") in out


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #


@pytest.fixture()
def filled_repo(repo: Path) -> Path:
    """A repo whose control set has no placeholders left — `check` is green on it."""
    init_repo(
        repo,
        test_cmd="pytest -q",
        lint_cmd="ruff check .",
        run_cmd="python -m widget",
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


def test_check_is_green_on_a_filled_repo(filled_repo: Path) -> None:
    assert run("check", str(filled_repo)) == 0


def test_check_fails_on_an_oversized_checkpoint(filled_repo: Path) -> None:
    checkpoint = filled_repo / "CURRENT_CHECKPOINT.md"
    checkpoint.write_text(
        checkpoint.read_text(encoding="utf-8")
        + "\n".join(f"- entry {i}" for i in range(jumpstart.CHECKPOINT_MAX_LINES + 50)),
        encoding="utf-8",
    )

    assert run("check", str(filled_repo)) == 1


def test_check_names_the_oversized_file_and_the_remedy(filled_repo: Path, capsys) -> None:
    checkpoint = filled_repo / "CURRENT_CHECKPOINT.md"
    checkpoint.write_text("x\n" * (jumpstart.CHECKPOINT_MAX_LINES + 1), encoding="utf-8")
    run("check", str(filled_repo))
    out = capsys.readouterr().out

    assert "OVERSIZE" in out
    assert f"CURRENT_CHECKPOINT.md is {jumpstart.CHECKPOINT_MAX_LINES + 1} lines" in out
    assert "Archive, do not delete" in out


def test_check_fails_on_an_oversized_changelog_recent_section(filled_repo: Path) -> None:
    changelog = filled_repo / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    padding = "\n".join(f"- change {i}" for i in range(jumpstart.CHANGELOG_RECENT_MAX_LINES + 20))
    text = text.replace(
        "## Recent changes",
        "## Recent changes\n\n" + padding,
        1,
    )
    changelog.write_text(text, encoding="utf-8")

    assert run("check", str(filled_repo)) == 1


def test_check_measures_the_recent_section_not_the_whole_changelog(filled_repo: Path) -> None:
    """The archive lives in the same file until it is moved out; a long archive
    section must not fail the bounded recent-changes rule."""
    changelog = filled_repo / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    text += "\n" + "\n".join(f"- old entry {i}" for i in range(2000))
    changelog.write_text(text, encoding="utf-8")

    assert run("check", str(filled_repo)) == 0


def test_check_fails_on_drift_between_claude_and_agents(filled_repo: Path, capsys) -> None:
    (filled_repo / "AGENTS.md").write_text("only Codex sees this\n", encoding="utf-8")

    assert run("check", str(filled_repo)) == 1
    assert "DRIFT" in capsys.readouterr().out


def test_check_fails_when_agents_is_missing(filled_repo: Path) -> None:
    (filled_repo / "AGENTS.md").unlink()

    assert run("check", str(filled_repo)) == 1


def test_check_fails_on_an_oversized_claude(filled_repo: Path) -> None:
    claude = filled_repo / "CLAUDE.md"
    claude.write_text("rule\n" * (jumpstart.CLAUDE_MAX_LINES + 1), encoding="utf-8")
    run("sync-agents", str(filled_repo))

    assert run("check", str(filled_repo)) == 1


# --------------------------------------------------------------------------- #
# Units behind the checks
# --------------------------------------------------------------------------- #


def test_section_line_count_stops_at_the_next_same_level_heading() -> None:
    text = "# Title\n\n## Recent changes\n\na\nb\n\n## Archived\n\nc\nd\ne\n"
    assert jumpstart.section_line_count(text, "Recent changes") == 5


def test_section_line_count_runs_to_the_end_when_it_is_the_last_section() -> None:
    text = "# Title\n\n## Recent changes\n\na\nb\n"
    assert jumpstart.section_line_count(text, "Recent changes") == 4


def test_section_line_count_ignores_a_deeper_heading_inside_the_section() -> None:
    text = "# T\n\n## Recent changes\n\n### 2026-01-01\n\na\n\n## Next\n\nb\n"
    assert jumpstart.section_line_count(text, "Recent changes") == 6


def test_section_line_count_is_none_when_the_heading_is_absent() -> None:
    assert jumpstart.section_line_count("# Title\n\nbody\n", "Recent changes") is None


def test_find_placeholders_is_deduplicated_and_ordered() -> None:
    found = jumpstart.find_placeholders("{{B}} {{A}} {{B}}")
    assert found == ["B", "A"]


def test_fill_leaves_unknown_tokens_in_place() -> None:
    assert jumpstart.fill("{{A}} {{B}}", {"A": "x"}) == "x {{B}}"


def test_no_subcommand_is_a_usage_error() -> None:
    assert jumpstart.main([]) == 2


# --------------------------------------------------------------------------- #
# The templates themselves
# --------------------------------------------------------------------------- #


def test_the_shipped_templates_keep_claude_and_agents_identical() -> None:
    assert sha256(REPO_ROOT / "templates/CLAUDE.md") == sha256(REPO_ROOT / "templates/AGENTS.md")


def test_every_installed_template_exists() -> None:
    for template_rel in jumpstart.INSTALL_MAP:
        assert (REPO_ROOT / "templates" / template_rel).is_file(), template_rel


def test_jumpstarter_passes_its_own_check() -> None:
    """Eat the dog food: this repo runs its own control set."""
    assert run("check", str(REPO_ROOT)) == 0


def test_a_placeholder_name_is_an_identifier() -> None:
    """Prose about placeholders writes {{...}}, which must not read as one — a check
    that fires on correct documentation is a check that gets ignored."""
    assert jumpstart.find_placeholders("write it as {{...}} in prose") == []
    assert jumpstart.find_placeholders("but {{TEST_CMD}} is one") == ["TEST_CMD"]


def test_no_template_uses_a_dotted_placeholder_name() -> None:
    """A dotted name would not match PLACEHOLDER_RE, so it would never be filled and
    never be reported — it would just sit in the installed file forever."""
    dotted = re.compile(r"\{\{[A-Za-z0-9_]*\.[^}]*\}\}")
    for path in sorted((REPO_ROOT / "templates").rglob("*")):
        if path.is_file():
            assert not dotted.search(path.read_text(encoding="utf-8")), path


def test_the_team_has_a_tester_that_is_not_the_builder() -> None:
    """The tests are written by an agent that will not write the fix.

    One review round found four tests that could not fail, all written by the agent
    that had written the fix. `tester` is the cure, so it must be installed and it
    must be forbidden to write the fix.
    """
    assert ".claude/agents/tester.md" in jumpstart.AGENT_FILES
    tester = (jumpstart.TEMPLATES_DIR / ".claude/agents/tester.md").read_text(
        encoding="utf-8"
    )
    assert "You never write the fix" in tester
    builder = " ".join(
        (jumpstart.TEMPLATES_DIR / ".claude/agents/builder.md")
        .read_text(encoding="utf-8")
        .split()
    )
    assert "may not weaken, skip, delete or rewrite a tester's assertion" in builder


def test_no_agent_template_tells_an_agent_to_stash() -> None:
    """A stash on a shared checkout takes the other session's in-flight work with it.

    Three collisions in one afternoon produced this rule; the builder template used to
    say "stash or restore", which is the wrong half of the choice.
    """
    for rel in jumpstart.AGENT_FILES:
        text = (jumpstart.TEMPLATES_DIR / rel).read_text(encoding="utf-8")
        for line in text.splitlines():
            if "git stash" in line or "stash the" in line:
                assert "Never" in line or "never" in line, (
                    f"{rel} tells an agent to stash: {line!r}"
                )
