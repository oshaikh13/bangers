# QA Type: Todo

Generate questions about what is on the user's plate: pending tasks, items they
will complete, or what they still need to handle. Candidate todos referenced by
the question must be visible in `context_events` (a stated intent, in-progress
artifact, or scheduled item) — or the question must be phrased generically.

Prefer simple horizons: right now, next hour, today, tomorrow, this week.
Ground completion or non-completion in future logs when needed. Do not treat an
email-only ask as a todo unless screen, audio, calendar, or filesys evidence
corroborates it.

Use numbered-list answers with compact status tags such as `[pending]`,
`[in-progress]`, `[scheduled]`, or `[done]`.
