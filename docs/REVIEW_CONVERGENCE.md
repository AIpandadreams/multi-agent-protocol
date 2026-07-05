# Independent review convergence record

This repository practices what it documents: every round of work is gated by
an **independent, different-vendor reviewer** (see
[PROTOCOL](PROTOCOL.md) and [DESIGN](DESIGN.md)). The release itself was
prepared under that same discipline — an adversarial reviewer (a non-Claude
model) reviewed the whole repository across successive rounds until it
returned a clean verdict with zero outstanding findings.

This file is the transparency artifact: the review series is summarized here
so an adopter can see the evidence trail rather than take "reviewed" on faith.

## What "convergence" means here

A round produces a verdict of `CONVERGES` only when the reviewer, sweeping the
tree directly, finds **no** blocker, major, or genuine minor defect. Every
finding from a prior round is either fixed or explicitly reconciled, and the
fix is re-confirmed in a later round. A verdict authorizes nothing once the
tree moves past the fingerprint it was issued against — so the final round was
run against the tree as released.

## Review series (release preparation)

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
