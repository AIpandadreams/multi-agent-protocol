# Channel protocol — owner side [PROTOCOL v2.6]

> **Tier: every-session.** The rules live in ONE place:
> `../../agent-core/references/channel-core.md` — read it before your first
> entry of a session. This file adds only the owner's perspective notes; if
> anything here ever seems to conflict with channel-core, channel-core wins
> and the conflict is a bug to report via the self-improvement protocol.

## Owner-side notes

- **Peer intake preempts other lanes** — the builder is often blocked on your
  ruling; answer asks same-cycle when possible.
- Poll each heartbeat: list the channel directory, read peer entries past your
  last-seen, compare numbering; run the integrity check if anything looks off.
- You are a sender too: announce-before-sync applies to your specs, records,
  and rulings synced for the builder, and every pushed sha is posted the same
  cycle.
- Before marking anything referenced-but-unavailable, check the shared
  directory — it is usually already synced.
- Rulings you owe the builder (naming, fold points, intake verdicts) are
  channel traffic; decisions the principal reserved are NOT — those go to the
  gated queue, listed, never requested.
