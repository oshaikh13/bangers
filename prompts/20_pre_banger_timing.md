# QA Type: Pre-Banger Timing

Generate single-turn questions about whether now is a good intervention moment.

Good questions ask whether the assistant should surface help now, wait, or stay
quiet; what is becoming timely; what would be too early; what would soon be too
late; and what the user is likely to do next without help. Keep the focus on
marginal value and receptivity, not scheduling mechanics or artifact format.

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
