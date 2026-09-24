# -*- coding: utf-8 -*-
r"""outpath_reach.py — MEASURE what `outpath_gate.py` sees, instead of asserting it.

WHY
---
The gate's design note states its reach in prose: intra-module assignment-only
dataflow, write/citation/read faces, `os.path.join`/`shutil`/`tempfile`/
`json.dump`-to-handle outside the set, argument-passed destinations unreported.

⛔ Every word of that is an AUTHORED CLAIM ABOUT BEHAVIOUR — the same class of
   claim that was false in `rev5_manifest.py:40`, false in an earlier note of mine, and
   false in a planted fixture of the gate itself. A reach statement nobody ran
   is a docstring, and today's whole lesson is that docstrings lie in the
   direction their author expects.

WHAT IT DOES
------------
Each case declares what I CLAIM (`covered` / `not covered`) and is then run
through the gate's own `scan_source`. Four outcomes:

  ✅ HOLDS      claimed covered, detected      — the claim is true
  ⛔ OVERCLAIM  claimed covered, MISSED        — ⛔⛔ the dangerous direction:
                                                 §5 promises more than it does
  ✅ HONEST     claimed uncovered, missed      — the limit is real, now measured
  ⭐ UNDERCLAIM claimed uncovered, DETECTED    — reach is better than stated

Exit 0 if no OVERCLAIM, else 1. ⛔ An overclaim is the only failing outcome,
because a limit stated too generously is what gets read as coverage.
"""
import sys

import outpath_gate as G

COVERED, NOT = "covered", "not covered"

B, A = G.BARE, G.ARGV0
RB, RA = G.READ_BARE, G.READ_ARGV0
RPB = G.REPORT_BARE

CASES = [
    # -------- claims of COVERAGE, from the design note. The 4th element is the
    #          EXPECTED CLASS: presence alone is not coverage. --------
    (COVERED, "builtin open(bare,'w')",
     "fh = open('out.json', 'w')\n", {B}),
    (COVERED, "Path(bare).write_text",
     "import pathlib\npathlib.Path('o.json').write_text('{}')\n", {B}),
    (COVERED, "argv[0]-derived destination, inline",
     "import pathlib, sys\n"
     "pathlib.Path(sys.argv[0]).parent.joinpath('t.json').write_text('')\n",
     {A}),
    (COVERED, "argv[0] destination through ONE variable",
     "import pathlib, sys\n"
     "d = pathlib.Path(sys.argv[0]).parent / 't.json'\nd.write_text('')\n",
     {A}),
    (COVERED, "Path(bare).open('w') — method form",
     "import pathlib\nfh = pathlib.Path('o.txt').open('w')\n", {B}),
    (COVERED, "bare READ via builtin open",
     "d = open('in.json', encoding='utf-8').read()\n", {RB}),
    (COVERED, "bare READ via read_text",
     "import pathlib\nt = pathlib.Path('in.json').read_text()\n", {RB}),
    (COVERED, "citation riding a bare write",
     "fh = open('R.json', 'w')\nprint('wrote R.json')\n", {B, RPB}),
    (COVERED, "⛔ variable mode is a WRITE, not a read",
     "m = 'w'\nfh = open('o.json', m)\n", {B}),

    # ---------------- claims of NON-coverage, from the design note ----------------
    (NOT, "os.path.join of bare parts",
     "import os\nfh = open(os.path.join('sub', 'o.json'), 'w')\n"),
    (NOT, "shutil.copy to a bare destination",
     "import shutil\nshutil.copy(src, 'o.json')\n"),
    (NOT, "tempfile.NamedTemporaryFile",
     "import tempfile\nfh = tempfile.NamedTemporaryFile(dir='.', delete=False)\n"),
    (NOT, "json.dump into a handle from a FUNCTION",
     "import json\n"
     "def h():\n    return open('o.json', 'w')\n"
     "json.dump({}, h())\n"),
    (NOT, "destination passed as a function ARGUMENT",
     "import pathlib\n"
     "def bank(dest):\n    pathlib.Path(dest).write_text('{}')\n"
     "bank('o.json')\n"),
    (NOT, "Path.rename / replace to a bare name",
     "import pathlib\npathlib.Path(src).rename('o.json')\n"),
    (NOT, "os.makedirs with a bare name",
     "import os\nos.makedirs('outdir', exist_ok=True)\n"),

    # -------- NOT claimed either way. ⭐ The point of writing them: a hole I
    #          never mentioned is worse than one I did, because §5 reads as
    #          exhaustive. --------
    (NOT, "⭐ UNSTATED: destination built by an f-string",
     "import pathlib\nn = 'o'\npathlib.Path(f'{n}.json').write_text('{}')\n"),
    (NOT, "⭐ UNSTATED: destination via str.format",
     "import pathlib\npathlib.Path('{}.json'.format('o')).write_text('{}')\n"),
    (NOT, "⭐ UNSTATED: os.chdir moves the CWD an anchored path relies on",
     "import os, pathlib\nos.chdir('..')\n"
     "(pathlib.Path(__file__).parent / 'o.json').write_text('{}')\n"),
    # ⛔ MEASURED, not assumed: dataflow helps ARGV0 and NOT bare literals.
    #    The cure was attempted and reverted — it took the corpus from 7
    #    findings to 82, all sampled ones false. See outpath_gate._anchor_refs.
    (NOT, "⛔ ASYMMETRY: bare name through ONE variable (argv0 form IS caught)",
     "d = 'o.json'\nfh = open(d, 'w')\n"),
    (NOT, "⛔ ASYMMETRY: bare name through a two-hop chain",
     "import pathlib\na = 'o.json'\nb = a\npathlib.Path(b).write_text('{}')\n"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("MEASURED REACH of outpath_gate — %d cases\n" % len(CASES))
    tally = {"HOLDS": 0, "OVERCLAIM": 0, "HONEST": 0, "UNDERCLAIM": 0}
    over = []
    tally["MISCLASS"] = 0
    for case in CASES:
        claim, name, src = case[0], case[1], case[2]
        want = case[3] if len(case) > 3 else None
        got = {c for _, _, c, _ in G.scan_source(src, name) if c in G.BAD}
        if claim == COVERED:
            if not got:
                key = "OVERCLAIM"
            elif want is not None and got != want:
                # ⛔ THE PROBER'S OWN BLIND SPOT, until it was fixed: it asked
                #    "detected?" and not "detected AS WHAT?". A WRITE reported
                #    as a READ is present in the output and looks like reach.
                key = "MISCLASS"
            else:
                key = "HOLDS"
        else:
            key = "UNDERCLAIM" if got else "HONEST"
        tally[key] += 1
        if key in ("OVERCLAIM", "MISCLASS"):
            over.append("%s [%s]" % (name, key))
        mark = {"HOLDS": "✅ HOLDS    ", "OVERCLAIM": "⛔ OVERCLAIM",
                "HONEST": "✅ HONEST   ", "UNDERCLAIM": "⭐ UNDERCLAIM",
                "MISCLASS": "⛔ MISCLASS "}[key]
        extra = ""
        if want is not None and got != want:
            extra = "   (expected %s)" % (",".join(sorted(want)) or "clean")
        print("  %s  %-52s %s%s" % (mark, name[:52],
                                    ",".join(sorted(got)) or "(not seen)",
                                    extra))

    print("\n  " + "  ".join("%s=%d" % (k, v) for k, v in tally.items()))
    if over:
        print("\n⛔ THE REACH STATEMENT OVERPROMISES on: %s" % ", ".join(over))
        print("   Fix the gate or fix the sentence — an overstated limit is "
              "read as coverage.")
        return 1
    print("\n✅ No overclaim: every case the reach statement promises to catch "
          "is caught, and every limit it names is real.")
    print("⚠ The ⭐ UNSTATED rows are holes the sentence never mentioned — "
          "they belong in it now.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
