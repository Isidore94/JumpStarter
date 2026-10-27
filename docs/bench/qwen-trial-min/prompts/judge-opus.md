You grade one code change, blind. You get: the brief, the candidate diff (with its tests),
the candidate's self-review, the lead's test results (own tests, hidden reference tests run
against the candidate, lint), and the REFERENCE diff, which is the change the project actually
merged for the same brief. The reference is a yardstick, not the only right answer: a different
design that meets the brief and passes the reference tests scores fully.

Score 0-3 each (3 = as good as or better than the reference):
- correctness: does it do what the brief asks, including edge cases the reference handles
- completeness: every item in the brief covered (name any missing)
- tests: fail-before-fix, assert the behaviour not the implementation, cover the edge cases
- scope: 3 = only what the brief needs; subtract for unrelated edits or churn
- brief_awareness: did the candidate notice and handle mistakes or gaps in the brief itself
- self_review: did its self-review find real problems; was its GO / NO-GO right
- trading_risk: 3 = no way this loses money or mis-sizes an order if merged as is; 0 = it
  would (score 3 and write n/a in notes when the repo is not a trading system)

Verdict: MERGE (ship as is), MINOR (ship after small fixes you can name), MAJOR (needs
rework), REJECT (wrong or harmful). Return ONLY JSON:
{"correctness":N,"completeness":N,"tests":N,"scope":N,"brief_awareness":N,"self_review":N,
 "trading_risk":N,"verdict":"...","notes":"3-6 sentences: the decisive facts, with file:line"}
