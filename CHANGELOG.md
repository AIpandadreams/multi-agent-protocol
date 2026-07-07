# Changelog

All notable changes to this repository are documented here. The repo
follows [SemVer](https://semver.org) for its own releases; the protocol the
skills implement carries its own version stamp (`PROTOCOL vX.Y`), which
changes only through the
[self-improvement protocol](plugins/agent-protocol/skills/agent-core/references/self-improvement-protocol.md).

| repo release | protocol version | notes |
|---|---|---|
| 1.2.0 | v2.6 | `PROTOCOL v2.6`: review-convergence, never-idle, git-sync cloud transport, role aliasing, wizard v2, ops tooling |
| 1.1.0 | v2.5 | tooling: `--wizard`, `--watch`, conformance suite |
| 1.0.0 | v2.5 | first public release |

## [Unreleased]

## [1.2.0] — 2026-07-07

### Added — PROTOCOL v2.5 → v2.6 amendment
An amendment bundle bumping the protocol the skills implement from
`PROTOCOL v2.5` to `PROTOCOL v2.6`:
- **Review-convergence cycle** — a new normative reference
  (`agent-core/references/review-convergence.md`) layering the multi-round
  cycle over `review-core.md`: the four seats (author / peer-model reviewer /
  cross-vendor reviewer / author-as-verifier-of-the-verdict), a 2–3 round
  budget with escalation-on-exhaustion, evidence-weighed adjudication of
  reviewer disagreement (votes/averages banned), a mechanism-neutral blocking
  line (BLOCKER/MAJOR gate, MODERATE/MINOR recorded), anti-anchoring, an
  anti-patterns catalogue, and a worked convergence arc.
- **`/converge` command** — a harness command that drives an artifact through
  the convergence cycle to a reviewer-declared stop.
- **Never-idle autonomy level** — a new normative reference
  (`agent-core/references/never-idle-core.md`) and a fourth rung on the
  autonomy dial: a worker between assignments holds at intake-watch and acts on
  settled events within one cycle. Closed MAY / MUST-NOT self-assign lists; the
  invariant that never-idle changes cadence, never authority. Adds the
  **AUTONOMY** and **WATCHER** binding slots.
- **Reviewer-lane outage rules** — `review-core.md` gains a normative
  `## Reviewer-lane outage` subsection: probe-before-blame, a fallback ladder
  (alternate transport → different-model judge → multi-judge panel, DEGRADED-
  tagged), and principal-gated gate-disable for outage windows.
- **FIX-CONFIRMATION round type** — `reviewer_poller.py` frames a request
  carrying `ROUND-TYPE: FIX-CONFIRMATION` to judge named fixes and end with
  CONVERGED / NOT-CONVERGED; the stamped `channel/INDEX.md` ledger gains a
  ROUND-TYPE column and a rounds-used-vs-budget note.
- **Pin-aware conformance** — `conformance_check.py` accepts a supported
  version set (v2.5 / v2.6) and checks every per-file stamp against the
  workspace's OWN pinned version, so a live v2.5 workspace and a fresh v2.6
  workspace both pass under one checkout.
- **git-sync transport (cloud / distributed peers)** — a new transport profile
  (`transports/git-sync.md`) binds the abstract channel verbs
  (POLL/READ/APPEND/PUBLISH/INTEGRITY) to git over a remote, for peers on
  separate machines or a live session plus a scheduled cloud twin. Ships with:
  the load-bearing disjoint-owned-paths invariant (any rebase conflict is a
  protocol-violation detector); two commit classes with two retry rules
  (append-class rebases, reservation-class re-verifies — a consume commit is
  never carried through the generic retry loop); self-managed vs hosted-cloud
  host classes; the credential doctrine (headless sessions never self-clone —
  a missing checkout aborts loudly); required force-push/branch-deletion
  protection; and a helper `tools/git_sync.py`. New **TRANSPORT**,
  **WORKSPACE_REMOTE**, and **SECRETS** binding slots; new
  `2agent.git-sync` / `3agent.git-sync` stamp profiles;
  `conformance_check.py` gains a `check_transport` pass (profile↔transport
  agreement, unknown-value block, repo-relative-path guard). See
  [docs/CLOUD.md](docs/CLOUD.md) for the deployment recipes and their honest
  hosted-cloud caveats.
- **Role display-name aliasing (rename)** — a new **ROLE_ALIASES** binding slot
  lets a deployment give its roles workspace-local display names (e.g.
  `engine→owner`, `helper→builder`) that `/wake` resolves in three tiers:
  canonical name → the workspace's `ROLE_ALIASES` row (which beats the built-ins)
  → the legacy `engine`/`helper`/`orch` built-ins (so pre-2.6 workspaces with no
  row still resolve). Aliases resolve ADDRESSING only — identity artifacts
  (`ROLE_LOCK`, `memory/<role>/`, `START_SESSION`) always use the canonical role.
  The rename is doc-only (no scripted rewrite); `conformance_check.py` gains a
  side-name pass and warns on a role renamed without a matching `ROLE_ALIASES`
  row.
- **Onboarding — wizard v2** — `new_project.py --wizard` is now a pre-stamp
  walkthrough: topology → side names (validated at entry — underscore and other
  channel-filename-illegal characters are rejected and re-prompted) → principal
  → project repo → reviewer (probes `PATH` for a `codex` CLI; `none` is allowed
  but warns that independent review is the core quality lever) → a grouped
  `{{FILL}}` walk (day-one slots vs deferrable, where Enter records a
  `{{DEFERRED}}` marker distinct from an untouched `{{FILL}}`). After every
  stamp it prints a **NEXT STEPS** block with absolute paths. New `--git-init`
  (default off; non-fatal, timeout-guarded so a cold GPG agent never eats the
  stamp) and `--plugin-install {marketplace,manual}` — `manual` omits the
  marketplace blocks from the stamped `.claude/settings.json` for a hand-copied
  `~/.claude` install. `--no-orchestrator` is now a deprecated alias for
  `--profile 2agent.local` (it errors instead of stamping an invalid workspace).
  The stamp also drops a **self-check copy** of `conformance_check.py` into the
  workspace (`SELF-CHECK MODE` banner — hygiene, not a trust gate), and the
  `/wake` command runs a pre-wake conformance gate that hard-stops on any
  BLOCKER (including the new **one-agent-per-role** check) and warns when the
  workspace is not a git repo (checkpoints won't persist). QUICKSTART gains a
  three-repo diagram and a first-exchange example; README gains a reading order.

The whole skills tree, the two lifecycle commands, and the tooling stamps flip
to `PROTOCOL v2.6`; `new_project.py` stamps v2.6 workspaces.

### Changed
- Documentation default topology inverted: the 3-agent shape (orchestrator +
  owner + builder) is now presented as the default, and `2agent.local` is
  reframed as the **dual-role-owner** variant (the owner absorbs the
  orchestrator's interface/intake duties). No protocol-semantic change; profile
  ids and tooling are untouched.

## [1.1.0] — 2026-07-05

Tooling round: three quality-of-life additions to `tools/`, each carried
through independent cross-vendor review to convergence. No protocol-semantic
change — `PROTOCOL v2.5` is unchanged.

### Added
- `new_project.py --wizard` — interactive walk-through that fills the
  `{{FILL}}` slots in a freshly stamped `BINDINGS.md`. Skipped automatically
  when stdin is not a TTY, so unattended stamps never block.
- `reviewer_poller.py --watch` — event-driven mode beside `--once`/`--loop`.
  A stdlib directory-signature check (no `watchdog` dependency) fires a review
  sweep once a channel change settles, cutting local review latency from a
  poll interval to a couple of seconds; a periodic fallback sweep still catches
  remote-pushed requests. Neither path reads a mid-write request.
- `tools/conformance_check.py` — a self-runnable, point-in-time workspace
  readiness check (the structural counterpart to the integrity CI): required
  files per profile, `PROTOCOL_VERSION`, profile/role-set agreement, an intact
  PROXY_AUTH guard, and a clean auth-log chain. BLOCKER vs WARN severities;
  `--strict` fails on unbound slots.
- `tools/validate_auth_log.py` — the auth-log chain validator is now a
  first-class file (previously only stamped into workspaces); `mirror_check.py`
  guards it byte-identical to the stamped copy.
- `tests/` — first committed test suite (stdlib `unittest`), pinning the
  `--watch` settle/fallback interleaving.

### Fixed / hardened
- Auth-log validator: a relayed CONSUMED must now follow the **complete**
  RECEIVED block (past its `source:` line), and relay + direct spends of the
  **same** grant are counted **together** against its scope — closing a latent
  double-spend (a `single` grant spent once by relay and once directly).
- `--watch`: a channel still being written is excluded from **both** the
  settle sweep and the periodic fallback sweep, so a half-written request is
  never read on either path.

## [1.0.0] — 2026-07-05

Initial public release: the local-transport distillation of a protocol
developed and hardened on live production work.

### Included
- `agent-protocol` plugin: `agent-core` shared normative references +
  three role skills (owner, builder, orchestrator).
- `/sleep` and `/wake <role>` session-lifecycle commands — the basis for
  unattended, cross-session **autonomy**.
- Self-improvement loop: the protocol amends itself through reviewed PRs to a
  human merge (`agent-core/references/self-improvement-protocol.md`), with
  principal-locked gates and `mirror_check.py` keeping the ruleset coherent.
- `tools/new_project.py` — stamps a dedicated agent workspace
  (`2agent.local` / `3agent.local` profiles), including the integrity CI
  workflow and the auth-log chain validator.
- `tools/mirror_check.py` — consistency CI over the skill tree.
- `tools/reviewer_poller.py` — optional bridge to a local Codex reviewer.
- `tools/wave_coverage_check.py` — coverage checker for builder read-waves.
- Documentation suite (incl. `docs/AUTONOMY.md` covering the two core
  platform properties) + a worked end-to-end example.

### Not included (deliberately — see README roadmap)
- The cloud transport (scheduled cold-successor wakes, integrity-gated
  automerge). Running upstream; platform surface still moving.
