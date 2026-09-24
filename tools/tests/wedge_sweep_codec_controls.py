#!/usr/bin/env python3
"""Codec controls for tools/custody/wedge_sweep.py  (owner DP8, 2026-08-18).

WHAT THIS GUARDS, AND WHY IT IS NOT A UNIT TEST OF THE SWEEP.

  The sweep's unencodable glyphs sit ONLY on the FINDING branch. A machine with
  no stalled session never reaches them, so the tool ran green for weeks
  BECAUSE IT HAD NOTHING TO SAY, and would have died the first time it did.
  A control that only exercises the quiet path re-creates exactly that
  false green, so every leg here drives a REAL STALL through the real main().

  Measured on the pre-fix object, 2026-08-18:
    * stdout was 0 BYTES -- not a truncated line. Block-buffered stdout never
      flushes, so the crash destroys every line printed BEFORE it as well.
    * the crash exits 1, which is this tool's OWN alarm code
      (`return 1 if stalls else 0`) -- so a monitor keyed on the exit code
      cannot distinguish "stall found" from "died trying to report one".

  ⛔ LEG 4 IS THE ONE THAT MATTERS. A green here means nothing unless the same
     harness goes RED on the pre-fix source, so leg 4 recovers the pre-fix
     object from git and asserts it DIES. Without it this file would pass on a
     tool that had never been fixed at all
     [[control-passing-for-the-wrong-reason]] [[mutation-test-discipline]].

Run:  python tools/tests/wedge_sweep_codec_controls.py
Exit: 0 all legs pass, 1 otherwise.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "custody" / "wedge_sweep.py"
PRE_FIX_REF = "17faa78a8"          # last commit BEFORE the DP8 codec cure
TOOL_RELPATH = "tools/custody/wedge_sweep.py"

STALL_AT = "2026-08-18T07:00:00-04:00"
NOW_AT = "2026-08-18T08:30:00-04:00"   # 5400s later: past --stall-s, under the
                                       # 14400s abandoned ceiling => a STALL


def _fixture(tmp: Path) -> tuple[Path, Path, str]:
    """A projects-dir whose one transcript ends on an outstanding tool call."""
    proj = tmp / "projects"
    proj.mkdir(parents=True, exist_ok=True)
    rec = {
        "type": "assistant",
        "timestamp": STALL_AT,
        "message": {"content": [{"type": "tool_use", "name": "Bash", "id": "tu_1"}]},
    }
    (proj / "deadbeefcafe1234.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
    procs = tmp / "procs.json"
    procs.write_text("[]", encoding="utf-8")   # testing seam: no live processes
    now = str(datetime.fromisoformat(NOW_AT).timestamp())
    return proj, procs, now


def _run(script: Path, proj: Path, procs: Path, now: str, encoding: str):
    env = dict(os.environ, PYTHONIOENCODING=encoding)
    return subprocess.run(
        [sys.executable, str(script), "--repo", str(REPO),
         "--projects-dir", str(proj), "--procs-from", str(procs), "--now", now],
        capture_output=True, env=env,          # capture => redirected => cp1252
    )


def main() -> int:
    failures: list[str] = []

    def check(leg: str, ok: bool, detail: str) -> None:
        print(("  PASS  " if ok else "  FAIL  ") + leg + " :: " + detail)
        if not ok:
            failures.append(leg)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        proj, procs, now = _fixture(tmp)

        # -- leg 1: the finding survives a cp1252 console -------------------
        r = _run(TOOL, proj, procs, now, "cp1252")
        check("1 cure/stall-cp1252", r.returncode == 1 and len(r.stdout) > 0
              and b"Traceback" not in r.stderr,
              "rc=%d stdout=%dB stderr=%dB (expect rc=1, stdout>0, no traceback)"
              % (r.returncode, len(r.stdout), len(r.stderr)))

        # -- leg 2: the ANSWER does not depend on the glyph -----------------
        # errors="replace" turns the glyph into '?'; an operator grepping for
        # the marker must still find the row, so the verdict carries an ASCII
        # token. This is the leg that survives a codec we have not thought of.
        check("2 cure/ascii-token", r.stdout.startswith(b"STALL "),
              "first stdout line starts with the ASCII token 'STALL ' -> %r"
              % r.stdout.split(b"\n")[0][:48])

        # -- leg 3: the quiet path is untouched -----------------------------
        empty = tmp / "empty"
        empty.mkdir()
        q = _run(TOOL, empty, procs, now, "cp1252")
        check("3 cure/quiet-clean", q.returncode == 0 and b"Traceback" not in q.stderr,
              "rc=%d (expect 0) stderr=%dB" % (q.returncode, len(q.stderr)))

        # -- leg 4: POSITIVE CONTROL — the pre-fix object MUST die ----------
        pre = tmp / "wedge_sweep_prefix.py"
        try:
            blob = subprocess.run(
                ["git", "show", "%s:%s" % (PRE_FIX_REF, TOOL_RELPATH)],
                capture_output=True, cwd=str(REPO), check=True).stdout
            pre.write_bytes(blob)
            p = _run(pre, proj, procs, now, "cp1252")
            died = (b"UnicodeEncodeError" in p.stderr)
            lost = (len(p.stdout) == 0)
            check("4 control/pre-fix-RED", died and lost,
                  "pre-fix rc=%d stdout=%dB UnicodeEncodeError=%s "
                  "(expect stdout=0B and the encode error — if this PASSES "
                  "quietly the harness is not keyed to the defect)"
                  % (p.returncode, len(p.stdout), died))
            # the crash is exit-code-indistinguishable from the healthy alarm
            check("4b control/rc-collision", p.returncode == r.returncode,
                  "pre-fix rc=%d == cured-alarm rc=%d — documents WHY the exit "
                  "code cannot be the detector" % (p.returncode, r.returncode))
        except subprocess.CalledProcessError as e:
            check("4 control/pre-fix-RED", False,
                  "could not recover %s:%s from git (%s)"
                  % (PRE_FIX_REF, TOOL_RELPATH, e))

    print()
    if failures:
        print("RESULT FAIL legs=%d (%s)" % (len(failures), ", ".join(failures)))
        return 1
    print("RESULT PASS legs=5")
    return 0


if __name__ == "__main__":
    sys.exit(main())
