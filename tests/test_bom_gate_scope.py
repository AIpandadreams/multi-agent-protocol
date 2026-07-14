"""The byte gate must cover EVERY published file — not a subtree, not a suffix list.

Two narrow versions of this gate have now shipped a defect:

1. Scoped to the skills subtree, it missed a BOM written into the release
   MANIFESTS (`.json`, outside the subtree). Every other gate read TEXT, where a
   BOM is invisible. The suite stayed green.
2. Widened to the repo but gated on a SUFFIX ALLOWLIST, it still missed every
   tracked extensionless machine-read file — `.github/CODEOWNERS` (which is the
   mechanical backstop for principal-locked paths), `.gitignore`, `LICENSE`.

So the gate scans every file, and this proves it on the surfaces each narrow
version missed. Green is not the assertion; the FINDING is.
"""
import unittest

try:                                    # discovery (`-s tests`) puts tests/ on the path
    from _mirror_fixture import repo_copy, run_mirror_check
except ImportError:                     # `python -m unittest tests.test_...` does not
    from tests._mirror_fixture import repo_copy, run_mirror_check

BOM = b"\xef\xbb\xbf"

# One representative of every class the two narrow gates excluded.
SURFACES = [
    # the manifests the first narrow gate missed
    "plugins/agent-protocol/.claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    # extensionless, machine-read — what the suffix allowlist missed
    ".github/CODEOWNERS",
    ".gitignore",
    "LICENSE",
    # inside the skill tree (the original gate's only scope — must still fire)
    "plugins/agent-protocol/skills/agent-core/references/channel-core.md",
    # docs, twins, tooling, root files
    "docs/CREATOR-SEAT-BOOTSTRAP.md",
    "docs/CREATOR-SEAT-BOOTSTRAP.html",
    "transports/local-fs.md",
    "tools/mirror_check.py",
    "README.md",
    "CHANGELOG.md",
]


class BomGateScopeTest(unittest.TestCase):
    def test_the_real_repo_carries_no_bom(self):
        with repo_copy() as repo:
            rc, out = run_mirror_check(repo)
            self.assertNotIn("BOM (", out)
            self.assertEqual(rc, 0, out)

    def test_a_planted_bom_is_caught_on_every_surface(self):
        for rel in SURFACES:
            with self.subTest(path=rel), repo_copy() as repo:
                target = repo / rel
                self.assertTrue(target.is_file(), f"{rel} vanished from the repo")
                target.write_bytes(BOM + target.read_bytes())
                rc, out = run_mirror_check(repo)
                self.assertNotEqual(rc, 0, f"gate passed a BOM in {rel}")
                self.assertIn("BOM (", out)
                self.assertIn(rel.split("/")[-1], out)

    def test_every_bom_encoding_is_caught_not_just_utf8(self):
        # The gate checked only EF BB BF — while UTF-16 is Windows PowerShell
        # 5.1's DEFAULT output encoding, i.e. the likeliest BOM to land here by
        # accident. A UTF-16 CODEOWNERS passed every gate green.
        # Every signature the gate lists, so the claim "checks every BOM" is
        # proven, not asserted — UTF-32 LE included, whose FF FE prefix the gate
        # must disambiguate from UTF-16 LE by matching the 4-byte form first.
        for name, bom in [("utf-8", b"\xef\xbb\xbf"),
                          ("utf-16-le", b"\xff\xfe"),
                          ("utf-16-be", b"\xfe\xff"),
                          ("utf-32-be", b"\x00\x00\xfe\xff"),
                          ("utf-32-le", b"\xff\xfe\x00\x00")]:
            with self.subTest(bom=name), repo_copy() as repo:
                target = repo / ".github" / "CODEOWNERS"
                target.write_bytes(bom + target.read_bytes())
                rc, out = run_mirror_check(repo)
                self.assertNotEqual(rc, 0, f"gate passed a {name} BOM")
                self.assertIn("CODEOWNERS", out)

    def test_a_new_file_type_is_covered_without_touching_the_gate(self):
        # The suffix allowlist meant every new file type arrived UNGATED by
        # default. Coverage must not depend on someone remembering to add an
        # extension: a file the gate has never heard of is still scanned.
        for rel in ("Dockerfile", "data.csv", "app.js", "Makefile"):
            with self.subTest(path=rel), repo_copy() as repo:
                (repo / rel).write_bytes(BOM + b"whatever\n")
                rc, out = run_mirror_check(repo)
                self.assertNotEqual(rc, 0, f"gate passed a BOM in {rel}")
                self.assertIn(rel, out.replace("\\", "/"))

    def test_git_unavailable_is_itself_a_finding_even_on_a_clean_tree(self):
        # The r4 bypass: tracked_files() returned an empty set when git could
        # not answer, so the gate scanned nothing and passed. The fix is
        # fail-CLOSED — no git means the exact publish scope is unknowable, and
        # that is a finding in its own right, not a green.
        with repo_copy(git=False) as repo:
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("git unavailable", out)

    def test_git_unavailable_still_catches_a_planted_bom(self):
        # Fail-closed must not mean fail-blind: with git gone the gate widens to
        # the whole tree (minus .git), so a real BOM is still caught — the
        # scope-reduced finding rides ALONGSIDE the BOM finding, never instead
        # of it.
        with repo_copy(git=False) as repo:
            target = repo / "CHANGELOG.md"
            target.write_bytes(BOM + target.read_bytes())
            rc, out = run_mirror_check(repo)
            self.assertNotEqual(rc, 0)
            self.assertIn("git unavailable", out)
            self.assertIn("BOM (", out)
            self.assertIn("CHANGELOG.md", out)


if __name__ == "__main__":
    unittest.main()
