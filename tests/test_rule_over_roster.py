#!/usr/bin/env python3
"""Arms for the rule-over-roster rewrite of migrate_workspace.py.

    python -m unittest discover -s tests

⛔ THE DEFECT THESE ARMS EXIST FOR. Two hand-written version rosters stood in
migrate_workspace.py -- one in the module docstring, one above the advisory slot list.
They disagreed on their lower bound ("v2.9, v3.0, v3.1 and v3.2 introduce NO new slots"
against "None of v2.8, v2.9, v3.0, v3.1 or v3.2 introduces new binding slots"). The
disagreement was the SYMPTOM. Measured against CHANGELOG.md, BOTH were false, and false on
the version they SHARE: release 1.7.0, stamp v2.9, introduced NON_ROLE_DIRS.

And the false claim was load-bearing, not decorative -- it is the sentence that licensed
omitting NON_ROLE_DIRS from the advisory list, so a workspace migrating from v2.5 through
v2.8 was never told the slot existed, while conformance BLOCKS on the undeclared directory
the slot is the declared cure for. A roster goes stale in the direction that SUPPRESSES
advice, and reads correctly while doing so.

RED-BY-DESIGN against the pre-rewrite module:
`test_the_advisory_list_offers_NON_ROLE_DIRS` (the operational defect) and both legs of
`NoRosterMayReturnTest` (the prose that hid it -- measured at 8 enumeration findings on
pre-rewrite main). `test_no_sentence_in_the_module_enumerates_versions` is additionally
red against this branch's OWN first commit, on a prose hop ladder in `migrate`'s
docstring that the r1 review did not name.

PROVENANCE OF THAT LADDER, corrected here because an earlier commit message on this
branch got it wrong. The ladder was NOT introduced by this branch. It entered the
module at `f2a69d1` (the v1.4.0 commit that restored the earliest hop) naming three
versions, and it grew to its eight-version form at `440aed1`, the restamp commit.
This branch's first commit touched no rung of it: its diff contains no ladder line
and the eight-version text is already byte-identical in its parent. The leg is red
there because the ladder was ALREADY PRESENT -- which is a finding about DETECTION,
not about authorship, and the two are easy to collapse when the detector first fires
on the commit you happen to be standing on.
"""
import ast
import contextlib
import importlib.util
import io
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tools" / "migrate_workspace.py"


def _load():
    spec = importlib.util.spec_from_file_location("migrate_workspace", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mw = _load()


class HopTableIsDerivedTest(unittest.TestCase):

    def test_hop_table_covers_every_pin_in_HOPS_and_nothing_else(self):
        starts = [mw.HOPS[0][0]] + [to for _f, to in mw.HOPS]
        rows = mw.hop_table()
        self.assertEqual(len(starts), len(rows))
        for v, row in zip(starts, rows):
            self.assertIn(f"pinned {v}", row)

    def test_the_rule_REPRODUCES_the_roster_it_replaced(self):
        """⭐ Equivalence, not merely self-consistency.

        A derived table that agrees with itself proves nothing about whether the
        replacement changed behaviour. These counts are transcribed from the hand-written
        docstring roster as it stood BEFORE the rewrite, so this arm compares the rule
        against the artifact it removed [[deploy-must-contain-what-it-replaces]]."""
        expected_hop_counts = {
            "v2.5": 7, "v2.6": 6, "v2.7": 5, "v2.8": 4,
            "v2.9": 3, "v3.0": 2, "v3.1": 1,
        }
        # ⛔ GRADED AGAINST THE FROZEN LADDER, NOT THE LIVE ONE (codex R-5 / opus R-4).
        # These seven counts are a TRANSCRIPTION of the roster as it stood at v3.2.
        # Read against the live `hop_table()` they went stale the moment HOPS grew: a
        # stamp bump shifts ALL SEVEN at once (v2.5 -> 8 hops, and v3.2 stops being the
        # no-op), and the natural repair is to re-hand-write the seven numbers -- which
        # is precisely the hand-written roster this branch exists to abolish, surviving
        # inside the branch's own test file. Measured, not predicted: appending one hop
        # reds this arm on 7 of 7 rows.
        #
        # Freezing the INPUT does not weaken the claim, because the claim was never
        # about the live ladder: it is that the RULE reproduces the ARTIFACT IT REMOVED,
        # and that artifact described the v3.2 ladder. `_rows_at_v32` carries the prefix
        # control, and a real behavioural change in `hop_table` still reds here.
        rows = {r.split()[1]: r for r in self._rows_at_v32()}
        for v, n in expected_hop_counts.items():
            self.assertIn(f"{n} hop(s)", rows[v],
                          f"pinned {v} should walk {n} hops, per the roster this rule "
                          f"replaced; got: {rows[v]}")
        # the FROZEN ladder's newest pin -- `mw.NEWEST` tracks the live ladder and would
        # KeyError against these frozen rows the first time a hop is appended.
        self.assertIn("no-op", rows[self.HOPS_AT_V32[-1][1]],
                      "the newest pin was a no-op in the roster and must stay one")

    def test_the_equivalence_anchor_SURVIVES_a_stamp_bump(self):
        """⭐ codex R-5 / opus R-4 — the regression guard for that cure.

        ⛔ THE DEFECT IS INVISIBLE ON TODAY'S LADDER, which is why it needs an arm and
        not a comment. Until r5 the anchor above graded its seven frozen counts against
        the LIVE `hop_table()`. On today's HOPS the live and frozen ladders are the same
        object, so the bug shows nothing; append ONE rung -- what the next restamp does
        -- and all seven rows red at once, and the natural repair is to re-hand-write the
        seven numbers. That is the hand-written roster this branch exists to abolish,
        surviving inside the branch's own test file.

        So this arm supplies the bump. Anyone who "simplifies" `self._rows_at_v32()` back
        to `mw.hop_table()` reds HERE instead of shipping a trap that detonates on
        whoever does the next restamp.

        RED-CAPABLE, shown not asserted: against the pre-r5 anchor this arm fails on
        7 of 7 rows (creator r5 record, LEG 1).

        ⚠ opus R-6: mutates a module global process-wide, like the other drive arms in
        this file. Safe under the sequential runner this workflow uses. Disclosed.
        """
        saved = mw.HOPS
        try:
            mw.HOPS = mw.HOPS + ((mw.HOPS[-1][1], "v99.9"),)
            # the arm above, re-run against a ladder that has grown a rung.
            self.test_the_rule_REPRODUCES_the_roster_it_replaced()
        finally:
            mw.HOPS = saved

    # HOPS as it stood at v3.2, frozen. This is the ladder EVERY frozen-fixture arm in
    # this class is read off, so those fixtures are anchored to a real state rather than
    # to whatever HOPS happens to be when the arm next runs [[measurement-freeze]].
    HOPS_AT_V32 = (("v2.5", "v2.6"), ("v2.6", "v2.7"), ("v2.7", "v2.8"),
                   ("v2.8", "v2.9"), ("v2.9", "v3.0"), ("v3.0", "v3.1"),
                   ("v3.1", "v3.2"))
    ROWS_AT_V32 = [
        "pinned v2.5  ->  7 hop(s): v2.5 -> v2.6 -> v2.7 -> v2.8 -> v2.9 -> v3.0 -> v3.1 -> v3.2",
        "pinned v2.6  ->  6 hop(s): v2.6 -> v2.7 -> v2.8 -> v2.9 -> v3.0 -> v3.1 -> v3.2",
        "pinned v2.7  ->  5 hop(s): v2.7 -> v2.8 -> v2.9 -> v3.0 -> v3.1 -> v3.2",
        "pinned v2.8  ->  4 hop(s): v2.8 -> v2.9 -> v3.0 -> v3.1 -> v3.2",
        "pinned v2.9  ->  3 hop(s): v2.9 -> v3.0 -> v3.1 -> v3.2",
        "pinned v3.0  ->  2 hop(s): v3.0 -> v3.1 -> v3.2",
        "pinned v3.1  ->  1 hop(s): v3.1 -> v3.2",
        "pinned v3.2  ->  no-op, exit 0 (already newest)",
    ]

    def _rows_at_v32(self):
        """`hop_table()` rendered against the FROZEN v3.2 ladder.

        ⛔ THE PREFIX ASSERTION IS THE CONTROL THAT KEEPS THE FREEZE HONEST, and it is
        the whole reason freezing is not just switching the arm off. An EXTENSION -- a
        hop appended by the next restamp -- leaves the prefix intact and is expected. A
        REWRITE of an existing rung reds HERE and says the frozen rows describe a ladder
        this repository no longer has [[anchor-validity-discipline]]. Without it, a
        frozen input would buy every arm below permanent immunity.

        ⚠ opus R-6, named at its one site. Substituting a module global is
        process-wide and is safe only under the sequential runner this workflow uses.
        Both frozen-fixture arms need the substitution, so it lives here ONCE rather
        than being copy-pasted into each -- this file carries one instance of R-6, not
        two. Disclosed, not silently matched.
        """
        live = list(mw.HOPS)
        self.assertEqual(list(self.HOPS_AT_V32), live[:len(self.HOPS_AT_V32)],
                         "the frozen v3.2 ladder is no longer a prefix of HOPS -- an "
                         "existing rung was rewritten, so the frozen rows describe a "
                         "ladder that no longer exists; re-derive them, do not edit "
                         "them to match")
        saved = mw.HOPS
        try:
            mw.HOPS = self.HOPS_AT_V32
            return mw.hop_table()
        finally:
            mw.HOPS = saved

    def test_the_displayed_ROUTE_is_pinned_and_not_just_its_length(self):
        """⭐ codex r2 R-8 / opus r2 R-8. The other hop arms assert the PIN and the hop
        COUNT and never read the route, which is the string an operator actually
        follows. It is pinned here byte-for-byte against a frozen ladder.

        ⛔ THE GAP IS NARROWER THAN IT LOOKS, and it was measured rather than assumed.
        Permuting HOPS does NOT reach it: `hop_table` derives the counts and the route
        from the same `starts` sequence, so a permuted ladder moves the counts too and
        `test_the_rule_REPRODUCES_the_roster_it_replaced` -- which keys expected counts
        BY PIN NAME -- already reds. What passes every pre-r3 arm is a RENDERING
        mutation: joining the route backwards leaves the pin and the count untouched and
        prints `v2.5 -> v3.2 -> v3.1 -> ... -> v2.6`, a route that is exactly wrong and
        entirely unread. That is what this arm is for, and saying so keeps the next
        reader from testing the mutation that was already covered.

        The frozen ladder is asserted to be a PREFIX of the live HOPS -- see
        `_rows_at_v32`, which both frozen-fixture arms share. That is the control that
        keeps this fixture honest as the protocol grows."""
        self.assertEqual(self.ROWS_AT_V32, self._rows_at_v32(),
                         "the rendered hop table changed shape or route")

    def test_hop_chain_and_hop_table_cannot_disagree(self):
        """Two readers of HOPS is two chances to be wrong. They are compared, not trusted."""
        for row in mw.hop_table():
            pin = row.split()[1]
            chain = mw._hop_chain(pin)
            if "no-op" in row:
                self.assertEqual([], chain)
            else:
                self.assertEqual(f"{len(chain)} hop(s)", re.search(r"\d+ hop\(s\)", row).group(0))


class SlotTableIsTheSourceOfTruthTest(unittest.TestCase):

    def test_the_advisory_list_offers_NON_ROLE_DIRS(self):
        """⭐ RED-BY-DESIGN against the pre-rewrite module, where this slot was absent.

        This is the operational defect, as distinct from the stale prose that hid it: a
        workspace pinned below v2.9 was never advised of a slot that conformance blocks
        for the lack of."""
        names = [n for n, _note, _ap in mw.ADVISORY_SLOTS]
        self.assertIn("NON_ROLE_DIRS", names)

    def test_every_table_slot_is_offered_and_every_offered_slot_is_in_the_table(self):
        """Both directions. A one-way check passes while the two structures drift apart,
        and set reconciliation is only sound in both [[counts-and-relations-discipline]]."""
        table = set(mw.SLOT_INTRODUCED_IN)
        offered = {n for n, _note, _ap in mw.ADVISORY_SLOTS}
        self.assertEqual(set(), table - offered,
                         f"in the table, never offered: {sorted(table - offered)}")
        self.assertEqual(set(), offered - table,
                         f"offered, but no introducing version recorded: "
                         f"{sorted(offered - table)}")

    def test_newest_slot_version_is_derived_and_matches_the_table(self):
        self.assertEqual("v2.9", mw.newest_slot_version(),
                         "NON_ROLE_DIRS arrived at v2.9 per CHANGELOG.md release 1.7.0")

    def test_slot_version_ordering_is_POSITIONAL_not_lexical(self):
        """A two-digit minor sorts wrong as a string: 'v2.10' < 'v2.9'. The ordering must
        not depend on the scheme not having reached two digits yet -- that is a control
        pinned to a value that will change [[anchor-validity-discipline]]."""
        self.assertLess("v2.10", "v2.9", "premise of this arm: lexical order is wrong here")
        saved = dict(mw.SLOT_INTRODUCED_IN)
        saved_hops = mw.HOPS
        try:
            mw.HOPS = mw.HOPS + (("v3.2", "v2.10"),)
            mw.SLOT_INTRODUCED_IN["SYNTHETIC"] = "v2.10"
            self.assertEqual("v2.10", mw.newest_slot_version(),
                             "a positional ordering must pick the LATEST hop, not the "
                             "lexically greatest string")
        finally:
            mw.SLOT_INTRODUCED_IN.clear()
            mw.SLOT_INTRODUCED_IN.update(saved)
            mw.HOPS = saved_hops

    def test_slots_introduced_since_is_a_function_of_the_pin(self):
        """It was previously stated as a CONSTANT, which is the roster's whole error in
        one word: what a migrating workspace has not been told depends on its pin."""
        self.assertEqual(["NON_ROLE_DIRS"], mw.slots_introduced_since("v2.8"))
        self.assertEqual([], mw.slots_introduced_since("v2.9"))
        self.assertEqual([], mw.slots_introduced_since(mw.NEWEST))
        self.assertIn("TRANSPORT", mw.slots_introduced_since("v2.5"))
        self.assertEqual([], mw.slots_introduced_since("v9.9"),
                         "an unknown pin yields nothing rather than raising")


class TheHeadingIsGRADED_AS_RENDEREDTest(unittest.TestCase):
    """⭐ r3 / codex R-5 + R-6, opus R-6. The heading is what an OPERATOR reads, and
    until now nothing asserted the bytes it prints -- the arms graded the derivations
    that feed it. A derivation can be right in every part while the sentence assembled
    from them says something false, which is exactly what R-5 is
    [[collected-is-not-reported]].

    ⛔ THE DEFECT. `slots_introduced_since` is strictly-after and MUST STAY SO -- the
    arms pin `slots_introduced_since("v2.9") == []`, and widening `>` to `>=` would tell
    a workspace genuinely at v2.9-with-the-slot that the slot is new to it. The problem
    is one layer up: a PROTOCOL stamp is shared by every release carrying it, and
    NON_ROLE_DIRS arrived in release 1.7.0 partway through v2.9. So a v2.9-pinned
    workspace sits on one side or the other and THE PIN CANNOT SAY WHICH. r2 printed
    "all predate this workspace's v2.9 pin" -- and then, in the same sentence, named
    NON_ROLE_DIRS as required. One printed line, two claims, contradicting each other.
    """

    @staticmethod
    def _render(pin, slots):
        """The real function's real stdout. No re-implementation of the heading here:
        a fixture that rebuilds the sentence grades the fixture."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mw.print_manual_steps(Path("."), dict(slots), {"owner": Path(".")},
                                  pinned_from=pin)
        return buf.getvalue()

    BASE = {"PROTOCOL_VERSION": "v3.2", "TRANSPORT": "local-fs",
            "AUTONOMY": "attended", "PROXY_AUTH": "OFF"}

    def test_a_pin_SHARING_the_introducing_stamp_gets_conservative_wording(self):
        """The row R-5 names. `v2.9` is NON_ROLE_DIRS's own stamp."""
        pin = mw.SLOT_INTRODUCED_IN["NON_ROLE_DIRS"]
        out = self._render(pin, self.BASE)
        self.assertNotIn(f"all predate this workspace's {pin} pin", out,
                         "the heading told an operator every missing slot predates a "
                         "pin that SHARES a stamp with the release introducing one of "
                         "them -- a false chronology, and one the same line then "
                         "contradicts")
        self.assertIn(f"NON_ROLE_DIRS arrived DURING {pin}", out,
                      "the shared-stamp case must be stated, not omitted: an operator "
                      "who cannot decide from the pin has to be told that")
        self.assertIn("cannot say whether this workspace predates it", out)

    def test_a_pin_BELOW_the_introducing_stamp_still_says_it_arrived_after(self):
        """The control. If the conservative wording swallowed every case, the arm above
        would pass on a heading that had simply stopped making claims
        [[instrument-polarity-controls]]."""
        out = self._render("v2.8", self.BASE)
        self.assertIn("arrived after this workspace's v2.8 pin", out)
        self.assertIn("NON_ROLE_DIRS", out)
        self.assertNotIn("arrived DURING v2.8", out,
                         "v2.8 does not share a stamp with any slot's introduction")

    def test_the_heading_does_not_HAND_NAME_a_slot_or_its_condition(self):
        """⛔ r3 / codex R-5, second half. The heading used to say `NON_ROLE_DIRS is
        REQUIRED once memory/ holds a non-role directory` -- a roster of one, in the
        heading of the list whose rows already carry that. It is the same artifact this
        branch removed everywhere else, one layer down, and it is what made the false
        chronology self-contradicting instead of merely wrong.

        The rule may be stated; the SLOT may not be named by the heading. The row still
        must carry it, which is the other half of the assertion."""
        out = self._render("v2.9", self.BASE)
        heading = next(l for l in out.splitlines()
                       if l.startswith("2. Binding slots not yet present"))
        self.assertNotIn("REQUIRED once memory/", heading,
                         "the heading hand-writes one slot's condition")
        self.assertIn("a conditional row is REQUIRED once its condition holds", heading,
                      "the rule that replaced the hand-written clause is gone too, so "
                      "an operator is no longer told conditional rows can be required")
        self.assertIn("conformance BLOCKS", out,
                      "the condition survives on NON_ROLE_DIRS's own row -- if it does "
                      "not, removing it from the heading LOST it")

    def test_pinned_from_has_no_default_because_the_branch_it_fed_was_DEAD(self):
        """⭐ opus r2 R-6. Every early status returns before `print_manual_steps`, and
        the surviving path always passes the pin that just cleared SUPPORTED_FROM -- so
        the `pinned_from`-falsy heading could not render on any run. It was a fourth
        wording of the same fact, unreachable and therefore never graded.

        Deleting the branch alone would have left the default, and a caller with no pin
        would then silently select whichever wording remained. The parameter is
        required, so that caller reds at the call instead."""
        import inspect
        sig = inspect.signature(mw.print_manual_steps)
        self.assertIs(inspect.Parameter.empty,
                      sig.parameters["pinned_from"].default,
                      "pinned_from has a default again -- a caller with no pin will "
                      "select wording no arm grades")
        with self.assertRaises(TypeError):
            mw.print_manual_steps(Path("."), {}, {})


class TheCLIContractIsDRIVENTest(unittest.TestCase):
    """⭐ codex r2 R-7 / opus r2 R-7. The `--hops` route and the relocated
    missing-workspace error were evidenced by HAND RUNS. A hand run is a claim about a
    past invocation; it grades nothing on the next commit
    [[completion-claims-need-an-instrument]]. These arms drive `main()` itself.

    ⛔ The relocation is the risky half. `--workspace` stopped being argparse-required
    so `--hops` could run without one, and the requirement moved into an explicit check.
    A move like that is silent when it fails: the flag simply becomes optional, every
    other arm still passes, and the tool starts accepting an invocation it used to
    refuse. So the arm asserts the EXIT CODE and the STREAM, not just that it complains.
    """

    @staticmethod
    def _run(argv):
        """(exit code or SystemExit code, stdout, stderr) from the real `main()`."""
        out, err = io.StringIO(), io.StringIO()
        saved = sys.argv
        try:
            sys.argv = ["migrate_workspace.py"] + argv
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = mw.main()
                except SystemExit as e:                 # argparse exits, it does not return
                    code = e.code
        finally:
            sys.argv = saved
        return code, out.getvalue(), err.getvalue()

    def test_hops_needs_no_workspace_and_prints_the_derived_ladder(self):
        code, out, err = self._run(["--hops"])
        self.assertEqual(0, code, f"--hops did not exit 0; stderr: {err}")
        self.assertEqual(mw.hop_table(), [l.strip() for l in out.splitlines()
                                          if l.strip().startswith("pinned ")],
                         "--hops printed something other than the derived hop table")
        self.assertIn(f"newest introduced at: {mw.newest_slot_version()}", out,
                      "the advisory line is derived from the slot table and must "
                      "track it")

    def test_a_missing_workspace_still_exits_2_with_usage_on_STDERR(self):
        """The behaviour the relocation had to preserve. argparse's own
        `--workspace`-required error was exit 2 with usage on stderr; the explicit
        check must be indistinguishable to a caller that is not --hops."""
        code, out, err = self._run([])
        self.assertEqual(2, code,
                         "a bare invocation no longer exits 2 -- the requirement moved "
                         "out of argparse and was not replaced")
        self.assertIn("usage:", err, "usage no longer reaches stderr")
        self.assertIn("--workspace is required", err)
        self.assertEqual("", out, "the error leaked onto stdout")

    def test_the_two_failure_CODES_mean_different_things_and_stay_apart(self):
        """⛔ READ OFF THE TOOL, not off an expectation. The first draft of this arm
        asserted 1 for a bad `--workspace` because that felt like "the tool ran and the
        target was unusable" -- and it reded. The contract the code actually keeps is
        the argparse one: **2 = this invocation cannot proceed** (no `--workspace`, or a
        path that is not a directory -- both decided before anything is read), **1 = the
        tool ran and REFUSED the workspace** (unsupported pin, or an error status). A
        test that encoded my expectation would have been a contract this branch
        invented [[tests-must-not-create-the-contract]].

        Both sides are asserted, because an arm that pins only one of two codes passes
        just as well after they collapse into each other -- and a scripted caller that
        cannot tell a typo from a refusal is exactly what that collapse costs."""
        code, _out, err = self._run(["--workspace", "no_such_workspace_dir_xyz"])
        self.assertEqual(2, code, "a non-directory --workspace is an invocation "
                                  "failure and shares argparse's code")
        self.assertIn("is not a directory", err)

        ws = Path(__file__).resolve().parent.parent   # a real dir with no pin at all
        code, _out, err = self._run(["--workspace", str(ws)])
        self.assertEqual(1, code,
                         "a workspace the tool RAN against and refused must not share "
                         "the invocation-failure code")

    def test_the_UNSUPPORTED_pin_is_REFUSED_and_the_refusal_TEACHES(self):
        """⛔ r4 / opus R-3. The arm above pins both CODES, and that was read as pinning
        both PATHS. It is not: a real directory with no BINDINGS.md returns
        `status == "error"`, so `unsupported` -- the branch a user with a genuine but
        unmigratable workspace actually hits -- was never executed by any arm. Two
        branches returning the same code are indistinguishable by code alone, so the
        code assertion cannot separate them [[green-coverage-discipline]].

        A pinned workspace is therefore BUILT, with a stamp the hop ladder does not
        start from, and the refusal is graded on its TEXT as well as its code. The
        message is a contract in its own right: the tool's own docstring says a refused
        user must learn from the refusal what a migratable pin looks like, without
        reading the source. A silent 1 keeps the code green while deleting that.

        CONTROL: the pin is asserted to be genuinely off the ladder before the run, so a
        future stamp bump that makes it supported reds here and names itself, instead of
        quietly turning this arm into a second copy of the `already` case."""
        import tempfile
        off_ladder = "v1.0"
        self.assertNotIn(off_ladder, mw.SUPPORTED_FROM,
                         "premise of this arm: the pin it builds is not a supported "
                         "starting version -- if the ladder grew down to it, this arm "
                         "is now testing the migrating path and must be re-derived")
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "BINDINGS.md").write_text(
                "| slot | value |\n"
                "|---|---|\n"
                f"| PROTOCOL_VERSION | {off_ladder} |\n",
                encoding="utf-8")
            self.assertEqual(off_ladder, mw.cc.pinned_version(mw.cc.parse_bindings(ws)),
                             "premise: the built workspace parses to the pin this arm "
                             "intends, so the refusal below is about the PIN")
            code, _out, err = self._run(["--workspace", str(ws)])
        self.assertEqual(1, code,
                         "a workspace the tool READ and refused for its pin must share "
                         "the refusal code, not the invocation-failure code")
        self.assertIn(off_ladder, err,
                      "the refusal does not quote the pin it refused, so a user cannot "
                      "tell which of several workspaces was rejected")
        for supported in mw.SUPPORTED_FROM:
            self.assertIn(supported, err,
                          f"the refusal omits the supported starting version "
                          f"{supported} -- it refuses without teaching, which is the "
                          f"message contract this branch's own tool docstring states")
        self.assertIn(mw.NEWEST, err,
                      "the refusal does not name the version a migration would reach")

    def test_the_retained_alias_is_the_SAME_OBJECT_not_a_copy(self):
        """codex r2 R-9. `NEW_V26_SLOTS` is kept as an alias of `ADVISORY_SLOTS`, and
        its docstring says a name stating a version it no longer means is the same
        defect one layer down. An alias that silently became a COPY would drift exactly
        as the two rosters did -- identity is the assertion, because equality would
        still pass on the day of the split."""
        self.assertIs(mw.ADVISORY_SLOTS, mw.NEW_V26_SLOTS,
                      "the alias is a copy, not the same list -- it can now disagree "
                      "with the table it is named after")


class NoRosterMayReturnTest(unittest.TestCase):
    """The durable half of the cure. Fixing today's rosters fixes today; these arms are
    what stop the next stamp bump from hand-writing another one that disagrees again.

    ⛔ WHY THIS CLASS WAS REWRITTEN (r2). The r1 guard was a single regex anchored on a
    TRIGGER PHRASE and matching only FORWARD from it. Both rosters it was written for
    were checked -- and it saw one of them by coincidence. The docstring roster writes
    its versions BEFORE its trigger:

        "... v2.9, v3.0, v3.1 and v3.2 introduce NO new slots; the v2.6 slot ..."

    so all four versions the claim is false about sat outside every match, and the only
    graded version was the incidental `v2.6` in the TRAILING clause. Delete that trailing
    text and the guard reported NOTHING on a false claim. Worse, the no-op control passed
    -- because it planted the sentence WITH its trailing text, so the control measured the
    coincidence too [[instrument-must-prove-it-fired]]. A control built from the same
    assumption as the instrument inherits its blindness.

    Two independent legs now, deliberately different in KIND, because one leg's blind
    spot must not be the other's:

      LEG 1 -- ENUMERATION BY COUNT, blind to phrasing. No logical sentence in the module
      may name 3+ distinct versions. A sentence that names eight versions IS a roster
      whatever it claims about them, so this leg needs no trigger phrase, has no
      direction, and fires on wordings nobody predicted. Measured: 0 findings on the
      fixed module, 1 on this branch's own first commit (a prose hop ladder in
      `migrate`'s docstring that BOTH r1 reviewers missed and this leg found -- the leg
      DETECTED it there; the ladder was already present and this branch did not write
      it, see the module docstring's provenance paragraph), 8 on pre-rewrite main --
      including both original rosters, which is the case r1 could only half-see.

      LEG 2 -- THE CLAIM, in both directions, capturing the claim's OWN version list.
      Only versions inside the list the claim quantifies over are graded, which is also
      the answer to r1's second finding: a version LITERAL elsewhere in the file is no
      longer indistinguishable from a version CLAIM, because the grader never looks
      outside the captured list. Covers a false claim naming 1-2 versions, i.e. below
      leg 1's threshold.

    ⚠ RESIDUAL, stated rather than implied. Leg 1 cannot see a false claim naming only
    ONE or TWO versions. Leg 2 cannot see a phrasing outside its verb set. A false claim
    naming exactly one or two versions in a wording neither pattern anticipates passes
    both legs; the differential arms below fix the 2-version case for the wordings that
    exist today and nothing here claims more than that. Both legs scan the MODULE only --
    this test file plants version literals on purpose and is not a subject.
    """

    # ⛔ THE PERIOD-INSIDE-A-VERSION HAZARD, and where it MEASURABLY lives in r2.
    #
    # r1's pattern used a bare `[^.\n]` to stop at a sentence boundary -- which also
    # stopped it at the period INSIDE a version token, so the scan saw "the v2" and never
    # a complete `vN.N`. The guard could not fire at all and reported green on the very
    # sentence it was written to catch.
    #
    # r2 inherits that hazard in BOUNDARY, not in INNER, and the difference is measured,
    # not guessed. Swapping BOUNDARY for a naive `[.;:]` drops leg 1 from 8 findings to
    # ZERO on pre-rewrite main and from 1 to ZERO on this branch's first commit: the
    # lookarounds are what keep a sentence from ending inside `v2.9`, and without them
    # leg 1 is dead while still green. INNER's `\.(?=\d)` escape hatch, by contrast,
    # changes NOTHING on any real specimen (2 vs 2 on pre-rewrite main, 0 vs 0 on the
    # tip) -- because `LIST` matches the version tokens itself and INNER never has to
    # cross one. It is kept as defence against a shape that has not yet occurred (a claim
    # whose subject list is separated from its verb by an aside naming another version),
    # and the arm below says so rather than dressing a constructed fixture up as
    # evidence the hatch is currently earning its place.
    #
    # `test_the_period_hazard_is_still_guarded_in_BOTH_legs` drives both, from the real
    # historic bytes where real bytes exist [[instrument-must-prove-it-fired]].
    VERSION = re.compile(r"\bv\d+\.\d+\b")
    INNER = r"(?:[^.;:\n]|\.(?=\d)){0,%d}?"

    # ⛔ r3 / codex R-2. INNER excludes `.` `;` `:` but admits the DASH conventions this
    # repository actually writes, so an 80-character span walks out of its own clause and
    # picks up a verb belonging to the next one. Reproduced, verbatim:
    #
    #   "v2.9 introduced a binding slot -- v3.0 adds no new binding slots."
    #
    # Both clauses are TRUE. Leg 2 fired anyway, blaming `v2.9` -- a false positive on a
    # correct sentence, which is the failure mode that teaches an author to stop
    # believing the guard.
    #
    # ⛔⛔ AND THE CURE IS NOT "EXCLUDE THE DASH", which is what it looks like. This
    # file's own `test_the_period_hazard_is_still_guarded_in_BOTH_legs` drives INNER with
    #
    #   "v2.9 and later -- that is, everything after v2.8 -- introduce no new slots"
    #
    # and REQUIRES a hit: that is a false claim whose subject is separated from its verb
    # by an APPOSITIVE ASIDE, where crossing the dashes is correct. Excluding the
    # character silences it -- trading codex's false positive for a false negative in the
    # one arm that exists to keep INNER honest. Two specimens, same punctuation mark,
    # opposite required verdicts, so the CHARACTER cannot be the discriminator.
    #
    # ⛔⛔⛔ r4. WHAT STOOD HERE WAS PARITY -- "an even number of crossed dashes is a
    # complete aside" -- AND IT WAS WRONG. Both r3 anchors refuted it independently,
    # with sentences neither had seen the other write:
    #
    #   "v2.9 introduced a slot -- documentation changed -- v3.1 adds no new slots."
    #   "v2.9 introduced a slot -- work continued -- v3.0 adds no new binding slots."
    #
    # TWO CLAUSE BREAKS ALSO COUNT EVEN. Parity cannot tell them from one aside, because
    # counting sees no structure -- it restored codex's original false positive with one
    # extra clause. The rule now lives in `_association_holds` and asks a structural
    # question instead: did this match reach PAST a nearer subject? Read it there; the
    # discriminator is not a property of the dash and never was.
    #
    # ⚠ RESIDUAL, re-derived at r4 because the rule changed under it. The r3 residual
    # (an aside OPENING before the version list) is CURED -- it fires now, and the arm
    # that pinned it silent reded and said so, which is why residuals are pinned rather
    # than written down. What survives is a different shape: a second clause that makes
    # its claim WITHOUT naming a version --
    #   "v2.9 introduced a slot -- nothing since adds new slots"
    # -- offers no nearer subject to find, so the association stands and leg 2 blames
    # v2.9. A false POSITIVE, the direction that teaches an author to stop believing the
    # guard. It is NOT covered, and it is named here rather than left for a fifth round.
    DASH = re.compile(r"--|—")
    LIST = r"v\d+\.\d+(?:\s*(?:,|and|or|/|through|->|to|-)\s*v\d+\.\d+)*"
    ENUMERATION_THRESHOLD = 3

    # ⛔ r3 / codex R-1, WIDENED past the one word codex named. `LIST` advertises EIGHT
    # operators and the reproduction ran the same false claim (`v2.8 <op> v3.0`,
    # straddling the `v2.9` that introduced a slot) through every one of them. All eight
    # were silent; only FOUR are defects:
    #
    #   ENUMERATION  `,` `and` `or` `/`      silent and CORRECT -- they name exactly
    #                                        their members and nothing else
    #   RANGE        `through` `->` `to` `-` silent and WRONG -- each IMPLIES members it
    #                                        does not name, and the implied member is
    #                                        where the false claim hides
    #
    # That split is the cure boundary. "Fixing" the enumerations would manufacture
    # exactly the false positive the F3 arm forbids -- a guard that fires on a claim
    # naming only true things -- so they are left alone, and the arm below asserts BOTH
    # halves so a later widening of the cure reds instead of passing quietly.
    #
    # `->` is this repository's own hop-ladder arrow, so the range class is not a
    # hypothetical shape: it is the form a future author is most likely to reach for.
    #
    # A range is expanded through THE LADDER ITSELF, never through a second list of
    # versions -- the ladder is the authority these rules read, and a hand-written
    # sequence here would be a roster inside the guard, which is this file's whole
    # subject. An endpoint that is not on the ladder expands to nothing and is still
    # counted literally, so an unparseable range degrades to r2's behaviour rather than
    # to silence.
    RANGE_OPS = ("through", "->", "to", "-")
    ENUM_OPS = (",", "and", "or", "/")
    RANGE = re.compile(
        r"\bv\d+\.\d+\s*(?:\bthrough\b|->|\bto\b|-)\s*v\d+\.\d+\b", re.IGNORECASE)

    @staticmethod
    def _ladder():
        """The ordered version sequence, DERIVED from the hop table."""
        return [mw.HOPS[0][0]] + [to for _frm, to in mw.HOPS]

    @classmethod
    def _named_versions(cls, text):
        """Every version a span names -- INCLUDING the ones a range only implies.

        Returns (named, unknown): `unknown` holds range endpoints that are NOT on the
        ladder, and it is never empty-by-accident.

        ⛔ r4 / codex R-2 + opus R-2. The r3 form SKIPPED a range whose endpoint was off
        the ladder -- neither expanding it nor rejecting it -- and both anchors named
        the same consequence:

            "v2.4 through v3.2 introduce no new binding slots."

        `v2.4` is not a supported pin, so the range expands to nothing and the sentence
        names two literal versions, which is BELOW leg 1's threshold of three. Both legs
        silent, on a claim that is false. A quiet skip in a guard is the worst branch to
        take: it reads as "no finding" and it means "I could not tell".

        An unknown endpoint is now REPORTED. The caller decides what to do with it; what
        this function may not do is stay silent about the fact that it did not know.
        """
        named = set(cls.VERSION.findall(text))
        ladder = cls._ladder()
        unknown = set()
        for m in cls.RANGE.finditer(text):
            ends = cls.VERSION.findall(m.group(0))
            off = [e for e in ends if e not in ladder]
            if off:
                unknown.update(off)
                continue
            if len(ends) != 2:
                continue
            lo, hi = sorted(ladder.index(e) for e in ends)
            named.update(ladder[lo:hi + 1])
        return named, unknown

    # A sentence ends at a period that is NOT BETWEEN TWO DIGITS, or at `;` / `:`.
    #
    # ⛔ r2's form said something subtly different and it was wrong in BOTH directions.
    # `(?<!\d)\.(?!\d)` reads "a digit on NEITHER side", where the rule wanted is "not
    # BETWEEN two digits" -- and the gap between those two readings is a period that has
    # a digit on exactly ONE side, which is precisely how a sentence ending in a version
    # token looks. Reproduced (creator r3, its repro script `repro_R1_R4.py`,
    # both rows with passing controls):
    #
    #   FALSE POSITIVE  "The stamp is v2.8. The stamp is v3.0. The stamp is v3.1."
    #                   -- three innocent one-version sentences never split, fused into a
    #                   single 3-version "roster". The control (same three sentences
    #                   ending in ordinary words) stays silent, so the fusion is
    #                   attributable to the terminal periods and not to the sentences.
    #   FALSE NEGATIVE  "v2.5, v2.6, ... v3.2 introduce no new binding slots."
    #                   -- each dot of the ASCII ellipsis is a boundary, so a real
    #                   four-version roster is chopped into fragments of one or two and
    #                   never reaches the threshold. `v2.7 -> ... -> v3.2` is this
    #                   repository's own house idiom, so this is not a synthetic shape.
    #
    # Two defects of OPPOSITE SIGN in one regex, which is why a lookahead alone is not
    # the cure: it fixes one and leaves the other standing. Both are addressed here.
    #
    # An ellipsis is a RUN, not a boundary. `\.{2,}` is matched FIRST and carries no
    # `end` group, so `_enumeration_findings` discards it and the sentence continues
    # through it. (Opus's r2 R-1 condition offered exactly this shape: "treat `\.{2,}`
    # as a non-splitting run".)
    #
    # ⚠ The `end` group is read through `groupdict().get(...)` at the call site, so a
    # BOUNDARY substituted WITHOUT that group -- which is what the naive-`[.;:]`
    # mutation arm below installs -- still grades every match as a boundary. The cure
    # must not quietly disarm the arm that proves BOUNDARY is load-bearing
    # [[instrument-must-prove-it-fired]].
    BOUNDARY = re.compile(r"\.{2,}|(?P<end>(?<!\d)\.|\.(?!\d)|[;:])")

    @classmethod
    def _claim_patterns(cls, inner_class=None):
        """Leg 2's two patterns. `inner_class` is injectable ONLY so the coupling arm can
        re-run the real grader with the historic period-excluded class and measure what it
        then misses -- the fix is driven, not attested."""
        inner = inner_class or cls.INNER
        neg = r"(?:introduce[s]?|add[s]?|bring[s]?|carr(?:y|ies))\s+(?:no|none)|no\s+new"
        return [
            # subject BEFORE the trigger -- the shape r1 was blind to
            ("subject-first", re.compile(
                rf"(?P<list>{cls.LIST})\s*{inner % 80}\b(?P<trig>{neg})\b{inner % 40}slot",
                re.IGNORECASE)),
            # trigger BEFORE the subject
            ("trigger-first", re.compile(
                rf"\bnone of\s+(?P<list>{cls.LIST}){inner % 80}slot",
                re.IGNORECASE)),
        ]

    @classmethod
    def _table_literals(cls, node):
        """Count version tokens that are whole string literals reachable ONLY through
        container structure -- a tuple/list/dict/set nesting, never a call argument.

        ⛔ r4 / codex R-3, CONFIRMED BY EXECUTION and not by argument. Opus read the
        assigned-prose hole as closed in both directions; codex said a COMPOSED roster
        walks through it. One fixture settled it (the r3 adjudication record §3,
        its fixture `fixture_R3_composed_prose.py`, both controls
        firing):

            _NOTE = "{}, {} and {} introduce no new slots.".format("v2.8","v2.9","v3.0")

        was exempted as a TABLE and both legs went silent. The r3 rule asked whether a
        version token IS a whole string literal -- and here three of them are, as
        arguments to `.format`. Whole literals by the letter of the rule; prose by
        intent, and prose that exists at runtime and nowhere the guard looks.

        A table is a STRUCTURE of literals. The descent therefore admits only container
        nodes, so an argument list cannot masquerade as one. `HOPS` (Tuple of Tuples)
        and `SLOT_INTRODUCED_IN` (Dict) are unaffected -- measured, not assumed.

        ⚠ RESIDUAL: a genuine table built by a CALL (`dict(...)`, `tuple(...)`) loses
        its exemption and leg 1 fires on it. A false POSITIVE, loud, and the safe
        direction against the silent false negative it replaces.
        """
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return sum(cls._table_literals(e) for e in node.elts)
        if isinstance(node, ast.Dict):
            return sum(cls._table_literals(e) for e in node.keys + node.values
                       if e is not None)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return 1 if re.fullmatch(r"v\d+\.\d+", node.value.strip()) else 0
        return 0

    @classmethod
    def _table_line_span(cls, text):
        """Line numbers belonging to a version TABLE, DERIVED from the source.

        The tables are the authority these rules read, so they must be exempt from leg 1
        -- an authority is allowed to enumerate. A hand-listed line range would be a
        roster inside the guard, and would go stale exactly as the prose did, so the
        exemption is COMPUTED. Returns (lines, names): the names are what the exemption
        actually fired on, so an arm can assert WHICH assignments were blanked instead
        of merely how many. An unparseable text has no tables to exempt, which is the
        correct answer for a bare fixture.

        ⛔ r3 / codex R-4. The r2 rule was "3+ version TOKENS among the literals", and
        its docstring claimed "a prose roster never is [exempt], because prose is not an
        assignment". That is false in one word -- prose CAN be an assignment. Reproduced:

            _NOTE = "v3.0, v3.1 and v3.2 introduce no new slots."

        is exempt under the r2 rule, so leg 1 goes blind on exactly the artifact it
        exists to catch, and blind SILENTLY, which is the worst direction.

        The discriminator is not the node's NAME and not its container shape. Exempting
        by name (`HOPS`, `SLOT_INTRODUCED_IN`) would put a hand-written list of
        authorities inside the guard -- the roster-in-the-guard this method's second
        sentence already refuses, and a new table would be blind until someone
        remembered to add it. Exempting containers misses
        `_NOTES = ("v3.0, v3.1 and v3.2 introduce no new slots.",)`, a tuple of prose.

        What actually separates them is measurable and needs no list: in a TABLE a
        version token IS a whole string literal (`"v2.5"`); in PROSE it is a substring
        of a sentence. Measured across the real module -- HOPS 14 exact of 14 tokens,
        SLOT_INTRODUCED_IN 7 of 7, both prose forms 0 of 3.

        ⛔ AMENDED at r4: "whole string literal" alone was not the discriminator. A
        roster COMPOSED by `.format("v2.8", "v2.9", "v3.0")` spells three whole
        literals and was exempted -- the r3 rule's own words, satisfied by prose. The
        count now descends CONTAINER STRUCTURE only; see `_table_literals`, which
        carries the fixture that settled it.

        ⚠ RESIDUAL: a table that does not spell its versions as bare literals -- built
        by f-string, or read from a file -- has no exact literals and LOSES its
        exemption, so leg 1 would fire on it. That is a false POSITIVE, loud and
        immediate, and it is the safe direction here: the r2 rule's failure was a silent
        false negative on the one leg that catches staleness by shape."""
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return set(), []
        lines, names = set(), []
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            exact = cls._table_literals(node.value)
            if exact >= NoRosterMayReturnTest.ENUMERATION_THRESHOLD:
                lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
                targets = [node.target] if isinstance(node, ast.AnnAssign) else node.targets
                names.extend(t.id for t in targets if isinstance(t, ast.Name))
        return lines, names

    @classmethod
    def _logical(cls, text, blank=frozenset()):
        """(normalized_text, [line number for each normalized char]).

        Source prose wraps. A guard that scans PHYSICAL lines cannot see a claim whose
        trigger phrase and subject noun land on opposite sides of a line break, which is
        the normal shape of an 80-column comment -- so it reports green on exactly the
        sentences it exists to catch. Leading whitespace and a leading comment marker are
        stripped so a wrapped comment reads as one sentence
        [[test-drive-must-match-its-fail-shape]]. Lines in `blank` are emptied, keeping
        the line numbering intact so a finding still reports its true line."""
        out, lines = [], []
        for n, raw in enumerate(text.splitlines(), start=1):
            s = "" if n in blank else raw.strip()
            if s.startswith("#"):
                s = s[1:].strip()
            if out:
                out.append(" ")
                lines.append(n)
            out.append(s)
            lines.extend([n] * len(s))
        return "".join(out), lines

    @classmethod
    def _enumeration_findings(cls, text):
        """LEG 1. Sentences naming ENUMERATION_THRESHOLD+ distinct versions."""
        blank, _n = cls._table_line_span(text)
        norm, lineno = cls._logical(text, blank)
        found, start = [], 0
        # A match is a boundary unless it is an ellipsis RUN. `groupdict().get(name,
        # default)` is deliberate rather than `m.group("end")`: a BOUNDARY substituted
        # without that group -- the naive-`[.;:]` mutation arm -- has an empty groupdict,
        # falls back to the whole match, and every match still counts. A cure that
        # silently disarmed that arm would leave it green and blind.
        ends = [m for m in cls.BOUNDARY.finditer(norm)
                if m.groupdict().get("end", m.group(0))]
        for m in ends + [None]:
            end = m.start() if m else len(norm)
            sent = norm[start:end]
            distinct = sorted(set(cls.VERSION.findall(sent)))
            if len(distinct) >= cls.ENUMERATION_THRESHOLD:
                found.append((lineno[start] if start < len(lineno) else 0,
                              distinct, sent.strip()[:140]))
            start = end + 1
        return found

    @classmethod
    def _association_holds(cls, m):
        """May this match's version list be associated with its trigger phrase?

        ⛔ r4 / codex R-1 + opus R-1. What stood here was DASH PARITY, and both anchors
        refuted it independently, with two sentences built without sight of each other:

            "v2.9 introduced a slot -- documentation changed -- v3.1 adds no new slots."
            "v2.9 introduced a slot -- work continued -- v3.0 adds no new binding slots."

        Both have an EVEN dash count, so parity permitted the crossing and leg 2 blamed
        `v2.9` on a sentence whose every clause is true -- codex's original R-2 false
        positive, restored by adding one more clause break. Parity was never pairing. It
        was COUNTING, and a count cannot tell one aside from two clause breaks: the two
        shapes are identical to it. Two independent constructions of the same
        counterexample is not a coincidence to grade down [[split-verdict-discipline]].

        THE RULE THAT REPLACES IT ASKS WHAT THE SENTENCE PUTS NEXT TO THE VERB. A match
        reaches from a version list to a trigger. If it crossed a dash, and a version
        token stands between the LAST dash it crossed and the trigger, then the trigger
        already had a NEARER subject and this match reached past it. That is the false
        association, whatever the dashes are doing. Validated over every specimen either
        anchor or orch named before it was written here -- both refutations SILENT, the
        real aside and the leading aside both surviving, rc 0
        [[test-drive-must-match-its-fail-shape]].

        `trigger-first` carries no `trig` group (its trigger PRECEDES the list, so
        "nearer subject" is not defined for it); it falls back to refusing any crossed
        dash, which is the conservative direction for a shape this repository does not
        write.

        ⚠ RESIDUAL, and it is the honest bound: this is still not a parse. A sentence
        whose second clause states its claim WITHOUT naming a version --
        `v2.9 introduced a slot -- nothing since adds new slots` -- has no nearer
        subject to find, so the association is permitted and leg 2 blames v2.9. A false
        POSITIVE, the direction that teaches an author to stop believing the guard, and
        it is NOT covered. It is named here rather than left for a fourth round.
        """
        span = m.group(0)
        trig = m.groupdict().get("trig")
        if trig is None:                      # trigger-first: refuse any crossing
            return not cls.DASH.search(span)
        crossed = [d for d in cls.DASH.finditer(span[:span.index(trig)])]
        if not crossed:
            return True                       # nothing crossed; nothing to reject on
        return not cls.VERSION.search(span[crossed[-1].end():span.index(trig)])

    @classmethod
    def _claim_findings(cls, text, inner_class=None):
        """LEG 2. Claims of 'no new slots' whose OWN version list names an introducer."""
        introducing = set(mw.SLOT_INTRODUCED_IN.values())
        norm, lineno = cls._logical(text)
        found = []
        for label, pat in cls._claim_patterns(inner_class):
            # r4 / codex + opus R-1. See `_association_holds` -- the parity rule that
            # stood here was REFUTED by both anchors independently and is gone.
            #
            # ⛔ NOT `finditer`, and the difference is measured, not stylistic.
            # `finditer` would have CONSUMED a rejected span already, so a genuine false
            # claim living in the clause AFTER the dash would be swallowed by the
            # rejected match and never re-scanned:
            #
            #   "v2.9 introduced a slot -- v2.6, v3.1 and v3.2 introduce no new slots."
            #
            # is silent under the consuming form while its own second clause alone fires
            # on `v2.6`. Rejecting a span therefore RESUMES INSIDE it, one character
            # past its start, not past its end. `pos` still increases strictly, so this
            # terminates; an ACCEPTED match advances to its end, so accepted findings
            # never overlap and are never recorded twice.
            pos = 0
            while pos <= len(norm):
                m = pat.search(norm, pos)
                if not m:
                    break
                if not cls._association_holds(m):
                    pos = m.start() + 1
                    continue
                pos = max(m.end(), m.start() + 1)
                named, unknown = cls._named_versions(m.group("list"))
                # r4 / R-2: an endpoint the ladder does not know is REPORTED, not
                # skipped. The claim cannot be graded -- so say that, loudly, rather
                # than returning the silence that reads as "no finding".
                bad = sorted(named & introducing) + [f"UNKNOWN-ENDPOINT:{u}"
                                                     for u in sorted(unknown)]
                if bad:
                    found.append((lineno[m.start()] if m.start() < len(lineno) else 0,
                                  label, bad, m.group(0).strip()[:140]))
        return found

    # ── the module, under both legs ────────────────────────────────────────
    def test_no_sentence_in_the_module_enumerates_versions(self):
        """⭐ LEG 1, RED-BY-DESIGN against pre-rewrite main (8 findings) AND against this
        branch's own first commit (1 -- the prose hop ladder in `migrate`'s docstring,
        which neither r1 reviewer named and this leg found).

        ⛔ DETECTED THERE, NOT AUTHORED THERE. The ladder entered the module long before
        this branch and was byte-identical in that commit's parent; the leg is red at
        that commit because the ladder was ALREADY PRESENT. Presence and origin are easy
        to collapse when a detector first fires on the commit you happen to be standing
        on, so every site that states this measurement now says which one it means --
        a reader who stops at one of them must not be able to infer the other
        [[correction-reach-discipline]]."""
        found = self._enumeration_findings(SRC.read_text(encoding="utf-8"))
        self.assertEqual([], found,
                         f"a sentence enumerates {self.ENUMERATION_THRESHOLD}+ versions "
                         f"-- that is a roster whatever it claims; state the rule and "
                         f"derive from HOPS / SLOT_INTRODUCED_IN:\n"
                         + "\n".join(map(str, found)))

    def test_no_claim_in_the_module_names_a_version_that_introduced_a_slot(self):
        """⭐ LEG 2, both directions. Only versions inside the CLAIM'S OWN list are
        graded, so a version literal elsewhere in the file cannot make this fire and
        cannot make it miss."""
        found = self._claim_findings(SRC.read_text(encoding="utf-8"))
        self.assertEqual([], found,
                         "a 'no new slots' claim names a version that DID introduce one; "
                         "derive from SLOT_INTRODUCED_IN instead of writing a roster:\n"
                         + "\n".join(map(str, found)))

    def test_the_table_exemption_is_derived_and_actually_found_the_tables(self):
        """The exemption is what keeps leg 1 off the authority it reads -- so if it
        silently found NOTHING, leg 1 would be scanning the tables and its green would
        mean the file has no tables, not that it has no rosters. Prove it fired
        [[instrument-must-prove-it-fired]].

        ⛔ r3 / codex R-4. This arm previously asserted `count >= 2`, which two ASSIGNED
        PROSE strings satisfy just as well as the two intended tables -- so it proved
        the exemption fired on SOMETHING, never on the right thing, while both real
        tables could have been missed. A count is not an identification
        [[counts-and-relations-discipline]]. It now asserts WHICH assignments were
        exempted, in both directions, and pins them to the names leg 1's own findings
        would have to be about."""
        lines, names = self._table_line_span(SRC.read_text(encoding="utf-8"))
        self.assertEqual({"HOPS", "SLOT_INTRODUCED_IN"}, set(names),
                         "the exemption did not fire on exactly the two version tables "
                         f"this module has; it fired on {sorted(names)}. An unexpected "
                         "name is prose being blanked; a missing one is a table leg 1 "
                         "is now scanning")
        self.assertTrue(lines, "a table was named but no lines were exempted")

    # A prose roster written as an ASSIGNMENT -- the shape the r2 exemption admitted.
    B_R4_ASSIGNED_PROSE = '_NOTE = "v3.0, v3.1 and v3.2 introduce no new slots."\n'
    B_R4_WRAPPED_PROSE = '_NOTES = ("v3.0, v3.1 and v3.2 introduce no new slots.",)\n'
    B_R4_COMMENT_PROSE = "# v3.0, v3.1 and v3.2 introduce no new slots.\n"
    B_R4_REAL_TABLE = ('HOPS = (("v2.5", "v2.6"), ("v2.6", "v2.7"), '
                       '("v2.7", "v2.8"))\n')

    def test_R4_assigned_PROSE_is_not_a_table_but_a_real_table_still_is(self):
        """⭐ codex r2 R-4. Both directions, because a cure to this one is one keystroke
        from disabling the exemption altogether -- and leg 1 would then fire on the
        module's own authority, which reads as the guard working until someone looks.

        The comment form is the CONTROL: byte-identical prose that was never exempt,
        so a red on the assigned forms is attributable to the ASSIGNMENT and not to leg
        1 having stopped catching the sentence [[instrument-polarity-controls]]. The
        wrapped form is why the cure is not "exempt only containers"."""
        self.assertTrue(self._enumeration_findings(self.B_R4_COMMENT_PROSE),
                        "premise of this arm: leg 1 catches this roster as a comment")
        for label, fixture in (("bare string", self.B_R4_ASSIGNED_PROSE),
                               ("tuple-wrapped", self.B_R4_WRAPPED_PROSE)):
            with self.subTest(shape="assigned prose", form=label):
                self.assertTrue(
                    self._enumeration_findings(fixture),
                    "a prose roster went blind by being written as an assignment -- "
                    "the exemption is matching version TOKENS inside a sentence "
                    "instead of whole literal version STRINGS")
                self.assertEqual([], self._table_line_span(fixture)[1],
                                 "assigned prose was named as a version table")
        self.assertEqual(["HOPS"], self._table_line_span(self.B_R4_REAL_TABLE)[1],
                         "a real table lost its exemption -- leg 1 will now fire on the "
                         "authority it reads, and the cure has overshot")
        self.assertEqual([], self._enumeration_findings(self.B_R4_REAL_TABLE),
                         "leg 1 fired on an exempt table")

    # ── the differential pair: same shape, opposite truth, opposite verdict ─
    #
    # ⛔ These are the arms r1 did not have. A guard that only ever sees clean input is an
    # unbounded negative; a guard that only ever sees dirty input may be firing on
    # anything at all. The pair is what separates "this instrument detects the defect"
    # from "this instrument dislikes version numbers".
    F_FALSE_SUBJECT_FIRST = "v2.8 and v2.9 introduce no new binding slots."
    F_TRUE_SUBJECT_FIRST = "v3.0 and v3.1 introduce no new binding slots."
    F_FALSE_TRIGGER_FIRST = "None of v2.8, v2.9 introduces new binding slots."
    F_TRUE_TRIGGER_FIRST = "None of v3.0, v3.1 introduces new binding slots."

    def test_F2_a_false_two_version_claim_is_caught_in_BOTH_directions(self):
        """⭐ Below leg 1's threshold on purpose, so this arm measures LEG 2 alone.

        Two versions, one of which (v2.9, release 1.7.0, NON_ROLE_DIRS) did introduce a
        slot. Graded by the SAME `_claim_findings` that grades the real file -- a fixture
        scored by a copy of the grader tests the copy
        [[emitter-and-verifier-are-one-grammar]]."""
        for label, sample in (("subject-first", self.F_FALSE_SUBJECT_FIRST),
                              ("trigger-first", self.F_FALSE_TRIGGER_FIRST)):
            with self.subTest(direction=label):
                self.assertEqual([], self._enumeration_findings(sample),
                                 "premise of this arm: the fixture is BELOW leg 1's "
                                 "threshold, so any red here is leg 2's")
                found = self._claim_findings(sample)
                self.assertTrue(found, f"leg 2 missed a false {label} claim: {sample!r}")
                self.assertIn("v2.9", found[0][2],
                              "caught, but not for the version that is actually false")

    def test_F3_a_TRUE_claim_in_the_same_shape_passes(self):
        """⭐ The other half of the differential. Identical wording over a range that
        genuinely introduces nothing must NOT fire -- otherwise the guard forbids the
        sentence rather than the falsehood, and the next author's correct claim is red."""
        for label, sample in (("subject-first", self.F_TRUE_SUBJECT_FIRST),
                              ("trigger-first", self.F_TRUE_TRIGGER_FIRST)):
            with self.subTest(direction=label):
                self.assertEqual([], self._claim_findings(sample),
                                 f"a TRUE {label} claim was flagged: {sample!r}")

    def test_the_r1_BLIND_SPOT_itself_is_now_caught(self):
        """⭐ The regression arm for r1's actual defect, in its discriminating form.

        This is the docstring roster with its trailing clause REMOVED -- the exact shape
        measured to slip past r1's guard entirely, because the only version r1 graded was
        the incidental `v2.6` in text that is not part of the claim. Both legs must see
        it now: leg 1 by count, leg 2 by the claim's own list."""
        sample = ("it never adds binding slots. v2.9, v3.0, v3.1 and v3.2 introduce "
                  "NO new\nslots; declared once")
        self.assertTrue(self._enumeration_findings(sample),
                        "leg 1 missed a four-version roster")
        found = self._claim_findings(sample)
        self.assertTrue(found, "leg 2 missed the claim r1 was blind to")
        self.assertIn("v2.9", found[0][2])

    def test_both_ORIGINAL_rosters_are_caught_as_they_were_WRAPPED_in_the_source(self):
        """A no-op control over the real historic bytes, wrapping included.

        ⛔ Reproduced WRAPPED, exactly as they stood -- including the line break that
        splits the trigger phrase from the word "slot". The first version of this control
        planted a single-line paraphrase and passed while the guard found ZERO offenders
        in the real pre-rewrite file. A control written from a restatement of the claim
        tests the restatement."""
        planted = {
            "docstring roster (was line ~75)":
                "  - it never adds binding slots. v2.9, v3.0, v3.1 and v3.2 introduce NO new\n"
                "    slots; the v2.6 slot",
            "advisory roster (was line ~175)":
                "# adding\", never stamped. None of v2.8, v2.9, v3.0, v3.1 or v3.2 introduces\n"
                "# new binding slots, so this list is unchanged across every later hop.",
        }
        for label, sample in planted.items():
            with self.subTest(roster=label):
                self.assertTrue(self._claim_findings(sample),
                                f"leg 2 did not fire on {label} -- the exact bytes it "
                                f"was written to catch. It is decorative.")
                self.assertTrue(self._enumeration_findings(sample),
                                f"leg 1 did not fire on {label}")

    # ── r3 / codex R-3: the two sentence-boundary defects, each with its RED drive ──
    #
    # ⛔ The fixtures are named as constants because both arms below drive them and the
    # r3 record quotes them verbatim; a fixture written twice drifts once.
    B_FUSED_SENTENCES = "The stamp is v2.8. The stamp is v3.0. The stamp is v3.1."
    B_FUSED_CONTROL = "The stamp is old. The stamp is newer. The stamp is newest."
    B_ELLIPSIS_ROSTER = "v2.5, v2.6, ... v3.2 introduce no new binding slots."
    B_ELLIPSIS_CONTROL = "v2.5, v2.6, v3.2 introduce no new binding slots."
    B_R2_BOUNDARY = re.compile(r"(?<!\d)\.(?!\d)|[;:]")   # the shipped r2 form

    def test_R3a_sentences_ENDING_in_a_version_are_not_fused_into_a_roster(self):
        """⭐ codex r2 R-3, false-positive half. GREEN then RED, in one arm.

        GREEN: three one-version sentences must not fire, and its control -- the same
        three sentences ending in ordinary words -- must not fire either, which is what
        makes a future red attributable to the terminal periods rather than to the
        sentences [[instrument-polarity-controls]].

        RED: restore r2's BOUNDARY and the SAME fixture must fire with all three
        versions. Without that half this arm is an unbounded negative -- it would pass
        just as well if leg 1 had stopped working altogether."""
        self.assertEqual([], self._enumeration_findings(self.B_FUSED_SENTENCES),
                         "three one-version sentences were fused into a roster; the "
                         "period after a version token is not being read as a boundary")
        self.assertEqual([], self._enumeration_findings(self.B_FUSED_CONTROL),
                         "premise of this arm: the same shape without version tokens is "
                         "silent, so any red above is about the terminal periods")
        saved = NoRosterMayReturnTest.BOUNDARY
        try:
            NoRosterMayReturnTest.BOUNDARY = self.B_R2_BOUNDARY
            red = self._enumeration_findings(self.B_FUSED_SENTENCES)
            self.assertTrue(red,
                            "r2's BOUNDARY no longer fuses sentences ending in a "
                            "version -- the defect this cure exists for is gone by some "
                            "other route, so re-derive this arm rather than deleting it")
            self.assertEqual(["v2.8", "v3.0", "v3.1"], red[0][1],
                             "the reproduced defect fused a different set than recorded")
        finally:
            NoRosterMayReturnTest.BOUNDARY = saved

    def test_R3b_an_ELLIPSIS_does_not_cut_a_roster_below_the_threshold(self):
        """⭐ codex r2 R-3 / opus r2 R-1, false-negative half -- the dangerous sign.

        `v2.7 -> ... -> v3.2` is this repository's OWN idiom, so a roster written that
        way is the likely shape, not a constructed one. GREEN: it must fire, and so must
        the ellipsis-free control (proving the sentence is a roster on its own merits).
        RED: under r2's BOUNDARY the ellipsis splits it below threshold and leg 1 goes
        silent -- a guard reporting green on the sentence it exists to catch."""
        self.assertTrue(self._enumeration_findings(self.B_ELLIPSIS_ROSTER),
                        "leg 1 missed a three-version roster because of the ellipsis")
        self.assertTrue(self._enumeration_findings(self.B_ELLIPSIS_CONTROL),
                        "premise of this arm: the same roster without the ellipsis "
                        "fires, so any red above is about the ellipsis alone")
        saved = NoRosterMayReturnTest.BOUNDARY
        try:
            NoRosterMayReturnTest.BOUNDARY = self.B_R2_BOUNDARY
            self.assertEqual(
                [], self._enumeration_findings(self.B_ELLIPSIS_ROSTER),
                "r2's BOUNDARY no longer loses the ellipsis roster -- the false negative "
                "is gone by some other route; re-derive this arm")
        finally:
            NoRosterMayReturnTest.BOUNDARY = saved

    # ── r3 / codex R-1: the operator CLASS, and the half that must stay silent ──
    #
    # The claim is the same in all eight rows -- `v2.8 <op> v3.0 introduce no new binding
    # slots` -- and it straddles `v2.9`, which introduced NON_ROLE_DIRS. Under a RANGE
    # operator that claim is FALSE and must fire; under an ENUMERATION operator the same
    # words name only v2.8 and v3.0, both true, and firing would be the false positive.
    B_R1_CLAIM = "%s introduce no new binding slots."
    B_R1_SPAN = ("v2.8", "v3.0")

    def test_R1_a_RANGE_operator_names_what_it_implies_and_an_ENUMERATION_does_not(self):
        """⭐ codex r2 R-1, widened to the class the reproduction measured.

        BOTH halves are asserted. A cure keyed to codex's one word (`through`) would
        range over a specimen instead of over the quantity; a cure applied to all eight
        would manufacture a false positive on a claim naming only true things, which is
        precisely what `test_F3_a_TRUE_claim_in_the_same_shape_passes` forbids. The
        boundary between them is the finding, so it is driven from both sides
        [[instrument-polarity-controls]].

        The operator sets are also RECONCILED against `LIST`'s own alternation, both
        ways -- declaring them twice is two chances to drift, so the arm compares them
        rather than trusting them [[counts-and-relations-discipline]]."""
        lo, hi = self.B_R1_SPAN
        straddled = self._ladder()[self._ladder().index(lo) + 1]
        self.assertIn(straddled, set(mw.SLOT_INTRODUCED_IN.values()),
                      f"premise of this arm: {straddled} lies inside the span and did "
                      f"introduce a slot, which is what makes the claim false")

        advertised = set(re.search(r"\(\?:((?:[^()]|\\.)+)\)\s*\\s\*v", self.LIST)
                         .group(1).split("|"))
        self.assertEqual(advertised, set(self.RANGE_OPS) | set(self.ENUM_OPS),
                         "LIST advertises a different operator set than RANGE_OPS + "
                         "ENUM_OPS classify -- an operator that is advertised but "
                         "unclassified is silently in neither half of this arm")
        self.assertEqual(set(), set(self.RANGE_OPS) & set(self.ENUM_OPS),
                         "an operator classified as both a range and an enumeration")

        for op in self.RANGE_OPS:
            with self.subTest(operator=op, half="range -> must fire"):
                claim = self.B_R1_CLAIM % f"{lo} {op} {hi}"
                found = self._claim_findings(claim)
                self.assertTrue(found,
                                f"a range written with `{op}` implies {straddled}, which "
                                f"introduced a slot, and leg 2 stayed silent -- the "
                                f"claim is false and unguarded")
                self.assertIn(straddled, found[0][2],
                              f"leg 2 fired on the `{op}` range but did not name the "
                              f"version the range only IMPLIES")
        for op in self.ENUM_OPS:
            with self.subTest(operator=op, half="enumeration -> must stay silent"):
                claim = self.B_R1_CLAIM % f"{lo}{op if op == ',' else f' {op} '} {hi}"
                self.assertEqual(
                    [], self._claim_findings(claim),
                    f"leg 2 fired on an enumeration written with `{op}`, which names "
                    f"only {lo} and {hi} -- both true. Expanding the enumeration "
                    f"operators manufactures a false positive on correct prose")

    def test_R1_leg_1_deliberately_does_NOT_expand_ranges(self):
        """⛔ A boundary that was MEASURED and then not crossed, recorded so the next
        author does not cross it by tidiness.

        Wiring the range expansion into leg 1 as well makes it fire on three sentences
        of the real module. Two of them are hard-coded spans that will go stale. The
        third is not: `migrate_workspace.py` says a workspace migrating from v2.5
        through v2.8 was never told the slot existed -- a statement about a CLOSED
        HISTORICAL WINDOW, true permanently, which no later hop can falsify. Flagging it
        is a false positive, and rewording a true sentence to appease a guard is the
        contortion this file exists to prevent.

        So leg 1 counts the versions a sentence LITERALLY names, and leg 2 -- which
        grades a CLAIM about slots, where an implied member is exactly where the false
        claim hides -- counts the ones a range implies. This arm drives that
        difference; if a future widening removes it, this reds and says why."""
        lo, hi = self.B_R1_SPAN
        ranged = self.B_R1_CLAIM % f"{lo} through {hi}"
        self.assertEqual([], self._enumeration_findings(ranged),
                         "leg 1 expanded a range into a roster -- see this docstring "
                         "for the true historical sentence that then reds")
        self.assertTrue(self._claim_findings(ranged),
                        "premise of this arm: leg 2 DOES expand the same sentence, so "
                        "the difference above is a boundary and not a dead expander")
        historical = ("a workspace migrating from v2.5 through v2.8 was never told the "
                      "slot existed")
        self.assertEqual([], self._enumeration_findings(historical),
                         "the real module's true historical sentence is being flagged "
                         "as a roster")

    # ── r3 / codex R-2: the unpaired dash, with the arm that pulls the OTHER way ──
    #
    # ⛔ These two fixtures carry the SAME punctuation mark and require OPPOSITE
    # verdicts. That is the whole finding, so they are named together and driven
    # together; an arm that only silenced the first would have reded the arm that keeps
    # INNER honest, and the cure would have looked green while trading a false positive
    # for a false negative [[instrument-polarity-controls]].
    B_R2_CLAUSE_BREAK = "v2.9 introduced a binding slot -- v3.0 adds no new binding slots."
    B_R2_CLAUSE_BREAK_EM = "v2.9 introduced a binding slot — v3.0 adds no new binding slots."
    B_R2_ASIDE = ("v2.9 and later -- that is, everything after v2.8 -- introduce "
                  "no new slots")
    B_R2_ASIDE_EM = ("v2.9 and later — that is, everything after v2.8 — introduce "
                     "no new slots")
    B_R2_NO_DASH = "v2.9 introduces no new binding slots."
    # r2 had no parity filter at all; a never-matching DASH restores exactly that.
    B_R2_NO_PARITY = re.compile(r"(?!)")

    def test_R2_an_UNPAIRED_dash_ends_the_clause_but_a_PAIRED_aside_does_not(self):
        """⭐ codex r2 R-2. GREEN in both directions, then RED, in one arm.

        GREEN(a): the clause break must go silent. Both clauses of
        `B_R2_CLAUSE_BREAK` are TRUE, so a hit is a false positive on a correct
        sentence -- the failure mode that teaches an author to stop believing the guard.
        GREEN(b): the appositive aside must KEEP FIRING. That one IS a false claim, and
        a cure that excluded the dash character would silence it. Both forms of each,
        because this repository writes `--` and `—` interchangeably.
        CONTROL: `B_R2_NO_DASH` has nothing to cross and must still fire, so a red in
        (a) is about the dash and not about leg 2 having died.
        RED: with parity disabled, the clause break fires again, blaming `v2.9`. Without
        that half this arm is an unbounded negative [[unfalsifiable-by-construction]]."""
        self.assertTrue(self._claim_findings(self.B_R2_NO_DASH),
                        "premise of this arm: leg 2 still catches a dash-free false "
                        "claim, so any silence below is attributable to the dash rule")
        for label, fixture in (("ascii", self.B_R2_CLAUSE_BREAK),
                               ("em dash", self.B_R2_CLAUSE_BREAK_EM)):
            with self.subTest(shape="unpaired clause break", form=label):
                self.assertEqual(
                    [], self._claim_findings(fixture),
                    "leg 2 attributed a claim across an UNPAIRED dash: both clauses of "
                    "this sentence are true, so this is a false positive on correct "
                    "prose")
        for label, fixture in (("ascii", self.B_R2_ASIDE),
                               ("em dash", self.B_R2_ASIDE_EM)):
            with self.subTest(shape="paired appositive aside", form=label):
                self.assertTrue(
                    self._claim_findings(fixture),
                    "leg 2 stopped catching a false claim whose subject is separated "
                    "from its verb by a COMPLETE aside -- the parity rule has been "
                    "replaced by something that excludes the dash character, which "
                    "trades codex's false positive for a false negative here")
        saved = NoRosterMayReturnTest.DASH
        try:
            NoRosterMayReturnTest.DASH = self.B_R2_NO_PARITY
            red = self._claim_findings(self.B_R2_CLAUSE_BREAK)
            self.assertTrue(red,
                            "without the parity filter leg 2 no longer fires on the "
                            "clause break -- the defect this cure exists for is gone by "
                            "some other route, so re-derive this arm rather than "
                            "deleting it")
            self.assertEqual(["v2.9"], red[0][2],
                             "the reproduced defect blamed a different version than "
                             "the r3 record quotes")
        finally:
            NoRosterMayReturnTest.DASH = saved

    # The residual the parity filter introduced ON ITS OWN, found by measuring the cure
    # instead of reasoning about it: a REJECTED span is still a match, and a consuming
    # scanner would swallow whatever lives inside it.
    B_R2_SWALLOWED = ("v2.9 introduced a slot -- v2.6, v3.1 and v3.2 introduce no new "
                      "slots.")
    B_R2_SWALLOWED_TAIL = "v2.6, v3.1 and v3.2 introduce no new slots."

    def test_R2_rejecting_a_span_does_not_SWALLOW_the_claim_inside_it(self):
        """⛔ A defect of the R-2 CURE, not of the code the cure was written against.

        The parity filter rejects the span opened by `v2.9`. Under a consuming scan that
        span has already eaten the second clause, whose claim about `v2.6` is FALSE and
        must fire -- so curing codex's false positive would have opened a false negative
        one clause to the right. Measured before the loop was rewritten; this arm is the
        red drive that keeps the rewrite from being quietly reverted to `finditer`.

        The control is the same second clause standing alone: it must fire, so a red
        above is about the swallowing and not about leg 2 having stopped catching it."""
        self.assertTrue(self._claim_findings(self.B_R2_SWALLOWED_TAIL),
                        "premise of this arm: the second clause fires on its own")
        found = self._claim_findings(self.B_R2_SWALLOWED)
        self.assertTrue(found,
                        "a false claim was swallowed by a span the dash rule REJECTED "
                        "-- rejecting a match must resume inside it, not past it")
        self.assertEqual(["v2.6"], found[0][2],
                         "the swallowed claim was recovered but blamed the wrong "
                         "version")

    # The two shapes at the edge of the parity rule. Both are pinned, in the direction
    # the leg ACTUALLY behaves -- a residual that lives in a paragraph is found by the
    # next reader or not at all, and one pinned in the wrong direction is worse than
    # none [[disclosed-residual-is-still-a-hole]].
    B_R2_ASIDE_THEN_CLAUSE = ("v2.9 -- the 1.7.0 stamp -- introduced a slot -- v2.6, "
                              "v3.1 and v3.2 introduce no new slots")
    B_R2_ASIDE_THEN_CLAUSE_TAIL = "v2.6, v3.1 and v3.2 introduce no new slots"
    B_R2_LEADING_ASIDE = "-- v2.6 and later -- introduce no new slots"
    B_R2_LEADING_ASIDE_TAIL = "v2.6 and later introduce no new slots"

    def test_R2_the_residuals_are_pinned_in_the_direction_the_leg_ACTUALLY_goes(self):
        """⛔ The surviving R-2 residual, made self-reporting.

        THREE DASHES, ODD COUNT (`B_R2_ASIDE_THEN_CLAUSE`) was disclosed as a known
        false negative when the parity filter was first designed, and under the
        CONSUMING scan it was one. It no longer is: rejecting a span now resumes one
        character past its START, so the second clause is re-scanned and its false claim
        about v2.6 is caught. It is pinned FIRING -- if a later change to pairing
        silences it again, that reds here and says which shape went dark. A residual
        pinned in the direction it was PREDICTED to go, rather than the direction it
        goes, would have asserted a false statement and could only have been made to
        pass by breaking the cure.

        A LEADING ASIDE (`B_R2_LEADING_ASIDE`) is what actually survives: the span opens
        at the version, crosses the aside's closing dash, and has nothing before it to
        resume behind. Odd, rejected, silent. A false NEGATIVE -- the safe direction --
        on a shape this repository has never written. It is pinned SILENT so that the
        day someone "fixes" pairing and flips it, the change is visible rather than
        inferred.

        Both carry their control: the same claim without the dashes must fire, so
        neither verdict above can be produced by a dead leg."""
        with self.subTest(shape="aside + dash-separated clause", pinned="FIRES"):
            self.assertTrue(self._claim_findings(self.B_R2_ASIDE_THEN_CLAUSE_TAIL),
                            "premise: the second clause fires on its own")
            found = self._claim_findings(self.B_R2_ASIDE_THEN_CLAUSE)
            self.assertTrue(found,
                            "the three-dash shape went silent again -- the rejected "
                            "span is being consumed instead of re-scanned")
            self.assertEqual(["v2.6"], found[0][2])
        with self.subTest(shape="aside opening before the list", pinned="FIRES"):
            self.assertTrue(self._claim_findings(self.B_R2_LEADING_ASIDE_TAIL),
                            "premise: the same claim without the aside fires, so the "
                            "verdict below is about the leading aside and not a dead leg")
            # ⛔ RE-DERIVED AT r4, on this arm's own instruction. Under parity this was
            # SILENT and pinned so. The nearer-subject rule reaches it: the span crosses
            # the closing dash, and there is no version token between that dash and the
            # trigger, so the association stands and the false claim is caught. The arm
            # reded when the rule changed and named the two places to re-derive -- which
            # is the whole reason a residual is pinned instead of written in a paragraph
            # [[disclosed-residual-is-still-a-hole]].
            found = self._claim_findings(self.B_R2_LEADING_ASIDE)
            self.assertTrue(found,
                            "the leading aside went silent again -- the association "
                            "rule has regressed toward counting dashes")
            self.assertEqual(["v2.6"], found[0][2])

    # ── r4: the two anchors' refutation of parity, as the arm that keeps it dead ──
    #
    # Built independently by codex and by opus, without sight of each other, and they
    # landed on the SAME shape: two clause breaks have an even dash count and are
    # indistinguishable from one aside under a count. Both are kept, verbatim as each
    # voice wrote them, because a single specimen would let a cure be tuned to one
    # sentence [[single-anchor-confirm-is-a-sample]].
    B_R4_EVEN_CODEX = "v2.9 introduced a slot -- documentation changed -- v3.1 adds no new slots."
    B_R4_EVEN_OPUS = "v2.9 introduced a slot -- work continued -- v3.0 adds no new binding slots."

    @staticmethod
    def _r3_parity(m):
        """The r3 rule verbatim, restored as a substitute for the RED half below.

        r3 shipped `if len(cls.DASH.findall(m.group(0))) % 2: continue` inline in the
        scanner -- an ODD count rejected, an EVEN count accepted. Expressed here as the
        predicate `_association_holds` now is, so the RED half swaps one function and
        changes nothing else about the scan."""
        return len(NoRosterMayReturnTest.DASH.findall(m.group(0))) % 2 == 0

    def test_R4_association_is_a_SUBJECT_test_and_NOT_a_dash_COUNT(self):
        """⛔ r4 / codex R-1 + opus R-1, CONFIRMED by both anchors and cured here.

        GREEN: both refutation sentences must go silent. Every clause of each is true --
        v2.9 did introduce a slot, and neither v3.1 nor v3.0 adds one -- so a hit is the
        false positive codex's r2 R-2 named, reachable again by adding one clause break.
        CONTROL: `B_R2_NO_DASH` still fires, so the silence is attributable to the
        association rule and not to leg 2 having died.
        BOUNDARY: the real aside must KEEP firing. A cure that rejected every crossed
        dash would pass the GREEN half and trade the false positive for a false
        negative, which is the trade this file exists to refuse
        [[instrument-polarity-controls]].
        RED: with the r3 parity predicate restored, BOTH refutations fire and blame
        `v2.9`. That is the defect reproduced at its own site, not argued -- and without
        it this arm is an unbounded negative [[unfalsifiable-by-construction]]."""
        self.assertTrue(self._claim_findings(self.B_R2_NO_DASH),
                        "premise of this arm: leg 2 still catches a dash-free false "
                        "claim, so any silence below is about the association rule")
        for voice, fixture in (("codex", self.B_R4_EVEN_CODEX),
                               ("opus", self.B_R4_EVEN_OPUS)):
            with self.subTest(anchor=voice, half="EVEN count -> must be silent"):
                self.assertEqual(
                    [], self._claim_findings(fixture),
                    f"{voice}'s refutation still fires: leg 2 reached past a NEARER "
                    f"subject to blame v2.9 on a sentence whose every clause is true")
        with self.subTest(half="the real aside must survive the cure"):
            self.assertTrue(self._claim_findings(self.B_R2_ASIDE),
                            "the appositive aside went silent -- the association rule "
                            "has degenerated into rejecting the dash character")
        saved = NoRosterMayReturnTest._association_holds
        try:
            NoRosterMayReturnTest._association_holds = self._r3_parity
            for voice, fixture in (("codex", self.B_R4_EVEN_CODEX),
                                   ("opus", self.B_R4_EVEN_OPUS)):
                with self.subTest(anchor=voice, half="RED under r3 parity"):
                    red = self._claim_findings(fixture)
                    self.assertTrue(red,
                                    f"{voice}'s refutation does NOT reproduce under the "
                                    f"r3 parity rule -- the defect is gone by some other "
                                    f"route, so re-derive this arm rather than deleting "
                                    f"it [[cure-discipline]]")
                    self.assertEqual(["v2.9"], red[0][2],
                                     "the reproduced defect blamed a version other than "
                                     "the one both anchors quoted")
        finally:
            NoRosterMayReturnTest._association_holds = saved

    # ── r4 / R-2: a range endpoint the ladder has never heard of ──
    #
    # `_named_versions` expands a range by INDEXING the ladder. An endpoint that is not
    # on it cannot be indexed, and r3 skipped that range -- which renders as no finding,
    # i.e. as "this claim is fine". The claim is not fine; it is UNGRADABLE, and those
    # are different answers [[lookup-failure-needs-own-outcome]].
    B_R4_OFF_LADDER = "v2.4 through v3.2 introduce no new binding slots."
    B_R4_ON_LADDER = "v2.5 through v3.2 introduce no new binding slots."

    def test_R4_an_UNKNOWN_range_endpoint_is_REPORTED_and_not_skipped(self):
        """⛔ r4 / codex R-2. A lookup failure gets its own outcome.

        `v2.4` predates the ladder's first rung, so the expansion cannot run. Silence
        would be indistinguishable from a graded pass, and the sentence a stamp bump
        makes wrong is exactly the sentence that names a version the ladder no longer
        carries. CONTROL: the same range with an on-ladder endpoint still fires the
        ORDINARY way -- naming the introducing version it implies, with no
        UNKNOWN-ENDPOINT marker -- so the new outcome cannot be produced by breaking
        expansion for everything."""
        found = self._claim_findings(self.B_R4_OFF_LADDER)
        self.assertTrue(found,
                        "an ungradable claim returned the same silence as a graded "
                        "pass: `v2.4` is not on the ladder and the range was skipped")
        self.assertIn("UNKNOWN-ENDPOINT:v2.4", found[0][2],
                      "the finding fired but did not say WHICH endpoint could not be "
                      "resolved, so the reader cannot tell an ungradable claim from a "
                      "false one")
        with self.subTest(control="on-ladder range still grades normally"):
            ok = self._claim_findings(self.B_R4_ON_LADDER)
            self.assertTrue(ok, "premise: an on-ladder range still fires")
            self.assertEqual([], [b for b in ok[0][2] if b.startswith("UNKNOWN")],
                             "a resolvable range is being reported as ungradable")
            self.assertIn("v2.9", ok[0][2],
                          "the on-ladder range stopped naming the introducing version "
                          "it implies -- expansion is broken, not merely guarded")

    # ── r4 / R-3: a roster COMPOSED at runtime ──
    #
    # ⛔ This row was a factual SPLIT between the anchors and was settled by EXECUTION,
    # not by a third voice: the r3 fixture `fixture_R3_composed_prose.py`
    # ran orch's specimen verbatim against the r3 module with both controls firing, and
    # both legs were SILENT -- codex CONFIRMED. The specimen is carried here unchanged.
    B_R4_COMPOSED_PROSE = ('_NOTE = "{}, {} and {} introduce no new slots."'
                           '.format("v2.8", "v2.9", "v3.0")\n')
    B_R4_CALL_BUILT_TABLE = ('HOPS = tuple([("v2.5", "v2.6"), ("v2.6", "v2.7"), '
                             '("v2.7", "v2.8")])\n')

    def test_R4_a_roster_COMPOSED_by_a_call_does_not_inherit_the_exemption(self):
        """⛔ r4 / codex R-3, confirmed by a fixture and cured here.

        The r3 discriminator was "a version token IS a whole string literal". Three
        whole literals sit in that `.format()` call, so the assignment was exempted and
        leg 1 went blind on a roster that exists at runtime -- the r2 failure, one
        composition step further out. A table is a STRUCTURE of literals, so the count
        now descends containers only and an argument list is not a container.

        CONTROL: the real `HOPS` tuple keeps its exemption BY NAME IN THE RESULT, not
        merely by staying silent -- an exemption that stopped finding any table would
        also produce the finding this arm wants, and the two must not be confusable
        [[green-coverage-discipline]].
        RESIDUAL, driven rather than described: a genuine table built by a CALL loses
        its exemption and leg 1 fires on it. Pinned, because it is a real false positive
        and the next author should meet it here rather than in the wild
        [[disclosed-residual-is-still-a-hole]]."""
        self.assertEqual([], self._table_line_span(self.B_R4_COMPOSED_PROSE)[1],
                         "the composed roster was exempted as a table -- its version "
                         "tokens are Call ARGUMENTS, whole literals by the letter of "
                         "the r3 rule and prose by intent")
        found = self._enumeration_findings(self.B_R4_COMPOSED_PROSE)
        self.assertTrue(found, "leg 1 is blind to a roster composed by `.format()`")
        self.assertEqual(["v2.8", "v2.9", "v3.0"], found[0][1],
                         "leg 1 fired but did not name the three versions the composed "
                         "sentence puts in front of a reader")
        with self.subTest(control="a real literal table keeps its exemption"):
            self.assertEqual(["HOPS"], self._table_line_span(self.B_R4_REAL_TABLE)[1],
                             "the container descent lost the real table -- the cure has "
                             "taken the authority's exemption away with the prose's")
        with self.subTest(residual="a table built by a call LOSES its exemption"):
            self.assertEqual(
                [], self._table_line_span(self.B_R4_CALL_BUILT_TABLE)[1],
                "a call-built table is being exempted, which is the hole this cure "
                "closed -- re-derive both this row and `_table_literals`")
            self.assertTrue(
                self._enumeration_findings(self.B_R4_CALL_BUILT_TABLE),
                "premise of the residual: leg 1 does fire on it, so the false positive "
                "is real and pinned rather than predicted")

    def test_the_period_hazard_is_still_guarded_in_BOTH_legs(self):
        """⭐ Q1's coupling, as a DRIVEN arm rather than a comment claiming it matters.

        This arm reds in EITHER direction: if someone removes a lookaround / escape
        hatch, the leg goes blind and its subTest reds; if a leg stops depending on one,
        that subTest reds too and says the comment above needs re-deriving. A guard's
        justification is a claim and gets graded like one [[reviewer-constraints-are-claims]].

        ⚠ The two subTests are NOT equally strong evidence, and the arm says which:
        BOUNDARY is driven from the REAL historic roster bytes, INNER from a CONSTRUCTED
        shape, because no real specimen needs INNER's hatch. Naming that is the point --
        the first version of this arm asserted the hatch mattered to leg 2 and reded,
        correctly, on its own false premise."""
        # -- leg 1's BOUNDARY: real bytes. Naive `[.;:]` ends a sentence INSIDE `v2.9`,
        #    so no complete version survives and the leg reports nothing at all.
        real_roster = ("  - it never adds binding slots. v2.9, v3.0, v3.1 and v3.2 "
                       "introduce NO new\n    slots; the v2.6 slot")
        with self.subTest(leg="1 BOUNDARY", evidence="real historic bytes"):
            self.assertTrue(self._enumeration_findings(real_roster),
                            "premise: leg 1 catches the real historic roster")
            saved = NoRosterMayReturnTest.BOUNDARY
            try:
                NoRosterMayReturnTest.BOUNDARY = re.compile(r"[.;:]")
                self.assertEqual(
                    [], self._enumeration_findings(real_roster),
                    "a naive sentence boundary no longer blinds leg 1 -- the "
                    "lookarounds in BOUNDARY may have stopped being load-bearing, so "
                    "re-derive the comment above rather than leaving a stale "
                    "justification in place")
            finally:
                NoRosterMayReturnTest.BOUNDARY = saved
        # -- leg 2's INNER: constructed. The subject list is separated from its verb by
        #    an aside naming another version, so INNER must cross a version token. No
        #    specimen in this repository's history has that shape.
        historic = r"(?:[^.;:\n]){0,%d}?"
        # ⛔ the SAME object the R-2 arm drives, not a second copy: these two arms
        # require opposite things of it (this one that it fires at all, R-2 that the
        # dash rule does not silence it), and a fixture written twice drifts once.
        crossing = self.B_R2_ASIDE
        with self.subTest(leg="2 INNER", evidence="constructed shape, not yet observed"):
            self.assertTrue(self._claim_findings(crossing),
                            "premise: leg 2 catches a claim whose INNER span crosses a "
                            "version token")
            self.assertEqual(
                [], self._claim_findings(crossing, inner_class=historic),
                "the period-excluded class no longer blinds leg 2 even on a span that "
                "must cross a version -- INNER's escape hatch has stopped being "
                "load-bearing entirely; drop it and the comment above it")

if __name__ == "__main__":
    unittest.main()
