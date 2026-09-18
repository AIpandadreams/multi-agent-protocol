# Private ↔ Public sync manifest

This private repo (`<private-repo>`, the 5-agent skills source) is
the ORIGIN; the public repo (`github.com/AIpandadreams/multi-agent-protocol`,
MIT) is a **genericized distillation** of it. The two drifted for months with no
record of which private artifact fed which public one — this file is that
record, plus the per-release ritual that keeps them from silently diverging
again. It is the root-cause fix for the drift the v1.2 audit found.

**Canonical direction:** as of public **v1.2.0 / PROTOCOL v2.6**, the public
plugin tree is declared **canonical**. **Historical record: BIG-3 Axis-1 EXECUTED 2026-07-10** (on
the principal's go-word): this tree adopted the public v1.2.0 plugin tree +
the three public-only tools; the private-only deltas re-applied on top are
exactly the enumerated de-genericizations (plugin.json identity/2.6.0
versioning, `<private-repo>` repo-name references ×5, the owner START_SESSION
worked-example instance, ops-gotchas concrete `<workspace-root>/` path form). The v2.5-island
posture is retired; future public releases go through the delta-check ritual
below as before.

## ⚠ IN-FLIGHT: the v2.7 wave landed PRIVATE-FIRST (2026-07-19)

For the first time, a protocol-version wave landed in this private tree BEFORE
the public release. This is a DELIBERATE, one-time inversion of the
public-canonical direction above, ratified by <principal> (<private-repo> <entry-id>; <entry-id>
creator-stewardship, orch confirm <entry-id>): the U3 amendments folded here (U2)
AHEAD of the public port (U1) because the public release is human-gated — U1
stages and HOLDS for <principal>'s publish click, so private could not wait behind it
without stalling the whole wave.

**The wave = plugin `2.6.9 → 2.7.0`, PROTOCOL `v2.6 → v2.7`.** What folded here:
- Amendment content: **A1** seat-qualification + **A3** cross-team-drafting-assist
  (both `agent-core/references/channel-core.md`); **Fold 1/2** (`memory-discipline.md`:
  carried-claim provenance + status-claim-is-a-measurement); **Fold 3**
  (`review-core.md`: sweep-completeness). (A4 / Aa / Ab, the FEDERATION doctrine,
  and the charter file are PUBLIC-only or <private-repo> lines — they ride U1 or go to
  the orch, NOT this tree.)
- Full protocol-version bump: all **31 plugin + 2 transport** (git-sync, local-fs)
  banners `[PROTOCOL v2.6] → [PROTOCOL v2.7]`.
- `tools/mirror_check.py`: hardcoded expected version `"v2.6" → "v2.7"` (6
  strings). **PRECEDENT: row 30 records the identical bump was required at
  v2.5→v2.6.** mirror_check is a SELF-CONSISTENCY gate (not a public comparison),
  so a COMPLETE v2.7 tree runs GREEN and **no cross-repo red CI exists** —
  private-ahead-of-public is a bookkeeping divergence, not a broken gate.
- `.mirror-check.json`: new `stamp_exempt` for the superseded
  `transports/cloud-git.md` (its `[PROTOCOL v2.5]` banner honestly records the
  version it was authored under; re-stamping would be a false statement — same
  record-exception class as overnight-mode). <principal> <entry-id> / <entry-id> P1:
  keep-exempt.

**DIVERGENCE RECONCILED — U1 LANDED (recorded 2026-07-22, creator <entry-id>
audit):** public is now **v1.4.0 / PROTOCOL v2.7** (`8e89768`); the banners,
mirror_check's expected-version string, the cloud-git exemption, and the
amendment content are at parity. The former "read private-ahead as the
private-first wave, not drift" instruction is RETIRED — a delta-check should now
expect parity, and any gap it finds is real drift to investigate, not a designed
wave.

**Deliberately NOT bumped this wave — DISCHARGED 2026-07-20 (F2 unit, <principal>
<entry-id> via <private-repo> orch):** the workspace-lifecycle / ops `tools/*.py` that
carried v2.6 references were aligned in one lockstep commit — 
`conformance_check.py` (`SUPPORTED_VERSIONS = ("v2.5","v2.6","v2.7")`),
`migrate_workspace.py` (hop moved to v2.6→v2.7; ⚠ **superseded rationale,
corrected 2026-07-22**: public v1.4.0 was cut precisely to overturn "the old hop
is served by the old checkout" — public now chains the full ladder in one run,
and THIS private tree is the one still carrying the single-hop defect),
`new_project.py` (stamps NEW workspaces at v2.7,
embedded `AUTH_LOG_VALIDATOR` bumped), `validate_auth_log.py` (standalone twin
bumped in LOCKSTEP — `mirror_check` §8 gates the two byte-identical),
`reviewer_poller.py` + `wave_coverage_check.py` (docstring banners), plus the
repo-root `.claude-plugin/marketplace.json` `metadata.version` 2.6.1→2.7.0 (a
missed lockstep leg of the U2 fold, creator finding <entry-id>). This was <entry-id>
P2, the follow-up unit scheduled after U1. **Public port CLOSED (recorded
2026-07-22):** v1.3.1 + v1.4.0 shipped it — public `tools/*.py` now carry
`SUPPORTED_VERSIONS = ("v2.5","v2.6","v2.7")` and `new_project` stamps v2.7;
the skew the 1.3.0 CHANGELOG disclosed no longer exists.

## Mapping (private source → public distillation)

| private artifact | public artifact | status |
|---|---|---|
| `plugins/agent-protocol/**` (skill tree) | `plugins/agent-protocol/**` | **Historical adoption record: ADOPTED @ public v1.2.0 (BIG-3 Axis-1, 2026-07-10)**: the 33 public-ahead files overlaid + 3 public-only files added (`commands/converge.md`, `references/never-idle-core.md`, `references/review-convergence.md`), LF-normalized to this tree's `i/lf w/lf` convention. Private-only deltas re-applied on top (the de-genericization set enumerated above); `plugin.json` versioning stays the private scheme (`2.7.0` as of the 2.6.1→2.7.0 bump recorded above). The retained historical record reports release `1.4.0` for the public plugin manifest. |
| `transports/cloud-git.md` | `transports/git-sync.md` | CONFIRMED. Genericized + shipped v1.2.0; private marked SUPERSEDED. Stale-in-private: dedicated-channel-repo framing, `git add -A`. |
| `transports/local-fs.md` | same path, public | **PORTED @ public v1.2.1 (2026-07-10 overnight)** — byte-copy of the `4069e93` blob; private was v2.5-stamped (caught by the freshly ported v2.6 `mirror_check`). |
| `docs/SETUP_CLOUD.md` | `docs/CLOUD.md` | CONFIRMED. Genericized + shipped v1.2.0; private marked SUPERSEDED. Same two stale framings. |
| `docs/SYSTEM_ASSESSMENT.md` | `docs/DESIGN.md` | **VERIFIED-SEMANTIC (2026-07-11 creator resume)** — genuine distillation, scrubbed (sanitization sweep of both public docs: zero private residue; only sanctioned `AIpandadreams` identity + openly-shipped Codex bridge). Two corrections from the verify: (1) `docs/REVIEW_CONVERGENCE.md` DROPPED from this row — it is the public repo's own r01–r10 release-review ledger, independently authored, NOT derived from this doc; (2) the private source is a **dated snapshot** (2026-07-05, v1.0 design basis) — public has legitimately moved forward (git-sync, `--watch` poller, `--wizard`, conformance suite all shipped after it froze), so NO sync expected in either direction; do not cite its §3/§4 scope lists as current. |
| `tools/{new_project,reviewer_poller}.py` | same names, public `tools/` | **PORTED** — `reviewer_poller` byte-copy of the public `4069e93` blob (v1.2.1, incl. the `--once` failure-propagation fix); `new_project` re-ported @ **v1.2.2 `374aeed`** (2026-07-13, embedded-validator argv fix). |
| `tools/{mirror_check,wave_coverage_check}.py` | same names, public `tools/` | **PORTED @ public v1.2.1 (2026-07-10 overnight)** — byte-copies of the `4069e93` blobs. The private copies were v2.5-era; the stale private `mirror_check` was actively FAILING against the post-Axis-1 v2.6 tree ("missing v2.5 stamp" on the three public-only reference files). v2.6 checker now runs GREEN on this tree. ⛔ **`mirror_check.py` byte-copy SUSPENDED at public v1.2.5 (2026-07-14)** — the public tool is **no longer tree-portable**: v1.2.5 added artifact-existence gates that fail LOUD on absence (twin gate on `docs/CREATOR-SEAT-BOOTSTRAP.{md,html}`, amendment-header copies in `CONTRIBUTING.md` + both `.github` templates, the `SOP-REGISTRY.md` count gate) — all **PUBLIC-ONLY by design** (row 37), so the v1.2.5 blob reports **10 findings** on this tree vs the 1 the current copy reports. Fail-loud is CORRECT in public (it closes the r4 hole where deleting a twin passed); it is structurally wrong in a mirror that carries the skills, not the docs tree. **The private copy is deliberately HELD at the v1.2.2 blob** until public **v1.2.6** makes the existence gates tree-declared (`--profile public\|mirror`, exclusions STATED not silent). Do not "fix" the drift by byte-copying — that lands a permanently-red gate, which is the failure mode v1.2.5 exists to prevent. **UN-HELD @ public v1.2.6 (2026-07-15, private `<private-oid>`)** — v1.2.6 delivered exactly the tree-declaration mechanism the hold waited for: byte-copy of the `02fb9e9` blob + tracked `.mirror-check.json` (docs_tree=false + the <entry-id> Q1 stamp exemption); gate GREEN on this tree for the first time since it existed. |
| `tools/scale_to_3agent.py`, `tools/adopt_v25_local.py` | `tools/scale_workspace.py`, `tools/adopt_project.py` | **Historical comparison; the private filenames in this row are unavailable in the public membership and are not runnable public instructions.** **DIVERGED-BY-DESIGN (semantic verify 2026-07-11 creator resume)** — the public tools are REDESIGNS sharing doctrine (idempotent scaling, principal-owned BINDINGS, adoption-as-agents'-choice), not mechanics; **no parity target, do not sync either direction**. Key facts: the scale pair operate in OPPOSITE directions (private adds owner+builder to an orch-only pa.cloud workspace; public adds the orchestrator to a 2agent.local workspace — both legitimately needed for different starting topologies); public single-sources templates from `new_project.py` while private inlines them; `adopt_v25_local.py` is a SPENT machine-specific one-shot (already ran for its purpose) with zero mechanical overlap with `adopt_project.py`. Sanitization of both public files: CLEAN, zero matches. ⚠ Private-side caveats recorded (fix before any future run, none urgent): `scale_to_3agent.py` still stamps `[PROTOCOL v2.5]` into new role files (historical private-side caveat: stale post-BIG-3) + has an idempotency hole (existing `memory/<role>/` skips the START_SESSION copy, never repaired); `adopt_v25_local.py` same-day re-run clobbers its own backup (breaks the reversibility guarantee) — relevant only if resurrected as a pattern. |
| `tools/{conformance_check,validate_auth_log,migrate_workspace}.py` | same names, public `tools/` | **Historical port record: PORTED (BIG-3 Axis-1, 2026-07-10)** as one bundle — byte-copies of public @ `6b0939e` (includes the BOM-banner detection fix + its regression test on the public side). The bundle ports together because `migrate_workspace` module-loads `conformance_check` at import, which in turn warns without `validate_auth_log`. `validate_auth_log` re-ported @ **v1.2.2 `374aeed`** (2026-07-13, argv contract: explicit root arg, loud fail on an empty named root). `conformance_check` re-ported @ **v1.2.7 `3920a4d`** (2026-07-16, fail-closed wake gate: the vendored checker joins its own required-file list — the release's ONE disclosed code change; its mutation-proven test stays public-only, this mirror carries no tests tree). |
| `plugins/.../agent-core/references/{channel-core,never-idle-core}.md` | same paths, public | **PARITY @ public v1.2.2 (2026-07-13)** — v1.2.1's clauses plus v1.2.2's timezone leg (channel-core) and monitor-less-seat bound-cadence rule (never-idle), byte-copies of the `374aeed` blobs (neither file carries de-genericizations). Rode private plugin 2.6.4. |
| `plugins/.../agent-core/references/{memory-discipline,proxy-auth-core}.md` | same paths, public | **PARITY @ public v1.2.2 (2026-07-13)** — checkpoint-clock rule (memory-discipline) + auth-log-commits-solo (proxy-auth) landed public-first; byte-copies of the `374aeed` blobs (no de-genericizations). Rode private plugin 2.6.4. |
| `plugins/.../references/{binding-slots,ops-gotchas×2}.md` | same paths, public | **OVERLAY @ public v1.2.2 (2026-07-13)** — the v1.2.2 additions (bare-cells note; shared-tree re-hash + isolated-worktree pattern + harness-hook-wedges class) applied ON TOP of the private copies, which keep their enumerated de-genericizations (`<private-repo>` repo-name in binding-slots MODEL row; concrete `<workspace-root>/` path form in owner ops-gotchas). Builder ops-gotchas was parity → byte-copy. |
| `plugins/.../skills/{owner-engine,helper-builder,orchestrator}-agent/references/START_SESSION.md` | same paths, public | **OVERLAY @ public v1.2.3 (2026-07-14)** — the new "Operating without the plugin loaded (skill-less baseline)" section applied ON TOP of the private copies. Builder + orchestrator verified byte-identical to public `836ec8a` after the overlay (no de-genericization); owner keeps its enumerated §0 worked-example de-genericization (concrete `<workspace-root>\<private-repo>` / Supabase bindings), which the section insertion does not touch. Rode private plugin 2.6.5. **Re-overlaid @ public v1.2.7 (2026-07-16)** — the new "Before binding: run the conformance gate (fail-closed)" section landed in all three the same way (builder + orchestrator byte-identical to public `3920a4d`; owner keeps the same §0 de-genericization, verified the only divergence). Rode private plugin 2.6.9. Historical ledger qualification: the overlay, parity and validation statements in this row are reports about the dated subjects shown. The private-side copies and verification records supporting them are not published here, so those statements remain unverified for this release. They establish no current parity and do not close the separate OID claims. |
| — | `docs/CREATOR-SEAT-BOOTSTRAP.{md,html}`, `docs/SOP-REGISTRY.md` | PUBLIC-ONLY by design (v1.2.1) — generalized from private ops; the private side keeps the live SOPs/runbooks themselves, no twin needed. |
| `docs/AMENDMENTS_PENDING.md`, `docs/amendments/`, `docs/AUTH_RECORD_DESIGN.md`, `docs/RESEARCH_REACH_AND_ACTUATORS.md`, `docs/REVIEW_REPORT.md`, `docs/OFFER_TO_WC_AGENTS.md`, `docs/MANUAL.md` | same paths, public | **As of the reported publication on 2026-09-15:** these seven inventory entries are present in the reviewed expected public tree. The directory entry expands to `batch-1-draft.md` and `batch-2-draft.md`, so the seven entries cover eight files. This membership check does not independently observe a remote publication. |
| `profiles/<principal>-5agent/**` | — | **Historical private-side profile reference:** the spelling shown here is genericized; the historical row refers to a private-side artifact. No matching distributed profile was found in the reviewed public tree. Private-side membership was not checked in this review. |
| `tools/watchdog.py` | — | **Historical private mechanism, unavailable in the reviewed public membership.** Its detection-only history does not supply a current public safeguard or satisfy a gate. |

**Historical inventory before wave 1 — original row retained below as history:**

> | `docs/AMENDMENTS_PENDING.md`, `docs/amendments/`, `docs/AUTH_RECORD_DESIGN.md`, `docs/RESEARCH_REACH_AND_ACTUATORS.md`, `docs/REVIEW_REPORT.md`, `docs/OFFER_TO_WC_AGENTS.md`, `docs/MANUAL.md`, `profiles/<principal>-5agent/**`, `tools/watchdog.py` | — | PRIVATE-ONLY by design. No public twin; never distilled. |


*CONFIRMED = verified byte-for-byte this session. CANDIDATE = strongly inferred
from names/history; verify at the next delta-check before relying on it.*

## Banner-stamp exceptions

Files that DELIBERATELY do not carry the standard `[PROTOCOL v2.7]` banner, so a
future stamp sweep does not "fix" them and break something:

- `plugins/agent-protocol/skills/overnight-mode/SKILL.md` — a **byte-identical
  custody copy** of <principal>'s live user-skill (folded <entry-id> verbatim, rode
  plugin 2.6.3). Adding the banner would change the file's sha and break the
  byte-custody guarantee vs the principal's live copy. Ruled a permanent **record-exception,
  no touch** by <principal> **<entry-id> Q1** (SOP-7 converged — Codex + isolated opus
  both CONFIRM; overnight batch 2026-07-14). This is the authoritative
  disposition; do not stamp it. (Closes the <entry-id> #4 open finding.)
- `transports/cloud-git.md` — the **superseded** cloud transport profile
  (retired at v1.2.0; `git-sync.md` is its successor). Its `[PROTOCOL v2.5]`
  banner records the version it was authored under, and re-stamping it to the
  current standard would falsify a retained historical record. Declared
  `stamp_exempt` in `.mirror-check.json` at the v2.7 wave (<principal> <entry-id> /
  <entry-id> P1: keep-exempt). Same record-exception class as overnight-mode.

## Per-release delta-check ritual

Run this whenever the public repo cuts a release, before deciding whether to
back-port:

1. **Diff the trees, EOL-normalized** (CRLF vs LF otherwise reports every file
   as changed):
   `diff -rq --strip-trailing-cr plugins/agent-protocol <public-checkout-at-tag>/plugins/agent-protocol`
   (extract the public side cleanly with `git archive <tag> plugins/agent-protocol | tar -x -C <tmp>`).
2. **Classify each divergence** — *public-ahead* (a back-port candidate under the applicable current ruling;
   BIG-3 timing is retained as historical context) · *private-only* (either push the genericized form up to public,
   or record it here as private-only-by-design) · *true drift* (same intent,
   diverged wording — reconcile deliberately).
3. **Never edit a built/derived file** — the served/derived artifacts regenerate;
   durable changes ride the source. Changes to shared skill text ride a reviewed
   amendment (self-improvement loop), not a hand-edit.
4. **Update this manifest** — flip CANDIDATE rows to CONFIRMED as you verify them,
   and record the release tag you last checked against.

Last checked against: **public v1.2.7 + main @ `3920a4d`** (v1.2.7 mirror wave,
2026-07-16: the loop's own failure modes codified — reviewer REFUSAL lane mode,
execution-environment coverage, verification-instrument discipline, and the
fail-closed wake gate. Port set derived MECHANICALLY per the ritual: each of the
25 changed public files classified against the previous public baseline
`02fb9e9` at the private HEAD's **blob** level (worktree bytes lie under
autocrlf). **9 byte-ports** (`commands/{converge,wake}.md`,
`agent-core/references/{review-convergence,review-core}.md`, builder
`START_SESSION` + `review-loop-protocol`, orchestrator `START_SESSION`, owner
`review-protocol`, `tools/conformance_check.py`); **3 overlays** —
`agent-core/SKILL.md` (public blob + the line-32 `<private-repo>` de-genericization
re-applied; verified the only divergence), owner `START_SESSION.md` (public blob
+ the §0 worked-example de-genericization re-applied; verified the only
divergence), `plugin.json` **2.6.8→2.6.9**; **1 private-only rider** — the
escape-rendering gotcha (author-side edit tools and typed tool args decode
`\uNNNN` spellings before the bytes land) joins owner `ops-gotchas.md`,
deliberately absent from the public release. `marketplace.json` NOT synced
(private `2.6.1` track). Public-only this release: `CHANGELOG.md`, the docs tree
(incl. `REVIEW_CONVERGENCE.md`'s new v1.2.7 series), `examples/worked-cycle.md`,
`tests/test_conformance.py`.) Prior baseline: **v1.2.6 @ `02fb9e9`** (v1.2.6
mirror wave, 2026-07-15, private `<private-oid>`: byte-ports of `channel-core.md`,
builder `ops-gotchas`, `transports/git-sync.md` — carried for the first time —
and the un-HELD `mirror_check.py`; owner `ops-gotchas` overlay gains the `.ps1`
BOM-inversion block; plugin 2.6.7→2.6.8; new tracked `.mirror-check.json`
declaration → gate GREEN with declared relaxations, this tree's first green.
Recorded here at the v1.2.7 rebaseline — the v1.2.6 port commit predates this
entry.) Prior baseline: **v1.2.5 + main @ `3f564d6`** (v1.2.5 mirror wave,
2026-07-14: the release that failed its own rules — BOM-writing guidance, a
byte-gate rule that was right but scoped to "data units", and review scope taken
as the touched-file set). Port set derived MECHANICALLY, not from memory: each of
the 24 changed public files was classified by comparing the private copy against
the **previous public baseline** `1c1fc43` — identical ⇒ safe byte-copy, divergent
⇒ overlay (it holds a private delta a byte-copy would destroy), absent ⇒
public-only. The result independently reproduced this manifest's hand-recorded
rows (owner ops-gotchas = overlay, builder = parity, twins + tests = public-only),
which is the corroboration that makes the port trustworthy. **8 byte-ports**
(`converge`, `channel-core`, `review-convergence`, `review-core`, builder
`ops-gotchas` + `review-loop-protocol`, owner `review-protocol`,
`transports/local-fs.md`); **2 overlays** — owner `ops-gotchas.md` (public blob +
the `<workspace-root>/` path de-genericization re-applied; PROVEN the only divergence from
public) and `plugin.json` **2.6.6→2.6.7** (private scheme; identity untouched).
**1 HELD: `tools/mirror_check.py`** — see the ⛔ note in its row; blocked on public
v1.2.6. `marketplace.json` is NOT synced (private runs its own `2.6.1` track).
Public-only this release: `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/PROTOCOL.md`,
both `.github` templates, the BOOTSTRAP twins, `examples/worked-cycle.md`, and the
4 `tests/` files (this mirror carries no tests tree).
⚠ **Two defects the port EXPOSED in the public v1.2.5 tool** (neither breaks the
public repo today — it tracks 0 `.ps1` — both are v1.2.6 units): (1) the widened
BOM gate is **mis-scoped for `.ps1`**: on Windows PowerShell 5.1 a BOM-less UTF-8
`.ps1` is read as ANSI and **mangles non-ASCII** — empirically confirmed on this
host (5.1.26100): BOM-less → `Â§ â€” Ã©`, BOM'd → clean. The BOM is REQUIRED there,
so the gate's three BOM findings in the historical private-source `docs/big3/*.ps1`
were **false positives** for those files. No tracked files match
`docs/big3/*.ps1` in the reviewed public tree. The mojibake a BOM-less read would cause
is the *same class* the ops-gotchas file warns about — i.e. the gate reproduces
v1.2.5's own thesis one layer up. (2) the stamp gate has no exemption for
`overnight-mode/SKILL.md`, a **ruled permanent no-touch record-exception**
(<entry-id> Q1, see §Banner-stamp exceptions) — so this tree's gate has been
standing red on a finding the record says is legitimate, which is how a gate
teaches people to ignore it. Prior baseline: **v1.2.4 @ `1c1fc43`** (v1.2.4 mirror wave,
2026-07-14: the no-idle ledger. TWO plugin-core files ported —
`agent-core/references/never-idle-core.md` was historically recorded as
**byte-identical to public**, but that claim remains **unverified** here
(object reference `<unverified-object>`; the earlier lookup reported no
resolution in either repository). The retained functional description is
"three-state ledger + anti-invention clamp + gate-preserving invariant";
no public/private provenance or byte identity is established by this note.
The other recorded port, `agent-core/SKILL.md`, was an **overlay-preserving hand-port** of the
reference-index row (its line-32 de-genericization `<private-repo>` repo wording is
private-only-by-design and survives; verified the ONLY divergence). Plugin
2.6.5→2.6.6. Public-only for this release: `docs/AUTONOMY.md`,
`docs/CREATOR-SEAT-BOOTSTRAP.md`+`.html`, `docs/SOP-REGISTRY.md`,
`CHANGELOG.md`, `tests/test_manifest_integrity.py`, and the two public manifest
bumps — the private mirror carries the plugin skills, not the public docs tree,
and uses the private `2.6.x` scheme.) Prior baseline: v1.2.3 @ `836ec8a` (v1.2.3 mirror wave,
2026-07-14: 3 START_SESSION overlay ports for the skill-less-baseline section —
builder + orchestrator byte-identical to public post-overlay, owner keeps its §0
worked-example de-genericization; plugin 2.6.4→2.6.5. `docs/CLOUD.md` +
`CHANGELOG.md` + the two manifest version bumps are public-only for this release:
the private CLOUD twin `docs/SETUP_CLOUD.md` is SUPERSEDED, and private
`plugin.json`/`marketplace.json` use the private `2.6.x` scheme). Prior baseline:
v1.2.2 @ `374aeed` (2026-07-13: 7 parity byte-ports incl. the
`validate_auth_log`/`new_project` argv-fix pair, 2 overlay files, plugin
2.6.3→2.6.4). Final two CANDIDATE rows resolved by semantic verify 2026-07-11 —
**no CANDIDATE rows remain**.
