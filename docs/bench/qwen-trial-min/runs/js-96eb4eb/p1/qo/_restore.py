"""Restore the four root .claude/agents/*.md files byte-exactly.

The worktree copy carries template placeholders where the committed dogfood
content was filled. `git diff -U0` shows exactly which worktree lines changed
and what they said at the index; reversing those pairs restores the original
bytes without touching anything else. Verification is the sha256 pin the C1
test carries (CLAUDE_ROLE_SHA256).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

PINNED = {
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
}


def restore(rel: str) -> None:
    result = subprocess.run(
        ["git", "diff", "-U0", "--", rel], capture_output=True, check=True
    )
    diff = result.stdout.decode("utf-8")
    raw = Path(rel).read_bytes()
    lines = raw.split(b"\n")
    replacements: dict[int, bytes] = {}
    for match in re.finditer(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", diff):
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        body = diff[match.end() :]
        stop = body.find("\n@@")
        if stop != -1:
            body = body[:stop]
        minus = [ln[1:] for ln in body.splitlines() if ln.startswith("-")]
        plus = [ln[1:] for ln in body.splitlines() if ln.startswith("+")]
        if len(minus) != count or len(plus) != count:
            raise AssertionError((rel, match.group(0), len(minus), len(plus), count))
        for offset, (original, damaged) in enumerate(zip(minus, plus)):
            number = start + offset
            current = lines[number - 1]
            eol = b"\r" if current.endswith(b"\r") else b""
            want = damaged.encode("utf-8")
            if current.rstrip(b"\r") != want:
                raise AssertionError(
                    (rel, number, current[:80], want[:80], "worktree line drifted")
                )
            replacements[number] = original.encode("utf-8") + eol
    for number, original in replacements.items():
        lines[number - 1] = original
    Path(rel).write_bytes(b"\n".join(lines))
    digest = hashlib.sha256(Path(rel).read_bytes()).hexdigest()
    status = "ok" if digest == PINNED[rel] else "PIN MISMATCH"
    print(f"{rel}: {len(replacements)} line(s) reversed -> {digest[:12]} {status}")
    if digest != PINNED[rel]:
        sys.exit(1)


if __name__ == "__main__":
    for rel in sorted(PINNED):
        restore(rel)
    print("all four restored and pinned")
