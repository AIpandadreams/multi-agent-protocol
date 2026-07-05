#!/usr/bin/env python3
"""Workspace conformance suite [PROTOCOL v2.5].

A self-runnable, point-in-time readiness check for a stamped workspace.
Where the integrity CI protects the coordination *record over time*
(append-only, provenance, secrets — it needs git history), this validates
that a workspace is *structurally conformant* right now: the right files for
its profile exist, every binding slot is resolved, the PROXY_AUTH safety
guard is intact, and the auth-log chain is clean. Run it after stamping,
after filling BINDINGS, and any time you want to confirm a deployment is
sound before waking an agent in it.

  python tools/conformance_check.py                 # check the current dir
  python tools/conformance_check.py --workspace ws  # check another workspace
  python tools/conformance_check.py --strict        # unbound slots also fail

Exit 0 = conformant (no BLOCKER; and no WARN under --strict); 1 = findings.
BLOCKER = structurally broken or unsafe. WARN = stamped but not yet fully
bound (normal right after a stamp; resolve before relying on the workspace).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# Roles a profile is expected to carry (used to make the required-file list
# profile-aware and to catch a memory/ tree that disagrees with the profile).
PROFILE_ROLES = {
    "2agent.local": {"owner", "builder"},
    "3agent.local": {"owner", "builder", "orchestrator"},
}

# The six irreversible/outward super-classes that are NEVER PROXY_AUTH-listable
# or relayable, in every configuration. The PROXY_AUTH slot's guard clause must
# name all six verbatim — dropping one silently weakens the safety property.
SUPER_CLASSES = [
    "outward-facing/publish actions",
    "email SEND",
    "new-money/new-recipient financial actions",
    "destructive operations on another party's artifacts",
    "canonical-repo merges",
    "changes to PROXY_AUTH",
]

FILL_RE = re.compile(r"\{\{FILL[:}]")
SLOT_RE = re.compile(r"^\|\s*([A-Z_/ ]+?)\s*\|\s*(.*?)\s*\|\s*$")


class Findings:
    def __init__(self):
        self.items = []  # (severity, message)

    def blocker(self, msg):
        self.items.append(("BLOCKER", msg))

    def warn(self, msg):
        self.items.append(("WARN", msg))

    def counts(self):
        b = sum(1 for s, _ in self.items if s == "BLOCKER")
        w = sum(1 for s, _ in self.items if s == "WARN")
        return b, w


def parse_bindings(ws: Path):
    """Return {SLOT: value} from BINDINGS.md's slot table (empty if absent)."""
    p = ws / "BINDINGS.md"
    if not p.is_file():
        return None
    slots = {}
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = SLOT_RE.match(line)
        if not m:
            continue
        key, val = m.group(1).strip(), m.group(2).strip()
        if key in ("slot", "---"):  # header / divider rows
            continue
        slots[key] = val
    return slots


def infer_roles(ws: Path):
    mem = ws / "memory"
    if not mem.is_dir():
        return set()
    return {d.name for d in mem.iterdir() if d.is_dir()}


def check_structure(ws: Path, roles, f: Findings):
    required = [
        "BINDINGS.md", "README.md", "MODELS.md",
        "channel/INDEX.md",
        "tools/validate_auth_log.py",
        ".github/workflows/integrity.yml",
        ".claude/settings.json",
    ]
    if "orchestrator" in roles:
        required += [
            "TASKQUEUE.md",
            "memory/orchestrator/session-registry.md",
            "memory/orchestrator/cost-ledger.md",
            "memory/orchestrator/dispatch-log.md",
        ]
    for role in sorted(roles):
        required += [
            f"memory/{role}/MEMORY.md",
            f"memory/{role}/auth-log.md",
            f"start/START_SESSION.{role}.md",
        ]
    for rel in required:
        if not (ws / rel).is_file():
            f.blocker(f"missing required file: {rel}")


def check_bindings(ws: Path, slots, roles, f: Findings):
    if slots is None:
        f.blocker("BINDINGS.md not found or unreadable")
        return

    ver = slots.get("PROTOCOL_VERSION", "")
    if "v2.5" not in ver:
        f.blocker(f"PROTOCOL_VERSION is '{ver or 'absent'}', expected v2.5")

    profile = slots.get("PROFILE", "")
    if profile not in PROFILE_ROLES:
        f.warn(f"PROFILE '{profile or 'absent'}' is not a known profile "
               f"({', '.join(PROFILE_ROLES)})")
    else:
        expected = PROFILE_ROLES[profile]
        if roles and roles != expected:
            f.blocker(
                f"profile {profile} expects roles {sorted(expected)} but "
                f"memory/ has {sorted(roles)}")

    # Unbound slots: any value still holding a {{FILL}} placeholder.
    for key, val in slots.items():
        if key in ("PROTOCOL_VERSION", "PROFILE"):
            continue
        if FILL_RE.search(val):
            f.warn(f"binding slot {key} still holds a {{{{FILL}}}} placeholder")

    # PROXY_AUTH is an orchestrator-relay concept: the slot exists only in
    # profiles that carry an orchestrator. Where it exists, its safety guard
    # must remain intact whether the lane is on or off.
    pa = slots.get("PROXY_AUTH", "")
    if "orchestrator" in roles and not pa:
        f.blocker("PROXY_AUTH slot is absent (required with an orchestrator)")
    elif pa:
        for phrase in SUPER_CLASSES:
            if phrase not in pa:
                f.blocker(
                    "PROXY_AUTH guard weakened: missing never-listable "
                    f"super-class '{phrase}'")
        on = not pa.lstrip().lower().startswith("off")
        guard = "never listable" in pa or "never listable or relayable" in pa
        if on and not guard:
            f.blocker("PROXY_AUTH is ON but the never-listable/relayable "
                      "guard clause is missing from the slot")


def check_auth_logs(ws: Path, roles, f: Findings):
    for role in sorted(roles):
        p = ws / "memory" / role / "auth-log.md"
        if not p.is_file():
            continue  # missing-file already reported by structure check
        t = p.read_text(encoding="utf-8", errors="replace")
        if "[PROTOCOL v2.5]" not in t:
            f.warn(f"memory/{role}/auth-log.md missing PROTOCOL v2.5 stamp")
        if "Append-only" not in t or "Single-writer" not in t:
            f.warn(f"memory/{role}/auth-log.md missing append-only/"
                   "single-writer header")

    # Fold in the mechanical chain validator if it is present.
    validator = ws / "tools" / "validate_auth_log.py"
    if validator.is_file():
        proc = subprocess.run(
            [sys.executable, str(validator)], cwd=str(ws),
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            out = (proc.stdout or "").strip() or (proc.stderr or "").strip()
            f.blocker(f"auth-log chain validation failed:\n    " +
                      out.replace("\n", "\n    "))


def check_channel(ws: Path, f: Findings):
    p = ws / "channel" / "INDEX.md"
    if not p.is_file():
        return  # reported by structure check
    t = p.read_text(encoding="utf-8", errors="replace")
    if "REVIEW-ROUND LEDGER" not in t:
        f.warn("channel/INDEX.md missing the REVIEW-ROUND LEDGER header")
    if "| round | side |" not in t:
        f.warn("channel/INDEX.md missing the ledger table header row")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=".",
                    help="workspace root to check (default: current dir)")
    ap.add_argument("--strict", action="store_true",
                    help="treat WARN (unbound slots etc.) as failing too")
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()
    if not ws.is_dir():
        print(f"conformance: {ws} is not a directory", file=sys.stderr)
        return 2

    f = Findings()
    slots = parse_bindings(ws)
    roles = infer_roles(ws)
    if not roles:
        f.blocker("no memory/<role>/ directories found — not a workspace?")

    check_structure(ws, roles, f)
    check_bindings(ws, slots, roles, f)
    check_auth_logs(ws, roles, f)
    check_channel(ws, f)

    blockers, warns = f.counts()
    if not f.items:
        print(f"CONFORMANCE: clean ({ws.name}, roles: {sorted(roles)})")
        return 0

    print(f"CONFORMANCE: {blockers} blocker(s), {warns} warning(s) [{ws.name}]")
    for sev, msg in f.items:
        print(f"  [{sev}] {msg}")
    fail = blockers > 0 or (args.strict and warns > 0)
    if not fail:
        print("(warnings only — workspace is structurally sound but not fully "
              "bound; use --strict to require every slot resolved)")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
