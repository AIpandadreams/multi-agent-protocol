# BUILDER AGENT — session start / handover TEMPLATE [PROTOCOL v2.5]

This file is a TEMPLATE. To deploy the builder agent on a project, copy it into
the project as its start-session/handover file, fill §0, and keep it current.
Follow the instantiated copy top to bottom at the start of every builder
session (fresh start, restart after compaction, or successor session). Do not
skip steps because the session "looks" continuous — the checklist is cheap and
a missed step is not. For mid-session resumes, `references/session-card.md` is
the condensed form — this full contract runs at every true session boundary.

## Before anything (unattended wakes): verify the workspace exists

An unattended wake (a scheduled session) must find the workspace already
provisioned — it never creates one. Check for the workspace's
`BINDINGS.md`: present → `cd` in and proceed; MISSING → the wake mechanism
is misconfigured — notify the principal ("HEARTBEAT ABORT: wake has no
workspace") and STOP; never improvise a workspace. Interactive local
sessions: the workspace is already on disk; skip.

## 0. Instance bindings (fill these per project)

| binding | value |
|---|---|
| ROLE_LOCK | this session is the BUILDER on `{{PROJECT}}` (if memory names another role or is unbound: stop, ask the principal) |
| SIDE_NAMES | `{{OWNER_SIDE}}` / `{{BUILDER_SIDE}}` (same pair the owner binds; used in filenames + entries) |
| Builder home directory | `{{BUILDER_HOME}}` (the directory the builder session starts in) |
| Owner's canonical repo | `{{OWNER_REPO}}` — READ-ONLY to the builder, always (SHARED_ARTIFACTS below are the only exception) |
| Frozen-snapshot location | `{{SNAPSHOT_DIR}}` (pinned extracts waves read from) |
| CHANNEL inbox | `{{CHANNEL}}` (shared; holds channel files, review requests/verdicts, synced deliverables, the round ledger `INDEX.md`) |
| Builder channel file | `{{BUILDER_SIDE}}_to_{{OWNER_SIDE}}_YYYY-MM-DD.md` (yours; rotate per day or ~64KB) |
| Owner channel file | `{{OWNER_SIDE}}_to_{{BUILDER_SIDE}}_YYYY-MM-DD.md` (read-only to you) |
| SHARED_ARTIFACTS | `{{LIST or "none": cross-boundary writable artifacts + conditions (out of commit surface; principal per-batch go; re-read before edit; writes announced)}}` |
| Canonical working papers | `{{WORKPAPERS_DIR}}` (off-repo durable store; identifiers allowed here ONLY if the principal designated it) |
| Project memory | `{{MEMORY_DIR}}/MEMORY.md` (+ topic files it indexes) |
| Reviewer | `{{REVIEWER}}` (mechanism relayed/harness-gate + model), serialized lane, side-prefixed series `review_request_{{BUILDER_SIDE}}_rNN.md` |
| Principal | `{{PRINCIPAL_NAME}}` — all gates; authorization only first-hand, affirmative first-person, in this session |
| Standing gates & embargoes | `{{LIST: what may never be written/named/sent without a go}}` |
| Size tripwire | `{{N}}` rows → same-day principal flag |
| HEARTBEAT | `{{MECHANISM + cadence}}`, offset from the owner's (+ when to delete it) |
| MODEL | you=`{{MODEL}}`, owner=`{{MODEL}}`, reviewer=`{{MODEL}}`, wave subagents=`{{MODEL}}` |

## 1. Read state (in this order)

1. `MEMORY.md` — full read of the "start here" block. It tells you: what
   converged, what is in flight (round numbers, background agent ids), the
   next channel entry number, the principal-gated queue, and the resume order.
2. The conventions/ground-rules topic file memory points to — before drafting
   anything.
3. The current day-loop/topic detail file — verbatim state of the last
   pipeline.
4. The round ledger (`INDEX.md`) tail — reconcile its last row FOR YOUR SIDE
   against memory's claimed round state. Any mismatch: investigate BEFORE
   acting.

## 2. Channel integrity check

1. Your OWN outbound file's last entry number equals memory's counter.
2. Owner file's entry numbers are contiguous through memory's "last seen".
3. Corrupted/truncated tail → DISCONTINUITY procedure (channel protocol):
   don't append; post a dated discontinuity entry; rebuild counters from the
   files (files are canonical, memory is the pointer); flag the principal.

## 3. Probe the machinery

1. **Heartbeat** per binding (one only; delete stale ones; delete at window
   end).
2. Background tasks: list running/completed tasks; a completed-but-unprocessed
   relay or wave return is your first work item.
3. Reviewer lane: confirm no stale "running" relay job is squatting the
   serialized lane (see ops-gotchas for the central-state repair). Silent
   after 2 nudges spanning 2 heartbeats → dead-lane escalation
   (review-loop-protocol).
4. Snapshot integrity: if a wave is in flight, confirm the frozen snapshot
   still matches its pin. Also `git fetch` in your read-only clone/snapshot
   source and note if the owner's remote moved.

## 4. Poll the channel

- List the inbox; read the owner file's entries past memory's "latest seen";
  compare numbering. Unread entries → intake now, before choosing new work.
- Unannounced deliverable files → "visible, holding intake" + start the
  hold-timeout clock (channel protocol).
- Your first entry of the session states: session resumed, protocol version,
  what is in flight, latest owner entries seen.

## 5. Resume the pipeline

- Memory's resume-order list is authoritative. Finish interrupted units before
  new ones; do not restart finished work — check for the artifact/ledger row
  first.
- Standing disciplines in force at all times: freeze round before execution ·
  results round after · one relay in flight · reconciliation before verdict ·
  no severity on unread suspects · annotate-not-delete · announce-before-sync ·
  verify peer-claimed shas before pinning · checkpoint memory after every
  shipped unit.

## 6. Session close / handover

Before ending (or when context pressure looms): checkpoint memory (state +
pointers + resume order), post any owed channel entry, note in-flight
background agent ids and round numbers, and leave quarantined/parked items
labeled with WHY they are parked (which gate, whose go). The successor should
be able to resume mid-pipeline without asking the principal anything that is
already written down.
