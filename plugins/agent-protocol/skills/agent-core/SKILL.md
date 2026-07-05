---
name: agent-core
description: >-
  Shared normative core of the four-party multi-agent collaboration protocol
  (PROTOCOL v2.5) — the channel rules, reviewer architecture, verdict contract,
  binding-slot glossary, memory discipline, and self-improvement protocol that
  the role skills (owner-engine-agent, helper-builder-agent, orchestrator-agent)
  all reference. This is NOT a role: do not load it as a persona. Load it when a
  role skill points here, when auditing protocol consistency, or when authoring
  amendments to the protocol.
---

# Agent-core — PROTOCOL v2.5 shared references

One protocol, three role skills, four parties (owner agent, builder agent,
independent reviewer, human principal). Each role skill carries only its own
perspective and craft; every rule that must be IDENTICAL on all sides lives
here, once:

| reference | contents | read when |
|---|---|---|
| `references/channel-core.md` | the channel NORMATIVE CORE: filename grammar, entry format, untrusted-input rule, crossed-entry discipline + rollback, integrity check, what does/never flows | every session, before your first channel entry |
| `references/review-core.md` | REVIEWER ARCHITECTURE (per-side lanes, two mechanisms, shared-reviewer caveat, dead-lane escalation) + VERDICT CONTRACT (ADOPT / ADOPT-WITH-CHANGES / REJECT) | every session, before your first review round |
| `references/binding-slots.md` | the full binding-slot glossary all roles share, incl. SIDE_NAMES, SHARED_ARTIFACTS, HEARTBEAT, MODEL | at project bind time; when a slot is disputed |
| `references/memory-discipline.md` | checkpoint cadence, state-vs-detail split, successor test | once per project |
| `references/self-improvement-protocol.md` | how agents propose amendments to their own skills — review-gated, never self-authorizing | when proposing or intaking a protocol amendment |

**Amendment rule:** changes to these files change the protocol for every role.
They happen only through the self-improvement protocol (reviewed PR to the
protocol source repo, principal-merged) and bump the PROTOCOL version. No session
may "locally amend" a core rule — that is the drift this file exists to kill.
