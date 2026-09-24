# -*- coding: utf-8 -*-
"""TICK_LAND_ORPHANED — the record a killed land cannot write for itself.

Commissioned by an orchestrator ruling, widened by a later one.

THE HOLE. tick_land writes TICK_LAND_FAILED.txt only on its OWN terminal-failure
path. A land killed mid-decision — the seat backgrounded it and then ended its
turn, which in `claude -p` terminates the session — writes nothing at all. So
the marker's ABSENCE cannot distinguish a clean land from a killed one, and the
seat is told elsewhere to act on that marker's presence. A killed process
cannot write its own obituary; the record has to come from something that
SURVIVES the kill. The launcher does. That is the whole design.

THE DISCRIMINATOR, and why it is not "no entry landed". A fire with nothing to
say legitimately lands nothing — the payload says so. Treating silence as an
orphan would cry wolf on every quiet hour. What separates the two is EVIDENCE
THAT A LAND WAS COMPOSED, and that evidence survives a kill:

  * body files (`*_BODY.md` / `*_MSG.txt` / `*_DELTA.md`) sitting in the clone
    root — the seat writes them BEFORE invoking tick_land, and tick_land leaves
    them on disk rather than cleaning up; and/or
  * tracked-file dirt in the clone — a delta prepended into the bank whose
    commit never happened. That is fire 317's exact signature, and it is the
    shape that goes on to eat LATER slots, because the next fire's sync refuses
    on dirt it will not reset away.

Composed + no terminal marker + nothing published = ORPHANED. All THREE
legs are evaluated (the publication leg was documented here but ABSENT
from the code until 2026-08-27, which made a SUCCESSFUL land
indistinguishable from an orphan and produced a false record). Each leg is
reported, so a reader can see WHICH evidence fired rather than trusting a
verdict [[stated-reason-must-discriminate]].

THE WIDENING (the later ruling). One killed fire cost three slots: its own, plus
the 03:13 and 04:13 slots that launched and died on the dirt it left. A record
that books only the killed fire makes the durability instrument's blind spot
permanent, because the ladder that prices lost slots cannot tell "never
launched" from "launched and died" without evidence the clone does not hold.
So the second mode books THE DARKENED SPAN: written by the rescuing hand at
CLEARANCE time, when both ends of the window are finally known, naming every
slot inside it and each slot's resolution state. It is a separate mode because
it has a different writer and a different moment — not because it is a
different subject.

Both modes append to the SAME ledger with the same discipline as
`_tickfails_publish`: byte-append (never rewrite), `git add` first because a
pathspec commit cannot reach an untracked file, pathspec commit, push once, and
never recurse into the act that just failed. Containment is the NEXT fire's
probe, not this run's exit code.
"""
import argparse
import io
import os
import subprocess
import sys
import traceback
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

BODY_SUFFIXES = ("_BODY.md", "_MSG.txt", "_DELTA.md")


def log(msg):
    print(msg)


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo)] + list(args),
                          capture_output=True, text=True)


SAMPLE = 5


def _fire_start_from_log(log_path):
    """This fire's start, from the launcher's own `==== ... ====` line.

    The launcher writes that line as its first act, so the LAST one in the file
    is this fire's start. Returns None on any failure -- a start that cannot be
    read must leave the leg UNKNOWN, never default to a window that would make
    the leg answer anyway.
    """
    try:
        import re
        pat = re.compile(r"^==== .*? tick \w+ (\d+/\d+/\d+)\s+(\d+:\d+:\d+)")
        found = None
        with io.open(log_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = pat.match(line)
                if m:
                    found = m
        if not found:
            return None
        return datetime.strptime(" ".join(found.groups()),
                                 "%m/%d/%Y %H:%M:%S").timestamp()
    except Exception:
        return None


PROBE_MIN = 40
PROBES = 3


def _published_leg(repo, fresh):
    """Did this fire's composed body reach the COMMITTED tree?

    The third conjunct of this tool's stated contract, absent from the code
    until 2026-08-27 and the direct cause of a false ORPHANED record: with
    only `composed` and `no marker`, a land that SUCCEEDED is indistinguishable
    from one that never happened, because TICK_LAND_FAILED.txt is written only
    on the terminal-failure path.

    Returns a leg triple. True = found, False = absent, None = cannot say.
    """
    bodies = [n for n in fresh if n.endswith("_BODY.md")]
    if not bodies:
        return ("published", None,
                "no *_BODY.md composed this fire - nothing to look for. The "
                "leg cannot answer, which is not the same as answering no.")

    name = sorted(bodies)[0]
    try:
        text = io.open(os.path.join(repo, name), encoding="utf-8",
                       errors="replace").read()
    except OSError as e:
        return ("published", None, "%s unreadable: %s" % (name, e))

    # Placeholder-free lines only: the composed body spells {{ID}}/{{STAMP}}
    # and the published entry spells a real id, so the heading can never match.
    cand = [l.strip() for l in text.splitlines()
            if len(l.strip()) >= PROBE_MIN and "{{" not in l]
    cand.sort(key=len, reverse=True)
    probes = cand[:PROBES]
    if not probes:
        return ("published", None,
                "%s carries no placeholder-free line of >=%d chars to probe "
                "with" % (name, PROBE_MIN))

    hits = 0
    for p in probes:
        # -e: a probe line beginning with `-` would otherwise parse as an option
        r = git(repo, "grep", "-F", "-q", "-e", p, "HEAD")
        if r.returncode == 0:
            hits += 1
        elif r.returncode not in (1,):
            return ("published", None,
                    "git grep failed (rc=%d): %s"
                    % (r.returncode, (r.stderr or "").strip()[:100]))

    if hits == len(probes):
        return ("published", True,
                "%s is IN the committed tree (%d/%d distinctive lines found) - "
                "this land SHIPPED" % (name, hits, len(probes)))
    if hits == 0:
        return ("published", False,
                "%s is absent from the committed tree (0/%d distinctive lines)"
                % (name, len(probes)))
    return ("published", None,
            "%s matches the committed tree only PARTIALLY (%d/%d) - possibly a "
            "different revision of the entry. Reporting ambiguous rather than "
            "rounding it to either side." % (name, hits, len(probes)))


def compose_evidence(repo, since=None):
    """What survives a kill and says a land was COMPOSED. Each leg reported.

    `since` is this fire's start as an epoch. WITHOUT IT THE BODY-FILE LEG IS
    UNKNOWN, not True: body files accumulate in the clone root indefinitely
    (519 present at the first live run, 2 of them recent), so an unscoped read
    is true on every fire and discriminates nothing.
    """
    legs = []
    _fresh_names = []      # names composed THIS fire; empty on the unscoped path
    try:
        allnames = sorted(n for n in os.listdir(repo)
                          if n.endswith(BODY_SUFFIXES))
    except OSError as e:
        legs.append(("body-files", None, "clone root unreadable: %s" % e))
    else:
        if since is None:
            legs.append(("body-files", None,
                         "UNSCOPED - %d in the clone root, but with no fire "
                         "start this leg cannot tell a land composed THIS fire "
                         "from weeks of debris. Reporting unknown rather than a "
                         "yes it cannot justify; pass --log so the start can be "
                         "read." % len(allnames)))
        else:
            fresh = []
            for n in allnames:
                try:
                    if os.path.getmtime(os.path.join(repo, n)) >= since:
                        fresh.append(n)
                except OSError:
                    pass
            _fresh_names = list(fresh)
            shown = ", ".join(fresh[:SAMPLE])
            more = "" if len(fresh) <= SAMPLE else " (+%d more)" % (len(fresh) - SAMPLE)
            legs.append(("body-files", bool(fresh),
                         "%d composed this fire%s of %d in the clone root%s"
                         % (len(fresh), " -- " + shown if fresh else "",
                            len(allnames), more)))

    legs.append(_published_leg(repo, _fresh_names))

    d = git(repo, "status", "--porcelain", "--untracked-files=no")
    if d.returncode != 0:
        legs.append(("tracked-dirt", None,
                     "git status failed: %s" % (d.stderr or "").strip()[:120]))
    else:
        dirt = [l for l in d.stdout.split("\n") if l.strip()]
        legs.append(("tracked-dirt", bool(dirt),
                     "; ".join(dirt) if dirt else "clone is tracked-clean"))
    return legs


def append_record(repo, seat, header, lines, commit_msg):
    """Byte-append + pathspec commit + one push. Never raises."""
    try:
        now = datetime.now().astimezone().replace(microsecond=0)
        led_dir = os.path.join(repo, "memory", "tickfails")
        os.makedirs(led_dir, exist_ok=True)
        led = os.path.join(led_dir,
                           "%s_%s.md" % (seat, now.strftime("%Y-%m-%d")))
        rec = "\n## %s %s %s\n\n" % (header, seat, now.isoformat())
        rec += "\n".join(lines) + "\n"
        with io.open(led, "ab") as fh:          # byte-append, never rewrite
            fh.write(rec.encode("utf-8"))
        rel = os.path.relpath(led, repo).replace(os.sep, "/")
        git(repo, "add", "--", rel)             # untracked is unreachable by pathspec
        c = git(repo, "commit", "-m", commit_msg, "--", rel)
        if c.returncode != 0:
            log("orphan-record: commit failed (%s) - the record survives as tree "
                "bytes and the next append recommits it"
                % (c.stderr or c.stdout).strip()[:160])
            return 0
        sha = git(repo, "rev-parse", "--short", "HEAD").stdout.strip()
        p = git(repo, "push", "origin", "HEAD")
        log("orphan-record: committed %s; push rc=%d (durability is the NEXT "
            "fire's containment probe, never this rc)" % (sha, p.returncode))
        return 0
    except Exception:  # noqa: BLE001
        log("orphan-record: publish failed (record may exist locally):\n"
            + traceback.format_exc()[-400:])
        return 0        # a bookkeeping failure must never take the tick down


def do_detect(a):
    repo = os.path.abspath(a.repo)
    marker = os.path.join(repo, a.marker)
    since = _fire_start_from_log(a.log) if getattr(a, "log", None) else None
    legs = compose_evidence(repo, since)
    # COMPOSITION axis only. `published` answers a different question -- did
    # the composed thing reach the tree -- and letting it into `unknown` makes
    # a quiet fire (nothing composed, so nothing to publish) UNDETERMINED, when
    # a quiet fire is the commonest and least alarming outcome there is.
    comp = [(n, v, d) for n, v, d in legs if n != "published"]
    composed = any(v is True for _, v, _ in comp)
    unknown = [n for n, v, _ in comp if v is None]
    by = dict((n, v) for n, v, _ in legs)

    print("TICK_LAND_ORPHANED detector  seat=%s  clone=%s" % (a.seat, repo))
    for name, val, detail in legs:
        print("  %-13s %-7s %s"
              % (name, {True: "YES", False: "no", None: "UNKNOWN"}[val], detail))
    print("  %-13s %s" % ("fail-marker",
                          "PRESENT" if os.path.exists(marker) else "absent"))

    if os.path.exists(marker):
        print("\nNOT ORPHANED: tick_land wrote its own terminal-failure marker, "
              "so the land reached a decision and recorded it.")
        return 0
    if not composed:
        if unknown:
            print("\nUNDETERMINED: no compose evidence, and %s came back "
                  "UNKNOWN - see its line above for whether it was unreadable "
                  "or merely unable to discriminate. Reporting rather than "
                  "concluding: a leg that did not answer is not a leg that "
                  "answered no." % ", ".join(unknown))
            return 3
        print("\nNOT ORPHANED: no evidence a land was ever composed. A fire with "
              "nothing to say lands nothing, and that is not a defect.")
        return 0

    # Something WAS composed. The remaining question is the third conjunct of
    # this tool's stated contract: did it get published?
    if by.get("tracked-dirt") is True:
        pass          # uncommitted material IS unpublished material. The dirt
                      # leg answers the publication question directly and beats
                      # any probe of the tree -- fall through to ORPHANED.
    elif by.get("published") is True:
        print("\nNOT ORPHANED: this fire's composed land is IN the committed "
              "tree, and the clone is tracked-clean. A land that shipped is not "
              "an orphan - without this leg a SUCCESSFUL land and a vanished "
              "one present the identical signature, because tick_land writes "
              "its failure marker only on the terminal-failure path.")
        return 0
    elif by.get("published") is None:
        print("\nUNDETERMINED: a land was composed and left no marker, but the "
              "publication leg could not answer - see its line above. Reporting "
              "rather than concluding: booking an ORPHANED record here is how a "
              "shipped entry gets priced as lost work.")
        return 3

    lines = [
        "A land was COMPOSED but reached NO terminal outcome. tick_land writes",
        "its failure marker only on its own terminal-failure path, so a land",
        "killed mid-decision writes nothing - the marker's ABSENCE is not",
        "evidence of success. This record is written by the LAUNCHER, which",
        "survives the kill.",
        "",
        "Evidence (each leg stated, so the verdict can be checked):",
    ]
    for name, val, detail in legs:
        lines.append("  - %s: %s -- %s"
                     % (name, {True: "YES", False: "no", None: "UNKNOWN"}[val],
                        detail))
    lines += [
        "",
        "Clone state at detection: %s" % (git(repo, "rev-parse", "--short",
                                              "HEAD").stdout.strip() or "?"),
        "Rescue material: the composed body files are LEFT ON DISK in the clone",
        "root, named above. They are the fire's work and are re-landable.",
        "",
        "⚠ THIS DIRT DARKENS LATER SLOTS. The next fire's sync REFUSES on",
        "tracked-file dirt by design and will not reset it away, so every",
        "subsequent slot dies at sync until a hand clears it. When it is",
        "cleared, book the span with --darkened-span so the lost slots are",
        "priced as launched-and-died rather than read as never-launched.",
    ]
    print("\nORPHANED - writing the record.")
    return append_record(
        repo, a.seat, "TICK_LAND_ORPHANED", lines,
        "tickfail(%s): land orphaned - launcher-written record (the killed "
        "process could not write its own)" % a.seat)


def do_span(a):
    repo = os.path.abspath(a.repo)
    slots = [s.strip() for s in (a.slots or "").split(",") if s.strip()]
    lines = [
        "The span a killed fire's dirt DARKENED, booked at clearance time by",
        "the clearing hand - the only moment both ends of the window are known.",
        "",
        "Window opened: %s   (the orphaned fire)" % a.since,
        "Window closed: %s   (clearance)" % a.until,
        "Slots inside the window: %d" % len(slots),
    ]
    for s in slots:
        lines.append("  - %s" % s)
    lines += [
        "",
        "Resolution state: %s" % a.resolution,
        "",
        "WHY THIS IS BOOKED SEPARATELY. The durability ladder prices lost slots,",
        "and across a DIRTY window its verdict is UNDISCRIMINATED: a slot that",
        "launched and died at the sync refusal looks exactly like a slot that",
        "never launched, and any loss count is a LOWER BOUND. Evidence that",
        "discriminates them - scheduler Last Run Time / Last Result, the alert",
        "file's mtime - lives outside the clone and is unavailable to any fire.",
        "Recording it here is what keeps the instrument's blind spot from",
        "becoming permanent.",
    ]
    if a.note:
        lines += ["", "Note: %s" % a.note]
    print("Booking darkened span %s .. %s (%d slot(s))"
          % (a.since, a.until, len(slots)))
    return append_record(
        repo, a.seat, "TICK_LAND_DARKENED_SPAN", lines,
        "tickfail(%s): darkened-span record - slots eaten by orphaned dirt"
        % a.seat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--seat", required=True)
    sub = ap.add_subparsers(dest="mode", required=True)

    d = sub.add_parser("detect", help="launcher-invoked, after the seat exits")
    d.add_argument("--marker", default="TICK_LAND_FAILED.txt")
    d.add_argument("--log", default=None,
                   help="launcher log; its last '==== ... ====' line is "
                        "this fire's start. Without it the body-file leg "
                        "is UNKNOWN, because an unscoped clone root is "
                        "true on every fire.")
    d.set_defaults(fn=do_detect)

    s = sub.add_parser("darkened-span", help="hand-invoked, at clearance")
    s.add_argument("--since", required=True)
    s.add_argument("--until", required=True)
    s.add_argument("--slots", default="",
                   help="comma-separated, each 'HH:MM state' e.g. "
                        "'03:13 launched-and-died'")
    s.add_argument("--resolution", required=True)
    s.add_argument("--note", default="")
    s.set_defaults(fn=do_span)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
