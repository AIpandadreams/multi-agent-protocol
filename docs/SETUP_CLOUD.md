# Cloud deployment — simple instructions [PROTOCOL v2.5]

> **⚠ SUPERSEDED at v1.2.0 — retained for history, not for reuse.** The public
> repo's `docs/CLOUD.md` (github.com/AIpandadreams/multi-agent-protocol,
> PROTOCOL v2.6) is now the canonical cloud deployment recipe; its
> honest hosted-cloud caveats and the credential doctrine here were genericized
> and shipped there. The same two stale framings apply as in
> `transports/cloud-git.md`: the **dedicated "channel repo"** model is replaced
> by the **unified workspace repo**, and the **`git add -A`** stamping step is
> replaced by **explicit-path staging**. Mapping + resync ritual:
> `docs/SYNC_MANIFEST.md`.

From zero to a running cloud workspace (PA-only or full 3-agent). Local
deployment is the README "Use" section; this is the cloud path.

## 1. Stamp the workspace (on the PC)

```powershell
cd <workspace-root>\<private-repo>
python tools/new_project.py --name pa --dest <workspace-root>\<private-repo> --profile pa.cloud
# or --profile 3agent.cloud for owner+builder+orchestrator
```

Gives you: BINDINGS.md ({{FILL}} slots), channel/, memory/<role>/ (MEMORY.md,
auth-log.md; orchestrator also session-registry + cost-ledger), TASKQUEUE.md
(orchestrator), MODELS.md, start/ files, `.claude/settings.json` (auto-installs
the agent-protocol plugin + <principal>-tools at session start), and
`.github/workflows/integrity.yml` (auth-log append-only + secret scan CI).

## 2. Private repo + protections

```powershell
cd <workspace-root>\<private-repo>
git init -b main; git add -A; git commit -m "stamp: pa workspace"
gh repo create <private-repo> --private --source . --push
```

Then on GitHub (once): protect `main` — require PR for the CANONICAL work
repo(s) per the SIGNING binding. The workspace repo itself (channel/memory)
stays direct-push, but **REQUIRES force-push + deletion protection on its
default branch** — auth-record source-commit SHAs and the
consume-reservation ordering are only trustworthy over non-rewritten
history. On plans where rulesets/branch protection are unavailable for
private repos (free tier), the compensating control is the watchdog's
history-guard (`tools/watchdog.py` alerts when the previously seen remote
sha stops being an ancestor of HEAD) — record the limitation in BINDINGS
and upgrade the account before enabling irreversible/outward proxy gate
classes. The history-guard is DETECTION-ONLY, not equivalent protection:
its first run only records a baseline (run the watchdog once IMMEDIATELY
after creating the remote), and a rewrite pushed and reverted between two
polls is invisible to it. Partial mitigation, proven 2026-07-04: the cloud
container's git credential proxy BLOCKS ref deletion outright (creates/
updates only) — so CLOUD sessions cannot delete branches or rewrite refs
regardless of plan tier; the residual exposure is credentials used from
outside the cloud containers. The integrity CI enforces the auth-log rules
(append-only + no mixed-path auth commits + author identity in per-role
mode + the stamped `tools/validate_auth_log.py` chain check: duplicate
CONSUMED, CONSUMED-without-RECEIVED, relay/consume counts over scope) plus
channel append-only and CHANNEL_STATE monotonicity.

**AUTH_PROVENANCE** (proxy-auth-core §Provenance): if PROXY_AUTH will be on
and the gate classes include irreversible/outward actions, give each role
its own push identity (deploy key or machine account) and a ruleset
restricting `memory/<role>/**` to it, then bind `per-role-identity` AND
commit `.auth-provenance.json` mapping each role to its bound author email
(`{"orchestrator": "...", "owner": "...", "builder": "..."}`) — the
integrity CI then rejects any auth-log commit whose author is not the
bound identity, and rejects the map itself if two roles share an identity.
Commit-author email is a WEAK signal on its own (any pusher can set it) —
the hard layer is the per-role deploy key/machine account plus the ruleset
restricting `memory/<role>/**` to it; the CI email check is the tripwire,
the platform restriction is the wall. Signed commits per role harden it
further where available.
A single-account deployment binds `single-identity` with the principal's
acceptance recorded in BINDINGS — the CI compensating checks and briefing
visibility are mandatory, and high-harm classes should stay first-hand.

## 3. Fill BINDINGS.md

Every `{{FILL}}`: reviewer (poller + Claude fallback), heartbeat cadences,
PROXY_AUTH (off, or on + explicit gate-class list — principal-set only),
pinned resources, escalation matrix. Commit + push.

## 4. claude.ai/code session + scheduled routine

1. Open claude.ai/code → new session on `<private-repo>`.
   **Grant the Claude GitHub app access to BOTH the workspace repo AND
   `<private-repo>`** (the plugin marketplace source is private —
   without access the skills can't auto-install). Add
   `<private-repo>` too if the <principal>-tools plugins are enabled.
2. First message: "You are the orchestrator for this workspace. Follow
   start/START_SESSION.orchestrator.md." The settings.json installs the
   skills automatically.
3. Create the heartbeat: **a ROUTINE (claude.ai/code/routines) with the
   repos ATTACHED — this is the load-bearing part.** Attach the workspace
   repo + `<private-repo>` (the marketplace source; skills can't install
   without it). The platform clones every attached repo at run start with
   the account's GitHub credentials — no PAT, no setup script, no
   self-clone. Environment: Default; EMPTY setup script; blank env vars.
   Schedules are LOCAL time with automatic DST conversion (no UTC-cron
   shifting). One routine per duty (idle tick hourly; briefing/EOD daily).
   The prompt:
   "Wake as this workspace's orchestrator. FIRST verify the workspace is
   present (~/<name>-workspace/BINDINGS.md); if missing, push-notify
   'HEARTBEAT ABORT: routine has no workspace — attach the repo to the
   routine' and STOP — NEVER attempt to self-clone (fired sessions have no
   standalone git credential). Then follow
   start/START_SESSION.orchestrator.md, run one idle tick per the
   orchestration protocol, checkpoint memory, commit to a claude/ branch,
   push, and open a PR using the built-in GitHub tools (NOT `gh` — it is
   not pre-installed and would need a visible token); integrity CI +
   automerge lands it on main. Stop. A wake that cannot push cleanly says
   so — it never claims progress."
   ⛔ Do NOT create heartbeats as raw MCP / env-level scheduled triggers:
   they attach an environment + prompt but NO repository — fired sessions
   land in empty containers and can neither be provisioned (setup-script
   clones lack credentials too) nor self-bootstrap (proven 2026-07-04).
   Active windows get a denser second routine only while declared. Verify
   go-live ONLY by an actual fired-and-delivered run (routine id +
   session id + merged sha recorded). Housekeeping: cloud sessions CANNOT
   delete branches (the credential proxy blocks ref deletion) — the
   principal prunes merged/stale `claude/*` branches on github.com
   periodically.
4. Secrets (Gmail connector, anything keyed): session/connector settings
   ONLY — never in the repo; the CI secret-scan is the backstop.

## 5. Reviewer poller (on the PC)

```powershell
python <workspace-root>\<private-repo>\tools\reviewer_poller.py --workspace <workspace-root>\<private-repo> --loop --interval 300
# or a Windows scheduled task running --once every 5 min
```

Cloud sessions drop `review_request_<SIDE>_rNN.md` in channel/ and push; the
poller feeds them to local Codex and pushes `verdict_<SIDE>_rNN.md` back.
Poller down → agents use the bound different-model Claude fallback reviewer
(review-core dead-lane rule).

## 6. Go-live checks (Phase 4 exit)

- Cold-successor test: kill a session mid-unit; next tick resumes from repo
  state alone.
- Briefing arrives on schedule; a planted tripwire pages per the escalation
  matrix; a planted dummy key fails CI; an edited auth-log line fails CI.
- Reviewer round-trips: request pushed → verdict lands. Then stop the poller
  and confirm the fallback engages.
- Cost ledger accumulates and the auth-log stays clean for a week.
