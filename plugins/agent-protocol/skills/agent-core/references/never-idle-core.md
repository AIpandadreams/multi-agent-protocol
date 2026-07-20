# Never-idle autonomy [PROTOCOL v2.7] — the fourth dial level

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

A monitor is not durable: session interrupts and context compaction can kill
it silently, and an unarmed watcher is indistinguishable from a quiet lane.
Arm-and-verify at every wake and resume (start contracts, machinery step) —
and treat "no events for suspiciously long" as a prompt to re-verify the
monitor is still armed, not as evidence the lane is quiet.

The inverse failure also occurs: a monitor can SURVIVE an interrupt the seat
assumed killed it, so a blind re-arm leaves TWO monitors firing on the same
lane (duplicate intake events, double-processing risk). **Re-arm is
stop-then-arm:** before arming, enumerate your live monitors and stop any
prior monitor on the same lane by its id — never arm on the assumption the
predecessor is dead.

**The monitor-less seat.** A seat operating WITHOUT a persistent monitor (an
interactive or direct session working a lane by hand) owes a **manual poll**
of every owed lane immediately after any reply-requesting post, and at every
wake and checkpoint. Posting a question does not page you; the reply lands
silently, and waiting for a monitor you never armed is the deaf-seat failure
without a monitor to blame. One immediate poll is not enough on its own — it
normally lands before the peer can answer. **While a reply is owed**, poll at
a bound cadence, and always before switching work or ending a turn, until the
reply arrives or the ask is explicitly parked.

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

## The three-state ledger

Watcher-driven intake makes a worker prompt about work that ARRIVES. It says
nothing about work that already exists and is going nowhere — the queued unit
nobody started, the finished unit waiting on a gate no one presented, the item
stalled on a peer's seam. A seat can be perfectly responsive on every lane it
watches and still sit on a pile of stalled deliverables. That pile is the real
idleness, and watching does not touch it.

So the top of the dial carries a second duty, owed at every checkpoint and
before any report of having nothing to do. **Every OPEN deliverable in the
seat's lane is in exactly one of three states** (a delivered-and-banked unit
has left the ledger; it is none of these):

1. **IN FLIGHT** — being worked now, inside existing authority.
2. **SURFACED** — ready but not the seat's to decide: presented to the
   principal as a decision, or handed to the peer whose seam it needs.
   Surfacing is how gated work MOVES; a surfaced item is progress, not a stall.
   A **gated** item's surfacing target is the **principal**: handing it to a
   peer does not discharge a gate, and a peer's ack is never authorization —
   *authorization never rides the channel*. Peer hand-off is for an item
   blocked on a peer's SEAM, never on a GATE.
3. **BLOCKED, BLOCKER NAMED** — named concretely: what blocks it, who or what
   clears it, and what it unblocks when cleared.

**"Idle" is not a fourth state.** A seat with nothing in flight is not thereby
idle-and-excused; it still owes the ledger — the surfaced items and the
blocked ones, each blocker named. Most seats that report themselves idle are
not idle at all: they are BLOCKED and have never named the blocker, which is
precisely the information the principal needed in order to unblock them. The
ledger converts silent waiting into a decision someone can act on.

### The clamp: triage, never invention

This duty is TRIAGE over work that already exists — the queue, the channel,
the standing duties. It is **not** a licence to manufacture scope, and it does
not widen the MAY-list by one line. "Utilize the time" and "put everything
possible in flight" are instructions about work that EXISTS and is stalled;
read as permission to invent work so the ledger looks busy, they produce
exactly the defect `Starvation honesty` names below. The MUST-NOT list is
unchanged: *idle time is still not a work source*.

An honest ledger with **nothing in flight** — N surfaced, M blocked, each
blocker named, no invented scope — is a COMPLETE and CORRECT report. A seat
that fabricates a unit rather than file that report has not shown diligence;
it has buried the one signal the principal needed.

Invention has a near neighbor that is easier to miss, because it wears a real
queue item's name: **a queued unit that has not received its go is BLOCKED
(blocker: the go) — never IN FLIGHT.** A seat reaching for a non-empty ledger
will reach for that unit first. The ledger never converts a pending
authorization into work in progress; doing so is the same defect as invention,
and it launders a gate into a status line. Drafting that unit's **spec** under
the MAY-list (*draft the next queued unit's spec*) is permitted pre-go
preparation and does not promote the unit: the **spec draft** may carry its own
IN FLIGHT line; the **unit** stays BLOCKED (blocker: the go). Permitted
preparation is never evidence of authorization.

## THE INVARIANT: cadence, not authority

Never-idle changes how OFTEN a worker acts on what it already may do — it never
widens WHAT it may do without the principal. Turning the dial to never-idle
adds zero authority: the same gates, the same review rounds, the same
first-hand-only super-classes. This is the whole safety story of the level — if
a proposed never-idle behavior would let a worker do something it could not do
at semi-autonomous, the behavior is wrong, not the invariant.

The ledger obeys the invariant exactly. **Surfacing a gated item is not
clearing its gate**: the item moves from the seat's silence to the principal's
desk, and there it stops until the principal's own word. A seat that reads
"no idle time" as authority to push a gated deliverable through in order to
empty its ledger has inverted the level — the ledger exists to make gates
VISIBLE, never to route around them.

## Starvation honesty

When the MAY-list is empty — nothing to intake, nothing queued to draft, checks
all green — the honest state is **delta-only status, the three-state ledger,
and wait**. A worker that manufactures busywork to look productive has
introduced a defect, not shown diligence: invented scope, redundant re-checks,
and churn all cost tokens and bury real signal. "Nothing in flight; here is
what is surfaced and what is blocked, by name" is a correct and reportable
state — and it is a strictly more useful one than silence, because every named
blocker is a thing the principal can now clear.
