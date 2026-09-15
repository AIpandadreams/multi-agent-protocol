# Amendment batch 2 — DRAFT, not yet applied [PROTOCOL v2.5 → v2.6 candidate]

Status: **DRAFT 2026-07-04**, deployment-driven. Source: the PA go-live saga
(2026-07-04) — proven platform facts about claude.ai/code cloud sessions
that the v2.5 cloud transport did not anticipate. Batch 1 covered protocol
semantics; batch 2 covers cloud EXECUTION mechanics. Path: finish drafting →
Codex round → apply → offer to running instances (their choice, as always).

Proven platform facts this batch responds to (all verified live, none
hypothetical — see transports/cloud-git.md and docs/SETUP_CLOUD.md, which
already record them as facts; batch 2 turns them into protocol doctrine):

1. Cloud sessions CANNOT push the workspace repo's `main` (branch → PR →
   merge only).
2. Raw-MCP/env-level scheduled triggers attach an environment + prompt but
   NO repository — fired sessions land in BARE containers. REVISED
   2026-07-04 (two failed test fires): fired sessions have NO standalone
   git credential — the proxy's `insteadOf` rewrite is present but the
   credential behind it is not (interactive sessions have it; fired ones
   don't), and setup-script clones fail the same way. Self-bootstrap is
   therefore DEAD; the only sanctioned heartbeat primitive is a ROUTINE
   with the repo(s) attached (platform clones them with the account's
   GitHub credentials per run).
3. The credential proxy BLOCKS ref deletion (`push --delete` fails; creates
   and updates work) — no cloud-side history rewrite OR branch cleanup, ever.
4. Fired-session delivery is a per-environment property; a probe branch that
   never lands is a real signal about the env, not the prompt.

## A. Consume serialization for cloud workers → proxy-auth-core.md + cloud-git.md

Problem: the pushed-reservation consume (plain `git push` to main, no
rebase) is IMPOSSIBLE for cloud sessions (fact 1). The live <private-repo>
BINDINGS carries a RELAY HOLD until this ships: relayed grants to cloud
worker sessions are parked; direct grants unaffected.

Candidate mechanism — **atomic consume-lock ref**:

- To consume relay `<relay-id>`, the consumer pushes a NEW ref
  `refs/consume/<relay-id>` pointing at its current HEAD (a create-only
  push: `git push origin HEAD:refs/consume/<relay-id>`). Ref creation is
  atomic server-side — exactly one concurrent creator wins; losers get a
  rejected push = lost race, re-verify from scratch (same semantics as the
  losing plain-push today).
- Fact 3 makes the lock TAMPER-PROOF from the cloud: once created, no cloud
  session can delete or move it. The lock ref is the reservation; the
  CONSUMED auth-log line then rides the session's normal claude/* branch →
  PR → automerge, carrying the lock ref name + the sha it points at.
- Validator extension: a CONSUMED event claiming a consume-lock must name a
  ref that exists and whose target commit is by the consuming role's bound
  identity (AUTH_PROVENANCE). Exactly-one-landed-CONSUMED becomes
  exactly-one-lock-ref + exactly-one CONSUMED line naming it.
- Reviewer caveat (round 10): VERIFY the platform accepts and protects the
  chosen ref namespace before relying on it — probe that the credential
  proxy allows creating `refs/consume/*` (it is not `refs/heads/*`), that
  the create is atomic under race, and that deletion is blocked for it too.
  A failed probe → fall back to a `claude/consume/<relay-id>` branch ref
  (same create-only semantics, uglier namespace).
- Open questions for the review round: (a) lock-ref garbage collection —
  only the principal can delete refs; propose: never collected, they ARE
  the audit trail (cheap — one ref per relay); (b) does the CI need a
  refs/consume/* namespace protection rule where available; (c) ordering
  between lock creation and the auth-log PR landing (lock first, always;
  a lock with no CONSUMED line after N hours = stalled consume, escalate).

## B. PUBLISH bound-branch doctrine → cloud-git.md

The PUBLISH verb assumed push-to-main. Amend: PUBLISH for a cloud session =
commit → push `claude/<purpose>` branch → open PR → the workspace's
integrity-gated AUTOMERGE lands it on main. "A unit is not shipped until
pushed" becomes "…until its PR is MERGED" for cloud sessions; a wake whose
PR has not merged reports in-flight, never done. The consume EXCEPTION row
is superseded by batch-2 §A for cloud sessions.

## C. Automerge doctrine → cloud-git.md + SETUP_CLOUD.md

Scope rule, explicit: integrity-gated automerge applies to workspace STATE
repos ONLY (channel/memory/auth-logs — the things the integrity CI can
mechanically verify). CANONICAL work repos keep first-hand merges per
SIGNING; an automerge job in a canonical repo is a binding violation.
Bindings: `.automerge-actors.json` (bound PR authors/actors) is the
identity gate; the head-branch prefix (`claude/`) + base==main conditions
are structural. The SIGNING slot grammar gains a value:
`automerge-integrity-gated (workspace state repo only)`.

## D. HEARTBEAT slot grammar: scheduling primitive is part of the binding → binding-slots.md + cloud-git.md

ONE sanctioned primitive (doctrine in cloud-git.md, revised per fact 2): a
platform ROUTINE with the repo(s) ATTACHED. Raw-MCP/env triggers are
forbidden (no repo, no credential, self-bootstrap proven dead). Amend the
HEARTBEAT slot to record: routine id, attached repos, schedule (local
time), and the fired-and-delivered proof (session id + merged sha + date).
A HEARTBEAT row without a recorded proof is PENDING, not live —
Phase-4-style exit clocks do not start on it.

## E. Timer/standing-machinery scoping → ops doctrine (local-fs.md + cloud-git.md)

Standing timers and pollers (reviewer poller, watchdog, heartbeat
schedulers) are scoped PER WORKSPACE ROOT: state stores, job ledgers, and
lock files live under (or are keyed by) the workspace they serve — never
shared across workspaces (the reviewer poller's per-workspace job store is
the model). Two workspaces sharing one timer state store = crossed
verdicts/wakes, a proven-class hazard. START_SESSION §4 (re-create standing
machinery) checks the timer's SCOPE as well as its existence.

## F. Branch hygiene duty → SETUP_CLOUD.md + orchestrator DUTIES

Because of fact 3, merged/stale `claude/*` branches accumulate and only the
principal can delete them. Add a standing orchestrator duty: the periodic
rollup/briefing lists branches safe to prune (merged into main, no open
PR); the principal prunes on github.com. Cloud sessions never attempt
deletion (it fails and pollutes the log).
