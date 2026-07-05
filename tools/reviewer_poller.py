#!/usr/bin/env python3
"""Codex-on-PC reviewer poller [PROTOCOL v2.5].

Bridges agent workspaces to a local Codex reviewer: polls each bound
workspace repo's channel/ for unanswered review requests
(review_request_<SIDE>_r<NN>.md with no matching verdict_<SIDE>_r<NN>.md),
feeds each to the local Codex CLI, commits the verdict file back, and pushes.
Runs on the principal's PC (scheduled task or --loop). When this poller is
down, agents fall back to their bound different-model Claude reviewer per
review-core's dead-lane escalation.

Usage:
  python tools/reviewer_poller.py --workspace path/to/workspace [...] --once
  python tools/reviewer_poller.py --config poller.json --loop --interval 300
  python tools/reviewer_poller.py --config poller.json --watch
  # poller.json: {"workspaces": ["path/to/ws1", "path/to/ws2"],
  #               "codex_cmd": "codex exec --sandbox read-only -C {workspace}"}

Three run modes:
  --once   one sweep, then exit (scheduled-task friendly).
  --loop   a full sweep every --interval seconds (fixed cadence).
  --watch  event-driven: a cheap directory-signature check (--watch-interval,
           default 2s) fires a sweep the instant a channel/ changes locally,
           so a review request on the shared filesystem is picked up in
           seconds instead of up to one poll interval. A fallback full sweep
           still runs at least every --interval seconds so requests arriving
           via a remote push (which don't touch the local dir until a fetch)
           are not missed. Stdlib only — no watchdog/inotify dependency.

The poller is transport machinery, not a party: it never edits requests,
never writes channel entries, and produces ONLY verdict files authored by
Codex. Dry-run mode (--dry-run) reports what it would review without
invoking Codex or pushing.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REQ_RE = re.compile(r"^review_request_(?P<side>[A-Za-z0-9-]+)_r(?P<nn>\d+)\.md$")
DEFAULT_CODEX_CMD = "codex exec --sandbox read-only -C {workspace}"

PROMPT_HEADER = """You are the independent reviewer for a multi-agent workspace \
(PROTOCOL v2.5). Below is a review request file. Review it against the \
workspace's files (read-only). Verdict contract: overall ADOPT / \
ADOPT-WITH-CHANGES / REJECT, plus numbered findings tagged \
BLOCKER/MAJOR/MODERATE/MINOR with file:line and a concrete fix each. \
Only your own wording may declare convergence. Respond with ONLY the verdict \
file content (markdown), starting with a '# Verdict' heading.

--- REVIEW REQUEST ({name}) ---
"""


def run(cmd, cwd=None, check=True, capture=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=capture,
                          text=True, shell=isinstance(cmd, str))


def pending_requests(channel: Path):
    reqs = []
    for p in sorted(channel.iterdir()):
        m = REQ_RE.match(p.name)
        if not m:
            continue
        verdict = channel / f"verdict_{m['side']}_r{m['nn']}.md"
        if not verdict.exists():
            reqs.append((p, verdict))
    return reqs


def review_one(ws: Path, req: Path, verdict: Path, codex_cmd: str,
               dry: bool) -> bool:
    print(f"[poller] {ws.name}: reviewing {req.name} -> {verdict.name}")
    if dry:
        print("[poller] dry-run: skipping Codex + push")
        return False
    prompt = PROMPT_HEADER.format(name=req.name) + req.read_text(
        encoding="utf-8", errors="replace")
    parts = codex_cmd.format(workspace=str(ws)).split()
    # Windows: bare npm-shim names ("codex" -> codex.cmd) are invisible to
    # CreateProcess — resolve to the full path via PATH lookup.
    exe = shutil.which(parts[0])
    if exe is None:
        print(f"[poller] reviewer command '{parts[0]}' not found on PATH",
              file=sys.stderr)
        return False
    try:
        # encoding pinned: reviewer output is UTF-8; Windows' cp1252 default
        # kills the reader threads on the first curly quote (stdout -> None)
        proc = subprocess.run([exe] + parts[1:] + [prompt],
                              capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"[poller] failed to launch reviewer: {e}", file=sys.stderr)
        return False
    if proc.returncode != 0:
        err = (proc.stderr or "")[-2000:]
        print(f"[poller] Codex failed on {req.name}:\n{err}", file=sys.stderr)
        return False
    out = (proc.stdout or "").strip()
    if not out:
        print(f"[poller] Codex returned empty output on {req.name}",
              file=sys.stderr)
        return False
    if "# Verdict" in out:
        out = out[out.index("# Verdict"):]
    verdict.write_text(
        out + "\n\n*— verdict produced by the local Codex reviewer via "
        "reviewer_poller.py [PROTOCOL v2.5]*\n", encoding="utf-8")
    run(["git", "add", verdict.name], cwd=ws / "channel")
    run(["git", "commit", "-m", f"verdict: {verdict.name} (reviewer poller)"],
        cwd=ws)
    run(["git", "push"], cwd=ws)
    print(f"[poller] pushed {verdict.name}")
    return True


def cycle(workspaces, codex_cmd, dry):
    total = 0
    for w in workspaces:
        ws = Path(w)
        channel = ws / "channel"
        if not channel.is_dir():
            print(f"[poller] skip {ws}: no channel/", file=sys.stderr)
            continue
        if not dry:
            run(["git", "fetch"], cwd=ws, check=False)
            run(["git", "pull", "--rebase"], cwd=ws, check=False)
        for req, verdict in pending_requests(channel):
            total += review_one(ws, req, verdict, codex_cmd, dry)
    return total


def dir_signature(channel: Path) -> frozenset:
    """A cheap fingerprint of a channel dir: (name, mtime_ns, size) per file.

    Changes when a request/verdict is added or rewritten — the trigger for an
    event-driven sweep. No file contents are read.
    """
    sig = []
    try:
        for e in os.scandir(channel):
            if e.is_file():
                st = e.stat()
                sig.append((e.name, st.st_mtime_ns, st.st_size))
    except FileNotFoundError:
        pass
    return frozenset(sig)


def watch(workspaces, codex_cmd, dry, watch_interval, fallback_interval):
    """Event-driven loop: sweep on local channel change, plus a periodic
    fallback sweep so remote-pushed requests are still caught."""
    chans = [Path(w) / "channel" for w in workspaces]
    print(f"[poller] watch mode: local changes trigger within ~{watch_interval}s; "
          f"fallback full sweep every {fallback_interval}s. Ctrl-C to stop.")
    # Initial sweep clears anything already pending.
    cycle(workspaces, codex_cmd, dry)
    sigs = {str(c): dir_signature(c) for c in chans}
    last_cycle = time.monotonic()
    while True:
        time.sleep(watch_interval)
        changed = False
        for c in chans:
            s = dir_signature(c)
            if s != sigs[str(c)]:
                sigs[str(c)] = s
                changed = True
        now = time.monotonic()
        if changed or (now - last_cycle) >= fallback_interval:
            cycle(workspaces, codex_cmd, dry)
            last_cycle = time.monotonic()
            # Re-snapshot: the sweep's own verdict writes (and any pulled
            # files) must not re-trigger on the next tick.
            for c in chans:
                sigs[str(c)] = dir_signature(c)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", action="append", default=[])
    ap.add_argument("--config")
    ap.add_argument("--codex-cmd", default=DEFAULT_CODEX_CMD)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--watch", action="store_true",
                    help="event-driven: sweep on local channel change plus a "
                         "fallback sweep every --interval seconds")
    ap.add_argument("--interval", type=int, default=300,
                    help="--loop cadence, and --watch fallback-sweep bound")
    ap.add_argument("--watch-interval", type=float, default=2.0,
                    help="--watch directory-check cadence (seconds)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    workspaces, codex_cmd = list(args.workspace), args.codex_cmd
    if args.config:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        workspaces += cfg.get("workspaces", [])
        codex_cmd = cfg.get("codex_cmd", codex_cmd)
    if not workspaces:
        print("no workspaces given (--workspace / --config)", file=sys.stderr)
        return 2

    if args.watch:
        try:
            watch(workspaces, codex_cmd, args.dry_run,
                  args.watch_interval, args.interval)
        except KeyboardInterrupt:
            print("\n[poller] watch stopped")
    elif args.loop:
        while True:
            cycle(workspaces, codex_cmd, args.dry_run)
            time.sleep(args.interval)
    else:
        cycle(workspaces, codex_cmd, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
