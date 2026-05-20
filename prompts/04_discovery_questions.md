# Task

You are given a proactive suggestion that an assistant might make to a user.

Your job is to generate question/answer pairs that would help another assistant execute that suggestion extremely well.

The questions should identify the context, constraints, preferences, source material, success criteria, and execution details needed to turn the suggestion into a useful artifact or action.

You may use subagents to help. You MUST search through additional logs (in the logs-indexed folder) for context in creating suggestions. Use the times to help identify relevant logs.

## Input

{suggestion_json}

## What to generate

Generate Q/A pairs that answer the most important questions an assistant would need before or during execution.

Good Q/A pairs should:

- Clarify the user’s concrete goal
- Identify the relevant source material or logs to inspect
- Capture user preferences, constraints, deadlines, and style
- Define the expected output artifact
- Specify how to judge quality
- Surface risks, missing context, or assumptions
- Break the suggestion into executable steps
- Include timing context when relevant

Do not generate generic questions. Each question should be specific to the given suggestion.

Prefer questions whose answers are directly useful for execution.

## Output format

Return JSON only. Do not include markdown, commentary, or extra text.

Use this shape:

{
  "suggestion_title": string,
  "qa_pairs": [
    {
      "question": string,
      "answer": string,
      "why_it_matters": string
    }
  ]
}

## Minimal example

Input suggestion:

{
  "title": "Compare inference providers after repeated pricing and docs searches",
  "timestamp": "2025-02-14T15:20:00",
  "trigger_evidence": [
    "User opened Together AI, Fireworks, Groq, Replicate, and OpenRouter documentation pages within the same work session",
    "User searched for 'batch inference pricing', 'hosted vLLM latency', and 'OpenAI-compatible inference API'",
    "User has a notes file mentioning constraints: must support Llama models, needs low-latency batch jobs, and should be easy to swap into an existing OpenAI-style client"
  ],
  "why_now": "The user has clearly moved from casual browsing to active provider evaluation, and there is enough context to produce a useful comparison before they spend more time switching between tabs.",
  "suggestion": "I can compare these inference providers for your specific eval pipeline and recommend the best default plus a fallback option.",
  "action": "Research Together AI, Fireworks, Groq, Replicate, and OpenRouter across pricing, latency, model availability, rate limits, batching support, reliability, and OpenAI-compatible API ergonomics. Then map each provider against the user's stated constraints.",
  "expected_artifact": "provider_comparison_report"
}

Output:

{
  "suggestion_title": "Compare inference providers after repeated pricing and docs searches",
  "qa_pairs": [
    {
      "question": "What decision is the user trying to make?",
      "answer": "They are choosing an inference provider for an eval pipeline that needs to support Llama models, low-latency batch jobs, and an OpenAI-compatible API.",
      "why_it_matters": "The assistant should optimize the comparison around a concrete provider decision, not produce a generic market overview."
    },
    {
      "question": "Which providers should be compared?",
      "answer": "Together AI, Fireworks, Groq, Replicate, and OpenRouter, because the user opened their docs and pricing pages in the same work session.",
      "why_it_matters": "This defines the comparison set and prevents the assistant from wasting effort on irrelevant providers."
    },
    {
      "question": "What dimensions should the comparison cover?",
      "answer": "Pricing, latency, model availability, Llama support, rate limits, batching support, reliability, and OpenAI-compatible API ergonomics.",
      "why_it_matters": "These dimensions map directly to the user’s apparent constraints and likely implementation concerns."
    },
    {
      "question": "What should the final artifact contain?",
      "answer": "A concise comparative report with a table, a recommended default provider, a fallback provider, tradeoffs, and implementation notes for swapping into the existing OpenAI-style client.",
      "why_it_matters": "This makes the output decision-ready rather than merely informative."
    }
  ]
}