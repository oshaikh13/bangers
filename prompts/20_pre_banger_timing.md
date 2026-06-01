# QA Type: Pre-Banger Timing

Generate single-turn questions only about the user's receptivity window.

Good questions ask whether this exact moment is open, premature, stale, or too
focused for brief help. Do not ask what the user will do themselves, whether
they would click, or what hidden artifact would be useful; those belong to other
QA types.

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
