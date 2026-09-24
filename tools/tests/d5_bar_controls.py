#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Controls for D5's repaired done_when bar (the orchestrator's review, Q1).

WHAT WAS WRONG. `pick()` anchored the round tag TERMINAL before the extension
(`-R<r>[a-z]?\\.(md|txt)$`), and every opus R3 verdict is
`VERDICT_opus_V21-R3_PASS1[_v<n>].txt`. The `_PASS1` infix made all three
unmatchable, so the bar could not return green for D5 whatever any voice wrote.
⭐ AND IT EXITED 1 IN SILENCE — the same code an honest double-REJECT returns,
with zero bytes on stdout and stderr. That is the whole reason it went
unnoticed: a VOID wearing a verdict's exit code [[honest-failure-outcomes]].

⛔ THE COMMISSION REQUIRES MUTATION PROOF BOTH WAYS, and that is what legs M1/M2
are: the OLD blind case must red FOR THE NAMED REASON (not merely red), and the
`_v3` pickup must be able to go GREEN. Without M2 every leg here is equally
satisfied by a bar that rejects everything, which is exactly the failure the
original had [[control-passing-for-the-wrong-reason]].

⚠ THE REPAIR CANNOT SELF-SERVE, ASSERTED RATHER THAN PROMISED. Leg 1 drives the
LIVE round and requires rc=1 — an honest double-REJECT. A bar repair that
flipped its own step green would be the thing to fear here, so it is graded.

⚠ REACHABILITY, STATED: this file lives in tools/tests/, which the dashboard
battery does NOT glob (it globs tools/dashboard/ and tools/dashboard/tests/).
It is run by hand, exactly like floor_antecedent_controls.py beside it. That is
the known-open roster finding already routed in an earlier builder report —
recorded here so a reader does not mistake "not in the battery" for "not run".

Exit: 0 all legs pass · 1 a leg failed · 2 VOID (harness never finished).
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import traceback

REPO = pathlib.Path(__file__).resolve().parents[2]
BAR = REPO / "workpapers" / "d5-v21-freeze-round-2026-08-22" / "d5_bar_candidate.sh"

RESULTS = []
REGISTERED = ["1", "2", "3", "4", "5", "6", "7", "8", "M1", "M2"]

CONFIRM = "D5-V99-R3: CONFIRM\nEND OF VERDICT EOV-TEST\n"
REJECT = "D5-V99-R3: REJECT\nEND OF VERDICT EOV-TEST\n"


def check(leg, passed, detail):
    RESULTS.append((leg, bool(passed), "%s" % (detail,)))


def run_bar(root, bar=None):
    """-> (rc, stderr). The bar is driven as a SUBPROCESS, the way the plan runs it."""
    r = subprocess.run(["bash", str(bar or BAR), str(root)],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(REPO),
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return r.returncode, (r.stderr or "")


def fixture(td, files, ver="v99"):
    """Build a round dir. `files` maps filename -> contents."""
    d = pathlib.Path(td) / "wp" / ("d5-%s-freeze-round-2026-08-22" % ver)
    d.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (d / name).write_text(body, encoding="utf-8")
    return str(pathlib.Path(td) / "wp")


def main():
    # ── 1. THE LIVE ROUND. Ruled expectation: an HONEST double-REJECT red. ──────
    rc, err = run_bar("workpapers")
    check("1", rc == 1 and "DISPOSITION" in err and "REJECT" in err,
          "⭐ THE LIVE ROUND READS AS AN HONEST DOUBLE-REJECT (rc=%d) AND SAYS SO. "
          "This is the leg that stops the repair from self-serving: the bar it "
          "repairs still REDS builder's own step, and it now prints why instead "
          "of exiting 1 in silence. slug=%r" % (rc, err.strip()[:150]))

    with tempfile.TemporaryDirectory() as td:
        # ── 2. THE CURE ITSELF: the _PASS/_v infix is picked up and can go GREEN.
        root = fixture(td, {
            "VERDICT_codex_V99-R3.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1_v3.txt": CONFIRM,
        })
        rc, err = run_bar(root)
        check("2", rc == 0,
              "⭐ THE MUST-FIRE. A double CONFIRM whose opus verdict carries the "
              "`_PASS1_v3` infix returns GREEN (rc=%d). Without this leg every "
              "other leg here is satisfied by a bar that reds unconditionally — "
              "which is precisely what the broken bar was. err=%r"
              % (rc, err.strip()[:120]))

        # ── 3. HIGHEST v WITHIN HIGHEST PASS (the frozen spec's selection rule).
        root = fixture(td + "/a", {
            "VERDICT_codex_V99-R3.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1_v2.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1_v3.txt": REJECT,
        })
        rc, err = run_bar(root)
        check("3", rc == 1 and "REJECT" in err,
              "⭐ SELECTION IS DISCRIMINATING, NOT INCIDENTAL: with _PASS1 and "
              "_PASS1_v2 both saying CONFIRM and only _PASS1_v3 saying REJECT, the "
              "bar reds (rc=%d). It reads the HIGHEST v, not the first match, not "
              "the alphabetical last, and not a majority. A leg where every file "
              "agreed would prove nothing about which one was read. err=%r"
              % (rc, err.strip()[:120]))

        # ── 4. A plain -R3 verdict LOSES to a _PASS-tagged one.
        root = fixture(td + "/b", {
            "VERDICT_codex_V99-R3.txt": CONFIRM,
            "VERDICT_opus_V99-R3.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1_v2.txt": REJECT,
        })
        rc, _e = run_bar(root)
        check("4", rc == 1,
              "an untagged `-R3.txt` ranks BELOW a `_PASS1_v2` re-issue (rc=%d): "
              "absent _PASS ranks 0, so the re-issue supersedes what it re-issues "
              "rather than being shadowed by sort order" % rc)

        # ── 5. RED ON A SPLIT, unchanged by the repair.
        root = fixture(td + "/c", {
            "VERDICT_codex_V99-R3.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1_v3.txt": REJECT,
        })
        rc, _e = run_bar(root)
        check("5", rc == 1,
              "RED ON A SPLIT BY DESIGN is untouched by the repair (rc=%d) — "
              "convergence, not dispatch, is the step's done" % rc)

        # ── 6. THE SIDECARS. Every opus verdict has .err and .raw.json beside it.
        root = fixture(td + "/d", {
            "VERDICT_codex_V99-R3.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1_v3.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1_v9.txt.err": "",
            "VERDICT_opus_V99-R3_PASS1_v9.txt.raw.json": "{}",
        })
        rc, err = run_bar(root)
        check("6", rc == 0,
              "⛔ THE `.err` / `.raw.json` SIDECARS ARE NOT PICKED. A `_v9` sidecar "
              "outranks `_v3` on the (PASS, v) key, so if the extension anchor "
              "failed the bar would select an EMPTY file and red at NO-MARKER. It "
              "returns green (rc=%d), so the anchor holds. These files sit beside "
              "every real opus verdict in the live round. err=%r"
              % (rc, err.strip()[:120]))

        # ── 7/8. EVERY FAILURE MODE GETS ITS OWN rc AND SLUG — rc=1 is RESERVED.
        root = fixture(td + "/e", {"VERDICT_codex_V99-R3.txt": CONFIRM})
        rc_missing, err_missing = run_bar(root)
        root = fixture(td + "/f", {
            "VERDICT_codex_V99-R3.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1_v3.txt": "no disposition line here\n",
        })
        rc_marker, err_marker = run_bar(root)
        root = fixture(td + "/g", {
            "VERDICT_codex_V99-R3.txt": CONFIRM,
            "VERDICT_opus_V99-R3_PASS1_v3.txt": "D5-V99-R3: CONFIRM\n",
        })
        rc_term, err_term = run_bar(root)
        rc_nodir, err_nodir = run_bar(pathlib.Path(td) / "empty-nothing-here")
        check("7", (rc_missing, rc_marker, rc_term, rc_nodir) == (6, 7, 8, 3),
              "⭐ rc=1 IS RESERVED FOR AN HONEST DISPOSITION RED. missing verdict=%d "
              "· unparseable marker=%d · truncated (no terminator)=%d · no round "
              "dir=%d — four states that ALL returned a silent 1 before, "
              "indistinguishable from 'the voices rejected'. That conflation is "
              "what made the VOID invisible for nine days"
              % (rc_missing, rc_marker, rc_term, rc_nodir))
        check("8", all(s in e for s, e in (
                  ("NO-VERDICT", err_missing), ("NO-MARKER", err_marker),
                  ("NO-TERMINATOR", err_term), ("NO-ROUND-DIR", err_nodir))),
              "...and each NAMES itself on stderr rather than exiting mute — an "
              "exit code nobody can attribute is not a finding "
              "[[honest-failure-outcomes]]. slugs=%r"
              % [e.strip()[:40] for e in
                 (err_missing, err_marker, err_term, err_nodir)])

        # ── M1/M2. THE MUTATIONS THE COMMISSION REQUIRES, BOTH WAYS. ────────────
        # ⛔ M1 RESTORES THE OLD TERMINAL-ANCHORED REGEX in a COPY of the bar — the
        # live file is never mutated, because another seat may run this round's bar
        # at any moment [[action-object-is-controlled-surface]].
        mutant = pathlib.Path(td) / "bar_old_anchor.sh"
        src = BAR.read_text(encoding="utf-8")
        anchor = '[Vv][0-9]+-[Rr]${r}[a-z]?(_PASS[0-9]+)?(_v[0-9]+)?\\.(md|txt)$'
        old = '[Vv][0-9]+-[Rr]${r}[a-z]?\\.(md|txt)$'
        if src.count(anchor) != 1:
            check("M1", False, "MUTATION ANCHOR NOT UNIQUE (%d occurrences) — this "
                               "leg graded NOTHING" % src.count(anchor))
            check("M2", False, "not graded, anchor failed")
        else:
            mutant.write_text(src.replace(anchor, old), encoding="utf-8")
            root = fixture(td + "/h", {
                "VERDICT_codex_V99-R3.txt": CONFIRM,
                "VERDICT_opus_V99-R3_PASS1_v3.txt": CONFIRM,
            })
            rc_mut, err_mut = run_bar(root, bar=mutant)
            rc_fix, _e = run_bar(root)
            check("M1", rc_mut == 6 and "NO-VERDICT" in err_mut,
                  "⭐ THE OLD BLIND CASE REDS **FOR THE NAMED REASON**, not merely "
                  "reds: with the terminal anchor restored, the same double-CONFIRM "
                  "fixture returns rc=%d naming NO-VERDICT — it reports that it "
                  "could not FIND the opus verdict, which is the truth. Under the "
                  "original bar this identical state returned a mute rc=1 and read "
                  "as a rejection. slug=%r" % (rc_mut, err_mut.strip()[:110]))
            check("M2", rc_fix == 0 and rc_mut != rc_fix,
                  "...and the REPAIRED bar takes the same fixture GREEN (rc=%d vs "
                  "mutant rc=%d). Both directions proven on ONE fixture, so the "
                  "difference is attributable to the regex and to nothing else "
                  "[[discriminator-needs-an-independent-difference]]"
                  % (rc_fix, rc_mut))

    graded = {leg for leg, _p, _d in RESULTS}
    for leg, passed, detail in RESULTS:
        print("%s %-3s %s" % ("PASS" if passed else "FAIL", leg, detail))
    missing = [l for l in REGISTERED if l not in graded]
    if missing:
        print("VOID: registered legs never graded: %s" % ", ".join(missing),
              file=sys.stderr)
        return 2
    npass = sum(1 for _l, p, _d in RESULTS if p)
    print("\nD5 bar controls: %d pass / %d fail" % (npass, len(RESULTS) - npass))
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        print("VOID: the harness raised before grading every leg.", file=sys.stderr)
        sys.exit(2)
