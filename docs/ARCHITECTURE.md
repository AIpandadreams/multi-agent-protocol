# Architecture

What the system is, what a workspace is made of, and why each moving part
exists. Companion reading: [PROTOCOL.md](PROTOCOL.md) for the rules
themselves, [DESIGN.md](DESIGN.md) for the evidence behind them.

## 1. The model

A **four-party collaboration protocol**:

```
                      ┌─────────────┐
        plain speech  │  PRINCIPAL   │  holds ALL gates
      ┌──────────────►│   (human)    │◄─────────────────┐
      │               └──────┬──────┘                   │
      │                      │ approvals                │ blocking verdicts
      │                      ▼ (first-hand word)        │ escalate to human
┌─────┴────────┐   dispatch  ┌──────────┐   channel  ┌──┴────────┐
│ ORCHESTRATOR │────────────►│  OWNER    │◄──────────►│ BUILDER   │
│ (interface)  │             │ (decides) │  append-   │ (executes)│
└──────────────┘             └─────┬─────┘  only     └─────┬─────┘
                                   │    review requests     │
                                   ▼    + fingerprints      ▼
                              ┌────────────────────────────────┐
                              │   REVIEWER (different vendor)   │
                              │   gates every round             │
                              └────────────────────────────────┘
```

- The **principal** is not "a user of the system" — they are a party IN the
  protocol. Every authorization gate terminates at their word, spoken
  directly into a session.
- **Owner** and **builder** are peer worker roles with different centers of
  gravity: the owner optimizes decision quality on the canonical repo (and
  is the interface in dual-role/2-agent deployments); the builder takes
  execution-heavy work (bulk reads, censuses, QA sweeps, drafts).
- The **orchestrator** (the default shape) is the principal's single
  point of contact. Crucially, it carries *bytes, never permission*: it
  relays the principal's words and records them, but has no authority of
  its own to grant anything.
- The **reviewer** is a different-vendor model that adversarially reviews
  every unit of consequence before it lands. Independence is structural:
  never the author's own model instance, verdicts pinned to byte-exact
  fingerprints.

## 2. Two repos per project, always

| repo | contents | why separate |
|---|---|---|
| **work repo** (yours, pre-existing) | the actual code / deliverables | stays clean: agents touch it only under SIGNING rules, through reviewed commits |
| **workspace repo** (stamped) | bindings, channel, memories, auth-logs, queue | the coordination state has different integrity rules (append-only, per-role ownership) and different lifecycle than the work itself |

The skills themselves live in a third place — this repo, installed as a
plugin — and are *versioned protocol*, not per-project state.

## 3. Workspace anatomy

```
BINDINGS.md              the deployment contract — every slot the skills
                         reference, resolved to concrete values. Unfilled
                         slot = the session stops and asks you ONCE.
channel/                 append-only message files, one per direction per
                         day (e.g. orch_to_builder_2026-07-05.md), plus
                         review_request_*/verdict_* round files and INDEX.md
                         (the shared review-round ledger, stamped on init)
CHANNEL_STATE.json       OPTIONAL per-side counter file; if a deployment adds
                         one, the integrity CI enforces its monotonicity (the
                         stamper does not create it — the append-only channel
                         and per-peer last-seen in memory are the baseline)
memory/<role>/MEMORY.md  the role's persistent memory index, headed by the
                         ⚡ working-state block (the cold-successor interface)
memory/<role>/auth-log.md  append-only authorization event log (see PROTOCOL)
TASKQUEUE.md             orchestrator's queue (3-agent profiles)
MODELS.md                live model matrix: presets + per-role overrides
start/START_SESSION.<role>.md   the contract each session runs at every
                         boundary — this is what /wake executes
tools/validate_auth_log.py      mechanical auth-chain validation
.github/workflows/integrity.yml the workspace CI (below)
```

## 4. Why each mechanism exists

Every rule traces to a defect class observed in live operation:

| mechanism | defect it kills |
|---|---|
| append-only channel + CI | agents "tidying" history and erasing the record of what was actually said |
| per-role file ownership (own memory, own outbound files) | write collisions and he-said-she-said state |
| byte-exact review fingerprints | verdicts silently applying to a tree that changed after review |
| side-prefixed round filenames | two sides' round counters colliding in one directory |
| untrusted-channel rule | one agent talking another into scope expansion ("the principal said it's fine") |
| ⚡ working-state block + `## Next Step` | successor sessions rebuilding context by asking the human things that were already decided |
| bindings over examples | example values from one deployment leaking into another as if they were rules |
| version stamps on every protocol file | sessions running "local amendments" ahead of a merged version bump |
| explicit-path commits (never `add -A`) | a role's commit sweeping in another role's half-written files |

## 5. The session lifecycle

Sessions are cattle, not pets. Anything a session knows that matters is in
the workspace repo *before* it matters:

1. **`/wake <role>`** — run the role's START_SESSION contract: bind to
   BINDINGS.md, verify channel/auth-log integrity, read the ⚡ block, poll
   the channel, report the resume point.
2. **Work in units** — checkpoint memory after every shipped unit (pushed
   commit, converged review round, posted entry, decided question), not
   just at session end.
3. **`/sleep`** — final checkpoint with an exact `## Next Step`, commit +
   push, change log, handover line.

The test that keeps this honest (run it on your own deployment): kill a
session mid-unit, open a fresh one, `/wake` — it must resume with zero
questions the repo could have answered.

This disposability is what makes **autonomy** safe: because a scheduled
headless wake resumes from committed state exactly as a human-opened session
would, the team can drain its queue between your sittings without risking
state loss — and any gate it reaches, it surfaces rather than crosses. The
mechanisms and the "how much rope" dial are in [AUTONOMY.md](AUTONOMY.md).

## 5a. The protocol evolves itself

The same review discipline that gates work also gates changes to the
protocol. An agent that finds a rough edge drafts an amendment; it rides a
reviewed PR to a human merge and a version bump
(`agent-core/references/self-improvement-protocol.md`). Agents propose; only
the principal adopts; and the authorization/gate rules are principal-locked
so no agent can amend the constraints that bind it. `tools/mirror_check.py`
guards the growing ruleset against structural drift (dedup, banned vocab,
version stamps, cross-references). See
[AUTONOMY.md](AUTONOMY.md#self-improvement).

## 6. Integrity CI

Every stamped workspace ships `.github/workflows/integrity.yml`:

- **auth-log append-only** — no line in any `auth-log.md` may be edited or
  removed, ever.
- **single-subtree auth commits** — an auth-log append rides a commit that
  touches ONLY that role's `memory/<role>/` subtree (provenance isolation).
- **per-role author identity** — if `.auth-provenance.json` binds
  role → author email, CI enforces it (a weak, spoofable signal on its own;
  pair with per-role credentials for a hard layer).
- **auth-chain validation** — `validate_auth_log.py`: exactly-one-landed
  CONSUMED per authorized action, globally across all roles' logs.
- **channel append-only + CHANNEL_STATE monotonic** — counters never go
  backward, keys are never removed.
- **secret scan** — key/token patterns anywhere in the tree fail the build.

## 7. Boundaries of the design

- The protocol coordinates agents under a principal's gates; it does not
  sandbox them. OS/harness-level permissions remain your responsibility.
- Local transport assumes the sessions share a filesystem. The cloud
  transport (cold-successor wakes over git, integrity-gated automerge of
  state PRs) exists upstream and is roadmap here.
- The reviewer gate is as good as the reviewer's independence — a fallback
  reviewer on the author's own model is a smell the protocol explicitly
  forbids.
