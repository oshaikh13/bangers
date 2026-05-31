# QA Type: Pre-Banger Engagement

Generate single-turn questions about whether the user would engage with an
assistant intervention at this moment.

Good questions distinguish "technically useful" from "the user would engage
with this now." Ask about acceptance, attention, likely click-through, what
would make help feel immediately worth opening, and what would make the user
ignore it because they are already doing the work or are in a focused loop.

Do not ask how to structure a report unless structure is the reason the user
would engage or the reason the assistant should wait.

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
