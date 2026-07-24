---
description: "Checkpoint this agent session (memory + commit + handover) and declare it safe to close"
argument-hint: "[optional note for the handover]"
---

# /sleep — checkpoint and hand over [PROTOCOL v2.8]

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

2. **Checkpoint memory** (`memory/<role>/MEMORY.md`), per the memory
   discipline (`agent-core/references/memory-discipline.md`). Your role here
   is the CANONICAL role (owner / builder / orchestrator) even if the
   workspace binds a different display name for your side — the
   `memory/<role>/` path and your commit identity always use the canonical
   role, never the display name:
   - Update the **⚡ working-state block** at the top: counters (next entry
     number, next round number), in-flight units, queue tips, last tick,
     resume order. The block plus the underlying artifacts IS the state.
   - Write a **`## Next Step`** section containing the exact action a
     successor takes first. Specific and actionable:
     - Good: `Post channel entry 41 acking builder 42; then dispatch round 13.`
     - Bad: `Continue the project.`
   - Relocate verbatim detail to topic files the index points to; the index
     holds state + pointers. Never delete facts to compact.
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
