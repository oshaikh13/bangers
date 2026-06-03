# QA Type: Hypothetical

Generate simple "if X, what will the user do?" questions.

The condition must be generic or visible in `context_events`. Do not leak a
future-only concrete event into the question. Good conditions are things like
an interruption, a failed test, an assistant suggestion, a pending reply, or a
choice between already-visible options.

Use future logs to answer what the user actually does in similar or immediate
conditions.
