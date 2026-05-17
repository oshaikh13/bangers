# Task

Analyze the logs-indexed folder at this time:

{candidate_row}

First, carefully analyze what the user is doing during this time, minute by minute.

Second, identify all the places where an AI assistant could've proactively helped. You can look into the future to identify what the user actually does or doesn't do, and personalize suggestions based on what the user has done in the past. You can look for signs of frustration (distraction, procrastination, disorganization, etc. by analyzing mouse movement, app switching, or other context clues).

Screen rows may include `source.screenshot_path`. These paths are relative to `logs-indexed/`, for example `logs-indexed/screenshots/2026-05-12_15-03-12-864819.png`. When text summaries or dense captions are insufficient, inspect the relevant screenshots directly and use them as visual evidence.

## Types of Suggestions

Generate a range of suggestions. The kind of suggestion I want are things that:

(a) Align with something I will do in the future- like, my focus is distracted, but I'll get to it in the future. And you can realize that future _now_ or soon after I get distracted. In a sense, these are things that will help me spend less time on my computer. Take note of the final artifact I find useful (a message, email, or research / reading I do, etc.)

or

(b) Something that I wouldn't think to do or clearly don't have time to do, but that information would unlock a lot of utility for me. So things like researching or making connections for something upcoming; or getting the right context for a question or meeting I have, etc.

Once you have a draft set of suggestions, look carefully through future and past logs, widening your search far *beyond* the selected range.

Additionally, categorize if you think these suggestions could run in the background, asynchronously, and surfaced later; or should be foregrounded and shown immediately to the user.

## Priorities

ALL SUGGESTIONS MUST BE SPECIFIC AND DO A SINGLE THING! Do not generate something generic that could be applied to many things (for example: DO NOT generate "draft preparation for meeting" - mention the specific meeting with a SINGLE entity).

Don't be overly biased by artifacts created by another proactive assistant - it could be that the user did NOT find these suggestions useful, if they never used them. 

Suggestions cannot take irreversible action (e.g. send an email, create an invite, etc; but they can SUGGEST doing such a thing.)

## Format

Think carefully and slowly, and explore the logs thoroughly. If you need more detail, read the relevant raw screenshots from the paths attached to screen rows.

Write 20 possible candidates to the exact JSON file path provided by the runner, ranging from most useful to least useful, with the following schema:

[{
    "context": "describe the context that lead up to this suggestion to remind the user what they were doing",
    "reasoning": "justification for why this task is needed and what the sources are used",
    "title": "concrete and specific name of the suggestion. start with a verb",
    "usefulness": "on a scale from 1 to 10, how useful is this suggestion? how much frustration will it save the user?",
    "enough_info": "on a scale from 1 to 10, do you have enough context to actually execute this task? or do you need more info?",
    "task_type": "async or sync",
    "utility_type": "a or b",
    "description": "detailed description of what is being executed"
}]