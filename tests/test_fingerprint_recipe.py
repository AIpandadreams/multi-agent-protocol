"""The published set-fingerprint recipe must be fail-CLOSED.

`git ls-files -s --error-unmatch -- <set> | sha256sum` LOOKS like it errors on a
missing member, but the pipe hands its exit status to sha256sum, which returns 0 —
so a mistyped member is silently dropped and the digest is computed over only the
tracked members (fail-open). Both round-5 reviewers reproduced this. Every
published copy therefore wraps the pipe in a `set -o pipefail` guard so git's
--error-unmatch failure propagates.

Two tests:
  - behavioral (needs bash): the guarded recipe exits nonzero on a missing member
    and zero on a valid set, and the bare pipe is shown to be the fail-open form —
    so the guard is demonstrably what closes the hole;
  - doc-drift (pure Python): wherever the recipe appears in the docs the guard
    appears with it, so a future edit cannot quietly revert to the bare pipe.
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {".git", ".venv", "venv", "__pycache__", "node_modules",
        ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def _guarded(members):
    """The canonical fail-closed recipe over `members`."""
    return ("( set -o pipefail; git rev-parse HEAD && git ls-files -s "
            f"--error-unmatch -- {' '.join(members)} | sha256sum )")


def _bash(script):
    return subprocess.run(["bash", "-c", script], cwd=str(ROOT),
                          capture_output=True, text=True)


class RecipeBehaviorTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("bash"), "bash not on PATH")
    def test_the_guarded_recipe_is_green_on_a_valid_set(self):
        r = _bash(_guarded(["CHANGELOG.md", "README.md"]))
        self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipUnless(shutil.which("bash"), "bash not on PATH")
    def test_the_guarded_recipe_fails_closed_on_a_missing_member(self):
        r = _bash(_guarded(["CHANGELOG.md", "not-a-real-member-xyz"]))
        self.assertNotEqual(r.returncode, 0,
                            "guarded recipe passed a missing member — fail-open")

    @unittest.skipUnless(shutil.which("bash"), "bash not on PATH")
    def test_the_bare_pipe_is_the_fail_open_form_the_guard_fixes(self):
        # The control that proves the guard is load-bearing: the SAME command
        # without `set -o pipefail` exits 0 even though git failed. If this ever
        # starts propagating on its own, the guard's rationale changed and the
        # docs should be revisited.
        bare = ("git ls-files -s --error-unmatch -- CHANGELOG.md "
                "not-a-real-member-xyz | sha256sum")
        b = _bash(bare)
        self.assertEqual(b.returncode, 0,
                         "bare pipe propagated git's failure unaided — the "
                         "fail-open premise no longer holds; revisit the recipe")


class RecipeDocParityTest(unittest.TestCase):
    """Wherever a DIGEST recipe is published, the pipefail guard must wrap THAT
    command — bound to the recipe, not merely present somewhere in the file.

    The first version of this guard asserted `pipefail` anywhere in the doc, and
    both round-6 reviewers defeated it the same way: revert one recipe line to the
    bare pipe while leaving an adjacent sentence's "pipefail" mention intact, and
    the test stayed green. That is the exact fail-open this guard exists to
    prevent — a guard with the hole it guards against. So the check is now
    positional: for each `git ls-files … | sha256sum` command, `set -o pipefail`
    must appear in the short window right before it (which spans the
    `( set -o pipefail; git rev-parse HEAD && ` prefix), not merely in the file."""

    # A DIGEST recipe: the git command piped into sha256sum. The unpiped inspect
    # step `git ls-files … <set>` has no sha256sum and is correctly NOT matched;
    # prose that mentions `--error-unmatch` and `sha256sum` separately is not a
    # command (no literal `git ls-files -s --error-unmatch … | sha256sum`) and
    # does not match either.
    RECIPE = re.compile(r"git ls-files -s --error-unmatch[\s\S]{0,160}?\|\s*sha256sum")
    LOOKBACK = 50   # > the ~24 chars from `set -o pipefail` to `git ls-files`,
                    # < the distance to an unrelated prose mention elsewhere.

    @classmethod
    def unguarded(cls, text):
        """Every digest recipe in `text` whose command is NOT preceded by a
        `set -o pipefail` guard within LOOKBACK chars."""
        return [m.group(0) for m in cls.RECIPE.finditer(text)
                if "set -o pipefail" not in text[max(0, m.start() - cls.LOOKBACK):m.start()]]

    def _doc_surfaces(self):
        return [p for p in ROOT.rglob("*.md")
                if not any(part in SKIP for part in p.relative_to(ROOT).parts)]

    def test_every_published_recipe_is_guarded_at_the_command(self):
        checked = 0
        for p in self._doc_surfaces():
            t = p.read_text(encoding="utf-8", errors="replace")
            checked += len(self.RECIPE.findall(t))
            bad = self.unguarded(t)
            self.assertFalse(bad, f"{p.relative_to(ROOT)} publishes a digest recipe "
                             f"with no `set -o pipefail` guard on the command itself "
                             f"(fail-open — the pipe masks git's failure): {bad}")
        # Guard the guard: finding NOTHING must not read as a pass.
        self.assertGreater(checked, 0,
            "no digest recipe found in any doc — this test would pass vacuously")

    def test_the_guard_check_catches_a_stripped_guard(self):
        # The mutation test both round-6 reviewers asked for: stripping the guard
        # from a real recipe must be caught, EVEN with a `pipefail` mention living
        # elsewhere in the same text (the file-level assertIn this replaced was not).
        guarded = ("( set -o pipefail; git rev-parse HEAD && git ls-files -s "
                   "--error-unmatch -- a.md b.md | sha256sum )")
        self.assertEqual(self.unguarded(guarded), [], "control: guarded recipe is clean")
        # the exact defeating shape from round 6: a distant prose 'pipefail' + a
        # bare recipe line. The distant mention must NOT rescue the bare command.
        defeating = ("We discuss set -o pipefail as a concept up here.\n\n"
                     + "filler " * 20 + "\n\n"
                     "git ls-files -s --error-unmatch -- a.md b.md | sha256sum\n")
        self.assertTrue(self.unguarded(defeating),
                        "a bare recipe with a distant pipefail mention slipped the "
                        "guard — the check is still effectively file-level")


if __name__ == "__main__":
    unittest.main()
