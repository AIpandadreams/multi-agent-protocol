"""VIEW-LAYER declarations — facts about the RENDERER, not about the design.

⛔ WHY THIS FILE EXISTS. The model leg declined to carry the column tiebreak's
inertness in `design_data.py` and routed it here with three recorded reasons,
all of which hold: it is a VIEW fact (it changes how one renderer resolves a
source line to a definition, and changes neither the design nor the model);
nothing in the declaration layer could re-run it, because the claim is true or
false entirely inside `generate_design.py`, which that layer deliberately does
not import; and carrying it there would run the dependency backwards. Its
instruction was "copy the DATACLASS if useful, never the FACT" — so the shape
below is deliberately the same shape, and every value in it is derived here.

The bank's own reason for splitting MODEL_FILES from VIEW_FILES is the reason
this file is separate from `design_data.py`: a change here changes the
DOCUMENT without changing the DESIGN, and a reviewer who cannot tell those
apart cannot review either.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InertGuard:
    """A guard that is CORRECT and currently changes no outcome.

    Two readings of "inert" live under this one shape and they are NOT the
    same claim: a guard may be UNREACHED, or it may be reached and decide,
    with the decision unable to go wrong on the object as it stands. The
    second is still a status worth carrying — but only if `measurement` says
    which one it is, because "reached zero times" is a falsifiable
    reachability claim and stating it of a branch that IS entered publishes a
    measured-false fact [[claims-must-survive-every-available-reading]].

    Shape copied from `design_data.InertGuard` on purpose: two layers
    declaring the same KIND of fact should render through one code path, and
    the generic renderer keys on the fields, not on the class. `conditions`
    are stated as checkable claims rather than as reasoning, because a status
    whose grounds cannot be re-run is a status nobody can retire
    [[a-stated-bound-is-an-open]].
    """
    id: str
    guard: str
    site: str
    status: str
    measurement: str
    bound: str
    conditions: tuple[str, ...]
    kept_because: str
    routed: str = ""
    note: str = ""


COLUMN_TIEBREAK_INERT = InertGuard(
    id="resolve-act-column-tiebreak-inert",
    guard="the `co_positions()` COLUMN TIEBREAK in `_resolve_act` — the arm "
          "that disambiguates two callables sharing one source line by "
          "scoring each candidate's span against the code object's own "
          "instruction positions",
    site="generate_design.py _resolve_act — the co_positions() scoring block, "
         "reached by falling PAST the single-candidate bypass (the "
         "len(cands) == 1 early return) that four comment lines separate "
         "from it. At the frozen identity that is L471-478 for the block and "
         "L465-466 for the bypass; anchor on the two symbols, since a "
         "comment-only diff moves the pins and not the code",
    status="VERIFIED-INERT",
    # ⛔ v18-R4 opus-4: this string used to carry "all 43 rules" and "the
    # identical 31-row enum" as HAND-TYPED figures — live cardinalities of
    # collections the document derives elsewhere (§S7.1's `len(M.RULES)`,
    # §S5's derived (cause, rule) pairs), two sites for one fact in a document
    # whose §10.2 v18-b entry says no cardinality is stored anywhere. Both
    # escaped the O8 guard: `rules` was not in its noun set and `31-row` has a
    # hyphen where the guard wanted whitespace. The figures are now the
    # placeholders `{n_rules}` and `{n_pairs}`, filled AT RENDER by
    # `generate_design.sec_inert_guards` from the live derivation — the same
    # bytes when the model is unchanged, and the RIGHT bytes when it is not.
    # A view record may describe a measurement; it may not store its result.
    measurement="THE BRANCH IS ENTERED, AND IT DECIDES. Replaying the live "
                "join over all {n_rules} rules: exactly ONE act line carries two "
                "callables — model.py L2068, where R-rollover's guard lambda "
                "(col 9) and its act lambda (col 31) share the line — so the "
                "single-candidate bypass does not catch that rule, control "
                "falls into the scoring block, and co_positions() selects "
                "col 31 over col 9. Entered once, on R-rollover, and its "
                "pick is what makes that rule's cause-join correct. What "
                "makes the status INERT is therefore not unreachedness: it "
                "is that the one decision cannot go wrong, because the two "
                "candidates are an ACT and that SAME rule's GUARD, never two "
                "rules' acts. Measured second, and it is the weaker leg: the "
                "pick is also output-neutral today — neutering the arm to "
                "cands[0] binds the guard lambda instead and still derives "
                "the identical {n_pairs}-row enum, because the act at L2068 carries "
                "no refusal cause of its own, so R-rollover contributes zero "
                "cause rows either way.",
    bound="LIVE THE MOMENT TWO RULES' ACTS SHARE A LINE. The inertness is a "
          "property of the current model, not of the code: it requires that "
          "no line in model.py carries the acts of two DIFFERENT rules. One "
          "such line makes the branch decide real rows immediately, and a "
          "wrong decision there is invisible at cause-set grain because a "
          "swap preserves the cause union exactly.",
    conditions=(
        "no source line in model.py is `_def_line` for two callables that "
        "are both the `act` of an operative rule",
        "the multi-candidate branch is entered for exactly ONE rule — "
        "R-rollover, at model.py L2068 — and the co-tenant on that line is "
        "that same rule's guard, so the scoring never chooses between two "
        "rules' acts (this is the condition that retires the status, not a "
        "count of zero entries)",
    ),
    kept_because="The guard is NOT removable just because it is inert. It "
                 "was added in response to a measured condition — two "
                 "lambdas on one line — which still holds; what makes it "
                 "inert is NOT that the branch goes unentered (it is entered, "
                 "once) but that the second lambda is a guard rather than "
                 "another rule's act, so its one live decision cannot go "
                 "wrong. Deleting it would make the join "
                 "silently wrong the first time that changes, and the "
                 "failure would be a mis-JOIN, not a crash "
                 "[[announced-action-must-be-taken]].",
    routed="Declared in the VIEW layer per the model leg's routing "
           "(design_data.py's recorded decline). Driven by "
           "test_generator.py's tiebreak-inertness test, which re-runs both "
           "conditions against the live join rather than restating them.",
    note="⚠ The inertness is asserted about THIS model at THIS anchor. The "
         "conditions above are what a future reader re-runs to retire or "
         "renew the status; the swap mutant in test_generator.py is what "
         "demonstrates the branch matters when it is NOT inert.",
)

# Both view-layer inert guards, for the generic renderer. Kept as a tuple even
# at length one so the render path is the same one a second entry would take.
VIEW_INERT_GUARDS = (COLUMN_TIEBREAK_INERT,)
