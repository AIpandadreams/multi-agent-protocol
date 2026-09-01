"""render_head's lane-tail STAMP delta — the first tests this module has ever had.

Subject: `tools/render_head.py`, the uncommitted delta that adds `import hashlib`,
an OPTIONAL `(?: tails=([0-9a-f]{16}))?` group to `FOOTER_RE`, and a
`tails=<sha256[:16]>` token emitted into the Next Step footer over the exact
`Lane tails at render: …` line the renderer wrote.

Design of record for the delta: the emitter half lives in this file's subject;
the VERIFIER half is prose, not code — `plugins/agent-protocol/commands/wake.md`
step 6c ("LANE-TAIL STAMP EXEMPTION"). Nothing in this repo executes the
verifier, so the legs that exercise it (`stamp_verdict` below) implement wake.md's
stated rule and say so, rather than pretending the subject does the matching.
The contract is wake.md's; this file only measures against it.

⛔ WHAT THESE TESTS ARE FOR. The exemption's whole security argument is that it
is derived from the footer PAYLOAD (a digest that only a real render can make
true), never from a line's SHAPE. Three things have to hold for that to be worth
anything, and each has a leg here:
  * a pre-delta footer still parses (else every already-rendered head in every
    workspace flips from FRESH to CORRUPT the moment this ships),
  * a token-bearing footer parses and the digest lands in its own group,
  * a MALFORMED token fails CLOSED rather than degrading to "no stamp".

The subject is loaded by path — `tools/` is not a package. `RENDER_HEAD_PATH`
overrides the path so a mutation run can point the suite at a MUTATED COPY in a
temp dir; the real file is never written to. That seam exists because the
subject is uncommitted in a tree other sessions are live in, and in-place
mutation of it is not a risk worth taking to verify a test.

⚙ HARNESS. This module is stdlib `unittest` — no pytest, no third-party import
of any kind — because CI runs `python -m unittest discover -s tests -v`, which
collects ONLY `unittest.TestCase` subclasses. A module of bare `def test_*`
functions collects zero tests there and the build goes green having executed
none of them. Every leg below is therefore a method on a TestCase.
"""
import contextlib
import hashlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RENDER_HEAD = Path(os.environ.get("RENDER_HEAD_PATH")
                   or (REPO / "tools" / "render_head.py"))

NOW = "2026-08-30T10:00:00-04:00"
NOW2 = "2026-08-30T18:30:00-04:00"     # a DIFFERENT stamp, for scoped idempotence
TAIL_PREFIX = "Lane tails at render: "


# ------------------------------------------------------------------- loading -
_SUBJECT = {}


def load_subject():
    """Load the subject by path, once per process.

    Stands in for the module-scoped `mod` fixture: every test gets the same
    module object, and the load is LAZY so that a missing/broken subject errors
    the individual tests instead of killing collection for the whole module —
    a module that fails to import contributes zero collected tests, which is
    the exact false-green this suite exists to avoid.
    """
    if "mod" not in _SUBJECT:
        spec = importlib.util.spec_from_file_location("render_head_under_test",
                                                      RENDER_HEAD)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _SUBJECT["mod"] = m
    return _SUBJECT["mod"]


def run_cli(mod, *argv):
    """Drive the subject through its real entry point so the EXIT CODE under
    test is the contract's exit code, not a function return value."""
    old = sys.argv
    sys.argv = ["render_head.py", *argv]
    try:
        return mod.main()
    finally:
        sys.argv = old


class _Captured:
    """The `.out` / `.err` shape `capsys.readouterr()` returned."""

    def __init__(self, out, err):
        self.out = out
        self.err = err


def run_cli_captured(mod, *argv):
    """`run_cli` with stdout/stderr captured — the `capsys` replacement.

    Returns `(rc, captured)`. Because each call captures afresh, a call whose
    output the original discarded with a bare `capsys.readouterr()` simply
    ignores the returned `captured`; there is no residue to drain.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = run_cli(mod, *argv)
    return rc, _Captured(out.getvalue(), err.getvalue())


# ------------------------------------------------------------------ fixtures -
PLAN = """\
schema_version: 1
project_id: TESTPLAN
state: open
owner_seat: owner
steps:
  - id: S1
    owner: owner
    status: pending
    desc: do the thing
"""

LANE = """\
# orch -> owner

## SAMPLE-4001 - first entry

body of the first entry

## SAMPLE-4002 - second entry

body of the second entry
"""


def make_ws(tmp_path):
    """The minimum workspace `render_head.py` will actually run over.

    Derived by reading the subject, not guessed:
      * `require_adopted()` REFUSES (rc 2) a workspace with no `plans/`;
      * `derive_sources()` REFUSES (rc 2) when neither `plans/*.plan.yaml` nor
        `channel/*.md` yields a source;
      * `lane_tails()` scopes to families whose `<sender>_to_<recipient>` name
        resolves to the bound seat, so the lane must be addressed `_to_owner`;
      * entry ids come from `find_sections()` H2 titles via `match_entry_id`;
      * `memory/owner/MEMORY.md` need NOT pre-exist — `render()` creates the
        parent and seeds `# owner memory` — so it is deliberately not created
        here, which also exercises the first-render (no prior sections) path.
    """
    ws = tmp_path / "ws"
    (ws / "plans").mkdir(parents=True)
    (ws / "channel").mkdir(parents=True)
    (ws / "plans" / "test.plan.yaml").write_bytes(PLAN.encode("utf-8"))
    (ws / "channel" / "orch_to_owner_2026-08-29.md").write_bytes(LANE.encode("utf-8"))
    return ws


def head_path(ws):
    return ws / "memory" / "owner" / "MEMORY.md"


def head_text(ws):
    return head_path(ws).read_bytes().decode("utf-8")


# ------------------------------------------------- wake.md 6c verifier (prose) -
def physical_lines(text):
    """Physical lines "stripped of its line terminator only — leading whitespace
    is part of the measured text" (wake.md 6c, verbatim constraint)."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [ln[:-1] if ln.endswith("\r") else ln for ln in lines]


def live_head_lines(mod, text):
    """The lines of the LIVE head body — every level-2 section span, using the
    SUBJECT'S OWN `find_sections()` rather than a second heading grammar
    invented here. `####` demoted blocks do not open a section, so their bytes
    (which `--adopt` preserves verbatim, tail line included) fall outside every
    span. That scoping is exactly what leg 7 measures."""
    out = []
    for sec in mod.find_sections(text):
        out.extend(physical_lines(text[sec.start:sec.end]))
    return out


def digest16(line):
    return hashlib.sha256(line.encode("utf-8")).hexdigest()[:16]


def stamp_verdict(lines, token):
    """wake.md 6c step 3, implemented over a caller-chosen line set.

    Returns ("exempt", line) / ("stale-render", None) / ("ambiguous", count).
    This is the VERIFIER half, which does not ship as code in this repo — it is
    reproduced here so the emitter's output can be graded against the rule it
    was built for, and it is deliberately trivial so that what it measures is
    the EMITTED BYTES, never a value this file hardcodes.
    """
    hits = [ln for ln in lines if digest16(ln) == token]
    if len(hits) == 1:
        return "exempt", hits[0]
    if not hits:
        return "stale-render", None
    return "ambiguous", len(hits)


# ------------------------------------------------------------- base TestCases -
class RenderHeadTestCase(unittest.TestCase):
    """Binds the subject module to `self.mod` for every leg."""

    def setUp(self):
        self.mod = load_subject()


class WorkspaceTestCase(RenderHeadTestCase):
    """Adds the `tmp_path` fixture: a per-test temporary directory, torn down
    by `addCleanup`. It is a `pathlib.Path`, exactly as pytest's `tmp_path` is,
    so every `/`-join below works unchanged."""

    def setUp(self):
        super().setUp()
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.tmp_path = Path(td.name)


# ==================================================================== LEG 1 ===
# ==================================================================== LEG 2 ===
# ==================================================================== LEG 3 ===
# ⭐ THE ANSWER, MEASURED, BECAUSE A DOWNSTREAM CONSUMER DEPENDS ON IT:
#
#   A malformed `tails=` value makes the WHOLE FOOTER UNPARSEABLE. It does NOT
#   degrade to "the optional group simply did not match while the rest still
#   parses".
#
# Why: `FOOTER_RE` is applied with `.fullmatch`, and the optional group sits
# between `sources=(\\S+?)` and the literal ` -->`. `(\\S+?)` cannot cross the
# space that precedes ` tails=`, so once a ` tails=…` run is present and the
# optional group refuses it (wrong length, wrong case, non-hex, empty), there is
# no alternative parse that reaches ` -->`. fullmatch returns None.
#
# The consequence — and this is the part a consumer must know — is that a broken
# stamp is NOT read as "this head has no stamp". `FOOTER_ATTEMPT_RE` still
# recognizes the line as a footer ATTEMPT, so `section_footer()` sees
# attempts=1 / clean=0 and RAISES RC_REFUSED ("ambiguous/tampered stamp"). So:
#
#     no footer-shaped line at all      -> None            ("no stamp")
#     footer-shaped, malformed tails    -> RC_REFUSED      ("broken stamp")
#
# Those are DIFFERENT outcomes, and the fail-closed one is the malformed case.
# That is the correct behaviour for a payload-derived exemption: a stamp that
# cannot be read must never be treated as a stamp that was never written.
MALFORMED_TAILS = {
    "15 hex (one short)":  "0123456789abcde",
    "17 hex (one long)":   "0123456789abcdef0",
    "non-hex":             "zzzzzzzzzzzzzzzz",
    "uppercase hex":       "0123456789ABCDEF",
    "empty value":         "",
    "16 chars, one bad":   "0123456789abcdeg",
}


class TestFooterGrammar(RenderHeadTestCase):
    """Legs 1, 2 and 3 at the REGEX / section-reader reading: what the footer
    grammar accepts, what it puts in which group, and what it does with a
    broken stamp."""

    # ================================================================ LEG 1 ===
    def test_leg1_footer_re_parses_the_PRE_DELTA_footer_form(self):
        """COMPATIBILITY GUARANTEE. A footer written before this delta carries no
        `tails=` token. If the widened `FOOTER_RE` stopped fullmatching it, every
        head already rendered in every workspace would read as a CORRUPT/tampered
        stamp (`section_footer` raises RC_REFUSED on an attempt that is not a clean
        fullmatch) — a fleet-wide refusal caused by shipping the grammar."""
        mod = self.mod
        old = ("<!-- render_head v1 rendered_at=2026-08-01T10:00:00-04:00 "
               "sources=plans/a.plan.yaml@111,channel/b.md@222 -->")
        m = mod.FOOTER_RE.fullmatch(old)
        self.assertIsNotNone(
            m, "pre-delta footer no longer parses — every rendered head corrupts")
        # The groups the pre-delta consumers read, unchanged and in the same order:
        # check() reads group(2) as the sources token, render()'s scoped-idempotence
        # comparison re-stamps from group(1).
        self.assertEqual(m.group(1), "2026-08-01T10:00:00-04:00")
        self.assertEqual(m.group(2), "plans/a.plan.yaml@111,channel/b.md@222")
        # ABSENT, not empty string — "no stamp" must stay distinguishable from
        # "empty stamp" for the wake's fail-closed clause 2.
        self.assertIsNone(m.group(3))

    # ================================================================ LEG 2 ===
    def test_leg2_footer_re_parses_the_NEW_form_and_captures_the_digest(self):
        """A token-bearing footer parses, and the digest lands in group 3 — its own
        group, so no consumer of group(1)/group(2) can pick it up by accident."""
        mod = self.mod
        tok = digest16("Lane tails at render: orch_to_owner SAMPLE-4002.")
        new = ("<!-- render_head v1 rendered_at=2026-08-01T10:00:00-04:00 "
               f"sources=plans/a.plan.yaml@111,channel/b.md@222 tails={tok} -->")
        m = mod.FOOTER_RE.fullmatch(new)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "2026-08-01T10:00:00-04:00")
        # The sources token must NOT absorb the tails token: `(\\S+?)` is non-greedy
        # and cannot cross the separating space, but that is a property worth
        # pinning rather than assuming — a greedy variant would silently swallow it
        # and check() would then try to split `tails=…` as a `<rel>@<epoch>` pair.
        self.assertEqual(m.group(2), "plans/a.plan.yaml@111,channel/b.md@222")
        self.assertEqual(m.group(3), tok)

    # ================================================================ LEG 3 ===
    def test_leg3_malformed_tails_makes_the_WHOLE_footer_unparseable(self):
        """Every malformed-token case, one subTest per case, in the same sorted
        order the parametrized original ran them in."""
        mod = self.mod
        for label, bad in sorted(MALFORMED_TAILS.items()):
            with self.subTest(label=label, bad=bad):
                line = ("<!-- render_head v1 rendered_at=2026-08-01T10:00:00-04:00 "
                        f"sources=plans/a.plan.yaml@111 tails={bad} -->")
                self.assertIsNone(mod.FOOTER_RE.fullmatch(line), (
                    f"{label}: a malformed tails value was accepted by the "
                    f"footer grammar"))
                # ... and it is still recognized as an ATTEMPT, which is what turns
                # "unparseable" into "refused" rather than "absent".
                self.assertIsNotNone(mod.FOOTER_ATTEMPT_RE.match(line), (
                    f"{label}: a broken stamp stopped registering as a footer "
                    f"attempt — it would silently read as an UNRENDERED head "
                    f"instead of a refusal"))

    def test_leg3b_broken_stamp_fails_CLOSED_at_the_section_reader(self):
        """The behaviour a consumer actually meets: RC_REFUSED, not None."""
        mod = self.mod
        for label, bad in sorted(MALFORMED_TAILS.items()):
            with self.subTest(label=label, bad=bad):
                text = ("# owner memory\n\n## Next Step\nDo the thing.\n"
                        "<!-- render_head v1 rendered_at=2026-08-01T10:00:00-04:00 "
                        f"sources=plans/a.plan.yaml@111 tails={bad} -->\n")
                with self.assertRaises(mod.SystemExit_) as exc:
                    mod.scoped_footer(text)
                self.assertEqual(exc.exception.code, mod.RC_REFUSED, label)
                self.assertIn("ambiguous/tampered stamp", exc.exception.msg)

    def test_leg3c_control_a_head_with_NO_footer_is_absent_not_refused(self):
        """The discriminating control for leg 3b. Without it, 3b only proves
        `scoped_footer` can raise — not that it raises BECAUSE the stamp is broken
        rather than because it is missing. Same section shape, no footer-shaped
        line: the outcome must be `None` ("no stamp"), never a refusal."""
        mod = self.mod
        text = ("# owner memory\n\n## Next Step\nDo the thing.\n"
                "<!-- some other html comment -->\n")
        m, sec = mod.scoped_footer(text)
        self.assertIsNone(m)
        self.assertIsNotNone(sec)


class TestRenderedHeadGrading(WorkspaceTestCase):
    """Legs 1b and 2b — the same compatibility question at the DEPLOYMENT
    reading: how a head on disk grades under `--check`."""

    # =============================================================== LEG 1b ===
    def test_leg1b_pre_delta_head_still_grades_F8_CURRENT(self):
        """The same guarantee at the DEPLOYMENT reading, not just the regex reading:
        a head whose footer has had its `tails=` token removed (i.e. a head rendered
        before this delta) must still grade FRESH under `--check`, not corrupt."""
        mod = self.mod
        ws = make_ws(self.tmp_path)
        rc, _ = run_cli_captured(mod, str(ws), "owner", "--now", NOW)
        self.assertEqual(rc, mod.RC_OK)

        text = head_text(ws)
        m, _sec = mod.scoped_footer(text)
        self.assertIsNotNone(
            m.group(3), "precondition: the fresh render must carry a token")
        pre_delta = text.replace(f" tails={m.group(3)} -->", " -->")
        self.assertNotEqual(pre_delta, text)
        head_path(ws).write_bytes(pre_delta.encode("utf-8"))

        rc, cap = run_cli_captured(mod, str(ws), "owner", "--check", "--now", NOW)
        out = cap.out
        self.assertEqual(rc, mod.RC_OK,
                         f"pre-delta head no longer grades fresh: {out!r}")
        self.assertIn("F8 CURRENT", out)

    # =============================================================== LEG 2b ===
    def test_leg2b_new_form_head_grades_F8_CURRENT(self):
        """Emitter and verifier are one grammar: the footer this renderer WRITES
        must be readable by the check leg it SHIPS WITH."""
        mod = self.mod
        ws = make_ws(self.tmp_path)
        rc, _ = run_cli_captured(mod, str(ws), "owner", "--now", NOW)
        self.assertEqual(rc, mod.RC_OK)
        rc, cap = run_cli_captured(mod, str(ws), "owner", "--check", "--now", NOW)
        out = cap.out
        self.assertEqual(rc, mod.RC_OK, out)
        self.assertIn("F8 CURRENT", out)


class TestEndToEndStamp(WorkspaceTestCase):
    """Legs 4 and 5 — the emitted bytes, and what a second render does to them."""

    # ================================================================ LEG 4 ===
    def test_leg4_end_to_end_render_stamps_the_line_it_emitted(self):
        """The property, end to end and FROM THE EMITTED BYTES: the footer's
        `tails=` digest is the SHA-256/16 of a line that is physically present in
        the head, and of EXACTLY ONE such line. Nothing here is hardcoded — the
        expected digest is recomputed from the file the renderer wrote."""
        mod = self.mod
        ws = make_ws(self.tmp_path)
        rc, cap = run_cli_captured(mod, str(ws), "owner", "--now", NOW)
        out = cap.out
        self.assertEqual(rc, mod.RC_OK, out)
        self.assertIn("RENDERED", out)

        text = head_text(ws)
        m, _sec = mod.scoped_footer(text)
        self.assertIsNotNone(m, "the rendered head carries no scoped footer")
        token = m.group(3)
        self.assertIsNotNone(token, "the render emitted no tails token")
        self.assertEqual(len(token), 16)

        verdict, line = stamp_verdict(live_head_lines(mod, text), token)
        self.assertEqual(verdict, "exempt", (
            f"the emitted footer's digest does not resolve to exactly one "
            f"line: {verdict}"))
        # The stamped line is the TAIL line, not some other line that happened to
        # collide — the grammar the emitter's own assert guards.
        self.assertTrue(line.startswith(TAIL_PREFIX),
                        f"stamp bound a non-tail line: {line!r}")
        # And the digest really is of THOSE bytes, recomputed independently.
        self.assertEqual(digest16(line), token)
        # The lane the fixture actually carries, so a renderer that stamped an empty
        # or wrong inventory could not pass this leg by stamping *something*.
        self.assertIn("SAMPLE-4002", line)

    # ================================================================ LEG 5 ===
    def test_leg5_re_render_is_idempotent_and_does_not_duplicate_the_footer(self):
        """Re-rendering an already-rendered head must not write, must not append a
        second footer, and must not append a second tail line. Driven with a
        DIFFERENT `--now` so the scoped-idempotence rule (only the generated
        footer's `rendered_at` is neutralized) is what is being exercised — a
        same-`--now` re-run would pass even if the scoping were broken."""
        mod = self.mod
        ws = make_ws(self.tmp_path)
        rc, _ = run_cli_captured(mod, str(ws), "owner", "--now", NOW)
        self.assertEqual(rc, mod.RC_OK)
        first = head_path(ws).read_bytes()

        rc, cap = run_cli_captured(mod, str(ws), "owner", "--now", NOW2)
        out = cap.out
        self.assertEqual(rc, mod.RC_OK, out)
        self.assertIn("CURRENT", out)
        self.assertNotIn("RENDERED", out)
        self.assertEqual(head_path(ws).read_bytes(), first,
                         "re-render rewrote a current head")

        text = head_text(ws)
        lines = physical_lines(text)
        self.assertEqual(
            sum(1 for ln in lines if mod.FOOTER_ATTEMPT_RE.match(ln.strip())), 1)
        self.assertEqual(sum(1 for ln in lines if ln.startswith(TAIL_PREFIX)), 1)
        self.assertEqual(sum(1 for ln in lines if ln.strip() == "## Next Step"), 1)
        # and the stamp still resolves after the no-write pass
        m, _sec = mod.scoped_footer(text)
        self.assertEqual(
            stamp_verdict(live_head_lines(mod, text), m.group(3))[0], "exempt")


class TestStampVerdictTrichotomy(WorkspaceTestCase):
    """Legs 6 and 6b — the other two arms of the verifier's trichotomy:
    a duplicated line goes AMBIGUOUS, an edited line goes STALE-RENDER."""

    # ================================================================ LEG 6 ===
    def test_leg6_duplicated_tail_line_is_detectable_as_AMBIGUOUS(self):
        """The fail-closed case the design names. Two byte-identical tail lines hash
        identically, so an appended lookalike cannot BECOME the stamp — it makes the
        stamp ambiguous, and the head demotes. Constructed by appending a verbatim
        copy of the emitted tail line into the live head body."""
        mod = self.mod
        ws = make_ws(self.tmp_path)
        rc, _ = run_cli_captured(mod, str(ws), "owner", "--now", NOW)
        self.assertEqual(rc, mod.RC_OK)

        text = head_text(ws)
        m, _sec = mod.scoped_footer(text)
        token = m.group(3)
        tail = next(ln for ln in physical_lines(text) if ln.startswith(TAIL_PREFIX))
        self.assertEqual(stamp_verdict(live_head_lines(mod, text), token)[0],
                         "exempt")

        # Append the lookalike INSIDE the live Next Step section (after the tail
        # line), which is where an editor would put it.
        forged = text.replace(tail + "\n", tail + "\n" + tail + "\n", 1)
        self.assertNotEqual(forged, text)
        head_path(ws).write_bytes(forged.encode("utf-8"))

        verdict, count = stamp_verdict(live_head_lines(mod, head_text(ws)), token)
        self.assertEqual(verdict, "ambiguous",
                         "a duplicated tail line was not detected")
        self.assertEqual(count, 2)

    # =============================================================== LEG 6b ===
    def test_leg6b_edited_tail_line_yields_ZERO_matches_not_a_silent_exemption(self):
        """The third arm of the verifier's trichotomy, and the one that keeps the
        exemption honest: edit the stamped line and the digest matches NOTHING, so
        no line is exempt. Without this leg, leg 6 only shows that two matches are
        countable — not that a single EDITED line loses its exemption instead of
        keeping it."""
        mod = self.mod
        ws = make_ws(self.tmp_path)
        rc, _ = run_cli_captured(mod, str(ws), "owner", "--now", NOW)
        self.assertEqual(rc, mod.RC_OK)

        text = head_text(ws)
        token = mod.scoped_footer(text)[0].group(3)
        tail = next(ln for ln in physical_lines(text) if ln.startswith(TAIL_PREFIX))
        edited = text.replace(
            tail + "\n", tail.replace("SAMPLE-4002", "SAMPLE-9999") + "\n", 1)
        self.assertNotEqual(edited, text)

        verdict, payload = stamp_verdict(live_head_lines(mod, edited), token)
        self.assertEqual(verdict, "stale-render")
        self.assertIsNone(payload)


class TestAdoptScoping(WorkspaceTestCase):
    """Leg 7 — the measured hazard: `--adopt` leaves a byte-identical duplicate
    of the tail line in the FILE, so the verifier's line set has to be scoped."""

    # ================================================================ LEG 7 ===
    def test_leg7_adopt_leaves_a_second_byte_identical_tail_line_in_the_file(self):
        """⚠ MEASURED HAZARD, pinned rather than accommodated.

        `--adopt` demotes the existing sections to `#### [superseded …]` with their
        bodies preserved BYTE-INTACT, then appends a fresh rendered pair. When the
        ledger has not moved, the fresh tail line is byte-identical to the demoted
        one — so the FILE now contains two lines with the same digest.

        A verifier that hashes every physical line of the FILE therefore reports
        AMBIGUOUS on a head produced by a sanctioned operation. A verifier that
        scopes to the LIVE head body (level-2 sections; `####` blocks excluded, per
        the subject's own `find_sections`) reports exactly one.

        Both numbers are asserted here, so the scoping is a tested requirement and
        not an assumption. wake.md's footer-recognition parenthetical says the live
        body sits "above any demoted `####` block"; after `--adopt` the demoted
        block is ABOVE the live pair, so a verifier that implements that
        parenthetical positionally — rather than structurally — lands on the wrong
        span. Reported to the caller, not worked around here.
        """
        mod = self.mod
        ws = make_ws(self.tmp_path)
        rc, _ = run_cli_captured(mod, str(ws), "owner", "--now", NOW)
        self.assertEqual(rc, mod.RC_OK)
        before = head_text(ws)
        tail = next(ln for ln in physical_lines(before)
                    if ln.startswith(TAIL_PREFIX))

        rc, _ = run_cli_captured(mod, str(ws), "owner", "--now", NOW2, "--adopt")
        self.assertEqual(rc, mod.RC_OK)
        after = head_text(ws)

        self.assertIn("#### [superseded", after,
                      "precondition: --adopt must demote in place")
        token = mod.scoped_footer(after)[0].group(3)

        whole_file = stamp_verdict(physical_lines(after), token)
        self.assertTrue(whole_file[0] == "ambiguous" and whole_file[1] == 2, (
            "expected the demoted copy of the tail line to collide with the fresh "
            f"one; got {whole_file}"))

        live = stamp_verdict(live_head_lines(mod, after), token)
        self.assertEqual(live[0], "exempt")
        self.assertTrue(live[1].startswith(TAIL_PREFIX))
        self.assertEqual(live[1], tail)


if __name__ == "__main__":
    unittest.main()
