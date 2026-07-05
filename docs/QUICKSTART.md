# Quickstart — zero to a running agent team

Everything below is runnable as written. Time budget: ~15 minutes, most of
it filling one file.

## Prerequisites

- [Claude Code](https://claude.com/claude-code) (CLI or desktop).
- Python 3.10+.
- git, and (recommended) a private remote for the workspace repo.
- Optional but strongly recommended: a second-vendor CLI reviewer such as
  [Codex](https://github.com/openai/codex) — the protocol's review gate is
  its biggest quality lever. A different-model Claude session works as a
  fallback (see [ADVANCED.md](ADVANCED.md#the-reviewer)).

## 1. Install the plugin

Clone this repo, then either add it as a plugin marketplace:

```
/plugin marketplace add AIpandadreams/multi-agent-protocol
/plugin install agent-protocol@multi-agent-protocol
```

or symlink/copy the skills for a user-level install:

```bash
cp -r plugins/agent-protocol/skills/* ~/.claude/skills/
cp plugins/agent-protocol/commands/*.md ~/.claude/commands/
```

## 2. Stamp a workspace

The workspace is a dedicated directory (its own repo — NOT inside your
project's code repo) holding everything persistent: bindings, the channel,
each role's memory, the task queue.

```bash
python tools/new_project.py --name myproject --dest path/to/myproject-ws \
    --profile 3agent.local --principal "Your Name"
```

Profiles: `3agent.local` (orchestrator + owner + builder — you talk only to
the orchestrator) or `2agent.local` (owner + builder — you talk to the owner
directly). Choosing: [CONFIGURATIONS.md](CONFIGURATIONS.md).

## 3. Fill BINDINGS.md

Open `BINDINGS.md` in the stamped workspace. Every `{{FILL}}` slot is a
deployment decision; the glossary lives at
`plugins/agent-protocol/skills/agent-core/references/binding-slots.md`.
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

Then make the workspace a repo:

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
  channel/             append-only inter-agent messages + review rounds
  memory/<role>/       each role's persistent memory + auth-log
  start/               per-role START_SESSION contracts (what /wake runs)
  tools/validate_auth_log.py   auth-chain validator (CI + local)
  .github/workflows/integrity.yml   append-only + provenance + secret-scan CI
  .claude/settings.json             installs the plugin at session start
```

## Troubleshooting

- **`/wake` says a binding is unfilled** — answer it once in-session; the
  agent records it in BINDINGS.md and won't ask again.
- **Review requests pile up unanswered** — your REVIEWER binding isn't
  live. Run `python tools/reviewer_poller.py --workspace <ws> --once` to
  bridge to a local Codex, or bind the different-model fallback.
- **Two agents wrote to the same file** — they shouldn't: each role owns
  its own memory and its own outbound channel files. If it happens, the
  integrity CI flags it; see [PROTOCOL.md](PROTOCOL.md#the-channel).
