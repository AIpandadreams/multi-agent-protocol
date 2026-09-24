#!/usr/bin/env python3
"""Held-tap ledger — defers a NARROW tap by one canary round.

WHY THIS IS A SEPARATE MODULE. `join.py` is armed and heavily controlled
(f8_controls stubs `join.decide` wholesale). Putting the deferral here keeps
join's diff to a filter plus two calls, and lets the arms drive the mechanism
directly instead of through a stubbed join.

WHAT IT DOES. A NARROW verdict means phase 2 missed inside the settle window
while the watcher went on beating. The probe STOPPED LOOKING at that boundary,
so a merely-slow-but-healthy watcher and a structurally-deaf one produce the
same token — and join taps the friction ledger on the token, never on the prose
the verdict computed. This holds the tap for one round and asks the only
question that separates them: did the token show up afterwards?

  token present next round -> it was a RACE. Drop the tap, close the record.
  token still absent       -> the watcher never registered that entry across a
                              full further round. FIRE, now carrying positive
                              evidence rather than a deadline expiry.

KEYED ON (edge, token), NEVER ON token ALONE. `sentinel.run_canary` derives its
default token from `time.strftime(...%H%M%S)` -- a ONE-SECOND stamp -- and join
probes every edge in a loop, so two edges probed inside the same second share a
token. Today that is harmless (canary file PATHS differ per recipient). Under a
deferral it would let one seat's watcher close another seat's held record as a
race: JOIN DEFECT 3's exact shape, a one-to-many relation collapsed by an
accident of key choice.

⚠ ON THE RETAINED LATENCY. `sentinel`'s own `lat2` is computed inside
`run_canary` and returned to nobody -- it exists in the mesh only as prose inside
the verdict note, and parsing that note would re-commit the very defect this
cure exists to fix. So the retained quantity is `late_lat_s`, measured from the
round's PROBE START rather than from sentinel's internal phase-2 mark. Probe
start precedes the mark, so this is an UPPER BOUND on the true phase-2 latency,
not the same number. It is monotone in the quantity a trend wants, and it is
labelled `late_lat_s` -- not `lat2` -- so nobody reads it as sentinel's figure.
"""
import io
import json
import os
import re
import time

LEDGER_DIRNAME = os.path.join("memory", "tapledger")

# A NEW directory, deliberately not HB_DIR. Every discovery site in the mesh --
# sentinel.py:365, waketap.py:437, arm_register.py:263 -- keys on `*.hb`, and the
# `.obs` consumers resolve by exact path. A ledger file in HB_DIR would be inert
# ONLY as long as that suffix discipline holds, which makes the safety a
# convention every future author must know. Nothing globs this directory at all,
# so it is inert by construction.

_TS = "%Y-%m-%dT%H:%M:%S%z"
_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})\b")


def ledger_dir(ws):
    return os.path.join(ws, LEDGER_DIRNAME)


def _record_name(edge, token):
    # (edge, token) in the FILENAME, so the key is the identity of the file and
    # two records cannot collide without colliding on both parts.
    return "%s__%s.json" % (edge, token)


def hold(ws, edge, token, seat, watch, probe_started, note):
    """Record a deferred NARROW tap. Returns the record path."""
    d = ledger_dir(ws)
    os.makedirs(d, exist_ok=True)
    rec = {
        "edge": edge, "token": token, "seat": seat, "watch": watch,
        "probe_started": probe_started, "note": note,
        "held_at": time.strftime(_TS), "status": "held",
    }
    p = os.path.join(d, _record_name(edge, token))
    with io.open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(rec, indent=2, sort_keys=True))
    return p


def _parse_ts(s):
    try:
        return time.mktime(time.strptime(s[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return None


def _obs_path(hb_dir, seat, watch):
    # EXACT PATH, never a glob. sentinel.py:557 records that the glob form was
    # itself a defect: glob("*.%s.obs")[0] returned the alphabetically-first
    # seat's log, so one seat's watcher was judged by another's evidence.
    return os.path.join(hb_dir, "%s.%s.obs" % (seat, watch))


def _token_line(obs_path, token):
    """The first obs line naming `token`, or None. Reads the WHOLE file.

    Not a tail read: a tail bounded by bytes or lines would miss a token that
    landed earlier in a busy round. Reading whole is affordable because this runs
    once per held record per round, not per poll.

    ROTATION needs no search branch here, and the reason CHANGED at r2. It used
    to rest on "nothing rotates `.obs` today" plus the A5 tripwire -- and owner's
    A4-rotation arm showed that analysis was placed one step too late: a
    RENAME (`.obs` -> `.obs.1`) makes `os.path.exists` False, so the hazard
    arrives at the exists-check, not at the whole-file read this docstring was
    reasoning about. A5 could never have covered it.

    With the exists-check raising (above), a renamed log is simply an absent one:
    HELD-UNRESOLVED, never a tap, against a watcher that did report. That holds
    for ANY cause of a vanished log, which is strictly more general than the
    rotation-search branch I declined to build. A5 is kept -- it still reports
    the day someone wires rotate_log at an `.obs` path, which is worth knowing --
    but it is no longer load-bearing for this hazard. A7 is.
    """
    if not os.path.exists(obs_path):
        # ⚠ THIS BRANCH WAS INVERTED AND OWNER (E473) CAUGHT IT. It returned
        # None, and `resolve()` maps None to the positive-evidence branch -- so a
        # MISSING obs log fired a NARROW tap and stamped "token absent across a
        # full further round" onto a file that was never opened. A fabricated
        # evidentiary basis, and the exact accusation the armed sentinel refuses
        # to make ("absence is never a verdict about the watcher").
        #
        # The rule was already written, three lines below, guarding the `except`.
        # I wrote it and then guarded the wrong branch with it: an early return
        # sitting OUTSIDE the try never met the rule stated inside it.
        #
        # A vanished log is an unreadable instrument, whatever made it vanish --
        # deletion, rotation-rename, a moved workspace, a cleanup script. All of
        # them now reach the same outcome: raise, `resolve()` records it in
        # `errors`, and THE RECORD STAYS HELD (status is never rewritten on this
        # path), so the operator sees HELD-UNRESOLVED rather than a tap.
        raise OSError("obs log absent — not evidence about the watcher: %s" % obs_path)
    try:
        with io.open(obs_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if token in line:
                    return line.rstrip("\n")
    except OSError:
        # An unreadable instrument is NOT evidence about the watcher. Returning
        # None here would read as "token absent" and FIRE a tap on an unread
        # file -- the accusation this whole mesh refuses to make. Raise instead.
        raise
    return None


def resolve(ws, hb_dir):
    """Resolve every held record. Returns (fire, closed, errors).

    fire   -- [(seat, watch, reason)] taps that must now be delivered
    closed -- [dict] records closed as NARROW-RACE, carrying late_lat_s
    errors -- [(path, message)] records that could not be resolved
    """
    d = ledger_dir(ws)
    fire, closed, errors = [], [], []
    if not os.path.isdir(d):
        return fire, closed, errors
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(d, name)
        try:
            with io.open(p, "r", encoding="utf-8") as fh:
                rec = json.load(fh)
        except (ValueError, OSError) as exc:
            errors.append((p, "unreadable held record: %s" % exc))
            continue
        if rec.get("status") != "held":
            continue
        seat, watch, token = rec.get("seat"), rec.get("watch"), rec.get("token")
        if not (seat and watch and token):
            errors.append((p, "held record missing seat/watch/token — cannot resolve"))
            continue
        try:
            line = _token_line(_obs_path(hb_dir, seat, watch), token)
        except OSError as exc:
            errors.append((p, "obs log unreadable — NOT treated as absent: %s" % exc))
            continue
        if line is None:
            # Absent across a full further round. This is the positive-evidence
            # case, and it is what makes the deferral a DELAY and not a deletion.
            fire.append((seat, watch, "canary-narrow"))
            rec["status"] = "fired"
            rec["resolution"] = "token absent across a full further round"
        else:
            rec["status"] = "closed"
            rec["resolution"] = "NARROW-RACE"
            rec["obs_line"] = line
            m = _TS_RE.match(line)
            t_obs = _parse_ts(m.group(1)) if m else None
            t_start = _parse_ts(rec.get("probe_started") or "")
            # late_lat_s is measured from PROBE START, not sentinel's phase-2
            # mark (which never crosses the layer). Upper bound, named so.
            rec["late_lat_s"] = (round(t_obs - t_start, 1)
                                 if (t_obs is not None and t_start is not None) else None)
            closed.append(rec)
        rec["resolved_at"] = time.strftime(_TS)
        with io.open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(rec, indent=2, sort_keys=True))
    return fire, closed, errors
