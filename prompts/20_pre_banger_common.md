# Task

Generate Q/A pairs for a user-model training set. This is pipeline `20`:
pre-banger QA for timing-sensitive proactive intervention.

The user model will see only:

```text
context_events + question
```

It must answer from those visible past events. You, the labeler, may inspect
the wider `logs-indexed/` folder, including future events, to produce the gold
answer. The final training export will drop all metadata except the past
context, question, and answer.

## Target

The target QA type for this run is:

`{qa_type}`

You are also given a hidden historical banger seed with ranking metadata. Use
it as supervision for whether an assistant intervention would have high
marginal value at this moment. Do not reveal that seed mechanically in every
question. The questions should teach the user model how to infer whether to
surface help now, wait, or stay quiet.

Good answers should usually explain:

- What the user is likely to do next without help.
- Whether now is a good time to surface proactive help.
- What marginal value the assistant would add beyond the user's likely next
  action.
- Why the user would engage, ignore it, or be interrupted by it.
- Why the user probably would or would not assemble the same synthesis
  themselves.
- What non-obvious connection, risk, timing window, or reframing makes the
  intervention valuable.

Do not anchor questions on artifact shape. Avoid questions about sections,
schemas, document types, or deliverable formats unless that is essential to the
timing judgment. Prefer "should the assistant surface anything now?" over "what
document should be created?"

## Hidden Seed Banger

```json
{seed_json}
```

## Training-Visible Context Events

These are the past indexed events visible to the user model. They are already
limited to the latest 100 events with `ts <= banger_timestamp`.

```json
{context_events_json}
```

## Required Grounding

- Every concrete noun in a question must appear in the past context events,
  unless the question is phrased generically.
- Use `logs-indexed/` to inspect broader past and future logs as needed.
- Future-grounded answers must read like predictions made from "now"; do not
  say "future logs show", "later", "in hindsight", or similar.
- History-grounded answers must use only events before `banger_timestamp`.
- Do not ask multiple-choice questions.
- Do not ask compound questions.
- Keep questions short and natural.
- Prefer questions that help a banger generator decide whether intervention has
  marginal value now, not questions that merely specify a document.
- It is valid for an answer to say the assistant should wait or stay quiet.
- Calibrate answers to the hidden ranking metadata. High intervention-value
  seeds should sound clearly worth surfacing now; low intervention-value seeds
  should explain why the idea is useful but poorly timed, obvious, or likely to
  be done by the user anyway.
- When ranking metadata includes `negative_reason`, use it to make negative
  answers specific: self-done, obvious next step, interruptive, undergrounded,
  or stale. Negatives should often mean "good idea, bad intervention moment,"
  not "bad idea."

## Perspective

Questions are asked about the user from an outside observer. Always phrase the
question in third person about "the user". Never use first person.

- Bad: "What would I want to see?"
- Bad: "Would I open this?"
- Good: "Is now a good moment for the assistant to help?"
- Good: "What is the user likely to do next without help?"
- Good: "Would surfacing help now interrupt the user's flow?"
- Good: "Would the user likely make this themselves?"

Answers should also speak about the user in third person.

## Output Fields

Each Q/A pair must include:

```json
{
  "q_id": 0,
  "question": "string",
  "answer": "string",
  "category": "{qa_type}",
  "timescale": "micro | short | medium | long",
  "answer_basis": "H | F | H+F",
  "verify_at_ts": 123.0,
  "verify_at_iso": "ISO timestamp",
  "question_basis": {
    "context_event_indexes": [0],
    "reason": "why these past events make this question askable"
  },
  "why_it_matters": "why this helps a banger generator",
  "evidence_grounding": "brief private evidence summary; may mention broad past/future log evidence",
  "question_difficulty": 1
}
```

`answer_basis` rules:

- `H`: answer uses only events before the banger timestamp; `verify_at_ts` must
  be before the banger timestamp.
- `F`: answer uses events at or after the banger timestamp; `verify_at_ts` must
  be at or after the banger timestamp.
- `H+F`: answer combines past context with future verification; `verify_at_ts`
  must be at or after the banger timestamp.

`timescale` rules:

- `micro`: up to 30 minutes
- `short`: 30 minutes to 2 hours
- `medium`: 2 hours to 24 hours
- `long`: more than 24 hours

Read the QA-type-specific instructions below and follow them for this run.
