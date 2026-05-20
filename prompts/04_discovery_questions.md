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
- Include some questions where the answer is explicitly unknown, using `"I don't know"` or a similarly clear statement when the logs do not contain enough evidence

Do not generate generic questions. Each question should be specific to the given suggestion.

Prefer questions whose answers are directly useful for execution.

For each Q/A pair, include `question_difficulty`, an integer from 1 to 10 that estimates how hard it is to answer the question from the user’s logs **at the SPECIFIC timestamp**; or to reasonably infer/predict the answer.

Use this scale:

- 1 = explicitly stated in the suggestion or logs
- 2–3 = strongly implied by multiple pieces of evidence
- 4–5 = partially supported but requires some inference
- 6–7 = weakly supported, ambiguous, or requires synthesizing scattered context
- 8–9 = mostly unknown and difficult to infer reliably
- 10 = impossible to answer from the available logs; answer should usually be “I don’t know”

When the answer is unknown, do not invent details. State what is missing and, if useful, what the executing assistant should ask or assume.

## Output format

Return JSON only. Do not include markdown, commentary, or extra text.

Use this shape:

{
  "suggestion_title": string,
  "qa_pairs": [
    {
      "question": string,
      "answer": string,
      "why_it_matters": string,
      "question_difficulty": number
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
  "suggestion": "I can compare inference providers after repeated pricing and docs searches",
  "qa_pairs": [
    {
      "question": "What decision is the user trying to make?",
      "answer": "They are choosing an inference provider for an eval pipeline that needs to support Llama models, low-latency batch jobs, and an OpenAI-compatible API.",
      "why_it_matters": "The assistant should optimize the comparison around a concrete provider decision, not produce a generic market overview.",
      "question_difficulty": 2
    },
    {
      "question": "Which providers should be compared?",
      "answer": "Together AI, Fireworks, Groq, Replicate, and OpenRouter, because the user opened their docs and pricing pages in the same work session.",
      "why_it_matters": "This defines the comparison set and prevents the assistant from wasting effort on irrelevant providers.",
      "question_difficulty": 1
    },
    {
      "question": "What dimensions should the comparison cover?",
      "answer": "Pricing, latency, model availability, Llama support, rate limits, batching support, reliability, and OpenAI-compatible API ergonomics.",
      "why_it_matters": "These dimensions map directly to the user’s apparent constraints and likely implementation concerns.",
      "question_difficulty": 2
    },
    {
      "question": "What should the final artifact contain?",
      "answer": "A concise comparative report with a table, a recommended default provider, a fallback provider, tradeoffs, and implementation notes for swapping into the existing OpenAI-style client.",
      "why_it_matters": "This makes the output decision-ready rather than merely informative.",
      "question_difficulty": 4
    },
    {
      "question": "What is the user's exact monthly inference budget?",
      "answer": "I don't know. The available evidence mentions pricing searches but does not provide a concrete budget.",
      "why_it_matters": "Without a budget, the assistant should avoid over-optimizing for absolute cost and instead compare pricing sensitivity across plausible usage levels.",
      "question_difficulty": 9
    },
    {
      "question": "What latency threshold would make a provider unacceptable?",
      "answer": "I don't know. The logs indicate the user cares about low latency, but they do not state a specific p50, p95, or p99 target.",
      "why_it_matters": "A provider recommendation may change substantially depending on whether the user needs interactive latency, batch throughput, or strict tail-latency guarantees.",
      "question_difficulty": 8
    }
  ]
}