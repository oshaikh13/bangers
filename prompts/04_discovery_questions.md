# Task

You are generating Q/A pairs to train a **user model**. The user model is a
question-answering model whose job is to help an assistant produce
proactive artifacts (the "banger") for the user. To do that well it must
handle three modes equally:

1. **Forecast** — predict what the user is about to do, write, click,
   decide, or feel. Answers come from F (the future window beyond the
   banger timestamp).
2. **Recall** — answer factual questions about the user's past behavior,
   preferences, and style. Answers come from H (the 100 visible context
   events and the user's broader pattern).
3. **Current state** — describe what the user is doing right now, what
   they are frustrated by, what is in their working set. Answers come
   from the tail of H.

All three modes are first-class. A banger is built by combining all of
them: the forecast tells the assistant *what* to prepare, the recall and
current-state Qs ground that preparation in what the user already knows,
prefers, and is working on.

## Details
You are given a proactive suggestion (the banger) that an assistant
might surface to the user.

Your job is to generate Q/A pairs an assistant would ask the user model
before or during executing this banger. Mix the three modes freely:
forecasts about the near future, recall of past behavior and style, and
descriptions of the current state. Use whatever mix the banger actually
needs — most bangers need at least a few of each. Lean toward forecasts
when the banger's value is acting before the user does; lean toward
recall and current state when grounding the artifact matters most.


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

Generate **exactly 3 threads** of Q/A pairs. A thread is an ordered
conversation an assistant might walk through with the user model before or
during execution of this banger. Each thread has **3–10 Q/A pairs**; you
pick the length per thread.

Within a thread, the questions are sequential — the order matters and
later Qs are read as following earlier ones:

- The **first Q in every thread is generic**. It can sit in any of the
  three modes: a forecast opener ("What is the user about to do?",
  "How will the user respond next?"), a current-state opener ("What is
  the user trying to do right now?", "What is the user frustrated
  by?"), or a recall opener ("What is the user's usual style for
  short status updates?").
- **Subsequent Qs in the same thread get more specific**, usually
  picking up a concrete noun, decision, file, or constraint that the
  previous Q's answer made salient. A natural progression is
  current-state → forecast → recall-of-preference → forecast of next
  action, but any ordering is fine if it serves the banger.
- Later Qs MAY occasionally stay generic (re-asking timing, style,
  preferences). That's expected.
- Threads are **independent of each other** — thread 1 does not
  condition on thread 0. It is fine, even expected, for the opening Qs
  of multiple threads to overlap or duplicate (different assistants
  would start the same way).

Each question should still be specific enough to be useful and phrased
the way an assistant would actually ask — short, natural, one thing per
question.

Good Q/A pairs cover any mix of the three modes:

**Forecast (answered from F):**
- How will the user act next — which path, which file, which message,
  which decision will they choose?
- What will the user write, send, or say next? When the exact next text
  is recoverable from F, lift it verbatim — don't paraphrase.
- How will the user react emotionally to the situation that is about to
  unfold?
- What value, number, or selection will the user enter next?
- Will the user finish this in the current session or defer it?

**Recall (answered from H or general user pattern):**
- What is the user's usual writing style, tone, and length for this kind
  of message?
- What preferences, constraints, deadlines, or hard nos has the user
  shown before?
- What prior work, files, or source material is the assistant expected
  to pull from?

**Current state (answered from the tail of H):**
- What is the user concretely trying to do right now? What is their
  goal? What might they be frustrated by?
- What is in the user's working set at this moment — which app, file,
  draft, conversation?
- What is the user's affective state — frustration, hesitation,
  excitement, fatigue?

Also fine:
- Surface what's missing or unknown — include some pairs where the
  honest answer is `"I don't know"` and the unknown itself matters for
  the banger.
- Define what the prepared artifact should contain or look like.



## What NOT to ask

- **No multiple-choice questions with enumerated options.** Bad: "Which
  sourdough hydration will the user try next: 65%, 72%, or 80%?" Good:
  "Which hydration is the user most likely to try for the next loaf?"
- **No compound questions.** Bad: "Will the user post the new dungeon
  map to the campaign Discord, and what filename will they save it
  under?" Split it, or pick one.
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
generically. Look it up before naming it. *(The examples below are
illustrative — pretend the user is rebuilding a 1972 Honda CB350 and is
posting to a Reddit thread called "cb350-rebuild-logbook". None of these
entities show up in any real context event.)*

- ❌ Bad: "How should the assistant help finish the carburetor jet
  swap before pulling the tank back off?" — "the tank" isn't in any
  context event for this banger, even though it sounds plausible.
- ✅ Good (named entity is in H): "What will the user post next in the
  cb350-rebuild-logbook thread?"
- ✅ Good (generic): "What is the user's goal right now?"

## No future-evidence leakage in the text

The text of the question and answer must read as if produced from inside
H. Banned phrases (and any close paraphrase):

- In **questions**: "future logs", "later", "what the user ends up", "in
  hindsight", "would have matched", "after the suggestion fires".
- In **answers**: "Future logs show", "Later, the user…", "As it turns
  out", "We can see in the logs that…", "Looking at what happens next…".

Write the answer as the user model's confident statement. You used F to
know it; the answer text is the prediction itself, not a meta-comment
about evidence. *(The examples below are illustrative — imagine the
banger is a one-page NPC-voice cheat sheet the user wants before running
tonight's D&D session.)*

- ❌ Bad answer: "Future logs show the user drops the planned Scottish
  brogue for the dwarven smith and goes with a gravelly Russian accent
  instead, then keeps it for the rest of the campaign."
- ✅ Good answer: "The user will voice the dwarven smith with a
  gravelly Russian accent, abandoning the Scottish brogue they
  rehearsed earlier in the week."

Past- and present-tense Q/As are fine; just match tense between question
and answer (past Q → past A, present Q → present A, future Q → future A).

## Output format

Return JSON only. Do not include markdown, commentary, or extra text.

Use this shape:

```json
{
  "suggestion_title": string,
  "banger_timestamp": string,
  "threads": [
    {
      "thread_id": number,
      "qa_pairs": [
        {
          "q_id": number,
          "question": string,
          "answer": string,
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
  ]
}
```

- `threads` must contain exactly 3 entries with `thread_id` 0, 1, 2 in
  that order.
- Each thread's `qa_pairs` must contain 3–10 entries with `q_id` 0, 1,
  2, … in that order. `q_id` is the question's position within its
  thread.

Field notes:

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

IMPORTANT: The opening question of every thread will be generic — a
forecast opener ("What will the user do next?", "How will the user
respond?"), a current-state opener ("What is the user trying to do right
now?", "What is the user frustrated by?"), or a recall opener ("What is
the user's usual style for status updates?"). Three threads opening
with similar generic Qs is fine. The later questions within each thread
are where specificity comes in. Across the full set of Q/A pairs, all
three modes — forecast, recall, current state — should be represented;
forecasts should not be a niche category.
