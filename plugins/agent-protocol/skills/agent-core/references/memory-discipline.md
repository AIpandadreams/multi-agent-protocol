# Memory discipline [PROTOCOL v2.5]

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
- **The ⚡ working-state block is the successor interface for ALL roles** — a
  compact block at the top of the memory index (counters, in-flight units,
  queue tips, last tick) that a cold successor reads FIRST. Prose below it is
  context; the block plus the underlying artifacts are the state.
- **Soft cap, trim-on-idle:** when the index outgrows a comfortable
  single-read, finish the in-flight unit first — trimming may wait for the
  next idle tick. Split topic files EARLY (at the first sign a theme
  recurs), not after the index bloats.
- **Quarantined/parked items** are labeled with WHY (which gate, whose go), so
  a successor neither drops nor "helpfully un-parks" them.
- Before any risky long operation: checkpoint first; compaction can land
  mid-pipeline.
