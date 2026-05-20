# Task

You are given a proactive suggestion that an assistant might make to a user.

Your job is to generate question/answer pairs that would help another assistant execute that suggestion extremely well.

The questions should identify the context, constraints, preferences, source material, success criteria, and execution details needed to turn the suggestion into a useful artifact or action.

You may use subagents to help. You MUST search through additional logs (in the logs-indexed folder) for context in creating suggestions. Use the times to help identify relevant logs.

To identify the answer to a question (e.g. how did the user respond to this email?) you should lift, verbaitim, the exact writing the user sent. Again, look carefully through the logs to maintain a user's preferences.

For question generation, you can use the FUTURE ground truth to determine the answer, but you MUST rationalize the answer in the context of past logs and *not reference the future*. This is because we are trying to train a predictive model.

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

For example, when the suggestion involves writing on behalf of the user, include Q/A pairs that identify:
- what the user is going to write
- who the audience is
- what source material should be used for facts
- what examples of the user’s own writing should be inspected
- what tone, structure, signoff, length, and formatting preferences are evident
- whether the assistant should draft, revise, or send
- how the user would write the message, using the verbatim ground-truth message when available

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
      "future_rationalization": string,
      "answer": string,
      "why_it_matters": string,
      "question_difficulty": number
    }
  ]
}

## Minimal examples

### Example 1

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
      "question": "Which providers are grounded in the user's own browsing behavior?",
      "future_rationalization": "I did not use the future to come up with this answer. The provider set is recoverable from the logs before the suggestion: at 15:03 the user opened Together AI pricing, at 15:06 Fireworks docs, at 15:08 Groq console docs, at 15:11 Replicate pricing, and at 15:14 OpenRouter model docs. No later behavior was needed to identify the core comparison set.",
      "answer": "The browser logs show the user opened Together AI, Fireworks, Groq, Replicate, and OpenRouter docs or pricing pages in the same work session, so those five providers should define the core comparison set.",
      "why_it_matters": "The comparison set should come from the user's observed evaluation behavior rather than from a generic market map.",
      "question_difficulty": 1
    },
    {
      "question": "What does the user's search behavior suggest they care about most?",
      "future_rationalization": "I did not use the future to come up with this answer. The priorities are inferable from the pre-suggestion searches: 'batch inference pricing' points to cost, 'hosted vLLM latency' points to latency, and 'OpenAI-compatible inference API' points to migration effort.",
      "answer": "The logs suggest the user cares most about cost, latency, and migration effort. That comes from searches for 'batch inference pricing', 'hosted vLLM latency', and 'OpenAI-compatible inference API', plus the notes about Llama support and an OpenAI-style client swap.",
      "why_it_matters": "The assistant should weight the comparison using the user's demonstrated concerns, not treat all provider dimensions as equally important.",
      "question_difficulty": 3
    },
    {
      "question": "What should the final artifact contain for this user?",
      "future_rationalization": "I used the later artifact the user accepted as a guide for what would have been useful: the final report they kept had a one-page recommendation, a provider comparison table, a 'default vs fallback' section, and a short migration checklist. I then rationalized that structure from the earlier evidence: the user was comparing pricing/docs pages and had an implementation-oriented note about swapping into an OpenAI-style client.",
      "answer": "Given the repeated provider-comparison activity, the final artifact should probably be a concise comparison report with a table, a best default provider, a fallback option, and implementation notes for swapping providers into the user's OpenAI-style client.",
      "why_it_matters": "The expected artifact should help the user choose and implement a provider, not merely summarize vendor pages.",
      "question_difficulty": 4
    },
    {
      "question": "What implementation details about the user's setup are still unknown?",
      "future_rationalization": "I did not use the future to come up with this answer. The missing details are identifiable by comparing the pre-suggestion evidence against what would be needed to execute the provider recommendation confidently: exact pipeline, language, client, deployment setup, model list, request format, and feature requirements.",
      "answer": "The logs do not fully pin down the user's exact eval pipeline, programming language, current inference client, deployment environment, model list, request format, or whether they need streaming, tool calling, structured outputs, fine-tuning, or embeddings.",
      "why_it_matters": "These missing user-specific details could change which provider is easiest or safest to recommend.",
      "question_difficulty": 9
    },
    {
      "question": "What exact Llama requirements does the user have?",
      "future_rationalization": "I partially used future evidence here. Later in the session, the user mentioned testing 'Llama 3.1 70B and maybe 8B for cheap sweeps,' but they still did not specify context length, quantization, hosted checkpoint requirements, or whether newest-family Llama support mattered. So the future narrows the likely model family but does not fully answer the question.",
      "answer": "The logs only establish that Llama support is required. They do not specify the exact model family, model size, context length, quantization requirements, checkpoint availability, or whether the user needs the newest Llama release.",
      "why_it_matters": "Provider fit can vary significantly depending on the exact Llama model and serving requirements.",
      "question_difficulty": 9
    },
    {
      "question": "What budget information is available from the user's logs?",
      "future_rationalization": "I did not use the future to come up with this answer. The pre-suggestion logs show cost sensitivity through pricing-page visits and the 'batch inference pricing' search, but they do not include a concrete monthly budget or spend ceiling.",
      "answer": "Cost is clearly part of the decision because the user visited pricing pages and searched for batch inference pricing. However, there is no concrete monthly inference budget in the available logs.",
      "why_it_matters": "Without a known budget, the assistant should compare pricing under plausible workload scenarios instead of declaring a universal cheapest option.",
      "question_difficulty": 8
    },
    {
      "question": "Does the user care more about batch throughput or interactive latency?",
      "future_rationalization": "I used later behavior to sharpen the interpretation. After the suggestion, the user ran a small benchmark note labeled 'nightly eval sweep' and wrote that 'interactive latency is nice but the main issue is getting the evals done cheaply overnight.' That future evidence supports interpreting the earlier 'batch inference pricing' and 'low-latency batch jobs' signals as primarily batch-throughput oriented, while still preserving the caveat that latency was not irrelevant.",
      "answer": "The evidence leans toward batch throughput because of the 'batch inference pricing' search and the notes about low-latency batch jobs. Still, the hosted vLLM latency search could also point to interactive or tail-latency concerns, so the assistant should not collapse everything into batch throughput.",
      "why_it_matters": "Providers can rank differently depending on whether the user's real priority is cost-efficient batch throughput, realtime latency, or tail reliability.",
      "question_difficulty": 6
    },
    {
      "question": "How important is OpenAI-compatible API support to this user?",
      "future_rationalization": "I did not use the future to come up with this answer. Before the suggestion, the user searched for 'OpenAI-compatible inference API' and had a note saying the provider should be easy to swap into an existing OpenAI-style client, which is enough to treat compatibility as highly important.",
      "answer": "OpenAI-compatible API support appears highly important. The user searched for 'OpenAI-compatible inference API', and their notes say the provider should be easy to swap into an existing OpenAI-style client.",
      "why_it_matters": "The assistant should evaluate compatibility in terms of the user's migration effort, not just whether a provider advertises an OpenAI-compatible endpoint.",
      "question_difficulty": 5
    }
  ]
}

### Example 2

Input suggestion:

{
  "title": "Draft a follow-up email after the user reviews a recruiter thread",
  "timestamp": "2025-03-04T10:15:00",
  "trigger_evidence": [
    "User opened a Gmail thread with a recruiter about scheduling a final interview",
    "User searched calendar availability for Thursday and Friday afternoon",
    "User previously asked for emails to sound concise, warm, and not overly enthusiastic",
    "Recent sent emails show the user typically writes short paragraphs, uses contractions, and ends with 'Best,'",
    "Later in the session, the user sent a reply to the recruiter"
  ],
  "why_now": "The user appears ready to respond but may benefit from a polished draft that matches their usual style and incorporates calendar availability.",
  "suggestion": "I can draft a reply to the recruiter confirming your availability and keeping the tone consistent with your usual emails.",
  "action": "Inspect the recruiter thread, the relevant calendar openings, recent sent emails from the user, and any ground-truth email the user eventually wrote. Use these to draft a response in the user's writing style.",
  "expected_artifact": "email_draft"
}

Output:

{
  "suggestion_title": "Draft a follow-up email after the user reviews a recruiter thread",
  "qa_pairs": [
    {
      "question": "How would this user likely write the email",
      "future_rationalization": "I looked at exactly what the user sent in the first place, and used that to reconstruct the message they would send.",
      "answer": "Given the user's recent sent emails, their preference for concise and warm-but-not-overly-enthusiastic wording, the email would likely read:\n\nHi Maya,\n\nThanks for following up — Thursday afternoon works well for me. I’m also free Friday after 2pm if that’s easier on your end.\n\nHappy to work around the team’s availability.\n\nBest,\nOmar",
      "why_it_matters": "This gives the executing assistant a target-style example with the user's likely phrasing, paragraph length, warmth level, and signoff.",
      "question_difficulty": 1
    },
    ...
  ]
}

Remember, while you may USE the future to help generate an answer, the "answer" field must NOT have any explicit references to the future logs.