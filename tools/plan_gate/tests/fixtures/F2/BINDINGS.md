# plan_gate test fixture workspace — NOT a real agent workspace.

Present because `compaction_inject.py` resolves the workspace ROOT by walking UP
for `BINDINGS.md` (`_resolve_workspace`, which tests each candidate directory with
`(cand / "BINDINGS.md").is_file()`). A directory that holds `plans/` but carries no
marker is deliberately NOT a workspace: the tool refuses it, prints NO WORKSPACE
ROOT, and reports that nothing was read. Without this file the fixture is a
workspace the tool correctly DECLINES, not a workspace under test
[[test-package-must-assert-its-own-boundary]].

Content is a comment only, on purpose. The resolver parses no fields — it calls
`.is_file()` and stops. Two functions in this repo DO parse fields out of a
BINDINGS.md: `tools/statevault/state.py`'s `x_protocol_version()` (wants a
`PROTOCOL vX.Y` row, raises without one) and `_bindings_side_names()` (wants
`SIDE_NAMES`, returns [] without one). Both open `os.path.join(WS, "BINDINGS.md")`
— the REAL workspace, named by `PA_WORKSPACE` or statevault's own hardcoded
fallback (the literal is deliberately not repeated here: this directory is graded
for machine-specific absolute paths by an unrelated lane's probe, and eleven new
copies of one would move that measurement for no reader's benefit).
Nothing under `tools/plan_gate/` imports statevault and no plan_gate test
redirects `PA_WORKSPACE`, so neither reader can reach this file. A `SIDE_NAMES` or
`PROTOCOL` row here would assert a binding this fixture does not have, read by
nobody. An honest marker beats a plausible fake.
