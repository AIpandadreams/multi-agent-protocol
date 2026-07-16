# START_SESSION — orchestrator [PROTOCOL v2.6]

Follow at EVERY session boundary: fresh, resumed, or cold successor. On an
unattended wake assume cold: nothing exists but the repo. A wake that cannot
complete this file does not dispatch anything.

## Operating without the plugin loaded (skill-less baseline)

This contract is followable WITHOUT the agent-protocol plugin/skills loaded —
the accepted baseline for unattended and cloud routines. A plugin *declared* in
`.claude/settings.json` is not necessarily *loaded*: a credential-less routine
cannot install a plugin from a private marketplace, and the install is
machine-level state absent from a fresh clone (`docs/CLOUD.md`). If `/wake` and
the skill surface are absent, do NOT stop — follow this file directly, drawing
the reference docs it cites (`channel-core.md`, `proxy-auth-core.md`,
`orchestration-protocol.md`, `transports/*`, …) from a checkout of the protocol
repo **pinned to a fixed ref/sha** (never a moving branch — the ref your
workspace records for this purpose). That pinned checkout is itself a wake
precondition — provided like the workspace, never self-cloned; **if it is
absent too, ABORT** as in the workspace-missing case, because a doc-less resume
IS the forbidden protocol-less improvisation. This defined floor is not a
protocol-less improvisation (still forbidden); the plugin/`/wake` layer is an
opportunistic convenience on top.

## 0. Verify the workspace exists (unattended wakes — before ANY read)

An unattended wake (a scheduled session) must find the workspace already
provisioned — it never creates one. First action: check for `BINDINGS.md`
in the workspace path. Present → `cd` in, run the conformance gate below,
then proceed to §1. MISSING → the
wake mechanism is misconfigured: notify the principal ("HEARTBEAT ABORT:
wake has no workspace") and STOP. A wake without the workspace reports
that fact; it never improvises one.

## Before binding: run the conformance gate (fail-closed)

Run the workspace's own `tools/conformance_check.py --workspace .` before
resolving any slot. Any BLOCKER is a HARD STOP: surface it to the principal
and do not proceed (WARN-only findings — unfilled `{{FILL}}` / postponed
`{{DEFERRED}}` slots — do not block). **The tool being ABSENT is itself a
BLOCKER, not a pass**: a gate that "passes" by never running is a false
green. If the workspace has no `tools/conformance_check.py`, fail CLOSED —
run the trusted copy from the pinned protocol checkout above (that checkout
absent too = the ABORT already stated), treat anything it reports the same
way, and surface the missing vendored tool to the principal as a structural
BLOCKER in its own right; a clean trusted-copy run does NOT clear it. Only
the principal's explicit word — affirmative first-person words, in THIS
session — waives the missing-tool BLOCKER for that wake.

## 1. Bind

- Load BINDINGS.md + `memory/orchestrator/MEMORY.md`. Resolve every slot
  (shared + orchestrator's: FLAVOR, PROXY_AUTH, TASKQUEUE, SESSION_REGISTRY,
  COST_LEDGER, ESCALATION, DUTIES, TICKS). Confirm ROLE_LOCK says
  orchestrator — if it names another role or is unbound, STOP and ask the
  principal.
- PROTOCOL_VERSION check: skill v2.6 vs workspace stamp; mismatch → flag,
  park protocol-sensitive actions.
- Git-synced workspaces: fetch all bound repos first; diverged or
  un-pushable state is the FIRST problem to solve — a wake that cannot push
  cleanly must not claim progress.

## 2. Verify integrity

- Channel: run the core integrity check (`channel-core.md`) on YOUR outbound
  files — tail entry number vs memory's counter; contiguity. Corruption →
  recovery per core, before any new entry.
- Auth-record: last line of `memory/orchestrator/auth-log.md` matches
  memory's pointer. Apply proxy-auth-core's cold-successor rules: RELAY-SENT
  without RECEIVED = in-flight — verify against the receiver's log, never
  resend under a new relay id; CONSUMED relays are spent forever; expired/
  revoked grants authorize nothing. If PROXY_AUTH is `off`, confirm no stray
  relay machinery survived a revocation.
- Cost ledger + TASKQUEUE parse cleanly; queue ids contiguous with memory.

## 3. Read state

`memory/orchestrator/MEMORY.md` carries a mandatory working-state (⚡) block —
the cold-successor interface. Schema (every field present, "none"/0 allowed):

```
## ⚡ working state
last tick: <ISO timestamp> (<idle|active-window>)
next TASKQUEUE id: T<N>
next channel entry: <N> · per-peer last-seen: <side>=<entry#>@<file> ...
next auth grant id: orchestrator-<NNNN> · auth-log tail: <last event line #>
dispatch log: memory/orchestrator/dispatch-log.md (append-only; one line per
  dispatch: id, date, task ref, target role, model+rule, status, result ptr)
in-flight dispatches: <ids + what resumption requires> | none
briefings: last sent <when/which> · next due <when/which>
decision menu: <count> items (list in body)
active preset: <name> · ledger tail: <last row #>
```

- Read the block, then: all peers' channel tails past the last-seen markers;
  review ledgers (read-only) for round movement.
- SESSION_REGISTRY: mark yourself current; note peers past heartbeat + grace.

## 4. Re-create standing machinery

- Heartbeat/tick schedule per TICKS (idle vs active-window cadence) — verify
  it exists, re-create if the platform lost it.
- Wake monitors (arm-and-verify): if the deployment uses persistent harness
  monitors as the wake path (channel watch, inbox watch), arm them NOW and
  verify each is live before dispatching anything. Session interrupts and
  context compaction silently kill armed monitors; a resume that skips
  re-arm is a deaf seat. Self-expiring pollers are not a valid wake path;
  arm-and-verify runs at EVERY wake and resume, not just fresh starts.
- Standing queue items (briefings, rollups) present in TASKQUEUE; re-seed any
  missing from the DUTIES binding.

## 5. Resume

- Fire anything overdue (missed briefing → send late, marked late).
- Drain the queue per orchestration-protocol §2: preempts, then stalls/
  bookkeeping anomalies (stale verdicts, missing crossing-acks, dead lanes),
  then ordinary items, oldest first.
- Post a short channel entry only if peers need to know you cycled (active
  window: yes; idle: registry update suffices).
- Checkpoint memory before the first long-running dispatch, and after every
  drained item thereafter.
