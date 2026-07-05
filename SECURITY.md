# Security policy

## What this project is, threat-wise

This repo ships **coordination discipline for AI agents**, not a sandbox.
The protocol constrains what *well-behaved* sessions do and makes
tampering *detectable* (append-only CI, provenance checks, fingerprinted
reviews); it cannot make a fully compromised session incapable of harm.
OS/harness permissions remain the enforcement layer under yours.

## Reporting a vulnerability

Report privately via **GitHub Security Advisories** (Security tab →
"Report a vulnerability") on this repository. Please include a minimal
reproduction. You can expect an acknowledgment within a week.

Reports we especially want:

- Ways an agent could **acquire authorization it wasn't granted** — auth-log
  chain bypasses, double-spend races the validator misses, relay
  fabrication that passes RECEIVED verification.
- Ways to **edit history undetected** — append-only or monotonicity checks
  that can be tricked (encoding games, rename games, CI-skip conditions).
- **Review-gate bypasses** — verdicts that apply to bytes other than the
  fingerprinted tree, or fingerprint collisions in practice.
- **Prompt-injection escalations through the channel** — channel content
  that reliably causes a role session to violate the untrusted-input rule.

## Out of scope

- Model jailbreaks in general (report to the model vendor).
- Attacks requiring write access the attacker wouldn't have under the
  deployment's own git permissions.
- The security of your work repo's own code — the protocol governs the
  coordination record, not your project.

## Standing rules the code ships with

- Secrets never belong in a workspace: env/credential stores only. The
  stamped CI secret-scans every push as a backstop, not a license.
- Workspace repos should be **private** with force-push/deletion
  protection where your hosting plan allows it.
- `.auth-provenance.json` author-identity checks are a weak (spoofable)
  signal — treat them as tripwires; per-role credentials are the hard
  layer.
