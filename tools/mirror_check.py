#!/usr/bin/env python3
"""Mirror-consistency CI for the agent-protocol skills (PROTOCOL v2.8).

Guards against the drift class that produced the original v2 defects:
role skills contradicting each other or the agent-core normative files.
Run from the repo root: python tools/mirror_check.py
Exit 0 = green; nonzero = findings printed.
"""
import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
from pathlib import Path, PurePosixPath

# Findings quote real bytes (`§ — é`, `Â§ â€” Ã©`). Piped or redirected on Windows,
# stdout defaults to cp1252 and PRINTING such a finding raises UnicodeEncodeError —
# the gate would crash while reporting the one defect that is Windows-specific.
# A gate that cannot say what it found has not found it.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "plugins" / "agent-protocol" / "skills"
CORE = SKILLS / "agent-core" / "references"
ROLES = ["owner-engine-agent", "helper-builder-agent", "orchestrator-agent"]

findings = []
notes = []  # relaxations in force — PRINTED every run, green or red


def text(p: Path) -> str:
    """Fail CLOSED, never fail LOUD-BY-CRASHING: several sections read the core
    files directly, and deleting channel-core.md used to raise here mid-run — the
    gate died with a traceback BEFORE printing a single finding it had already
    collected. A gate that dies while reporting has not reported (the same defect
    class as the stdout guard, arriving through the filesystem instead of the
    codec). A missing/unreadable file is a finding, and its content is then empty
    — which makes every content check on it fail loud and correctly attributed,
    never vacuously green: a check for a REQUIRED phrase in "" is a finding."""
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        findings.append(f"unreadable file {p.relative_to(ROOT)}: {exc}")
        return ""


def check(cond: bool, msg: str) -> None:
    if not cond:
        findings.append(msg)


# 0. THE TREE DECLARES ITSELF.
#
# "The twin pair must exist here" and "if both are here they must agree" are two
# different claims, and the last release fused them. Making existence fail LOUD
# closed a real hole (deleting a twin used to pass the twin gate) — and it was
# right for THIS tree. But the same tool also runs in the private mirror, which
# carries the skill tree and NOT the docs tree, by design. There, seven existence
# gates fire on artifacts that are absent on purpose and the gate stands
# permanently red. A gate nobody can ever see go green is not a gate; it is a
# thing people learn to scroll past. That is the failure this file exists to
# prevent, so it must not be the failure this file causes.
#
# A tree may therefore DECLARE what it is, in a tracked `.mirror-check.json`:
#
#     {"docs_tree": false,
#      "stamp_exempt": [{"path": "...", "reason": "..."}]}
#
# BOUNDS — a declaration may relax only what it is allowed to relax, because an
# unbounded declaration is just a bypass with a config file in front of it:
#   - it may switch off the docs-tree EXISTENCE gates. It may NOT switch off
#     their consistency checks: whatever IS present is still compared.
#   - it may exempt ENUMERATED paths from the version-stamp gate, each with a
#     non-empty reason. (Stamp exemptions exist for files whose BYTES are
#     load-bearing — a byte-identical custody copy, say — where stamping a
#     banner in would break the very guarantee the file exists to provide.)
#   - it may NEVER switch off the BOM gate, and it may never be SILENT: every
#     relaxation in force is printed with its reason on every run.
#   - a stale entry — exempting a path that is not there — is itself a FINDING,
#     so the list cannot quietly rot into a blanket bypass.
#   - an unreadable declaration fails CLOSED (full gates + a finding). It never
#     means "relax everything"; that is the one interpretation a broken config
#     must never get.
#
# No declaration file at all => exactly the behaviour the public tree had before
# this option existed. The default is not "trusting"; the default is "strict".
DECL_PATH = ROOT / ".mirror-check.json"
ALLOWED_KEYS = {"docs_tree", "stamp_exempt"}

# UTF-8, UTF-16 LE/BE, UTF-32 BE/LE. UTF-32 LE (FF FE 00 00) shares UTF-16 LE's
# 2-byte prefix, so it is listed FIRST and matched before plain UTF-16 LE — the
# label in the finding is then accurate rather than "FF FE". Declared here, above
# the declaration loader, because that loader must reject a BOM'd declaration: the
# file that configures the BOM gate does not get to violate it.
BOMS = [(b"\x00\x00\xfe\xff", "UTF-32 BE"), (b"\xff\xfe\x00\x00", "UTF-32 LE"),
        (b"\xef\xbb\xbf", "UTF-8"), (b"\xff\xfe", "UTF-16 LE"),
        (b"\xfe\xff", "UTF-16 BE")]


STRICT = {"docs_tree": True, "stamp_exempt": []}


def refuse(why: str) -> dict:
    """ALL-OR-NOTHING. A declaration is honoured only if it is entirely well-formed;
    any defect in it grants NOTHING and runs the full gate set.

    The first cut honoured a declaration piecemeal — it stripped a BOM and carried
    on, and an unknown key raised a finding while the keys it *did* understand still
    took effect. Both reviewers walked straight through that: a malformed file was
    still relaxing gates. Partial trust in a config that exists to weaken checks is
    just a bypass with extra steps. There is no half-valid declaration."""
    findings.append(f"{DECL_PATH.name}: {why} — REFUSED. No relaxation is granted "
                    "and the full gate set is running.")
    return dict(STRICT)


def declaration_is_tracked() -> bool:
    """The declaration is the one file where a bypass would hide, so it must be in
    the repo where a reviewer can see it in the diff. An untracked one is invisible
    to review and is refused. (Both reviewers landed this: an untracked declaration
    silently relaxed a local run.)"""
    try:
        subprocess.run(["git", "ls-files", "--error-unmatch", "--", DECL_PATH.name],
                       cwd=str(ROOT), capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError:
        return False        # no git → cannot audit it → cannot trust it


def _exact_spelling(rel: str) -> bool:
    """True when every segment of rel matches an on-disk name byte-exactly —
    or, failing that, matches EXACTLY ONE normalization-equivalent,
    case-exact entry. is_file() answers case-insensitively on Windows, so a
    declaration spelled 'Transports/x.md' names a real file here and a
    MISSING one on Linux — one declaration, two meanings (round 16). The
    normalization allowance is round 18: macOS DECOMPOSES filenames on disk
    while git stores the precomposed spelling (core.precomposeUnicode), so
    a faithful checkout there answers with an NFD name for an NFC index
    entry — byte-exact comparison would call every non-ASCII tracked name
    an alias on the platform behaving correctly. Case variants and 8.3
    short names never normalization-match, so the alias findings this
    function feeds are unaffected; zero or SEVERAL equivalent entries stay
    False (several is a real ambiguity — two on-disk spellings of one
    name)."""
    cur = ROOT
    for seg in rel.split("/"):
        try:
            entries = os.listdir(cur)
        except OSError:
            return False
        if seg in entries:
            cur = cur / seg
            continue
        want = unicodedata.normalize("NFC", seg)
        matches = [e for e in entries
                   if unicodedata.normalize("NFC", e) == want]
        if len(matches) != 1:
            return False
        cur = cur / matches[0]
    return True


def _reject_duplicate_keys(pairs):
    """object_pairs_hook: a plain json.loads keeps the LAST of duplicate keys,
    so {"docs_tree": true, "docs_tree": false} reads as reviewed-strict while
    enforcing relaxed (round 15). Ambiguity in a file whose job is to weaken
    gates is refused at every object level."""
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON key {k!r} — the last value would "
                             "silently win over the one a reviewer read first")
        seen[k] = v
    return seen


def load_declaration():
    if not DECL_PATH.is_file():
        return dict(STRICT)
    # The declaration must be a REGULAR file. A tracked symlink (git mode
    # 120000) satisfies the tracked-ness check by NAME while the EFFECTIVE
    # bytes come from wherever it points — which can be an untracked file no
    # diff ever reviewed (round 15). The reviewed bytes must BE the bytes.
    try:
        _st = os.stat(DECL_PATH, follow_symlinks=False)
    except OSError as exc:
        return refuse(f"cannot be inspected ({exc})")
    if DECL_PATH.is_symlink() or bool(
            getattr(_st, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
        return refuse("is a symlink or reparse point — the bytes a reviewer "
                      "sees in the diff must be the effective bytes, and a "
                      "link can source them from an untracked file")
    if not declaration_is_tracked():
        return refuse("present but NOT TRACKED by git (or git is unavailable, so it "
                      "cannot be audited). A file that relaxes gates must be visible "
                      "in the diff that relaxes them")
    try:
        raw = DECL_PATH.read_bytes()
    except OSError as exc:
        return refuse(f"cannot be read ({exc})")
    if any(raw.startswith(sig) for sig, _ in BOMS):
        return refuse("carries a byte-order mark — the file that configures the BOM "
                      "gate does not get to violate it")
    try:
        decl = json.loads(raw.decode("utf-8"),
                          object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, ValueError) as exc:
        return refuse(f"is not valid UTF-8 JSON ({exc})")
    if not isinstance(decl, dict):
        return refuse("must be a JSON object")
    unknown = sorted(set(decl) - ALLOWED_KEYS)
    if unknown:
        return refuse(f"has unknown key(s) {unknown} — a typo must never read as a "
                      "granted relaxation, and the author believes they declared "
                      f"something (known keys: {sorted(ALLOWED_KEYS)})")
    if "docs_tree" in decl and not isinstance(decl["docs_tree"], bool):
        return refuse("'docs_tree' must be true or false")
    if "stamp_exempt" in decl and not isinstance(decl["stamp_exempt"], list):
        return refuse("'stamp_exempt' must be a list")
    seen_exempt = set()
    for entry in decl.get("stamp_exempt", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            return refuse(f"stamp_exempt entry {entry!r} needs a string 'path'")
        # A REASON must be a genuine non-empty string. The first cut wrote
        # str(entry.get("reason", "")), which turns null into "None", 0 into "0",
        # and False into "False" — every one of them a reason-less exemption
        # passing green. Both reviewers found it. Coercion is not validation.
        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return refuse(f"stamp_exempt entry for {entry.get('path')!r} has no "
                          f"non-empty string reason (got {reason!r}) — an "
                          "unexplained exemption is indistinguishable from a bypass")
        # HOSTILE path shapes refuse the WHOLE declaration, here at load —
        # round 14: they were per-entry findings inside stamp_exemptions(),
        # which runs AFTER the declaration's other relaxations took effect,
        # so a file carrying '../..' kept its docs_tree=false active and the
        # red run under-reported (the strict docs findings never printed).
        # A '..' or escaping path was never a typo and never legitimate
        # drift; nothing else in a file carrying one deserves trust. (A
        # STALE entry — a file deleted after it was declared — stays a
        # per-entry finding below: drift is not hostility, and the run is
        # red either way.)
        rel = entry["path"]
        if ".." in Path(rel).parts:
            return refuse(f"stamp_exempt path {rel!r} contains '..' — an "
                          "exemption names a literal path in this tree, and a "
                          "path that says 'elsewhere' was never a typo")
        try:                                    # confinement: no absolute or
            (ROOT / rel).resolve().relative_to(ROOT.resolve())   # linked escape
        except ValueError:
            return refuse(f"stamp_exempt path {rel!r} resolves outside the "
                          "repo — an exemption may only name a file in this "
                          "tree")
        # CANONICAL spelling. The exemption key is LEXICAL, so one file must
        # have exactly one spelling — the loader used to accept backslashes,
        # trailing slashes, '.' segments, and absolute in-repo paths, then
        # normalize them (round 15): a tracked declaration whose visible
        # spelling is not the enforced key, and which means something
        # different (or goes stale) on another OS.
        if ("\\" in rel or Path(rel).is_absolute() or rel != rel.strip()
                or any(seg in ("", ".") for seg in rel.split("/"))):
            return refuse(f"stamp_exempt path {rel!r} is not a canonical "
                          "repo-relative POSIX path — forward slashes, "
                          "relative, no '.' or empty segments, no trailing "
                          "slash; a lexical key must have one spelling")
        # EXACT on-disk spelling. Canonical FORM is not enough: is_file()
        # answers case-insensitively here, so 'Transports/x.md' passed every
        # check, printed its reason, exempted nothing (the lexical key never
        # matches the walked path) — and reads as STALE on a case-sensitive
        # host. A declaration must mean one thing on every host (round 16).
        # A path that names NO file either way is the stale case — per-entry
        # finding later, not a refusal.
        if (ROOT / rel).is_file() and not _exact_spelling(rel):
            return refuse(f"stamp_exempt path {rel!r} does not match the "
                          "tree's exact spelling — on this filesystem it "
                          "finds a file, on a case-sensitive one it is "
                          "stale; one declaration must mean one thing on "
                          "every host")
        # DUPLICATES. Two entries for one path print two reasons while only
        # one wins in enforcement — a review surface that disagrees with the
        # effective declaration (round 15).
        if rel in seen_exempt:
            return refuse(f"stamp_exempt lists {rel!r} more than once — every "
                          "declared reason prints, but only one entry can be "
                          "in force")
        seen_exempt.add(rel)
    return {"docs_tree": decl.get("docs_tree", True),
            "stamp_exempt": decl.get("stamp_exempt", [])}


DECL = load_declaration()
DOCS_TREE = DECL["docs_tree"]


def stamp_exemptions():
    """LEXICAL repo-relative POSIX path -> reason. Shape and reason were already
    validated (an invalid entry refuses the WHOLE declaration), so what is left
    is per-path truth: the file must be inside this tree, and it must actually
    be here. A stale entry — a list that outlives its files — is a finding,
    because that is how an exemption list quietly widens into a blanket bypass.
    Round 13: this map was keyed by RESOLVED path, so a directory junction (or
    symlink) at an UNLISTED path whose target was declared exempt INHERITED
    the exemption — the declaration reviewed one path and quietly exempted
    another. The key, and the comparison in stamped(), is the lexical path —
    where the file SITS, never where it points. Round 14 moved the HOSTILE
    shapes ('..' segments, paths escaping the repo) up into load_declaration's
    all-or-nothing refusal — by the time we are here, every entry is
    well-formed and confined, and only per-path TRUTH remains."""
    out = {}
    for entry in DECL["stamp_exempt"]:
        rel = entry["path"]
        target = ROOT / rel
        if not target.is_file():
            findings.append(f"stale stamp exemption: '{rel}' is declared exempt "
                            "but is not in this tree — remove the entry (a list "
                            "that outlives its files becomes a bypass)")
            continue
        key = target.relative_to(ROOT).as_posix()
        out[key] = entry["reason"].strip()
        notes.append(f"stamp-exempt: {key} — {entry['reason'].strip()}")
    return out


STAMP_EXEMPT = stamp_exemptions()

if not DOCS_TREE:
    notes.append(
        "docs_tree=false — this tree declares it does not carry the public docs "
        "artifacts, so 7 artifact-EXISTENCE gates are NOT APPLICABLE here: the "
        "CREATOR-SEAT-BOOTSTRAP.{md,html} twin pair, the amendment-header copies "
        "in CONTRIBUTING.md + .github/PULL_REQUEST_TEMPLATE.md + "
        ".github/ISSUE_TEMPLATE/protocol_amendment.md, the SOP-REGISTRY.md "
        "count gate, and docs/CLOUD.md. Consistency still runs on whichever of "
        "them ARE present, and no other gate is relaxed.")


def stamped(p: Path) -> bool:
    """Version-stamp gate, honouring enumerated exemptions — compared by the
    file's LEXICAL repo-relative path (round 13: a resolve()-based lookup let
    a junction alias inherit a declared exemption)."""
    return "v2.8" in text(p) or p.relative_to(ROOT).as_posix() in STAMP_EXEMPT


# 1. Core files exist
for name in ["channel-core.md", "review-core.md", "review-convergence.md",
             "never-idle-core.md", "binding-slots.md",
             "memory-discipline.md", "self-improvement-protocol.md",
             "proxy-auth-core.md"]:
    check((CORE / name).is_file(), f"agent-core missing {name}")

# 2. Byte gate: no byte-order mark of ANY encoding, in ANY file this repo ships.
# This gate has been narrowed wrong three times, and each narrowing looked
# reasonable:
#   - scoped to the skills subtree → missed a BOM in the release MANIFESTS;
#   - widened to the repo but gated on a SUFFIX ALLOWLIST → missed every tracked
#     extensionless file (.github/CODEOWNERS, .gitignore, LICENSE);
#   - widened to all files but checking only EF BB BF → missed UTF-16, which is
#     Windows PowerShell 5.1's DEFAULT output encoding, i.e. the single most
#     likely BOM to appear here by accident.
# So: every file, every BOM, read as bytes.
#
# EXCLUSIONS, stated because an unstated exclusion reads as coverage:
#   - files INSIDE the directories in SKIP_DIRS (VCS internals, tool caches,
#     vendored dependency trees) — but only if git does not track them. A file
#     git tracks is published, wherever it sits, so tracked paths are scanned
#     unconditionally and SKIP_DIRS cannot hide one.
#   - nothing else: no suffix allowlist, no size cut, no binary skip (this repo
#     ships no binaries; a real one cannot begin with a BOM anyway).
# Untracked working-tree files ARE scanned (local scratch can red the gate —
# noisy, never blind).
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules",
             ".pytest_cache", ".mypy_cache", ".ruff_cache"}
# (BOMS — the five signatures, longest-first — is declared above, next to the
# declaration loader, which must reject a BOM'd declaration.)


# 2a. `.ps1` INVERTS the rule — and the exception is not a favour to PowerShell,
# it is the same defect this repo keeps shipping, one layer up.
#
# Windows PowerShell 5.1 decodes a BOM-LESS UTF-8 .ps1 as ANSI. Every non-ASCII
# byte is mangled: `§ — é` comes back as `Â§ â€” Ã©` — verified on 5.1.26100, not
# recalled. That is the SAME mojibake class ops-gotchas warns about, which means a
# blanket "no BOM anywhere" gate would COMMAND the defect it was written to
# prevent. v1.2.4 shipped guidance that caused the defect it warned about; a gate
# that strips the BOM from a .ps1 is that bug again, wearing a CI badge.
#
# So for .ps1 the BOM is not tolerated — it is REQUIRED, whenever the file has any
# non-ASCII byte to mangle. Carving out a silent exemption would have been the lazy
# fix: it would have left the real bug (a script that mangles its own output)
# entirely unguarded. An exception you cannot state as a rule is a hole.
# The inversion is a property of PowerShell's SCRIPT READER, not of one suffix.
# `.ps1`, `.psm1` (module) and `.psd1` (manifest) all go through it and all mangle
# identically — a reviewer verified `.psm1` on 5.1.26100 and got the same `Â§ â€” Ã©`.
# Keying the exception on `.ps1` alone left the trap armed one extension over, and
# WORSE than before: the docs now tell you to save PowerShell with a BOM, so an
# author who obeyed them for a module file got red-gated by the fix itself. Bind the
# rule to the format that has the behaviour, not to the example that revealed it.
# And "the format" is wider than script code: `.psrc` (role capability) and `.pssc`
# (session configuration) are data files, but the engine loads both through the
# same reader — a reviewer fed a BOM-less UTF-8 `.psrc` to
# Import-PowerShellDataFile on 5.1 and got the identical mangle, with no extension
# check anywhere on that path. Until this line, the gate red-gated a correctly
# BOM'd `.psrc`: the round-1 MAJOR verbatim, one extension over, inside the
# release that fixed round 1.
# EXCLUDED, stated: `.ps1xml` (data, read as XML by .NET, not by the script reader).
PS_SCRIPT_SUFFIXES = {".ps1", ".psm1", ".psd1", ".psrc", ".pssc"}


def ps_script_bom_check(label: str, kind: str, raw: bytes) -> None:
    if raw[:3] == b"\xef\xbb\xbf":
        return                                  # correct: PS 5.1 reads it as UTF-8
    for sig, bom_label in BOMS:                 # UTF-16/32: PS runs it, but no tool
        if raw.startswith(sig):                 # in this repo can read it as text
            findings.append(f"BOM ({bom_label}) in {label} — a {kind} "
                            "wants the UTF-8 BOM specifically, not this one")
            return
    if any(b >= 0x80 for b in raw):
        findings.append(
            f"{label} is a {kind} with non-ASCII bytes and NO UTF-8 "
            "BOM — Windows PowerShell 5.1 will decode it as ANSI and mangle them "
            "(`§ — é` → `Â§ â€” Ã©`). PowerShell script files are the one class where "
            "the BOM is REQUIRED; write it with a BOM, or keep the script pure ASCII")


def bom_gate(label: str, kind: str, raw: bytes) -> None:
    """The per-file byte gate, fed bytes from ANY source — the worktree loop
    below and the index-blob scan (2c) both call it, because the bytes git
    publishes are the INDEX's, not necessarily the worktree's (round 17
    BLOCKER: a BOM'd blob swapped into the index behind a clean worktree
    twin was green — the gate read the one copy git does not ship)."""
    if kind in PS_SCRIPT_SUFFIXES:
        ps_script_bom_check(label, kind, raw)  # inverted rule — see 2a
        return
    head = raw[:4]
    for sig, bom_label in BOMS:
        if head.startswith(sig):
            findings.append(f"BOM ({bom_label}, {sig.hex(' ').upper()}) in "
                            f"{label}")
            break


INDEX_STAGE = {}   # name -> (mode, object id); filled by tracked_files()


def tracked_files():
    """Paths git tracks — authoritative for 'published'. Returns None (NOT an
    empty set) when git is unavailable, so the caller can tell 'tracks nothing'
    from 'could not ask' and refuse to certify reduced scope silently."""
    try:
        out = subprocess.run(["git", "ls-files", "--stage", "-z"],
                             cwd=str(ROOT),
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    # Decode git's RAW bytes as UTF-8 — git stores and emits pathnames as
    # UTF-8 bytes, but text=True decoded them with the WINDOWS LOCALE
    # (cp1252), so a tracked 'café.md' became a phantom path that exists
    # nowhere: the real file read as untracked (skipped under a cache dir)
    # and the phantom was never readable — a tracked BOM'd blob invisible to
    # the very gate that claims tracked files (round 16, BLOCKER).
    # --stage (round 17): mode and object id per entry, because the gates
    # below need to know WHICH bytes git publishes, not just which names.
    names = []
    for raw in out.split(b"\0"):
        if not raw:
            continue
        head, _, name_b = raw.partition(b"\t")
        try:
            name = name_b.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(
                f"tracked path not decodable as UTF-8: {name_b!r} — a name "
                "this gate cannot represent is a file it cannot scan; fail "
                "closed")
            continue
        parts = head.split(b" ")
        mode = parts[0].decode("ascii", "replace") if parts else "?"
        obj = parts[1].decode("ascii", "replace") if len(parts) > 1 else "?"
        stage = parts[2].decode("ascii", "replace") if len(parts) > 2 else "?"
        names.append(name)
        INDEX_STAGE[name] = (mode, obj)
        # The index PUBLISHES every entry; the byte gates read regular files.
        # A mode this gate cannot scan-by-content is content it cannot
        # certify (round 17): a symlink entry publishes its target path as
        # the blob, a gitlink publishes a commit this repo does not contain.
        if mode not in ("100644", "100755"):
            findings.append(
                f"non-regular index entry (mode {mode}): {name} — the index "
                "publishes this entry but the byte gates certify regular "
                "files only; fail closed")
        if stage != "0":
            findings.append(
                f"unmerged index entry (stage {stage}): {name} — a tree with "
                "unresolved merge stages has no single answer for what git "
                "would publish; fail closed")
    # NON-PORTABLE names. A segment ending in a dot or space, containing a
    # character Win32 forbids in file names, or naming a Windows device is
    # stored fine in the index but ALIASES to a different visible name — or
    # to no worktree file, or to a console device — on Windows, so what this
    # gate scans is not what that checkout answers with (round 16: 'x.md'
    # clean and stamped, 'x.md.' carrying a BOM'd unstamped blob, green;
    # round 17: 'bad?name.md', 'CONIN$.txt' and superscript-digit COM names
    # sailed through the first cut, which knew only trailing dot/space and
    # the classic device stems).
    _DEVICES = ({"con", "prn", "aux", "nul", "conin$", "conout$"}
                | {f"{dev}{d}" for dev in ("com", "lpt")
                   for d in "123456789" + chr(0xB9) + chr(0xB2) + chr(0xB3)})
    _FORBIDDEN = set('<>:"|?*\\') | {chr(c) for c in range(0x20)}
    for n in names:
        for seg in n.split("/"):
            if (seg != seg.rstrip(". ")
                    or seg.split(".", 1)[0].rstrip(" ").lower() in _DEVICES
                    or any(c in _FORBIDDEN for c in seg)):
                findings.append(
                    f"non-portable tracked path: {n!r} — a segment ending in "
                    "a dot or space, containing a character Windows forbids "
                    "in names, or naming a Windows device (console aliases "
                    "and superscript-digit COM/LPT included) cannot check "
                    "out faithfully on Windows, so the index publishes a "
                    "blob no visible worktree file answers for")
                break
    # COLLISIONS in the index. On a case-insensitive filesystem one worktree
    # file answers for every variant index entry, so scanning the visible
    # file certifies bytes the released tree does not carry — git ships BOTH
    # blobs (round 15: a case-variant index entry carrying a BOM'd unstamped
    # blob was green). The RAW ls-files names are the only place this is
    # detectable — Windows Path objects collapse the variants before any
    # later gate can see them. The key folds case, Unicode normalization
    # (NFC/NFD spellings of one name), and Windows dot/space trimming.
    groups = {}
    for n in names:
        key = "/".join(unicodedata.normalize("NFC", seg).casefold().rstrip(". ")
                       for seg in n.split("/"))
        groups.setdefault(key, []).append(n)
    for group in sorted(v for v in groups.values() if len(v) > 1):
        findings.append(
            "case-colliding tracked paths: " + ", ".join(sorted(group)) +
            " — one worktree file answers for all of these index entries on "
            "a case-insensitive filesystem, so this gate would certify bytes "
            "the released tree does not carry")
    # ALIAS RESOLUTION (round 17, judge): a tracked name that RESOLVES to a
    # worktree file spelled differently — an 8.3 short name (LONGNA~1.MAR
    # for longnamefile123.markdown), a lone case variant, a stripped
    # trailing dot — makes one on-disk file answer for an index blob under
    # another name: every byte gate reads the visible file and certifies
    # bytes git does not publish under that name. The collision key above
    # only sees PAIRS of tracked names; an alias needs no second entry.
    # _exact_spelling (the declaration loader's os.listdir walk) compares
    # the index spelling to the stored on-disk names, so ANY alias form —
    # including ones nobody has enumerated yet — trips it.
    for n in names:
        if (ROOT / n).is_file() and not _exact_spelling(n):
            findings.append(
                f"tracked path answers through an alias: {n!r} — the index "
                "spelling does not match the on-disk name it resolves to, "
                "so the scanned worktree file is not the file git publishes "
                "under this name; fail closed")
    return {ROOT / p for p in names}


def _tree_files(prune):
    """Every file under ROOT except the pruned directory names — enumerated
    with os.walk and an onerror callback, because Path.rglob() SUPPRESSES the
    OSError from a directory it cannot list (round 15: an unlistable
    directory under docs/ hid an untracked BOM'd file with no finding at all
    — the fail-closed rule the guarded trees got in round 14, applied to the
    whole-repo enumeration this gate advertises). Pruned dirs are never
    descended, so an unlistable one cannot red the gate either — pruning is
    the caller's statement that nothing under that NAME is claimed."""
    def _err(exc):
        findings.append(
            f"repository tree not fully scannable: "
            f"{getattr(exc, 'filename', None) or '<unknown path>'} "
            f"({type(exc).__name__}) — this gate claims every shipped and "
            "untracked file, and a directory it cannot list is unknown, "
            "not clean; fail closed")
    for cur, dirnames, filenames in os.walk(ROOT, onerror=_err):
        dirnames[:] = [d for d in dirnames if d not in prune]
        for name in filenames:
            yield Path(cur) / name


def repo_files():
    tracked = tracked_files()
    if tracked is None:
        # No git → cannot know which cache/vendor files are published. Rather
        # than silently narrow coverage (a tracked BOM under node_modules would
        # go unseen), scan EVERYTHING under root except .git, and say so once.
        findings.append("git unavailable: cannot resolve tracked files, so the "
                        "BOM gate is scanning every path except .git (a tracked "
                        "file under a cache/vendor dir cannot be distinguished "
                        "from scratch — run with git on PATH for exact scope)")
        yield from sorted(_tree_files(prune=frozenset({".git"})))
        return
    # With git available, SKIP_DIRS are PRUNED from the walk (round 16: an
    # unlistable untracked node_modules/ false-redded the gate — a scratch
    # dir the gate never claims must not be able to red it). Tracked files
    # under pruned dirs are NOT lost: they arrive through the tracked-set
    # tail below, which is exactly the path that reads them.
    seen = set()
    for p in sorted(_tree_files(prune=SKIP_DIRS)):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts) and p not in tracked:
            continue
        seen.add(p)
        yield p
    for p in sorted(tracked - seen):          # tracked but not walked
        if p.is_file():
            yield p
        else:
            # Round 17 (part of the BLOCKER): this tail used to DROP such
            # entries silently — a tracked name whose worktree file is
            # deleted, or can never materialize on this host, still
            # publishes its index blob, unscanned.
            findings.append(
                f"tracked path missing from the worktree: "
                f"{p.relative_to(ROOT).as_posix()} — git publishes its "
                "index blob but there is nothing here to scan; fail closed")


for p in repo_files():
    try:
        raw = p.read_bytes()
    except OSError as exc:                     # unreadable/locked → a finding,
        findings.append(f"unreadable file {p.relative_to(ROOT)}: {exc}")
        continue                               # never a crashed gate
    bom_gate(str(p.relative_to(ROOT)), p.suffix.lower(), raw)

# 2b. No mojibake in the skill tree.
# SCOPE, stated (an unstated scope reads as coverage): this sweep reads the
# SKILL TREE's .md files — the normative surface agents actually load. docs/,
# README and CHANGELOG are not swept for mojibake; the BOM gate above covers
# their bytes but cannot see mangled text (a mangle carries no BOM). Widening
# the sweep is cheap if the docs tree ever earns it — but today the claim is
# "the skill tree is clean", and that is the claim being checked.
# Three files legitimately CONTAIN the corruption, because they document it —
# channel-core states the byte rule and its .ps1 inversion, each ops-gotchas states
# what the shell does to it, and all land harder showing the real bytes than
# describing them. So the exemption is ENUMERATED — three exact repo-relative
# paths, never a basename and never "any file". The first cut keyed on BASENAME,
# which is an exemption that grows by itself: any future file that happened to be
# named ops-gotchas.md, anywhere in the tree, inherited the licence unreviewed.
# And the licensed files must EXIST: the exempt set used to be derived from the
# files found on disk, so deleting one deleted every check that ran on it — the
# presence gate below was vacuously green over a file that was GONE (a reviewer
# proved it by deleting the helper copy). Absence of a licensed file is a finding,
# not a smaller quorum — same rule as the twin pair.
#
# "Bounded" has to mean something a parser can decide — and the review record
# proved that "a parser" must not mean "a model of the document". Every
# earlier cut of this exemption bounded the licence with progressively more
# CommonMark: a backtick-lookback, span parity, a real span parser, a fence
# state machine, container peeling, indent bounds, the seven HTML-block kinds,
# a paragraph tracker. Eleven of the twenty-six recorded cuts (7, 9, 10, 11,
# 14, 15, 17, 18, 19, 20, 21) were the SAME defeat: some line shape CommonMark and
# the model classified differently, where the difference put a licensed span
# back in reach — phase inversion. Round 11 delivered four such divergences in
# one verdict (link-reference definitions, container-boundary state, ordered
# lists that cannot interrupt a paragraph, backticks in a backtick fence's
# info string), which is the space telling us it is not enumerable by hand.
#
# So the licence stopped consulting a model. A mojibake candidate is exempt
# iff its ENTIRE LINE is byte-identical to one of the enumerated documentation
# lines below, in that exact file. No spans, no fences, no blocks, no
# paragraphs: a line that byte-matches enumerated documentation cannot carry
# NEW corruption, by construction — and every other line in the tree is
# scanned unconditionally, whatever block CommonMark would say it sits in.
# Duplicating a licensed line elsewhere in its file is exempt and harmless
# (it is the same bytes); corrupting a licensed line un-matches it and every
# candidate on it reds; corrupting anything else was never licensed at all.
# The escape-spelled strings are deliberate: two of the mangled dashes differ
# only in a final U+0022 vs U+201D — visually identical, byte-distinct —
# exactly the near-twin a copy-paste gets wrong and nobody ever sees.
MOJIBAKE_EXEMPT_PATHS = [
    "plugins/agent-protocol/skills/agent-core/references/channel-core.md",
    "plugins/agent-protocol/skills/owner-engine-agent/references/ops-gotchas.md",
    "plugins/agent-protocol/skills/helper-builder-agent/references/ops-gotchas.md",
]

MOJIBAKE_EXAMPLE_LINES = {
    "plugins/agent-protocol/skills/agent-core/references/channel-core.md": {
        '    (`\xa7 \u2014 \xe9` \u2192 `\xc2\xa7 \xe2\u20ac\u201d \xc3\xa9`), so there the BOM is not tolerated but **required**.',
    },
    "plugins/agent-protocol/skills/owner-engine-agent/references/ops-gotchas.md": {
        'them. PowerShell round-trips inject BOM + mojibake (`\xe2\u20ac"`, `\xc2\xa7`) into transcribed',
        'non-ASCII byte (`\xa7 \u2014 \xe9` \u2192 `\xc2\xa7 \xe2\u20ac\u201d \xc3\xa9`). Note the loop that closes: that is not',
    },
    "plugins/agent-protocol/skills/helper-builder-agent/references/ops-gotchas.md": {
        '  byte (`\xa7 \u2014 \xe9` \u2192 `\xc2\xa7 \xe2\u20ac\u201d \xc3\xa9` \u2014 that is where this mojibake is BORN, not just where it',
        '  round-trips also inject mojibake (`\xe2\u20ac"`, `\xc2\xa7`) into transcribed verdicts and ledger',
    },
}

# The detector itself was the last enumeration standing. ("â€", "Â§") named the
# mangled em dash and section sign — the two characters the example spans happen
# to show — and nothing else. A line-by-line corruption sweep of the guarded
# files (encode UTF-8, decode cp1252: the exact defect) missed 18 corruptible
# lines — every one a line whose only non-ASCII is `→` or `⚠`, INCLUDING the
# .ps1 bullet this very release added to channel-core. (Independent sweeps
# agree on that 18-line gap while never agreeing on the corpus size — reviewers
# count "corruptible" differently — so the gap is the one reproducible number,
# and the only number stated here, in the CHANGELOG, or in the tests: a fourth
# reviewer caught the three surfaces each quoting a different corpus count.
# A number that does not reproduce does not get written down.) A marker
# enumeration is the suffix enumeration
# one section up, re-shipped: right for the instances that revealed it, silent
# one character over.
#
# The first repair took the four lead characters these docs happen to use
# (Â Ã â ð, for lead bytes C2/C3/E2/F0) — honestly scoped, and still one
# plausible edit from blind: `Ā` (lead 0xC4) mangles to `Ä€` and sailed through,
# because Ä was not in the set. Enumerating four leads is enumerating, with
# better prose. So take the WHOLE class, by construction: a cp1252-mangled UTF-8
# character is the rendering of a lead byte 0xC2–0xF4 followed by renderings of
# continuation bytes 0x80–0xBF, and that character run, mapped back to its
# bytes, IS valid UTF-8. Real corruption therefore always round-trips; prose
# almost never does (`café…` puts é before a continuation-class char, but é
# opens a THREE-byte sequence and no third byte follows, so the round-trip
# fails and it is not flagged). One stated exception CLASS: TRUNCATED mangles.
# Double-mangling through best-fit quotes eats the trailing byte, so the result
# cannot round-trip — the bytes that would prove it corruption are gone — yet
# it is corruption this repo has met in the wild (`â€`, the straight-quote
# dash, sits in these files' own examples). The first fix special-cased that
# ONE prefix, and a reviewer immediately produced its siblings: `â‚` (E2 82, a
# beheaded currency sign) and `ðŸ` (F0 9F, a beheaded emoji) fail the
# round-trip identically and were waved through. A truncated mangle is
# unrecognizable BY CONSTRUCTION, so this exception cannot be a class rule.
# Round 5 then caught the hand-kept family list violating its own charter
# within one round: "blocks that actually occur in text this project ships"
# was three families while the tree itself ships arrows and warning signs —
# `â†` and `âš` sailed through. The families are now DERIVED: every
# 3-plus-byte character the skill tree actually carries contributes its
# 2-byte prefix, plus three stated seeds met in the wild (punctuation,
# currency, emoji) that survive their characters leaving the tree. A
# hand-kept list lags its corpus; a derived one cannot. The five bytes
# cp1252 leaves undefined
# (81 8D 8F 90 9D) render as C1 controls under the Windows best-fit reader;
# both character classes and the inverse mapping carry them, so a mangled `❤`
# (E2 9D A4) is not invisible just because one of its bytes has no glyph.
_CP1252_ORPHANS = {0x81, 0x8D, 0x8F, 0x90, 0x9D}   # undefined in cp1252


def _cp1252_char(b: int) -> str:
    return chr(b) if b in _CP1252_ORPHANS else bytes([b]).decode("cp1252")


# The lead class takes EVERY lead byte 0xC2–0xF4 — including 0xDF (ß). Round 4
# excluded that one lead because "groß—aber" (DF 97) round-trips to valid
# UTF-8; round 5 proved a single-lead exclusion does not cure the class:
# `É—` (C9 97) and `é—“` (E9 97 93) round-trip identically, because cp1252
# renders the whole lead range AS the accented European letters — ANY of them
# hard against smart punctuation can form valid UTF-8. The ambiguity is
# symmetric and locally undecidable: the bytes of "Ã–" are both a mangled Ö
# and French prose. So the detector takes a SIDE and states it: a candidate
# whose continuation characters are ALL typography a human types directly
# after a word (_WRITER_PUNCT, 13 characters) is read as PROSE — UNLESS the
# candidate's bytes decode to Latin-1 Supplement text (round 7). The round-5
# cut of this guard read every such candidate as prose and called the blind
# range harmless because "the tree carries none of those characters" —
# checked by a coverage gate over the tree's own characters. A reviewer
# proved that gate checks the WRONG POPULATION: corruption arrives as the
# mangle of whatever text someone pastes, not of characters already present.
# Mangled Ö ("Ã–") landed green in a live skill file — its continuation byte
# renders as an en dash, so the prose side ate it, and the coverage gate
# never fired because Ö was never IN the tree while the mangle's components
# (Ã, –) are individually detectable. The tie-break: a prose-shaped candidate
# whose bytes decode to U+00A0–U+00FF is read as CORRUPTION — Ã directly
# against writer typography is vanishingly rare in real prose, while mangled
# Western-European text is the most common corruption there is. The prose
# side survives for everything that decodes beyond Latin-1: "É—" (U+0257),
# "ß—" (U+07D7), "é—“" (CJK) all stay green. Round 9 widened the corruption
# side once more: cp1252's OWN extension letters (ŒœŠšŽžŸƒ) sit outside
# Latin-1 Supplement but are exactly the non-Latin-1 letters a Windows-ANSI
# writer produces — a judge walked mangled French œ ("Å“": left curly IS
# writer typography, U+0153 is beyond Latin-1) straight through the prose
# side. Only Œ œ Š ƒ are reachable here (the other four carry a
# non-typography continuation byte, so the round-trip rule already flags
# them); stated cost of the widening: a REAL Å or Æ hard against an opening
# curly quote or NBSP now reads as corruption — a rare adjacency, and a loud
# false red beats silent corruption. Cost, restated: a mangle whose decode
# lands OUTSIDE Latin-1-plus-those-letters and whose continuations are all
# writer typography is still unseen (mangled NKo ߗ reads as "ß—") — held by
# the coverage gate below, now run over a FIXED support alphabet rather than
# the tree's shifting inventory.
#
# Typography a human types DIRECTLY AFTER a word character: … ‹ ' ' " " • – —
# › NBSP « ». Low quotes (‚ „) are deliberately absent — they OPEN quotations,
# so they follow spaces and dashes, not letters — and their absence is what
# keeps mangled ł (`Å‚`) visible.
_WRITER_PUNCT = frozenset({0x85, 0x8B, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96,
                           0x97, 0x9B, 0xA0, 0xAB, 0xBB})

_LEADS = "".join(_cp1252_char(b) for b in range(0xC2, 0xF5))
_CONTS = "".join(_cp1252_char(b) for b in range(0x80, 0xC0))
MOJIBAKE_RE = re.compile(f"[{re.escape(_LEADS)}][{re.escape(_CONTS)}]{{1,3}}")


def _cp1252_bytes(s: str):
    """Inverse of the Windows best-fit ANSI read (cp1252 + C1 controls for the
    five undefined bytes). None when a character has no cp1252 byte at all."""
    out = bytearray()
    for ch in s:
        if ord(ch) in _CP1252_ORPHANS:
            out.append(ord(ch))
        else:
            try:
                out += ch.encode("cp1252")
            except UnicodeEncodeError:
                return None
    return bytes(out)


# cp1252's letter repertoire beyond Latin-1 Supplement — see the round-9
# widening in the narrative above.
_CP1252_EXTENSION_LETTERS = frozenset("ŒœŠšŽžŸƒ")

# The truncation families, DERIVED plus stated seeds (see the narrative
# above): every 3-plus-byte character the skill tree carries contributes its
# 2-byte prefix, so the list cannot lag the corpus it claims to cover. Stated
# residual: a TRUNCATED mangle of a symbol the tree does not carry (â„ for ™,
# âˆ for ∞) has no derived family and fails the round-trip — unseen until
# the clean symbol arrives, when derivation picks its prefix up and the
# coverage gate pins the full-mangle side.
TRUNCATION_PREFIXES = tuple(sorted(
    {b"\xe2\x80", b"\xe2\x82", b"\xf0\x9f"}
    | {ch.encode("utf-8")[:2]
       for p in SKILLS.rglob("*.md") for ch in text(p)
       if ord(ch) >= 0x80 and len(ch.encode("utf-8")) >= 3}))


def _is_mojibake(candidate: str) -> bool:
    b = _cp1252_bytes(candidate)
    if b is None:
        return False
    if b[:2] in TRUNCATION_PREFIXES:    # the stated truncation exception, above
        return True
    n = 2 if b[0] < 0xE0 else 3 if b[0] < 0xF0 else 4
    if len(b) < n:
        return False
    try:
        b[:n].decode("utf-8")
    except UnicodeDecodeError:
        return False
    if all(c in _WRITER_PUNCT for c in b[1:n]):
        # The prose side of the stated ambiguity, above — but a candidate whose
        # bytes decode to Latin-1 Supplement text OR a cp1252 extension letter
        # is the mangle of common Western-European prose, and corruption is
        # the likelier reading (round 7: mangled Ö sailed through here as
        # "Ã + en dash"; round 9: mangled œ as "Å + left curly").
        decoded = b[:n].decode("utf-8")
        if all(0xA0 <= ord(c) <= 0xFF or c in _CP1252_EXTENSION_LETTERS
               for c in decoded):
            return True
        return False
    return True

_MD_LINE_BREAK = re.compile(r"\r\n|\r|\n")


def _md_lines(src: str) -> list:
    return _MD_LINE_BREAK.split(src)


def mojibake_hits(src: str, allowed_lines=frozenset()) -> list:
    """Every line is scanned; a candidate is exempt ONLY when its entire line
    byte-matches an enumerated documentation line (MOJIBAKE_EXAMPLE_LINES —
    the licence narrative lives there). Earlier versions decided the
    exemption's reach with a document MODEL — a backtick lookback, span
    parity, a real span parser, a fence state machine, container peeling,
    indent bounds, the seven HTML-block kinds, a paragraph tracker — and ten
    review rounds each found a line shape the model and CommonMark read
    differently, with the difference putting a licensed span back in reach.
    A byte-identical line can carry no new corruption; every other line is
    scanned unconditionally, whatever block CommonMark would say it sits
    in — fences, HTML blocks and delimiter lines exempt nothing because
    NOTHING does except the enumerated bytes.

    A "line" here is what a markdown renderer ends with CRLF, CR, or LF —
    NOT str.splitlines(), whose wider separator set (VT, FF, NEL, U+2028,
    U+2029) is a round-12 defeat re-armed: those are characters IN a
    markdown line, so splitting on them let "junk + VT + licensed line"
    self-exempt its licensed suffix while a renderer shows one modified
    line carrying the mangled bytes. Splitting only where markdown does
    makes that construct a single line, byte-different from the licence,
    and therefore scanned."""
    hits = []
    for lineno, line in enumerate(_md_lines(src), 1):
        if line in allowed_lines:
            continue
        for m in MOJIBAKE_RE.finditer(line):
            if _is_mojibake(m.group(0)):
                hits.append((lineno, m.group(0)))
    return hits


# An allowlist that outlives the text it permits is a bypass in waiting: it would go
# on licensing a string nobody writes any more, and nobody would ever see it. Same
# rule as the stale stamp exemption — every entry must be earning its keep.
def check_example_allowlist_is_live() -> None:
    for rel, lines in sorted(MOJIBAKE_EXAMPLE_LINES.items()):
        if rel not in MOJIBAKE_EXEMPT_PATHS:
            findings.append(
                f"mojibake allowlist keyed to a non-exempt path: {rel} — the "
                "licence and the exemption list must name the same files")
            continue
        content = set(_md_lines(text(ROOT / rel)))   # same line unit as the scan
        for want in sorted(lines):
            if want not in content:
                findings.append(
                    f"stale mojibake allowlist line in {rel}: {want[:60]!r}… — "
                    "the gate licenses a line the file no longer carries. Remove "
                    "or update the entry: an allowlist that outlives its text "
                    "quietly licenses corruption")
            elif not any(_is_mojibake(m.group(0))
                         for m in MOJIBAKE_RE.finditer(want)):
                findings.append(
                    f"dead mojibake allowlist line in {rel}: {want[:60]!r}… — it "
                    "licenses no detectable mangle today, so the entry exempts "
                    "nothing and quietly pre-licenses whatever lands on that "
                    "line tomorrow")


# The allowlist licenses the MANGLED strings — so it happily licenses a file whose
# CLEAN example has been swapped for its mangled twin: the trio is an allowlisted
# span, and nothing above ever said the clean text must still be there. The judge
# performed exactly that swap and the gate said green. The exemption exists so
# these files can show the corruption NEXT TO the correct form; a file showing
# only the mangled bytes is not documenting a defect, it is having one — with a
# permit. So the licence is conditional on a PRESENCE, and the presence is checked.
CLEAN_EXAMPLE = "`\xa7 — \xe9`"            # `§ — é` as an inline code span


def check_clean_example_is_present(files) -> None:
    for p in files:
        if CLEAN_EXAMPLE not in text(p):
            findings.append(
                f"{p.relative_to(ROOT)} is mojibake-exempt so it can show the "
                f"corruption next to the clean form, but the clean example "
                f"{CLEAN_EXAMPLE} is gone — an exempt file carrying only the "
                "mangled bytes is a corrupted file with a permit")


exempt_files = []
for rel in MOJIBAKE_EXEMPT_PATHS:
    p = ROOT / rel
    if p.is_file():
        exempt_files.append(p)
    else:
        findings.append(
            f"mojibake-exempt file missing: {rel} — the exemption licenses it and "
            "the skill tree requires it; a licence whose file is gone is a gate "
            "quietly narrowed, not a smaller quorum")
# The licence is keyed LEXICALLY — by where the file sits in the tree, never
# through resolve(). Round 12: resolve()-keying let a symlink at an UNLISTED
# path inherit its exempt target's licence (the r3 basename-inheritance hole,
# rebuilt through the filesystem), and an out-of-tree symlink target CRASHED
# the checker on relative_to before it printed a single finding (the r3
# unguarded-read class, arriving through resolution instead of absence).
#
# Round 13: the round-12 symlink rule was enforced only on the *.md files the
# walk could SEE — and rglob does not look through a symlinked DIRECTORY, so
# aliasing a whole skills directory hid its guarded content from every gate
# in this file with no finding at all: a walk cannot police the thing it
# cannot traverse. The guarded tree is therefore swept for reparse points of
# every kind — file or directory, symlink or junction (is_symlink() is False
# for a junction) — and any one of them is a finding in itself: a link that
# makes one file answer at two paths puts licensed bytes where no licence
# was reviewed.
def _unscannable(p, exc) -> None:
    # Round 14: a directory the gate cannot list is not clean — it is
    # UNKNOWN, and unknown fails closed. Without this, os.walk swallowed
    # the OSError and the branch simply ended: an access-denied directory
    # full of unstamped or licensed bytes came back green.
    findings.append(
        f"guarded tree not fully scannable: {p} ({type(exc).__name__}) — "
        "a gate that cannot list a directory cannot call its content "
        "clean; fail closed")


def _walk_error(exc: OSError) -> None:
    _unscannable(getattr(exc, "filename", None) or "<unknown path>", exc)


def _is_reparse(p: Path) -> bool:
    try:
        if p.is_symlink():
            return True
        st = os.stat(p, follow_symlinks=False)
    except OSError as exc:                      # can't even stat it: fail
        _unscannable(p, exc)                    # closed, and don't descend
        return True
    return bool(getattr(st, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


# Both walked trees are swept — skills AND transports carry path-keyed gates
# (the mojibake licence here, the stamp exemptions above), and an alias
# defeats a path key the same way in either.
for _guarded_root in (SKILLS, ROOT / "transports"):
    # Round 14: os.walk yields only DESCENDANTS — it never stats its own
    # root, so a junction replacing the entire guarded tree walked straight
    # through the sweep. The root is checked before the walk. (is_symlink,
    # not exists, guards the entry test: exists() follows links, so a
    # dangling symlink root would otherwise read as merely absent.)
    if not (_guarded_root.is_symlink() or _guarded_root.exists()):
        continue
    if _is_reparse(_guarded_root):
        findings.append(
            f"symlink in the guarded tree: "
            f"{_guarded_root.relative_to(ROOT).as_posix()} — the whole "
            "guarded tree answers through an alias; every path-keyed gate "
            "below it is keyed to paths that are not where the bytes live. "
            "Track the directory directly")
        continue
    for cur, dirnames, filenames in os.walk(_guarded_root, onerror=_walk_error):
        for name in dirnames + filenames:
            e = Path(cur) / name
            if _is_reparse(e):
                findings.append(
                    f"symlink in the guarded tree: "
                    f"{e.relative_to(ROOT).as_posix()} — this tree's gates "
                    "are keyed by path, and a link or junction that makes "
                    "one file answer at two paths puts licensed or exempted "
                    "bytes where no licence was reviewed. Track the file "
                    "directly")
        dirnames[:] = [d for d in dirnames if not _is_reparse(Path(cur) / d)]

for p in SKILLS.rglob("*.md"):
    rel = p.relative_to(ROOT).as_posix()
    allowed = frozenset(MOJIBAKE_EXAMPLE_LINES.get(rel, ()))
    hits = mojibake_hits(text(p), allowed)
    if hits:
        where = ", ".join(f"line {n}" for n, _ in hits[:4])
        findings.append(f"mojibake in {p.relative_to(ROOT)} ({where})")

check_example_allowlist_is_live()
check_clean_example_is_present(exempt_files)

# 2c. THE INDEX, NOT THE WORKTREE, IS WHAT GIT PUBLISHES. Every byte gate
# above reads worktree bytes — but a commit or archive ships the INDEX blob,
# and the two are not the same file (round 17, BLOCKER): a BOM'd blob swapped
# into the index behind a clean worktree twin was green, a tracked file
# deleted from the worktree fell out of the tail silently (cured in
# repo_files), and an index entry whose name cannot even materialize on
# Windows was green three ways. So every staged blob whose bytes differ
# from its worktree twin is read DIRECTLY from object storage — by the
# object id already in hand, in one cat-file batch — and pushed through the
# byte gates: the BOM gate for every file class, the mojibake scan for
# skill-tree .md files. The first cut asked `git diff` which entries
# diverge, and round 18 produced two green defeats of that question inside
# one verdict: diff IGNORES assume-unchanged/skip-worktree entries by
# design, and a same-size blob behind an unchanged stat cache is never
# content-compared at all. Enumerating the index itself leaves nothing for
# a flag or a stale stat cache to mute. A routinely dirty tree stays
# green — the blob behind an ordinary uncommitted edit is the last
# committed content, which passed these same gates when it landed; only
# bytes that never went through them can red here.
# SCOPE, stated: the stamp and content gates still certify the WORKTREE
# spelling. On a clean checkout (CI, a fresh clone — where releases are cut)
# index and worktree coincide, so the full gate suite covers the published
# bytes there; this section closes the local-divergence byte channel.
_SKILLS_PREFIX = SKILLS.relative_to(ROOT).as_posix() + "/"


def _index_blobs():
    """(name, blob bytes) for every stage-0 regular index entry, read from
    object storage in one `cat-file --batch` call. None when git cannot
    answer; a missing/unreadable object is a per-entry fail-closed
    finding."""
    entries = [(n, m_o[1]) for n, m_o in sorted(INDEX_STAGE.items())
               if m_o[0] in ("100644", "100755")]
    if not entries:
        return []
    try:
        out = subprocess.run(["git", "cat-file", "--batch"], cwd=str(ROOT),
                             input="".join(o + "\n" for _, o in
                                           entries).encode("ascii"),
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    blobs, pos = [], 0
    for name, obj in entries:
        nl = out.find(b"\n", pos)
        if nl < 0:
            blobs.append((name, None))          # header truncated
            continue
        head = out[pos:nl].split(b" ")
        # PARSE THE HEADER DEFENSIVELY — the whole point of this section is a
        # gate that reports instead of crashing, and a malformed header
        # (git version drift, a corrupt object db, a truncated batch)
        # reaching int(head[2]) would raise ValueError and take the checker
        # down with a traceback before it printed the findings it already
        # had (round 19: the no-crash contract, arriving through the object
        # store). A blob response is exactly "<oid> blob <decimal>\n<bytes>\n",
        # its first token the SAME object id we asked for — anything else,
        # including an incomplete body, an unexpected id, or a size token so
        # long int() itself refuses it (Python's 4300-digit limit, round 20:
        # a guard that crashes on its own input is not a guard), is an
        # unreadable blob (None), a per-entry fail-closed finding downstream.
        if (len(head) == 3 and head[0] == obj.encode("ascii")
                and head[1] == b"blob"
                and head[2].isdigit() and len(head[2]) <= 20):
            size = int(head[2])
            body = out[nl + 1:nl + 1 + size]
            if len(body) == size and out[nl + 1 + size:nl + 2 + size] == b"\n":
                blobs.append((name, body))
                pos = nl + 1 + size + 1          # content + trailing LF
            else:                                # body truncated / no LF
                blobs.append((name, None))
                pos = len(out)                   # stream desynced; stop reading
        else:                                    # "<oid> missing" or malformed
            blobs.append((name, None))
            pos = nl + 1
    return blobs


def _flag_hidden_entries():
    """Entries flagged assume-unchanged (lowercase tag in ls-files -v) or
    skip-worktree ('S'/'s'): git diff IGNORES them by design, so the
    divergence enumeration above is blind exactly there — a hostile staged
    blob behind either bit re-opened the round-17 channel (round 18, judge:
    BOM'd blob + --assume-unchanged = green). The bit is an instruction not
    to compare this entry against the worktree, and this gate cannot
    certify what it is told not to compare. Fail closed on the flag itself,
    whatever the blob carries."""
    try:
        out = subprocess.run(["git", "ls-files", "-v", "-z"], cwd=str(ROOT),
                             capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    hidden = []
    for raw in out.split(b"\0"):
        if len(raw) < 3:
            continue
        tag = raw[:1].decode("ascii", "replace")
        if tag == "S" or tag.islower():
            try:
                name = raw[2:].decode("utf-8")
            except UnicodeDecodeError:
                name = repr(raw[2:])
            hidden.append((tag, name))
    return hidden


_hidden = _flag_hidden_entries()
if _hidden is None:
    if INDEX_STAGE:     # git answered ls-files but not -v: fail closed
        findings.append(
            "cannot enumerate index flags (git ls-files -v failed) — "
            "divergence-hidden entries are unverifiable; fail closed")
else:
    for _tag, _name in _hidden:
        _bit = ("skip-worktree" if _tag in ("S", "s")
                else "assume-unchanged")
        findings.append(
            f"index entry hidden from divergence comparison ({_bit}): "
            f"{_name} — git diff ignores this entry by design, so the "
            "staged blob it publishes is never compared with the worktree "
            "bytes this gate reads; fail closed")


_blobs = _index_blobs()
if _blobs is None:
    if INDEX_STAGE:     # git answered ls-files but not cat-file: fail closed
        findings.append(
            "cannot read the staged blobs (git cat-file failed) — the "
            "bytes git would publish are unverified; fail closed")
else:
    for _name, _blob in _blobs:
        if _blob is None:
            findings.append(
                f"cannot read the staged blob for {_name} — the bytes git "
                "would publish are unverified; fail closed")
            continue
        try:
            _wt = (ROOT / _name).read_bytes()
        except OSError:
            _wt = None      # absent worktree twin is already a finding
        if _wt == _blob:
            continue        # the worktree scan above read these exact bytes
        bom_gate(f"{_name} (index blob)",
                 PurePosixPath(_name).suffix.lower(), _blob)
        # Suffix selection is the NORMALIZED suffix, not endswith(".md") —
        # round 18: a staged UPPER.MD blob took the BOM leg and skipped
        # this one, while the worktree sweep would have read the file.
        if (_name.startswith(_SKILLS_PREFIX)
                and PurePosixPath(_name).suffix.lower() == ".md"):
            _allowed = frozenset(MOJIBAKE_EXAMPLE_LINES.get(_name, ()))
            _hits = mojibake_hits(_blob.decode("utf-8", "replace"), _allowed)
            if _hits:
                _where = ", ".join(f"line {n}" for n, _ in _hits[:4])
                findings.append(
                    f"mojibake in the index blob for {_name} ({_where})")

# DETECTOR COVERAGE — the prose guard's bill, presented. The first cut of
# this gate swept only the characters the tree HAPPENED to carry, and round 7
# proved that is the wrong population: corruption arrives as the mangle of
# whatever text someone pastes — mangled Ö landed green while the tree-swept
# gate stayed silent, because Ö was never in the tree and the mangle's
# component characters individually pass. The population is now FIXED plus
# the living tree: every printable Latin-1 Supplement character (the text
# most likely to arrive in this repo's languages, present in the tree or
# not), cp1252's extension letters (round 9 — mangled French œ walked the
# prose side; the alphabet entry is what makes CI DEFEND that widening), and
# every distinct non-ASCII character the tree actually carries must mangle
# to something the detector flags. A character landing in what remains of
# the blind range is a finding at ARRIVAL time — extend the detector or
# reconsider the character, never discover the blindness from a corrupted
# file later.
_SUPPORT_ALPHABET = ({chr(cp) for cp in range(0xA0, 0x100)}
                     | _CP1252_EXTENSION_LETTERS
                     | {c for p in SKILLS.rglob("*.md") for c in text(p)
                        if ord(c) >= 0x80})
for _ch in sorted(_SUPPORT_ALPHABET):
    _m = "".join(_cp1252_char(b) for b in _ch.encode("utf-8"))
    if not (MOJIBAKE_RE.fullmatch(_m) and _is_mojibake(_m)):
        findings.append(
            f"detector blind spot: {_ch!r} (U+{ord(_ch):04X}) is in the "
            f"support alphabet but its cp1252 mangle {_m!r} the mojibake gate "
            "cannot see — the prose-guard blind range overlaps expected "
            "content; extend the detector or replace the character")

# 2c. The gate and the prose that teaches it must agree on the suffix set.
# Round 3, three reviewers, independently: the gate had grown to five suffixes
# and every guidance passage still said three — so a reader obeying the
# NORMATIVE doc for a `.psrc` saved it BOM-less and walked straight into the
# gate; a maintainer "simplifying" the gate back to match the doc would have
# re-opened the round-2 hole with the doc as their justification. Prose may not
# regress independently of the check it describes: the documented set is DERIVED
# from each file (every `.psX`-shaped token, minus the stated `.ps1xml`
# exclusion) and compared with the set the gate enforces.
# Derivation is CASE-INSENSITIVE and TWO-TIER — round 4: a doc teaching
# `.PS2` in caps, or bare .ps2 with no backticks, was invisible to a
# lowercase-backticked-only pattern; round 5: the cure over-corrected, and a
# bare FILENAME mention ("a fixture named archive.ps2") drifted the derived
# set and red-gated the file. So: a BACKTICKED suffix token is guidance
# wherever it sits, in any case; a BARE token counts only on a line that
# speaks of the BOM or byte-order — the inversion IS about the BOM, so
# inversion guidance that never says so is already broken guidance, and a
# filename in passing prose is not guidance at all. Round 6 tightened both
# triggers: a bare token must be lexically STANDALONE (the `.ps2` tail of
# `archive.ps2` is a filename fragment, not a suffix mention), and the
# BOM term must be a bounded word ("bombproof" is not a BOM discussion) —
# both false-red'd legitimate prose on a genuinely-BOM-speaking line.
# Round 7: the round-6 bounding itself was mis-scoped one alternation over —
# the word boundaries bound only to `boms?`, leaving `byte-order` an
# unbounded substring, so "byte-ordering"/"byte-ordered" activated the tier
# and false-red'd the very filename shape round 6 pinned green. The
# boundaries now wrap the WHOLE alternation.
# Stated limits: a backticked filename would still drift the set (loud and
# reviewable, never silent), and this gate holds the suffix SET in parity,
# not the semantics — a doc that lists all five but attributes the wrong
# READER to one of them is a reviewer's catch, not this gate's.
BACKTICKED_SUFFIX = re.compile(r"`(\.ps[a-z0-9]+)`", re.IGNORECASE)
BARE_SUFFIX = re.compile(r"(?<![\w.])\.ps[a-z0-9]+", re.IGNORECASE)
BOM_TERM = re.compile(r"(?<![a-z0-9])(?:boms?|byte-order)(?![a-z0-9])",
                      re.IGNORECASE)
for rel in MOJIBAKE_EXEMPT_PATHS:            # the same three files own this prose
    p = ROOT / rel
    if not p.is_file():
        continue                             # absence is already a finding above
    _t = text(p)
    _tokens = {s.lower() for s in BACKTICKED_SUFFIX.findall(_t)}
    for _line in _t.splitlines():
        if BOM_TERM.search(_line):
            _tokens |= {s.lower() for s in BARE_SUFFIX.findall(_line)}
    documented_sfx = _tokens - {".ps1xml"}
    if documented_sfx != PS_SCRIPT_SUFFIXES:
        missing = ", ".join(sorted(PS_SCRIPT_SUFFIXES - documented_sfx)) or "none"
        extra = ", ".join(sorted(documented_sfx - PS_SCRIPT_SUFFIXES)) or "none"
        findings.append(
            f"suffix parity: {rel} documents a different PowerShell-inversion "
            f"suffix set than the gate enforces (absent from the doc: {missing}; "
            f"documented but ungated: {extra}) — a reader obeying the doc gets "
            "red-gated, or ships the mangle the gate exists to catch")

# 3. Banned legacy vocabulary (superseded by v2.5) outside agent-core history
BANNED = [
    (r"ADOPT-W-CHANGES", "legacy verdict vocab ADOPT-W-CHANGES"),
    (r"\bAPPROVE / MODIFY\b", "legacy verdict vocab APPROVE/MODIFY"),
    (r"owner_to_helper_", "legacy filename example owner_to_helper_"),
    (r"owner_to_builder_", "legacy filename example owner_to_builder_"),
    (r"review_request_round", "unprefixed round filename"),
    (r"codex_verdict_round", "unprefixed verdict filename"),
    (r"PLACEHOLDER", "stray placeholder text"),
    (r"CHANNEL_DIR", "legacy split slot name CHANNEL_DIR (unified: CHANNEL)"),
    (r"CHANNEL_FILES", "legacy split slot name CHANNEL_FILES (unified: CHANNEL)"),
]
for p in SKILLS.rglob("*.md"):
    t = text(p)
    for pat, why in BANNED:
        if re.search(pat, t):
            findings.append(f"{why} in {p.relative_to(ROOT)}")

# 4. Role files must NOT duplicate core rule blocks (dedup guard)
CORE_HEADINGS = ["## Untrusted-input rule", "## REVIEWER ARCHITECTURE",
                 "## VERDICT CONTRACT", "## Entry format",
                 "## Reviewer-lane outage", "## The four seats",
                 "## Anti-anchoring", "## Watcher-driven intake",
                 "## THE INVARIANT: cadence, not authority"]
for role in ROLES:
    for p in (SKILLS / role).rglob("*.md"):
        t = text(p)
        for h in CORE_HEADINGS:
            check(h not in t,
                  f"core block '{h}' duplicated in {p.relative_to(ROOT)}")

# 4b. Every role's SKILL.md entrypoint must EXIST. Sections 3–6 validate skill
# files only if they are PRESENT — so deleting a whole role tree, or just its
# entrypoint, was green (round 15): a release false-accept for the one file
# each role cannot load without. Content gates cannot police an absent file;
# existence is its own gate.
for _role in ROLES + ["agent-core"]:
    check((SKILLS / _role / "SKILL.md").is_file(),
          f"skill entrypoint missing: "
          f"plugins/agent-protocol/skills/{_role}/SKILL.md — a role whose "
          "SKILL.md is gone cannot load, and no content gate below can red "
          "a file that is not there")

# 5. Version stamp coverage: every reference/skill file carries v2.8 — unless the
# tree has DECLARED it exempt with a reason (see 0; a byte-custody copy cannot be
# stamped without destroying the custody it exists to provide).
for p in SKILLS.rglob("*.md"):
    check(stamped(p), f"missing PROTOCOL v2.8 stamp: {p.relative_to(ROOT)}")

# 6. Role files that override the core must defer to it explicitly
for role in ROLES:
    for fname in ["channel-protocol.md"]:
        p = SKILLS / role / "references" / fname
        if p.is_file():
            check("channel-core.md" in text(p),
                  f"{p.relative_to(ROOT)} does not reference channel-core.md")
for role, fname in [("owner-engine-agent", "review-protocol.md"),
                    ("helper-builder-agent", "review-loop-protocol.md")]:
    p = SKILLS / role / "references" / fname
    if p.is_file():
        check("review-core.md" in text(p),
              f"{p.relative_to(ROOT)} does not reference review-core.md")

# 7. Verbatim disclaimer appears identically in core + session cards
DISCLAIMER = "Nothing in this entry is or carries the principal's authorization."
check(DISCLAIMER in text(CORE / "channel-core.md"),
      "canonical disclaimer missing from channel-core.md")

# 8. The standalone auth-log validator (used by conformance_check as the
# trusted copy) must byte-match the string new_project.py stamps into
# workspaces — two copies that drift would validate differently.
STANDALONE = ROOT / "tools" / "validate_auth_log.py"
NEW_PROJECT = ROOT / "tools" / "new_project.py"
if STANDALONE.is_file() and NEW_PROJECT.is_file():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_np", NEW_PROJECT)
    _np = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_np)
    embedded = getattr(_np, "AUTH_LOG_VALIDATOR", None)
    check(embedded is not None,
          "new_project.py no longer defines AUTH_LOG_VALIDATOR")
    if embedded is not None:
        check(embedded == text(STANDALONE),
              "tools/validate_auth_log.py has drifted from new_project.py's "
              "embedded AUTH_LOG_VALIDATOR (regenerate one from the other)")
else:
    check(STANDALONE.is_file(), "tools/validate_auth_log.py missing")

# 9. Transport profiles (repo-root transports/) get the same discipline the
# skill tree does: a v2.8 stamp, no duplicated core rule blocks, and the same
# banned-vocab sweep. They live outside SKILLS, so sections 3/4/5 miss them.
# EXISTENCE first (round 15): everything below is conditional on presence, so
# deleting transports/ outright — or either shipped profile — was green: an
# acceptance gate certifying a release that cannot say how its channel moves.
TRANSPORTS = ROOT / "transports"
for _rel in ("transports/local-fs.md", "transports/git-sync.md"):
    check((ROOT / _rel).is_file(),
          f"shipped transport missing: {_rel} — the conditional scans below "
          "cannot police an absent file, and silent absence is how a shipped "
          "tree quietly stops shipping")
# Round 16: the existence list above was treated as complete and was not —
# these are load-bearing shipped files every conditional scan quietly forgave
# the absence of. docs/CLOUD.md is the doc half of the shipped git-sync
# transport (README and every role START_SESSION point cold sessions at it),
# but it lives under docs/, so its EXISTENCE follows the docs_tree
# declaration like the other docs artifacts; the rest are unconditional.
for _rel in ("profiles/README.md", "profiles/MODELS.md",
             "tools/new_project.py"):
    check((ROOT / _rel).is_file(),
          f"load-bearing shipped file missing: {_rel} — a content gate cannot "
          "police an absent file, and silent absence is a release quietly "
          "narrowing what it ships")
if DOCS_TREE:
    check((ROOT / "docs" / "CLOUD.md").is_file(),
          "docs/CLOUD.md missing — the shipped git-sync transport is bound to "
          "this doc; a transport shipped in halves is not shipped")
if TRANSPORTS.is_dir():
    for p in TRANSPORTS.rglob("*.md"):
        t = text(p)
        check(stamped(p),
              f"missing PROTOCOL v2.8 stamp: {p.relative_to(ROOT)}")
        for h in CORE_HEADINGS:
            check(h not in t,
                  f"core block '{h}' duplicated in {p.relative_to(ROOT)}")
        for pat, why in BANNED:
            if re.search(pat, t):
                findings.append(f"{why} in {p.relative_to(ROOT)}")

# 10. Cloud is a SHIPPED transport now, not a roadmap item: the stale
# "git-synced channel repo variant is on the roadmap" phrasing (and close kin)
# must not survive anywhere in the doc surfaces we own — it points readers at a
# future that already arrived. History (CHANGELOG released sections) is exempt
# by not being scanned here.
ROADMAP_BAN = re.compile(
    r"git[- ]sync(?:ed)?\s+channel(?:[- ]repo)?\s+variant\s+is\s+on\s+the\s+roadmap",
    re.IGNORECASE)
roadmap_scan = list(SKILLS.rglob("*.md"))
for sub in ("transports", "docs", "profiles"):
    d = ROOT / sub
    if d.is_dir():
        roadmap_scan += list(d.rglob("*.md"))
if (ROOT / "README.md").is_file():
    roadmap_scan.append(ROOT / "README.md")
for p in roadmap_scan:
    if ROADMAP_BAN.search(text(p)):
        findings.append(
            f"stale cloud-as-roadmap phrasing in {p.relative_to(ROOT)} — "
            "git-sync ships now (transports/git-sync.md + docs/CLOUD.md)")

# 11. The consume-commit safety byte-phrase must appear VERBATIM in both the
# proxy-auth core (which owns the rule) and the git-sync transport (which binds
# it) — a drift between them would let one describe a retry the other forbids.
CONSUME_PHRASE = "must never carry a consume commit"
for rel in ("plugins/agent-protocol/skills/agent-core/references/proxy-auth-core.md",
            "transports/git-sync.md"):
    p = ROOT / rel
    if p.is_file():
        check(CONSUME_PHRASE in text(p),
              f"{rel} missing the consume-commit byte-phrase "
              f"'{CONSUME_PHRASE}'")

# 12. Baseline tripwire (NOT a semantic detector — say what it is).
# The role-neutral file-hygiene baseline lives in channel-core ONCE; role files
# carry shell-specific traps and a pointer, never the obligation. Section 4's
# dedup guard matches HEADINGS, so it cannot see a rule restated as prose — which
# is exactly how the encoding baseline ended up in three files, in three
# wordings. This guard is a TRIPWIRE over the baseline's load-bearing sentences:
# it catches a copy-paste (the common case) and it cannot catch a paraphrase.
# That limit is honest and stated; a reviewer, not this gate, is the control for
# a re-worded restatement.
CORE_ONLY_PHRASES = [
    "Every file here is written UTF-8 without BOM",
    "A green suite is not a shippable artifact",
    "a gate that never opens the bytes cannot certify them",
    "Gate every machine-read artifact",
    "never a BOM-swallowing",
    "enumerate what the gate excludes",
    "certifies that subtree and nothing else",
    "an unstated exclusion reads as coverage",
]


def flat(t: str) -> str:
    """Collapse whitespace and case AND strip markdown emphasis/code marks — a
    rule re-wrapped, re-cased, or dressed in `backticks`/**bold** is the same
    rule. (An earlier version normalized only whitespace+case, so ``UTF-8`` and
    **green** slipped the tripwire.)"""
    return re.sub(r"[*`_]", "", re.sub(r"\s+", " ", t)).lower()


# The obligation is role-neutral, so it must not be restated ANYWHERE outside
# the core that owns it — not only in the role subtrees, but in transports/ too
# (this release edited transports/local-fs.md precisely to stop it carrying the
# baseline). channel-core owns the phrases; everything else points at it.
core_text = flat(text(CORE / "channel-core.md"))
baseline_scan = [p for p in SKILLS.rglob("*.md") if p != CORE / "channel-core.md"]
baseline_scan += [p for p in (ROOT / "transports").rglob("*.md")] \
    if (ROOT / "transports").is_dir() else []
for phrase in CORE_ONLY_PHRASES:
    check(flat(phrase) in core_text,
          f"channel-core.md no longer states the baseline phrase '{phrase}' "
          "(section 12 guards it — move it back or update the guard)")
    for p in baseline_scan:
        check(flat(phrase) not in flat(text(p)),
              f"file restates the core baseline ('{phrase}') in "
              f"{p.relative_to(ROOT)} — reference channel-core instead")

# 13. Co-maintained twins fail as a PAIR — so gate them as a pair. "Remember to
# update the other copy" is not a control: a release nearly shipped a doc whose
# rendered twin still showed the old content, and the first version of THIS gate
# would have passed that very defect (it compared heading COUNTS and a title
# regex, and the drift was a table row).
# 13a. CREATOR-SEAT-BOOTSTRAP.md <-> .html — compare the identities of every
# structure a reader can see: section headings, bolded case-study titles, and
# catalog table rows. Counts are not identities; identities are what drift.
BOOT_MD = ROOT / "docs" / "CREATOR-SEAT-BOOTSTRAP.md"
BOOT_HTML = ROOT / "docs" / "CREATOR-SEAT-BOOTSTRAP.html"


def strip_md(s: str) -> str:
    """Normalize a fragment for comparison across the .md/.html renderings."""
    s = re.sub(r"<[^>]+>", "", s)                    # html tags (incl. attrs)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&#39;", "'").replace("&quot;", '"')
    s = re.sub(r"[*`_]", "", s)                      # md emphasis/code marks
    return re.sub(r"\s+", " ", s).strip().rstrip(".").lower()


def mask_code(md_src: str) -> str:
    """Blank out fenced/indented code so a code EXAMPLE containing literal `##`
    or `**x**` or `| … |` is not mistaken for a real heading/bold/row. (Codex
    r4: a matched md/html code sample produced three false drift findings.)"""
    md_src = re.sub(r"```.*?```", "", md_src, flags=re.S)      # fenced
    md_src = re.sub(r"^(?: {4}|\t).*$", "", md_src, flags=re.M)  # indented
    return md_src


def twin_drift(kind: str, md_set: set, html_set: set) -> None:
    for missing in sorted(md_set - html_set):
        findings.append(f"twin drift: {kind} '{missing}' is in "
                        "CREATOR-SEAT-BOOTSTRAP.md but not its .html twin")
    for extra in sorted(html_set - md_set):
        findings.append(f"twin drift: {kind} '{extra}' is in "
                        "CREATOR-SEAT-BOOTSTRAP.html but not its .md twin")


# Fail LOUD if either twin is missing — the pair invariant cannot be "skip the
# check when half the pair is gone" (Codex+Opus r4: deleting a twin passed).
if DOCS_TREE:
    check(BOOT_MD.is_file(), "CREATOR-SEAT-BOOTSTRAP.md missing — twin gate blind")
    check(BOOT_HTML.is_file(), "CREATOR-SEAT-BOOTSTRAP.html missing — twin gate blind")
else:
    # Existence is not asserted here — but HALF a pair still is. One twin present
    # and the other gone is drift or a deletion in ANY tree, and stays a finding.
    check(BOOT_MD.is_file() == BOOT_HTML.is_file(),
          "CREATOR-SEAT-BOOTSTRAP: one twin is present and the other is not — a "
          "pair cannot be half-carried, even in a tree that need not carry it")
if BOOT_MD.is_file() and BOOT_HTML.is_file():
    # SCOPE (enumerated, because an unstated exclusion reads as coverage): this
    # compares the SETS of section headings, every bold/strong run, and every
    # table row's leading cell — identities, not counts. It does NOT compare
    # prose paragraphs or deep HTML nesting; a re-worded body sentence is a
    # reviewer's catch. Attributes on <strong>/<tr>/<td>/<th> are tolerated;
    # code examples are masked so their literal markup is not read as structure.
    md, html = mask_code(text(BOOT_MD)), text(BOOT_HTML)
    twin_drift(
        "section",
        {strip_md(h) for h in re.findall(r"^#{2,4}\s+(.+)$", md, re.M)},
        {strip_md(h) for h in re.findall(r"<h[234][^>]*>(.*?)</h[234]>", html,
                                         re.S)})
    twin_drift(
        "bold text",
        {strip_md(c) for c in re.findall(r"\*\*(.+?)\*\*", md, re.S)},
        {strip_md(c) for c in re.findall(r"<strong[^>]*>(.*?)</strong>", html,
                                         re.S)})
    # Table rows: the SOP catalog is the "registry says nine, rendering shows
    # eight" defect class this repo names in review-core. Compare leading cells,
    # header cells (<th>) included; attributes on the tags are tolerated.
    twin_drift(
        "table row",
        {strip_md(r) for r in re.findall(r"^\|\s*([^|\s][^|]*?)\s*\|", md, re.M)
         if not set(strip_md(r)) <= {"-", ""}},
        {strip_md(r) for r in re.findall(
            r"<tr[^>]*>\s*<t[dh][^>]*>(.*?)</t[dh]>", html, re.S)})

# 13b. The amendment header has THREE copies — the guide, the PR template GitHub
# injects, and the proposal issue template. A field added to one and not the
# others means the surface where the rule actually bites keeps the weaker
# contract. (This is how `artifact set` / `omission search` were nearly shipped
# to CONTRIBUTING.md alone.) The field set is DERIVED from the copies, not
# hard-coded, so a NEW field drifts loudly too; labels are matched anchored, so
# deleting a label while the words survive in prose does not pass.
HEADER_COPIES = ["CONTRIBUTING.md",
                 ".github/PULL_REQUEST_TEMPLATE.md",
                 ".github/ISSUE_TEMPLATE/protocol_amendment.md"]
# `fingerprint` binds a diff that does not exist yet at proposal time — the one
# field legitimately absent from the issue template. Every other field is common.
HEADER_EXEMPT = {".github/ISSUE_TEMPLATE/protocol_amendment.md":
                 {"fingerprint", "problem"}}   # `problem` is a section heading
                                               # there, not a header label
# These MUST appear in every copy that does not explicitly exempt them — so
# dropping one from all copies still fails (a derived-union check alone cannot
# see a field that is nowhere). `fingerprint` is here because it carries the set
# digest; the issue template exempts it above.
REQUIRED_FIELDS = {"artifact set", "omission search", "files touched",
                   "principal-locked paths touched", "version impact",
                   "fingerprint"}
# Labels may carry digits and other word characters ("risk 2", "blast-radius");
# an earlier alphabet-only pattern let a digit-bearing single-copy label hide.
LABEL_RE = re.compile(r"^[\s\-*>]*\*{0,2}([A-Za-z][\w \-/]{2,40}?)\*{0,2}\s*:",
                      re.M)


def amendment_region(rel: str, t: str) -> str:
    """The header block itself — not the whole file, whose prose is full of
    colons that are not header fields."""
    if rel.endswith("protocol_amendment.md"):
        m = re.search(r"\*\*Blast radius\*\*(.*?)(?:\n\s*\n|\Z)", t, re.S)
    elif "PULL_REQUEST" in rel:
        m = re.search(r"AMENDMENT(.*?)(?:\n- \[|\Z)", t, re.S)
    else:
        m = re.search(r"```\n(AMENDMENT.*?)```", t, re.S)
    return m.group(1) if m else ""


# A PARTIAL set is drift in EVERY tree, and the comment that used to sit here
# claimed the field-parity loop below caught it. It did not: delete one of the
# three copies in a declared mirror and the two survivors agree with each other,
# so the gate went green on a set that had lost a third of itself. Absence of the
# whole set is declarable; absence of PART of it never is — same rule as the twin
# pair, and it took a reviewer to notice the claim had no code under it.
present = [rel for rel in HEADER_COPIES if (ROOT / rel).is_file()]
check(len(present) in (0, len(HEADER_COPIES)),
      f"amendment-header set is PARTIAL: {len(present)} of {len(HEADER_COPIES)} "
      f"copies present ({', '.join(present)}). The copies stand or fall together — "
      "a set cannot be half-carried, and the survivors agreeing with each other "
      "is not parity, it is a smaller quorum")

header_fields = {}
for rel in HEADER_COPIES:
    p = ROOT / rel
    if not p.is_file():
        if DOCS_TREE:
            findings.append(f"amendment-header copy missing: {rel}")
        continue
    region = amendment_region(rel, text(p))
    check(bool(region), f"amendment-header block not found in {rel} — the "
                        "parity gate cannot see it")
    header_fields[rel] = {m.strip().lower() for m in LABEL_RE.findall(region)}

if header_fields:
    union = set().union(*header_fields.values())
    for rel, fields in header_fields.items():
        exempt = HEADER_EXEMPT.get(rel, set())
        for field in sorted((union - fields) - exempt):
            findings.append(
                f"amendment-header drift: '{field}' is in another copy of the "
                f"header but missing from {rel} (the three copies carry the "
                "same fields; add it, or exempt it deliberately)")
        for field in sorted((REQUIRED_FIELDS - fields)
                            - HEADER_EXEMPT.get(rel, set())):
            findings.append(
                f"amendment-header drift: required field '{field}' missing "
                f"from {rel}")

# 14. Cross-file COUNT claims. "The registry advertises nine entries; the
# rendering shows eight" is the defect class review-core names — and the SOP
# registry states its catalog size in prose while the catalog itself lives in
# two other files. A number in prose is a claim about a file it cannot see.
# FAIL CLOSED: the sentence exists in SOP-REGISTRY, so if it stops matching (a
# numeral instead of a word, a count past the word map, a reworded sentence),
# that is a finding — not a silently skipped check that disarms the gate.
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
         "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
         "twenty": 20}
REGISTRY = ROOT / "docs" / "SOP-REGISTRY.md"
if DOCS_TREE:
    check(REGISTRY.is_file(), "SOP-REGISTRY.md missing — count gate (14) blind")
if REGISTRY.is_file() and BOOT_MD.is_file():
    m = re.search(r"catalog of \*{0,2}([\w]+)\*{0,2} numbered SOPs",
                  text(REGISTRY))
    # Row ids are numbers, sometimes split (2a/2b) — the CLAIM counts the
    # numbers, so count distinct numbers, not rows.
    numbered = {int(n) for n in
                re.findall(r"^\|\s*(\d+)[a-z]?\s*\|", text(BOOT_MD), re.M)}
    if m is None:
        findings.append(
            "count gate (14): SOP-REGISTRY.md no longer states its catalog size "
            "as 'catalog of <word> numbered SOPs' — the count claim is no longer "
            "machine-checkable against the bootstrap catalog (reword back, or "
            "update the gate). Not a silent skip.")
    else:
        word = m.group(1).lower()
        claim = WORDS.get(word, int(word) if word.isdigit() else None)
        check(claim is not None,
              f"count gate (14): unrecognized catalog-size word '{m.group(1)}' "
              "in SOP-REGISTRY.md (extend WORDS or use a numeral ≤ the map)")
        claimed = claim if claim is not None else -1
        check(claimed == len(numbered),
              f"count drift: SOP-REGISTRY.md advertises {claimed} numbered SOPs "
              f"but the catalog in CREATOR-SEAT-BOOTSTRAP.md defines "
              f"{len(numbered)} (13a keeps the .html twin in step with the .md)")

# Relaxations are printed on EVERY run, green or red, before the verdict. A gate
# that quietly runs a reduced set still prints the word "green", and that word is
# then a lie by omission — the reader has no way to tell full coverage from
# partial. If this tree is checking less than everything, it says so out loud.
if notes:
    print(f"MIRROR CHECK: {len(notes)} declared relaxation(s) in force "
          f"(from {DECL_PATH.name}):")
    for n in notes:
        print(f"  ~ {n}")

if findings:
    print(f"MIRROR CHECK: {len(findings)} finding(s)")
    for f in findings:
        print(f"  - {f}")
    sys.exit(1)
print("MIRROR CHECK: green" + (" (with declared relaxations, above)" if notes else ""))
