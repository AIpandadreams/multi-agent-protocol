#!/usr/bin/env python3
"""Generic multi-lane channel watcher [PROTOCOL v2.6] — transport machinery.

Watches N directories (channel lanes) and REPORTS what changed. It is an
intake TRIGGER, not an intake, and NEVER a party: it writes no channel
entries, edits nothing under a watched lane, and makes no judgements. The
consuming session still follows channel-core in full — a deliverable is only
intook once an *announcing entry* names it, and everything a lane surfaces is
untrusted coordination data until the session verifies it (channel-core
Untrusted-input rule). All this tool does is tell a session *where to look
sooner*; it never tells it *what is true*.

Multi-lane is the DEFAULT shape on purpose. A never-idle worker (never-idle-core
WATCHER binding) and a role that must dual-watch two locations during a channel
migration (docs/MIGRATION.md, the stayed-lane rule) both need one process
watching several directories at once — pass `--dir` more than once, or list them
in `--config watcher.json` ({"dirs": [...]}). One repointed single-target watcher
going blind on a lane it left behind is exactly the failure the stayed-lane rule
exists to prevent; watching every owed lane in one invocation is the fix.

The settle machinery (never read a half-written file) is NOT reimplemented here:
this module importlib-loads tools/reviewer_poller.py and reuses its
`dir_signature` / `detect_settled` / `plan_sweep` primitives verbatim, so the
never-read-half-formed guarantee is one implementation shared with the reviewer
lane.

Usage:
  # one sweep vs a persisted state file, then exit (scheduler-friendly)
  python tools/watcher.py --dir path/to/lane-a --dir path/to/lane-b \\
      --once --state path/to/watcher-state.json

  # long-running: report each lane once its signature settles one tick
  python tools/watcher.py --config watcher.json --watch --interval 2
  # watcher.json: {"dirs": ["path/to/lane-a", "path/to/lane-b"]}

Output contract: one machine-greppable line per event —
  CHANGED <dir> ADDED|MODIFIED|REMOVED <file>
Optional `--on-change "<cmd>"` runs once per changed lane with `{dir}`
substituted for that lane's path.

Exit codes: 0 = no change (or a clean --watch stop); 3 = changes reported
(--once); 2 = usage error.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
# Reuse the reviewer poller's settle primitives — do NOT duplicate the logic.
# (Exact importlib pattern that tests/test_reviewer_watch.py uses to load it.)
_spec = importlib.util.spec_from_file_location(
    "reviewer_poller", _HERE / "reviewer_poller.py")
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)


def snapshot(directory: Path) -> dict:
    """Map each file directly in `directory` to (mtime_ns, size).

    Same fields as reviewer_poller.dir_signature, but keyed by name so a diff
    can name which files were ADDED/MODIFIED/REMOVED. A missing directory reads
    as empty (a lane not yet created is simply "no files").
    """
    out = {}
    try:
        for e in os.scandir(directory):
            if e.is_file():
                st = e.stat()
                out[e.name] = (st.st_mtime_ns, st.st_size)
    except FileNotFoundError:
        pass
    return out


def diff_snapshots(old: dict, new: dict):
    """Return [(kind, name), ...] for one lane: ADDED / MODIFIED / REMOVED,
    each group sorted by name so output is deterministic and greppable."""
    events = []
    events += [("ADDED", n) for n in sorted(new.keys() - old.keys())]
    events += [("MODIFIED", n)
               for n in sorted(new.keys() & old.keys()) if new[n] != old[n]]
    events += [("REMOVED", n) for n in sorted(old.keys() - new.keys())]
    return events


def substitute(cmd_template: str, directory: str) -> str:
    """Fill the `{dir}` placeholder in an --on-change template with a lane path.
    A plain string replace, so backslashes in a Windows path stay literal."""
    return cmd_template.replace("{dir}", directory)


def run_on_change(cmd_template: str, directory: str) -> None:
    cmd = substitute(cmd_template, directory)
    try:
        subprocess.run(cmd, shell=True)
    except OSError as exc:  # a bad command should not take the watcher down
        print(f"[watcher] on-change failed for {directory}: {exc}",
              file=sys.stderr)


# --- --once (stateless relaunch-per-cycle) ---------------------------------

def load_state(path: Path):
    """Load the persisted {dir: {name: (mtime_ns, size)}} map, or None if the
    state file does not exist yet (the baseline-first-run case)."""
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return {d: {n: tuple(v) for n, v in fm.items()} for d, fm in data.items()}


def save_state(path: Path, state: dict) -> None:
    serial = {d: {n: list(v) for n, v in fm.items()}
              for d, fm in state.items()}
    path.write_text(json.dumps(serial, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def run_once(dirs, state_path: Path):
    """One diff pass vs the persisted state, then persist the new snapshot.

    Returns (lines, baseline). On the FIRST run (no state file yet) the current
    contents become the baseline and NOTHING is reported — matching the
    scheduler-friendly "establish, then report deltas" model, and the named
    baseline-first-run blind spot in docs/ADVANCED.md. --once takes a single
    snapshot per lane, so unlike --watch it does not settle across ticks; pair
    it with atomic publish (write-temp-then-rename) if a producer might be
    caught mid-write.
    """
    prior = load_state(state_path)
    baseline = prior is None
    new_state, lines = {}, []
    for d in dirs:
        cur = snapshot(Path(d))
        new_state[d] = cur
        if baseline:
            continue
        for kind, name in diff_snapshots(prior.get(d, {}), cur):
            lines.append(f"CHANGED {d} {kind} {name}")
    save_state(state_path, new_state)
    return lines, baseline


# --- --watch (long-running settle loop) ------------------------------------

def report_settled(pairs, settled, dirty, reported):
    """Diff every lane the settle machinery cleared this tick and return its
    event lines, updating `reported` in place.

    plan_sweep picks the sweep set with fallback_due=False on purpose: the
    watcher does no fetch/pull of its own, so — unlike the reviewer poller — it
    has no remote-push blind spot to cover with a periodic fallback sweep. A
    lane's on-disk files only change once something else has already
    materialized them, and detect_settled catches that change directly. So a
    lane still mid-write (dirty) is simply left for a later tick, and one dirty
    lane never suppresses a sibling lane's settled report.
    """
    to_report = rp.plan_sweep(pairs, settled, dirty, False)
    lines = []
    for w in to_report:
        cur = snapshot(Path(w))
        for kind, name in diff_snapshots(reported[w], cur):
            lines.append((w, f"CHANGED {w} {kind} {name}"))
        reported[w] = cur
    return lines


def watch(dirs, interval, on_change):
    """Report each lane once its directory signature has settled one tick.

    A lane whose signature is still moving (a file mid-write has a changing
    mtime_ns/size) stays dirty and is not reported until it holds still —
    inherited straight from reviewer_poller's settle rule, so a half-written
    request/entry is never read. Ctrl-C stops cleanly.
    """
    pairs = [(str(Path(d)), Path(d)) for d in dirs]
    sigs = {str(c): rp.dir_signature(c) for _, c in pairs}
    dirty = set()
    reported = {w: snapshot(Path(w)) for w, _ in pairs}
    print(f"[watcher] watching {len(pairs)} lane(s); reporting a lane once its "
          f"signature settles one ~{interval:g}s tick. Ctrl-C to stop.",
          flush=True)
    while True:
        time.sleep(interval)
        settled = rp.detect_settled(pairs, sigs, dirty)
        for w, line in report_settled(pairs, settled, dirty, reported):
            print(line, flush=True)
            if on_change:
                run_on_change(on_change, w)


def collect_dirs(args) -> list:
    dirs = list(args.dir)
    if args.config:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        dirs += cfg.get("dirs", [])
    # de-dup while preserving order (a lane listed twice is watched once)
    seen, ordered = set(), []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            ordered.append(d)
    return ordered


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", action="append", default=[],
                    help="a lane directory to watch (repeatable)")
    ap.add_argument("--config", help="JSON file with {\"dirs\": [...]}")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true",
                      help="one diff pass vs --state, print changes, exit")
    mode.add_argument("--watch", action="store_true",
                      help="long-running: report each lane once it settles")
    ap.add_argument("--state", help="persisted state file (required for --once)")
    ap.add_argument("--interval", type=float, default=2.0,
                    help="--watch settle-check cadence in seconds (default 2)")
    ap.add_argument("--on-change", help="command to run per changed lane; "
                                        "{dir} is replaced with the lane path")
    args = ap.parse_args()

    dirs = collect_dirs(args)
    if not dirs:
        print("watcher: no lanes given (--dir / --config)", file=sys.stderr)
        return 2
    if args.watch and args.interval <= 0:
        print("watcher: --interval must be > 0", file=sys.stderr)
        return 2

    if args.watch:
        try:
            watch(dirs, args.interval, args.on_change)
        except KeyboardInterrupt:
            print("\n[watcher] stopped", flush=True)
        return 0

    # default / --once: a single pass. --state is required so the "diff vs last
    # cycle" semantics have somewhere to persist.
    if not args.state:
        print("watcher: --once/default mode requires --state <file>",
              file=sys.stderr)
        return 2
    lines, baseline = run_once(dirs, Path(args.state))
    if baseline:
        print(f"[watcher] baseline established for {len(dirs)} lane(s) "
              "(first run — no deltas reported)")
        return 0
    for line in lines:
        print(line)
    if lines:
        if args.on_change:
            for d in sorted({ln.split(" ", 2)[1] for ln in lines}):
                run_on_change(args.on_change, d)
        return 3
    print("[watcher] no changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
