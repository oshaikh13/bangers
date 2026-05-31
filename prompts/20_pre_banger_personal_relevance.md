# QA Type: Pre-Banger Personal Relevance

Generate single-turn questions about whether the user's current priorities,
taste, worries, collaborators, recurring projects, or style of working make
this a good intervention moment.

Good questions ask why this would matter to this user now, and whether that
personal relevance is strong enough to justify surfacing help before the user
asks. The answer may name current projects or people only when they appear in
the visible context events. Prefer concrete behavioral relevance over
personality speculation.

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
