# Task

Your job is to generate useful question/answer pairs about the user that would help fulfill a user's goal. Here is a combined_json_element with a parent goal:

{combined_json_element}

You may use subagents to help. You REALLY SHOULD search through additional logs (in the logs-indexed folder) for context in creating questions. Use the times to help identify relevant logs.

Do not generate questions for their own sake. Include only question/answer pairs whose answers would materially improve the final artifact, recommendation, plan, draft, analysis, or decision support produced for this specific suggestion.

## How to think

First, understand the combined goal as a concrete task:
- What useful work is the assistant expected to do?
- What user context would change the best output?
- What assumptions would be risky, personal, preference-sensitive, or hard to infer from logs?
- What constraints, goals, relationships, deadlines, budgets, standards, or tradeoffs matter?

Then generate a useful set of question/answer pairs that would help fulfill the suggestion well.

Each question/answer pair must include a `time`. Use one of the source suggestion `time` values from the `combined_json_element` whenever possible.

You may repeat the same `question` at different `time` values. This is useful when the combined suggestion appeared multiple times and the best inferred answer might vary across time because more context accumulated, urgency changed, or the user moved closer to a deadline. Repeated questions should still have a reason to exist: their `time`, `inferred_answer`, `answer_difficulty`, or `why_it_matters` should differ.

Good questions often ask about:
- the user's goal or success criteria
- personal preferences that affect the output
- constraints such as budget, time, location, access, tools, tone, or format
- the user's relationship to people, organizations, projects, documents, or decisions involved
- decision criteria and priorities when tradeoffs are unavoidable
- missing facts where a concrete plausible answer would materially shape the result
- boundaries around what the assistant should avoid doing or assuming
- the exact artifact the user creates (e.g. what email do they write next)
- there is variance to the answer depending on time.

Strong inferred answers often include:
- named people, companies, projects, documents, meetings, places, or artifacts from the combined suggestion
- relevant dates, deadlines, or timing relationships from source suggestions
- a concrete format, tone, constraint, priority, or tradeoff
- the next action the assistant should take if this answer is used
- specific inclusions, exclusions, sections, comparison criteria, message points, decision criteria, or checklist items

If exact details are missing, generate a concrete best-guess answer and hedge inside `inferred_answer`. The answer should still contain specifics, but it should make clear that those specifics are inferred guesses rather than known facts.

The right pattern is: specific guessed answer + uncertainty language + what evidence made the guess plausible.

If you genuinely do not know, say that in `inferred_answer`, but still provide the most useful concrete fallback guess. Use a high `answer_difficulty` score.

---

Question: "What kind of budget does the user want?"

Bad example: "The user is probably budget-conscious."

Good example: "The moving budget is probably around $1,800 total. A reasonable plan would use DIY packing, a U-Haul for the main move, and about $350 for two hours of labor to move the couch, bed frame, and desk. This is a guess based on the repeated budget concern; the exact ceiling is not visible."

---

Question: "What format should the summary be in?"

Bad example: "The user wants a helpful summary."

Good example: "The briefing should probably be a one-page prep note for the Acme call with three sections: open implementation issues, the renewal-risk decision from the last email thread, and three questions about timeline, budget owner, and success criteria. This is inferred from the suggestion title and may need adjustment if the actual agenda differs."

---

Question: "Which roommate should own which moving tasks?"

Good example when the model does not know: "I do not know the real division of responsibilities from the available context. A useful fallback guess is: Omar owns truck booking, address changes, and utilities because those are admin-heavy tasks; his roommate owns packing supplies, elevator reservations, and cleaning coordination; both confirm the checklist together every evening during the final week. This is a weak guess and should be treated as tentative."

## Difficulty scale

Rate `answer_difficulty` as an integer from 1 to 10:

- 1 means the answer is explicit or almost certain from the available context.
- 3 means the answer is easy to infer with minor uncertainty.
- 5 means the answer is a reasonable inference but could be wrong.
- 7 means the answer requires a speculative inference and should be treated cautiously.
- 10 means the answer is very hard to infer, but you still chose a concrete plausible answer.

Do not include questions where no reasonable answer can be inferred at all. Those are not useful question/answer pairs for this task.

## What to avoid

Do not include questions whose answers are already fully explicit in the combined suggestion or its source suggestions.

Do not include questions whose answers would not change the output.

Do not include questions that merely ask the user to restate information the assistant should be able to inspect or infer from available evidence.

## Quality bar

Each pair should pass this test:

"If this inferred answer is used, would the assistant produce a meaningfully better version of the combined suggestion?"

If the answer is no, remove the pair.

Question/answer pairs should be:
- specific
- answerable by the user and reasonably inferable by the assistant
- tied to the combined suggestion
- framed in plain language
- narrow enough to answer quickly
- broad enough that the answer materially changes the assistant's work
- honest about uncertainty in both `inferred_answer` and the difficulty score

## Output format

Return only valid JSON with this schema:

{
  "combined": "the combined suggestion name or title",
  "reasoning": "brief explanation of what information is useful to infer and why these question/answer pairs matter",
  "question_answer_pairs": [
    {
      "why_it_matters": "how this answer would change the fulfillment of the combined suggestion",
      "time": "source suggestion timestamp this question/answer pair is tied to",
      "question": "specific question about the user that would help fulfill the suggestion",
      "inferred_answer": "specific inferred answer with concrete names, constraints, dates, sections, criteria, or actions; hedge when details are guessed",
      "answer_difficulty": 5
    }
  ]
}

## Example

Input combined suggestion:

{
  "combined": "Plan the move with your roommate around budget and move-in date",
  "suggestions": [
    {
      "name": "Build a move plan for Omar and his roommate",
      "time": "2026-05-14T09:30:00"
    },
    {
      "name": "Revise the roommate move plan after budget and packing anxiety came up again",
      "time": "2026-05-16T20:10:00"
    }
  ]
}

Good output:

{
  "combined": "Plan the move with your roommate around budget and move-in date",
  "reasoning": "The useful missing facts are the move budget, anchor date, and coordination style because they directly change the recommended timeline, vendor choices, and roommate task split. The inferred answers use concrete guesses where needed and hedge those guesses instead of presenting them as known facts.",
  "question_answer_pairs": [
    {
      "why_it_matters": "This changes whether the plan should recommend movers, a rental truck, storage, or a mostly DIY approach.",
      "time": "2026-05-14T09:30:00",
      "question": "What moving budget should the assistant plan around?",
      "inferred_answer": "Omar and his roommate probably have a moving budget around $1,800 total. A reasonable guessed allocation is $450 for a U-Haul and gas, $350 for two hours of moving labor for the couch, bed frame, and desk, $200 for boxes and packing supplies, and $800 as buffer for deposits, cleaning, and last-minute setup. This is inferred from the budget emphasis, not directly stated.",
      "answer_difficulty": 7
    },
    {
      "why_it_matters": "At the later surfacing time, this changes whether the plan should preserve the cheaper DIY path or upgrade to more paid help to reduce last-minute stress.",
      "time": "2026-05-16T20:10:00",
      "question": "What moving budget should the assistant plan around?",
      "inferred_answer": "By this later point, the budget probably needs a little more stress buffer: around $2,200 total, with $500 for truck and gas, $600 for three to four hours of moving labor, $250 for packing supplies, and $850 reserved for cleaning, deposits, and last-minute setup. This is a time-specific guess based on the suggestion resurfacing after anxiety and packing pressure came up again.",
      "answer_difficulty": 8
    },
    {
      "why_it_matters": "This determines the packing timeline, booking deadlines, apartment setup sequence, and roommate coordination schedule.",
      "time": "2026-05-14T09:30:00",
      "question": "What move-in date should the assistant use as the anchor deadline?",
      "inferred_answer": "The move-in date appears to be around June 1, 2026. Build the plan backward from that guessed anchor: apartment and truck decisions by May 20, packing finished by May 29, pickup and loading on May 31, and essential setup on June 1. If the actual move-in date differs, shift the milestones while preserving the same spacing.",
      "answer_difficulty": 3
    },
    {
      "why_it_matters": "This determines whether to recommend paid help, earlier packing, fewer errands per day, or a compressed move schedule.",
      "time": "2026-05-16T20:10:00",
      "question": "What tradeoff should the assistant optimize for: cost, stress reduction, or speed?",
      "inferred_answer": "The best-guess tradeoff is cost control plus stress reduction. A plausible division is: Omar handles truck booking, address changes, and utilities; his roommate handles packing supplies, elevator reservations, and cleaning coordination; both use a shared checklist with daily 20-minute check-ins during the final week. The exact task split is guessed from the roommate-planning context.",
      "answer_difficulty": 5
    },
    {
      "why_it_matters": "This determines whether the plan should assign tasks by person or leave them as shared checklist items.",
      "time": "2026-05-16T20:10:00",
      "question": "Which roommate should own which moving tasks?",
      "inferred_answer": "I do not know the real division of responsibilities from the available context. A useful fallback guess is: Omar owns truck booking, address changes, and utilities because those are admin-heavy tasks; his roommate owns packing supplies, elevator reservations, and cleaning coordination; both confirm the checklist together every evening during the final week. This is a weak guess and should be treated as tentative.",
      "answer_difficulty": 9
    }
  ]
}
