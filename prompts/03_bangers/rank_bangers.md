# Task

You are ranking historical banger seeds for stage `03_bangers`, producing the
ranked seed list consumed by `05_q_to_b`.

The goal is to create a scored seed list that teaches a user model when a
proactive assistant intervention would have high marginal value for the user.
Do not merely sort by the original numeric fields. Read the candidate bangers,
inspect `logs-indexed/` around and after their timestamps, and decide:

- Would the idea be useful to the user at all?
- Was this a good moment to surface it?
- Would the user probably do the same thing next without help?
- Would surfacing it now interrupt flow, add noise, or feel premature?
- Would the assistant notice a timely synthesis, risk, contradiction, or
  framing that the user was unlikely to assemble themselves?

## Input Bangers

Read the combined banger seed file at this path:

```text
{combined_bangers_path}
```

The file contains a top-level `seeds` array. Each seed already has its
canonical `seed_id`, source indexes, original banger metadata, and hidden
`target_banger`. Rank across every seed in this file as one interval-range run.

Each seed includes the original banger scores and metadata. The scores are
useful hints, not the final answer. You may use subagents to help rank and 
search the logs.

## Scoring Criteria

Score each seed on two primary axes:

`user_value`: how useful, cool, personally relevant, or clarifying this idea
would be if the user engaged with it.

`intervention_value_now`: how valuable it would have been for the assistant to
surface this now, given timing, attention, likely next actions, and whether the
user would do it themselves.

High `user_value` but low `intervention_value_now` is possible. For example, an
idea can be useful but badly timed because the user is already doing the next
step, is in a fragile execution loop, or needs to finish the current action
before synthesis would help.

High `intervention_value_now` seeds often have:

- Scattered evidence the user is unlikely to synthesize in the moment.
- A live contradiction, risk, trust issue, or timing window the assistant can
  clarify before it decays.
- A personally relevant cross-thread connection the user has not yet noticed.
- A repair or admin loop where a boundary-setting intervention would prevent
  further drift.
- Future evidence that the user kept circling the topic without assembling the
  useful synthesis themselves.

Low `intervention_value_now` seeds often have:

- The user is already doing the same thing immediately.
- The suggestion would mostly narrate an obvious next chore.
- The current flow is too focused for interruption to add value.
- The idea is interesting but not grounded enough yet.
- The value depends mostly on artifact formatting or generic checklisting.

Examples of seed types that often fit: stabilization charters, lodging
reconciliation, sandbox trust explanations, Simile evidence addenda, field-debug
kits, positioning memos, cautious claim maps, and source-backed contradiction
resolutions.

Examples that often have low intervention value now: immediate repair tasks the
user already drove, command cards the user manually wrote or asked for, and
obvious implementation chores.

## Intervention Posture

Assign one posture:

- `surface_now`: the assistant should probably surface help at this moment.
- `wait`: the idea may become useful, but this exact moment is not right.
- `stay_quiet`: proactive help would likely add little value or interrupt.

Assign one `negative_reason`:

- `none`: this is a positive surface-now example.
- `self_done`: the user is likely to do the same useful thing without help.
- `obvious_next_step`: the idea is only the next visible chore.
- `interruptive`: surfacing help now would break a focused or fragile flow.
- `undergrounded`: the idea is cool but not justified by visible context yet.
- `stale`: the need is already handled or no longer timely.

## Output

Write JSON only:

```json
{
  "seeds": [
    {
      "rank": 1,
      "seed_id": "29_0_0",
      "user_value": 1,
      "intervention_value_now": 1,
      "intervention_posture": "surface_now",
      "negative_reason": "none",
      "engagement_pull": 1,
      "surprise": 1,
      "personal_relevance": 1,
      "disregard": 1,
      "grounding": 1,
      "self_done_penalty": 1,
      "timing_reason": "why this is or is not a good moment to intervene",
      "marginal_value_reason": "what the assistant adds beyond what the user is likely to do next",
      "self_done_reason": "whether the user would probably do the same thing without help",
      "future_check": "what future logs show about timing, follow-through, or self-done behavior",
      "notes": "optional short note"
    }
  ]
}
```

Include every candidate seed exactly once, best intervention moments first
within this interval-range run. Do not use `keep`, `downrank`, or any binary inclusion
label. Low-ranked seeds are still useful as negative examples because their QA
answers should teach the model why the assistant should wait or stay quiet.
