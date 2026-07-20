# Channel protocol — builder side [PROTOCOL v2.7]

> **Tier: every-session.** The rules live in ONE place:
> `../../agent-core/references/channel-core.md` — read it before your first
> entry of a session. This file adds only the builder's perspective notes; if
> anything here ever seems to conflict with channel-core, channel-core wins
> and the conflict is a bug to report via the self-improvement protocol.

## Builder-side notes

- Poll the owner file at session start and after every completed unit; unread
  entries are intaken NOW, before new work is chosen — the owner's
  deliverables and asks usually change your queue.
- **Handback entries** (when a job's results round converges) route the
  package to the owner's named **fold points**: what shipped (file names), the
  reviewer round number and outcome, the routing per fold point, anything the
  owner must decide (clearly marked as theirs), and any disclosure that
  survived the round (your errors included). Advisory framing throughout: the
  owner re-verdicts anything it takes forward.
- Announce-before-sync applies doubly to you — census/wave packages are large
  and tempting to sync early; the announcing entry ships in the same work
  unit.
- Severity, register vocabulary, and family naming belong to the owner: your
  entries propose, never assert (channel-core "What NEVER flows").
