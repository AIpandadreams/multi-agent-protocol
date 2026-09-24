#!/usr/bin/env python3
"""Controls for render_head's ENTRY_ID_RE — the lane-tail id grammar.

⭐ THIS FILE EXISTS BECAUSE THE GRAMMAR HAD NO CONTROL AT ALL.
`render_head.py`'s own docstring records getting this regex wrong three times,
and `grep -rn ENTRY_ID_RE tools/tests/` returned nothing before this file. The
two existing render_head control files cover the CANARY exclusion and the ALERT
path; neither touches the id grammar. A tool whose most-revised expression is
untested will be revised wrong a fourth time. [[tests-must-not-create-the-contract]]

⛔ THE CONTRACT IS NOT THIS FILE. It is /wake step 6c, verbatim:

    "Entry ids may be written with or without the hyphen
     (`<FAMILY>-<n>` and `E<n>` are both live forms)."

That sentence is the specification. This file only measures the implementation
against it, which is why the DIVERGENCES block below is written as
divergence-from-spec and never as expected behaviour: a control that encodes
the bug as the contract launders the bug. [[emitter-and-verifier-are-one-grammar]]

HOW THIS FILE BEHAVES, and why it is green today:
  * INVARIANTS   — properties that hold now and must keep holding. A break here
                   is a regression and fails the run.
  * DIVERGENCES  — measured, PUBLISHED disagreements with /wake 6c (owner E1326,
                   E1328). Each asserts that the divergence is STILL PRESENT.
                   ⭐ So if someone fixes the regex, THIS FILE FAILS LOUDLY and
                   names the case to promote into INVARIANTS. It cannot silently
                   outlive the defect, and it cannot block the fix either.

Green today therefore means "the defect is where we left it", NOT "the tool is
correct". The run prints that distinction rather than leaving a bare check mark
to be quoted as health. [[guard-green-can-be-the-defect]]

Run: python tools/tests/render_head_id_grammar_controls.py
"""
import importlib.util
import sys
from pathlib import Path

# ⛔ THIS FILE IS A SCRIPT, NOT A PYTEST BATTERY, AND WITHOUT THIS GUARD IT TAKES
#    DOWN EVERY OTHER BATTERY IN THE SAME INVOCATION. Everything below runs at MODULE
#    level and reaches `sys.exit(...)`. Under collection that SystemExit escapes into
#    pytest's importer, which reports INTERNALERROR and aborts the WHOLE run at rc 3 --
#    not this file's legs lost, but every battery named alongside it.
#
# ⚠ AIMED AT THE ONE INVOCATION SHAPE THIS FLEET USES. `pytest tools/tests/` collects
#    and never reaches this file: the default `python_files` patterns are `test_*.py`
#    and `*_test.py` and this repo adds no pytest config widening them, so a directory
#    run skips every `*_controls.py`. The batteries are only ever run by NAMING them,
#    and `pytest tools/tests/*_controls.py` is exactly the form that dies at rc 3.
#
#    Swept per a fleet ruling (sweep the twenty-nine with the same guard, as one unit), the
#    same cure proven on wire_record_import_controls.py under an earlier ruling.
if __name__ != "__main__":
    import pytest

    pytest.skip(
        "render_head_id_grammar_controls.py is a SCRIPT leg, not a pytest battery: it does its work at module "
        "level and ends in sys.exit(). Run it directly -- `python tools/tests/render_head_id_grammar_controls.py` "
        "-- which is how the leg census counts it (a script leg, not a pytest leg). "
        "Collected here it would abort the whole run at rc 3.",
        allow_module_level=True)

# Console-encoding cure, same house form as the sibling control files: a
# cp1252-unencodable glyph on stdout takes the run down mid-report. Route the
# report through a replace-on-error writer instead of trusting the console.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:                                          # noqa: BLE001
    pass

REPO = Path(__file__).resolve().parents[2]
PROD = REPO / "tools" / "render_head.py"

# ⚠ MUTATION MODE — the ONLY way to point this file at a non-production binary,
# and it is deliberately awkward. A control that has never been shown to FAIL
# certifies nothing, so the mutation path has to exist; but a control that can
# be quietly aimed at a copy is the defect the sibling file was written to cure
# ([[guards-must-point-at-production]]). Both env vars are required, and the
# banner below makes a mutant run impossible to mistake for a certification in
# a scrollback. [[mutation-test-discipline]]
import os

_MUTANT = os.environ.get("RH_ID_CONTROL_MUTANT")
if _MUTANT and os.environ.get("RH_ID_CONTROL_MUTATION_TEST") == "i-am-mutating":
    PROD = Path(_MUTANT)
    _MUTATING = True
else:
    _MUTATING = False

fails = []
notes = []


def leg(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
    if detail:
        print(f"          {detail}")
    if not ok:
        fails.append(f"{name}: {detail}")


def load_prod():
    """Import PRODUCTION render_head, never a workpaper copy.

    [[guards-must-point-at-production]] — this repo holds ~30 render_head.py
    copies under workpapers/ and .scratch/. A control that imports by bare name
    can bind one of those and certify a file nobody runs.
    """
    spec = importlib.util.spec_from_file_location("_rh_prod", PROD)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:                # module runs argparse under __main__ guard
        pass
    return mod


print("=" * 72)
print("render_head ENTRY_ID_RE grammar controls")
if _MUTATING:
    print("⛔⛔ MUTATION RUN — this is NOT a certification of production.")
    print("    Any result below describes a deliberately altered binary.")
print(f"  {'MUTANT binary' if _MUTATING else 'production binary'}: {PROD}")
if not PROD.is_file():
    print("⛔ production render_head.py not found — cannot certify anything")
    sys.exit(2)

rh = load_prod()
RX = getattr(rh, "ENTRY_ID_RE", None)
if RX is None:
    print("⛔ ENTRY_ID_RE is absent from production render_head.py.")
    print("   The symbol was renamed or removed. This control is now blind and")
    print("   MUST be repointed rather than deleted. Failing closed.")
    sys.exit(2)

# ⭐ REPOINTED (2026-08-15, per a fleet ruling), and the reason is the whole point of this
# file. The grammar gained a SECOND arm (ENTRY_ID_NOSEP_RE) and production reads
# both through ONE entry point, `match_entry_id`. This control went on binding
# ENTRY_ID_RE — the separated arm alone — and therefore kept certifying that
# `E730` "is rejected" while production had just started ACCEPTING it. It was
# GREEN and it was publishing a false statement: "3 divergences from /wake 6c
# still present". A control bound to a COMPONENT of the grammar cannot see a
# change to the grammar [[emitter-and-verifier-are-one-grammar]], and green is
# the worst way for that to present [[guard-green-can-be-the-defect]].
#
# The subject of this file is the grammar PRODUCTION USES, so it binds what
# production calls. ENTRY_ID_RE is kept above only so its absence still fails
# closed and so the arm-existence leg below can assert the union has not
# silently collapsed back to one arm.
MATCH = getattr(rh, "match_entry_id", None)
NOSEP = getattr(rh, "ENTRY_ID_NOSEP_RE", None)
if MATCH is None:
    print("⛔ match_entry_id is absent from production render_head.py.")
    print("   Production reads the id grammar through that entry point; without it")
    print("   this control can only bind a component and would certify half the")
    print("   grammar while reporting on all of it. Failing closed.")
    sys.exit(2)
print(f"  separated arm     : {RX.pattern}")
print(f"  separator-less arm: {NOSEP.pattern if NOSEP else '<ABSENT>'}")
print("  bound entry point : match_entry_id (the union — what production calls)")
print()


def m(s):
    """Match against the heading TEXT, as find_sections supplies it.

    ⚠ The regex is ^-anchored. Passing a raw '## ...' line makes EVERY case
    fail uniformly, which reads like a catastrophic finding and is really a
    broken probe — owner burned exactly this twice on 2026-08-11 before the
    uniformity gave it away. The marker is stripped here so the control tests
    the grammar and not the caller. [[instrument-polarity-controls]]
    """
    return MATCH(s.lstrip("#").strip())


# ----------------------------------------------------------------- INVARIANTS
print("INVARIANTS — must hold; a break here is a regression")

leg("hyphenated id, single recipient, matches",
    bool(m("## ORCH → OWNER — SYN-2720 rest of heading")),
    "the canonical orch form is the one shape the renderer has always keyed")

leg("bare hyphenated id with no addressing prefix matches",
    bool(m("## SYN-1228 rest")),
    "/wake 6c names the prefixed form as live; the prefix is optional")

leg("ASCII '->' arrow is accepted alongside U+2192",
    bool(m("## ORCH -> OWNER — SYN-2720 rest")),
    "both arrows appear in the corpus")

_g = m("## ORCH → OWNER — SYN-2720 rest")
leg("captures prefix and number as separate groups",
    bool(_g) and _g.group(1) == "SYN" and _g.group(2) == "2720",
    f"groups={_g.groups() if _g else None}")

leg("a heading with no id at all does NOT match",
    m("## WAKE 2026-08-11T08:44:19-0400 — owner / chan — heartbeat-stale") is None,
    "the instrument must be able to say no, or it discriminates nothing")

leg("prose mentioning an id mid-sentence does not match from the left",
    m("## see SYN-2720 for context") is None,
    "an id OCCURS only where the heading publishes what the entry IS "
    "(/wake 6c); a body mention is not an occurrence")

# ---- PROMOTED FROM DIVERGENCES by the P5 cure, 2026-08-11 (builder) ---------
# Evidence + controls: a cure workpaper in the private workspace (CONTROLS.md,
# controls.py 4/4, CORPUS_IMPACT.txt). These three were DIVERGENCE legs until
# that cure; they are invariants now, and this file failing is what made the
# promotion happen rather than letting the grammar widen unrecorded.

leg("SPACE-separated id form matches (the P5 subject)",
    bool(m("## BUILDER → ORCH — SYN 1482 [v2.8] rest")),
    "the motivating defect: one builder-to-orch lane file had 40 entry "
    "headings and ZERO visible ids, so that family's tail reported a stale id, "
    "~1,250 entries stale. Measured pre-cure, cured, re-measured (+1,845 ids).")

leg("multi-recipient addressing matches",
    bool(m("## ORCH → OWNER+ALL — SYN-2711 rest")),
    "recipient slot widened to [A-Z][A-Za-z+& ]*? for the live '+'-joined and "
    "multi-word house forms (ORCH+CREATOR, ALL SEATS). Was E1326 §1-2's "
    "published divergence; cured deliberately, not as a side effect.")

leg("multi-WORD recipient matches",
    bool(m("## BUILDER → ALL SEATS — SYN 1394 [v2.8] rest")),
    "same widening, second live form. Recovered only 2 headings corpus-wide "
    "and moved NO tail — correctness, not a load-bearing part of the cure, "
    "and said so here so nobody reads it as one.")

leg("a DATE-shaped number is still not an id (the fabrication guard)",
    m("## WAKE 2026-08-11T00:14:31-0400 — owner / chan — heartbeat-stale") is None,
    "owner named this before the cure was written (in an owner-to-orch lane "
    "§3a): admitting a space turns WAKE headings into a 'WAKE-2026' id across "
    "all four sentinel_wake_* lanes. Guard is `(?!-\\d)`; sentinel lanes "
    "measured at ZERO ids both pre- and post-cure. Duplicates the no-id-at-all "
    "leg above BY SHAPE but not by reason — that one asks whether the "
    "instrument can say no, this one asks whether THIS cure broke that.")

# ---- PROMOTED FROM DIVERGENCES by the >=3-digit floor cure, 2026-08-15 -------
# A fleet ruling, ruled binding by the orchestrator. Evidence:
# a grammar-floor workpaper in the private workspace (measure_equalities.py — three
# equalities: 1,326 newly-visible == 1,326 E-form, 0 minted-beyond-E, 0 lost;
# prove_floor_earns_it.py — the floor's own load-bearing measurement) and
# tools/tests/render_head_f3_both_forms_controls.py (F3 fires in BOTH heading
# forms, fresh-head negative control passes in both, and the pre-amendment
# grammar is shown to MISS the separator-less stale head at rc=0).

leg("ZERO-separator id form matches (the ruled subject)",
    bool(m("## E730 rest of heading")),
    "/wake 6c names `E730` a live form verbatim and the grammar rejected it, so "
    "every E<n> owner entry was invisible to the lane scan. 1,326 headings "
    "recovered corpus-wide.")

leg("ZERO-separator id behind an addressing prefix matches",
    bool(m("## OWNER → ORCH — E1322 rest")),
    "owner's whole outbound lane: 8 of 8 headings unseen (E1328 §1). The "
    "recipient axis was cured at P5 and the separator axis here — separately, "
    "which is what the independence claim below now rests on.")

_e = m("## OWNER → ORCH — E1322 rest")
leg("…and captures the SAME groups as the separated arm",
    bool(_e) and _e.group(1) == "E" and _e.group(2) == "1322",
    f"groups={_e.groups() if _e else None} — the two arms must be "
    "interchangeable at the call site or _lane_scan's group(1)/group(2) reads "
    "mean different things depending on which arm fired "
    "[[emitter-and-verifier-are-one-grammar]]")

leg("⭐ a 1-2 digit zero-separator run is REFUSED (the >=3 floor)",
    m("## R5 - narrow, codex only, explicitly NOT a re-review") is None,
    "the floor's actual job, and this is a REAL corpus heading, not an invented "
    "probe: prove_floor_earns_it.py measures that dropping the floor to >=1 "
    "mints `R-5` out of this very sentence. A bare capital followed by one "
    "digit is prose. ⚠ The same measurement shows >=2 would also refuse it — "
    "THREE is a chosen height, not a measured one, and no leg here claims "
    "otherwise [[decoration-verdict-is-a-question]].")

print()

# ---------------------------------------------------------------- DIVERGENCES
print("DIVERGENCES from /wake 6c — measured and published (owner E1326, E1328).")
print("Each asserts the divergence is STILL PRESENT. A FAIL here may mean the")
print("defect was CURED: verify, then promote the case into INVARIANTS above.")

DIVERGENCES = [
    # ⭐⭐ TWO CASES WERE REMOVED FROM THIS LIST (2026-08-15, per a fleet ruling) BECAUSE
    # THEY WERE CURED, and they were promoted into INVARIANTS above rather than
    # deleted — this file's own recovery text demands exactly that ("If this was
    # an intentional fix, move this case into INVARIANTS and cite the commit").
    # The cured cases:
    #   `E730`                      — the bare zero-separator form
    #   `OWNER → ORCH — E1322 rest` — zero-separator behind an addressing prefix
    # Both are now matched by ENTRY_ID_NOSEP_RE, so owner's whole outbound lane
    # (8 of 8 headings unseen at E1328 §1) is visible to the lane scan.
    #
    # ⚠ They did NOT fail here when the cure landed. This control was binding
    # ENTRY_ID_RE, the separated arm alone, so it went on asserting "rejected"
    # about a pattern production no longer consults. The promotion below is not
    # bookkeeping — it is the repair of a control that had gone blind
    # [[amend-at-the-claim-site]] [[guards-must-point-at-production]].
    ("tick namespace is rejected",
     "ORCH → OWNER — ORCH-T008 rest",
     "id number slot is (\\d+); 'T008' cannot match. The whole tick lineage "
     "is invisible at every seat (E1326 §1)."),
]

for name, probe, why in DIVERGENCES:
    still_broken = m(probe) is None
    leg(f"[divergence] {name}", still_broken,
        why if still_broken else
        f"⭐ NO LONGER DIVERGENT — {probe!r} now matches. If this was an "
        f"intentional fix, move this case into INVARIANTS and cite the "
        f"commit. If it was accidental, the grammar widened without a ruling.")
    if still_broken:
        notes.append(name)

print()

# ---- composition check: the causes are INDEPENDENT, not one defect ----------
print("MECHANISM — the causes must be shown to be independent")

# ⭐ REWRITTEN TWICE, and the rewrites ARE the evidence. This block originally
# asserted independence by requiring both axes to still FAIL — two simultaneous
# failures that could have shared one root. P5 cured the recipient axis and the
# claim was restated as "recipient CURED, separator NOT". A fleet ruling has now
# cured the separator axis too, so that form is dead as well: nothing here can
# be shown independent by exhibiting a live failure any more.
#
# Independence is now measured HISTORICALLY, which is the strongest form the
# evidence has ever supported: the two axes were cured by DIFFERENT changes at
# DIFFERENT times, and each cure demonstrably left the other axis untouched.
# That is what "independent causes" asserts, and unlike the previous two
# versions it cannot rot — a future cure cannot falsify a record of which cure
# closed what. What it CAN do is silently stop being checked, so the legs below
# are kept as live matches over the corpus forms rather than as a comment.
leg("recipient axis and separator axis are BOTH live and BOTH matched",
    m("## OWNER → ORCH+ALL — E1320 rest") is not None
    and m("## E1320 rest") is not None
    and m("## OWNER → ORCH+ALL — E-1320 rest") is not None,
    "the full cross-product: multi-recipient×zero-separator, bare×zero-"
    "separator, multi-recipient×hyphenated. All three match, so neither axis "
    "is silently gating the other [[discriminator-needs-an-independent-difference]]")

# ⛔ THE INDEPENDENCE CLAIM NEEDS SOMETHING THAT STILL FAILS, or it is a claim
# about a grammar that now says yes to everything and the block above would
# pass just as well on a `.*` pattern [[control-passing-for-the-wrong-reason]].
# The tick namespace is that case: still divergent, and it varies the NUMBER
# slot, which is a third axis neither cure touched.
leg("…and a THIRD axis is still uncured, so the block can still fail",
    m("## ORCH → OWNER — ORCH-T008 rest") is None
    and m("## ORCH → OWNER+ALL — ORCH-T008 rest") is None,
    "the tick namespace is refused under BOTH recipient forms and BOTH "
    "separator forms — an axis orthogonal to the two that were cured. If this "
    "ever passes, the grammar widened without a ruling.")

print("-" * 72)
if fails:
    print(f"⛔ {len(fails)} control(s) FAILED")
    for f in fails:
        print("   -", f)
    print()
    print("   If the failures are all [divergence] legs, the tool may have been")
    print("   FIXED. That is good news and still a failure of this file: promote")
    print("   the cured cases into INVARIANTS so the fix is guarded going forward.")
    sys.exit(1)

print(f"✅ render_head id-grammar controls: all green "
      f"({len(notes)} divergence(s) from /wake 6c still present)")
print("   ⚠ GREEN HERE MEANS 'the defect is where we left it', NOT 'the grammar")
print("     is correct'. render_head still cannot see the TICK namespace")
print("     (ORCH-T008) — the whole tick lineage, at every seat.")
print("     Cured and now INVARIANTS above, not divergences: multi-recipient +")
print("     space-separated forms (2026-08-11, P5); ZERO-separator ids such as")
print("     E730 / E1322 (2026-08-15, a fleet ruling, +1,326 headings).")
print("   ⚠ And the >=3-digit floor on the zero-separator arm is a CHOSEN height:")
print("     measured to cost 0 real ids and to refuse the one prose fabrication")
print("     in the corpus, but >=2 does both equally well. Not evidence-backed")
print("     above >=2 — see the private grammar-floor workpaper.")
