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


def _profile_findings(profile, roles):
    """Call `check_bindings` on hand-built slots; return the Findings object.

    Only the profile/role-set leg is under test. The version slot is filled
    FROM `SUPPORTED_VERSIONS` rather than written as a literal: a hardcoded
    version here would turn the next protocol bump into a failure in a test
    that is not about versions.
    """
    pinned = cc.SUPPORTED_VERSIONS[-1]
    slots = {"PROTOCOL_VERSION": pinned, "PROFILE": profile}
    f = cc.Findings()
    with tempfile.TemporaryDirectory() as td:
        cc.check_bindings(Path(td), slots, roles, pinned, f)
    return f


def _profile_blockers(profile, roles):
    """The blockers this leg raises, and only this leg's."""
    return [m for m in _sev(_profile_findings(profile, roles), "BLOCKER")
            if "expects roles" in m]


class NonSeatIdentityProfileTest(unittest.TestCase):
    """A PROFILE enumerates SEATS; `memory/` holds IDENTITIES.

    `infer_roles` returns every directory under `memory/`, which by this
    module's own doctrine (IDENTITIES THAT ARE NOT SEATS) includes non-seats.
    Comparing that set directly against a profile asks a seat question of an
    identity set, so a workspace with a legitimate `memory/creator/` failed a
    profile it actually satisfied — a fail-closed BLOCKER that no correct file
    at that seat could clear.

    That defect was cured in halves. The vocabulary half landed with
    `NON_SEAT_IDENTITIES` / `LOCK_VOCABULARY`; the profile comparison kept
    reading the identity set, so the blocker was RELOCATED, not removed. These
    cases pin the second half.

    ⭐ The first case FAILS against the un-subtracted comparison, so this class
    proves its own liveness rather than asserting it. The rest are the controls
    that keep the cure from becoming a hole: subtracting non-seats must not
    make a genuinely wrong role set pass, and must not turn a missing seat into
    silence.
    """

    SEATS = {"owner", "builder", "orchestrator"}
    PROFILE = "3agent.local"

    def test_the_exact_seat_set_passes(self):
        self.assertEqual(_profile_blockers(self.PROFILE, set(self.SEATS)), [])

    def test_a_non_seat_identity_does_not_fail_a_profile_it_satisfies(self):
        """R1's purpose. This is the case that fails without the subtraction."""
        for non_seat in cc.NON_SEAT_IDENTITIES:
            with self.subTest(non_seat=non_seat):
                self.assertEqual(
                    _profile_blockers(self.PROFILE, self.SEATS | {non_seat}), [],
                    "a non-seat identity must not fail a profile whose seats "
                    "are all present")

    def test_a_missing_seat_still_blocks_when_a_non_seat_is_present(self):
        """The subtraction must not swallow a real defect standing beside it."""
        got = _profile_blockers(self.PROFILE, {"owner", "builder", "creator"})
        self.assertEqual(len(got), 1, got)
        # The list reported is the COMPARISON set — identities minus the
        # enumerated non-seats — and it is listed without a noun, because
        # that set is only seats when nothing unrecognised is present.
        self.assertIn("memory/ has ['builder', 'owner']", got[0])
        # ⛔ And the message NAMES what it set aside. Reporting only the seats
        # would be true and proportioned wrong: it reads as though `memory/`
        # held nothing else, which is the same failure direction as silence.
        self.assertIn("non-seat identities not compared: ['creator']", got[0])

    def test_a_workspace_of_only_non_seats_blocks_rather_than_skipping(self):
        """The guard stays on `roles`, never on `seats`.

        Guarding on `seats` would be the obvious form and is a fail-silent:
        a workspace holding only non-seat identities has no seats, so the
        comparison would be skipped for having nothing to compare — a hole
        introduced by the cure itself.
        """
        got = _profile_blockers(self.PROFILE, {"creator"})
        self.assertEqual(len(got), 1, got)
        self.assertIn("memory/ has []", got[0])
        self.assertIn("non-seat identities not compared: ['creator']", got[0])

    def test_a_missing_seat_with_no_non_seats_blocks_without_the_note(self):
        """No set-aside, no note — the disclosure is earned, not decorative."""
        got = _profile_blockers(self.PROFILE, {"owner", "builder"})
        self.assertEqual(len(got), 1, got)
        self.assertNotIn("non-seat identities", got[0])

    def test_an_unrecognised_directory_is_not_a_non_seat_and_still_blocks(self):
        """R1 admits the enumerated non-seats. It legalises nothing else.

        A workspace carrying some other extra `memory/` directory is still a
        profile mismatch — this is the boundary of what the change does, held
        by a test so it cannot quietly widen.
        """
        extra = "heartbeats"
        self.assertNotIn(extra, cc.NON_SEAT_IDENTITIES)
        got = _profile_blockers(self.PROFILE, self.SEATS | {extra})
        self.assertEqual(len(got), 1, got)
        self.assertNotIn("non-seat identities", got[0])
        # ⛔ POSITIVE assertion on the REMAINDER, not just the note's absence.
        # An unrecognised directory survives the subtraction, so it is named
        # in the mismatch — but it is NOT a seat, and the message must not
        # call it one. Asserting only that the note is absent would let the
        # remainder be mislabelled silently, which is how the noun defect
        # this test now pins against survived its own round.
        self.assertIn(f"memory/ has {sorted(self.SEATS | {extra})}", got[0])
        self.assertNotIn("has seats", got[0])



# ---------------------------------------------------------------------------
# NON_ROLE_DIRS — the declared exclusion, and the guard that PREVENTS
# ---------------------------------------------------------------------------

def _declare_non_role(dest, value):
    """Write a NON_ROLE_DIRS row into the stamped BINDINGS slot table."""
    b = dest / "BINDINGS.md"
    t = b.read_text(encoding="utf-8")
    t = re.sub(r"\n\| NON_ROLE_DIRS \|[^\n]*\n", "\n", t)
    if value is not None:
        t = t.replace("| SIDE_NAMES |",
                      f"| NON_ROLE_DIRS | {value} |\n| SIDE_NAMES |", 1)
    b.write_text(t, encoding="utf-8", newline="")


def _by_sev(out, sev):
    """Every finding at exactly this severity, message-only.

    Severity is read from the printed `[SEV]` tag rather than inferred from the exit code:
    an exit code is a property of the WHOLE run and any unrelated finding can produce it,
    so a test that reads one cannot attribute it to the thing under test.
    """
    tag = f"[{sev}]"
    return [l.split(tag, 1)[1].strip() for l in out.splitlines() if tag in l]


def _refused(name):
    return (f"NON_ROLE_DIRS declares '{name}', which the role vocabulary defines — the "
            "declaration was REFUSED and the name is still inferred; remove it "
            "from the row")


CANONICAL_REFUSED = _refused("builder")
# A NON-SEAT identity is refused on the same footing as a canonical role: the
# guard keys on LOCK_VOCABULARY, which is CANONICAL_ROLES + NON_SEAT_IDENTITIES.
NON_SEAT_REFUSED = _refused("creator")


class NonRoleDirsTest(unittest.TestCase):
    """The exclusion is DECLARED, never inferred, and any name in LOCK_VOCABULARY is REFUSED.

    LOCK_VOCABULARY is the identity vocabulary, not the role list: it is every canonical role
    PLUS every checked non-seat identity. `creator` is the case that separates the two — it is
    not a role, so a guard keyed to roles would let it through, and it is exactly the identity
    whose exemption from its own checker this guard exists to prevent.

    Every test here asserts the BLOCKER SET EXACTLY, in a workspace built to contain no other
    cause of a blocker. That is deliberate and it is the whole point: an assertion like
    `assertNotEqual(code, 0)` names the right outcome and is satisfied by any unrelated
    finding, so it cannot tell you the guard under test did anything. Exact-set equality on a
    clean workspace can only pass for one reason.
    """

    def _ws(self, d):
        dest = Path(d) / "ws"
        self.assertEqual(_stamp(dest, []), 0)
        (dest / "memory" / "heartbeats").mkdir()   # a real non-role directory
        return dest

    def test_undeclared_dir_still_blocks(self):
        # The property that makes "declared, never inferred" worth having: nothing is skipped
        # for merely LOOKING like runtime state.
        with tempfile.TemporaryDirectory() as d:
            dest = self._ws(d)
            code, out = _conformance(dest)
            self.assertNotEqual(code, 0)
            self.assertIn("missing required file: memory/heartbeats/MEMORY.md",
                          "\n".join(_by_sev(out, "BLOCKER")))

    def test_declared_dir_is_excluded_and_workspace_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            dest = self._ws(d)
            _declare_non_role(dest, "heartbeats")
            code, out = _conformance(dest)
            self.assertEqual([], _by_sev(out, "BLOCKER"))
            self.assertEqual(0, code)
            self.assertIn("excluded by NON_ROLE_DIRS: heartbeats", out)

    def test_canonical_role_is_REFUSED_and_still_inferred(self):
        """THE MAJOR-5 CURE, asserted on both halves.

        Reporting a canonical-role declaration while still applying the exclusion is an alarm
        without a prevention — strictly worse than no guard, because the operator sees a
        complaint and the role vanishes anyway. So this asserts the blocker AND that the role
        survived inference; either half alone would pass over the defect.
        """
        with tempfile.TemporaryDirectory() as d:
            dest = self._ws(d)
            _declare_non_role(dest, "heartbeats, builder")
            code, out = _conformance(dest)
            # ATTRIBUTION: exactly one blocker, and it is this one. Any other cause of a red
            # in this workspace breaks the equality rather than hiding inside it.
            self.assertEqual([CANONICAL_REFUSED], _by_sev(out, "BLOCKER"))
            self.assertNotEqual(code, 0)
            # PREVENTION: the role is still in the inferred set, and the report says so.
            self.assertIn("'builder'", out.splitlines()[0])
            self.assertIn("REFUSED (in the role vocabulary, still inferred): builder", out)

    def test_each_refusal_names_ITS_OWN_role(self):
        """Two refusals in one run, asserted as an exact ordered list.

        A single-refusal fixture cannot tell a message built from the role being iterated
        from a message built from some other member of the declared set — with one canonical
        name in play the two are the same string. Declaring two makes the identity of each
        message load-bearing: any substitution that decouples the printed name from the name
        under refusal collapses both messages onto one and breaks the list.
        """
        with tempfile.TemporaryDirectory() as d:
            dest = self._ws(d)
            _declare_non_role(dest, "heartbeats, builder, owner")
            code, out = _conformance(dest)
            self.assertEqual([_refused("builder"), _refused("owner")],
                             _by_sev(out, "BLOCKER"))
            self.assertNotEqual(code, 0)
            for role in ("builder", "owner"):
                self.assertIn(f"'{role}'", out.splitlines()[0],
                              f"{role} was excluded despite being refused")

    def test_refusal_is_a_property_of_the_applied_set_not_the_message(self):
        """The prevention is measured at the function that computes the applied exclusions,
        not by reading the sentence the tool prints about itself."""
        self.assertEqual({"heartbeats"},
                         cc.effective_exclusions({"heartbeats", "builder", "owner"}))
        self.assertEqual(set(), cc.effective_exclusions(set(cc.CANONICAL_ROLES)))
        # ⛔ THE RE-KEY, measured at the function rather than at the message:
        # the refusal keys on LOCK_VOCABULARY, so NOTHING the vocabulary defines
        # can be excluded — non-seat identities included.
        self.assertEqual(set(), cc.effective_exclusions(set(cc.LOCK_VOCABULARY)))

    def test_a_NON_SEAT_identity_is_refused_exactly_like_a_canonical_role(self):
        """⛔ The reason the guard keys on LOCK_VOCABULARY and not CANONICAL_ROLES.

        `creator` is not a canonical role, so a CANONICAL_ROLES-keyed guard would
        ADMIT `NON_ROLE_DIRS: creator` — and admitting it would drop `memory/creator/`
        out of role inference and therefore out of `check_structure`'s artifact
        requirements. That would let the workspace under test exempt a checked
        identity from its own checker, decided from inside the file being checked.
        The exemption must not be reachable from a binding slot at all.
        """
        self.assertNotIn("creator", cc.CANONICAL_ROLES)      # not a role …
        self.assertIn("creator", cc.NON_SEAT_IDENTITIES)     # … but an identity
        self.assertIn("creator", cc.LOCK_VOCABULARY)         # … the vocabulary defines
        # Not excluded, and the refusal names ITS OWN name, not some other member.
        self.assertEqual(set(), cc.effective_exclusions({"creator"}))
        self.assertEqual({"heartbeats"},
                         cc.effective_exclusions({"heartbeats", "creator"}))
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "ws"
            _stamp(dest, [])
            (dest / "memory" / "creator").mkdir()
            _declare_non_role(dest, "creator")
            code, out = _conformance(dest)
            self.assertEqual(1, code)
            self.assertIn(NON_SEAT_REFUSED, _by_sev(out, "BLOCKER"))
            self.assertIn(
                "REFUSED (in the role vocabulary, still inferred): creator", out)

    def test_stale_declaration_warns_and_does_not_block(self):
        with tempfile.TemporaryDirectory() as d:
            dest = self._ws(d)
            _declare_non_role(dest, "heartbeats, nonexistent-dir")
            code, out = _conformance(dest)
            self.assertEqual([], _by_sev(out, "BLOCKER"))
            self.assertTrue(any("nonexistent-dir" in m and "stale exclusion" in m
                                for m in _by_sev(out, "WARN")))

    def test_absent_and_placeholder_declarations_mean_nothing_declared(self):
        # The HINTED forms are the ones that matter: both placeholders are documented as
        # accepting `{{FILL: hint}}`, so a literal-string comparison would parse a hinted
        # placeholder into directory names and exclude them.
        for value in ("{{FILL}}", "{{DEFERRED}}", "  ",
                      "{{FILL: which dirs are not roles}}", "{{DEFERRED: pending audit}}"):
            self.assertEqual(set(), cc.declared_non_role_dirs({"NON_ROLE_DIRS": value}),
                             f"value {value!r} should declare nothing")
        self.assertEqual(set(), cc.declared_non_role_dirs({}))
        self.assertEqual(set(), cc.declared_non_role_dirs(None))

    def test_no_sentinel_value_is_silently_swallowed(self):
        """`none` is a directory name, not a magic word.

        An undocumented sentinel list is a place for a declaration to disappear quietly; the
        only values that mean "nothing declared" are the ones the file already documents.
        """
        for value in ("none", "n/a", "-"):
            self.assertEqual({value}, cc.declared_non_role_dirs({"NON_ROLE_DIRS": value}),
                             f"{value!r} should be read as a directory name")

    def test_separator_forms_parse_equivalently(self):
        for value in ("a, b", "a,b", "a b", " a ,  b ", "a,,b"):
            self.assertEqual({"a", "b"}, cc.declared_non_role_dirs({"NON_ROLE_DIRS": value}),
                             f"value {value!r}")

    def test_default_stamp_declares_nothing_and_is_unaffected(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "ws"
            self.assertEqual(_stamp(dest, []), 0)
            code, out = _conformance(dest)
            self.assertEqual(0, code)
            self.assertNotIn("NON_ROLE_DIRS", out)


if __name__ == "__main__":
    unittest.main()
