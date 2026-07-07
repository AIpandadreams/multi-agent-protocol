#!/usr/bin/env python3
"""Regression tests for tools/scale_workspace.py [PROTOCOL v2.6].

Scaling a 2-agent workspace up to 3-agent must add the orchestrator scaffold
WITHOUT disturbing the principal-owned BINDINGS.md, and must be idempotent. A
mangled BINDINGS or a second run that re-writes files would both be silent
corruption, so both get committed tests. Stdlib unittest only:

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
_np_spec = importlib.util.spec_from_file_location(
    "new_project", ROOT / "tools" / "new_project.py")
np = importlib.util.module_from_spec(_np_spec)
_np_spec.loader.exec_module(np)
_sw_spec = importlib.util.spec_from_file_location(
    "scale_workspace", ROOT / "tools" / "scale_workspace.py")
sw = importlib.util.module_from_spec(_sw_spec)
_sw_spec.loader.exec_module(sw)


def _stamp_2agent(dest: Path, name="adoptme"):
    """Stamp a fresh 2agent.local workspace, swallowing new_project's stdout."""
    saved = sys.argv
    try:
        sys.argv = ["new_project.py", "--name", name, "--dest", str(dest),
                    "--profile", "2agent.local"]
        with redirect_stdout(io.StringIO()):
            rc = np.main()
    finally:
        sys.argv = saved
    assert rc == 0, f"stamp failed: {rc}"


def _run(argv):
    saved = sys.argv
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["scale_workspace.py"] + argv
        with redirect_stdout(out), redirect_stderr(err):
            code = sw.main()
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


class ScaleTest(unittest.TestCase):
    def test_scale_adds_orchestrator_and_preserves_bindings(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / "ws"
            _stamp_2agent(ws)
            bindings_before = (ws / "BINDINGS.md").read_bytes()

            code, out, _ = _run(["--workspace", str(ws)])
            self.assertEqual(code, 0)

            # Every orchestrator-delta file now exists.
            for rel in sw.ORCH_FILES:
                self.assertTrue((ws / rel).is_file(), f"missing {rel}")

            # BINDINGS.md is byte-identical — the tool never touches it.
            self.assertEqual((ws / "BINDINGS.md").read_bytes(), bindings_before)

            # It printed the by-hand steps (PROFILE flip + FLAVOR row).
            self.assertIn("PROFILE | 3agent.local", out)
            self.assertIn("FLAVOR", out)

    def test_second_run_is_noop(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / "ws"
            _stamp_2agent(ws)
            _run(["--workspace", str(ws)])
            # Capture a file's bytes after first scale, then run again.
            taskqueue_after_first = (ws / "TASKQUEUE.md").read_bytes()

            code, out, _ = _run(["--workspace", str(ws)])
            self.assertEqual(code, 0)
            self.assertIn("nothing to do", out)
            # No file was rewritten on the second run.
            self.assertEqual((ws / "TASKQUEUE.md").read_bytes(),
                             taskqueue_after_first)

    def test_dry_run_creates_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / "ws"
            _stamp_2agent(ws)

            code, out, _ = _run(["--workspace", str(ws), "--dry-run"])
            self.assertEqual(code, 0)
            self.assertIn("would create", out)
            # Nothing was actually written.
            for rel in sw.ORCH_FILES:
                self.assertFalse((ws / rel).exists(),
                                 f"dry-run created {rel}")

    def test_not_a_workspace_exits_one(self):
        with tempfile.TemporaryDirectory() as d:
            empty = Path(d) / "empty"
            empty.mkdir()
            code, _, err = _run(["--workspace", str(empty)])
            self.assertEqual(code, 1)
            self.assertIn("BINDINGS", err)


if __name__ == "__main__":
    unittest.main()
