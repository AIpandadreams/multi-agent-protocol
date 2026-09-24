# MEASURED — the recorded exploration runs

⭐ **REWRITTEN 2026-08-14 for the RECONCILE round.** This file previously
recorded the PRE-RECONCILE run (10 seeds, model keyed to v17-as-commissioned).
Those figures are superseded and are NOT preserved here as a second table: a
stale measurement kept beside a fresh one is read as a comparison, and these two
runs measure different rule tables, not the same table twice.

Command: `python explore.py --sem V16` and `--sem V17` (= `DEFAULT_BOUNDS`,
`max_depth=5`), on 2026-08-14, CPython 3.13, Windows. Defaults: `--x1 refuse`,
`--applicable gens`. **All eleven seeds. These are measured figures.**

Object under test: `D5_WRITE_PATH_DESIGN_v17.md`, 1 084 077 B,
sha256 `ecc088887cb2badb7b349ccfad1cc2c51acd8e74152594ce13f379fa54c2e733`.

| semantics | seeds | distinct states | edges | wall |
|---|---|---|---|---|
| `V16` | 11 | **104 615** | **1 182 527** | **116.64 s** |
| `V17` | 11 | **114 348** | **1 243 188** | **131.22 s** |
| total | | **218 963** | **2 425 715** | **247.86 s** (4 min 8 s) |

No budget bound except depth: `max_states` (200 000/seed) and `wall_seconds`
(240/seed) were both far from binding; only `max_depth=5` truncated. Raw witness
counts `TOTAL findings:` = **434** (V16) and **326** (V17); those are witnesses,
not findings — the distinct findings are the tables below. Most of both totals
is `EXTRA-3` (340 + 287), the design's own disclosed unsettled window.

The V17 graph is byte-for-byte the same size before and after the layer-gating
repair below (114 348 / 1 243 188 in both runs), which is the evidence that the
repair moved only the V16 layer — as it was meant to.

Battery: `python -m unittest test_model` — **37 tests, 211.2 s, OK, 0 failures,
0 skips.**

---

## Property tallies, measured

| property | V16 | V17 |
|---|---|---|
| **(i)** commits enabled with zero readable generations | **10** | 0 |
| **(iii)** item open, every stated repair refused | **20** | **0** |
| `iii-TRANSIENT` (item does not survive the corrective start) | 0 | 11 |
| **(v)** a second `server_start` changes the durable substrate | **10** | 0 |
| **A2** raised somewhere, cleared nowhere | **20** | **0** |
| `A2-DEPTH-ARTIFACT` (another seed clears it) | 2 | 6 |
| `A2-INFORMATIONAL` (no clearing act is claimed) | 11 | 22 |
| **A4** authority rotation silently absorbed | **10** | 0 |
| **EXTRA-1** collision observed with intake absent | **11** | 0 |
| `EXTRA-3` disclosed unsettled window | 340 | 287 |

V16 `(iii)` and `A2` witnesses, by item: `custody-revert-lost` 9,
`rollover-intent-conflicting` 11. V17 `A2-INFORMATIONAL`:
`block-ledger-quarantined` 11, `rollover-intent-cleared-unapplied` 11 — both
items the design raises and names no clearing act for, deliberately.

---

## ⚠ Depth sensitivity of A2 — why the gate runs at shipping bounds

`A2` is a **whole-graph** property, so a shallower cut reports items whose
clearing act has not been reached yet. Measured on `V17`: depth 4 reported 9 A2
items, depth 5 reported 3. The gate (`_found_shipping`) therefore runs at the
shipping bounds, and `cleared_anywhere()` reconciles ACROSS seeds so an item one
seed cannot reach but another clears is demoted to `A2-DEPTH-ARTIFACT` **naming
the seed that clears it** — a demotion that cites its own witness, not a
judgment call. Seed `authority-divergent` was added for exactly this: it starts
at the state whose exit costs six events from `steady`, one past the cut.

---

## V16 — the positive control, intact after the reconcile

The V16 layer is the instrument's sensitivity evidence: it must keep re-finding
the walks the round already knows about. It does.

| property | finding | corroborates |
|---|---|---|
| **(i)** | custody commits ENABLED with zero readable generations; persists across restarts (`SUPERSEDED-LOST`, item never re-raised). 10 witnesses. | **opus P1, exactly** |
| **(iii)/A2** | `custody-revert-lost`, `revert_request` → REFUSE(`already-reverted`) by `R-revert-already-unconditional` — the repair refused by the condition the item describes. 9. | **codex F1** |
| **(iii)/A2** | `rollover-intent-conflicting`, `ledger_recovery[intent-clear]` → REFUSE(`intent-not-identifiable`) — two OPEN intents on one ledger, v16's payload names no intent. 11. | **opus P3 / codex F3** |
| **A4** | authority rotation silently absorbed: no generation, no item, no refusal. 10. | [redacted] A4 |
| **(v)** | a second `server_start` CHANGES the durable substrate — the resume re-applies its payload after `lose_ledger` + `crash[after-ledger-create-before-marker]` + `lose_ledger` + `crash[after-recovery-intent-before-create]`. §13.4 (c) L6877-6883 claims resume idempotence. 10. | new, and **nearly lost** — see below |
| **EXTRA-1** | collision observed with the intake ABSENT: creates nothing, appends nothing, refuses nothing, raises nothing. 11. | **opus P6** |

⛔ **THE INSTRUMENT'S OWN WORST DEFECT THIS ROUND: three v17 cures were written
into the V16 CONTROL LAYER, unconditioned.** §13.4 (e)'s "different targets"
limb, X5's marker write inside the resume's adopt arm, and X10's `intent_id`
idempotence were all encoded without a `variant == V17` guard. The third
**silenced the V16 `(v)` finding entirely** — it went from 10 witnesses to zero
and NOTHING failed, because the v17 gate only asks what v17 reports and every
v17-facing test was green. A cure applied to the pre-cure layer erases the
defect it was written to cure. Found by sweeping `model.py` for V17 branches and
asking which v17 mechanisms had none; the sweep is now the standing test
`TestLayerHygiene`, which also asserts `(i)` fires on opus P1's walk directly
rather than inferring the control's health from a tally.

⛔ **ONE V16 WITNESS WAS RETRACTED THIS ROUND, and it was the model's, not the
design's.** The pre-reconcile run reported a third V16 `(iii)`:
`custody-revert-lost` with `revert_request` → REFUSE(`revert-unauthorized`)
after `revert_auth.log` loss, "the authorization the repair needs is in the file
that went missing". **That is the mis-encoding v17 §5.2 L3796-3802 names as
M3(a)** — and v17 settles it against BOTH layers, because the pinned order
`authorize ⇒ record ⇒ attempt ⇒ CAS ⇒ consume` it appeals to is pre-existing
prose ("the same order this clause's own §13.5 window analysis depends on"), not
a v17 cure. The route writes its own `authorize` line, so a re-inited empty
ledger IS an exit. Witnesses withdrawn under both layers.

---

## V17 — measured result of the reconcile

**Zero `(i)`, zero `(iii)`, zero `A2`, zero `A4`, zero `EXTRA-1`, zero
`EXTRA-2`, zero `(iv)`, zero `(v)`.** Every F-NEW-1..7 closes against
v17-as-written. Residuals are the two demoted classes and `EXTRA-3`.

⚠ **Named instrument residual M-RES-1** (recorded in
`TestLayerHygiene.CURE_RULES_ADMITTED_TO_V16`, not fixed): the rule row
`R-revert-lost-two-witness` carries X2's SELECTED-PAIR form and the two v17
refusal names, yet its `sem` admits V16/P12/P14. v16's pre-X2 form validated over
ALL associations. It is shadowed on every state the V16 findings walk by
`R-revert-already-unconditional`, which precedes it in the table — so the control
measures correctly today — but it is a cure sitting in the control layer and it
is disclosed rather than quietly carried. Split the row at the next fold.

⚠ **A clean sheet is the result that most needs its control.** The reading is
credible only because the SAME rule table, run one layer down, still reproduces
all five V16 findings above, and because the battery's P12/P14 pre-cure wedges
still fire. A model that reports nothing under v17 and nothing under v16 has
measured nothing.

`iii-TRANSIENT` (11, all `rollover-intent-conflicting`): the item is open in the
witnessed state and every single-event repair is refused, but the design's own
next startup pass clears it — so it is a window, not a wedge. Reported, demoted,
never silently dropped.
