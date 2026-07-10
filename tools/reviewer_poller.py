#!/usr/bin/env python3
"""Codex-on-PC reviewer poller [PROTOCOL v2.6].

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
           default 2s) fires a sweep once a channel/ change has settled (a
           stable signature for one tick — so a half-written request is never
           read), picking a request up in a couple of ticks instead of up to
           one poll interval. A fallback sweep still runs at least every
           --interval seconds so requests arriving via a remote push (which
           don't touch the local dir until a fetch) are not missed; it skips
           any channel that is mid-write, so the half-written guarantee holds on
           the timer path too. Stdlib only — no watchdog/inotify dependency.

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
(PROTOCOL v2.6). Below is a review request file. Review it against the \
workspace's files (read-only). Verdict contract: overall ADOPT / \
ADOPT-WITH-CHANGES / REJECT, plus numbered findings tagged \
BLOCKER/MAJOR/MODERATE/MINOR with file:line and a concrete fix each. \
Only your own wording may declare convergence. Respond with ONLY the verdict \
file content (markdown), starting with a '# Verdict' heading.

--- REVIEW REQUEST ({name}) ---
"""

FIX_CONF_RE = re.compile(r"^ROUND-TYPE:\s*FIX-CONFIRMATION\b", re.MULTILINE)

FIX_CONFIRMATION_FRAMING = """\
ROUND TYPE: FIX-CONFIRMATION. Judge ONLY whether the fixes described in this \
request resolve the specific prior-round findings it names — do not open new \
scope. End your verdict with exactly one line reading CONVERGED (every named \
finding resolved) or NOT-CONVERGED (one or more still open).

"""


def build_prompt(name: str, body: str) -> str:
    """Assemble the reviewer prompt for one request body. A FIX-CONFIRMATION
    request — a body carrying a `ROUND-TYPE: FIX-CONFIRMATION` line — gets the
    fix-confirmation framing ahead of the request payload; any other request
    does not. Factored out so the marker handling is unit-testable."""
    header = PROMPT_HEADER.format(name=name)
    if FIX_CONF_RE.search(body):
        header += FIX_CONFIRMATION_FRAMING
    return header + body


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
    prompt = build_prompt(
        req.name, req.read_text(encoding="utf-8", errors="replace"))
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
        "reviewer_poller.py [PROTOCOL v2.6]*\n", encoding="utf-8")
    run(["git", "add", verdict.name], cwd=ws / "channel")
    run(["git", "commit", "-m", f"verdict: {verdict.name} (reviewer poller)"],
        cwd=ws)
    run(["git", "push"], cwd=ws)
    print(f"[poller] pushed {verdict.name}")
    return True


def cycle(workspaces, codex_cmd, dry):
    done, failed = 0, 0
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
            if review_one(ws, req, verdict, codex_cmd, dry):
                done += 1
            elif not dry:
                failed += 1
    return done, failed


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


def detect_settled(pairs, sigs, dirty):
    """Advance the change-tracking state one tick. Mutates `sigs`/`dirty` in
    place and returns the workspaces whose channel *settled* this tick — was
    dirty last tick, signature stable now. A channel whose signature changed is
    (re)marked dirty; a dirty channel that held still is cleared and reported
    settled. Pure w.r.t. everything except the two passed-in containers, so a
    fake-signature test can drive it deterministically."""
    settled_ws = []
    for w, c in pairs:
        key = str(c)
        s = dir_signature(c)
        if s != sigs[key]:
            sigs[key] = s          # still moving — record and wait
            dirty.add(key)
        elif key in dirty:
            dirty.discard(key)     # stable for a full tick — settled
            settled_ws.append(w)
    return settled_ws


def plan_sweep(pairs, settled_ws, dirty, fallback_due):
    """Decide which workspaces to sweep this tick. On a fallback (timer) tick,
    sweep every channel that is NOT mid-write (`dirty`); otherwise sweep only
    the channels that settled this tick. Either way a mid-write channel is never
    swept — that is the never-read-half-formed guarantee, and it must hold on
    the fallback path as well as the settle path. Returns [] for a no-op tick."""
    if fallback_due:
        return [w for w, c in pairs if str(c) not in dirty]
    return list(settled_ws)


def watch(workspaces, codex_cmd, dry, watch_interval, fallback_interval):
    """Event-driven loop: sweep on local channel change, plus a periodic
    fallback sweep so remote-pushed requests are still caught.

    A change is acted on only once its directory signature has *settled* —
    stayed identical for one full watch tick after first changing. A request
    file still being written has a moving (mtime_ns, size) across ticks, so it
    stays marked dirty and is excluded from BOTH the settle sweep and the
    periodic fallback sweep — the poller never reads it half-written; it adds
    at most one watch_interval of latency. (For a hard guarantee regardless of
    watch_interval, have the producer publish atomically: write a temp file
    and rename it into place.)

    Corollary: a channel is rescued from the dirty set only by *settling*, not
    by the fallback timer — a pathological producer that rewrites the channel
    on every single tick would be excluded from every sweep and never reviewed.
    That is by design (better late than a half-read verdict) and harmless for
    real producers, which stop writing once a request is complete."""
    pairs = [(w, Path(w) / "channel") for w in workspaces]
    print(f"[poller] watch mode: local changes trigger within ~{watch_interval*2:.0f}s "
          f"(one settle tick); fallback sweep every {fallback_interval}s. "
          "Ctrl-C to stop.")
    # Initial sweep clears anything already pending.
    cycle(workspaces, codex_cmd, dry)
    sigs = {str(c): dir_signature(c) for _, c in pairs}
    dirty = set()  # channels seen changing, awaiting a stable tick
    last_cycle = time.monotonic()
    while True:
        time.sleep(watch_interval)
        settled_ws = detect_settled(pairs, sigs, dirty)
        now = time.monotonic()
        fallback_due = (now - last_cycle) >= fallback_interval
        to_sweep = plan_sweep(pairs, settled_ws, dirty, fallback_due)
        if fallback_due:
            last_cycle = now
        if not to_sweep:
            continue
        cycle(to_sweep, codex_cmd, dry)
        # Re-snapshot only the swept channels: their own verdict writes (and
        # any pulled files) must not re-trigger on the next tick. Channels
        # left unswept keep their in-flight sig/dirty state intact.
        swept = set(to_sweep)
        for w, c in pairs:
            if w in swept:
                sigs[str(c)] = dir_signature(c)
                dirty.discard(str(c))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", action="append", default=[])
    ap.add_argument("--config")
    ap.add_argument("--codex-cmd", default=DEFAULT_CODEX_CMD)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--loop", action="store_true")
    mode.add_argument("--watch", action="store_true",
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
    if (args.loop or args.watch) and args.interval <= 0:
        ap.error("--interval must be > 0")
    if args.watch and args.watch_interval <= 0:
        ap.error("--watch-interval must be > 0")

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
        # --once propagates failure: exit nonzero when any attempted review
        # failed, so a scheduling wrapper can surface the outage instead of
        # reading a swallowed reviewer error as success.
        _, failed = cycle(workspaces, codex_cmd, args.dry_run)
        return 1 if failed else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
