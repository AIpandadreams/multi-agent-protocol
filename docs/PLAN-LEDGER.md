# The Plan Ledger — obligations that survive a memory loss

An agent session forgets. Context fills, gets compacted into a summary, and a summary is
**lossy** — a commitment, a deadline, or a decision that was waiting on someone can
disappear without anything announcing that it went.

Role memory files help, but they are prose, and prose is read by judgment. The plan ledger
is the mechanical failsafe underneath them: **every open commitment is typed data in a
file, and tooling re-injects it into each new context — so a session that has forgotten
everything is still handed its obligations.**

---

## Words used precisely

Three words in this document and its companions carry a narrower meaning than their
ordinary one. ⛔ **Reading them loosely is the fastest way to misread all three documents:**

- **gate** — a *decision* that blocks dependent work until someone rules it. (Not a check
  that runs, and not a CI job; a tool that refuses something is called a **check**.)
- **canonical** — the copy of a file in this repository, as opposed to a **vendored** copy
  that a deployment has taken and may have modified. (Not "correct" and not "blessed" —
  purely a statement of where the file lives.)
- **seat** — a named position a participant occupies, with its own directory and record.
  (Not a person, and not a running process.)
- **creator** — a chartered external identity that may OWN plans (a valid step `owner`
  value) without holding any positional seat in a stamped profile. The vocabulary of
  record for how it relates to the three positional seats is the seat & identity table
  in `plugins/agent-protocol/skills/agent-core/references/binding-slots.md`.

---

## What this release contains, and what it does not

⛔ **Read this before the design below.** The 1.9.0 release shipped **this document** —
the specification — with none of the five parts as tooling. **As of 1.9.1, part 2 (the
memory failsafe) ships as runnable tooling** (`tools/compaction_inject.py` with its
shared ledger-access module `tools/plan_common.py`), and the `plans/` directory exists
with its operator-facing README. Every part below carries its own status:

| part | status in this release |
|---|---|
| 1. The ledger file format | **specified here** — `plans/README.md` (operator seed) ships as of 1.9.1; no schema file and no example plan file ship |
| 2. The memory failsafe (compaction hook) | **ships as of 1.9.1** — `tools/compaction_inject.py` + `tools/plan_common.py` |
| 3. The enforcement check | **specified here, deferred** — its source and test suite are not ported |
| 4. The clock sweep | **specified here, deferred** — ⚠ until it ships, `/wake` runs its daemon-liveness check (step 6a) only in a workspace that binds a `CLOCK_DAEMON` row in BINDINGS.md (a deployment-supplied daemon); without that binding the wake report says `no clock daemon bound` rather than leading every wake with a `⛔ CLOCK DAEMON DOWN` alarm nothing could ever clear |
| 5. Wake integration | **ships as of 1.9.0** — `/wake` step 6 runs on every wake: daemon liveness (6a, gated as row 4 states), the open-ledger digest rendered into the report's mandatory `Ledger:` line (6b), and the stale-head cross-check (6c) |

⚠ **Deferral-coupling note (parts 3–5):** the deferred parts are not vapor — reference
implementations exist and run in the steward's private deployment, and their public
landing here is a gated port wave on the steward's side. That event is exactly what
invalidates the "deferred" rows above: re-verify this table whenever a ported part
lands (the same pass should re-check `/wake`'s renderer deferral, which lives on the
same private side).

So the design below is written in the present tense of a **specification**: for parts
3–5 it describes what those parts do *when built*, and you should not expect to find,
run, or verify them in this checkout. Part 2 you now can — its hook wiring (PreCompact
`--mark`, SessionStart `--inject`) is described in `plans/README.md`, and note that its
`--ack` discharge path completes only when part 3 (the enforcement gate) lands. ⭐ **A
deferral that is stated is a scope decision; a deferral that is silent is a broken
promise** — this table is the whole list, not a sample.

---

## The parts

### 1. The ledger files — `plans/*.plan.yaml`

One file per plan. Typed fields, so nothing important exists only as a sentence:

| field | what it holds |
|---|---|
| `state` | `open` or closed — only open plans are injected |
| `commissioned` | who authorised the plan, under which authority record, and when |
| `owner_seat` | which seat owns it |
| `coordinates` | the repositories, paths, branches and records the plan touches |
| `steps[]` | each with its owner, preconditions, status, a **`done_when` command with an expected result**, and an `evidence` block recording when it ran and the hashes of what it produced |
| `gates[]` | decisions: the question, who rules it, what it unblocks, and the ruling once made |
| `clocks[]` | timed obligations, with fire times |
| `constraints[]` | live restrictions, with the condition that ends them |

Two of these carry most of the weight:

- **`done_when` means a step is finished when a command proves it**, not when someone
  reports it. The command and its expected result are written down before the work starts,
  so "done" is not a matter of opinion afterwards.
- **An unruled gate blocks its steps mechanically.** A decision nobody has made cannot be
  passed by momentum — the steps behind it stay blocked until the ruling is recorded.

### 2. The memory failsafe — the compaction hook

When a session's context is compacted, this hook renders every **open** plan into a typed
digest — steps still pending, gates unruled, clocks unfired, constraints live — and injects
that digest into the fresh context, stamped with a nonce so a stale injection is
distinguishable from a current one. The digest states its own contract: the compaction
summary is lossy, and the injected block is the carrier of record.

### 3. The enforcement check

⚠ **A check, not a gate — by this document's own definitions block, and it was titled
"gate" until 2026-08-07.** It is a tool that refuses; the *gates* are the ruled decisions
in `gates[]` that it enforces. The two are not interchangeable, and a definitions block
the same document then violates is worse than no block: it shows the vocabulary is
aspirational rather than used.

A pre-tool hook that **blocks** gated side effects — deploys, releases, publications —
whenever the ledger says they are gated. A block must be acknowledged in-context;
overriding one is a single-use authorisation **bound to the exact command signature**, so a
changed command needs a fresh override rather than inheriting the old one. Every override
is logged.

### 4. The clock sweep

A daemon sweeps the timed obligations and stamps a heartbeat after each completed sweep.
Any session that wakes checks that stamp: **older than the liveness window — or absent,
unparseable, or dated in the future — and the wake report leads with the daemon being
down.** Timed obligations are then treated as unswept rather than assumed handled.

⭐ The design rule underneath this one: **silence is never read as health.** An unarmed
watcher and a quiet lane look identical from the outside, so liveness is something the
system asserts positively or not at all.

### 5. Wake integration

The wake procedure reads the ledger on every session start: it renders the seat's open
items — a projection that **may drop nothing that is open for that seat** — runs the
daemon-liveness check, and checks the dispatch head for staleness before treating it as an
instruction.

---

## What an operator can do with this, as the parts land

⚠ **Most of the following is not yet available from this release** — see the status
table above. The exception is the last bullet's foundation: the compaction re-injection
hook (part 2) now ships, so the typed digest a cold successor receives after a
compaction is real tooling in this checkout; the query, verification, and liveness
bullets still wait on parts 3–5. This is what the design buys an operator; each
bullet becomes real as its part lands:

- **Ask what is actually open**, for any seat, and get a typed answer rather than a summary.
- **See which decisions are waiting on a person**, and what each one is holding up.
- **Verify a "done" claim** by running the same `done_when` command yourself.
- **Find out whether the clock daemon is alive**, rather than inferring it from quiet.
- **Hand a cold successor a working picture of the obligations** without relying on
  anything a previous session remembered to write in prose.

## Honest limits

- The ledger records what someone typed into it. **A commitment never entered is not
  protected** — the failsafe is against forgetting, not against never recording.
- Injection proves the digest reached the context. It does not prove the session acted on
  it; that is what the gates and the `done_when` commands are for.
- The heartbeat proves a sweep completed. It does not prove the sweep was correct.

## The lesson this file exists to record

A system can run for a long time documented only in its own source code and in the
messages its components exchange — which is to say, invisible to the people it serves.
**A system whose verification requires reading its source is not verifiable by its
owner.** From here on: an undocumented ship is an unfinished ship, and the documentation
lands in the same commit series as the code.
