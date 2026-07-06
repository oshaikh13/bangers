# QA Type: Recall

Generate past-tense questions about what already happened before
`qa_timestamp_ts`.

Answers must use `answer_basis: "H"` and `verify_at_ts` before the QA
timestamp. Use recall questions to extend the visible time horizon backward:
ask about concrete things the user did before the current interval, including
specific artifacts, apps, messages, pages, files, task steps, decisions, or
working context when those details are grounded in the past context.

Do not inspect future logs for recall answers.
