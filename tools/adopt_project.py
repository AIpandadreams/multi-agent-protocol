#!/usr/bin/env python3
"""Adopt an existing ad-hoc collaboration into a v2.5+ workspace [PROTOCOL v2.6].

Two teammates already working together (a shared inbox folder, a pair of
sessions, an informal channel) want the protocol's guarantees — numbered
append-only channel, per-role memory + auth-log, the reviewer ledger, the
integrity CI. This tool is deliberately THIN: it stamps a fresh dedicated
workspace (delegating entirely to new_project.py) and then prints the ADOPTION
CHECKLIST — the human/agent steps that a stamper cannot and must not do on its
own, because carrying live coordination state is a judgement call owned by the
agents, not the installer.

What it does NOT do: it does not read, move, reset, or reinterpret the old
collaboration's state. Counters, ops-gotchas, and project memory are carried
over BY THE ROLES as their own retrospective work, at a boundary the agents
agree to — never silently rewritten by an installer. The live-lane cutover
itself follows docs/MIGRATION.md.

Usage:
  python tools/adopt_project.py --name myproject --dest path/to/myproject-ws \\
      [--profile 3agent.local] [any new_project.py flag]

Unrecognized flags are passed straight through to new_project.py, so the full
stamp surface (--principal, --owner-side, --no-orchestrator, --wizard, ...) is
available. The stamper REFUSES a non-empty --dest; that refusal is surfaced
verbatim (adoption stamps a NEW workspace beside the old one — it never writes
into the existing collaboration's directory). Exit mirrors new_project.
"""
import argparse
import importlib.util
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "new_project", _HERE / "new_project.py")
np = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(np)


def adoption_checklist(bindings_summary: str) -> str:
    """The post-stamp adoption checklist as a plain string (pure, no I/O).

    Exposed as an importable function so a later onboarding wizard can embed it
    verbatim. `bindings_summary` is a short human description of the stamped
    workspace (e.g. its name + dest) folded into the header; it is not parsed.
    """
    return f"""ADOPTION CHECKLIST — {bindings_summary}

The workspace is stamped. Adopting the LIVE collaboration is the agents'
decision, relayed to them informationally — it is never imposed silently by
this installer. Before the first real round runs on the new workspace:

1. CARRY LIVE COUNTERS FROM THE OLD CHANNEL'S TAIL. Read the ACTUAL last
   entries of the old collaboration and seed each side's next-entry counter and
   latest-peer-seen from them. Never reset to 1 and never trust memory or
   bindings for the number — read the live tail. Reviewer round series carry
   per side from each side's own tail; they are never merged.

2. PRESERVE ROLE-AUTHORED STATE AS THE ROLE'S OWN WORK. Ops-gotchas, project
   context, and decision history move over as each role's retrospective entry
   in its own memory/<role>/ — authored by that role, not written by the
   installer. The installer records nothing on a role's behalf.

3. CUT ONLY AT AN AGREED BOUNDARY. Adopt at a clean seam — never mid-round or
   mid-wave. Both sides acknowledge the boundary before the old lane is frozen.

4. RUN THE LIVE-LANE CUTOVER PER docs/MIGRATION.md. The freeze/reconcile/
   redirect/verify sequence — including the stayed-lane rule for any lane that
   is NOT moving — is the migration pattern; adoption reuses it wholesale.

Nothing here is authorization: the agents decide whether and when to adopt.
"""


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--dest", required=True)
    # Everything else is new_project's business — parse only what we need to
    # build the checklist summary, and forward the full argv onward.
    args, _ = ap.parse_known_args()

    # Delegate stamping to new_project (it refuses a non-empty dest; we surface
    # that verbatim rather than second-guessing it).
    saved = sys.argv
    try:
        sys.argv = ["new_project.py"] + sys.argv[1:]
        rc = np.main()
    finally:
        sys.argv = saved
    if rc != 0:
        # new_project already printed the reason (e.g. "refusing: <dest> exists
        # and is not empty"). Adoption stamps a NEW workspace — do not proceed.
        return rc

    print()
    print(adoption_checklist(f"{args.name} at {args.dest}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
