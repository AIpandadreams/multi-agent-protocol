#!/usr/bin/env python3
"""Regression tests for the public-release scrub gate.

The gate's job is to fail LOUD and EARLY on anything private in a release tree,
so the ordering (named-path guard before pattern scan), the exit codes, and the
patterns-file parsing all get committed tests. Stdlib unittest only, to match
the repo's no-extra-dependency posture:

    python -m unittest discover -s tests

NOTE: the CI scrub step scans this very file, so the fixture tokens below are
deliberately chosen NOT to match any pattern in examples/scrub_patterns.example.txt
(they use 'privname' / 'acmecorp' / '.test' rather than the example placeholders).
"""
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "release_scrub", ROOT / "tools" / "release_scrub.py")
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)


def _run(argv):
    """Invoke main() with argv, returning (exit_code, stdout, stderr)."""
    import sys
    saved = sys.argv
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["release_scrub.py"] + argv
        with redirect_stdout(out), redirect_stderr(err):
            code = rs.main()
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


class LoadPatternsTest(unittest.TestCase):
    def test_comments_and_blanks_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            pf = Path(d) / "patterns.txt"
            pf.write_text(
                "# a comment\n"
                "\n"
                "   \n"
                "   # indented comment\n"
                "privname\n"
                "acmecorp\n",
                encoding="utf-8")
            patterns = rs.load_patterns(pf)
            self.assertEqual([label for label, _ in patterns],
                             ["privname", "acmecorp"])

    def test_bad_regex_raises(self):
        with tempfile.TemporaryDirectory() as d:
            pf = Path(d) / "patterns.txt"
            pf.write_text("ok\n(unclosed\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                rs.load_patterns(pf)
            self.assertIn("line 2", str(ctx.exception))

    def test_empty_patterns_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            pf = Path(d) / "patterns.txt"
            pf.write_text("# only comments\n\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                rs.load_patterns(pf)


class PrivatePathGuardTest(unittest.TestCase):
    def test_guard_fires_before_pattern_scan(self):
        # A private path present AND a pattern hit: the path guard must win,
        # exiting 1 with RELEASE BLOCKED before any file is scanned.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "release"
            (root / "profiles" / "private").mkdir(parents=True)
            (root / "leak.txt").write_text("privname is here", encoding="utf-8")
            pf = Path(d) / "patterns.txt"
            pf.write_text("privname\n", encoding="utf-8")

            code, out, _ = _run([str(root), "--patterns", str(pf),
                                 "--private-path", "profiles/private"])
            self.assertEqual(code, 1)
            self.assertIn("RELEASE BLOCKED", out)
            self.assertIn("profiles/private", out)
            # Path guard aborts before scanning, so no file:line hit is printed.
            self.assertNotIn("leak.txt:1", out)

    def test_absent_private_path_does_not_block(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "release"
            root.mkdir()
            (root / "ok.txt").write_text("all clear", encoding="utf-8")
            pf = Path(d) / "patterns.txt"
            pf.write_text("privname\n", encoding="utf-8")

            code, out, _ = _run([str(root), "--patterns", str(pf),
                                 "--private-path", "profiles/private"])
            self.assertEqual(code, 0)
            self.assertIn("clean", out)


class ScanTest(unittest.TestCase):
    def test_clean_tree_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "release"
            root.mkdir()
            (root / "a.md").write_text("nothing private here\n", encoding="utf-8")
            pf = Path(d) / "patterns.txt"
            pf.write_text("privname\nacmecorp\n", encoding="utf-8")

            code, out, _ = _run([str(root), "--patterns", str(pf)])
            self.assertEqual(code, 0)
            self.assertIn("clean", out)

    def test_planted_hit_reports_file_and_line(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "release"
            root.mkdir()
            (root / "doc.md").write_text(
                "line one\ncontact dev@acmecorp.test now\n", encoding="utf-8")
            pf = Path(d) / "patterns.txt"
            pf.write_text("@acmecorp\\.test\n", encoding="utf-8")

            code, out, _ = _run([str(root), "--patterns", str(pf)])
            self.assertEqual(code, 1)
            self.assertIn("doc.md:2:", out)
            self.assertIn("[@acmecorp\\.test]", out)
            # The matched secret address itself must NOT be echoed.
            self.assertNotIn("dev@acmecorp.test", out)

    def test_patterns_file_not_scanned_against_itself(self):
        # The patterns file living inside the release tree must not self-match.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "release"
            root.mkdir()
            (root / "clean.md").write_text("harmless\n", encoding="utf-8")
            pf = root / "patterns.txt"
            pf.write_text("privname\n", encoding="utf-8")

            code, out, _ = _run([str(root), "--patterns", str(pf)])
            self.assertEqual(code, 0)
            self.assertIn("clean", out)

    def test_binary_and_skip_dirs_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "release"
            (root / ".git").mkdir(parents=True)
            (root / ".git" / "config").write_text("privname\n", encoding="utf-8")
            (root / "logo.png").write_text("privname\n", encoding="utf-8")
            pf = Path(d) / "patterns.txt"
            pf.write_text("privname\n", encoding="utf-8")

            code, out, _ = _run([str(root), "--patterns", str(pf)])
            self.assertEqual(code, 0)
            self.assertIn("clean", out)


class UsageErrorTest(unittest.TestCase):
    def test_bad_regex_patterns_file_exits_two(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "release"
            root.mkdir()
            pf = Path(d) / "patterns.txt"
            pf.write_text("ok\n(unclosed\n", encoding="utf-8")

            code, _, err = _run([str(root), "--patterns", str(pf)])
            self.assertEqual(code, 2)
            self.assertIn("line 2", err)

    def test_missing_patterns_file_exits_two(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "release"
            root.mkdir()
            code, _, err = _run([str(root), "--patterns",
                                 str(Path(d) / "nope.txt")])
            self.assertEqual(code, 2)

    def test_root_not_a_directory_exits_two(self):
        with tempfile.TemporaryDirectory() as d:
            pf = Path(d) / "patterns.txt"
            pf.write_text("privname\n", encoding="utf-8")
            code, _, err = _run([str(Path(d) / "missing"),
                                 "--patterns", str(pf)])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
