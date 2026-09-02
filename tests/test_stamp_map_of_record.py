#!/usr/bin/env python3
"""Mutation tests for mirror_check section 15 — the advertised protocol stamp
must have a row in CHANGELOG.md's header table.

    python -m unittest discover -s tests

⛔ THE DEFECT THIS GATE EXISTS FOR. The v3.1 -> v3.2 restamp moved every per-file
stamp, the README protocol badge and the plugin manifest description, and did NOT
add a table row. The repository advertised, on its front page and in the plugin
it publishes, a protocol version its own map of record had never heard of — and
every gate in mirror_check.py was green while that was true, because no gate
compared those surfaces. Section 5 checks that files carry the CURRENT stamp, and
the current stamp is whatever the source says it is: a claim cannot fail a check
that reads it as the standard.

The gate was written BEFORE the fix, against the failing tree, so its red is a
measurement of the real artifact rather than a prediction about a planted one:

    $ python tools/mirror_check.py
    MIRROR CHECK: 2 finding(s)
      - advertised stamp with no row in the map of record: the protocol badge in
        README.md advertises PROTOCOL v3.2, but CHANGELOG.md's header table has
        no row naming it (it knows v3.1, v2.9, v2.8, v2.7, v2.6, v2.5). ...
      - advertised stamp with no row in the map of record: the plugin manifest
        description in plugins/agent-protocol/.claude-plugin/plugin.json ...

Both surfaces, named separately, on the tree as the principal found it. Every
arm below asserts the SPECIFIC finding text, never merely `rc != 0`: a mutation
that reds the gate for some other reason is a test passing for the wrong reason,
and this file's whole subject is gates that were green for the wrong reason.
"""
import re
import unittest
from pathlib import Path

try:                                    # discovery (`-s tests`) puts tests/ on the path
    from _mirror_fixture import repo_copy, run_mirror_check
except ImportError:                     # `python -m unittest tests.test_...` does not
    from tests._mirror_fixture import repo_copy, run_mirror_check

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = "CHANGELOG.md"
README = "README.md"
MANIFEST = "plugins/agent-protocol/.claude-plugin/plugin.json"
HEADER = "| repo release | protocol version | notes |"

BADGE = re.compile(r"img\.shields\.io/badge/protocol-(v\d+\.\d+)-")
MANIFEST_STAMP = re.compile(r"PROTOCOL (v\d+\.\d+)")


def _current_stamp():
    """The stamp the tree advertises, read from the badge rather than written in
    here. A test that hard-codes 'v3.2' starts failing at the next restamp for a
    reason that has nothing to do with the gate [[anchor-validity-discipline]]."""
    m = BADGE.search((ROOT / README).read_text(encoding="utf-8"))
    assert m, "premise of this suite: README.md carries a protocol badge"
    return m.group(1)


STAMP = _current_stamp()


def _sub(repo, rel, old, new, count=1):
    p = repo / rel
    t = p.read_text(encoding="utf-8")
    assert t.count(old) >= count, f"{rel}: anchor found {t.count(old)}x: {old!r}"
    p.write_text(t.replace(old, new, count), encoding="utf-8", newline="")


class FixtureCanaryTest(unittest.TestCase):
    """The control for every arm below. Each one asserts a planted defect is
    REPORTED; if the unmutated copy is already red, every such assertion passes
    without the plant doing anything. The canary is what separates "the gate
    caught my mutation" from "the gate was already complaining"."""

    def test_the_pristine_copy_is_green(self):
        with repo_copy() as repo:
            rc, out = run_mirror_check(repo)
            self.assertEqual(rc, 0, out)


class AdvertisedStampNeedsARowTest(unittest.TestCase):

    def test_deleting_the_row_for_the_advertised_stamp_is_caught(self):
        """⭐ The defect as it actually stood: the map loses the stamp the badge
        advertises. Both advertisers must be named — a gate that reports one and
        stops would let the second surface drift unseen."""
        with repo_copy() as repo:
            p = repo / CHANGELOG
            lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
            i = next(n for n, ln in enumerate(lines) if ln.strip() == HEADER)
            kept = [ln for n, ln in enumerate(lines)
                    if not (n > i and ln.startswith("| ")
                            and f"| {STAMP} |" in ln)]
            self.assertLess(len(kept), len(lines),
                            f"premise: some row names {STAMP}")
            p.write_text("".join(kept), encoding="utf-8", newline="")

            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("advertised stamp with no row in the map of record", out)
            self.assertIn(README, out)
            self.assertIn(MANIFEST, out)

    def test_a_badge_bumped_ahead_of_the_map_is_caught(self):
        """The forward direction — the restamp half. A badge may only name a
        stamp the table has shipped, so bumping it alone is red."""
        with repo_copy() as repo:
            _sub(repo, README, f"protocol-{STAMP}-", "protocol-v9.9-")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertRegex(out, r"advertised stamp with no row.*README\.md "
                                  r"advertises PROTOCOL v9\.9")

    def test_the_manifest_bumped_ahead_of_the_map_is_caught(self):
        with repo_copy() as repo:
            _sub(repo, MANIFEST, f"PROTOCOL {STAMP}", "PROTOCOL v9.9")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertRegex(out, r"advertised stamp with no row.*plugin\.json "
                                  r"advertises PROTOCOL v9\.9")

    def test_two_advertisers_naming_different_ROWED_stamps_is_caught(self):
        """Membership is not agreement. Both stamps below have rows, so the
        row check is satisfied on each surface and the repo still tells a reader
        two different things — which is why the disagreement is its own finding
        and not a by-product of the membership one."""
        rows = [ln for ln in (ROOT / CHANGELOG).read_text(encoding="utf-8")
                .splitlines() if ln.startswith("| ")]
        other = next(m.group(1) for ln in rows
                     if (m := re.search(r"\|\s*(v\d+\.\d+)\s*\|", ln))
                     and m.group(1) != STAMP)
        with repo_copy() as repo:
            _sub(repo, MANIFEST, f"PROTOCOL {STAMP}", f"PROTOCOL {other}")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("advertised stamps disagree", out)
            self.assertNotIn("advertised stamp with no row in the map of record",
                             out)

    def test_the_gate_reads_ONLY_the_header_table(self):
        """⭐ A positive control on the gate's BOUND. CHANGELOG.md carries other
        markdown tables, and a scan for row-shaped lines anywhere in the file
        would read them as releases — so a stray `| x | v9.9 |` somewhere in the
        history would silently license the badge. Plant exactly that and require
        the finding to survive."""
        with repo_copy() as repo:
            _sub(repo, README, f"protocol-{STAMP}-", "protocol-v9.9-")
            p = repo / CHANGELOG
            p.write_text(p.read_text(encoding="utf-8")
                         + "\n\n| not a release | v9.9 | not the map |\n",
                         encoding="utf-8", newline="")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertRegex(out, r"advertised stamp with no row.*README\.md "
                                  r"advertises PROTOCOL v9\.9")


class TheGateFailsClosedTest(unittest.TestCase):
    """Every surface this gate reads is prose or a manifest field, and both get
    reworded. A gate whose subject moves out from under it goes green while
    checking nothing — the same false green as the defect it was written for, one
    level up [[instrument-must-prove-it-fired]]."""

    def test_a_reworded_badge_fails_closed(self):
        with repo_copy() as repo:
            _sub(repo, README, f"img.shields.io/badge/protocol-{STAMP}-",
                 f"example.invalid/protocol/{STAMP}/")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("no longer machine-readable", out)
            self.assertIn("the protocol badge in README.md", out)

    def test_a_manifest_that_drops_the_stamp_fails_closed(self):
        with repo_copy() as repo:
            _sub(repo, MANIFEST, f"(PROTOCOL {STAMP})", "(the protocol)")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("no longer machine-readable", out)
            self.assertIn("the plugin manifest description", out)

    def test_a_renamed_table_header_fails_closed(self):
        with repo_copy() as repo:
            _sub(repo, CHANGELOG, HEADER, "| version | stamp | notes |")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("no longer carries the header row", out)
            self.assertIn("Not a silent skip", out)

    def test_a_deleted_advertiser_fails_closed(self):
        """Absence is the one shape a content check can never see: nothing to
        match means nothing to report [[green-coverage-discipline]]."""
        with repo_copy() as repo:
            (repo / MANIFEST).unlink()
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("it advertises the plugin manifest description", out)


if __name__ == "__main__":
    unittest.main()
