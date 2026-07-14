#!/usr/bin/env python3
"""Mirror-consistency CI for the agent-protocol skills (PROTOCOL v2.6).

Guards against the drift class that produced the original v2 defects:
role skills contradicting each other or the agent-core normative files.
Run from the repo root: python tools/mirror_check.py
Exit 0 = green; nonzero = findings printed.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "plugins" / "agent-protocol" / "skills"
CORE = SKILLS / "agent-core" / "references"
ROLES = ["owner-engine-agent", "helper-builder-agent", "orchestrator-agent"]

findings = []


def text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def check(cond: bool, msg: str) -> None:
    if not cond:
        findings.append(msg)


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
# UTF-8, UTF-16 LE/BE, UTF-32 BE/LE. UTF-32 LE (FF FE 00 00) shares UTF-16 LE's
# 2-byte prefix, so it is listed FIRST and matched before plain UTF-16 LE — the
# label in the finding is then accurate rather than "FF FE".
BOMS = [(b"\x00\x00\xfe\xff", "UTF-32 BE"), (b"\xff\xfe\x00\x00", "UTF-32 LE"),
        (b"\xef\xbb\xbf", "UTF-8"), (b"\xff\xfe", "UTF-16 LE"),
        (b"\xfe\xff", "UTF-16 BE")]


def tracked_files():
    """Paths git tracks — authoritative for 'published'. Returns None (NOT an
    empty set) when git is unavailable, so the caller can tell 'tracks nothing'
    from 'could not ask' and refuse to certify reduced scope silently."""
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=str(ROOT),
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return {ROOT / p for p in out.split("\0") if p}


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
        for p in sorted(ROOT.rglob("*")):
            if ".git" not in p.relative_to(ROOT).parts and p.is_file():
                yield p
        return
    seen = set()
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts) and p not in tracked:
            continue
        if p.is_file():
            seen.add(p)
            yield p
    for p in sorted(tracked - seen):          # tracked but not walked
        if p.is_file():
            yield p


for p in repo_files():
    try:
        with p.open("rb") as fh:
            head = fh.read(4)
    except OSError as exc:                     # unreadable/locked → a finding,
        findings.append(f"unreadable file {p.relative_to(ROOT)}: {exc}")
        continue                               # never a crashed gate
    for sig, label in BOMS:
        if head.startswith(sig):
            findings.append(f"BOM ({label}, {sig.hex(' ').upper()}) in "
                            f"{p.relative_to(ROOT)}")
            break

# 2b. No mojibake in the skill tree
# (ops-gotchas.md documents the mojibake strings as examples — only count
# occurrences outside backticked example text there)
for p in SKILLS.rglob("*.md"):
    t = text(p)
    for marker in ("â€", "Â§"):
        hits = [m for m in re.finditer(re.escape(marker), t)]
        if p.name == "ops-gotchas.md":
            hits = [m for m in hits
                    if not re.search(r"`[^`]*$", t[max(0, m.start() - 40):m.start()])]
        check(not hits, f"mojibake in {p.relative_to(ROOT)}")

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

# 5. Version stamp coverage: every reference/skill file carries v2.6
for p in SKILLS.rglob("*.md"):
    check("v2.6" in text(p), f"missing PROTOCOL v2.6 stamp: {p.relative_to(ROOT)}")

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
# skill tree does: a v2.6 stamp, no duplicated core rule blocks, and the same
# banned-vocab sweep. They live outside SKILLS, so sections 3/4/5 miss them.
TRANSPORTS = ROOT / "transports"
if TRANSPORTS.is_dir():
    for p in TRANSPORTS.rglob("*.md"):
        t = text(p)
        check("v2.6" in t,
              f"missing PROTOCOL v2.6 stamp: {p.relative_to(ROOT)}")
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
check(BOOT_MD.is_file(), "CREATOR-SEAT-BOOTSTRAP.md missing — twin gate blind")
check(BOOT_HTML.is_file(), "CREATOR-SEAT-BOOTSTRAP.html missing — twin gate blind")
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


header_fields = {}
for rel in HEADER_COPIES:
    p = ROOT / rel
    if not p.is_file():
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

if findings:
    print(f"MIRROR CHECK: {len(findings)} finding(s)")
    for f in findings:
        print(f"  - {f}")
    sys.exit(1)
print("MIRROR CHECK: green")
