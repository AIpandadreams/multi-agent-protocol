#!/usr/bin/env python3
"""Workspace conformance suite [PROTOCOL v2.5 / v2.6].

A self-runnable, point-in-time readiness check for a stamped workspace.
Where the integrity CI protects the coordination *record over time*
(append-only, provenance, secrets — it needs git history), this validates
that a workspace is *structurally conformant* right now: the right files for
its profile exist, every binding slot is resolved, the PROXY_AUTH safety
guard is intact, and the auth-log chain is clean. Run it after stamping,
after filling BINDINGS, and any time you want to confirm a deployment is
sound before waking an agent in it.

Version handling is PIN-AWARE: the workspace's own `PROTOCOL_VERSION` must be
one of the SUPPORTED_VERSIONS (a version outside the set is a BLOCKER — the
required-file and stamp expectations are undefined for it), and every per-file
stamp (auth-logs, channel INDEX) is checked against that WORKSPACE'S pinned
version, not a hardcoded literal. This keeps a live v2.5 workspace green under a
v2.6 checkout of the suite, and vice-versa.

Run it from a protocol checkout (this file lives here, not inside a stamped
workspace) and point --workspace at the workspace you want to check:

  python tools/conformance_check.py --workspace path/to/ws           # check a ws
  python tools/conformance_check.py --workspace path/to/ws --strict  # unbound slots fail too
  python tools/conformance_check.py                                  # check cwd (only if cwd is itself a workspace)

Exit 0 = conformant (no BLOCKER; and no WARN under --strict); 1 = findings.
BLOCKER = structurally broken or unsafe (missing required file, wrong/unknown
profile, unsupported PROTOCOL_VERSION, weakened PROXY_AUTH guard, broken
auth-log chain). WARN = stamped but not yet fully bound, or cosmetic drift
(unfilled slot, a per-file stamp/header that doesn't match the workspace's
pinned version) — resolve before relying on the workspace, or gate with
--strict.
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

# Protocol versions this suite knows how to validate. A workspace pinned outside
# the set is a BLOCKER (its file/stamp expectations are undefined here); a
# workspace pinned inside it is checked against its OWN version, so both a live
# v2.5 and a fresh v2.6 workspace pass under one checkout of this tool.
SUPPORTED_VERSIONS = ("v2.5", "v2.6")
VERSION_RE = re.compile(r"v2\.\d+")


def pinned_version(slots):
    """The workspace's own PROTOCOL_VERSION token (e.g. 'v2.6'), or None."""
    if not slots:
        return None
    m = VERSION_RE.search(slots.get("PROTOCOL_VERSION", ""))
    return m.group(0) if m else None

# The six irreversible/outward super-classes that are NEVER PROXY_AUTH-listable
# or relayable, in every configuration. The PROXY_AUTH slot's guard clause must
# name all six verbatim — dropping one silently weakens the safety property.
SUPER_CLASSES = [
    "outward-facing/publish actions",
    "email SEND",
    "new-money/new-recipient financial actions",
    "destructive operations on another party's artifacts",
    "canonical-repo merges",
    # Full canonical sixth class — checking only "changes to PROXY_AUTH" would
    # pass a slot that dropped "/ gates / embargoes / the protocol".
    "changes to PROXY_AUTH / gates / embargoes / the protocol",
]

# Matches both documented placeholder forms: {{FILL}} and {{FILL: hint}}.
FILL_RE = re.compile(r"\{\{FILL(?::[^}]*)?\}\}")
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
            continue  # header ("| slot |") + divider ("|---|") rows can't
                      # match SLOT_RE's uppercase key class, so they're skipped
        slots[m.group(1).strip()] = m.group(2).strip()
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


def check_bindings(ws: Path, slots, roles, pinned, f: Findings):
    if slots is None:
        f.blocker("BINDINGS.md not found or unreadable")
        return

    ver = slots.get("PROTOCOL_VERSION", "")
    if pinned is None or pinned not in SUPPORTED_VERSIONS:
        f.blocker(f"PROTOCOL_VERSION is '{ver or 'absent'}', expected one of "
                  f"{{{', '.join(SUPPORTED_VERSIONS)}}}")

    profile = slots.get("PROFILE", "")
    if profile not in PROFILE_ROLES:
        # BLOCKER, not WARN: an unknown profile means the required-file set is
        # undefined, so a non-strict run could otherwise exit 0 having checked
        # nothing meaningful.
        f.blocker(f"PROFILE '{profile or 'absent'}' is not a known profile "
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
        if on and "never listable or relayable" not in pa:
            f.blocker("PROXY_AUTH is ON but the never-listable/relayable "
                      "guard clause is missing from the slot")


def check_auth_logs(ws: Path, roles, pinned, f: Findings):
    stamp = f"[PROTOCOL {pinned}]" if pinned else None
    for role in sorted(roles):
        p = ws / "memory" / role / "auth-log.md"
        if not p.is_file():
            continue  # missing-file already reported by structure check
        t = p.read_text(encoding="utf-8", errors="replace")
        if stamp and stamp not in t:
            f.warn(f"memory/{role}/auth-log.md missing {stamp} stamp")
        if "Append-only" not in t or "Single-writer" not in t:
            f.warn(f"memory/{role}/auth-log.md missing append-only/"
                   "single-writer header")

    # Fold in the mechanical chain validator. Run the TRUSTED copy that ships
    # beside this script in the protocol checkout — never the target
    # workspace's own tools/validate_auth_log.py, which for an "unsure"
    # workspace would be running unvetted code. Bounded by a timeout so a
    # pathological log can't hang the check.
    validator = Path(__file__).resolve().parent / "validate_auth_log.py"
    if not validator.is_file():
        f.warn("auth-log chain check skipped: trusted validate_auth_log.py "
               "not found beside conformance_check.py (run from a protocol "
               "checkout)")
        return
    try:
        proc = subprocess.run(
            [sys.executable, str(validator)], cwd=str(ws),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60)
    except subprocess.TimeoutExpired:
        f.blocker("auth-log chain validation timed out (>60s)")
        return
    if proc.returncode != 0:
        out = (proc.stdout or "").strip() or (proc.stderr or "").strip()
        f.blocker("auth-log chain validation failed:\n    " +
                  out.replace("\n", "\n    "))


def check_channel(ws: Path, pinned, f: Findings):
    p = ws / "channel" / "INDEX.md"
    if not p.is_file():
        return  # reported by structure check
    t = p.read_text(encoding="utf-8", errors="replace")
    stamp = f"[PROTOCOL {pinned}]" if pinned else None
    if stamp and stamp not in t:
        f.warn(f"channel/INDEX.md missing {stamp} stamp")
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
    pinned = pinned_version(slots)
    if not roles:
        f.blocker("no memory/<role>/ directories found — not a workspace?")

    check_structure(ws, roles, f)
    check_bindings(ws, slots, roles, pinned, f)
    check_auth_logs(ws, roles, pinned, f)
    check_channel(ws, pinned, f)

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
