#!/usr/bin/env python3
"""verdict_completeness — U1-as-amended (per an orchestrator ruling): is an anchor's dispatch
output actually a GRADED verdict, or only a terminated one?

Commission: an orchestrator ruling's item U1, SUPERSEDED IN FULL by a later ruling after owner retracted
a premise in an earlier seat report. ⚠ The retracted premise mattered: the original commission asserted codex's r2 file
carried NO grade line and made the real r2 file a MUST-VOID control. It carries
one (L5018, `Package verdict: REQUEST-CHANGES`, codex's own voice); owner's
probe was a case-sensitive grep for `VERDICT`. So the real file is a MUST-PASS
control here, inverted from the original commission. This module is HARDENING
against a real-but-unfired hazard, not a repair -- and saying that plainly is
part of the deliverable. [[claims-must-survive-every-available-reading]]

THE SURVIVING HAZARD, which is real and measured. The r2 transcript carries
FOUR grade-shaped lines. A grade-shaped search that stops at the FIRST match
cites the wrong voice and the wrong round:

    L97    "Package verdict CONFIRM / REVISE / REQUEST-CHANGES with numbered
            findings"                        -- the PROMPT's instruction text
    L2452  "## VERDICT: REQUEST-CHANGES"     -- echo of the opus r1 file
    L3223  "## VERDICT: REQUEST-CHANGES"     -- echo inside tool output
    L5018  "Package verdict: REQUEST-CHANGES"-- ⭐ codex's OWN voice, the real one
    L5072  "Package verdict: REQUEST-CHANGES"-- post-terminator summary tail

HOW OWN VOICE IS DECIDED, and it is measured rather than assumed. The transcript
is a sequence of REGIONS opened by a marker on its own line. Walking back from a
grade line to the nearest preceding marker discriminates all four exactly:

    L2452 -> `exec`        (2027)   tool output          EXCLUDE
    L3223 -> `exec`        (3220)   tool output          EXCLUDE
    L5018 -> `codex`       (5017)   the anchor speaking  ATTRIBUTE
    L5072 -> `tokens used` (5070)   post-verdict tail    EXCLUDE

A proximity rule (`nearest codex marker`) was tried first and FAILS: L2452's
nearest `codex` is 427 lines back and L3223's is 242 back, so both would have
attributed. Region-opening markers are the discriminator; distance is not.
[[discriminator-needs-an-independent-difference]]

⛔ MISSING GRADE IS **VOID**, NEVER FAIL, AND NEVER INFERRED. A dispatch whose
grade cannot be attributed tells us nothing about the package under review -- it
is a broken instrument, not a failing subject. VOID means redispatch once with
the grade instruction tightened. [[honest-failure-outcomes]]

RC DISCIPLINE, the two-limbed form: status and rc are emitted TOGETHER so a
verdict is never confused with an outage.
    rc 0  PASS  -- terminator present AND an own-voice grade attributed
    rc 2  VOID  -- the checker ran and reached a verdict of "not gradeable"
    rc 1  ERROR -- the checker itself could not run (outage, not a verdict)
"""
from __future__ import annotations

import argparse
import io
import re
import sys

#: Region-opening markers, matched as a WHOLE stripped line. Anything opened by
#: a non-`codex` marker is not the anchor speaking.
OWN_VOICE_MARKER = "codex"
REGION_MARKERS = {"codex", "exec", "thinking", "user", "tokens used",
                  "turn diff", "system"}

#: The two grade forms the prompt grammars demand, case-insensitive. The COLON
#: is required and is load-bearing: it is what excludes L97, the prompt's own
#: instruction sentence ("Package verdict CONFIRM / REVISE / ..."), which names
#: every grade and asserts none.
GRADE_RE_ORCH4941 = re.compile(
    r"^\s*(?:##\s*VERDICT:|Package\s+verdict:)\s*"
    r"(?P<grade>CONFIRM|REVISE|REQUEST-CHANGES|APPROVE|BLOCK)\b",
    re.IGNORECASE)

#: ⛔ MEASURED, AND IT CHANGES HOW THIS MAY BE WIRED. The amending ruling names
#: `package verdict:` / `## VERDICT:` as "the two forms the prompt grammars
#: demand". That is TRUE of the plan-gate r2 dispatch and FALSE as a general
#: rule: EACH DISPATCH'S PROMPT SPECIFIES ITS OWN FORM. Measured in this tree --
#:   codex-out-a1hk.txt              prompt: "verdict CONFIRM or REVISE"
#:                                   emitted L492: `verdict REVISE`  (bare, lowercase)
#:   codex-out-auth1528-framing-r2   prompt: "End with `VERDICT:` one word"
#:   codex-out-plangate-r2           emitted L5018: `Package verdict: REQUEST-CHANGES`
#: Run against thirty real anchor outputs with the amending ruling's pair hardcoded, this
#: checker VOIDed essentially ALL of them. Wired as a gate in that state it
#: would VOID nearly every dispatch in the fleet -- a catastrophic fail-closed
#: bought by 15 green synthetic controls.
#:
#: The defect is structural, not a missing alternative: the PROMPT is the
#: emitter's grammar spec, and a verifier that hardcodes a different one is not
#: checking the same language. [[emitter-and-verifier-are-one-grammar]]
#: So the caller MUST supply the form its own prompt demanded (--grade-re), and
#: the default is documented as SCOPED to the amending ruling's dispatch family rather
#: than presented as universal. A permissive fallback is deliberately NOT
#: offered: widening until everything passes would make the check unable to fail.
GRADE_RE = GRADE_RE_ORCH4941

TERMINATOR_RE = re.compile(r"^\s*END OF VERDICT\s+(?P<nonce>EOV-[0-9a-fA-F]+)\s*$")


class Result:
    def __init__(self, status, reason, **kw):
        self.status = status          # PASS | VOID | ERROR
        self.reason = reason
        self.__dict__.update(kw)

    @property
    def rc(self):
        return {"PASS": 0, "VOID": 2, "ERROR": 1}[self.status]

    def render(self):
        out = [f"STATUS: {self.status}", f"REASON: {self.reason}"]
        for k in ("terminator_line", "nonce", "grade_line", "grade",
                  "attributed_marker", "excluded", "grammar"):
            v = getattr(self, k, None)
            if v is not None:
                out.append(f"{k.upper()}: {v}")
        out.append(f"RC: {self.rc}")
        return "\n".join(out)


def check(text: str, expect_nonce: str | None = None, grade_re=None) -> Result:
    # The caller's own prompt grammar wins. Falling back to the amending ruling's pair
    # is correct ONLY for that dispatch family; see GRADE_RE's note.
    grade_re = grade_re or GRADE_RE
    lines = text.splitlines()

    # 1. Terminator. Its LINE NUMBER bounds the verdict body: a grade after it
    #    is a summary tail, not the verdict.
    term_no = None
    nonce = None
    for i, ln in enumerate(lines, 1):
        m = TERMINATOR_RE.match(ln)
        if m:
            term_no, nonce = i, m.group("nonce")
            # keep scanning: the LAST terminator is the dispatch's own
    if term_no is None:
        return Result("VOID", "no terminator line found "
                              "(`END OF VERDICT EOV-<nonce>`)")
    if expect_nonce and nonce != expect_nonce:
        return Result("VOID",
                      f"terminator nonce mismatch: found {nonce}, "
                      f"expected {expect_nonce}",
                      terminator_line=term_no, nonce=nonce)

    # 2. Every grade-shaped line, each attributed to its region.
    candidates = []
    marker_no, marker = None, None
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s in REGION_MARKERS:
            marker_no, marker = i, s
            continue
        m = grade_re.match(ln)
        if m:
            candidates.append({
                "line": i, "grade": m.group("grade").upper(),
                "marker": marker, "marker_line": marker_no,
                "own_voice": marker == OWN_VOICE_MARKER,
                "before_terminator": i < term_no,
            })

    if not candidates:
        return Result("VOID", "terminator present but NO line matched the "
                              "expected grade grammar -- terminated, not "
                              "graded IN THIS GRAMMAR (if the dispatch's "
                              "prompt demanded a different form, pass it "
                              "with --grade-re; a VOID here may indicate a "
                              "grammar mismatch, not a gradeless anchor)",
                      terminator_line=term_no, nonce=nonce,
                      grammar=grade_re.pattern[:70])

    attributable = [c for c in candidates
                    if c["own_voice"] and c["before_terminator"]]
    excluded = "; ".join(
        f"L{c['line']}({c['marker'] or 'no-marker'}"
        f"{',post-terminator' if not c['before_terminator'] else ''})"
        for c in candidates if c not in attributable)

    if not attributable:
        return Result("VOID",
                      f"{len(candidates)} grade-shaped line(s) found but NONE in "
                      f"the anchor's own voice before the terminator -- every one "
                      f"is an echo or a tail",
                      terminator_line=term_no, nonce=nonce, excluded=excluded)

    # The own-voice grade CLOSEST to the terminator is the dispatch's verdict:
    # an anchor that restates its grade mid-run has not issued two verdicts.
    best = max(attributable, key=lambda c: c["line"])

    # ⚠ A DISAGREEMENT AMONG OWN-VOICE GRADES IS NOT SILENTLY RESOLVED BY
    # TAKING THE LAST ONE. Two different grades in the anchor's own voice means
    # the run is not gradeable by this instrument, and guessing which the anchor
    # meant is exactly the inference the amending ruling forbids.
    grades = {c["grade"] for c in attributable}
    if len(grades) > 1:
        return Result("VOID",
                      f"own-voice grades DISAGREE ({sorted(grades)}) -- not "
                      f"resolved by recency; redispatch",
                      terminator_line=term_no, nonce=nonce,
                      excluded=excluded or None)

    return Result("PASS", "terminator present and an own-voice grade attributed",
                  terminator_line=term_no, nonce=nonce,
                  grade_line=best["line"], grade=best["grade"],
                  attributed_marker=f"{best['marker']}@{best['marker_line']}",
                  excluded=excluded or None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="anchor output file")
    ap.add_argument("--nonce", help="expected EOV- terminator nonce")
    ap.add_argument("--grade-re", help="regex for THIS dispatch's grade line, "
                    "with a (?P<grade>...) group -- take it from the prompt that "
                    "demanded it, never from habit")
    ap.add_argument("--controls", action="store_true")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    if args.controls:
        return _controls()
    if not args.path:
        ap.error("path required unless --controls")
    try:
        text = io.open(args.path, "r", encoding="utf-8", errors="replace").read()
    except OSError as exc:
        # An unreadable file is an OUTAGE, not a verdict about the package.
        r = Result("ERROR", f"cannot read {args.path}: {exc.__class__.__name__}")
        print(r.render())
        return r.rc
    gre = re.compile(args.grade_re, re.IGNORECASE) if args.grade_re else None
    r = check(text, args.nonce, gre)
    print(r.render())
    return r.rc


def _controls() -> int:
    """The amending ruling's three controls, plus the ones that keep them honest."""
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    real = os.path.join(here, "workpapers", "plan-gate-callsig-2026-08-30",
                        "codex-out-plangate-r2.txt")
    bad = 0

    def show(name, ok, detail=""):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")

    # (1) THE REAL FROZEN r2 FILE MUST PASS, attributing 5018 and NOT the decoys.
    if not os.path.exists(real):
        show("control 1: real r2 file present", False,
             "file absent — an absent corpus is NOT a passing control")
    else:
        r = check(io.open(real, encoding="utf-8", errors="replace").read())
        show("control 1a: real r2 file PASSES", r.status == "PASS", r.reason)
        show("control 1b: attributes L5018", getattr(r, "grade_line", None) == 5018,
             f"got L{getattr(r, 'grade_line', None)}")
        show("control 1c: grade is REQUEST-CHANGES",
             getattr(r, "grade", None) == "REQUEST-CHANGES")
        exc = getattr(r, "excluded", "") or ""
        for decoy in ("L2452", "L3223", "L5072"):
            show(f"control 1d: {decoy} excluded, not attributed", decoy in exc)
        show("control 1e: L97 never even a candidate (no colon)",
             "L97" not in exc and getattr(r, "grade_line", None) != 97)

    # (2) terminator-only fixture VOIDs
    r = check("some prose\nDISPATCH_STATUS: OK\nEND OF VERDICT EOV-deadbeef\n")
    show("control 2: terminator-only VOIDs", r.status == "VOID", r.reason)

    # (3) echo-only fixture VOIDs (decoys present, own-voice grade stripped)
    echo_only = ("codex\nthinking about it\n"
                 "exec\n succeeded in 10ms:\n"
                 "## VERDICT: REQUEST-CHANGES\n"
                 "exec\n succeeded in 12ms:\n"
                 "Package verdict: CONFIRM\n"
                 "END OF VERDICT EOV-deadbeef\n")
    r = check(echo_only)
    show("control 3: echo-only VOIDs", r.status == "VOID", r.reason)

    # (4) POSITIVE CONTROL on the fixture path — without it, controls 2/3 could
    # pass because the checker VOIDs everything. [[control-passing-for-the-wrong-reason]]
    r = check("exec\n succeeded:\n## VERDICT: CONFIRM\n"
              "codex\nPackage verdict: REVISE\n"
              "END OF VERDICT EOV-deadbeef\n")
    show("control 4: own-voice grade after an echo PASSES", r.status == "PASS",
         r.reason)
    show("control 4b: and attributes the OWN-VOICE one, not the echo",
         getattr(r, "grade", None) == "REVISE")

    # (5) no terminator at all VOIDs
    r = check("codex\nPackage verdict: CONFIRM\n")
    show("control 5: graded but unterminated VOIDs", r.status == "VOID", r.reason)

    # (6) nonce mismatch VOIDs
    r = check("codex\nPackage verdict: CONFIRM\nEND OF VERDICT EOV-aaaa\n",
              expect_nonce="EOV-bbbb")
    show("control 6: nonce mismatch VOIDs", r.status == "VOID", r.reason)

    # (7) disagreeing own-voice grades VOID rather than resolve by recency
    r = check("codex\nPackage verdict: CONFIRM\n"
              "codex\nPackage verdict: REVISE\n"
              "END OF VERDICT EOV-aaaa\n")
    show("control 7: disagreeing own-voice grades VOID", r.status == "VOID",
         r.reason)

    # (8) rc discipline: VOID and ERROR are DIFFERENT codes
    show("control 8: VOID rc=2 and ERROR rc=1 are distinct",
         Result("VOID", "x").rc == 2 and Result("ERROR", "x").rc == 1
         and Result("PASS", "x").rc == 0)

    # ⭐ (9) THE GRAMMAR-MISMATCH LEG, and it is the one that keeps this module
    # honest. The first eight controls are the amending ruling's family plus fixtures I wrote; run
    # against 30 REAL anchor outputs the default grammar VOIDed essentially all
    # of them, because each dispatch's prompt demands its own form. This leg
    # pins BOTH halves on a second real file: the default VOIDs it, and the
    # form ITS OWN prompt demanded PASSES it. Without the second half a VOID
    # could not be told apart from a genuinely gradeless anchor -- which is the
    # difference between "redispatch" and "the anchor failed to grade".
    other = os.path.join(here, "workpapers", "a1-ext-hooks-clickable-2026-08-26",
                         "codex-out-a1hk.txt")
    if not os.path.exists(other):
        show("control 9: second real anchor output present", False,
             "file absent — an absent corpus is NOT a passing control")
    else:
        t = io.open(other, encoding="utf-8", errors="replace").read()
        r_def = check(t)
        show("control 9a: default ruled grammar VOIDs a differently-graded "
             "real file", r_def.status == "VOID", r_def.reason[:60])
        gre = re.compile(r"^\s*verdict\s+(?P<grade>CONFIRM|REVISE|REQUEST-CHANGES)\b",
                         re.IGNORECASE)
        r_own = check(t, None, gre)
        show("control 9b: that file's OWN prompt grammar PASSES it",
             r_own.status == "PASS", r_own.reason)
        show("control 9c: attributing its own-voice line, not the tail",
             getattr(r_own, "grade_line", None) == 492
             and "L520" in (getattr(r_own, "excluded", "") or ""),
             f"L{getattr(r_own, 'grade_line', None)}, "
             f"excluded={getattr(r_own, 'excluded', None)}")

    print(f"\n{'GREEN' if bad == 0 else f'RED ({bad} failing)'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
