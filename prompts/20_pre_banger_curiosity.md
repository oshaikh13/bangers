# QA Type: Pre-Banger Curiosity

Generate single-turn questions about when a curiosity hook would be worth
surfacing now.

Good questions identify hooks the user would be curious to inspect, but also
ask whether the timing makes that hook useful or distracting. Strong hooks
include a contradiction, hidden connection, source-backed answer to a nagging
question, surprising comparison, or concrete thing that resolves ambiguity.
Avoid asking for artifact sections or format.

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
