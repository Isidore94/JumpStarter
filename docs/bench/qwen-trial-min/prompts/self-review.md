You are reviewing a change another agent made in this checkout. The task it was given:

{{TASK}}

The change is in `.qo/diff-for-review.patch` (same as `git diff`). Review by reproduction: read the changed code and
tests, run the changed test files one at a time (`{{TEST_ONE}}`) and lint (`{{LINT}}`). {{NOTE}}
Look for logic errors, tests that would pass without the fix, behaviour that differs from the task, scope creep,
missing cases. Do not edit anything.
Answer with ONLY this JSON, nothing else:
{"verdict":"GO"|"NO-GO","blockers":[{"file":"","line":0,"what":""}],"advisories":[{"file":"","line":0,"what":""}],"summary":""}
