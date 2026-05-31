# QA Type: Pre-Banger Threaded Mix

Generate 3 independent multi-turn threads. Each thread should mix the simple
pre-banger dimensions into a short non-Markovian sequence about intervention
timing and marginal value.

Each thread has 3-6 Q/A pairs. Later questions in a thread should naturally
depend on earlier answers by picking up a motive, tension, context clue,
engagement hook, likely next action, acceptance risk, or reason to wait. Threads
are independent; thread 1 must not depend on thread 0.

Good thread arcs include:

- Current attention -> likely next action -> intervention value -> wait/surface
- Curiosity -> personal relevance -> engagement risk -> self-done likelihood
- Timing -> surprise -> marginal value -> stay quiet or next useful surface
- Current attention -> latent want -> cool angle -> acceptance risk

Avoid questions that over-specify document structure, sections, schemas, or
deliverable formats. The thread should help a banger generator understand
whether help would be useful now, whether the user would do it anyway, and what
would make the intervention feel cool rather than noisy.

Return JSON only:

```json
{
  "qa_type": "{qa_type}",
  "seed_id": "string",
  "banger_timestamp": "string",
  "target_banger": {},
  "context_events": [],
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

Use `thread_id` values 0, 1, 2 in that order. Within each thread, `q_id` values
must be contiguous from 0.
