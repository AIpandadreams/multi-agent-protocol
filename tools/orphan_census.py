#!/usr/bin/env python3
"""Orphan-process census — REPORT ONLY. Commissioned by an orchestrator ruling.

WHY IT REPORTS AND DOES NOT KILL
--------------------------------
Two distinct orphan classes surfaced in one day (builder's custody_emitter hooks
at 0.00s CPU with dead parents; a 24.4-hour git-log pickaxe), and a third the
same afternoon (an ast.parse hook, 71 min, dead parent).  The standing WATCHDOG
PID RULE exists because identification is the hard part here: a name-kill once
nearly took a peer's live process off a shared machine.  So v1 CENSUSES and
never kills.  Kill authority is a separate later flip, at orch's hand, after the
census has demonstrated specificity — zero false positives across enough days to
mean something.

SCOPE GUARD: this program only ever READS process tables.  It writes
exactly one file, under a dated census directory in the private workspace, and never touches
another seat's files or another seat's processes.

THE SIGNATURE — all three must hold
-----------------------------------
  1. parent dead or absent
  2. ~0 CPU across a sampled window (default 6s — the form that identified the
     git-log orphan)
  3. age past a STATED bound (default 30 min; --age-min, and it is printed in
     every census so no reader has to guess what "orphan" meant that day)

⚠ PID REUSE IS HANDLED, and this is the subtle one.  "Parent alive" is decided
by looking up ParentProcessId — but Windows reuses PIDs, so a dead parent's PID
can be held by an unrelated NEW process, which would make a true orphan look
parented and silently drop it from the census.  A process created AFTER its
supposed child cannot be its parent, so that case is classified DEAD-BY-REUSE
rather than alive [[names-must-resolve-against-artifacts]].

INSTRUMENT HONESTY
------------------
An empty census is only meaningful if the collector actually read something.  A
process table that comes back empty is INSTRUMENT-BROKEN, never "no orphans"
[[honest-failure-outcomes]] — and the positive control is this program's own
PID: if the collector cannot see the process asking the question, it cannot see
anything.  Own-process and own-child records are then excluded from candidacy,
so the census can never report itself.

Exit codes:  0 = CLEAN (census read fine, nothing matched)
             1 = ORPHANS FOUND (census file written; post the lane line)
             2 = INSTRUMENT-BROKEN (do not read a clean result out of this run)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CLEAN, FOUND, BROKEN = 0, 1, 2

DEFAULT_AGE_MIN = 30.0
DEFAULT_WINDOW_S = 6.0
DEFAULT_CPU_EPS = 0.05          # seconds of CPU across the window that still reads as "idle"

# Only these are ever candidates. A census that ranged over every process on a
# shared workstation would be a census of the principal's machine, not of our leaked
# tooling, and its false-positive rate would be meaningless.
WATCHED = ("python.exe", "node.exe", "git.exe", "codex.exe", "pwsh.exe", "powershell.exe")

PS_COLLECT = r"""
$ErrorActionPreference = 'Stop'
$rows = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name,
    CreationDate, CommandLine
$out = @()
foreach ($r in $rows) {
  $cpu = $null
  try { $p = Get-Process -Id $r.ProcessId -ErrorAction Stop; $cpu = $p.CPU } catch { }
  $out += [pscustomobject]@{
    pid_ = [int]$r.ProcessId
    ppid = [int]$r.ParentProcessId
    name = [string]$r.Name
    created = $(if ($r.CreationDate) { $r.CreationDate.ToString('o') } else { $null })
    cpu = $cpu
    cmd = [string]$r.CommandLine
  }
}
$out | ConvertTo-Json -Depth 3 -Compress
"""


def collect(timeout=60):
    """Read the process table via PowerShell. Returns (rows, error_or_None)."""
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                            "-Command", PS_COLLECT],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except Exception as exc:                      # noqa: BLE001 - reported, not swallowed
        return None, f"collector failed to run: {exc.__class__.__name__}: {exc}"
    if r.returncode != 0:
        return None, f"collector exited {r.returncode}: {(r.stderr or '').strip()[:300]}"
    text = (r.stdout or "").strip()
    if not text:
        return None, "collector produced no output"
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"collector output did not parse as JSON: {exc}"
    if isinstance(data, dict):                    # PowerShell unwraps a 1-element array
        data = [data]
    return data, None


def _parsed(stamp):
    if not stamp:
        return None
    try:
        return datetime.datetime.fromisoformat(stamp)
    except ValueError:
        return None


def classify(rows_t0, rows_t1, now, age_min=DEFAULT_AGE_MIN, cpu_eps=DEFAULT_CPU_EPS,
             exclude_pids=()):
    """PURE. Given two samples of the process table, return (orphans, notes).

    Split out from collect() so every branch of the signature can be driven with
    synthetic records — a census whose logic can only be exercised when a real
    orphan happens to exist is a census nobody can trust
    [[guards-without-input-are-not-shipped]].
    """
    by_pid_t0 = {r["pid_"]: r for r in rows_t0}
    by_pid_t1 = {r["pid_"]: r for r in rows_t1}
    notes = []
    orphans = []

    for pid, r in by_pid_t0.items():
        if pid in exclude_pids:
            continue
        if r.get("name") not in WATCHED:
            continue
        if pid not in by_pid_t1:
            continue                      # exited during the window — not an orphan, gone

        created = _parsed(r.get("created"))
        if created is None:
            notes.append(f"pid {pid} ({r.get('name')}): unparseable creation stamp — SKIPPED, "
                         f"not counted clean")
            continue
        age_m = (now - created).total_seconds() / 60.0
        if age_m < age_min:
            continue

        # (1) parent dead or absent — with PID reuse handled
        par = by_pid_t1.get(r.get("ppid"))
        if par is None:
            parent_state = "DEAD (no such pid)"
        else:
            par_created = _parsed(par.get("created"))
            if par_created is not None and created is not None and par_created > created:
                parent_state = (f"DEAD-BY-REUSE (pid {r.get('ppid')} now held by "
                                f"{par.get('name')} created after the child)")
            else:
                continue                  # genuinely parented — not an orphan

        # (2) ~0 CPU across the sampled window
        c0, c1 = r.get("cpu"), by_pid_t1[pid].get("cpu")
        if c0 is None or c1 is None:
            notes.append(f"pid {pid} ({r.get('name')}): CPU unreadable — SKIPPED, "
                         f"not counted clean")
            continue
        delta = float(c1) - float(c0)
        if delta > cpu_eps:
            continue                      # doing work; a long job is not a leak

        orphans.append({
            "pid": pid, "name": r.get("name"), "age_min": round(age_m, 1),
            "parent_pid": r.get("ppid"), "parent_state": parent_state,
            "cpu_total_s": c1, "cpu_delta_s": round(delta, 4),
            "cmd": (r.get("cmd") or "")[:220],
        })

    orphans.sort(key=lambda o: -o["age_min"])
    return orphans, notes


def main() -> int:
    ap = argparse.ArgumentParser(description="Report-only orphan census.")
    ap.add_argument("--age-min", type=float, default=DEFAULT_AGE_MIN,
                    help=f"age bound in minutes (default {DEFAULT_AGE_MIN})")
    ap.add_argument("--window", type=float, default=DEFAULT_WINDOW_S,
                    help=f"CPU sampling window in seconds (default {DEFAULT_WINDOW_S})")
    ap.add_argument("--cpu-eps", type=float, default=DEFAULT_CPU_EPS)
    ap.add_argument("--ws", default=os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    ap.add_argument("--no-write", action="store_true",
                    help="print the census, write no file")
    args = ap.parse_args()

    t0, err = collect()
    if err:
        print(f"INSTRUMENT-BROKEN: {err}")
        return BROKEN
    # POSITIVE CONTROL — if the collector cannot see the process asking, an empty
    # result means the reader is broken, not that the machine is clean.
    me = os.getpid()
    if not any(r.get("pid_") == me for r in t0):
        print(f"INSTRUMENT-BROKEN: positive control failed — own pid {me} absent from a "
              f"{len(t0)}-row process table; the collector is not reading this machine.")
        return BROKEN

    time.sleep(args.window)
    t1, err = collect()
    if err:
        print(f"INSTRUMENT-BROKEN: second sample: {err}")
        return BROKEN

    now = datetime.datetime.now().astimezone()
    kids = {r["pid_"] for r in t1 if r.get("ppid") == me}
    orphans, notes = classify(t0, t1, now, args.age_min, args.cpu_eps,
                              exclude_pids={me} | kids)

    print(f"orphan census {now.strftime('%Y-%m-%d %H:%M:%S %z')} (probed)")
    print(f"  process table: {len(t0)} rows / {len(t1)} rows across a {args.window}s window")
    print(f"  signature: parent dead-or-absent AND cpu delta <= {args.cpu_eps}s "
          f"AND age > {args.age_min} min")
    print(f"  watched names: {', '.join(WATCHED)}")
    print(f"  REPORT ONLY — no process is signalled (per a fleet ruling)")
    for n in notes:
        print(f"  note: {n}")
    print(f"  orphans: {len(orphans)}")
    for o in orphans:
        print(f"    pid {o['pid']:<7} {o['name']:<16} age {o['age_min']:>7.1f}m  "
              f"cpu {o['cpu_total_s']}s (delta {o['cpu_delta_s']})  parent {o['parent_state']}")
        print(f"      {o['cmd']}")

    if orphans and not args.no_write:
        day = now.strftime("%Y-%m-%d")
        outdir = os.path.join(args.ws, "workpapers", f"orphan-census-{day}")
        os.makedirs(outdir, exist_ok=True)
        path = os.path.join(outdir, f"census_{now.strftime('%H%M%S')}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({
                "probed_at": now.isoformat(),
                "report_only": True,
                "signature": {"age_min": args.age_min, "cpu_eps": args.cpu_eps,
                              "window_s": args.window, "watched": list(WATCHED)},
                "table_rows": [len(t0), len(t1)],
                "notes": notes,
                "orphans": orphans,
            }, fh, indent=2)
        print(f"  census written: {path}")

    return FOUND if orphans else CLEAN


if __name__ == "__main__":
    sys.exit(main())
