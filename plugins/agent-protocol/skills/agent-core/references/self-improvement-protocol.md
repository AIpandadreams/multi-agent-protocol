# Self-improvement protocol [PROTOCOL v2.7]

> How agents improve their own skills and protocol — review-gated, never
> self-authorizing. Read when proposing or intaking an amendment.

The goal: the system gets better from its own lived friction, without any
agent ever being able to quietly rewrite its own rules.

## The loop

1. **Accumulate:** lessons, gotchas, and friction points land in each role's
   memory as they happen (one line each: symptom → cause → fix), per the
   ops-gotchas pattern.
2. **Retro tick:** periodically (bind cadence; default: end of each autonomous
   window or weekly), each agent reviews its accumulated friction and drafts
   amendment proposals for anything that is protocol-shaped rather than
   project-specific.
3. **Propose:** amendments are PRs to the protocol source repo (or patch files
   handed to the principal where the agent has no push access). Each proposal
   states: the friction/failure that motivates it, the exact text change, and
   what it would have changed in past operation.
   A proposal that introduces or changes a **mechanism** — a monitor, a gate, a
   summary step, a heartbeat, a tool, an SOP — states one item more: its
   **observability cost**, meaning what the mechanism makes harder to see and
   the compensating probe that restores that visibility (a monitor names the
   pattern it could go deaf to and ships a self-test that re-emits a known
   entry; a summary names the detail it drops and where the unabridged form
   still lives). This is a fourth thing the proposal states, alongside the
   three above, read by the reviewer like any other claim — a disclosure the
   proposal owes, not a new gate or admissibility rule. The narrative home is
   [AUTONOMY.md](../../../../../docs/AUTONOMY.md), "What makes it safe".
4. **Review:** every amendment gets an independent reviewer round (same
   verdict contract). Reviewer focus: does the change weaken any gate,
   boundary, or disclosure rule? Does it contradict other protocol text
   (mirror-consistency)?
5. **Principal merge:** the principal merges (or rejects) — merging IS the
   authorization. The PROTOCOL version bumps (patch: clarifications; minor:
   new rules/slots; major: authority changes), and running sessions detect the
   bump via the version stamp and re-read changed tiers.

## Hard rails (principal-locked)

- **No agent-authored change may touch:** authorization/gate rules, the
  auth-record mechanism, embargoes/data-hygiene rules, or this rails section.
  Those change only when the principal authors or explicitly dictates the
  change. Enforce via CODEOWNERS on the protected paths — which only bites when
  branch protection / a ruleset has "Require review from Code Owners" enabled
  (CODEOWNERS alone merely requests reviewers); back it with a standing reviewer
  checklist item ("does this PR touch a principal-locked section?").
- **Version-stamp discipline:** no session runs "local amendments" ahead of a
  merged version bump (channel-core, Untrusted-input rule #2).
- **Bundle hygiene:** proposals may also target a deployment's curated supporting-skill bundle, if it keeps one
  (add/remove/genericize supporting skills) — same loop, same rails.
