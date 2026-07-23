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
   - **Negative-evidence admissibility (a bar the reviewer applies to absence-claims used
     as gate evidence):** a claim that something is **clean, absent, zero, or not-there** —
     evidence a gate leans on to conclude *nothing is wrong* — is **inadmissible** unless it
     names **the instrument that looked** and **that instrument's known blind spots**. An
     **absence-claim is defined by its role, not its surface polarity**: any claim whose
     function is to assert that a class of problem is *not present* — including a
     positively-phrased **completeness or all-present claim** ("all N verified present",
     "every case handled", "fully covered") — is an absence-claim about what would otherwise
     be *missing*, and is governed identically; rephrasing a negative as a positive is not
     an escape. (Worked: "all 14 files re-checked and consistent" asserts *that no
     inconsistent file exists* — an absence-claim — and must name its instrument and blind
     spots exactly as "no inconsistent file found" would.) `No occurrences found` is not
     evidence; "no occurrences found by `<instrument>`, which cannot see `<blind spot>` and
     does cover `<coverage>`" is.

     The bar is **admissibility, not truth**: a non-conforming absence-claim is treated as
     **unsupported** — the gate proceeds as if the claim had not been made, never as if the
     absence were proven — so the fail-safe direction at this branch is to **withhold
     reliance**, never to accept an unnamed all-clear (the cost of a withheld good claim is
     one restatement; the cost of a trusted blind one is a silently missed defect). **This
     fail-safe holds only where the gate requires affirmative support to pass:** this
     protocol's verdict contract honors a **fast-path or convergence declaration only in the
     reviewer's explicit verbatim words, never inferred from the absence of blockers**, so a
     withdrawn unsupported claim cannot be silently read as a clearance. The bar **relies on**
     that
     property; it does not create it — where a gate would default to pass on no objection,
     withholding the claim must be paired with an explicit rejection, not left to silence.

     The reviewer applies the bar to **every absence-claim used as gate evidence** in a
     proposal or a review — wherever a gate *relies* on the absence — read like any other
     stated claim; a passing remark that decides nothing is not gate evidence. Where it is
     ambiguous whether a gate relies on an absence-claim, the classification's own fail-safe
     is to treat it as **relied-on** — ambiguity resolves toward the bar, never away from it.
     Because the bar is met by *naming* an instrument, it can be satisfied ritually — a hollow "not
     found by `<instrument>`, which has no known blind spots" reads as a verified all-clear
     while asserting the very thing at issue; that is this rule's own blind spot, declared.
     Its check is that a named instrument's **blind-spot profile is itself a claim** — the
     reviewer weighs it against a **checkable referent**, the instrument's own documentation
     or specification and the fleet's **recorded** failure modes, at the review step, so a
     wrong or empty blind-spot declaration is a reviewable defect, not a free pass.

     An **instrument**, for this rule, is any check, reviewer, or tool **operated by an
     agent** under this protocol — the parties whose absence-claims the rule governs. A
     hollow declaration that survives review is caught only by a check that terminates
     **outside those agent-operated instruments**: **the principal**, or a reviewer the
     principal names who is **not** an agent-operated instrument under this protocol — never
     a second agent-operated instrument, because two such instruments clearing each other over a
     shared blind spot is the **mutual-acquittal** failure this rule exists to name. The
     irreducible residual — the **class** of hollow all-clears that both the reviewer and
     any outside review may miss — is the **principal's to own knowingly, as a disclosed
     residual-risk class**, not as a specific undetected instance (which, being undetected,
     cannot be named in advance); the principal **may** commission external review of that
     class at their discretion. It is owned by disclosure, never discharged by another
     agent's say-so, and never converted into a promised fleet mechanism.
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
- **Provenance admissibility (a bar applied to artifacts and to citations of authority
  offered as gate evidence):** an artifact offered at a gate — a table, a count, a hash,
  a diff, a measurement — is **inadmissible** unless it carries **valid provenance**: the
  command or procedure that produced it, stated **verbatim**, in the form another party
  could run or follow; the inputs it was applied to, identified precisely enough to do it
  again; and,
  where the artifact asserts a count, a shape, or a coverage, the assertion that was
  checked when it was written. Provenance is **recorded, not
  remembered** — it travels with the artifact, so that a reader who was not present can
  re-derive the result rather than take it on trust. A **wrongly recorded** provenance is
  worse than none, because it reads as a verified record while directing any re-run at
  the wrong thing; so provenance that does not resolve to what actually produced the
  artifact is **absent provenance, not weak provenance**, and is refused on the same
  terms. (Worked: a hash offered without the command that computed it is a number, not a
  record — a reader cannot tell which bytes were hashed, or by what.) Where the source is
  **mutable** — a live surface, a transient reading, a state that moves — the record says
  so and states when it was taken: an honestly time-stamped observation of a moving
  source **is admissible**, because a reader can see exactly what was done and against
  what. What is refused is presenting a transient reading **as though** it were
  reproducible, which is a wrongly recorded provenance like any other.

  **Citations of authority are governed identically.** Every commission, relay, or gated
  instruction **an agent issues** cites a **resolvable identifier** for the authority it
  claims — an entry that exists and can be read by the party receiving the instruction.
  Authority asserted in prose — "first-hand, this sitting", "as approved earlier", "the
  principal agreed" — is **not a citation**: it names no referent anyone can resolve, and
  is inadmissible on its face, however true it may be. **This binds the record an agent
  writes; it does not bind the principal's own speech.** When the principal speaks
  authority directly into the session that needs it, that word **is** the authority, not a
  citation of authority: it is never refused for naming no entry, never deferred, and
  never made to wait on a record being written first. The obligation this rule creates
  falls on the agent who acts on that word — to **write the entry** — and it is that
  written record the ordering rule governs. A **relay** of the principal's word to a party
  who did not hear it is an agent-issued instruction like any other, and cites an entry.
  **Ordering:** the authority entry lands **before, or in the same commit as**, any
  agent-issued instruction citing it. Ordering costs nothing, and it closes the window in
  which a citation to a not-yet-written entry cannot be told apart from a citation to a
  ruling that was never made.

  **This bar only refuses.** A non-conforming artifact or citation is **not admitted** —
  the gate proceeds as if it had not been offered. It is never treated as disproven,
  never held against the party that offered it, and admitting a conforming one approves
  nothing: valid provenance earns an artifact a **reading**, never a pass. It says the
  record can be re-derived; it says nothing about whether the content is right. The
  fail-safe direction at every branch is therefore to **refuse and ask for the record**,
  because the cost of refusing a sound artifact is one restatement, while the cost of
  admitting an unre-derivable one is a conclusion nobody can check later.

  **This rule is satisfiable today, by hand, and requires no tooling.** A resolvable
  identifier is resolved by reading the entry it names; a verbatim command is checked by
  reading it and, where it matters, running it. Where an emitter or checker is later
  built, it enforces this rule mechanically but **is not part of it**, and nothing here
  depends on such tooling existing or on any schedule for building it.

  **Declared limit.** Well-formed provenance can still be wrong, and on either half: a
  record naming a procedure other than the one actually run reads exactly like a correct
  one, and a resolvable identifier can name an entry that exists but records a ruling
  never made. No check at the point of offering distinguishes either from the genuine
  article — this bar raises the cost of a false record without eliminating it, on both
  halves alike. What survives is a **class**, not a nameable instance
  (an undetected wrong record cannot be named in advance), and it terminates with **the
  principal**, owned knowingly as a disclosed residual risk, with any review of that
  class at the principal's discretion. That is a statement of ownership, not a promised
  process or cadence.
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
