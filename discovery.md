# Task

Analyze the logs-indexed folder at this time:

{candidate_row}

First, carefully analyze what the user is doing during this time.

Second, identify all the places where an AI assistant could've proactively helped. You can look into the future to identify what the user actually does or doesn't do, and personalize suggestions based on what the user has done in the past.

## Rules

Generate a range of suggestions:

The kind of suggestion I want are things that:

(a) Align with something I will do in the future- like, my focus is distracted, but I'll get to it in the future. And you can realize that future _now_ or soon after I get distracted. In a sense, these are things that will help me spend less time on my computer. Take note of the final artifact I find useful (a message, email, or research / reading I do, etc.)

or

(b) Something that I would never even think to do / search, but that information would unlock a lot of utility for me. So things like researching or making connections; or getting the right context for a question or meeting I have, etc.

Once you have a draft set of suggestions, look carefully through future and past logs, widening your search far *beyond* the selected range.

Additionally, categorize if you think these suggestions could run in the background, asynchronously, and surfaced later; or should be foregrounded and shown immediately to the user.

ALL SUGGESTIONS MUST BE SPECIFIC AND DO A SINGLE THING! Do not generate something generic that could be applied to many things (for example: DO NOT generate "draft preparation for meeting" - mention the specific meeting)

## Format

Think carefully and slowly, and explore the logs thoroughly. 

Write 20 possible candidates to a JSON file called candidate_{interval_index}.json under the /candidates folder, ranging from most useful to least useful, with the following schema:

[{
    "reasoning": "justification for why this task is needed and what the sources are used",
    "title": "concrete name of the suggestion, start with a title",
    "usefulness": "on a scale from 1 to 10, how useful is this suggestion?",
    "task_type": "async or sync",
    "utility_type": "a or b",
    "description": "detailed description of what is being executed"
}]