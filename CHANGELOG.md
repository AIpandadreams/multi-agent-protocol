# Changelog

All notable changes to this repository are documented here. The repo
follows [SemVer](https://semver.org) for its own releases; the protocol the
skills implement carries its own version stamp (`PROTOCOL vX.Y`), which
changes only through the
[self-improvement protocol](plugins/agent-protocol/skills/agent-core/references/self-improvement-protocol.md).

| repo release | protocol version | notes |
|---|---|---|
| 1.3.0 | v2.7 | `PROTOCOL v2.7`: the public tree crosses to v2.7. Three review-lane lessons banked from live runs fold into the normative skills — seat-qualification on cross-team lines and a cross-team drafting-assist lane (channel-core); carried-claim provenance and "a status claim is a measurement, re-verified not carried" (memory-discipline); sweep-completeness — a narrow probe's silence proves nothing (review-core). A new `docs/CREATOR-SEAT-CHARTER.md` names the *chartered external seat* — a solo, repo-isolated, orchestrator-fronted protocol-stewardship session — as a recognized THIRD identity form beside the role seats and the orchestrator: mandate, boundaries (outward-facing stays the principal's, first-hand; an orchestrator-lane authorization does not lift a principal-first-hand outward gate), cold-start, and an explicit grant of NO new authority; admitted into the FEDERATION identity invariant and the bootstrap's now-topology-aware Design duty. Disclosed skew (deliberate, tracked): the bundled workspace-lifecycle tooling — `new_project.py`, `migrate_workspace.py`, the conformance supported-version set — and its docs stay v2.6 and move together in a later coordinated workspace-migration release; until then a v2.7 install that scaffolds a fresh workspace stamps it v2.6, so the first wake parks protocol-sensitive actions on the stamp mismatch, by design |
| 1.2.7 | v2.6 | the loop's own failure modes, codified — each burned first-hand before it was written down: a reviewer lane that ANSWERS with a refusal is a third outage shape beside silent and down (cure = accurate description, never evasion; verdicts written incrementally with an explicit incomplete/final marker; a partial stream supplies findings for seat-4 adjudication but NEVER ship authority); convergence gains an execution-environment axis (every shipping platform gets an ACTUAL run wherever runnable coverage exists, else it is recorded UNEXECUTED with the residual risk escalated — the "single-platform chorus" anti-pattern, banked from this repo's own 1.2.6 CI escape, where 21 rounds of review on one host shipped 4 POSIX launch-time errors); verification instruments offered as ship evidence earn the same distrust as the gates they certify (bind to the most structured surface that exists and to exact messages, launch/import/collection failures fail CLOSED to RED, every new guard proves liveness by mutation or is disclosed as defense-in-depth); and the wake gate fails CLOSED when its tool is absent — a workspace missing `tools/conformance_check.py` no longer no-ops the hygiene gate on ANY wake path, `/wake` and the skill-less START_SESSION floor alike, and the checker itself now lists its vendored copy as a required file (this release's one disclosed code change), because a gate that "passes" by never running is the worst false green |
| 1.2.6 | v2.6 | the fix that reproduced the bug it fixed. 1.2.5 widened the no-BOM gate to every file — and `.ps1` **INVERTS** that rule: Windows PowerShell 5.1 decodes a BOM-*less* UTF-8 script as ANSI and mangles non-ASCII (`§ — é` → `Â§ â€” Ã©`), so the gate would have *commanded the very mojibake the protocol warns about*. PowerShell **script files** (`.ps1`/`.psm1`/`.psd1`/`.psrc`/`.pssc` — the exception follows the 5.1 script/data-file *reader*, not the one suffix that bit us) now REQUIRE the BOM and are checked for it (an exception you cannot state as a rule is a hole). 1.2.5 also fused two different claims — "this artifact must exist here" and "if it exists it must agree with its twin" — making the checker unrunnable in any tree that legitimately does not carry the docs (it went 10-findings red in the private mirror, and a gate nobody can see go green is one people learn to scroll past). A tree may now DECLARE itself in `.mirror-check.json`; relaxations are bounded, printed with reasons, tracked, stale entries are findings, a defective declaration grants NOTHING, and no declaration = the old strict behaviour exactly. Reviewers defeated cut after cut — the mojibake gate alone fell twenty-six times (lookback, span licence, fence claim, marker enumeration, a fence fix that skipped the delimiter line, a lead-set that was still an enumeration, a fence tracker blind to tilde/nested fence shapes, a truncation exception that named one prefix of a family, fences hidden behind list/blockquote markers, a container peel that manufactured fence CLOSERS out of literal marker lines inside a fence — disproving its own "over-peeling only widens scanning" claim — an indented run doing the same through the 4-space/tab hole, a span finder counting stray and escaped backticks as delimiters, a coverage gate sweeping the tree's own characters when corruption arrives as mangles of text that was never there, a liberal OPENER inverting fence phase by consuming the real opener as its closer, a fence-only machine blind to the seven CommonMark HTML-block kinds that swallow fence lines, a Latin-1 boundary that read mangled French œ as prose, a cannot-interrupt-a-paragraph rule built on a blank-line proxy when fences and headings end paragraphs too, and then FOUR block-model divergences in one round — link-reference definitions, container-scoped block state, ordered lists that cannot interrupt a paragraph, and a backtick in a backtick fence's info string — at which point the block model was RETIRED rather than repaired: the exemption no longer consults a document model at all — a candidate is exempt only when its entire line is byte-identical to one of five enumerated documentation lines keyed by exact path, every other line is scanned unconditionally whatever block it sits in, and the allowlist is gated live on stale, dead, and mis-keyed entries — after which the retirement's own first review round cut it twice more: the scanner's line unit was str.splitlines(), whose extra separators (VT/FF/NEL/U+2028/U+2029) let a renderer-visible modified line self-exempt a licensed suffix (lines now end only where markdown ends them), and resolve()-keyed paths let a symlink at an unlisted path inherit an exempt licence while an out-of-tree link crashed the checker (keying is lexical now, and a symlink in the guarded tree is itself a finding — a rule then re-cut one round later because it ran only on files the walk could SEE: rglob looks through neither a symlinked directory nor past a junction, so both guarded trees are now swept for reparse points of every kind, and the resolve()-keyed stamp-exemption map fell to the same junction alias and went lexical too — then cut twice more one round later: os.walk never stats the root it is handed, so a junction replacing an ENTIRE guarded tree walked through the sweep, and without an onerror callback the walk swallowed the OSError from an unlistable directory and called the corner it never read clean, so guarded roots are now reparse-checked before the walk and every unreadable path is a fail-closed finding, while a hostile declaration path — `..` or resolving outside the repo — now refuses the whole declaration instead of coexisting with its own active relaxations); the detector validates by byte round-trip with a stated cp1252-letter-aware prose side, derived truncation families, and a detector-coverage gate over a fixed support alphabet); the next round turned on the gate's own footing outside the mojibake lane: existence became its own gate (shipped transports, all four SKILL.md entrypoints — deletion of any was green), the whole-repo BOM enumeration fails closed instead of trusting rglob's silent error-suppression, case-colliding index entries are a finding (one visible worktree file was certifying a second, unseen released blob), and the declaration loader hardened four more ways (regular-file only — a tracked symlink sourced its relaxation from untracked bytes; duplicate JSON keys refused; duplicate entries refused; canonical POSIX spelling required); the round after THAT found the tracked names themselves hostile: git's UTF-8 pathnames were being decoded with the Windows locale, so a tracked non-ASCII name became a phantom path and its BOM'd blob invisible (BLOCKER), trailing-dot index aliases and NFC/NFD variants joined case collisions as findings, the loader now also requires the tree's exact on-disk spelling, the first existence list was completed (profiles, new_project.py — whose absence silently disarmed the auth-log drift gate — and docs/CLOUD.md, declarable with the docs tree), and scratch dirs the gate never claims are pruned so an unlistable node_modules cannot false-red it; and the round after that turned on the split between the two trees git actually keeps: every byte gate read WORKTREE bytes while a commit ships the INDEX blob, so a BOM'd blob swapped into the index behind a clean worktree twin was green (BLOCKER — divergent staged blobs now go through the byte gates themselves, while a routinely dirty tree stays green because an ordinary edit's staged blob is the last committed content), a tracked-but-deleted worktree path fell out of the tail silently (now a finding, with non-regular and unmerged index entries refused too), the non-portable list learned the names its first cut did not know (Win32-forbidden characters, `CONIN$`, superscript-digit `COM¹`), and an index name that merely RESOLVES to a differently spelled worktree file — an 8.3 short name, a lone case variant — is a finding by exact-spelling comparison, closing the alias family rather than its members; and the round after that beat the cure's own enumeration twice in one verdict — git diff ignores assume-unchanged/skip-worktree entries by design and never content-compares a same-size blob behind an unchanged stat cache, both green — so the scan stopped asking git which entries diverge and reads EVERY staged blob by object id in one cat-file batch (the flags are also findings in themselves), the staged mojibake leg selects on the normalized suffix, and the alias guard learned macOS's decomposed on-disk spellings without re-admitting case or 8.3 aliases — so every gate here is guarded by the mutation that beat its predecessor, and doc/gate suffix parity is itself a gate. Suite 206 → 332 |
| 1.2.5 | v2.6 | corrects shipped guidance that caused a real defect, and the SCOPE of two rules that were already right: PS 5.1's `-Encoding utf8` WRITES a BOM (the docs recommended it as the fix for the UTF-16 default); the byte-gate rule existed but was scoped to "data units", so nobody applied it to a release manifest; and review scope is now the ARTIFACT SET, not the touched-file set — a reviewer handed your diff cannot report the file you forgot. Twins now fail as a pair *mechanically*: the BOM gate scans every file (no suffix allowlist), the doc/HTML twin and the three copies of the amendment header get parity gates, and the file-hygiene baseline moves once into a role-neutral core so the orchestrator inherits it. Every new gate ships with a mutation test — the first drafts of three of them were green *and* defeated. Suite 171 → 206 |
| 1.2.4 | v2.6 | the no-idle ledger at the top of the autonomy dial: never-idle made a worker prompt about work that ARRIVES but said nothing about work already stalled — every deliverable is now IN FLIGHT / SURFACED / BLOCKED-WITH-BLOCKER-NAMED ("idle" is not a fourth state), with an anti-invention clamp and gate-preserving surfacing rules; SOP catalog row 9 |
| 1.2.3 | v2.6 | skill-less cloud-wake floor is the baseline (plugin = opportunistic layer; declared-but-not-loaded is the motivating case): routines follow the in-repo `START_SESSION` contract + a protocol checkout pinned to a fixed ref/sha, else ABORT; `CLOUD.md` arming gate revised (floor-hardened + representative-task dry-run) |
| 1.2.2 | v2.6 | transport live-validation + second-migration hardening: hosted wake handshake, empirical remote-protection verification, declared≠loaded plugin rule, version-migration live-run notes, `validate_auth_log.py` argv fix |
| 1.2.1 | v2.6 | live-operation hardening: wake-monitor arm-and-verify, incident-driven ops-gotchas, `migrate_workspace.py`, creator-seat + SOP-registry docs, `--once` failure propagation |
| 1.2.0 | v2.6 | `PROTOCOL v2.6`: review-convergence, never-idle, git-sync cloud transport, role aliasing, wizard v2, ops tooling |
| 1.1.0 | v2.5 | tooling: `--wizard`, `--watch`, conformance suite |
| 1.0.0 | v2.5 | first public release |

## [1.3.0] — 2026-07-20

**PROTOCOL v2.7: the public tree crosses over.** The protocol stamp moves
v2.6 → v2.7 across the skills, transports, and self-consistency gate.
Three lessons banked from live multi-team runs fold into the normative
references, and a new charter names a session shape the protocol had been
running without a name for. The release ships one disclosed version skew,
described below.

### Three review-lane lessons (channel-core, memory-discipline, review-core)

- **Seat-qualification on cross-team lines, and a cross-team drafting-assist
  lane** (channel-core): a message that crosses a team boundary states which
  seat it speaks for — two teams can carry the same role names for
  different agents — and a seat may be lent to another team to ASSIST
  DRAFTING, not only to gate-review, on the lender's authority and without
  adopting the borrowing team's identity.
- **Carried claims are unexamined; a status claim is a measurement**
  (memory-discipline): any sentence that asserts a prior artifact's STATE is
  re-measured where it is re-stated, never carried forward on trust — a
  moved pin is a finding to report, not a thing to silently re-pin.
- **Sweep-completeness** (review-core): a narrow probe that returns nothing
  proves nothing about coverage — widen the sweep past what feels
  necessary before reading silence as absence.

### The chartered external seat — a third identity form

New: `docs/CREATOR-SEAT-CHARTER.md`. The federation modeled two identity
forms — the role seats (owner/engine, helper/builder) and the
orchestrator. Sustained protocol-stewardship work runs as neither: a solo,
repo-isolated session, fronted to the principal through the orchestrator,
that reads the whole fleet and proposes protocol changes but commits only to
its own tree. The charter names it the *chartered external seat* and states
its mandate, its boundaries, its cold-start, and — explicitly — that
it grants NO new authority: outward-facing acts stay the principal's,
first-hand, and an orchestrator-lane authorization does not lift a
principal-first-hand outward gate (verify it in the authority log, hold, and
route back). `FEDERATION.md`'s identity invariant now admits the third form,
and the creator-seat bootstrap's Design duty is made topology-aware: a
standalone creator presents directly, a global-PA-fronted seat presents
through the orchestrator.

### One disclosed version skew (deliberate, tracked)

The version-stamp gate covers the reference and skill files; it does not
cover the workspace-lifecycle tooling. That tooling — `new_project.py`,
`migrate_workspace.py`, and the conformance checker's supported-version set
— stays at v2.6 in this release, together with the docs that describe its
current behaviour, because bumping it in isolation would strand a fresh v2.7
workspace with no migrator to reach it. The consequence is real and
intended: a v2.7 install that scaffolds a new workspace stamps it v2.6, and
the first wake then parks protocol-sensitive actions on the stamp mismatch
— the fail-closed behaviour working as designed. The tooling, its tests,
and its docs move together in a later coordinated workspace-migration
release.

## [1.2.7] — 2026-07-16

**The loop's own failure modes, codified.** 1.2.6's convergence generated
three protocol lessons that its own scope did not carry — real, dated defects
in how REVIEW itself runs. A fourth arrived the next day as a field finding (two
workspaces, same day) with the same failure shape in the session lifecycle: a
wake gate that "passed" by never running. 1.2.7 writes all four into the
normative docs, plus ONE disclosed checker change (a required-file line + its
test — see the wake-gate unit below; the docs-only scope was deliberately
widened there because an instructional gate is exactly the thing that unit
exists to distrust).

### A reviewer lane that ANSWERS with a refusal (review-core, Reviewer-lane outage)

The outage section modeled a SILENT lane (no output; dead-lane escalation) and
a DOWN lane (usage-limit/transport error; probe, fallback ladder). A vendor
safety layer produces a third shape: the run dies in seconds WITH explanatory
output and no verdict — observed first 2026-07-14 (adversarially-worded review
request flagged as offensive-security tasking; the same substance in plain QA
wording passed first try), then four more times during 1.2.6's own rounds
(the flag landing on the reviewer's final message). The new rules: distinguish
by OUTPUT SHAPE before blaming quota; cure by accurate description, never
evasion (if accurate language will not pass, escalate — do not rephrase to
sneak intent past a classifier); harden rounds by instructing incremental
verdict writes carrying an explicit incomplete/final marker; and a partial or
refusal-truncated stream supplies FINDINGS for seat-4 adjudication but never
authorizes ship and never counts as reviewer-declared convergence.

### The execution-environment axis (review-convergence)

1.2.6 shipped through 21 review rounds — every voice on the same Windows
host — and went red on Linux CI within minutes of landing: three tests invoked
`cmd.exe`, and POSIX raises before any result exists. Nobody missed it; nobody
could have seen it — the loop had no POSIX voice. That is the mis-scoped
bundle one axis over: bundles scope WHAT is reviewed, environments scope WHERE
it runs. New rules: the round request enumerates the shipping environments
alongside the artifact set; every environment gets an ACTUAL EXECUTION
wherever runnable coverage exists (a contract or CI matrix handed to a seat is
static review, not coverage — launch-time failures are only observable by
running); an environment with no runnable coverage is recorded UNEXECUTED and
the residual risk explicitly escalated or accepted. Anti-pattern named: the
single-platform chorus.

### Verification instruments are ship evidence (review-core, new section)

Two burns in one wave: a fix-verification probe printed a false green over an
ImportError (its ok-heuristic missed a lowercase `errors=3`), and a mutation
test stayed green because a DIFFERENT guard than the one under test satisfied
its assertion. The instrument that certifies the gate deserves the gate's own
distrust: bind to the most structured result surface the tool has and to the
EXACT messages the specific guard emits; prove the subject actually RAN and
fail launch/import/collection errors CLOSED to RED; prove every new guard
load-bearing by mutation/deletion, and disclose the un-forcible ones as
defense-in-depth instead of faking coverage.

### The wake gate fails closed when its tool is absent (wake command + every wake path)

Field finding, two workspaces, same day (2026-07-16): a workspace without its
vendored `tools/conformance_check.py` silently NO-OPS the prescribed wake
gate — the gate "passes" by never running, and nothing red appears precisely
because nothing ran. The wake step now fails CLOSED: a missing gate tool is
itself a BLOCKER-class structural finding; the wake runs the trusted copy from
the protocol checkout instead and surfaces the absence to the principal (a
clean trusted-copy run does NOT clear it); no protocol checkout to source a
trusted copy from either = the gate cannot run at all, HARD STOP; only the
principal's explicit word — affirmative, first-person, in THIS session —
waives the missing-tool BLOCKER, and every other BLOCKER is resolved, not
waived. Round 1 of this release's own review then proved the rule mis-scoped
in exactly the way it warns about: the documented SKILL-LESS wake path (the
accepted baseline for unattended and cloud routines — the very environment
that produced the field finding) never reached the `/wake` gate at all. So the
gate now lives in all three role START_SESSION contracts too, the operator
docs stop claiming the checker is "not stamped into each workspace" (it is,
and its absence is the finding), and — the one deliberate deviation from this
release's docs-only scope — `tools/conformance_check.py` itself now lists the
vendored checker as a required file, so a trusted-copy run against a degraded
workspace reports the absence structurally instead of trusting the waking
agent to remember to look. An instruction to check is the same class of gate
this unit distrusts; the required-file line is the load-bearing form.

## [1.2.6] — 2026-07-15

**The fix reproduced the bug it fixed.** 1.2.5 was a release about rules that
were right but mis-scoped. Porting it to a mirror tree exposed, within the hour,
two mis-scoped rules **inside 1.2.5 itself**. That is not an embarrassment to
bury in a patch note; it is the thesis holding, and the only honest thing to do
with a thesis that holds is to say where it held.

### `.ps1` inverts the no-BOM rule — and 1.2.5's gate would have caused the corruption it warns about

Windows PowerShell 5.1 decodes a BOM-*less* UTF-8 `.ps1` as **ANSI**. Every
non-ASCII byte is mangled. Verified on 5.1.26100, not recalled:

| the same script, saved two ways | what PowerShell prints |
|---|---|
| UTF-8, **no** BOM | `sect=Â§ dash=â€” acc=Ã©` |
| UTF-8, **with** BOM | `sect=§ dash=— acc=é` |

`Â§`, `â€”` — that is the exact mojibake `ops-gotchas` has warned about for
releases. This is where it is **born**, not merely where it is seen. So the
repo-wide "no BOM anywhere" gate 1.2.5 shipped would, pointed at a `.ps1`, have
**instructed you to author the corruption the protocol exists to prevent** — the
same shape as the 1.2.4 defect that started this whole thread, now wearing a CI
badge. (It never fired: this repo tracks no `.ps1`. It was a trap set for the
first person to add one.)

- PowerShell **script files** — `.ps1`, `.psm1`, `.psd1` — are exempt from the
  no-BOM rule and get the **inverse** check: non-ASCII bytes with **no** BOM is a
  finding that names the mangling. A silent carve-out would have been the lazy fix;
  it leaves the real bug — a script that corrupts its own output — unguarded.
  **An exception you cannot state as a rule is a hole.**
  (The first cut of this fix keyed on `.ps1` alone. A reviewer verified that `.psm1`
  goes through the same script reader and mangles identically — so the trap was still
  armed one extension over, and *worse* than before: the docs now tell you to save
  PowerShell with a BOM, so an author obeying them for a module file got red-gated by
  the fix itself. The rule binds the **format that has the behaviour**, not the
  example that revealed it. Excluded, stated: `.ps1xml`, which .NET reads as XML.
  Round 2 then repeated round 1 verbatim: `.psrc` (role capability) and `.pssc`
  (session configuration) are *data* files, but the engine loads both through the
  same reader — `Import-PowerShellDataFile` mangles a BOM-less `.psrc` identically,
  with no extension check anywhere on that path — and the fixed gate was still
  red-gating a correctly BOM'd one. Same defect, same fix, one extension over,
  inside the release that fixed it. All five suffixes are now bound, both
  directions tested.
  And round 3 found the fold had reached the code, the tests, and this CHANGELOG —
  every surface except the **normative prose**: corollary (d) and both
  `ops-gotchas` still taught the three-suffix set, so a reader obeying the
  normative doc for a `.psrc` saved it BOM-less and walked straight into the gate
  — three reviewers, independently, the same finding, one of them adding that a
  maintainer who "simplified" the gate back to match the doc would re-open the
  round-2 hole *with the doc as their justification*. The passages now enumerate
  all five suffixes and name **both consumers**, and the agreement is a check,
  not a claim: `mirror_check` derives each guidance file's documented suffix set
  from its `.psX`-shaped tokens — **case-insensitive and two-tier** (round 4:
  `.PS2` in caps and bare `.ps2` in prose were both invisible to a
  lowercase-backticked-only pattern; round 5: deriving from *every* raw token
  over-corrected, and a passing filename mention — "a fixture named
  archive.ps2" — drifted the set and red-gated the file. A backticked token is
  guidance wherever it sits; a bare token counts only on a line that speaks of
  the BOM, because the inversion *is* about the BOM. Round 6: that cure was
  itself two substrings too loose — the `.ps2` *tail* of `archive.ps2` matched
  the bare pattern, and the `bom` inside "bombproof" activated the tier, so a
  filename mention false-red'd the moment its line also genuinely discussed
  the BOM. A bare token must be lexically **standalone** and the BOM term a
  **bounded word**. Round 7: the round-6 bounding was itself mis-scoped one
  alternation over — the boundaries bound only to `boms?`, leaving
  `byte-order` an unbounded substring, so "byte-ordering" re-opened the same
  false red; the boundaries now wrap the whole alternation, and all five
  phrasings are pinned green) — and compares it with the
  set the gate enforces, so prose can no longer regress on its own. The gate
  holds the suffix **set** in parity, not the semantics: a doc listing all five
  but attributing the wrong *reader* to one is a reviewer's catch, and says so
  in the source.)
- `channel-core` gains corollary **(d)**: the byte rule is **per-format**, at least
  one format inverts it, and you must know what a format's real consumer does with
  the leading bytes *before* you gate it.

### A tree may now declare what it is (`.mirror-check.json`)

1.2.5 fused two different claims: *"this artifact must exist here"* and *"if it
exists it must agree with its twin."* Fusing them closed a real hole (deleting a
twin used to pass the twin gate) — and made the checker structurally unrunnable
in any tree that does not carry the docs by design. In the private mirror it went
**10-findings red**, permanently. **A gate nobody can ever see go green is not a
gate; it is a thing people learn to scroll past** — which is the failure this
checker exists to prevent, so it must not be the failure the checker causes.

A tree may now declare itself, and the declaration is **bounded** — an unbounded
one is just a bypass with a config file in front of it:

- it may switch off the docs-tree **existence** gates; it may **not** switch off
  their consistency checks. Whatever *is* present is still compared — and **half a
  twin pair is still a finding in every tree**, so the original hole stays shut.
- it may exempt **enumerated** paths from the version-stamp gate, each with a
  **non-empty reason** (stamp exemptions exist for files whose *bytes* are
  load-bearing — a byte-identical custody copy, where stamping a banner destroys
  the guarantee the file exists to give).
- it may **never** switch off the BOM gate.
- it may never be **silent**: every relaxation in force is printed, with its
  reason, on every run — green or red. A reduced run that prints a bare "green" is
  a lie by omission.
- it must be **tracked**. A file that relaxes gates has to be visible in the diff
  that relaxes them; an untracked declaration is refused. (Both reviewers used one
  to relax a local run invisibly.)
- a **stale** entry (exempting a path that isn't there) is itself a finding: a list
  that outlives its files quietly becomes a bypass. Paths are confined to the tree.
- an exemption names **where the file sits, never where a path points**. The
  exemption map was keyed by *resolved* path, so a directory junction (or
  symlink) at an unlisted path whose target was declared exempt **inherited the
  exemption** — the declaration reviewed one path and quietly exempted another
  (a junction is the alias shape `is_symlink()` cannot see). Keying and the
  stamp lookup are lexical now; resolution serves only to confine entries to
  the repo; a `..` segment — which would make the lexical key and the file it
  names disagree — is refused outright.
- a **hostile** path — a `..` segment, a path resolving outside the repo — refuses
  the **whole declaration**, not just its own entry. It was first cut as a
  per-entry finding inside the exemption pass, which runs *after* the other
  declaration fields take effect: a declaration carrying one hostile entry kept
  its `docs_tree` relaxation active while the red run under-reported. A hostile
  path was never a typo and never legitimate drift — nothing else in a file
  carrying one deserves trust. (A **stale** entry stays a per-entry finding:
  drift is not hostility, and the run is red either way.)
- the declaration file itself must be a **regular file**. The tracked-ness
  control checked only the PATHNAME, so a tracked *symlink* (git mode 120000)
  satisfied it while the effective bytes came from an **untracked target no
  diff ever reviewed** — the reviewed bytes must BE the bytes.
- **duplicate JSON keys are refused at every object level.** A plain parser
  keeps the LAST duplicate, so `{"docs_tree": true, "docs_tree": false}` reads
  as reviewed-strict while enforcing relaxed — it hid a full docs-artifact
  deletion behind a green run. Duplicate `stamp_exempt` entries are refused
  for the same reason one layer down: both reasons print, one is in force.
- an exemption path must be spelled in **canonical repo-relative POSIX form**.
  The loader accepted backslashes, trailing slashes, `.` segments, and
  absolute in-repo paths, then *normalized* them into the lexical key — a
  declaration whose visible spelling is not the enforced key, and which means
  something different (or goes stale) on another OS. A lexical key has
  exactly one spelling.
- and that spelling must match the tree's **exact on-disk names**. Canonical
  form was not enough: `is_file()` answers case-insensitively on Windows, so
  `Transports/x.md` passed every check, printed its reason, exempted *nothing*
  (the lexical key never matches the walked path) — and reads as stale on a
  case-sensitive host. One declaration, one meaning, every host.
- a defective declaration is **ALL-OR-NOTHING**: any defect — bad JSON, a BOM, an
  unknown key, a non-boolean, a reason that is not a real non-empty string — grants
  **nothing** and runs the full gate set. The first cut honoured a broken declaration
  *piecemeal*: it stripped a BOM and carried on, and a typo'd key raised a finding
  while the keys it understood still took effect. Both reviewers walked straight
  through that. `"reason": null` was the sharpest case — the code did
  `str(reason)`, which turns `null` into the perfectly non-empty string `"None"`, so
  a reason-less exemption passed green. **Coercion is not validation**, and partial
  trust in a config whose whole job is to weaken checks is a bypass with extra steps.
- **no declaration = the previous strict behaviour, exactly.** The default is not
  trusting; the default is strict.

### Also

- **Existence is its own gate.** Every content gate validates a file only if it
  is PRESENT — so deleting `transports/` outright, either shipped transport
  profile, a whole role tree, or any role's `SKILL.md` entrypoint was **green**:
  an acceptance gate certifying a release that no longer ships what it says it
  ships. The shipped transport profiles and all four skill entrypoints now have
  explicit existence findings (the docs tree already had them; absence there is
  declarable because a mirror legitimately lacks it — a transport-less or
  role-less tree is not a mirror, it is a gap). And the first existence list
  was itself treated as complete when it was not: `profiles/README.md`,
  `profiles/MODELS.md`, and `tools/new_project.py` were still
  deletable-to-green — the last one silently *disarming* the auth-log drift
  gate, whose byte-match is conditional on both files being present — and
  `docs/CLOUD.md`, the doc half of the shipped git-sync transport, joined the
  docs-tree existence set (declarable, like its siblings).
- **The whole-repo enumeration fails closed.** `Path.rglob()` *suppresses* the
  OSError from a directory it cannot list, so the BOM gate — which claims every
  shipped and untracked file — silently skipped an unlistable directory and the
  untracked BOM'd file inside it. The enumeration now walks with the same
  fail-closed onerror rule the guarded trees have: a directory the gate cannot
  read is unknown, not clean. Scratch directories the gate never claims
  (`node_modules`, caches, virtualenvs) are *pruned before descent* — an
  unlistable one of those must not red the gate either, and tracked files
  under them still arrive through the tracked-set tail, which is exactly the
  path that reads them.
- **The tracked-file names themselves are hostile input.** Three ways one
  visible worktree file was certifying a released blob the gate never read:
  git emits pathnames as UTF-8 bytes but `text=True` decoded them with the
  *Windows locale* — a tracked `café.md` became a phantom path, the real file
  read as untracked-and-skipped, and its BOM'd blob was invisible to the very
  gate that claims tracked files; a segment ending in a dot or space (or
  naming a Windows device) is stored fine in the index but ALIASES to its
  trimmed twin on Windows — `x.md` clean and stamped, `x.md.` carrying an
  unstamped BOM'd blob, green; and two index entries differing only in case
  (or only in Unicode normalization) each carry their own blob while the
  case-insensitive worktree shows ONE file. Tracked names are now decoded as
  UTF-8 with undecodable names failing closed, non-portable segments are
  findings, and collisions are detected on the raw `git ls-files` names under
  an NFC + casefold + dot/space-trim key — Windows `Path` objects collapse
  the variants before any later gate can see them.
- **The index, not the worktree, is what git publishes.** Every byte gate read
  worktree bytes — but a commit or archive ships the *index blob*, and the two
  are not the same file: a BOM'd blob swapped into the index behind a clean
  worktree twin was green, a tracked file deleted from the worktree fell out
  of the tracked-set tail *silently*, and an index entry whose name cannot
  even materialize on Windows was green three ways. Now the tail's silent drop
  is a finding ("tracked path missing from the worktree"), non-regular and
  unmerged index entries are findings (a symlink entry publishes its target
  path as the blob; a gitlink publishes a commit the repo does not contain),
  and every entry whose worktree bytes *diverge* from its staged blob has the
  staged blob itself pushed through the byte gates — the BOM gate for every
  file class, the mojibake scan for skill-tree `.md` files. A routinely dirty
  tree stays green: the divergent blob of an ordinary uncommitted edit is the
  last committed content, which passed these same gates when it landed. The
  divergence enumeration itself then fell twice in one round: `git diff`
  *ignores* entries flagged `assume-unchanged` or `skip-worktree` by design,
  and a same-size staged blob behind an unchanged stat cache is never
  content-compared at all — two green defeats of asking git *which* entries
  diverge, one round after the channel "closed". So the scan stopped asking:
  every stage-0 regular blob is read directly by object id (one `cat-file`
  batch, its header parsed defensively so a malformed or truncated response
  is a fail-closed finding, not a traceback that loses the findings already
  collected) and compared with its worktree twin in-process — nothing for a
  flag or a stale stat cache to mute — and the flags are *also* findings in
  themselves, because an instruction not to compare an entry is an entry the
  gate cannot certify. The staged-blob mojibake leg selects on the
  *normalized* suffix (a staged `UPPER.MD` blob took the BOM leg only), and
  the alias guard accepts exactly one normalization-equivalent, case-exact
  on-disk entry per segment — macOS decomposes filenames while git stores
  the precomposed spelling, so byte-exact comparison would have called every
  non-ASCII tracked name an alias on the platform behaving correctly (case
  variants and 8.3 names never normalization-match; ambiguity stays a
  finding). The stamp and content gates still certify the worktree
  spelling — stated, and covered where releases are actually cut, because on
  a fresh checkout index and worktree coincide. The first non-portable cut was also incomplete —
  it knew trailing dot/space and the classic device stems, and accepted
  `bad?name.md` (Win32 forbids the character outright), `CONIN$` (a console
  device the classic list omits), and superscript-digit `COM¹` (Windows reads
  `¹²³` as digits in device stems); all are findings now. And an index name
  that merely *resolves* to a differently spelled worktree file — an 8.3
  short name (`LONGNA~1.MAR` answering for `longnamefile123.markdown`), a
  lone case variant with no second tracked entry for the collision key to
  pair it with — is a finding by exact-spelling comparison against the
  on-disk names, which closes the alias *family* rather than its enumerated
  members.
- The checker forces its own stdout to UTF-8. Its findings quote `§ — é`; piped on
  Windows, printing one would have raised `UnicodeEncodeError` and crashed the gate
  **while reporting the one defect that is Windows-specific**. A gate that cannot
  say what it found has not found it.
- `channel-core.md` joins `ops-gotchas.md` in the mojibake gate's example-text
  exemption — it now has to *show* the corruption it legislates about. Widening an
  exemption is how a gate goes quietly blind, and this gate went blind **twenty-six
  times** before it held:
  - **Cut 1** asked whether a backtick appeared in the preceding 40 characters — which
    is equally true of the text *after* a closed span. Real corruption on any line that
    also held a code span went green. Both reviewers demonstrated it on the shipped file.
  - **Cut 2** used backtick **parity**, which locates a span correctly — but "you are
    inside a span" was never the licence. Corrupting the em dash of the *clean* example
    `` `§ — é` `` yields mojibake **inside** a code span, and it was waved through.
  - **Cut 3** was defeated by its own comment. It *said* "fenced blocks get no
    exemption" and the code never looked at a fence, so corruption pasted into a
    ` ``` ` block and wrapped in backticks still passed — a claim standing in for a
    check, in the release whose entire thesis is that a claim is not a check.
  - **Cut 4** was blind in the *detector*, not the exemption: it enumerated two
    markers (`â€`, `Â§`) — the two characters the example spans happen to show. A
    line-by-line corruption sweep of the guarded files (encode UTF-8, decode
    cp1252 — the exact defect) missed **18** corruptible lines, every one a line
    whose only non-ASCII is `→` or `⚠` — *including the `.ps1` bullet this very
    release added*. (Independent sweeps agree on the **18-line gap** and have
    never agreed on the corpus total — a round-4 reviewer caught three surfaces
    of this release each quoting a *different* total — so the gap is the only
    number stated, here, in the checker's comments, and in the tests. A number
    that does not reproduce does not get written down.) An enumerated marker
    list is the enumerated suffix list one section up, re-shipped.
  - **Cut 5** was the fence fix reproducing the fence hole one line up: cut 3's
    repair toggled the fence state and skipped to the next line, so the
    **delimiter line itself** was never scanned — mojibake in a fence's info
    string passed, in the round after the release said "a fence exempts
    nothing".
  - **Cut 6** was the repaired detector, still enumerating: four lead characters
    cover the docs' *current* repertoire, and `Ā` (lead byte 0xC4) mangles to
    `Ä€` one code point outside it. Honest scoping is not coverage.
  - **Cut 7** was the fence tracker itself. It keyed on `startswith("```")` —
    and CommonMark fences come in **tildes** too, and close only on a run of the
    *same character at least as long* as the opener (which is exactly how a
    document quotes a three-backtick fence literally: wrap it in four). A `~~~`
    fence never registered, so its body was scanned as prose *with the span
    exemption available*; a ```` fence was closed early by the very ` ``` ` line
    it was quoting. Both mis-parses landed on the **exempting** side. One state
    machine now owns fence shape for every consumer in the checker, and its
    failure mode is biased the other way: a line that even looks like a
    delimiter is treated as one, which can only widen scanning, never the
    exemption. (Closing is stricter than opening: a closer carries **nothing**
    after its run — info text belongs to openers — so a ` ``` ` line with
    trailing text inside a fence is content, not an early exit back into
    exemption territory.)
  - **Cut 8** was the truncation exception, enumerating **one instance of a
    family**: `â€` (E2 80) was special-cased because these files document it,
    and its siblings fail the round-trip identically — `â‚` (E2 82, a beheaded
    currency sign) and `ðŸ` (F0 9F, a beheaded emoji) were waved through. A
    truncated mangle has, by definition, lost the bytes that would prove it
    corruption, so this exception *cannot* be a class rule. And the first cure —
    three hand-enumerated families — **violated its own charter within one
    round**: "blocks that actually occur in text this project ships" was three
    entries while the tree itself ships arrows and warning signs, whose
    truncated mangles `â†` (E2 86) and `âš` (E2 9A) sailed through. The
    families are now **derived**: every 3-plus-byte character the skill tree
    carries contributes its 2-byte prefix, plus three stated seeds met in the
    wild that survive their characters leaving the tree. A hand-kept list lags
    its corpus; a derived one cannot.
  - **Cut 9** was the fence tracker again, one container over: a fence can open
    inside a CommonMark **list item** (`- ```……`) or **blockquote** (`> ````), and
    the delimiter hid behind the marker — the fence never registered, its body
    was scanned as prose *with the span exemption available*, and an
    allowlisted span inside it was waved through. Container prefixes are now
    peeled before the delimiter match.
  - **Cut 10** was cut 9's cure, and it disproved cut 9's own safety claim.
    The first peel was greedy — any marker, any line — on the argument that
    over-peeling "can only make more lines read as delimiters, which widens
    scanning." False: peeling a list marker on a line **inside** an open fence
    manufactured a delimiter where CommonMark sees literal text, and the
    manufactured delimiter **closed the fence** — handing every following line
    back to the span exemption. `- ```` ` inside a ```` fence, or `> ``` `
    inside a bare fence, was an exit door. A false delimiter *outside* a fence
    widens scanning; the same false delimiter *inside* one widens the
    exemption — the claim held for openers only. Peeling is now
    **asymmetric**: outside a fence, peel everything (that direction really is
    safe); inside, peel exactly the opener's blockquote depth — a quote-opened
    fence repeats its `>` prefix on every line including the closer — and
    never a list marker. A closer must match the opener's depth exactly; a
    run at the wrong depth is content.
  - **Cut 11** was the same door with an indentation key: CommonMark allows at
    most THREE spaces on a closing fence — four spaces or a tab make the run
    literal fenced content — and the closing path accepted `\s*`, so a
    four-space-indented ` ``` ` inside a fence manufactured a closer and
    restored the exemption (an over-indented `>` marker at quote depth 1 did
    it too). The closing path now takes 0–3 spaces, spaces only, on both the
    run and the quote markers; the OPENING path stays liberal, because a false
    opener only widens scanning and that asymmetry is now the stated design,
    not an accident.
  - **Cut 12** was the span finder, which had never actually parsed a span.
    Backtick PARITY (split on backticks, odd segments are code) counts every
    backtick as a delimiter — so an **unclosed** backtick licensed everything
    after it, and a backslash-**escaped** backtick, which CommonMark reads as
    literal punctuation creating no span at all, opened an exemption: the
    exact allowlisted payload sat in bare prose behind a stray backtick and
    passed. A span now exists only where CommonMark closes one — an opening
    run of N backticks, closed by the next run of exactly N, escapes literal
    outside spans, unclosed runs granting nothing.
  - **Cut 13** was the coverage gate checking the **wrong population** — and it
    is the enumeration mistake a third time, disguised as its own cure. The
    prose side's blind range was "held" by a gate proving every character IN
    THE TREE has a detectable mangle. But corruption arrives as the mangle of
    whatever text someone pastes: mangled Ö (`Ã–`) landed green in a live
    skill file — the prose side read it as Ã-plus-en-dash, and the coverage
    gate stayed silent because Ö was never in the tree while the mangle's
    component characters individually pass. Two fixes, both shipped: a
    prose-shaped candidate whose bytes decode to **Latin-1 Supplement** text
    is corruption (Ã hard against writer typography is vanishingly rare;
    mangled Western-European text is the most common corruption there is —
    the French and German pins stay green because their decodes land outside
    Latin-1), and the coverage gate now sweeps a **fixed support alphabet**
    (all printable Latin-1 plus the living tree) so the guarantee no longer
    depends on what the tree happens to carry. What remains blind is stated
    and pinned: a mangle that decodes outside Latin-1 with all-typography
    continuations — NKo ߗ reads as `ß—` — reds at arrival via the coverage
    gate, and « (two rounds the pinned blind character) is now welcome, its
    mangle visible.
  - **Cut 14** was cut 11's own safety claim, disproven the way cut 10
    disproved cut 9's. The opening path had stayed liberal "because a false
    opener only widens scanning" — and a reviewer inverted the fence PHASE
    through it: a 4-space-indented ` ``` ` is indented code to CommonMark,
    not a fence, but the liberal opener registered it, consumed the REAL
    opener on the next line as its closer, and the true fence's body was
    scanned as outside-fence prose with the exemption available. In a
    two-state toggle, a false delimiter in EITHER direction flips every
    classification after it — three "this direction is safe" claims fell in
    three consecutive rounds (greedy peeling, liberal closers, liberal
    openers), so no direction gets to be liberal: fence runs and container
    markers count only behind 0–3 spaces, spaces only, on BOTH paths,
    exactly as CommonMark reads them, with the bound living in the fence
    regex itself so every consumer inherits it. Stated residual, pinned in a
    test: a fence nested in list content at 4+ absolute spaces reads as
    indented code (this machine is absolute; CommonMark is
    container-relative), and its body keeps the exemption available —
    bounded severity, because the exemption licenses only the three exact
    documented strings, and any other mojibake there still reds.
  - **Cut 15** was cut 14's machine still one **block type** short. CommonMark
    HTML BLOCKS swallow fence-looking lines: `<script>` opens an HTML block
    and a ` ``` ` inside it is HTML content — but the fence-only machine
    registered it as an opener, consumed the REAL opener on the next line as
    its closer, and the true fence's body was scanned as outside prose with
    the exemption available. The same phase inversion as cut 14, reached
    through a block type the machine did not model. The block phase now
    tracks all seven CommonMark HTML-block kinds: the five marker-terminated
    ones (raw-text tags, comments, processing instructions, declarations,
    CDATA — each may end on its own start line) and the two blank-line-ended
    ones (block-level tag names, and any complete tag alone on its line —
    which fires only after a blank line, because it cannot interrupt a
    paragraph; without that rule a custom tag mid-paragraph would open a
    phantom block whose first blank line hands the text after it back to the
    exemption). Every line of an HTML block is scanned with **no exemption**,
    exactly like a fence.
  - **Cut 16** was the prose side's stated Latin-1 boundary sitting one block
    too low. Mangled French œ (`Å“`) walked through: the left curly quote IS
    writer typography and U+0153 sits just beyond Latin-1 Supplement, so the
    cut-13 rule never fired — everyday French (cœur, œuvre) was the blind
    range's most representative resident while the narrative advertised only
    exotic NKo. cp1252's own extension letters (ŒœŠšŽžŸƒ) are exactly the
    non-Latin-1 letters a Windows-ANSI writer produces, so the corruption
    side now takes them too; only Œ œ Š ƒ arrive through the prose branch
    (the other four carry a non-typography continuation byte and already
    round-trip-flag). Stated cost, accepted: a REAL Å or Æ hard against an
    opening curly quote or NBSP now reads as corruption — a rare adjacency,
    and a loud false red beats silent corruption. The letters joined the
    coverage gate's support alphabet, so CI itself defends the widening.
  - **Cut 17** was cut 15's paragraph rule built on a PROXY. "Cannot
    interrupt a paragraph" had been implemented as "fires only after a blank
    line" — and a paragraph is ended by more than blank lines. After a
    closed FENCE (the reviewer's reproduction), an ATX heading, a thematic
    break, or a setext underline, a lone complete tag IS eligible to open an
    HTML block with no blank line in sight; the proxy read it as prose, the
    fence-looking line after it registered as an opener, and the phase
    inverted exactly as in cuts 14 and 15 — the third round in a row the
    inversion arrived through a block shape the machine approximated instead
    of modeled. The machine now tracks the paragraph itself: a plain prose
    line opens one; a blank line, a fence opener, any HTML-block line, an
    ATX heading, or a thematic break closes it; a setext underline closes
    one only while it is open (alone it is paragraph text); an indented line
    or a `[`-led line outside a paragraph stays outside one (indented code /
    link reference definitions — the `[` test is a stated approximation that
    errs on the scanning side). A lazy continuation — an indented line
    *inside* a paragraph — keeps it open, pinned in a test.
  - **Cuts 18–21** arrived in a single round, and that is the finding. **Cut
    18** was cut 17's own stated approximation, disproven the following
    round — the FOURTH consecutive "this direction is safe" claim to fall:
    `[ordinary paragraph]` is paragraph text, not a link reference
    definition, so the `[`-led rule that "errs on the scanning side" left
    the machine outside a paragraph, a mid-paragraph custom tag opened a
    phantom HTML block, and the phase inverted. **Cut 19** was container
    scope: the machine tracked block state globally while CommonMark scopes
    it per container, so a fence or `<script>` opened *inside* a blockquote
    leaked its open state past the quote's end — text outside the quote
    scanned as inside-block, the real fence's body as outside prose. **Cut
    20** was list interruption: an ordered-list item can interrupt a
    paragraph only when its marker is `1.`, so `2.` followed by a fence
    after a paragraph is paragraph *text* — but the container peel read the
    fence behind it unconditionally, phantom opener, inversion. **Cut 21**
    (the judge's find, its first inversion): a backtick fence's info string
    may not contain a backtick, so ```` ```x`y ```` opens nothing — but the
    fence regex accepted it, and the real fence one line down closed a
    phantom.
  - **Cut 21 is where the cure changed species.** Eleven of the twenty-one
    cuts to that point (7, 9–11, 14, 15, 17–21) were the SAME defeat: some line shape
    CommonMark and the machine's model classified differently, with the
    difference putting a licensed span back in reach. Four in one verdict is
    the space announcing it is not enumerable by hand — so round 11 did not
    add four rules, it **retired the model**. The licence no longer consults
    a document model at all: a mojibake candidate is exempt **iff its entire
    line is byte-identical to one of five enumerated documentation lines**,
    keyed by exact repo-relative path. A byte-identical line can carry no
    *new* corruption by construction, and every other line — fence body,
    HTML block, delimiter line, list item, blockquote, wherever CommonMark
    would say it sits — is scanned unconditionally. There is no block phase
    left to invert: the fence state machine, container peeling, the seven
    HTML-block kinds, the paragraph tracker, and the span parser are
    deleted, and the line shapes that defeated them live on as red tests
    against the *new* licence. The trade is stated: a *clean* edit to a
    documented example line now reds until the allowlist is regenerated — a
    loud false red on the five lines whose whole job is to be exact, bought
    against a licence that ten rounds could not stop inverting.
  - **Cuts 22 and 23** were the retirement's own first round of review, and
    both sat in machinery the new licence still had to trust. **Cut 22**:
    the scanner's line unit was `str.splitlines()`, which also splits on
    VT, FF, NEL, U+2028 and U+2029 — none of which ends a *markdown* line.
    "junk + VT + licensed line" is ONE modified line to any renderer,
    carrying the licensed mangled bytes — but the scanner saw two lines,
    and the licensed suffix exempted itself. A line now ends only where
    markdown ends one (CRLF, CR, LF), which makes the construct a single
    byte-different — and scanned — line; the liveness gate uses the same
    unit, so an example surviving only as such a suffix is STALE, not
    carried. **Cut 23**: the licence was keyed through `resolve()`, so a
    symlink at an *unlisted* path answering with an exempt target's
    content inherited the target's licence — round 3's basename
    inheritance rebuilt through the filesystem — and a symlink pointing
    outside the tree **crashed the checker** on an unguarded
    `relative_to` before it printed the findings it had already collected
    (round 3's unguarded-read class, arriving through resolution instead
    of absence). Keying is lexical now — where the file *sits*, never
    where it points — and a symlink in the guarded tree is itself a
    finding, its content scanned with no exemption.
  - **Cut 24** was cut 23's rule enforced only on the files the walk could
    SEE. The symlink finding ran per `*.md` file out of `rglob` — and
    `rglob` does not look through a symlinked **directory**, so aliasing a
    whole skills directory hid its guarded content from every gate in the
    checker with no finding at all: a walk cannot police the thing it
    cannot traverse. And a Windows **junction** is a reparse point for
    which `is_symlink()` answers False — the alias shape a symlink-only
    rule walks straight past. Both guarded trees (skills and transports —
    each carries a path-keyed gate) are now swept for **reparse points of
    every kind**, file or directory, symlink or junction, and any one of
    them is a finding in itself.
  - **Cut 25** was cut 24's sweep never statting its own starting point.
    `os.walk` yields only *descendants* — it never inspects the root it was
    handed — so a junction replacing an **entire guarded tree** walked
    straight through the sweep and the gate came back green over a tree
    supplied wholesale through an alias: the exact defeat cut 24 closed,
    one level up. Each guarded root is now checked for reparse status
    before the walk begins.
  - **Cut 26** was the walk going silently blind instead of loudly. Without
    an `onerror` callback, `os.walk` *swallows* the `OSError` from a
    directory it cannot list and simply ends that branch — an
    access-denied directory full of unstamped or licensed bytes came back
    green, with nothing in the output to say a corner of the tree was
    never looked at. A directory the gate cannot read is not clean, it is
    **unknown**, and unknown fails closed: every unlistable directory and
    every unstattable entry is now a finding naming the path the scan
    could not reach.
  - The detector also produced false **rejects**, and the first cure repeated
    the enumeration mistake in mirror image. `ß` renders lead byte 0xDF, and
    `groß—aber` is DF 97 in cp1252 bytes — **valid UTF-8**, so the round-trip
    validator *confirms* legitimate German as corruption. Round 4 excluded that
    one lead; round 5 proved the class: `É—` (C9 97) and `é—“` (E9 97 93)
    round-trip identically, because cp1252 renders the **whole lead range as
    accented European letters** — any of them against smart punctuation can
    form valid UTF-8. The ambiguity is symmetric and locally undecidable (the
    bytes of `Ã–` are both a mangled Ö and French prose), so the detector now
    takes a stated **side**: a candidate whose continuation characters are all
    typography a human types directly after a word (13 characters; low quotes
    deliberately absent — they open, so they follow spaces, and their absence
    keeps mangled `ł` visible) is read as prose — **unless its bytes decode to
    Latin-1 Supplement text** (cut 13: mangled Ö is exactly Ã-plus-en-dash,
    and corruption is the likelier reading of that shape by a wide margin).
    The blind range the prose side still buys is stated — a mangle decoding
    OUTSIDE Latin-1 with all-typography continuations, like NKo `ߗ` reading
    as `ß—` — and it is held by a **detector-coverage gate** over a **fixed
    support alphabet** (all printable Latin-1 plus every character the tree
    carries): a character whose mangle the detector cannot see is a finding
    the day it arrives, not the day it corrupts. German and French are pinned
    green in tests; `ߗ` landing in the tree is pinned **red**; `«` — blind
    for two rounds — is pinned **welcome**, its mangle now visible.
  - **What holds:** the detector matches the **structure** of a mangle, not a
    list of them — the cp1252 rendering of any UTF-8 lead byte (0xC2–0xF4)
    followed by renderings of continuation bytes (0x80–0xBF), confirmed by
    **round-trip**: mapped back to its bytes, real corruption *is* valid UTF-8,
    by construction. Prose almost never survives that test — `café…` fails it
    (é opens a three-byte sequence and no third byte follows) where a bare
    character-class rule would have flagged it as corruption. One stated
    exception class: the truncated prefix families (cut 8) — **derived** from
    the tree's own characters plus three stated seeds — flagged although they
    do not round-trip, because they are real-world corruption. One stated
    prose side: all-writer-typography continuations that decode beyond
    Latin-1 and cp1252's extension letters read as prose (cuts 13 and 16),
    with the blind range it buys held by the
    **detector-coverage gate** over its fixed support alphabet. The
    five bytes cp1252 leaves undefined ride along as C1 controls, so a mangled
    `❤` is not invisible for lacking a glyph. Block shape no longer exists
    in the checker at all: since cut 21, **every** line — fence body, HTML
    block, delimiter line, list item, blockquote — is scanned
    unconditionally, because the machinery that decided otherwise is
    retired along with the eleven defeats it collected, and the line shapes
    that beat it stand as red tests against the licence that replaced it.
    The permitted occurrences stay **ENUMERATED** and got *stricter*: five
    exact documentation **LINES**, keyed by exact lexical repo-relative
    path — a candidate is exempt only when its entire line (ended where
    markdown ends one: CRLF, CR, LF) is byte-identical to one of them, and
    a byte-identical line can carry no new corruption by construction. A
    reparse point in either guarded tree — file or directory, symlink or
    junction, at the root or below it — is a finding in itself, because
    every path-keyed gate is only as honest as the tree's paths, and a
    directory the sweep cannot list is a finding too: a gate that cannot
    read a corner of the tree does not get to call that corner clean. (The
    five are
    escape-spelled in the source, generated from the guarded files
    themselves, so what the licence permits is provably what the docs
    carry — and the liveness gate keeps it that way.)
  - The allowlist must also stay **live**, on three axes now that it licenses
    lines: a licensed line the file no longer carries is a finding (**stale** —
    an allowlist that outlives its text goes on licensing a string the docs
    abandoned), a licensed line that licenses no detectable mangle is a finding
    (**dead** — it exempts nothing today and quietly pre-licenses whatever
    corruption lands on that exact line tomorrow), and an allowlist key naming
    a path outside the exemption list is a finding (the licence and the
    exemption list must name the same files).
  - The licence is also conditional on a **presence**. The allowlist permits the
    *mangled* strings — so swapping the **clean** example `` `§ — é` `` for its
    mangled twin passed every check above: the trio is a licensed span, and no rule
    said the clean text must still be there (the judge performed exactly that swap
    and the gate said green). Each exempt file must still carry the clean example;
    a file showing only the mangled bytes is a corrupted file with a permit.
  - And the licence is keyed by **exact path** and conditional on **existence**.
    It was keyed by *basename* — any future file named `ops-gotchas.md`, anywhere
    in the tree, inherited the exemption unreviewed — and the exempt set was
    derived from the files found on disk, so **deleting** a licensed file deleted
    every check that ran on it: a reviewer proved the presence gate vacuous by
    removing the helper copy outright, and the gate said green over a file that
    was gone. A missing licensed file is now a finding — same rule as the twin
    pair: absence is never a smaller quorum. Writing the test for that exposed
    one more: deleting `channel-core.md` itself **crashed the checker** on an
    unguarded read before it printed a single finding it had already collected —
    red for the wrong reason, report lost, the stdout-guard defect class arriving
    through the filesystem instead of the codec. `text()` now fails closed: a
    missing file is a finding and reads as empty, which makes every content
    check on it fail loud — never vacuously green.
  The guard test is now the mutation that beat cut 2. The *original* test planted the
  marker on a line with no backticks at all — the one case that passes even with the
  exemption hardwired open.
- **New tests** in `tests/test_tree_declaration.py` — a mix of **mutation** tests
  (break one thing, assert the gate names it) and **acceptance** tests (the correct
  artifact must be *green*, or the "fix" is just a regression with better prose).
  Between them: a BOM'd PowerShell script is green while a BOM-less non-ASCII one is
  named; the BOM gate cannot be declared away; an exemption exempts nothing else; a
  typo'd key grants nothing; and deleting one twin still fails **even in a declared
  mirror**. Each broken-declaration test also deletes a twin as a **canary** — asserting
  only "the error was printed" would pass while the bypass still worked.
- Every gate here was made to fail before it was believed. A reviewer *deleted* three
  of the new checks and the suite stayed green — the non-list `stamp_exempt` validator,
  the non-string `path` validator, and the rule that relaxations are disclosed on a
  **red** run as well as a green one (the red run is precisely when a reader needs to
  know which gates were off). Those three now have the mutations that exposed them.
  Round 2 then added two more of the same species:
  - the non-list test's own **fix** was green-and-defeated: a string iterates as
    *characters*, each character fails the per-entry check, and the refusal the test
    asserted on still printed — from the **wrong guard**. It now asserts the list
    validator's own message and feeds it a non-iterable (`5`) that would traceback
    without the validator: a crash is `rc != 0` too, and a test that cannot tell a
    refusal from a crash defends nothing.
  - the forced-UTF-8 stdout guard **survived its own deletion on the Linux CI
    runner** — the default pipe codec there is already UTF-8, so only Windows
    defended it, and the runner that gates merges is Linux. A
    `PYTHONIOENCODING=ascii` test now forces the hostile codec on every platform —
    and the *first cut of that test* was green-and-defeated too: it planted
    mojibake, whose finding quotes a path and line numbers (pure ASCII), so the
    guardless print never met a byte the codec could choke on. Replay caught it.
    It now plants the BOM-less `.ps1`, whose finding quotes `§ — é` → `Â§ â€” Ã©`.
- Suite **206 → 332**.

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
