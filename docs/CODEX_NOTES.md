# Working on JumpStarter with Codex

Document role: **active runbook.** What a Codex session reads in this repo, what it
cannot do, and how the same work packets reach it.

The generic version that ships to other projects is `templates/codex/CODEX_NOTES.md`.

## What Codex reads

At idle boot, Codex reads only its identity and standing instructions plus
[`MEMORY.md`](../MEMORY.md). `AGENTS.md` is a byte-identical generated copy of
`CLAUDE.md`, so the operating rules are the same for both tools; there is no
Codex-specific rules variant.

When a task is in scope, use `AGENTS.md`'s narrow mandatory workflow: the active-state
block, `plan.md` sections 5/6/7 and the task's phase, a search of the changelog inventory,
the relevant `docs/README.md` entries, and only the supporting documents the task needs.
For questions about prior work, decisions, dates, people or preferences, search memory
first and cite the detail file, provenance tag and date. `MEMORY.md` routes recall; it
does not replace the project plan or status ledgers. The current owner-goals record is
[`decisions/0002-owner-goals-asked-properly.md`](decisions/0002-owner-goals-asked-properly.md).

**Never hand-edit `AGENTS.md`.** Edit `CLAUDE.md` and run
`python tools/jumpstart.py sync-agents .`. `check .` fails on the sha256 mismatch, which
is how a hand-edit gets caught.

## Native roles and model routing

`.codex/config.toml` selects Astra/high for a new JumpStarter lead, enables agents, and
sets Terra/high as the fallback subagent route. The named native roles use Terra/high for
tester, builder and reviewer, while Luna/medium handles read-only recon. Config defaults
cannot retroactively switch a running session or override an explicit UI choice.

The exact model IDs are `gpt-6-astra`, `gpt-5.6-terra`, and `gpt-5.6-luna`.

Codex does not read `.claude/settings.json`; its own sandbox and approval settings
apply. Anything the Claude allow-list treats as destructive is still destructive.

## Handing a packet to Codex

The packet format is tool-neutral (`templates/.claude/packets/PACKET_TEMPLATE.md`). To run a native role in a
Codex session:

1. Start at the repo root, on the packet's branch (`claude/<slug>`), in its own
   worktree if another session is running.
2. Spawn the matching native role from `.codex/agents/` and give it the packet path
   under `.claude/packets/`, plus the branch name. Claude and Codex consume the same
   packet; never maintain a second Codex packet copy.
3. Require the same handoff or verdict format the role definition specifies. **The
   formats are the interface between tools**: a Codex builder's handoff must be readable
   by a Claude Code lead, and the reverse. The crossing remains unproven until its real
   project gate is recorded.

One packet, one session, one role. A session that builds and then reviews its own work is
not a review.

### When native role selection is unavailable

Disclose the limitation once. Read the tracked role TOML, then call the generic spawn
tool with its model and effort, `fork_turns="none"`, and a message containing the role's
developer instructions, packet and isolated worktree path. Label it an **adapted role
run**; it cannot close the native-role gate. Never silently accept inherited Astra
workers. If spawning itself is unavailable, report the blocker.

## What stays the same in both tools

- The bounded read comes before the first edit.
- Fail-before-fix is proven, not claimed.
- Review is by reproduction, not by reading.
- One checkout, many agents: worktrees for builders and reviewers.
- Chat is short; detail lives in commits, docs and handoffs.
- The owner decides priorities and promotions.

The root Codex role copies contain a local workspace-memory paragraph for boot and recall.
It preserves their models, role boundaries and packet/handoff contract; templates remain
unchanged because the extension does not instruct downstream projects.
