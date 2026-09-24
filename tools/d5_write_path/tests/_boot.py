"""Put the REPO ROOT on ``sys.path`` so ``tools.d5_write_path`` imports.

``tools/`` carries no ``__init__.py``, so it resolves as a PEP-420 namespace
package and ``tools.d5_write_path`` (a regular package) imports through it —
but only if the repo root is on the path. ``unittest discover -t .`` supplies
that when run from the worktree root; this module supplies it as well, so a
test file run directly still resolves. No ``importlib`` games, one insertion,
idempotent.
"""

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
