# The Plan Ledger — machine-readable obligations that survive memory loss

*This directory holds a workspace's plan files. This README is the operator-facing
description of what the ledger is and what each part does; the full specification is
[`docs/PLAN-LEDGER.md`](../docs/PLAN-LEDGER.md). Everything stated here says plainly
whether it ships as tooling or as specification.*

---

## What problem this solves

Agent sessions lose memory. Context windows fill and get compacted (summarized), and a
summary is **lossy** — an obligation, a deadline, or a gate that lived only in
conversation can silently vanish. Role memory files (`memory/<role>/`) help, but they
are prose, and prose is read by judgment, not by machine.

The plan ledger is the failsafe: **every open commitment is typed data in a YAML file,
and tooling re-injects it into the fresh context after each compaction — so a session
that has forgotten everything still receives its obligations, mechanically.**

## The parts

### 1. The ledgers themselves — `plans/*.plan.yaml` (this directory)

Ships: this README only — no schema file and no example plan file ship yet; the field
reference below and `docs/PLAN-LEDGER.md` are the format's description of record.

One file per plan. Typed fields, no prose-only obligations:

| field | what it holds |
|---|---|
| `state` | `open` or closed — only open plans are injected |
| `commissioned` | who authorized the plan, under which authority id, when |
| `owner_seat` | which agent seat owns it |
| `coordinates` | the repos, paths, branches, and ids the plan touches |
| `steps[]` | each with its own `owner`, `preconditions`, `status`, a **`done_when` command with an expected result** (a step is done when a command proves it, not when someone says so), and an `evidence` block recording when it ran and the hashes of what it produced |
| `gates[]` | decisions: the `question`, who rules it (`ruler`), what it `unblocks`, and the ruling once made — an unruled gate keeps its steps blocked mechanically |
| `clocks[]` | timed obligations with fire times |
| `constraints[]` | live restrictions with their expiry conditions |

### 2. The memory failsafe — `tools/compaction_inject.py` (ships in this repo, with its shared ledger-access module `tools/plan_common.py`)

When a session's context is compacted, this hook renders every **open** plan into a
typed digest (steps still pending, gates unruled, clocks unfired, constraints live)
and injects that digest into the fresh context, stamped with an injection nonce. The
digest states its own contract: *"The compaction summary is lossy; THIS block is the
carrier of record."* Wiring: `--mark` runs as a **PreCompact** hook (records that a
compaction boundary is coming), and `--inject` runs as a **SessionStart** hook with
matcher `"compact"` (renders and emits the digest into the post-compaction context).
Its injection markers are the `plans/.last_injection.*` and
`plans/.compaction_pending.*` files that appear beside the plan files once it runs.

Prerequisite: **PyYAML** (`pip install pyyaml`) — the one non-stdlib dependency.
Without it the hook does not crash the session: it reports the ledger as unreadable
and, per its declared fail direction, gated classes stay closed. After each injection
the hook names an `--ack` step: that command ships with the enforcement gate (part 3,
deferred), so until part 3 lands the ack is informational and the injection receipt
simply records that the digest was emitted.

### 3–5. The enforcement gate, the clock sweep, the wake integration

Specified in [`docs/PLAN-LEDGER.md`](../docs/PLAN-LEDGER.md) with a per-part
shipped/deferred status table — the gate's source and test suite, the clock-sweep
daemon, and the wake-side ledger verification are **deferred to their own reviewed
release**; the specification is normative in the meantime. A deferral that is stated
is a scope decision; a deferral that is silent is a broken promise.

## The lesson this directory records

This system first ran documented only in its own source code — invisible to the
principal it protects. A system whose verification requires reading Python is not
verifiable by its owner. From here forward: **an undocumented ship is an unfinished
ship**, and the documentation lands in the same commit series as the code.
