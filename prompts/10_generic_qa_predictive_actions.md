# QA Type: Predictive Actions

Generate future-predictive questions about what the user will do next: which
file, repo, app, message, decision, search, or path they will choose.

Keep each question generic or grounded in something visible in `context_events`.
Good questions ask for the next action, next artifact, next reply, next file,
or next decision. Avoid questions that require several named entities.

Use `answer_basis: "F"` or `"H+F"`.
