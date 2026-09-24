"""lane_entry_width.py -- derive a channel entry's own byte width from git history.

WHY THIS EXISTS (T329 -> T330 -> T331, orch headless tick lineage).

An entry that publishes its own byte width is a fixed point: the number measures
the object it is written inside, so it is wrong the instant it is written and
there is no "measure later" -- the only commit that can frame an entry's width
is the commit that lands it, which does not exist at composition time and dies
with the clone if the push fails. T330's resolution INVERTS the duty: the width
is derivable by ANY READER from the lane's own history, so the author's duty is
OMISSION and the reader's instrument is this file.

    width(E) = size(C:lane) - size(C^:lane)   where C = the commit that
                                              introduced E's heading

T331 IS THE REASON THIS IS CODE AND NOT PROSE. T330 shipped as a prose recipe.
The recipe's locate step says "find the oldest commit still containing the
entry". Substituting the BARE ID -- the obvious shorter needle -- silently
returns the PREDECESSOR's width, because every entry in this lineage carries a
`. next <id> .` footer pointer, so the id's bytes first appear one entry EARLY.
The wrong answer is therefore a member of the set of the lineage's own TRUE
values: it agrees with the published record, and agreement is the predicted
symptom of the defect rather than evidence against it. Three independent hands
certified the recipe and all three ran the correct needle BY HABIT; one of them
never ran the locate step at all and consumed the author's answer for it.

    => The needle is the HEADING LINE, compared as BYTES. Both halves are
       load-bearing and both are enforced below:
         - heading, not bare id      -> _locate() takes the needle from _heading()
         - bytes, not str            -> every blob is read with `git show` binary;
                                        nothing is decoded. Heading separators in
                                        this lineage are U+00B7 and U+2192, which
                                        a cp1252 text walk cannot even represent,
                                        so a text-mode implementation returns
                                        "not found" at rc=0.

REFUSAL BEATS A PLAUSIBLE NUMBER. Every precondition T330 stated in prose is a
hard check here: the needle must hit exactly once, the entry must have landed,
and a commit that introduces more than one entry yields a SUM -- reported as
such, never as the entry's width.

Runtime strings are ASCII-only (shared tools convention -- the launcher hands
python no encoding and every guard fires by construction otherwise).

Run:  python tools/lane_entry_width.py --lane channel/orch_to_creator_2026-08-16.md --entry ORCH-T144
Controls: python tools/tests/lane_entry_width_controls.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys

RC_OK = 0
RC_PRECONDITION = 1   # width computed but a stated precondition does not hold
RC_REFUSED = 3        # cannot answer; no number is printed


class Refused(Exception):
    pass


def _git(repo: str, args: list[str]) -> bytes:
    """Run git, return raw stdout bytes. Never decodes."""
    p = subprocess.run(["git", "-C", repo] + args,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise Refused("git %s failed rc=%d: %s"
                      % (" ".join(args[:2]), p.returncode,
                         p.stderr.decode("utf-8", "replace").strip()[:200]))
    return p.stdout


def _blob(repo: str, rev: str, path: str) -> bytes | None:
    """Lane bytes at rev, or None if the lane does not exist there."""
    try:
        return _git(repo, ["show", "%s:%s" % (rev, path)])
    except Refused:
        return None


def _headings(blob: bytes) -> list[bytes]:
    """Every entry heading line in the lane, as raw bytes, newline stripped.

    Entry grain is '## ' at column 0. Deeper levels are BODY sub-headings and a
    seat opens sub-sections by citing another entry's id -- admitting '###' turns
    a citation into an entry and under-reports the lane tail (T106).
    """
    out = []
    for line in blob.split(b"\n"):
        if line.startswith(b"## "):
            out.append(line.rstrip(b"\r"))
    return out


_STAMP = re.compile(rb"20\d\d-\d\d-\d\d")


def _in_id_field(heading: bytes, needle: bytes) -> bool:
    """Does `needle` sit in the heading's ID FIELD rather than in its prose?

    T331's cure (bare id -> heading line) has a SECOND ambiguity layer under it,
    found by this tool's own fixture and not by any hand: an entry id also
    appears inside LATER entries' heading lines, as a back-reference ("the
    reader-side grade of ORCH-T143 s3 is ACCEPTED ..."). So "the heading line
    containing the id" is NOT unique on a live lane -- ORCH-T143 matches three
    headings and ORCH-T144 matches two.

    The discriminator is structural, not positional: these headings are built
    id-field first, then a date stamp, then prose. The entry's OWN heading is
    the one where the id appears BEFORE the heading's first date stamp; every
    back-reference lands after it. Positional rules over this bank have been
    falsified repeatedly (T111/T114/T133), so this keys on the stamp -- a
    boundary the heading itself carries -- and never on file order.
    """
    m = _STAMP.search(heading)
    cut = m.start() if m else len(heading)
    return heading.find(needle) != -1 and heading.find(needle) < cut


def _heading(blob: bytes, entry_id: str) -> bytes:
    """The ONE heading line whose ID FIELD is entry_id. Refuses on 0 or 2+."""
    needle = entry_id.encode("utf-8")
    all_hits = [h for h in _headings(blob) if needle in h]
    if not all_hits:
        raise Refused(
            "entry %s has no '## ' heading at this rev -- it has not landed, or "
            "the id is wrong. NOT reporting a width." % entry_id)
    hits = [h for h in all_hits if _in_id_field(h, needle)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise Refused(
            "entry %s appears in %d heading(s) but in none of their ID FIELDS "
            "-- every occurrence is a back-reference, so the entry itself has "
            "not landed on this lane. NOT reporting a width." % (
                entry_id, len(all_hits)))
    raise Refused(
        "entry %s matches %d heading ID FIELDS; the needle is ambiguous and any "
        "width would be a guess. Heads: %s"
        % (entry_id, len(hits),
           " | ".join(h.decode("utf-8", "replace")[:60] for h in hits)))


def _touching_commits(repo: str, rev: str, path: str) -> list[str]:
    """Commits touching the lane, newest first."""
    raw = _git(repo, ["rev-list", rev, "--", path])
    return [c for c in raw.decode("ascii", "replace").split() if c]


def _locate(repo: str, path: str, commits: list[str], needle: bytes) -> str:
    """OLDEST commit in `commits` whose lane blob contains `needle`.

    `commits` is newest-first, so the introducing commit is the LAST hit.
    Exposed separately so the controls can drive it with a deliberately wrong
    needle and demonstrate the T331 trap instead of merely asserting it.
    """
    found = None
    for c in commits:
        blob = _blob(repo, c, path)
        if blob is not None and needle in blob:
            found = c
    if found is None:
        raise Refused("needle occurs in no revision of %s" % path)
    return found


def width(repo: str, path: str, entry_id: str, rev: str = "HEAD") -> dict:
    tip = _blob(repo, rev, path)
    if tip is None:
        raise Refused("lane %s does not exist at %s" % (path, rev))

    needle = _heading(tip, entry_id)
    commits = _touching_commits(repo, rev, path)
    if not commits:
        raise Refused("no commit touches %s at %s" % (path, rev))

    c = _locate(repo, path, commits, needle)
    cur = _blob(repo, c, path)
    parents = _git(repo, ["rev-list", "--parents", "-n", "1", c]
                   ).decode("ascii", "replace").split()
    prev = _blob(repo, parents[1], path) if len(parents) > 1 else None
    prev_bytes = len(prev) if prev is not None else 0

    added = [h for h in _headings(cur)
             if prev is None or h not in _headings(prev)]

    notes = []
    rc = RC_OK
    if len(added) != 1:
        rc = RC_PRECONDITION
        notes.append(
            "SUM, not a width: commit %s introduced %d entries (%s). T330's "
            "arithmetic is exact only where the landing commit touches the lane "
            "once." % (c[:9], len(added),
                       ", ".join(h.decode("utf-8", "replace")[:40]
                                 for h in added[:4])))
    if prev is not None and cur.count(b"\r") != prev.count(b"\r"):
        rc = RC_PRECONDITION
        notes.append(
            "RE-ENCODING: CR count moved %d -> %d across this commit, so the "
            "delta mixes the entry with a line-ending rewrite."
            % (prev.count(b"\r"), cur.count(b"\r")))
    if prev is None:
        notes.append("commit %s has no parent blob for this lane; width is the "
                     "whole file at that commit." % c[:9])

    return {
        "entry": entry_id,
        "lane": path,
        "introducing_commit": c,
        "prev_bytes": prev_bytes,
        "cur_bytes": len(cur),
        "width": len(cur) - prev_bytes,
        "heading": needle.decode("utf-8", "replace"),
        "commits_scanned": len(commits),
        "notes": notes,
        "rc": rc,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Derive a channel entry's byte width from the lane's git "
                    "history. Needle = the heading line, compared as bytes.")
    ap.add_argument("--lane", required=True, help="repo-relative lane path")
    ap.add_argument("--entry", required=True, help="entry id, e.g. ORCH-T144")
    ap.add_argument("--repo", default=".", help="repo root (default: .)")
    ap.add_argument("--rev", default="HEAD", help="tip to resolve at")
    a = ap.parse_args(argv)

    try:
        r = width(a.repo, a.lane, a.entry, a.rev)
    except Refused as e:
        print("REFUSED: %s" % e)
        return RC_REFUSED

    print("entry              %s" % r["entry"])
    print("lane               %s" % r["lane"])
    print("introducing commit %s  (of %d commits touching the lane)"
          % (r["introducing_commit"][:9], r["commits_scanned"]))
    print("lane bytes         %d -> %d" % (r["prev_bytes"], r["cur_bytes"]))
    print("WIDTH              %d B" % r["width"])
    for n in r["notes"]:
        print("  ! %s" % n)
    if r["rc"] == RC_OK:
        print("  preconditions hold: single-entry commit, no re-encoding.")
    return r["rc"]


if __name__ == "__main__":
    sys.exit(main())
