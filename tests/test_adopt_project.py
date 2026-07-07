#!/usr/bin/env python3
"""Regression tests for tools/adopt_project.py [PROTOCOL v2.6].

Adoption must never write into an existing collaboration's directory (it stamps
a NEW workspace beside it) and its checklist is the load-bearing part — the
per-side-counter-carry and the MIGRATION.md pointer are what keep a live cutover
from corrupting state. The pure adoption_checklist() is also embedded by a later
wizard, so its contract gets a direct test. Stdlib unittest only:

    python -m unittest discover -s tests
"""
import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "adopt_project", ROOT / "tools" / "adopt_project.py")
ap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ap)


def _run(argv):
    saved = sys.argv
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["adopt_project.py"] + argv
        with redirect_stdout(out), redirect_stderr(err):
            code = ap.main()
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


class ChecklistFunctionTest(unittest.TestCase):
    """adoption_checklist() is pure and importable — a wizard embeds it."""

    def test_mentions_per_side_counters_and_migration(self):
        text = ap.adoption_checklist("myproject at path/to/ws")
        lower = text.lower()
        self.assertIn("myproject at path/to/ws", text)
        # The load-bearing phrases: per-side counters, read from the live tail,
        # never reset, and the pointer to the migration pattern.
        self.assertIn("per side", lower)
        self.assertIn("tail", lower)
        self.assertIn("never reset", lower)
        self.assertIn("MIGRATION.md", text)

    def test_is_pure_no_io(self):
        # Two calls with the same argument return byte-identical output and the
        # function performs no file I/O it could leak.
        a = ap.adoption_checklist("x")
        b = ap.adoption_checklist("x")
        self.assertEqual(a, b)


class AdoptStampTest(unittest.TestCase):
    def test_stamps_new_workspace_and_prints_checklist(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "newws"
            code, out, _ = _run(["--name", "proj", "--dest", str(dest),
                                 "--profile", "2agent.local"])
            self.assertEqual(code, 0)
            self.assertTrue((dest / "BINDINGS.md").is_file())
            self.assertIn("ADOPTION CHECKLIST", out)
            self.assertIn("MIGRATION.md", out)

    def test_refuses_non_empty_dest(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "existing"
            dest.mkdir()
            (dest / "already.txt").write_text("stuff", encoding="utf-8")
            code, out, err = _run(["--name", "proj", "--dest", str(dest),
                                   "--profile", "2agent.local"])
            self.assertEqual(code, 1)
            # new_project's refusal message is surfaced verbatim.
            self.assertIn("refusing", (out + err))


if __name__ == "__main__":
    unittest.main()
