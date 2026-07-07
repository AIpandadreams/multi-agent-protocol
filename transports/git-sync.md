# Transport profile: git-sync [PROTOCOL v2.6]

For agents running as separate Claude Code sessions on **different machines**
(distributed peers, or a live session plus a scheduled cloud twin) that share a
workspace only through a **git remote**. Binds the abstract channel verbs to git
operations. The local-fs transport assumes one shared filesystem; git-sync drops
that assumption — the remote, not a mounted directory, is the rendezvous.

The whole profile rests on one **load-bearing invariant**: *each writer commits
only the files it owns* (its own outbound channel file, its own
`memory/<role>/`, its own deliverables). Because writers never touch each
other's paths, a rebase-on-reject can never produce a content conflict from
honest concurrent work — so `PUBLISH` retry is provably safe, and **any rebase
conflict is therefore a protocol-violation detector**, not a merge to resolve.

| verb | implementation |
|---|---|
| POLL | `git fetch` the remote, then compare the fetched peer tail against memory's last-seen — **fetch before you act**, never reason from a stale local checkout. Cadence: each heartbeat + session start + after every completed unit. |
| READ | integrate fetched peer history **fast-forward only** (`git merge --ff-only` / `git pull --ff-only`, or rebase your own unpushed commits onto it). A non-ff that would require a content merge is **not** integrated: post a DISCONTINUITY entry and STOP (per the invariant, it means someone wrote a file they do not own). |
| APPEND | stage the files you own **by explicit path** and `git commit` locally. An entry that is committed but **not yet pushed IS NOT POSTED** — the peer cannot fetch it. Posting completes at PUBLISH. |
| PUBLISH | `git push`. On reject (remote moved): `fetch` → reintegrate (READ) → re-push, **max 3 attempts**; still failing → mark the lane **DOWN** and escalate (channel-core discontinuity + flag the principal). See push-ordering below — the retry rule differs by commit class. |
| INTEGRITY | channel-core's post-fetch checks (contiguous numbering, own-tail == counter) **plus** the workspace's server-side `integrity.yml` running on every push — the remote is the enforcement point no local session can bypass. |

## Push-ordering: two commit classes, two retry rules

A `PUBLISH` reject means a peer pushed first. What you do next depends on what
your commit *is*:

- **Append-class** (a channel entry, a memory checkpoint, a deliverable): the
  loser **rebases and re-pushes**. The invariant guarantees no content conflict,
  so the two entries simply serialize — both survive, ordered by who landed
  first. This is the generic retry loop in the `PUBLISH` row above.
- **Reservation-class** (an auth-log `CONSUMED` event — the exactly-one-landed
  reservation of a proxy-auth grant, per proxy-auth-core.md): the loser **DROPS
  its reservation and re-verifies from the new tip** — it is **never** carried
  through the generic rebase loop. Losing the push race means someone else may
  have consumed the same grant; blindly rebasing your CONSUMED on top would
  double-spend. Re-fetch, re-check whether the grant is still unconsumed, and
  only then reserve again. (This is the git-sync expression of proxy-auth-core's
  "losing a push race means re-verify".)

Mixing the two in one push is a bug: reservation commits publish alone. Put
plainly, and to match proxy-auth-core.md verbatim: the generic PUBLISH verb
with its pull-rebase retry loop **must never carry a consume commit**.

## Host classes (bind per machine, in the host profile)

git-sync runs on two shapes of host, and they publish differently:

- **Self-managed host** — you control the machine and its git credentials
  (a laptop, a VM, your own server). **Direct-push to the workspace default
  branch is the default** `PUBLISH`; `integrity.yml` on the remote is the tamper
  alarm behind it.
- **Hosted-cloud host** — a platform-attached checkout (a cloud agent runner)
  that **cannot push the workspace default branch** and has **no `gh` CLI**
  assumed. `PUBLISH` is a **work branch + pull request** via the platform's
  native git/PR tooling; integration to the default branch is the automerge
  recipe in [docs/CLOUD.md](../docs/CLOUD.md). PR-publish is the **default** for
  this class, not an option.

Both classes stage **only owned paths, by explicit path**. `git add -A` /
`git add .` is **explicitly rejected** — it is exactly how a headless push
sweeps up a file the role does not own and trips the conflict detector (or
worse, lands a cross-owner write the detector was meant to catch). This matches
the interactive rule in the `/sleep` command.

## Credential doctrine (production-derived — applies to every role)

A scheduled or event-fired **headless** session has **no standalone git
credential** and **MUST NOT self-clone or self-bootstrap** a workspace. The
scheduler is responsible for delivering a **provisioned checkout** — an already-
cloned, already-authenticated working tree — before the role's wake prompt runs.
A headless wake that finds **no workspace present aborts loudly and notifies**;
it never improvises one by cloning. (A session that could clone itself a
workspace could also clone itself *out* of its gates — the provisioned-checkout
rule is a control boundary, not just convenience.) This holds for **all** roles'
headless wakes, owner/builder/orchestrator alike.

## Idempotent wake ("already shipped?")

Because a session can die between "commit" and "push", or a scheduler can fire a
tick that a previous tick already completed, a git-sync wake **checks whether the
current unit is already shipped before redoing it**: fetch, then look for the
unit's own committed entry/deliverable in the fetched history (by its durable id
— round number, entry number, job id — never a session id). If it is already
there, the unit is done; do not re-emit it (a re-emit makes an empty commit or a
duplicate entry). An optional `CHANNEL_STATE.json` manifest of last-shipped ids
makes the check O(1); the committed history is the fallback ground truth.

## Announce-before-sync, solved atomically

On a shared filesystem, a deliverable file and its announcing channel entry can
appear at slightly different moments (channel-core's hold-timeout exists for
exactly that gap). On git-sync the gap closes: the **deliverable and its
announcing entry ride the SAME push** — the same commit is preferred, one push
at minimum. A peer therefore never fetches a deliverable without its
announcement. The channel-core **hold-timeout clock starts at fetch-visibility**
(when the file first appears in a fetch), not at the author's write-time, since
write-time is invisible to the reader across a remote.

## Remote protection (REQUIRED, not optional)

The workspace default branch **MUST** have **force-push protection and branch-
deletion protection** enabled on the remote. Auth-record SHAs and the
consume-ordering guarantee both depend on history that is **never rewritten**: a
force-push could silently reorder or drop a CONSUMED event and defeat the
exactly-one-landed rule. Where the hosting platform cannot enforce this, the
documented fallback is **detection-only** — a scheduled check that the last-seen
remote SHA is still an ancestor of the current tip (see the heartbeat-monitoring
note in [docs/ADVANCED.md](../docs/ADVANCED.md)) — with its blind spots named:
it cannot see the baseline first run, and a rewrite-and-revert between two polls
slips through. **Hosted ref-deletion asymmetry:** refs created from a hosted-
cloud side are typically permanent from that side; pruning stale `state/**`
branches is **principal housekeeping** done from a privileged context, not
something a role does.

## Concurrent same-role foreign commits = single-active-writer alarm

git-sync's headline failure mode is **two live sessions of the same role**
(e.g. a forgotten live twin plus a fired cold-successor) both writing. The
detector: on POLL, foreign commits to **your own** role's owned paths that you
did not author. That is a **single-active-writer violation** (docs/CLOUD.md) —
stop, do not push over it, and surface to the principal. The rule that prevents
it is one active writer per role at a time; switching which machine is live is
`/sleep` on one side then `/wake` on the other, never two awake at once.

## Other bindings, git-sync flavor

- **TRANSPORT** = `git-sync` (the binding slot that selects this profile;
  conformance checks the profile↔slot agreement). Ships in this release.
- **WORKSPACE_REMOTE** = the git remote URL + default branch the workspace
  synchronizes through (this transport's rendezvous). Ships in this release.
- **CHANNEL** / **MEMORY** = **repo-relative** paths (`channel/`,
  `memory/<role>/`) under the provisioned checkout — the same repo-relative
  bindings local-fs uses; only the *machine* clone path differs, and that
  absolute path is host-profile data, never a committed binding.
- **SECRETS** = host environment / platform connector only — a git credential or
  token lives in the scheduler's secret store, **never committed** to the
  workspace. Ships in this release.
- **HEARTBEAT** = a scheduled headless wake per role (see the credential
  doctrine); note any per-tick cost under the binding.
- **Profiles** = `2agent.git-sync` / `3agent.git-sync` select this transport at
  stamp time. Ship in this release.
- **SIGNING**, **REVIEWER**, **PRINCIPAL interface** = as bound per deployment
  (unchanged by transport).

## Host profile (bind per machine)

As with local-fs, machine facts are TRANSPORT data, not protocol: record each
host's clone path, host class (self-managed / hosted-cloud), credential source,
scheduler and its **timezone/DST** behavior, and platform PR tooling in the host
profile alongside the bindings — never in the committed protocol text.
