# Public-repo land policy — multi-agent-protocol (standing)

**Codified by <principal> 2026-07-13 (<private-repo> <entry-id>, batch-2 clickables ruling: Option A — status quo codified).**

## The policy

1. **Who may land direct-to-main:** the creator seat ONLY, on the public repo
   `AIpandadreams/multi-agent-protocol`.
2. **When:** ONLY for SOP-7-converged releases — the release content must have
   passed the standing convergence gate (Codex reviewer + isolated ≠-author
   Claude judge; see SOPS registry) before the land. No convergence, no direct
   land.
3. **Disclosure is mandatory, every land:** the land report to <principal> carries an
   explicit branch-protection-bypass disclosure line (the LAND_CHECKLIST step-5
   pattern from the v1.2.1 wave). Disclose regardless of circumstances.
4. **Protection config stays untouched:** main keeps classic protection as
   probed 2026-07-13 — PR + 1 approving review + code-owner review required,
   force-pushes and deletions blocked, `enforce_admins` DISABLED (this is the
   exemption creator lands ride), zero rulesets. Outside contributors remain
   fully PR-gated; history remains rewrite-proof.

## Why (fact base at ruling)

- Pre-land review already happens OFF GitHub via SOP-7 convergence; CI
  (mirror-check workflow) validates post-push.
- A PR-flow alternative cannot work as-configured: GitHub does not allow
  self-approval, so a single-human-account org needs a second eligible
  reviewer (second account / bot / CODEOWNERS change) or a temporary
  protection modification — friction without added assurance over the
  convergence gate.

## Change control

This policy changes only on <principal>'s explicit word (new auth entry). If the
repo ever gains a second human maintainer or bot reviewer, re-present the
PR-flow option — the self-approval blocker disappears at that point.
