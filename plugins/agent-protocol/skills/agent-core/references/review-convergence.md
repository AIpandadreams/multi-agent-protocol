# Review CONVERGENCE cycle [PROTOCOL v2.7] — the multi-round layer

> Layered over `review-core.md`. **review-core wins on any conflict; this file
> governs the cycle ACROSS rounds** — how a series of rounds moves an artifact
> from first draft to a reviewer-declared stop. The single-round contract
> (verdict vocabulary, fingerprint rule, reviewer read-only-ness, dead-lane
> escalation) lives in review-core and is not restated here.

> See also: `docs/REVIEW_CONVERGENCE.md` — this repository's own applied
> evidence trail of the cycle these rules define.

A round is one adversarial pass. Convergence is the *sequence* of passes that
ends only when the reviewer says it ends. This file exists because the failure
modes of a SERIES — anchoring on a stale verdict, averaging disagreeing
reviewers into a vote, the author quietly declaring victory — are different
from the failure modes of a single round, and each was a real defect.

## The four seats

A converging review moves through up to four seats. They are seats, not
necessarily four different sessions — but the model-difference floor is real:

1. **Author** — the session that produced the artifact. Its own decisions are
   the highest-risk content in it (review-core).
2. **Peer reviewer** — REQUIRED to be a different model instance from the
   author. This is the floor: a same-model self-review is not a review. Catches
   the author's blind spots that survive self-checking.
3. **Cross-vendor reviewer** — a different *provider*, not merely a different
   instance. This is the recommended REVIEWER binding, because self-preference
   bias is provider-shaped: a model rates text in its own house style higher
   (arXiv:2410.21819). The cross-vendor seat is where the strongest catches
   land.
4. **Author-as-verifier-of-the-verdict** — a NAMED stage, not an afterthought.
   Every finding a reviewer returns is either ADOPTED or REFUTED with cited
   evidence quoted in the round record. Silent acceptance is as much a
   violation as silent skipping (review-core, VERDICT CONTRACT: "Disagreeing
   with a required change is allowed — silently skipping it is not"). A verdict
   you did not verify is a verdict you did not read.

A minimal converging series uses seats 1, 2/3, and 4. Seat 2 is the floor; seat
3 is the recommendation. Adding seats never substitutes for the author doing
seat 4.

## Round budget and stop conditions

- **Budget: 2–3 substantive rounds by default.** A substantive round is one
  that verdicts new or changed material — a pure re-announcement is not a round.
  A deployment that needs a different budget records the override in the
  REVIEWER binding notes (no new slot; the binding already carries per-side
  round state).
- **Stop requires the reviewer's positive convergence declaration in its own
  verbatim words** — review-core is the authority on this ("Only the reviewer's
  own wording declares convergence"). Absence of blockers is NOT convergence;
  neither is the author's read of the tone. If the reviewer did not say it, the
  series has not converged.
- **Budget exhausted without a convergence declaration → the principal's
  decision menu**, carrying the full round history (each round's request file,
  verdict disposition, and what changed). Never auto-loop past the budget;
  never let the author declare convergence to escape the budget. The principal
  decides: spend another round, ship with the open findings recorded, or
  reject.

## Adjudicating reviewer disagreement

When two seats disagree on a finding, the author adjudicates — with cited
evidence quoted in the round record — or escalates to the principal. What is
banned is resolving the disagreement by **counting**: no votes, no averaging,
no "two of three said ship". A verdict is evidence-weighed, never tallied. Two
reviewers agreeing on a wrong reading are still wrong; one reviewer with the
primary source beats two without it. The adjudication is itself round material:
the record shows which reading won and the evidence that decided it.

**Before weighing two verdicts, compare the SCOPES they were handed.** Verdicts
over different bundles are not comparable, and a CONFIRM from the narrower one
is not evidence of anything the wider one saw. A reviewer bounded to the
touched-file set cannot report an omission — so its silence about a missing
file is not a clean bill, it is a blind spot you built. When one voice finds
something the other structurally could not have seen, that is not a split to
adjudicate; it is a scope defect to fix and re-dispatch.

## Execution-environment coverage

Bundles scope WHAT is reviewed; environments scope WHERE it runs. A loop
whose every voice ran the artifact on one platform, when the artifact ships
to another, has the mis-scoped-bundle failure shape one axis over: every seat
performs perfectly, unanimity is a chorus, and the escape ships on the
platform nobody ran.

- **The round request enumerates the artifact's execution environments** (CI
  matrix platforms, runtime targets) alongside the artifact set.
- **Every shipping environment gets an ACTUAL EXECUTION wherever runnable
  coverage exists** — a real run of the suite/artifact on that platform (a CI
  leg, a container, a second host). A platform contract or CI matrix handed
  to a seat is static review, NOT execution coverage: launch-time failures (a
  binary the platform lacks, a path form it rejects) are only observable by
  running.
- **An environment with no runnable coverage is recorded UNEXECUTED** in the
  round record, and the residual risk is explicitly escalated or accepted —
  never labeled covered. Silence about an environment no seat ran is a blind
  spot you built, not a clean bill (the narrower-scope CONFIRM rule, one axis
  over).

## The blocking line

Mechanism-neutral statement of what gates the ship:

- **What blocks:** a REJECT, and every listed required change of an
  ADOPT-WITH-CHANGES. Until each is applied-and-reconfirmed or explicitly
  refuted-with-evidence in the record, the artifact does not ship.
- **Where a reviewer mechanism emits severity tags** (the reviewer_poller
  grammar tags findings BLOCKER / MAJOR / MODERATE / MINOR): **BLOCKER and
  MAJOR gate**; **MODERATE and MINOR are recorded and non-blocking**. Severity
  is the reviewer's to assign, never the author's to soften — an author
  downgrading a BLOCKER to "MINOR, noted" is skipping a required change by
  another name.

## Anti-anchoring

Later seats review the ARTIFACT at its fingerprint — never a prior verdict.

- **Bundles are label-free.** A seat is handed the tree (or diff) at its
  fingerprint with no attached prior verdict, no "the last reviewer said", no
  ADOPT/REJECT history. Priming a fresh seat with an earlier disposition
  manufactures agreement.
- **Prior-verdict content enters only fix-confirmation rounds, scoped to named
  findings.** A FIX-CONFIRMATION round legitimately carries "here are findings
  F1–F3 from r0N and the fixes" — that is its whole job. A fresh full-review
  seat gets no such priming.
- **Re-reviews target the tree at the NEW fingerprint.** After fixes, the tree
  moved; the old verdict authorizes nothing (review-core, fingerprint rule).
  Every round quotes the fingerprint of the exact tree it judged.

## Anti-patterns

Each is a real way a review series produces false convergence:

- **Self-preference bias** (arXiv:2410.21819) — a model scores text in its own
  style higher; the peer seat MUST be a different model, the cross-vendor seat
  is stronger still.
- **Sycophantic convergence** — a reviewer accepts the author's framing and
  re-states it back instead of re-deriving from the artifact. Mandate
  independent re-derivation of every load-bearing claim (review-core's
  spawned-judge honesty + independent-verification asks).
- **Position / verbosity bias** — a longer or first-listed answer rated higher
  for length or order, not merit. Judge content, not word count or slot.
- **Anchoring on prior verdicts** — see Anti-anchoring; a seat shown a prior
  disposition tends to ratify it.
- **Debate-as-judging** — treating reviewer disagreement as a debate to be
  won on rhetoric rather than adjudicated on evidence. The blocking line and
  the primary source decide, not the better argument.
- **Over-blocking** — inflating MODERATE/MINOR notes to BLOCKER as performed
  rigor, or blocking to look thorough. Severity inflation is as much a defect
  as severity softening; both distort the blocking line.
- **The mis-scoped bundle** — the quietest false convergence of all, because
  every seat performs perfectly. A bundle scoped to the touched-file set cannot
  surface the file you FORGOT to touch, so a CONFIRM over it certifies only the
  files you already knew about — and reads exactly like a clean bill. Scope the
  bundle to the ARTIFACT SET (review-core), name co-maintained twins even when
  unchanged, and ask each seat outright: *what should have changed here and
  didn't?* Unanimous agreement across seats that were all handed the same blind
  spot is not convergence; it is a chorus.
- **The single-platform chorus** — the mis-scoped bundle's twin on the
  environment axis. N seats, one host: unanimity across seats that all ran
  the artifact on the same platform certifies only that platform, and it
  reads exactly like cross-platform convergence until the other platform
  actually runs it. Enumerate the shipping environments in the request and
  get a real execution on each (see Execution-environment coverage).

## A worked convergence arc

Fictional, generic project: a small spec, `parser-spec.md`, defining a
config-file grammar, with a generated `parser-spec.schema.json` that must track
it. The **artifact set** is both files — the schema is a co-maintained
counterpart even in rounds that do not touch it (review-core), so it is named in
every request and pinned by the fingerprint. Builder side (SIDE_NAMES bind
`builder`). Fingerprints via review-core's **set** recipe — the set's contents,
not a diff, because an unchanged member emits no diff bytes:
`( set -o pipefail; git rev-parse HEAD && git ls-files -s --error-unmatch --
parser-spec.md parser-spec.schema.json | sha256sum )` (`--error-unmatch` errors on
an untracked member; the `set -o pipefail` guard makes that failure propagate,
which the bare pipe to sha256sum would mask as exit 0).

**Round 1 — FREEZE.** Author stages the draft, fingerprints the set
(`base=…, set=a1b2c3…`), writes `review_request_builder_r01.md`
(ROUND-TYPE: FREEZE) quoting the artifact set (both files), the result of an
omission search (*what else should move when the grammar does? — searched the
README example block and the schema; schema in-set, README example unaffected*),
the touched subset (`parser-spec.md`), the environment enumeration (*no runnable
execution environment — a spec and its generated schema, nothing executes; a
parser implementing it would bring one*), and numbered questions. The cross-vendor
reviewer sweeps the tree directly and writes `verdict_builder_r01.md`,
fingerprint `a1b2c3…` MATCH:

> Overall: **ADOPT-WITH-CHANGES**.
> F1 (MAJOR): the grammar allows an unterminated quoted string — no rule closes
> `"`. Add an explicit termination production.
> F2 (MAJOR): §3 says keys are case-insensitive; the example in §5 relies on
> case-sensitive keys. Contradiction — pick one.
> F3 (MINOR): "whitespace" is undefined; enumerate the code points.

**Author verifies the verdict (seat 4).** F1 and F2 adopted (both re-derived
against the draft — real). F3 adopted. All three are round material; F1/F2 gate
(MAJOR), F3 recorded.

**Round 2 — FIX-CONFIRMATION.** Author fixes all three, re-fingerprints the set
(`set=d4e5f6…`), writes `review_request_builder_r02.md`
(ROUND-TYPE: FIX-CONFIRMATION) naming F1–F3 and the fixes, quoting `d4e5f6…`. A
second seat (the peer-model reviewer, brought in for the fix-confirmation)
returns `verdict_builder_r02.md`, fingerprint `d4e5f6…` MATCH:

> F1 resolved. F3 resolved. **F2 NOT resolved:** §3 now says case-sensitive but
> §5's example output still lower-cases the key — the contradiction moved, it
> did not close. NOT-CONVERGED.

The two seats now disagree in effect: r01's cross-vendor seat would have passed
F2 as "pick one, done"; r02's peer seat says the pick was applied inconsistently.

**Author adjudicates (seat 4), evidence cited in the record.** The author quotes
§5 line for line: the example output does still lower-case the key. The r02 seat
is right; the fix was partial. No vote is taken — the primary text (the artifact
itself) decides. Author fixes §5, re-fingerprints the set (`set=g7h8i9…`).

**Round 3 — FIX-CONFIRMATION (scoped to F2).** `review_request_builder_r03.md`
names only F2 and the §5 fix, quotes `g7h8i9…`. `verdict_builder_r03.md`,
fingerprint `g7h8i9…` MATCH:

> F2 resolved — §3 and §5 now agree on case-sensitivity. No open findings.
> **CONVERGED.**

Stop condition met: the reviewer's own verbatim `CONVERGED`, against the tree
as it will ship (`g7h8i9…`). Three substantive rounds, inside budget. The INDEX
ledger carries one row per round (r01 FREEZE, r02/r03 FIX-CONFIRMATION), each
with its fingerprint and disposition. The series — not any single verdict — is
the evidence that the spec is sound.
