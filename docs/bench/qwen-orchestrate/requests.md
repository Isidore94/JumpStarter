# Raw requests (what Aaron would have typed), one per replayed commit

The reference answer is the real commit's diff (base..ref). The brief writer (Opus 5.5 high) saw only the request
and the tree at `base`; the orchestrator under test (Qwen 3.8 27B fp4) saw only the brief and the tree at `base`.

| sha7 | repo | base | ref | request |
|---|---|---|---|---|
| 677a5d2 | JumpStarter | 85b8474 | 677a5d2 | `check` should fail when CLAUDE.md cites an INTERNALS entry that doesn't exist in docs/INTERNALS.md. Right now retrofit only checks that the file exists, it never reads it. |
| d756e9d | TraderTaxHelper | 56c399a | d756e9d | The Summary should show P&L before commissions and the commissions paid for the year's closed trades, with the taxable share. Commissions must stay deducted in the taxable P&L, and the card should say not to add them again as an expense. |
| 91eb9b8 | EveTradingbot | 20be217 | 91eb9b8 | Every hauling scan ends NO_ROUTE with "current system 30000142 is not in the stargate graph" even though the SDE build in the footer looks current. The stargate and npc station tables are empty. Reload the SDE when a table is empty, whatever the build stamp says. |
