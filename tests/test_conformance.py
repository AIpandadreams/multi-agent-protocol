#!/usr/bin/env python3
"""Regression tests for the conformance suite and the workspace stamper.

Covers, among other things, the role-rename feature (SIDE_NAMES /
ROLE_ALIASES): that new_project stamps the right ROLE_ALIASES row (empty by
default, present when a side is renamed), that a default stamp stays
byte-adjacent, and that conformance_check.check_side_names classifies
malformed / renamed workspaces correctly. Also compares one axis the two tools
share: the stamper's `PROFILE_CHOICES` and the checker's `PROFILE_ROLES` are
independent literals, and this file asserts they name the same profiles -- the
names only, not what a name means to either tool. Stdlib unittest only,
importlib-loading the tools the same way test_release_scrub.py does:

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
        # (no ROLE_ALIASES row inserted) — the rows that would sit
        # around it stay adjacent.
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

    def test_missing_vendored_checker_blocks(self):
        # The wake gate fails CLOSED when the workspace's stamped checker is
        # absent: a trusted-copy run must surface the absence itself as a
        # BLOCKER, never run green over a workspace that cannot self-check.
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            self.assertEqual(_stamp(dest, []), 0)
            (dest / "tools" / "conformance_check.py").unlink()
            code, out = _conformance(dest)
            self.assertNotEqual(code, 0)
            self.assertIn(
                "missing required file: tools/conformance_check.py", out)


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
        # A renamed-but-unaliased owner side: engine / builder, no ROLE_ALIASES.
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

    def test_aliases_missing_legacy_name_wrong_role_blocks(self):
        # A BUILDER side named `engine` with no covering entry MISROUTES: the
        # legacy built-in maps engine→owner, so /wake engine wakes the WRONG
        # role. Only an explicit ROLE_ALIASES entry (which /wake checks BEFORE
        # the built-ins) resolves it correctly — absent one, this must block.
        f = _side_findings("owner / engine", ROLES_2)
        self.assertTrue(
            any("WRONG role" in m and "engine" in m
                for m in _sev(f, "BLOCKER")))

    def test_legacy_wrong_role_with_overriding_entry_passes(self):
        # Same shape but WITH the overriding entry: workspace ROLE_ALIASES
        # beats the legacy built-in in /wake's tier order, so it resolves.
        f = _side_findings("owner / engine", ROLES_2,
                           role_aliases="engine→builder")
        self.assertEqual(_sev(f, "BLOCKER"), [])
        self.assertEqual(_sev(f, "WARN"), [])

    def test_side_named_after_out_of_profile_canonical_role_blocks(self):
        # 2-agent profile, OWNER side named `orchestrator`: /wake resolves
        # canonical names FIRST, for ALL roles — not just this profile's — so
        # /wake orchestrator would target the absent orchestrator role even
        # with an alias row present.
        f = _side_findings("orchestrator / builder", ROLES_2,
                           role_aliases="orchestrator→owner")
        self.assertTrue(
            any("canonical name of the orchestrator role" in m
                for m in _sev(f, "BLOCKER")))

    def test_partial_alias_row_unresolved_side_warns_wont_resolve(self):
        # A row that EXISTS but omits a renamed side must not pass silently:
        # `capt` (orchestrator) matches no legacy built-in — /wake capt fails.
        f = _side_findings("engine / builder / capt", ROLES_3,
                           role_aliases="engine→owner")
        self.assertTrue(
            any("won't resolve" in m and "capt" in m
                for m in _sev(f, "WARN")))
        self.assertEqual(_sev(f, "BLOCKER"), [])

    def test_partial_alias_row_legacy_covered_soft_warns(self):
        # Omitted side covered by a same-role legacy built-in (helper→builder)
        # still resolves — soft nudge, not a "won't resolve" claim.
        f = _side_findings("engine / helper / orch", ROLES_3,
                           role_aliases="engine→owner")
        self.assertTrue(
            any("legacy" in m and "helper" in m for m in _sev(f, "WARN")))
        self.assertFalse(
            any("won't resolve" in m for m in _sev(f, "WARN")))

    def test_complete_alias_row_yields_no_side_name_warns(self):
        f = _side_findings("engine / helper / orch", ROLES_3,
                           role_aliases="engine→owner, helper→builder")
        self.assertEqual(_sev(f, "WARN"), [])
        self.assertEqual(_sev(f, "BLOCKER"), [])

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


class ProfileAxisTest(unittest.TestCase):
    """`new_project.PROFILE_CHOICES` against `conformance_check.PROFILE_ROLES`.

    They are independent literals in two different tools, and neither reads
    the other's literal. This test compares them, and rejects a literal
    that is empty or holds an empty name. Two literals that name nothing can
    compare equal, so the comparison alone would pass while neither tool
    names anything.

    It does not describe what the rest of the suite does about drift
    between the two. Some of its blind spots can be named here; the list
    is not a survey. Two literals can name the same profiles and still disagree
    about what a name MEANS -- `new_project` decides the role set by
    parsing the name, `conformance_check` by looking it up in a table -- and
    this test compares names only. A name repeated in `PROFILE_CHOICES` is
    invisible to it, because a set collapses the repetition;
    `PROFILE_ROLES` is a dict, where a repeated key is already gone before
    any set is built. Beyond the two literals, a profile name can also be
    spelled out elsewhere, and nothing here binds those spellings to
    either -- among them the stamper's own defaults, both when `--profile`
    is omitted and under the deprecated `--no-orchestrator` alias, the
    wizard's string, which is composed from fragments rather than written
    whole, usage text, and prose surfaces elsewhere in the tree. Nothing
    here reports such a spelling drifting. Whether anything else catches
    one varies from spelling to spelling, and is not this test's claim to
    make.

    The invocation `scale_workspace.py` builds is listed apart from them,
    because it is not the same kind of thing: it passes `--profile` to
    `new_project.main`, so argparse checks it against `PROFILE_CHOICES`
    and a lockstep rename makes it exit rather than drift. It is a blind
    spot of this test, which reads neither tool's call sites, but not a
    silent one.
    """

    def test_stamper_and_checker_name_the_same_profiles(self):
        # Set equality, in both directions, because divergence has two
        # directions and a comparison that only reported one of them would
        # be silent on the other. What each direction COSTS is a property of
        # the tools rather than of this test, and is not asserted here.
        #
        # The failure names the side rather than leaving it to be recovered
        # from the argument order of a set-difference report.
        # A literal that is empty, or that holds an empty name, is
        # rejected before the comparison runs. Two literals that name
        # nothing can compare equal while neither tool names anything.
        # This names the side for the same reason the comparison below does.
        bad = [name for name, literal in (
            ("tools/new_project.py PROFILE_CHOICES", np.PROFILE_CHOICES),
            ("tools/conformance_check.py PROFILE_ROLES", cc.PROFILE_ROLES))
            if not literal or not all(literal)]
        self.assertEqual(
            bad, [],
            "a profile literal is empty or holds an empty name: %s" % bad)

        only_stamper = sorted(set(np.PROFILE_CHOICES) - set(cc.PROFILE_ROLES))
        only_checker = sorted(set(cc.PROFILE_ROLES) - set(np.PROFILE_CHOICES))
        self.assertEqual(
            (only_stamper, only_checker), ([], []),
            "profile drift between the two tools: "
            "offered by tools/new_project.py PROFILE_CHOICES but unknown to "
            "tools/conformance_check.py PROFILE_ROLES: %s; known to "
            "PROFILE_ROLES but not offered by PROFILE_CHOICES: %s"
            % (only_stamper, only_checker))


if __name__ == "__main__":
    unittest.main()
