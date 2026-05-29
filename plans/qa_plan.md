# Plan: P_ama as a learned buffer-transition model

## Goal

Train `P_ama` to drive proactive suggestions as a **stateful scorer over a candidate
buffer**. Every tick it ingests the current buffer plus recent activity and rewrites the
buffer: re-scoring every item, inserting newly-noticed leads, and dropping dead ones. The
runtime is then trivial — surface anything whose score crosses a threshold.

We need to **generate training data of the form `(H, old_buffer) → new_buffer`.**

## The model contract: `old buffer → new buffer`

```
INPUT
  H                ← recent activity window (~100 log events)
  buffer (old):
    - "model-registry spec + migration map"      s=0.83
    - "prediction retry cleanup"                 s=0.41
    - "rename the staging branch"                s=0.12

         ┌─────────┐
   H  ─► │  P_ama  │ ─►  buffer (new)
 buffer  └─────────┘
                    - "model-registry spec + migration map"   s=0.91   ↑ evidence kept landing
                    - "prediction retry cleanup"              s=0.55   ↑ slightly firmer
                    - "draft reply to the Elsa thread"        s=0.74   ✦ NEW (just noticed)
                    - (rename branch DROPPED)                          ✗ model evicted it
```

In one forward pass the model:

- **rescores** every existing item (↑ as evidence accrues, ↓ as it fizzles),
- **inserts** newly-noticed leads with an initial score,
- **omits** dead items (soft, model-driven eviction).

Each buffer item carries `{suggestion, s, surfaced, last_surfaced_at}`. The buffer (with
those flags) is the only state carried between ticks.

## Core ideas

### 1. Calibrated score `s ∈ [0,1]`

A privileged pass that sees the full universe of candidate suggestions at once assigns each
a **calibrated percentile**: a suggestion's fresh score = "useful-er than X% of
everything." Calibrated by construction, so a fixed threshold `τ` is meaningful.

### 2. Repeat prevention: the `surfaced` flag + tombstone

There are two distinct "re-appearings," with two different guards:

**(a) The same buffer item re-firing.** Handled by an explicit `surfaced` flag, *not* by
the score. When an item fires it is **kept in the buffer** (a tombstone) with
`surfaced=true`, and the runtime gate refuses to fire any surfaced item — regardless of how
high `s` stays:

```
tick t     X "registry spec"  s=0.91  surfaced=false   → 0.91 ≥ τ → FIRE; set surfaced=true; KEEP X
tick t+1   X "registry spec"  s=0.91  surfaced=TRUE     → gate blocks it (surfaced) → silent
...
tick t+k   (after window T)   X evicted → if H genuinely shows the need again, may re-insert fresh
```

The item **must stay in the buffer**: if it were evicted on firing, the next tick would see
the same `H`, re-propose it as a fresh high-`s` item, and fire again. The tombstone is what
remembers "already shown."

(The trace shows `s` held at 0.91 only to make the point that the **flag**, not the score,
blocks re-firing. In practice, once surfaced the model also drives `s` down — it's been
offered, so its marginal value is now low — and *that* is what lets the floor evict it after
window `T`. The flag is the hard guarantee in the meantime.)

**(b) The model re-inserting the same idea worded differently** (a *new* entry that is
secretly X). This is the learned part: because the tombstone is visible in the input, the
model is trained to recognize "I already offered this" and not add the duplicate (or add it
only at low `s`). This is what "marginal, buffer-aware scoring" buys us.

So: the flag + kept tombstone stop re-firing (deterministic); marginal scoring stops
re-proposal (learned).

### 3. The buffer stratifies into three bands

```
 high s   live candidates  (firing / about to fire)
 mid  s   held leads        (promising but not yet worth interrupting)
 low  s   tombstones        (recently surfaced → suppress repeats → evicted after a window)
```

A lead becoming worth surfacing = an item rising mid→high. A fizzling lead = an item
decaying. Nothing to surface = nothing in the high band.

### 4. Eviction (bounded buffer) — two layers

The model omitting items is not trustworthy alone, so the runtime guarantees the bound:

1. **Soft (model):** dead items are left out of the new buffer.
2. **Hard (runtime safety net):**
   - **Cap `K`** (e.g. 20): keep top-`K` by `s`, evict the rest. Buffer can never exceed `K`.
   - **Floor `ε`:** drop items below `ε`…
   - **…except a tombstone window `T`:** a just-surfaced item is pinned at low `s` for ~`T`
     minutes so it blocks repeats, *then* becomes evictable.

Eviction = cap + floor sweeping the low band once the tombstone window passes.

## Runtime loop (`ticks/`)

```
every ~10s:
  buffer_new = P_ama(H_live, buffer)          # rescore + insert + omit, one pass
  for item in buffer_new:
      if item.s ≥ τ and not item.surfaced:
          surface(item); item.surfaced = True  # show to user
  buffer = evict(buffer_new)                   # cap K · floor ε · tombstone TTL T
```

State between ticks = `buffer`. Knobs = `τ` (fire), `K` (cap), `ε` (floor), `T`
(tombstone window).

## Training data generation

We synthesize `(H, old_buffer) → new_buffer` examples from two sources:

### A. Sampled buffer states (bulk, parallel)

For a candidate-moment, manufacture a plausible `old_buffer` and compute the correct
`new_buffer`:

- Real `H` = the log events at that timestamp.
- `old_buffer` = a randomized mix: the target item (sometimes present, sometimes not) +
  random distractor suggestions at random scores/recencies.
- `new_buffer` = the labeled update, where each item's target score comes from the
  calibration pass:
  - target absent from buffer, ripe → inserted at its calibrated percentile,
  - target present and fresh-surfaced → driven to ~0 (tombstone),
  - evidence-accruing item → score nudged up; fizzling item → nudged down,
  - dead/stale items → omitted.

The key contrastive pair: **same `H`, target ± in buffer → high vs ~0 score.** That single
contrast teaches the marginal / no-repeat behavior. Sampling many buffers (rather than one
trajectory) prevents overfitting to a single path.

### B. A few real forward rollouts (realism)

Walk a timeline tick-by-tick, threading each produced `new_buffer` into the next tick's
input, so a handful of genuine trajectories capture the true dynamics (a lead's rise to
threshold, tombstone decay, eviction).

### Supervision

- The candidate universe supplies the items.
- A **privileged calibration pass over all candidates at once** assigns each its calibrated
  percentile = its fresh-score **ceiling**. This is the labeling oracle.
- The **score trajectory** (an item's ↑/↓ across ticks) is **frontier-judged**: given the
  `H` up to a tick, a frontier model decides *how much of that item's evidence has landed
  so far* and sets `s` accordingly — ramping from a low initial score toward the calibrated
  ceiling as the supporting signals accumulate, and downward when they don't materialize.
  The ceiling caps it; the frontier sets where on the ramp each tick sits.
- A fired item's target keeps it in the buffer with `surfaced=true` (tombstone) so the
  data teaches retention + non-re-firing.
- A frontier model also writes the natural-language suggestion text for inserted items.

## Open decisions

- **Item handle for `old→new` matching:** match by suggestion text (cheapest) vs. a small
  per-item `id` the harness assigns on insert and the model echoes back.
- **Percentile basis:** over *all* candidates (gives a real "this is junk" floor — best for
  a fixed `τ`) vs. the surface-worthy subset only.
- **Score semantics:** is the stored `s` already marginal/novelty-adjusted, or a raw
  calibrated value with novelty applied at scoring time?
- **Eviction authority:** model proposes drops + runtime hard-caps (recommended) vs.
  eviction purely runtime-side.
- **Values for `τ`, `K`, `ε`, `T`.**
