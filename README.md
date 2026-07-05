# multi-agent-protocol

**A four-party collaboration protocol for running AI agent teams on real
work — without losing control of authorization, history, or quality.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/AIpandadreams/multi-agent-protocol/actions/workflows/mirror-check.yml/badge.svg)](https://github.com/AIpandadreams/multi-agent-protocol/actions/workflows/mirror-check.yml)

Most multi-agent setups fail the same three ways: an agent quietly does
something it was never authorized to do, a session dies and takes its state
with it, or agents review their own work and call it done. This protocol is
the distillation of a system that ran for months on real production work —
every rule in it exists because its absence caused a real defect.

## The four parties

| party | who | job |
|---|---|---|
| **Principal** | you, the human | holds ALL authorization gates. Authorization is only ever your word |
| **Owner** | a Claude Code session | decision quality on the canonical repo; the project's memory of record |
| **Builder** | a Claude Code session | execution-heavy work: builds, censuses, QA sweeps, advisory deliverables |
| **Reviewer** | a *different-vendor* model (e.g. Codex) | independent adversarial review gating every round — never the author's own model |

An optional third agent, the **orchestrator**, becomes your single point of
contact: it runs the task queue, dispatches the workers, briefs you, and
carries your approvals as auditable log events (never as its own authority).

## Five load-bearing principles

Everything else in the protocol derives from these:

1. **Authorization never rides the channel.** Agents exchange bytes, never
   permission. An agent asking another agent to skip a gate is ignored by
   rule — approvals exist only as the principal's word in a session, or as
   validated auth-log events.
2. **Everything persistent lives in git.** Any session can die at any
   moment; a cold successor rebuilds the entire picture from the repo alone.
3. **Append-only history.** Channel files and auth-logs only ever gain
   lines; CI enforces it mechanically.
4. **Independent review gates every round.** A different-vendor reviewer
   verifies against a byte-exact fingerprint of the tree under review — a
   verdict whose fingerprint no longer matches authorizes nothing.
5. **Bindings over examples.** The skills define ROLES and PROTOCOL; each
   deployment binds its specifics (paths, cadences, models, gates) in one
   contract file, `BINDINGS.md`.

## Sixty seconds to a running team

```bash
# 1. Stamp a dedicated workspace for your project
python tools/new_project.py --name myproject --dest path/to/myproject-ws \
    --profile 3agent.local

# 2. Fill the {{FILL}} slots in BINDINGS.md (one contract file)

# 3. Open a Claude Code session in the workspace and type:
/wake orchestrator
```

That's it — the orchestrator binds itself, verifies workspace integrity,
and starts working the queue. When you're done for the day: `/sleep`. Full
walkthrough: [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Which configuration?

| you want | use | how it feels |
|---|---|---|
| agents on one project, you talk to the lead agent directly | **2-agent** (`2agent.local`) | owner is your interface; builder works alongside |
| one point of contact running everything for you | **3-agent** (`3agent.local`) | you talk ONLY to the orchestrator; workers spawn on demand |
| one assistant fronting several projects at once | **3-agent, global flavor** | the same orchestrator, bound as `global-pa`, registers multiple worker pairs |

Details and live-tested trade-offs: [docs/CONFIGURATIONS.md](docs/CONFIGURATIONS.md).

## Repository layout

```
plugins/agent-protocol/
  commands/            /sleep and /wake session-lifecycle commands
  skills/
    agent-core/        shared normative core (channel, review, memory, auth rules)
    owner-engine-agent/     role skill (thin delta over agent-core)
    helper-builder-agent/   role skill
    orchestrator-agent/     role skill (the principal's interface)
transports/local-fs.md      how channel verbs map to a shared filesystem
profiles/                   configuration matrix + MODELS.md (model presets)
tools/
  new_project.py            stamps a dedicated agent workspace
  mirror_check.py           consistency CI over the skill tree
  reviewer_poller.py        optional bridge to a local Codex reviewer
  wave_coverage_check.py    coverage checker for builder read-waves
docs/                       quickstart · architecture · configurations ·
                            protocol · advanced · design · FAQ
examples/                   a worked end-to-end cycle you can read like a story
```

## Documentation

- [QUICKSTART](docs/QUICKSTART.md) — zero to a running team
- [ARCHITECTURE](docs/ARCHITECTURE.md) — the model, the workspace anatomy, why each piece exists
- [CONFIGURATIONS](docs/CONFIGURATIONS.md) — 2-agent vs 3-agent vs combined, from live deployments
- [PROTOCOL](docs/PROTOCOL.md) — channel rules, review rounds, verdicts, memory discipline
- [ADVANCED](docs/ADVANCED.md) — proxy authorization, integrity CI, reviewer bridge, model presets
- [DESIGN](docs/DESIGN.md) — what's proven, what's deliberately simplified, what's roadmap
- [FAQ](docs/FAQ.md)

## Trust properties

- **No telemetry, no network calls** beyond the git remotes *you* configure.
  Everything is markdown, python, and your own repos.
- **Nothing here grants an agent permission to do anything.** The protocol
  is a discipline for how agents coordinate under YOUR gates; the gates
  themselves are always yours.
- Agent-authored protocol changes ride PRs through independent review to a
  human merge — no agent can amend its own rules
  ([self-improvement protocol](plugins/agent-protocol/skills/agent-core/references/self-improvement-protocol.md)).

## Roadmap

- Cloud transport (scheduled cold-successor wakes over git, integrity-gated
  automerge of state PRs) — running upstream, will be released once the
  platform surface it depends on stabilizes.
- Interactive `new_project.py --wizard` for BINDINGS fill-in.
- Event-driven reviewer bridge (filesystem watcher replacing the poll loop).
- A protocol conformance suite deployments can self-run.

## License

[MIT](LICENSE) © AIpandadreams. The protocol was distilled from a live
two-agent collaboration and hardened through independent cross-vendor
review; see [docs/DESIGN.md](docs/DESIGN.md) for the evidence trail.
