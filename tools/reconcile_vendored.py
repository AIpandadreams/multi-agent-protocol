#!/usr/bin/env python3
"""Reconcile the vendored in-workspace copies of `conformance_check.py`.

`new_project.py` writes a stamped copy of the conformance checker into every
workspace it stamps. Nothing ever reconciled those copies against the
protocol checkout, so they rot silently: a workspace can carry a checker that
predates the protocol version the workspace itself declares, and the stamp
gives no way to tell, because the stamp was written as a literal at stamp
time and never re-derived.

The cure is to make the stamp DERIVED FROM THE CONTENT it describes:

  * the supports-through version is read out of the vendored body's own
    `SUPPORTED_VERSIONS`, never written as a literal, so the stamp cannot
    disagree with the code it sits on top of;
  * a sha256 of the canonical body is recorded, so drift is detectable from
    inside the workspace, without the protocol checkout to hand. It is a
    hash of the DECODED, stamp-free text, so line endings do not enter it:
    this reports CODE drift, not byte drift, and a copy that differs from
    canonical only in line endings is deliberately reported OK. That is the
    right sensitivity for a file checked out on several platforms, but it
    means the number must not be read as a byte digest of the file;
  * this module owns the ONLY implementation of the stamp. `new_project.py`
    imports `vendor_text` from here rather than formatting its own, because
    a second implementation of a consistency stamp is the same drift defect
    one axis over -- writer and checker would be free to disagree.

A stamp edited by hand still fails, because the sha is taken over the body
with the stamp removed.

Exit codes:  0 all reconciled | 1 drift or missing found | 2 usage error
"""
import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "tools" / "conformance_check.py"

BEGIN = "# --- BEGIN VENDOR STAMP (generated; do not edit) ---"
END = "# --- END VENDOR STAMP ---"

SUPPORTED_RE = re.compile(r"^SUPPORTED_VERSIONS\s*=\s*\(([^)]*)\)", re.M)
SHA_RE = re.compile(r"^#\s*canonical-sha256:\s*([0-9a-f]{64})\s*$", re.M)

# The pre-derivation stamp: a single `# STAMPED COPY ...` line carrying a
# hardcoded version and the stamping date.
LEGACY_RE = re.compile(r"^# STAMPED COPY .*\n", re.M)


def body_of(text):
    """The file with any vendor stamp removed.

    Strips BOTH the current delimited block and the LEGACY single-line
    header. Stripping the legacy form matters: without it the old header's
    own date and version are hashed as if they were code, so two workspaces
    carrying byte-identical CODE report different bodies purely because they
    were stamped on different days. Stamp-free text is its own body.
    """
    if BEGIN in text:
        head, rest = text.split(BEGIN, 1)
        if END not in rest:
            raise ValueError("vendor stamp opened but never closed")
        _, tail = rest.split(END, 1)
        text = head + tail.lstrip("\n")
    return LEGACY_RE.sub("", text, count=1)


def sha_of(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def supported_through(text):
    """Highest version the BODY itself declares. Derived, never asserted."""
    m = SUPPORTED_RE.search(text)
    if not m:
        return None
    vers = re.findall(r'"([^"]+)"', m.group(1))
    return vers[-1] if vers else None


def make_stamp(canonical_text, when):
    """The vendor stamp for `canonical_text`, stamped on `when`.

    Every fact in it except the date is read out of `canonical_text`.
    """
    through = supported_through(canonical_text) or "unknown"
    return (
        "%s\n"
        "# multi-agent-protocol conformance_check.py, vendored %s\n"
        "# supports-through: %s   (read from this file's own"
        " SUPPORTED_VERSIONS)\n"
        "# canonical-sha256: %s\n"
        "#   (over the decoded, stamp-free text: code drift, not byte drift"
        " -- line endings do not enter it)\n"
        "# In-workspace HYGIENE SELF-CHECK (workspace-owned code). For a"
        " trust\n"
        "# decision run the protocol checkout's copy against this workspace.\n"
        "# Verify with: python tools/reconcile_vendored.py --check\n"
        "%s\n" % (BEGIN, when, through, sha_of(canonical_text), END)
    )


def vendor_text(canonical_text, when):
    """`canonical_text` with its stamp inserted below any shebang."""
    stamp = make_stamp(canonical_text, when)
    if canonical_text.startswith("#!"):
        nl = canonical_text.index("\n") + 1
        return canonical_text[:nl] + stamp + canonical_text[nl:]
    return stamp + canonical_text


def write_vendored(target, text):
    """Write `text` with its line endings UNTRANSLATED.

    `Path.write_text` applies platform newline translation, so on Windows it
    rewrites every line of a LF file as CRLF. That is not a cosmetic detail:
    re-vendoring into a workspace whose file is LF then produces a whole-file
    diff in someone else's repository, burying the handful of lines that
    actually changed. Measured here first-hand -- a re-vendor changed 142
    real lines and git reported 678 insertions and 777 deletions.

    The comparison side of this tool is deliberately EOL-insensitive, which
    is why it could not see its own conversion. Writing faithfully is the
    other half: the checker ignores line endings, and the writer does not
    invent them.
    """
    target.write_text(text, encoding="utf-8", newline="")


def inspect(target, canonical_text):
    """Return (status, detail) for one vendored copy."""
    if not target.is_file():
        return "MISSING", "no vendored copy present"
    text = target.read_text(encoding="utf-8")
    try:
        body = body_of(text)
    except ValueError as exc:
        return "DRIFT", str(exc)

    actual = sha_of(body)
    expected = sha_of(canonical_text)
    recorded = SHA_RE.search(text)

    if actual == expected:
        if recorded is None:
            return "DRIFT", "body current but carries NO stamp"
        if recorded.group(1) != expected:
            return "DRIFT", ("stamp says %s but body is %s -- stamp edited"
                             % (recorded.group(1)[:12], actual[:12]))
        return "OK", "body matches canonical (%s)" % actual[:12]

    detail = "body %s != canonical %s" % (actual[:12], expected[:12])
    through = supported_through(body)
    if through:
        detail += "; vendored copy supports only through %s" % through
    if recorded and recorded.group(1) == actual:
        detail += "; its stamp is self-consistent but STALE"
    return "DRIFT", detail


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("workspaces", nargs="*", type=Path,
                    help="workspace roots to reconcile")
    ap.add_argument("--check", action="store_true",
                    help="report only; never write (the default)")
    ap.add_argument("--fix", action="store_true",
                    help="re-vendor any copy that has drifted")
    ns = ap.parse_args(argv)

    if not ns.workspaces:
        ap.error("no workspaces given: pass one or more workspace roots")
    if ns.fix and ns.check:
        ap.error("--check and --fix are mutually exclusive")
    if not CANONICAL.is_file():
        print("canonical checker not found at %s" % CANONICAL, file=sys.stderr)
        return 2

    canonical_text = CANONICAL.read_text(encoding="utf-8")
    if BEGIN in canonical_text:
        print("canonical copy carries a vendor stamp; refusing",
              file=sys.stderr)
        return 2

    print("canonical: %s" % CANONICAL)
    print("  sha256 %s | supports through %s"
          % (sha_of(canonical_text)[:12], supported_through(canonical_text)))
    print()

    when = date.today().isoformat()
    bad = 0
    for ws in ns.workspaces:
        target = ws / "tools" / "conformance_check.py"
        status, detail = inspect(target, canonical_text)
        print("%-8s %-24s %s" % (status, ws.name, detail))
        if status == "OK":
            continue
        bad += 1
        if ns.fix and status == "DRIFT":
            write_vendored(target, vendor_text(canonical_text, when))
            again, d2 = inspect(target, canonical_text)
            print("         re-vendored -> %s (%s)" % (again, d2))
            if again == "OK":
                bad -= 1

    print()
    print("%d workspace(s) checked, %d needing attention"
          % (len(ns.workspaces), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
