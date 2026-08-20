# Autonomy & self-improvement

Two capabilities are core to this protocol, not add-ons: the team **operates
autonomously** between your touchpoints, and the protocol **improves itself**
under its own review discipline. Both fall out of the same foundation —
everything persistent lives in git, and nothing an agent does escapes a gate
or a review — so they are safe by construction, not by hope.

## Autonomy

The design goal is a team you *direct*, not one you *babysit*. You set
direction and hold the gates; the agents carry the work forward on their own
in between.

### What makes it safe

Autonomy is only responsible if an unattended agent cannot (a) lose state,
(b) exceed its authority, or (c) hide a failure behind a mechanism that still
looks healthy. The protocol guarantees all three:

- **State can't be lost.** Every shipped unit is checkpointed to the ⚡
  working-state block in the workspace repo before it counts. A session that
  dies mid-unit loses at most that unit; the next wake resumes from the
  committed state. (Tested — see [DESIGN.md](DESIGN.md).) Session death is
  not the only loss channel: **context compaction** silently summarizes a
  live session, and a summary is lossy — the plan ledger
  ([PLAN-LEDGER.md](PLAN-LEDGER.md)) is the shipped failsafe for exactly
  that channel, re-injecting every open typed obligation into the fresh
  context.
- **Authority can't be exceeded.** Authorization never rides the channel and
  is never implied by a memory note or a peer's say-so. The irreversible/outward
  super-classes (outward-facing/publish actions, email SEND,
  new-money/new-recipient financial actions, destructive operations on another
  party's artifacts, canonical-repo merges, and changes to PROXY_AUTH / gates /
  embargoes / the protocol) are first-hand-only in every configuration. An
  unattended agent that reaches one of those gates *stops and surfaces it*
  rather than proceeding.
- **Concealment can't be silent.** Every mechanism that makes the work easier
  to run — a monitor, a summary, a heartbeat, a gate — also makes *some*
  failure harder to see: a monitor watching too narrow a pattern goes deaf
  while looking healthy, a summary drops the detail a later check needed, a
  gate passing on a stale fingerprint hides the mismatch. So a mechanism is
  responsible only if it **declares what it makes harder to observe and ships
  the compensating probe** that restores that visibility — a named blind spot
  with a probe is safe; a silent one is where failures live. This is a
  disclosure the mechanism owes, not a new gate on top of the two above; the
  rule a proposal states it under is in
  [self-improvement-protocol.md](../plugins/agent-protocol/skills/agent-core/references/self-improvement-protocol.md).

### The mechanisms

| mechanism | what it buys you |
|---|---|
| **`/sleep`** | end a session deliberately: checkpoint memory with an exact `## Next Step`, commit + push, hand off. Safe to close the window. |
| **`/wake <role>`** | resume cold in a fresh session: bind, verify integrity, read the ⚡ block, report the resume point — no context pasting, no recap. |
| **Heartbeat ticks** | a scheduled headless run per role that drains the queue between your sittings (fail-closed; see [ADVANCED.md](ADVANCED.md#heartbeats-unattended-operation)). |
| **Orchestrator duties** | standing, scheduled work the orchestrator does unprompted: morning/EOD briefings, queue triage, cost-ledger rollups (bound in DUTIES + TICKS). |
| **Cost governor** | keeps unattended spend inside your bound budget, reporting any preset drop rather than surprising you. |
| **Compaction hook** (plan ledger) | `tools/compaction_inject.py` re-injects every open typed obligation into the post-compaction context, so a compacted session is still handed its commitments — wiring in [ADVANCED.md](ADVANCED.md#the-plan-ledger-compaction-hook); spec in [PLAN-LEDGER.md](PLAN-LEDGER.md). |

Because sessions are disposable, autonomy scales the obvious way: run a tick
every hour, every morning, or on demand — the protocol behaves identically
whether a human or a scheduler opened the session.

### The autonomy dial

You choose how much rope, per deployment, by binding:

- **Attended** — you open every session; ticks off. Maximum oversight of what
  can put work in front of a seat.
- **Semi-autonomous** — scheduled ticks drain the queue; the orchestrator
  briefs you and parks anything gated. The common setting.
- **Standing duties** — the orchestrator also initiates recurring work
  (reports, sweeps) on its own cadence.
- **Never-idle** — a worker between assignments holds at intake-watch rather
  than sleeping to the next tick: it responds to a settled event on a lane it
  owns within one cycle, so nothing actionable waits for a scheduler. It may
  self-assign only from a closed list (intake, memory checkpoints, drafting the
  next queued unit's spec, in-scope QA, mechanical checks, retrospective notes)
  and stops-and-surfaces at any gate exactly as at every other level. It also
  owes a **three-state ledger**: every deliverable in its lane is *in flight*,
  *surfaced* (to you, or to the peer whose seam it needs), or *blocked with the
  blocker named* — "idle" is not a fourth state, and a seat that reports itself
  idle is usually a seat that never named its blocker. Requires a WATCHER
  binding.

At never-idle the team never sits idle waiting for a clock, yet the top of the
dial adds no authority: a watching worker is bound by the same gates and the
same review rounds as an assigned one. The full rules — the at-watch posture,
watcher-driven intake, and the closed MAY / MUST-NOT self-assign lists — are in
[never-idle-core.md](../plugins/agent-protocol/skills/agent-core/references/never-idle-core.md).

Turning the dial up never widens what an agent may do without you — it only
changes how often it acts on what it already may.

### Full speed: the standing go-ahead

Every position on the dial answers the same routing question — *without a fresh
word from you, what can put work in front of this seat?* At attended, nothing:
you open every session.

Three of the positions above touch a second question, and none of them settles
it. Never-idle says a worker may take up the items on that closed list *on its
own initiative*, and standing-duties has the orchestrator run its bound duties
unprompted — each an answer, but only for a class of work named in advance. A
scheduled tick drains the queue with nobody present to ask, which answers it for
whatever you queued, as a consequence of the tick being headless rather than as
a rule anyone stated. None of them states a rule for work in general: **once a
seat has work in front of it that it is already authorized to do, is having it
enough to proceed — or must it stop and ask?**

That is a separate question, and it has its own failure mode. An *arc* is the
connected run of steps carrying a single approved piece of work from its start
to its end; it may span more than one *unit*, a unit being one deliverable whose
start is governed by its own go. A seat that comes back for a fresh go-ahead at
every step of such an arc makes you the bottleneck on your own decision, and
spends a round-trip per step re-asking a question you have answered.

**Full speed** is a standing pre-authorization to *proceed without re-asking*.
It is not a pre-authorization of any particular work: it never supplies a unit's
authority; it only removes the pre-start ask standing in front of authority the
seat already has.

What you give up is the pre-start ask — the one the seat would otherwise make
before each step, and again before each unit it picks up. When the seat says
what it is about to do and under what authority, that ask may expose a mistaken
idea of scope before the work begins; a bare "proceed?" answered "yes" exposes
nothing. Inside the scope in force the ask is absent, so a misunderstanding may
survive until a review round or a gate exposes it. That is why the scope below
is yours to state, and why being unsure resolves to stopping *and surfacing* — a
stop you never hear about is the reporting defect named below, not caution.
Where this section says *the scope in force* it means the scope you stated — or,
when you stated none, whatever the scope rule below supplies by default: at most
a single unit, and in two of its three cases nothing at all. The mode rests on
four clauses:

- **Completion is the go-signal.** Finishing a step is itself the signal to
  begin the next step of the same arc — *provided that next step is inside both
  the arc's existing authority and the scope in force*. Completion moves neither
  boundary: a next step that would cross a gate is not made in-authority by the
  step before it completing, and one that falls outside that scope is worked the
  ordinary way, after asking.
- **Having an authorized in-scope unit is enough to begin.** A unit that already
  has its own go *and* lies inside the scope in force goes in flight once it is
  in front of the seat, rather than being held until you are next asked. What
  can put that unit in front of the seat at all remains the dial's question;
  this clause governs only what happens once it is there.
- **It is open-ended within its scope.** Within the session you granted it in,
  the pre-authorization stands until you revoke it first-hand: it does not lapse
  on a date, and inside the scope in force it is not re-granted unit by unit.
  That it does not reach a session you never said it in is the ordinary
  authorization rule, not a lapse. An unscoped grant is the narrow case — the
  default below is all it gets, and in two of its three branches that default is
  nothing at all, so whatever it does not cover needs your word; state a scope
  if you want the grant to reach further than that default reaches — and no
  scope, however wide, carries it into a session you did not speak it in.
- **Blocked is not idle.** Work genuinely parked on a gate is *surfaced to you
  with its blocker named* — a pair of duties, not one imported state:
  never-idle's ledger keeps surfacing and blocking separate, and what is
  borrowed here rather than invented is its discipline for naming a blocker.
  Both are owed, because together they are what makes the rest of the clause
  safe: the seat moves on to the next unit in front of it that meets the second
  clause's two conditions, instead of waiting on the gate. Parking is not a
  substitute for surfacing.

**Full speed is not a binding slot**, and the distinction matters for how a seat
establishes it. There is no `FULL_SPEED` entry in
[binding-slots.md](../plugins/agent-protocol/skills/agent-core/references/binding-slots.md),
so there is no bound value a seat can point at — and the **Authority can't be
exceeded** rule above puts the mode where every authorization sits: it does not
ride the channel and is not implied by a memory note or a peer's say-so. A
session runs at full speed on your own word, spoken into the session that acts
on it. That is how every approval arrives with `PROXY_AUTH` off, the default and
the shipped state; turning it on adds a relayed form without changing what an
approval is. Both forms are the same record: an approval of a gated action,
naming the class of gate cleared, against a scope its spends count down, and
consumed by events that name what was done. Full speed is not an action and
stands in front of no gate, so neither form gives it a gate class to record, an
effect for a consumption to name, or anything for a scope to count down. That is
a fact about the record's shape, which `PROXY_AUTH` off does not remove, rather
than a guess about a binding this page cannot see. A record you wrote earlier
does not establish the mode in a session you did not say it in — however
first-hand that record was when you wrote it, it reaches the seat as a note, and
the rule above already says a note is not an authorization. A seat that cannot
point to your word in its own session is not at full speed and should say so
rather than assume. Whether the mode ought to become a bound slot, with the
version-stamp and conformance discipline that implies, is an open protocol-class
question this page does not settle.

A standing pre-authorization also has a **scope**, and the scope is yours to
state rather than the seat's to infer: which lanes, which repositories, which
classes of unit. Granted without a stated scope it covers at most one unit, and
only when exactly one was in front of the seat when you gave it: that unit and
nothing else — not others queued beside it, not the next to arrive, and not a
longer arc unless your grant says so — so the fourth clause's move to a next
unit is inert until you state a scope. If none was in front, or more than one
and your grant does not say which, there is no default scope at all: nothing is
in scope, the seat asks rather than picks, and it does not later attach your
grant to whatever arrives next. A seat that finds itself reasoning about whether
your grant *probably* reaches some new lane — or the next unit of the same work
— has already left the scope, and the reasoning is the evidence.

**The invariant: tempo, not boundary.** Full speed changes how often you must
speak, never what a seat may do. It creates no authority — the gates, the review
rounds, and the first-hand-only super-classes bind identically at full speed and
at a dead stop. It is never-idle's *cadence, not authority* invariant carried to
a second lever. If a proposed full-speed behavior would change the substantive
work a seat may do, or where a gate falls, rather than only how often you must
be asked, the behavior is wrong, not the invariant. One duty does travel with
the mode, disclosed here rather than folded in: the fourth clause pairs
never-idle's discipline for naming a blocker with surfacing the parked unit, so
a seat at full speed surfaces work it parks at a gate and names its blocker, at
any dial position. The rest of that ledger does not travel: not its accounting
of every open deliverable into exactly one of three states, not the cadence owed
at every checkpoint and before each report of having nothing to do, and not its
rule for handing an item blocked on a peer's seam to that peer. It is an
addition on the duty side, which is why it is stated rather than left to the
invariant, whose subject is permissions.

Full speed formalizes prior practice as a separate setting. The SOP catalog in
[CREATOR-SEAT-BOOTSTRAP.md](CREATOR-SEAT-BOOTSTRAP.md) (Part 5, the *No-idle /
continuous forward progress* row) already carries continuous progress and the
never-idle level together, and states the same limit in one line — acting within
existing authority without waiting to be prompted grants none of it. That row
records the practice; this section names full speed as the setting that waives
the pre-start ask, and gives its provenance, scope, operation, and revocation
independently of the dial.

A unit faces two conditions, and they gate different things. **Does the unit
have its own go?** It does not while a gate its start would cross stands
uncleared — full speed supplies no go a gate reserves for you — and a unit still
waiting on its authorization is **blocked on that go**, not merely un-started.
Without this one the unit does not begin at all, and starting it anyway converts
a pending authorization into work in progress, which
[never-idle-core.md](../plugins/agent-protocol/skills/agent-core/references/never-idle-core.md)
describes as an easier-to-miss neighbor of invented work, because it wears a
real queue item's name and launders a gate into a status line. Ungated in
general is not the same as authorized in particular.

**Does your full-speed grant reach it?** It does not if the unit falls outside
the scope in force, gate or no gate. Without this one the unit may still be done
— but only after asking: full speed removes the pre-start ask inside that scope
and nowhere else, so a perfectly authorized unit outside it is worked the
ordinary way, not refused. Outside the waiver is not the same as forbidden, and
being unsure either way is itself the answer — the seat stops and surfaces
rather than beginning.

Both of the combinations that sound odd are coherent — a never-idle seat that
must still be asked before each step, and an attended one that, once you hand it
an arc, carries it forward without being re-asked at each step. Pairing the top
of the dial with full speed is what produces a team that both picks work up on
its own and carries it to a gate without prompting — within the scope in force,
and asking as usual outside it.

**Speed does not relax verification.** Every discipline that exists because
unverified speed produces falsehoods binds unchanged at tempo — a fingerprint
re-checked against the bytes actually shipping, a claim carried from an earlier
session re-verified against the tree, a status measured before it is reported.
Full speed makes *more* of those checks happen per hour; it does not make fewer
happen per unit. A mode that bought throughput by skipping them would not be
faster, only wrong further from the cause.

Nor does it license invented work: never-idle's starvation rule holds exactly as
written, and an empty MAY-list is answered with the report that rule prescribes,
and then with waiting, rather than with a manufactured unit. An idle seat is a
*routing* defect when work it is already authorized to do exists and nothing has
put it in front of the seat — fixed by dispatching that work rather than by
finding something to look busy with. It is a *reporting* defect when the seat's
real state is blocked with the blocker unnamed — which, for work parked at a
gate, the duty above already forbids.

Revocation is yours, first-hand, and takes effect on any step not already begun.
A seat brings its current step to a safe checkpoint rather than stopping
mid-write, then goes back to asking between steps; it does not run its remaining
in-flight units to completion first.

## Self-improvement

The system that runs the work also **evolves the rules of the work** — under
the same discipline it applies to everything else. This is what makes it a
living protocol rather than a frozen ruleset.

### The loop

1. **Observe.** A session hits a rough edge — a rule that misfired, a gap, a
   recurring friction — and records it (retrospective note, or a
   `docs/` amendment draft).
2. **Propose.** The improvement becomes a PR to the protocol source, with an
   amendment header stating the problem, blast radius, and version impact
   (see [CONTRIBUTING.md](../CONTRIBUTING.md)).
3. **Review.** It goes through an independent review round — a different
   vendor's model, byte-exact fingerprint, extraction-bound evidence —
   exactly like any unit of work.
4. **Adopt.** **You merge it**, and the protocol version bumps. No session
   runs "local amendments" ahead of a merged bump.

### The hard rail

Agents may propose, but **only the principal adopts** — and some things
agents may not propose changes to at all: the authorization/gate rules, the
auth mechanism, embargoes, and the hard-rails section itself. Those are
principal-locked. An agent cannot amend the gates that constrain it, no
matter how good the argument. That single rule is what lets self-improvement
be a feature instead of a risk.

*When an automated drafter's own change would touch one of these locked subjects,
the draft-time tripwire (self-improvement-protocol.md, Hard rails) downgrades it to
a notice-only memo — surfacing that a change is wanted without proposing one; the
principal still authors any locked change independently.*

### Keeping the protocol coherent as it grows

Self-improvement adds rules over time; two guards keep the set from drifting
into contradiction:

- **`tools/mirror_check.py`** (CI) — the role skills are thin deltas over the
  shared `agent-core`. The checker fails the build on the structural
  drift that produced the protocol's original defects: a role file
  duplicating a normative core block (the dedup guard), banned legacy
  vocabulary, missing cross-references between a role file and the core it
  refines, or a missing `[PROTOCOL vX.Y]` version stamp. It is a structural
  guard, not a semantic prover — deeper contradiction-checking is on the
  roadmap — but every amendment must pass it.
- **Version stamps** — every protocol file carries `[PROTOCOL vX.Y]`; a
  session that finds a skill/workspace version mismatch parks
  protocol-sensitive actions until the human resolves the pin.

### Provenance

This protocol is itself the output of the loop it prescribes: it began as a
two-agent pair's working agreement, went through repeated independent review
rounds, and continues to evolve by amendment. [DESIGN.md](DESIGN.md) has the
evidence trail.

## Together

Autonomy without self-improvement is a team that runs but never gets better.
Self-improvement without autonomy is a protocol that improves but still needs
you in the room. Combined — and gated the way this protocol gates everything
— you get a team that carries work forward on its own *and* sharpens its own
operating rules over time, while every irreversible decision and every rule
change still terminates at your word.
