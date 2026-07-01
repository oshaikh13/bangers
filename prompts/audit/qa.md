# QA Audit Prompt

# Task

Audit one generated Q/A pair for a user-model training set.

The original generator was allowed to inspect wider past and future logs to
produce the gold answer. The trained user model will **not** see those logs.
It will see only:

```text
context_events + question
```

Your job is to judge whether this Q/A pair is a good training example from the
user model's perspective.

## Timestamp

The question is asked at:

```text
qa_timestamp_ts = {qa_timestamp_ts}
qa_timestamp    = {qa_timestamp}
```

Treat this as the user model's "now". The `context_events` are the visible past
events, already limited to events with `ts <= qa_timestamp_ts`.

## Audit Labels

Choose exactly one label:

- too_easy
- too_hard
- cheating
- just_right

Use these definitions:

- `too_easy`: The answer is nearly copied from one visible context event, or a
  trivial restatement of the latest visible activity. The example does not
  require meaningful synthesis, prediction, preference modeling, or state
  tracking.
- `too_hard`: The answer is not reasonably inferable from
  `context_events + question`. This includes questions that require hidden
  future facts, private facts, or specific details not signaled by the visible
  past context. Judge the gold answer at its stated level of specificity. If
  the context supports only a broad theme but the answer names specific future
  apps, files, websites, people, messages, or actions that are not signaled by
  the visible context, mark `too_hard`.
- `cheating`: The pair leaks the answer through the question, timestamp,
  context window, or metadata-like phrasing. Examples: a future-looking
  question whose answer event is already visible in `context_events`; a
  question that embeds the answer's concrete artifact/action; a misplaced
  timestamp that turns a claimed prediction into a past-context lookup; or a
  question whose wording makes only one answer possible without modeling.
- `just_right`: The question is answerable from the visible past context but
  requires useful synthesis. It may use a future-verified gold answer, but the
  prediction or inference must be plausibly supported by `context_events`.

## Decision Rules

- Reason from the user model's input: `context_events + question`.
- Use `answer`, `answer_basis`, `verify_at_ts`, `question_basis`, and `evidence_grounding` only to identify what the generated pair is claiming. They are not evidence that the user model could answer the question. Inferability must be judged only from `context_events + question`.
- For future-looking questions, do not mark `too_hard` merely because the exact
  future is uncertain. Mark `just_right` if the visible context makes the gold
  answer a reasonable prediction.
- Mark `cheating` when the apparent future answer is already present in the
  visible past context or the question leaks future-only specifics.
- Mark `too_hard` when the answer is only knowable from future logs and the
  visible past context does not make it a reasonable prediction.
- Mark `too_easy` only when the example is too obvious, not merely because it is
  well-grounded.

If multiple labels seem possible, use this precedence:
1. `cheating` for leakage, timestamp/window artifacts, or future-framed questions whose answer is already visible.
2. `too_hard` when the answer as written is not reasonably inferable.
3. `too_easy` when it is inferable but trivial.
4. `just_right` otherwise.

## Output

Write one JSON object to this exact path:

{output_path}

Do not include markdown, commentary, or extra text. Reason before categorizing:

```json
{
  "rationale": "First explain what is visible in the past context, whether the answer is inferable, and whether there is any leakage or timestamp cheating. Then justify the label.",
  "label": "just_right",
  "confidence": 0.5
}
```

`label` must be one of `too_easy`, `too_hard`, `cheating`, or `just_right`.
`confidence` must be a JSON number from 0.0 to 1.0, not a string.

## Q/A Pair To Audit

```json
{qa_payload_json}
```
