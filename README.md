# multi-agent-protocol

**A four-party collaboration protocol for running AI agent teams on real
work — without losing control of authorization, history, or quality.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/AIpandadreams/multi-agent-protocol/actions/workflows/mirror-check.yml/badge.svg)](https://github.com/AIpandadreams/multi-agent-protocol/actions/workflows/mirror-check.yml)
[![Release](https://img.shields.io/github/v/release/AIpandadreams/multi-agent-protocol?sort=semver)](https://github.com/AIpandadreams/multi-agent-protocol/releases)
[![Protocol](https://img.shields.io/badge/protocol-v2.6-informational)](docs/PROTOCOL.md)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A2BE2)](docs/QUICKSTART.md#1-install-the-plugin)
[![No telemetry](https://img.shields.io/badge/telemetry-none-brightgreen)](#trust-properties)

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

The default shape runs all three agents. The **orchestrator** is your
single point of contact: it runs the task queue,
dispatches the workers, briefs you, and carries your approvals as auditable
log events (never as its own authority). Prefer a more compact setup? Run
the **dual-role owner** variant, where the owner absorbs the orchestrator's
interface and intake duties. Either way the orchestrator is an *interface*
role — it carries bytes, never permission — not a fifth authority party.

## Two properties that make it a platform, not a script

- **Autonomy.** Sessions are disposable. Everything a session knows lives in
  git before it matters, so the team keeps working *between* your sittings:
  `/sleep` checkpoints and hands off, `/wake` resumes cold with zero context
  pasting, scheduled ticks drain the queue unattended, and the orchestrator
  runs its standing duties (briefings, queue triage) on a cadence you set.
  You give direction and hold the gates; the agents carry the work forward on
  their own between those touchpoints. See [AUTONOMY.md](docs/AUTONOMY.md).
- **Self-improvement.** The protocol can amend *itself* — through its own
  review discipline. An agent that hits a rough edge proposes an amendment;
  it goes through an independent review round and a version bump, and **you**
  merge it. The system that runs the work also evolves the rules of the work,
  and no agent can quietly rewrite its own gates. The repo eats its own
  dogfood ([self-improvement protocol](plugins/agent-protocol/skills/agent-core/references/self-improvement-protocol.md)).

## Seven load-bearing principles

Everything else in the protocol derives from these:

1. **Authorization never rides the channel.** Agents exchange bytes, never
   permission. An agent asking another agent to skip a gate is ignored by
   rule — approvals exist only as the principal's word in a session, or as
   validated auth-log events for reversible, internal gate classes the
   principal enumerated. The irreversible/outward super-classes
   (outward-facing/publish actions, email SEND, new-money/new-recipient
   financial actions, destructive operations on another party's artifacts,
   canonical-repo merges, and changes to PROXY_AUTH / gates / embargoes / the
   protocol) are first-hand-only, always — never relayable.
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
6. **The team runs itself between your touchpoints.** Sessions are cattle,
   not pets; continuity is the ⚡ working-state block in git, not a live
   context window. This is what makes unattended operation safe rather than
   hopeful.
7. **The protocol improves under its own discipline.** Rule changes ride the
   same reviewed-PR-to-human-merge loop as any other work — agents can
   propose, only the principal can adopt.

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
| one point of contact running everything for you | **3-agent** (`3agent.local`) **(default)** | you talk ONLY to the orchestrator; workers spawn on demand |
| one assistant fronting several projects at once | **3-agent, global flavor** | the same orchestrator, bound as `global-pa`, registers multiple worker pairs |
| agents on one project, you talk to the lead agent directly | **2-agent** (`2agent.local`) | the owner runs dual-role as your interface; builder works alongside |

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
  conformance_check.py      point-in-time workspace readiness check
  validate_auth_log.py      auth-log chain validator (also stamped per workspace)
  watcher.py                generic multi-lane channel watcher (reports only)
  scale_workspace.py        upgrade a 2-agent workspace to 3-agent
  adopt_project.py          adopt an ad-hoc collaboration into a workspace
  migrate_workspace.py      migrate a stamped v2.5 workspace up to PROTOCOL v2.6
docs/                       quickstart · architecture · configurations ·
                            protocol · advanced · design · FAQ
examples/                   a worked end-to-end cycle you can read like a story
```

## Documentation

**Reading order.** New here? Read in this order: **QUICKSTART** (stand one up) →
**ARCHITECTURE** (what the pieces are) → **CONFIGURATIONS** (pick 2- vs 3-agent)
→ **PROTOCOL** (the rules the agents follow). Then, as you need them:
**AUTONOMY** and **ADVANCED** for unattended operation + proxy-auth, **CLOUD**
for peers on separate machines, **MIGRATION**/**FEDERATION** for scaling, and
**DESIGN**/**REVIEW_CONVERGENCE** for the evidence trail. **FAQ** anytime.

- [QUICKSTART](docs/QUICKSTART.md) — zero to a running team
- [ARCHITECTURE](docs/ARCHITECTURE.md) — the model, the workspace anatomy, why each piece exists
- [AUTONOMY](docs/AUTONOMY.md) — unattended operation + self-improvement, the two core platform properties
- [CONFIGURATIONS](docs/CONFIGURATIONS.md) — 2-agent vs 3-agent vs combined, from live deployments
- [MIGRATION](docs/MIGRATION.md) — moving a live channel's lanes safely (the stayed-lane rule)
- [FEDERATION](docs/FEDERATION.md) — many separate teams under one principal, isolated by construction
- [PROTOCOL](docs/PROTOCOL.md) — channel rules, review rounds, verdicts, memory discipline
- [ADVANCED](docs/ADVANCED.md) — proxy authorization, integrity CI, reviewer bridge, model presets
- [CLOUD](docs/CLOUD.md) — running peers on separate machines over a git remote (the git-sync transport)
- [DESIGN](docs/DESIGN.md) — what's proven, what's deliberately simplified, what's roadmap
- [REVIEW_CONVERGENCE](docs/REVIEW_CONVERGENCE.md) — the independent-review evidence trail behind this release
- [CREATOR-SEAT-BOOTSTRAP](docs/CREATOR-SEAT-BOOTSTRAP.md) — a single-file handoff that turns a fresh Claude session into a protocol creator: design interview, SOP catalog, runbook library, incident case studies
- [SOP-REGISTRY](docs/SOP-REGISTRY.md) — principal-ruled standing orders over the protocol, and the cross-team registry pattern
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

## Cloud / distributed peers

- Running peers on **separate machines** (or a live session plus a scheduled
  cloud twin) over a git remote is a **shipped transport** — the `git-sync`
  profiles (`2agent.git-sync` / `3agent.git-sync`) bind it. See the
  [git-sync transport profile](transports/git-sync.md) and
  [docs/CLOUD.md](docs/CLOUD.md), which is deliberately honest about the
  hosted-cloud host class and the platform surface its automerge recipe leans
  on.

## License

[MIT](LICENSE) © AIpandadreams. The protocol was distilled from a live
two-agent collaboration and hardened through independent cross-vendor
review; see [docs/DESIGN.md](docs/DESIGN.md) for the evidence trail.
