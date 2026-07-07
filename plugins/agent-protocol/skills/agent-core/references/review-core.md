# Review NORMATIVE CORE [PROTOCOL v2.6] — single source of truth

> Referenced by every role skill's review-protocol file. Identical for all
> sides by construction: it exists once, here.

Every commit-bound artifact (owner side) and every job (builder side) is gated
by an independent reviewer — a different model where available. The round is
adversarial verification of YOU: your own decisions are the highest-risk
content in any artifact.

## REVIEWER ARCHITECTURE

- **Each side runs its OWN review lane with its OWN round series.** Rounds are
  numbered sequentially per side; artifacts are side-prefixed so lanes can
  never collide in the shared directory:
  `review_request_<SIDE>_r<NN>.md` → `verdict_<SIDE>_r<NN>.md`
  (`<SIDE>` = the bound side name, e.g. OWNER/ENGINE or BUILDER).
- **One shared round ledger** (`INDEX.md` in the channel directory) with a
  `side` column; each side appends only its own rows: round, side, ROUND-TYPE
  (FREEZE / RESULTS / FIX-CONFIRMATION), request file, verdict file (+ how it
  was written), verdict summary, actions taken, next round.
- **Two sanctioned reviewer mechanisms** — bind per project, per side:
  1. *Relayed reviewer*: a background subagent relays the request to the
     reviewer model; the verdict lands as a file (fallback chain: native write
     → shell write → verbatim-in-transcript + your transcription WITH a
     transcription banner stating who transcribed and why).
  2. *Harness gate reviewer*: a stop/commit-time review gate built into the
     harness. It produces no verdict file — you MUST record the round and
     verdict substance in the ledger row AND the commit message; transcribe on
     request.

  The **inbox file contract** (request/verdict files in the channel
  directory, named per the grammar above) is the only REQUIRED reviewer
  transport; relays, pollers, and harness gates are implementation details
  behind it and may change without a protocol change.
- **Fingerprint rule — the tree under review:** every review request AND its
  verdict quote a mechanical fingerprint of the exact tree under review. A
  verdict whose fingerprint does not match the tree at commit time authorizes
  nothing — request an addendum re-verdict; never commit on a verdict that
  predates the current tree. Byte-faithful recipe, pinned: Bash
  `git diff --cached | sha256sum` (or `git diff <base>..HEAD -- <paths> |
  sha256sum` for path-scoped rounds). PowerShell 5.1 string capture re-encodes
  bytes and MUST NOT be used for fingerprints.
- **Reviewers are read-only on the tree under review.** RED reproductions run
  in-memory or on copies — never `git checkout --`/`git restore` against the
  author's working tree.
- **Reviewer-found defects** (a defect arriving inside a verdict) get an
  immediate RED-first follow-up round, credited `first_observed_by: reviewer`.
- **Addendum flow:** catches landing after a request is dispatched travel as a
  dated addendum plus an explicit re-verdict request — never silent edits to
  the dispatched request, never a commit on the pre-addendum verdict.
- **Spawned-judge honesty:** subagent-judge blindness is PARTIAL —
  harness-injected memory can leak into a "blind" judge. Mandate: label-free
  bundles, quote-anchored verdicts, the author's own re-verdict as backstop,
  and a standing disclosure whenever a judge references out-of-bundle
  context. Judge returns captured from completion messages are parsed by
  documented mechanics; any normalization is disclosed.
- **Shared-reviewer caveat:** the same reviewer instance serving multiple
  sides becomes a de-facto context bridge between sessions that must not talk
  directly. Acceptable ONLY because the reviewer is read-only and speaks only
  in verdicts; never use the reviewer to route asks, status, or content to a
  peer — that is channel traffic.
- **Dead-lane escalation:** reviewer silent after 2 nudges spanning 2
  heartbeats → mark the lane dead in memory; for a relayed reviewer, first
  repair a stale relay job squatting the lane (see the role skill's
  ops-gotchas, "Reviewer relay quirks" — the fix is in the relay plugin's
  central state), otherwise spawn/bind a fresh reviewer; note the lane change
  in the ledger; flag the principal if any gated work is queued behind it.
  Distinguish a silent lane from a DOWN lane first — see `## Reviewer-lane
  outage` below.

## Reviewer-lane outage

A reviewer transport can fail as a WHOLE LANE, not one round: a quota-limited
reviewer CLI downs every transport sharing it at once — the stop/commit-time
gate AND the poller AND any ad-hoc relay through the same account all fail
together, and the failure repeats every session until the quota resets. This is
not your work being rejected, and it is not a per-round bug.

- **PROBE BEFORE BLAME.** A whole-lane failure and a REJECT look nothing alike
  once you check: fire a direct one-shot probe at the reviewer (a trivial
  request). A usage-limit / transport error back means lane-down; a real
  verdict back means the lane is up and the silence was something else. A down
  lane is NEVER interpreted as REJECT — an absent verdict authorizes nothing
  and blocks nothing; it just means no round happened.
- **Fallback ladder (normative order):** (1) a different-vendor **alternate
  transport** for the same reviewer class; (2) a **spawned judge on a model
  DIFFERENT from the author's** (the peer-model floor still holds); (3) a
  **multi-judge panel**. Options (2) and (3) are marked **DEGRADED** in the
  verdict metadata so the record shows the round did not run on the primary
  cross-vendor lane.
- **GATE-DISABLE IS PRINCIPAL-GATED.** Disabling the review gate for an outage
  window is a control change, not an ops workaround: it requires explicit
  principal authorization, is time- and scope-bounded, is logged, and is
  re-enabled at the window's end. No agent disables its own review gate — that
  is the exact self-authorization the protocol exists to block.

## VERDICT CONTRACT

Verdicts are **ADOPT / ADOPT-WITH-CHANGES / REJECT** — per-question verdicts
allowed in multi-question rounds, plus an overall disposition.

- **ADOPT** → ship as-is; record round + verdict. Zero-change ADOPTs still get
  a ledger row; non-blocking notes are recorded even when no edit is made.
- **ADOPT-WITH-CHANGES** → apply every required change, re-verify the touched
  claims, ship once. Required changes are LISTED by the reviewer for you to
  apply — the reviewer never edits files.
- **REJECT** → back to draft; rework gets a fresh round.
- Disagreeing with a required change is allowed — silently skipping it is not.
  Argue back with evidence in the round; document any deliberately-unapplied
  change in the record.
- Only the reviewer's own wording declares convergence ("CONVERGED", "FROZEN",
  "cleared for execution").
- **Reviewer-granted fast paths:** a FREEZE/ADOPT verdict may EXPLICITLY
  authorize direct execution without a fix-confirmation round. The loop honors
  such grants only in the reviewer's verbatim words — never inferred from tone
  or the absence of blockers.
- **Parallel rounds** on one side are allowed ONLY when the artifacts under
  review are path-disjoint AND separately staged; otherwise the lane is
  serialized (one round in flight).
- **Across rounds:** a series of rounds converging an artifact — the four
  seats, the round budget, adjudicating reviewer disagreement, the blocking
  line, and anti-anchoring — is governed by `review-convergence.md`, layered
  over this contract (this file wins on any conflict).
