# Task

You are generating Q/A pairs to train a user model. This model is a predictive model.
That can answer questions about:
a) the user's past
b) make predictions about the user's future (forecast)

The user model is a question answering model that can answer any questions about the user.


## Details
You are given a proactive suggestion (an artifact) that an assistant
might surface to the user.

Your job is to generate Q/A pairs that the assistant could:

1. ask a **user model** to come up with that suggestion / artifact. This could require:
a) asking Qs about the user's past.
b) making predictions about the user's future.

2. Then the assistant might ask questions about aspects of the suggestion to the user model, like:
a) information about the user, or the context that would be in the suggestion, or any source material
b) preferences that the user might have
c) success criteria
d) etc. anything else from the user model needed for executing and making a useful artifact for the user


The question is asked at a specific timestamp. The past before this is the history **H** 
The model has no access to the future.
You, the labeler, have both H and the **future** logs (call this window
**F**) — search `logs-indexed/` freely in both directions. Use F to ground
ground-truth answers; the user model has to learn to predict those answers
from H alone.

For question generation you MAY use the future to determine the answer,
but the **question and answer text themselves must not reference the
future**. Write the answer as a confident statement the user model would
make from inside H. The hindsight evidence goes in `evidence_grounding`,
which is dropped before training.

- You MUST search through additional logs (in the `logs-indexed/` folder). Use the times to identify relevant logs.

- To answer questions about what the user writes, sends, or says (e.g. "how would the user reply to this email?"), **lift the exact text verbatim** from the user's actual reply in the logs. Look carefully at the user's prior messages for style cues. Don't paraphrase a verbatim artifact; if the exact text isn't recoverable, pick a different question.

## Input

### Banger suggestion

{suggestion_json}

### Training-visible context events

{context_events_json}

## What to generate

Generate Q/A pairs that answer the most important questions an assistant
would need before or during execution of this banger. Each question should
be specific to this suggestion, but phrased the way an
assistant would actually ask — short, natural, one thing per question.

Good Q/A pairs should:

- Clarify what the user is concretely trying to do right now. 
    What is the user's goal? What might they be frustrated by?
- Identify the relevant source material or prior work to inspect.
- Capture user preferences, constraints, deadlines, and writing style.
- Define what the prepared artifact should contain.
- Surface how the user will most likely act next (which path, which file,
  which message, which decision).
- Recover verbatim what the user is about to write, send, or say, when
  that text is in the logs.
- Surface what's missing or unknown — include some pairs where the
  honest answer is `"I don't know"` and the unknown itself matters for
  the banger.
- Note timing context when relevant (today vs. defer, before vs. after
  some event already in H).
- Ask questions about the affective state of the user. Especially about the user's frustrations, and affordances.



## What NOT to ask

- **No multiple-choice questions with enumerated options.** Bad: "Which
  route will the user pick: A, B, or C?" Good: "Which route is the user
  most likely to take?"
- **No compound questions.** Bad: "Will the user upload proof to the
  portal, and which file should be prepared for that?" Split it, or pick
  one.
- **No questions stuffed with proper-noun context.** If a question needs
  three named entities, a clause about what the user did earlier, and a
  conditional, it's too complex — an assistant wouldn't ask it. Trim to
  one focused thing.
- **No questions whose answer is fully restated in the suggestion**
  (`suggestion`, `action`, `expected_artifact`, `goal`). Those teach the
  user model nothing the banger assistant doesn't already have.

## Self-containment

Every concrete noun in a **question** — person, app, file, project, repo,
topic — must appear somewhere in the 100 `context_events`, or be phrased
generically. Look it up before naming it.

- ❌ Bad: "How should the assistant help with the 2025 tax filing
  extension without losing the CPA thread?" — "the CPA thread" isn't in
  any context event.
- ✅ Good (named entity is in H): "How would the user write the next
  message in the CPA portal thread?"
- ✅ Good (generic): "What is the user's goal?"

## No future-evidence leakage in the text

The text of the question and answer must read as if produced from inside
H. Banned phrases (and any close paraphrase):

- In **questions**: "future logs", "later", "what the user ends up", "in
  hindsight", "would have matched", "after the suggestion fires".
- In **answers**: "Future logs show", "Later, the user…", "As it turns
  out", "We can see in the logs that…", "Looking at what happens next…".

Write the answer as the user model's confident statement. You used F to
know it; the answer text is the prediction itself, not a meta-comment
about evidence.

- ❌ Bad answer: "Future logs show the user abandons the IRS Free File
  path and uses TurboTax."
- ✅ Good answer: "The user will most likely file through TurboTax. The
  Free File draft they started is set aside without being submitted."

Past- and present-tense Q/As are fine; just match tense between question
and answer (past Q → past A, present Q → present A, future Q → future A).

## Output format

Return JSON only. Do not include markdown, commentary, or extra text.

Use this shape:

```json
{
  "suggestion_title": string,
  "banger_timestamp": string,
  "qa_pairs": [
    {
      "question": string,
      "answer": string,
      "banger_dimension": string,
      "question_basis": {
        "context_event_indexes": [number],
        "reason": string
      },
      "why_it_matters": string,
      "evidence_grounding": string,
      "question_difficulty": number
    }
  ]
}
```

Field notes:

- `banger_dimension`: short descriptive tag — `goal_clarity`,
  `source_context`, `user_style`, `expected_artifact`,
  `decision_support`, `next_action`, `verbatim_artifact`, `missing_info`,
  `timing`, `execution_plan`. Pick whatever fits; don't force coverage.
- `question_basis.context_event_indexes`: the H event indexes that make
  the question natural to ask. At least one; usually more when the
  question depends on a pattern.
- `evidence_grounding`: cite the actual log evidence — H or F — behind
  the answer. For F-dependent answers, name the F events by `ts_iso`,
  connector, and what they show. For H-only answers, name the supporting
  context_event indexes. This field is for QA hygiene and is **not**
  included in the training row, so naming F evidence here is the only
  safe place to do so.

Do not output `context_events`. The runner attaches the stored context
events to each Q/A procedurally from `banger_timestamp`.

Remember: you may USE the future to ground the answer, but the question
and answer text must not explicitly reference future logs.

Prefer questions whose answers are directly useful for execution. Fewer
strong pairs are better than many weak ones.
IMPORTANT: Most questions will be generic! Like "What is the user's goal right now?" or "What is the user's current frustration?" or "How will the user respond to this email?" ... this is normal and expected.
The follow-up questions will be more specific. 