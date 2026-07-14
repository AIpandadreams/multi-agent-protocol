"""Shared fixture: run tools/mirror_check.py over a MUTATED copy of the real repo.

Gates are only worth what their failing case is worth. Asserting that a gate is
green on a clean tree proves nothing — every gate this repo has ever shipped was
green on the tree that carried the defect. So each guard gets a mutation test:
copy the repo, break exactly one thing, and assert the gate says so.

Two properties worth knowing before you debug a surprise:
  - The copy is of the WORKING TREE, not `git ls-files` — so an uncommitted local
    file with a BOM in it will red these tests. That is deliberate: the gate is
    blind to nothing, and a scratch file that fails it is a true finding about
    your tree, not a false one about the repo.
  - `repo_copy()` gives the copy a real git index (`git init` + `git add -A`, no
    commit, no identity needed), so mirror_check runs the SAME path it runs in CI
    — tracked-file resolution succeeds. This matters: mirror_check's BOM gate
    fails LOUD when git cannot answer (the r4 bypass was git-unavailable →
    tracked set empty → scan nothing). A fixture that stripped git would put
    every run on that fallback path, and every mutation test would then go green
    on the git-unavailable finding instead of on the defect it planted — a
    false-green of exactly the class this suite exists to prevent. Use
    `repo_copy(git=False)` ONLY to exercise the git-unavailable branch on purpose.

Cost: the git index is built ONCE, on a module-scoped pristine copy; each
mutation copies that pristine tree (its `.git` is index-only, so the copy is
cheap) rather than re-running `git add` 40+ times.
"""
import atexit
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Skip VCS internals, caches, and any in-repo virtualenv or vendored tree — the
# copy runs once per mutation, so a developer with a .venv in the repo would
# otherwise pay for it on every case.
IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache",
                                ".mypy_cache", ".ruff_cache", "*.pyc",
                                ".venv", "venv", "node_modules")

_PRISTINE = None


def _pristine() -> Path:
    """A copy of the working tree with a fresh git index, built once per run.

    `git add -A` populates the index so `git ls-files` answers exactly as it
    does in CI; no commit and no user identity are required for that. The
    resulting `.git` holds only an index + refs (no packs, no history), so
    copying it per mutation is cheap."""
    global _PRISTINE
    if _PRISTINE is None:
        base = Path(tempfile.mkdtemp(prefix="mirror-pristine-"))
        atexit.register(shutil.rmtree, base, ignore_errors=True)
        dst = base / "repo"
        shutil.copytree(ROOT, dst, ignore=IGNORE)
        # autocrlf off: git add must not care about line endings here, and we
        # never read the index blobs — mirror_check reads the working tree.
        subprocess.run(["git", "-c", "core.autocrlf=false", "init", "-q"],
                       cwd=str(dst), check=True,
                       capture_output=True, text=True)
        subprocess.run(["git", "-c", "core.autocrlf=false", "add", "-A"],
                       cwd=str(dst), check=True,
                       capture_output=True, text=True)
        _PRISTINE = dst
    return _PRISTINE


@contextmanager
def repo_copy(git: bool = True):
    """Yield a writable copy of the working tree.

    git=True  (default): the copy carries a git index → mirror_check runs its
              real, tracked-file-resolving path.
    git=False: no .git in the copy → mirror_check hits its git-unavailable
              fallback. Use this ONLY to test that branch on purpose."""
    src = _pristine() if git else ROOT
    ignore = None if git else IGNORE      # pristine already excluded caches
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "repo"
        shutil.copytree(src, dst, ignore=ignore)
        yield dst


def run_mirror_check(repo: Path):
    """Return (returncode, stdout) for mirror_check run inside `repo`."""
    proc = subprocess.run(
        [sys.executable, str(repo / "tools" / "mirror_check.py")],
        cwd=str(repo), capture_output=True, text=True)
    return proc.returncode, proc.stdout
