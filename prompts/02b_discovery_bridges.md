# Task

We have a combined goals file:

{combined_path}

Your job is to identify bridge goals: overarching goals, motivations, or competing tensions that are only visible when connecting two or more distinct goals, life facets, obligations, ideas, projects, people, or deadlines.

Write the bridge goals to:

{bridges_path}

## What a bridge goal is

A strong bridge goal creates an "aha" moment by showing what the user's separate behaviors are really trying to serve, or what tradeoff those behaviors are struggling to resolve.

The bridge should connect observations into an insight about the motivation underneath them.

For example, a user might repeatedly ask ChatGPT to complete homework. A shallow system infers the goal "complete homework faster." A better bridge goal notices the tension: the user wants to gain expertise, but ongoing commitments make it hard to prioritize learning.

Bridge goals should often be framed as:

- An overarching goal the user is pursuing across several local tasks.
- A competing tension between what the user is doing and what they appear to need or value.
- A constraint from one life facet that changes how another facet should be understood.
- A recurring pattern where the deeper need differs from the surface behavior.

Examples:
- Protect presence during family travel while preventing research obligations and task deadlines from becoming hidden stress.
- Make a fuzzy research stance public in a more playful, memorable form by connecting a zine idea with a specific post.
- Turn CHI from conference attendance into research momentum for papers, collaborators, and follow-up writing.
- Make a technical product idea legible and credible by connecting benchmark evidence, demo reliability, onboarding friction, and public explanation.
- Stay responsive to collaborators without letting coordination consume deep work.

## How to find bridge goals

Read the entire combined goals file. Look for combinations where:

1. Two or more goals compete for the same time, attention, deadline window, trip, meeting, collaborator, identity, or source of truth.
2. The user's surface behavior seems to optimize one thing, while the broader pattern suggests they need something else.
3. One goal provides source material, constraints, motivation, or emotional context for another goal.
4. A personal context changes how a work task should be interpreted, or a work obligation changes how a personal plan should be understood.
5. Several administrative tasks are really about reducing a single underlying risk, uncertainty, or cognitive load.
6. A research, writing, or launch thread is connected to another project thread by a shared motivation or identity.
7. A recurring collaboration pattern spans multiple people or projects and reflects a deeper tension between responsiveness and focus.
8. A generated proactive output is only meaningful if understood against other goals, values, or source-of-truth evidence.
9. The user repeatedly defers a meaningful goal by doing adjacent useful work, suggesting productive avoidance or hidden friction.

Prefer bridge goals that feel specific to this user and this moment. A bridge goal should usually name concrete projects, trips, people, papers, products, places, meetings, or deadlines.

For each candidate bridge, ask:

- What is the surface behavior?
- What deeper need, value, or motivation might be underneath it?
- What tension or constraint makes the surface behavior understandable?
- What broader goal becomes visible only after connecting these goals?

For each bridge goal, write:

- `context`: the concrete cross-goal evidence or situation that makes the bridge visible.
- `reasoning`: why the connected goals reveal one broader motivation or tension.
- `description`: what the user is trying to accomplish at the broader bridge-goal level.

## What to avoid

Do not create weak bridge goals like:
- "Organize all tasks"
- "Prepare for work"
- "Manage deadlines"
- "Summarize everything"
- "Balance personal and professional life"
- "Be more productive"
- "Stay on top of commitments"

Do not connect goals only because they are both important. The connection must reveal a motivation, tension, constraint, or tradeoff that changes how the goals should be understood.

Do not merge everything into one giant life plan. A good bridge goal has a bounded underlying tension and a reason the connected goals belong together.

Do not merge things that are completely unrelated or do not create a meaningful tension, dependency, shared motivation, or shared constraint.

Do not create bridges by grouping multiple people, meetings, collaborators, or messages unless they are all part of the same concrete project, decision, event, or dependency chain. "Several people need updates" is not a bridge. Preserve separate people or meetings as separate goals unless connecting them reveals a specific shared tension.

Do not duplicate a bridge if it is already expressible as one combined goal. The bridge should add something by crossing goal boundaries.

Do not simply mirror the user's repeated behavior if the cross-goal evidence suggests that behavior conflicts with their broader needs. Name the tension and the deeper goal.

## Scoring

For each bridge goal, include:

- `usefulness`: 1 to 10. Higher means recognizing this bridge goal would materially reduce risk, improve prioritization, reveal an important connection, or clarify what the user really needs.
- `confidence`: 1 to 10. Higher means the connected goals strongly support the bridge goal.
- `surprise`: 1 to 10. Higher means the bridge is non-obvious and likely to create an "aha" moment.
- `attention_gap`: 1 to 10. Higher means the bridge goal appears to reflect something the user wants or needs, but is not giving focused attention right now / in the near future because of time pressure, competing commitments, avoidance, or context switching.

High-surprise bridge goals can have lower confidence, but avoid pure speculation.

## Output format

Write a JSON array to:

{bridges_path}

Use this exact schema:

[
  {
    "bridge": "concise name for the bridge goal",
    "context": "short evidence summary for this bridge goal",
    "reasoning": "why these connected goals reveal one broader motivation or tension",
    "description": "what the user is trying to accomplish at the bridge-goal level",
    "connected_goals": [
      {
        "combined_index": 0,
        "combined": "name from combined.json",
        "reason": "why this goal belongs in the bridge"
      }
    ],
    "best_timing": "best timestamp or timing rule inferred from the connected source goals",
    "usefulness": 1,
    "confidence": 1,
    "surprise": 1,
    "attention_gap": 1
  }
]

## Requirements

- Output only valid JSON.
- Do not include markdown in the file.
- Do not include commentary outside the JSON file.
- Include between 5 and 20 bridge goals, unless the combined file contains too little material.
- Every bridge must connect at least two distinct combined goals.
- Use zero-based `combined_index` values from the order of the combined goals file.
- Preserve the exact `combined` names from the source file.
- Be specific. Name concrete projects, trips, deadlines, papers, people, products, or places when available.
- Favor fewer, stronger bridge goals over many weak bundles.
- Include `context`, `reasoning`, and `description` for every bridge goal.
