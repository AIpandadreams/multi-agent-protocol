# Changelog

All notable changes to this repository are documented here. The repo
follows [SemVer](https://semver.org) for its own releases; the protocol the
skills implement carries its own version stamp (`PROTOCOL vX.Y`), which
changes only through the
[self-improvement protocol](plugins/agent-protocol/skills/agent-core/references/self-improvement-protocol.md).

| repo release | protocol version | notes |
|---|---|---|
| 1.2.5 | v2.6 | corrects shipped guidance that caused a real defect, and the SCOPE of two rules that were already right: PS 5.1's `-Encoding utf8` WRITES a BOM (the docs recommended it as the fix for the UTF-16 default); the byte-gate rule existed but was scoped to "data units", so nobody applied it to a release manifest; and review scope is now the ARTIFACT SET, not the touched-file set — a reviewer handed your diff cannot report the file you forgot. Twins now fail as a pair *mechanically*: the BOM gate scans every file (no suffix allowlist), the doc/HTML twin and the three copies of the amendment header get parity gates, and the file-hygiene baseline moves once into a role-neutral core so the orchestrator inherits it. Every new gate ships with a mutation test — the first drafts of three of them were green *and* defeated. Suite 171 → 206 |
| 1.2.4 | v2.6 | the no-idle ledger at the top of the autonomy dial: never-idle made a worker prompt about work that ARRIVES but said nothing about work already stalled — every deliverable is now IN FLIGHT / SURFACED / BLOCKED-WITH-BLOCKER-NAMED ("idle" is not a fourth state), with an anti-invention clamp and gate-preserving surfacing rules; SOP catalog row 9 |
| 1.2.3 | v2.6 | skill-less cloud-wake floor is the baseline (plugin = opportunistic layer; declared-but-not-loaded is the motivating case): routines follow the in-repo `START_SESSION` contract + a protocol checkout pinned to a fixed ref/sha, else ABORT; `CLOUD.md` arming gate revised (floor-hardened + representative-task dry-run) |
| 1.2.2 | v2.6 | transport live-validation + second-migration hardening: hosted wake handshake, empirical remote-protection verification, declared≠loaded plugin rule, version-migration live-run notes, `validate_auth_log.py` argv fix |
| 1.2.1 | v2.6 | live-operation hardening: wake-monitor arm-and-verify, incident-driven ops-gotchas, `migrate_workspace.py`, creator-seat + SOP-registry docs, `--once` failure propagation |
| 1.2.0 | v2.6 | `PROTOCOL v2.6`: review-convergence, never-idle, git-sync cloud transport, role aliasing, wizard v2, ops tooling |
| 1.1.0 | v2.5 | tooling: `--wizard`, `--watch`, conformance suite |
| 1.0.0 | v2.5 | first public release |

## [1.2.5] — 2026-07-14

**Guidance that caused the defect it warned about — and two rules that were
right but mis-scoped.** Shipping 1.2.4 burned three lessons the same afternoon.
None of them is a new idea. One was the protocol telling you to do the exact
thing that broke the release; the other two were rules this repo already
published, applied to a set too small to contain the defect.

- **`ops-gotchas.md` (both role copies) — the "utf8" flag that writes a BOM.**
  The docs said *"write shared files as UTF-8 without BOM"* and, in the same
  breath, *"prefer an explicit `-Encoding utf8`"*. On Windows PowerShell 5.1
  those two instructions contradict each other: `-Encoding utf8` emits UTF-8
  **with** a BOM. It doesn't fix the UTF-16 default — it trades one bad artifact
  for a worse one, because a BOM is invisible to every line-oriented tool while
  strict parsers reject it outright (`json.loads` → *"Unexpected UTF-8 BOM"*).
  Corrected to writers that are actually no-BOM, **version-tagged**:
  `[IO.File]::WriteAllText($path, $text, [Text.UTF8Encoding]::new($false))` on
  **PS 5+** (`::new()` arrived in 5.0); `-Encoding utf8NoBOM` on **PS 6+** (it
  does not exist on 5.1). Detection likewise — read the first **four** bytes,
  matched longest-first (UTF-32's mark is 4 bytes and shares UTF-16 LE's opening
  two): `[IO.File]::ReadAllBytes($p)[0..3]` on 5+, `Get-Content -Encoding Byte
  -TotalCount 4` on 5.1, `-AsByteStream -TotalCount 4` on 6+. **Every
  shell snippet a protocol file publishes now carries the versions it runs on** —
  an untagged snippet is a trap with a green face. This took three passes to get
  right, and the misses are the lesson: draft 1 was unrunnable on the shell it
  targeted (PowerShell method arguments are expression-mode, so bare words are a
  parser error), and draft 2 carried two **wrong** version boundaries. A
  wrongly-tagged snippet is worse than an untagged one — it fails exactly like
  the flag it was warning about. The writer snippet also now says what nobody
  documents: `[IO.File]` resolves a **relative** path against the process working
  directory, not `Get-Location`, so a relative name lands somewhere you are not
  standing. Pass an absolute path.
- **The byte-gate rule was not missing. Its SCOPE was.** *"Gate anything whose
  consumer reads bytes with a byte leg"* has been in the bootstrap case studies
  since 1.2.1 — written as a **data-unit** rule. So when a BOM landed in the two
  release **manifests**, nobody recognized a manifest as the kind of thing that
  rule covers: it passed the full test suite *and* the structural doc gate, and
  would have shipped JSON that a strict parser rejects. The rule is restated
  where it belongs — the byte leg is owed by **any** gate whose artifact is
  machine-read (data units, manifests, lockfiles, generated code) — and the
  gates were widened to match:
  - `tests/test_manifest_integrity.py` (shipped in 1.2.4) reads both manifests
    as raw bytes: no BOM, strict decode (never the BOM-swallowing `utf-8-sig`),
    parse, and versions that must agree across files.
  - `tools/mirror_check.py`'s BOM gate now scans **every file git tracks, plus
    the working tree**, of any name, reading bytes — and checks **every** BOM
    (UTF-8, UTF-16 LE/BE, UTF-32), not just UTF-8. It took three narrowings to
    get here, and each one looked reasonable at the time: scoped to the skills
    subtree (missed the manifests); widened to the repo but gated on a **suffix
    allowlist** (missed every extensionless file — `.github/CODEOWNERS`, the
    mechanical backstop for principal-locked paths, plus `.gitignore` and
    `LICENSE`); widened to all files but checking only `EF BB BF` (missed
    **UTF-16 — which is Windows PowerShell 5.1's default output encoding**, i.e.
    the likeliest BOM to land here by accident). A fourth miss never shipped but
    is the sharpest: resolving "what git tracks" returned an **empty set** when
    git was unavailable, so the gate scanned *nothing* and passed — fail-open. It
    now fails **closed**: no git means the publish scope is unknowable, which is
    itself a finding, and the gate widens to the whole tree (minus `.git`) so a
    real BOM is still caught alongside the scope warning. Reviewers defeated each
    version with a planted BOM before it shipped. The gate **enumerates its
    exclusions** in-line — tool caches, VCS internals, and vendored trees, *and
    only if git does not track them* — because an unstated exclusion reads as
    coverage. `tests/test_bom_gate_scope.py` plants a real BOM on every surface
    the narrow versions missed (including file types the gate has never heard of,
    so coverage never again depends on remembering to add an extension), proves
    every BOM signature the gate lists — UTF-8, UTF-16 LE/BE, UTF-32 LE/BE — is
    caught on the extensionless `CODEOWNERS` surface, and exercises the
    git-unavailable branch on purpose. A clean-tree canary in the guard suite
    (`FixtureCanaryTest`, `tests/test_mirror_guards.py`) proves the mutation tests
    fail on their mutation, not on a stray background finding.
  - **The fingerprint that couldn't see the set.** Naming an unchanged twin in
    the bundle is worthless if the bundle's fingerprint can't tell it's there —
    and a `git diff` digest can't: an unchanged member emits no diff bytes, so
    the digest is byte-identical with or without it. Every fingerprint recipe for
    a set-scoped round (`review-core.md`, `/converge`, `docs/PROTOCOL.md`,
    `CONTRIBUTING.md`, the PR template, the worked example) now digests the
    **contents** of the set, so adding a member changes the digest. `--error-unmatch`
    makes a mistyped or untracked member error — but *only in git*: piped into
    `sha256sum`, git's nonzero exit is masked and the pipeline returns 0,
    computing a plausible digest over the tracked members alone (fail-open — the
    very gap `--error-unmatch` was added to close; both round-5 reviewers
    reproduced it). So the published recipe wraps the pipe in a guard —
    `( set -o pipefail; git rev-parse HEAD && git ls-files -s --error-unmatch --
    <set> | sha256sum )` — which propagates the failure while leaving the digest
    value byte-for-byte unchanged; `tests/test_fingerprint_recipe.py` proves both
    halves (the guarded recipe goes nonzero on a missing member, the bare pipe is
    shown fail-open) and that every published digest recipe is guarded *at the
    command* — the check binds `pipefail` to each `git ls-files … | sha256sum`, not
    merely to the file (an earlier draft asserted the word anywhere in the doc, and
    both round-6 reviewers reverted one recipe to the bare pipe with the prose
    mention intact and the test stayed green — the guard wearing the hole it
    guards). That is the point.
- **`review-core.md` — scope the review to the ARTIFACT SET, not the touched
  files.** A reviewer bounded to "the files I changed" is structurally incapable
  of reporting the file you *forgot* to change, and an omission is a defect like
  any other. Artifacts with a **co-maintained twin** (a doc and its rendered
  `.html`, a schema and its generated types, a file and its mirror in another
  repo) fail **as a pair** and must be named as a pair in the bundle. Live case:
  a reviewer scoped to 4 changed files returned CONFIRM while the un-updated
  HTML twin of an edited doc sat outside its window; a second reviewer handed
  the whole repo caught it at once. **Unanimous agreement across seats that were
  all handed the same blind spot is not convergence; it is a chorus** — when
  voices disagree, suspect the scope you handed them before you suspect the
  voices. The rule now binds the surfaces that actually dispatch rounds:
  `/converge` takes an artifact SET and freezes it (naming co-maintained
  counterparts even when unchanged, plus an explicit omission search), both role
  review-dispatch files require the same, `docs/PROTOCOL.md` restates it, and
  `review-convergence.md` names **the mis-scoped bundle** as an anti-pattern.
  The amendment header — which exists in **three** places, and where a field
  added to one is a field the other two silently drop — gains `artifact set:` and
  `omission search:` alongside `files touched:` in all three: `CONTRIBUTING.md`,
  `.github/PULL_REQUEST_TEMPLATE.md` (the copy GitHub actually injects into every
  PR), and `.github/ISSUE_TEMPLATE/protocol_amendment.md`. The first draft of
  this release amended only the guide — the two templates that *deliver* it were
  the omission, caught by the omission search this release adds. `/converge`'s
  worked example (`examples/worked-cycle.md`) now shows the request shape with a
  set that names two files the round never touched. That is the whole argument
  for the rule, made at our own expense.
- **Twins get a mechanical gate, because "remember the other copy" is not a
  control.** `mirror_check.py` now compares `CREATOR-SEAT-BOOTSTRAP.md` and its
  rendered `.html` on the **identities** of the three structures that carry the
  catalog — section headings, bold/`<strong>` runs, and table-row leading cells —
  and fails on any that exists in one twin and not the other. Identities
  (presence in one twin but not its pair), not counts, order, or prose: it does
  **not** diff body paragraphs or HTML nesting, a re-worded sentence stays a
  reviewer's catch, and that exclusion is stated in the gate because an unstated
  one reads as coverage. Identities rather than counts because *the first version
  of this gate compared counts and a title-shaped regex, and both reviewers
  walked a renamed heading and a new catalog row straight past it* — and a
  catalog row is exactly the drift that motivated the gate. It also fails **loud
  if either twin is missing** (deleting one used to skip the check) and masks
  fenced/indented code so a `##` or `**x**` inside a matched example is not read
  as a real heading or bold run. A second gate keeps the three amendment-header
  copies in parity: the field set is **derived from the copies**, not hard-coded,
  so a field added to one drifts as loudly as a field dropped from another, and
  labels are matched anchored (deleting the `artifact set:` label while the words
  survive in prose no longer passes). A third fails when a count claimed in prose
  outruns what it counts — `SOP-REGISTRY.md` advertising nine SOPs against a
  catalog that defines eight is the "registry says nine, rendering shows eight"
  defect this repo already names — and fails **closed** if that prose sentence
  stops matching at all, rather than silently disarming. Every guard ships with a
  mutation test (`tests/test_mirror_guards.py`) that breaks exactly one thing and
  asserts the gate names it: **a gate that has never been seen to fail is not a
  gate** — which is how the first drafts of these three shipped green while
  defeated.
- **`channel-core.md` — file hygiene is role-neutral.** UTF-8-without-BOM and
  "gate as bytes" lived only in the two role `ops-gotchas` files, so the
  orchestrator — which carries none — inherited neither, while writing channel
  entries, auth-logs, and registries like everyone else. The baseline now lives
  **once**, in the core every role reads; the role files keep their
  shell-specific traps and point at it. (Our own first draft restated it in all
  three files while claiming otherwise — the old dedup guard matches *headings*
  and cannot see a rule restated as prose.) The new guard is a **tripwire**, not
  a paraphrase detector: it fails if a role file repeats one of the baseline's
  load-bearing sentences, which catches the copy-paste that actually happens and
  is honest that a re-worded restatement remains a reviewer's catch, not a gate's.
  `transports/local-fs.md` no longer points readers at "each role's ops-gotchas"
  for a rule one role could never find.
- Suite **171 → 206** (the count against the released 1.2.4 base, `1c1fc43` —
  not against an intermediate draft of this release); `tools/mirror_check.py`
  gains four gates.

## [1.2.4] — 2026-07-14

**The no-idle ledger.** Never-idle made a worker prompt about work that
*arrives* — watcher-driven intake — but said nothing about work that already
exists and is going nowhere: the queued unit nobody started, the finished unit
waiting on a gate no one presented, the item stalled on a peer's seam. A seat
could be perfectly responsive on every watched lane, sit on a pile of stalled
deliverables, and report itself — honestly and uselessly — as *idle*.

- **`never-idle-core.md`** — the **three-state ledger**, owed at every
  checkpoint and before any report of having nothing to do: every deliverable
  in the seat's lane is **IN FLIGHT**, **SURFACED**, or **BLOCKED WITH ITS
  BLOCKER NAMED** (what blocks it, who clears it, what it unblocks). *"Idle" is
  not a fourth state.* A seat that reports itself idle is usually a BLOCKED seat
  that never named its blocker — which was the one fact the principal needed in
  order to clear it. The ledger turns silent waiting into a decision someone
  can act on.
- **The anti-invention clamp** — the ledger is TRIAGE over work that already
  exists (queue, channel, standing duties), never a licence to manufacture
  scope: "put everything possible in flight" is about work that EXISTS and is
  stalled. An honest ledger with *nothing* in flight is a COMPLETE report. And
  its near neighbor, which wears a real queue item's name: **a queued unit that
  has not received its go is BLOCKED (blocker: the go), never IN FLIGHT** — the
  ledger does not launder a pending authorization into a status line.
- **Gate-preserving surfacing** — surfacing a gated item is **not** clearing its
  gate; the item moves to the principal's desk and stops there. A **gated**
  item's surfacing target is the *principal*: handing it to a peer does not
  discharge a gate, and a peer's ack is never authorization (*authorization
  never rides the channel*). Peer hand-off is for a SEAM, never a GATE. The
  ledger exists to make gates VISIBLE, never to route around them.
- **`docs/AUTONOMY.md`** — the never-idle dial bullet carries the ledger.
- **`docs/CREATOR-SEAT-BOOTSTRAP.md`** (+ HTML twin) — SOP catalog **row 9**,
  *no-idle / continuous forward progress*; plus an explicit note that the
  catalog's numbers are its own illustrative sequence, not any deployment's
  master ledger — which matters, sitting beside the registry's "master numbers,
  never renumbered" rule.
- **`docs/SOP-REGISTRY.md`** — stale catalog count corrected (a stale registry
  is worse than none, by its own rule).

## [1.2.3] — 2026-07-14

A single coherent hardening: make **skill-less operation the defined baseline
for unattended/cloud routines**, closing the gap the v1.2.2 declared≠loaded rule
exposed. When a scheduled wake finds the protocol plugin declared but not loaded
— the normal case for a credential-less routine that cannot install a plugin
from a private marketplace — the in-repo `START_SESSION.<role>.md` contract is
followable on its own, drawing its core reference docs from a protocol checkout
pinned to a fixed ref/sha. Protocol text stays `v2.6`; carried through a
cross-vendor + isolated-judge convergence loop.

### Added
- **`START_SESSION.md` (all three role templates): "operating without the
  plugin loaded (skill-less baseline)."** The contract is explicitly followable
  with no plugin/skills loaded; obtain the cited reference docs from a checkout
  of the protocol repo pinned to a fixed ref/sha (never a moving branch); the
  plugin/`/wake` layer is an opportunistic convenience on top, not a dependency.

### Changed
- **`docs/CLOUD.md` go-live item 5 — from "gate on a proven load / stop when the
  skill surface is absent" to "the skill-less floor is the baseline."** The
  v1.2.2 rule correctly observed declaration ≠ load but treated an unloaded
  plugin as a stop condition; a plugin from a private marketplace a
  credential-less routine cannot fetch would then never run at all. The floor
  inverts the default — routines operate from the in-repo START contract, the
  plugin is a bonus — while preserving the valid caution that the *defined*
  floor is not a protocol-less improvisation, with an explicit ABORT when
  neither the plugin nor the pinned protocol checkout is present. The arming
  gate is restated:
  **arm once the floor is hardened AND one hosted dry-run completes the start
  contract exercising a representative task (not recital).**

## [1.2.2] — 2026-07-13

Hardening release distilled from the git-sync transport's first full
**empirical validation** over a live remote — a seven-point smoke battery
(verb round-trip, both retry-rule classes, the collision detector, the
credential doctrine, remote protection, and a live hosted-session handshake)
— plus a second real v2.5→v2.6 workspace migration and the incidents three
more days of live multi-team operation surfaced. Protocol text stays `v2.6`
— every change is a clause-level strengthening within the existing version,
carried through a three-voice cross-vendor + isolated-judge convergence loop.

### Added
- **`docs/CLOUD.md`: the hosted wake handshake (marker + nonce)** — go-live
  battery item 7: prove a hosted session can see pushed state and publish
  over the real hosted auth path before it carries any real work. Pre-stage
  a scratch marker branch carrying a nonce; a one-off hosted session replies
  on a new work branch echoing the nonce + its own timestamp; an observer
  polls `ls-remote`. Verify by CONTENT, never by branch NAME — hosted
  platforms may suffix or rename a requested branch per their own
  conventions. The honesty-scope note is updated to match what this earned:
  a live one-off hosted round-trip is now maintainer-verified (2026-07);
  *scheduled* hosted operation remains not-CI-proven.
- **`docs/MIGRATION.md`: "Version migrations: live-run notes"** — what two
  real `migrate_workspace.py` runs earned: the expected ONE-TIME
  integrity-CI red-X when the migrator re-stamps banner lines in
  append-only-checked files (disclose, quiesce, never history-rewrite);
  finding adjudication (probe whether a verification finding PRE-EXISTS the
  migration before treating it as a migration defect — close the migration,
  register a scoped follow-up gate); transport adoption IS profile adoption
  (conformance hard-couples them — "transport now, profile later" is a
  blocked state, not a smaller change); run the auth-log validator from the
  workspace root or pass it explicitly.
- `tests/test_validate_auth_log.py` — pins the validator's new invocation
  contract (below).

### Hardened (incident-driven protocol text, within v2.6)
- **`transports/git-sync.md`: verify remote protection EMPIRICALLY** — two
  production-earned rules under the existing REQUIRED clause: (1) platform-
  capability rationales go stale — a "platform cannot enforce this" binding
  rationale must carry a date and be re-probed at every migration/audit (a
  real deployment's default branch sat fully rewindable for months behind
  exactly such a stale rationale); (2) the verification pattern — arm the
  rule, prove the rejection on a temporarily-covered scratch ref, narrow
  back, then READ BACK the final active configuration (the covered-ref test
  proves the mechanism, the read-back proves the final targeting); never
  rewind-test the live default branch.
- **`docs/CLOUD.md`: declared ≠ loaded** — cold-successor wake rule 5: a
  plugin declaration in the checkout's settings does not mean the hosted
  runner loads it (observed live). Probe from inside a live hosted session;
  arming a scheduled wake gates on a proven load; wake prompts fail loudly
  when the skill surface is absent.
- **`channel-core.md`: the timezone leg of the wall-clock rule** — a
  tool-verified stamp can still corrupt the timeline if its zone is misread
  (some tools emit UTC). Never relabel a UTC output as local; stamp from a
  local-clock call or carry the zone designator verbatim.
- **`never-idle-core.md`: the monitor-less seat** — a seat with no
  persistent monitor owes a manual poll of every owed lane immediately after
  any reply-requesting post and at every wake/checkpoint — and, while a
  reply is owed, at a bound cadence until it arrives or the ask is parked
  (one immediate poll normally lands before the peer can answer); posting a
  question does not page you.
- **`memory-discipline.md`: checkpoint stamps from a verified local clock** —
  working-state timestamps follow the same tool-verified-clock rule as
  channel entries, zone carried; a UTC value relabeled as local
  future-stamps the canonical resume state, and a successor reading an
  implausible stamp treats the block as suspect.
- **`proxy-auth-core.md`: auth-log appends commit SOLO** — single-purpose
  commits touching only the auth-log file keep the chain's history a clean
  sequence of auth events and keep the same-subtree CI signal sharp.
- **`binding-slots.md`: bare cells for tooling-parsed slots** — `PROFILE` /
  `TRANSPORT` / `PROTOCOL_VERSION` cells hold the bare canonical value only;
  provenance rides the commit message, never the cell (an annotated cell
  reads fine to a human and fails conformance's exact match).
- **`ops-gotchas.md` (owner + builder): shared-live-trees extension + a new
  class** — peer pull-rebase re-hash (cite the landed remote sha, never your
  pre-rebase local one) and the isolated-worktree publish pattern (fetch →
  worktree add at the remote tip → cherry-pick → push → remove) for trees
  holding a peer's live WIP; plus **harness-hook wedges**: a stuck harness
  hook process can freeze a session mid-turn indefinitely — kill the HOOK
  process, not the session; hooks need hard kill-timers and
  exit-after-write, and a scheduled janitor converts the class to a
  non-event.
- **`CREATOR-SEAT-BOOTSTRAP.md`** — SOP-7 gains the strict-tense rule for
  decision-package FACTS (past = resolved-during-prep, future = still-open;
  a reviewer cannot converge an ambiguous tense), and Part 7 gains two new
  case studies: *the stale platform rationale* and *declared ≠ loaded*.

### Fixed
- `tools/validate_auth_log.py` (and the byte-identical copy `new_project.py`
  stamps into workspaces) — the validator previously ignored argv entirely
  and globbed from the cwd, so `validate_auth_log.py <path>` silently
  checked NOTHING and exited 0 ("no logs found") — a green that means "ran
  from the wrong directory". New contract: optional single positional
  workspace-root argument (default `.`); an explicitly named root containing
  no logs exits 1 loudly; a bare invocation finding none keeps the
  compatible exit-0 (pre-first-grant workspaces still pass CI); extra
  arguments exit 2.

## [1.2.1] — 2026-07-10

Hardening release distilled from the first full week of PROTOCOL v2.6 live
operation (a same-day two-workspace v2.5→v2.6 migration plus the incidents it
surfaced). Protocol text stays `v2.6` — every change is a clause-level
strengthening within the existing version, adopted through principal rulings
and carried through cross-vendor + isolated-judge convergence review.

### Added
- **`docs/CREATOR-SEAT-BOOTSTRAP.md` (+ `.html`)** — a complete, self-contained
  handoff document that turns a fresh Claude session into a *multi-agent
  protocol creator*: the system in one page, the creator-seat role definition
  (duties + incident-derived boundaries), a topology-design interview (tandem /
  hub / multi-team, e.g. 3+2 and 3+2+2), a generalized SOP catalog, a runbook
  library (onboarding, live hash-pinned migration, archive hardening,
  failure surfacing, reviewer-outage recovery), and nine incident case
  studies that each became protocol.
- **`docs/SOP-REGISTRY.md`** — the SOP layer: principal-ruled standing orders
  over the protocol, master-number rules, the cross-team `SOPS.md` registry
  file, and the numbering-collision lesson (document + team-qualify, never
  renumber).
- `tools/migrate_workspace.py` — migrates a stamped `PROTOCOL v2.5` workspace up
  to `v2.6`. Mechanical, idempotent, and reversible. The rewrite is
  line-structured, not a blind whole-file replace: it flips a `[PROTOCOL v2.5]`
  stamp only on a file's BANNER line (its opening title heading / docstring —
  the sole place a stamp is emitted), and rewrites the `PROTOCOL_VERSION` row
  structurally (matched by slot name, any spacing; only the version cell is
  flipped, extra cells preserved) so version detection and the rewrite can never
  disagree. The same literal token off the banner — inside a PROXY_AUTH/authority
  row, a memory-body heading or prose, or a fenced example — is therefore LEFT
  UNTOUCHED (and reported, so the conservative skip is auditable), and a file's
  existing line endings are preserved exactly. Following `scale_workspace.py`'s
  contract, it never edits authority rows — it PRINTS the PROXY_AUTH reword when
  the slot predates v2.6's canonical super-class wording (first-hand only) —
  never stamps the new v2.6 slots (it prints the not-yet-present ones, flagged by
  whether they apply to this profile), and never rewrites coordination state
  (counters/memory are carried by the agents per `docs/MIGRATION.md`). Ends with
  an informational `conformance_check.py` run and points the operator to
  `--strict` as the final gate; `--dry-run` previews without writing.
  Fills the version-migrate gap in the lifecycle family (`new_project` stamps
  fresh · `scale_workspace` grows 2→3 · `adopt_project` adopts ad-hoc). Pin-aware
  conformance means a not-yet-migrated workspace stays green under a v2.6
  checkout, so workspaces migrate independently, each at its own freeze boundary.

### Hardened (incident-driven protocol text, within v2.6)
- **Wake monitors: arm-and-verify** — all three role START_SESSION contracts
  gain a machinery step, all three session cards gain resume STEP 1 ("Wake
  monitors ARMED?"), and `never-idle-core.md` gains the monitor-durability
  rule. Root incident: a session interrupt + context compaction silently
  killed a live seat's monitors and its resume path had no re-arm step — the
  seat sat deaf while peer posts accumulated. An unarmed watcher is
  indistinguishable from a quiet lane; self-expiring pollers are not a valid
  wake path.
- **`ops-gotchas.md` (owner + builder): two new burned-lesson classes** —
  *Shared live trees (index sweeps)*: in a repo another session actively
  works, a bare `git commit` after `git add <file>` commits the ENTIRE index,
  silently sweeping the peer's staged work — always commit with an explicit
  pathspec, disclose any sweep immediately, never rewrite shared history
  unilaterally. *Silent credential prompts*: credential-manager outages hang
  git network ops on an invisible prompt — set `GIT_TERMINAL_PROMPT=0` so
  agents fail fast, repair the credential helper instead of retrying.
- **`channel-core.md`: two clauses closing live gaps** — *Mid-day rotation
  convention*: a size-triggered rotation file carries a suffix name, a header
  pointing back to the closed file, and UNBROKEN entry numbering/counters
  across the boundary (rotation changes the container, never the sequence;
  codified from a first-try-successful live improvisation). *Tool-verified
  timestamps*: entry stamps come from a tool call, never momentum-copied from
  prior entries — the drift class this closes was observed to RECUR the same
  day it was diagnosed, because the fix wasn't yet mechanical protocol text.
- **`CREATOR-SEAT-BOOTSTRAP.md` runbooks 6.5/6.6** — principal HALT/RESUME
  procedure (verify the durable relay artifact, relay to peer, checkpoint,
  monitors stay armed as the resume signal path, full wake on resume) and two
  review-lane escalation patterns (the self-ruled-extension rider R1/R2, the
  contest-adoption confirm leg), all executed live before being written down.
- **`never-idle-core.md`: re-arm is stop-then-arm** — the deaf-seat inverse:
  a monitor can survive an interrupt the seat assumed killed it, so a blind
  re-arm leaves two monitors firing on one lane. Enumerate and stop the
  predecessor by id before arming (observed twice in one week live).
- **Bootstrap additions from the second consult round** — scoped-pull rule
  for shared live trees (`--ff-only`, in the index-sweep case study), the
  "byte-blind gate" case study (parse-level gates are structurally blind to
  byte-layer defects; data-unit gates need a raw-byte leg), and SOP catalog
  entry 8 (single-writer fixed-time external status-board sync).

### Fixed
- `tools/reviewer_poller.py` — `--once` now exits nonzero when any attempted
  review failed, so scheduling wrappers can surface a reviewer outage. It
  previously returned 0 unconditionally, which made reviewer failures (e.g.
  quota exhaustion) look like success to a task scheduler indefinitely.
- `tools/migrate_workspace.py` — banner detection now tolerates a leading UTF-8
  BOM (`U+FEFF`). A BOM-prefixed banner line (as written by some Windows
  editors) previously failed the stamp-prefix match and was mis-reported as an
  off-banner token, silently leaving the file on the old version stamp. The BOM
  is stripped for DETECTION only — the byte itself survives the rewrite
  unchanged. Found by a cross-vendor review pass against a live workspace copy;
  regression-tested (BOM survives, stamp flips).

## [1.2.0] — 2026-07-07

### Added — PROTOCOL v2.5 → v2.6 amendment
An amendment bundle bumping the protocol the skills implement from
`PROTOCOL v2.5` to `PROTOCOL v2.6`:
- **Review-convergence cycle** — a new normative reference
  (`agent-core/references/review-convergence.md`) layering the multi-round
  cycle over `review-core.md`: the four seats (author / peer-model reviewer /
  cross-vendor reviewer / author-as-verifier-of-the-verdict), a 2–3 round
  budget with escalation-on-exhaustion, evidence-weighed adjudication of
  reviewer disagreement (votes/averages banned), a mechanism-neutral blocking
  line (BLOCKER/MAJOR gate, MODERATE/MINOR recorded), anti-anchoring, an
  anti-patterns catalogue, and a worked convergence arc.
- **`/converge` command** — a harness command that drives an artifact through
  the convergence cycle to a reviewer-declared stop.
- **Never-idle autonomy level** — a new normative reference
  (`agent-core/references/never-idle-core.md`) and a fourth rung on the
  autonomy dial: a worker between assignments holds at intake-watch and acts on
  settled events within one cycle. Closed MAY / MUST-NOT self-assign lists; the
  invariant that never-idle changes cadence, never authority. Adds the
  **AUTONOMY** and **WATCHER** binding slots.
- **Reviewer-lane outage rules** — `review-core.md` gains a normative
  `## Reviewer-lane outage` subsection: probe-before-blame, a fallback ladder
  (alternate transport → different-model judge → multi-judge panel, DEGRADED-
  tagged), and principal-gated gate-disable for outage windows.
- **FIX-CONFIRMATION round type** — `reviewer_poller.py` frames a request
  carrying `ROUND-TYPE: FIX-CONFIRMATION` to judge named fixes and end with
  CONVERGED / NOT-CONVERGED; the stamped `channel/INDEX.md` ledger gains a
  ROUND-TYPE column and a rounds-used-vs-budget note.
- **Pin-aware conformance** — `conformance_check.py` accepts a supported
  version set (v2.5 / v2.6) and checks every per-file stamp against the
  workspace's OWN pinned version, so a live v2.5 workspace and a fresh v2.6
  workspace both pass under one checkout.
- **git-sync transport (cloud / distributed peers)** — a new transport profile
  (`transports/git-sync.md`) binds the abstract channel verbs
  (POLL/READ/APPEND/PUBLISH/INTEGRITY) to git over a remote, for peers on
  separate machines or a live session plus a scheduled cloud twin. Ships with:
  the load-bearing disjoint-owned-paths invariant (any rebase conflict is a
  protocol-violation detector); two commit classes with two retry rules
  (append-class rebases, reservation-class re-verifies — a consume commit is
  never carried through the generic retry loop); self-managed vs hosted-cloud
  host classes; the credential doctrine (headless sessions never self-clone —
  a missing checkout aborts loudly); required force-push/branch-deletion
  protection; and a helper `tools/git_sync.py`. New **TRANSPORT**,
  **WORKSPACE_REMOTE**, and **SECRETS** binding slots; new
  `2agent.git-sync` / `3agent.git-sync` stamp profiles;
  `conformance_check.py` gains a `check_transport` pass (profile↔transport
  agreement, unknown-value block, repo-relative-path guard). See
  [docs/CLOUD.md](docs/CLOUD.md) for the deployment recipes and their honest
  hosted-cloud caveats.
- **Role display-name aliasing (rename)** — a new **ROLE_ALIASES** binding slot
  lets a deployment give its roles workspace-local display names (e.g.
  `engine→owner`, `helper→builder`) that `/wake` resolves in three tiers:
  canonical name → the workspace's `ROLE_ALIASES` row (which beats the built-ins)
  → the legacy `engine`/`helper`/`orch` built-ins (so pre-2.6 workspaces with no
  row still resolve). Aliases resolve ADDRESSING only — identity artifacts
  (`ROLE_LOCK`, `memory/<role>/`, `START_SESSION`) always use the canonical role.
  The rename is doc-only (no scripted rewrite); `conformance_check.py` gains a
  side-name pass and warns on a role renamed without a matching `ROLE_ALIASES`
  row.
- **Onboarding — wizard v2** — `new_project.py --wizard` is now a pre-stamp
  walkthrough: topology → side names (validated at entry — underscore and other
  channel-filename-illegal characters are rejected and re-prompted) → principal
  → project repo → reviewer (probes `PATH` for a `codex` CLI; `none` is allowed
  but warns that independent review is the core quality lever) → a grouped
  `{{FILL}}` walk (day-one slots vs deferrable, where Enter records a
  `{{DEFERRED}}` marker distinct from an untouched `{{FILL}}`). After every
  stamp it prints a **NEXT STEPS** block with absolute paths. New `--git-init`
  (default off; non-fatal, timeout-guarded so a cold GPG agent never eats the
  stamp) and `--plugin-install {marketplace,manual}` — `manual` omits the
  marketplace blocks from the stamped `.claude/settings.json` for a hand-copied
  `~/.claude` install. `--no-orchestrator` is now a deprecated alias for
  `--profile 2agent.local` (it errors instead of stamping an invalid workspace).
  The stamp also drops a **self-check copy** of `conformance_check.py` into the
  workspace (`SELF-CHECK MODE` banner — hygiene, not a trust gate), and the
  `/wake` command runs a pre-wake conformance gate that hard-stops on any
  BLOCKER (including the new **one-agent-per-role** check) and warns when the
  workspace is not a git repo (checkpoints won't persist). QUICKSTART gains a
  three-repo diagram and a first-exchange example; README gains a reading order.

The whole skills tree, the two lifecycle commands, and the tooling stamps flip
to `PROTOCOL v2.6`; `new_project.py` stamps v2.6 workspaces.

### Changed
- Documentation default topology inverted: the 3-agent shape (orchestrator +
  owner + builder) is now presented as the default, and `2agent.local` is
  reframed as the **dual-role-owner** variant (the owner absorbs the
  orchestrator's interface/intake duties). No protocol-semantic change; profile
  ids and tooling are untouched.

## [1.1.0] — 2026-07-05

Tooling round: three quality-of-life additions to `tools/`, each carried
through independent cross-vendor review to convergence. No protocol-semantic
change — `PROTOCOL v2.5` is unchanged.

### Added
- `new_project.py --wizard` — interactive walk-through that fills the
  `{{FILL}}` slots in a freshly stamped `BINDINGS.md`. Skipped automatically
  when stdin is not a TTY, so unattended stamps never block.
- `reviewer_poller.py --watch` — event-driven mode beside `--once`/`--loop`.
  A stdlib directory-signature check (no `watchdog` dependency) fires a review
  sweep once a channel change settles, cutting local review latency from a
  poll interval to a couple of seconds; a periodic fallback sweep still catches
  remote-pushed requests. Neither path reads a mid-write request.
- `tools/conformance_check.py` — a self-runnable, point-in-time workspace
  readiness check (the structural counterpart to the integrity CI): required
  files per profile, `PROTOCOL_VERSION`, profile/role-set agreement, an intact
  PROXY_AUTH guard, and a clean auth-log chain. BLOCKER vs WARN severities;
  `--strict` fails on unbound slots.
- `tools/validate_auth_log.py` — the auth-log chain validator is now a
  first-class file (previously only stamped into workspaces); `mirror_check.py`
  guards it byte-identical to the stamped copy.
- `tests/` — first committed test suite (stdlib `unittest`), pinning the
  `--watch` settle/fallback interleaving.

### Fixed / hardened
- Auth-log validator: a relayed CONSUMED must now follow the **complete**
  RECEIVED block (past its `source:` line), and relay + direct spends of the
  **same** grant are counted **together** against its scope — closing a latent
  double-spend (a `single` grant spent once by relay and once directly).
- `--watch`: a channel still being written is excluded from **both** the
  settle sweep and the periodic fallback sweep, so a half-written request is
  never read on either path.

## [1.0.0] — 2026-07-05

Initial public release: the local-transport distillation of a protocol
developed and hardened on live production work.

### Included
- `agent-protocol` plugin: `agent-core` shared normative references +
  three role skills (owner, builder, orchestrator).
- `/sleep` and `/wake <role>` session-lifecycle commands — the basis for
  unattended, cross-session **autonomy**.
- Self-improvement loop: the protocol amends itself through reviewed PRs to a
  human merge (`agent-core/references/self-improvement-protocol.md`), with
  principal-locked gates and `mirror_check.py` keeping the ruleset coherent.
- `tools/new_project.py` — stamps a dedicated agent workspace
  (`2agent.local` / `3agent.local` profiles), including the integrity CI
  workflow and the auth-log chain validator.
- `tools/mirror_check.py` — consistency CI over the skill tree.
- `tools/reviewer_poller.py` — optional bridge to a local Codex reviewer.
- `tools/wave_coverage_check.py` — coverage checker for builder read-waves.
- Documentation suite (incl. `docs/AUTONOMY.md` covering the two core
  platform properties) + a worked end-to-end example.

### Not included (deliberately — see README roadmap)
- The cloud transport (scheduled cold-successor wakes, integrity-gated
  automerge). Running upstream; platform surface still moving.
