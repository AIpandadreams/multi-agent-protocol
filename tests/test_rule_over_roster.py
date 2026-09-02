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

Two arms below are RED-BY-DESIGN against the pre-rewrite module:
`test_the_advisory_list_offers_NON_ROLE_DIRS` and
`test_no_prose_roster_claims_no_new_slots_over_a_slot_bearing_range`.
"""
import importlib.util
import re
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
        rows = {r.split()[1]: r for r in mw.hop_table()}
        for v, n in expected_hop_counts.items():
            self.assertIn(f"{n} hop(s)", rows[v],
                          f"pinned {v} should walk {n} hops, per the roster this rule "
                          f"replaced; got: {rows[v]}")
        self.assertIn("no-op", rows[mw.NEWEST],
                      "the newest pin was a no-op in the roster and must stay one")

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


class NoRosterMayReturnTest(unittest.TestCase):
    """The durable half of the cure. Fixing the two rosters fixes today; this arm is what
    stops the next stamp bump from hand-writing a third one that disagrees again."""

    # ⛔ `\.(?=\d)` is load-bearing. The first version of this pattern used
    # `[^.\n]{0,160}` to stop at a sentence boundary -- which also stopped it at the
    # period INSIDE a version token, so the scan saw "the v2" and never a complete
    # `vN.N`. The guard could not fire at all and reported green on the very sentence it
    # was written to catch. A period is now admitted only when a digit follows it, so a
    # version survives the scan and a sentence end still ends it. Caught by
    # test_the_guard_can_actually_fire, which is the only reason it is not still true.
    @staticmethod
    def _logical(text):
        """(normalized_text, [line number for each normalized char]).

        Source prose wraps. A guard that scans PHYSICAL lines cannot see a claim whose
        trigger phrase and subject noun land on opposite sides of a line break, which is
        the normal shape of an 80-column comment -- so it reports green on exactly the
        sentences it exists to catch. Leading whitespace and a leading comment marker are
        stripped so a wrapped comment reads as one sentence
        [[test-drive-must-match-its-fail-shape]]."""
        out, lines = [], []
        for n, raw in enumerate(text.splitlines(), start=1):
            s = raw.strip()
            if s.startswith("#"):
                s = s[1:].strip()
            if out:
                out.append(" ")
                lines.append(n)
            out.append(s)
            lines.extend([n] * len(s))
        return "".join(out), lines

    NO_NEW_SLOTS = re.compile(
        r"(?:none of|introduce[s]? no|no new)(?:[^.\n]|\.(?=\d)){0,200}",
        re.IGNORECASE)
    VERSION = re.compile(r"\bv\d+\.\d+\b")

    def test_no_prose_roster_claims_no_new_slots_over_a_slot_bearing_range(self):
        """⭐ RED-BY-DESIGN against the pre-rewrite module: both original rosters matched.

        The rule enforced is narrow on purpose, so it cannot false-fire on ordinary prose:
        a sentence may say "no new binding slots", and it may name versions, but it must
        not do BOTH while naming a version the table says introduced one."""
        norm, lineno = self._logical(SRC.read_text(encoding="utf-8"))
        introducing = set(mw.SLOT_INTRODUCED_IN.values())
        offenders = []
        for m in self.NO_NEW_SLOTS.finditer(norm):
            frag = m.group(0)
            if "slot" not in frag.lower():
                continue
            bad = set(self.VERSION.findall(frag)) & introducing
            if bad:
                offenders.append((lineno[m.start()], sorted(bad), frag.strip()[:120]))
        self.assertEqual([], offenders,
                         "a 'no new slots' claim names a version that DID introduce one; "
                         "state the rule and derive from SLOT_INTRODUCED_IN instead of "
                         "writing a roster:\n" + "\n".join(map(str, offenders)))

    def test_the_guard_can_actually_fire(self):
        """A no-op control. The arm above passes on a clean file, which is also what it
        would do if the pattern matched nothing ever -- an unbounded negative that is
        never red [[instrument-must-prove-it-fired]]. So feed it the ORIGINAL sentence and
        require a hit."""
        # ⛔ Both planted rosters are reproduced WRAPPED, exactly as they stood in the
        # source -- including the line break that splits the trigger phrase from the word
        # "slot". The first version of this control planted a single-line paraphrase and
        # passed while the guard found ZERO offenders in the real pre-rewrite file. A
        # control written from a restatement of the claim tests the restatement.
        planted = {
            "docstring roster (was line ~75)":
                "  - it never adds binding slots. v2.9, v3.0, v3.1 and v3.2 introduce NO new\n"
                "    slots; the v2.6 slot",
            "advisory roster (was line ~175)":
                "# adding\", never stamped. None of v2.8, v2.9, v3.0, v3.1 or v3.2 introduces\n"
                "# new binding slots, so this list is unchanged across every later hop.",
        }
        introducing = set(mw.SLOT_INTRODUCED_IN.values())
        for label, sample in planted.items():
            norm, _ln = self._logical(sample)
            hits = [m.group(0) for m in self.NO_NEW_SLOTS.finditer(norm)
                    if "slot" in m.group(0).lower()
                    and set(self.VERSION.findall(m.group(0))) & introducing]
            self.assertTrue(hits, f"the guard did not fire on {label} -- the exact bytes "
                                  f"it was written to catch. It is decorative.")


if __name__ == "__main__":
    unittest.main()
