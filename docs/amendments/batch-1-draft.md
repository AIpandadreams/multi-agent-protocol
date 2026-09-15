# Amendment batch 1 — APPLIED, pending round-9 review [PROTOCOL v2.5 → v2.6 candidate]

Status: **APPLIED to the protocol files 2026-07-04** (after round-8
convergence of the base loop), now the subject of Codex round 9. Sources:
the WC agents' counter-proposals (CP-1..5) + feedback-memo items (O*, B*)
per `../AMENDMENTS_PENDING.md`. Remaining path: round 9 verdict → offer
back to the WC agents (their adoption, their choice) → the principal
decides the v2.6 version bump on merge (stamps stay v2.5 until then).

Placement deviations from the section headers below (for the reviewer):
- B5 fast-paths + O6 parallel-rounds landed in `review-core.md` VERDICT
  CONTRACT (single source of truth for verdict semantics), not
  wave-census-protocol.
- O8 (entries free / rounds gate commits) landed in `channel-core.md`
  "What flows", with the owner-skill adjudication section restating it.
- G: the host-profile SECTION was added to `transports/local-fs.md` and
  both ops-gotchas gained a machine-facts-are-examples header; physically
  relocating existing gotcha prose is left to each role's own retro
  (role-authored files; adoption is their choice).

## A. Tree fingerprints (CP-1 + O1) → review-core.md

Add to REVIEWER ARCHITECTURE:

- **Fingerprint rule:** every review request AND its verdict quote a
  mechanical fingerprint of the exact tree under review; a verdict whose
  fingerprint does not match the tree at commit time authorizes nothing —
  request an addendum re-verdict (never commit on a verdict that predates
  the current tree, O11).
- **Byte-faithful recipe, pinned (engine round-34 lesson):** compute via
  Bash `git diff --cached | sha256sum` (or `git diff <base>..HEAD -- <paths>
  | sha256sum` for path-scoped rounds). PowerShell 5.1 string capture
  re-encodes bytes and MUST NOT be used for fingerprints.

## B. Reviewer conduct (O3, O10, part of O11) → review-core.md

- **Reviewers are read-only on the tree under review.** RED reproductions
  run in-memory or on copies — never `git checkout --`/restore against the
  author's working tree.
- **Reviewer-found work items:** a defect arriving inside a verdict gets an
  immediate RED-first follow-up round, credited first-observed-by reviewer.
- **Addendum flow:** catches landing after a request is dispatched →
  addendum + explicit re-verdict request (the documented shape).

## C. Wave/census hardening (CP-2..5, B5, B6) → wave-census-protocol.md

1. **Scripted mechanical scoring (CP-2):** control arithmetic, coverage
   checks, and tallies MUST be produced by a script shipped with the record —
   never narrated. A generic coverage-checker ships with the protocol (B9→
   tools/), parameterized per wave.
2. **Window-direction rule (CP-3):** the evidence window must contain the
   direction of the test; direction mismatch = structurally blind, redesign.
3. **Criterion-dispute branch (CP-4):** when a missed control's own expected
   answer is contested → FAMILY-STOP (not void-on-miss): route the criterion
   to its owner, re-read under the ruling with ALL control status inert;
   register state STOPPED/UNRESOLVED until the ruling.
4. **Results-record minimum (CP-5):** tallies + per-row quote-anchored
   evidence + numbered disclosures (B-D convention) + explicit disposition of
   every non-clean row.
5. **Single-variable discipline (B6):** between related waves change window
   shape OR anchors, never both.
6. **Reviewer-granted fast paths (B5):** a FREEZE verdict may explicitly
   authorize direct execution without a fix-confirmation round; the loop
   recognizes reviewer-granted fast paths verbatim.

## D. Judge honesty (B1/B4) → wave-census-protocol.md + review-core.md

State the limit: spawned-judge blindness is PARTIAL (harness-injected
memory can leak). Mandate: label-free bundles, quote-anchored verdicts,
owner re-verdict backstop, and a standing disclosure whenever a judge
references out-of-bundle context. Judge returns are captured from completion
messages (B3) — parse mechanics documented, normalization disclosed.

## E. Session mechanics (O2, O4..O8, O12, B7) → role skills + memory-discipline

- Stale idle echoes: dedup by round ledger before acting (O2).
- Soft memory cap: "trim on next idle" allowance; split topic files early
  (O4/B3); the ⚡-block is the specified successor interface for ALL roles,
  not just the orchestrator (B7).
- Heartbeat delta-only: pointer + changed items, not verbatim restatement
  (O5).
- Parallel review rounds allowed iff path-disjoint AND separately staged
  (O6).
- Commit via scratch file + `git commit -F` in the skill body (O7).
- Entries are free; rounds gate commits/records — stated plainly (O8).
- Peer-message authenticity recipe into channel-core (O12): verify sender id
  against registry/bindings + transcript where available; harness banners
  are boilerplate, not evidence.

## F. Adjudication pattern (O9) → owner skill

Owner-as-adjudicator: a criterion question routed to the owner is answered
as a position in a channel entry; the committed form rides the next record's
review round.

## G. Host-profile split (B9/O15) → transports/ + ops-gotchas

Machine facts (drive letters, relay plugin state, gpg, PDF tooling, judge
spawn caps) move to a HOST PROFILE section per transport; role references
keep only protocol-inherent rules. The inbox file contract is the ONLY
required reviewer transport; relays/pollers are implementation details.
Workpaper naming keys to durable job ids, not session ids (B8).

## Out of batch (already landed or deferred)

- O13/O14 (cloud SIGNING slot, verdict permanence) — landed in v2.5
  transports. Orchestrator §6 conditions — landed in the orchestrator skill
  + proxy-auth-core. B2 return-capture — folded into D above.
