# Task

Your job is to come up with creative, helpful, and concrete suggestions for a user given a batch of goals.

The suggestions should help the user prepare for the goal, not take over the user's instrumental action in the world. Prefer content work like drafting, researching, gathering evidence, synthesizing context, critiquing, outlining, planning, preparing checklists, and assembling everything the user would need to confidently act. When ongoing review or editing matters, that content can be packaged in a small app or interface, but the value should come from the prepared material rather than the UI itself.

You may use subagents to help. You MUST search through additional logs (in the logs-indexed folder) for context in creating suggestions, and for scoring suggestions. Use the times to help identify relevant logs.

## Input

{combined_json_element}

The input is a batch object with `output_path` and `items`. Each item has
`input_index` and `input`. The `input` object contains the goal or bridge fields:
`type`, `name`, `time`,
`usefulness`, `confidence`, `disregard`, `context`, `reasoning`, and
`description`.

For `type: "goal"`, generate suggestions that help the user make progress on the named siloed goal by preparing a useful artifact or information bundle. If interaction is important, the artifact may be packaged as a small app or interface.

For `type: "bridge"`, generate suggestions that prepare useful artifacts or context for the broader cross-goal motivation or tension implied by the name. Do not collapse the suggestion back into only one narrow subgoal unless log evidence shows that subgoal is the real leverage point.

For each batch item, use `input.name` as the goal to investigate, `input.time` as the starting point for log search, and `input.context`, `input.reasoning`, and `input.description` to understand the underlying situation before choosing concrete suggestions. Shared log searches across the batch are fine, but each output file must stay focused on its own batch item.

## Reframe action-shaped goals before generating suggestions

Goal names often arrive shaped by the user's observable action — "Submit the workshop paper revision", "Send the quarterly board update", "Book the team offsite venue", "File the home-office expense report", "Publish the npm release", "Buy a replacement monitor". Before generating opportunities, silently reframe the goal as the **preparation state** the user needs to reach in order to take or skip that action with confidence. The user is always the one who files, submits, sends, publishes, books, buys, applies, posts, deploys, or cancels — your suggestions must target the artifact they would review immediately before doing so, not the action itself.

Examples of the reframe:

- "Submit the workshop paper revision" → "Have a revised draft with every reviewer comment addressed point-by-point, a diff against v1, and a response letter ready for one final read-through."
- "Send the quarterly board update" → "Have a complete update drafted with metrics tables, narrative sections, and asks ready to edit and send."
- "Book the team offsite venue" → "Have a recommended venue with comparison, total cost, cancellation terms, and the booking page queued, ready to confirm."
- "File the home-office expense report" → "Have every receipt categorized into a single drafted report with totals computed and the two ambiguous categories flagged for the user's call."

Generate opportunities against the reframed state, not the action verb. Do not echo the action verb into the goal field of your output; restate the goal in preparation terms.

## How to help

Do not assume there is only one “best” suggestion per goal. Instead, identify the different moments where the system could usefully intervene. Each opportunity should correspond to a specific point in time, a specific user context, and a specific kind of assistance.

The assistant's offer should be preparation-focused. Do not propose that the assistant autonomously send messages, submit forms, book travel, buy items, apply to jobs, cancel services, post publicly, change account settings, deploy code, email other people, or otherwise perform irreversible or externally visible actions on the user's behalf. If the user's underlying goal requires one of those actions, the suggestion should instead be to draft the message, gather the options, prepare the submission materials, produce a decision memo, create a checklist, or assemble the exact information needed for the user to approve and take the action. If an app or interface includes follow-through, make it an explicit user-controlled final step after review and confirmation.

When suggesting an app or interface, keep it content-led: specify the draft, source material, evidence, options, recommendations, open questions, or next steps it should contain. Only mention interface behavior that directly helps the user review, edit, refine, track, or approve that material.

Prefer producing the **content of the artifact** over a checklist describing how the user should produce it. If the user needs to submit a form, draft the filled form with values populated and ambiguous fields flagged. If they need to send a message, draft the message text. If they need to make a code change, draft the patch or PR description with the test stubs. If they need to choose between options, draft the recommendation with rationale and the exact line-edits to make, not just the comparison. A `*_checklist`, `*_audit`, `*_matrix`, `*_regression_plan`, or `*_runbook` is only the right artifact when the user genuinely must act on each line themselves and no narrower draftable artifact would serve — otherwise turn it into a draft they can edit, accept, or reject in one pass.

For example, if the user is working on a paper review, there may be separate opportunities to:

- Find related work while they are reading the paper
- Turn rough review notes into a complete review after they have drafted the main points
- Critique the review for fairness and tone before submission
- Draft a concise summary or justification after the review is complete

Each of these should be treated as a separate opportunity with its own timestamp, evidence, suggestion, action, and expected artifact.

## What to look for

Great suggestions are things that:

- Accelerate a goal the user might not have time to pursue.
- Consolidate scattered context into a decision, message, plan, or artifact
- Package prepared content in a small workspace only when ongoing review, editing, tracking, or approval materially helps
- Prepare for an upcoming moment where context will matter
- Resolve repeated loops, hesitation, or unresolved cognitive load
- Discover a latent goal the user has not explicitly identified yet
- Explain or investigate a meaningful anomaly
- Reduce future friction from a recurring pattern

## Suggestions

Here are a few examples of great suggestions — these are suggestions that are concrete, timely, and artifact-producing:

1. Comparative research before a decision
  - Context: The user was evaluating inference providers.
  - Great suggestion: “I can compare the inference providers you’ve been evaluating and give you a concrete recommendation for your use case.”
  - Why it is good: It turns scattered exploration into a decision-ready artifact; and it's something a user might not have time to do.

2. Briefing before meeting a new person
  - Context: The user was about to meet someone new.
  - Great suggestion: “I can pull together a short briefing on [person] before your meeting with them.”
  - Why it is good: It arrives right before context matters and helps the user show up prepared.

3. Training run analysis
  - Context: The user was training a model on Tinker and the logs were stored locally.
  - Great suggestion: “I can analyze the [run name] training logs and tell you what’s working and what isn’t.”
  - Why it is good: It investigates meaningful anomalies and produces actionable debugging insight; and it's also something you think the user doesn't have figured out yet.

4. Paper-review drafting
  - Context: The user had notes on a paper review but still needed to write the full review.
  - Great suggestion: “I can turn your notes into a complete review of [paper title] ready to submit.”
  - Why it is good: It picks up after the main intellectual work is done and turns notes into the required artifact.

5. Countering productive procrastination
  - Context: The user had been avoiding a blog post while completing other useful tasks.
  - Great suggestion: “I can draft an opening and outline for the [blog post topic] post using what you’ve already written.”
  - Why it is good: It converts scattered avoidance-adjacent work into concrete draft material the user can react to.

6. Helping with difficult purchase decisions
  - Context: The user was spending too long deliberating about a large purchase.
  - Great suggestion: “I can turn your research on [product] into a decision brief with a clear recommended default.”
  - Why it is good: It turns circular deliberation into a bounded decision artifact while leaving the purchase decision to the user.

7. Slide review before a talk
  - Context: The user has a slide deck for an upcoming talk and there is enough context about the talk content and audience.
  - Great suggestion: “I can review your [talk name] slides against your goal and audience and give you suggestions on what to edit, add, or remove.”
  - Why it is good: It helps the user improve the presentation at the moment when the deck is concrete enough to critique but still early enough to revise before presenting. The user also likely won't think of or have time to solicit critique right away.

8. Preparing a formal submission
  - Context: The user has a formal submission due (a grant proposal, a permit renewal, a conference camera-ready, or a benefits claim) with source material spread across past versions, a current draft, supporting spreadsheets, and the program instructions.
  - Great suggestion: "I can produce a fully drafted [grant/permit/submission type] ready for your review, with ambiguous fields called out."
  - Why it is good: It produces the actual artifact the user would otherwise build manually under deadline pressure, while leaving the consequential submission step to the user. The artifact is the draft itself, not a checklist of what to gather.

## Timestamps

Find the _optimal_ times to interrupt a user. This should be the moment you have enough evidence to prepare a useful artifact or gather everything necessary for the goal. Pick a time that isn't too late either — the user should be in the right context to receive this evidence. And do NOT pick too many times, or the user will get annoyed.

LOOK at screenshots to determine the right time. 

For each opportunity, include:

- The specific timestamp or time range when the suggestion should be surfaced
- The evidence available at that moment
- Why that is the right time and not too early or too late
- The concrete preparation work the system should offer to do
- The expected output artifact, such as a report, draft, plan, plot, agenda, email, outline, critique, recommendation, or content-focused workspace

The `expected_artifact` name must describe the **content** of the artifact, not the action the user will eventually take with it. Do not include verbs like `submit`, `submission`, `file`, `filing`, `send`, `post`, `publish`, `deploy`, `book`, `buy`, or `apply` in the artifact name — these signal the model has anchored on the user action rather than on the prepared content. Prefer `camera_ready_revision_draft` over `paper_submission_packet`, `expense_report_draft_with_flagged_categories` over `expense_filing_packet`, `board_update_email_draft` over `board_update_send_packet`, `release_notes_and_changelog_draft` over `release_publish_packet`.

## Scoring

For each suggestion, include:

- `usefulness`: 1 to 10. How much value this suggestion would provide the user if they looked at it, on a scale from 1 to 10.
- `confidence`: 1 to 10. How likely is the that the user will actually click on this suggestion if it was surfaced. Just because it's useful does not mean the user may actually look at it.
- `disregard`: 1 to 10. How likely is it that the user will NOT do this themselves now or in the near future because of time pressure, competing commitments, avoidance, context switching, etc.
- `surprise`: 1 to 10. Higher means the suggestion is non-obvious to the user and likely to create an "aha" moment.

## Output format

Write JSON only to the batch `output_path`. Do not include markdown, commentary or extra text in that file. Include one entry in `bangers` for each input item.

Use this shape:

{
  "bangers": [
    {
      "input_index": 0,
      "goals": [
        {
          "goal": string,
          "opportunities": [
            {
              "timestamp": string,
              "trigger_evidence": [string],
              "why_now": string,
              "suggestion": string,
              "action": string,
              "expected_artifact": string,
              "usefulness": 1,
              "confidence": 1,
              "surprise": 1,
              "disregard": 1
            }
          ]
        }
      ]
    }
  ]
}

Minimal example:

{
  "bangers": [
    {
      "input_index": 0,
      "goals": [
        {
          "goal": "Choose an inference provider for a new eval pipeline",
          "opportunities": [
            {
              "timestamp": "2025-02-14T15:20:00",
              "trigger_evidence": [
                "User opened Together AI, Fireworks, Groq, Replicate, and OpenRouter documentation pages within the same work session",
                "User searched for 'batch inference pricing', 'hosted vLLM latency', and 'OpenAI-compatible inference API'",
                "User has a notes file mentioning constraints: must support Llama models, needs low-latency batch jobs, and should be easy to swap into an existing OpenAI-style client"
              ],
              "why_now": "The user has moved from casual browsing to active provider evaluation, and there is enough context to produce a useful comparison.",
              "suggestion": "I can compare these inference providers for your specific eval pipeline and recommend the best default plus a fallback option.",
              "action": "Research Together AI, Fireworks, Groq, Replicate, and OpenRouter across pricing, latency, model availability, rate limits, batching support, reliability, and OpenAI-compatible API ergonomics.",
              "expected_artifact": "provider_comparison_report",
              "usefulness": 8,
              "confidence": 7,
              "surprise": 5,
              "disregard": 6
            }
          ]
        }
      ]
    }
  ]
}
