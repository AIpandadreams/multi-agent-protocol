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
- **Gate-touch tripwire (draft-time companion to the merge-time review requirement
  in this section):** a scheduled or automated drafter — e.g. a retro that clusters
  recorded friction into amendment PRs — checks its own draft, before filing,
  against a principal-authored **protected-region manifest**: a machine-readable
  list of every principal-designated protected region — at minimum the classes
  named in this section (authorization/gate rules, the auth-record mechanism,
  embargoes/data-hygiene rules, and this rails section), extending to the code,
  configuration, tests, and schemas that implement or enforce those gates. A draft
  whose diff touches a manifested region is **not filed as a PR**; it downgrades to
  a **notice-only memo** — the memo reports the friction and evidence, the
  agent-authored diff is discarded and cannot be adopted by approving the memo, and
  any resulting change to a protected region is separately authored or explicitly
  dictated by the principal under the principal-lock rule in this section. (An agent
  never proposes a locked-section change; the tripwire only surfaces that one is
  wanted.) The check is mechanical — a diff against the manifest, never a judgment
  the drafter makes about its own draft — and **successful completion is a
  precondition to filing:** a checker that does not run or errors, a
  missing/unreadable/invalid manifest, a coverage proof that is missing, failed,
  expired, no longer current, or that the checker cannot reproduce or cannot
  establish as single-valued (see below), or
  any changed path or hunk it cannot classify all downgrade to a memo; the gate is
  never satisfied by silence. The manifest —
  together with its schema, its classification and keying semantics, the checker
  **and its reproduction rule**, the coverage probe's **survey specification, query,
  and principal-defined execution context**, the owner
  assignment, and every bypass or override rule — is **itself a protected region**,
  authored and changed only by the principal. The probe's **results** are the sole
  part that is not principal-authored: they are mechanically generated, and the named
  operational owner is authorized to regenerate them **solely by executing the
  protected query unmodified** in that context, never by hand-editing them. Because a
  declared result is byte-indistinguishable from a genuine one, validity is
  **mechanically verified, not asserted**: the checker **re-executes the query against
  the exact filing-time repository snapshot in the principal-defined execution context
  and requires identical output** — this reproduction is a filing precondition like the
  rest — so **a result the checker cannot reproduce is no proof at all** (reproduction
  is the test of production, subsuming the bare "not produced by executing" closure).
  For that reproduction test to bind, the protected query is **required to be
  single-valued over the filing-time snapshot and principal-defined context** — a
  deterministic function with canonical output ordering, stated as part of its
  protected specification — and this single-valuedness is **mechanically established
  as a filing precondition, not merely declared**: the protected apparatus carries a
  **principal-ratified determinism-validation rule**, and the checker must establish
  that the query satisfies it before a proof stands. A deterministic restricted-runner
  or pinned-input construction can satisfy such a rule; **matching one or more reruns —
  and the absence of observed divergence — does not**, since a bounded rerun shows
  existence, not single-valuedness. A query the checker **cannot establish as
  single-valued is no proof and downgrades**; and, as a backstop, **any observed
  divergence** (two executions over the same snapshot and context yielding different
  output) **also voids the proof and downgrades**. A coincidental match between the
  checker's rerun and a cherry-picked divergent run is a violated invariant, not a
  pass — and the invariant is enforced by establishment, so it does **not** depend on
  that divergence being observed (detection mechanics are tooling-altitude; the
  established single-valued invariant is rail-level). Because
  a missing or stale entry fails silently — a gate-touching draft that looks safe —
  the manifest's coverage is not assumed complete but **re-verified by a
  principal-ratified, blocking coverage probe** with a **named operational owner**
  responsible for running it, refreshing it, and acting on a failure; while no owner
  is named the probe cannot be kept current, so — via the precondition above — every
  draft downgrades until the principal names one (fail-safe, never fail-open). The
  probe's population is defined
  *independently of the manifest* — the protected classes named in this section
  together with a mechanical, reproducible repository survey of the artifacts that
  implement or enforce those gates, a survey that fails closed (an artifact it cannot
  classify joins the population rather than dropping out) — so it cannot pass by
  covering an empty, self-referential, or narrowed set; and a
  coverage proof is *current* only while the manifest revision and repository state
  it attests equal those being checked at filing time, and it lies within the bound
  cadence. If the
  manifest does not cover that population, or no current proof exists, the probe does
  not pass and no draft is filed under the precondition above. That probe is the
  compensating visibility this mechanism owes for the blind spot it introduces, per
  the disclosure rule in the loop's Propose step.
- **Version-stamp discipline:** no session runs "local amendments" ahead of a
  merged version bump (channel-core, Untrusted-input rule #2).
- **Bundle hygiene:** proposals may also target a deployment's curated supporting-skill bundle, if it keeps one
  (add/remove/genericize supporting skills) — same loop, same rails.
