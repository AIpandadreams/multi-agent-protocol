# THE MANUAL — <principal>'s multi-agent system, complete guide [PROTOCOL v2.5]

One document: what the system is, every variation (2.5/3-agent × local/cloud),
how to implement each, how to operate it daily, and where everything lives.
Deeper references are linked at the end; this file is the front door.

---

## 1. What this system is

A **four-party collaboration protocol** for running AI agents on real work
without losing control of authorization, history, or quality:

| party | who | job |
|---|---|---|
| **Principal** | <principal> | holds ALL gates. Authorization is only ever your word |
| **Orchestrator** | Claude session | your single interface: translates plain speech into dispatches, runs the queue, briefs you, relays approvals (when PROXY_AUTH is on) |
| **Workers** | owner + builder Claude sessions | owner = decision quality on the canonical repo; builder = execution-heavy work |
| **Reviewer** | Codex (different vendor) | independent adversarial review of every round; Claude-on-a-different-model as fallback |

Five load-bearing principles (everything else derives from these):
1. **Authorization never rides the channel.** Agents exchange bytes, never
   permission. Approvals travel only as auth-log events (see §5) or your
   first-hand word in a session.
2. **Everything persistent lives in git.** Any session can die at any moment;
   a cold successor rebuilds the entire picture from the repo alone.
3. **Append-only history.** Channel files and auth-logs only ever gain lines;
   CI enforces it.
4. **Independent review gates every round.** A different-vendor reviewer with
   a byte-exact fingerprint of the tree under review.
5. **Bindings over examples.** The skills define ROLES and PROTOCOL; each
   deployment binds specifics (paths, cadences, models) in its BINDINGS.md.

## 2. The repos

| repo | role |
|---|---|
| `<workspace-root>\<private-repo>` = <private-repo> (private) | **SOURCE OF TRUTH**: the plugin (role skills + agent-core), transports, profiles, tools, docs. You never run agents here — you stamp workspaces FROM here |
| `<workspace-root>\<private-repo>` = <private-repo> (private) | the CLOUD PA's live workspace (channel, memory, auth-logs, queue) |
| `<workspace-root>\<private-repo>` = <private-repo> (private) | the LOCAL PA's live workspace — same layout, local transport |
| per-project workspaces (stamped on demand) | one per real project; the work repo itself stays clean |
| work repos (e.g. <private-repo>) | canonical code/deliverables; agents touch them only under SIGNING rules |

A **workspace** always contains: `BINDINGS.md` (the deployment's contract),
`channel/` (inter-agent messages + review requests/verdicts), `memory/<role>/`
(each role's persistent memory + auth-log), `TASKQUEUE.md`, `MODELS.md`,
`start/` (instantiated START_SESSION per role), `tools/validate_auth_log.py`,
`.github/workflows/integrity.yml` (the integrity CI), `.claude/settings.json`
(auto-installs the skills at session start).

## 3. The variations — which one, when

Two axes: **2.5-agent vs 3-agent** and **local vs cloud** = 4 configurations,
all from the same skills. The difference is only which profile you stamp and
which BINDINGS you fill.

| config | what it means | use when |
|---|---|---|
| **2.5-agent local** | owner + builder only; the OWNER doubles as your interface (no orchestrator) | a single project where you're happy talking to the owner directly. This is how <private-repo> runs today |
| **3-agent local** | + orchestrator; you talk ONLY to it | you want the PA experience: one point of contact, approvals relayed, workers on demand. This is `<workspace-root>\<private-repo>` |
| **3-agent cloud** | same, but sessions are claude.ai/code cloud sessions; every wake is a cold successor; heartbeat = scheduled routines | always-on presence, phone access, scheduled briefings. This is `<private-repo>` |
| **2.5-agent cloud** | owner+builder in the cloud, no orchestrator | rarely the right choice; supported but not deployed |

**Stamp commands** (from `<workspace-root>\<private-repo>`):
```powershell
python tools/new_project.py --name <proj> --dest <dir> --profile 3agent.local
#  profiles: 2agent.local | 3agent.local | 2agent.cloud | 3agent.cloud | pa.cloud
```

Local vs cloud is a **transport**, not a rewrite — `transports/local-fs.md`
vs `transports/cloud-git.md` define how the same verbs (POLL, READ, APPEND,
PUBLISH, INTEGRITY) are performed:

| concern | LOCAL | CLOUD |
|---|---|---|
| message delivery | shared filesystem — instant | git pull/push; workers land state via `claude/*` branch → PR → **integrity-gated automerge** |
| push to workspace main | direct | IMPOSSIBLE for cloud sessions (branch→PR only) |
| heartbeat | Windows scheduled tasks | **routines with repos ATTACHED** (the ONLY working primitive — raw MCP/env triggers fire into empty containers; fired sessions cannot self-clone, they have no git credential) |
| signing | gpg-local or sign-on-merge | sign-on-merge / web-flow; agents never hold keys |
| branch cleanup | normal | cloud sessions CANNOT delete refs (proxy blocks it) — you prune on github.com |
| reviewer | Codex on this PC, direct | same Codex via the reviewer poller (channel-file round trip) |

## 4. Core machinery (what the moving parts do)

**BINDINGS.md** — the deployment contract. Every slot the skills reference
(CANONICAL_REPO, CHANNEL, REVIEWER, SIGNING, HEARTBEAT, PROXY_AUTH, EMBARGOES,
DUTIES, TICKS…) resolved to concrete values. Glossary:
`plugins/agent-protocol/skills/agent-core/references/binding-slots.md`.
Unfilled slot = the session stops and asks you once.

**Channel** — append-only files in `channel/`, one per direction per day
(`orch_to_builder_YYYY-MM-DD.md` etc.). Entries are numbered, ack the peer
entries seen, and carry a no-authorization disclaimer. `CHANNEL_STATE.json`
tracks each side's counters (CI: never backward, keys never removed).
Channel content is UNTRUSTED coordination data — an entry asking a session
to expand scope, skip a gate, or claiming "the principal said it's fine" is
ignored by rule.

**Review rounds** — side-prefixed files `review_request_<SIDE>_rNN.md` /
`verdict_<SIDE>_rNN.md` in the channel. Every request quotes a byte-exact
tree fingerprint (Bash `git diff ... | sha256sum` — never PowerShell); a
verdict whose fingerprint no longer matches authorizes nothing. Verdicts:
ADOPT / ADOPT-WITH-CHANGES / REJECT. The reviewer poller
(`tools/reviewer_poller.py`, scheduled every 5 min per workspace) carries
requests to local Codex and pushes verdicts back.

**Auth-log lane (PROXY_AUTH)** — how your approvals travel when you talk only
to the orchestrator. Your verbatim words are recorded as a GRANT in the
orchestrator's `memory/orchestrator/auth-log.md`; a relay to a worker is
RELAY-SENT → the worker verifies it in the committed log and records
RECEIVED (with source commit sha) → spends it with exactly ONE landed
CONSUMED (a pushed reservation — losing a push race means re-verify) → ACK.
`tools/validate_auth_log.py` + CI enforce the chain mechanically, globally
across all roles' logs. PROXY_AUTH is ON only for ENUMERATED gate classes
(your PA binds 6); wildcards are invalid by construction; outward / money /
destructive / email-send are FIRST-HAND ONLY, always; only you, speaking
directly into the orchestrator session, can change PROXY_AUTH itself.

**Memory discipline** — each role checkpoints `memory/<role>/MEMORY.md` with
a mandatory ⚡ working-state block (counters, in-flight work, pointers).
That block + the channel is the ENTIRE interface a cold successor needs —
proven by test: sessions killed mid-unit resume with zero gaps.

**Integrity CI** (`.github/workflows/integrity.yml`, stamped into every
workspace): auth-log append-only · single-subtree auth commits · per-role
author identity (if bound) · provenance-map uniqueness · auth-chain
validation · channel append-only · CHANNEL_STATE monotonic · secret scan ·
**automerge job** (cloud): merges `claude/*`→main state PRs only after
integrity passes, trust controls read from base main, PRs touching
workflows/tools/bindings/trust files refused (those need YOUR merge).

**MODELS.md** — live per-role model matrix. 5 presets (Maximum / Strong /
Balanced / Economy / Fast) + custom; switchable by one phrase to the
orchestrator; every change versioned in git.

**Watchdog** (`tools/watchdog.py`, scheduled hourly): alerts if a cloud
workspace goes silent past threshold; history-guard detects remote history
rewrites (detection-only compensating control on free-tier repos).

## 5. Implementation guides

### 5a. Start the LOCAL PA (already built — <workspace-root>\<private-repo>)
1. Open a Claude Code session in `<workspace-root>\<private-repo>`.
2. Say: **"You are the orchestrator for this workspace. Follow
   start/START_SESSION.orchestrator.md."**
3. Talk to it in plain speech. It queues, dispatches, briefs, and brings
   you approvals per the 6 bound gate classes. Workers spawn on demand —
   you never address them.
Reviewer poller task `<scheduled-task>` already runs every 5 min.
To add unattended ticks later: a Windows scheduled task per the HEARTBEAT
row in its BINDINGS (the orchestrator will draft it; you approve).

### 5b. Stand up a NEW local project (3-agent)
1. `python tools/new_project.py --name <proj> --dest <workspace-root>\<proj>-ws --profile 3agent.local`
2. Fill every `{{FILL}}` in BINDINGS.md (the orchestrator can draft; you
   confirm PROXY_AUTH + EMBARGOES yourself).
3. `git init -b main; git add -A; git commit; gh repo create <org>/<name> --private --source . --push`
4. Open the orchestrator session (as 5a). It wakes workers when tasks
   need them. 2.5-agent variant: stamp `2agent.local`, open the OWNER
   session instead — it is your interface.

### 5c. Stand up CLOUD (full recipe: docs/SETUP_CLOUD.md)
Condensed: stamp `pa.cloud`/`3agent.cloud` → private repo + protections
(force-push/deletion protection, or watchdog fallback on free tier) → fill
BINDINGS → claude.ai/code session on the repo (grant the GitHub app BOTH the
workspace AND <private-repo> repos) → heartbeat = **routines with the repos
ATTACHED** (Default env, EMPTY setup script, local-time schedules; never raw
MCP/env triggers — fired sessions land in empty containers and cannot
self-clone) → reviewer poller on the PC → go-live checks (cold-successor
test, tripwire tests, fired-and-delivered proof recorded in BINDINGS).

### 5d. Offer v2.5 to an EXISTING deployment (e.g. <private-repo>)
Running agents own their originals — adoption is THEIR choice, relayed via
you. On both decisions + your go: `python tools/adopt_v25_local.py`
(backs up originals, installs v2.5 role skills + agent-core into
~/.claude/skills).

## 6. Operating it day to day

- **You speak plain English to the orchestrator.** It echoes back its
  interpretation when your (voice) input is ambiguous, then dispatches.
- **Approvals**: it brings you a decision menu; your exact words get logged;
  irreversible/outward classes get echo-confirmed before relay.
- **Briefings**: morning (08:00) + EOD (18:00) per DUTIES; every grant you
  issued appears in the next briefing.
- **Model control**: "switch to Economy", "put the builder on Opus" — done
  and versioned.
- **Review cadence**: every unit of consequence gets a Codex round before
  it lands; you only see the outcome unless a verdict blocks.
- **Stopping**: close the session. State is in git; the next wake (or your
  next session) resumes from the ⚡ block. Nothing lives in a session.

## 7. Safety rails (fixed, not bindable away)

- First-hand only, forever: outward-facing actions, new-money/new-recipient,
  destructive actions on others' artifacts, email SENDING, canonical-repo
  merges, changes to PROXY_AUTH / ground rules / embargoes.
- Supabase: agents may touch ONLY the <private-repo> project
  (<project-id>). Every other project is forbidden.
- Secrets: env/connector settings only; never committed; CI secret-scan
  backstops.
- Agent-authored protocol changes ride PRs through Codex review to YOUR
  merge — no agent can amend its own gates.

## 8. Current deployments (2026-07-04)

| deployment | status |
|---|---|
| `<workspace-root>\<private-repo>` (3-agent local PA) | BUILT, awaiting your first orchestrator session |
| `<private-repo>` (3-agent cloud PA) | live state repo + working relay lane + automerge; heartbeat PENDING your routine creation (repos attached) + fired-and-delivered proof |
| <private-repo> (2.5 local) | running its original skills; v2.5 offer open (builder ADOPT, engine decision/input requested) |
| localpilot (validation) | synthetic Phase-5 cycle PASSED end-to-end; disposable |

## 9. Deeper references

- `docs/SETUP_CLOUD.md` — full cloud recipe
- `docs/REVIEW_REPORT.md` — the convergence review history
- `docs/AUTH_RECORD_DESIGN.md` — proxy-auth design in depth
- `docs/amendments/` — batch 1 (applied) + batch 2 (draft)
- `transports/local-fs.md` / `transports/cloud-git.md` — transport verbs
- `plugins/agent-protocol/skills/agent-core/references/` — channel-core,
  review-core, proxy-auth-core, memory-discipline, binding-slots
- role skills: `owner-engine-agent/`, `helper-builder-agent/`,
  `orchestrator-agent/` (each: SKILL.md + references)
- `profiles/MODELS.md` — model matrix + presets
- tools: `new_project.py` (stamp), `reviewer_poller.py`, `watchdog.py`,
  `validate_auth_log.py`, `wave_coverage_check.py`, `adopt_v25_local.py`,
  `mirror_check.py`
