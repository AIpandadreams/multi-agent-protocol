#!/usr/bin/env python3
"""entry_claim_lint.py — pre-publish lint for a DRAFT channel entry.

WHY THIS EXISTS. Three times in one day (2026-08-30) I published a claim whose
defect was not in the reasoning but in the *reach of the read* behind it:

  1. One lane entry restated "six enumerated doors" when there are four — read off a
     receipt instead of my own lane.
  2. Another reported the publish door as two shapes, citing
     `worker.js:1459-1460`. PUB_SHAPES is a FOUR-row enum; I quoted its last two
     and pinned line numbers that made the partial read look deliberate.
  3. A third said "I have widened it [the pre-write check]" — in the past
     tense, as an accomplished fact, while nothing had been widened. This file
     is that claim being made true, after the fact, which is the wrong order and
     is the reason the check now exists in executable form instead of as a
     resolution I intended to keep.

⛔ THE POINT: after (1) I resolved to grep my own lane before writing any entry
carrying a count. That resolution is what failed at (2) and (3). A discipline
I have to REMEMBER at the moment of writing is not a control -- it is a hope
with a good track record, and its failures are invisible precisely when I am
busy enough to need it. So it is code, and it runs on the draft.

ADVISORY BY DESIGN. This flags claims for re-derivation; it cannot know whether
a count is right. Exit 1 means "go re-derive these at the object before you
append", never "this entry is wrong". [[guard-validity-discipline]] -- a hint,
honestly labelled as one, is not a gate pretending to be one.

USAGE
  python tools/entry_claim_lint.py <draft.md>     # lint a draft; 0 clean, 1 flags
  python tools/entry_claim_lint.py --selftest     # controls; 0 pass, 1 fail
"""

import re
import sys

# ── the three checks ────────────────────────────────────────────────────────
# Each is (name, compiled regex, what to go do about it). The prompts are
# imperative and name the OBJECT to re-read, because "double-check this" is
# advice a busy author skips and "open the file and count the rows" is not.

RANGE_CITATION = re.compile(
    r"\b[\w./\\-]+\.(?:js|mjs|cjs|ts|py|ps1|sh|md|yaml|yml|json)"
    r":\d+\s*[-–]\s*\d+\b"
)

# Cardinals -- words and digits -- attached to nouns that name ENUMERABLE things.
# Bounded to 1-3 digits: a byte count or a line number is not this kind of claim.
COUNT_NOUNS = (
    r"doors?|shapes?|rows?|options?|keys?|call sites?|sites?|arms?|legs?|voices?|"
    r"entries|entry|states?|branches?|members?|fields?|cases?|clauses?|"
    r"instances?|occurrences?|callers?|seats?|lanes?|gates?|steps?"
)
COUNT_CLAIM = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d{1,3})\s+"
    r"(?:\w+\s+){0,2}?(?:" + COUNT_NOUNS + r")\b",
    re.IGNORECASE,
)

# Past-tense self-attribution of an action. This is check (3) above: the entry
# says the thing is done. If it was not done THIS TURN, the entry is a promise
# wearing the grammar of a receipt. [[announced-action-must-be-taken]]
DONE_CLAIM = re.compile(
    r"\bI(?:'ve| have)?\s+(?:now\s+)?"
    r"(?:added|widened|updated|fixed|landed|swept|encoded|wired|cured|removed|"
    r"corrected|extended|pinned|banked|closed)\b",
    re.IGNORECASE,
)

CHECKS = [
    ("RANGE-CITATION", RANGE_CITATION,
     "You cited a LINE RANGE. Open that file and find where the CONSTRUCT ends. "
     "An enum, table or array extends past the lines your eye landed on, and a "
     "pinned range makes a partial read look deliberate."),
    ("COUNT-CLAIM", COUNT_CLAIM,
     "You asserted a COUNT of something enumerable. Re-derive it at the object "
     "THIS TURN. A count carried from a receipt, a memory, or an earlier entry "
     "is stale the moment the object moves. [[carried-artifacts-expire]]"),
    ("DONE-CLAIM", DONE_CLAIM,
     "You claimed an action as COMPLETE. Did you do it this turn, before "
     "writing this? If it is queued, say so in the future tense and then go "
     "do it. [[announced-action-must-be-taken]]"),
]


def lint(text):
    """Return a list of (check_name, line_no, matched_text, guidance)."""
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for name, rx, guidance in CHECKS:
            for m in rx.finditer(line):
                out.append((name, lineno, m.group(0).strip(), guidance))
    return out


# ── controls ────────────────────────────────────────────────────────────────
# ⛔ A linter with no red-arm is a decoration: it reports "clean" on an entry it
# is structurally incapable of grading, and clean is the reassuring answer.
# Every check therefore carries BOTH a positive control (text it MUST flag) and
# a negative one (text it must NOT), so a regex that stops matching fails here
# rather than going quiet in production. [[instrument-must-prove-it-fired]]

POSITIVE = [
    ("RANGE-CITATION", "measured at `worker.js:1459-1460`, the door admits two shapes"),
    ("RANGE-CITATION", "see src/page.js:2318-2331 for the header"),
    ("COUNT-CLAIM", "the six enumerated doors are listed in the request"),
    ("COUNT-CLAIM", "PUB_SHAPES has 4 rows"),
    ("COUNT-CLAIM", "asserts exactly three textual call sites"),
    ("DONE-CLAIM", "I have widened it to flag any citation of a line RANGE."),
    ("DONE-CLAIM", "I swept the remaining censuses."),
    ("DONE-CLAIM", "I've corrected the stale pin."),
]

# Each must trip NOTHING. These are the false-positive bar: ordinary entry prose
# that a sloppier pattern would flag, which is how a lint dies -- not by missing
# defects but by crying wolf until its author stops reading it.
NEGATIVE = [
    "Commit `06ed70c` landed with 695272 bytes on disk.",
    "The battery reports 836 pass / 0 fail, rc=0.",
    "Held behind the freeze until orch says the window has closed.",
    "See src/worker.js:1455 for the enum comment.",
    "The principal ruled the direction at 13:16 -0400 and gated execution.",
    "I will widen the check before the next entry.",
    "The producer flattens to 120 chars.",
]


def selftest():
    failures = []
    for want, text in POSITIVE:
        names = {n for n, _, _, _ in lint(text)}
        if want not in names:
            failures.append("POSITIVE control did not fire [" + want + "]: " + text)
    for text in NEGATIVE:
        hits = lint(text)
        if hits:
            failures.append("NEGATIVE control tripped " +
                            str([h[0] for h in hits]) + ": " + text)
    for f in failures:
        print("SELFTEST FAIL  " + f)
    total = len(POSITIVE) + len(NEGATIVE)
    if failures:
        print("entry_claim_lint SELFTEST: RED (rc=1) - " + str(len(failures)) +
              " of " + str(total) + " controls failed")
        return 1
    print("entry_claim_lint SELFTEST: GREEN (rc=0) - " + str(len(POSITIVE)) +
          " positive + " + str(len(NEGATIVE)) + " negative controls, all as expected")
    return 0


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    if argv[1] == "--selftest":
        return selftest()
    try:
        with open(argv[1], "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        # A draft that cannot be read is NOT a clean draft. Distinct exit code:
        # an unreadable instrument input is VOID, never GREEN.
        # [[honest-failure-outcomes]]
        print("entry_claim_lint: VOID (rc=3) - cannot read draft: " + str(exc))
        return 3
    hits = lint(text)
    if not hits:
        print("entry_claim_lint: no flags in " + argv[1] +
              " (" + str(len(text.splitlines())) + " lines scanned)")
        return 0
    by_check = {}
    for name, lineno, matched, guidance in hits:
        by_check.setdefault(name, []).append((lineno, matched, guidance))
    for name in sorted(by_check):
        rows = by_check[name]
        print("")
        print("-- " + name + " - " + str(len(rows)) + " flag(s)")
        print("   " + rows[0][2])
        for lineno, matched, _ in rows:
            print("   line " + str(lineno) + ": " + matched)
    print("")
    print("entry_claim_lint: " + str(len(hits)) + " flag(s) in " + argv[1] +
          " - ADVISORY. Re-derive each at the object, then append.")
    return 1


if __name__ == "__main__":
    # The console here is cp1252. Entry prose is full of arrows and box marks,
    # so echoing a flagged line could crash the linter -- which would exit 1,
    # the SAME code as "flags found". A broken instrument must never be
    # mistakable for a finding. [[honest-failure-outcomes]]
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main(sys.argv))
