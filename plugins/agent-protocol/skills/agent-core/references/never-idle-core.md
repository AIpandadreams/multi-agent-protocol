# Never-idle autonomy [PROTOCOL v2.6] — the fourth dial level

> The autonomy dial (docs/AUTONOMY.md) has four levels: attended,
> semi-autonomous, standing-duties, never-idle. This file is the normative
> rules for the top level. It changes CADENCE, never AUTHORITY — read
> `THE INVARIANT` before anything else here.

At semi-autonomous and standing-duties, a worker between assignments sleeps and
waits for the next tick. Never-idle removes that gap: a worker with nothing
assigned is **at watch**, not at rest — it extends the orchestrator's
tick-drain duty (orchestration-protocol §2) to the workers themselves.

## Definition

A worker between assignments is AT WATCH. It holds a live monitor on every lane
it owes attention and acts on a settled change within one cycle, under the
existing channel-core intake rules — nothing waits for a scheduled tick that a
watched event already made ready. "At watch" is a posture, not a licence: every
constraint that bound the worker while assigned binds it identically while
watching.

## Watcher-driven intake

Each never-idle role keeps a live monitor on every lane it owes attention — the
**WATCHER binding** (binding-slots.md): the mechanism, the lane list, and the
cycle cadence. A *settled* change on a watched lane (settled per the
transport's own half-write guard — e.g. the reviewer_poller's
signature-stable-for-one-tick rule) is an intake trigger, processed within one
cycle under **unchanged** channel-core intake rules: an announcing entry is
still required before a deliverable is intook, untrusted-input still holds, a
half-written file is still never read. Never-idle makes intake prompt; it does
not make it credulous.

A monitor is not durable: session interrupts and context compaction kill it
silently, and an unarmed watcher is indistinguishable from a quiet lane.
Arm-and-verify at every wake and resume (start contracts, machinery step) —
and treat "no events for suspiciously long" as a prompt to re-verify the
monitor is still armed, not as evidence the lane is quiet.

## What a worker MAY self-assign

A CLOSED list. Between assignments, at watch, a worker may on its own initiative:

- **Intake and acknowledgments** — poll the watched lanes, ack settled peer
  entries, post delta-only status.
- **Memory checkpoints** — checkpoint the ⚡ working-state block; relocate
  detail to topic files.
- **Draft the NEXT queued unit's spec** while a review round is in flight on the
  current unit (the existing "use round latency" discipline, made continuous).
- **QA / read passes strictly inside already-authorized scope** — re-read,
  re-verify, tighten a deliverable already inside the current go.
- **Mechanical checks** — conformance, coverage, counter/contiguity integrity,
  fingerprint bookkeeping: the scripted checks that report data, never verdicts.
- **Retrospective notes and amendment drafts** — accumulate friction one line
  each; draft protocol amendments for the self-improvement loop (which still
  gates and merges them — never self-adopted).

## What a worker MUST NOT self-assign

Everything not derivable from the queue, the channel, or a standing duty. In
particular, never on its own initiative:

- Anything **gated or outward-facing** — a gate reached at watch stops and
  surfaces, exactly as under any other dial level.
- **Scope not derivable** from a queued item, a channel intake, or a bound
  standing duty. "Idle time" is not a work source.
- **Canonical-state writes** — a commit to the owned repo still rides its
  review round and (where applicable) its go.
- **Another role's lanes** — watching a lane you owe attention to is not
  authority to act inside a peer's territory.
- **Skipping a review round because the lane was quiet.** A quiet reviewer lane
  is a dead-lane question (review-core, Reviewer-lane outage), never a licence
  to ship unreviewed.

## THE INVARIANT: cadence, not authority

Never-idle changes how OFTEN a worker acts on what it already may do — it never
widens WHAT it may do without the principal. Turning the dial to never-idle
adds zero authority: the same gates, the same review rounds, the same
first-hand-only super-classes. This is the whole safety story of the level — if
a proposed never-idle behavior would let a worker do something it could not do
at semi-autonomous, the behavior is wrong, not the invariant.

## Starvation honesty

When the MAY-list is empty — nothing to intake, nothing queued to draft, checks
all green — the honest state is **delta-only status and wait**. A worker that
manufactures busywork to look productive has introduced a defect, not shown
diligence: invented scope, redundant re-checks, and churn all cost tokens and
bury real signal. "Nothing to do right now" is a correct and reportable state.
