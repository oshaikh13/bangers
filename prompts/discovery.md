# Task

Analyze the `logs-indexed/` folder at this time:

{candidate_row}

Your job is to identify moments where a proactive AI assistant could have helped the user in a specific, high-agency, genuinely useful way. You may use subagents to help.

Do not merely summarize what happened. Infer the larger task or life context behind the user's behavior, then propose concrete suggestions that could have been surfaced at the right time.

## Step 1: Understand the selected time range

First, carefully analyze what the user is doing during this time, minute by minute.

Use all available evidence:
- screen rows
- app/window titles
- browser URLs and searches
- text summaries
- dense captions
- mouse movement
- scrolling
- app switching
- idle time
- copied text
- calendar/email/chat/doc context, if available
- screenshots when needed

Screen rows may include `source.screenshot_path`. These paths are relative to `logs-indexed/`, for example:

`logs-indexed/screenshots/2026-05-12_15-03-12-864819.png`

When text summaries or dense captions are insufficient, inspect the relevant screenshots directly and use them as visual evidence.

Pay attention to time spent reading, scrolling, hovering, comparing, searching, rewriting, hesitating, switching apps, or returning to the same object. These are often signs that the user is stuck, uncertain, distracted, procrastinating, gathering context, or doing work manually.

## Step 2: Look beyond the selected range

After you understand the selected time range, widen your search far beyond it.

Look into both future and past logs to understand:
- what the user eventually does
- what they abandon
- what they repeatedly return to
- what artifacts they later find useful
- what deadlines, meetings, trips, moves, emails, projects, or decisions this moment connects to
- what personal context matters
- what multilingual context matters
- whether another proactive assistant already created a similar artifact, and whether the user actually used it

You may look into the future to identify what the user eventually needed. The goal is to surface that useful work earlier, at the moment it would have helped.

Do not be overly biased by artifacts created by another proactive assistant. It could be that the user did not find those suggestions useful if they never directly used them.

## What makes a great suggestion

A great suggestion is (1) specific, (2) timely, and (3) does one concrete thing.

The best suggestions are often not just "help with what is on the screen." They identify very useful TODOs implied by the user's behavior.

In other words:

The assistant should do the useful work implied by the user's activity, even when that work spans tools, time, languages, projects, etc.

Here are some examples of useful suggestion patterns, which you can use for inspiration:

1. Surface the answer the user eventually finds, but earlier.

Example: The user spends 20 minutes reading Next.js caching docs and later finds a GitHub issue that explains the fix. Suggest summarizing that specific GitHub issue and the exact config change needed for the app.

2. Turn scattered context into the next useful artifact.

Example: The user reads a vendor email thread, opens a pricing spreadsheet, and then opens Slack to message Priya. Suggest drafting the specific Slack message to Priya about the vendor pricing decision.

3. Prepare for a specific upcoming event while the user is focused elsewhere.

Example: The user has a call with Acme Corp in 30 minutes but is debugging unrelated code. Suggest preparing a one-page Acme briefing with the last unresolved issues and three questions to ask.

4. Convert dense reading into a project-specific artifact.

Example: The user reads a long article about retrieval evaluation and has recent work on a support-search prototype. Suggest turning the article into a concrete evaluation plan for that prototype.

5. Consolidate a repeated unresolved loop.

Example: The user opens the same Sentry error and Linear ticket multiple times across several days. Suggest compiling the stack traces, code paths inspected, affected users, and the most likely root cause.

6. Replace manual comparison with a tailored recommendation.

Example: The user switches between Together, Fireworks, Groq, OpenRouter, and Baseten pricing pages. Suggest a comparison table specifically for the user's model-serving workload, including cost, model support, latency, batching, reliability, and recommendation.

7. Run analysis for an active research project.

Example: The user has been circling a research question about whether asking questions improves LongNap. Suggest analyzing relevant logs to compare moments where the system asked active questions against moments where it did not, then summarize patterns and design implications.

8. Complete a procrastinated artifact.

Example: The user keeps returning to a half-written event outreach email, switches apps, and delays finishing it. Suggest creating the full event outreach package: polished invitation email, follow-up variants, event description, and attendee tracking checklist.

9. Synthesize life logistics from scattered personal context.

Example: The user and roommate discuss moving plans, budget, neighborhood constraints, and anxiety about the move across multiple messages, some of which are not in English. Suggest building a move plan that works backward from the move-in date, includes moving services, budget constraints, packing timeline, and decisions to resolve with the roommate.

10. Explain an anomaly the user pauses on.

Example: The user hovers over a revenue spike in a dashboard and later searches invoices from the same date. Suggest investigating the spike and connecting it to the likely customer upgrade, invoice, or one-time payment.

11. Remove recurring low-value friction.

Example: The user repeatedly opens and archives the same class of GitHub notification emails. Suggest a Gmail filter that labels Dependabot updates while keeping direct review requests in the inbox.

12. Make the user's next decision easier.

Example: The user compares portable monitors across Amazon, Reddit, Wirecutter, and YouTube. Suggest one recommended monitor for the user's actual setup and constraints, rather than a generic summary.

## Suggestion timing

Each suggestion must include an `execution_timestamp`.

This is the moment when the assistant should surface the suggestion to the user.

Choose the timestamp carefully. It should usually be:
- soon after the assistant has enough evidence to be useful
- before the user wastes time doing the work manually
- when the user appears stuck, distracted, or about to switch away
- shortly before a relevant meeting, deadline, trip, or event
- after enough context has accumulated, but not so late that the suggestion is pointless

Do not always use the end of the selected range. The best timestamp may be:
- during the selected range
- shortly after the selected range
- before the selected range, if past context already made the suggestion obvious
- later in the future, if the suggestion only becomes useful once a deadline approaches

Use an ISO-like timestamp string if possible. If exact timestamps are available in the logs, use the best exact timestamp. If not, use the closest available timestamp and explain the timing in the reasoning.

## What to avoid

Bad suggestions are generic, vague, or merely administrative.

Do not generate suggestions like:
- "Prepare for your meeting"
- "Summarize this page"
- "Organize your inbox"
- "Help with research"
- "Draft a follow-up"
- "Review your calendar"
- "Stay focused"
- "Take a break"
- "Create a todo list"
- "Look into this later"

Do not suggest irreversible actions. The assistant may draft, prepare, compare, analyze, recommend, or suggest, but must not send an email, create an invite, purchase something, submit a form, delete data, or take other irreversible action.

Do not generate a suggestion unless it is tied to specific evidence.

Do not overfit to whatever is visible in the current screenshot if wider logs show that something else mattered more.

Do not produce suggestions that could apply to 100 different users or 100 different moments.

A useful heuristic: the title should usually contain a proper noun, specific project name, specific person, specific company, specific artifact, specific deadline, or highly specific object. If the title could apply to almost any work session, it is too generic.

## Examples of good suggestions

Example 1: Inference provider research

{
  "execution_timestamp": "2026-05-12T15:18:30",
  "context": "You searched for several inference providers and opened pricing/docs pages for Together, Fireworks, Groq, OpenRouter, and Baseten while working on model-serving decisions.",
  "reasoning": "The searches show early-stage provider comparison, but the useful artifact is not another tab. It is a cost and capability comparison tailored to the workload. Future activity shows continued manual evaluation of providers, so surfacing this after the third provider search would likely save time.",
  "description": "Create a comprehensive comparison of the inference providers you looked at, including pricing, supported models, latency claims, rate limits, batching support, reliability concerns, and the best choice for your expected usage.",
  "title": "Compare inference providers and costs for the model-serving decision",
  "usefulness": 9,
  "enough_info": 7
}

Example 2: Research analysis for LongNap

{
  "execution_timestamp": "2026-05-09T11:42:00",
  "context": "You had an active research thread about whether asking questions improves LongNap-style memory behavior, and you later inspected logs related to user questions and downstream outcomes.",
  "reasoning": "This is not just reading or note-taking; it implies an analysis task. The assistant can use the logs to test whether active questioning correlates with better recall, task completion, or later usefulness.",
  "description": "Run an analysis over the relevant logs to compare moments where the system asked clarifying or proactive questions against moments where it did not. Summarize patterns, failure cases, and concrete design implications for improving LongNap.",
  "title": "Analyze whether active questions improve LongNap outcomes",
  "usefulness": 10,
  "enough_info": 7
}

Example 3: Human-like terminal-use tasks

{
  "execution_timestamp": "2026-05-10T16:05:15",
  "context": "You were exploring how to make terminal-use tasks more human-like, then later looked at datasets and examples of benchmark tasks.",
  "reasoning": "The project calls for empirical analysis, not just brainstorming. Future behavior shows the user needed patterns from datasets, so the assistant should proactively gather and analyze examples.",
  "description": "Download and inspect relevant terminal-use task datasets, identify patterns that make tasks feel artificial versus human-like, and summarize concrete task design recommendations with examples.",
  "title": "Analyze terminal-use datasets for human-like task patterns",
  "usefulness": 10,
  "enough_info": 6
}

Example 4: Event outreach procrastination

{
  "execution_timestamp": "2026-05-13T20:24:45",
  "context": "You were repeatedly returning to an unfinished email about organizing an event, with signs of hesitation and task switching before completing the outreach.",
  "reasoning": "The behavior suggests procrastination around a communication-heavy task. A high-value suggestion would complete the artifact and reduce social and organizational friction.",
  "description": "Create a complete event outreach package: a polished invitation email, shorter follow-up variants, a one-page event description, and a lightweight attendee tracking checklist.",
  "title": "Create the outreach package for the event invitation email",
  "usefulness": 9,
  "enough_info": 8
}

Example 5: Moving plan with roommate

{
  "execution_timestamp": "2026-05-14T09:30:00",
  "context": "You and your roommate discussed moving plans, budget, neighborhood constraints, and anxiety about the move across messages, including some non-English conversation. Your move-in date created a clear deadline.",
  "reasoning": "The moving task is distributed across personal conversations, calendar dates, searches, and budget constraints. A generic reminder would miss the opportunity to synthesize the plan and work backward from the deadline.",
  "description": "Build a move plan for you and your roommate: timeline from move-in date, budget-aware moving-service options, packing schedule, apartment setup checklist, and open decisions to resolve together.",
  "title": "Plan the move with your roommate around budget and move-in date",
  "usefulness": 10,
  "enough_info": 7
}

Example 6: Answer found later

{
  "execution_timestamp": "2026-05-12T10:16:20",
  "context": "You spent time searching through Next.js caching docs, then later found a GitHub issue explaining that the behavior was caused by route segment config.",
  "reasoning": "Future activity shows the GitHub issue contained the answer you needed. Surfacing it earlier would have saved the search loop.",
  "description": "Explain the specific Next.js caching issue you ran into and summarize the GitHub issue that resolved it. Add the exact config change you later applied.",
  "title": "Surface the Next.js caching fix from the GitHub issue earlier",
  "usefulness": 9,
  "enough_info": 9
}

Example 7: Upcoming customer call

{
  "execution_timestamp": "2026-05-11T13:35:00",
  "context": "You had an upcoming call with Acme Corp, but you were deep in unrelated debugging and did not appear to prepare for the meeting.",
  "reasoning": "The calendar event creates a near-term need, while the screen activity shows your attention was elsewhere. Past logs show you previously discussed Acme's onboarding issues.",
  "description": "Prepare a one-page briefing for the Acme Corp call with their open issues, the last decision made, and three specific questions to ask. Include unresolved follow-ups from prior emails or notes.",
  "title": "Prepare a briefing for the Acme Corp onboarding call",
  "usefulness": 9,
  "enough_info": 7
}

Example 8: Manual provider or product comparison

{
  "execution_timestamp": "2026-05-12T17:08:10",
  "context": "You repeatedly switched between Vercel, Render, and Fly.io pricing pages while evaluating where to deploy the side project.",
  "reasoning": "The app switching and repeated revisits suggest you were manually comparing options. A structured comparison would reduce the back-and-forth.",
  "description": "Create a focused comparison table of Vercel, Render, and Fly.io for this project's likely workload: monthly cost, deployment complexity, background jobs, databases, and scaling limits.",
  "title": "Compare Vercel, Render, and Fly.io for the side project deployment",
  "usefulness": 8,
  "enough_info": 8
}

Example 9: Scattered context before a message

{
  "execution_timestamp": "2026-05-12T14:22:05",
  "context": "You read the Linear contract thread, checked the pricing spreadsheet, and then opened Slack to message Priya.",
  "reasoning": "The sequence suggests you were gathering context to compose a message. The useful artifact is likely the message itself, not another summary.",
  "description": "Draft a Slack message to Priya summarizing the contract decision, the pricing constraint, and the one open question about annual billing. Keep it short and ready to paste.",
  "title": "Draft the Slack message to Priya about the Linear contract decision",
  "usefulness": 8,
  "enough_info": 8
}

Example 10: Repeated unresolved bug loop

{
  "execution_timestamp": "2026-05-15T11:12:40",
  "context": "You reopened the same Sentry error and related Linear ticket multiple times across the week without resolving it.",
  "reasoning": "Repeated revisits indicate unresolved cognitive load. A proactive assistant can consolidate the evidence and suggest the next diagnostic step.",
  "description": "Compile the recurring Sentry error, relevant stack traces, affected users, and the code paths you inspected. Recommend the most likely root cause and one concrete experiment to confirm it.",
  "title": "Consolidate the recurring Sentry error into a root-cause brief",
  "usefulness": 9,
  "enough_info": 8
}

Example 11: Dense reading tied to project

{
  "execution_timestamp": "2026-05-13T15:44:00",
  "context": "You spent several minutes reading a dense blog post about retrieval evaluation while also having recent work on the support-search prototype.",
  "reasoning": "The reading likely matters because it connects to a project you have been working on. The high-utility move is not just summarizing the article, but translating it into the project's evaluation plan.",
  "description": "Extract the evaluation ideas from the retrieval article and turn them into a concrete test plan for the support-search prototype, including metrics, sample queries, and failure cases to check.",
  "title": "Turn the retrieval evaluation article into a test plan for support search",
  "usefulness": 9,
  "enough_info": 7
}

Example 12: Long legal or vendor review

{
  "execution_timestamp": "2026-05-14T16:27:30",
  "context": "You slowly read through the termination and auto-renewal sections of a vendor contract.",
  "reasoning": "Slow scrolling over legal language suggests careful review. The assistant can extract risk-relevant clauses and connect them to upcoming deadlines.",
  "description": "Summarize the termination, auto-renewal, payment, and liability clauses from this vendor contract, with a plain-English risk assessment and the date by which you would need to cancel.",
  "title": "Extract the key risks from the vendor contract",
  "usefulness": 9,
  "enough_info": 8
}

Example 13: Dashboard anomaly

{
  "execution_timestamp": "2026-05-12T09:55:15",
  "context": "You paused on a revenue dashboard chart showing a sharp spike on Tuesday and hovered around that data point.",
  "reasoning": "The pause suggests the anomaly mattered, but the dashboard alone may not explain it. Future logs show you later searched for customer invoices around the same date.",
  "description": "Investigate the Tuesday revenue spike by connecting it to invoices, customer upgrades, or one-time payments around that date, and summarize the most likely cause.",
  "title": "Explain the Tuesday revenue spike in the dashboard",
  "usefulness": 8,
  "enough_info": 6
}

Example 14: Repetitive inbox triage

{
  "execution_timestamp": "2026-05-13T08:51:20",
  "context": "You opened and archived several similar GitHub notification emails in a row.",
  "reasoning": "This is repetitive triage. Future logs show these notifications continue to interrupt your workflow.",
  "description": "Suggest a Gmail filter for this specific class of GitHub notifications, such as auto-labeling Dependabot PR updates while keeping direct review requests in the inbox.",
  "title": "Create a Gmail filter for low-priority GitHub notifications",
  "usefulness": 7,
  "enough_info": 8
}

Example 15: Travel planning

{
  "execution_timestamp": "2026-05-15T18:03:00",
  "context": "You looked at flights to Austin, the conference agenda, and hotel maps in separate tabs.",
  "reasoning": "The travel planning context is scattered, and the useful missing artifact is a schedule that connects arrival time, hotel check-in, and the first conference event.",
  "description": "Build a practical arrival-day itinerary for the Austin trip, including airport arrival, transit to the hotel, check-in timing, and the first conference session you are likely trying to make.",
  "title": "Create the Austin conference arrival-day itinerary",
  "usefulness": 8,
  "enough_info": 7
}

## Required output

Write 20 possible candidates to the exact JSON file path provided by the runner.

Rank them from most useful to least useful.

Use this exact schema:

[
  {
    "execution_timestamp": "the best timestamp to surface this suggestion to the user",
    "context": "describe the context that led up to this suggestion, so the user remembers what they were doing",
    "reasoning": "justify why this task is needed, what evidence supports it, and why this execution timestamp is the right time to surface it",
    "description": "2-3 sentence description of what is being done for the user",
    "title": "single sentence summary of the suggestion; specific, not generic",
    "usefulness": "on a scale from 1 to 10, how useful is this suggestion and how much frustration or time will it save the user?",
    "enough_info": "on a scale from 1 to 10, how much information is available to actually execute this task well?"
  }
]

Rules for the JSON:
- Produce exactly 20 candidates.
- Rank from most useful to least useful.
- Every suggestion must do one specific thing.
- Every suggestion must include an execution timestamp.
- Every title must be specific enough that it could not apply to 100 different situations.
- Prefer suggestions that produce a concrete artifact.