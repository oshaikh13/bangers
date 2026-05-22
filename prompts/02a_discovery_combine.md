# Task

We have a goals folder:

{dir_name}

Analyze all goal files in this folder and combine repeated or near-duplicate goals into a single consolidated file. Use subagents if you need to.

Many goals are repeats. Your job is to identify all unique goals and write them to:

{combined_path}

## Deduplication rules

Goals are considered the same if they are trying to accomplish the same underlying task for the same target.

Goals are unique if they target a different specific person, place, project, meeting, event, company, document, artifact, or decision.

Important: if two goals are similar in structure but should be surfaced at different times for different targets, keep them separate.

For example:
- “Prepare for the Acme call” and “Prepare for the Stripe call” are unique because they target different companies.
- “Draft follow-up to Priya about the Linear contract” and “Draft follow-up to Priya about the event venue” are unique because they target different artifacts/decisions.
- “Compare inference providers for the eval pipeline” and “Compare inference providers for the production API” may be unique if the workload, decision, or context differs.
- “Create a move plan for Omar and his roommate” should be merged with other move-plan goals if they refer to the same move, roommate, budget, and move-in date.
- If the same goal appears multiple times with different wording but the same target and purpose, merge it.

## How to combine

For each unique goal:
1. Create a concise combined goal name.
2. Write a short `context`, `reasoning`, and `description` for the combined goal.
3. Include all source goals that map to it.
4. Preserve the original goal name/title, timestamp, and scores for each source goal.
5. If available, use the original `execution_timestamp`; otherwise use the best available time field.
6. Rank combined goals roughly from most useful to least useful, using the source goals’ usefulness scores and the number/quality of supporting duplicates as evidence.

Definitions:
- `context`: the concrete evidence or situation that makes this combined goal visible.
- `reasoning`: why the source goals should be understood as one underlying goal.
- `description`: what the user is trying to accomplish, phrased as a useful objective.

## Output format

Write a JSON array to:

{combined_path}

Use this exact schema:

[
  {
    "combined": "concise name for the unique combined goal",
    "context": "short evidence summary for this combined goal",
    "reasoning": "why these source goals combine into this underlying goal",
    "description": "what the user is trying to accomplish",
    "goals": [
      {
        "name": "original goal name or title",
        "time": "original execution timestamp or best available timestamp",
        "usefulness": "original usefulness score if available",
        "confidence": "original confidence score if available",
        "attention_gap": "original attention_gap score if available"
      }
    ]
  }
]

## Requirements

- Output only valid JSON.
- Do not include markdown in the file.
- Do not include commentary outside the JSON file.
- Preserve distinct goals when they target different people, places, projects, companies, documents, meetings, artifacts, or decisions.
- Merge goals that are only wording variations of the same underlying task.
- Do not drop source goals; every input goal should appear under exactly one combined goal unless it is malformed or unusable.
- If a goal is malformed, skip it only if there is no recoverable name/title or timestamp.
- Preserve `usefulness`, `confidence`, and `attention_gap` from source goals when available. If a source goal lacks one of these scores, omit that score for that source goal rather than inventing it.
- Include `context`, `reasoning`, and `description` for every combined goal.
