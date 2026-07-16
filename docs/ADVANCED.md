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
- The irreversible/outward super-classes are **never listable and never
  relayable**, in every configuration: outward-facing/publish actions,
  email SEND, new-money/new-recipient financial actions, destructive
  operations on another party's artifacts, canonical-repo merges, and
  changes to PROXY_AUTH / gates / embargoes / the protocol. First-hand
  only, forever.
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
python tools/reviewer_poller.py --config poller.json --watch        # event-driven
```

The poller finds unanswered `review_request_*` files, feeds each to the
Codex CLI (read-only sandbox), writes the verdict file back, and commits.
It is transport machinery, not a party: it never edits requests and never
writes channel entries. Schedule it (Task Scheduler / cron) and forget it.

Three run modes: `--once` (one sweep, ideal for a scheduled task), `--loop`
(a full sweep every `--interval` seconds), and `--watch` — event-driven, so a
review request written to a shared-filesystem channel is picked up within a
couple of `--watch-interval` ticks (default 2s) instead of waiting out a poll
cycle. It acts on a change only once the channel signature has *settled*
(stable for one tick), so a request that is still being written is never read
half-formed; for a hard guarantee independent of the interval, have the
producer publish atomically (write a temp file, then rename it into place). A
fallback sweep still runs every `--interval` seconds so requests arriving via a
remote push are never missed — it, too, skips any channel that is mid-write, so
the never-read-half-formed guarantee holds on the timer path as well. (A channel
that never stops changing is therefore only ever picked up once it settles, not
by the timer — the intended trade of liveness for never reading a half-written
request; real producers stop writing once a request is complete.) `--watch` is
stdlib-only (a cheap directory-signature check — no `watchdog`/inotify
dependency).

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

## Conformance suite — is this workspace sound?

`tools/conformance_check.py` is the *structural* counterpart to the integrity
CI. Where the CI protects the record **over time** (append-only, provenance,
secrets — it diffs git history), conformance is a **point-in-time** readiness
check you run locally: after stamping, after filling `BINDINGS.md`, or any
time before you `/wake` an agent in a workspace you're unsure about.

Run it from a protocol checkout and point `--workspace` at the target.
(Stamping also drops a hygiene copy inside each workspace —
`<ws>/tools/conformance_check.py`, the one `/wake` runs in SELF-CHECK
MODE — but for vetting, the protocol checkout's copy is the trusted one.)

```bash
python tools/conformance_check.py --workspace path/to/ws           # check a workspace
python tools/conformance_check.py --workspace path/to/ws --strict  # unbound slots fail too
python tools/conformance_check.py                                  # check cwd (only if cwd is itself a workspace)
```

It verifies, profile-aware:

- every required file for the profile exists (orchestrator-only files are
  required only for `3agent.local`);
- `PROTOCOL_VERSION` is one of the supported versions (v2.5 or v2.6) and the
  profile's role set matches the `memory/` tree;
- the **PROXY_AUTH guard is intact** — the six never-listable super-classes
  are all still named in the slot (a deployer who edits the slot and drops
  one silently weakens the safety property; this catches it), and if the lane
  is switched on the never-listable/relayable clause is still present;
- the auth-log chain is clean (it folds in `validate_auth_log.py`);
- each auth-log and the channel ledger carry the header stamp for the
  workspace's own pinned version (checked pin-aware, not against a fixed
  literal).

Findings are tagged by severity, and the split is deliberate:

- **BLOCKER** (nonzero exit) — structurally broken or unsafe: a missing
  required file, a wrong/unknown profile, a role set that disagrees with the
  profile, a `PROTOCOL_VERSION` outside the supported set (v2.5 / v2.6), a
  weakened PROXY_AUTH guard, or a broken auth-log chain.
- **WARN** (exit 0 unless `--strict`) — stamped but not yet fully bound, or
  cosmetic drift: an unfilled `{{FILL}}` slot, or a per-file stamp / header on
  an auth-log or the channel ledger that doesn't match the workspace's pinned
  version. These don't make the
  workspace unsafe, so they don't fail a plain run; `--strict` promotes them.

So a freshly stamped workspace passes with warnings for its unfilled slots; a
fully bound one passes `--strict` clean. (The load-bearing version signal —
`PROTOCOL_VERSION` in BINDINGS — is a BLOCKER; the per-file stamps are the
softer, cosmetic layer.)

For a trust decision, run it from a protocol checkout pointed at the
workspace (`--workspace path/to/ws`) — the checkout's copy, never the
workspace's stamped hygiene copy — and it deliberately runs its own trusted
copy of `validate_auth_log.py` rather than the target workspace's. A
workspace whose own stamped copy is MISSING is itself structurally broken:
the wake gate fails CLOSED on that absence (a BLOCKER in its own right,
never a skipped step). That also makes it
a natural CI gate: check the workspace out next to a protocol checkout and run
`--strict` once every slot should be resolved.

## Renaming a side (display names)

A side's *display* name — what shows in channel filenames, entry headers, and
`/wake <name>` — is separate from its *canonical role* (owner / builder /
orchestrator). The canonical role is load-bearing: `memory/<role>/` paths,
`start/START_SESSION.<role>.md`, ROLE_LOCK, the auth-log chain, and every
append-only counter key off it and must never change. You can, however, rename
the display name (e.g. `builder` → `helper`) without touching any of that. See
the `SIDE_NAMES` / `ROLE_ALIASES` slots in `binding-slots.md`.

Do it at a **session boundary**, not mid-flight:

1. **Freeze.** Both agents `/sleep` first — no in-flight channel entries or
   review rounds.
2. **Edit `BINDINGS.md`.** Set `SIDE_NAMES` to the new names, add or update the
   `ROLE_ALIASES` row (`<new display>→<canonical role>`, comma-separated), and
   append a history marker inside the `SIDE_NAMES` value so a later reader can
   decode old channel filenames — e.g.
   `SIDE_NAMES | engine / helper (formerly: engine / builder, until 2026-07-07)`.
   Display names use charset `[A-Za-z0-9-]+` — no underscore (it is the
   `<from>_to_<to>_<date>` filename separator).
3. **Leave history alone.** Do NOT rename existing `channel/` files or
   `memory/<role>/` directories — the old names stay so past filenames still
   parse. New entries use the new names; each side's per-side entry counter
   continues unbroken (role identity is unchanged, so numbering never resets).
4. **Land + verify + wake.** One commit at the freeze boundary, run
   `python tools/conformance_check.py --workspace <ws>` (a renamed side without
   a matching `ROLE_ALIASES` row warns; an alias pointing at the wrong role
   blocks), then `/wake <new name>`.

## Heartbeats (unattended operation)

Local deployments run attended by default: sessions live while you're
working. For unattended ticks (queue-draining between sittings), schedule
a headless run per role — e.g. a Windows scheduled task or cron job that
opens the workspace and runs the role's tick prompt. Rules that live
experience made non-negotiable:

- The tick runs in a **dedicated clone**, not your interactive checkout. This
  is isolation **by construction, not by convention**: because the tick's clone
  is a different working tree, it *physically cannot* stage the WIP sitting in
  your interactive session — there is no `git add` it could run that would reach
  those files. That is the difference between "we're careful not to commit your
  half-finished edit" and "it is not possible to".
- Fail closed: clone missing / cd failed / pull failed → abort loudly with
  a logged reason, never "best-effort continue".
- **Stage only the role's own paths, by explicit path** — never `git add -A`
  / `git add .`. The tick commits exactly the files its role produces, and
  **any unexpected diff outside those paths is an ABORT, not a commit**: a tick
  that finds something it did not expect stops and logs it rather than sweeping
  it into history. Propagate the exit code so the scheduler can alert.
- An unattended wake that finds no workspace reports
  "HEARTBEAT ABORT" and stops — it never improvises one.

**Monitoring the heartbeat.** The tick keeps the queue moving; a second,
principal-side check watches *the tick itself*. Schedule a lightweight probe
that alerts when the workspace remote goes **silent past an idle-max** (no new
commit within, say, your longest expected gap between ticks) — a stalled or
crashed scheduler is otherwise invisible, since "nothing happened" looks
identical to "nothing needed to happen". Pair it with a **history-rewrite
guard**: the last-seen remote sha must remain an **ancestor** of the current tip
(`git merge-base --is-ancestor <last-seen> <tip>`); a tip that no longer
descends from what you last saw means force-pushed/rewritten history, which on
an append-only workspace is a red flag worth a human look. This is
**detection-only**, and its blind spots are named on purpose: it cannot see the
**baseline first run** (no prior sha to compare), and a **rewrite-and-revert
between two polls** slips through (the tip is an ancestor again by the time you
look). The protocol deliberately **does not ship** this probe — the alert
channel (email, chat, pager) is platform-specific and yours to wire; the two
checks above are the whole contract.
