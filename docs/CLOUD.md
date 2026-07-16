# Running in the cloud

The local deployments in [CONFIGURATIONS.md](CONFIGURATIONS.md) assume every
session lives on one machine sharing one filesystem. This page covers the other
case: sessions on **different machines** synchronizing only through a git remote,
using the **git-sync transport** ([transports/git-sync.md](../transports/git-sync.md)).
Nothing about the four parties, the gates, or the review rounds changes — only
the transport under the channel does.

> Neutral examples throughout: hosts `alpha`/`beta`, remotes on `example.com`,
> checkouts at `path/to/workspace`. Substitute your own.

**Honesty scope.** The distributed-peers pattern is what this protocol was
distilled from and is production-proven. The **hosted-cloud** pattern below is
documented and production-derived, and as of 2026-07 the maintainers have
verified a **live one-off hosted round-trip** against a real workspace remote:
a hosted session fetched pushed state and published a reply over the real
hosted auth path (the marker + nonce handshake, battery item 7). What this
repo still does **NOT** claim is verified **scheduled** hosted operation — no
CI job here exercises a hosted runner on a timer. Treat the hosted-cloud
sections as a design verified once by hand that you must verify in your own
environment (the go-live battery at the end is exactly how).

## Two patterns

### Distributed peers

Each role runs on its own machine; all of them are self-managed hosts (own
credentials, direct-push). The remote is the shared channel. This is just the
local shape with `TRANSPORT = git-sync`: owner on `alpha`, builder on `beta`,
each pushing its own files, each fetching before it acts.

### Cloud twin

One role has a **live** session on a machine you drive interactively, plus a
**twin** clone (often a hosted-cloud runner) that a scheduler wakes to carry the
work forward while you're away. The old "which copy is canonical?" question
**dissolves**: the **remote is the canonical rendezvous**, and no clone is
canonical. The rule that keeps it safe is below.

## The one rule: single active writer per role

**At most one session per role writes at a time.** The remote is where they
meet; a twin clone is **read-only until it is woken**, and waking one side means
the other is asleep. Concretely:

- Switching which machine is live for a role = `/sleep` on the active one
  (checkpoint + push), then `/wake` on the other (fetch-first + resume). Never
  two awake for the same role at once.
- The git-sync transport has a built-in **alarm** for a violation: on POLL, a
  foreign commit to your **own** role's owned paths that you did not author is a
  single-active-writer breach (a forgotten live twin, say). Stop, don't push
  over it, surface to the principal.

This is why identity is one role per workspace ([FEDERATION.md](FEDERATION.md)):
"owner" is a seat, and only one session sits in it at a time.

## Scheduled cold-successor wake (worked example)

A scheduler fires a headless session that resumes a role from the repo alone —
no live context, no human in the loop:

```
# scheduler entry (timezone-pinned — see the DST note below)
#   precondition the SCHEDULER guarantees: a provisioned, authenticated
#   checkout already exists at path/to/workspace
cd path/to/workspace && claude -p "/wake owner"
```

What makes this safe, in order:

1. **The scheduler provides the checkout.** A headless session has **no
   standalone git credential and never self-clones** (git-sync credential
   doctrine). The scheduler delivers an already-cloned, already-authenticated
   working tree. **Workspace present? else ABORT** — a wake that finds no
   workspace reports the abort and stops; it never improvises one. This holds
   for every role's headless wake.
2. **Fetch-first.** `/wake` on git-sync fetches before it reasons, so the cold
   successor resumes from the true remote tip, not a stale local checkout. A
   divergence found at fetch is the session's *first* problem to resolve, ahead
   of any queue work.
3. **Idempotent resume.** Before redoing the in-flight unit, the wake checks
   whether it is **already shipped** (its durable id already in the fetched
   history) — a scheduler that double-fires never double-ships.
4. **Pre-approved git surface.** The stamped `.claude/settings.json` already
   allow-lists the git/gh commands the channel loop needs, so an unattended wake
   doesn't stall on a permission prompt it cannot answer.
5. **The skill-less floor is the baseline; the plugin is an opportunistic
   layer.** A plugin/marketplace declaration in the checkout's settings does
   **not** mean the hosted runner loads it — observed live: a hosted session on
   a workspace whose settings *declared* the protocol plugin reported it absent
   from its loaded set, and a plugin from a private marketplace a
   credential-less runner cannot fetch fails the same way (declaration ≠
   installation; the install is machine-level state absent from a fresh clone).
   So do **not** build the wake on the plugin loading. The **in-repo START
   contract is followable without the plugin** — point the scheduled wake prompt
   at `start/START_SESSION.<role>.md` directly, and that contract draws its core
   reference docs from a checkout of the protocol repo **pinned to a fixed
   ref/sha** (never a moving branch). The start contract runs the pre-bind
   conformance gate fail-closed: a workspace missing its stamped
   `tools/conformance_check.py` is a BLOCKER surfaced to the principal (the
   pinned checkout's trusted copy runs in its place), never a silently
   skipped gate. That pinned protocol checkout is itself a
   wake precondition — provided like the workspace in item 1 (scheduler /
   host-profile), never self-cloned; **if it is absent too, that is the item-1
   ABORT case**, because a doc-less resume *is* the forbidden protocol-less
   improvisation. This defined floor is *not* a protocol-less improvisation
   (still forbidden) — it is the accepted baseline for unattended routines.
   The plugin/`/wake` layer is a convenience on top: probe it from inside a
   live hosted session and use it if it loaded. **Arming a scheduled
   wake gates on the skill-less floor being hardened AND one hosted dry-run that
   completes the start contract exercising a representative task — not contract
   recital.**

State survives a mid-unit death because every shipped unit is checkpointed to
the ⚡ working-state block in git before it counts ([AUTONOMY.md](AUTONOMY.md)) —
the cold successor rebuilds the whole picture from the repo.

## Integrity-gated automerge

How a role's work reaches the workspace default branch depends on the host
class (git-sync, Host classes):

- **Self-managed → direct push (default).** The role pushes its owned paths
  straight to the default branch; the remote's `integrity.yml`
  ([ADVANCED.md](ADVANCED.md#workspace-integrity-ci-internals)) is the tamper
  alarm running on every push (append-only, provenance, secret-scan, monotonic
  state). Direct push is safe *because* that server-side check cannot be
  bypassed from a client.
- **Hosted-cloud → PR automerge (default).** A hosted session cannot push the
  default branch, so it publishes to a **work branch** (`state/<role>/<unit>`)
  and opens a PR via the platform's native tooling. Automerge lands it **only**
  when the required checks pass.

Hardening recipe for the PR-automerge path:

1. **State branches**: each unit publishes to `state/<role>/<unit>` — never
   directly to the default branch.
2. **Required integrity check**: the workspace `integrity.yml` is a **required**
   status check on the default branch; a PR cannot merge until it is green.
3. **Branch protection with require-up-to-date** ("head-pinning"): the PR must
   be current with the default branch tip to merge, so a stale PR can't land
   over newer history. Combined with the **required force-push and
   branch-deletion protection** git-sync mandates, the append-only history the
   auth-record SHAs depend on is preserved.

Enabling the platform-side automerge switch itself (the API call that turns
auto-merge on for a repo) is **principal housekeeping**, not something a role
does — the same way pruning stale `state/**` branches is.

## Go-live verification battery

Do NOT declare a cloud deployment live because the config parses. Run this
battery; each item is a real failure the protocol is supposed to survive:

1. **Cold-kill mid-unit → resume.** Kill a session mid-unit; the next scheduled
   tick must resume from the repo alone and finish the unit, losing nothing but
   the killed step.
2. **Tripwire pages.** A planted liveness tripwire (remote silent past your
   idle-max) must actually alert you — see the heartbeat-monitoring note in
   [ADVANCED.md](ADVANCED.md#heartbeats-unattended-operation).
3. **Planted dummy secret fails CI.** Commit a throwaway fake secret to a work
   branch; the `integrity.yml` secret scan must fail the build (never merge it).
4. **Hand-edited auth-log line fails CI.** Edit (not append) a line in a
   `memory/<role>/auth-log.md`; the append-only + chain checks must reject it.
5. **Reviewer round-trip.** Run one real review round end-to-end, and confirm
   the poller-down **fallback** engages when the primary reviewer lane is
   unavailable (a spawned judge on a different model than the author).
6. **A real fired-and-delivered scheduled run.** The deployment is live **only**
   once an actually-scheduled tick has fired and delivered on its own — a manual
   `claude -p "/wake"` proves the prompt, not the scheduler.
7. **Hosted wake handshake (marker + nonce).** Before any hosted session
   carries real work, prove it can see pushed state and publish over the real
   hosted auth path — without touching a live lane:
   1. Pre-stage a scratch **marker branch** (`smoke/<name>`) carrying a marker
      file with a fresh **nonce** and the reply instructions.
   2. The principal fires a **one-off hosted session** bound to the workspace
      repo with a paste-prompt: read the marker branch, reply on a NEW work
      branch with a reply file echoing the exact nonce plus the session's own
      timestamp; touch nothing else (no default-branch writes, no channel
      writes, no PRs).
   3. An observer polls `git ls-remote` for the reply ref. **Verify by
      CONTENT (the echoed nonce), never by branch NAME** — hosted platforms
      may suffix or rename a requested branch per their own conventions.
   4. Clean up both scratch refs and confirm the remote head-set is
      byte-identical to pre-smoke.

**Scheduler timezone / DST note:** pin the schedule to an explicit timezone and
decide what a DST transition should do (a skipped or doubled hour can drop or
duplicate a tick). Record the choice in the host profile; the idempotent-wake
check (item 1's cousin) is your backstop against a doubled tick, but don't rely
on it to paper over an ambiguous schedule.

## Binding it

git-sync deployments set `TRANSPORT = git-sync`, `WORKSPACE_REMOTE` to the
remote URL + default branch, and keep any git credential in `SECRETS` (host
env / connector only, never committed); the `2agent.git-sync` /
`3agent.git-sync` profiles select the transport at stamp time. Those slots and
profiles ship in this release — see [CONFIGURATIONS.md](CONFIGURATIONS.md) and
the binding-slot glossary. `CHANNEL` and `MEMORY` stay repo-relative; only each
host's clone path is machine-specific, and that lives in the host profile, never
in a committed binding.
