---
description: "Run a multi-round convergence review of a committed artifact to a reviewer-declared stop"
argument-hint: "<artifact> [--rounds N]"
---

# /converge — drive a review series to convergence [PROTOCOL v2.6]

Run the multi-round convergence cycle over one artifact: peer round →
cross-vendor round → fix-confirmation round(s) → stop on the reviewer's own
convergence declaration. The rules live in
`agent-core/references/review-convergence.md` (layered over `review-core.md`);
this command is the procedure that follows them — it references, never
restates.

Artifact + options: $ARGUMENTS

## Steps (in order)

0. **Resolve and freeze.** Resolve the REVIEWER binding (mechanism + model per
   side) and the workspace from BINDINGS.md. Verify the artifact is COMMITTED
   (an uncommitted tree cannot be fingerprinted honestly) and record its
   fingerprint with review-core's pinned recipe
   (`git diff <base>..HEAD -- <artifact> | sha256sum` — Bash, never PowerShell
   capture). Default round budget is 2–3; `--rounds N` overrides it and is
   recorded in the REVIEWER binding notes.

1. **Peer round.** Dispatch a peer review: a spawned judge on a model DIFFERENT
   from the author's (the floor). Hand it a **label-free** bundle — the artifact
   at its fingerprint, no prior verdict, no disposition history (anti-anchoring).
   Ask it to re-derive every load-bearing claim from the artifact, not from any
   summary. Verdict per review-core's contract.

2. **Adjudicate + fix.** As author-verifier (the named seat): adopt each finding
   or REFUTE it with cited evidence quoted in the round record — never silent
   acceptance, never silent skipping. Apply fixes, re-fingerprint the moved tree.

3. **Cross-vendor round.** Dispatch a round through the bound REVIEWER (a
   different PROVIDER) using `review_request_<side>_rNN.md` (your side's series,
   per review-core's grammar). Reviewer answers with `verdict_<side>_rNN.md`,
   overall ADOPT / ADOPT-WITH-CHANGES / REJECT, findings quoted against the
   quoted fingerprint. Where the mechanism emits severity tags, BLOCKER/MAJOR
   gate, MODERATE/MINOR are recorded.

4. **Adjudicate + fix.** As in step 2: adopt-or-refute-with-evidence, apply,
   re-fingerprint. If two seats disagree on a finding, adjudicate with cited
   evidence quoted in the record — never by vote or average.

5. **Fix-confirmation round(s).** For each round confirming fixes, the request
   file carries a `ROUND-TYPE: FIX-CONFIRMATION` line and names ONLY the findings
   under confirmation plus their fixes (scoped — no new material). Re-fingerprint
   each round; the old verdict authorizes nothing once the tree moves.

6. **Stop conditions.**
   - The reviewer's own VERBATIM convergence declaration ("CONVERGED" / the
     bound grammar's positive form) → converged. Record the stop in the INDEX.
   - Round budget exhausted (default 2–3, or `--rounds N`) without a convergence
     declaration → STOP; present the full round history to the principal's
     decision menu (spend another round / ship with open findings recorded /
     reject). Never auto-loop; never author-declare convergence.
   - Reviewer lane down (a probe returns a transport/usage error, not a verdict)
     → follow review-core's Reviewer-lane outage ladder; a down lane is never
     read as REJECT, and disabling the gate is principal-gated.

7. **Record every round.** Each round appends its own row to `channel/INDEX.md`
   (round, side, ROUND-TYPE, request file, verdict file + how written, verdict
   summary, actions taken, next round — the stamped column order) — the series
   is the evidence, not any single verdict.

## Rules

- The convergence rules are in `review-convergence.md` and `review-core.md` —
  this command dispatches and records; it does not redefine the cycle.
- Convergence is the REVIEWER's declaration, never the author's. A quiet lane or
  an absent blocker is not convergence.
- Every round targets the tree at its CURRENT fingerprint; a verdict whose
  fingerprint no longer matches the tree authorizes nothing.
