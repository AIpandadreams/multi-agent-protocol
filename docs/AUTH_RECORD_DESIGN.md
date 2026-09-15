# AUTH-RECORD design [PROTOCOL v2.5] — rationale + deployment notes

**The normative mechanism lives in the skill tree:**
`plugins/agent-protocol/skills/agent-core/references/proxy-auth-core.md`
(event-sourced schema, relay/replay rules, receiver-side rule, defaults).
This document is the design rationale and the deployment-side requirements;
where anything here could be read to differ, proxy-auth-core wins.
**Principal-locked** either way: no agent-authored PR may alter the design,
the gate rules, or the record mechanics.

## Problem

Locally, authorization is the principal's word in a live session. In the
cloud every wake is a cold successor: the session the principal spoke into is
gone, so authorization must survive as a DURABLE, VERIFIABLE record — without
becoming a laundering vector. With PROXY_AUTH additionally enabled, the
relay's audit trail is the primary safety mechanism.

## Shape of the solution

- Each role keeps `memory/<role>/auth-log.md` in the workspace repo:
  append-only, single-writer (that role's sessions only), event-sourced.
- **Direct authorization** (principal speaks into the acting session): one
  GRANT event per the core schema (`spoken-in: <session id>`), spent by
  `CONSUMED <grant-id>[/D<k>]` events — scope decremented by CONSUMED count;
  the consume is the same pushed reservation as the relayed case. This is
  the only form that exists when PROXY_AUTH is off.
- **Relayed authorization** (PROXY_AUTH on, enumerated classes): the full
  GRANT → RELAY-SENT → RECEIVED → CONSUMED → ACK chain across the
  orchestrator's and receiver's logs, words matching byte-for-byte, per
  proxy-auth-core. Authorization never rides the channel; channel entries at
  most announce grant/relay ids.
- Corrections are new events referencing old ids; nothing is rewritten. Git
  history is the tamper-evidence layer. No personal/confidential data beyond
  the principal's words and the gate description.

## Successor behavior (cloud)

A cold successor acts on a record ONLY if: it is in its own role's log,
unconsumed, unexpired, unrevoked, and the planned action is plainly inside
the words' scope. Anything arguable → decision menu. Successors never
re-derive authorization from channel entries, commit messages, memory prose,
or a peer's log. In-flight relays follow the core's rules: verify the
receiver's log; never resend under a new relay id; consumed = spent forever.

## Audit

- **Reviewer:** every authorization-claiming action is checked against the
  log chain (direct: grant + consumption; relayed: full double-entry chain).
  The passing shape is exactly one: a matching, in-scope,
  provenance-valid grant/relay with exactly one landed CONSUMED chain for
  this action (no CONSUMED = unauthorized; a second CONSUMED for the same
  action = violation). Anything else = REJECT + flag.
- **CI (workspace repos):** append-only check on `auth-log.md` (a push
  editing or deleting existing lines fails) + the stamped
  `tools/validate_auth_log.py` chain check — the exactly-one rule enforced
  mechanically (duplicate CONSUMED ids, relayed CONSUMED without a RECEIVED
  block, RELAY-SENT/direct-CONSUMED counts over the grant's scope) — +
  secret scan + channel append-only + CHANNEL_STATE monotonicity per
  `transports/cloud-git.md`. CI is the mechanical layer; the reviewer's
  semantic audit (words in scope, gate class on the list, provenance) sits
  on top.
- **Orchestrator bookkeeping:** status picture lists grants aging unconsumed
  and relays without ACK.

## Failure modes designed against

| attack/failure | defense |
|---|---|
| paraphrased or summarized authorization | verbatim rule + byte-match double entry |
| forged grant appended to another role's log | AUTH_PROVENANCE binding (per-role identity + path protection + CI author check; single-identity fallback: same-subtree-only commits, source-commit verification in RECEIVED, briefing visibility) |
| two concurrent successors consuming the same relay | consume = pushed reservation; only the CONSUMED that lands on the remote holds it; rejected push = re-verify |
| revocation racing an in-flight consume | ordering rule: REVOKED landing before the CONSUMED push voids the relay; fresh fetch immediately before the consume-push is mandatory |
| replaying a consumed/old grant | forward-only consumption events; unique relay ids; idempotent retries; ABORTED stays spent; expiry; monotonic ids |
| scope creep ("he approved something like this") | plainly-inside test + enumerated gate classes → decision menu |
| wildcard proxy scope | enumerated-list requirement; "everything" is invalid by construction |
| peer/channel laundering | single-writer logs; channel never carries authorization; announcements are untrusted pointers |
| tampering with history | append-only CI + git history + reviewer audit |
| lost context after compaction/cold wake | the log IS the source; memory only points at it |
| relayed enable of PROXY_AUTH itself | binding set only by the principal directly in the orchestrator session; relays void |
