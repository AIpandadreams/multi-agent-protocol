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

## Recommendations and counter-cases

- **Recommendations and counter-cases (a rule about how a recommendation reaches whoever
  decides):** when a seat recommends a course at a **decision of record** — a gate, a
  ratification, a merge, an authorization, or any decision whose outcome is written down and
  afterwards relied on — the recommendation travels **with the strongest case against
  itself**, written by the seat making it, in the same artifact, at the same moment. Not a
  caveat, not a risk note, not a hedge: the **best argument available that the
  recommendation is wrong**. The working test is whether a reader who already disagreed
  would **recognise their own position in it**. A counter-case no opponent would claim as
  theirs has not been written yet.

  **De minimis — the rule has a floor, and its two halves stop at that floor differently.**
  A passing suggestion offered in the course of work is not a recommendation at a decision
  of record. Where it is genuinely unclear which of the two is in front of you, the halves
  resolve in **opposite directions, deliberately**. The **obligation** resolves toward
  supplying a counter-case, because writing one costs a paragraph, while a nudge that
  travels unopposed is a decision made with one side of the argument missing and no sign
  that a side was missing. The **withholding** resolves toward **not** applying, because a
  seat free to deny standing whenever it labels something a decision of record has been
  handed an instrument for dismissing whatever it finds inconvenient — and that instrument
  would be aimed at exactly the informal remark this rule was never written to police. An
  unaccompanied suggestion below the floor is read on its merits like any other remark;
  nothing in this rule supplies anyone a reason to discount it.

  **The burden sits with the recommender, deliberately.** A recommendation placed beside a
  gate does not merely inform — it arrives carrying the standing of the seat that made it,
  and the party deciding frequently has neither the context nor the minutes to build the
  opposing view from scratch. The seat that assembled the case is the one that already
  knows where it is thinnest. Requiring the counter-case from anyone else would ask the
  least-equipped party to do the most work, at the moment they have least time.

  **A recommendation lacking one is not a recommendation.** It **does not count as** one:
  the underlying facts remain readable and usable, but nothing follows from the
  circumstance that a seat recommended it, and the deciding party owes it no deference on
  that account. Nor does this run the other way — supplying a counter-case wins nothing.
  A recommendation so accompanied is not thereby better founded, and this rule certifies no
  recommendation as sound. It withholds standing; it never confers it.

  **A counter-case is not itself a recommendation** for the purposes of this rule — even
  where it argues for a different course, which a good one usually will. It is the companion
  to a recommendation, not a fresh one, and it generates **no nested obligation**: the
  **pair is the unit**, and the rule is discharged when the pair is complete. Nothing here
  recurses. Should a seat afterwards recommend that alternative course in its own right, at
  a decision of record, that is a new recommendation and travels with its own counter-case.

  **This governs presentation, not choice.** It binds what a seat must supply and says
  nothing about what any decider may accept. It creates no gate, adds no approval step, and
  delays no decision anyone is ready to take. **Read that as a non-grant, not a licence:**
  this rule erects no bar to acting on a bare recommendation, and it confers no freedom to
  do so either. Whatever standing a party already holds, it keeps; what the rails decline
  to give, this clause does not hand over. It reaches no further than the seat that offered
  the recommendation.

  **It reaches recommendations issued after ratification.** One already made when this rule
  takes effect keeps whatever standing it had; nothing here reaches back to strip it, and
  matters settled under the old reading stay settled. The rule bites at **issuance**, never
  behind it.

  **No tooling, no format.** Writing the case against costs a paragraph inside whatever
  artifact already carries the recommendation. Should menus, cards or staging docks be
  built later, they may carry this rule but do not constitute it; none is promised here,
  scheduled here, or assumed by anything above.

  **Declared limit — both halves.** *On strength:* nothing written here can compel a
  counter-case to be **good**. A seat wanting its recommendation adopted may compose a weak
  one that honours every word of this rule while hollowing out its purpose — and at the
  moment of reading, a deliberately feeble counter-case is hard to separate from an honest
  one mounted against a genuinely strong recommendation. This rule raises the cost of that
  manoeuvre and leaves it standing in the record where it can be examined later; it does
  not prevent it. *On framing:* a counter-case argues against the recommendation **as
  posed**, and can say nothing whatever about the option that was never tabled. A
  well-argued pair still forecloses everything outside itself, and what was never offered
  leaves no mark for a reader to catch. Both are **kinds** of failure rather than instances
  anyone could name beforehand; both are owned by **the principal** as declared risk, and
  any revisiting of either is the principal's to call and to time. That is ownership
  language, and it promises no review.

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
- **KPI authorship and pairing (a bar on the metrics that decide whether an amendment
  merges):** a metric **gates** when a decision to merge or not merge an amendment turns
  on its value. Which metrics gate is **the principal's to set** — either **authored by
  the principal**, or **drafted by a named seat and ratified by the principal**. The
  record shows **which of those two happened, and who drafted it**: a ratified slate is
  not an authored one, and on the single lever that decides which amendments merge, the
  difference is worth stating rather than blurring. A gating set traceable to neither is
  **not in force**, and a gate that rests on it proceeds as though no metric gated it.

  **Velocity never travels alone.** A **velocity metric** — one whose improvement asserts
  that work was **produced, delivered, or completed at a greater rate or in less time** —
  does not enter the gating set by itself. It enters **paired** with a
  metric that counts **defects that escaped** — work that reached a stage it should not
  have reached in the state it was in. **The two must correspond, or they are not a pair:**
  the defect-escape metric counts escapes **from the whole of the body of work** the velocity
  metric measures, over a period that **covers** the one the velocity claim is made about. A
  second metric satisfying every other requirement while counting escapes from a population
  that **leaves out any of the velocity metric's work** — wholly different work, or only
  **part** of it, with the rest unobserved — or over a window that leaves part of the velocity
  claim's period unobserved — leaves the velocity figure
  **unpaired**, with the consequence stated below. Both halves are settled by reading the two
  definitions beside each other:
  **a population that includes the whole of the velocity metric's work and a window that
  covers the whole of the velocity claim's period**. The two are **selected together,
  carried on the same
  authority — authored or ratified — and reported together in the same artifact**. A
  velocity figure offered at a gate **without its pair** is **absent evidence, not weak
  evidence**: it is not read down, not discounted, not given reduced weight. It is simply
  not there. The reason is that a speed number
  alone cannot distinguish work that got faster from work that got faster **by skipping
  something**, and the entire purpose of the pairing is that a reader never has to guess
  which of the two they are being shown. **What the improvement claims decides, not what
  the metric is called:** renaming a throughput metric, inverting it into a duration to be
  minimised, or expressing it as a ratio does not exempt it — if the improved direction
  says *the work went out faster, or in greater volume per unit of time*, it is a velocity
  metric. A cumulative count is not a rate merely because it rises: where the period it
  covers can itself lengthen, the increase asserts nothing about how fast the work went
  out, and this sentence does not reach it.
  **Equally, a metric is not a velocity metric merely because its improvement direction is
  "more" or "cheaper".** Coverage, availability, reliability and cost assert something
  about **how complete, how robust, or how expensive** the work is, not about how fast it
  went out; they carry no pairing obligation, and pairing one of them to a defect-escape
  count would assert a relationship that does not exist. Where a single metric makes both
  claims at once, treat it as a velocity metric: the pairing costs one number, and the
  failure it guards against does not.

  **A metric is selected as defined.** What the principal authored or ratified is the
  metric **as it stood at that moment** — its formula, its denominator, its population, its
  window and its threshold. Change any of those and the result is a **different metric**,
  whatever it is still called; a different metric is a **new selection**, and it comes under
  this bar like
  any other. A record showing a ratified slate that contains the name is not a record of
  authority over the altered measure. **The name is not the metric.**

  **Measuring is not selecting.** This bar governs **only** the set the principal has
  authored or ratified. Measuring a figure, recording it, baselining it or charting it are
  untouched by this rule, and none of those acts makes a metric gating. Read this as a
  **non-grant, not a licence**: it is a statement that observation falls outside the bar,
  never a permission to observe. Whatever a seat may already do, it may still do; whatever
  the rails withhold, nothing here supplies. This bar subtracts from no permission and
  confers none.

  **It bites at selection, and does not reach backwards.** This bar **does not reach** a
  set already gating when the rule takes effect, until that set is **next selected**. That
  is a limit on the bar's **reach**, and **not a preservation of the set**: nothing here
  confers force on a set that lacks it, ratifies an agent-chosen one, or supplies an
  authority it never had. Whatever standing such a set has, it has from elsewhere; this
  rule neither adds to it nor shields it, and a set that was never anyone's to choose is
  not made anyone's by this paragraph. No decision already taken reopens on account of this
  rule, and no figure already relied on becomes absent retrospectively.

  **"Next selected" has a trigger, so no set can *change* without coming under the bar.** A
  set is selected again whenever it is authored or ratified, **and whenever its membership
  changes or any member's definition changes** — a metric added, a metric dropped, or a
  formula, denominator, population, window or threshold altered. At that moment the whole set
  comes under this bar like any other. **What the trigger does not close is stillness, and
  that is
  deliberate.** A set nobody ever touches is not renewed by the passage of time and does not
  come under this bar at all: it simply keeps whatever standing it already had, which is not
  something this rule supplies. Closing that gap would make the bar reach backwards into
  sets chosen under the earlier reading, and this rule's prospectivity is the reason it can
  be adopted without reopening anything already settled. So the gap is a **declared limit**
  rather than a closure claimed and not delivered: an untouched legacy set is governed by
  whatever else governs it, and by nothing here.

  **Exclusion is the entire remedy.** A gating set answering to neither authorship test,
  and a velocity figure arriving without its pair, are **left out of the decision**, and
  the gate is settled on what remains. Nothing is inferred from the exclusion: the figure
  is not counted as evidence
  *against* the amendment, and the seat that offered it is not marked down for having
  offered it. Conformance earns nothing either — a properly authorised, properly paired
  set tells a reader *these are the measures the principal chose, and both are present*,
  and stops there. Whether the amendment deserves to merge is a separate question this
  bar never reaches. Wherever a branch is unclear, **leave the figure out and ask whose
  set it came from**: excluding a sound metric costs one ruling to restore, while
  admitting an agent-chosen one installs a merge criterion nobody authorised — and leaves
  nothing behind to show that nobody did.

  **Nothing here waits on tooling.** The whole rule is exercisable with a pen: the gating
  set is a short written list, its authorship is visible in the record that carries it,
  and a pair is confirmed by reading the two definitions beside each other —
  **a population that includes the whole of the velocity metric's work and a window that
  covers the whole of the velocity claim's period** — and finding both numbers in one
  artifact. Should
  a benchmark harness or metrics pipeline arrive later, it **computes** these figures — it
  does not constitute them. This rule does not assume that harness, does not schedule it,
  and does not weaken if it is never built.

  **Declared limit — both halves of the rule.** *On the metric half:* a well-chosen pair
  still misleads, in two distinct ways, and **neither is bounded** — they differ by
  mechanism, not by whether they run out. The first is **lag in time**: a defect-escape
  count usually **trails** the velocity figure it is paired with — a speed gain can be
  booked before the escapes it caused have surfaced. Nothing here sets a maturation horizon
  or a discovery deadline, so an escape not yet found is absent from the count however well
  the population is drawn, and the wait for it to surface can run arbitrarily long. The
  pairing does not shorten that wait or close it; it puts the escapes found **so far**
  beside the velocity figure, so the number is read in the open rather than alone. The
  second is **population growth**. The correspondence requirement is a **floor, not a
  ceiling**: it forbids a defect population that **fails to contain the velocity metric's
  work**, or a window that fails to cover **the velocity claim's period** — one that leaves
  work out, or a window offset so as to leave part of the period uncovered — but it does not
  forbid one that **contains the whole and more**. A superset that includes the whole of the
  velocity metric's work and then some leaves out nothing, so it is not the "leaves out"
  failure above and clears the floor. That superset is what the floor leaves open: a raw
  escape *count* cannot be flattered by it — more population or a wider window can only
  **raise or hold** a count, never lower it — but where the defect figure is a **rate or
  density**, a superset **can dilute** it, and an arbitrarily large clean superset can drive
  it arbitrarily toward zero. This residual is left open, not closed here.
  *On the authority half:* a drafted-and-ratified slate carries its drafter's framing —
  which metrics were offered, and which were never proposed at all, shape a ruling without
  ever appearing in it, and an unproposed metric leaves no trace to review. Naming the
  drafter makes that influence **attributable**; it does not remove it. None of these
  residuals can be pointed at in advance — each is a **shape of failure**, not an instance —
  and all come to rest with **the principal**, accepted with eyes open as declared risk. If
  any of them is ever revisited, that is the principal's to initiate and to time. This
  paragraph assigns ownership; it commits no one to a schedule and promises no review.
- **Version-stamp discipline:** no session runs "local amendments" ahead of a
  merged version bump (channel-core, Untrusted-input rule #2).
- **Bundle hygiene:** proposals may also target a deployment's curated supporting-skill bundle, if it keeps one
  (add/remove/genericize supporting skills) — same loop, same rails.
