# Task

Your job is to come up with creative, helpful, and concrete suggestions for a user given a batch of goals.

The suggestions should help the user prepare for the goal, not take over the user's instrumental action in the world. Prefer content work like drafting, researching, gathering evidence, synthesizing context, critiquing, outlining, planning, preparing checklists, and assembling everything the user would need to confidently act. When ongoing review or editing matters, that content can be packaged in a small app or interface, but the value should come from the prepared material rather than the UI itself.

You may use subagents to help. You MUST search through additional logs (in the logs-indexed folder) for context in creating suggestions, and for scoring suggestions. Use the times to help identify relevant logs.

## Input

{combined_json_element}

The input is a batch. Each item has `input_index`, `output_path`, and `input`.
The `input` object contains the goal or bridge fields: `type`, `name`, `time`,
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
  - Great suggestion: “I can research the major inference providers, compare them across latency, pricing, model support, reliability, API ergonomics, and deployment constraints, then produce a concrete recommendation for your use case.”
  - Why it is good: It turns scattered exploration into a decision-ready artifact; and it's something a user might not have time to do.

2. Briefing before meeting a new person
  - Context: The user was about to meet someone new.
  - Great suggestion: “Before your meeting, I can pull together a short briefing on this person’s prior work, recent projects, publications, and the parts most relevant to your current work, plus a few high-leverage questions to ask.”
  - Why it is good: It arrives right before context matters and helps the user show up prepared.

3. Training run analysis
  - Context: The user was training a model on Tinker and the logs were stored locally.
  - Great suggestion: “I can analyze the local training logs, plot loss curves and other metrics, flag anomalies, compare runs, and summarize what seems to be working or failing. If useful, I can package the plots and run comparisons in a small dashboard.”
  - Why it is good: It investigates meaningful anomalies and produces actionable debugging insight; and it's also something you think the user doesn't have figured out yet.

4. Paper-review drafting
  - Context: The user had notes on a paper review but still needed to write the full review.
  - Great suggestion: “I can turn your review notes into a full structured review in your usual style, including summary, strengths, weaknesses, questions, actionable feedback, and evidence for each critique.”
  - Why it is good: It picks up after the main intellectual work is done and turns notes into the required artifact.

5. Countering productive procrastination
  - Context: The user had been avoiding a blog post while completing other useful tasks.
  - Great suggestion: “I can gather the notes, links, and arguments you have already produced, then draft three possible openings and a tight outline for the blog post.”
  - Why it is good: It converts scattered avoidance-adjacent work into concrete draft material the user can react to.

6. Helping with difficult purchase decisions
  - Context: The user was spending too long deliberating about a large purchase.
  - Great suggestion: “I can turn your tabs and notes into a decision brief: criteria, tradeoffs, total cost, risks, a recommended default, and what would change the recommendation.”
  - Why it is good: It turns circular deliberation into a bounded decision artifact while leaving the purchase decision to the user.

7. Slide review before a talk
  - Context: The user has a slide deck for an upcoming talk and there is enough context about the talk content and audience.
  - Great suggestion: “I can review your slides based on what you’re trying to communicate and who you’re presenting to, then give concrete suggestions on what to improve, cut, reorder, clarify, or redesign.”
  - Why it is good: It helps the user improve the presentation at the moment when the deck is concrete enough to critique but still early enough to revise before presenting. The user also likely won't think of or have time to solicit critique right away.

8. Preparing a formal submission
  - Context: The user has a formal submission due (a grant proposal, a permit renewal, a conference camera-ready, or a benefits claim) with source material spread across past versions, a current draft, supporting spreadsheets, and the program instructions.
  - Great suggestion: "I can produce a fully drafted submission with every field populated from your documents, each value sourced back to its origin, and the three ambiguous items flagged with the program instructions quoted side-by-side — so you review one document and submit it yourself."
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

For each batch item, write JSON only to its `output_path`. Do not include markdown, commentary, or extra text in those files.

Use this shape:

{
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

Minimal example:

{
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
          "why_now": "The user has clearly moved from casual browsing to active provider evaluation, and there is enough context to produce a useful comparison before they spend more time switching between tabs.",
          "suggestion": "I can compare these inference providers for your specific eval pipeline and recommend the best default plus a fallback option.",
          "action": "Research Together AI, Fireworks, Groq, Replicate, and OpenRouter across pricing, latency, model availability, rate limits, batching support, reliability, and OpenAI-compatible API ergonomics. Then map each provider against the user's stated constraints.",
          "expected_artifact": "provider_comparison_report",
          "usefulness": 1,
          "confidence": 1,
          "surprise": 1,
          "disregard": 1
        },
        {
          "timestamp": "2025-02-14T16:05:00",
          "trigger_evidence": [
            "User has a draft comparison table but no final choice",
            "User opened the eval pipeline code and inspected the current OpenAI client wrapper",
            "User searched for 'OpenRouter python client example' and 'Together OpenAI compatible endpoint'"
          ],
          "why_now": "The research phase appears mostly complete, and the user is now close to implementation. A recommendation would prevent the comparison from becoming open-ended deliberation.",
          "suggestion": "I can turn the provider research into a concrete implementation plan and pick the provider that minimizes code changes.",
          "action": "Draft a recommendation, explain the tradeoff, identify the exact client wrapper changes needed, and prepare a small migration checklist for the user to review before changing code.",
          "expected_artifact": "implementation_recommendation_and_checklist",
          "usefulness": 1,
          "confidence": 1,
          "surprise": 1,
          "disregard": 1
        }
      ]
    },
    {
      "goal": "Finish a UIST paper review",
      "opportunities": [
        {
          "timestamp": "2025-02-15T10:15:00",
          "trigger_evidence": [
            "User opened a UIST paper PDF and highlighted the related-work section",
            "User wrote a note: 'not sure this is actually novel vs prior mixed-initiative tools'",
            "User searched for two cited papers and one uncited phrase from the introduction"
          ],
          "why_now": "The user is still forming their critique, so related work can shape the review before the main judgment is locked in.",
          "suggestion": "I can find closely related papers and summarize whether this paper is actually distinct from prior mixed-initiative systems.",
          "action": "Search for related papers, group them by research angle, identify the closest baselines, and summarize what the reviewed paper adds or misses relative to them.",
          "expected_artifact": "related_work_brief",
          "usefulness": 1,
          "confidence": 1,
          "surprise": 1,
          "disregard": 1
        },
        {
          "timestamp": "2025-02-15T11:40:00",
          "trigger_evidence": [
            "User has written bullets under 'strengths', 'weaknesses', and 'questions'",
            "User has a clear main concern: the evaluation does not support the strongest claim",
            "User has not yet written the final review text in the review form"
          ],
          "why_now": "The intellectual content is mostly present, but the user still needs to turn it into a polished review. This is exactly where drafting assistance saves time without replacing judgment.",
          "suggestion": "I can turn your notes into a full structured review in your usual review style.",
          "action": "Synthesize the notes into a review with summary, strengths, weaknesses, detailed comments, questions for authors, an overall recommendation rationale, and evidence for each critique.",
          "expected_artifact": "paper_review_draft",
          "usefulness": 1,
          "confidence": 1,
          "surprise": 1,
          "disregard": 1
        },
        {
          "timestamp": "2025-02-15T12:25:00",
          "trigger_evidence": [
            "User has a mostly complete review draft",
            "User is editing phrases like 'the authors fail to' and 'this is not convincing'",
            "User opened the submission page shortly after finishing the draft"
          ],
          "why_now": "The review is complete enough to critique, but it has not yet been submitted. This is the last high-leverage moment to improve fairness, specificity, and author-facing tone.",
          "suggestion": "I can check whether any parts of the review are unfair, under-supported, or discouraging to authors, and suggest more constructive wording.",
          "action": "Review the draft for harsh language, unsupported claims, missing evidence, and places where critique could be made more actionable. Provide line-level edits.",
          "expected_artifact": "review_revision_notes",
          "usefulness": 1,
          "confidence": 1,
          "surprise": 1,
          "disregard": 1
        }
      ]
    }
  ]
}
