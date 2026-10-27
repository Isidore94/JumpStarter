# qwen-trial-min: requests and minimal briefs

Lead: Fable 5.1. Method: the request is what Aaron would have typed (the merged commit's message, in plain words); the
brief is that request cleaned into 5-8 lines: goal, done-when, files only if already known else "find it", a
don't-touch list, one pattern line. No recon before the brief: one grep per repo for names, no look at the reference
diff. Lead time is wall-clock from opening the commit messages to the brief files being written, per batch.

## Batch 1 (tasks 1-5, non-TradingBotV3), 2026-10-27 09:42:03-09:46:37 PT

Five briefs in 4.5 minutes of lead time: one Bash call for the five commit messages and greps (about 2k tokens read),
one call writing the five briefs (about 2.5k tokens written). Under a minute and well under 1k output tokens per brief.

1. cs-108c631 (ContentSummarizer, parent 6597749, M). Request: "the web page goes stale; add refresh-now and an
   auto-refresh choice off/15/30/60 s remembered per browser, pause it while I'm typing, don't let a tampered cookie
   loop it, and cache the GPU badge so auto-refresh doesn't pay the probe; routing must still probe live."
   Brief: briefs/cs-108c631.md (6 lines).
2. eve-66905ff (EveTradingbot, parent cbbbf61, S). Request: "net_edge flatters wide books: it subtracts two
   percentages measured against different reference points; price the real round trip multiplicatively so a wide
   book stops ranking first; a flat book at value nets exactly -tax." Brief: briefs/eve-66905ff.md (5 lines).
3. eve-ce70d4c (EveTradingbot, parent 0edd59c, S). Request: "when my avoid list severs a pair, hauling says blocked
   by security, which I can't act on; name the constraint that actually cut it." Brief: briefs/eve-ce70d4c.md (5 lines).
4. js-96eb4eb (JumpStarter, parent d3c3f81, M). Request: "set up the native Codex lead config (Astra high, Terra
   fallback) and give the four Codex role TOMLs name/description so Codex can pick them; init installs it, check and
   retrofit report it missing." Brief: briefs/js-96eb4eb.md (5 lines).
5. tth-56c399a (TraderTaxHelper, parent ea5254e, M). Request: "IBKR fixes: assigned/exercised option premium goes
   into the share cost/proceeds, commission rebates are money in, O/C warning fixes, job payroll CPP credited first,
   and a job-income box on the summary page." Brief: briefs/tth-56c399a.md (5 lines).

## Batch 2 (tasks 6-10, TradingBotV3), 2026-10-27 10:38:40-10:41:03 PT

Five briefs in 2.5 minutes of lead time: one Bash call reading the five commit messages (about 2k tokens), one grep call for module names at the parent commits (about 0.5k tokens), five Write calls (about 3k tokens written). These briefs are longer (6 lines each, but the goal line is dense) because the trader's commit messages carry the spec in his own words; nothing was taken from the diffs.

6. tbv3-243279e2 (parent 8dd4110). Request: "the tape light should use SPY's own M5 range vs its hour norm, TICK only as the fallback; measured it, SPY is the cleanest signal. keep thresholds, monitor writes market.tape fail-open, chip says tape fast/normal/calm". Brief: 6 lines.
7. tbv3-b4c56626 (parent a079383). Request: "trader fit step 4: flag the M30 extended pullback, my favourite. rows whose only hard no's are the two extension rules get one batched M30 fetch and the pullback alert's own rule; waive the rules and add the bonus; None on failure never a failed scan; replay and backfill do not fetch". Brief: 6 lines.
8. tbv3-4b830d03 (parent 7d02841). Request: "the bounce alert letter does not separate outcomes; show a setup tier A-D from hour, family, sector RRS and tape vs side, keep the learning letter beside it". Brief: 6 lines.
9. tbv3-51c27bf1 (parent 9c894a0). Request: "the bounces failing read must work for shorts too and say whether levels hold in general: support and resistance sub-reads, new verdict words, chip and mentor row updated". Brief: 6 lines.
10. tbv3-697d8828 (parent bbfab10, stretch). Request: "swing focus SMA guard: the daily 50/100/200 SMAs a name is above when it joins are its guard, a completed D1 close through one prunes it, shorts mirrored, swing list only". Brief: 6 lines.
