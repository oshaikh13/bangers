# Full Rollout Architecture

This document defines the runtime structure for a proactive language model that reads Omar's passive activity logs, maintains opportunity state, uses tools when needed, and decides whether to stay quiet, prepare in the background, or surface help.

The model is called on a regular tick. It receives a prebuilt context window and may use tools for long-range retrieval and durable writes.

## Core Principle

The hot path should not require tool calls to fetch obvious context.

Always in context:

- `recent_activity`
- `recent_interventions`
- `active_opportunities`
- `policy`
- compact `user_profile`

Available through search tools:

- older activity
- older interventions
- long-term semantic memory
- old or resolved opportunities

Writable stores:

- opportunity store
- intervention log
- memory store

Passive sensors write the activity log. The model does not write activity events.

## Stores

### Activity Log

Raw or summarized passive events from connectors.

Examples:

- screen events
- calendar events
- email summaries
- notifications
- file system events
- audio/transcript summaries

The model sees a recent slice in `recent_activity`. It can search older activity with `search_activity`.

### Opportunity Store

Durable structured state for possible assistant help.

An opportunity can be new, prepared, surfaced, updated, resolved, expired, or dismissed. This store is the main mechanism for background preparation and duplicate prevention.

Example:

```json
{
  "id": "powernap_moments_filter_debug",
  "dedupe_key": "powernap:moments_filter:manual_run_debugging",
  "state": "surfaced",
  "first_seen_at": "2026-04-07T17:39:50Z",
  "last_updated_at": "2026-04-07T17:44:58Z",
  "surfaced_at": "2026-04-07T17:41:47Z",
  "cooldown_until": "2026-04-07T17:51:47Z",
  "expires_at": null,
  "confidence": 0.91,
  "urgency": 0.82,
  "interruption_cost": 0.35,
  "current_instruction": "Debug the `Operation not permitted` failure when copying files into logs-tada.",
  "background_summary": "Need shifted from command syntax to write permissions or sandbox access for logs-tada.",
  "next_best_action": "Help with permissions if Omar keeps inspecting the error or asks why."
}
```

### Intervention Log

Structured record of what the assistant already surfaced.

This is operational history, not general memory. It prevents repeats and tracks outcomes.

Example:

```json
{
  "id": "int_2026_04_07_174458_powernap_filter",
  "opportunity_id": "powernap_moments_filter_debug",
  "dedupe_key": "powernap:moments_filter:manual_run_debugging",
  "shown_at": "2026-04-07T17:44:58Z",
  "channel": "assistant_panel",
  "summary": "Explained that the filter failure is a logs-tada write permission issue.",
  "message_hash": "sha256:...",
  "outcome": "shown"
}
```

### Memory Store

Long-term semantic memory: stable preferences, project facts, people, recurring workflows, and compact summaries.

Example:

```json
{
  "id": "mem_debugging_style_command_first",
  "type": "preference",
  "content": "Omar prefers command-first debugging help with concise explanation after the command.",
  "confidence": 0.82,
  "created_at": "2026-04-07T18:00:00Z",
  "updated_at": "2026-04-07T18:00:00Z"
}
```

## Tick Context

Before each model call, the runtime context builder assembles the tick context.

It should include:

```json
{
  "tick": {
    "time": "2026-04-07T17:44:58Z",
    "window": "last_10_minutes",
    "timezone": "America/Los_Angeles"
  },
  "recent_activity": [],
  "recent_interventions": [],
  "active_opportunities": [],
  "policy": {},
  "user_profile": {},
  "retrieved_context": {
    "relevant_activity": [],
    "relevant_interventions": [],
    "relevant_memory": [],
    "relevant_opportunities": []
  }
}
```

### Recent Activity

Always included. This is the fixed passive log slice.

```json
[
  {
    "ts": "2026-04-07T17:41:47Z",
    "connector": "screen",
    "text": "Omar asks whether he can run the Moments command from higher up so `./logs` works.",
    "source_ref": "logs-indexed/screen/2026-04-07.jsonl:37"
  },
  {
    "ts": "2026-04-07T17:43:49Z",
    "connector": "screen",
    "text": "Omar runs `uv run python -m apps.moments.filter ./logs`.",
    "source_ref": "logs-indexed/screen/2026-04-07.jsonl:49"
  },
  {
    "ts": "2026-04-07T17:44:58Z",
    "connector": "screen",
    "text": "Terminal shows `Operation not permitted` copying into logs-tada, and Omar selects the error text.",
    "source_ref": "logs-indexed/screen/2026-04-07.jsonl:58"
  }
]
```

### Recent Interventions

Always included. This should be compact and time-bounded.

```json
[
  {
    "shown_at": "2026-04-07T17:41:47Z",
    "opportunity_id": "powernap_moments_filter_debug",
    "dedupe_key": "powernap:moments_filter:manual_run_debugging",
    "channel": "assistant_panel",
    "summary": "Suggested `uv run python -m apps.moments.filter ./logs` from the powernap repo root.",
    "outcome": "shown"
  }
]
```

### Active Opportunities

Always included. This includes candidates, background-prepared opportunities, surfaced opportunities still in cooldown, and unresolved opportunities.

```json
[
  {
    "id": "powernap_moments_filter_debug",
    "dedupe_key": "powernap:moments_filter:manual_run_debugging",
    "state": "surfaced",
    "confidence": 0.84,
    "urgency": 0.7,
    "surfaced_at": "2026-04-07T17:41:47Z",
    "cooldown_until": "2026-04-07T17:51:47Z",
    "current_instruction": "Help Omar run the Moments filter command with correct cwd and uv invocation.",
    "background_summary": "Use `uv run python -m apps.moments.filter ./logs` from the powernap repo root."
  }
]
```

### Policy

Always included. This controls proactivity and channels.

```json
{
  "proactivity": "balanced",
  "thresholds": {
    "background_prepare": 0.35,
    "ambient": 0.55,
    "surface": 0.75,
    "interrupt": 0.9
  },
  "channels": {
    "background_prepare": true,
    "ambient_badge": true,
    "assistant_panel": true,
    "notification": false
  },
  "topic_overrides": {
    "deadlines": "lower",
    "travel": "lower",
    "debugging": "medium",
    "social": "higher"
  }
}
```

### User Profile

Always included, but compact.

```json
{
  "summary": "Omar is building personal user-modeling / proactive-assistant infrastructure using passive logs.",
  "preferences": [
    "Prefer concise, command-first debugging help.",
    "Allow liberal background preparation.",
    "Be conservative with actual interruptions."
  ]
}
```

## Tools

The model can use tools for context expansion and durable writes.

It should not normally call tools for recent activity, recent interventions, or active opportunities because those are already in the tick context.

### Retrieval Tools

#### `search_activity`

Search older passive logs.

Use when the current tick hints at an opportunity but needs older evidence.

Schema:

```json
{
  "query": "string",
  "time_range": {
    "start": "iso timestamp or relative string",
    "end": "iso timestamp or relative string"
  },
  "connectors": ["screen", "calendar", "email", "notifications", "filesys", "audio"],
  "limit": 10
}
```

Example:

```json
{
  "query": "Barcelona Airbnb hotel tax departure",
  "time_range": {"start": "last_30_days", "end": "now"},
  "connectors": ["email", "calendar", "screen"],
  "limit": 10
}
```

#### `search_interventions`

Search older assistant interventions.

Use for duplicate checks beyond the recent intervention window, or to learn whether similar suggestions were ignored.

Schema:

```json
{
  "query": "string or null",
  "opportunity_id": "string or null",
  "dedupe_key": "string or null",
  "time_range": {
    "start": "iso timestamp or relative string",
    "end": "iso timestamp or relative string"
  },
  "limit": 10
}
```

Example:

```json
{
  "query": null,
  "opportunity_id": null,
  "dedupe_key": "travel:barcelona:predeparture",
  "time_range": {"start": "last_14_days", "end": "now"},
  "limit": 5
}
```

#### `search_memory`

Search long-term semantic memory.

Use for preferences, stable project facts, people, and recurring patterns.

Schema:

```json
{
  "query": "string",
  "types": ["preference", "project", "person", "travel", "workflow", "summary"],
  "limit": 10
}
```

Example:

```json
{
  "query": "Omar travel checklist interruption preferences",
  "types": ["preference", "travel", "summary"],
  "limit": 5
}
```

#### `search_opportunities`

Search old, resolved, expired, or dismissed opportunities.

Active opportunities are already in context, so this tool is only for long-range lookup.

Schema:

```json
{
  "query": "string or null",
  "dedupe_key": "string or null",
  "states": ["resolved", "expired", "dismissed", "surfaced", "prepared"],
  "time_range": {
    "start": "iso timestamp or relative string",
    "end": "iso timestamp or relative string"
  },
  "limit": 10
}
```

### Write Tools

#### `upsert_opportunity`

Create or update an opportunity.

Use for `background_prepare`, `wait_for_more_evidence`, `surface_now`, and `update_existing`.

Schema:

```json
{
  "id": "string",
  "dedupe_key": "string",
  "state": "candidate | prepared | surfaced | resolved | expired | dismissed",
  "first_seen_at": "iso timestamp",
  "last_updated_at": "iso timestamp",
  "surfaced_at": "iso timestamp or null",
  "cooldown_until": "iso timestamp or null",
  "expires_at": "iso timestamp or null",
  "confidence": 0.0,
  "urgency": 0.0,
  "interruption_cost": 0.0,
  "current_instruction": "string",
  "background_summary": "string",
  "next_best_action": "string",
  "evidence_refs": ["source refs"]
}
```

#### `mark_opportunity_state`

Small state transition for an existing opportunity.

Use when resolving, expiring, or dismissing without rewriting the full record.

Schema:

```json
{
  "id": "string",
  "state": "resolved | expired | dismissed",
  "reason": "string",
  "at": "iso timestamp"
}
```

#### `record_intervention`

Record that the assistant actually surfaced something.

Use whenever the model emits a user-facing suggestion through any channel.

Schema:

```json
{
  "opportunity_id": "string",
  "dedupe_key": "string",
  "shown_at": "iso timestamp",
  "channel": "ambient_badge | assistant_panel | notification | chat",
  "summary": "string",
  "message": "string",
  "message_hash": "string or null",
  "outcome": "shown | ignored | clicked | dismissed | accepted | unknown"
}
```

#### `write_memory`

Write durable semantic memory.

Use sparingly. Do not use it for every intervention or every opportunity update.

Schema:

```json
{
  "type": "preference | project | person | travel | workflow | summary",
  "content": "string",
  "confidence": 0.0,
  "source_refs": ["source refs"],
  "created_at": "iso timestamp",
  "updated_at": "iso timestamp"
}
```

## Model Output Contract

Every tick should produce a structured decision.

```json
{
  "decision": {
    "action": "no_action | background_prepare | wait_for_more_evidence | surface_now | update_existing | mark_resolved",
    "opportunity_id": "string or null",
    "dedupe_key": "string or null",
    "confidence": 0.0,
    "urgency": 0.0,
    "intervention_score": 0.0,
    "reason": "string"
  },
  "tool_calls": [],
  "user_message": null
}
```

If `user_message` is non-null, the rollout must also include a `record_intervention` write.

If the action creates or updates an opportunity, the rollout must include `upsert_opportunity` or `mark_opportunity_state`.

## Full Rollout: Moments Filter Debugging

This is an example of what a real rollout could look like across several ticks.

### Tick 1: Notice But Do Not Interrupt

Input tick context:

```json
{
  "tick": {
    "time": "2026-04-07T17:39:50Z",
    "window": "last_10_minutes"
  },
  "recent_activity": [
    {
      "ts": "2026-04-07T17:39:50Z",
      "connector": "screen",
      "text": "Omar asks whether he can kick off the Moments workflow manually from the command line.",
      "source_ref": "logs-indexed/screen/2026-04-07.jsonl:18"
    }
  ],
  "recent_interventions": [],
  "active_opportunities": [],
  "policy": {
    "thresholds": {
      "background_prepare": 0.35,
      "surface": 0.75,
      "interrupt": 0.9
    }
  },
  "user_profile": {
    "preferences": ["Allow liberal background preparation.", "Be conservative with interruptions."]
  },
  "retrieved_context": {
    "relevant_activity": [],
    "relevant_interventions": [],
    "relevant_memory": [],
    "relevant_opportunities": []
  }
}
```

Model output:

```json
{
  "decision": {
    "action": "background_prepare",
    "opportunity_id": "powernap_moments_filter_debug",
    "dedupe_key": "powernap:moments_filter:manual_run_debugging",
    "confidence": 0.62,
    "urgency": 0.45,
    "intervention_score": 0.47,
    "reason": "Omar may need command-line invocation help, but he has not failed or repeated the question yet."
  },
  "tool_calls": [
    {
      "name": "upsert_opportunity",
      "arguments": {
        "id": "powernap_moments_filter_debug",
        "dedupe_key": "powernap:moments_filter:manual_run_debugging",
        "state": "prepared",
        "first_seen_at": "2026-04-07T17:39:50Z",
        "last_updated_at": "2026-04-07T17:39:50Z",
        "surfaced_at": null,
        "cooldown_until": null,
        "expires_at": null,
        "confidence": 0.62,
        "urgency": 0.45,
        "interruption_cost": 0.35,
        "current_instruction": "Prepare help for manually running the Moments workflow.",
        "background_summary": "Omar may need command-line invocation help for the Moments pipeline.",
        "next_best_action": "Wait for another command/cwd question or a terminal error.",
        "evidence_refs": ["logs-indexed/screen/2026-04-07.jsonl:18"]
      }
    }
  ],
  "user_message": null
}
```

### Tick 2: Update And Keep Waiting

Input changes:

- `active_opportunities` includes `powernap_moments_filter_debug`.
- Recent activity now includes Omar asking whether this should be run with `uv`.

Model output:

```json
{
  "decision": {
    "action": "wait_for_more_evidence",
    "opportunity_id": "powernap_moments_filter_debug",
    "dedupe_key": "powernap:moments_filter:manual_run_debugging",
    "confidence": 0.74,
    "urgency": 0.55,
    "intervention_score": 0.61,
    "reason": "The opportunity is more likely, but Omar is still receiving answer context and no error has appeared."
  },
  "tool_calls": [
    {
      "name": "upsert_opportunity",
      "arguments": {
        "id": "powernap_moments_filter_debug",
        "dedupe_key": "powernap:moments_filter:manual_run_debugging",
        "state": "prepared",
        "first_seen_at": "2026-04-07T17:39:50Z",
        "last_updated_at": "2026-04-07T17:41:10Z",
        "surfaced_at": null,
        "cooldown_until": null,
        "expires_at": null,
        "confidence": 0.74,
        "urgency": 0.55,
        "interruption_cost": 0.35,
        "current_instruction": "Prepare help for running the Moments filter with uv and the correct working directory.",
        "background_summary": "Likely command: `uv run python -m apps.moments.filter ./logs`; cwd may matter.",
        "next_best_action": "Surface if Omar asks another adjacent command/cwd question.",
        "evidence_refs": [
          "logs-indexed/screen/2026-04-07.jsonl:18",
          "logs-indexed/screen/2026-04-07.jsonl:32"
        ]
      }
    }
  ],
  "user_message": null
}
```

### Tick 3: Surface Help

Input changes:

- Omar asks whether he can run from higher up so `./logs` works.
- Same active opportunity is in context.
- No recent intervention for this opportunity exists.

Model output:

```json
{
  "decision": {
    "action": "surface_now",
    "opportunity_id": "powernap_moments_filter_debug",
    "dedupe_key": "powernap:moments_filter:manual_run_debugging",
    "confidence": 0.84,
    "urgency": 0.7,
    "intervention_score": 0.78,
    "reason": "This is now a repeated command/cwd uncertainty, crossing the surface threshold."
  },
  "tool_calls": [
    {
      "name": "upsert_opportunity",
      "arguments": {
        "id": "powernap_moments_filter_debug",
        "dedupe_key": "powernap:moments_filter:manual_run_debugging",
        "state": "surfaced",
        "first_seen_at": "2026-04-07T17:39:50Z",
        "last_updated_at": "2026-04-07T17:41:47Z",
        "surfaced_at": "2026-04-07T17:41:47Z",
        "cooldown_until": "2026-04-07T17:51:47Z",
        "expires_at": null,
        "confidence": 0.84,
        "urgency": 0.7,
        "interruption_cost": 0.35,
        "current_instruction": "Help Omar run the Moments filter command with the correct cwd and uv invocation.",
        "background_summary": "Use `uv run python -m apps.moments.filter ./logs` from the powernap repo root; adjust logs path if running elsewhere.",
        "next_best_action": "If the command fails, update the same opportunity with the concrete error.",
        "evidence_refs": [
          "logs-indexed/screen/2026-04-07.jsonl:18",
          "logs-indexed/screen/2026-04-07.jsonl:32",
          "logs-indexed/screen/2026-04-07.jsonl:37"
        ]
      }
    },
    {
      "name": "record_intervention",
      "arguments": {
        "opportunity_id": "powernap_moments_filter_debug",
        "dedupe_key": "powernap:moments_filter:manual_run_debugging",
        "shown_at": "2026-04-07T17:41:47Z",
        "channel": "assistant_panel",
        "summary": "Suggested the uv command and cwd assumption for Moments filter.",
        "message": "From the `powernap` repo root, run `uv run python -m apps.moments.filter ./logs`. If you run it from another directory, adjust the logs path accordingly.",
        "message_hash": null,
        "outcome": "shown"
      }
    }
  ],
  "user_message": "From the `powernap` repo root, run `uv run python -m apps.moments.filter ./logs`. If you run it from another directory, adjust the logs path accordingly."
}
```

### Tick 4: Update Existing Opportunity With Concrete Error

Input changes:

- Recent activity shows the command ran.
- Terminal shows `Operation not permitted` copying into logs-tada.
- Recent interventions includes the command/cwd suggestion from Tick 3.
- Active opportunity is in `surfaced` state and cooldown.

Model output:

```json
{
  "decision": {
    "action": "update_existing",
    "opportunity_id": "powernap_moments_filter_debug",
    "dedupe_key": "powernap:moments_filter:manual_run_debugging",
    "confidence": 0.91,
    "urgency": 0.82,
    "intervention_score": 0.81,
    "reason": "There is materially new evidence: the problem is now a logs-tada write permission failure, not command syntax."
  },
  "tool_calls": [
    {
      "name": "upsert_opportunity",
      "arguments": {
        "id": "powernap_moments_filter_debug",
        "dedupe_key": "powernap:moments_filter:manual_run_debugging",
        "state": "surfaced",
        "first_seen_at": "2026-04-07T17:39:50Z",
        "last_updated_at": "2026-04-07T17:44:58Z",
        "surfaced_at": "2026-04-07T17:41:47Z",
        "cooldown_until": "2026-04-07T17:51:47Z",
        "expires_at": null,
        "confidence": 0.91,
        "urgency": 0.82,
        "interruption_cost": 0.25,
        "current_instruction": "Debug the `Operation not permitted` failure when copying files into logs-tada.",
        "background_summary": "The need shifted from command syntax to write permissions or sandbox access for `/Users/oshaikh/Documents/GeneralUserModels/powernap/logs-tada/`.",
        "next_best_action": "Do not repeat command syntax advice; help inspect permissions or sandbox path allowlists.",
        "evidence_refs": [
          "logs-indexed/screen/2026-04-07.jsonl:49",
          "logs-indexed/screen/2026-04-07.jsonl:57",
          "logs-indexed/screen/2026-04-07.jsonl:58"
        ]
      }
    },
    {
      "name": "record_intervention",
      "arguments": {
        "opportunity_id": "powernap_moments_filter_debug",
        "dedupe_key": "powernap:moments_filter:manual_run_debugging",
        "shown_at": "2026-04-07T17:44:58Z",
        "channel": "assistant_panel",
        "summary": "Explained that the failure is a logs-tada write permission or sandbox issue.",
        "message": "That error is no longer about the command shape. The process cannot write into `logs-tada`; check directory permissions, sandbox allowlists, and whether existing files are locked or owned by another process.",
        "message_hash": null,
        "outcome": "shown"
      }
    }
  ],
  "user_message": "That error is no longer about the command shape. The process cannot write into `logs-tada`; check directory permissions, sandbox allowlists, and whether existing files are locked or owned by another process."
}
```

### Tick 5: Suppress Duplicate

Input changes:

- Omar asks `any idea why?`
- Recent interventions already include a permission-debugging suggestion seconds earlier.

Model output:

```json
{
  "decision": {
    "action": "no_action",
    "opportunity_id": "powernap_moments_filter_debug",
    "dedupe_key": "powernap:moments_filter:manual_run_debugging",
    "confidence": 0.93,
    "urgency": 0.86,
    "intervention_score": 0.28,
    "reason": "The same permission-debugging help was just surfaced. No materially new evidence has appeared."
  },
  "tool_calls": [],
  "user_message": null
}
```

## Full Rollout: Barcelona Background Preparation

This rollout shows the background path.

### Tick 1: Prepare In Background

Input:

- Recent email summaries include Barcelona booking information.
- Calendar includes `Stay at Barcelona Princess`.
- Email includes Airbnb reservation and tax deadline reminders.
- Omar is not currently working on travel.

The model may call long-range retrieval if the recent slice is incomplete:

```json
{
  "name": "search_activity",
  "arguments": {
    "query": "Barcelona Airbnb hotel tax departure",
    "time_range": {"start": "last_30_days", "end": "now"},
    "connectors": ["email", "calendar", "screen"],
    "limit": 10
  }
}
```

Model output:

```json
{
  "decision": {
    "action": "background_prepare",
    "opportunity_id": "barcelona_trip_prep",
    "dedupe_key": "travel:barcelona:predeparture",
    "confidence": 0.76,
    "urgency": 0.55,
    "intervention_score": 0.58,
    "reason": "Travel preparation is likely useful, but Omar is not currently acting on travel."
  },
  "tool_calls": [
    {
      "name": "upsert_opportunity",
      "arguments": {
        "id": "barcelona_trip_prep",
        "dedupe_key": "travel:barcelona:predeparture",
        "state": "prepared",
        "first_seen_at": "2026-04-07T21:03:25Z",
        "last_updated_at": "2026-04-07T21:03:25Z",
        "surfaced_at": null,
        "cooldown_until": null,
        "expires_at": "2026-04-22T23:59:59Z",
        "confidence": 0.76,
        "urgency": 0.55,
        "interruption_cost": 0.45,
        "current_instruction": "Prepare a Barcelona pre-departure checklist.",
        "background_summary": "Confirm lodging split, verify flight details, handle taxes before departure or Apr 15, and prepare passport/ETIAS/offline maps/adapters/bank checklist.",
        "next_best_action": "Surface if Omar opens travel files, departure is close, or missing accommodation is detected.",
        "evidence_refs": [
          "logs-indexed/calendar/2026-04-07.jsonl:1",
          "logs-indexed/email/2026-04-07.jsonl:3",
          "logs-indexed/email/2026-04-07.jsonl:6",
          "logs-indexed/email/2026-04-07.jsonl:21"
        ]
      }
    }
  ],
  "user_message": null
}
```

### Tick 2: Surface When Context Becomes Relevant

Input changes:

- Omar opens `zurich_barcelona_trip_prep.md`.
- The file includes travel checklist items.
- Active opportunity `barcelona_trip_prep` is already prepared.

Model output:

```json
{
  "decision": {
    "action": "surface_now",
    "opportunity_id": "barcelona_trip_prep",
    "dedupe_key": "travel:barcelona:predeparture",
    "confidence": 0.88,
    "urgency": 0.78,
    "intervention_score": 0.82,
    "reason": "Omar is now looking at the travel-prep artifact, so surfacing the prepared checklist is timely."
  },
  "tool_calls": [
    {
      "name": "upsert_opportunity",
      "arguments": {
        "id": "barcelona_trip_prep",
        "dedupe_key": "travel:barcelona:predeparture",
        "state": "surfaced",
        "first_seen_at": "2026-04-07T21:03:25Z",
        "last_updated_at": "2026-04-08T16:31:58Z",
        "surfaced_at": "2026-04-08T16:31:58Z",
        "cooldown_until": "2026-04-08T20:31:58Z",
        "expires_at": "2026-04-22T23:59:59Z",
        "confidence": 0.88,
        "urgency": 0.78,
        "interruption_cost": 0.3,
        "current_instruction": "Help Omar act on Barcelona pre-departure checklist items.",
        "background_summary": "Time-sensitive items: confirm accommodation, verify flight details, file taxes or extension, passport/ETIAS/EES, bank notification, offline maps, adapters, euros.",
        "next_best_action": "Help execute or prioritize checklist items if Omar engages.",
        "evidence_refs": [
          "logs-indexed/screen/2026-04-08.jsonl:315",
          "logs-indexed/screen/2026-04-08.jsonl:316",
          "logs-indexed/screen/2026-04-08.jsonl:317"
        ]
      }
    },
    {
      "name": "record_intervention",
      "arguments": {
        "opportunity_id": "barcelona_trip_prep",
        "dedupe_key": "travel:barcelona:predeparture",
        "shown_at": "2026-04-08T16:31:58Z",
        "channel": "assistant_panel",
        "summary": "Surfaced Barcelona pre-departure checklist and urgent tax/accommodation items.",
        "message": "You have Barcelona travel coming up, and this checklist has a few time-sensitive loose ends: confirm accommodation, verify flight details, and handle taxes before departure or Apr 15.",
        "message_hash": null,
        "outcome": "shown"
      }
    }
  ],
  "user_message": "You have Barcelona travel coming up, and this checklist has a few time-sensitive loose ends: confirm accommodation, verify flight details, and handle taxes before departure or Apr 15."
}
```

## Training Data Implications

Constructed SFT examples should mirror the full rollout contract.

Each training example should include:

- prebuilt tick context
- any optional retrieval tool calls and results
- write tool calls
- optional user-facing message
- hidden audit metadata showing future validation and leakage checks

Each opportunity should produce a trajectory, not one isolated row:

```text
background_prepare -> wait_for_more_evidence -> surface_now -> update_existing -> no_action duplicate suppression -> mark_resolved
```

The final constructed training artifact should be an opportunity trajectory:

```json
{
  "trajectory_id": "traj_powernap_moments_filter_2026_04_07",
  "opportunity_id": "powernap_moments_filter_debug",
  "dedupe_key": "powernap:moments_filter:manual_run_debugging",
  "source_window": {
    "start_iso": "2026-04-07T17:36:32Z",
    "end_iso": "2026-04-07T17:56:43Z",
    "connectors": ["screen"]
  },
  "initial_store_state": {
    "active_opportunities": []
  },
  "traces": [
    {
      "trace_id": "trace_powernap_filter_001",
      "history_cutoff_iso": "2026-04-07T17:39:50Z",
      "target_action": "background_prepare",
      "messages": ["full SFT/tool-call transcript for this tick"]
    },
    {
      "trace_id": "trace_powernap_filter_002",
      "history_cutoff_iso": "2026-04-07T17:41:10Z",
      "target_action": "wait_for_more_evidence",
      "messages": ["full SFT/tool-call transcript for this tick"]
    },
    {
      "trace_id": "trace_powernap_filter_003",
      "history_cutoff_iso": "2026-04-07T17:41:47Z",
      "target_action": "surface_now",
      "messages": ["full SFT/tool-call transcript for this tick"]
    },
    {
      "trace_id": "trace_powernap_filter_004",
      "history_cutoff_iso": "2026-04-07T17:44:58Z",
      "target_action": "update_existing",
      "messages": ["full SFT/tool-call transcript for this tick"]
    },
    {
      "trace_id": "trace_powernap_filter_005",
      "history_cutoff_iso": "2026-04-07T17:45:32Z",
      "target_action": "no_action",
      "messages": ["full SFT/tool-call transcript for this tick"]
    }
  ],
  "audit": {
    "future_validation": "Omar first asks command/cwd questions, then hits `Operation not permitted` copying to logs-tada, then asks `any idea why?`.",
    "evidence_before_and_after_t": [
      "logs-indexed/screen/2026-04-07.jsonl:18",
      "logs-indexed/screen/2026-04-07.jsonl:32",
      "logs-indexed/screen/2026-04-07.jsonl:37",
      "logs-indexed/screen/2026-04-07.jsonl:57",
      "logs-indexed/screen/2026-04-07.jsonl:58",
      "logs-indexed/screen/2026-04-07.jsonl:61"
    ],
    "leakage_check": "Each trace only includes logs at or before its own history_cutoff_iso.",
    "final_outcome": "The opportunity evolves from command help into permission debugging."
  }
}
```

Each trace's `messages` field is the visible training transcript. Future validation, evidence after cutoff, and leakage checks stay in `audit` and must not be shown to the model.

The model should learn that recent activity, recent interventions, and active opportunities are already present. Tool calls are for:

- searching older stores
- writing state
- recording surfaced interventions
- writing durable memory

The model should not learn to call retrieval tools for every tick. Most ticks should require no retrieval and often no user-facing message.
