#!/usr/bin/env python3
"""Public-release hygiene gate: scan a release tree for private strings.

Before a workspace or repo is published to a public mirror it must be free of
deployment-specific identifiers — real names, home-directory paths, private
repo slugs, internal hostnames, and the like. What counts as "private" is a
property of *your* deployment, not of this protocol, so the pattern list is
intentionally NOT baked into this tool: you supply it with --patterns, and the
real list is meant to live OUTSIDE the repo (see examples/scrub_patterns.example.txt
for the shape and the copy-it-out-and-fill-it-in instructions).

Two guards run, cheapest first:

  1. Named-path guard (--private-path, repeatable): a fail-FAST check that a
     path known to be private (e.g. a profiles/private/ directory) has not been
     dragged into the release tree. If any listed path exists under <root> the
     scan is aborted with "RELEASE BLOCKED" before a single file is read.
  2. Pattern scan: every text file under <root> is matched line-by-line against
     the case-insensitive regexes in the patterns file.

Usage:
  python tools/release_scrub.py <root> --patterns <file> \\
      [--private-path <relpath> ...]

Exit 0 = clean; 1 = a blocked path or one or more pattern hits; 2 = usage error
(missing args, unreadable/empty patterns file, or a bad regex — the offending
line is reported). Hits print as `file:line: [pattern]` — the pattern text and
the line NUMBER only, never the matched text, so running the gate never echoes
the very secret it is guarding.
"""
import argparse
import re
import sys
from pathlib import Path

# Directories never worth scanning (VCS/build/tooling noise).
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".claude"}

# Extensions we treat as binary and skip outright (avoids mojibake matches and
# wasted reads on assets that cannot carry a private *string* anyway).
BINARY_EXTS = {".png", ".jpg", ".gif", ".ico", ".pyc", ".zip"}


def load_patterns(path: Path):
    """Compile the patterns file into a list of (label, regex).

    One case-insensitive regex per line; blank lines and lines whose first
    non-space character is '#' are ignored. Raises ValueError (caught by main
    and mapped to exit 2) on an unreadable/empty file or a bad regex, naming the
    offending line so the operator can fix it.
    """
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ValueError(f"cannot read patterns file {path}: {exc}")
    patterns = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            patterns.append((stripped, re.compile(stripped, re.IGNORECASE)))
        except re.error as exc:
            raise ValueError(
                f"bad regex in patterns file at line {lineno}: {stripped!r} ({exc})")
    if not patterns:
        raise ValueError(f"patterns file {path} has no usable patterns")
    return patterns


def check_private_paths(root: Path, private_paths):
    """Return the subset of private_paths that actually exist under root."""
    return [rel for rel in private_paths if (root / rel).exists()]


def iter_files(root: Path, exclude=None):
    """Yield scannable files under root, pruning SKIP_DIRS and binary assets.

    `exclude` is a set of resolved paths to skip — used to keep the patterns
    file (a control input, not release content) from being scanned against
    itself when it happens to live inside the release tree.
    """
    exclude = exclude or set()
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.resolve() in exclude:
            continue
        parts = set(p.relative_to(root).parts)
        if parts & SKIP_DIRS:
            continue
        if p.suffix.lower() in BINARY_EXTS:
            continue
        yield p


def scan(root: Path, patterns, exclude=None):
    """Return a list of (relpath, lineno, label) for every pattern hit."""
    hits = []
    for p in iter_files(root, exclude):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue  # unreadable file: skip rather than abort the whole scan
        rel = p.relative_to(root).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, rx in patterns:
                if rx.search(line):
                    hits.append((rel, lineno, label))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="release tree to scan")
    ap.add_argument("--patterns", required=True,
                    help="file of case-insensitive regexes (one per line; "
                         "'#' comments and blank lines ignored)")
    ap.add_argument("--private-path", action="append", default=[],
                    dest="private_paths", metavar="RELPATH",
                    help="path (relative to root) that must NOT exist in the "
                         "release tree; repeatable; checked before scanning")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"release_scrub: {root} is not a directory", file=sys.stderr)
        return 2

    patterns_path = Path(args.patterns)
    try:
        patterns = load_patterns(patterns_path)
    except ValueError as exc:
        print(f"release_scrub: {exc}", file=sys.stderr)
        return 2

    # Guard 1: named-path fail-fast, before any file is read.
    present = check_private_paths(root, args.private_paths)
    if present:
        print("RELEASE BLOCKED")
        print("private path(s) present in the release tree:")
        for rel in present:
            print(f"  {rel}")
        print("remove these from the release tree (or export the public subset "
              "without them) before publishing.")
        return 1

    # Guard 2: pattern scan. The patterns file itself is a control input, not
    # release content — never scan it against itself (it would self-match).
    exclude = {patterns_path.resolve()} if patterns_path.exists() else set()
    hits = scan(root, patterns, exclude)
    if hits:
        print(f"RELEASE BLOCKED: {len(hits)} private-string hit(s)")
        for rel, lineno, label in hits:
            print(f"{rel}:{lineno}: [{label}]")
        return 1

    print("release_scrub: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
