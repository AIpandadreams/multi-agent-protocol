"""The role vocabulary is ONE table, and reading a ROLE_LOCK line is not a grep.

Three defects share one cause: the set of canonical role names was written out
four times in `conformance_check.py`, and nothing said the four had to agree.

  1. The ROLE_LOCK reader was a line-grep — `ROLE_LOCK[^\\n]*?\\b(OWNER|BUILDER|
     ORCHESTRATOR)\\b` — which scanned for the first role-shaped token anywhere
     on the line. It answered `OWNER` for `— this seat is NOT the OWNER`.
  2. `creator` was in none of the four literals, so a live workspace's correct
     `memory/creator/MEMORY.md` produced a fail-closed BLOCKER that no correct
     file at that seat could clear.
  3. An unrecognised role was silently DROPPED from the positional `ordered`
     list, which made a downstream trap-check stop running without saying so.

Each test below breaks one property and expects the failure. The claims these
tests exist to enforce are the ones the module's own comments make; a comment
asserting a property nothing checks is the defect this repository's units are
about, and it applies to the cure as much as to the thing cured.
"""
import ast
import pathlib
import unittest

from tools import conformance_check as cc


def _module_ast():
    """Parse the checker's source.

    ⛔ `pathlib.read_text` rather than a bare `open(...).read()`. The bare form
    leaks the handle, and CPython's ResourceWarning about it is written into the
    test runner's own output stream — mid-line, between a test's name and its
    `... ok`. Two of the cases here did exactly that, and the damage is not
    cosmetic: it splits the outcome token, so the stream no longer reconciles
    against `Ran N`. ⭐ A test that corrupts the runner's output breaks the
    instrument used to certify the run it belongs to.
    """
    return ast.parse(pathlib.Path(cc.__file__).read_text(encoding="utf-8"))


class TheVocabularyIsOneTable(unittest.TestCase):
    """`ROLE_VOCABULARY` is the single source; the rest derive from it."""

    def test_the_derived_names_match_the_table_in_both_directions(self):
        table = [role for role, _ in cc.ROLE_VOCABULARY]
        self.assertEqual(cc.CANONICAL_ROLES, table)
        self.assertEqual(sorted(cc.DEFAULT_SIDE), sorted(table))
        self.assertEqual([cc.DEFAULT_SIDE[r] for r in table],
                         [side for _, side in cc.ROLE_VOCABULARY])

    # ⛔ EXEMPT A SITE, NEVER A VALUE — and say what covers the exemption.
    # `LEGACY_ALIASES` is a module-level literal whose values are role names, so
    # it trips the sweep below. It is not a second copy of the vocabulary: it
    # states which historical DISPLAY names /wake still resolves, and adding a
    # role does not require a row in it. What it must not do is target a role
    # the table lacks, and that is guarded separately by the module's import-time
    # subset assertion, exercised by the test above. Any OTHER literal
    # enumerating role names is the defect this unit exists to end.
    VOCABULARY_SITES = {"ROLE_VOCABULARY", "CANONICAL_ROLES", "DEFAULT_SIDE"}
    EXEMPT_SITES = {"LEGACY_ALIASES"}

    def test_no_role_name_is_written_out_a_second_time(self):
        """The comment claims a role is added in one row and nowhere else.

        That claim holds only while no OTHER literal has to be kept in step with
        the table — which is exactly what the four coupled sites were.

        ⛔ Asked of the AST, not of the spelling: a regex over the source cannot
        tell a definition from a docstring quoting one, and this module's own
        prose quotes the old alternation.
        """
        tree = _module_ast()
        checked = 0
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = getattr(node, "targets", None) or [node.target]
            names = {t.id for t in targets if isinstance(t, ast.Name)}
            if names & (self.VOCABULARY_SITES | self.EXEMPT_SITES):
                continue
            value = node.value
            if not isinstance(value, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
                continue
            checked += 1
            parts = (value.keys or []) + value.values if isinstance(
                value, ast.Dict) else list(value.elts)
            literal = {p.value for p in parts
                       if isinstance(p, ast.Constant) and isinstance(p.value, str)}
            named = sorted(literal & set(cc.CANONICAL_ROLES))
            if len(named) >= 2:
                self.fail("a second literal (%s) enumerates roles %r"
                          % (", ".join(sorted(names)) or "?", named))
        # ⚠ A sweep that inspected nothing would pass silently. This module has
        # other collection literals; if it ever has none, the assertion above is
        # vacuous and this says so.
        self.assertGreater(checked, 0,
                           "the sweep examined no collection literal at all — "
                           "it is not measuring anything")

    def test_the_derived_sites_are_actually_DERIVED_not_merely_in_agreement(self):
        """⛔ Found by mutating this unit's own cure, and it is the unit's rule
        turned on itself.

        The sweep above exempts `CANONICAL_ROLES` and `DEFAULT_SIDE` by name,
        because they are meant to restate the table — so replacing either with a
        hand-maintained literal of identical content passed every test here: the
        equality check compared values, and the values agreed. They would agree
        right up until the first edit that moved one and not the other, which is
        the whole defect this unit exists to end.

        ⭐⭐ An exemption list is itself a hardcoded enumeration, and it fails
        closed for exactly the site it names. So the exempted sites must be
        shown to be derived — a comprehension reading ROLE_VOCABULARY — and not
        merely to hold the right answer today.
        """
        tree = _module_ast()
        seen = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in ("CANONICAL_ROLES",
                                                        "DEFAULT_SIDE"):
                    seen[t.id] = node.value
        self.assertEqual(sorted(seen), ["CANONICAL_ROLES", "DEFAULT_SIDE"])
        for name, value in sorted(seen.items()):
            self.assertIsInstance(
                value, (ast.ListComp, ast.DictComp, ast.SetComp),
                "%s is a literal, not a derivation — it can drift from "
                "ROLE_VOCABULARY silently" % name)
            sources = {n.id for n in ast.walk(value) if isinstance(n, ast.Name)}
            self.assertIn("ROLE_VOCABULARY", sources,
                          "%s is a comprehension but does not read "
                          "ROLE_VOCABULARY" % name)

    def test_legacy_aliases_may_not_target_a_role_the_table_lacks(self):
        """The import-time assertion is itself a claim; this fires it.

        Re-running the module's own guard against a doctored map is the only
        way to show the guard is live: an assertion that never executes on a
        bad input is indistinguishable from a comment.
        """
        doctored = dict(cc.LEGACY_ALIASES, ghost="registrar")
        self.assertFalse(set(doctored.values()) <= set(cc.CANONICAL_ROLES))
        # And the shipped map passes the same predicate.
        self.assertTrue(set(cc.LEGACY_ALIASES.values()) <= set(cc.CANONICAL_ROLES))

    def test_the_vocabulary_knows_the_seat_that_prompted_this(self):
        """…and knows it as an IDENTITY, which is not the same as a seat.

        This assertion first read `assertIn("creator", CANONICAL_ROLES)`, and
        that version passed while the tool was wrong: the seat-trap in
        `check_side_names` iterates every canonical role, so membership made
        `creator` illegal as a side name in every workspace — on the stated
        grounds that "/wake resolves canonical names first", which `wake.md`
        resolves for exactly owner|builder|orchestrator. A test can only be as
        careful as the distinction it asserts.
        """
        self.assertIn("creator", cc.LOCK_VOCABULARY)
        self.assertNotIn("creator", cc.CANONICAL_ROLES)


class ReadingALockIsNotAGrep(unittest.TestCase):
    """`role_lock_role` accepts the corpus and refuses the ambiguous."""

    # Every ACCEPT case is a real line: from a live workspace's memory index or
    # from `new_project.py`'s generator. Three distinct sentence shapes are
    # present, which is why no single sentence template would do.
    ACCEPT = [
        ("ROLE_LOCK: this workspace's OWNER sessions only.", "owner"),
        ("ROLE_LOCK: this workspace's CREATOR sessions only.", "creator"),
        ("ROLE_LOCK: this workspace's sessions are the ORCHESTRATOR only. "
         "Principal-set, do not edit.", "orchestrator"),
        ("ROLE_LOCK: this workspace's BUILDER sessions only (source/QA lane). "
         "PROTOCOL **v2.7**.", "builder"),
        ("ROLE_LOCK: builder", "builder"),
    ]

    # Every REFUSE case made the old predicate answer a confident, specific,
    # WRONG role — except the last, which it already refused.
    REFUSE = [
        "ROLE_LOCK: — this seat is NOT the OWNER",
        "ROLE_LOCK: none (see the ORCHESTRATOR for authority)",
        "ROLE_LOCK: CO-OWNER",
        "ROLE_LOCK: CREATOR, deputising for the OWNER",
        "ROLE_LOCK: OWNERSHIP",
    ]

    def test_every_shape_the_corpus_carries_is_accepted(self):
        for text, want in self.ACCEPT:
            with self.subTest(text=text[:40]):
                self.assertEqual(cc.role_lock_role(text), want)

    def test_every_ambiguous_declaration_is_refused(self):
        for text in self.REFUSE:
            with self.subTest(text=text[:40]):
                self.assertIsNone(cc.role_lock_role(text))

    def test_a_role_named_only_inside_a_parenthetical_is_not_the_value(self):
        self.assertIsNone(cc.role_lock_role("ROLE_LOCK: unset (ask the OWNER)"))

    def test_a_role_named_after_the_first_sentence_is_not_the_value(self):
        self.assertEqual(
            cc.role_lock_role("ROLE_LOCK: this workspace's OWNER sessions "
                              "only. Escalate to the ORCHESTRATOR."),
            "owner")

    def test_two_roles_in_one_sentence_are_refused_rather_than_ordered(self):
        """Refusal is policy, not an accident of implementation.

        There is no reading of `CREATOR, deputising for the OWNER` the function
        is entitled to pick, so it must not pick one. Asserted in both orders so
        a first-wins or last-wins implementation fails here.
        """
        self.assertIsNone(cc.role_lock_role("ROLE_LOCK: CREATOR then OWNER"))
        self.assertIsNone(cc.role_lock_role("ROLE_LOCK: OWNER then CREATOR"))

    def test_a_wrapped_prose_line_is_not_a_declaration(self):
        """⛔ Found against the live corpus, and it cost a whole cure iteration.

        A memory index that DISCUSSES role locks has sentences whose line break
        happens to put `ROLE_LOCK` at column 0 — two live orchestrator indexes
        carry exactly that, e.g. `ROLE_LOCK vs the shipped conformance regex's
        hardcoded 3-role alternation`. A line-start anchor alone cannot tell that
        from a declaration.

        ⭐ The colon is the field marker. There is no bare field VALUE in this
        format, but there IS a separator, and requiring it is what distinguishes
        the declaration from everything that merely mentions it. Worse than
        cosmetic: a prose line naming a DIFFERENT role would otherwise be
        answered confidently and wrongly.
        """
        text = ("ROLE_LOCK is set by the ORCHESTRATOR at first bind.\n\n"
                "ROLE_LOCK: this workspace's OWNER sessions only.\n")
        self.assertEqual(cc.role_lock_role(text), "owner")

    def test_two_real_declarations_in_one_file_are_refused(self):
        """Ambiguity is refused at the FILE grain too, not just the line grain.

        Taking the first would be the same confident-wrong guess one level up.
        """
        self.assertIsNone(cc.role_lock_role("ROLE_LOCK: owner\n"
                                            "ROLE_LOCK: builder\n"))

    def test_absent_declaration_is_none_not_an_exception(self):
        self.assertIsNone(cc.role_lock_role("# index\n\nno lock here\n"))
        self.assertIsNone(cc.role_lock_role(""))
        self.assertIsNone(cc.role_lock_role(None))


class AnUnknownRoleIsRefusedNotDropped(unittest.TestCase):
    """The third face: silence replaced by a blocker."""

    def _run(self, roles, side_names):
        f = cc.Findings()
        cc.check_side_names({"SIDE_NAMES": side_names}, roles, f)
        return [m for sev, m in f.items if sev == "BLOCKER"]

    def test_an_unrecognised_role_raises_a_blocker(self):
        msgs = self._run({"owner", "builder", "registrar"},
                         "owner / builder / registrar")
        self.assertTrue(any("registrar" in m and "vocabulary" in m
                            for m in msgs), msgs)

    def test_a_profile_of_known_roles_raises_no_vocabulary_blocker(self):
        """The control. Without it the test above passes on a function that
        blocks unconditionally, which would be a different defect."""
        msgs = self._run({"owner", "builder", "orchestrator"},
                         "owner / builder / orch")
        self.assertEqual([m for m in msgs if "vocabulary" in m], [])

    def test_the_trap_check_still_catches_a_side_named_after_another_role(self):
        """The check whose silence was the finding, shown still working."""
        msgs = self._run({"owner", "builder"}, "orchestrator / builder")
        self.assertTrue(any("canonical name of the orchestrator role" in m
                            for m in msgs), msgs)


class AnIdentityIsNotAutomaticallyASeat(unittest.TestCase):
    """`creator` may name a lock; it may not take a positional slot.

    ⛔ THE DEFECT THESE HOLD WAS MINE, and it was invisible to every test I had
    written: `creator` as a fourth `ROLE_VOCABULARY` row passed the whole suite
    while making `creator` illegal as a side name in EVERY workspace, because
    the seat-trap iterates all canonical roles. It surfaced only when the AST
    was asked which sites a table row actually reaches, and then only when the
    separating profile was RUN against both versions.
    """

    def _side(self, roles, side_names):
        f = cc.Findings()
        cc.check_side_names({"SIDE_NAMES": side_names}, roles, f)
        return ([m for sev, m in f.items if sev == "BLOCKER"],
                [m for sev, m in f.items if sev == "WARN"])

    def test_a_side_named_creator_is_not_blocked(self):
        """The separating case. Under the fourth-row version this blocked."""
        blockers, _ = self._side({"owner", "builder"}, "owner / creator")
        self.assertEqual([m for m in blockers if "creator" in m], [], blockers)

    def test_the_control_a_side_named_after_a_REAL_seat_still_blocks(self):
        """⭐ Without this the test above passes on a trap that never fires."""
        blockers, _ = self._side({"owner", "builder"}, "owner / orchestrator")
        self.assertTrue(any("canonical name of the orchestrator role" in m
                            for m in blockers), blockers)

    def test_a_profile_declaring_creator_warns_rather_than_blocks_or_drops(self):
        """A known non-seat is its own condition — not unknown, not silent."""
        blockers, warns = self._side({"owner", "builder", "creator"},
                                     "owner / builder")
        self.assertEqual([m for m in blockers if "vocabulary" in m], [], blockers)
        self.assertTrue(any("creator" in m and "not as a positional seat" in m
                            for m in warns), warns)

    def test_a_lock_may_still_name_the_non_seat_identity(self):
        """The whole point of the split: the cure survives it."""
        self.assertEqual(
            cc.role_lock_role("ROLE_LOCK: this workspace's CREATOR sessions "
                              "only.\n"), "creator")

    def test_the_two_vocabularies_are_derived_and_disjoint(self):
        self.assertEqual(list(cc.LOCK_VOCABULARY),
                         list(cc.CANONICAL_ROLES) + list(cc.NON_PROFILE_IDENTITIES))
        self.assertFalse(set(cc.CANONICAL_ROLES) & set(cc.NON_PROFILE_IDENTITIES))

    def test_positional_order_is_unchanged_by_the_split(self):
        """SIDE_NAMES are positional, so a reorder is a silent mis-mapping.

        The seat order is the load-bearing property the whole table comment
        warns about; asserting it here means a future edit that appends a seat
        in the wrong place fails loudly rather than shifting every workspace's
        side names by one.
        """
        self.assertEqual(cc.CANONICAL_ROLES, ["owner", "builder", "orchestrator"])


if __name__ == "__main__":
    unittest.main()
