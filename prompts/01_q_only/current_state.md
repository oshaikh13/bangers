# QA Type: Current State

Generate questions about what the user is doing right now: active goal,
working set, frustration, uncertainty, open artifact, or immediate next step.

Use the tail of the 100 context events heavily. The answer can be `H` if it is
pure current-state synthesis, or `H+F` when future logs verify the current
state interpretation.

Keep questions general enough to be useful across many assistants:
"What is the user trying to do right now?" is often good.
