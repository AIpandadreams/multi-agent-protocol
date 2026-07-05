# Delegated read waves & censuses — the builder's core method [PROTOCOL v2.5]

> **Tier: before designing any delegated read wave or census** (not needed for
> plain single-session work).

This is how the builder audits large corpora (documents, data files, extracts) with
subagents while keeping every verdict trustworthy. The method's spine: **freeze the
source, baseline it mechanically, delegate the reading, reconcile mechanically before
trusting anything, control for judge failure, and preserve raw outputs under any
adjudication layer you add.**

## 1. Freeze the source

- Waves never read the owner's live tree. Produce a frozen snapshot at a pinned version
  (`git archive` at a sha, or a dated copy) and give agents ONLY snapshot paths.
- Verify snapshot-vs-live identity at spec time (content diff; line-ending-only deltas
  documented) and re-check the delta when results are handed back — if the live tree
  moved under you, say so and state whether it invalidates anything.

## 2. Mechanical baseline BEFORE the wave

Before any agent reads, compute per-item ground truth for everything a script can
measure: section spans, heading counts, marker/line inventories, file line counts.
Agents' returns must reconcile against this baseline exactly; any mismatch is a re-read
trigger, not a shrug.

- **The definitional-grep lesson:** a baseline is only as good as its pattern's
  semantics. A literal-string tier once matched only changelog comments while the real
  live markers used a colon form — the "grounded" baseline was definitionally wrong. So:
  eyeball actual hits when building a baseline; classify by meaning, not by the first
  regex that returns numbers. If a baseline defect is found mid-wave: issue baseline v2
  (v1 preserved), amend the frozen spec by dated amendment, define a bridging
  reconciliation rule for in-flight returns, and disclose at the results round.

## 3. Wave design

- 6–10 read-only agents, each with a bounded slice (alphabetical or structural), a
  shared instruction core, and per-group format notes for known anomalies (heading
  variants, prose-formatted sections) so agents aren't surprised into improvisation.
- **Window-direction rule:** the evidence window handed to each reader must contain
  the DIRECTION of the test — a window that structurally cannot show what the test
  looks for is blind by design, and a miss inside it proves nothing. Direction
  mismatch discovered at any point = redesign the window, don't score the wave.
- **Single-variable discipline:** between related waves change the window shape OR
  the anchors — never both — so a result delta is attributable.
- Returns are **strict structured JSON** as the agent's final message: inventories with
  ids, verdicts with rationales and pointers, marker captures with line numbers,
  anomalies, and read-confirmation fields (spans, counts) that exist purely so the
  consolidator can check them.
- High effort, capped concurrency, no orchestration frameworks, no nested spawning.

## 4. Builder spot-audit (recorded PRE-return)

Before accepting the wave, the builder directly reads a small adversarial sample (2–3
items chosen for known trickiness) and RECORDS its own inventory before any agent
return is examined — including pre-stated verdict-affecting conditions ("if the agent's
inventory omits X, that is a discrepancy"). A verdict-affecting mismatch escalates:
that agent's whole slice re-read, plus a targeted mechanical re-check across the full
population, not just the implicated slice.

## 5. Reconciliation before verdict

Consolidation is a script, not vibes: span checks (exact starts; bounded tolerance for
documented end-convention differences with a KNOWN-exceptions dict), count checks with
documented fallbacks, marker line-set comparison (union of agent captures vs baseline
lists — classification-binning differences are not discrepancies; missing/extra line
numbers are), zero-result floors, and a printed flag list. **No delegated verdict enters
the results table until its item reconciles.** The script ships with the record.

**Scripted mechanical scoring — never narrated:** control arithmetic, coverage
checks, and tallies MUST be produced by a script shipped with the record. A
narrated tally ("all 14 controls hit") that no script re-derives is not a
result. A generic coverage-checker ships with the protocol
(`tools/wave_coverage_check.py` in the multi-agent-protocol repo), parameterized per wave
(manifest of expected slices/controls in, tallies + flag list out); waves may
extend it, never replace it with prose.

## 6. Controls and the VOID rule

- Positive controls: known findings planted in the population, enumerated as exact
  keyed fixtures (item, field, occurrence index) — never prose pointers. Controls must
  span **position classes** (string edges, mid-sentence, boundaries) and be
  **field-attribution-accurate**; both failure modes were hit in practice (a regex that
  only matched lowercase context missed sentence-boundary cases; fixtures once pointed
  at the wrong field and correctly VOIDed a valid run).
- Floors are stated in the frozen spec (aggregate AND per-stratum). A miss VOIDs the
  wave: exactly one fresh blind re-read is allowed; still missing = wave invalid. No
  laundering — originals are kept, the VOID is reported, and the re-run is a new run.
- **Criterion-dispute branch (FAMILY-STOP, not void-on-miss):** when a missed
  control's own expected answer is contested — the fixture may be wrong, not the
  reader — do NOT void the wave on it. Route the criterion to its owner for a
  ruling, re-read the affected family under the ruling with ALL control status
  inert, and hold the register state STOPPED/UNRESOLVED for that family until the
  ruling lands. Voiding on a disputed criterion launders a spec defect into a
  reader failure.
- Soft negatives (planted clean items) estimate false-positive rate; they are an
  estimate, never an exoneration.
- Blind judging: don't prime judges with the history you expect them to confirm.
  Unprimed reproduction of known signatures is evidence; primed reproduction is
  noise. **Spawned-judge blindness is PARTIAL** — harness-injected memory can leak
  into a "blind" judge — so: label-free bundles, quote-anchored verdicts, the
  builder's own re-verdict backstop, and a standing disclosure whenever a judge
  references context outside its bundle. Judge returns are captured from
  completion messages — document the parse mechanics and disclose any
  normalization applied.

## 7. Adjudication layers preserve raw outputs

When delegated readers split on a rubric (same shape verdicted differently by different
agents), do not overwrite. Add a documented `builder_normalized` layer beside the raw
verdict column, state the convention, review every normalization candidate (keyword scan
+ eyeball), restore any the convention shouldn't touch via an explicit exceptions set in
the script, and DISCLOSE the layer plus its known asymmetries at the results round. Bias
the layer so the owner can cheaply undo it.

## 8. Honest results memos

The memo states coverage, flags, floors met, incidents (including judge misreports you
mechanically disproved), and recall implications of anything missed — recomputed
honestly ("2 of 17 known positives missed ⇒ recall on knowns ≈ 88%") rather than
narrated away. Set-membership claims get checked against the actual census list, not
against what a code number suggests.

**Results-record minimum** (below this, the record is not reviewable): script-produced
tallies; per-row quote-anchored evidence; numbered disclosures (B-D convention: each
disclosure gets a stable id the verdict can cite); and an explicit disposition for
EVERY non-clean row — no row exits the record as an unexplained residue.
