# QA Type: Pre-Banger Value

Generate single-turn questions only about how worthwhile proactive help would
be for the user here.

Every question must explicitly ask for an estimate on a `1 to 100` scale and
ask for the reason. Keep the question generic: it should be a close rephrase of
"estimate on a 1 to 100 scale how worthwhile proactive help would be here, and
give the reason." Do not start questions with a context-preface such as "After
the user...", "When the user...", or "With the user...".

Use natural phrasing such as:

- "Estimate on a 1 to 100 scale how worthwhile proactive help would be here,
  and give the reason."
- "On a 1 to 100 scale, how much value would help add for the user here, and
  why?"
- "Estimate how worth surfacing this is on a 1 to 100 scale, with the reason."
- "On a 1 to 100 scale, how worthwhile would proactive help be here, and why?"

Every answer must start with the numeric estimate followed by a period, then
the reason:

- `92. The user appears to be juggling scattered context, so proactive
  synthesis would likely save meaningful effort.`
- `54. There is some visible friction, but the stakes and marginal benefit are
  not yet clear.`
- `12. The user is already driving the next step, so help would mostly restate
  an obvious action.`

Use the hidden `ranking_metadata.value_estimate` as the answer's numeric
estimate. Use `ranking_metadata.rank_percentile`, `user_value`,
`intervention_value_now`, `negative_reason`, and `marginal_value_reason` only
to calibrate the reason.

Calibration should be continuous:

- 90-100: strongly worthwhile.
- 70-90: worthwhile, with a concrete value signal.
- 45-70: mixed or conditional.
- 20-45: limited value.
- 1-20: not worth surfacing.

Keep this lane distinct:

- Value asks whether help is worth surfacing for this user.
- Timing asks whether this moment is open.
- Disregard asks whether the user would handle it without help.
- Curiosity asks what uncertainty is visible.

Anti-leak rules:

- Questions and answers must not say "value percentile", "rank", "ranking
  metadata", "seed quality", or describe hidden banger details.
- Do not summarize the hidden artifact.
- Do not name hidden artifact nouns unless they already appear in
  `context_events`.
- Explain the score through observable user state: attention, stakes, urgency,
  friction, risk, likely engagement, and marginal value.

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
