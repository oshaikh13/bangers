# Task

Your job is to come up with creative, helpful, and concrete suggestions for the user given a goal.

You may use subagents to help. You MUST search through additional logs (in the logs-indexed folder) for context in creating suggestions. Use the times to help identify relevant logs.

## Input

{combined_json_element}

## How to help

A single goal may contain multiple distinct opportunities for help.

Do not assume there is only one “best” suggestion per goal. Instead, identify the different moments where the system could usefully intervene. Each opportunity should correspond to a specific point in time, a specific user context, and a specific kind of assistance.

For example, if the user is working on a paper review, there may be separate opportunities to:

- Find related work while they are reading the paper
- Turn rough review notes into a complete review after they have drafted the main points
- Critique the review for fairness and tone before submission
- Draft a concise summary or justification after the review is complete

Each of these should be treated as a separate opportunity with its own timestamp, evidence, suggestion, action, and expected artifact.

## What to look for

Great suggestions are things that:

- Accelerate an active goal the user is already pursuing
- Consolidate scattered context into a decision, message, plan, or artifact
- Prepare for an upcoming moment where context will matter
- Resolve repeated loops, hesitation, or unresolved cognitive load
- Discover a latent goal the user has not explicitly identified yet
- Explain or investigate a meaningful anomaly
- Reduce future friction from a recurring pattern

## Suggestions

Here are a few examples of great suggestions — these are suggestions that are concrete, timely, and directly executable:

1. Comparative research before a decision
  - Context: The user was evaluating inference providers.
  - Great suggestion: “I can research the major inference providers, compare them across latency, pricing, model support, reliability, API ergonomics, and deployment constraints, then produce a concrete recommendation for your use case.”
  - Why it is good: It turns scattered exploration into a decision-ready artifact.

2. Briefing before meeting a new person
  - Context: The user was about to meet someone new.
  - Great suggestion: “Before your meeting, I can pull together a short briefing on this person’s prior work, recent projects, publications, and the parts most relevant to your current work, plus a few high-leverage questions to ask.”
  - Why it is good: It arrives right before context matters and helps the user show up prepared.

3. Training run analysis
  - Context: The user was training a model on Tinker and the logs were stored locally.
  - Great suggestion: “I can analyze the local training logs, plot loss curves and other metrics, flag anomalies, compare runs, and summarize what seems to be working or failing.”
  - Why it is good: It investigates meaningful anomalies and produces actionable debugging insight.

4. Paper-review drafting
  - Context: The user had notes on a paper review but still needed to write the full review.
  - Great suggestion: “I can turn your review notes into a full structured review in your usual style, including summary, strengths, weaknesses, questions, and actionable feedback.”
  - Why it is good: It picks up after the main intellectual work is done and turns notes into the required artifact.

5. Countering productive procrastination
  - Context: The user had been avoiding a blog post while completing other useful tasks.
  - Great suggestion: “I can notice when you are doing productive but avoidance-adjacent work, help narrow your environment to the blog post, and suggest a small hook that makes the post feel exciting again.”
  - Why it is good: It resolves a repeated loop and helps the user re-enter the intended task.

6. Helping with difficult purchase decisions
  - Context: The user was spending too long deliberating about a large purchase.
  - Great suggestion: “I can help you externalize the decision criteria, compare the arguments for and against, set a timebox or deadline, and recommend a decision based on your stated priorities.”
  - Why it is good: It turns circular deliberation into a bounded decision process.

7. Slide review before a talk
  - Context: The user has a slide deck for an upcoming talk and there is enough context about the talk content and audience.
  - Great suggestion: “I can review your slides based on what you’re trying to communicate and who you’re presenting to, then give concrete suggestions on what to improve, cut, reorder, clarify, or redesign.”
  - Why it is good: It helps the user improve the presentation at the moment when the deck is concrete enough to critique but still early enough to revise before presenting.

## Timestamps

Find the _optimal_ times to interrupt a user. This should be the moment you have enough evidence to actually execute on the goal itself. Pick a time that isn't too late either — the user should be in the right context to receive this evidence. And do NOT pick too many times, or the user will get annoyed.

LOOK at screenshots to determine the right time. 

For each opportunity, include:

- The specific timestamp or time range when the suggestion should be surfaced
- The evidence available at that moment
- Why that is the right time and not too early or too late
- The concrete action the system should offer to take
- The expected output artifact, such as a report, draft, plan, plot, agenda, email, outline, critique, or recommendation

## Output format

Return JSON only. Do not include markdown, commentary, or extra text.

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
          "expected_artifact": string
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
          "action": "Research Together AI, Fireworks, Groq, Replicate, and OpenRouter across pricing, latency, model availability, rate limits, batching support, reliability, and OpenAI-compatible API ergonomics. Then map each provider against the user's stated constraints."
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
          "action": "Select a recommended provider, explain the tradeoff, identify the exact client wrapper changes needed, and draft a small migration checklist."
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
          "action": "Search for related papers, group them by research angle, identify the closest baselines, and summarize what the reviewed paper adds or misses relative to them."
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
          "action": "Synthesize the notes into a review with summary, strengths, weaknesses, detailed comments, questions for authors, and an overall recommendation rationale."
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
          "action": "Review the draft for harsh language, unsupported claims, missing evidence, and places where critique could be made more actionable. Provide line-level edits."
        }
      ]
    }
  ]
}