---
description: "Run a multi-round convergence review of a committed artifact SET to a reviewer-declared stop"
argument-hint: "<artifact>... [--rounds N]"
---

# /converge — drive a review series to convergence [PROTOCOL v2.8]

Run the multi-round convergence cycle over an **artifact set**: peer round →
cross-vendor round → fix-confirmation round(s) → stop on the reviewer's own
convergence declaration. The rules live in
`agent-core/references/review-convergence.md` (layered over `review-core.md`);
this command is the procedure that follows them — it references, never
restates.

Artifact set + options: $ARGUMENTS

## Steps (in order)

0. **Resolve, SCOPE, and freeze.** Resolve the REVIEWER binding (mechanism +
   model per side) and the workspace from BINDINGS.md.

   **Scope the SET before you freeze it** (review-core: scope to the artifact
   set, never the touched-file set — a bundle of only-what-you-changed cannot
   surface what you forgot to change):
   - List every **co-maintained counterpart** of each named artifact — a doc and
     its rendered `.html`, a schema and its generated types, a file and its mirror
     in another repo, a version that must agree across two manifests — and add it
     to the set **even if it is unchanged**. Twins fail as a pair.
   - Run an **omission search** across the repo: what SHOULD have changed under
     this amendment and did not? Record the result (including "none") in the round
     record; an unrecorded omission search did not happen.
   - Carry both facts into the bundle: the artifact set, and separately the
     touched/staged subset. They are not the same list, and the reviewer must be
     told which is which.
   - Enumerate the artifact's **execution environments** alongside the set
     (review-convergence, Execution-environment coverage): where does this
     artifact ship or run, which environment does THIS round actually execute
     on, and which stay UNEXECUTED (recorded, residual risk named — a platform
     contract or CI matrix handed to a seat is static review, not execution).
     "None — prose only, nothing to run" is a valid enumeration; silence is not.

   Then verify the set is COMMITTED (an uncommitted tree cannot be fingerprinted
   honestly) and record the fingerprint of the WHOLE SET with review-core's
   set recipe — Bash, never PowerShell capture:

   ```
   # inspect — one line per member; a missing/mistyped member errors here:
   git ls-files -s --error-unmatch -- <every set member>
   # digest — pipefail propagates git's failure (sha256sum alone masks it, exit 0):
   ( set -o pipefail; git rev-parse HEAD && git ls-files -s --error-unmatch -- <every set member> | sha256sum )
   ```

   Use the SET recipe, not a diff digest: an unchanged member emits no diff bytes,
   so a diff-based fingerprint cannot tell a bundle that includes the unchanged
   twin from one that omits it — it silently fails to pin exactly the members this
   step exists to add. `--error-unmatch` makes an untracked member (a typo, a
   generated file, an out-of-repo mirror) a hard error in the inspect step — but
   piping to sha256sum would swallow git's exit status, so the digest form wraps
   it in `set -o pipefail`; confirm the inspect output has one line per member. An
   out-of-repo mirror carries its
   own base+digest, quoted alongside. Default round budget is 2–3; `--rounds N`
   overrides it and is recorded in the REVIEWER binding notes.

1. **Peer round.** Dispatch a peer review: a spawned judge on a model DIFFERENT
   from the author's (the floor). Hand it a **label-free** bundle — the artifact
   SET at its fingerprint, no prior verdict, no disposition history
   (anti-anchoring). Ask it to re-derive every load-bearing claim from the
   artifacts, not from any summary, and to answer the omission question outright:
   *what should have changed here and didn't?* Verdict per review-core's contract.

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
   under confirmation plus their fixes (scoped — no new material). The cure text
   itself is inside that scope: the charge sweeps it for a fresh instance of the
   cured class and for defects in the new claims it makes (review-convergence).
   Re-fingerprint each round; the old verdict authorizes nothing once the tree
   moves.

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
   - Reviewer lane ANSWERS with a refusal (fast failure WITH explanatory output,
     no completed verdict — a vendor safety layer flagged the request or the
     output) → NOT an outage and NOT a REJECT: re-dispatch describing the work
     accurately in plain QA terms — never rephrase to sneak flagged intent past
     a classifier — and if accurate wording still will not pass, escalate to the
     principal. A refusal-truncated stream supplies findings for adjudication,
     never ship authority (review-core, THE REFUSAL MODE).

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
- **A convergence over a mis-scoped set is not convergence.** Unanimous CONFIRMs
  from seats that were all handed the same blind spot certify only the files you
  already knew about (review-convergence, *the mis-scoped bundle*). If a round
  reveals the SET was wrong, that is not a finding to adjudicate — re-scope and
  re-dispatch.
