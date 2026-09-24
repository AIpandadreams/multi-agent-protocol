#!/usr/bin/env python3
"""custody_attempts.py — the ATTEMPT LOG: the artifact that makes a FROZEN seat
and a GONE seat two different things on disk.

⛔ THE DEFECT THIS EXISTS TO CURE. `custody_emitter` writes only on SUCCESS —
the lease `touch()` and the cadence line both land at the END of a run that got
all the way through. So the two states below are byte-identical downstream:

    FROZEN  the seat's process is ALIVE and wedged mid-tool (the measured
            hung-PreToolUse-hook mode: 26 minutes of frozen session)
    GONE    the seat is dead, crashed, or simply exited

Both present as "emissions stopped at T". A consumer holding only that series
cannot tell a seat that still holds the tree from one that released it, and the
two demand opposite actions. Worse, the parameter that was supposed to absorb
the difference — the lease TTL — cannot: to cover a freeze it would have to be
sized by how long a pathology lasts, and pathology has no upper bound. A TTL
sized that way stops discriminating at all.

⭐ THE CURE IS STRUCTURAL, NOT NUMERIC. Write an ATTEMPT record BEFORE the work
and a COMPLETION record AFTER it. Then:

    attempt with NO completion   the process REACHED the hook and never got
                                 back            → FROZEN
    no attempt at all            the process never reached the hook
                                 → GONE
    attempt + completion         it went in and came out  → HEALTHY

The discriminator is the ASYMMETRY between those two artifacts, not a threshold
on one of them. The threshold that remains (`freeze_after_s`) only answers "has
enough time passed to call this a freeze rather than an in-flight call" — it
does not have to separate freeze from death, because the records already do.
That is the whole point: a number sized by taste now only decides WHEN to look,
never WHAT it is looking at.

⛔ WHY THE COMPLETION IS WRITTEN IN A `finally` AND WHY THAT IS LOAD-BEARING.
The ways a run can end split exactly along the line we need:
  · normal return, or an exception that propagates → `finally` RUNS → closed.
    A raise is "got back", not "hung", and the emitter's existing battery
    already treats those as different failure modes (bars [2] vs [4]).
  · `os._exit()` from the watchdog, SIGKILL, SIGTERM from the wrapper's
    `timeout -k`, or a genuine unbounded wedge → `finally` NEVER RUNS → open.
So "open" means precisely "this process did not come back under its own power".

⚠ NAMED RESIDUAL — WHAT THIS CANNOT SEE. The attempt record is written by the
emitter, so it exists only once the interpreter is up and the payload parsed.
The two MEASURED wedges had the python process at 0.0 s CPU
— wedged in interpreter/prelude startup, BEFORE any line of the emitter ran.
Such a wedge leaves NO attempt record and is therefore reported GONE, which is
wrong. This is the same bound that falsified the in-process watchdog, and it is
falsified here for the same reason: an in-process artifact cannot describe the
phase before the process exists. Covering it needs a record written by the
PARENT (custody_emit_wrapper.sh already touches `.custody_wrapper_lastfire`
before exec'ing python, so the hook point exists) — deliberately NOT built here,
because that is a wrapper change and this leg is scoped to the emitter. What IS
covered: every wedge from `parse` onward, which includes the seat-resolution
phase (the only in-python phase that reads other files and can block on them).

⚠ SECOND NAMED RESIDUAL — the watchdog's own exit leaves an OPEN attempt, since
`os._exit()` skips the `finally` by design. If such a run is the LAST record for
a session, the session reads FROZEN when it was really "aborted, then gone".
Left uncured deliberately: the cure would be an abort record written from
`_hard_exit`, and `_hard_exit`'s ONLY job is to be the bound that always fires —
adding a filesystem write to it puts I/O on the path that exists because I/O
hung. Failing toward FROZEN is also the safe direction here, matching the
ruling the emitter already carries for `unknown` over silence: an ambiguous
"someone may be stuck" costs a human a look, while a false "gone" is what gets a
live tree discarded.

⛔ APPEND-ONLY, and never rewritten. `write_text` TRUNCATES; every write here is
`open(p, "a")` of ONE short line terminated by a newline. A torn write can
therefore damage only the tail line — prior records are not in the write path at
all and cannot be destroyed by it. The reader tolerates a malformed tail, COUNTS
it, and reports the count rather than silently dropping it.
"""
import os
import re
import time

# ── the grammar, emitter and reader share ONE definition of it ────────────────
# The writer below and `classify` below are the only two things that know this
# format, and they are in the same file precisely so a change cannot land in one
# without the other [[emitter-and-verifier-are-one-grammar]].
ATTEMPT_PREFIX = ".custody_attempts."
KIND_ATTEMPT = "A"
KIND_COMPLETE = "C"
SEP = "\t"

# Bounded, and bounded HONESTLY — on reaching the cap the file SAYS SO in-band,
# rather than silently becoming a partial series a reader would take as whole.
# Same convention as `_note_cadence`'s CADENCE_MAX_LINES.
ATTEMPT_MAX_LINES = 20000
CAP_MARKER = "# CAPPED"

# Session ids are used as a FILENAME component. Same character class custody_lease
# enforces, for the same reason: a crafted id must not escape the directory.
_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_FIELD_UNSAFE = re.compile(r"[^\x20-\x7e]")

# classification states
HEALTHY = "healthy"
FROZEN = "frozen"
GONE = "gone"
UNKNOWN = "unknown"

# ⚠ PROVISIONAL AND DELIBERATELY NOT WIRED AS A DEFAULT. `classify` takes
# `freeze_after_s` as a REQUIRED argument and raises when it is missing, so this
# number can never become the answer by omission — a caller that wants the guess
# has to name it, and the guess is then visible at the call site. This mirrors
# the ruling custody_lease already carries for `ttl_seconds` ("a REQUIRED
# argument and a missing one RAISES — never silently becomes a number somebody
# picked once"). The real figure is being derived by a separate leg from the
# cadence series; until it lands, this is a placeholder and nothing more
# [[stated-bound-is-an-open]].
PROVISIONAL_FREEZE_AFTER_S = 900.0


def path_for(workspace, session):
    """The per-session attempt log. Returns None for an unusable session id."""
    if not session or not _SESSION_RE.match(session):
        return None
    return os.path.join(str(workspace), "plans", ATTEMPT_PREFIX + session)


def _clean(value):
    """One field, guaranteed not to contain a separator or a line break.

    A seat name or a resolver message carrying a tab or a newline would forge
    extra fields or an extra RECORD — i.e. the log's own grammar would be
    writable by the data it logs."""
    s = "" if value is None else str(value)
    s = s.replace(SEP, " ").replace("\r", " ").replace("\n", " ")
    return _FIELD_UNSAFE.sub("?", s)[:120] or "?"


def _append_line(path, line):
    """Append-only. `write_text` would TRUNCATE — the idiom is copied verbatim
    from custody_emitter._append_line rather than imported, because importing
    the emitter EXECUTES it (its prelude reads stdin and arms a watchdog), so
    this module must never do that."""
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)
        return True
    except Exception:  # noqa: BLE001 — a bookkeeping failure is never an error
        return False


def _line_count(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except FileNotFoundError:
        return 0
    except Exception:  # noqa: BLE001
        return None


def start(workspace, session, phase="parse"):
    """Record an ATTEMPT and return its id, or None if nothing was recorded.

    ⭐ The cap is checked HERE and not at completion time, so the log can never
    be left holding an attempt whose completion the cap refused to write — that
    would manufacture the exact FROZEN signature out of a bookkeeping limit.
    Refusing at the attempt means a capped log records neither half of a pair,
    and the reader reports the cap instead of a verdict.

    Returns None on ANY failure. Callers must treat None as "attempt logging is
    off for this run" and skip the completion.
    """
    p = path_for(workspace, session)
    if p is None:
        return None
    n = _line_count(p)
    if n is None:
        return None
    if n >= ATTEMPT_MAX_LINES:
        if n == ATTEMPT_MAX_LINES:
            _append_line(p, "%s at %d lines — this attempt log is TRUNCATED. It is "
                            "NOT a complete record and its tail must NOT be read as a "
                            "freeze/gone verdict.\n" % (CAP_MARKER, ATTEMPT_MAX_LINES))
        return None
    attempt_id = "%d-%.6f" % (os.getpid(), time.time())
    ok = _append_line(p, SEP.join(
        (KIND_ATTEMPT, "%.3f" % time.time(), attempt_id, str(os.getpid()),
         _clean(phase))) + "\n")
    return attempt_id if ok else None


def finish(workspace, session, attempt_id, seat="?", how="?"):
    """Record the COMPLETION of `attempt_id`. Best effort; never raises."""
    if not attempt_id:
        return False
    p = path_for(workspace, session)
    if p is None:
        return False
    return _append_line(p, SEP.join(
        (KIND_COMPLETE, "%.3f" % time.time(), _clean(attempt_id), str(os.getpid()),
         _clean(seat), _clean(how))) + "\n")


# ── the reader ────────────────────────────────────────────────────────────────
def read_records(path):
    """Parse a log into (records, malformed_count, capped, status).

    `status` is one of "ok" / "absent" / "unreadable", and those last two are
    DELIBERATELY not one event. ⛔ The emitter's own `_read_unresolved` carries a
    measured finding on exactly this: collapsing "not there" and "could not read
    it" into one bare `except` made four distinct states indistinguishable and
    published a fabricated origin as a measurement. The same collapse here would
    report a log we failed to OPEN as a session that never wrote one — which is
    the difference between "this instrument is broken" and "this seat is new".

    A malformed line is likewise COUNTED, never silently dropped: the only way
    this file gets one is a torn write or a crash mid-append, and both are facts
    a reader of a liveness log needs [[empty-result-needs-its-count]].
    """
    records, malformed, capped = [], 0, False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return None, 0, False, "absent"
    except Exception:  # noqa: BLE001
        return None, 0, False, "unreadable"
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith("#"):
            if line.startswith(CAP_MARKER):
                capped = True
            continue
        parts = line.split(SEP)
        if len(parts) < 4 or parts[0] not in (KIND_ATTEMPT, KIND_COMPLETE):
            malformed += 1
            continue
        try:
            ts = float(parts[1])
        except ValueError:
            malformed += 1
            continue
        records.append({"kind": parts[0], "ts": ts, "id": parts[2],
                        "pid": parts[3], "rest": parts[4:]})
    return records, malformed, capped, "ok"


def classify(workspace, session, freeze_after_s, now=None):
    """Classify ONE session as healthy / frozen / gone / unknown.

    `freeze_after_s` is REQUIRED and a missing or non-positive value RAISES —
    see PROVISIONAL_FREEZE_AFTER_S for why it is not defaulted.

    The rules, and the reason each one is not the obvious alternative:

      HEALTHY  the newest record is younger than the threshold. Note this holds
               for an OPEN attempt too: a call currently in flight is not a
               freeze, and classifying it as one would make every busy seat
               look wedged — a detector that fires on everything detects
               nothing.
      FROZEN   the newest record is an OPEN attempt older than the threshold.
               It went into the hook and never came out.
      GONE     the newest record is older than the threshold and is CLOSED.
               It came out, and then nothing further happened.
      UNKNOWN  no log, no parseable records, or a CAPPED log. A truncated log's
               tail is not evidence about the present, so it gets no verdict
               rather than a confident wrong one.
    """
    if freeze_after_s is None or not isinstance(freeze_after_s, (int, float)) \
            or isinstance(freeze_after_s, bool) or freeze_after_s <= 0:
        raise ValueError(
            "freeze_after_s is REQUIRED and must be a positive number, got %r. "
            "It is not defaulted on purpose: the figure is being derived from "
            "the measured cadence series, and a guess that arrives by omission "
            "is indistinguishable from a measurement."
            % (freeze_after_s,))
    now = time.time() if now is None else now
    p = path_for(workspace, session)
    out = {"session": session, "state": UNKNOWN, "reason": "", "age_s": None,
           "last_kind": None, "records": 0, "malformed": 0, "open_attempts": 0,
           "status": "absent"}
    if p is None:
        out["status"] = "unreadable"
        out["reason"] = "unusable session id"
        return out

    records, malformed, capped, status = read_records(p)
    out["malformed"] = malformed
    out["status"] = status
    if records is None:
        # Two different facts, reported as two [[stated-reason-must-discriminate]].
        out["reason"] = ("no attempt log for this session — it has never emitted"
                         if status == "absent" else
                         "the attempt log EXISTS but could not be read — this is "
                         "a statement about the instrument, not about the seat")
        return out
    out["records"] = len(records)
    if capped:
        out["reason"] = ("attempt log is CAPPED at %d lines — truncated, so its "
                         "tail cannot support a verdict" % ATTEMPT_MAX_LINES)
        return out
    if not records:
        out["reason"] = ("attempt log holds no parseable records (%d malformed)"
                         % malformed)
        return out

    closed = {r["id"] for r in records if r["kind"] == KIND_COMPLETE}
    open_ids = [r["id"] for r in records
                if r["kind"] == KIND_ATTEMPT and r["id"] not in closed]
    out["open_attempts"] = len(open_ids)

    last = records[-1]
    out["last_kind"] = last["kind"]
    age = now - last["ts"]
    out["age_s"] = age

    if age <= freeze_after_s:
        out["state"] = HEALTHY
        out["reason"] = ("newest record is %.1fs old, within the %.1fs freeze "
                         "threshold%s" % (age, freeze_after_s,
                                          " (a call is in flight)"
                                          if last["kind"] == KIND_ATTEMPT else ""))
        return out

    # ⭐ THE DISCRIMINATOR. Everything above this point is shared by both
    # verdicts; this single condition is what makes frozen and gone two
    # different answers rather than one silence.
    if last["kind"] == KIND_ATTEMPT and last["id"] in open_ids:
        out["state"] = FROZEN
        out["reason"] = ("newest record is an OPEN attempt %.1fs old — the "
                         "process reached the hook and never returned" % age)
    else:
        out["state"] = GONE
        out["reason"] = ("newest record is a COMPLETED attempt %.1fs old — the "
                         "process returned, then stopped attempting" % age)
    return out


def sessions(workspace):
    """Every session id with an attempt log in this workspace."""
    d = os.path.join(str(workspace), "plans")
    try:
        names = os.listdir(d)
    except OSError:
        return []
    return sorted(n[len(ATTEMPT_PREFIX):] for n in names
                  if n.startswith(ATTEMPT_PREFIX))


def classify_all(workspace, freeze_after_s, now=None):
    return [classify(workspace, s, freeze_after_s, now=now)
            for s in sessions(workspace)]


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("workspace")
    ap.add_argument("--session", help="one session; default = all")
    ap.add_argument("--freeze-after-s", type=float, required=True,
                    help="seconds after which an OPEN attempt reads as a freeze. "
                         "REQUIRED — no default; see PROVISIONAL_FREEZE_AFTER_S.")
    a = ap.parse_args(argv)
    rows = ([classify(a.workspace, a.session, a.freeze_after_s)] if a.session
            else classify_all(a.workspace, a.freeze_after_s))
    if not rows:
        print("no attempt logs under %s/plans" % a.workspace)
        return 0
    for r in rows:
        print("%-9s %-40s age=%s open=%d recs=%d bad=%d  %s"
              % (r["state"], r["session"],
                 "n/a" if r["age_s"] is None else "%.1fs" % r["age_s"],
                 r["open_attempts"], r["records"], r["malformed"], r["reason"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
