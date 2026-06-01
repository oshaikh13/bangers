# QA Type: Pre-Banger Curiosity

Generate single-turn questions only about the uncertainty, concern, or
ambiguity the user is revealing.

Good questions ask what the user seems curious, unsure, or worried about from
the visible context. Do not ask whether the assistant should help now, whether
the user would engage, or whether the user would handle it themselves; those
belong to other QA types.

Generate exactly `{pairs_per_run}` Q/A pairs unless fewer are honestly
groundable. Never generate fewer than 3.

Return JSON only:

```json
{
  "qa_type": "{qa_type}",
  "seed_id": "string",
  "banger_timestamp": "string",
  "target_banger": {},
  "qa_pairs": []
}
```
