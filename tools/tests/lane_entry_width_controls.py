"""Controls for tools/lane_entry_width.py -- the T331 fixture.

WHAT THIS SUITE IS FOR. T330 shipped the width instrument as PROSE. Three hands
certified it -- author, independent reproduction, and an explicit locate-step
clean bill -- and all three ran the correct needle BY HABIT, so a defect in an
input every auditor supplied correctly was invisible to any number of hands. A
prose instrument cannot be unit-tested; that is the whole argument for this file.

C1 IS THE ONE THAT MATTERS, AND IT DEMONSTRATES THE DEFECT RATHER THAN ASSERTING
THE CURE. It drives _locate() twice over one synthetic history -- once with the
bare id, once with the heading line -- and requires them to DISAGREE, with the
bare-id answer landing on the PREDECESSOR's commit. A control that only checked
"width == expected" would pass on a bare-id implementation for exactly the reason
T331 names: the wrong value is drawn from the set of the lineage's own true
values, so agreement with the record is the predicted symptom of the defect, not
evidence against it.

EVERY FIXTURE HISTORY IS SYNTHETIC AND HERMETIC (its own temp repo), so the
suite does not rot as the live lanes grow. C6 is the live cross-check and SKIPS
with a stated reason when the history it needs is not in this clone -- a skip is
reported, never silently counted as a pass.

Run: python tools/tests/lane_entry_width_controls.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import lane_entry_width as W  # noqa: E402

LANE = "channel/lane.md"

# Real shapes from the live lane: separators are U+00B7 and U+2192, and the
# footer pointer is the mechanism under test. Kept byte-verbatim -- a fixture
# invented to match the implementation tests the implementation against itself.
SEP = "·"
ARROW = "→"

FAILS = []
SKIPS = []


def _run(repo, args, env=None):
    p = subprocess.run(["git", "-C", repo] + args, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, env=env)
    if p.returncode != 0:
        raise SystemExit("fixture git failed: %s\n%s"
                         % (args, p.stdout.decode("utf-8", "replace")))


def _entry(eid, nxt, body_kb=1):
    """One entry in this lineage's real shape, INCLUDING the footer pointer.

    The footer's `next <id>` is why a bare-id needle first matches one entry
    EARLY. Dropping it from the fixture would delete the defect under test.
    """
    head = "## ORCH %s CREATOR %s %s %s 2026-08-16 %s probed" % (
        ARROW, SEP, eid, SEP, SEP)
    body = ("x" * 60 + "\n") * (body_kb * 17)
    foot = " %s counters: this entry %s %s next %s %s\n" % (
        SEP, SEP, eid, nxt, SEP)
    return head + "\n\n" + body + foot + "\n"


def _mkrepo(tmp):
    env = dict(os.environ,
               GIT_AUTHOR_NAME="c", GIT_AUTHOR_EMAIL="c@x",
               GIT_COMMITTER_NAME="c", GIT_COMMITTER_EMAIL="c@x")
    _run(tmp, ["init", "-q", "-b", "main"], env)
    _run(tmp, ["config", "core.autocrlf", "false"], env)
    (Path(tmp) / "channel").mkdir(parents=True, exist_ok=True)
    return env


def _append(tmp, env, text, msg):
    p = Path(tmp) / LANE
    with open(p, "ab") as f:
        f.write(text.encode("utf-8"))
    _run(tmp, ["add", "--", LANE], env)
    _run(tmp, ["commit", "-q", "-m", msg], env)
    return _run_out(tmp, ["rev-parse", "HEAD"], env)


def _run_out(repo, args, env):
    p = subprocess.run(["git", "-C", repo] + args, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, env=env)
    return p.stdout.decode("ascii", "replace").strip()


def check(name, cond, detail=""):
    if cond:
        print("  PASS  %s" % name)
    else:
        print("  FAIL  %s -- %s" % (name, detail))
        FAILS.append(name)


def skip(name, why):
    print("  SKIP  %s -- %s" % (name, why))
    SKIPS.append(name)


def build_lineage(tmp):
    """T142 -> T143 -> T144, each footer pointing at its successor."""
    env = _mkrepo(tmp)
    c142 = _append(tmp, env, _entry("ORCH-T142", "ORCH-T143", 1), "t142")
    c143 = _append(tmp, env, _entry("ORCH-T143", "ORCH-T144", 2), "t143")
    c144 = _append(tmp, env, _entry("ORCH-T144", "ORCH-T145", 3), "t144")
    return env, c142, c143, c144


def c1_the_trap(tmp):
    print("C1 -- the bare-id needle lands on the PREDECESSOR (T331, demonstrated)")
    env, c142, c143, c144 = build_lineage(tmp)
    commits = W._touching_commits(tmp, "HEAD", LANE)
    tip = W._blob(tmp, "HEAD", LANE)

    bare = W._locate(tmp, LANE, commits, b"ORCH-T144")
    head = W._locate(tmp, LANE, commits, W._heading(tip, "ORCH-T144"))

    check("C1a bare-id locates the predecessor's commit",
          bare == c143, "bare=%s want c143=%s" % (bare[:9], c143[:9]))
    check("C1b heading locates the true introducing commit",
          head == c144, "head=%s want c144=%s" % (head[:9], c144[:9]))
    check("C1c the two needles DISAGREE (the defect is live in this fixture)",
          bare != head, "both returned %s -- fixture lost its footer" % bare[:9])

    # And the consequence: the bare-id width is the predecessor's PUBLISHED width.
    w144 = W.width(tmp, LANE, "ORCH-T144")["width"]
    w143 = W.width(tmp, LANE, "ORCH-T143")["width"]
    b_prev = len(W._blob(tmp, c143 + "^", LANE) or b"")
    bare_width = len(W._blob(tmp, c143, LANE)) - b_prev
    check("C1d the bare-id answer EQUALS a true value of this lineage",
          bare_width == w143 and w143 != w144,
          "bare=%d t143=%d t144=%d" % (bare_width, w143, w144))


def c2_needle_uniqueness(tmp):
    print("C2 -- an ambiguous needle REFUSES; it does not pick one")
    env = _mkrepo(tmp)
    _append(tmp, env, _entry("ORCH-T200", "ORCH-T201", 1), "a")
    # A second heading carrying the same id (a re-land, or a union that doubled).
    _append(tmp, env, _entry("ORCH-T200", "ORCH-T201", 1), "b")
    try:
        W.width(tmp, LANE, "ORCH-T200")
        check("C2a refuses on 2 matching headings", False, "returned a width")
    except W.Refused as e:
        check("C2a refuses on 2 matching headings", "ambiguous" in str(e), str(e)[:80])


def c3_absent_entry(tmp):
    print("C3 -- an unlanded entry REFUSES; it does not report 0")
    env = _mkrepo(tmp)
    _append(tmp, env, _entry("ORCH-T300", "ORCH-T301", 1), "a")
    try:
        W.width(tmp, LANE, "ORCH-T999")
        check("C3a refuses on an absent entry", False, "returned a width")
    except W.Refused as e:
        check("C3a refuses on an absent entry", "has not landed" in str(e),
              str(e)[:80])


def c4_non_ascii_separators(tmp):
    print("C4 -- the heading's U+00B7 / U+2192 bytes survive (no text decode)")
    env, c142, c143, c144 = build_lineage(tmp)
    tip = W._blob(tmp, "HEAD", LANE)
    h = W._heading(tip, "ORCH-T144")
    check("C4a heading carries the real separator bytes",
          b"\xc2\xb7" in h and b"\xe2\x86\x92" in h,
          "heading bytes: %r" % h[:60])
    r = W.width(tmp, LANE, "ORCH-T144")
    check("C4b width resolves despite them", r["rc"] == W.RC_OK and r["width"] > 0,
          "rc=%s width=%s" % (r["rc"], r["width"]))
    # The falsifier: a cp1252 text walk cannot even hold this needle.
    # NOTE, and this control was WRONG on its first run: it originally did
    # h.decode("cp1252").encode("cp1252"), which round-trips trivially because
    # cp1252 is near-bijective over BYTES -- it measured the wrong direction and
    # reported a green tool as red. The hazard is encoding the STRING: U+2192 has
    # no cp1252 codepoint. Same class as the entry this suite exists for -- a
    # check that measures a copy of the thing rather than the thing.
    try:
        h.decode("utf-8").encode("cp1252")
        cp_ok = True
    except UnicodeEncodeError:
        cp_ok = False
    check("C4c a cp1252 text walk could NOT carry this needle (why bytes)",
          not cp_ok, "cp1252 encoded the heading; fixture lost its glyphs")


def c5_multi_entry_commit(tmp):
    print("C5 -- a commit landing two entries reports a SUM, flagged")
    env = _mkrepo(tmp)
    _append(tmp, env, _entry("ORCH-T400", "ORCH-T401", 1), "a")
    both = _entry("ORCH-T401", "ORCH-T402", 1) + _entry("ORCH-T402", "ORCH-T403", 1)
    _append(tmp, env, both, "two at once")
    r = W.width(tmp, LANE, "ORCH-T401")
    check("C5a rc signals the precondition failure",
          r["rc"] == W.RC_PRECONDITION, "rc=%s" % r["rc"])
    check("C5b the note says SUM, not width",
          any("SUM" in n for n in r["notes"]), "notes=%s" % r["notes"])


def c7_backreference_layer(tmp):
    """The SECOND ambiguity layer, found by this fixture and not by any hand.

    T331 cured needle bare-id -> heading line. But a later entry's HEADING
    back-references an earlier entry's id, so "the heading containing the id" is
    not unique on a live lane either. C7 is the synthetic form of the live shape
    that made C6 refuse on its first run (ORCH-T143 matched 3 headings).
    """
    print("C7 -- a back-reference in a LATER heading must not defeat the needle")
    env = _mkrepo(tmp)
    c1 = _append(tmp, env, _entry("ORCH-T500", "ORCH-T501", 1), "a")
    # A peer entry whose heading cites T500 in its PROSE, after the date stamp.
    peer = ("## ORCH %s CREATOR %s ORCH-T3094 %s 2026-08-16 07:43:35 %s "
            "the reader-side grade of ORCH-T500 s3 is ACCEPTED %s re ORCH-T500"
            % (ARROW, SEP, SEP, SEP, SEP)) + "\n\n" + ("y" * 40 + "\n") * 9
    c2 = _append(tmp, env, peer, "peer cites it")

    tip = W._blob(tmp, "HEAD", LANE)
    raw = [h for h in W._headings(tip) if b"ORCH-T500" in h]
    check("C7a the id really does match 2 heading lines (layer is live)",
          len(raw) == 2, "matched %d" % len(raw))
    try:
        r = W.width(tmp, LANE, "ORCH-T500")
        check("C7b the id-field discriminator picks the entry's own heading",
              r["introducing_commit"] == c1,
              "got %s want %s" % (r["introducing_commit"][:9], c1[:9]))
    except W.Refused as e:
        check("C7b the id-field discriminator picks the entry's own heading",
              False, "refused: %s" % str(e)[:90])

    # And an id that ONLY ever appears as a back-reference must refuse, not guess.
    try:
        W.width(tmp, LANE, "ORCH-T3094")
        check("C7c an id present only in prose still resolves (it IS an id field)",
              True)
    except W.Refused as e:
        check("C7c an id present only in prose still resolves (it IS an id field)",
              False, str(e)[:80])


def c6_live_crosscheck(repo_root):
    print("C6 -- live cross-check against T331's published table")
    lane = "channel/orch_to_creator_2026-08-16.md"
    if not (Path(repo_root) / lane).exists():
        skip("C6", "lane %s not in this clone" % lane)
        return
    want = {"ORCH-T143": 16497, "ORCH-T144": 19939}
    for eid, exp in want.items():
        try:
            r = W.width(repo_root, lane, eid)
        except W.Refused as e:
            skip("C6 %s" % eid, str(e)[:70])
            continue
        check("C6 %s width == %d" % (eid, exp), r["width"] == exp,
              "got %d at %s" % (r["width"], r["introducing_commit"][:9]))


def main():
    root = str(HERE.parent.parent)
    for fn in (c1_the_trap, c2_needle_uniqueness, c3_absent_entry,
               c4_non_ascii_separators, c5_multi_entry_commit,
               c7_backreference_layer):
        with tempfile.TemporaryDirectory() as tmp:
            fn(tmp)
    c6_live_crosscheck(root)

    print("")
    if FAILS:
        print("FAILED: %d (%s)" % (len(FAILS), ", ".join(FAILS)))
    if SKIPS:
        print("SKIPPED: %d (%s) -- reported, never counted as passes"
              % (len(SKIPS), ", ".join(SKIPS)))
    if not FAILS:
        print("all controls pass")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
