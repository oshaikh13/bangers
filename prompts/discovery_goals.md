# Task

Analyze the `logs-indexed/` folder at this time:

{candidate_row}

Your job is to identify moments where a proactive AI assistant could help the user make progress toward a specific goal in a high-agency, genuinely useful way. You may use subagents to help.

Do not merely summarize what happened. Infer the larger task, decision, project, life context, or unmet need behind the user's behavior. Then identify concrete proactive opportunities that would have advanced the user's goal at the right time.

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

You may look into the future to identify what the user eventually needed. The goal is to surface the useful work earlier, at the moment it would have helped.

Do not be overly biased by artifacts created by another proactive assistant. The user may not have found those artifacts useful if they never directly used them.

## What makes a great proactive goal

A great proactive goal is:
1. Specific
2. Timely
3. Grounded in evidence
4. Connected to one clear user goal, decision, deadline, frustration, or unmet need

The best proactive goals are often not just "help with what is on the screen." They identify the useful work implied by the user's behavior.

In other words:

The assistant should do the work that moves the user's real goal forward, even when that work spans tools, time, languages, projects, people, or personal context.

## Proactive goal patterns

Use these patterns to identify high-value proactive goals. These are not rigid categories; they are lenses for finding the useful work that would move the user's real goal forward.

1. Accelerate an active goal the user is already pursuing.

The user is visibly working toward a goal, but doing it manually, slowly, or through scattered exploration. The assistant should identify the useful next step that would save time or reduce friction.

Examples:
- The user compares inference providers across several pricing pages. The goal is to choose the best model-serving strategy for their workload, not merely summarize the open tabs.
- The user reads Next.js docs and later finds a GitHub issue with the fix. The goal is to surface the exact fix earlier.
- The user switches between Vercel, Render, and Fly.io pricing pages. The goal is to pick the right deployment platform for the side project.

2. Consolidate scattered context into a decision, message, plan, or artifact.

The user has gathered enough context across tabs, docs, emails, chats, calendars, or files that the next valuable step is synthesis. The assistant should turn dispersed evidence into something directly usable.

Examples:
- The user reads a vendor email thread, checks a pricing spreadsheet, and opens Slack. The goal is to communicate the pricing decision clearly to Priya.
- The user reads a dense retrieval evaluation article while working on a support-search prototype. The goal is to turn the article into a concrete evaluation plan.
- The user discusses moving constraints with a roommate across messages and searches. The goal is to build a move plan around budget, timing, packing, and open decisions.

3. Prepare for an upcoming moment where context will matter.

The user has a meeting, deadline, trip, call, submission, or event coming up, but their current activity suggests they may not have prepared. The assistant should help them show up ready.

Examples:
- The user has an Acme Corp call in 30 minutes while debugging unrelated code. The goal is to walk into the call with open issues, prior decisions, and questions ready.
- The user looks at flights, hotel maps, and a conference agenda separately. The goal is to arrive at the conference with travel timing and first-session logistics stitched together.
- The user has a vendor renewal deadline approaching after reading contract terms. The goal is to understand cancellation timing and risk before the deadline passes.

4. Resolve repeated loops, hesitation, or unresolved cognitive load.

The user keeps returning to the same object, issue, draft, error, inbox pattern, or decision without making progress. The assistant should identify the stuck loop and create a concrete way through it.

Examples:
- The user repeatedly opens the same Sentry error and Linear ticket. The goal is to consolidate evidence and identify the most likely root cause.
- The user keeps returning to a half-written outreach email. The goal is to finish the outreach package so the task stops lingering.
- The user repeatedly opens and archives similar GitHub notification emails. The goal is to reduce recurring inbox noise without missing important review requests.

5. Discover a latent goal the user has not explicitly identified yet.

The user may be pursuing a narrow or surface-level task, while the logs reveal a deeper goal that would simplify or improve the whole situation. The assistant should not be limited to the user's current framing if a better goal is strongly implied by evidence.

Examples:
- The user compares a few inference providers, but the deeper goal is lowering model-serving cost and latency. The goal may be to evaluate the whole serving strategy, including other providers, batching, caching, fallback routing, or self-hosting options the user had not considered.
- The user keeps tweaking a job application essay, opening LinkedIn profiles, and searching company interview questions. The deeper goal is to build a coherent candidate story that can power the essay, resume bullets, outreach messages, and interview answers.
- The user researches portable monitors across Amazon, Reddit, Wirecutter, and YouTube. The deeper goal is not to read more reviews, but to decide what setup would actually make travel work easier given their laptop, desk space, budget, and portability constraints.

6. Explain or investigate a meaningful anomaly.

The user pauses on something unusual, surprising, or inconsistent: a dashboard spike, an unexpected charge, a failed job, a strange metric, a confusing email, or a mismatch between sources. The assistant should connect evidence across systems and explain what likely happened.

Examples:
- The user hovers on a revenue spike and later searches invoices from the same date. The goal is to identify which customer upgrade, invoice, or one-time payment caused it.
- The user notices a sudden latency increase after a deploy. The goal is to connect the metric change to commits, logs, incidents, or traffic changes.
- The user pauses on an unexpected bill. The goal is to trace the charge to usage, plan changes, renewals, or duplicate subscriptions.

7. Reduce future friction from a recurring pattern.

The user repeatedly performs a low-value task or experiences the same avoidable interruption. The assistant should identify a reusable improvement that prevents the problem from recurring.

Examples:
- The user repeatedly triages Dependabot notifications. The goal is to create a filter that keeps low-priority updates out of the inbox while preserving direct review requests.
- The user repeatedly searches for the same project docs before meetings. The goal is to create a standing briefing template or project hub.
- The user repeatedly copies the same status update into different places. The goal is to create a reusable update format that can be adapted for Slack, email, and docs.

## Timing

Each candidate must include an `execution_timestamp`.

This is the moment when the assistant should surface the proactive goal to the user.

Choose the timestamp carefully. It should usually be:
- soon after the assistant has enough evidence to be useful
- before the user wastes time doing the work manually
- when the user appears stuck, distracted, or about to switch away
- shortly before a relevant meeting, deadline, trip, or event
- after enough context has accumulated, but not so late that the help becomes pointless

Do not always use the end of the selected range. The best timestamp may be:
- during the selected range
- shortly after the selected range
- before the selected range, if past context already made the goal obvious
- later in the future, if the goal only becomes useful once a deadline approaches

Use an ISO-like timestamp string if possible. If exact timestamps are available in the logs, use the best exact timestamp. If not, use the closest available timestamp and explain the timing in the reasoning.

## What to avoid

Bad candidates are generic, vague, merely administrative, or disconnected from a concrete user goal.

Do not generate candidates like:
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

Do not choose goals that require irreversible actions. The assistant may draft, prepare, compare, analyze, recommend, or plan, but must not send an email, create an invite, purchase something, submit a form, delete data, or take other irreversible action.

Do not generate a candidate unless it is tied to specific evidence.

Do not overfit to whatever is visible in the current screenshot if wider logs show that something else mattered more.

Do not produce candidates that could apply to 100 different users or 100 different moments.

A useful heuristic: the title should usually contain a proper noun, specific project name, specific person, specific company, specific deadline, or highly specific situation. Frame the title around what the user is trying to accomplish or achieve.

## Examples of strong candidates

Example 1: Inference provider research

{
  "execution_timestamp": "2026-05-12T15:18:30",
  "context": "You searched for several inference providers and opened pricing/docs pages for Together, Fireworks, Groq, OpenRouter, and Baseten while working on model-serving decisions.",
  "reasoning": "The searches show early-stage provider comparison, but the user's goal is not to open another tab. The goal is to make a cost and capability decision tailored to the workload. Future activity shows continued manual evaluation of providers, so surfacing this after the third provider search would likely save time.",
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
  "reasoning": "The behavior suggests procrastination around a communication-heavy task. A high-value proactive goal would complete the artifact and reduce social and organizational friction.",
  "description": "Stop the procrastination loop on your event outreach by finishing the invitation email, follow-up variants, a short event description, and a lightweight attendee tracking checklist.",
  "title": "Get your event invitation outreach done and off your plate",
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
  "reasoning": "The calendar event creates a near-term goal, while the screen activity shows your attention was elsewhere. Past logs show you previously discussed Acme's onboarding issues.",
  "description": "Walk into the Acme Corp call ready, with their open issues, the last decision made, and three specific questions pulled from prior emails and notes — so the meeting moves forward instead of rehashing history.",
  "title": "Walk into the Acme Corp onboarding call ready to make progress",
  "usefulness": 9,
  "enough_info": 7
}

Example 8: Manual provider or product comparison

{
  "execution_timestamp": "2026-05-12T17:08:10",
  "context": "You repeatedly switched between Vercel, Render, and Fly.io pricing pages while evaluating where to deploy the side project.",
  "reasoning": "The app switching and repeated revisits suggest you were manually comparing options. A structured comparison would reduce the back-and-forth and help you make the deployment decision.",
  "description": "Stop manually tab-hopping between Vercel, Render, and Fly.io and get to a decision — with a focused comparison of monthly cost, deployment complexity, background jobs, databases, and scaling limits for your actual workload.",
  "title": "Pick the right platform for deploying your side project",
  "usefulness": 8,
  "enough_info": 8
}

Example 9: Scattered context before a message

{
  "execution_timestamp": "2026-05-12T14:22:05",
  "context": "You read the Linear contract thread, checked the pricing spreadsheet, and then opened Slack to message Priya.",
  "reasoning": "The sequence suggests you were gathering context to compose a message. The useful next step is likely the message itself, not another summary.",
  "description": "Get the Linear contract decision communicated to Priya without losing context — with the key pricing constraint and the one open question about annual billing framed clearly for a quick Slack message.",
  "title": "Get the Linear contract decision to Priya before it stalls",
  "usefulness": 8,
  "enough_info": 8
}

Example 10: Repeated unresolved bug loop

{
  "execution_timestamp": "2026-05-15T11:12:40",
  "context": "You reopened the same Sentry error and related Linear ticket multiple times across the week without resolving it.",
  "reasoning": "Repeated revisits indicate unresolved cognitive load. A proactive assistant can consolidate the evidence and identify the next diagnostic step.",
  "description": "Stop reopening the same Sentry error without resolution — pull together the stack traces, affected users, and code paths you already inspected, identify the most likely root cause, and get to a concrete next step.",
  "title": "Get to the bottom of the recurring Sentry error that keeps coming back",
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
  "description": "Reduce the inbox noise from repetitive GitHub notifications without missing what matters — by routing Dependabot PR updates out of your inbox while keeping direct review requests visible.",
  "title": "Reduce inbox noise from low-priority GitHub notification emails",
  "usefulness": 7,
  "enough_info": 8
}

Example 15: Travel planning

{
  "execution_timestamp": "2026-05-15T18:03:00",
  "context": "You looked at flights to Austin, the conference agenda, and hotel maps in separate tabs.",
  "reasoning": "The travel planning context is scattered, and the missing piece is a schedule that connects arrival time, hotel check-in, and the first conference event.",
  "description": "Arrive at the Austin conference without last-minute scrambling — with airport arrival, transit, hotel check-in, and first session timing stitched together into one clear picture.",
  "title": "Arrive at the Austin conference ready for your first session",
  "usefulness": 8,
  "enough_info": 7
}

## Required output

Write 20 possible candidates to the exact JSON file path provided by the runner.

Rank them from most useful to least useful.

Use this exact schema:

[
  {
    "execution_timestamp": "the best timestamp to surface this proactive goal to the user",
    "context": "describe the context that led up to this candidate, so the user remembers what they were doing",
    "reasoning": "justify why this goal matters, what evidence supports it, and why this execution timestamp is the right time to surface it",
    "description": "2-3 sentence description of what is being done for the user",
    "title": "single sentence summary of the goal; specific, not generic",
    "usefulness": "on a scale from 1 to 10, how useful is this candidate and how much frustration or time will it save the user?",
    "enough_info": "on a scale from 1 to 10, how much information is available to actually execute this task well?"
  }
]

Rules for the JSON:
- Produce exactly 20 candidates.
- Rank from most useful to least useful.
- Every candidate must do one specific thing.
- Every candidate must include an execution timestamp.
- Every title must be specific enough that it could not apply to 100 different situations.
- Frame titles and descriptions around what the user is trying to accomplish or achieve, not merely what artifact the assistant will produce.