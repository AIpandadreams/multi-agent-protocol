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

DRIFT IS NOT ONE THING, and `--fix` must not treat it as one. A copy can be
behind canonical -- ordinary rot, and re-vendoring is exactly right. Or it can
carry code the canonical does not have, because someone edited the vendored
file in place. Overwriting the second case DESTROYS work that exists nowhere
else, and the pre-fix tool could not tell them apart: both were "DRIFT", and
`--fix` rewrote both. Measured 2026-07-30 across the four stamped workspaces:
one of them defines module-level names the canonical has never
had, so this was a live hazard, not a hypothetical one.

So a copy that DEFINES module-level names the canonical has NEVER DEFINED is
reported DIVERGED, and `--fix` REFUSES it by name. Two things about that
sentence are load-bearing, and both were bought:

  * asked of the AST, not of a spelling. A name is not a mechanism, and a
    grep for the names that happen to be there today would go blind the
    moment someone adds another;
  * asked of the canonical's WHOLE HISTORY, not its current shape. The first
    version compared against today's canonical, and it was falsified within
    the hour: a cut landed that DELETED a module-level name, and three
    untouched workspaces immediately read as local work because they still
    defined it. `canonical_ever_defined` explains that in full. Being merely
    OLD is not divergence, and a subset test alone does not deliver that --
    the deletion direction is what breaks it.

Exit codes:  0 all reconciled | 1 drift, divergence or missing | 2 usage error
"""
import argparse
import ast
import hashlib
import re
import subprocess
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


def defined_names(text):
    """Module-level names `text` DEFINES -- functions, classes, assignments.

    Module level only, deliberately. A name bound inside a function body is an
    implementation detail of a definition already counted, and counting it
    would make an ordinary refactor read as divergence.

    Returns None when the text does not parse. An unparseable copy is a defect
    in its own right, but it is not evidence of local work, and guessing
    either way would be worse than saying so.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    out = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            out.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target,
                                                            ast.Name):
            out.add(node.target.id)
    return out


def canonical_ever_defined(root=None, relpath="tools/conformance_check.py"):
    """Every module-level name the canonical has EVER defined, from git.

    ASKED OF HISTORY, AND THE REASON IS A FALSE POSITIVE I MEASURED. The first
    version of this compared the copy against TODAY's canonical, which is wrong
    the moment the canonical DELETES a name: an untouched stale copy still
    defines it, and reads as local work. That is not hypothetical -- the
    role-vocabulary cut landed while this unit was being written, it removed
    `ROLE_LOCK_RE`, and three pristine workspaces immediately reported
    DIVERGED. A predicate that depends on the canonical's shape TODAY decays
    with every landing.

    Returns None when history cannot be read. Callers must disclose that,
    because without history the predicate is the over-firing one again.
    """
    root = Path(root) if root else ROOT
    # A SHALLOW CHECKOUT HAS HISTORY, JUST NOT ENOUGH, and that is a different
    # answer from "no history" -- which is the only one the guard below can
    # give. Measured, not supposed: CI ran `actions/checkout@v4` at its default
    # `fetch-depth: 1`, so `git log` SUCCEEDED over a one-commit history and the
    # union equalled the CURRENT name set. Every name the canonical had ever
    # deleted was invisible, `ROLE_LOCK_RE` among them, and the caller was told
    # nothing. The predicate silently reverts to the over-firing one this
    # function exists to replace, while looking like it worked.
    #
    # An instrument must refuse a question its input cannot answer. Returning
    # None here routes a truncated corpus to the SAME disclosure path as an
    # unreadable one, because for this predicate they have the same standing.
    shallow = subprocess.run(["git", "-C", str(root), "rev-parse",
                              "--is-shallow-repository"],
                             capture_output=True, text=True)
    if shallow.returncode == 0 and shallow.stdout.strip() == "true":
        return None
    log = subprocess.run(["git", "-C", str(root), "log", "--format=%H", "--",
                          relpath], capture_output=True, text=True)
    if log.returncode != 0 or not log.stdout.strip():
        return None
    revs = log.stdout.split()
    spec = "".join("%s:%s\n" % (r, relpath) for r in revs)
    batch = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"],
                           input=spec.encode("utf-8"), capture_output=True)
    if batch.returncode != 0:
        return None

    ever, buf, seen = set(), batch.stdout, 0
    while seen < len(buf):
        nl = buf.index(b"\n", seen)
        header = buf[seen:nl].split()
        seen = nl + 1
        if len(header) != 3:            # "<oid> missing" -- skip this rev
            continue
        size = int(header[2])
        names = defined_names(buf[seen:seen + size].decode("utf-8", "replace"))
        seen += size + 1                # payload plus its trailing newline
        if names:
            ever |= names
    return ever or None


def local_additions(body, canonical_text, ever=None):
    """Names the vendored BODY defines that the canonical has never defined.

    `ever` is the historical union from `canonical_ever_defined`. Without it
    the comparison falls back to today's canonical alone, which over-fires on
    deletions -- so callers that pass None must say so in what they print.

    Empty when either side fails to parse -- see `defined_names`.
    """
    theirs = defined_names(body)
    ours = defined_names(canonical_text)
    if theirs is None or ours is None:
        return []
    known = ours | (ever or set())
    return sorted(theirs - known)


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


def inspect(target, canonical_text, ever=None):
    """Return (status, detail) for one vendored copy.

    `ever` is the historical union from `canonical_ever_defined`; passing None
    means the divergence question is asked against today's canonical alone,
    and the detail line says so rather than letting the caller assume.
    """
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

    # Asked AFTER drift is established, because a copy that matches canonical
    # byte-for-code cannot have local additions, and BEFORE returning, because
    # the caller decides what `--fix` may touch from the status alone.
    added = local_additions(body, canonical_text, ever)
    if added:
        note = "" if ever else (" [NO HISTORY AVAILABLE -- compared against"
                                " today's canonical only, so a name the"
                                " canonical DELETED reads as local work]")
        return "DIVERGED", (detail + "; defines %d name(s) the canonical has"
                            " never defined: %s%s"
                            % (len(added), ", ".join(added), note))
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

    ever = canonical_ever_defined()
    print("canonical: %s" % CANONICAL)
    print("  sha256 %s | supports through %s"
          % (sha_of(canonical_text)[:12], supported_through(canonical_text)))
    if ever:
        print("  divergence judged against %d name(s) the canonical has ever"
              " defined, read from git history" % len(ever))
    else:
        print("  WITHOUT git history: divergence is judged against today's"
              " canonical alone and may over-report")
    print()

    when = date.today().isoformat()
    bad = 0
    for ws in ns.workspaces:
        target = ws / "tools" / "conformance_check.py"
        status, detail = inspect(target, canonical_text, ever)
        print("%-8s %-24s %s" % (status, ws.name, detail))
        if status == "OK":
            continue
        bad += 1
        if ns.fix and status == "DIVERGED":
            # Stated, not implied. A refusal that happens only because the
            # status string fails an equality test elsewhere is a protection
            # nobody can find, and the next edit to this loop removes it
            # without noticing.
            print("         REFUSING --fix: re-vendoring would DESTROY the "
                  "names listed above, which exist only in this copy. "
                  "Reconcile them into the canonical first.")
            continue
        if ns.fix and status == "DRIFT":
            write_vendored(target, vendor_text(canonical_text, when))
            again, d2 = inspect(target, canonical_text, ever)
            print("         re-vendored -> %s (%s)" % (again, d2))
            if again == "OK":
                bad -= 1

    print()
    print("%d workspace(s) checked, %d needing attention"
          % (len(ns.workspaces), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
