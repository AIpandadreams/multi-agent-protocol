# -*- coding: utf-8 -*-
"""(25) — NEXT-OCCURRENCE SPECIMEN CAPTURE for a canary the owner watcher could
not read. (Commissioned by an orchestrator ruling.)

⛔ WHAT PROBLEM THIS EXISTS FOR. On 2026-08-26 17:48 the owner channel watcher
recorded `UNREADABLE channel/builder_to_owner_CANARY-…-174503.md bytes=1956`.
It saw the file and reported an honest outcome, but never echoed the token, so
sentinel judged `owner/chan` BLIND — correctly. The cause could not be
determined, because **canaries self-delete (~3.5 min) and the specimen was gone
before anyone looked** [[fixing-can-close-the-evidence-window]]. This tool
exists to make the NEXT occurrence diagnosable. It does not diagnose anything.

⚖ WHY THIS IS A SIDECAR AND NOT A HOOK INSIDE `watch_channel.v2.sh`, which is
what the mint's wording suggested. The watcher is not a script sitting on disk
waiting to be run — it is running RIGHT NOW as several long-lived bash
processes, one per seat, started 2026-08-22. Bash reads a running script BY
BYTE OFFSET, so editing that file in place can derange the live instances, and
they are not all mine: a mistake there takes out builder's and orch's inbound
detection as well as owner's. An instrument that risks three seats' watchers to
diagnose one seat's read failure is a bad trade.

Triggering off the watcher's OWN obs record is also stricter against the mint's
central bound — *the instrument must not change the thing under test*:
  * it never writes to the obs log, so it cannot manufacture an echo and turn a
    BLIND verdict into a false SIGHTED;
  * it never writes to `channel/`, so it cannot touch the canary lifecycle;
  * it only ever READS the specimen, so the canary's self-delete is unaffected.
Latency cost is bounded and small: detection→obs is ~6s by the watcher's own
design and this polls every few seconds, against a ~3.5 min window.

⛔ CAPTURE-PATH RULES, all load-bearing:
  1. **Bytes only, never decoded.** The specimen is written with `open(...,'rb')`
     → `write`. Nothing in this file decodes it, prints it, or matches on it.
     Interpretation is a SEPARATE unit that runs once a specimen exists.
  2. **The specimen filename NEVER contains the canary token** — it is keyed by
     timestamp and a digest. A filename carrying the token would put it where
     future greps can find it, which is how an inert artifact becomes a live
     signal.
  3. **Nothing here may raise.** This is telemetry attached to a watchdog, and
     `sentinel.py` already carries the lesson in as many words: a telemetry
     failure must never take down the thing that was trying to report a real
     problem. Every failure is recorded INTO the meta file and swallowed.
  4. **Specimens are not auto-committed.** Raw bytes of unknown provenance do
     not enter git on a timer; the diagnosis unit decides what to commit.
"""
import argparse
import hashlib
import io
import os
import sys
import time
import traceback

CANARY_MARK = "CANARY-DO-NOT-ACT-CANARY-"
DEFAULT_OBS = os.path.join("memory", "heartbeats", "owner.chan.obs")
DEFAULT_OUT = os.path.join("workpapers", "canary-unreadable-2026-08-26", "specimens")


def _utc():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def capture(path, obs_line, out_dir):
    """Snapshot `path` as raw bytes plus metadata. Returns the specimen id, or
    None if nothing could be captured. NEVER raises."""
    meta = ["# canary UNREADABLE specimen — raw capture, NOT a diagnosis",
            "captured_utc   : %s" % _utc(),
            "trigger_obs    : %s" % obs_line.strip(),
            "target_path    : %s" % path]
    blob = None
    try:
        st = os.stat(path)
        meta.append("stat_size      : %d" % st.st_size)
        meta.append("stat_mtime_utc : %s"
                    % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime)))
        meta.append("stat_mode      : %o" % st.st_mode)
    except Exception as exc:                                    # noqa: BLE001
        meta.append("stat           : FAILED (%s: %s)" % (type(exc).__name__, exc))
        meta.append("  ⚠ the file was already gone or unstattable at capture time — "
                    "this row IS the finding for this occurrence, not a tool failure")

    try:
        with open(path, "rb") as fh:                             # bytes, never text
            blob = fh.read()
        meta.append("read_bytes     : %d  (raw, undecoded)" % len(blob))
        meta.append("sha256         : %s" % hashlib.sha256(blob).hexdigest())
    except Exception as exc:                                    # noqa: BLE001
        meta.append("read_bytes     : FAILED (%s: %s)" % (type(exc).__name__, exc))
        meta.append("  ⚠ a BINARY read failed. That excludes decoding as the cause and "
                    "points at permissions, locking, or a vanish — record only")

    # A text read is attempted ONLY to capture the exception a decoder would
    # raise. Its RESULT is discarded; nothing downstream reads decoded content.
    try:
        with io.open(path, "r", encoding="utf-8") as fh:
            fh.read()
        meta.append("utf8_decode    : SUCCEEDED (so a utf-8 decode is not the cause)")
    except Exception as exc:                                    # noqa: BLE001
        meta.append("utf8_decode    : RAISED %s: %s" % (type(exc).__name__, exc))

    if blob is None and "stat           :" not in "\n".join(meta):
        pass  # nothing to key on; still write the meta below

    key = hashlib.sha256(((path or "") + obs_line).encode("utf-8")).hexdigest()[:12]
    sid = "specimen-%s-%s" % (_utc(), key)          # ⛔ never the canary filename
    try:
        os.makedirs(out_dir, exist_ok=True)
        if blob is not None:
            with open(os.path.join(out_dir, sid + ".bin"), "wb") as fh:
                fh.write(blob)
        with io.open(os.path.join(out_dir, sid + ".meta.txt"), "w",
                     encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(meta) + "\n")
    except Exception:                                           # noqa: BLE001
        sys.stderr.write("[canary-capture] could not write specimen %s:\n%s\n"
                         % (sid, traceback.format_exc()))
        return None
    return sid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--obs", default=DEFAULT_OBS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--poll", type=float, default=5.0)
    ap.add_argument("--once", action="store_true",
                    help="scan from position 0 and exit (used by the control)")
    a = ap.parse_args()

    if not os.path.isfile(a.obs):
        sys.stderr.write("[canary-capture] INSTRUMENT-BROKEN: %s absent — this tool "
                         "cannot arm, and its silence would otherwise look like "
                         "'no occurrences'\n" % a.obs)
        return 2

    pos = 0 if a.once else os.path.getsize(a.obs)
    print("[canary-capture] armed on %s from byte %d; out=%s; poll=%ss"
          % (a.obs, pos, a.out, a.poll))
    sys.stdout.flush()

    while True:
        try:
            size = os.path.getsize(a.obs)
            if size > pos:
                with io.open(a.obs, "r", encoding="utf-8", errors="replace",
                             newline="") as fh:
                    fh.seek(pos)
                    chunk = fh.read()
                pos = size
                for line in chunk.splitlines():
                    if "UNREADABLE" not in line or CANARY_MARK not in line:
                        continue
                    # field 3 of `<ts> UNREADABLE <path> bytes=<n>`
                    parts = line.split()
                    target = next((p for p in parts if CANARY_MARK in p), None)
                    if not target:
                        continue
                    sid = capture(target, line, a.out)
                    print("[canary-capture] %s specimen=%s target=%s"
                          % ("CAPTURED" if sid else "CAPTURE-FAILED", sid, target))
                    sys.stdout.flush()
        except Exception:                                       # noqa: BLE001
            # Rule 3: never die. A capture tool that crashes leaves the next
            # occurrence undiagnosable AND looks like "no occurrence".
            sys.stderr.write("[canary-capture] non-fatal scan error:\n%s\n"
                             % traceback.format_exc())
            sys.stderr.flush()
        if a.once:
            return 0
        time.sleep(a.poll)


if __name__ == "__main__":
    sys.exit(main())
