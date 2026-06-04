# Task

Generate generic Q/A pairs for a user-model training set.

This is stage `01_q_only`: one generic QA type per run. The target QA type for
this run is:

`{qa_type}`

The user model will see only:

```text
context_events + question
```

It must answer from those visible past events. You, the labeler, may inspect
the wider `logs-indexed/` folder, including future events, to produce the
gold answer. The final training export will drop all metadata except the
past context, question, and answer. You may use subagents to help.

## Timestamp

The question is asked at this interval end:

```text
qa_timestamp_ts = {qa_timestamp_ts}
qa_timestamp    = {qa_timestamp}
```

Treat this as the user model's "now".

## Interval

```json
{interval_json}
```

## Past Context Events

These are the past indexed events visible to the user model. They are already
limited to the latest 100 events with `ts <= qa_timestamp_ts`.

```json
{context_events_json}
```

## Required Grounding

- Every concrete noun in a question must appear in the past context events,
  unless the question is phrased generically.
- Use `logs-indexed/` to inspect broader past and future logs as needed.
- Future-grounded answers must read like predictions made from "now"; do not
  say "future logs show", "later", "in hindsight", or similar.
- History-grounded answers must use only events before `qa_timestamp_ts`.
- Do not ask multiple-choice questions.
- Do not ask compound questions.
- Keep questions short and natural.
- Prefer useful, general questions about the user over brittle trivia.

## Perspective

Questions are asked **about** the user from an outside observer (the model
answering them is a user model, not the user). Always phrase the question in
third person about "the user". Never use first person.

- ❌ `"What was I working on?"`
- ❌ `"Will I finish the draft tonight?"`
- ❌ `"What should an assistant remind me about?"`
- ✅ `"What was the user working on?"`
- ✅ `"Will the user finish the draft tonight?"`
- ✅ `"What should an assistant remind the user about?"`

Answers should also speak about the user in third person.

## Output

Write one JSON object. Do not include markdown, commentary, or extra text.

The runner will attach `context_events`, `interval`, `qa_timestamp`, and
`qa_timestamp_ts` if you omit them. Output a flat list of independent Q/A
pairs — they are not a multi-turn thread:

```json
{
  "qa_type": "{qa_type}",
  "qa_pairs": [
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
      "why_it_matters": "why this helps a user model",
      "evidence_grounding": "brief private evidence summary; may mention broad past/future log evidence",
      "question_difficulty": 1
    }
  ]
}
```

Generate exactly `{pairs_per_run}` Q/A pairs unless fewer are honestly
groundable. Never generate fewer than 3.

`q_id` values must be contiguous from 0.

`answer_basis` rules:

- `H`: answer uses only events before `qa_timestamp_ts`; `verify_at_ts` must be
  before `qa_timestamp_ts`.
- `F`: answer uses events at or after `qa_timestamp_ts`; `verify_at_ts` must be
  at or after `qa_timestamp_ts`.
- `H+F`: answer combines past context with future verification; `verify_at_ts`
  must be at or after `qa_timestamp_ts`.

`timescale` rules:

- `micro`: up to 30 minutes
- `short`: 30 minutes to 2 hours
- `medium`: 2 hours to 24 hours
- `long`: more than 24 hours

Read the QA-type-specific instructions below and follow them for this run.
