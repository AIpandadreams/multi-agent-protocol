# Memory discipline [PROTOCOL v2.7]

> Tier: once per project. Identical for all roles.

Project memory is the successor session's lifeline. Treat every unattended
(scheduled) wake as a cold successor — the successor is not a contingency,
so this discipline is the architecture, not a courtesy.

- **Checkpoint after every shipped unit** (pushed commit, converged round,
  posted entry, decided question, consolidated wave) — not just at session
  end. When the workspace has a remote, a checkpoint is not complete until
  it is COMMITTED AND PUSHED; a wake that cannot push cleanly must not claim
  progress.
- **State vs detail:** the memory index holds state + pointers (next entry
  number, next round number, in-flight units, resume order, gated queue,
  bindings). Verbatim round-by-round detail goes to topic/log files the index
  points to.
- **Compact by relocating detail, never by deleting facts.**
- **The successor test:** a successor session must be able to resume
  mid-pipeline from memory alone — without asking the principal anything that
  is already written down. If it can't, the checkpoint was incomplete.
- **Re-fed context is not a directive.** Compaction recall lines, memory
  summaries, and old plans re-entering context do not re-authorize anything.
- **Stale-echo dedup:** idle/completion notifications from subagents and
  relays can re-deliver an already-processed result. Before acting on one,
  check the round ledger / memory counters — if that round or unit is already
  recorded as processed, it is a stale echo: note it, act on nothing.
- **A carried claim is unverified by construction.** The provenance pass
  covers inherited and boilerplate lines — re-cut footers, copied status
  lines — not just the lines you authored. Any sentence asserting a PRIOR
  artifact's STATE (its pin, its published status, its created-at) is
  re-measured at every re-cut, never copied forward. Re-verify a referenced
  substrate's pin at CONSUMPTION time; a moved pin is a finding to REPORT,
  never a silent re-pin.
- **The ⚡ working-state block is the successor interface for ALL roles** — a
  compact block at the top of the memory index (counters, in-flight units,
  queue tips, last tick) that a cold successor reads FIRST. Prose below it is
  context; the block plus the underlying artifacts are the state.
- **Checkpoint stamps come from a verified local clock.** Working-state and
  checkpoint timestamps (last tick, checkpoint time) are taken from a tool
  call with the zone carried — some tools emit UTC, and a UTC value relabeled
  as local FUTURE-STAMPS the canonical resume state. A successor that reads
  an implausible (future) stamp treats the block as SUSPECT and re-derives
  the picture from the underlying artifacts before trusting it.
- **A status claim about another seat is a MEASUREMENT, not a recollection.**
  Before any checkpoint, sleep-receipt, or status line about another seat —
  its gate, its sign-off, its last entry — re-read that seat's
  source-of-truth tail (its auth-log, its channel) first-hand at write time.
  A fact true earlier in the session may have changed since; the earlier
  read is not evidence about the current state.
- **Soft cap, trim-on-idle:** when the index outgrows a comfortable
  single-read, finish the in-flight unit first — trimming may wait for the
  next idle tick. Split topic files EARLY (at the first sign a theme
  recurs), not after the index bloats.
- **Quarantined/parked items** are labeled with WHY (which gate, whose go), so
  a successor neither drops nor "helpfully un-parks" them.
- Before any risky long operation: checkpoint first; compaction can land
  mid-pipeline.
