# Task

Generate Q/A pairs for a user-model training set. This is stage `05_q_to_b`:
pre-banger QA for timing-sensitive proactive intervention, using banger seed
rankings produced by `03_bangers`.

The user model will see only:

```text
context_events + question
```

It must answer from those visible past events. You, the labeler, may inspect
the wider `logs-indexed/` folder, including future events, to produce the gold
answer. The final training export will drop all metadata except the past
context, question, and answer. You may use subagents to help.

## Target

The target QA type for this run is:

`{qa_type}`

You are also given a hidden historical banger seed with ranking metadata. Use
it as supervision for whether an assistant intervention would have high
marginal value at this moment. Do not reveal that seed mechanically in every
question. The questions should teach the user model how to infer the user's
state: attention, preferences, beliefs, receptivity, and likely next behavior.

Answers must be concise: usually 1-2 short sentences. Focus on what the user
seems to care about, believe, notice, tolerate, or do next. Do not enumerate the
hidden banger artifact, write an implementation plan, or explain the full
suggestion unless the question truly requires it.

For yes/no questions, answer with the judgment first, then the user-state
reason. Prefer answers like: "Yes. The user seems to care about avoiding data
loss, and they are already asking about cleanup."

Do not anchor questions on artifact shape. Avoid questions about sections,
schemas, document types, or deliverable formats unless that is essential to the
user-state judgment.

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
- Ask only within the QA type's lane. Do not reuse generic intervention
  questions that belong to another type.
- Only timing-lane questions should directly ask whether the assistant should
  surface, wait, or stay quiet. In threaded output, that belongs in the
  receptivity thread.
- Calibrate answers to the hidden ranking metadata. High intervention-value
  seeds should sound like a clearer user-state signal; low intervention-value
  seeds should explain why the same topic is poorly timed, obvious, or likely
  to be handled by the user anyway.
- When ranking metadata includes `negative_reason`, use it to make negative
  answers specific: self-done, obvious next step, interruptive, undergrounded,
  or stale. Negatives should often mean "good idea, bad intervention moment,"
  not "bad idea."

## Perspective

Questions are asked about the user from an outside observer. Always phrase the
question in third person about "the user". Never use first person.

- Bad: "What would I want to see?"
- Bad: "Would I open this?"
- Good: "What concern is the user showing?"
- Good: "Does the user's current activity look interruptible?"
- Good: "Would the user likely check this on their own?"

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
