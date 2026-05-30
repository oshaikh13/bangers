# QA Type: Recall

Generate past-tense questions about what already happened before
`qa_timestamp_ts`.

Answers must use `answer_basis: "H"` and `verify_at_ts` before the QA
timestamp. Prefer synthesis over trivia: how the user spent a period, what they
last touched, what style they used, what projects dominated, or what caused a
recent switch.

Do not inspect future logs for recall answers.
