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

## What Codex cannot do here

- **It does not read `.claude/agents/`.** There are no automatic `builder`, `reviewer` or
  `recon` sub-agents. The roles still apply — they are enacted by hand (below).
- **It does not read `.claude/settings.json`.** The command allow-list does not apply;
  approvals work through Codex's own sandbox and approval settings. Anything the
  allow-list treats as destructive is still destructive.
- **It does not read `.claude/packets/`** unless you point it at a packet path
  explicitly. Do that — the packet is the specification.

## Handing a packet to Codex

The packet format is tool-neutral (`.claude/packets/PACKET_TEMPLATE.md`). To run one
role in a Codex session:

1. Start the session at the repo root, on the branch for the packet
   (`{{BRANCH_PREFIX}}<slug>`), in its own worktree if another session is running.
2. Give it, in this order: the role brief (paste the body of
   `.claude/agents/builder.md`, `reviewer.md` or `recon.md` — skip the YAML front
   matter, which is Claude Code metadata), then the packet file, then the branch name.
3. Require the same output format the role file specifies: the builder's handoff block,
   the reviewer's GO / NO-GO block, or recon's evidence-first report. **The formats are
   the interface between tools** — a Codex builder's handoff must be readable by a Claude
   Code lead, and the reverse.

One packet, one session, one role. A session that builds and then reviews its own work
is not a review — the second proof exists because the first is done by the party most
motivated to see it succeed.

## What stays the same in both tools

- The bounded read comes before the first edit.
- Fail-before-fix is proven, not claimed.
- Review is by reproduction, not by reading.
- Live stores are read-only unless the packet names the write.
- One checkout, many agents: worktrees for builders and reviewers, and nobody switches
  the main checkout's branch while {{PROJECT}} runs from it.
- Chat is short; detail lives in commits, docs and handoffs.
- `{{OWNER}}` decides restarts, promotions and priorities.
