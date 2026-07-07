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
    "2agent.git-sync": {"owner", "builder"},
    "3agent.git-sync": {"owner", "builder", "orchestrator"},
}

# Transports the TRANSPORT slot may bind. The `.git-sync` / `.local` profile
# suffix implies which one; a stamped value that disagrees is a BLOCKER.
KNOWN_TRANSPORTS = ("local-fs", "git-sync")
# A CHANNEL/MEMORY value that carries an absolute path (drive-letter, POSIX
# root, or UNC) rather than a repo-relative one — a host-profile leak under
# git-sync, where both must resolve inside the synchronized workspace repo.
# The drive-letter alternative is guarded by a negative lookbehind so it does
# NOT fire on the `s:/` inside a URL scheme (`https://…`); a real drive path
# (`C:\ws`, at line start or after a space/paren) has no alphanumeric before
# the letter. The POSIX alternative requires the leading `/` to sit at string
# start or after whitespace, so URL path slashes (never whitespace-preceded)
# don't match either.
ABS_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|(?:^|\s)/[^\s/]|\\\\[^\s\\]")

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
# A {{DEFERRED}} marker is a slot the operator DELIBERATELY postponed in the
# wizard — distinct from an untouched {{FILL}}. It is still unresolved (a WARN),
# but the message says so, and --strict still catches it.
DEFERRED_RE = re.compile(r"\{\{DEFERRED(?::[^}]*)?\}\}")
SLOT_RE = re.compile(r"^\|\s*([A-Z_/ ]+?)\s*\|\s*(.*?)\s*\|\s*$")
# ROLE_LOCK declaration inside a memory index — the canonical role a memory
# directory locks its sessions to (P-1: one agent per role per workspace).
ROLE_LOCK_RE = re.compile(r"ROLE_LOCK[^\n]*?\b(OWNER|BUILDER|ORCHESTRATOR)\b",
                          re.IGNORECASE)

# SIDE_NAMES are positional against this canonical order; each role's DEFAULT
# side name is what a plain stamp uses (owner/builder keep the canonical name,
# the orchestrator's conventional short name is `orch`). A side whose name
# differs from its default is a rename that should carry a ROLE_ALIASES entry.
CANONICAL_ROLES = ["owner", "builder", "orchestrator"]
DEFAULT_SIDE = {"owner": "owner", "builder": "builder", "orchestrator": "orch"}
# Filename-grammar charset for a side name — underscore is FORBIDDEN because it
# is the `<from>_to_<to>_<date>` channel-filename separator.
SIDE_CHARSET_RE = re.compile(r"^[A-Za-z0-9-]+$")
# /wake's legacy built-in aliases (kept so pre-2.6 workspaces still resolve).
# A renamed side covered by one of these resolves without a ROLE_ALIASES row.
LEGACY_ALIASES = {"engine": "owner", "helper": "builder", "orch": "orchestrator"}
# ROLE_ALIASES entries accept either arrow form: `display→role` or `display->role`.
ALIAS_SEP_RE = re.compile(r"\s*(?:→|->)\s*")


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

    # Unbound slots: an untouched {{FILL}}, or a {{DEFERRED}} the operator
    # deliberately postponed. Both are unresolved (WARN; --strict fails on
    # either), but the message distinguishes "nobody has looked at this" from
    # "postponed on purpose".
    for key, val in slots.items():
        if key in ("PROTOCOL_VERSION", "PROFILE"):
            continue
        if DEFERRED_RE.search(val):
            f.warn(f"binding slot {key} is {{{{DEFERRED}}}} (deliberately "
                   "postponed in the wizard) — resolve before relying on it")
        elif FILL_RE.search(val):
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


# A channel DIRECTION entry's name follows `<from>_to_<to>_<date>.md`
# (channel-core). The lint is deliberately LENIENT and WARN-only, and only
# grades files that are clearly MEANT to be direction entries — those carrying
# the `_to_` infix. Review-lane artifacts (review_request_*, *_verdict_*) and
# other channel files have their own grammar and are left alone, so the lint
# catches a malformed direction filename (a typo) without flooding a live
# channel that legitimately holds many file classes.
CHANNEL_ENTRY_RE = re.compile(r"^[A-Za-z0-9-]+_to_[A-Za-z0-9-]+_.+\.md$")


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


def check_channel_entry_format(ws: Path, f: Findings):
    """Smoke-lint channel entry filenames against the direction grammar.

    Only entry files are graded — INDEX.md (the ledger) and dotfiles are
    exempt. WARN-only by design; a fresh stamp has no entry files, so this is
    silent until the first real entry lands.
    """
    chan = ws / "channel"
    if not chan.is_dir():
        return
    for p in sorted(chan.glob("*.md")):
        if p.name == "INDEX.md" or "_to_" not in p.name:
            continue  # INDEX + non-direction files (review lane, etc.) exempt
        if not CHANNEL_ENTRY_RE.match(p.name):
            f.warn(f"channel/{p.name} looks like a direction entry but doesn't "
                   "match `<from>_to_<to>_<date>.md` (channel-core) — check for "
                   "a typo")


def _report_uncovered(missing, row_state, f: Findings):
    """Report renamed sides with no explicit ROLE_ALIASES entry.

    Coverage follows wake.md's resolution order. Three classes:
    - a legacy built-in maps the name to the SAME role → still resolves
      (soft WARN: make it explicit);
    - a legacy built-in maps it to a DIFFERENT role → /wake would wake the
      WRONG role (BLOCKER: an explicit entry overrides the built-in);
    - no built-in at all → the name is unresolvable (WARN).
    `missing` maps canonical role → uncovered display name; `row_state`
    describes why coverage is absent (no row at all, or row omits them).
    """
    if not missing:
        return
    for role, name in sorted(missing.items()):
        other = LEGACY_ALIASES.get(name)
        if other is not None and other != role:
            f.blocker(f"renamed side '{name}' (the {role} side) is /wake's "
                      f"legacy built-in alias for the {other} role and has no "
                      f"overriding ROLE_ALIASES entry — /wake {name} would "
                      f"wake the WRONG role; add '{name}→{role}' (an explicit "
                      "workspace entry overrides the built-in)")
    unresolved = sorted(n for r, n in missing.items()
                        if n not in LEGACY_ALIASES)
    legacy_ok = sorted(n for r, n in missing.items()
                       if LEGACY_ALIASES.get(n) == r)
    if unresolved:
        f.warn(f"renamed side(s) {unresolved} — {row_state} — /wake <name> "
               "won't resolve until you add an entry")
    if legacy_ok:
        f.warn(f"renamed side(s) {legacy_ok} rely on /wake's legacy built-in "
               f"aliases ({row_state}) — add explicit ROLE_ALIASES entries "
               "to make the mapping explicit")


def check_side_names(slots, roles, f: Findings):
    """Validate SIDE_NAMES (and any ROLE_ALIASES row) for a workspace.

    SIDE_NAMES are positional: split on ' / ', they map in order onto the
    profile's roles taken in canonical order (owner, builder, orchestrator).
    Each name must be filename-grammar-safe ([A-Za-z0-9-]; underscore is a
    BLOCKER — it is the channel-filename separator), unique, and must not be
    the canonical name of a DIFFERENT profile role. A ROLE_ALIASES row, when
    present, must map each display name back to the canonical role its
    SIDE_NAMES position implies. Aliases affect addressing/display only.
    """
    if slots is None:
        return
    ordered = [r for r in CANONICAL_ROLES if r in roles]
    raw = slots.get("SIDE_NAMES", "")
    # A SIDE_NAMES value may carry a trailing parenthetical note (a
    # "(formerly: ..., until <date>)" history marker, or a channel-grammar
    # reminder). Strip parentheticals BEFORE splitting so the note's spaces /
    # slashes / underscored filename examples never look like side names.
    stripped = re.sub(r"\([^)]*\)", "", raw)
    names = [n.strip() for n in stripped.split(" / ") if n.strip()]

    if not names:
        f.warn("SIDE_NAMES slot is empty or unparseable")
        return

    if len(names) != len(ordered):
        f.warn(f"SIDE_NAMES has {len(names)} name(s) but the profile has "
               f"{len(ordered)} role(s) {ordered}")

    seen = {}
    for i, name in enumerate(names):
        if not SIDE_CHARSET_RE.match(name):
            if "_" in name:
                f.blocker(f"SIDE_NAMES entry '{name}' contains an underscore — "
                          "underscore breaks the <from>_to_<to>_<date> channel "
                          "filename grammar (allowed charset: [A-Za-z0-9-])")
            else:
                f.blocker(f"SIDE_NAMES entry '{name}' has characters outside "
                          "[A-Za-z0-9-] (breaks the channel filename grammar)")
        if name in seen:
            f.blocker(f"SIDE_NAMES entry '{name}' is duplicated (positions "
                      f"{seen[name] + 1} and {i + 1}) — side names must be unique")
        else:
            seen[name] = i
        # A side named after a DIFFERENT role's canonical name is a trap —
        # checked against ALL canonical roles, not just this profile's: /wake
        # resolves canonical names FIRST (tier 1), before any workspace alias,
        # so `/wake orchestrator` in a 2-agent workspace whose OWNER side is
        # named `orchestrator` would target the absent orchestrator role.
        if i < len(ordered):
            my_role = ordered[i]
            for other in CANONICAL_ROLES:
                if other != my_role and name == other:
                    f.blocker(f"SIDE_NAMES entry '{name}' (the {my_role} side) "
                              f"is the canonical name of the {other} role — "
                              "/wake resolves canonical names before any "
                              "alias, so a side may not be named after "
                              "another role")

    # Positions carrying a non-default display name (differ from the role's
    # default side name) — the same predicate new_project uses to decide
    # whether to stamp a ROLE_ALIASES row.
    renamed = {ordered[i]: names[i]
               for i in range(min(len(names), len(ordered)))
               if names[i] != DEFAULT_SIDE.get(ordered[i])}

    alias_raw = slots.get("ROLE_ALIASES", "")
    has_alias_row = "ROLE_ALIASES" in slots and alias_raw != ""

    if not has_alias_row:
        _report_uncovered(renamed, "no ROLE_ALIASES row is present", f)
        return

    # Validate the ROLE_ALIASES row against the SIDE_NAMES positions.
    display_to_role = {names[i]: ordered[i]
                       for i in range(min(len(names), len(ordered)))}
    seen_display = set()
    for part in alias_raw.split(","):
        part = part.strip()
        if not part:
            continue
        bits = ALIAS_SEP_RE.split(part, maxsplit=1)
        if len(bits) != 2 or not bits[0].strip() or not bits[1].strip():
            f.blocker(f"ROLE_ALIASES entry '{part}' is not '<display>→<role>'")
            continue
        display, target = bits[0].strip(), bits[1].strip()
        if display in seen_display:
            f.blocker(f"ROLE_ALIASES display name '{display}' is listed twice")
        seen_display.add(display)
        if target not in ordered:
            f.blocker(f"ROLE_ALIASES target '{target}' is not a canonical role "
                      f"in this profile ({ordered})")
            continue
        if display not in display_to_role:
            f.blocker(f"ROLE_ALIASES display '{display}' is not one of the "
                      "bound SIDE_NAMES")
            continue
        implied = display_to_role[display]
        if implied != target:
            f.blocker(f"ROLE_ALIASES maps '{display}'→{target} but SIDE_NAMES "
                      f"places '{display}' at the {implied} position")

    # Completeness: a row that exists but omits a renamed side is as silent a
    # failure as no row at all — every renamed side must still resolve.
    missing = {r: n for r, n in renamed.items() if n not in seen_display}
    _report_uncovered(missing, "the ROLE_ALIASES row has no entry for them", f)


def check_transport(slots, f: Findings):
    """Validate the TRANSPORT binding (v2.6) against the profile + paths.

    The slot is OPTIONAL and pin-aware by omission: a workspace with no
    TRANSPORT row is never flagged here — a v2.5 workspace predates the slot,
    and a v2.6 workspace that simply hasn't adopted it defaults to local-fs
    semantics. The check only acts on a PRESENT value:

    - an unknown value is a BLOCKER (its verb bindings are undefined);
    - a value that disagrees with the profile's `.git-sync` / `.local` suffix
      is a BLOCKER (the profile and the transport must name the same thing);
    - under git-sync, an absolute path in CHANNEL or MEMORY is a WARN — those
      must be repo-relative so they resolve inside the synchronized workspace
      on every host (an absolute path is a leaked host profile).
    """
    if slots is None:
        return
    transport = slots.get("TRANSPORT", "").strip()
    if not transport:
        return  # absent slot never flags (pin-aware by omission)

    if transport not in KNOWN_TRANSPORTS:
        f.blocker(f"TRANSPORT '{transport}' is unknown — expected one of "
                  f"{{{', '.join(KNOWN_TRANSPORTS)}}}")
        return

    profile = slots.get("PROFILE", "")
    if profile in PROFILE_ROLES:
        expected = "git-sync" if profile.endswith("git-sync") else "local-fs"
        if transport != expected:
            f.blocker(f"TRANSPORT '{transport}' disagrees with PROFILE "
                      f"'{profile}' (which binds {expected})")

    if transport == "git-sync":
        for key in ("CHANNEL", "MEMORY"):
            val = slots.get(key, "")
            if ABS_PATH_RE.search(val):
                f.warn(f"{key} holds an absolute path under git-sync "
                       f"('{val}') — CHANNEL/MEMORY must be repo-relative so "
                       "they resolve inside the synchronized workspace on "
                       "every host (looks like a leaked host profile)")


def check_one_agent_per_role(ws: Path, roles, f: Findings):
    """P-1: exactly one agent per role per workspace — fail CLOSED.

    Each memory/<role>/ index locks its sessions to a canonical role via a
    ROLE_LOCK line. This verifies that mapping is 1:1: a role dir must lock to
    its OWN role, and no two dirs may claim the same role (a collision would let
    two agents answer as the same authority). Unparseable ROLE_LOCK on a role
    that should carry one is itself a BLOCKER — the invariant can't be
    confirmed, so it fails closed. The design is to scale HORIZONTALLY (separate
    workspaces), never to run two agents of one role in one workspace.
    """
    declared = {}  # canonical role -> [dirs that lock to it]
    for role in sorted(roles):
        p = ws / "memory" / role / "MEMORY.md"
        if not p.is_file():
            continue  # missing-file BLOCKER already raised by check_structure
        m = ROLE_LOCK_RE.search(p.read_text(encoding="utf-8", errors="replace"))
        if not m:
            f.blocker(f"memory/{role}/MEMORY.md has no parseable ROLE_LOCK line "
                      "— one-agent-per-role can't be confirmed (fails closed)")
            continue
        got = m.group(1).lower()
        declared.setdefault(got, []).append(role)
        if got != role:
            f.blocker(f"memory/{role}/MEMORY.md ROLE_LOCK names '{got}', not its "
                      f"directory role '{role}' — a role dir must lock to its "
                      "own role")
    for canon, dirs in sorted(declared.items()):
        if len(dirs) > 1:
            f.blocker(f"ROLE_LOCK collision: role '{canon}' is claimed by "
                      f"multiple memory dirs {sorted(dirs)} — exactly one agent "
                      "per role per workspace (P-1); scale horizontally with "
                      "separate workspaces, never two agents of one role here")


def _self_check_banner():
    """Print the SELF-CHECK MODE banner when this file is the STAMPED in-workspace
    copy (C2): its parent-of-tools directory carries a BINDINGS.md, whereas the
    protocol checkout's copy sits beside no workspace BINDINGS. The in-workspace
    copy is workspace-OWNED code, so it is a hygiene self-check, never a trust
    gate — for a trust decision, run the protocol checkout's copy.

    Detection keys on THIS FILE's own provenance (a workspace BINDINGS.md beside
    its tools/ dir), NOT on whether the --workspace target happens to contain
    this file. That is deliberate: the banner is about the code you are running
    being workspace-owned, so it correctly fires whenever a stamped copy runs —
    including when pointed at some OTHER workspace, which is exactly when the
    "don't trust workspace-owned code" reminder matters most."""
    own_ws = Path(__file__).resolve().parent.parent
    if (own_ws / "BINDINGS.md").is_file():
        print("SELF-CHECK MODE — this is the workspace's OWN stamped copy of "
              "the conformance suite (workspace-owned code). It is a hygiene "
              "self-check, not a trust gate; for a trust decision run the "
              "protocol checkout's copy against this workspace.\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default=".",
                    help="workspace root to check (default: current dir)")
    ap.add_argument("--strict", action="store_true",
                    help="treat WARN (unbound slots etc.) as failing too")
    args = ap.parse_args()

    _self_check_banner()

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
    check_side_names(slots, roles, f)
    check_transport(slots, f)
    check_one_agent_per_role(ws, roles, f)
    check_auth_logs(ws, roles, pinned, f)
    check_channel(ws, pinned, f)
    check_channel_entry_format(ws, f)

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
