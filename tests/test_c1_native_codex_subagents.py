"""Packet C1: native Codex roles are additive to the Claude agent team."""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import jumpstart  # noqa: E402  (path set above)

CODEX_ROLES = ("tester", "builder", "reviewer", "recon")
PLACEHOLDER = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")
CLAUDE_ROLE_SHA256 = {
    ".claude/agents/builder.md": (
        "09d72132008f49586c2b54aba530cf3ee7d40951397186863f3747ee3e95d9d6"
    ),
    ".claude/agents/recon.md": (
        "ca1d0278f9ad6d738cc02ed95fc98a3cf13926f429fa3c453aa28f478215a38d"
    ),
    ".claude/agents/reviewer.md": (
        "07eaeef5f6f73f98ee3ba6b999389247b67e71f81921e94af8aac680cced8dba"
    ),
    ".claude/agents/tester.md": (
        "bc2fef24f15e5902c22124a5752ef4e4ec67374063516d727ccadcb1c94bd1df"
    ),
    "templates/.claude/agents/builder.md": (
        "b08acdd2a3e993595f7c237eac457cb86e04d143723690a5b4181674aca6366b"
    ),
    "templates/.claude/agents/recon.md": (
        "d5b47c42ecfcee3abaea144d4474cfd028d39b113d42bb9ba8f5813eee48201a"
    ),
    "templates/.claude/agents/reviewer.md": (
        "fafcf405b4ad110157cedde2b999a67ea95b3df7e744c0158b3c1fd285518628"
    ),
    "templates/.claude/agents/tester.md": (
        "23addf1ff9a94d78e345afc0d1d21a9d6f0c1b8982675d35874cb0aa617c2ea9"
    ),
}


def run(*argv: str) -> int:
    return jumpstart.main(list(argv))


def init_repo(
    path: Path,
    *,
    include_models: bool,
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
    if include_models:
        argv.extend(
            [
                "--codex-strong-model",
                "gpt-5.6-terra",
                "--codex-cheap-model",
                "gpt-5.6-luna",
            ]
        )
    if force:
        argv.append("--force")
    return run(*argv)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "widget"
    target.mkdir()
    return target


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_codex_agent(text: str) -> dict[str, str]:
    """Parse the string-only TOML subset used by Codex agent definitions.

    Python 3.9 has no tomllib. This parser is deliberately independent of the CLI and
    rejects unknown syntax, duplicate keys, missing delimiters, and trailing content.
    """
    parsed: dict[str, str] = {}
    lines = iter(enumerate(text.splitlines(), start=1))
    scalar = re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"([^"\\]*)"\s*$')
    multiline = re.compile(r'^([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*"""\s*$')

    for line_number, raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = scalar.fullmatch(line)
        if match:
            key, value = match.groups()
        else:
            match = multiline.fullmatch(line)
            assert match is not None, f"unsupported TOML syntax on line {line_number}: {raw!r}"
            key = match.group(1)
            body: list[str] = []
            for _, body_line in lines:
                if body_line.strip() == '"""':
                    break
                body.append(body_line)
            else:
                raise AssertionError(f"unterminated TOML multiline string for {key}")
            value = "\n".join(body)
        assert key not in parsed, f"duplicate TOML key: {key}"
        parsed[key] = value

    required = {"model", "model_reasoning_effort", "developer_instructions"}
    assert required <= set(parsed), f"missing required TOML keys: {sorted(required - set(parsed))}"
    return parsed


def _tree_bytes(path: Path) -> dict[str, bytes]:
    return {
        item.relative_to(path).as_posix(): item.read_bytes()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def _fill_remaining_placeholders(path: Path, keep: frozenset[str] = frozenset()) -> None:
    """Model a human completing the questionnaire, independently of jumpstart.fill."""
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix not in {".md", ".json", ".toml"}:
            continue
        text = item.read_text(encoding="utf-8")
        filled = PLACEHOLDER.sub(
            lambda match: match.group(0) if match.group(1) in keep else "filled",
            text,
        )
        item.write_text(filled, encoding="utf-8")


def test_native_codex_roles_preserve_claude_and_route_models_by_cost(repo: Path) -> None:
    """Codex gets native roles without changing one byte of Claude's working team."""
    template_paths = {
        role: REPO_ROOT / "templates" / ".codex" / "agents" / f"{role}.toml"
        for role in CODEX_ROLES
    }
    for path in template_paths.values():
        assert path.is_file(), f"missing native Codex template {path.relative_to(REPO_ROOT)}"
        _parse_codex_agent(path.read_text(encoding="utf-8"))

    for rel, expected in CLAUDE_ROLE_SHA256.items():
        assert _sha256(REPO_ROOT / rel) == expected, f"Claude role changed: {rel}"

    expected_dogfood = {f".codex/agents/{role}.toml" for role in CODEX_ROLES}
    tracked_dogfood = set(
        subprocess.run(
            ["git", "ls-files", "--", ".codex/agents"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    assert tracked_dogfood == expected_dogfood
    dogfood = {
        role: _parse_codex_agent(
            (REPO_ROOT / ".codex" / "agents" / f"{role}.toml").read_text(encoding="utf-8")
        )
        for role in CODEX_ROLES
    }
    for role in ("tester", "builder", "reviewer"):
        assert dogfood[role]["model"] == "gpt-5.6-terra"
        assert dogfood[role]["model_reasoning_effort"] == "high"
    assert dogfood["recon"]["model"] == "gpt-5.6-luna"
    assert dogfood["recon"]["model_reasoning_effort"] == "medium"

    assert init_repo(repo, include_models=True) == 0
    configs = {
        role: _parse_codex_agent(
            (repo / ".codex" / "agents" / f"{role}.toml").read_text(encoding="utf-8")
        )
        for role in CODEX_ROLES
    }

    for role in ("tester", "builder", "reviewer"):
        assert configs[role]["model"] == "gpt-5.6-terra"
        assert configs[role]["model_reasoning_effort"] == "high"
    assert configs["recon"]["model"] == "gpt-5.6-luna"
    assert configs["recon"]["model_reasoning_effort"] == "medium"

    instructions = {
        role: " ".join(configs[role]["developer_instructions"].split())
        for role in CODEX_ROLES
    }
    assert "You never write the fix" in instructions["tester"]
    assert "may not weaken, skip, delete or rewrite a tester's assertion" in instructions[
        "builder"
    ]
    assert "Never edit" in instructions["reviewer"]
    assert "You change nothing" in instructions["recon"]
    assert "claude/<slug>" in instructions["tester"]
    assert "claude/<packet-slug>" in instructions["builder"]
    assert ".claude/packets/" in " ".join(instructions.values())
    assert "templates/.claude/agents/*.md" in instructions["builder"]
    assert "templates/.codex/agents/*.toml" in instructions["builder"]
    assert "CLAUDE.md" in instructions["builder"]
    assert "AGENTS.md" in instructions["builder"]
    assert "byte-identical" in instructions["builder"]


def test_init_and_retrofit_manage_codex_roles_without_weakening_safety(
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The real CLI installs, checks, and audits both harness-native role sets."""
    unfilled = tmp_path / "unfilled"
    unfilled.mkdir()
    assert init_repo(unfilled, include_models=False) == 0
    for role in CODEX_ROLES:
        text = (unfilled / ".codex" / "agents" / f"{role}.toml").read_text(
            encoding="utf-8"
        )
        assert "{{CODEX_STRONG_MODEL}}" in text or "{{CODEX_CHEAP_MODEL}}" in text
    _fill_remaining_placeholders(
        unfilled,
        frozenset({"CODEX_STRONG_MODEL", "CODEX_CHEAP_MODEL"}),
    )
    assert run("check", str(unfilled)) == 1
    unfilled_output = capsys.readouterr().out
    assert "CODEX_STRONG_MODEL" in unfilled_output
    assert "CODEX_CHEAP_MODEL" in unfilled_output

    assert init_repo(repo, include_models=True) == 0
    for role in CODEX_ROLES:
        assert (repo / ".codex" / "agents" / f"{role}.toml").is_file()
    _fill_remaining_placeholders(repo)
    assert run("check", str(repo)) == 0
    assert run("retrofit", str(repo)) == 0
    capsys.readouterr()

    gitignore = (repo / ".gitignore").read_text(encoding="utf-8")
    assert "!/.codex/agents/" in gitignore
    assert "/.codex/*" not in gitignore
    assert gitignore.count(jumpstart.GITIGNORE_MARKER) == 1
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    (repo / ".codex" / "config.toml").write_text("approval_policy = 'never'\n", encoding="utf-8")
    for tracked in (".codex/agents/tester.toml", ".codex/config.toml"):
        check_ignore = subprocess.run(
            ["git", "check-ignore", "--quiet", tracked],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        assert check_ignore.returncode == 1, f"{tracked} was incorrectly ignored"

    protected = repo / ".codex" / "agents" / "builder.toml"
    protected.write_text("the project's own Codex role\n", encoding="utf-8")
    assert init_repo(repo, include_models=True) == 0
    assert protected.read_text(encoding="utf-8") == "the project's own Codex role\n"
    assert (repo / ".gitignore").read_text(encoding="utf-8").count(
        jumpstart.GITIGNORE_MARKER
    ) == 1
    assert init_repo(repo, include_models=True, force=True) == 0
    capsys.readouterr()

    missing = repo / ".codex" / "agents" / "recon.toml"
    missing.unlink()
    before = _tree_bytes(repo)
    assert run("retrofit", str(repo)) == 1
    output = capsys.readouterr().out
    assert _tree_bytes(repo) == before, "retrofit wrote to the audited repository"
    assert ".codex/agents/recon.toml not found" in output
    finding_names = re.findall(r"^  \[[A-Z ]+\] ([^:]+):", output, flags=re.MULTILINE)
    assert len(finding_names) == len(set(finding_names)), (
        "Claude and Codex role findings must have distinct names"
    )


def test_codex_guidance_uses_native_roles_and_the_shared_packet_interface(repo: Path) -> None:
    """Every owner-facing route stops prescribing manual Claude-brief conversion."""
    assert init_repo(repo, include_models=True) == 0

    installed_notes = (repo / "docs" / "CODEX_NOTES.md").read_text(encoding="utf-8")
    root_notes = (REPO_ROOT / "docs" / "CODEX_NOTES.md").read_text(encoding="utf-8")
    for notes in (installed_notes, root_notes):
        assert ".codex/agents/" in notes
        assert "gpt-5.6-terra" in notes
        assert "gpt-5.6-luna" in notes
        assert ".claude/packets/" in notes
        assert "handoff" in notes.lower()
        assert "paste the body" not in notes.lower()
        assert "there are no automatic" not in notes.lower()

    for rel in (
        "README.md",
        "docs/AGENT_TEAM.md",
        "playbooks/new-project.md",
        "playbooks/retrofit.md",
        "playbooks/build-review-loop.md",
    ):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert ".codex/agents/" in text, f"{rel} still omits native Codex roles"

    for team in (
        (REPO_ROOT / "docs" / "AGENT_TEAM.md").read_text(encoding="utf-8"),
        (repo / "docs" / "AGENT_TEAM.md").read_text(encoding="utf-8"),
    ):
        assert ".claude/agents/" in team
        assert ".codex/agents/" in team
        assert "same packet" in team.lower()

    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert (REPO_ROOT / "CLAUDE.md").read_bytes() == (REPO_ROOT / "AGENTS.md").read_bytes()
    assert ".claude/agents/" in claude
    assert ".codex/agents/" in claude
    assert "templates/.codex/agents/*.toml" in claude

    for internals in (
        (REPO_ROOT / "docs" / "INTERNALS.md").read_text(encoding="utf-8"),
        (repo / "docs" / "INTERNALS.md").read_text(encoding="utf-8"),
    ):
        assert "AGENTS.md == AGENTS.md" in internals
        assert "Codex/<slug>" in internals
        assert "templates/.codex/agents/*.toml" in internals
