"""Packet C2: native Codex lead configuration and role metadata."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib as tomli
else:
    import tomli

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import jumpstart  # noqa: E402  (path set above)

CODEX_ROLES = ("tester", "builder", "reviewer", "recon")
PLACEHOLDER = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")


def run(*argv: str) -> int:
    return jumpstart.main(list(argv))


def init_repo(
    path: Path,
    *,
    lead_model: str | None = None,
    strong_model: str | None = "gpt-5.6-terra",
    cheap_model: str | None = "gpt-5.6-luna",
    force: bool = False,
) -> int:
    argv = [
        "init",
        str(path),
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
        "--branch-prefix",
        "claude/",
    ]
    for option, value in (
        ("--codex-lead-model", lead_model),
        ("--codex-strong-model", strong_model),
        ("--codex-cheap-model", cheap_model),
    ):
        if value is not None:
            argv.extend([option, value])
    if force:
        argv.append("--force")
    return run(*argv)


def _fill_remaining_placeholders(path: Path, keep: frozenset[str] = frozenset()) -> None:
    """Model owner answers without using the CLI's placeholder implementation."""
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix not in {".md", ".json", ".toml"}:
            continue
        item.write_text(
            PLACEHOLDER.sub(
                lambda match: match.group(0) if match.group(1) in keep else "filled",
                item.read_text(encoding="utf-8"),
            ),
            encoding="utf-8",
        )


def _tree_bytes(path: Path) -> dict[str, bytes]:
    return {
        item.relative_to(path).as_posix(): item.read_bytes()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "widget"
    target.mkdir()
    return target


def test_native_codex_roles_have_required_nonempty_metadata_in_both_sets() -> None:
    """Codex can discover every shipped role by its native metadata."""
    for base in (REPO_ROOT / ".codex", REPO_ROOT / "templates" / ".codex"):
        for role in CODEX_ROLES:
            path = base / "agents" / f"{role}.toml"
            assert path.is_file(), f"missing native role {path.relative_to(REPO_ROOT)}"
            role_config = tomli.loads(path.read_text(encoding="utf-8"))
            for key in ("name", "description", "developer_instructions"):
                assert role_config.get(key, "").strip(), (
                    f"{path.relative_to(REPO_ROOT)} has no useful {key}"
                )


def test_init_installs_lead_config_without_overwriting_and_keeps_unknown_models_visible(
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Lead config follows init's normal fill, skip, force, and placeholder contract."""
    assert init_repo(repo, lead_model="gpt-6-astra") == 0
    config = repo / ".codex" / "config.toml"
    config_data = tomli.loads(config.read_text(encoding="utf-8"))
    assert config_data["model"] == "gpt-6-astra"
    assert config_data["model_reasoning_effort"] == "high"
    assert config_data["agents"]["enabled"] is True
    assert config_data["agents"]["default_subagent_model"] == "gpt-5.6-terra"
    assert config_data["agents"]["default_subagent_reasoning_effort"] == "high"

    owner_config = "model = 'owner-selected'\n"
    config.write_text(owner_config, encoding="utf-8")
    assert init_repo(repo, lead_model="gpt-6-astra") == 0
    assert config.read_text(encoding="utf-8") == owner_config
    assert init_repo(repo, lead_model="gpt-6-astra", force=True) == 0
    assert tomli.loads(config.read_text(encoding="utf-8"))["model"] == "gpt-6-astra"

    unconfigured = tmp_path / "unconfigured"
    unconfigured.mkdir()
    assert init_repo(unconfigured, strong_model=None) == 0
    unconfigured_config = (unconfigured / ".codex" / "config.toml").read_text(
        encoding="utf-8"
    )
    assert "{{CODEX_LEAD_MODEL}}" in unconfigured_config
    assert "{{CODEX_STRONG_MODEL}}" in unconfigured_config
    _fill_remaining_placeholders(
        unconfigured,
        frozenset({"CODEX_LEAD_MODEL", "CODEX_STRONG_MODEL"}),
    )
    assert run("check", str(unconfigured)) == 1
    output = capsys.readouterr().out
    assert "CODEX_LEAD_MODEL" in output
    assert "CODEX_STRONG_MODEL" in output


def test_check_and_retrofit_report_missing_native_config_and_metadata_without_writing(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Native lead and role gaps are reported by both audit paths, never repaired."""
    assert init_repo(repo) == 0
    _fill_remaining_placeholders(repo)
    config = repo / ".codex" / "config.toml"
    if config.exists():
        config.unlink()
    for role in CODEX_ROLES:
        role_path = repo / ".codex" / "agents" / f"{role}.toml"
        role_path.write_text(
            re.sub(
                r'(?m)^(name|description)\s*=\s*"[^"\n]*"\s*\n?',
                "",
                role_path.read_text(encoding="utf-8"),
            ),
            encoding="utf-8",
        )

    assert run("check", str(repo)) == 1
    check_output = capsys.readouterr().out
    assert ".codex/config.toml not found" in check_output
    assert "name" in check_output
    assert "description" in check_output

    before = _tree_bytes(repo)
    assert run("retrofit", str(repo)) == 1
    retrofit_output = capsys.readouterr().out
    assert _tree_bytes(repo) == before, "retrofit wrote to the audited repository"
    assert ".codex/config.toml not found" in retrofit_output
    assert "name" in retrofit_output
    assert "description" in retrofit_output


def test_native_metadata_audit_reads_only_top_level_toml_fields(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Role prose cannot masquerade as native metadata; valid scalar TOML can."""
    assert init_repo(repo) == 0
    tester = repo / ".codex" / "agents" / "tester.toml"
    tester_text = tester.read_text(encoding="utf-8")
    tester.write_text(
        tester_text.replace('name = "tester"', "name = 'tester' # native name").replace(
            'description = "Writes packet behaviour tests before the fix, proves they fail, and hands the red branch to the builder without changing production code."',
            "description = 'A valid tester role' # native description",
        ),
        encoding="utf-8",
    )
    builder = repo / ".codex" / "agents" / "builder.toml"
    builder_text = builder.read_text(encoding="utf-8")
    builder_text = builder_text.replace('name = "builder"\n', "").replace(
        'description = "Builds one approved packet in an isolated worktree, makes the tester\'s red tests pass without weakening them, and reconciles the required documentation."\n',
        "",
    )
    builder.write_text(
        builder_text.replace(
            'developer_instructions = """',
            'developer_instructions = """\nname = "only role prose"\ndescription = "also role prose"',
        ),
        encoding="utf-8",
    )

    assert run("check", str(repo)) == 1
    check_output = capsys.readouterr().out
    assert "native role metadata tester" in check_output
    assert "native role metadata builder" in check_output
    assert "builder.toml missing required name, description" in check_output
    assert run("retrofit", str(repo)) == 1
    retrofit_output = capsys.readouterr().out
    assert "native role metadata tester" in retrofit_output
    assert "builder.toml missing required name, description" in retrofit_output


def test_native_metadata_audit_reports_an_empty_top_level_value_without_crashing(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Empty scalar metadata remains a gap even when its TOML syntax is valid."""
    assert init_repo(repo) == 0
    _fill_remaining_placeholders(repo)
    tester = repo / ".codex" / "agents" / "tester.toml"
    tester.write_text(
        tester.read_text(encoding="utf-8").replace('name = "tester"', 'name = ""'),
        encoding="utf-8",
    )

    assert run("check", str(repo)) == 1
    check_output = capsys.readouterr().out
    assert "native role metadata tester" in check_output
    assert "tester.toml missing required name" in check_output
    assert run("retrofit", str(repo)) == 1
    retrofit_output = capsys.readouterr().out
    assert "native role metadata tester" in retrofit_output
    assert "tester.toml missing required name" in retrofit_output


def test_missing_native_role_is_a_gap_in_both_report_only_audits(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert init_repo(repo) == 0
    _fill_remaining_placeholders(repo)
    (repo / ".codex" / "agents" / "builder.toml").unlink()
    before = _tree_bytes(repo)
    for command in ("check", "retrofit"):
        assert run(command, str(repo)) == 1
        assert ".codex/agents/builder.toml not found" in capsys.readouterr().out
        assert _tree_bytes(repo) == before
