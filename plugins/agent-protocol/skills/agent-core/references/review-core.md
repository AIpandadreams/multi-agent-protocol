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
- **A diff digest does not bind the artifact SET.** An unchanged member emits no
  diff bytes, so a diff-based fingerprint is byte-identical whether or not the
  unchanged twin is in the bundle — it cannot pin the very members the artifact-
  set rule exists to include. When the round's scope is a SET (the normal case
  once co-maintained counterparts are named), fingerprint the set's CONTENTS,
  not its delta:

  ```
  # inspect — one line per member; a missing/mistyped member errors HERE, where
  # the exit status and stderr are visible (exit 1 + "did not match any file(s)"):
  git ls-files -s --error-unmatch -- <every set member>
  # digest — set -o pipefail makes that same failure propagate through the pipe;
  # without it sha256sum's exit 0 masks git's, and the digest silently drops the
  # missing member (fail-open — the gap --error-unmatch was added to close):
  ( set -o pipefail; git rev-parse HEAD && git ls-files -s --error-unmatch -- <every set member> | sha256sum )
  ```

  which binds the base commit plus the current blob of every member, changed or
  not. Adding a member changes the digest; that is the point. **`--error-unmatch`
  is load-bearing:** without it, a member git does not track — a typo'd path, a
  generated artifact, a not-yet-added file — contributes zero bytes and raises
  nothing, so the digest silently fails to bind exactly the member you thought
  you were pinning (the same silent-omission shape as the diff digest, one level
  up). With it, that member is a hard error in the inspect step — but the digest
  pipe alone would swallow git's exit status (sha256sum returns 0), which is why
  the digest form wraps it in `set -o pipefail`. Verify the inspect output has one
  line per named member, and quote both halves (base + digest).
  **An out-of-repo mirror is not bindable this way** — `git ls-files` only sees
  this repo; a twin living in another repo carries its OWN base+digest, quoted
  alongside, and the round names both.
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
- **Scope the request to the ARTIFACT SET, not the touched-file set.** A
  reviewer bounded to "the files I changed" is structurally incapable of
  reporting the file you FORGOT to change — and an omission is a defect the
  same as a bad edit. Every artifact with a **co-maintained twin** (a doc and
  its rendered `.html`, a schema and its generated types, a file and its
  byte-identical mirror in another repo) fails AS A PAIR: name the pair in the
  bundle. Live case: a reviewer scoped to 4 changed files returned CONFIRM
  while the 5th file — the co-maintained HTML twin of an edited doc — sat
  un-updated, which would have shipped a registry advertising nine entries and
  linking to a rendering showing eight. Note WHY the diff alone could not save
  it: the forgotten file **was not in the diff** — that is what "forgotten"
  means. What caught it was a reviewer told to hunt **OMISSIONS across the
  repo**, not merely to audit the change. Ask your reviewer the question only an
  artifact-set scope can answer: *what should have changed here and didn't?*
  When two voices disagree, suspect the SCOPE you handed them before you suspect
  the voices — verdicts over different bundles are not comparable.
- **Shared-reviewer caveat:** the same reviewer instance serving multiple
  sides becomes a de-facto context bridge between sessions that must not talk
  directly. Acceptable ONLY because the reviewer is read-only and speaks only
  in verdicts; never use the reviewer to route asks, status, or content to a
  peer — that is channel traffic.
- **Dead-lane escalation:** reviewer silent after 2 nudges spanning 2
  heartbeats → mark the lane dead in memory; for a relayed reviewer, first
  repair a stale relay job squatting the lane (where your role has an
  ops-gotchas file, see its "Reviewer relay quirks" — the fix is in the relay
  plugin's central state; some roles carry no such file, and the repair is the
  same), otherwise spawn/bind a fresh reviewer; note the lane change
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
  verdict back means the lane is up and the silence was something else; a
  FAST failure WITH explanatory output and no verdict is a third shape — a
  REFUSAL (next bullet), which is not an outage and not a REJECT. A down
  lane is NEVER interpreted as REJECT — an absent verdict authorizes nothing
  and blocks nothing; it just means no round happened.
- **THE REFUSAL MODE — a lane that ANSWERS is neither silent nor down.** A
  reviewer transport's vendor safety layer can decline the REQUEST — the run
  dies in seconds with explanatory output and no artifact at all — or flag
  the reviewer's own OUTPUT mid-run or at the final message, leaving an
  incomplete (or even completed) verdict artifact behind. Either way the
  lane ANSWERED: distinguish by output shape before blaming quota or the
  lane, and read the artifact's own incomplete/final marker for what was
  captured — the authority boundary is a COMPLETED verdict, never the
  file's mere existence. The cure is ACCURATE DESCRIPTION, never
  evasion: re-dispatch describing the work in plain QA terms (validation
  testing, acceptance-bar verification, does-the-check-hold-under-bad-inputs)
  instead of adversarial vocabulary that misreads as offensive tasking.
  HARD BOUNDARY: never rephrase to sneak flagged intent past a classifier —
  describe legitimate work accurately, and if accurate language still will
  not pass, that is escalation material for the principal, not a wording
  problem.
  Round hardening: instruct reviewers to write verdict artifacts
  incrementally and EARLY, carrying an explicit incomplete/final state marker
  (e.g. "Overall: IN PROGRESS") until the fingerprint, the disposition, and
  the completion declaration are all present — a flag at the final message
  then costs one message, not the round.
- **A partial stream supplies findings, never authority.** The verdict FILE
  is transport, not authority: findings that were fully streamed with
  concrete, host-reproducible probes may be adjudicated at seat 4 (first-hand
  verification is the gate either way, and the ledger row records how the
  verdict was captured). But a partial or refusal-truncated stream NEVER
  authorizes ship and NEVER counts as reviewer-declared convergence — the
  fingerprint rule, the formal dispositions, and the reviewer's-own-words
  stop condition are unchanged by this mode. A refusal-killed round with NO
  recoverable findings is a round that did not happen: it authorizes nothing
  and blocks nothing, same as a down lane.
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

## Verification instruments

Evidence offered to a round is only as good as the instrument that produced
it, and instruments fail green: a probe that asserts on a heuristic scan of
free text can print PASS over an ImportError, and a guard test can be
satisfied by a DIFFERENT guard than the one under test — at which point it is
not a test, it is a decoration that reads like one. The fingerprint recipe
above already distrusts one instrument (its inspect line and pipefail exist
because the bare pipe lied); this section states the general rule for every
verification instrument offered as SHIP EVIDENCE:

- **Bind to the most structured result surface that exists** — summary lines,
  counts, exit metadata — and to the EXACT expected identifiers or messages
  (the specific text the specific guard emits), never a heuristic scan of
  free text. No tool is required to grow a machine-readable surface it does
  not have; the rule is to bind to the most structured one it has.
- **Prove the subject RAN.** Carry a validity check (a collected-count, a
  pristine-baseline run) and treat launch, import, and collection failures as
  FAIL-CLOSED RED: "the harness never validly executed the subject" must
  never convert into absence, a skip, or a heuristic green.
- **Prove the guard is load-bearing, not merely present.** A suite going
  green after a guard is added says nothing about the guard; only its
  mutation or deletion going RED does. Give every new guard a liveness
  demonstration appropriate to it — delete or mutate it in a scratch copy and
  demand the specific finding — and when no real input can reach the mutated
  condition, DISCLOSE the guard as defense-in-depth instead of faking coverage.

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
