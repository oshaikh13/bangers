# QA Type: Dropped Commitments

Generate questions about visible commitments, plans, or tasks whose outcome is
uncertain: they may slip, remain unacted-on, get deferred, or be followed
through after some delay.

Only ask when an open item is visible in `context_events` — an unanswered
message, in-progress doc, or stated intent. Prefer questions where the answer
can distinguish among follow-through, partial follow-through, deferral, and
non-action. Answers should explain the observed outcome and the most concrete
reason visible from behavior. Avoid guilt-heavy or speculative phrasing.

Across a batch, include cases where the user follows through when those are
honestly groundable; do not make every example a dropped or deferred commitment.

Most answers should use `answer_basis: "H+F"`.
