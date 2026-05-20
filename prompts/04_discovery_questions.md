# Task

You are given a proactive suggestion that an assistant might make to a user.

Your job is to generate question/answer pairs that would help another assistant execute that suggestion extremely well.

The questions should identify the context, constraints, preferences, source material, success criteria, and execution details needed to turn the suggestion into a useful artifact or action.

You may use subagents to help. You MUST search through additional logs (in the logs-indexed folder) for context in creating suggestions. Use the times to help identify relevant logs.

To identify the answer to a question (e.g. how did the user respond to this email?) you should lift, verbaitim, the exact writing the user sent. Again, look carefully through the logs to maintain a user's preferences.

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
      "question": "What is the user trying to write?",
      "answer": "They are trying to write a reply to a recruiter confirming availability for a final interview.",
      "why_it_matters": "The assistant should produce an executable email draft, not a generic scheduling recommendation.",
      "question_difficulty": 1
    },
    {
      "question": "Who is the audience for the email?",
      "answer": "A recruiter coordinating a final interview.",
      "why_it_matters": "The recipient affects the tone: professional, clear, and warm, but not overly casual.",
      "question_difficulty": 1
    },
    {
      "question": "What source material should the assistant inspect before drafting?",
      "answer": "The recruiter email thread, the user's calendar availability for Thursday and Friday afternoon, recent sent emails that reveal the user's writing style, and the ground-truth reply the user later sent if available.",
      "why_it_matters": "The draft needs to be accurate about scheduling, responsive to the recruiter’s actual message, and written in the user’s real voice.",
      "question_difficulty": 2
    },
    {
      "question": "What writing style should the assistant emulate?",
      "answer": "Concise, warm, and not overly enthusiastic. The logs also indicate the user tends to write short paragraphs, uses contractions, and signs off with 'Best,'.",
      "why_it_matters": "This gives the executing assistant concrete stylistic signals to preserve instead of defaulting to a generic professional tone.",
      "question_difficulty": 2
    },
    {
      "question": "What examples of the user's own writing are relevant?",
      "answer": "Recent sent emails are relevant, especially ones involving scheduling, recruiting, or professional follow-ups. The logs specifically mention that these emails show short paragraphs, contractions, and a 'Best,' signoff.",
      "why_it_matters": "The assistant should learn from comparable writing samples, not just infer tone from the current thread.",
      "question_difficulty": 3
    },
    {
      "question": "How would the user write this email?",
      "answer": "Hi Maya,\n\nThanks for following up — Thursday afternoon works well for me. I’m also free Friday after 2pm if that’s easier on your end.\n\nHappy to work around the team’s availability.\n\nBest,\nOmar",
      "why_it_matters": "This gives the executing assistant a verbatim target-style example, so it can learn the user’s actual phrasing, paragraph length, warmth level, and signoff instead of relying only on abstract tone labels.",
      "question_difficulty": 1
    },
    {
      "question": "What concrete information must the email include?",
      "answer": "The user's availability on Thursday afternoon and Friday after 2pm, plus a polite indication that the recruiter or team can choose whichever time works best.",
      "why_it_matters": "The draft must satisfy the practical scheduling goal while remaining brief.",
      "question_difficulty": 2
    },
    {
      "question": "Should the assistant send the email or create a draft?",
      "answer": "Create a draft. The suggestion says 'draft a reply' and does not indicate that the user explicitly asked to send it immediately.",
      "why_it_matters": "Sending email requires explicit user intent; otherwise the assistant should prepare something reviewable.",
      "question_difficulty": 2
    },
    {
      "question": "What should the final artifact look like?",
      "answer": "A ready-to-review email draft that preserves the thread’s subject line and contains a short body written in the user's style.",
      "why_it_matters": "This defines the output as a usable email artifact rather than notes about how to respond.",
      "question_difficulty": 3
    },
    {
      "question": "Does the recruiter require a specific interview length, timezone, or video platform?",
      "answer": "I don't know. The available evidence mentions a recruiter thread but does not include the thread contents.",
      "why_it_matters": "The assistant should check the thread before drafting so the reply reflects any constraints already stated by the recruiter.",
      "question_difficulty": 8
    },
    {
      "question": "How should quality be judged?",
      "answer": "The draft should be factually accurate, short, warm but restrained, consistent with the user's prior sent emails, and immediately usable with minimal edits.",
      "why_it_matters": "This gives the executing assistant a practical bar for success that includes both correctness and voice matching.",
      "question_difficulty": 4
    }
  ]
}