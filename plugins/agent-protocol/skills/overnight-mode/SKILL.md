---
name: overnight-mode
description: The principal's fleet-wide overnight launch directive — put every queued, approved, unblocked unit in flight across all teams while he sleeps, honoring any priority he names, with gates unchanged and a morning report. Invoke when the principal says "overnight mode" (with or without extra priorities).
---

# /overnight-mode — fleet-wide overnight launch [commissioned by a fleet ruling, 2026-07-12] — PROTOCOL v3.2

The principal's word "overnight mode" = the SOP-5 queue-emptying push, **overnight edition, all
teams**. He is going to sleep; the fleet works. This skill is executed by whichever
lead seat receives the word (normally the orchestrator seat).

## Semantics (fixed)

- **Launch**: every unit that is queued + approved + unblocked enters flight tonight —
  team 1 (orch/owner/builder), creator seat, and team 2 via relay (team 2 self-manages).
- **Priorities**: anything the principal names in the same breath ("I want X by morning")
  is a RULING — it jumps the queue and its release entry says so. Voice-to-text
  artifacts interpreted by intent per the standing rule.
- **Gates unchanged**: embargoes, owner bars, Codex/SOP-7 chains, echo-confirm posture,
  and the six irreversible/outward super-classes (first-hand only) all stay exactly
  as they were UNLESS his overnight word explicitly rules otherwise. An advance
  deploy/publish word embedded in the directive is honored only for the exact action
  it names, gated-chain-green first, and is DISCLOSED in the auth-log reading.
- **Principal-gated work**: stages-to-ready (clickables drafted, convergence run,
  runbooks staged) — never executed. Blockers get NAMED, not worked around.

## Steps

1. **Auth-log** — append the DIRECTIVE entry with the principal's verbatim words, the class
   ("SOP-5 pattern, overnight edition, all teams"), any embedded rulings each read out
   explicitly (with disclosed interpretation), and any advance-authorization reading.
   Solo commit (auth-log discipline).
2. **Enumerate lanes** — from memory ⚡ blocks + channel state, list per lane:
   in-flight (leave), queued+approved+unblocked (launch), principal-gated (stage),
   blocked (name blocker).
3. **Release entries** — channel entries to owner / builder / creator with concrete
   unit releases, priority order, and bar/gate expectations; team-2 relay file to the
   legacy inbox with the verbatim word (team 2 self-manages its own queue).
4. **Wake the fleet** — ccd send_message nudges to every peer session (owner, builder,
   creator, team-2 seats); idle peers don't see channel commits without a nudge.
5. **Arm the night watch** — confirm the orch inbound monitor is running; keep the
   orchestrator session responsive to channel traffic overnight (verify verdicts,
   route freezes, unblock peers). Headless ticks stay enabled.
6. **Own lane** — the orchestrator also launches its own queued work (verifies,
   publishes already-approved artifacts, housekeeping) between inbound events.
7. **Morning report** — at the principal's first word (or his wake), deliver: shipped
   overnight / gated-and-staged awaiting his click / blocked+why.
   Anything that needed his device or first-hand action is front of the list.

## Sign-off

Reply to the principal briefly: what just entered flight per lane, what the morning picture
will look like, good night. No questions — he's gone; decisions surface as morning
clickables with SOP-7 convergence.
