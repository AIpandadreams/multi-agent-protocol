#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sweep commit messages for the doubled-space signature of a backtick eaten by command
substitution — the damage class the fleet line asked every seat to check for.

⛔ A DOUBLED SPACE IS A CANDIDATE, NOT A VERDICT. Aligned tables, ASCII art and sentence
   spacing all produce them legitimately. This prints the line for a human to read; it never
   pronounces. Two of the author's own commits flagged here are deliberate column alignment —
   that is the argument for the posture, not an argument against the tool.

⭐ THE STRONGER SIGNAL IS A STRANDED ARTICLE. `with an  vacuity guard` is damage: `an` requires
   a following vowel-sound word and there is none. A doubled space between two ordinary words
   usually is not. The tool marks that case; it still does not pronounce.

Reads the RAW COMMIT OBJECT (`git cat-file commit`) so nothing is decoded through a shell that
could hide the very bytes under test — the same reason CR counts must come from raw bytes.

Usage:
    python sweep_backtick.py [--repo PATH] [--count N] [SHA ...]

    --repo   repository to sweep (default: the current working directory)
    --count  how many commits back from HEAD to sweep (default 30)
    SHA      extra revisions to include explicitly, e.g. ones you already suspect

⚠ The sweep's REACH is `--count` commits. It is not a repository-wide statement and must not be
  reported as one: say how many commits were read.
"""
import argparse
import re
import subprocess
import sys

# C1 sink cure (batch standardization of the house cure adopted
# by an orchestrator ruling). Under a cp1252 console a cp1252-unencodable glyph in an
# emit raises UnicodeEncodeError on stdout and takes the run down mid-report;
# stderr is immune (backslashreplace). This mints no defect claim about this
# file -- it is prophylactic. Exercised two-sided by tools/sink_cure_controls.py.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass  # non-reconfigurable stream (e.g. a test harness wrapper)

# An article that must be followed by a word, with the word missing.
STRANDED_RE = re.compile(r"\b(a|an|the|to|of|in|for|with|and|or|is|was)\s\s+\S")


def git(repo, *args):
    p = subprocess.Popen(["git", "-C", repo] + list(args),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, _err = p.communicate()
    return out.decode("utf-8", errors="replace")


def message_of(raw):
    i = raw.find("\n\n")
    return raw[i + 2:] if i >= 0 else ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--count", type=int, default=30)
    ap.add_argument("shas", nargs="*")
    a = ap.parse_args(argv)

    # ⛔ RESOLVE EVERY REVISION TO ITS FULL SHA BEFORE DEDUPING. A short sha given on the
    #    command line and the full sha from the log are two KEYS FOR ONE COMMIT, and the
    #    duplicate inflates the candidate count — a wrong number with a real cause.
    #    ⭐ A PATH IS NOT AN IDENTITY WHEN THE KEY IS A STRING, in its git spelling.
    shas = []
    for s in list(a.shas) + git(a.repo, "log", "-%d" % a.count, "--format=%H").split():
        full = git(a.repo, "rev-parse", s).strip() or s
        if full not in shas:
            shas.append(full)

    flagged = 0
    stranded = 0
    for sha in shas:
        msg = message_of(git(a.repo, "cat-file", "commit", sha))
        if not msg:
            continue
        for n, line in enumerate(msg.split("\n"), 1):
            body = line.rstrip().lstrip()
            m = re.search(r"\S(  )\S", body)
            if not m:
                continue
            flagged += 1
            hard = bool(STRANDED_RE.search(body))
            if hard:
                stranded += 1
            print("%s  line %d%s" % (sha[:9], n, "   <- STRANDED WORD" if hard else ""))
            print("    %s" % body[:140])
            print("    %s^^ doubled space at col %d" % (" " * min(m.start(1), 130), m.start(1)))

    print("\nread: %d commit(s) in %s" % (len(shas), a.repo))
    print("candidates: %d   of which a preceding word is left stranded: %d" % (flagged, stranded))
    print("⛔ CANDIDATES, NOT FINDINGS — a doubled space has legitimate causes. Read the line.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
