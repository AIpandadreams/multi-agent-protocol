---
description: "Checkpoint this agent session (memory + commit + handover) and declare it safe to close"
argument-hint: "[optional note for the handover]"
---

# /sleep — checkpoint and hand over [PROTOCOL v3.2]

Put this agent session to sleep: persist everything a cold successor needs,
land it in git, and tell the principal it is safe to close the window.
Sleep is the flip side of `/wake <role>` — together they replace recall-line
pasting entirely.

Optional note from the principal to weave into the handover: $ARGUMENTS

## Steps (in order — do not skip)

1. **Identify your role.** You are role-locked for this session
   (owner | builder | orchestrator). If this session never bound a role,
   say so and stop — /sleep is for role sessions inside an agent workspace
   (a directory with `BINDINGS.md` and `memory/<role>/`).

1b. **Soft-land everything in flight FIRST** (principal's standing
   instruction, 2026-09-16, both workspaces — "land everything in flight
   fully and softly" is part of every /sleep, never something the
   principal has to say). Before any checkpoint write, enumerate and
   dispose of every in-flight object this seat owns, in this order:
   - **Drafted but unlanded text** (lane entries, auth-log entries,
     relays, register rows sitting in a scratchpad): append through the
     sanctioned writer, pathspec-commit, push, grade the landed object
     (hash-object vs the committed blob), and confirm remote containment
     (`git branch -r --contains <oid>`). A draft that cannot land now is
     recorded in the ledger as parked, with its file path and why.
   - **Uncommitted edits to files this seat owns**: commit by explicit
     path and push. Peers' modified or untracked files are NOT yours —
     never stage, stash, reset, clean or tidy them.
   - **Dispatched review legs still running** (codex / opus / OR voices):
     do NOT kill them. Record tag, spawn PID, output path and the
     grading rule in `memory/<role>/REARM.md` (step 4b) so the successor
     grades the finished output at wake; a leg whose output already
     carries its verdict is graded and recorded now.
   - **Peers waiting on this seat**: every ask addressed to this seat
     that is not yet answered gets either its answer landed or a one-line
     lane entry saying it is carried across the restart and when it will
     be answered. Silence across a restart is a routing defect.
   - **Principal-gated items**: list them (gate, what it unblocks) in the
     ledger; sleep never opens a gate.
   "Softly" means: no force-push, no `--amend` in a shared tree, no
   reset/checkout/restore/stash/clean, no killing of peers' processes, no
   deleting or moving anything outside this seat's own scratch. If a
   landing is refused by a gate (identifier gate, plan gate, push
   rejected), fix the object or park it with the refusal text recorded —
   never bypass the gate to make sleep faster.

2. **Checkpoint memory** (`memory/<role>/MEMORY.md`), per the memory
   discipline (`plugins/agent-protocol/skills/agent-core/references/memory-discipline.md`). Your role here
   is the CANONICAL role (owner / builder / orchestrator) even if the
   workspace binds a different display name for your side — the
   `memory/<role>/` path and your commit identity always use the canonical
   role, never the display name:
   - The volatile head — the ⚡ working-state block and the `## Next Step`
     section — is a RENDERING of the open ledger (`plans/*.plan.yaml`)
     plus the live lane tails, and ALL head writes go through the
     renderer: run `tools/render_head.py <workspace> <role>`.
     /sleep NEVER hand-authors the head — not the ⚡ block, not the
     `## Next Step`, not a "small refresh" (sole exception: the
     bootstrap carve-out — a pre-adoption workspace with no `plans/`
     ledger, where the renderer cannot run; step 3 names the legal
     hand cures there, and adopting the ledger ends the exception).
     A still-hand-authored head
     (no `render_head` footer) migrates via `tools/render_head.py --adopt`,
     which demotes the old head byte-intact under a `####` historical
     heading and renders the single new head — the documented
     supersession move, mechanized. State a successor needs lives in the
     LEDGER (update `plans/*.plan.yaml` step status / evidence / clocks),
     then render; never route it around the ledger into hand-written
     head prose.
   - Hand judgment goes in **`## Standing judgment`** (the renderer never
     generates or modifies it). Relocate verbatim detail to topic files
     the index points to; the index holds state + pointers. Never delete
     facts to compact.
   - If a unit is parked on a gate, record WHY (which gate, whose go) so the
     successor neither drops it nor un-parks it.

3. **Land it.** Commit the files you own (memory, channel entries you
   appended) by **explicit path** — never a bare `git add -A` — and push.
   If the push fails, resolve it now; an unpushed checkpoint is not a
   checkpoint, and you must not declare sleep on top of one.
   - **git-sync transport:** the push includes every state branch you
     advanced this session, not just the default branch — channel, auth-log,
     and any reservation-class `state/**` branch. A checkpoint that leaves a
     state branch unpushed strands the peer at the old tip, so reconcile and
     push each before declaring sleep (fetch first if the push is rejected).

4b. **Restart persistence (PC restart + app restart).** A sleep must
   survive the machine going down, not just the window closing. Nothing a
   successor needs may live only in the session, the harness, or an
   unpushed local commit.
   - **Session-scoped instruments DIE with the app**: harness Monitors,
     session-scheduled crons/wakeups, background shells and watchdog
     loops. Write every one that must exist after wake into
     **`memory/<role>/REARM.md`** (hand-authored, this seat's file, one
     block per instrument: kind `monitor | cron | background | leg`,
     purpose, the exact command or its script path, interval/expiry,
     what event it emits and who acts on it). /wake step 5b re-arms from
     this file. An empty or absent REARM.md means "nothing to re-arm" and
     the successor must be able to trust that, so keep it current.
   - **OS-scheduled tasks persist across a PC restart** (schtasks, cron,
     launchd) but may sit disabled or fail their first run after boot.
     List each one this seat depends on in REARM.md under `verify:` with
     its name and expected state (Ready/enabled, last run, next run) so
     the wake verifies rather than assumes.
   - **Git is the only durable store**: every commit this seat made this
     session is contained in the workspace remote's default branch (or its
     named state branch) — check with `git branch -r --contains`. A
     publish worktree, a scratchpad, or a temp directory may be gone or
     stale at wake; anything read from one at wake is re-derived from the
     remote first. Record the remote tip (oid) at sleep in the ledger
     evidence so the wake can measure what moved.
   - **The live working tree** may hold peers' uncommitted work and lag
     the remote; the wake reconciles it by fetch + merge only (never
     reset). Record HEAD, the remote tip and the modified-file count at
     sleep so the wake compares.
   - **Local-only external state** the successor will need (an inbox
     directory for relays, a handover root, a cloud-synced share path) is
     named in REARM.md with what was last placed there, so the wake reads
     it instead of rediscovering it.

4. **Change log.** List exactly what changed this session, file by file
   (required even when small).

5. **Handover.** Print exactly this block:

   ```
   ---
   💤 SLEEPING — safe to close this session.
   WAKE: /wake <role> — <first action, 10 words max>
   ---
   ```

   The wake line is a command, not a summary — the successor reads MEMORY.md
   itself.

## Rules

- Sleep changes STATE only. It never grants, extends, or implies
  authorization; open gates stay open and are listed in the ⚡ block.
- If nothing new happened this session, still refresh `## Next Step` and
  print the handover block.
- Mid-pipeline sleep is fine — that is exactly what the ⚡ block is for —
  but checkpoint BEFORE any risky long operation, not after it fails.
