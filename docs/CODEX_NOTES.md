# Working on JumpStarter with Codex

Document role: **active runbook.** What a Codex session reads in this repo, what it
cannot do, and how the same work packets reach it.

The generic version that ships to other projects is `templates/codex/CODEX_NOTES.md`.

## What Codex reads

- **`AGENTS.md` at the repo root** — a byte-identical generated copy of `CLAUDE.md`, so
  the operating rules are the same for both tools. There is no Codex-specific variant, on
  purpose: two files that say almost the same thing drift, and then agents disagree.
- Everything `AGENTS.md` points at: `CURRENT_CHECKPOINT.md`'s "Active state at a glance"
  block, `plan.md` sections 5/6/7 and the current phase, `CHANGELOG.md`'s inventory
  (searched, not read), `docs/README.md`, `docs/INTERNALS.md`, `PRINCIPLES.md`, and
  `docs/decisions/0001-owner-goals-and-priorities.md`.

**Never hand-edit `AGENTS.md`.** Edit `CLAUDE.md` and run
`python tools/jumpstart.py sync-agents .`. `check .` fails on the sha256 mismatch, which
is how a hand-edit gets caught.

## What Codex cannot do here

- **It does not read `.claude/agents/`.** No automatic `builder`, `reviewer` or `recon`
  sub-agents. The roles still apply; they are enacted by hand (below).
- **It does not read `.claude/settings.json`.** The command allow-list does not apply;
  approvals work through Codex's own sandbox settings. What the allow-list treats as
  destructive is still destructive.
- **It does not read `.claude/packets/`** unless you point it at a packet path
  explicitly. Do that — the packet is the specification.

## Handing a packet to Codex

The packet format is tool-neutral (`templates/.claude/packets/PACKET_TEMPLATE.md`). To
run one role in a Codex session:

1. Start at the repo root, on the packet's branch (`claude/<slug>`), in its own worktree
   if another session is running.
2. Give it, in this order: the role brief (paste the body of `.claude/agents/builder.md`,
   `reviewer.md` or `recon.md` — skip the YAML front matter, which is Claude Code
   metadata), then the packet file, then the branch name.
3. Require the same output format the role file specifies: the builder's handoff block,
   the reviewer's GO / NO-GO block, or recon's evidence-first report. **The formats are
   the interface between tools** — a Codex builder's handoff must be readable by a Claude
   Code lead, and the reverse. `plan.md` phase 1 item 2 is the gate that proves this
   actually works; until it passes, treat the crossing as unproven.

One packet, one session, one role. A session that builds and then reviews its own work is
not a review.

## What stays the same in both tools

- The bounded read comes before the first edit.
- Fail-before-fix is proven, not claimed.
- Review is by reproduction, not by reading.
- One checkout, many agents: worktrees for builders and reviewers.
- Chat is short; detail lives in commits, docs and handoffs.
- The owner decides priorities and promotions.
