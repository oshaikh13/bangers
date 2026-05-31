# QA Type: Pre-Banger Disregard

Generate single-turn questions about whether the user probably will or will not
do the useful thing without help.

Good questions ask what the user is likely to avoid, postpone, skim past,
manually debug around, leave scattered, or conversely complete themselves in the
next few actions. Answers should explain how self-done likelihood changes the
value of surfacing help now without implying blame.

Prefer marginal-value answers: what would be worth surfacing because the user
would not assemble it themselves, and what should not be surfaced because the
user is already on track to do it.

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
