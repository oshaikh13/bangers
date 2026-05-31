# QA Type: Pre-Banger Surprise

Generate single-turn questions about useful non-obvious angles whose timing may
or may not justify intervention.

Good questions ask what connection, reframing, or synthesis the user is unlikely
to notice unaided, and whether surfacing that angle now would help or interrupt.
The answer should still be grounded in visible context and future evidence, not
weirdness for its own sake.

Avoid questions that simply ask for the next obvious task or a clever artifact
idea detached from timing.

Generate exactly `{pairs_per_run}` Q/A pairs unless fewer are honestly
groundable. Never generate fewer than 3.

Return JSON only:

```json
{
  "qa_type": "{qa_type}",
  "seed_id": "string",
  "banger_timestamp": "string",
  "target_banger": {},
  "context_events": [],
  "qa_pairs": []
}
```
