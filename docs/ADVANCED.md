# Advanced topics

None of this is needed for a first deployment. Read when the relevant
binding stops saying "off" or "default".

## PROXY_AUTH — the auth-log lane

**What it solves.** In a 3-agent deployment you talk only to the
orchestrator — but workers still need your approvals. Without proxy auth,
you'd have to open each worker session to grant things (fine, and the
default). With it, your words travel as *auditable data*:

1. **GRANT** — your verbatim words, recorded in the orchestrator's
   `memory/orchestrator/auth-log.md` with a grant id and an explicit scope
   (`single` or `batch-N`).
2. **RELAY-SENT** — the orchestrator relays the grant to a worker,
   appending the relay event to its own log and committing it.
3. **RECEIVED** — the worker verifies the grant *in the committed log*
   (never trusting the channel's word for it) and records the receipt with
   the source commit sha.
4. **CONSUMED** — the worker spends it with exactly ONE landed consumption
   event (a pushed reservation; losing a push race means re-verify).
5. **ACK** — closure flows back.

`tools/validate_auth_log.py` enforces the chain mechanically — globally
across all roles' logs, so the same relay consumed in two logs is caught
as a double-spend. The workspace CI runs it on every push.

**The constraints that make it safe:**

- ON only for an **enumerated list** of gate classes, named in
  BINDINGS.md. Wildcards are invalid by construction.
- The irreversible classes are **never relayable**: outward-facing
  actions, new-money/new-recipient, destructive operations, gate/protocol
  changes. First-hand only, forever.
- Only the principal, speaking directly into the orchestrator session, can
  change PROXY_AUTH itself.
- Auth-log appends ride commits confined to the role's own
  `memory/<role>/` subtree; CI rejects mixed-path auth commits. Optional
  `.auth-provenance.json` binds each role to a distinct author identity.

**Ship state:** OFF. Turn it on only when the relay round-trip is actually
costing you time, and enumerate the narrowest class list that fixes it.

## The reviewer

The review gate assumes an **independent** reviewer — different vendor
preferred, different model at minimum, never the author's own instance.

Worked path — local Codex CLI via the poller:

```bash
python tools/reviewer_poller.py --workspace path/to/ws --once      # one sweep
python tools/reviewer_poller.py --config poller.json --loop --interval 300
```

The poller finds unanswered `review_request_*` files, feeds each to the
Codex CLI (read-only sandbox), writes the verdict file back, and commits.
It is transport machinery, not a party: it never edits requests and never
writes channel entries. Schedule it (Task Scheduler / cron) and forget it.

Alternatives, in preference order:

1. Any other second-vendor CLI — adapt `codex_cmd` in `poller.json`.
2. A Claude session pinned to a model different from the author's, run as
   a manual reviewer against the same request/verdict file contract.
3. (Dead-lane fallback only) the author's vendor, different model — the
   protocol treats this as degraded and says so in the verdict metadata.

## Model presets — MODELS.md

Each workspace's `MODELS.md` is live configuration: an active preset
(maximum / strong / balanced / economy / fast, or your own), per-role
overrides, escalation rules, and a cost-governor rule that may drop to
economy under budget pressure but must report it and never silently
downgrades the reviewer. Change it by telling the orchestrator ("switch to
economy", "put the builder on Opus") — every change lands as a commit.

## Builder read-waves (wave census)

For large evidence-gathering jobs the builder runs **waves**: parallel
read subagents over a partitioned corpus, consolidated with quote-anchored
findings, followed by blind judge passes. `tools/wave_coverage_check.py`
verifies the partition actually covered the corpus (the failure mode is
silent: a wave that skips a shard *looks* identical to one that didn't).
The full procedure is in the builder skill
(`helper-builder-agent/references/wave-census-protocol.md`). Niche until
you need it; when you need it, it's the difference between "we checked
everything" meaning something or not.

## Workspace integrity CI internals

Stamped into every workspace (`.github/workflows/integrity.yml`):

| check | rule |
|---|---|
| auth-log append-only | no removed/edited lines in any `memory/*/auth-log.md` |
| single-subtree auth commits | an auth-log commit touches only its role's `memory/<role>/` |
| provenance map sanity | `.auth-provenance.json` identities must be unique per role |
| auth-chain validation | `validate_auth_log.py` (exactly-one CONSUMED, global) |
| channel append-only | no removed/edited lines in `channel/*.md` |
| CHANNEL_STATE monotonic | counters never backward, keys never removed, no type resets |
| secret scan | private-key/token patterns anywhere fail the build |

These are *state* checks — they protect the coordination record. Your work
repo keeps its own CI; the protocol deliberately doesn't touch it.

## Heartbeats (unattended operation)

Local deployments run attended by default: sessions live while you're
working. For unattended ticks (queue-draining between sittings), schedule
a headless run per role — e.g. a Windows scheduled task or cron job that
opens the workspace and runs the role's tick prompt. Rules that live
experience made non-negotiable:

- The tick runs in a **dedicated clone**, not your interactive checkout.
- Fail closed: clone missing / cd failed / pull failed → abort loudly with
  a logged reason, never "best-effort continue".
- Commit by explicit path; propagate the exit code so the scheduler can
  alert.
- An unattended wake that finds no workspace reports
  "HEARTBEAT ABORT" and stops — it never improvises one.
