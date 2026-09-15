# Transport profile: cloud-git [PROTOCOL v2.5]

> **⚠ SUPERSEDED at v1.2.0 — retained for history, not for reuse.** The public
> repo's `transports/git-sync.md` (github.com/AIpandadreams/multi-agent-protocol,
> PROTOCOL v2.6) is now canonical for the cloud / distributed-peer transport.
> This file's **credential doctrine** (a fired/headless session NEVER
> self-clones — the scheduler must deliver a provisioned checkout, and a missing
> workspace aborts loudly) and its **self-managed vs hosted-cloud host-class**
> split were genericized and shipped there. Two framings below are explicitly
> superseded and must NOT be carried forward:
> - the **dedicated per-project "channel repo"** model (the "dedicated private
>   channel repo" line) → replaced by the **unified workspace repo** (channel +
>   memory + bindings + tasks in one repo).
> - the PUBLISH verb's **`git add -A`** → replaced by **explicit-path staging**
>   (stage only your own disjoint-owned files; `git add -A` on a shared
>   workspace can sweep a peer's un-integrated bytes into your commit, which
>   sleep.md's explicit-path rule forbids).
>
> Kept because it holds production-proven platform facts the public
> genericization compressed (the credential-proxy ref-deletion block; the
> routine-with-repos-attached scheduling primitive). Mapping + resync ritual:
> `docs/SYNC_MANIFEST.md`.

For agents running as claude.ai/code cloud sessions / scheduled routines.
**Load-bearing fact: there is no long-lived session.** Every scheduled wake is
a COLD successor: fresh clone, zero context. Anything persistent lives in git.
The START_SESSION contract is the architecture.

The channel is a dedicated private **channel repo** (per project instance);
each agent's memory lives in it too (`memory/<role>/`).

| verb | implementation |
|---|---|
| POLL | `git fetch && git pull --rebase --autostash` the channel repo at wake + before every decision that depends on peer state. Cadence = heartbeat period (no continuous watcher exists) |
| READ | read peer files from the fresh pull |
| APPEND | write only YOUR files (outbound channel file, your review requests/verdict transcriptions, your `memory/<role>/**`) — disjoint single-writer files can't merge-conflict by construction |
| PUBLISH | `git add -A && commit && pull --rebase && push`; on reject retry ≤5. Cloud sessions cannot push `main` — push a `claude/*` branch and open a PR (in routine sessions use the BUILT-IN GitHub tools for the PR, not `gh` — `gh` is not pre-installed and would need a visible token); the workspace's integrity-gated automerge lands state PRs. **A unit is not shipped until pushed.** A wake that cannot push cleanly must not claim progress. **EXCEPTION — auth-log consume/reservation commits NEVER use this verb:** per proxy-auth-core, after the fresh fetch + re-verify, commit CONSUMED and run a PLAIN `git push` with no pull/rebase between append and push; a rejected push = lost race — drop the consume commit (reset) and re-verify from scratch. Rebasing a consume onto a moved remote would let a losing consumer land after the winner and defeat the reservation |
| INTEGRITY | channel-core checks + `CHANNEL_STATE.json` manifest (each side records its last entry # and the peer sha last read); the stamped workspace CI asserts channel files only ever gain lines, CHANNEL_STATE counters never go backward, auth-logs are append-only, and auth chains pass `tools/validate_auth_log.py` (exactly-one landed CONSUMED); branch protection forbids force-push (free-tier fallback: watchdog history-guard, detection-only). Proven platform fact (2026-07-04): the container's git credential proxy BLOCKS ref deletion from cloud sessions (`push --delete` fails; creates/updates work) — cloud-side history rewrite and branch cleanup are impossible by construction. Corollary: stale `claude/*` branches are pruned only by the principal on github.com; and a ref once created by a cloud session (e.g. a future consume-lock ref) cannot be removed by any cloud session |

Other bindings, cloud flavor:
- **MEMORY** = `channel-repo/memory/<role>/` — checkpoint = commit + push
  (memory-discipline.md).
- **HEARTBEAT** = a scheduled ROUTINE per role, offset, **with the channel/
  workspace repo(s) ATTACHED** — the platform clones attached repos with the
  account's GitHub credentials at every run; each fire = cold successor
  running the instantiated START_SESSION. Idle tick: fetch, check
  queue/channel, sleep if nothing actionable. Wakes must be idempotent
  (check "already shipped?" before redoing work). The wake VERIFIES the
  workspace is present and aborts loudly if absent ("HEARTBEAT ABORT:
  routine has no workspace — attach the repo to the routine") — **it never
  self-clones: fired sessions have NO standalone git credential** (proven
  2026-07-04: the credential proxy challenges fired sessions for a password
  they don't have and hard-fails under GIT_TERMINAL_PROMPT=0; setup-script
  clones fail the same way). The ONLY sanctioned scheduling primitive is a
  routine with repos attached. Raw MCP/env-level triggers attach an
  environment + prompt but NO repository — they fire into empty containers
  and can neither be provisioned nor self-bootstrap; a proven-dead
  primitive, not a hypothetical. Routines schedule in LOCAL time with
  automatic DST conversion (no UTC-cron shifting).
- **REVIEWER** = primary: review requests routed through the channel repo to
  the principal's PC running Codex (a local poller pushes verdicts back);
  fallback when the PC is offline: a separate cloud Claude session on a
  DIFFERENT model than the author. The ledger records which mechanism gated
  each round.
- **SIGNING** = `webflow-api` or `sign-on-merge`: agents push unsigned working
  commits to branches and open PRs; the canonical repo's main is protected;
  the merge is signed by GitHub web-flow or by the principal locally. No
  signing path available → the commit queues, exactly like a cold gpg-agent.
- **PRINCIPAL interface** = the claude.ai/code chat attached to the session —
  plus the AUTH-RECORD (`memory/<role>/auth-log.md`): event-sourced per
  proxy-auth-core.md — the receiving session records the principal's words as
  a GRANT at the moment they were typed and spends it with CONSUMED events;
  the consume is a PUSHED reservation (fresh fetch → append → push → proceed
  only on a landed push), which is what makes concurrent cold successors
  safe. A cold successor may act on an unconsumed, in-scope, provenance-valid
  record; the reviewer audits every authorization-claiming action against
  the log. Written ONLY by the session the principal spoke into — never by a
  peer (AUTH_PROVENANCE binding proves the writer). The channel still NEVER carries
  authorization: in workspaces whose bindings set PROXY_AUTH on, relayed
  authorization travels ONLY as auth-log events the receiver verifies in the
  orchestrator's committed log and mirrors into its own (proxy-auth-core.md);
  channel entries at most announce grant/relay ids.
- **SECRETS** = cloud env secrets only (e.g. the pinned Supabase project's
  key); never in any committed file; secret-scan CI on every push.
- **COST** = heartbeats run only at the bound cadence; the orchestrator's
  always-on tick is the default presence, workers wake on demand.
