#!/usr/bin/env python3
"""Regression tests for the git-sync transport (Workstream E).

Covers the TRANSPORT / WORKSPACE_REMOTE / SECRETS binding slots: that
new_project stamps the `*.git-sync` profiles with the right rows (and the
`*.local` profiles without a WORKSPACE_REMOTE row), that the deliberate
template additions keep the byte-adjacency the stamp guarantees, and that
conformance_check.check_transport classifies present/absent/agreeing/
disagreeing/unknown transports and repo-relative-vs-absolute paths correctly.

Stdlib unittest only, importlib-loading the tools the same way
test_conformance.py does:

    python -m unittest discover -s tests
"""
import importlib.util
import io
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(mod_name, rel_path):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


np = _load("new_project", "tools/new_project.py")
cc = _load("conformance_check", "tools/conformance_check.py")


def _stamp(dest, extra_args):
    """Run new_project.main() to stamp a workspace at `dest`; return exit code."""
    saved = sys.argv
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["new_project.py", "--name", "t", "--dest", str(dest)] + extra_args
        with redirect_stdout(out), redirect_stderr(err):
            return np.main()
    finally:
        sys.argv = saved


def _conformance(dest):
    """Run conformance_check.main() against `dest`; return (code, stdout)."""
    saved = sys.argv
    out, err = io.StringIO(), io.StringIO()
    try:
        sys.argv = ["conformance_check.py", "--workspace", str(dest)]
        with redirect_stdout(out), redirect_stderr(err):
            code = cc.main()
    finally:
        sys.argv = saved
    return code, out.getvalue()


def _transport_findings(slots):
    """Call check_transport on hand-built slots; return the Findings object."""
    f = cc.Findings()
    cc.check_transport(slots, f)
    return f


def _sev(findings, sev):
    return [m for s, m in findings.items if s == sev]


class GitSyncStampTest(unittest.TestCase):
    def test_3agent_git_sync_stamps_transport_remote_and_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            self.assertEqual(_stamp(dest, ["--profile", "3agent.git-sync"]), 0)
            text = (dest / "BINDINGS.md").read_text(encoding="utf-8")
            self.assertIn("| PROFILE | 3agent.git-sync |", text)
            self.assertIn("| TRANSPORT | git-sync |", text)
            self.assertIn("| WORKSPACE_REMOTE | {{FILL", text)
            self.assertIn("| SECRETS | none committed", text)
            # CHANNEL/MEMORY are repo-relative for BOTH transports — never an
            # absolute host path under git-sync.
            self.assertIn("| CHANNEL | channel/ (repo-relative", text)
            self.assertIn("| MEMORY | memory/<role>/ (repo-relative) |", text)

    def test_2agent_git_sync_stamps_two_roles_and_passes_conformance(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            self.assertEqual(_stamp(dest, ["--profile", "2agent.git-sync"]), 0)
            self.assertTrue((dest / "memory" / "owner").is_dir())
            self.assertTrue((dest / "memory" / "builder").is_dir())
            self.assertFalse((dest / "memory" / "orchestrator").is_dir())
            code, out = _conformance(dest)
            self.assertEqual(code, 0)  # warnings only (unfilled FILL slots)
            # the transport agrees with the profile — no transport finding line
            self.assertNotIn("TRANSPORT", out)

    def test_git_sync_stamp_has_no_absolute_path_transport_warn(self):
        # A freshly stamped git-sync workspace binds repo-relative CHANNEL/
        # MEMORY, so check_transport must not raise the host-profile-leak WARN.
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _stamp(dest, ["--profile", "3agent.git-sync"])
            slots = cc.parse_bindings(dest)
            f = _transport_findings(slots)
            self.assertEqual(_sev(f, "BLOCKER"), [])
            self.assertFalse(any("absolute path" in m for m in _sev(f, "WARN")))

    def test_local_stamp_has_no_workspace_remote_row(self):
        # The `.local` profiles bind local-fs and must NOT carry a
        # WORKSPACE_REMOTE row (it is git-sync-only).
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _stamp(dest, ["--profile", "3agent.local"])
            text = (dest / "BINDINGS.md").read_text(encoding="utf-8")
            self.assertIn("| TRANSPORT | local-fs |", text)
            self.assertNotIn("WORKSPACE_REMOTE", text)


class TemplateByteAdjacencyTest(unittest.TestCase):
    # The stamp guarantees a stable slot order; these lock the DELIBERATE
    # additions from Workstream E so a future template edit that reorders or
    # drops a row is caught (companion to test_conformance's SIDE_NAMES ->
    # CANONICAL_REPO adjacency guard).
    def test_default_local_stamp_profile_transport_side_names_adjacent(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _stamp(dest, [])  # default profile = 3agent.local
            text = (dest / "BINDINGS.md").read_text(encoding="utf-8")
            # local-fs: no WORKSPACE_REMOTE row between TRANSPORT and SIDE_NAMES
            self.assertIn(
                "| PROFILE | 3agent.local |\n"
                "| TRANSPORT | local-fs |\n"
                "| SIDE_NAMES |", text)
            self.assertNotIn("| WORKSPACE_REMOTE |", text)

    def test_git_sync_stamp_transport_remote_side_names_adjacent(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _stamp(dest, ["--profile", "3agent.git-sync"])
            text = (dest / "BINDINGS.md").read_text(encoding="utf-8")
            # git-sync: WORKSPACE_REMOTE row sits between TRANSPORT and SIDE_NAMES
            self.assertRegex(
                text,
                r"\| PROFILE \| 3agent\.git-sync \|\n"
                r"\| TRANSPORT \| git-sync \|\n"
                r"\| WORKSPACE_REMOTE \| \{\{FILL[^}]*\}\} \|\n"
                r"\| SIDE_NAMES \|")


class CheckTransportTest(unittest.TestCase):
    def test_transport_agrees_with_git_sync_profile(self):
        f = _transport_findings(
            {"PROFILE": "3agent.git-sync", "TRANSPORT": "git-sync"})
        self.assertEqual(_sev(f, "BLOCKER"), [])

    def test_transport_agrees_with_local_profile(self):
        f = _transport_findings(
            {"PROFILE": "2agent.local", "TRANSPORT": "local-fs"})
        self.assertEqual(_sev(f, "BLOCKER"), [])

    def test_transport_disagrees_with_profile_blocks(self):
        # git-sync value under a .local profile is a hard mismatch.
        f = _transport_findings(
            {"PROFILE": "3agent.local", "TRANSPORT": "git-sync"})
        self.assertTrue(
            any("disagrees with PROFILE" in m for m in _sev(f, "BLOCKER")))

    def test_unknown_transport_value_blocks(self):
        f = _transport_findings(
            {"PROFILE": "3agent.local", "TRANSPORT": "carrier-pigeon"})
        self.assertTrue(
            any("is unknown" in m for m in _sev(f, "BLOCKER")))

    def test_absent_transport_is_silent_on_v25_pin(self):
        # A v2.5 workspace predates the slot — a missing TRANSPORT never flags.
        f = _transport_findings(
            {"PROFILE": "3agent.local", "PROTOCOL_VERSION": "v2.5"})
        self.assertEqual(f.items, [])

    def test_absent_transport_is_silent_on_v26_without_it(self):
        # A v2.6 workspace that simply hasn't adopted the slot is also silent.
        f = _transport_findings(
            {"PROFILE": "3agent.local", "PROTOCOL_VERSION": "v2.6"})
        self.assertEqual(f.items, [])

    def test_git_sync_absolute_channel_path_warns(self):
        f = _transport_findings(
            {"PROFILE": "3agent.git-sync", "TRANSPORT": "git-sync",
             "CHANNEL": "C:\\ws\\channel",
             "MEMORY": "memory/<role>/ (repo-relative)"})
        self.assertEqual(_sev(f, "BLOCKER"), [])
        self.assertTrue(
            any("CHANNEL" in m and "absolute path" in m
                for m in _sev(f, "WARN")))

    def test_git_sync_posix_absolute_memory_path_warns(self):
        f = _transport_findings(
            {"PROFILE": "2agent.git-sync", "TRANSPORT": "git-sync",
             "CHANNEL": "channel/ (repo-relative)",
             "MEMORY": "/srv/ws/memory/<role>/"})
        self.assertTrue(
            any("MEMORY" in m and "absolute path" in m
                for m in _sev(f, "WARN")))

    def test_git_sync_repo_relative_paths_no_warn(self):
        f = _transport_findings(
            {"PROFILE": "3agent.git-sync", "TRANSPORT": "git-sync",
             "CHANNEL": "channel/ (repo-relative; this workspace repo)",
             "MEMORY": "memory/<role>/ (repo-relative)"})
        self.assertEqual(_sev(f, "WARN"), [])
        self.assertEqual(_sev(f, "BLOCKER"), [])

    def test_repo_relative_value_with_url_note_no_warn(self):
        # A repo-relative value that cites a URL must NOT trip the absolute-path
        # guard — the `s:/` in `https://` used to false-match the drive-letter
        # alternative (the MODERATE finding).
        f = _transport_findings(
            {"PROFILE": "3agent.git-sync", "TRANSPORT": "git-sync",
             "CHANNEL": "channel/ (repo-relative)",
             "MEMORY": "memory/<role>/ (see https://example.com/doc)"})
        self.assertEqual(_sev(f, "WARN"), [])
        self.assertEqual(_sev(f, "BLOCKER"), [])


class AbsPathRegexTest(unittest.TestCase):
    # Directly pin ABS_PATH_RE against the cases the MODERATE finding named:
    # real absolute paths match; repo-relative values and URLs do not.
    def _matches(self, value):
        return cc.ABS_PATH_RE.search(value) is not None

    def test_repo_relative_channel_no_match(self):
        self.assertFalse(self._matches("channel/"))
        self.assertFalse(self._matches("channel/ (repo-relative)"))

    def test_windows_drive_path_matches(self):
        self.assertTrue(self._matches("C:\\ws"))
        self.assertTrue(self._matches("C:/ws"))
        # at string start (no char before the drive letter)
        self.assertTrue(self._matches("C:\\ws\\channel"))

    def test_posix_absolute_path_matches(self):
        self.assertTrue(self._matches("/srv/ws"))
        self.assertTrue(self._matches("/var/lib/ws"))

    def test_unc_path_matches(self):
        self.assertTrue(self._matches("\\\\host\\share"))

    def test_bare_url_no_match(self):
        self.assertFalse(self._matches("https://example.com/x"))
        self.assertFalse(self._matches("http://example.com/a/b"))

    def test_value_with_embedded_url_no_match(self):
        self.assertFalse(
            self._matches("memory/<role>/ (see https://example.com/doc)"))


if __name__ == "__main__":
    unittest.main()
