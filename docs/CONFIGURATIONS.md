# Configurations — 2-agent, 3-agent, and their combination

The same skills serve every configuration; the difference is only which
profile you stamp and which BINDINGS you fill. Both configurations below
ran (and run) on real work — the notes are from those deployments, not
theory.

## 2-agent: owner + builder (`2agent.local`)

**You talk to the owner directly; the owner doubles as your interface.**

```
you ◄──► OWNER ◄── channel ──► BUILDER
              \                /
               ► REVIEWER ◄───
```

- Best for: a single project where you're comfortable being "in the room"
  — you review the owner's proposals yourself and speak approvals directly
  into either session.
- The owner carries the canonical repo and decision log; the builder takes
  bulk work the owner shouldn't burn context on (read-waves over large
  corpora, censuses, QA passes, advisory drafts).
- Authorization is trivially simple: no relays. Whatever session needs an
  approval asks you in that session. PROXY_AUTH stays off.
- **Live-tested notes** (from a deployment that ran 50+ review rounds this
  way): the division of labor holds up when the *channel discipline* holds
  up — numbered entries, acks, one direction per file. The failure mode to
  watch is the principal becoming the bottleneck relay between the two
  agents; if you notice yourself copy-pasting between sessions, the
  channel bindings are wrong or the agents aren't polling.

## 3-agent: + orchestrator (`3agent.local`)

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
- **Live-tested notes**: the orchestrator is *purely additive* — nothing
  in the owner/builder contract changes when it appears. That is what
  makes the upgrade path (below) safe. The discipline that matters most
  here is the dispatch log: every dispatch gets a row, every row gets an
  outcome, and the briefing quotes them — otherwise the principal loses
  the thread of what was done in their name.

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

- **2-agent → 3-agent**: stamp nothing new. Add the orchestrator's binding
  rows to BINDINGS.md (the slot list is in `binding-slots.md`), create
  `memory/orchestrator/` + TASKQUEUE.md (copy the shapes from a fresh
  `3agent.local` stamp), and `/wake orchestrator`. Workers notice nothing.
- **3-agent → 2-agent** (downgrade): just stop waking the orchestrator.
  Its queue parks; the owner resumes interface duty.

## Choosing, concretely

| signal | choose |
|---|---|
| one project, you enjoy reviewing the work directly | 2-agent |
| you keep forgetting what the agents are doing between sessions | 3-agent (briefings + queue are the fix) |
| several concurrent projects, one brain to rule them | 3-agent global flavor |
| you want approvals relayed while you're away from the worker sessions | 3-agent + PROXY_AUTH (advanced — read [ADVANCED.md](ADVANCED.md) first) |

## What stays constant in every configuration

- The reviewer gates every round. It is the fourth party, not an option.
- The principal's gates are first-hand-only for the irreversible/outward
  super-classes (outward-facing/publish actions, email SEND,
  new-money/new-recipient financial actions, destructive operations on another
  party's artifacts, canonical-repo merges, and changes to PROXY_AUTH / gates /
  embargoes / the protocol) in every configuration, PROXY_AUTH or not.
- Workspace anatomy is identical — a 2-agent workspace is a 3-agent
  workspace with three binding rows and one memory directory fewer.
