# QA Type: Pre-Banger Disregard

Generate single-turn questions only about what the user would likely handle
without help.

Good questions ask whether the user would notice, remember, check, avoid,
postpone, or self-solve the concern. Do not ask whether the moment is timely,
whether the user would click, or what artifact should be created.

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
