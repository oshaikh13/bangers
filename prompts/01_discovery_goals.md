# Task

Analyze the `logs-indexed/` folder at this time:

{candidate_row}

Your job is to identify the user's goals. You may use subagents to help.

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
- idle time (look at differences between timestamps)
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

You may look into the future to identify what the user eventually needed. The goal is to surface the true goal earlier, at the moment it would have helped.

Do not be overly biased by artifacts created by another proactive assistant. The user may not have found those artifacts useful if they never directly used them.

## What makes a great proactive goal

A great proactive goal is:
1. Specific
2. Timely
3. Grounded in evidence
4. Connected to one clear user goal, decision, deadline, frustration, or unmet need
5. Useful enough that achieving it would materially save time, reduce frustration, avoid risk, or improve an outcome
6. Confidently inferred from behavior, timing, and surrounding logs, not merely plausible

The best proactive goals are often not just "help with what is on the screen." They identify the useful work implied by the user's behavior.

A goal should describe the outcome the user is trying to reach.

Examples:
- The user compares inference providers across several pricing pages. The goal is to choose the best model-serving strategy for their workload, not merely summarize the open tabs.
- The user reads Next.js docs and later finds a GitHub issue with the fix. The goal is to fix the specific caching issue earlier, not merely summarize documentation.
- The user switches between Vercel, Render, and Fly.io pricing pages. The goal is to pick the right deployment platform for the side project, not merely compare websites.
- The user reads a vendor email thread, checks a pricing spreadsheet, and opens Slack. The goal is to communicate the pricing decision clearly to Priya, not merely draft a generic message.
- The user discusses moving constraints with a roommate across messages and searches. The goal is to settle the move plan around budget, timing, packing, and open decisions, not merely create a checklist.

## Scoring usefulness, confidence, and attention gap

Every candidate must include `usefulness`, `confidence`, and `attention_gap`.

`usefulness` answers: if the user achieved this goal well, how valuable would that be for them?

Score high usefulness when the goal would save substantial time, reduce meaningful frustration, unblock a decision, prepare the user for an important moment, prevent a likely mistake, or improve an outcome the user clearly cares about. A goal can be useful even if more information would be needed to fully execute it.

`confidence` answers: how confident are you that the user actually has this goal in the first place?

Score high confidence when the goal is directly supported by repeated behavior, explicit searches, open artifacts, deadlines, meetings, messages, future follow-through, or strong cross-log evidence. Score lower confidence when the goal is a reasonable but speculative interpretation of ambiguous behavior.

Highly useful goals may be more speculative, resulting in lower confidence. Similarly, you may be very confident in a goal, but its usefulness is less of a priority in the user's eyes.

`attention_gap` answers: how likely is it that the user will NOT do this themselves now or in the immediate future because of time pressure, competing commitments, avoidance, context switching, etc.

Score high attention gap when the goal appears important but is being displaced by time pressure, competing commitments, productive avoidance, scattered context, repeated deferral, or context switching. Score low attention gap when the user is already honed in on the exact work and likely to do it immediately without help. You can look at future logs to determine this!

Examples:
- High attention gap: the user repeatedly opens a paper-writing checklist but keeps switching to adjacent debugging or admin work.
- High attention gap: the user expresses interest in writing a post but only reads related articles and never starts drafting.
- Low attention gap: the user is already in the tax filing flow, entering fields steadily, and has the source documents open.
- Low attention gap: the user is actively debugging the exact error and already making the patch.

## Proactive goal patterns

Use these patterns to identify high-value proactive goals. These are not rigid categories; they are lenses for finding the user's real goal.

### 1. Accelerate an active goal the user is already pursuing

The user is visibly working toward a goal, but doing it manually, slowly, or through scattered exploration.

Examples:
- The user compares inference providers across several pricing pages. The goal is to choose the best model-serving strategy for their workload, not merely summarize the open tabs.
- The user reads Next.js docs and later finds a GitHub issue with the fix. The goal is to find the exact fix earlier.
- The user switches between Vercel, Render, and Fly.io pricing pages. The goal is to pick the right deployment platform for the side project.

### 2. Consolidate scattered context into a decision, message, plan, or artifact

The user has gathered enough context across tabs, docs, emails, chats, calendars, or files that the real goal is synthesis.

Examples:
- The user reads a vendor email thread, checks a pricing spreadsheet, and opens Slack. The goal is to communicate the pricing decision clearly to Priya.
- The user reads a dense retrieval evaluation article while working on a support-search prototype. The goal is to use the article to decide what retrieval model or evaluation plan to use.
- The user discusses moving constraints with a roommate across messages and searches. The goal is to settle the move plan around budget, timing, packing, and open decisions.

### 3. Prepare for an upcoming moment where context will matter

The user has a meeting, deadline, trip, call, submission, or event coming up, and their activity suggests a specific goal tied to that moment.

Examples:
- The user has an Acme Corp call in 30 minutes while debugging unrelated code. The goal is to walk into the call with open issues, prior decisions, and questions ready.
- The user looks at flights, hotel maps, and a conference agenda separately. The goal is to arrive at the conference with travel timing and first-session logistics stitched together.
- The user has a vendor renewal deadline approaching after reading contract terms. The goal is to understand cancellation timing and risk before the deadline passes.

### 4. Resolve repeated loops, hesitation, or unresolved cognitive load

The user keeps returning to the same object, issue, draft, error, inbox pattern, or decision without making progress.

Examples:
- The user repeatedly opens the same Sentry error and Linear ticket. The goal is to consolidate evidence and identify the most likely root cause.
- The user keeps returning to a half-written outreach email. The goal is to finish the outreach email so the task stops lingering.
- The user repeatedly opens and archives similar GitHub notification emails. The goal is to reduce and categorize inbox noise without missing important review requests.

### 5. Discover a latent goal the user has not explicitly identified yet

The user may be pursuing a narrow surface-level task, while the logs reveal a deeper goal that would simplify or improve the whole situation.

Examples:
- The user compares a few inference providers, but the deeper goal is lowering model-serving cost and latency. The goal may be to evaluate the whole serving strategy, including other providers, batching, caching, fallback routing, or self-hosting options.
- The user keeps tweaking a job application essay, opening LinkedIn profiles, and searching company interview questions. The deeper goal is to build a coherent story that can power the essay, resume bullets, outreach messages, and interview answers.
- The user researches portable monitors across Amazon, Reddit, Wirecutter, and YouTube. The deeper goal is not to read more reviews, but to decide what setup would actually make travel work easier given their laptop, desk space, budget, and portability constraints.

### 6. Explain or investigate a meaningful anomaly

The user pauses on something unusual, surprising, or inconsistent: a dashboard spike, unexpected charge, failed job, strange metric, confusing email, or mismatch between sources.

Examples:
- The user hovers on a revenue spike and later searches invoices from the same date. The goal is to identify which customer upgrade, invoice, or one-time payment caused it.
- The user notices a sudden latency increase after a deploy. The goal is to connect the metric change to commits, logs, incidents, or traffic changes.
- The user pauses on an unexpected bill. The goal is to trace the charge to usage, plan changes, renewals, or duplicate subscriptions.

### 7. Reduce future friction from a recurring pattern

The user repeatedly performs a low-value task or experiences the same avoidable interruption.

Examples:
- The user repeatedly triages Dependabot notifications. The goal is to keep low-priority updates out of the inbox while preserving direct review requests.
- The user repeatedly searches for the same project docs before meetings. The goal is to have a reliable project hub or briefing source.
- The user repeatedly copies the same status update into different places. The goal is to create a reusable update format that can be adapted for Slack, email, and docs.

## Timing

Each candidate must include an `execution_timestamp`.

This is the moment when the user's goal becomes clear enough to surface.

Choose the timestamp carefully. It should usually be:
- soon after there is enough evidence to identify the goal
- before the user wastes time doing the work manually
- when the user appears stuck, distracted, or about to switch away
- shortly before a relevant meeting, deadline, trip, or event
- after enough context has accumulated, but not so late that surfacing the goal becomes pointless

Do not always use the end of the selected range. The best timestamp may be:
- during the selected range
- shortly after the selected range
- before the selected range, if past context already made the goal obvious
- later in the future, if the goal only becomes useful once a deadline approaches

Use an ISO-like timestamp string if possible. If exact timestamps are available in the logs, use the best exact timestamp. If not, use the closest available timestamp and explain the timing in the reasoning.

## What to avoid

Bad candidates are generic, vague, merely administrative, suggestion-like, or disconnected from a concrete user goal.

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

Do not generate a candidate when the user goal is merely plausible but not well-supported by logs.

Do not overfit to whatever is visible in the current screenshot if wider logs show that something else mattered more.

Do not produce candidates that could apply to 100 different users or 100 different moments.

A useful heuristic: the title should usually contain a proper noun, specific project name, specific person, specific company, specific deadline, or highly specific situation. Frame the title around what the user is trying to accomplish or achieve.

## Examples of strong candidates

Example 1: Inference provider research

{
  "execution_timestamp": "2026-05-12T15:18:30",
  "context": "You searched for several inference providers and opened pricing/docs pages for Together, Fireworks, Groq, OpenRouter, and Baseten while working on model-serving decisions.",
  "reasoning": "The searches show early-stage provider comparison, but the user's goal is not to open another tab. The goal is to make a cost and capability decision tailored to the workload. Future activity shows continued manual evaluation of providers, so surfacing this after the third provider search would likely save time.",
  "description": "Choose the inference provider setup that fits the user's actual model-serving workload, including cost, supported models, latency expectations, rate limits, batching support, and reliability concerns.",
  "goal": "Get from scattered provider research to a clear serving decision.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 2: Research analysis for LongNap

{
  "execution_timestamp": "2026-05-09T11:42:00",
  "context": "You had an active research thread about whether asking questions improves LongNap-style memory behavior, and you later inspected logs related to user questions and downstream outcomes.",
  "reasoning": "This is not just reading or note-taking; it implies an analysis goal. The relevant goal is to understand whether active questioning improves recall, task completion, or later usefulness.",
  "description": "Understand whether moments where the system asked clarifying or proactive questions led to better LongNap outcomes than moments where it did not.",
  "goal": "Identify which questioning behaviors lead to better LongNap outcomes and extract design implications for improving it.",
  "usefulness": "number from 1 to 10",
  "confidence":"number from 1 to 10"
}

Example 3: Human-like terminal-use tasks

{
  "execution_timestamp": "2026-05-10T16:05:15",
  "context": "You were exploring how to make terminal-use tasks more human-like, then later looked at datasets and examples of benchmark tasks.",
  "reasoning": "The project calls for empirical analysis, not just brainstorming. Future behavior shows the user needed patterns from datasets, so the goal is to identify what makes terminal-use tasks feel artificial versus realistic.",
  "description": "Understand what patterns make terminal-use benchmark tasks feel artificial versus human-like.",
  "goal": "Use relevant datasets and examples to produce concrete task design recommendations.",
  "usefulness": "number from 1 to 10",
  "confidence":"number from 1 to 10"
}

Example 4: Event outreach procrastination

{
  "execution_timestamp": "2026-05-13T20:24:45",
  "context": "You were repeatedly returning to an unfinished email about organizing an event, with signs of hesitation and task switching before completing the outreach.",
  "reasoning": "The behavior suggests procrastination around a communication-heavy task. The user's goal is to get the outreach finished so the event planning can move forward and stop lingering.",
  "description": "Finish the event invitation outreach and resolve the lingering communication task.",
  "goal": "Have the invite language, follow-up variants, event description, and attendee tracking clear enough to move forward.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 5: Moving plan with roommate

{
  "execution_timestamp": "2026-05-14T09:30:00",
  "context": "You and your roommate discussed moving plans, budget, neighborhood constraints, and anxiety about the move across messages, including some non-English conversation. Your move-in date created a clear deadline.",
  "reasoning": "The moving task is distributed across personal conversations, calendar dates, searches, and budget constraints. A generic reminder would miss the underlying goal: settling the move plan with the roommate before the deadline creates stress.",
  "description": "Settle the move plan with the roommate around the move-in date, budget, neighborhood constraints, packing timeline, and open decisions.",
  "goal": "Reduce anxiety and make the move feel concrete and manageable before the deadline.",
  "usefulness": "number from 1 to 10",
  "confidence":"number from 1 to 10"
}

Example 6: Answer found later

{
  "execution_timestamp": "2026-05-12T10:16:20",
  "context": "You spent time searching through Next.js caching docs, then later found a GitHub issue explaining that the behavior was caused by route segment config.",
  "reasoning": "Future activity shows the GitHub issue contained the answer the user needed. The goal was to resolve the caching bug, not to continue reading documentation.",
  "description": "Resolve the specific Next.js caching issue caused by route segment config.",
  "goal": "Reach the fix earlier and avoid the documentation search loop.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 7: Upcoming customer call

{
  "execution_timestamp": "2026-05-11T13:35:00",
  "context": "You had an upcoming call with Acme Corp, but you were deep in unrelated debugging and did not appear to prepare for the meeting.",
  "reasoning": "The calendar event creates a near-term goal, while the screen activity shows the user's attention was elsewhere. Past logs show prior discussion of Acme's onboarding issues, so the goal is to be ready to make progress in the call.",
  "description": "Walk into the Acme Corp onboarding call ready to move the account forward.",
  "goal": "Have open issues, prior decisions, and specific questions in mind before the meeting starts.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 8: Manual provider or product comparison

{
  "execution_timestamp": "2026-05-12T17:08:10",
  "context": "You repeatedly switched between Vercel, Render, and Fly.io pricing pages while evaluating where to deploy the side project.",
  "reasoning": "The app switching and repeated revisits suggest the user was manually comparing options. The underlying goal is to make a deployment decision for the actual workload, not continue tab-hopping.",
  "description": "Pick the right deployment platform for the side project based on cost, deployment complexity, background jobs, databases, and scaling limits.",
  "goal": "Commit to a deployment platform rather than continuing to manually compare options.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 9: Scattered context before a message

{
  "execution_timestamp": "2026-05-12T14:22:05",
  "context": "You read the Linear contract thread, checked the pricing spreadsheet, and then opened Slack to message Priya.",
  "reasoning": "The sequence suggests the user was gathering context in order to communicate a decision. The goal is to get the pricing constraint and annual billing question to Priya clearly before the decision stalls.",
  "description": "Get the Linear contract decision communicated to Priya while the pricing context is fresh.",
  "goal": "Make the key constraint and open annual billing question clear enough for a quick decision.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 10: Repeated unresolved bug loop

{
  "execution_timestamp": "2026-05-15T11:12:40",
  "context": "You reopened the same Sentry error and related Linear ticket multiple times across the week without resolving it.",
  "reasoning": "Repeated revisits indicate unresolved cognitive load. The goal is to get to a concrete diagnosis rather than keep reopening the same evidence.",
  "description": "Get to the bottom of the recurring Sentry error by connecting the stack traces, affected users, and code paths already inspected.",
  "goal": "Identify the likely root cause and reach a clear next diagnostic step.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 11: Dense reading tied to project

{
  "execution_timestamp": "2026-05-13T15:44:00",
  "context": "You spent several minutes reading a dense blog post about retrieval evaluation while also having recent work on the support-search prototype.",
  "reasoning": "The reading likely matters because it connects to a project the user has been working on. The goal is not to summarize the article, but to translate it into the project's evaluation plan.",
  "description": "Decide what retrieval evaluation direction to use for the support-search prototype, informed by the dense retrieval article the user just read.",
  "goal": "Have specific metrics, sample queries, and failure cases that can guide the prototype rather than continuing to absorb more background reading.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 12: Long legal or vendor review

{
  "execution_timestamp": "2026-05-14T16:27:30",
  "context": "You slowly read through the termination and auto-renewal sections of a vendor contract.",
  "reasoning": "Slow scrolling over legal language suggests careful review. The underlying goal is to understand the risk and deadline implications before the contract creates a problem.",
  "description": "Understand the termination, auto-renewal, payment, and liability risks in the vendor contract.",
  "goal": "Know the practical cancellation deadline and the consequences before renewal or commitment.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 13: Dashboard anomaly

{
  "execution_timestamp": "2026-05-12T09:55:15",
  "context": "You paused on a revenue dashboard chart showing a sharp spike on Tuesday and hovered around that data point.",
  "reasoning": "The pause suggests the anomaly mattered, but the dashboard alone may not explain it. Future logs show the user later searched for customer invoices around the same date, so the goal is to identify the cause of the spike.",
  "description": "Explain the Tuesday revenue spike by connecting it to invoices, customer upgrades, or one-time payments around that date.",
  "goal": "Understand whether the spike reflects real growth, an anomaly, or a one-off event.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 14: Repetitive inbox triage

{
  "execution_timestamp": "2026-05-13T08:51:20",
  "context": "You opened and archived several similar GitHub notification emails in a row.",
  "reasoning": "This is repetitive triage. Future logs show these notifications continue to interrupt the user's workflow, so the goal is to reduce inbox noise without losing important review requests.",
  "description": "Reduce the inbox noise from repetitive GitHub notifications while keeping important review requests visible.",
  "goal": "Stop low-priority updates from repeatedly interrupting the user's workflow.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

Example 15: Travel planning

{
  "execution_timestamp": "2026-05-15T18:03:00",
  "context": "You looked at flights to Austin, the conference agenda, and hotel maps in separate tabs.",
  "reasoning": "The travel planning context is scattered, and the missing piece is a schedule that connects arrival time, hotel check-in, and the first conference event. The goal is arriving prepared, not merely comparing travel information.",
  "description": "Coordinate the Austin conference arrival plan across flight timing, transit, hotel check-in, and the first session.",
  "goal": "Arrive without last-minute scrambling.",
  "usefulness": "number from 1 to 10",
  "confidence": "number from 1 to 10"
}

## Required output

Write 20 possible goals to the exact JSON file path provided by the runner.

Rank them primarily from most useful to least useful, but use confidence as a guardrail: a high-usefulness guess with weak evidence should rank below goals that are both useful and well-supported.

Use this exact schema:

[
  {
    "execution_timestamp": "the best timestamp when this goal becomes clear enough to surface",
    "context": "describe the context that led up to this goal, so the user remembers what they were doing",
    "reasoning": "justify why this goal matters, what evidence supports it, and why this execution timestamp is the right time to surface it",
    "description": "1-2 sentences describing the user's goal, including the specific scope, dimensions, or decisions involved",
    "goal": "one sentence stating the concrete outcome the user wants to reach",
    "usefulness": "on a scale from 1 to 10, how useful would achieving this goal be for the user?",
    "confidence": "on a scale from 1 to 10, how confident are you that the user actually has this goal in the first place?",
    "attention_gap": "on a scale from 1 to 10, how much does the user seem to want or need this while not giving it focused attention in the near future?"
  }
]

Rules for the JSON:
- Produce exactly 20 goals.
- Every candidate must describe one specific user goal.
- Generate goals across the confidence range.
- Every candidate must include an execution timestamp.
- Every candidate must include integer `usefulness`, `confidence`, and `attention_gap` scores from 1 to 10.
- Every title must be specific enough that it could not apply to a different situation.
