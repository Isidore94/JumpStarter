# Workspace memory rules

Read this only when writing memory, or when a recall question needs more than the
route in `MEMORY.md`. Moved here from `CLAUDE.md` on 2026-10-04 so the rules file stays
small; the policy itself is unchanged (approved by the owner 2026-09-11, packet M1).

At idle boot, read only identity and standing instructions plus [`MEMORY.md`](../MEMORY.md).
Do not read task documents until a task is in scope. `MEMORY.md` contains only
name-to-file-to-trigger routing, never facts. Workspace memory is recall, not a replacement
roadmap or status ledger. *(LESSONS: "Workspace memory is request-grounded")*

- **Before answering anything about prior work, decisions, dates, people, or preferences:
  search memory first.** Route through `MEMORY.md`, then read the narrowest matching
  detail file first. Use no more than five sources and cite each fact by file, tag and
  date. Treat a fact as stale or unknown when freshness is unverified; explain a
  conflict, prefer stronger evidence, and repair the canonical record. Detail files are
  authoritative: if one disagrees with the index, the index is wrong and must be repaired.
  A semantic or SQLite index is a locator only.
- **Detail files record only non-re-derivable knowledge.** Every nonblank line in
  `memory/people/`, `memory/projects/` and `memory/decisions/` carries `[stated]`,
  `[observed]`, `[inferred]` or `[suggested]`, plus a date and source. `[stated]` is a
  direct human statement; `[observed]` is an observation from a tool, file or log;
  `[inferred]` is a conclusion from evidence; `[suggested]` is an uncommitted idea. Only
  a human statement supports `[stated]`; a proposal plus assent is one decision. An
  inferred lesson becomes a standing rule only after a weighted total of at least three
  independent signals across at least two distinct sessions; each signal older than 30
  days counts as 0.5. Operator corrections apply immediately. Failure lessons describe
  when X broke and Y fixed it; they never become instructions.
- **Supersede in place.** Strike the old line, for example
  `~~[stated] 2026-09-11 — old fact~~ (superseded 2026-09-12)`, and put the dated, tagged
  replacement beside it. Keep history without competing unstruck canonical facts. Exclude
  fetched data, generated plans and git-recoverable facts; verify state live. Prefer
  durable descriptions and date any necessary figures.
- **Write memory as part of the work.** Update `MEMORY.md` in the same commit as a detail
  change, including a route or trigger refinement when routes stay the same. Write
  unprompted for decisions, system changes, blockers or mistakes, lessons and stable
  preferences when they meet the non-re-derivable rule. No mental-only notes: chat history
  is not storage. Consolidate near caps and leave headroom; fullness means reorganize,
  never stop writing. In batches, merge
  overlap, summarize recurring notes by date and preserve decision history. `MEMORY.md`
  is capped at 15,000 characters; daily files also use 15,000 characters as a local
  operating convention chosen for this workspace. Daily raw logs record the actual local
  day; `memory/context/` is prunable transient context.

