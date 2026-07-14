"""Mutation tests for the two guards added because "remember to update the other
copy" is not a control.

- **Semantic dedup (mirror_check §12).** The heading-based dedup guard cannot see
  a core rule restated as PROSE in a role file — which is exactly how the
  encoding baseline ended up in three files at once, drifting in three wordings.
- **Co-maintained twins (§13).** A doc and its rendered `.html`; the amendment
  header and the two GitHub templates that deliver it. Both pairs shipped a
  near-miss: the twin the reviewer never saw, and the template that kept the
  weaker contract after the guide was amended.

Each test breaks exactly one thing and asserts the gate names it.
"""
import re
import unittest

try:                                    # discovery (`-s tests`) puts tests/ on the path
    from _mirror_fixture import repo_copy, run_mirror_check
except ImportError:                     # `python -m unittest tests.test_...` does not
    from tests._mirror_fixture import repo_copy, run_mirror_check

OWNER_OPS = ("plugins/agent-protocol/skills/owner-engine-agent/references/"
             "ops-gotchas.md")
CORE = "plugins/agent-protocol/skills/agent-core/references/channel-core.md"
BOOT_MD = "docs/CREATOR-SEAT-BOOTSTRAP.md"
BOOT_HTML = "docs/CREATOR-SEAT-BOOTSTRAP.html"
HEADER_COPIES = ["CONTRIBUTING.md",
                 ".github/PULL_REQUEST_TEMPLATE.md",
                 ".github/ISSUE_TEMPLATE/protocol_amendment.md"]


class FixtureCanaryTest(unittest.TestCase):
    """The control for every mutation test below: the UNMUTATED copy must be
    green. If the fixture ever fails on a clean tree — a stray finding, a
    git-resolution problem — then every `assertNotEqual(rc, 0)` here would pass
    for the wrong reason, which is the false-green this whole suite exists to
    prevent."""

    def test_the_pristine_copy_is_green(self):
        with repo_copy() as repo:
            rc, out = run_mirror_check(repo)
            self.assertEqual(rc, 0, out)


class BaselineTripwireTest(unittest.TestCase):
    """A TRIPWIRE, not a paraphrase detector — and the tests say so. It catches
    the copy-paste (the common case, and the one that actually happened); a
    re-worded restatement is a reviewer's job, and the gate's docstring admits
    it rather than letting the CHANGELOG claim otherwise."""

    def test_a_role_file_restating_a_baseline_sentence_is_caught(self):
        for phrase in ("A green suite is not a shippable artifact.",
                       "Every file here is written UTF-8 without BOM.",
                       "Gate every machine-read artifact as bytes."):
            with self.subTest(phrase=phrase), repo_copy() as repo:
                p = repo / OWNER_OPS
                p.write_text(p.read_text(encoding="utf-8") + f"\n\n{phrase}\n",
                             encoding="utf-8")
                rc, out = run_mirror_check(repo)
                self.assertNotEqual(rc, 0, f"tripwire missed: {phrase}")
                self.assertIn("restates the core baseline", out)

    def test_re_casing_and_re_wrapping_do_not_evade_the_tripwire(self):
        with repo_copy() as repo:
            p = repo / OWNER_OPS
            p.write_text(p.read_text(encoding="utf-8") +
                         "\n\nA GREEN suite\nis not a shippable\nartifact.\n",
                         encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("restates the core baseline", out)

    def test_inline_markdown_emphasis_does_not_evade_the_tripwire(self):
        # `**green**` / ``UTF-8`` inside a listed sentence used to slip past a
        # whitespace+case-only normalizer.
        with repo_copy() as repo:
            p = repo / OWNER_OPS
            p.write_text(p.read_text(encoding="utf-8") +
                         "\n\nA **green** suite is not a `shippable` artifact.\n",
                         encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("restates the core baseline", out)

    def test_the_tripwire_scans_transports_not_only_role_files(self):
        # transports/local-fs.md was edited THIS release to stop carrying the
        # baseline; the tripwire must cover it, or the fix is unguarded.
        with repo_copy() as repo:
            p = repo / "transports" / "local-fs.md"
            p.write_text(p.read_text(encoding="utf-8") +
                         "\n\nEvery file here is written UTF-8 without BOM.\n",
                         encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("restates the core baseline", out)

    def test_the_guard_fails_loudly_if_the_core_drops_the_rule(self):
        # A dedup guard that silently passes once the rule is deleted from the
        # core would enforce nothing at all.
        with repo_copy() as repo:
            p = repo / CORE
            p.write_text(
                p.read_text(encoding="utf-8")
                .replace("A green suite is not a shippable artifact", "x"),
                encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("no longer states the baseline phrase", out)


class TwinGuardTest(unittest.TestCase):
    """Every mutation here defeated the FIRST version of this gate. It compared
    heading COUNTS and matched only case-study titles shaped like "The ...", so
    a renamed heading, an un-"The" title, and a table row all sailed through —
    and a table row is precisely the drift the gate was built for."""

    def _mutate(self, rel, addition):
        with repo_copy() as repo:
            p = repo / rel
            p.write_text(p.read_text(encoding="utf-8") + addition,
                         encoding="utf-8")
            return run_mirror_check(repo)

    def test_a_case_study_added_to_the_md_alone_is_caught(self):
        rc, out = self._mutate(
            BOOT_MD, "\n**The forgotten twin.** Added to the markdown only.\n")
        self.assertNotEqual(rc, 0)
        self.assertIn("twin drift", out)
        self.assertIn("the forgotten twin", out)

    def test_a_case_study_added_to_the_html_alone_is_caught(self):
        rc, out = self._mutate(
            BOOT_HTML,
            "\n<p><strong>The orphan render.</strong> html only.</p>\n")
        self.assertNotEqual(rc, 0)
        self.assertIn("twin drift", out)
        self.assertIn("the orphan render", out)

    def test_a_bold_title_that_does_not_start_with_The_is_caught(self):
        # The old regex only saw "**The …**" titles.
        rc, out = self._mutate(
            BOOT_MD, "\n**A markdown-only case.** Body text.\n")
        self.assertNotEqual(rc, 0)
        self.assertIn("a markdown-only case", out)

    def test_a_renamed_heading_is_caught(self):
        # Counts stay equal — identities do not. The old gate compared counts.
        with repo_copy() as repo:
            p = repo / BOOT_MD
            body = p.read_text(encoding="utf-8")
            first = re.search(r"^## (.+)$", body, re.M).group(1)
            p.write_text(body.replace(f"## {first}", "## Renamed section", 1),
                         encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("renamed section", out)

    def test_a_catalog_table_row_added_to_the_md_alone_is_caught(self):
        # THE motivating defect: the near-miss that started this release was a
        # table row present in one twin and not the other.
        rc, out = self._mutate(
            BOOT_MD, "\n| 10 | **Brand-new SOP** | Some rule. |\n")
        self.assertNotEqual(rc, 0)
        self.assertIn("twin drift", out)

    def test_a_registry_count_that_outruns_the_catalog_is_caught(self):
        # "The registry advertises nine entries; the rendering shows eight."
        with repo_copy() as repo:
            p = repo / BOOT_MD
            body = p.read_text(encoding="utf-8")
            p.write_text(re.sub(r"^\|\s*9\s*\|.*$", "", body, flags=re.M),
                         encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("count drift", out)

    # --- fail-loud / fail-closed: every one of these PASSED an earlier draft ---

    def test_deleting_a_twin_fails_loudly(self):
        # The pair invariant cannot be "skip the check when half the pair is
        # gone" — deleting either twin used to pass green.
        for victim in (BOOT_MD, BOOT_HTML):
            with self.subTest(victim=victim), repo_copy() as repo:
                (repo / victim).unlink()
                rc, out = run_mirror_check(repo)
                self.assertNotEqual(rc, 0)
                self.assertIn("twin gate blind", out)

    def test_a_prose_only_bold_run_in_one_twin_is_caught(self):
        # An HTML-only <strong> WITH ATTRIBUTES used to slip the bare-<strong>
        # regex.
        rc, out = self._mutate(
            BOOT_HTML, '\n<p><strong class="x">Attributed orphan</strong></p>\n')
        self.assertNotEqual(rc, 0)
        self.assertIn("attributed orphan", out)

    def test_a_table_row_added_to_the_html_alone_is_caught(self):
        rc, out = self._mutate(
            BOOT_HTML, "\n<table><tr><td>77</td><td>html-only row</td></tr></table>\n")
        self.assertNotEqual(rc, 0)
        self.assertIn("twin drift", out)

    def test_matched_code_examples_do_not_false_positive(self):
        # Code carrying literal ##/**/|…| markup, added to BOTH twins, must NOT be
        # read as real structure — for FENCED and INDENTED code alike (mask_code
        # blanks both). This is a green-EXPECTED test, so it must not pass merely
        # because nothing was planted: a SENTINEL asserts the markup really landed
        # in each file before the green is trusted. (Codex r5: the prior version
        # asserted only `assertNotIn`, which the clean tree already satisfies.)
        cases = {
            "fenced": (
                "\n```\n## not a heading\n**not bold** | not | a | row |\n```\n",
                "\n<pre><code>## not a heading\n"
                "**not bold** | not | a | row |\n</code></pre>\n"),
            "indented": (
                "\n    ## not a heading\n    **not bold** | not | a | row |\n",
                "\n<pre><code>    ## not a heading\n"
                "    **not bold** | not | a | row |\n</code></pre>\n"),
        }
        for kind, (md_block, html_block) in cases.items():
            with self.subTest(code=kind), repo_copy() as repo:
                md_p, html_p = repo / BOOT_MD, repo / BOOT_HTML
                md_p.write_text(md_p.read_text(encoding="utf-8") + md_block,
                                encoding="utf-8")
                html_p.write_text(html_p.read_text(encoding="utf-8") + html_block,
                                  encoding="utf-8")
                # sentinel: the very markup whose masking we assert is really here
                self.assertIn("## not a heading",
                              md_p.read_text(encoding="utf-8"), f"{kind}: md write lost")
                self.assertIn("## not a heading",
                              html_p.read_text(encoding="utf-8"), f"{kind}: html write lost")
                rc, out = run_mirror_check(repo)
                # the promised green: matched code in BOTH twins must not just
                # avoid a twin-drift finding, it must leave the whole gate green —
                # otherwise an unrelated red before the twin comparison would still
                # satisfy assertNotIn (codex r6).
                self.assertEqual(rc, 0, out)
                self.assertNotIn("twin drift", out)

    def test_a_numeral_registry_claim_does_not_disarm_the_count_gate(self):
        # Rewriting "nine" -> "9" used to silently skip §14; then a catalog row
        # could be deleted undetected. Now a numeral is still checked.
        with repo_copy() as repo:
            reg = repo / "docs" / "SOP-REGISTRY.md"
            reg.write_text(reg.read_text(encoding="utf-8")
                           .replace("nine numbered SOPs", "9 numbered SOPs"),
                           encoding="utf-8")
            boot = repo / BOOT_MD
            boot.write_text(re.sub(r"^\|\s*9\s*\|.*$", "",
                                   boot.read_text(encoding="utf-8"), flags=re.M),
                            encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("count", out)

    def test_a_reworded_registry_claim_fails_closed(self):
        # If the count sentence stops matching entirely, that is a finding —
        # not a silently disabled gate.
        with repo_copy() as repo:
            reg = repo / "docs" / "SOP-REGISTRY.md"
            reg.write_text(reg.read_text(encoding="utf-8")
                           .replace("numbered SOPs", "listed procedures"),
                           encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("count gate", out)


class AmendmentHeaderParityTest(unittest.TestCase):
    def test_dropping_a_field_from_any_copy_is_caught(self):
        # The near-miss this guards: `artifact set` / `omission search` landing in
        # CONTRIBUTING.md while the PR template GitHub actually injects keeps the
        # old touched-files-only contract.
        for rel in HEADER_COPIES:
            for field in ("artifact set", "omission search"):
                with self.subTest(path=rel, field=field), repo_copy() as repo:
                    p = repo / rel
                    p.write_text(
                        p.read_text(encoding="utf-8").replace(field, "REMOVED"),
                        encoding="utf-8")
                    rc, out = run_mirror_check(repo)
                    self.assertNotEqual(rc, 0)
                    self.assertIn("amendment-header drift", out)
                    self.assertIn(field, out)

    def test_deleting_the_label_while_the_words_survive_in_prose_is_caught(self):
        # The bypass: the first version substring-searched the whole file, so
        # removing the `artifact set:` LABEL passed as long as the phrase
        # appeared anywhere — including in the prose explaining the field.
        for rel in HEADER_COPIES:
            with self.subTest(path=rel), repo_copy() as repo:
                p = repo / rel
                body = p.read_text(encoding="utf-8")
                p.write_text(re.sub(r"artifact set\s*:", "artifact set —", body),
                             encoding="utf-8")
                rc, out = run_mirror_check(repo)
                self.assertNotEqual(rc, 0)
                self.assertIn("artifact set", out)

    def test_a_field_added_to_one_copy_alone_is_caught(self):
        # The field set is DERIVED from the three copies, not hard-coded — so a
        # NEW field drifts loudly instead of silently.
        with repo_copy() as repo:
            p = repo / ".github" / "PULL_REQUEST_TEMPLATE.md"
            body = p.read_text(encoding="utf-8")
            p.write_text(body.replace("version impact: none",
                                      "blast radius: none\nversion impact: none"),
                         encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("blast radius", out)

    def test_a_digit_bearing_single_copy_label_is_caught(self):
        # An earlier LABEL_RE accepted only letters/space/hyphen/slash, so a
        # label like "risk 2:" added to one copy was invisible to the union.
        with repo_copy() as repo:
            p = repo / ".github" / "PULL_REQUEST_TEMPLATE.md"
            body = p.read_text(encoding="utf-8")
            p.write_text(body.replace("version impact: none",
                                      "risk 2: none\nversion impact: none"),
                         encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("risk 2", out)

    def test_dropping_fingerprint_from_all_non_exempt_copies_is_caught(self):
        # `fingerprint` carries the set digest. A derived-union check alone
        # cannot see a field that is nowhere; it is in REQUIRED_FIELDS so it
        # must exist in every copy that does not exempt it.
        with repo_copy() as repo:
            for rel in ("CONTRIBUTING.md", ".github/PULL_REQUEST_TEMPLATE.md"):
                p = repo / rel
                p.write_text(re.sub(r"fingerprint\s*:", "fingerprint —",
                                    p.read_text(encoding="utf-8")),
                             encoding="utf-8")
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("fingerprint", out)

    def test_deleting_a_header_copy_is_caught(self):
        with repo_copy() as repo:
            (repo / ".github" / "PULL_REQUEST_TEMPLATE.md").unlink()
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("amendment-header copy missing", out)


if __name__ == "__main__":
    unittest.main()
