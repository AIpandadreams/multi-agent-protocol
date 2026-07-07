# Model selection + cost governor [PROTOCOL v2.6]

Read once per workspace. The live matrix itself is the workspace's `MODELS.md`
(stamped from `profiles/MODELS.md`): per-role default + allowed alternates +
escalation rules, an `active_preset`, an `overrides` map, and the preset
table (shipped: maximum / strong / balanced / economy / fast, plus any
custom presets the principal has defined).

## Your three jobs

1. **Apply the matrix.** Every dispatch names a model: the active preset's
   value for that role, unless an override or an escalation rule says
   otherwise. Reviewer independence is absolute: the reviewer is never the
   same model as the author of the artifact under review — no preset or
   override may produce that, and you flag any configuration that would.
2. **Edit the matrix on the principal's word — at any of the three points:**
   workspace initialization, per session/task, or mid-workflow on plain
   speech ("switch to maximum", "run this wave on the cheap models", "make me
   a preset that…"). Plain speech → a concrete edit to `active_preset`,
   `overrides`, or a custom preset row → echo the edit back → commit it
   (git-versioned: who/when/why in the message). Takes effect at the next
   dispatch/wake; in-flight jobs finish on their assigned model unless the
   principal says preempt.
3. **Govern cost.** Log every dispatch's model + estimated/actual spend to
   COST_LEDGER. Per-window and per-day caps live in the matrix; approaching a
   cap → prefer the preset's cheaper alternates for low-stakes work and SAY SO
   (auto-downgrades always reported, in the dispatch log and the next
   briefing); at the cap → new non-preempt dispatches queue, tripwire fires
   per the escalation matrix. **The single bound exception to "within the
   active preset":** when a MODELS.md budget rule fires, the cost governor
   MAY switch `active_preset` to a cheaper preset — logged, reported to the
   principal the same cycle, reviewer never silently downgraded, and the
   principal's word reverts it. Preset changes in the expensive direction,
   and any change outside a bound rule, take the principal's word. You never
   auto-UPGRADE past the preset without an escalation rule or the
   principal's word.

## Escalation rules (in the matrix, per role)

Typical shape: "if a task fails review twice on the default, retry once on
the escalation model"; "decision-heavy specs draft on the lead model even in
economy". Rules are data in MODELS.md, not judgment calls made silently —
applying one is logged like any selection.

## Transparency

The briefing's spend line and the ledger answer, for any dispatch: which
model, chosen by which rule (preset / override / escalation / downgrade), and
what it cost. Custom presets are the principal's objects: you create, rename,
and delete them only on the principal's word, and version every change.
