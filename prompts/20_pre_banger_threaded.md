# QA Type: Pre-Banger Threaded

Generate exactly 3 independent threads of Q/A pairs. A thread is a coherent
mini-conversation an assistant might have with the user model before deciding
whether to surface proactive help.

Each thread must have a clear throughline. Do not create three unrelated
questions under one thread. Do not repeat the same question across threads with
minor wording changes. You may also UPDATE the content of the answers based on 
logs-indexed to more naturally feel mult-turn.

Use these thread arcs:

- Thread 0, receptivity: current state -> timing signal -> surface/wait/stay
  quiet judgment.
- Thread 1, curiosity: visible concern -> uncertainty or belief -> what the
  user would value clarified.
- Thread 2, self-done: likely next action -> whether the user would check or
  solve it alone -> assistant marginal value.

Each thread should contain 3-`{pairs_per_run}` Q/A pairs. Later questions in a
thread should build on the earlier answers by narrowing the same user-state
question. Answers stay concise and should describe the user's preferences,
beliefs, tolerance, or likely behavior, not the hidden artifact's details.

Return JSON only:

```json
{
  "qa_type": "{qa_type}",
  "seed_id": "string",
  "banger_timestamp": "string",
  "target_banger": {},
  "threads": [
    {
      "thread_id": 0,
      "qa_pairs": []
    },
    {
      "thread_id": 1,
      "qa_pairs": []
    },
    {
      "thread_id": 2,
      "qa_pairs": []
    }
  ]
}
```
