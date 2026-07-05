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

Autonomy is only responsible if an unattended agent cannot (a) lose state or
(b) exceed its authority. The protocol guarantees both:

- **State can't be lost.** Every shipped unit is checkpointed to the ⚡
  working-state block in the workspace repo before it counts. A session that
  dies mid-unit loses at most that unit; the next wake resumes from the
  committed state. (Tested — see [DESIGN.md](DESIGN.md).)
- **Authority can't be exceeded.** Authorization never rides the channel and
  is never implied by a memory note or a peer's say-so. The irreversible/outward
  super-classes (outward-facing/publish actions, email SEND,
  new-money/new-recipient financial actions, destructive operations on another
  party's artifacts, canonical-repo merges, and changes to PROXY_AUTH / gates /
  embargoes / the protocol) are first-hand-only in every configuration. An
  unattended agent that reaches one of those gates *stops and surfaces it*
  rather than proceeding.

### The mechanisms

| mechanism | what it buys you |
|---|---|
| **`/sleep`** | end a session deliberately: checkpoint memory with an exact `## Next Step`, commit + push, hand off. Safe to close the window. |
| **`/wake <role>`** | resume cold in a fresh session: bind, verify integrity, read the ⚡ block, report the resume point — no context pasting, no recap. |
| **Heartbeat ticks** | a scheduled headless run per role that drains the queue between your sittings (fail-closed; see [ADVANCED.md](ADVANCED.md#heartbeats-unattended-operation)). |
| **Orchestrator duties** | standing, scheduled work the orchestrator does unprompted: morning/EOD briefings, queue triage, cost-ledger rollups (bound in DUTIES + TICKS). |
| **Cost governor** | keeps unattended spend inside your bound budget, reporting any preset drop rather than surprising you. |

Because sessions are disposable, autonomy scales the obvious way: run a tick
every hour, every morning, or on demand — the protocol behaves identically
whether a human or a scheduler opened the session.

### The autonomy dial

You choose how much rope, per deployment, by binding:

- **Attended** — you open every session; ticks off. Maximum oversight.
- **Semi-autonomous** — scheduled ticks drain the queue; the orchestrator
  briefs you and parks anything gated. The common setting.
- **Standing duties** — the orchestrator also initiates recurring work
  (reports, sweeps) on its own cadence.

Turning the dial up never widens what an agent may do without you — it only
changes how often it acts on what it already may.

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
   vendor's model, byte-exact fingerprint — exactly like any unit of work.
4. **Adopt.** **You merge it**, and the protocol version bumps. No session
   runs "local amendments" ahead of a merged bump.

### The hard rail

Agents may propose, but **only the principal adopts** — and some things
agents may not propose changes to at all: the authorization/gate rules, the
auth mechanism, embargoes, and the hard-rails section itself. Those are
principal-locked. An agent cannot amend the gates that constrain it, no
matter how good the argument. That single rule is what lets self-improvement
be a feature instead of a risk.

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
