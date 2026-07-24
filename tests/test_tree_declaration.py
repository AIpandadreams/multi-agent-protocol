"""v1.2.6 gates: the tree declaration, and the PowerShell BOM inversion.

These are a MIX, and the mix is deliberate:
  - MUTATION tests plant one defect and assert the gate NAMES it. A gate that has
    never been seen to fail is not a gate — three shipped green-and-defeated in
    v1.2.5, and both cuts of the mojibake fix in THIS release were defeated by a
    reviewer after its tests were green.
  - ACCEPTANCE tests assert the gate stays QUIET where it must (a BOM'd .psd1, a
    declared mirror tree, the pristine repo). A gate that cannot be satisfied is
    just an outage, and every one of these rules red-gated something legitimate
    before it was scoped correctly.
Read the name: `..._is_a_finding` / `..._is_caught` / `..._grants_nothing` plant a
defect; `..._is_green` / `..._is_honoured` / `..._stays_green` assert the quiet.

Two of these gates exist because v1.2.5's own fixes were mis-scoped:
  - the no-BOM rule was applied to .ps1, where a BOM is REQUIRED (PS 5.1 decodes a
    BOM-less UTF-8 .ps1 as ANSI and mangles non-ASCII) — a gate that would have
    commanded the very mojibake this repo warns about;
  - the artifact-EXISTENCE gates fail loud on absence, which is right in the docs
    tree and structurally wrong in a mirror that does not carry the docs tree.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from _mirror_fixture import repo_copy

ROOT = Path(__file__).resolve().parent.parent
DECL = ".mirror-check.json"
BOM = b"\xef\xbb\xbf"


def run(repo: Path, env: dict = None):
    # Decode the pipe as UTF-8 EXPLICITLY. The findings these tests assert on
    # contain `§ — é` — on Windows the default pipe codec is cp1252 and reading
    # them back raises UnicodeDecodeError, so a test that trusts the locale here
    # fails on the platform the gate is FOR.
    p = subprocess.run([sys.executable, str(repo / "tools" / "mirror_check.py")],
                       capture_output=True, text=True, cwd=str(repo),
                       encoding="utf-8", errors="replace", env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def write(repo: Path, rel: str, data: bytes):
    t = repo / rel
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_bytes(data)


def declare(repo: Path, obj, track: bool = True, raw: bytes = None):
    """Write the declaration AND put it in the index. A declaration that relaxes
    gates must be visible in the diff that relaxes them, so an untracked one is
    refused — which means a test that forgets to track it is testing the refusal
    path, not the feature."""
    (repo / DECL).write_bytes(
        raw if raw is not None else json.dumps(obj, indent=2).encode("utf-8"))
    if track:
        subprocess.run(["git", "-c", "core.autocrlf=false", "add", "-f", DECL],
                       cwd=str(repo), check=True, capture_output=True)


class Ps1BomTest(unittest.TestCase):
    """The BOM rule INVERTS for .ps1. Both directions must be enforced."""

    def test_ps1_with_nonascii_and_no_bom_is_a_finding(self):
        with repo_copy() as repo:
            write(repo, "tools/demo.ps1", "Write-Output 'sect=§'\n".encode("utf-8"))
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("non-ASCII bytes and NO UTF-8 BOM", out)

    def test_ps1_with_nonascii_and_a_bom_is_green(self):
        """The exact file the old gate would have FAILED — and whose 'fix' would
        have broken the script on PS 5.1. It must pass."""
        with repo_copy() as repo:
            write(repo, "tools/demo.ps1", BOM + "Write-Output 'sect=§'\n".encode("utf-8"))
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_pure_ascii_ps1_needs_no_bom(self):
        """Nothing to mangle, nothing to require."""
        with repo_copy() as repo:
            write(repo, "tools/demo.ps1", b"Write-Output 'plain'\n")
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_a_bom_in_a_normal_file_is_still_a_finding(self):
        """The .ps1 carve-out must not leak into any other format."""
        with repo_copy() as repo:
            write(repo, "docs/NOTE.md", BOM + b"# hi\n")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("BOM (UTF-8", out)


class MojibakeExemptionIsBoundedTest(unittest.TestCase):
    """channel-core was added to the mojibake gate's example-text exemption so it
    could SHOW the corruption it now legislates about. Widening an exemption is
    exactly the move that quietly blinds a gate — and the first cut of this one WAS
    blind: it asked whether a backtick appeared in the preceding 40 characters, which
    is equally true of the text just AFTER a closed code span. Both reviewers walked
    through it on the real shipped file.

    So the headline test here is the one they used to defeat it. A test that only
    plants a marker on a line with no backticks (the easy case) would pass even with
    the exemption hardwired to 'always exempt' — that is the false-green shape this
    repo keeps paying for, and it is what the first version of this test did."""

    CORE = "plugins/agent-protocol/skills/agent-core/references/channel-core.md"
    OPS = "plugins/agent-protocol/skills/owner-engine-agent/references/ops-gotchas.md"

    def _append(self, repo, rel, line):
        p = repo / rel
        p.write_text(p.read_text(encoding="utf-8") + line, encoding="utf-8")
        return run(repo)

    def test_mojibake_AFTER_a_closed_code_span_is_caught(self):
        """THE defeating mutation. Corruption on a line that also holds a legitimate
        inline code span — indistinguishable from an example under a lookback rule,
        obvious under backtick parity."""
        for rel in (self.CORE, self.OPS):
            with self.subTest(file=rel), repo_copy() as repo:
                rc, out = self._append(
                    repo, rel, "\nThe `channel` is written UTF-8 Â§ without BOM.\n")
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_corrupting_the_CLEAN_example_inside_its_own_span_is_caught(self):
        """The mutation that defeated cut TWO. Backtick parity correctly located the
        span — but "you are inside a span" was never the licence. Corrupting the em
        dash of the clean example `§ — é` produces real mojibake INSIDE a code span,
        and the gate waved it through. The licence is being one of the ENUMERATED
        example strings; a span that is not one of them may not contain a mojibake
        byte, wherever it sits."""
        with repo_copy() as repo:
            p = repo / self.CORE
            lines = p.read_text(encoding="utf-8").splitlines()
            i = next(n for n, l in enumerate(lines) if "`§ — é`" in l)
            lines[i] = lines[i].replace("`§ — é`", "`§ â€” é`")
            p.write_text("\n".join(lines) + "\n", encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_mojibake_in_plain_prose_is_caught(self):
        for rel in (self.CORE, self.OPS):
            with self.subTest(file=rel), repo_copy() as repo:
                rc, out = self._append(repo, rel, "\nA corrupted em dash â€” here.\n")
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_mojibake_on_a_fence_delimiter_line_is_caught(self):
        """Round 3's defeat of the fence FIX: cut 3's repair toggled the fence
        state and `continue`d, so the delimiter line ITSELF was never scanned —
        mojibake in an info string passed, in the round after the release said
        'a fence exempts nothing'. Both delimiter positions must be scanned."""
        mangled = "§".encode("utf-8").decode("cp1252")
        for planted in (f"\n```text {mangled}\n```\n",
                        f"\n```text\ninside is fine\n``` {mangled}\n"):
            with self.subTest(planted=planted.strip()), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_a_tilde_fence_exempts_nothing(self):
        """Round 4: the fence tracker keyed on startswith("```") alone, so a
        ~~~ fence never registered — its body was scanned as PROSE with the
        span exemption available, and an allowlisted span inside it was waved
        through. CommonMark fences come in tildes too."""
        for planted in ("\n~~~text\n`Â§ â€” Ã©`\n~~~\n",     # allowlisted span in body
                        "\n~~~ Â§\ncontent\n~~~\n"):        # mangle in the info string
            with self.subTest(planted=planted.strip()), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_a_longer_fence_is_not_closed_by_a_shorter_quoted_one(self):
        """Round 4's second fence form: a ```` fence quoting a literal ```
        line. Under the bare toggle the QUOTED delimiter closed the fence, so
        an allowlisted span after it — still inside the quad fence — was back
        in exemption territory. A fence closes only on a run of the same
        character at least as long as its opener."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE, "\n````markdown\n```\n`Â§ â€” Ã©`\n````\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_a_container_prefixed_fence_exempts_nothing(self):
        """Round 5: a fence can open INSIDE a CommonMark container — a list
        item or a blockquote — and the delimiter hid behind the marker, so the
        fence never registered and its body was scanned as prose WITH the span
        exemption available. Container prefixes are peeled before the
        delimiter match; all three marker forms must register."""
        for planted in ("\n- ```text\n  `Â§ â€” Ã©`\n  ```\n",
                        "\n1. ~~~text\n   `Â§ â€” Ã©`\n   ~~~\n",
                        "\n> ```text\n> `Â§ â€” Ã©`\n> ```\n"):
            with self.subTest(planted=planted.strip().splitlines()[0]), \
                    repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_a_closer_with_trailing_text_does_not_close(self):
        """CommonMark: a CLOSING fence may carry only whitespace after its run
        — info text belongs to openers. Treating ``` info-text as a closer
        drops the machine out of the fence early, putting every line after it
        back in exemption territory: a mis-parse on the exempting side, which
        is the one direction this state machine must never err."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE,
                "\n```text\n``` not-a-closer\n`Â§ â€” Ã©`\n```\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_a_marker_line_inside_a_fence_does_not_close_it(self):
        """Round 6: the round-5 container cure peeled markers UNCONDITIONALLY,
        and peeling a list marker on a line INSIDE an open fence INVENTED a
        closer — CommonMark treats `- ```` ` inside a ```` fence as literal
        text, but the machine closed the fence and handed every following
        line back to the span exemption. This disproved the round-5 claim
        that over-peeling "can only widen scanning": the mis-parse landed on
        the exempting side. Inside a fence, list markers are never peeled;
        all four marker forms must stay in-fence."""
        for marker in ("- ", "+ ", "* ", "1. "):
            with self.subTest(marker=marker), repo_copy() as repo:
                rc, out = self._append(
                    repo, self.CORE,
                    f"\n````text\n{marker}````\n`Â§ â€” Ã©`\n````\n")
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_a_quote_marker_line_inside_a_bare_fence_does_not_close_it(self):
        """Round 6, one container over from the codex repro: a `> ``` ` line
        inside a fence that OPENED at quote depth zero invented a closer the
        same way. Inside a fence, quote markers are peeled only up to exactly
        the opener's depth — a run at the wrong depth is literal content."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE,
                "\n```text\n> ```\n`Â§ â€” Ã©`\n```\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_a_novel_line_after_a_quoted_fence_is_not_licensed(self):
        """Through round 10 this was a fence-machine acceptance test: the
        quote-opened fence had to close so the licensed span AFTER it stayed
        green. The byte-exact licence retired the machine and the category —
        the `Prose after:` line is NOVEL, not one of the enumerated
        documentation lines, so the span on it is a finding now, fences or
        no fences. Showing the mangle on a new line means enumerating that
        exact line in the allowlist, in review."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE,
                "\n> ```text\n> plain content\n> ```\n\nProse after: "
                "`Â§ â€” Ã©` (allowed example)\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_an_indented_run_inside_a_fence_does_not_close_it(self):
        """Round 7: CommonMark allows at most THREE spaces of indentation on a
        closing fence — four spaces or a tab make the run literal fenced
        content — and the round-6 closer accepted `\\s*`, so an indented ```
        inside a fence manufactured a closer and restored the exemption. Same
        for an over-indented quote marker at depth 1."""
        for name, planted in (
                ("four spaces", "\n```text\n    ```\n`Â§ â€” Ã©`\n```\n"),
                ("tab", "\n```text\n\t```\n`Â§ â€” Ã©`\n```\n"),
                ("indented quote at depth 1",
                 "\n> ```text\n    > ```\n`Â§ â€” Ã©`\n> ```\n")):
            with self.subTest(indent=name), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_an_indented_false_opener_does_not_invert_fence_phase(self):
        """Round 8: the round-7 indent bound covered only the CLOSING path,
        on the claim that a false OPENER can only widen scanning. Phase
        inversion disproved it: a 4-space-indented ``` is indented code to
        CommonMark, not a fence — but the liberal opener registered it,
        consumed the REAL opener on the next line as its closer, and the true
        fence's body was scanned as outside-fence prose WITH the exemption
        available. In a two-state toggle, a false delimiter in EITHER
        direction flips every classification after it."""
        for name, planted in (
                ("four spaces", "\n    ```\n```\n`Â§ â€” Ã©`\n```\n"),
                ("tab", "\n\t```\n```\n`Â§ â€” Ã©`\n```\n"),
                ("over-indented list marker",
                 "\n     - ```\n```\n`Â§ â€” Ã©`\n```\n")):
            with self.subTest(indent=name), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_a_three_space_opener_still_registers(self):
        """Acceptance for the round-8 opener bound: three spaces is the most
        CommonMark permits on an OPENING fence, and it must keep opening —
        the payload sits inside the fence, where nothing is exempt."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE, "\n   ```text\n`Â§ â€” Ã©`\n   ```\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_the_indented_fence_residual_is_retired(self):
        """Round 8 pinned a stated residual: a licensed trio in an
        indented-code body stayed GREEN because the absolute-indent machine
        read it as outside-fence prose with the exemption available. The
        byte-exact licence has no such residual — the trio line is novel
        wherever it sits, so the formerly-green licensed-string case and the
        non-example mangle now red the same way."""
        with self.subTest(shape="licensed trio in indented-code body"), \
                repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE, "\n    ```\n`Â§ â€” Ã©`\n    ```\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)
        with self.subTest(shape="non-example mangle reds too"), \
                repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE, "\n    ```\n`Ã–`\n    ```\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_a_novel_line_after_a_closed_fence_is_not_licensed(self):
        """Formerly the round-7 closer acceptance: the fence had to close so
        the allowed example after it stayed green. Same retirement as the
        quoted-fence case — the After-line is novel, and novel lines are
        never licensed."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE,
                "\n```text\nplain\n   ```\n\nAfter: `Â§ â€” Ã©` (allowed)\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_round_11_inversions_are_retired_with_the_model(self):
        """Round 11 delivered four confirmed phase inversions in one round —
        a [-led paragraph line defeating the link-reference-definition
        approximation, block state leaking across a blockquote boundary, an
        ordered list starting at 2 interrupting a paragraph CommonMark says
        it cannot, and a backtick inside a backtick-fence info string making
        a phantom opener. The cure was not four more rules: the licence
        stopped consulting a block model, so every one of these constructs
        reds the same way any novel line does."""
        for name, planted in (
                ("[-led paragraph vs LRD approximation",
                 "\n[ordinary paragraph]\n<custom-elem>\n```\n\n"
                 "`Â§ â€” Ã©`\n```\n"),
                ("quote-scoped html block leaking past its container",
                 "\n> <script>\n```\n</script>\n`Â§ â€” Ã©`\n```\n"),
                ("quote-scoped fence state crossing containers",
                 "\n> ```\n> old\noutside\n> ```\n> `Â§ â€” Ã©`\n> ```\n"),
                ("ordered list at 2 interrupting a paragraph",
                 "\nparagraph\n2. ```\n```\n`Â§ â€” Ã©`\n```\n"),
                ("backtick in a backtick-fence info string",
                 "\n```x`y\n```\n`Â§ â€” Ã©`\n```\n")):
            with self.subTest(shape=name), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_a_licensed_line_smuggled_behind_a_nonmarkdown_separator_reds(self):
        """Round 12: str.splitlines() splits on VT, FF, NEL, U+2028 and
        U+2029 — none of which end a MARKDOWN line. "junk + separator +
        licensed line" is ONE modified line to a renderer, carrying the
        licensed mangled bytes — but the scanner saw two lines and the
        licensed suffix exempted itself. The scanner now splits only where
        markdown does (CRLF, CR, LF), so the construct is a single
        byte-different line and is scanned."""
        for name, sep in (("VT", chr(0x0B)), ("FF", chr(0x0C)),
                          ("NEL", chr(0x85)), ("LS", chr(0x2028)),
                          ("PS", chr(0x2029))):
            with self.subTest(separator=name), repo_copy() as repo:
                p = repo / self.CORE
                src = p.read_text(encoding="utf-8")
                doc_line = next(l for l in src.splitlines() if "Â§" in l)
                p.write_text(src + "\nplain prefix text" + sep + doc_line
                             + "\n", encoding="utf-8")
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_a_doc_line_hidden_behind_a_separator_is_stale(self):
        """The liveness gate must use the SAME line unit as the scanner: if
        it still split on str.splitlines(), a documented line surviving only
        as the suffix of "junk + VT + line" would count as carried — the
        file no longer shows the example on a line of its own, but the
        licence would stay quietly live."""
        with repo_copy() as repo:
            p = repo / self.CORE
            src = p.read_text(encoding="utf-8")
            doc_line = next(l for l in src.splitlines() if "Â§" in l)
            p.write_text(src.replace("\n" + doc_line + "\n",
                                     "\nprefix" + chr(0x0B) + doc_line + "\n",
                                     1), encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("stale mojibake allowlist line", out)
            self.assertIn("mojibake in", out)

    @staticmethod
    def _can_symlink(repo):
        probe = repo / "symlink-probe"
        try:
            os.symlink(repo / "README.md", probe)
        except (OSError, NotImplementedError):
            return False
        probe.unlink()
        return True

    def test_a_symlink_alias_does_not_inherit_the_licence(self):
        """Round 12: the licence was keyed through resolve(), so a symlink
        at an UNLISTED path answering with an exempt target's content
        inherited the target's licence — the round-3 basename-inheritance
        hole rebuilt through the filesystem. Keying is lexical now, a
        symlink in the guarded tree is itself a finding, and the alias's
        content scans with no exemption."""
        with repo_copy() as repo:
            if not self._can_symlink(repo):
                self.skipTest("symlinks unavailable on this host")
            os.symlink(repo / self.CORE,
                       repo / "plugins/agent-protocol/skills/agent-core"
                              "/references/ops-alias.md")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("symlink in the guarded tree", out)
            self.assertIn("mojibake in", out)

    def test_a_symlinked_directory_is_a_finding(self):
        """Round 13: the round-12 symlink rule ran only on the *.md files the
        walk could SEE — and rglob does not look through a symlinked
        DIRECTORY, so aliasing a whole skills directory hid its guarded
        content from every gate with no finding at all. The guarded trees
        are now swept for reparse points of every kind, directories
        included."""
        with repo_copy() as repo:
            if not self._can_symlink(repo):
                self.skipTest("symlinks unavailable on this host")
            os.symlink(repo / "plugins/agent-protocol/skills/agent-core",
                       repo / "plugins/agent-protocol/skills/alias-core",
                       target_is_directory=True)
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("symlink in the guarded tree", out)
            self.assertIn("alias-core", out)

    def test_a_junction_in_the_guarded_tree_is_a_finding(self):
        """A Windows directory junction is a reparse point for which
        is_symlink() answers False — the alias shape that walks straight
        past a symlink-only rule. The sweep tests the reparse attribute,
        not just is_symlink()."""
        with repo_copy() as repo:
            custody = repo / "transports" / "custody"
            custody.mkdir(parents=True, exist_ok=True)
            (custody / "copy.md").write_text("PROTOCOL v2.8 stamped\n",
                                             encoding="utf-8")
            try:
                j = subprocess.run(
                    ["cmd", "/c", "mklink", "/J",
                     str(repo / "transports" / "alias"), str(custody)],
                    capture_output=True)
            except FileNotFoundError:  # no cmd.exe — POSIX host
                self.skipTest("junctions unavailable on this host")
            if j.returncode != 0:
                self.skipTest("junctions unavailable on this host")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("symlink in the guarded tree", out)
            self.assertIn("transports/alias", out)

    def test_a_reparse_point_at_a_guarded_root_is_a_finding(self):
        """Round 14: os.walk yields only DESCENDANTS — it never stats its
        own root, so a junction replacing the ENTIRE guarded tree walked
        straight through the sweep and the gate came back green over a
        tree supplied wholesale through an alias. The root is checked
        before the walk."""
        for root_rel in ("plugins/agent-protocol/skills", "transports"):
            with self.subTest(root=root_rel), repo_copy() as repo:
                real = repo / (root_rel.rsplit("/", 1)[-1] + "-real")
                (repo / root_rel).rename(real)
                try:
                    j = subprocess.run(
                        ["cmd", "/c", "mklink", "/J",
                         str(repo / root_rel), str(real)],
                        capture_output=True)
                except FileNotFoundError:  # no cmd.exe — POSIX host
                    self.skipTest("junctions unavailable on this host")
                if j.returncode != 0:
                    self.skipTest("junctions unavailable on this host")
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("symlink in the guarded tree", out)
                self.assertIn(root_rel, out)

    def test_an_unreadable_directory_is_a_finding_not_a_green(self):
        """Round 14: os.walk swallows OSError silently unless given an
        onerror callback — an access-denied directory simply ended its
        walk branch, and a directory of unstamped or licensed bytes the
        gate could not list came back green. A tree the gate cannot read
        is UNKNOWN, and unknown fails closed."""
        with repo_copy() as repo:
            d = repo / "plugins/agent-protocol/skills/unreadable"
            d.mkdir()
            (d / "unstamped.md").write_text("no stamp\n", encoding="utf-8")
            if os.name == "nt":
                user = os.environ["USERNAME"]
                deny = subprocess.run(
                    ["icacls", str(d), "/deny", f"{user}:(OI)(CI)(RD)"],
                    capture_output=True)
                if deny.returncode != 0:
                    self.skipTest("cannot deny directory listing on this host")
                try:
                    rc, out = run(repo)
                finally:
                    subprocess.run(["icacls", str(d), "/remove:d", user],
                                   capture_output=True)
            else:
                os.chmod(d, 0)
                try:
                    rc, out = run(repo)
                finally:
                    os.chmod(d, 0o755)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("not fully scannable", out)

    def test_an_unreadable_directory_outside_the_guarded_trees_is_a_finding(self):
        """Round 15: the round-14 fail-closed rule covered only the two
        guarded roots — the whole-repo BOM enumeration still used rglob(),
        which SUPPRESSES the OSError from a directory it cannot list, so an
        untracked BOM'd file under docs/ vanished with no finding while the
        gate claims every shipped and untracked file. The enumeration now
        walks with a fail-closed onerror of its own."""
        with repo_copy() as repo:
            d = repo / "docs" / "unreadable"
            d.mkdir()
            (d / "hidden.md").write_bytes(BOM + b"# bommed\n")
            if os.name == "nt":
                user = os.environ["USERNAME"]
                deny = subprocess.run(
                    ["icacls", str(d), "/deny", f"{user}:(OI)(CI)(RD)"],
                    capture_output=True)
                if deny.returncode != 0:
                    self.skipTest("cannot deny directory listing on this host")
                try:
                    rc, out = run(repo)
                finally:
                    subprocess.run(["icacls", str(d), "/remove:d", user],
                                   capture_output=True)
            else:
                os.chmod(d, 0)
                try:
                    rc, out = run(repo)
                finally:
                    os.chmod(d, 0o755)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("repository tree not fully scannable", out)

    def test_an_unlistable_excluded_scratch_dir_stays_green(self):
        """Round 16 (acceptance): SKIP_DIRS are pruned from the walk before
        descent — an unlistable UNTRACKED node_modules/ must not red a gate
        that never claims its content (it did: os.walk descended and hit
        onerror before the skip filter could run). Tracked files under
        pruned dirs still arrive through the tracked-set tail."""
        with repo_copy() as repo:
            d = repo / "node_modules" / "blocked"
            d.mkdir(parents=True)
            (d / "scratch.txt").write_text("junk\n", encoding="utf-8")
            if os.name == "nt":
                user = os.environ["USERNAME"]
                deny = subprocess.run(
                    ["icacls", str(d), "/deny", f"{user}:(OI)(CI)(RD)"],
                    capture_output=True)
                if deny.returncode != 0:
                    self.skipTest("cannot deny directory listing on this host")
                try:
                    rc, out = run(repo)
                finally:
                    subprocess.run(["icacls", str(d), "/remove:d", user],
                                   capture_output=True)
            else:
                os.chmod(d, 0)
                try:
                    rc, out = run(repo)
                finally:
                    os.chmod(d, 0o755)
            self.assertEqual(rc, 0, out)
            self.assertNotIn("not fully scannable", out)

    def test_a_symlink_alias_does_not_inherit_a_stamp_exemption(self):
        """Round 13's second MAJOR: the stamp-exemption map was keyed by
        RESOLVED path, so an alias at an unlisted path whose target was
        declared exempt inherited the exemption — the declaration reviewed
        one path and quietly exempted another. Keying is lexical now: the
        alias file is judged at the path where it SITS and fails the stamp
        gate on its own."""
        with repo_copy() as repo:
            if not self._can_symlink(repo):
                self.skipTest("symlinks unavailable on this host")
            custody = repo / "transports" / "custody"
            custody.mkdir(parents=True, exist_ok=True)
            (custody / "copy.md").write_text("no stamp here\n",
                                             encoding="utf-8")
            declare(repo, {"stamp_exempt": [
                {"path": "transports/custody/copy.md",
                 "reason": "byte-identical custody copy"}]})
            os.symlink(custody / "copy.md",
                       repo / "transports" / "alias-copy.md")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("missing PROTOCOL v2.8 stamp", out)
            self.assertIn("alias-copy.md", out)

    def test_a_stamp_exemption_with_dotdot_grants_nothing(self):
        """A '..' segment makes the lexical key and the file it names
        disagree — and since round 14 a hostile path refuses the WHOLE
        declaration at load, so the file it aimed at stays gated."""
        with repo_copy() as repo:
            custody = repo / "transports" / "custody"
            custody.mkdir(parents=True, exist_ok=True)
            (custody / "copy.md").write_text("no stamp here\n",
                                             encoding="utf-8")
            declare(repo, {"stamp_exempt": [
                {"path": "transports/../transports/custody/copy.md",
                 "reason": "byte-identical custody copy"}]})
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("contains '..'", out)
            self.assertIn("REFUSED", out)
            self.assertIn("missing PROTOCOL v2.8 stamp", out)

    def test_an_out_of_tree_symlink_is_a_finding_not_a_crash(self):
        """Round 12's second half: resolve()-based rel computation raised
        ValueError on a symlink whose target sits outside the repo — the
        checker died before printing the findings it had already collected
        (the round-3 unguarded-read class, arriving through resolution
        instead of absence)."""
        with repo_copy() as repo:
            if not self._can_symlink(repo):
                self.skipTest("symlinks unavailable on this host")
            outside = repo.parent / "r12-outside-target.md"
            outside.write_text("plain text\n", encoding="utf-8")
            try:
                os.symlink(outside,
                           repo / "plugins/agent-protocol/skills/agent-core"
                                  "/references/ops-out.md")
                rc, out = run(repo)
            finally:
                outside.unlink()
            self.assertNotEqual(rc, 0, out)
            self.assertNotIn("Traceback", out)
            self.assertIn("symlink in the guarded tree", out)

    def test_an_html_block_does_not_invert_fence_phase(self):
        """Round 9: CommonMark HTML blocks swallow fence-looking lines — a
        ``` inside <script>...</script> is HTML content, not an opener. The
        fence-only machine registered it, consumed the REAL opener on the
        next line as its closer, and the true fence's body was scanned as
        outside prose WITH the exemption available: round 8's phase
        inversion again, reached through a block type the machine did not
        model. All seven CommonMark HTML-block kinds are now tracked."""
        for name, planted in (
                ("script, kind 1",
                 "\n<script>\n```\n</script>\n```\n`Â§ â€” Ã©`\n```\n"),
                ("comment, kind 2",
                 "\n<!--\n```\n-->\n```\n`Â§ â€” Ã©`\n```\n"),
                ("block tag, kind 6",
                 "\n<div>\n```\n\n```\n`Â§ â€” Ã©`\n```\n")):
            with self.subTest(block=name), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_mojibake_inside_an_html_block_is_not_exempt(self):
        """An HTML block grants nothing, exactly like a fence: a span-shaped
        licensed trio inside one is HTML content, not a documented example.
        The one-line comment also pins the same-line START-AND-END rule for
        kinds 1-5 on the scanning side."""
        for name, planted in (
                ("inside a script block", "\n<script>\n`Â§ â€” Ã©`\n</script>\n"),
                ("inside a one-line comment", "\n<!-- `Â§ â€” Ã©` -->\n")):
            with self.subTest(where=name), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_novel_lines_after_html_constructs_are_not_licensed(self):
        """Through round 10 these were HTML-block termination acceptances:
        each block had to END so the licensed span after it stayed green.
        Under the byte-exact licence the block never mattered — the
        `(allowed)` line is NOVEL in every construct, so all seven red. The
        positive case (a byte-identical documented line stays exempt after
        any construct) is pinned separately."""
        for name, planted in (
                ("kind 1 close tag",
                 "\n<script>\nx\n</script>\n\n`Â§ â€” Ã©` (allowed)\n"),
                ("kind 2 arrow", "\n<!-- note\n-->\n\n`Â§ â€” Ã©` (allowed)\n"),
                ("kind 3 question", "\n<?php\n?>\n\n`Â§ â€” Ã©` (allowed)\n"),
                ("kind 4 bracket",
                 "\n<!DOCTYPE html\n>\n\n`Â§ â€” Ã©` (allowed)\n"),
                ("kind 5 cdata", "\n<![CDATA[\nx ]]>\n\n`Â§ â€” Ã©` (allowed)\n"),
                ("kind 6 blank line", "\n<div>\nx\n\n`Â§ â€” Ã©` (allowed)\n"),
                ("same-line start and end",
                 "\n<!-- note -->\n`Â§ â€” Ã©` (allowed)\n")):
            with self.subTest(end=name), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_a_lone_tag_cannot_interrupt_a_paragraph(self):
        """Kind 7 (a complete tag alone on its line) opens an HTML block only
        after a blank line — CommonMark says it cannot interrupt a paragraph.
        Without that gate, a custom tag mid-paragraph opens a phantom block
        whose first blank line hands the text after it BACK to the exemption
        while the real fence opener it swallowed inverts the phase: here the
        trio sits inside a REAL fence and must red."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE,
                "\nprose line\n<custom-elem>\n```\n\n`Â§ â€” Ã©`\n```\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_a_lone_tag_after_a_blank_line_opens_a_block(self):
        """The other side of the kind-7 gate: after a blank line the lone tag
        DOES open a block, and everything until the next blank — including
        fence-looking lines and the trio — is HTML content with no exemption
        reachable."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE,
                "\n\n<custom-elem>\n```\ntext\n```\n`Â§ â€” Ã©`\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_a_lone_tag_after_any_closed_block_opens_a_block(self):
        """Round 10: the kind-7 gate's first cut was a prev-line-was-blank
        PROXY for "cannot interrupt a paragraph" — and a paragraph is ended
        by more than blank lines. After a closed fence (the reviewer's
        reproduction), an ATX heading, a thematic break, a setext underline,
        indented code, or a link reference definition, a lone tag IS
        eligible with no blank line in sight; the proxy read it as prose,
        the fence-looking line after it registered as an opener, and the
        phase inverted exactly as in rounds 8 and 9. The machine now tracks
        the paragraph itself. In every construct below the trio sits inside
        a REAL fence the phantom opener used to steal, and must red."""
        for name, planted in (
                ("closed fence",
                 # the paragraph text before the fence is load-bearing: a
                 # fence INTERRUPTS a paragraph, so the opener must close it
                 # — replay found the blank-led variant of this construct
                 # never exercised that assignment
                 "\npara text\n```\nprior fenced block\n```\n<custom-elem>\n"
                 "```\n\n```\n`Â§ â€” Ã©`\n```\n"),
                ("ATX heading",
                 "\n## heading\n<custom-elem>\n```\n\n```\n`Â§ â€” Ã©`\n```\n"),
                ("thematic break",
                 "\n---\n<custom-elem>\n```\n\n```\n`Â§ â€” Ã©`\n```\n"),
                ("setext underline",
                 "\npara text\n===\n<custom-elem>\n```\n\n```\n"
                 "`Â§ â€” Ã©`\n```\n"),
                ("indented code",
                 "\n\n    code line\n<custom-elem>\n```\n\n```\n"
                 "`Â§ â€” Ã©`\n```\n"),
                ("link reference definition",
                 "\n\n[ref]: https://example.invalid\n<custom-elem>\n```\n\n"
                 "```\n`Â§ â€” Ã©`\n```\n")):
            with self.subTest(after=name), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_a_lazy_continuation_keeps_the_paragraph_open(self):
        """Acceptance for the round-10 tracker's indented-line rule: a
        4-space-indented line INSIDE a paragraph is a lazy continuation,
        not indented code, so the paragraph stays open and a lone tag after
        it still cannot interrupt — the fence after the tag is real and the
        trio inside it reds."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE,
                "\npara text\n    lazy continuation\n<custom-elem>\n```\n\n"
                "`Â§ â€” Ã©`\n```\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_backticks_that_form_no_span_license_nothing(self):
        """Round 7: backtick PARITY counted every backtick as a delimiter, so
        an UNCLOSED backtick licensed everything after it and an ESCAPED
        backtick (literal punctuation to CommonMark) opened an exemption —
        the exact allowlisted payload sat in bare prose and passed. A span
        exists only where CommonMark closes one: equal-length runs, escapes
        literal, unclosed runs grant nothing."""
        for name, planted in (
                ("unclosed opener", "\nUnclosed example: `Â§ â€” Ã©\n"),
                ("escaped opener", "\nEscaped marker: \\`Â§ â€” Ã©`\n"),
                ("mismatched runs", "\nMismatched: ``Â§ â€” Ã©`\n")):
            with self.subTest(shape=name), repo_copy() as repo:
                rc, out = self._append(repo, self.CORE, planted)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_leads_outside_the_original_four_are_caught(self):
        """Round 3, cut 6: [ÂÃâð] covered the docs' CURRENT repertoire — `Ā`
        (lead 0xC4) mangled to `Ä€` and sailed through. The round-trip detector
        must catch the whole lead-byte class, including a sequence carrying one
        of the five bytes cp1252 leaves undefined (❤ = E2 9D A4)."""
        orphans = {0x81, 0x8D, 0x8F, 0x90, 0x9D}
        for char in ("Ā", "ł", "ω", "❤"):
            with self.subTest(char=char), repo_copy() as repo:
                raw = char.encode("utf-8")
                mangled = "".join(
                    chr(b) if b in orphans else bytes([b]).decode("cp1252")
                    for b in raw)
                rc, out = self._append(
                    repo, self.CORE, f"\nOut-of-set corruption {mangled} here.\n")
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_legitimate_adjacent_nonascii_prose_stays_green(self):
        """The false positive the round-trip rule exists to avoid: é directly
        before an ellipsis is a lead-class char followed by a continuation-class
        char, and a bare character-class rule would flag it. é opens a THREE-byte
        sequence with no third byte following, so the round-trip fails and the
        prose passes. ("voilà" is back in round 7: à was a blind-range
        character until the Latin-1 decode rule closed that range, so the
        coverage gate now welcomes it — this plant is the acceptance proof.)"""
        with repo_copy() as repo:
            other = repo / "plugins/agent-protocol/skills/agent-core/references/x.md"
            other.write_text("# x [PROTOCOL v2.8]\n\nvoilà — café… — d'accord.\n",
                             encoding="utf-8")
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_legitimate_german_prose_with_eszett_stays_green(self):
        """Round 4's false REJECT. ß renders lead byte 0xDF, and "groß—aber"
        is DF 97 in cp1252 bytes — valid UTF-8 (an NKo letter), so the
        round-trip validator confirms legitimate German as corruption. Round 4
        cured it with a single-lead exclusion; round 5 proved the CLASS needs
        the prose guard (all continuations are writer-typography → prose), and
        the German case now rides that. Real prose must not red-gate the
        tree."""
        with repo_copy() as repo:
            other = repo / "plugins/agent-protocol/skills/agent-core/references/x.md"
            other.write_text(
                "# x [PROTOCOL v2.8]\n\nDas ist groß—aber korrekt.\n",
                encoding="utf-8")
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_legitimate_french_typography_stays_green(self):
        """Round 5's false REJECTs, one lead over from the German case:
        `É—` (C9 97) and `é—“` (E9 97 93) both round-trip to valid UTF-8,
        because the whole cp1252 lead range renders as accented European
        letters. The prose guard reads a candidate whose continuations are all
        writer-typography as prose — every accented letter against smart
        punctuation, not one excluded lead at a time."""
        with repo_copy() as repo:
            other = repo / "plugins/agent-protocol/skills/agent-core/references/x.md"
            other.write_text(
                "# x [PROTOCOL v2.8]\n\nCAFÉ—OUVERT, et café—“ouvert” aussi.\n",
                encoding="utf-8")
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_a_blind_range_character_arriving_in_the_tree_is_a_finding(self):
        """The prose guard's bill. What remains of its blind range after the
        round-7 Latin-1 rule (a mangle whose continuation bytes all render as
        writer-typography AND whose decode lands outside Latin-1) is held by
        the coverage gate. ߗ (U+07D7, NKo) mangles to `ß—`, which reads as
        German prose: the day it lands in a skill file, the gate must say the
        detector cannot protect it. (This test planted « through round 6 —
        the Latin-1 rule made « detectable, so the pinned character moved to
        the range that is still genuinely blind.)"""
        with repo_copy() as repo:
            other = repo / "plugins/agent-protocol/skills/agent-core/references/x.md"
            other.write_text(
                "# x [PROTOCOL v2.8]\n\nNKo letter ߗ arrives here.\n",
                encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("detector blind spot", out)

    def test_the_coverage_gate_defends_the_detector_not_just_the_tree(self):
        """REPLAY on the round-7 fold found the fixed support alphabet
        undefended: the blind-range test plants its character IN the tree, so
        a tree-only population catches that plant just as well. The
        alphabet's distinctive promise is different — the gate must red when
        the DETECTOR goes blind on expected text while the tree stays clean.
        So: weaken the detector (remove the Latin-1 decode rule, recreating
        the round-7 hole exactly) and the PRISTINE tree itself must red with
        detector blind spots — «, Ö and their row are in the support
        alphabet whether or not any file carries them."""
        with repo_copy() as repo:
            mc = repo / "tools" / "mirror_check.py"
            src = mc.read_text(encoding="utf-8")
            block = ('        decoded = b[:n].decode("utf-8")\n'
                     "        if all(0xA0 <= ord(c) <= 0xFF"
                     " or c in _CP1252_EXTENSION_LETTERS\n"
                     "               for c in decoded):\n"
                     "            return True\n"
                     "        return False")
            self.assertIn(block, src)   # the rule being weakened must exist
            mc.write_text(src.replace(block, "        return False", 1),
                          encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("detector blind spot", out)

    def test_the_coverage_gate_defends_the_extension_widening(self):
        """The round-7 REPLAY lesson, repeating one round later: the round-9
        œ widening's CI defense is the extension letters' membership in the
        support alphabet — and REPLAY found that membership itself
        undefended (remove it and the suite stays green, because the direct
        œ test exercises the detector, not the alphabet). So: weaken just
        the extension clause of the detector in a scratch copy, and the
        PRISTINE tree must red on the letters — which only happens while
        they are in the alphabet. A green here with the clause gone means
        the alphabet entry is decoration."""
        with repo_copy() as repo:
            mc = repo / "tools" / "mirror_check.py"
            src = mc.read_text(encoding="utf-8")
            clause = " or c in _CP1252_EXTENSION_LETTERS"
            self.assertIn(clause, src)   # the rule being weakened must exist
            mc.write_text(src.replace(clause, "", 1), encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("detector blind spot", out)

    def test_guillemets_arriving_in_the_tree_are_now_welcome(self):
        """Acceptance for the round-7 Latin-1 rule: « was the pinned
        blind-range character for two rounds; its mangle `Â«` decodes to
        U+00AB — Latin-1 — so the detector now reads it as corruption and the
        coverage gate has no complaint about the clean character."""
        with repo_copy() as repo:
            other = repo / "plugins/agent-protocol/skills/agent-core/references/x.md"
            other.write_text(
                "# x [PROTOCOL v2.8]\n\nGuillemets « arrive » here.\n",
                encoding="utf-8")
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_mangles_of_characters_absent_from_the_tree_are_caught(self):
        """Round 7, the judge's MAJOR. The coverage gate swept only characters
        the tree HAPPENED to carry, and the prose guard read `Ã–` (mangled Ö)
        as Ã-plus-en-dash prose — so pasted mangled German/Spanish landed
        green in a live skill file while both defenses stayed silent: Ö was
        never IN the tree, and the mangle's components (Ã, –) individually
        pass. A candidate whose bytes decode to Latin-1 Supplement text is now
        corruption, tree membership irrelevant."""
        for name, mangled in (("O-umlaut C3 96", "\xc3–"),
                              ("N-tilde C3 91", "\xc3‘"),
                              ("guillemet C2 AB", "\xc2\xab")):
            with self.subTest(char=name), repo_copy() as repo:
                other = (repo / "plugins/agent-protocol/skills/agent-core"
                         "/references/x.md")
                other.write_text(
                    f"# x [PROTOCOL v2.8]\n\nPasted corruption: {mangled}\n",
                    encoding="utf-8")
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)

    def test_mangled_cp1252_extension_letters_are_caught(self):
        """Round 9, the judge's finding: mangled French œ (`Å“`) walked the
        prose side — the left curly quote IS writer typography, and U+0153
        sits outside Latin-1 Supplement, so the round-7 rule never fired.
        cp1252's own extension letters (ŒœŠšŽžŸƒ) are exactly the
        non-Latin-1 letters Windows-ANSI prose produces, so their mangles are
        corruption too. Only Œ œ Š ƒ are reachable through the prose branch
        (š ž Ž Ÿ carry a non-typography continuation byte and already
        round-trip-flag); stated cost, accepted: a REAL Å or Æ hard against
        an opening curly quote or NBSP now reads as corruption — a rare
        adjacency, and a loud false red beats silent corruption."""
        for name, mangled in (("oe C5 93", "c\xc5“ur"),
                              ("OE C5 92", "\xc5’uvre"),
                              ("S-caron C5 A0", "\xc5\xa0kola"),
                              ("f-hook C6 92", "\xc6’unction")):
            with self.subTest(char=name), repo_copy() as repo:
                other = (repo / "plugins/agent-protocol/skills/agent-core"
                         "/references/x.md")
                other.write_text(
                    f"# x [PROTOCOL v2.8]\n\nPasted corruption: {mangled}\n",
                    encoding="utf-8")
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)
                self.assertIn("mojibake in", out)

    def test_truncated_currency_and_emoji_mangles_are_caught(self):
        """Round 4: the truncation exception named ONE prefix (E2 80, the
        straight-quote dash). Its siblings fail the round-trip identically —
        `â‚` is a beheaded currency sign (E2 82), `ðŸ` a beheaded emoji
        (F0 9F) — and were waved through. All three enumerated families flag."""
        for name, mangled in (("currency E2 82", "â‚"),
                              ("emoji F0 9F", "ðŸ")):
            with self.subTest(family=name), repo_copy() as repo:
                rc, out = self._append(
                    repo, self.CORE, f"\nA truncated mangle {mangled} here.\n")
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_truncated_mangles_of_the_trees_own_characters_are_caught(self):
        """Round 5: the hand-kept three-family list violated its own charter
        ("blocks that actually occur in text this project ships") — the tree
        ships arrows and warning signs, and their truncated mangles `â†`
        (E2 86) and `âš` (E2 9A) sailed through. The families are now DERIVED
        from every 3-plus-byte character the tree carries, so the list cannot
        lag its corpus."""
        for name, mangled in (("arrow E2 86", "â†"),
                              ("warning E2 9A", "âš")):
            with self.subTest(family=name), repo_copy() as repo:
                rc, out = self._append(
                    repo, self.CORE, f"\nA truncated mangle {mangled} here.\n")
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_the_truncated_straight_quote_mangle_is_still_caught(self):
        """`â€` + a non-continuation byte does NOT round-trip (E2 80 22 is not
        valid UTF-8) — but it is real corruption these files document (the
        straight-quote dash), so it is a stated always-flag exception. A
        round-trip-only detector would have silently un-detected it."""
        with repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE, '\nA double-mangled dash â€" appears here.\n')
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_the_detector_is_a_class_not_an_enumeration(self):
        """Round 2's defeat. ("â€", "Â§") named the two characters the example
        spans happen to show; a corruption sweep of the guarded files missed 18
        corruptible lines, every miss a line whose only non-ASCII is an arrow or
        a warning sign — including the .ps1 bullet THIS release added. (The gap
        is the one number independent sweeps reproduce; corpus totals never
        agreed, so none is stated.) Corrupt one
        character from each UTF-8 width class the docs use (2-byte Latin-1, two
        3-byte symbols the old markers missed, 4-byte emoji): the gate must name
        every one. The corruption is COMPUTED (encode UTF-8, decode cp1252), not
        pasted, so the test plants the defect itself rather than an author's
        recollection of it."""
        for char in ("é", "→", "⚠", "🛑"):
            with self.subTest(char=char), repo_copy() as repo:
                mangled = char.encode("utf-8").decode("cp1252")
                rc, out = self._append(
                    repo, self.CORE, f"\nA corrupted character {mangled} here.\n")
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)

    def test_the_documented_example_lines_stay_exempt(self):
        """The exemption must still DO its job — otherwise the fix is just a
        regression with better prose. The licence is byte-exact LINES now,
        so the positive case is a byte-identical duplicate of a documented
        line: exempt anywhere in its file, even inside a fence, because
        identical bytes cannot carry new corruption. A novel line showing
        the same span is the negative case, red across this suite."""
        with self.subTest(where="duplicated in prose"), repo_copy() as repo:
            doc_line = next(
                l for l in (repo / self.CORE).read_text(encoding="utf-8")
                .splitlines() if "\xc2\xa7" in l)
            rc, out = self._append(repo, self.CORE, "\n" + doc_line + "\n")
            self.assertEqual(rc, 0, out)
        with self.subTest(where="duplicated inside a fence"), \
                repo_copy() as repo:
            doc_line = next(
                l for l in (repo / self.CORE).read_text(encoding="utf-8")
                .splitlines() if "\xc2\xa7" in l)
            rc, out = self._append(
                repo, self.CORE, "\n```\n" + doc_line + "\n```\n")
            self.assertEqual(rc, 0, out)
        with self.subTest(where="novel line reds"), repo_copy() as repo:
            rc, out = self._append(
                repo, self.CORE,
                "\nSaving without a BOM yields `Â§ â€” Ã©` instead.\n")
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_the_documented_examples_do_not_false_positive(self):
        """The pristine tree — which carries `Â§ â€” Ã©` as an example inside backticks
        in BOTH files — must be green."""
        with repo_copy() as repo:
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_the_exemption_does_not_extend_to_other_skill_files(self):
        with repo_copy() as repo:
            other = repo / "plugins/agent-protocol/skills/agent-core/references/x.md"
            other.write_text("# x [PROTOCOL v2.8]\n\nA backticked `Â§` example.\n",
                             encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)

    def test_an_allowlisted_span_inside_a_FENCE_is_caught(self):
        """Cut three's hole. The code comment said "fenced blocks get no exemption"
        and the code never looked at a fence — so corruption pasted into a ``` block
        and wrapped in backticks was waved through, in the release whose whole thesis
        is that a claim is not a check. Inside a fence a backtick is a literal, not a
        span; no fence in these files carries an example; a fence exempts nothing."""
        for rel in (self.CORE, self.OPS):
            with self.subTest(file=rel), repo_copy() as repo:
                rc, out = self._append(
                    repo, rel, "\n```text\n`Â§ â€” Ã©`\n```\n")
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake in", out)


class CleanExampleMustStayTest(unittest.TestCase):
    """The allowlist licenses the MANGLED strings — so swapping the CLEAN example
    `§ — é` for its mangled twin passes every span check: the trio is a licensed
    span. The judge performed exactly that swap and the gate said green. The
    exemption exists so these files can show the corruption NEXT TO the correct
    form; a file showing only the mangled bytes is a corrupted file with a permit,
    so the licence is conditional on the clean form's PRESENCE."""

    FILES = (MojibakeExemptionIsBoundedTest.CORE,
             MojibakeExemptionIsBoundedTest.OPS,
             "plugins/agent-protocol/skills/helper-builder-agent"
             "/references/ops-gotchas.md")

    def test_swapping_the_clean_example_for_the_mangled_trio_is_a_finding(self):
        for rel in self.FILES:
            with self.subTest(file=rel), repo_copy() as repo:
                p = repo / rel
                p.write_text(p.read_text(encoding="utf-8")
                             .replace("`§ — é`", "`Â§ â€” Ã©`"),
                             encoding="utf-8")
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("clean example", out)

    def test_all_three_exempt_files_still_carry_the_clean_example(self):
        """Presence in the PRISTINE tree — the check must have something to hold."""
        for rel in self.FILES:
            with self.subTest(file=rel):
                t = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn("`§ — é`", t)


class ExemptPathKeyingTest(unittest.TestCase):
    """Round 3: the exemption was keyed by BASENAME and derived from the files
    found on disk. Both properties were bypasses: any new file named
    ops-gotchas.md anywhere inherited the licence unreviewed, and deleting a
    licensed file deleted every check that ran on it — the presence gate was
    vacuously green over a file that was GONE."""

    def test_deleting_an_exempt_file_is_a_finding(self):
        """Also pins that the gate SURVIVES the deletion: removing channel-core
        used to crash the checker on an unguarded read before it printed any of
        the findings it had already collected — red for the wrong reason, with
        the report lost."""
        for rel in CleanExampleMustStayTest.FILES:
            with self.subTest(file=rel), repo_copy() as repo:
                (repo / rel).unlink()
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("mojibake-exempt file missing", out)
                self.assertNotIn("Traceback", out)

    def test_the_exemption_is_keyed_by_path_not_basename(self):
        """A new file that merely SHARES a licensed basename gets no licence."""
        with repo_copy() as repo:
            imposter = (repo / "plugins/agent-protocol/skills/orchestrator-agent"
                        "/references/ops-gotchas.md")
            imposter.write_text(
                "# notes [PROTOCOL v2.8]\n\nA backticked `Â§` example.\n",
                encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in", out)


class SuffixParityTest(unittest.TestCase):
    """Round 3, three reviewers independently: the gate grew to five suffixes and
    every guidance passage still taught three — a reader obeying the NORMATIVE doc
    for a .psrc walked straight into the gate. The documented set is now DERIVED
    from each file's backticked tokens and compared with the gate's set, so prose
    cannot regress on its own."""

    def test_prose_dropping_a_suffix_is_a_finding(self):
        for rel in CleanExampleMustStayTest.FILES:
            with self.subTest(file=rel), repo_copy() as repo:
                p = repo / rel
                src = p.read_text(encoding="utf-8")
                self.assertIn("`.pssc`", src, f"{rel} lost its enumeration?")
                p.write_text(src.replace("`.pssc`", "`.psd1`"), encoding="utf-8")
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("suffix parity", out)

    def test_prose_documenting_an_ungated_suffix_is_a_finding(self):
        """Drift in the other direction: the doc teaching an inversion the gate
        does not enforce ships scripts the gate will not protect."""
        with repo_copy() as repo:
            p = (repo / "plugins/agent-protocol/skills/agent-core"
                 "/references/channel-core.md")
            p.write_text(p.read_text(encoding="utf-8")
                         + "\nAlso `.ps9` inverts.\n", encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("suffix parity", out)
            self.assertIn(".ps9", out)

    def test_case_and_typography_do_not_hide_a_documented_suffix(self):
        """Round 4: `.PS2` in caps, or bare .ps2 with no backticks, is still
        the doc teaching an inversion the gate does not enforce — and a
        lowercase-backticked-only pattern read both as absent, so prose could
        regress exactly as before with different typography. (The bare form
        counts only on a line that speaks of the BOM — see the filename test
        below for why — so the planted guidance says so, as real inversion
        guidance always does.)"""
        for planted in ("\nAlso `.PS2` inverts.\n",
                        "\nAlso bare .ps2 needs the BOM.\n",
                        "\nAlso bare .ps2 needs the Byte-Order mark.\n"):
            with self.subTest(planted=planted.strip()), repo_copy() as repo:
                p = (repo / "plugins/agent-protocol/skills/agent-core"
                     "/references/channel-core.md")
                p.write_text(p.read_text(encoding="utf-8") + planted,
                             encoding="utf-8")
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("suffix parity", out)
                self.assertIn(".ps2", out)

    def test_a_bare_filename_mention_is_not_guidance(self):
        """Round 5: the round-4 cure over-corrected — deriving from EVERY raw
        token meant a passing filename mention ("a fixture named archive.ps2")
        drifted the derived set and red-gated the guidance file. A bare token
        counts only on a line that speaks of the BOM; a backticked token is
        guidance wherever it sits.

        Round 6: the round-5 cure was itself two substrings too loose — the
        `.ps2` TAIL of `archive.ps2` matched the bare pattern, and the `bom`
        inside "bombproof" activated the tier, so a filename mention on a
        genuinely-BOM-speaking line (and on a bombproof line) false-red'd.
        A bare token must be lexically standalone and the BOM term bounded;
        all three phrasings must stay green.

        REPLAY on the first cut of this test found the bombproof case
        green-and-defeated: its bare token sat inside a filename, so the
        standalone lookbehind alone kept it green and the bounded BOM term
        was decoration. The bombproof line therefore carries a STANDALONE
        bare token — only the bounded term keeps that one green.

        Round 7: the round-6 bounding was mis-scoped one alternation over —
        the word boundaries bound only to `boms?`, leaving `byte-order` an
        unbounded substring, so "byte-ordering"/"byte-ordered" activated the
        tier. Both phrasings carry standalone tokens: only whole-alternation
        boundaries keep them green."""
        for planted in ("\nAn unrelated fixture is named archive.ps2; it "
                        "is not PowerShell guidance.\n",
                        "\nThe BOM regression fixture is named archive.ps2; "
                        "it is not PowerShell guidance.\n",
                        "\nA bombproof archive format uses the .ps2 "
                        "extension for fixtures; it is not PowerShell "
                        "guidance.\n",
                        "\nA byte-ordering fixture uses the .ps2 extension; "
                        "it is not PowerShell guidance.\n",
                        "\nA byte-ordered fixture uses the .ps2 extension; "
                        "it is not PowerShell guidance.\n"):
            with self.subTest(planted=planted.strip()), repo_copy() as repo:
                p = (repo / "plugins/agent-protocol/skills/agent-core"
                     "/references/channel-core.md")
                p.write_text(p.read_text(encoding="utf-8") + planted,
                             encoding="utf-8")
                rc, out = run(repo)
                self.assertEqual(rc, 0, out)


class StdoutGuardIsCrossPlatformTest(unittest.TestCase):
    """The forced-UTF-8 stdout guard exists so a finding that quotes real bytes
    can be PRINTED on a hostile pipe codec. Deleting it broke tests only on
    Windows — on the Linux CI runner the default pipe codec is already UTF-8, so
    the guard survived its own deletion on the exact runner that gates merges.
    Force the hostile codec explicitly and every platform runs the scenario the
    guard exists for: without it, the print raises UnicodeEncodeError and the gate
    crashes while reporting the one defect it was built to report."""

    def test_findings_print_even_on_an_ascii_stdout(self):
        """The first cut of THIS test was green-and-defeated by replay: it planted
        mojibake, whose finding quotes a path and line numbers — pure ASCII — so
        the print never touched a byte the hostile codec could choke on and the
        guardless gate passed. The defect must be one whose finding QUOTES real
        bytes: the BOM-less .ps1 finding spells out `§ — é` → `Â§ â€” Ã©`."""
        with repo_copy() as repo:
            write(repo, "tools/demo.ps1", "Write-Output 'sect=§'\n".encode("utf-8"))
            rc, out = run(repo, env={**os.environ, "PYTHONIOENCODING": "ascii"})
            self.assertNotEqual(rc, 0, out)
            self.assertIn("NO UTF-8 BOM", out)         # the finding was SAID
            self.assertNotIn("Traceback", out)         # not crashed while saying it


class AllowlistMustStayLiveTest(unittest.TestCase):
    """An allowlist that outlives the text it permits is a bypass nobody can see: it
    goes on licensing a string no file uses, and the next author to type that string
    — by paste, by accident — sails through. Both drift directions are tested."""

    CORE_KEY = ('    "plugins/agent-protocol/skills/agent-core/references/'
                'channel-core.md": {')

    def test_an_entry_that_no_file_uses_is_a_finding(self):
        """The widening move: license a line, ship no file that carries it.
        Delete the staleness check and this test goes red — that is the point.
        The injected line carries a real mangle so it fails ONLY the
        staleness branch, not the dead-entry one."""
        with repo_copy() as repo:
            tool = repo / "tools" / "mirror_check.py"
            src = tool.read_text(encoding="utf-8")
            self.assertIn(self.CORE_KEY, src)
            tool.write_text(
                src.replace(
                    self.CORE_KEY,
                    self.CORE_KEY
                    + '\n        "a licensed line no file carries \\xc2\\xa7",',
                    1),
                encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("stale mojibake allowlist line", out)

    def test_an_entry_whose_example_was_edited_away_is_a_finding(self):
        """The rot move: a later cleanup edits the documented line, the
        licence stays — and now names bytes the file no longer carries."""
        with repo_copy() as repo:
            for rel in (MojibakeExemptionIsBoundedTest.CORE,
                        MojibakeExemptionIsBoundedTest.OPS,
                        "plugins/agent-protocol/skills/helper-builder-agent"
                        "/references/ops-gotchas.md"):
                p = repo / rel
                p.write_text(p.read_text(encoding="utf-8").replace("`Â§`", "`(sect)`"),
                             encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("stale mojibake allowlist line", out)

    def test_an_entry_that_licenses_no_mangle_is_a_finding(self):
        """A licensed line with no detectable mangle exempts nothing today
        and pre-licenses whatever corruption lands on that exact line
        tomorrow — dead weight with a permit. Same species as staleness,
        different branch."""
        with repo_copy() as repo:
            tool = repo / "tools" / "mirror_check.py"
            src = tool.read_text(encoding="utf-8")
            self.assertIn(self.CORE_KEY, src)
            plant = "a clean line that licenses no mangle at all"
            tool.write_text(
                src.replace(self.CORE_KEY,
                            self.CORE_KEY + f'\n        "{plant}",', 1),
                encoding="utf-8")
            core = repo / MojibakeExemptionIsBoundedTest.CORE
            core.write_text(core.read_text(encoding="utf-8")
                            + "\n" + plant + "\n", encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("dead mojibake allowlist line", out)

    def test_an_allowlist_key_must_be_an_exempt_path(self):
        """The licence and the exemption list must name the same files — an
        allowlist entry for a path outside MOJIBAKE_EXEMPT_PATHS is a licence
        nobody reviewed as an exemption."""
        with repo_copy() as repo:
            tool = repo / "tools" / "mirror_check.py"
            src = tool.read_text(encoding="utf-8")
            marker = "MOJIBAKE_EXAMPLE_LINES = {"
            self.assertIn(marker, src)
            tool.write_text(
                src.replace(
                    marker,
                    marker + '\n    "plugins/agent-protocol/skills/'
                    'orchestrator-agent/references/x.md": '
                    '{"whatever \\xc2\\xa7"},', 1),
                encoding="utf-8")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("keyed to a non-exempt path", out)

    def test_the_pristine_allowlist_is_live_stays_green(self):
        with repo_copy() as repo:
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)


class PowerShellModuleSuffixTest(unittest.TestCase):
    """The inversion belongs to PowerShell's script READER, not to one suffix. A
    reviewer verified .psm1 mangles identically on 5.1 — so keying the exception on
    .ps1 alone left the trap armed one extension over, AND red-gated a correctly
    BOM'd module file for obeying the very doc this release ships.

    Round 2 repeated round 1 verbatim: .psrc (role capability) and .pssc (session
    configuration) are DATA files loaded through the same engine reader —
    Import-PowerShellDataFile mangled a BOM-less .psrc identically on 5.1, with no
    extension check anywhere on that path — and the fixed gate still red-gated a
    correctly BOM'd one. Both directions, all five suffixes."""

    SUFFIXES = (".ps1", ".psm1", ".psd1", ".psrc", ".pssc")

    def test_every_powershell_script_suffix_requires_the_bom(self):
        for ext in self.SUFFIXES:
            with self.subTest(ext=ext), repo_copy() as repo:
                write(repo, f"tools/demo{ext}", "Write-Output 'sect=§'\n".encode("utf-8"))
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("NO UTF-8 BOM", out)

    def test_a_correctly_bommed_module_is_green_not_red_gated(self):
        for ext in self.SUFFIXES:
            with self.subTest(ext=ext), repo_copy() as repo:
                write(repo, f"tools/demo{ext}",
                      BOM + "Write-Output 'sect=§'\n".encode("utf-8"))
                rc, out = run(repo)
                self.assertEqual(rc, 0, out)


class DeclarationDefaultTest(unittest.TestCase):
    def test_no_declaration_means_full_strictness(self):
        """The default is not 'trusting'. Deleting a twin with no declaration
        present must still fail — this is the r4 hole, and it stays closed."""
        with repo_copy() as repo:
            (repo / "docs" / "CREATOR-SEAT-BOOTSTRAP.html").unlink()
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("twin gate blind", out)


class MirrorTreeTest(unittest.TestCase):
    """docs_tree=false: the seven existence gates go quiet — and NOTHING else does."""

    _MIRROR_ABSENT = ("docs/CREATOR-SEAT-BOOTSTRAP.md",
                      "docs/CREATOR-SEAT-BOOTSTRAP.html",
                      "docs/SOP-REGISTRY.md",
                      "docs/CLOUD.md",
                      "CONTRIBUTING.md",
                      ".github/PULL_REQUEST_TEMPLATE.md",
                      ".github/ISSUE_TEMPLATE/protocol_amendment.md")

    def _mirror(self, repo):
        declare(repo, {"docs_tree": False})
        for rel in self._MIRROR_ABSENT:
            (repo / rel).unlink()
        # A real mirror does not TRACK these files either — round 17 made a
        # tracked-but-absent worktree path a finding (git still publishes
        # the blob), so the simulation must drop the index entries too.
        subprocess.run(["git", "update-index", "--force-remove", "--",
                        *self._MIRROR_ABSENT],
                       cwd=str(repo), capture_output=True)

    def test_a_declared_mirror_tree_is_green_without_the_docs_artifacts(self):
        with repo_copy() as repo:
            self._mirror(repo)
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_the_relaxation_is_printed_not_silent(self):
        """A reduced run that prints a bare 'green' is a lie by omission."""
        with repo_copy() as repo:
            self._mirror(repo)
            rc, out = run(repo)
            self.assertIn("docs_tree=false", out)
            self.assertIn("NOT APPLICABLE", out)
            self.assertIn("declared relaxation", out)

    def test_half_a_twin_pair_still_fails_in_a_mirror(self):
        """Absence of the pair is declared. Absence of HALF of it never is."""
        with repo_copy() as repo:
            self._mirror(repo)
            (repo / "docs" / "CREATOR-SEAT-BOOTSTRAP.md").write_text("# back\n")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("half-carried", out)

    def test_the_bom_gate_cannot_be_switched_off(self):
        """The one gate no declaration may ever relax."""
        with repo_copy() as repo:
            self._mirror(repo)
            write(repo, "transports/x.md", BOM + b"# x [PROTOCOL v2.8]\n")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("BOM (UTF-8", out)

    def test_skill_tree_gates_still_run_in_a_mirror(self):
        """docs_tree=false relaxes the DOCS tree, not the skill tree."""
        with repo_copy() as repo:
            self._mirror(repo)
            p = repo / "plugins/agent-protocol/skills/agent-core/references/channel-core.md"
            p.write_bytes(p.read_bytes().replace(b"v2.8", b"v2.5"))
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("missing PROTOCOL v2.8 stamp", out)


class StampExemptionTest(unittest.TestCase):
    """An exemption is the one place a bypass could hide, so it is bounded:
    enumerated, reasoned, non-stale, and printed."""

    SKILL = "plugins/agent-protocol/skills/agent-core/references/custody-copy.md"

    def _unstamped(self, repo):
        write(repo, self.SKILL, b"# a byte-identical custody copy\n")

    def test_an_unstamped_file_fails_without_an_exemption(self):
        with repo_copy() as repo:
            self._unstamped(repo)
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("missing PROTOCOL v2.8 stamp", out)

    def test_a_reasoned_exemption_makes_it_green_and_says_why(self):
        with repo_copy() as repo:
            self._unstamped(repo)
            declare(repo, {"stamp_exempt": [
                {"path": self.SKILL,
                 "reason": "byte-identical custody copy; stamping breaks custody"}]})
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)
            self.assertIn("stamp-exempt:", out)
            self.assertIn("breaks custody", out)

    def test_an_exemption_without_a_reason_is_refused(self):
        with repo_copy() as repo:
            self._unstamped(repo)
            declare(repo, {"stamp_exempt": [{"path": self.SKILL}]})
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("no non-empty string reason", out)
            self.assertIn("missing PROTOCOL v2.8 stamp", out)  # and nothing relaxed

    def test_a_stale_exemption_is_a_finding(self):
        """A list that outlives its files silently becomes a bypass."""
        with repo_copy() as repo:
            declare(repo, {"stamp_exempt": [
                {"path": "plugins/agent-protocol/skills/gone.md", "reason": "x"}]})
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("stale stamp exemption", out)

    def test_an_exemption_does_not_exempt_any_OTHER_file(self):
        with repo_copy() as repo:
            self._unstamped(repo)
            write(repo, "plugins/agent-protocol/skills/agent-core/references/other.md",
                  b"# no stamp here either\n")
            declare(repo, {"stamp_exempt": [
                {"path": self.SKILL, "reason": "custody copy"}]})
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("other.md", out)


class BrokenDeclarationTest(unittest.TestCase):
    """ALL-OR-NOTHING. The first cut honoured a broken declaration PIECEMEAL — it
    stripped a BOM and carried on, and an unknown key raised a finding while the keys
    it understood still took effect. Both reviewers walked straight through that.
    A defective declaration must now grant NOTHING.

    Each test below deletes a twin as a CANARY: if the relaxation leaked through
    despite the defect, the twin gate would be off and 'twin gate blind' would be
    absent. Asserting only 'the error was printed' would pass even if the bypass
    still worked — that is the trap the first version of these tests fell into."""

    def _defect(self, repo, **kw):
        (repo / "docs" / "CREATOR-SEAT-BOOTSTRAP.html").unlink()   # canary
        declare(repo, kw.pop("obj", None), **kw)
        return run(repo)

    def _assert_refused(self, rc, out):
        self.assertNotEqual(rc, 0, out)
        self.assertIn("REFUSED", out)
        self.assertIn("twin gate blind", out)      # the FULL gate set really ran
        self.assertNotIn("docs_tree=false", out)   # nothing was relaxed

    def test_unparseable_declaration_grants_nothing(self):
        with repo_copy() as repo:
            rc, out = self._defect(repo, raw=b'{"docs_tree": false, not json')
            self._assert_refused(rc, out)

    def test_a_bommed_declaration_grants_nothing(self):
        """The file that configures the BOM gate does not get to violate it."""
        with repo_copy() as repo:
            rc, out = self._defect(repo, raw=BOM + b'{"docs_tree": false}')
            self._assert_refused(rc, out)
            self.assertIn("byte-order mark", out)

    def test_an_unknown_key_grants_nothing(self):
        """A typo that silently does nothing is worse than an error: the author
        believes they declared something."""
        with repo_copy() as repo:
            rc, out = self._defect(repo, obj={"docs_trees": False,
                                              "docs_tree": False})
            self._assert_refused(rc, out)
            self.assertIn("unknown key", out)

    def test_a_non_boolean_docs_tree_grants_nothing(self):
        with repo_copy() as repo:
            rc, out = self._defect(repo, obj={"docs_tree": "false"})
            self._assert_refused(rc, out)

    def test_an_untracked_declaration_grants_nothing(self):
        """A file that relaxes gates must be visible in the diff that relaxes them.
        Both reviewers used an untracked declaration to silently relax a local run."""
        with repo_copy() as repo:
            rc, out = self._defect(repo, obj={"docs_tree": False}, track=False)
            self._assert_refused(rc, out)
            self.assertIn("NOT TRACKED", out)

    def test_a_non_list_stamp_exempt_grants_nothing(self):
        """A string here is the natural typo — and `for e in "a/b.md"` iterates
        CHARACTERS, so a validator-less tool would quietly exempt nothing while the
        author believes it exempted something. The reviewer deleted this validator
        and the suite stayed green; then the FIRST fix of this test was ALSO
        green-and-defeated: each iterated character fails the per-entry check, so
        "REFUSED" still printed — from the WRONG guard — and asserting only
        'stamp_exempt appears somewhere' was satisfied by it. Assert the list
        validator's OWN message, and include a non-iterable that would TRACEBACK
        without it: a crash is rc!=0 too, and a test that cannot tell a refusal
        from a crash defends nothing."""
        for bad in ("skills/x.md", 5):
            with self.subTest(value=bad), repo_copy() as repo:
                rc, out = self._defect(repo, obj={"docs_tree": False,
                                                  "stamp_exempt": bad})
                self._assert_refused(rc, out)
                self.assertIn("must be a list", out)
                self.assertNotIn("Traceback", out)

    def test_a_non_string_path_grants_nothing(self):
        """Same shape as the `reason` coercion bug one field over: a path that is a
        number, a list, or null must not be str()'d into something path-like."""
        for bad in (123, None, ["skills/x.md"], {"p": "x"}):
            with self.subTest(path=bad), repo_copy() as repo:
                rc, out = self._defect(repo, obj={
                    "docs_tree": False,
                    "stamp_exempt": [{"path": bad, "reason": "custody copy"}]})
                self._assert_refused(rc, out)

    def test_a_declaration_with_duplicate_keys_grants_nothing(self):
        """Round 15: json.loads keeps the LAST of duplicate keys, so
        {"docs_tree": true, "docs_tree": false} reads as reviewed-strict
        while enforcing relaxed — and it hid a full docs-artifact deletion
        behind a green run. Ambiguity in the file that weakens gates is a
        refusal at every object level."""
        with repo_copy() as repo:
            rc, out = self._defect(
                repo, raw=b'{"docs_tree": true, "docs_tree": false}')
            self._assert_refused(rc, out)
            self.assertIn("duplicate JSON key", out)

    def test_a_duplicate_exemption_entry_grants_nothing(self):
        """Round 15: two entries for one path print BOTH reasons while only
        one is in force — a review surface that disagrees with the effective
        declaration."""
        with repo_copy() as repo:
            rc, out = self._defect(repo, obj={"docs_tree": False, "stamp_exempt": [
                {"path": "transports/git-sync.md", "reason": "reason A"},
                {"path": "transports/git-sync.md", "reason": "reason B"}]})
            self._assert_refused(rc, out)
            self.assertIn("more than once", out)

    def test_a_symlink_declaration_grants_nothing(self):
        """Round 15: the tracked-ness control checks only the PATHNAME, so a
        tracked symlink (git mode 120000) satisfied it while the EFFECTIVE
        bytes came from an untracked target no diff ever reviewed. The
        declaration must be a regular file."""
        with repo_copy() as repo:
            probe = repo / "symlink-probe"
            try:
                os.symlink(repo / "README.md", probe)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable on this host")
            probe.unlink()
            (repo / "docs" / "CREATOR-SEAT-BOOTSTRAP.html").unlink()   # canary
            target = repo / ".decl-target.json"
            target.write_text('{"docs_tree": false}', encoding="utf-8")
            subprocess.run(["git", "config", "core.symlinks", "true"],
                           cwd=str(repo), capture_output=True)
            os.symlink(target, repo / DECL)
            subprocess.run(["git", "add", "-f", DECL], cwd=str(repo),
                           capture_output=True)
            rc, out = run(repo)
            self._assert_refused(rc, out)
            self.assertIn("symlink or reparse point", out)

    def test_a_hostile_exemption_path_refuses_the_whole_declaration(self):
        """Round 14: '..' and escaping paths were per-entry findings inside
        stamp_exemptions(), which runs AFTER docs_tree took effect — so a
        declaration carrying one hostile entry kept its OTHER relaxations
        active, and the strict docs findings never printed on the red run.
        Hostile input was never valid: it refuses everything. (A STALE
        entry stays a per-entry finding — drift is not hostility.)"""
        with self.subTest(escape="dotdot"), repo_copy() as repo:
            rc, out = self._defect(repo, obj={
                "docs_tree": False,
                "stamp_exempt": [{"path": "transports/../transports/git-sync.md",
                                  "reason": "probe"}]})
            self._assert_refused(rc, out)
            self.assertIn("contains '..'", out)
        with self.subTest(escape="absolute"), repo_copy() as repo:
            rc, out = self._defect(repo, obj={
                "docs_tree": False,
                "stamp_exempt": [{"path": str(repo.parent / "elsewhere.md"),
                                  "reason": "probe"}]})
            self._assert_refused(rc, out)
            self.assertIn("outside the repo", out)


class RelaxationsAreDisclosedOnREDTooTest(unittest.TestCase):
    """A red run is exactly when a reader most needs to know which gates were OFF —
    they are reading the findings to decide what the tree is. Printing the notes only
    on green means the one run anybody studies is the one that hides its own scope.
    The reviewer suppressed the notes on red and all 31 tests stayed green."""

    def test_a_failing_mirror_run_still_prints_what_was_relaxed(self):
        with repo_copy() as repo:
            declare(repo, {"docs_tree": False})
            for rel in ("docs/CREATOR-SEAT-BOOTSTRAP.md",
                        "docs/CREATOR-SEAT-BOOTSTRAP.html",
                        "docs/SOP-REGISTRY.md",
                        "CONTRIBUTING.md",
                        ".github/PULL_REQUEST_TEMPLATE.md",
                        ".github/ISSUE_TEMPLATE/protocol_amendment.md"):
                (repo / rel).unlink()
            write(repo, "transports/x.md", BOM + b"# x [PROTOCOL v2.8]\n")  # force red
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("BOM (UTF-8", out)
            self.assertIn("docs_tree=false", out)          # scope still disclosed
            self.assertIn("declared relaxation", out)


class ReasonMustBeARealReasonTest(unittest.TestCase):
    """`str(entry.get("reason", ""))` turned null into "None", 0 into "0" and False
    into "False" — every one a reason-less exemption passing GREEN. Both reviewers
    found it. Coercion is not validation."""

    SKILL = "plugins/agent-protocol/skills/agent-core/references/custody-copy.md"

    def _try_reason(self, repo, reason):
        write(repo, self.SKILL, b"# a custody copy, no stamp\n")
        entry = {"path": self.SKILL}
        if reason is not ...:
            entry["reason"] = reason
        declare(repo, {"stamp_exempt": [entry]})
        return run(repo)

    def test_falsy_and_non_string_reasons_are_all_refused(self):
        for reason in (None, 0, False, [], {}, "   ", "", ...):
            with self.subTest(reason=reason), repo_copy() as repo:
                rc, out = self._try_reason(repo, reason)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("REFUSED", out)
                # and the exemption did NOT take effect
                self.assertIn("missing PROTOCOL v2.8 stamp", out)

    def test_a_real_reason_is_honoured(self):
        with repo_copy() as repo:
            rc, out = self._try_reason(repo, "byte-identical custody copy")
            self.assertEqual(rc, 0, out)


class ExemptionPathIsConfinedTest(unittest.TestCase):
    def test_a_path_escaping_the_repo_is_refused(self):
        """Round 13 split this refusal in two: a '..' segment is refused
        LEXICALLY (it would make the lexical key and the file it names
        disagree) before resolution ever runs, and the resolve-based
        confinement remains for the escapes '..' does not cover — an
        absolute path out of the tree. Round 14 moved both into the
        declaration-level REFUSED path: hostile input was never valid."""
        with self.subTest(escape="dotdot"), repo_copy() as repo:
            declare(repo, {"stamp_exempt": [
                {"path": "../../../etc/passwd", "reason": "nope"}]})
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("contains '..'", out)
            self.assertIn("REFUSED", out)
        with self.subTest(escape="absolute"), repo_copy() as repo:
            outside = (repo.parent / "outside-target.md")
            outside.write_text("PROTOCOL v2.8\n", encoding="utf-8")
            try:
                declare(repo, {"stamp_exempt": [
                    {"path": str(outside), "reason": "nope"}]})
                rc, out = run(repo)
            finally:
                outside.unlink()
            self.assertNotEqual(rc, 0, out)
            self.assertIn("outside the repo", out)
            self.assertIn("REFUSED", out)

    def test_a_noncanonical_spelling_is_refused(self):
        """Round 15: the loader accepted backslashes, trailing slashes, '.'
        segments, and absolute in-repo paths, then NORMALIZED them into the
        lexical key — a tracked declaration whose visible spelling is not
        the enforced key, and which means something different (or goes
        stale) on another OS. A lexical key has exactly one spelling."""
        cases = [("backslashes", "transports\\custody\\copy.md"),
                 ("trailing-slash", "transports/custody/copy.md/"),
                 ("dot-segment", "transports/./custody/copy.md"),
                 ("absolute-in-repo", None)]      # built per-repo below
        for label, spelling in cases:
            with self.subTest(form=label), repo_copy() as repo:
                custody = repo / "transports" / "custody"
                custody.mkdir(parents=True, exist_ok=True)
                (custody / "copy.md").write_text("no stamp here\n",
                                                 encoding="utf-8")
                path = spelling if spelling else \
                    (repo / "transports" / "custody" / "copy.md").as_posix()
                declare(repo, {"stamp_exempt": [
                    {"path": path, "reason": "probe"}]})
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("REFUSED", out)
                self.assertIn("canonical", out)
                self.assertIn("missing PROTOCOL v2.8 stamp", out)  # nothing granted

    def test_a_case_variant_spelling_is_refused_where_it_finds_a_file(self):
        """Round 16: canonical FORM is not enough — is_file() answers
        case-insensitively on Windows, so 'Transports/x.md' passed every
        check, printed its reason, exempted NOTHING (the lexical key never
        matches the walked path), and reads as STALE on a case-sensitive
        host. One declaration must mean one thing on every host."""
        with repo_copy() as repo:
            if not (repo / "TRANSPORTS" / "git-sync.md").is_file():
                self.skipTest("case-sensitive filesystem: the wrong-case "
                              "spelling is the stale path here, already gated")
            (repo / "transports" / "custody-copy.md").write_text(
                "no stamp here\n", encoding="utf-8")
            declare(repo, {"stamp_exempt": [
                {"path": "Transports/custody-copy.md", "reason": "probe"}]})
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("REFUSED", out)
            self.assertIn("exact spelling", out)


class ShippedArtifactExistenceTest(unittest.TestCase):
    """Round 15: every content gate below the existence line validates a file
    only if it is PRESENT — so deleting transports/ outright, either shipped
    transport profile, a whole role tree, or any role's SKILL.md entrypoint
    was green: an acceptance gate certifying a release that no longer ships
    what it says it ships. Existence is its own gate."""

    def test_a_deleted_transport_profile_is_a_finding(self):
        for rel in ("transports/local-fs.md", "transports/git-sync.md"):
            with self.subTest(rel=rel), repo_copy() as repo:
                (repo / rel).unlink()
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("shipped transport missing", out)

    def test_a_deleted_transports_tree_is_a_finding(self):
        with repo_copy() as repo:
            shutil.rmtree(repo / "transports")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("shipped transport missing", out)

    def test_a_deleted_load_bearing_tool_or_profile_is_a_finding(self):
        """Round 16: the round-15 existence list was treated as complete and
        was not — profiles/ and tools/new_project.py were deletable-to-green,
        and new_project.py's absence silently disarmed the section-8
        auth-log drift gate (a content gate conditional on both files)."""
        for rel in ("profiles/README.md", "profiles/MODELS.md",
                    "tools/new_project.py"):
            with self.subTest(rel=rel), repo_copy() as repo:
                (repo / rel).unlink()
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("load-bearing shipped file missing", out)

    def test_a_deleted_cloud_doc_is_a_finding_unless_declared(self):
        """docs/CLOUD.md is the doc half of the shipped git-sync transport;
        it lives under docs/, so its existence follows the docs_tree
        declaration like the other docs artifacts."""
        with self.subTest(mode="strict"), repo_copy() as repo:
            (repo / "docs" / "CLOUD.md").unlink()
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("docs/CLOUD.md missing", out)
        with self.subTest(mode="declared-mirror"), repo_copy() as repo:
            (repo / "docs" / "CLOUD.md").unlink()
            subprocess.run(["git", "update-index", "--force-remove", "--",
                            "docs/CLOUD.md"],
                           cwd=str(repo), capture_output=True)
            declare(repo, {"docs_tree": False})
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_a_missing_skill_entrypoint_is_a_finding(self):
        for role in ("agent-core", "owner-engine-agent",
                     "helper-builder-agent", "orchestrator-agent"):
            with self.subTest(role=role), repo_copy() as repo:
                (repo / "plugins" / "agent-protocol" / "skills" / role
                 / "SKILL.md").unlink()
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("skill entrypoint missing", out)
                self.assertIn(role, out)

    def test_a_deleted_role_tree_is_a_finding(self):
        with repo_copy() as repo:
            shutil.rmtree(repo / "plugins" / "agent-protocol" / "skills"
                          / "orchestrator-agent")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("skill entrypoint missing", out)


class TrackedCaseCollisionTest(unittest.TestCase):
    def test_a_tracked_non_ascii_name_is_still_scanned(self):
        """Round 16 BLOCKER: git emits pathnames as UTF-8 bytes, but text=True
        decoded them with the WINDOWS LOCALE (cp1252) — a tracked 'café.md'
        became a phantom path, the real file read as untracked (skipped under
        a cache dir), and its BOM'd blob was invisible to the very gate that
        claims tracked files."""
        with repo_copy() as repo:
            nm = repo / "node_modules"
            nm.mkdir(exist_ok=True)
            (nm / "café.md").write_bytes(BOM + b"# bommed tracked\n")
            subprocess.run(["git", "add", "-f", "node_modules/café.md"],
                           cwd=str(repo), capture_output=True)
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("BOM", out)
            self.assertIn("café.md", out)

    def test_a_trailing_dot_index_alias_is_a_finding(self):
        """Round 16: 'x.md.' is a valid index name whose worktree spelling
        ALIASES to 'x.md' on Windows — a clean stamped visible file answered
        for a BOM'd unstamped blob the gate never read."""
        with repo_copy() as repo:
            vis = repo / "transports" / "WinAlias.md"
            vis.write_bytes(b"# alias probe [PROTOCOL v2.8]\n")
            subprocess.run(["git", "add", "-f", "transports/WinAlias.md"],
                           cwd=str(repo), capture_output=True)
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=BOM + b"# no stamp\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "-c", "core.protectNTFS=false", "update-index",
                 "--add", "--cacheinfo",
                 f"100644,{sha},transports/WinAlias.md."],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot inject trailing-dot index entry here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("non-portable tracked path", out)

    def test_a_normalization_variant_index_pair_is_a_finding(self):
        """Round 16 (judge NIT, folded): casefold() does not collapse NFC/NFD
        spellings of one name, which collide on a normalization-insensitive
        filesystem — the collision key now folds NFC first."""
        with repo_copy() as repo:
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=b"# x [PROTOCOL v2.8]\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            nfc = "transports/caféprobe.md"
            nfd = "transports/caféprobe.md"
            self.assertNotEqual(nfc, nfd)   # really two spellings
            for name in (nfc, nfd):
                r = subprocess.run(
                    ["git", "update-index", "--add", "--cacheinfo",
                     f"100644,{sha},{name}"],
                    cwd=str(repo), capture_output=True)
                if r.returncode != 0:
                    self.skipTest("cannot inject normalization-variant entry")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("case-colliding tracked paths", out)

    def test_a_tracked_file_missing_from_the_worktree_is_a_finding(self):
        """Round 17 (part of the BLOCKER): the tracked-set tail silently
        DROPPED entries with no worktree file — a tracked name whose file is
        deleted (or can never materialize on this host) still publishes its
        index blob, unscanned."""
        with self.subTest(how="index-only injection"), repo_copy() as repo:
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=b"# clean\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "update-index", "--add", "--cacheinfo",
                 f"100644,{sha},node_modules/ghost.md"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot inject index-only entry here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("missing from the worktree", out)
        with self.subTest(how="worktree deletion"), repo_copy() as repo:
            nm = repo / "node_modules"
            nm.mkdir(exist_ok=True)
            p = nm / "gone.md"
            p.write_bytes(BOM + b"# bommed then deleted\n")
            subprocess.run(["git", "add", "-f", "node_modules/gone.md"],
                           cwd=str(repo), capture_output=True)
            p.unlink()
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("missing from the worktree", out)

    def test_a_divergent_index_blob_is_scanned_not_trusted(self):
        """Round 17 BLOCKER: every byte gate read WORKTREE bytes, but a
        commit or archive ships the INDEX blob — a BOM'd blob swapped into
        the index behind a clean worktree twin was green."""
        with repo_copy() as repo:
            nm = repo / "node_modules"
            nm.mkdir(exist_ok=True)
            (nm / "staged.md").write_bytes(b"# clean worktree twin\n")
            subprocess.run(["git", "add", "-f", "node_modules/staged.md"],
                           cwd=str(repo), capture_output=True)
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=BOM + b"# hostile\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "update-index", "--cacheinfo",
                 f"100644,{sha},node_modules/staged.md"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot swap an index blob here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("BOM", out)
            self.assertIn("(index blob)", out)

    def test_a_mojibake_index_blob_under_the_skill_tree_is_a_finding(self):
        """The divergence scan feeds skill-tree .md blobs through the
        mojibake detector too — a mangled staged blob behind a clean
        worktree file is corruption git would publish."""
        with repo_copy() as repo:
            rel = "plugins/agent-protocol/skills/agent-core/SKILL.md"
            mangled = chr(0x2014).encode("utf-8").decode("cp1252") \
                .encode("utf-8")
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo),
                               input=b"# heading\nmangled " + mangled +
                                     b" dash\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "update-index", "--cacheinfo", f"100644,{sha},{rel}"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot swap an index blob here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in the index blob", out)

    def test_a_win32_forbidden_character_name_is_a_finding(self):
        """Round 17: the first non-portable cut knew trailing dot/space and
        the classic device stems — a segment carrying a character Win32
        forbids outright ('?', ':', '<', ...) cannot check out on Windows at
        all, and its blob sailed through."""
        with repo_copy() as repo:
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=b"# clean\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "-c", "core.protectNTFS=false", "update-index",
                 "--add", "--cacheinfo",
                 f"100644,{sha},node_modules/bad?name.md"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot inject forbidden-character entry here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("non-portable tracked path", out)

    def test_a_console_device_alias_name_is_a_finding(self):
        """Round 17: CONIN$/CONOUT$ are console-device aliases and Windows
        reads superscript 1/2/3 as digits in COM/LPT stems — names the
        classic reserved list does not contain."""
        for seg in ("CONIN$.txt", "COM" + chr(0xB9) + ".txt"):
            with self.subTest(seg=seg), repo_copy() as repo:
                h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                                   cwd=str(repo), input=b"# clean\n",
                                   capture_output=True)
                sha = h.stdout.decode("ascii").strip()
                r = subprocess.run(
                    ["git", "-c", "core.protectNTFS=false", "update-index",
                     "--add", "--cacheinfo",
                     f"100644,{sha},node_modules/{seg}"],
                    cwd=str(repo), capture_output=True)
                if r.returncode != 0:
                    self.skipTest("cannot inject device-alias entry here")
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("non-portable tracked path", out)

    def test_a_non_regular_index_entry_is_a_finding(self):
        """A mode-120000 entry publishes its target path as the blob; the
        byte gates certify regular files only, so the mode itself is the
        finding."""
        with repo_copy() as repo:
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=b"target/elsewhere.md",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "update-index", "--add", "--cacheinfo",
                 f"120000,{sha},node_modules/link.md"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot inject symlink-mode entry here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("non-regular index entry", out)

    def test_an_index_name_answering_through_an_alias_is_a_finding(self):
        """Round 17 (judge): an index name that RESOLVES to a differently
        spelled worktree file — an 8.3 short name, a lone case variant —
        needs no second tracked entry, so the collision key never fires,
        and the byte gates read the visible file's bytes under a name git
        does not publish them as."""
        with self.subTest(form="lone case variant"), repo_copy() as repo:
            content = b"# alias probe\n"
            (repo / "transports" / "AliasOnly.md").write_bytes(content)
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=content,
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "update-index", "--add", "--cacheinfo",
                 f"100644,{sha},transports/aliasonly.md"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot inject case-alias entry here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertTrue("answers through an alias" in out
                            or "missing from the worktree" in out, out)
        with self.subTest(form="8.3 short name"), repo_copy() as repo:
            long_name = "longalias-probe-file.md"
            (repo / "transports" / long_name).write_bytes(b"# long probe\n")
            subprocess.run(["git", "add", "-f", f"transports/{long_name}"],
                           cwd=str(repo), capture_output=True)
            try:
                d = subprocess.run(
                    ["cmd", "/c", "dir", "/x", str(repo / "transports")],
                    capture_output=True, text=True, errors="replace")
            except FileNotFoundError:  # no cmd.exe — POSIX host
                self.skipTest("host generates no 8.3 short names here")
            m = re.search(r"(\S+~\d\S*)\s+" + re.escape(long_name),
                          d.stdout or "")
            if not m:
                self.skipTest("host generates no 8.3 short names here")
            short = f"transports/{m.group(1)}"
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=BOM + b"# no stamp\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "-c", "core.protectNTFS=false", "update-index",
                 "--add", "--cacheinfo", f"100644,{sha},{short}"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot inject 8.3-alias entry here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertTrue("answers through an alias" in out
                            or "missing from the worktree" in out, out)

    def test_an_unmerged_index_entry_is_a_finding(self):
        """A tree with unresolved merge stages has no single answer for what
        git would publish — certifying one is certifying a guess."""
        with repo_copy() as repo:
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=b"# clean\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            info = f"100644 {sha} 1\tnode_modules/conflict.md\n"
            r = subprocess.run(["git", "update-index", "--index-info"],
                               cwd=str(repo), input=info.encode("ascii"),
                               capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot inject an unmerged stage entry here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("unmerged index entry", out)

    def test_a_missing_staged_object_is_a_finding_not_a_crash(self):
        """Round 19: the staged-blob batch reader must REPORT, not crash, on
        a header it cannot parse. A cacheinfo entry pointing at a sha not in
        the object db makes `git cat-file --batch` answer '<sha> missing' —
        the reachable shape of a malformed/unreadable response — and the
        parser must yield a fail-closed finding without a traceback (the
        no-crash contract, arriving through the object store)."""
        with repo_copy() as repo:
            bogus = "dead" + "0" * 36
            r = subprocess.run(
                ["git", "update-index", "--add", "--cacheinfo",
                 f"100644,{bogus},node_modules/ghostobj.md"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot inject a dangling-sha index entry here")
            rc, out = run(repo)
            self.assertNotIn("Traceback", out)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("cannot read the staged blob", out)

    def test_a_stat_cache_hidden_divergent_blob_is_a_finding(self):
        """Round 18 (the second green defeat of asking git diff): a staged
        blob behind an UNCHANGED stat cache — same size, same mtime, file
        mtime older than the index write — is never content-compared, so
        diff reports nothing while the index publishes hostile bytes. The
        scan reads every staged blob by object id; there is no stat cache
        to consult."""
        with repo_copy() as repo:
            nm = repo / "node_modules"
            nm.mkdir(exist_ok=True)
            p = nm / "statcache.md"
            hostile = BOM + b"# hostile bytes 123\n"
            clean = b"# clean twin bytes 123\n"
            self.assertEqual(len(hostile), len(clean))
            p.write_bytes(hostile)
            old = 1_600_000_000_000_000_000
            os.utime(p, ns=(old, old))
            subprocess.run(["git", "add", "-f", "node_modules/statcache.md"],
                           cwd=str(repo), capture_output=True)
            p.write_bytes(clean)
            os.utime(p, ns=(old, old))
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("(index blob)", out)

    def test_an_uppercase_suffix_staged_blob_is_mojibake_scanned(self):
        """Round 18: the staged-blob mojibake leg selected on
        endswith('.md') while every other suffix decision here is
        case-normalized — a staged UPPER.MD blob took the BOM leg only and
        published mojibake green."""
        with repo_copy() as repo:
            rel = ("plugins/agent-protocol/skills/agent-core/references/"
                   "UPPER.MD")
            (repo / rel).write_bytes(b"# clean upper [PROTOCOL v2.8]\n")
            subprocess.run(["git", "add", "-f", rel],
                           cwd=str(repo), capture_output=True)
            mangled = chr(0x2014).encode("utf-8").decode("cp1252") \
                .encode("utf-8")
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo),
                               input=b"# stamped [PROTOCOL v2.8]\nmangled " +
                                     mangled + b" dash\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "update-index", "--cacheinfo", f"100644,{sha},{rel}"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot swap an index blob here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("mojibake in the index blob", out)

    def test_a_flag_hidden_divergent_blob_is_a_finding(self):
        """Round 18 (judge): git diff IGNORES assume-unchanged and
        skip-worktree entries by design, so the divergence scan was blind
        exactly there — a BOM'd staged blob behind either bit was green.
        The flag itself is the finding: an instruction not to compare an
        entry is an entry this gate cannot certify."""
        for flag in ("--assume-unchanged", "--skip-worktree"):
            with self.subTest(flag=flag), repo_copy() as repo:
                rel = "transports/local-fs.md"
                hostile = BOM + (repo / rel).read_bytes()
                h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                                   cwd=str(repo), input=hostile,
                                   capture_output=True)
                sha = h.stdout.decode("ascii").strip()
                subprocess.run(
                    ["git", "update-index", "--cacheinfo",
                     f"100644,{sha},{rel}"],
                    cwd=str(repo), capture_output=True)
                r = subprocess.run(["git", "update-index", flag, rel],
                                   cwd=str(repo), capture_output=True)
                if r.returncode != 0:
                    self.skipTest(f"cannot set {flag} here")
                rc, out = run(repo)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("hidden from divergence comparison", out)

    def test_a_routinely_dirty_tree_stays_green(self):
        """The divergence scan must not make a working tree unusable: an
        ordinary uncommitted edit diverges from the index, but the staged
        blob is the last committed content — clean — so the gate stays
        green. Red-on-any-divergence would gate every fold on itself."""
        with repo_copy() as repo:
            p = repo / "tests" / "test_tree_declaration.py"
            with open(p, "ab") as f:
                f.write(b"\n# routine uncommitted edit\n")
            rc, out = run(repo)
            self.assertEqual(rc, 0, out)

    def test_case_colliding_index_entries_are_a_finding(self):
        """Round 15: git happily tracks two paths differing only in case,
        each with its OWN blob — but a case-insensitive worktree shows one
        file, so every byte gate here read the visible bytes and certified
        a released blob it never saw. Detectable only in the raw ls-files
        names (Path objects collapse the variants)."""
        with repo_copy() as repo:
            vis = repo / "transports" / "CaseProbe.md"
            vis.write_bytes(b"# case probe [PROTOCOL v2.8]\n")
            subprocess.run(["git", "add", "-f", "transports/CaseProbe.md"],
                           cwd=str(repo), capture_output=True)
            h = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                               cwd=str(repo), input=BOM + b"# no stamp\n",
                               capture_output=True)
            sha = h.stdout.decode("ascii").strip()
            r = subprocess.run(
                ["git", "update-index", "--add", "--cacheinfo",
                 f"100644,{sha},transports/caseprobe.md"],
                cwd=str(repo), capture_output=True)
            if r.returncode != 0:
                self.skipTest("cannot inject case-variant index entry here")
            rc, out = run(repo)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("case-colliding tracked paths", out)


if __name__ == "__main__":
    unittest.main()
