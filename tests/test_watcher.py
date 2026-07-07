#!/usr/bin/env python3
"""Regression tests for tools/watcher.py [PROTOCOL v2.6].

The watcher is transport machinery — a wrong diff or a suppressed lane is a
silent intake failure, so add/modify/remove detection, the --once state
round-trip, settle semantics (a mid-write lane is not reported until it holds
still), MULTI-DIR INDEPENDENCE (one dirty lane never suppresses another lane's
report), exit codes, and {dir} substitution all get committed tests. Stdlib
unittest only, matching the repo's no-extra-dependency posture:

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
    "watcher", ROOT / "tools" / "watcher.py")
w = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(w)
rp = w.rp  # the reviewer_poller module the watcher reuses


def _run(argv):
    """Invoke main() with argv, returning (exit_code, stdout, stderr)."""
    saved = sys.argv
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["watcher.py"] + argv
        with redirect_stdout(out), redirect_stderr(err):
            code = w.main()
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


class DiffSnapshotsTest(unittest.TestCase):
    def test_added_modified_removed(self):
        old = {"a": (1, 10), "b": (1, 10), "keep": (5, 5)}
        new = {"b": (2, 20), "keep": (5, 5), "c": (1, 10)}
        events = w.diff_snapshots(old, new)
        self.assertIn(("ADDED", "c"), events)
        self.assertIn(("MODIFIED", "b"), events)
        self.assertIn(("REMOVED", "a"), events)
        # an unchanged file produces no event
        self.assertNotIn(("MODIFIED", "keep"), events)

    def test_no_change_is_empty(self):
        same = {"a": (1, 10)}
        self.assertEqual(w.diff_snapshots(same, dict(same)), [])


class OnceStateRoundTripTest(unittest.TestCase):
    def test_baseline_then_unchanged_then_change(self):
        with tempfile.TemporaryDirectory() as d:
            lane = Path(d) / "lane"
            lane.mkdir()
            (lane / "e1.md").write_text("x", encoding="utf-8")
            state = Path(d) / "state.json"

            # First run: baseline established, nothing reported, exit 0.
            code, out, _ = _run(["--dir", str(lane), "--once",
                                 "--state", str(state)])
            self.assertEqual(code, 0)
            self.assertIn("baseline", out)
            self.assertTrue(state.is_file())

            # Second run, unchanged tree: still exit 0, "no changes".
            code, out, _ = _run(["--dir", str(lane), "--once",
                                 "--state", str(state)])
            self.assertEqual(code, 0)
            self.assertIn("no changes", out)

            # Now add a file: exit 3 and an ADDED line naming it.
            (lane / "e2.md").write_text("y", encoding="utf-8")
            code, out, _ = _run(["--dir", str(lane), "--once",
                                 "--state", str(state)])
            self.assertEqual(code, 3)
            self.assertIn("CHANGED", out)
            self.assertIn("ADDED e2.md", out)

    def test_once_requires_state(self):
        with tempfile.TemporaryDirectory() as d:
            lane = Path(d) / "lane"
            lane.mkdir()
            code, _, err = _run(["--dir", str(lane), "--once"])
            self.assertEqual(code, 2)
            self.assertIn("--state", err)

    def test_no_dirs_is_usage_error(self):
        code, _, err = _run(["--once", "--state", "whatever.json"])
        self.assertEqual(code, 2)
        self.assertIn("no lanes", err)


class SettleSemanticsTest(unittest.TestCase):
    """The watcher reuses reviewer_poller's settle primitives, so a file being
    written is not reported until its lane signature holds still one tick."""

    def test_mid_write_not_reported_until_settled(self):
        with tempfile.TemporaryDirectory() as d:
            lane = Path(d) / "lane"
            lane.mkdir()
            pairs = [(str(lane), lane)]
            sigs = {str(lane): rp.dir_signature(lane)}
            dirty = set()
            reported = {str(lane): w.snapshot(lane)}

            # Tick 1: a file appears -> lane dirty, NOT settled -> no report.
            (lane / "req.md").write_text("partial", encoding="utf-8")
            settled = rp.detect_settled(pairs, sigs, dirty)
            self.assertEqual(settled, [])
            self.assertEqual(
                w.report_settled(pairs, settled, dirty, reported), [])
            self.assertIn(str(lane), dirty)

            # Tick 2: no further writes -> lane settles -> now reported ADDED.
            settled = rp.detect_settled(pairs, sigs, dirty)
            self.assertEqual(settled, [str(lane)])
            lines = w.report_settled(pairs, settled, dirty, reported)
            self.assertEqual(len(lines), 1)
            self.assertIn("ADDED req.md", lines[0][1])


class MultiDirIndependenceTest(unittest.TestCase):
    def test_one_dirty_lane_does_not_suppress_another(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "lane_a", Path(d) / "lane_b"
            a.mkdir()
            b.mkdir()
            pairs = [(str(a), a), (str(b), b)]
            sigs = {str(a): rp.dir_signature(a), str(b): rp.dir_signature(b)}
            dirty = set()
            reported = {str(a): w.snapshot(a), str(b): w.snapshot(b)}

            # lane_a gets a file and holds; lane_b is still mid-write.
            (a / "done.md").write_text("x", encoding="utf-8")
            rp.detect_settled(pairs, sigs, dirty)   # a dirty; b clean
            (b / "churning.md").write_text("y", encoding="utf-8")
            settled = rp.detect_settled(pairs, sigs, dirty)  # a settles; b moves

            self.assertEqual(settled, [str(a)])
            self.assertIn(str(b), dirty)
            lines = w.report_settled(pairs, settled, dirty, reported)
            # lane_a IS reported even though lane_b is dirty this same tick.
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0][0], str(a))
            self.assertIn("ADDED done.md", lines[0][1])


class SubstitutionTest(unittest.TestCase):
    def test_dir_placeholder_replaced(self):
        self.assertEqual(
            w.substitute("touch {dir}/marker", "path/to/lane"),
            "touch path/to/lane/marker")

    def test_on_change_invocation_writes_marker(self):
        # Prove {dir} substitution AND invocation without depending on a shell
        # builtin: the command is the python interpreter running a tiny helper
        # script that creates a marker inside the substituted directory.
        with tempfile.TemporaryDirectory() as d:
            lane = Path(d) / "lane"
            lane.mkdir()
            helper = Path(d) / "mark.py"
            helper.write_text(
                "import sys, pathlib\n"
                "pathlib.Path(sys.argv[1], 'marker').write_text('x')\n",
                encoding="utf-8")
            cmd = f'"{sys.executable}" "{helper}" "{{dir}}"'
            w.run_on_change(cmd, str(lane))
            self.assertTrue((lane / "marker").is_file())


class CollectDirsTest(unittest.TestCase):
    def test_config_and_dir_merge_and_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "watcher.json"
            cfg.write_text('{"dirs": ["path/to/b", "path/to/a"]}',
                           encoding="utf-8")
            args = type("A", (), {"dir": ["path/to/a"], "config": str(cfg)})()
            dirs = w.collect_dirs(args)
            # "path/to/a" appears in both --dir and config -> watched once
            self.assertEqual(dirs.count("path/to/a"), 1)
            self.assertEqual(set(dirs), {"path/to/a", "path/to/b"})


if __name__ == "__main__":
    unittest.main()
