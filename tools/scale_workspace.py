#!/usr/bin/env python3
"""Scale a stamped 2agent.local workspace up to 3agent.local [PROTOCOL v2.6].

Adds the orchestrator scaffold a 3-agent workspace needs that a 2-agent one
lacks — `memory/orchestrator/` (MEMORY.md, auth-log.md, dispatch-log.md,
session-registry.md, cost-ledger.md), `TASKQUEUE.md`, and
`start/START_SESSION.orchestrator.md` — WITHOUT touching anything already
there. The owner/builder contract is unchanged (docs/CONFIGURATIONS.md, the
2->3 upgrade path): this tool just materializes the extra files.

Single source of truth: the added files' BODIES come from new_project.py, not
from copies inlined here. This tool stamps a throwaway 3agent workspace with
new_project (same PROJECT name as the target, so the seeded ids/headers match)
and copies only the orchestrator-delta files out of it. Change a template in
new_project.py and this tool tracks it for free.

BINDINGS.md is PRINCIPAL-OWNED and never edited here. The orchestrator binding
rows (FLAVOR, PROXY_AUTH, TASKQUEUE, ...) and the PROFILE flip to 3agent.local
are the principal's to make by hand; this tool prints exactly the rows to add
(read straight from new_project.ORCH_SLOTS) and the reminder.

Usage:
  python tools/scale_workspace.py --workspace path/to/ws            # scale it
  python tools/scale_workspace.py --workspace path/to/ws --dry-run  # list only

Idempotent: a second run finds the scaffold present and does nothing. Exit
0 = scaled or already-scaled (no-op); 1 = target problem (not a 2-agent
workspace); 2 = usage error.
"""
import argparse
import importlib.util
import io
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

_HERE = Path(__file__).resolve().parent
# Single source: load new_project so the added files' bodies (and the printed
# BINDINGS rows) come from its templates, never a copy pasted here.
_spec = importlib.util.spec_from_file_location(
    "new_project", _HERE / "new_project.py")
np = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(np)

# The exact delta between a 2agent and a 3agent stamp — the orchestrator
# scaffold. Order is create-friendly (dirs before their files fall out of the
# path).
ORCH_FILES = [
    "memory/orchestrator/MEMORY.md",
    "memory/orchestrator/auth-log.md",
    "memory/orchestrator/dispatch-log.md",
    "memory/orchestrator/session-registry.md",
    "memory/orchestrator/cost-ledger.md",
    "TASKQUEUE.md",
    "start/START_SESSION.orchestrator.md",
]


def read_slot(bindings_text: str, slot: str):
    """Return the value of `| SLOT | value |` from a BINDINGS table, or None."""
    for line in bindings_text.splitlines():
        cells = [c.strip() for c in line.split("|")]
        # a well-formed row splits to ['', 'SLOT', 'value', '']
        if len(cells) >= 4 and cells[1] == slot:
            return cells[2]
    return None


def stamp_temp_orchestrator(name: str):
    """Stamp a throwaway 3agent workspace and return (dest, tmp_root).

    Caller removes tmp_root. new_project.main reads sys.argv, so we set it;
    its stdout is swallowed (this tool prints its own summary)."""
    tmp = Path(tempfile.mkdtemp(prefix="scale_ws_"))
    dest = tmp / "stamp"
    saved = sys.argv
    try:
        sys.argv = ["new_project.py", "--name", name, "--dest", str(dest),
                    "--profile", "3agent.local"]
        with redirect_stdout(io.StringIO()):
            rc = np.main()
    finally:
        sys.argv = saved
    if rc != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"new_project stamp failed (exit {rc})")
    return dest, tmp


def validate_target(ws: Path):
    """Return (project_name, error). error is None when ws is a scalable
    2-agent workspace."""
    if not ws.is_dir():
        return None, f"{ws} is not a directory"
    bindings = ws / "BINDINGS.md"
    if not bindings.is_file():
        return None, f"{ws} has no BINDINGS.md — not a workspace"
    for role in ("owner", "builder"):
        if not (ws / "memory" / role).is_dir():
            return None, (f"{ws} is missing memory/{role}/ — not a 2-agent "
                          "workspace (nothing to scale)")
    text = bindings.read_text(encoding="utf-8", errors="replace")
    name = read_slot(text, "PROJECT")
    if not name:
        return None, f"{ws}/BINDINGS.md has no PROJECT slot"
    return name, None


def scale(ws: Path, dry_run: bool):
    """Create the missing orchestrator files. Returns (created, skipped)."""
    missing = [rel for rel in ORCH_FILES if not (ws / rel).is_file()]
    if not missing:
        return [], list(ORCH_FILES)
    if dry_run:
        return missing, [r for r in ORCH_FILES if r not in missing]

    name = read_slot((ws / "BINDINGS.md").read_text(encoding="utf-8",
                                                    errors="replace"),
                     "PROJECT")
    src, tmp = stamp_temp_orchestrator(name)
    try:
        for rel in missing:
            dst = ws / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src / rel, dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return missing, [r for r in ORCH_FILES if r not in missing]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", required=True,
                    help="the 2agent.local workspace to scale up")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be created and exit; create nothing")
    args = ap.parse_args()

    ws = Path(args.workspace)
    name, err = validate_target(ws)
    if err:
        print(f"scale_workspace: {err}", file=sys.stderr)
        return 1

    created, present = scale(ws, args.dry_run)

    if not created:
        print(f"scale_workspace: {ws.name} already has the orchestrator "
              "scaffold — nothing to do (idempotent no-op).")
        return 0

    verb = "would create" if args.dry_run else "created"
    print(f"scale_workspace: {verb} {len(created)} orchestrator file(s) in "
          f"{ws.name}:")
    for rel in created:
        print(f"  {verb}: {rel}")
    if present:
        for rel in present:
            print(f"  (already present: {rel})")

    if args.dry_run:
        print("\n(dry run — nothing was written)")
        return 0

    # BINDINGS.md is the principal's. Print the rows to add by hand rather than
    # editing it — straight from new_project's single-source ORCH_SLOTS.
    print("\nNEXT (principal, by hand in BINDINGS.md — not done automatically):")
    print("  1. Flip the PROFILE row to: | PROFILE | 3agent.local |")
    print("  2. Add these orchestrator binding rows (resolve each {{FILL}}):\n")
    for line in np.ORCH_SLOTS.rstrip("\n").splitlines():
        print(f"     {line}")
    print("\n  3. Re-run conformance (--strict once every slot is resolved):")
    print(f"     python tools/conformance_check.py --workspace {ws} --strict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
