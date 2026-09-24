#!/usr/bin/env python3
"""Launcher identity check — does the scheduler run the TRACKED launcher?

⛔ THIS FILE'S CONTRACT INVERTED ON 2026-08-10 AND THE OLD POLARITY IS KEPT HERE
ON PURPOSE. Written a few minutes earlier, it asserted parity between the tracked
copy and an OUT-OF-TREE live copy that the scheduler invoked — detection, because
identity was not available: re-pointing is `schtask-change` and no action token
licensed the tick tasks. A fleet ruling chose (A) — identity beats detection — the
tokens were granted, and both tasks now invoke `start/launchers/` directly.

The moment that landed, the old check went RED while reporting the GOAL state:
"PALocalOrchTick does NOT invoke the file compared above." The predicate was
still true; it had simply stopped meaning what it was written to mean.
[[guard-preconditions-expire]] — a guard outlives the world it was written for,
and a guard that reports success as failure is on its way to being ignored.

NOW: green means the scheduler invokes the TRACKED file. Pointing back at
`%USERPROFILE%\\pa-task-launchers\\` is the REGRESSION this now catches —
that path holds legacy orphans, kept (not deleted; deletion is not mine) and
flagged, because the live hazard is someone editing the copy nothing runs.

Exit 0 = the scheduler runs the tracked launcher. Exit 1 = it does not.
Exit 2 = could not look — which is NOT success, and never reported as green.
"""
import pathlib
import subprocess
import sys

# ⛔ CONSOLE-ENCODING GUARD (Q5 round, a fleet ruling). Python selects the
#   locale codec (cp1252 here) whenever this stream is PIPED OR REDIRECTED --
#   which is the normal condition under a scheduled task, a hook, or any
#   dispatcher that captures output -- even on a cp65001 console. Without this,
#   one marker glyph raises UnicodeEncodeError and the process exits rc=1, and
#   in this fleet's grammar rc=1 means THE SUBJECT REGRESSED. The encoding
#   fault would be published as a verdict about the thing under test.
# ⭐ `errors=` is the half that gets forgotten: a stream reconfigured to utf-8
#   but left at errors='strict' is still one character from rc=1.
# ⚠ TypeError is load-bearing -- the `errors=` keyword raises it on a custom
#   stream whose reconfigure() accepts only `encoding`, and that shape once
#   shipped as a new crash one import earlier. Shape copied from
#   tools/append_co.py:182-195 per INVENTORY.md §3.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, TypeError, ValueError, OSError):
        pass

TRACKED_DIR = pathlib.Path(__file__).resolve().parents[2] / "start" / "launchers"
LEGACY_DIR = pathlib.Path.home() / "pa-task-launchers"
PAIRS = (("PALocalOrchTick", "orch-tick-hidden.vbs"),
         ("PALocalCreatorTick", "creator-tick-hidden.vbs"))


def _task_target(task):
    """What the scheduler ACTUALLY invokes. The tracked file tells you what
    SHOULD run; only this tells you what does."""
    try:
        out = subprocess.run(["schtasks", "/query", "/tn", task, "/fo", "LIST", "/v"],
                             capture_output=True, text=True, timeout=30)
    except Exception as e:                                   # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"
    if out.returncode != 0:
        return None, f"schtasks rc={out.returncode}"
    for line in out.stdout.splitlines():
        if line.strip().lower().startswith("task to run:"):
            return line.split(":", 1)[1].strip(), None
    return None, "no 'Task To Run' row in schtasks output"


def main():
    rc = 0
    for task, name in PAIRS:
        tracked = TRACKED_DIR / name
        if not tracked.exists():
            print(f"CANNOT LOOK  {name}: tracked copy missing at {tracked}")
            rc = max(rc, 2)
            continue
        target, err = _task_target(task)
        if err:
            print(f"CANNOT LOOK  {task}: {err} — UNKNOWN, not green")
            rc = max(rc, 2)
            continue
        t = (target or "").lower()
        if str(tracked).lower() in t:
            print(f"identity     {task} -> tracked {name}")
            # A path can be present and still be unrunnable: a mangled /tr string
            # (leading space, unbalanced quote) reads fine at a glance and fails at
            # fire time. Burned by exactly that on this task today.
            if '"' in (target or "") and (target or "").count('"') % 2:
                print(f"  ⚠ UNBALANCED QUOTE in the stored command: {target!r}")
                rc = max(rc, 1)
        elif str(LEGACY_DIR).lower() in t:
            print(f"REGRESSION   {task} points back at the LEGACY out-of-tree copy: {target}")
            rc = max(rc, 1)
        else:
            print(f"UNKNOWN TARGET {task}: {target}")
            rc = max(rc, 1)
    orphans = sorted(p.name for p in LEGACY_DIR.glob("*tick-hidden.vbs")) if LEGACY_DIR.exists() else []
    if orphans:
        print(f"note: legacy orphans still present in {LEGACY_DIR}: {', '.join(orphans)} "
              f"— nothing invokes them; kept rather than deleted (not mine to delete), "
              f"and the hazard they carry is someone editing the copy nothing runs")
    return rc


if __name__ == "__main__":
    sys.exit(main())
