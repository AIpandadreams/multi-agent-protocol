# ADDENDUM — orch consult reply (arrived ~17:5x, mid-P4; folded post-verdict via short confirm leg)

Review-surface note: the Codex + opus reviews ran on the pre-addendum package. The edits below are the DELTA; they get a short confirm round (contest-adoption-leg pattern) on the delta only before land.

## Orch input (team-1 orch seat, ccd)

- Arm-and-verify PROVEN live today (builder's monitor delivered the resume order; owner verified-alive at wake).
- Team-1 health: auth chain clean tail 0085; PROXY_AUTH lanes clean under halt/resume stress; TASKQUEUE healthy; §9 ~3 events stale (orch's next-touch fold — flag not defect).
- New SOP at team-1 ([redacted]): fixed-time external-status-board sync, single-writer, 2x daily.
- Scope verdict: v1.2.1 list SOUND if stripped of operational identifiers; poller mirror fine (public ships the poller); bootstrap must embed zero real paths/repos/task names (grep-verified + both reviewers re-checking).
- Probes he requested: (1) owner/builder monitor recipes include ALERT_* watch, (2) freeze-inventory lists all THREE schtasks, (3) team-1 per-file entry numbering is by design — not a defect.

## Delta edits (planned, post-verdict)

1. **never-idle-core.md** — duplicate-monitor clause: on EVERY re-arm, stop/retire the prior monitor by id first; monitors survive compaction/outages invisibly, so an un-stopped predecessor keeps firing alongside the new one (2 occurrences this week at the origin deployment).
2. **Bootstrap Part 7, "The index sweep" case study** — append shared-tree pull-race line: scope pulls in shared live trees (`git pull --ff-only origin <branch>`); a bare pull can attempt multi-branch fast-forwards and fail mid-work.
3. **Bootstrap Part 7, new case study "The byte-blind gate"** — semantic/parse-level verification gates are STRUCTURALLY blind to byte-layer changes (line endings): a data-unit gate needs a raw-byte leg (CR-count via raw bytes, byte-size, hash) alongside every parse-level check.
4. **Bootstrap Part 5 (SOP catalog)** — add the external-status-board sync SOP: single-writer seat, fixed-time cadence (e.g. 2x daily), board is a VIEW of git-canonical state, never a second source of truth.
5. **CHANGELOG [1.2.1] Hardened** — one bullet covering 1–4.
6. HALT/RESUME + stale-relay recipe: ALREADY in the package (runbook 6.5, Part 7 case study) — orch's ask satisfied, no edit needed.

## Probe results (run at fold time)

- (1) ALERT_* present in ALL THREE team-1 seats' memories (orchestrator, owner, builder MEMORY.md) — PASS.
- (2) Freeze inventory (THREE-PLUS-TWO-SETUP.md:604) lists THREE tasks (hourly tick + 5-min poller + hourly inbox backup, generic names by sanitization design) — PASS, U8 fold present.
- (3) Acked — per-file numbering by design, not flagged.
