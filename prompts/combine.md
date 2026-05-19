# Task

We have a candidates folder:

{dir_name}

Analyze all candidate suggestion files in this folder and combine repeated or near-duplicate suggestions into a single consolidated file. Use subagents if you need to.

Many suggestions are repeats. Your job is to identify all unique suggestions and write them to:

{dir_name}/combined.json

## Deduplication rules

Suggestions are considered the same if they are trying to accomplish the same underlying task for the same target.

Suggestions are unique if they target a different specific person, place, project, meeting, event, company, document, artifact, or decision.

Important: if two suggestions are similar in structure but should be surfaced at different times for different targets, keep them separate.

For example:
- “Prepare for the Acme call” and “Prepare for the Stripe call” are unique because they target different companies.
- “Draft follow-up to Priya about the Linear contract” and “Draft follow-up to Priya about the event venue” are unique because they target different artifacts/decisions.
- “Compare inference providers for the eval pipeline” and “Compare inference providers for the production API” may be unique if the workload, decision, or context differs.
- “Create a move plan for Omar and his roommate” should be merged with other move-plan suggestions if they refer to the same move, roommate, budget, and move-in date.
- If the same suggestion appears multiple times with different wording but the same target and purpose, merge it.

## How to combine

For each unique suggestion:
1. Create a concise combined suggestion name.
2. Include all source suggestions that map to it.
3. Preserve the original suggestion name/title and timestamp for each source suggestion.
4. If available, use the original `execution_timestamp`; otherwise use the best available time field.
5. Rank combined suggestions roughly from most useful to least useful, using the source suggestions’ usefulness scores and the number/quality of supporting duplicates as evidence.

## Output format

Write a JSON array to:

{dir_name}/combined.json

Use this exact schema:

[
  {
    "combined": "concise name for the unique combined suggestion",
    "suggestions": [
      {
        "name": "original suggestion name or title",
        "time": "original execution timestamp or best available timestamp"
      }
    ]
  }
]

## Requirements

- Output only valid JSON in `combined.json`.
- Do not include markdown in the file.
- Do not include commentary outside the JSON file.
- Preserve distinct suggestions when they target different people, places, projects, companies, documents, meetings, artifacts, or decisions.
- Merge suggestions that are only wording variations of the same underlying task.
- Do not drop source suggestions; every input suggestion should appear under exactly one combined suggestion unless it is malformed or unusable.
- If a suggestion is malformed, skip it only if there is no recoverable name/title or timestamp.