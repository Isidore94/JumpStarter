# Working on {{PROJECT}} with Codex

Document role: **active runbook.** What a Codex session reads in this repo, what it
cannot do, and how the same work packets reach it.

## What Codex reads

- **`AGENTS.md` at the repo root.** It is a byte-identical generated copy of
  `CLAUDE.md`, so the operating rules — the bounded read, the core rules, the hard
  invariants, the commands, the working agreement, the ask-first rule, the short-chat
  rule — are the same for both tools. There is no Codex-specific variant, on purpose:
  two files that say almost the same thing drift, and then agents disagree.
- Everything `AGENTS.md` points at: `CURRENT_CHECKPOINT.md`'s "Active state at a glance"
  block, `plan.md` sections 5/6/7 and the current phase, `CHANGELOG.md`'s inventory
  (searched, not read), `docs/README.md`, `docs/INTERNALS.md`,
  `docs/decisions/0001-owner-goals-and-priorities.md`.

**Never hand-edit `AGENTS.md`.** Edit `CLAUDE.md` and run
`python tools/jumpstart.py sync-agents .`. A Codex session that edits `AGENTS.md`
directly has forked the rules; `jumpstart.py check .` fails on the sha256 mismatch, which
is how it gets caught.

## Native roles and model routing

For example, JumpStarter uses `gpt-6-astra` for its lead, `gpt-5.6-terra` for
substantive roles and `gpt-5.6-luna` for recon; choose this project's models explicitly.

`.codex/config.toml` holds `{{CODEX_LEAD_MODEL}}` for a new lead, enables agents, and
sets `{{CODEX_STRONG_MODEL}}`/high as the fallback route. Tester, builder and reviewer
use `{{CODEX_STRONG_MODEL}}` at high effort; recon uses `{{CODEX_CHEAP_MODEL}}` at
medium. Defaults do not switch a running session or override an explicit UI choice.

Codex does not read `.claude/settings.json`; its own sandbox and approval settings
apply. Anything the Claude allow-list treats as destructive is still destructive.

## Handing a packet to Codex

The packet format is tool-neutral (`.claude/packets/PACKET_TEMPLATE.md`). To run a native role in a
Codex session:

1. Start at the repo root, on the packet's branch (`{{BRANCH_PREFIX}}<slug>`), in its own
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

Disclose the limitation once. Read the tracked TOML, then pass its model, effort,
developer instructions, packet and isolated worktree path to the generic spawner with
`fork_turns="none"`. Label it an **adapted role run**; it does not close a native-role
gate. Never silently use inherited lead-model workers. If spawning is unavailable,
report the blocker.

## What stays the same in both tools

- The bounded read comes before the first edit.
- Fail-before-fix is proven, not claimed.
- Review is by reproduction, not by reading.
- Live stores are read-only unless the packet names the write.
- One checkout, many agents: worktrees for builders and reviewers, and nobody switches
  the main checkout's branch while {{PROJECT}} runs from it.
- Chat is short; detail lives in commits, docs and handoffs.
- `{{OWNER}}` decides restarts, promotions and priorities.
