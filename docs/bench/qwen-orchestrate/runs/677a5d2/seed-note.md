# Seed note: run 677a5d2

**The bug.** `HTML_COMMENT_RE` is made greedy (`<!--.*-->` instead of `<!--.*?-->`, with
`re.DOTALL`), so `_strip_html_comments` deletes everything from the first `<!--` in
`CLAUDE.md` to the last `-->`, not each comment on its own. Every live citation between two
comments disappears before matching, and a dangling one is reported as resolving.

**Input that exposes it.** A freshly `init`-ed project that adds a rule where the template
tells it to: between the `<!-- Add rules as they are learned ... -->` comment and the
`<!-- one rule per line, same shape -->` comment under the rules heading, for example
`- **New.** a learned rule. *(INTERNALS: "no such entry")*`. With the seed, `check` prints
`[OK] INTERNALS citations: all 3 citations resolve`. Without it, it prints
`[MISSING] cited entry "no such entry"`. The same happens in unit form:
`find_internals_citations('<!-- a -->\n*(INTERNALS: "x")*\n<!-- b -->\n')` returns `[]`
instead of `["x"]`.

**How a reviewer finds it.** Read the comment regex: a DOTALL `.*` with no `?` spans from
the first opener to the last closer. Then look at `templates/CLAUDE.md`: it ships three
HTML comments, and the space between the first and the third is exactly where a project's
learned rules go. That is the one place the check matters most.

**Why the tests miss it.** The only comment-skipping test
(`test_internals_citations_fold_wrapped_names_and_skip_comments`) has a single comment,
followed by the live citation, and greedy and lazy behave the same on one comment. The
`filled_repo` check tests use the unmodified template, where nothing live sits between the
comments. Its three live citations are outside that span, so the count and the OK both hold.
No test puts a citation between two comments.
