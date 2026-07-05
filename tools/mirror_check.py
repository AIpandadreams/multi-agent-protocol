#!/usr/bin/env python3
"""Mirror-consistency CI for the agent-protocol skills (PROTOCOL v2.5).

Guards against the drift class that produced the original v2 defects:
role skills contradicting each other or the agent-core normative files.
Run from the repo root: python tools/mirror_check.py
Exit 0 = green; nonzero = findings printed.
"""
import re
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
for name in ["channel-core.md", "review-core.md", "binding-slots.md",
             "memory-discipline.md", "self-improvement-protocol.md",
             "proxy-auth-core.md"]:
    check((CORE / name).is_file(), f"agent-core missing {name}")

# 2. No BOM / mojibake anywhere in the skill tree
# (ops-gotchas.md documents the mojibake strings as examples — only count
# occurrences outside backticked example text there)
for p in SKILLS.rglob("*.md"):
    raw = p.read_bytes()
    check(not raw.startswith(b"\xef\xbb\xbf"), f"BOM in {p.relative_to(ROOT)}")
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
                 "## VERDICT CONTRACT", "## Entry format"]
for role in ROLES:
    for p in (SKILLS / role).rglob("*.md"):
        t = text(p)
        for h in CORE_HEADINGS:
            check(h not in t,
                  f"core block '{h}' duplicated in {p.relative_to(ROOT)}")

# 5. Version stamp coverage: every reference/skill file carries v2.5
for p in SKILLS.rglob("*.md"):
    check("v2.5" in text(p), f"missing PROTOCOL v2.5 stamp: {p.relative_to(ROOT)}")

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

if findings:
    print(f"MIRROR CHECK: {len(findings)} finding(s)")
    for f in findings:
        print(f"  - {f}")
    sys.exit(1)
print("MIRROR CHECK: green")
