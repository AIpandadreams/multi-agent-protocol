# Configurations — 3-agent, 2-agent, and their combination

The same skills serve every configuration; the difference is only which
profile you stamp and which BINDINGS you fill. Both configurations below
ran (and run) on real work — the notes are from those deployments, not
theory.

## 3-agent: orchestrator + owner + builder (`3agent.local`) — the default shape

**You talk ONLY to the orchestrator; workers exist on demand.**

```
you ◄──► ORCHESTRATOR ── dispatch ──► OWNER ◄── channel ──► BUILDER
                 │                        \                /
                 └── briefs, decisions,    ► REVIEWER ◄───
                     approvals to relay
```

- Best for: the personal-assistant experience — one point of contact,
  morning/evening briefings, a task queue you feed in plain language, and
  approvals brought to you as a decision menu.
- The orchestrator adds four binding families: FLAVOR, TASKQUEUE +
  DUTIES + TICKS (what it does unprompted), ESCALATION (when it interrupts
  you), and PROXY_AUTH (how your approvals reach workers — see below).
- **Live-tested notes**: the orchestrator duties are *separable* — nothing
  in the owner/builder contract changes whether they run as their own
  session (this default) or inside the owner (dual-role, below). That
  separability is what makes the two upgrade paths safe in both directions.
  The discipline that matters most here is the dispatch log: every dispatch
  gets a row, every row gets an outcome, and the briefing quotes them —
  otherwise the principal loses the thread of what was done in their name.

## 2-agent: dual-role owner (`2agent.local`)

**You talk to the owner directly; the owner runs dual-role, absorbing the
orchestrator's interface duty.**

```
you ◄──► OWNER ◄── channel ──► BUILDER
              \                /
               ► REVIEWER ◄───
```

- Best for: a single project where you're comfortable being "in the room"
  — you review the owner's proposals yourself and speak approvals directly
  into either session.
- The **dual-role owner** absorbs what the orchestrator does in the default
  shape: plain-speech intake, the visible queue of gated items, and the
  dispatch bookkeeping. The trade-off is direct: the owner spends some of
  its context budget on interface duty instead of pure decision work — fine
  on one focused project, the reason to split the role out once several are
  in flight.
- The owner carries the canonical repo and decision log; the builder takes
  bulk work the owner shouldn't burn context on (read-waves over large
  corpora, censuses, QA passes, advisory drafts).
- Authorization is trivially simple: no relays. Whatever session needs an
  approval asks you in that session. PROXY_AUTH stays off by construction —
  no relay lane exists without an orchestrator.
- **Live-tested notes** (from a deployment that ran 50+ review rounds this
  way): the division of labor holds up when the *channel discipline* holds
  up — numbered entries, acks, one direction per file. The failure mode to
  watch is the principal becoming the bottleneck relay between the two
  agents; if you notice yourself copy-pasting between sessions, the
  channel bindings are wrong or the agents aren't polling.

## Combining them: one orchestrator over many pairs

The orchestrator's `FLAVOR` binding has two values:

- `project:<name>` — dedicated to one workspace (the plain 3-agent above).
- `global-pa` — a **global personal assistant**: one orchestrator fronting
  multiple projects' worker pairs (and non-project duties of its own).

In global flavor, the orchestrator keeps a session registry of every
worker pair it manages, routes tasks to the right project workspace, and
aggregates briefings across all of them. Each project workspace remains
fully self-contained (own channel, own memories, own reviewer rounds) —
the orchestrator is a client of each, never a back-channel between them.
Nothing moves between projects except through the orchestrator with the
principal's knowledge.

This is the "combination" mode: a 2-agent project deployment and a
3-agent PA deployment running simultaneously, sharing nothing but the
protocol — and the principal chooses per project whether to route it
through the PA or talk to its owner directly. Both can be true at once
for different projects.

## Upgrade paths

- **Collapsing to a dual-role owner (3→2)**: stop waking the orchestrator.
  Its queue parks; the owner absorbs interface duty. Stamp nothing new —
  the owner/builder contract is unchanged.
- **Splitting the dual role back out (2→3)**: stamp nothing new. Add the
  orchestrator's binding rows to BINDINGS.md (the slot list is in
  `binding-slots.md`), create `memory/orchestrator/` + TASKQUEUE.md (copy
  the shapes from a fresh `3agent.local` stamp), and `/wake orchestrator`.
  Workers notice nothing. `tools/scale_workspace.py --workspace <ws>` does the
  file half for you — it materializes the orchestrator scaffold from the same
  templates a fresh stamp uses and prints the exact BINDINGS rows to add by
  hand (it never edits the principal-owned BINDINGS.md itself).

## Choosing, concretely

| signal | choose |
|---|---|
| you keep forgetting what the agents are doing between sessions | 3-agent (the default — briefings + queue are the fix) |
| several concurrent projects, one brain to rule them | 3-agent global flavor |
| one project, you enjoy reviewing the work directly and prefer talking to the owner | 2-agent (dual-role owner) |
| you want approvals relayed while you're away from the worker sessions | 3-agent + PROXY_AUTH (advanced — read [ADVANCED.md](ADVANCED.md) first) |
| several **fully separate** teams under one principal (not one brain over many pairs) | [FEDERATION.md](FEDERATION.md) — teams share only the protocol and you; authorization never crosses a team boundary |

## What stays constant in every configuration

- The reviewer gates every round. It is the fourth party, not an option.
- The principal's gates are first-hand-only for the irreversible/outward
  super-classes (outward-facing/publish actions, email SEND,
  new-money/new-recipient financial actions, destructive operations on another
  party's artifacts, canonical-repo merges, and changes to PROXY_AUTH / gates /
  embargoes / the protocol) in every configuration, PROXY_AUTH or not.
- Workspace anatomy is identical — a 2-agent workspace is a 3-agent
  workspace with three binding rows and one memory directory fewer.
