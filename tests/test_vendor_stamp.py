"""The vendored-checker stamp: derived, reconcilable, and single-sourced.

The defect these cover, measured 2026-07-28: `new_project.py` wrote a stamped
copy of `conformance_check.py` into every workspace with the protocol version
HARDCODED in the header, and nothing ever reconciled the copy afterwards. All
four stamped workspaces carried checkers that would have blocked on a v2.9
workspace, and three carried byte-identical code under three DIFFERENT header
stamps -- so the stamp did not even indicate which code was present.

Each test below names the property it holds, and the drift tests REPLAY the
real pre-fix header form rather than a convenient stand-in: a detector that
has never seen the defect it exists for has not been shown to catch it.
"""
import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name, rel_path):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rv = _load("reconcile_vendored", "tools/reconcile_vendored.py")

# The header `new_project.py` emitted before this unit, verbatim in shape.
LEGACY_HEADER = (
    "# STAMPED COPY — multi-agent-protocol PROTOCOL v2.9 @ 2026-07-20. "
    "In-workspace HYGIENE SELF-CHECK (workspace-owned code); for a trust "
    "decision run the protocol checkout's copy against this workspace.\n"
)

CANON = (
    '#!/usr/bin/env python3\n'
    '"""a checker"""\n'
    'SUPPORTED_VERSIONS = ("v2.5", "v2.6", "v2.9")\n'
    'def main():\n'
    '    return 0\n'
)

OLDER = CANON.replace('"v2.5", "v2.6", "v2.9"', '"v2.5", "v2.6"')


class VendorStampDerivation(unittest.TestCase):
    """Everything in the stamp except the date is read out of the content."""

    def test_supports_through_follows_the_body_not_a_literal(self):
        new = rv.make_stamp(CANON, "2026-07-28")
        old = rv.make_stamp(OLDER, "2026-07-28")
        self.assertIn("supports-through: v2.9", new)
        # Control: the SAME stamper on a different body yields a different
        # ceiling. Without this the assertion above would also pass on a
        # hardcoded "v2.9", which is the very defect being cured.
        self.assertIn("supports-through: v2.6", old)

    def test_recorded_sha_is_over_the_stamp_free_body(self):
        text = rv.vendor_text(CANON, "2026-07-28")
        self.assertEqual(rv.body_of(text), CANON)
        self.assertIn(rv.sha_of(CANON), text)

    def test_stamp_sits_below_the_shebang(self):
        text = rv.vendor_text(CANON, "2026-07-28")
        self.assertTrue(text.startswith("#!/usr/bin/env python3\n"))
        self.assertTrue(text.split("\n")[1].startswith(rv.BEGIN))

    def test_body_of_strips_the_LEGACY_header_too(self):
        """The motivating defect, replayed.

        Two workspaces with byte-identical CODE, stamped on different days,
        must report the SAME body. Before this, the legacy header's own date
        was hashed as if it were code.
        """
        day_one = LEGACY_HEADER.replace("2026-07-20", "2026-07-20") + CANON
        day_two = LEGACY_HEADER.replace("2026-07-20", "2026-07-25") + CANON
        self.assertNotEqual(day_one, day_two)          # control: differ
        self.assertEqual(rv.body_of(day_one), rv.body_of(day_two))
        self.assertEqual(rv.body_of(day_one), CANON)

    def test_unterminated_stamp_raises_rather_than_silently_truncating(self):
        broken = rv.BEGIN + "\n# half a stamp\n" + CANON
        with self.assertRaises(ValueError):
            rv.body_of(broken)


class InspectStatuses(unittest.TestCase):
    """Every branch of `inspect`, each proved able to fire."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        (self.ws / "tools").mkdir()
        self.target = self.ws / "tools" / "conformance_check.py"
        self.addCleanup(self._tmp.cleanup)

    def test_missing_copy(self):
        self.assertEqual(rv.inspect(self.target, CANON)[0], "MISSING")

    def test_freshly_vendored_is_OK(self):
        self.target.write_text(rv.vendor_text(CANON, "2026-07-28"),
                               encoding="utf-8")
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "OK", detail)

    def test_stale_body_is_DRIFT_and_names_its_ceiling(self):
        """A real stale workspace: older code under a legacy header."""
        self.target.write_text(LEGACY_HEADER + OLDER, encoding="utf-8")
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "DRIFT")
        self.assertIn("supports only through v2.6", detail)

    def test_hand_edited_stamp_is_caught(self):
        text = rv.vendor_text(CANON, "2026-07-28")
        text = text.replace(rv.sha_of(CANON), "0" * 64)
        self.target.write_text(text, encoding="utf-8")
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "DRIFT")
        self.assertIn("stamp edited", detail)

    def test_current_body_with_no_stamp_is_DRIFT(self):
        self.target.write_text(CANON, encoding="utf-8")
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "DRIFT")
        self.assertIn("NO stamp", detail)

    def test_line_endings_alone_are_NOT_drift(self):
        """EOL-insensitivity is deliberate, so it is stated and tested.

        The sha is taken over decoded, stamp-free text, so a workspace whose
        copy differs from canonical only in line endings is reconciled, not
        flagged. Found by measuring the bytes this tool's own --fix writes on
        Windows and noticing the checker could not see the difference: the
        behaviour is right for a file checked out on several platforms, but
        it was undescribed and untested, which is how a property becomes an
        accident.
        """
        crlf = rv.vendor_text(CANON, "2026-07-28").replace("\n", "\r\n")
        self.target.write_bytes(crlf.encode("utf-8"))
        self.assertIn(b"\r\n", self.target.read_bytes())   # control
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "OK", detail)

    def test_a_real_code_change_is_still_DRIFT_under_CRLF(self):
        """Control for the test above: EOL blindness must not hide content."""
        crlf = rv.vendor_text(OLDER, "2026-07-28").replace("\n", "\r\n")
        self.target.write_bytes(crlf.encode("utf-8"))
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "DRIFT")
        self.assertIn("supports only through v2.6", detail)


class DivergedIsNotDrift(unittest.TestCase):
    """A copy carrying local code is not a copy that fell behind.

    Both were "DRIFT" before this, and `--fix` rewrote both. The direction
    tests matter as much as the firing test: a detector that calls every
    non-matching copy DIVERGED would pass the first test below and destroy the
    distinction, so the stale-copy control sits beside it.
    """

    ADDED = "\n\nLOCAL_ONLY_HELPER = 1\n"

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        (self.ws / "tools").mkdir()
        self.target = self.ws / "tools" / "conformance_check.py"
        self.addCleanup(self._tmp.cleanup)

    def test_a_copy_defining_a_name_the_canonical_lacks_is_DIVERGED(self):
        self.target.write_text(rv.vendor_text(CANON, "2026-07-28") + self.ADDED,
                               encoding="utf-8")
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "DIVERGED", detail)
        self.assertIn("LOCAL_ONLY_HELPER", detail)

    def test_the_control_a_copy_that_is_merely_OLD_is_DRIFT_not_DIVERGED(self):
        """The other direction, and the one that makes the status mean anything.

        A stale copy defines a SUBSET of the canonical's names. If staleness
        read as divergence, `--fix` would refuse every workspace it exists to
        repair.
        """
        self.target.write_text(LEGACY_HEADER + OLDER, encoding="utf-8")
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "DRIFT", detail)

    def test_divergence_is_asked_of_the_AST_not_of_a_spelling(self):
        """A copy that MENTIONS a name has not defined one."""
        mention = (rv.vendor_text(CANON, "2026-07-28")
                   + "\n# see also LOCAL_ONLY_HELPER in the workspace notes\n"
                   + '"""LOCAL_ONLY_HELPER is discussed here, not defined."""\n')
        self.target.write_text(mention, encoding="utf-8")
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "DRIFT", detail)
        self.assertNotIn("LOCAL_ONLY_HELPER", detail)

    def test_a_name_bound_inside_a_function_is_not_divergence(self):
        inner = rv.vendor_text(CANON, "2026-07-28").replace(
            "    return 0\n", "    local_binding = 1\n    return local_binding\n")
        self.target.write_text(inner, encoding="utf-8")
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "DRIFT", detail)

    def test_an_unparseable_copy_is_DRIFT_and_does_not_crash(self):
        """Unparseable is a defect, but it is not evidence of local work."""
        self.target.write_text(rv.vendor_text(CANON, "2026-07-28")
                               + "\ndef (:\n", encoding="utf-8")
        status, detail = rv.inspect(self.target, CANON)
        self.assertEqual(status, "DRIFT", detail)

    def test_defined_names_reports_None_rather_than_guessing(self):
        self.assertIsNone(rv.defined_names("def (:\n"))
        self.assertIn("main", rv.defined_names(CANON))      # control


class FixRefusesDivergence(unittest.TestCase):
    """`--fix` must leave a diverged copy byte-identical, and say why.

    Driven through `main` rather than `inspect`, because the destruction this
    prevents happens in the loop, not in the classifier.
    """

    REAL = (ROOT / "tools" / "conformance_check.py").read_text(encoding="utf-8")

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        (self.ws / "tools").mkdir()
        self.target = self.ws / "tools" / "conformance_check.py"
        self.addCleanup(self._tmp.cleanup)

    def _run_fix(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = rv.main(["--fix", str(self.ws)])
        return rc, buf.getvalue()

    def test_fix_refuses_and_the_bytes_are_unchanged(self):
        text = rv.vendor_text(self.REAL, "2026-07-28") + "\nLOCAL_ONLY = 1\n"
        rv.write_vendored(self.target, text)
        before = self.target.read_bytes()

        rc, out = self._run_fix()

        self.assertEqual(self.target.read_bytes(), before,
                         "--fix overwrote a diverged copy")
        self.assertIn("DIVERGED", out)
        self.assertIn("REFUSING --fix", out)
        self.assertEqual(rc, 1, "a refusal must still exit non-zero")

    def test_the_control_fix_still_repairs_an_ordinary_DRIFT(self):
        """Without this, a `--fix` that refused everything would pass above."""
        text = rv.vendor_text(self.REAL, "2026-07-28") + "\n# a local comment\n"
        rv.write_vendored(self.target, text)
        before = self.target.read_bytes()

        rc, out = self._run_fix()

        self.assertNotEqual(self.target.read_bytes(), before,
                            "--fix did not rewrite an ordinary drifted copy")
        self.assertNotIn("REFUSING", out)
        self.assertEqual(rc, 0)
        self.assertEqual(rv.inspect(self.target, self.REAL)[0], "OK")


class WritesFaithfully(unittest.TestCase):
    """The writer must not invent line endings the source did not have.

    The checker is deliberately EOL-insensitive, so it cannot catch this --
    which is exactly why it needs its own test. Measured first-hand: a
    re-vendor through `Path.write_text` on Windows turned a LF workspace file
    into CRLF, and git reported 678 insertions and 777 deletions over a real
    change of 142 lines, in a repository shared with other sessions.
    """

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name) / "conformance_check.py"
        self.addCleanup(self._tmp.cleanup)

    def test_LF_source_is_written_as_LF(self):
        text = rv.vendor_text(CANON, "2026-07-28")
        self.assertNotIn("\r", text)                      # control: source LF
        rv.write_vendored(self.target, text)
        self.assertNotIn(b"\r", self.target.read_bytes())

    def test_CRLF_source_is_written_as_CRLF(self):
        """Faithful means faithful in both directions, not 'always LF'."""
        text = rv.vendor_text(CANON, "2026-07-28").replace("\n", "\r\n")
        rv.write_vendored(self.target, text)
        raw = self.target.read_bytes()
        self.assertIn(b"\r\n", raw)
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))


class ExitCodes(unittest.TestCase):
    """A usage error is not a failing gate, and must not read as one.

    These call argparse in-process, and argparse writes its usage text to
    stderr. Left uncaptured that text lands in the RUNNER's stream, splitting
    the case's own ``... ok`` across lines: the run still reports OK while the
    per-case stream no longer sums to ``Ran N``. A test that corrupts the
    runner's output breaks the instrument used to certify the run it belongs
    to, so the capture below is part of the test, not tidiness.
    """

    @contextlib.contextmanager
    def _usage_exit(self):
        """Assert SystemExit(2) while keeping argparse's text off the stream."""
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            with self.assertRaises(SystemExit) as cm:
                yield
        self.assertEqual(cm.exception.code, 2)
        # The message is captured, not discarded — a usage error that says
        # nothing is its own defect.
        self.assertTrue(buf.getvalue().strip(), "usage error printed nothing")

    def test_no_workspaces_is_a_usage_error_not_a_failure(self):
        with self._usage_exit():
            rv.main([])

    def test_check_and_fix_are_mutually_exclusive(self):
        with self._usage_exit():
            rv.main(["--check", "--fix", "."])


class SingleSource(unittest.TestCase):
    """The cure is that ONE implementation of the stamp exists."""

    def test_new_project_does_not_format_its_own_stamp(self):
        src = (ROOT / "tools" / "new_project.py").read_text(encoding="utf-8")
        self.assertNotIn("# STAMPED COPY", src)
        self.assertIn("_vendor_stamper", src)

    def test_new_project_emits_a_stamp_reconcile_accepts(self):
        """The writer's output must satisfy the checker, end to end."""
        np = _load("new_project", "tools/new_project.py")
        canonical = (ROOT / "tools" / "conformance_check.py").read_text(
            encoding="utf-8")
        text = np._vendor_stamper().vendor_text(canonical, "2026-07-28")

        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d)
            (ws / "tools").mkdir()
            target = ws / "tools" / "conformance_check.py"
            target.write_text(text, encoding="utf-8")
            status, detail = rv.inspect(target, canonical)
            self.assertEqual(status, "OK", detail)

    def test_the_real_checker_declares_a_ceiling_the_stamp_can_read(self):
        """Guards against the stamp degrading to 'unknown' unnoticed."""
        canonical = (ROOT / "tools" / "conformance_check.py").read_text(
            encoding="utf-8")
        through = rv.supported_through(canonical)
        self.assertIsNotNone(through)
        self.assertRegex(through, r"^v\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
