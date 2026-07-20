# Migrating a channel

Sometimes a live collaboration has to move its coordination lanes — an ad-hoc
inbox folder becomes a proper workspace channel, a channel splits when a team
divides, or several lanes consolidate into one directory. The hard part is not
copying files; it is moving a *live, append-only, counter-bearing* channel
without losing an entry, double-counting, or leaving a lane silently
unwatched. This is the production-earned procedure for doing it safely.

The whole pattern rests on one property: **the old channel is untouched until
the very last step**, so at any point before then you can abort and resume
exactly where you froze. Everything else is bookkeeping in service of that.

> Conventions in this doc are neutral: sides are `alpha`/`beta`, workspaces are
> `path/to/old-ws` and `path/to/new-ws`, rounds are `rNN`. Substitute your
> bound names (SIDE_NAMES).

## The eight steps

Each step has a one-line rationale — the reason it exists is the reason not to
skip it.

### 1. SCOPE

Enumerate **every** lane in the old location, not just the obvious one: the
peer channel (`alpha_to_beta`, `beta_to_alpha`), the reviewer request/verdict
lane, any relay lanes to other teams, and the review-round ledger
(`INDEX.md`). For each lane the principal locks three things: **MOVE or STAY**,
the **retirement mode** for a moved lane (archive read-only vs. delete), and the
**cut boundary** (the entry/round number after which new traffic goes to the new
location). Recording this as a `## MIGRATION` section in BINDINGS.md is a useful
documented convention — an optional home for the per-lane decisions so a cold
successor can see the plan.

*Rationale: a lane you forget to enumerate is a lane nobody migrates and nobody
watches — the single most common way a migration loses traffic.*

### 2. FREEZE

Post a **freeze entry** on the old channel; both sides ack it. From this point
no new substantive entries land on the old lanes. Any watcher or poller pointed
at the old location is stopped by **request-and-confirm** — the operator asks
the session that owns the watcher to stop it and waits for confirmation; one
session never reaches over and reconfigures another session's watcher. Record,
**per side**, the exact latest entry number and latest-peer-seen — read from the
**live tail of the files**, never from memory or bindings (those can lag).

*Rationale: the freeze is what makes the migration atomic. The per-side counters
read from the tail are the ground truth you will carry forward and, if you
abort, resume from.*

### 3. RECONCILE

Each role edits **only its own** memory to reflect the frozen state (its
counters, its in-flight units). Capture the whole reconciliation in **one signed
commit**. Gate on a **CLEAN TREE** before proceeding — no unrelated WIP riding
along. The reviewer round series is carried **per side from that side's own
tail**; the two sides' round series are never merged into one sequence.

*Rationale: single-writer memory and one clean signed commit keep the frozen
picture auditable; merging round series would collide two independent counters.*

### 4. REDIRECT

Point new entries at the new channel, with each side's **per-side counters
continuing** from the frozen numbers (alpha was at entry 41 → the first entry on
the new lane is alpha entry 42). Repoint any watcher by **request-and-confirm**,
same as stopping it.

**THE STAYED-LANE RULE (normative home).** A migration almost always leaves some
lane behind — the reviewer lane stays put while the peer channel moves, or a
relay lane to another team is untouched. A single-target watcher that you
*repoint* at the new location **goes blind on every lane it left behind.** So:

- Every STAYED lane MUST retain a **named live monitor** — either a second
  watcher instance still pointed at it, or an explicit acked poll cadence a
  session owns. A stayed lane with **no** live monitor is a
  **STOP-FOR-PRINCIPAL**: do not complete the migration until it has one.
- Watch for the **grammar-mismatch trap**: a monitor whose filename matcher is
  tuned to the *current* naming silently ignores legacy-named files in a stayed
  lane and falsely reports "nothing pending". Before trusting a monitor on a
  stayed lane, verify its matcher against that lane's **actual** filenames, and
  **probe one live round** through any repointed transport to confirm end-to-end
  delivery.

This is why the watcher (`tools/watcher.py`) takes multiple `--dir` arguments:
watching the moved lane *and* every stayed lane from one process is the fix, and
it is the same multi-lane posture never-idle-core's WATCHER binding already
requires.

*Rationale: a repointed watcher is the classic silent failure — everything looks
green because the process is running, while an entire lane sails past unread.*

### 5. VERIFY

Run `tools/conformance_check.py --workspace path/to/new-ws --strict` and the
auth-log validation. Run **one test round per moved lane AND per stayed lane**,
and confirm both sides agree on the carried per-side counters.

*Rationale: "the config parses" is not "traffic flows". A probe round on each
lane — moved and stayed — is the only proof the redirect actually works.*

### 6. DECOMMISSION

Make the migrated-lane files **read-only / archived**, and drop a **pointer
file** recording each lane's last entry/round numbers so the archive is
self-describing. Stayed lanes are **untouched**. This is explicitly the **LAST
and ONLY hard-to-reverse step** — do it only after VERIFY is green.

*Rationale: everything before this is reversible; this is the point of no
return, so it comes last and only once the new lanes are proven.*

### 7. UNFREEZE

Post a **migration-complete entry** on the new channel; both sides ack. Normal
cadence resumes.

*Rationale: the freeze entry stopped traffic; an explicit complete entry is what
tells both sides (and their watchers) it is safe to flow again.*

### 8. ROLLBACK (the escape hatch, available through step 5)

Because the old channel is untouched until DECOMMISSION, an abort is trivial:
lift the freeze and **resume the old lanes at the frozen per-side counters**.
The freeze is exactly what prevented divergence — no entry ever landed in two
places, so there is nothing to reconcile on the way back.

*Rationale: a migration you cannot safely abort is a migration you should not
start; the untouched-until-last-step ordering is what buys the escape hatch.*

## Version migrations: live-run notes

The *version* axis of migration (`tools/migrate_workspace.py`, carrying a
stamped workspace across a PROTOCOL version bump) is mechanically simple —
but two live runs earned these notes:

- **The one-time integrity-CI red-X, and why it is gone.** Earlier runs
  tripped the workspace's own append-only CI **once** at the migration
  commit, because the migrator re-stamped the BANNER line of append-only
  files (auth-log headers being the common case). That is the defect the
  keep-records doctrine closed: a record's banner is part of the record, so
  the migrator now leaves `memory/<role>/auth-log.md`, `dispatch-log.md`,
  `tick-log.md` and `channel/*.md` **entirely untouched**, reports every one
  it kept, and conformance accepts their older-but-supported creation stamp
  as green. A migration commit that still trips append-only is therefore a
  finding now, not an expected cost — and it was never something to "fix" by
  rewriting history.
- **Finding adjudication: pre-existing vs regression.** A defect surfaced by
  post-migration verification is not automatically a migration defect. Probe
  whether it **pre-exists** the migration (the git history of the relevant
  config answers this), and if it does: close the migration, and register
  the finding as its own scoped follow-up gate. Holding a completed
  migration open against an inherited defect conflates two workstreams.
- **Transport adoption is profile adoption.** Conformance hard-couples the
  `.git-sync` profiles to the git-sync transport: a workspace cannot adopt
  `TRANSPORT: git-sync` while keeping a `.local` profile — "transport now,
  profile later" is not a smaller change, it is a BLOCKED state. Move the
  profile, `TRANSPORT`, `WORKSPACE_REMOTE`, and `SECRETS` in one reviewed
  change.
- **Run the auth-log validator from the workspace root** — or pass the root
  explicitly (`validate_auth_log.py path/to/workspace`): it discovers logs
  under the selected workspace root (the working directory only when the
  argument is omitted), and naming a root that contains none is an error,
  not a pass.

## See also

- `tools/watcher.py` — multi-lane watcher; watch the moved lane and every stayed
  lane in one process (the stayed-lane rule, mechanically).
- [AUTONOMY.md](AUTONOMY.md) and never-idle-core's **WATCHER binding** — the same
  "a live monitor on every owed lane" requirement the stayed-lane rule enforces
  during a migration.
- `tools/adopt_project.py` — adopting an ad-hoc collaboration stamps the new
  workspace and then points here for the live-lane cutover.
- `tools/migrate_workspace.py` — the *version* axis of migration (carrying a
  stamped workspace across a PROTOCOL version bump), distinct from the
  *channel* migration this doc covers. It carries the whole supported ladder —
  v2.5 → v2.6 → v2.7 — and walks it from the workspace's pin up to the newest
  version in a single run, so a v2.5 workspace needs one checkout, not a
  release-by-release sequence. It flips the version stamps only and points back
  here for the counter/state carry.
