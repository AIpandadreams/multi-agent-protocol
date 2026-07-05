# Changelog

All notable changes to this repository are documented here. The repo
follows [SemVer](https://semver.org) for its own releases; the protocol the
skills implement carries its own version stamp (`PROTOCOL vX.Y`), which
changes only through the
[self-improvement protocol](plugins/agent-protocol/skills/agent-core/references/self-improvement-protocol.md).

| repo release | protocol version | notes |
|---|---|---|
| 1.0.0 | v2.5 | first public release |

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
