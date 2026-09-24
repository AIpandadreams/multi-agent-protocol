#!/usr/bin/env python3
"""rotate_log.py -- D2 flip install-step log rotation (a finding from the orchestrator's review).

NOT part of the reviewed heartbeat mesh. The mesh -- sentinel.py / join.py /
waketap.py -- is frozen at 3351d0a7 and only ever *prints* to stdout; the run
log is the schtask's `>> memory\\heartbeats\\sentinel-runs.log` redirect target.
Left alone that log grows ~70 KB/day unbounded at 30-min cadence. This is the
standalone, pre-append rotation the scheduled command runs *before* the join,
so nothing in the frozen mesh had to change to bound it.

Policy: rotate-at-2MB-keep-3 -> `.log` (live) + `.log.1` + `.log.2`; the oldest
archive is discarded. `keep` counts the live file, so keep=3 leaves 2 archives.

Usage (scheduled command, cwd = repo root):
    python tools\\heartbeat\\rotate_log.py memory\\heartbeats\\sentinel-runs.log 2097152 3

Contract (deliberate, because a rotation must NEVER take down the wake run the
scheduled command chains after it with `&&`):
  * log absent, or size <= max_bytes  -> no-op, SILENT, exit 0.
  * size > max_bytes                  -> shift .log.(keep-2)->.(keep-1) ...
                                         .log->.log.1; the next append starts a
                                         fresh .log. Prints one line to stderr.
  * per-file OSError during the shift  -> reported to stderr, that file skipped,
                                         exit STAYS 0 (best-effort; the wake runs).
  * unusable ARGUMENTS (wrong count / non-int / keep<1) -> exit 2. This is an
    install-time misconfiguration, caught by the runbook's step-5 "parked but
    installed" verification, never a steady-state runtime path.
Idempotent: a second run on an already-rotated (small) log is a no-op.
"""
import os
import sys

DEFAULT_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
DEFAULT_KEEP = 3                      # .log + .log.1 + .log.2


def rotate(path, max_bytes=DEFAULT_MAX_BYTES, keep=DEFAULT_KEEP):
    """Rotate `path` if it exceeds `max_bytes`. Returns True iff a shift ran.

    Best-effort: any per-file OSError is reported and the file skipped; the
    function never raises for filesystem trouble, so the caller's `&& join`
    always proceeds. `keep` counts the live file (keep=3 -> 2 archives).
    """
    try:
        size = os.path.getsize(path)
    except OSError:
        return False  # absent (or unstat-able) -> nothing to rotate
    if size <= max_bytes:
        return False

    archives = max(keep - 1, 0)  # number of .log.N files to retain
    # Drop the oldest beyond retention: .log.<archives> is discarded.
    oldest = "%s.%d" % (path, archives)
    if os.path.exists(oldest):
        try:
            os.remove(oldest)
        except OSError as e:
            sys.stderr.write("rotate_log: could not remove %s: %s\n" % (oldest, e))
    # Shift .log.(N-1) -> .log.N down to .log.1 -> .log.2.
    for n in range(archives - 1, 0, -1):
        src, dst = "%s.%d" % (path, n), "%s.%d" % (path, n + 1)
        if os.path.exists(src):
            try:
                os.replace(src, dst)
            except OSError as e:
                sys.stderr.write("rotate_log: could not move %s -> %s: %s\n" % (src, dst, e))
    # Finally .log -> .log.1 (only if we actually keep at least one archive).
    if archives >= 1:
        try:
            os.replace(path, "%s.1" % path)
        except OSError as e:
            sys.stderr.write("rotate_log: could not move %s -> %s.1: %s\n" % (path, path, e))
            return False
    else:
        # keep=1: no archives kept -> just truncate the live log.
        try:
            os.remove(path)
        except OSError as e:
            sys.stderr.write("rotate_log: could not truncate %s: %s\n" % (path, e))
            return False
    sys.stderr.write("rotate_log: rotated %s (was %d bytes > %d)\n" % (path, size, max_bytes))
    return True


def main(argv):
    if not (1 <= len(argv) <= 3):
        sys.stderr.write(
            "usage: rotate_log.py <logpath> [max_bytes=%d] [keep=%d]\n"
            % (DEFAULT_MAX_BYTES, DEFAULT_KEEP))
        return 2
    path = argv[0]
    try:
        max_bytes = int(argv[1]) if len(argv) >= 2 else DEFAULT_MAX_BYTES
        keep = int(argv[2]) if len(argv) >= 3 else DEFAULT_KEEP
    except ValueError:
        sys.stderr.write("rotate_log: max_bytes and keep must be integers\n")
        return 2
    if keep < 1 or max_bytes < 0:
        sys.stderr.write("rotate_log: keep must be >= 1 and max_bytes >= 0\n")
        return 2
    rotate(path, max_bytes, keep)  # best-effort; runtime trouble never fails the chain
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
