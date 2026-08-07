#!/usr/bin/env python3
"""Workspace conformance suite [PROTOCOL v2.5 / v2.6 / v2.7 / v2.8 / v2.9 / v3.0 / v3.1].

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
version, not a hardcoded literal. This keeps v2.5 through v3.0 workspaces green
under a v3.1 checkout of the suite, while fresh v3.1 workspaces are accepted by
that same checkout. (An OLDER checkout does not learn newer pins — a
v3.1-pinned workspace under a v2.9-era checkout is a BLOCKER by design.)

Run it from a protocol checkout for a TRUST decision and point --workspace
at the workspace you want to check. (Stamping also drops a copy of this file
INTO each workspace — that copy runs in SELF-CHECK MODE as a hygiene gate,
and its absence from a workspace is itself a BLOCKER-class finding, never a
skipped gate.)

  python tools/conformance_check.py --workspace path/to/ws           # check a ws
  python tools/conformance_check.py --workspace path/to/ws --strict  # unbound slots fail too
  python tools/conformance_check.py                                  # check cwd (only if cwd is itself a workspace)

Exit 0 = conformant (no BLOCKER; and no WARN under --strict); 1 = findings.
BLOCKER = structurally broken or unsafe (missing required file, wrong/unknown
profile, unsupported PROTOCOL_VERSION, weakened PROXY_AUTH guard, broken
auth-log chain). WARN = stamped but not yet fully bound, or cosmetic drift
(unfilled slot; a per-file record banner whose stamp is not a supported
version at-or-below the workspace's pin — append-only records legitimately
keep the stamp of the version they were CREATED under, so an OLDER supported
stamp is green, only a newer/unsupported/missing banner stamp is a finding) —
resolve before relying on the workspace, or gate with --strict.
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
# workspace pinned inside it is checked against its OWN version, so a live v2.5
# through v3.0 workspace and a fresh v3.1 one all pass under one checkout of this
# tool. Membership in THIS tuple is the acceptance gate; keep it ascending with
# the newest version LAST (reconcile_vendored.py reads supports-through from the
# last element positionally).
SUPPORTED_VERSIONS = ("v2.5", "v2.6", "v2.7", "v2.8", "v2.9", "v3.0", "v3.1")
# Any-major version-token extractor (widened from v2-only for the v3.0 cut).
# Acceptance is decided by SUPPORTED_VERSIONS membership above, never by this
# regex, so widening it admits nothing — it only lets a non-v2 pin be READ so
# the membership check can rule on it (fail-closed on unknown majors: a v4.0
# pin is extracted, then BLOCKERs as not in SUPPORTED_VERSIONS).
VERSION_RE = re.compile(r"v\d+\.\d+")


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
# ── THE ROLE VOCABULARY ──────────────────────────────────────────────────────
# One table. Every role-name enumeration in this file DERIVES from it, so adding
# a role is one row here and nothing anywhere else. It was four independent
# literals — an alternation, an ordered list, a default-side map, and an alias
# map's value set — each of which had to be edited in step and none of which
# said so. SIDE_NAMES are positional against this order, so rows are APPENDED,
# never reordered: position is meaning.
#
# Each role's DEFAULT side name is what a plain stamp uses; most keep the
# canonical name, and the orchestrator's conventional short name is `orch`. A
# side whose name differs from its default is a rename that should carry a
# ROLE_ALIASES entry.
ROLE_VOCABULARY = (
    # canonical role   default side name
    ("owner",          "owner"),
    ("builder",        "builder"),
    ("orchestrator",   "orch"),
)
CANONICAL_ROLES = [role for role, _side in ROLE_VOCABULARY]
DEFAULT_SIDE = {role: side for role, side in ROLE_VOCABULARY}
# ── IDENTITIES THAT ARE NOT SEATS ────────────────────────────────────────────
# `creator` began as a fourth row above, and putting it there was wrong in a way
# only a run could show: the seat-trap in check_side_names iterates ALL canonical
# roles, so the row made `creator` illegal as a side name in every workspace. The
# trap's own stated grounds are that "/wake resolves canonical names first" — and
# `wake.md` resolves exactly `owner | builder | orchestrator` at tier 1. There is
# no /wake collision to protect against, so the block was true by mechanism and
# false by justification. BINDINGS.md:13 (auth-0359) says the same thing from the
# other side: creator is "NOT a SIDE_NAME — a THIRD identity category".
#
# So the file carries TWO vocabularies, and wake.md already implies both: tier-1
# resolution and SIDE_NAMES positions are about SEATS, while the role identity
# artifacts (ROLE_LOCK, `memory/<role>/`, `start/START_SESSION.<role>.md`) are
# about IDENTITIES. A lock line may name any identity; only a seat gets a
# positional slot.
NON_SEAT_IDENTITIES = ("creator",)
LOCK_VOCABULARY = tuple(CANONICAL_ROLES) + NON_SEAT_IDENTITIES
assert not set(CANONICAL_ROLES) & set(NON_SEAT_IDENTITIES), (
    "an identity may be a seat or a non-seat, never both: %r"
    % sorted(set(CANONICAL_ROLES) & set(NON_SEAT_IDENTITIES)))
# Filename-grammar charset for a side name — underscore is FORBIDDEN because it
# is the `<from>_to_<to>_<date>` channel-filename separator.
SIDE_CHARSET_RE = re.compile(r"^[A-Za-z0-9-]+$")
# /wake's legacy built-in aliases (kept so pre-2.6 workspaces still resolve).
# A renamed side covered by one of these resolves without a ROLE_ALIASES row.
LEGACY_ALIASES = {"engine": "owner", "helper": "builder", "orch": "orchestrator"}
# This map states a DIFFERENT fact from the vocabulary — which historical display
# names /wake still resolves — so it stays its own literal rather than being
# derived. What it may not do is name a role the vocabulary does not have: that
# would resurrect the split this table exists to end, quietly, at whichever call
# site looked it up first. Checked at import, so the file cannot load in that
# state.
assert set(LEGACY_ALIASES.values()) <= set(CANONICAL_ROLES), (
    "LEGACY_ALIASES targets %r, which ROLE_VOCABULARY does not define"
    % sorted(set(LEGACY_ALIASES.values()) - set(CANONICAL_ROLES)))
# ROLE_ALIASES entries accept either arrow form: `display→role` or `display->role`.
ALIAS_SEP_RE = re.compile(r"\s*(?:→|->)\s*")
# NON_ROLE_DIRS values are comma- or whitespace-separated.
NON_ROLE_SPLIT_RE = re.compile(r"[,\s]+")

# ── READING A ROLE_LOCK LINE ─────────────────────────────────────────────────
# The line this reads is prose, not a field. Every workspace in the corpus, and
# `new_project.py`'s own generator, writes a SENTENCE:
#
#     ROLE_LOCK: this workspace's OWNER sessions only.
#     ROLE_LOCK: this workspace's sessions are the ORCHESTRATOR only. <more>
#     ROLE_LOCK: this workspace's BUILDER sessions only (a note). <more>
#
# so there is no value to read, and a grammar pinned to any one of those
# sentences rejects the others. What this must NOT do is what it used to: scan
# the line for the first role-shaped token anywhere on it. That succeeded on
# `— this seat is NOT the OWNER`, on `none (see the ORCHESTRATOR for authority)`,
# on `CO-OWNER`, and on `CREATOR, deputising for the OWNER` — four confident,
# specific, WRONG answers. A wrong role is worse than no role: it names
# something and invites the reader to go and fix the wrong thing.
#
# So: read the first sentence of the declaration, and accept it only when it
# names exactly one role and does not negate. Everything else is unparseable,
# which the caller already treats as a fail-closed BLOCKER.
# ⛔ THE COLON IS REQUIRED, AND IT IS THE WHOLE SELECTOR. Making it optional
# matched WRAPPED PROSE: a memory index discussing role locks has sentences whose
# line break happens to put `ROLE_LOCK` at column 0 — `ROLE_LOCK vs the shipped
# conformance regex's ...` — and two live orchestrator indexes carry exactly that.
# So there IS a field marker here even though there is no bare field value: the
# colon separates the declaration from everything that merely mentions it.
_ROLE_LOCK_LINE_RE = re.compile(r"^[^\S\n]*ROLE_LOCK[^\S\n]*:(.*)$", re.M)
_PARENTHETICAL_RE = re.compile(r"\([^)]*\)")
# A whole word, where `-` counts as part of the word: `CO-OWNER` is not `OWNER`.
_WORDISH = r"(?<![\w-])%s(?![\w-])"
_NEGATION_RE = re.compile(r"(?<![\w-])(?:not|never|no|none|except|excluding)"
                          r"(?![\w-])|n't", re.IGNORECASE)


def role_lock_role(text):
    """The canonical role a ROLE_LOCK declaration names, or None if ambiguous.

    None means "this text does not unambiguously name one role" — it does NOT
    mean the file is unlocked, and the caller must treat it as a failure to
    confirm rather than as an absence of a lock.

    Ambiguity is deliberate policy here, and it applies at BOTH grains. A
    declaration naming two roles is refused rather than resolved by position,
    because there is no reading of `CREATOR, deputising for the OWNER` that this
    function is entitled to pick. A FILE carrying two declaration lines is
    refused for the same reason: taking the first would let a prose line that
    happens to begin `ROLE_LOCK ...` outrank the real declaration below it, and
    if that prose named another role the answer would be confidently wrong —
    which is the failure this reader exists to end, one grain up.
    """
    declarations = _ROLE_LOCK_LINE_RE.findall(text or "")
    if len(declarations) != 1:
        return None
    # Parentheticals are stripped BEFORE the sentence split, so a note's own
    # punctuation cannot end the sentence early and a role mentioned inside an
    # aside is not read as the declaration. `check_side_names` strips them from
    # SIDE_NAMES for the same reason.
    decl = _PARENTHETICAL_RE.sub(" ", declarations[0])
    decl = decl.split(".")[0]
    if _NEGATION_RE.search(decl):
        return None
    # LOCK_VOCABULARY, not CANONICAL_ROLES: a lock declares an IDENTITY, and the
    # non-seat identities are exactly the ones a positional check must not see.
    found = {role for role in LOCK_VOCABULARY
             if re.search(_WORDISH % role, decl, re.IGNORECASE)}
    return found.pop() if len(found) == 1 else None


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


def declared_non_role_dirs(slots):
    """The names written in the OPTIONAL NON_ROLE_DIRS slot, verbatim and unfiltered.

    This is the DECLARATION, not the exclusion that gets applied — the two are deliberately
    separate functions so that refusing a declared name is a property of the code rather than
    a promise in a message. `effective_exclusions` decides what is actually applied.

    An absent row, an empty cell, or an unresolved placeholder all mean "nothing declared" —
    the placeholder forms are recognized with the file's own FILL/DEFERRED matchers rather than
    by literal comparison, because both are documented as accepting a hint (`{{FILL: hint}}`),
    and a literal match would parse a hinted placeholder as a list of directory names. An
    unresolved slot still earns its unbound-slot WARN from `check_bindings`; it just does not
    exclude anything. No other sentinel value is special: a cell reading `none` declares a
    directory named `none`, which — absent such a directory — surfaces as a stale exclusion
    rather than being silently swallowed.

    Values are comma- or whitespace-separated.
    """
    if not slots:
        return set()
    raw = (slots.get("NON_ROLE_DIRS") or "").strip()
    if not raw or FILL_RE.search(raw) or DEFERRED_RE.search(raw):
        return set()
    return {n for n in NON_ROLE_SPLIT_RE.split(raw) if n}


def effective_exclusions(declared):
    """The exclusions actually APPLIED to role inference: declared names MINUS every name in
    LOCK_VOCABULARY.

    LOCK_VOCABULARY, not CANONICAL_ROLES: the subtraction is keyed to the IDENTITY vocabulary —
    every canonical role AND every checked non-seat identity. `creator` is why the distinction is
    load-bearing rather than pedantic: it is not a canonical role, so a role-keyed subtraction
    would let `NON_ROLE_DIRS: creator` through and drop `memory/creator/` out of the structural
    checks — a checked identity exempting itself from its own checker.

    THIS is what makes the rule true rather than merely announced. A declaration naming such a
    name is reported as a BLOCKER by `check_non_role_dirs`, but reporting alone would leave it
    excluded anyway — an alarm without a prevention, which is strictly worse than no guard at
    all, because the operator sees a complaint and the identity still vanishes from inference.
    Filtering here means the sentence "a checked identity cannot be excluded" is a fact about the
    code path, and the blocker is the notification of a refusal that has ALREADY happened.
    """
    return {n for n in declared if n not in LOCK_VOCABULARY}


def infer_roles(ws: Path, excluded=()):
    mem = ws / "memory"
    if not mem.is_dir():
        return set()
    excluded = set(excluded)
    return {d.name for d in mem.iterdir() if d.is_dir() and d.name not in excluded}


def check_non_role_dirs(ws: Path, slots, f: Findings):
    """Report on the DECLARATION. Returns nothing; the applied set comes from
    `effective_exclusions`, which has already refused every name in LOCK_VOCABULARY — canonical
    role or checked non-seat identity alike — by the time this runs.

    ⛔ The membership test below must stay keyed to the same LOCK_VOCABULARY. Keyed to
    CANONICAL_ROLES it would silently omit the `creator` refusal even while `effective_exclusions`
    correctly retained it: the name would be inferred, but the operator would never be told the
    declaration had been refused.
    """
    declared = declared_non_role_dirs(slots)
    if not declared:
        return
    mem = ws / "memory"
    present = {d.name for d in mem.iterdir() if d.is_dir()} if mem.is_dir() else set()
    for name in sorted(declared):
        if name in LOCK_VOCABULARY:
            f.blocker(
                f"NON_ROLE_DIRS declares '{name}', which the identity vocabulary defines "
                "— the declaration was REFUSED and the name is still inferred; remove "
                "it from the row")
        elif name not in present:
            f.warn(f"NON_ROLE_DIRS declares '{name}' but memory/{name}/ does not exist "
                   "— stale exclusion, remove it")


def check_structure(ws: Path, roles, f: Findings):
    required = [
        "BINDINGS.md", "README.md", "MODELS.md",
        "channel/INDEX.md",
        "tools/validate_auth_log.py",
        "tools/conformance_check.py",
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
        # A PROFILE enumerates SEATS. `roles` is every directory under
        # memory/, which by this file's own doctrine (see IDENTITIES THAT
        # ARE NOT SEATS) holds IDENTITIES -- seats AND non-seats. Comparing
        # the two sets directly asks a SEAT question of an IDENTITY set, so
        # a workspace with a legitimate `memory/creator/` fails a profile it
        # actually satisfies.
        #
        # Subtract non-seats HERE and ONLY here: check_structure still
        # iterates every identity, so a non-seat's three artifacts stay
        # REQUIRED and CHECKED -- this admits the identity to the profile,
        # it does not exempt it from anything.
        #
        # The guard stays on `roles`, NOT on `seats`: a workspace holding
        # ONLY non-seat identities has no seats, and must fail LOUDLY rather
        # than skip the comparison for having nothing to compare.
        seats = roles - set(NON_SEAT_IDENTITIES)
        if roles and seats != expected:
            set_aside = sorted(roles & set(NON_SEAT_IDENTITIES))
            # Name what was set aside. A message reporting only the seats
            # would read as though memory/ held nothing else.
            #
            # The remainder is listed with NO noun, deliberately. `seats` is
            # `roles - NON_SEAT_IDENTITIES` -- identities not KNOWN to be
            # non-seats -- so it still contains any unrecognised directory,
            # which is precisely not a seat. Calling the list "seats" states
            # something false about exactly the directory the operator most
            # needs described correctly. The note appears exactly when the
            # remainder differs from `roles`, so it already carries the whole
            # disclosure: the noun said nothing the note does not.
            note = (f" (non-seat identities not compared: {set_aside})"
                    if set_aside else "")
            f.blocker(
                f"profile {profile} expects roles {sorted(expected)} but "
                f"memory/ has {sorted(seats)}{note}")

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


def _ver_tuple(v):
    """'v2.6' -> (2, 6) for ordering comparisons."""
    return tuple(int(x) for x in v.lstrip("v").split("."))


# Two-stage banner parse: ANY protocol-marker-shaped token is counted first
# (so a second marker of ANY version shape — `[PROTOCOL v3.0]`, `[PROTOCOL
# v26]` — breaks the exactly-one rule), then the single survivor must match
# the strict well-formed stamp. A v2.x-only counting regex would let a
# non-v2.x second marker escape the count (codex r3 probe).
_BANNER_ANY_STAMP_RE = re.compile(r"\[PROTOCOL\b[^\]]*\]")
_BANNER_STAMP_RE = re.compile(r"\[PROTOCOL (v\d+\.\d+)\]")


def _record_stamp_ok(text, pinned):
    """APPEND-ONLY records (auth-logs, channel INDEX) keep the stamp of the
    protocol version they were CREATED under — a record's banner is part of
    the record, and version migrations never rewrite append-only files (doing
    so would trip the records' own append-only integrity gates). Judged on the
    record's BANNER LINE ONLY (first content line, BOM-tolerant) — body text
    naturally quotes historical protocol tokens and must never mask a wrong,
    newer, or missing banner. Valid = the banner carries exactly one
    protocol-marker-shaped token AND that token is a well-formed
    [PROTOCOL vX.Y] stamp whose version is a SUPPORTED_VERSIONS member that
    does not exceed the workspace pin. Anything else (no banner token, a
    second marker of ANY shape, unsupported, malformed, or newer than pin)
    is a finding."""
    if pinned is None:
        return True
    banner = None
    for line in text.splitlines():
        if line.lstrip("﻿").strip():
            banner = line
            break
    if banner is None:
        return False
    markers = _BANNER_ANY_STAMP_RE.findall(banner)
    if len(markers) != 1:
        return False
    m = _BANNER_STAMP_RE.fullmatch(markers[0])
    if m is None:
        return False
    v = m.group(1)
    return v in SUPPORTED_VERSIONS and _ver_tuple(v) <= _ver_tuple(pinned)


def check_auth_logs(ws: Path, roles, pinned, f: Findings):
    for role in sorted(roles):
        p = ws / "memory" / role / "auth-log.md"
        if not p.is_file():
            continue  # missing-file already reported by structure check
        t = p.read_text(encoding="utf-8", errors="replace")
        if pinned and not _record_stamp_ok(t, pinned):
            f.warn(f"memory/{role}/auth-log.md banner lacks exactly one "
                   f"supported creation-version PROTOCOL stamp <= pin "
                   f"({pinned})")
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
    if pinned and not _record_stamp_ok(t, pinned):
        f.warn(f"channel/INDEX.md banner lacks exactly one supported "
               f"creation-version PROTOCOL stamp <= pin ({pinned})")
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
    # ⛔ An unrecognised role used to be DROPPED here, and the drop was silent.
    # Everything downstream is positional against `ordered`, so a profile
    # carrying a role this file does not know made the list short, and the
    # trap-check below — guarded by `if i < len(ordered)` — simply stopped
    # running for the trailing positions. A side literally named after another
    # canonical role went uncaught, and the silence was indistinguishable from a
    # clean result. A check that quietly stops checking is worse than one that
    # refuses: refusal is visible.
    #
    # ⛔ BOTH messages below say `memory/ holds`, NOT "profile declares", and the
    # distinction is the difference between a fixable report and a wild goose
    # chase. `roles` reaches this function from `infer_roles(ws, ...)` — it is
    # read off the memory/ TREE, never off the profile. Saying "profile declares"
    # sent the operator to BINDINGS.md to delete a declaration that was never
    # there, while the actual cause was a directory. A message must name the
    # thing the reader can go change.
    unknown = sorted(set(roles) - set(LOCK_VOCABULARY))
    if unknown:
        f.blocker(f"memory/ holds {unknown}, which this checker's identity "
                  f"vocabulary does not define (known: {list(LOCK_VOCABULARY)}) — "
                  "SIDE_NAMES are positional against that vocabulary, so the "
                  "side-name checks below cannot be trusted for this workspace")
    # A KNOWN identity that is not a seat is a different condition from an
    # unknown one, and collapsing the two would be the silent drop again wearing
    # a blocker's clothes: it gets no SIDE_NAMES slot by design, so the count
    # mismatch warning below would otherwise fire and read as a profile defect.
    non_seat = sorted(set(roles) & set(NON_SEAT_IDENTITIES))
    if non_seat:
        f.warn(f"memory/ holds {non_seat}, which this checker knows as an "
               "identity but not as a positional seat — it takes no SIDE_NAMES "
               "slot, so the count below is measured against the seats alone, "
               "and a side NAMED after it is refused")
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
        # A non-seat identity may not occupy a SIDE_NAMES position at all.
        #
        # ⛔ Keyed to the IDENTITY vocabulary, and the trap below is deliberately
        # NOT — they ask different questions and share only a vocabulary. The
        # trap asks what /wake RESOLVES, which is canonical roles (tier 1); a
        # non-seat identity is never resolved by that path (the creator seat
        # "does not wake through the workspace role-resolution path" —
        # docs/CREATOR-SEAT-CHARTER.md §6), so re-keying the trap to the
        # identity vocabulary would raise a BLOCKER asserting a collision that
        # cannot occur. This check asks the identity question instead — may this
        # name hold a seat? — which is exactly what the identity vocabulary
        # answers, and it is what makes a misconfigured seat row fail closed
        # rather than pass with warnings the reader has been pre-excused for.
        # ⛔ `and name in roles` is LOAD-BEARING, not a narrowing of convenience.
        # A workspace that does NOT carry this identity may legitimately name a
        # side after it — `owner / creator` in a 2-agent workspace is legal, and
        # test_role_vocabulary.AnIdentityIsNotAutomaticallyASeat holds exactly
        # that line after a past defect made `creator` illegal as a side name in
        # EVERY workspace. Blocking on the name alone re-introduces that defect
        # by a different route. What is refused is narrower and is a statement
        # about THIS workspace: it carries the identity AND hands it a seat, so
        # the profile asserts a seat that does not exist.
        if name in NON_SEAT_IDENTITIES and name in roles:
            f.blocker(f"SIDE_NAMES entry '{name}' is an identity this workspace "
                      "carries, not a seat it has — SIDE_NAMES positions map "
                      "onto seats in order, so this entry claims a seat that "
                      "does not exist")
        # A side named after a DIFFERENT role's canonical name is a trap —
        # checked against ALL canonical roles, not just this profile's: /wake
        # resolves canonical names FIRST (tier 1), before any workspace alias,
        # so `/wake orchestrator` in a 2-agent workspace whose OWNER side is
        # named `orchestrator` would target the absent orchestrator role.
        #
        # ⛔ This was guarded by `if i < len(ordered)`, so a name in a position
        # past the profile's role count was never trap-checked at all — the same
        # "quietly stops checking" failure this function's own preamble
        # describes, surviving one layer below the cure that named it. The
        # collision is a property of the NAME (what /wake resolves), not of the
        # position, so it is checked at EVERY position. Only the message needs
        # the position's role, and a surplus position has none.
        my_role = ordered[i] if i < len(ordered) else None
        for other in CANONICAL_ROLES:
            if other != my_role and name == other:
                whose = (f"the {my_role} side" if my_role is not None
                         else f"position {i + 1}, which maps to no seat in "
                              "this profile")
                f.blocker(f"SIDE_NAMES entry '{name}' ({whose}) "
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
        got = role_lock_role(p.read_text(encoding="utf-8", errors="replace"))
        if got is None:
            f.blocker(f"memory/{role}/MEMORY.md has no parseable ROLE_LOCK line "
                      "— one-agent-per-role can't be confirmed (fails closed); "
                      "the declaration's first sentence must name exactly one "
                      f"of {list(LOCK_VOCABULARY)} and must not negate")
            continue
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
    declared = declared_non_role_dirs(slots)
    applied = effective_exclusions(declared)
    roles = infer_roles(ws, excluded=applied)
    pinned = pinned_version(slots)
    if not roles:
        f.blocker("no memory/<role>/ directories found — not a workspace?")

    check_non_role_dirs(ws, slots, f)
    check_structure(ws, roles, f)
    check_bindings(ws, slots, roles, pinned, f)
    check_side_names(slots, roles, f)
    check_transport(slots, f)
    check_one_agent_per_role(ws, roles, f)
    check_auth_logs(ws, roles, pinned, f)
    check_channel(ws, pinned, f)
    check_channel_entry_format(ws, f)

    # The role set is the denominator every structural check below is measured against, so it
    # is printed beside the verdict — together with what was excluded and what was REFUSED —
    # and on the red path as well as the green one. A verdict a reader cannot reconcile against
    # `ls memory/` is one they have to take on trust.
    refused = sorted(declared - applied)
    context = f"roles: {sorted(roles)}"
    if applied:
        context += f" | excluded by NON_ROLE_DIRS: {', '.join(sorted(applied))}"
    if refused:
        context += (f" | REFUSED (in the identity vocabulary, still inferred): "
                    f"{', '.join(refused)}")

    blockers, warns = f.counts()
    if not f.items:
        print(f"CONFORMANCE: clean ({ws.name}, {context})")
        return 0

    print(f"CONFORMANCE: {blockers} blocker(s), {warns} warning(s) [{ws.name}, {context}]")
    for sev, msg in f.items:
        print(f"  [{sev}] {msg}")
    fail = blockers > 0 or (args.strict and warns > 0)
    if not fail:
        print("(warnings only — workspace is structurally sound but not fully "
              "bound; use --strict to require every slot resolved)")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
