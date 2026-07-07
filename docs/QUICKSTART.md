# Quickstart — zero to a running agent team

Everything below is runnable as written. Time budget: ~15 minutes, most of
it filling one file.

## Three repos, three jobs

The setup keeps **three separate repositories** — don't conflate them:

```
┌──────────────────────────┐   the SKILLS + TOOLS: the protocol itself.
│  multi-agent-protocol    │   You clone it once; new_project.py and the
│  (this repo — a checkout)│   trusted conformance_check.py live here.
└────────────┬─────────────┘
             │  stamps + (later) vets
             ▼
┌──────────────────────────┐   the WORKSPACE: per-project coordination
│  <project>-ws            │   STATE — BINDINGS, channel/, memory/<role>/,
│  (its own private repo)  │   TASKQUEUE, a stamped in-ws conformance copy.
└────────────┬─────────────┘   NOT your product code.
             │  agents work on
             ▼
┌──────────────────────────┐   the CANONICAL_REPO: the ACTUAL project the
│  your project's repo     │   agents build. The owner owns it; it is named
│  (the code being built)  │   in the workspace's BINDINGS, never stored in it.
└──────────────────────────┘
```

The workspace is deliberately its **own** repo, separate from the code repo, so
coordination history (who said what, which round, which grant) never mixes into
your product's git log.

## Prerequisites

- [Claude Code](https://claude.com/claude-code) (CLI or desktop).
- Python 3.10+.
- git, and (recommended) a private remote for the workspace repo.
- Optional but strongly recommended: a second-vendor CLI reviewer such as
  [Codex](https://github.com/openai/codex) — the protocol's review gate is
  its biggest quality lever. A different-model Claude session works as a
  fallback (see [ADVANCED.md](ADVANCED.md#the-reviewer)).

## 1. Install the plugin

Clone this repo — the clone is the **protocol checkout** (repo 1 above), where
`new_project.py` and the trusted `conformance_check.py` live. Then install the
skills **one way** — the two methods are alternatives, not both:

- **Plugin marketplace (recommended)** — Claude keeps it updated, and every
  stamped workspace's `.claude/settings.json` re-installs it at session start,
  so teammates you open in a workspace get it automatically:

  ```
  /plugin marketplace add AIpandadreams/multi-agent-protocol
  /plugin install agent-protocol@multi-agent-protocol
  ```

- **Manual copy (no marketplace)** — a user-level install you update yourself:

  ```bash
  cp -r plugins/agent-protocol/skills/* ~/.claude/skills/
  cp plugins/agent-protocol/commands/*.md ~/.claude/commands/
  ```

  If you go manual, note that the stamped `settings.json` still lists the
  marketplace plugin; either ignore that (your `~/.claude` copy wins) or drop
  the `enabledPlugins` entry from the workspace's `.claude/settings.json`.

## 2. Stamp a workspace

The workspace is a dedicated directory (its own repo — NOT inside your
project's code repo) holding everything persistent: bindings, the channel,
each role's memory, the task queue.

```bash
python tools/new_project.py --name myproject --dest path/to/myproject-ws \
    --profile 3agent.local --principal "Your Name"
```

Profiles: `3agent.local` (orchestrator + owner + builder — the default; you
talk only to the orchestrator) or `2agent.local` (compact: dual-role owner —
the owner absorbs the orchestrator duties and you talk to it directly).
Choosing: [CONFIGURATIONS.md](CONFIGURATIONS.md).

Prefer to be walked through it? Add `--wizard` for an interactive **pre-stamp**
walkthrough — topology (roles + local/git-sync transport) → side names →
principal → project repo → reviewer (it probes your PATH for a CLI) → git-init →
plugin-install — and it renders the resolved `BINDINGS.md` in one pass:

```bash
python tools/new_project.py --name myproject --dest path/to/myproject-ws --wizard
```

Type `defer` on any slot to record it as `{{DEFERRED}}` (a *deliberately
postponed* marker, distinct from an untouched `{{FILL}}`). Add `--git-init` to
make the workspace a git repo immediately (non-fatal — if git or an identity is
missing it just tells you), and `--plugin-install` to print the install steps
again at the end. After stamping, the tool prints a **NEXT STEPS** block with
exactly what to do next. `--no-orchestrator` is a deprecated alias for
`--profile 2agent.local`.

## 3. Fill BINDINGS.md

Open `BINDINGS.md` in the stamped workspace (with any `--wizard` answers
already applied — Enter-skipped slots still show `{{FILL}}`). Every `{{FILL}}`
slot is a deployment decision; the glossary lives
at `plugins/agent-protocol/skills/agent-core/references/binding-slots.md`.
The three that matter most on day one:

| slot | what to put |
|---|---|
| `CANONICAL_REPO` | the path + remote + branch of the ACTUAL project the agents will work on |
| `REVIEWER` | who reviews each side's work — e.g. `codex CLI via tools/reviewer_poller.py, model default` or `claude session on a different model` |
| `EMBARGOES / GATES` | anything the agents must always bring to you first (deploys, emails, spending, deletions…) |

Leave `PROXY_AUTH` **off** (the default). It's an advanced feature
([ADVANCED.md](ADVANCED.md#proxy_auth--the-auth-log-lane)) and nothing
requires it: with it off, you simply give approvals in whichever session
asks for them.

Then make the workspace a repo — **unless you already did**: `--git-init` (or
answering "yes" to the wizard's git-init question) has already run this, so skip
to pushing a remote. Otherwise:

```bash
cd path/to/myproject-ws
git init -b main && git add -A && git commit -m "stamp myproject workspace"
# recommended: push to a private remote so history is protected
```

## 4. Wake your first agent

Open a Claude Code session **in the workspace directory** and type:

```
/wake orchestrator        (3-agent profile)
/wake owner               (2-agent profile)
```

The session binds itself to BINDINGS.md, verifies workspace integrity,
reads its memory, and reports its resume point. First session on a fresh
stamp: it will ask you to confirm any bindings you left unfilled — answer
once, it records them.

From here you talk in plain language. The orchestrator queues tasks,
dispatches workers (it will tell you when it needs a worker session opened,
or spawn subagents where your setup allows), and brings you decisions.

A first exchange looks like this:

```
you:  We're modernizing the billing service. First job: audit the retry
      logic in src/payments and propose a fix plan — don't change code yet.
orch: Queued as T4 and dispatched to the owner (billing repo). It will draft
      a plan, the builder will pressure-test it, and the reviewer gates it
      before anything lands. I'll bring you the plan to approve. Anything
      off-limits I should record as an embargo (e.g. touching prod config)?
you:  Yes — no schema migrations without asking me.
orch: Recorded as a gate. Starting the audit now.
```

Nothing there granted the agents permission to *do* anything irreversible —
approvals stay with you, in whichever session asks.

## 5. End a session

```
/sleep
```

The agent checkpoints its memory (with an exact `## Next Step`), commits
and pushes its state, prints a change log, and tells you it's safe to close
the window. Next time, `/wake <role>` resumes exactly there — no context
pasting, no recap.

## What you get per workspace

```
myproject-ws/
  BINDINGS.md          the deployment contract (you own this file)
  TASKQUEUE.md         orchestrator's queue (3-agent)
  MODELS.md            model matrix — switch presets by telling the orchestrator
  channel/             append-only inter-agent messages + review rounds;
                       INDEX.md is the shared review-round ledger
  memory/<role>/       each role's persistent memory + auth-log
  start/               per-role START_SESSION contracts (what /wake runs)
  tools/validate_auth_log.py   auth-chain validator (CI + local)
  .github/workflows/integrity.yml   append-only + provenance + secret-scan CI
  .claude/settings.json             installs the plugin at session start
```

## Check your workspace is sound

Any time after stamping — and especially after filling `BINDINGS.md` — run
the conformance check to confirm the deployment is structurally sound before
waking an agent. Run it **from your protocol checkout** (where you cloned this
repo — the checker lives there, not inside the workspace) and point
`--workspace` at the workspace:

```bash
cd path/to/multi-agent-protocol   # your clone of this repo
python tools/conformance_check.py --workspace path/to/myproject-ws
```

A fresh stamp passes with `WARN`s for the slots you haven't filled yet (and a
distinct WARN for any `{{DEFERRED}}` you postponed); once every slot is
resolved, `--strict` should come back clean. A **BLOCKER** — a missing file, an
unsupported protocol pin, a weakened PROXY_AUTH guard, a broken auth-log chain,
or two roles colliding on one identity — means the deployment is unsound; fix it
before waking.

The stamp also drops a **copy of the checker inside the workspace**
(`<ws>/tools/conformance_check.py`). Running that copy prints a `SELF-CHECK
MODE` banner: it is workspace-owned code, so it's a **hygiene** check (which
`/wake` runs automatically as a pre-wake gate), not a trust gate. To *vet an
unfamiliar workspace someone handed you*, run the **protocol checkout's** copy
against it, as above — never the workspace's own. Details:
[ADVANCED.md](ADVANCED.md#conformance-suite--is-this-workspace-sound).

## Troubleshooting

- **`/wake` says a binding is unfilled** — answer it once in-session; the
  agent records it in BINDINGS.md and won't ask again.
- **Review requests pile up unanswered** — your REVIEWER binding isn't
  live. Run `python tools/reviewer_poller.py --workspace <ws> --once` to
  bridge to a local Codex, or bind the different-model fallback.
- **Two agents wrote to the same file** — they shouldn't: each role owns
  its own memory and its own outbound channel files. If it happens, the
  integrity CI flags it; see [PROTOCOL.md](PROTOCOL.md#the-channel).
