# Changelog

All notable changes to this repository are documented here. The repo
follows [SemVer](https://semver.org) for its own releases; the protocol the
skills implement carries its own version stamp (`PROTOCOL vX.Y`), which
changes only through the
[self-improvement protocol](plugins/agent-protocol/skills/agent-core/references/self-improvement-protocol.md).

| repo release | protocol version | notes |
|---|---|---|
| 1.1.0 | v2.5 | tooling: `--wizard`, `--watch`, conformance suite |
| 1.0.0 | v2.5 | first public release |

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
