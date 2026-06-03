# QA Type: Activity Window

Generate questions of the form "What will the user do in the next [window]?"

Use future logs to answer with a concise timeline of the user's actual activity
in that window. Vary the window across pairs: 5, 10, 15, or 30 minutes; 1 or
2 hours; rest of today; tomorrow; this week.

Answers should be specific enough to train prediction, but not overloaded with
minute-by-minute trivia for long windows.

Use `answer_basis: "F"` unless the answer also depends on past context.
