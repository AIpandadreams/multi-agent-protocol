# Independent review convergence record

> See also: [review-convergence.md](../plugins/agent-protocol/skills/agent-core/references/review-convergence.md)
> — the normative *rules* for the multi-round convergence cycle. This file is
> this repository's own applied evidence trail of that cycle.

This repository practices what it documents: every round of work is gated by
an **independent, different-vendor reviewer** (see
[PROTOCOL](PROTOCOL.md) and [DESIGN](DESIGN.md)). Every release is prepared
under that same discipline — an adversarial reviewer (a non-Claude model)
reviews the changed artifact sets across successive rounds until it returns
a convergence declaration in its own words.

This file is the transparency artifact: each release's review series is
summarized here so an adopter can see the evidence trail rather than take
"reviewed" on faith. The most recent series is first.

## What "convergence" means here

A round produces a verdict of `CONVERGES` only when the reviewer, sweeping the
tree directly, finds **no** blocker, major, or genuine minor defect. Every
finding from a prior round is either fixed or explicitly reconciled, and the
fix is re-confirmed in a later round. A verdict authorizes nothing once the
tree moves past the fingerprint it was issued against — so the final round was
run against the tree as released.

## Review series — v1.2.7

Two amendment atoms converged separately, then the integrated bundle
re-converged as one release. Two voices at every convergence point — a
different-vendor reviewer and an isolated same-family judge on a model
different from the author's — with every finding gated on first-hand
reproduction by the adjudicating seat before folding.

| stage | scope | outcome |
|---|---|---|
| r1 (per atom) | FREEZE over atom A+B+C (review-process rules: refusal mode, execution-environment coverage, verification instruments — 3 files) and atom E (fail-closed wake gate — 1 file), base `5c2d978`, digests `981c0969…` / `6404483…` | ADOPT-WITH-CHANGES both atoms: 1 BLOCKER (the fail-closed wake gate never reached the documented skill-less wake path) + 6 MAJOR across the two unions; all folded, sets widened to every touched surface |
| r2 (per atom) | fix-confirmation, base `935989e`, digests `a1b0816a…` (10 members) / `79f350e0…` (8) | judges ADOPT; reviewer found real residuals in both atoms (the checker's own module help, a literal example request, the rendered HTML twin) — cured, sets widened again (atom E reached 11 members at r4: base `bf0b4e5`, digest `110a07a1…`) |
| r3 / r4 | narrow fix-confirmations, bases `d267e36` / `bf0b4e5` | atom A+B+C **CONVERGED FOR FREEZE** (r3); atom E **CONVERGED FOR FREEZE** (r4, after a tree-wide sweep proved the third instance of one stale location claim was the last) |
| integration | FREEZE over the full 24-member release bundle + bookkeeping, base `8a02141`, digest `ca8ff367…` | judge: ADOPT, zero findings; reviewer: ADOPT-WITH-CHANGES — this very file was stale against the release it claims to evidence, plus one CHANGELOG framing line. The cure is the section you are reading; a final narrow fix-confirmation over the widened set gates the land, alongside ubuntu CI green at the landed base |

Execution record (the release's own environment-coverage rule, applied to
itself): **Windows host** — full suite executed at the fold bases `935989e`
and `8a02141` (330 passed + 3 skipped + 188 subtests each; mirror gate
green), with targeted batteries plus the mirror gate at the narrow-round
bases in between.
**ubuntu CI** — the full workflow (mirror check, release scrub, unit suite)
ran green on every push of the release branch; its green at the landed base
is a land precondition, not an assumption.

## Review series — initial public release (1.0.0)

| round | focus | outcome |
|---|---|---|
| r01–r03 | first full-repo pass: docs quality, protocol fidelity vs. the internal source, scrub completeness, quickstart followability | findings raised and fixed (structural + authorization wording) |
| r04–r07 | authorization safety property — the irreversible/outward super-classes are **never** listable or relayable via PROXY_AUTH — stated completely and identically in every enumerating, category-reference, and definitional-slot mention | **converged (r07)**: the complete canonical set appears consistently everywhere; no file describes PROXY_AUTH as able to cover a forbidden class |
| r08 | whole-repo structural sweep: dangling references, quickstart breaks, community-file completeness, scrub | findings raised (missing review-round ledger stamp, missing CODEOWNERS, fingerprint-recipe drift, doc/anatomy mismatches) and fixed |
| r09 | fix-confirmation + enforcement-accuracy | findings raised (CODEOWNERS enforcement requires branch protection to bite; owner session must reconcile the round ledger; one lingering fingerprint recipe) and fixed |
| r10 | final fix-confirmation + whole-repo sweep | **CONVERGES — zero findings** |

### The recurring authorization theme (r04–r07)

The single property the reviewer pressed hardest on: the six first-hand-only
super-classes — **outward-facing/publish actions, email SEND,
new-money/new-recipient financial actions, destructive operations on another
party's artifacts, canonical-repo merges, and changes to PROXY_AUTH / gates /
embargoes / the protocol** — must be stated as the *complete* set in every
place the topic appears, so no partial list can ever be misread as exhaustive.
Rounds r04 through r07 walked the entire repository making that true, from the
normative core down to the quick-reference cards and the `new_project.py`
BINDINGS template.

## Reproducing the check

The reviewer used only read access to the tree. Any different-vendor model can
repeat the sweep: point it at the repo, ask it to verify (a) the authorization
super-class set is complete and consistent everywhere, (b) no dangling
references to unshipped files/tools, (c) no personal data beyond the sanctioned
`AIpandadreams` identity, and (d) the quickstart is followable by a stranger.
The [reviewer bridge](../plugins/agent-protocol/skills/agent-core/references/review-core.md)
describes the general mechanism deployments use for their own work.
