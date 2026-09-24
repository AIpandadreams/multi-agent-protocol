#!/usr/bin/env python3
"""Polarity drive for orphan_census.classify (review round 3).

The classifier is pure, so every branch is driven with synthetic process records
instead of waiting for a real orphan to exist. That matters here beyond
convenience: the branch most likely to be WRONG — PID reuse making a true orphan
look parented — cannot be produced on demand on a live machine, so a drive that
only ran against real process tables would never test it.

Each case states what would go wrong if the branch broke, because a census whose
false-positive rate is about to earn it KILL authority (orch's later flip) has to
be wrong in a direction someone can name.

Exit: 0 = all cases as specified, 1 = at least one off-spec.
"""
import datetime
import importlib.util
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("oc", HERE / "orphan_census.py")
oc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oc)

NOW = datetime.datetime(2026, 8, 13, 15, 0, 0,
                        tzinfo=datetime.timezone(datetime.timedelta(hours=-4)))


def ts(minutes_ago):
    return (NOW - datetime.timedelta(minutes=minutes_ago)).isoformat()


def proc(pid, ppid, name="python.exe", age=120, cpu=0.0, cmd="x"):
    return {"pid_": pid, "ppid": ppid, "name": name, "created": ts(age),
            "cpu": cpu, "cmd": cmd}


CASES = []


def case(name, t0, t1, want_pids, why):
    CASES.append((name, t0, t1, set(want_pids), why))


# --- the textbook orphan: dead parent, idle, old ------------------------------
case("classic orphan (dead parent, 0 cpu, 120 min)",
     [proc(100, 999)], [proc(100, 999)], [100],
     "if this misses, the census never finds the thing it was commissioned for")

# --- each signature clause must be independently necessary --------------------
# ⚠ THE PARENT FIXTURES USE cmd.exe DELIBERATELY, and the first draft did not.
# With the parent named node.exe, these two cases FAILED — because that parent's
# own parent (pid 1) is not in the synthetic table, making the PARENT itself a
# textbook orphan, which the classifier correctly reported. The bug was in my
# setup, not the assertion, so the setup moved: cmd.exe is out of WATCHED, which
# is also the real fleet shape (our leaked python/node processes hang off
# cmd.exe). Recorded because "the fixture accidentally contained a second
# instance of the thing under test" is easy to mistake for a false positive and
# 'fix' by loosening the classifier [[control-passing-for-the-wrong-reason]].
case("parent ALIVE — not an orphan",
     [proc(100, 50), proc(50, 1, name="cmd.exe", age=300)],
     [proc(100, 50), proc(50, 1, name="cmd.exe", age=300)], [],
     "flagging a parented process would put live tooling on a kill list later")

case("dead parent but BURNING CPU — not a leak",
     [proc(100, 999, cpu=10.0)], [proc(100, 999, cpu=14.0)], [],
     "a long-running job with a detached parent is working, not wedged")

case("dead parent, idle, but only 5 min old — under the age bound",
     [proc(100, 999, age=5)], [proc(100, 999, age=5)], [],
     "young detached processes are normal mid-spawn; flagging them floods the census")

# --- the branch that cannot be staged on a live machine -----------------------
case("PID REUSE: 'parent' was created AFTER the child — still an orphan",
     [proc(100, 50, age=600), proc(50, 1, name="node.exe", age=10)],
     [proc(100, 50, age=600), proc(50, 1, name="node.exe", age=10)], [100],
     "without this, a recycled pid silently rescues a true orphan from the census "
     "— the census would under-report and look specific for the wrong reason")

case("genuine parent older than child is NOT reuse",
     [proc(100, 50, age=60), proc(50, 1, name="cmd.exe", age=600)],
     [proc(100, 50, age=60), proc(50, 1, name="cmd.exe", age=600)], [],
     "the reuse rule must not swallow ordinary parentage")

# --- scope ---------------------------------------------------------------------
case("unwatched process name is out of scope",
     [proc(100, 999, name="chrome.exe")], [proc(100, 999, name="chrome.exe")], [],
     "this is a census of our leaked tooling, not of the principal's machine")

case("exited during the window — gone, not orphaned",
     [proc(100, 999)], [], [],
     "a process that left is not a leak; reporting it would be unactionable")

# --- honest outcomes -----------------------------------------------------------
case("unparseable creation stamp is SKIPPED, not counted clean",
     [dict(proc(100, 999), created="not-a-date")],
     [dict(proc(100, 999), created="not-a-date")], [],
     "must appear in notes rather than silently vanishing into a clean result")

case("unreadable CPU is SKIPPED, not counted clean",
     [dict(proc(100, 999), cpu=None)], [dict(proc(100, 999), cpu=None)], [],
     "an unknown is not a zero [[honest-failure-outcomes]]")

case("excluded pid (the census's own process) never self-reports",
     [proc(100, 999)], [proc(100, 999)], [],
     "a census that reports itself is noise on every single run")


def main():
    bad = 0
    for name, t0, t1, want, why in CASES:
        exclude = {100} if "excluded pid" in name else set()
        orphans, notes = oc.classify(t0, t1, NOW, exclude_pids=exclude)
        got = {o["pid"] for o in orphans}
        ok = got == want
        if not ok:
            bad += 1
        print("%-7s %-60s want %-9s got %s" % ("PASS" if ok else "*FAIL*", name[:60],
                                               sorted(want) or "none", sorted(got) or "none"))
        print("        why: %s" % why)
        if notes:
            for n in notes:
                print("        note: %s" % n)

    # A drive where nothing can fail proves nothing: require both polarities AND
    # at least one note-producing case [[control-design-discipline]].
    spans_found = any(w for _, _, _, w, _ in CASES)
    spans_clean = any(not w for _, _, _, w, _ in CASES)
    noted = any(oc.classify(t0, t1, NOW)[1] for _, t0, t1, _, _ in CASES)
    print()
    print("cases: %d, off-spec: %d" % (len(CASES), bad))
    print("drive spans: orphan-found=%s clean=%s honest-skip-notes=%s"
          % (spans_found, spans_clean, noted))
    if not (spans_found and spans_clean and noted):
        print("*** DRIVE IS NOT A CONTROL — it does not span both verdicts and a skip ***")
        return 1
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
