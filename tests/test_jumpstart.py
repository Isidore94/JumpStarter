"""Tests for the JumpStarter CLI and the templates it ships.

Each test says what would break in a real project if the behaviour regressed.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = REPO_ROOT / "templates"
sys.path.insert(0, str(REPO_ROOT / "tools"))

import jumpstart  # noqa: E402  (path set above)

LITE_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "plan.md",
    "CHANGELOG.md",
    "docs/decisions/0001-goals.md",
    "docs/LESSONS.md",
}

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def run(*argv: str) -> int:
    return jumpstart.main(list(argv))


def init_repo(path: Path, profile: str = "lite", **extra: str) -> int:
    argv = ["init", str(path), "--name", "Widget", "--profile", profile]
    for key, value in extra.items():
        argv += ["--" + key.replace("_", "-"), value]
    return run(*argv)


FILLED = {
    "description": "a small widget service",
    "stack": "Python 3.12",
    "test_cmd": "pytest -q",
    "lint_cmd": "ruff check .",
    "run_cmd": "python -m widget",
    "codex_lead_model": "lead-model",
    "codex_strong_model": "strong-model",
    "codex_cheap_model": "cheap-model",
}


def fill_by_hand(repo: Path) -> None:
    """What the agent does in SETUP.md step 4: answer every remaining blank."""
    for path in repo.rglob("*"):
        if path.is_file() and path.relative_to(repo).as_posix() not in (
            jumpstart.TEMPLATES_BY_NATURE
        ):
            text = path.read_text(encoding="utf-8")
            path.write_text(jumpstart.PLACEHOLDER_RE.sub("answered", text), encoding="utf-8")


def filled_repo(path: Path, profile: str = "lite") -> Path:
    assert init_repo(path, profile, **FILLED) == 0
    fill_by_hand(path)
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()
    }


def finding(findings: list[jumpstart.Finding], check: str) -> jumpstart.Finding:
    return next(f for f in findings if f.check == check)


def legacy_repo(path: Path) -> Path:
    """The layout JumpStarter shipped before 2026-10-04, as real projects still have it."""
    rules = '# Rules\n\nRead narrow.\n- **A rule.** Why. *(INTERNALS: "A rule")*\n'
    (path / "CLAUDE.md").write_text(rules, encoding="utf-8")
    (path / "AGENTS.md").write_text(rules, encoding="utf-8")
    (path / "plan.md").write_text("# Plan\n\n## 12. Remaining work\n- x\n", encoding="utf-8")
    (path / "CURRENT_CHECKPOINT.md").write_text(
        "# Checkpoint\n\n## Active state at a glance\n\n| Branch | main |\n", encoding="utf-8"
    )
    (path / "CHANGELOG.md").write_text(
        "# History\n\n## Current implemented inventory\n- x\n\n## Recent changes\n- y\n",
        encoding="utf-8",
    )
    (path / "docs/decisions").mkdir(parents=True)
    (path / "docs/decisions/0001-owner-goals-and-priorities.md").write_text("q\n", "utf-8")
    (path / "docs/INTERNALS.md").write_text(
        "# Internals\n\n## A rule (2026-09-03, an incident)\nIt broke.\n", encoding="utf-8"
    )
    return path


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "widget"
    target.mkdir()
    return target


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #


def test_lite_writes_six_small_files_and_nothing_tool_specific(repo: Path) -> None:
    """Lite is the vibe-coding default: no helper-agent folders, no .gitignore edits."""
    assert init_repo(repo) == 0
    assert set(snapshot(repo)) == LITE_FILES


def test_team_adds_helper_agents_for_both_tools_on_top_of_lite(repo: Path) -> None:
    assert init_repo(repo, "team") == 0
    files = set(snapshot(repo))
    assert files >= LITE_FILES
    for role in jumpstart.ROLES:
        assert f".claude/agents/{role}.md" in files
        assert f".codex/agents/{role}.toml" in files
        assert f"docs/agents/{role}.md" in files
    assert {"docs/AGENT_TEAM.md", ".codex/config.toml", ".claude/settings.json"} <= files
    assert "docs/packets/TEMPLATE.md" in files


def test_team_appends_to_gitignore_once_and_keeps_what_was_there(repo: Path) -> None:
    (repo / ".gitignore").write_text("node_modules/", encoding="utf-8")
    init_repo(repo, "team")
    run("init", str(repo), "--name", "Widget", "--profile", "team", "--force")
    text = (repo / ".gitignore").read_text(encoding="utf-8")
    assert text.startswith("node_modules/\n")
    assert text.count(jumpstart.GITIGNORE_MARKER) == 1
    assert ".claude/worktrees/" in text


def test_init_fills_what_it_was_told_and_leaves_the_rest_visible(repo: Path) -> None:
    init_repo(repo, test_cmd="pytest -q", description="a widget")
    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert "# Widget" in agents and "a widget" in agents and "`pytest -q`" in agents
    assert "{{LINT_CMD}}" in agents  # never a plausible default: check reports it
    assert "{{DATE}}" not in (repo / "CHANGELOG.md").read_text(encoding="utf-8")


def test_init_never_overwrites_without_force(repo: Path) -> None:
    (repo / "plan.md").write_text("my plan\n", encoding="utf-8")
    init_repo(repo)
    assert (repo / "plan.md").read_text(encoding="utf-8") == "my plan\n"
    run("init", str(repo), "--name", "Widget", "--force")
    assert "## Now" in (repo / "plan.md").read_text(encoding="utf-8")


def test_init_does_not_split_rules_that_live_only_in_claude_md(repo: Path) -> None:
    """Writing a template AGENTS.md beside a real CLAUDE.md would leave Claude and
    Codex on different rules. init skips both and points at sync-agents."""
    (repo / "CLAUDE.md").write_text("# Real rules\n", encoding="utf-8")
    init_repo(repo)
    assert not (repo / "AGENTS.md").exists()
    assert (repo / "CLAUDE.md").read_text(encoding="utf-8") == "# Real rules\n"


def test_init_beside_an_existing_agents_md_adds_only_the_import(repo: Path) -> None:
    """A Codex-first repo already has AGENTS.md: keep it and give Claude the import."""
    (repo / "AGENTS.md").write_text("# Codex rules\n", encoding="utf-8")
    init_repo(repo)
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# Codex rules\n"
    assert jumpstart.imports_agents((repo / "CLAUDE.md").read_text(encoding="utf-8"))


def test_init_on_a_missing_directory_is_a_usage_error(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "nope"), "--name", "X") == 2


def test_no_subcommand_is_a_usage_error() -> None:
    assert run() == 2


# --------------------------------------------------------------------------- #
# retrofit and check
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("shape", ["bare", "legacy", "lite", "team"])
def test_retrofit_writes_nothing(repo: Path, shape: str) -> None:
    """retrofit is report-only. A retrofit that starts by editing gets reverted."""
    if shape == "legacy":
        legacy_repo(repo)
    elif shape != "bare":
        init_repo(repo, shape)
    before = snapshot(repo)
    run("retrofit", str(repo))
    assert snapshot(repo) == before


def test_a_bare_repo_is_one_clear_sentence_and_exit_1(repo: Path, capsys) -> None:
    assert run("retrofit", str(repo)) == 1
    assert "No agent setup here yet" in capsys.readouterr().out


@pytest.mark.parametrize("profile", ["lite", "team"])
def test_check_is_green_once_every_blank_is_answered(repo: Path, profile: str) -> None:
    filled_repo(repo, profile)
    assert run("check", str(repo)) == 0
    assert run("retrofit", str(repo)) == 0


def test_a_fresh_init_fails_check_until_the_blanks_are_filled(repo: Path, capsys) -> None:
    init_repo(repo)
    assert run("check", str(repo)) == 1
    out = capsys.readouterr().out
    assert "blanks in plan.md" in out and "GOAL" in out


def test_the_older_layout_still_passes_with_advisories(repo: Path) -> None:
    """Projects set up before 2026-10-04 must not turn red for their file names alone.
    They get advisories that say how to slim down."""
    findings = jumpstart.audit(legacy_repo(repo))
    assert all(f.ok for f in findings), [f.render() for f in findings if not f.ok]
    assert finding(findings, "CLAUDE.md imports AGENTS.md").status == jumpstart.ADVISORY
    assert finding(findings, "## Now").status == jumpstart.ADVISORY


def test_claude_and_agents_that_differ_is_drift(repo: Path) -> None:
    filled_repo(repo)
    (repo / "CLAUDE.md").write_text("# Other rules\n", encoding="utf-8")
    assert finding(jumpstart.audit(repo), "CLAUDE.md imports AGENTS.md").status == "DRIFT"
    assert run("check", str(repo)) == 1


def test_agents_md_without_claude_md_is_a_gap(repo: Path) -> None:
    filled_repo(repo)
    (repo / "CLAUDE.md").unlink()
    assert not finding(jumpstart.audit(repo), "CLAUDE.md imports AGENTS.md").ok


def test_an_oversized_agents_md_is_a_gap(repo: Path) -> None:
    filled_repo(repo)
    with (repo / "AGENTS.md").open("a", encoding="utf-8") as f:
        f.write("- rule\n" * jumpstart.AGENTS_MAX_LINES)
    assert finding(jumpstart.audit(repo), "AGENTS.md size").status == "OVERSIZE"


def test_an_oversized_now_block_is_a_gap(repo: Path) -> None:
    filled_repo(repo)
    plan = (repo / "plan.md").read_text(encoding="utf-8")
    long_now = "## Now\n" + "- note\n" * jumpstart.NOW_MAX_LINES
    (repo / "plan.md").write_text(plan.replace("## Now\n", long_now), encoding="utf-8")
    assert finding(jumpstart.audit(repo), "## Now").status == "OVERSIZE"


def test_a_heading_that_merely_contains_now_is_not_the_brief(repo: Path) -> None:
    """`## Known issues` contains "now"; matching it would pass a plan with no brief."""
    filled_repo(repo)
    (repo / "plan.md").write_text("# Plan\n\n## Known issues\n- x\n", encoding="utf-8")
    assert finding(jumpstart.audit(repo), "## Now").status == jumpstart.MISSING


def test_an_oversized_plan_is_a_gap(repo: Path) -> None:
    filled_repo(repo)
    with (repo / "plan.md").open("a", encoding="utf-8") as f:
        f.write("- item\n" * jumpstart.PLAN_MAX_LINES)
    assert finding(jumpstart.audit(repo), "plan size").status == "OVERSIZE"


def test_the_log_is_measured_as_a_section_not_the_whole_file(repo: Path) -> None:
    """An archive kept below the log in the same file must not trip the log's bound."""
    filled_repo(repo)
    with (repo / "CHANGELOG.md").open("a", encoding="utf-8") as f:
        f.write("\n## Archive\n" + "- old\n" * (jumpstart.LOG_MAX_LINES + 50))
    assert finding(jumpstart.audit(repo), "changelog log").ok


def test_an_oversized_log_is_a_gap(repo: Path) -> None:
    filled_repo(repo)
    with (repo / "CHANGELOG.md").open("a", encoding="utf-8") as f:
        f.write("- entry\n" * (jumpstart.LOG_MAX_LINES + 1))
    assert finding(jumpstart.audit(repo), "changelog log").status == "OVERSIZE"


def test_a_changelog_with_no_log_section_is_measured_whole(repo: Path) -> None:
    filled_repo(repo)
    (repo / "CHANGELOG.md").write_text(
        "# History\n\n## What exists\n" + "- x\n" * (jumpstart.LOG_MAX_LINES + 5),
        encoding="utf-8",
    )
    log = finding(jumpstart.audit(repo), "changelog log")
    assert not log.ok and "whole file" in log.detail


def test_a_changelog_with_no_inventory_is_a_gap(repo: Path) -> None:
    filled_repo(repo)
    (repo / "CHANGELOG.md").write_text("# History\n\n## Log\n- x\n", encoding="utf-8")
    assert not finding(jumpstart.audit(repo), "what exists").ok


def test_missing_goals_record_is_a_gap(repo: Path) -> None:
    filled_repo(repo)
    (repo / "docs/decisions/0001-goals.md").unlink()
    assert not finding(jumpstart.audit(repo), "owner goals").ok


def test_stray_status_files_are_named_as_an_advisory(repo: Path) -> None:
    filled_repo(repo)
    (repo / "HANDOFF_NOTES.md").write_text("x\n" * 12, encoding="utf-8")
    (repo / "README.md").write_text("readme\n", encoding="utf-8")
    stray = finding(jumpstart.audit(repo), "extra status files")
    assert stray.status == jumpstart.ADVISORY
    assert "HANDOFF_NOTES.md (12 lines)" in stray.detail and "README" not in stray.detail


def test_the_report_is_ascii_so_any_console_can_print_it(repo: Path, capsys) -> None:
    init_repo(repo, "team")
    run("retrofit", str(repo))
    capsys.readouterr().out.encode("ascii")


# --------------------------------------------------------------------------- #
# Lessons: every cited rule is written down
# --------------------------------------------------------------------------- #


def cite(repo: Path, citation: str, lessons: str) -> jumpstart.Finding:
    filled_repo(repo)
    with (repo / "AGENTS.md").open("a", encoding="utf-8") as f:
        f.write(f"\n- **Rule.** Why. {citation}\n")
    (repo / "docs/LESSONS.md").write_text(f"# Lessons\n\n{lessons}", encoding="utf-8")
    return finding(jumpstart.audit(repo), "lessons")


def test_a_cited_rule_with_no_lesson_is_a_gap_that_names_it(repo: Path) -> None:
    result = cite(repo, '(LESSONS: "Never stash")', "## Something else\n")
    assert not result.ok and '"Never stash"' in result.detail


def test_matching_survives_wrapping_case_and_a_dated_suffix(repo: Path) -> None:
    result = cite(repo, '(LESSONS: "never\n  stash")', "## Never Stash (2026-09-03, a loss)\n")
    assert result.ok


def test_an_example_citation_inside_a_comment_is_not_a_citation(repo: Path) -> None:
    assert cite(repo, '<!-- (LESSONS: "Example") -->', "").ok


def test_the_older_internals_citation_still_counts(repo: Path) -> None:
    result = cite(repo, '(INTERNALS: "Old rule")', "## Something else\n")
    assert not result.ok and '"Old rule"' in result.detail


def test_the_same_rule_cited_twice_counts_once(repo: Path) -> None:
    result = cite(repo, '(LESSONS: "A") (LESSONS: "a")', "## Other\n")
    assert result.detail.startswith("1 cited rule(s)")


# --------------------------------------------------------------------------- #
# Team
# --------------------------------------------------------------------------- #


def test_a_lite_repo_gets_no_team_findings(repo: Path) -> None:
    filled_repo(repo)
    assert jumpstart.audit_team(repo) == []


def test_a_missing_role_is_a_gap(repo: Path) -> None:
    filled_repo(repo, "team")
    (repo / ".codex/agents/recon.toml").unlink()
    assert not finding(jumpstart.audit(repo), "Codex helper agents").ok


def test_a_wrapper_pointing_at_a_missing_role_file_is_a_gap(repo: Path) -> None:
    filled_repo(repo, "team")
    (repo / "docs/agents/builder.md").unlink()
    gap = finding(jumpstart.audit(repo), "Claude helper agents instructions")
    assert not gap.ok and "docs/agents/builder.md" in gap.detail


def test_a_codex_role_without_its_metadata_is_a_gap(repo: Path) -> None:
    filled_repo(repo, "team")
    path = repo / ".codex/agents/tester.toml"
    path.write_text(re.sub(r'(?m)^name = ".*"\n', "", path.read_text("utf-8")), "utf-8")
    assert not finding(jumpstart.audit(repo), "Codex role tester").ok


def test_codex_agents_without_a_config_is_a_gap(repo: Path) -> None:
    filled_repo(repo, "team")
    (repo / ".codex/config.toml").unlink()
    assert not finding(jumpstart.audit(repo), "Codex config").ok


def test_deleting_the_codex_folder_leaves_a_claude_only_team_green(repo: Path) -> None:
    """AGENT_TEAM.md tells a Claude-only project to delete .codex/. That must work."""
    filled_repo(repo, "team")
    for path in sorted((repo / ".codex").rglob("*"), reverse=True):
        path.rmdir() if path.is_dir() else path.unlink()
    (repo / ".codex").rmdir()
    assert run("check", str(repo)) == 0


def test_metadata_reader_sees_only_top_level_string_fields() -> None:
    text = 'name = "recon"\ndeveloper_instructions = """\nDo it.\n"""\n'
    assert jumpstart._native_metadata_present(text, "name")
    assert jumpstart._native_metadata_present(text, "developer_instructions")
    assert not jumpstart._native_metadata_present(text, "description")
    assert not jumpstart._native_metadata_present('name = ""\n', "name")


# --------------------------------------------------------------------------- #
# sync-agents
# --------------------------------------------------------------------------- #


def test_sync_moves_claude_only_rules_into_agents(repo: Path) -> None:
    (repo / "CLAUDE.md").write_text("# Real rules\n", encoding="utf-8")
    assert run("sync-agents", str(repo)) == 0
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == "# Real rules\n"
    assert jumpstart.imports_agents((repo / "CLAUDE.md").read_text(encoding="utf-8"))


def test_sync_collapses_identical_copies_to_one_source(repo: Path) -> None:
    legacy_repo(repo)
    rules = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert run("sync-agents", str(repo)) == 0
    assert (repo / "AGENTS.md").read_text(encoding="utf-8") == rules
    assert finding(jumpstart.audit(repo), "CLAUDE.md imports AGENTS.md").status == "OK"


def test_sync_refuses_copies_that_differ_and_writes_nothing(repo: Path) -> None:
    (repo / "CLAUDE.md").write_text("one\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("two\n", encoding="utf-8")
    before = snapshot(repo)
    assert run("sync-agents", str(repo)) == 1
    assert snapshot(repo) == before


def test_sync_is_a_no_op_when_already_in_sync(repo: Path) -> None:
    init_repo(repo)
    before = snapshot(repo)
    assert run("sync-agents", str(repo)) == 0
    assert snapshot(repo) == before


def test_sync_with_nothing_to_sync_fails(repo: Path) -> None:
    assert run("sync-agents", str(repo)) == 1


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def test_section_line_count_stops_at_the_next_same_level_heading() -> None:
    text = "# T\n## Log\na\nb\n### deeper\nc\n## Next\nd\n"
    assert jumpstart.section_line_count(text, "Log") == 5
    assert jumpstart.section_line_count(text, "Next") == 2
    assert jumpstart.section_line_count(text, "Missing") is None


def test_a_placeholder_name_is_an_identifier() -> None:
    """Prose about placeholders writes {{...}}, which must not read as one."""
    assert jumpstart.find_placeholders("write {{...}} in prose") == []
    assert jumpstart.find_placeholders("{{A}} {{B}} {{A}}") == ["A", "B"]


def test_fill_leaves_unknown_tokens_in_place() -> None:
    assert jumpstart.fill("{{A}} {{B}}", {"A": "x"}) == "x {{B}}"


# --------------------------------------------------------------------------- #
# The templates themselves
# --------------------------------------------------------------------------- #


def template_texts() -> list[tuple[Path, str]]:
    return [(p, p.read_text(encoding="utf-8")) for p in sorted(TEMPLATES.rglob("*")) if p.is_file()]


def test_lite_stays_short_enough_to_read_in_one_go() -> None:
    """The reader is an agent on a context budget, often a small local model."""
    agents = (TEMPLATES / "lite/AGENTS.md").read_text(encoding="utf-8")
    assert len(agents.splitlines()) <= 90
    lite_bytes = sum(p.stat().st_size for p in (TEMPLATES / "lite").rglob("*") if p.is_file())
    assert lite_bytes <= 8000


def test_every_role_file_stays_short() -> None:
    for path in (TEMPLATES / "team/docs/agents").glob("*.md"):
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 60, path
    assert len((TEMPLATES / "team/docs/AGENT_TEAM.md").read_text("utf-8").splitlines()) <= 90


def test_claude_md_template_imports_agents_md() -> None:
    assert jumpstart.imports_agents((TEMPLATES / "lite/CLAUDE.md").read_text(encoding="utf-8"))


def test_agents_md_speaks_to_every_kind_of_agent() -> None:
    agents = (TEMPLATES / "lite/AGENTS.md").read_text(encoding="utf-8")
    for tool in ("Claude Code", "Codex", "local model"):
        assert tool in agents


def test_both_tools_run_the_same_role_instructions() -> None:
    """One instruction file per role, so Claude and Codex helpers cannot drift."""
    for role in jumpstart.ROLES:
        shared = f"docs/agents/{role}.md"
        assert (TEMPLATES / "team" / shared).is_file()
        assert shared in (TEMPLATES / f"team/.claude/agents/{role}.md").read_text("utf-8")
        assert shared in (TEMPLATES / f"team/.codex/agents/{role}.toml").read_text("utf-8")


def test_cheap_model_for_lookups_strong_for_building() -> None:
    """Cost is the trust signal: the wrong model on a cheap job is the failure mode."""
    claude = TEMPLATES / "team/.claude/agents"
    assert "model: haiku" in (claude / "recon.md").read_text("utf-8")
    assert "{{CODEX_CHEAP_MODEL}}" in (TEMPLATES / "team/.codex/agents/recon.toml").read_text(
        "utf-8"
    )
    for role in ("tester", "builder", "reviewer"):
        assert "model: haiku" not in (claude / f"{role}.md").read_text("utf-8")


def test_read_only_roles_cannot_edit() -> None:
    for role in ("recon", "reviewer"):
        text = (TEMPLATES / f"team/.claude/agents/{role}.md").read_text("utf-8")
        assert "disallowedTools: Write, Edit" in text


def test_the_tester_never_writes_the_fix() -> None:
    assert "never write" in (TEMPLATES / "team/docs/agents/tester.md").read_text("utf-8")


def test_claude_front_matter_is_plain_key_value() -> None:
    """A second ': ' in a YAML value breaks the parse and the agent silently vanishes."""
    for path in (TEMPLATES / "team/.claude/agents").glob("*.md"):
        front = path.read_text("utf-8").split("---")[1]
        for line in front.strip().splitlines():
            assert line.count(": ") == 1, (path.name, line)


def test_git_stash_appears_only_as_a_prohibition() -> None:
    for path, text in template_texts():
        for line in text.splitlines():
            if "git stash" in line:
                assert "never" in line.lower() or "Bash(git stash" in line, (path, line)


def test_templates_carry_nothing_from_any_one_project() -> None:
    banned = ("trading", "tradingbot", "powershell", "fable", "astra", "terra", "luna", "gpt-")
    for path, text in template_texts():
        lowered = text.lower()
        for word in banned:
            assert word not in lowered, (path, word)


def test_no_template_uses_a_dotted_placeholder_name() -> None:
    """A dotted name would never be filled and never be reported."""
    dotted = re.compile(r"\{\{[A-Za-z0-9_]*\.[^}]*\}\}")
    for path, text in template_texts():
        assert not dotted.search(text), path


# --------------------------------------------------------------------------- #
# JumpStarter on itself
# --------------------------------------------------------------------------- #


def test_jumpstarter_passes_its_own_check() -> None:
    assert run("check", str(REPO_ROOT)) == 0


def test_the_lint_target_matches_the_declared_python_floor() -> None:
    """An unpinned or mismatched linter suggests code the floor cannot run."""
    ruff = (REPO_ROOT / "ruff.toml").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert 'target-version = "py39"' in ruff
    assert "Python 3.9" in readme
