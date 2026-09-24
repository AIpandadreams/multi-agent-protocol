"""Package marker for ``tools/`` — added by DW1 (under a fleet ruling).

⚠ **Why this file exists, and what it deliberately does NOT do.**

``tools/d5_write_path/`` ships a ``unittest`` battery whose mandated invocation
is, from the worktree root::

    python -m unittest discover -s tools/d5_write_path/tests -t .

``unittest``'s discovery requires the start directory to be importable from the
top-level directory, which makes ``tools`` a package. That is the whole reason
for this file.

It changes nothing for the existing surface: every script here is still run as
``python tools/<name>.py`` (a direct path run puts ``tools/`` itself on
``sys.path``, exactly as before), and this module executes **no code and
imports nothing** — an empty package marker cannot alter another module's
import resolution, its cwd assumptions, or its relative ``open()`` calls.

``tools/d5_model/`` deliberately has NO ``__init__.py`` and is imported flat by
putting its own directory on ``sys.path``; that arrangement is untouched —
``tools/d5_write_path/model_import.py`` is the single shim that performs it.
"""
