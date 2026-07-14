#!/usr/bin/env python3
"""Regression tests for validate_auth_log.py's invocation contract.

Pins the argv fix: the validator previously ignored argv entirely and globbed
from the cwd, so `validate_auth_log.py <path>` silently checked NOTHING and
exited 0. New contract: optional single positional workspace-root argument
(default `.`); an explicitly named root containing no logs exits 1 loudly; a
bare invocation finding none keeps the compatible exit-0; extra args exit 2.
Stdlib unittest only:

    python -m unittest discover -s tests
"""
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name, rel_path):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


val = _load("validate_auth_log", "tools/validate_auth_log.py")

CLEAN_LOG = "# auth-log\n\n## GRANT g-001\nscope: single\n"
DIRTY_LOG = ("# auth-log\n\n## GRANT g-001\nscope: single\n"
             "CONSUMED g-001\nCONSUMED g-001\n")


def _run(argv):
    """Call main() with a patched argv; return (exit_code, stdout)."""
    saved = sys.argv
    out = io.StringIO()
    try:
        sys.argv = ["validate_auth_log.py"] + argv
        with redirect_stdout(out):
            code = val.main()
        return code, out.getvalue()
    finally:
        sys.argv = saved


def _workspace(tmp, log_text=None):
    """Make tmp/memory/orchestrator[/auth-log.md]; return the root Path."""
    root = Path(tmp)
    role = root / "memory" / "orchestrator"
    role.mkdir(parents=True)
    if log_text is not None:
        (role / "auth-log.md").write_text(log_text, encoding="utf-8")
    return root


class TestExplicitRoot(unittest.TestCase):
    def test_clean_log_under_named_root_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp, CLEAN_LOG)
            code, out = _run([str(root)])
        self.assertEqual(code, 0)
        self.assertIn("1 log(s) clean", out)

    def test_violation_under_named_root_fails(self):
        # proves the named root's logs are actually parsed, not just counted
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp, DIRTY_LOG)
            code, out = _run([str(root)])
        self.assertEqual(code, 1)
        self.assertIn("duplicate CONSUMED", out)

    def test_named_root_with_no_logs_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp, log_text=None)  # memory/, no auth-log.md
            code, out = _run([str(root)])
        self.assertEqual(code, 1)
        self.assertIn("no memory/*/auth-log.md", out)

    def test_named_root_without_memory_dir_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = _run([tmp])
        self.assertEqual(code, 1)


class TestBareInvocation(unittest.TestCase):
    def test_bare_run_with_no_logs_stays_exit_zero(self):
        # compat: stamped-workspace CI runs bare before the first grant exists
        saved_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                code, out = _run([])
            finally:
                # restore BEFORE the tempdir cleanup — Windows cannot rmdir
                # a directory that is still the process cwd
                os.chdir(saved_cwd)
        self.assertEqual(code, 0)
        self.assertIn("nothing to check", out)

    def test_bare_run_still_finds_cwd_logs(self):
        saved_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                _workspace(tmp, CLEAN_LOG)
                os.chdir(tmp)
                code, _ = _run([])
            finally:
                os.chdir(saved_cwd)
        self.assertEqual(code, 0)


class TestUsage(unittest.TestCase):
    def test_extra_args_exit_2(self):
        code, out = _run(["a", "b"])
        self.assertEqual(code, 2)
        self.assertIn("usage:", out)


if __name__ == "__main__":
    unittest.main()
