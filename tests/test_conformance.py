#!/usr/bin/env python3
"""Regression tests for the workspace conformance suite's side-name checks.

Covers the role-rename feature (SIDE_NAMES / ROLE_ALIASES): that new_project
stamps the right ROLE_ALIASES row (empty by default, present when a side is
renamed), that a default stamp stays byte-identical, and that
conformance_check.check_side_names classifies malformed / renamed workspaces
correctly. Stdlib unittest only, importlib-loading the tools the same way
test_release_scrub.py does:

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


def _load(mod_name, rel_path):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


np = _load("new_project", "tools/new_project.py")
cc = _load("conformance_check", "tools/conformance_check.py")

ROLES_3 = {"owner", "builder", "orchestrator"}
ROLES_2 = {"owner", "builder"}


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


def _side_findings(side_names, roles, role_aliases=None):
    """Call check_side_names on hand-built slots; return the Findings object."""
    slots = {"SIDE_NAMES": side_names}
    if role_aliases is not None:
        slots["ROLE_ALIASES"] = role_aliases
    f = cc.Findings()
    cc.check_side_names(slots, roles, f)
    return f


def _sev(findings, sev):
    return [m for s, m in findings.items if s == sev]


class DefaultStampTest(unittest.TestCase):
    def test_default_stamp_has_no_alias_row_and_is_byte_adjacent(self):
        # Regression-guard the template: an all-defaults stamp emits an empty
        # alias_row, so SIDE_NAMES is immediately followed by CANONICAL_REPO
        # (no ROLE_ALIASES row inserted) — byte-identical to a pre-change stamp.
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            self.assertEqual(_stamp(dest, []), 0)
            text = (dest / "BINDINGS.md").read_text(encoding="utf-8")
            self.assertNotIn("ROLE_ALIASES", text)
            self.assertIn(
                "| SIDE_NAMES | owner / builder / orch |\n"
                "| CANONICAL_REPO |", text)

    def test_default_stamp_passes_conformance(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            self.assertEqual(_stamp(dest, []), 0)
            code, out = _conformance(dest)
            self.assertEqual(code, 0)  # warnings only (unfilled FILL slots)
            # no side-name WARN on an all-defaults stamp (orch is its default)
            self.assertNotIn("no ROLE_ALIASES row is", out)


class RenamedStampTest(unittest.TestCase):
    def test_builder_side_helper_stamps_alias_row_and_passes(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            self.assertEqual(
                _stamp(dest, ["--owner-side", "engine",
                              "--builder-side", "helper"]), 0)
            text = (dest / "BINDINGS.md").read_text(encoding="utf-8")
            self.assertIn("| SIDE_NAMES | engine / helper / orch |", text)
            self.assertIn("| ROLE_ALIASES | engine→owner, helper→builder |",
                          text)
            # README names the display when it differs; orch is unchanged.
            readme = (dest / "README.md").read_text(encoding="utf-8")
            self.assertIn('owner (as "engine")', readme)
            self.assertIn('builder (as "helper")', readme)
            code, _ = _conformance(dest)
            self.assertEqual(code, 0)  # warnings only

    def test_stamped_alias_row_yields_no_side_name_blockers(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            _stamp(dest, ["--builder-side", "helper"])
            slots = cc.parse_bindings(dest)
            f = cc.Findings()
            cc.check_side_names(slots, ROLES_3, f)
            self.assertEqual(_sev(f, "BLOCKER"), [])


class CorruptSideNameTest(unittest.TestCase):
    def test_underscore_side_name_blocks(self):
        f = _side_findings("own_er / builder / orch", ROLES_3)
        self.assertTrue(any("underscore" in m for m in _sev(f, "BLOCKER")))

    def test_duplicate_side_names_block(self):
        f = _side_findings("engine / engine / orch", ROLES_3)
        self.assertTrue(any("duplicated" in m for m in _sev(f, "BLOCKER")))

    def test_side_named_after_another_role_blocks(self):
        # owner side named "builder" collides with the builder role's name.
        f = _side_findings("builder / helper / orch", ROLES_3)
        self.assertTrue(
            any("canonical name of the builder role" in m
                for m in _sev(f, "BLOCKER")))

    def test_aliases_missing_legacy_covered_soft_warns(self):
        # Mirrors the live wc-tandem-ws case: engine / builder, no ROLE_ALIASES.
        # `engine` IS covered by /wake's legacy built-in (engine→owner), so the
        # WARN nudges toward an explicit row without claiming wake would fail.
        f = _side_findings("engine / builder", ROLES_2)
        self.assertTrue(
            any("legacy built-in aliases" in m for m in _sev(f, "WARN")))
        self.assertFalse(
            any("won't resolve" in m for m in _sev(f, "WARN")))
        self.assertEqual(_sev(f, "BLOCKER"), [])

    def test_aliases_missing_unresolved_name_warns_wont_resolve(self):
        # `captain` matches no legacy built-in — /wake captain really fails.
        f = _side_findings("captain / builder", ROLES_2)
        self.assertTrue(
            any("won't resolve" in m and "captain" in m
                for m in _sev(f, "WARN")))
        self.assertEqual(_sev(f, "BLOCKER"), [])

    def test_aliases_missing_legacy_name_wrong_role_warns_wont_resolve(self):
        # A BUILDER side named `engine` is NOT covered: the legacy built-in
        # maps engine→owner, the wrong role. Only an explicit ROLE_ALIASES row
        # (which /wake checks BEFORE the built-ins) resolves it correctly.
        f = _side_findings("owner / engine", ROLES_2)
        self.assertTrue(
            any("won't resolve" in m and "engine" in m
                for m in _sev(f, "WARN")))

    def test_unknown_alias_target_blocks(self):
        f = _side_findings("engine / helper / orch", ROLES_3,
                           role_aliases="engine→owner, helper→bilder")
        self.assertTrue(
            any("not a canonical role" in m for m in _sev(f, "BLOCKER")))

    def test_alias_wrong_position_blocks(self):
        # engine sits at the owner position but the alias claims it is builder.
        f = _side_findings("engine / helper / orch", ROLES_3,
                           role_aliases="engine→builder, helper→owner")
        self.assertTrue(
            any("places 'engine' at the owner position" in m
                for m in _sev(f, "BLOCKER")))

    def test_arrow_ascii_form_accepted(self):
        # `->` is accepted alongside the unicode arrow.
        f = _side_findings("engine / helper / orch", ROLES_3,
                           role_aliases="engine->owner, helper->builder")
        self.assertEqual(_sev(f, "BLOCKER"), [])


if __name__ == "__main__":
    unittest.main()
