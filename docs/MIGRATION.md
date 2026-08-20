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
  v2.5 → v2.6 → v2.7 → v2.8 → v2.9 → v3.0 → v3.1 — and walks it from the workspace's pin up to the newest
  version in a single run, so a v2.5 workspace needs one checkout, not a
  release-by-release sequence. It flips the version stamps only and points back
  here for the counter/state carry.

---

# Migrating a vendored conformance checker

## Why this migration (added at repo release 1.9.0) has an ORDER, and what breaks if you ignore it

Most releases here migrate by running the migration tool. **This one does not**, and the
reason is worth stating because it was found by running it rather than by reading it.

Three things interact — and ⛔ **they did not all land in the release this note
shipped with (1.9.0)**, which is itself part of why the ordering bites:

1. the conformance checker's vocabulary carries an identity beyond the positional roles —
   **already shipped, in an earlier cut** (reachable from both `v1.7.0` and `v1.8.0`);
2. workspaces may declare directories under `memory/` that are *not* roles;
3. some workspaces carry a **vendored copy** of the checker that predates both.

⚠ **Owed, not shipped:** a further amendment to how the checker treats a name that shadows
a side-name is **still under review and is not part of any release yet**. Do not plan
around it; this note describes only behaviour that has landed.

Taken in the wrong order, each of the first two breaks against the third.

### ⛔ The two failure modes, both observed in practice

**(a) Re-vendor before fixing the declaration → every wake stops.**
A workspace that provisions the new identity's directory *and* declares that directory a
non-role has, until now, been running a checker that **accepts the declaration silently** —
its refusal is keyed only to positional roles, and the new identity is not one. The updated
checker keys the same refusal to the **full identity vocabulary**, so the declaration is
**refused**, the name is inferred anyway, and the declaration becomes a blocker:

> `NON_ROLE_DIRS declares '<name>', which the identity vocabulary defines — the declaration
> was REFUSED and the name is still inferred; remove it from the row`

⭐ The finding **names its own remedy**, and the remedy is a **one-token edit** — remove
that name from the row. But if you re-vendor first and read the row second, the workspace
is hard-stopped in between.

**(b) Re-vendor before porting local additions → a guard disappears silently.**
⛔ **This is the dangerous one, and it is dangerous precisely because it is quiet.**
A vendored copy is not always merely *behind*; it may carry checks that the canonical
version **has never had**. Deployments commonly add local checks that guard a *publication
surface* — commit metadata is the usual example, since it is published by definition and
is easy to get wrong once and never notice — along with local recording that something
downstream depends on.

A straight re-vendor **deletes them**. Nothing goes red. No finding appears. Wakes keep
passing. ⭐ **Failure mode (a) is loud and gets fixed within a minute; (b) is silent and
could run for months.** Loud breakage is the cheap kind.

### ✅ The order that works

1. **Inventory first.** For every workspace with a vendored checker, ask whether it is
   *behind* the canonical or *diverged from* it — i.e. does it define anything the
   canonical has never defined? ⛔ **"Out of date" and "carries local code" are different
   conditions with different remedies, and one tool reporting both as "needs attention"
   will get one of them wrong.**
   ⚠ **Verify this by hand — true as of repo release 1.9.1.** The tooling does not yet
   separate the two conditions for you, so diff your copy against the canonical file and read what your
   side defines that canonical does not. It is the one step of this order that is manual,
   and it is the step that matters most — ⭐ **the whole failure mode below is a local
   definition nobody knew was local.**
2. **Port or retire the local additions, explicitly.** Anything the vendored copy defines
   and the canonical does not is either **moved into the canonical** or **retired with a
   stated reason**. ⛔ Neither is "it disappeared during an upgrade."
3. **Fix the declaration row**, in the workspaces that carry one, and verify in a scratch
   copy before touching a live workspace.
4. **Then re-vendor** (`python tools/reconcile_vendored.py --fix` — `--check`
   first reports OK / DRIFT / MISSING per workspace without writing), and
   re-run conformance.
5. **Verify the guards still exist** after the re-vendor — by name, not by a green run.
   ⭐ A guard's absence is not something a passing check reports.

## Conformance changes since your last vendored copy

⚠ **Framed by your copy's age, not by the release this note shipped with (1.9.0) —
deliberately.** Several of these
landed in **earlier** cuts: the identity-vocabulary refusal, for instance, is reachable
from **both `v1.7.0` and `v1.8.0`** (verified against the tags, not inferred). If you
vendored before those, they are new *to you* even though they are not new to the project.
⛔ **Check the tag your copy came from; do not read this table as a changelog for the
newest release.**

| change | effect on an existing workspace |
|---|---|
| the identity vocabulary is checked, not just positional roles | a declaration excluding a vocabulary name is **refused and reported**; the name is still inferred |
| the applied exclusions and any refusals print beside the verdict | on the **green** path as well as the red one — so a refusal is visible without a failure |

⭐ **Why a refusal still infers the name.** A guard that complains while the exclusion goes
through anyway is worse than no guard: the operator sees a complaint, and the directory
leaves the structural checks regardless. So the refusal does both — it reports, *and* the
name stays governed.

## ⛔ Two INPUT-COMPATIBILITY breaks a name-level diff will not show you

Both were found by an adversarial review of the first real port done under this note — not
by the note, and not by the capability guard. ⚠ **Neither is a bug in the canonical: both
are deliberate canonical decisions, stated in the canonical source.** They are listed here
because "port your local additions" is a *name*-level instruction, and these live inside
function bodies where no name-level diff and no AST surface census can reach them. ⭐ **If
your inventory was a name diff — and step 1 above tells you to do a name diff — this
section is the part you have not checked.**

**(1) `NON_ROLE_DIRS` sentinel values and backticks are no longer normalized.**
A fork that treated `none` / `-` / `n/a` as "nothing declared", or stripped backticks
before splitting, will change behaviour on those cells:

| cell | fork | canonical |
|---|---|---|
| `none` · `-` · `n/a` | nothing declared | a directory literally named `none` / `-` / `n/a` is declared → a **stale-exclusion WARN**, and rc=1 under `--strict` |
| `` `cache` `` | excludes `cache` | declares a directory named `` `cache` `` → the real `memory/cache/` is **inferred, not excluded** |

⭐ This is canonical's stated intent, in its own words at `declared_non_role_dirs`: a cell
reading `none` surfaces as a stale exclusion *rather than being silently swallowed*.
⛔ **Do not "fix" it by re-adding the fork's normalization** — that is not porting a local
addition, it is overriding a canonical decision from a downstream copy, and the next
re-vendor deletes it again. **Fix the CELL**: leave it empty, or use the documented
`{{FILL}}` / `{{DEFERRED}}` placeholder forms, which canonical does recognize.

**(2) `ROLE_LOCK` now requires the colon form.**
`ROLE_LOCK = OWNER`, or any line naming a role without `ROLE_LOCK:`, parsed under a fork
whose regex scanned the whole line; canonical requires the colon-form declaration. ⭐ The
colon is doing real work — without it the reader matched WRAPPED PROSE in memory indexes
that merely *discussed* role locks, and two live orchestrator indexes carried exactly that.

⚠ **Grep every `memory/*/MEMORY.md` for its `ROLE_LOCK` line before the swap.** This one
is fail-CLOSED — an unparseable lock is already a BLOCKER, so it announces itself rather
than mis-reading — but it announces itself *at the next wake*, which is a bad moment to
find out. **One command, before you swap, not after.**

## If you maintain a vendored copy

Answer these before upgrading:

- Does your copy define anything the canonical does not? **Check by name, not by size or
  date.** ⛔ A newer file is not a superset.
- Is anything in your copy load-bearing for a **publication** surface — commit metadata,
  release artefacts, anything that leaves the machine? Those are the ones whose loss is
  silent.
- Does your workspace declare a `memory/` directory that the new vocabulary now claims?
  Fix the row **before** the swap, not after.

## Honest limits of this note

- It describes the ordering hazard as **measured on the deployments we could inspect**
  (two). A deployment we have not seen may carry local additions we have not
  enumerated — the inventory step exists because the list cannot be written in advance.
- The one-token declaration fix is **stated by the instrument**; verify it in a scratch
  copy end-to-end before applying it live. ⛔ *An instrument naming its own remedy is not
  the same as that remedy having been run.*
