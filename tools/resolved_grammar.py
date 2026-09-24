#!/usr/bin/env python3
"""resolved_grammar — the machine reader for the fleet's RESOLVED grammar.

Commission: the orchestrator's U2 item ("`evidence=` fail-closed consumer"), under a fleet ruling.

⚠ PREMISE CORRECTION, REPORTED RATHER THAN BUILT AROUND. U2 was scoped as
"every consumer of the RESOLVED grammar treats a row with no
`evidence=` field as `evidence=unknown`". Measured: the consumer set is EMPTY.
`tools/intake_inbox_watchdog.mjs:190` writes the grammar into an alert file's
header, and nothing anywhere parses a `RESOLVED` row -- the readers are seats,
by eye. So there was no consumer to harden; this module IS the first one, and
the fail-closed rule is built in from its first line rather than retrofitted.
Saying so matters: a unit reported as "consumers hardened" when no consumer
existed would be a completion claim with no instrument behind it.
[[completion-claims-need-an-instrument]]

THE GRAMMAR (the owner's proposal, 2026-08-29 §1, adopted by a fleet ruling):

    ## ✅ TRIAGE RECEIPT · <stamp> · <seat>
    - RESOLVED id=<N> · <SERVED|SUPERSEDED|UNATTRIBUTABLE|DUPLICATE> · <prose>

THE AMENDMENT (a fleet ruling, prospective): `evidence=` is REQUIRED on every
row written from the amendment's stamp forward. A row with NO `evidence=`
field reads `unknown` -- NEVER `first-hand`. Fail-closed on the absent field,
so the amendment cannot silently upgrade the 15 pre-amendment rows already on
the lane. [[invert-claim-gates-to-default-undischarged]]

⭐ THE TRAP THIS MODULE IS BUILT AGAINST, and it is live on the lane today:
the free-prose tail of a real row reads "was answered FIRST-HAND by the principal at
21:57:40 ET" (intake_to_orch_alerts_2026-08-29.md, id=108). A reader that
looked for the string "first-hand" anywhere in the row would upgrade a
pre-amendment row to first-hand on the strength of its PROSE. Evidence is read
ONLY from a `evidence=<value>` FIELD, never from the prose, and a control
below pins that with the real sentence. [[mention-is-not-use]]
"""
from __future__ import annotations

import re
import sys

#: The dispositions the grammar admits. A row carrying anything else is a
#: DEFECT, surfaced -- never coerced into the nearest neighbour, and never
#: dropped (a dropped row silently shrinks the resolved set, which is the
#: fail-OPEN direction for "still unserved = flagged minus resolved").
DISPOSITIONS = ("SERVED", "SUPERSEDED", "UNATTRIBUTABLE", "DUPLICATE")

#: The evidence values the amendment admits. `unknown` is the DEFAULT and is a
#: real value, not a null: a consumer must be able to tell "no claim was made"
#: from "a claim was made and it was weak". [[honest-failure-outcomes]]
EVIDENCE = ("first-hand", "reported", "derived", "unknown")

ABSENT = "unknown"

_ROW_RE = re.compile(
    r"^\s*[-*]\s*RESOLVED\s+id=(?P<id>\d+)\s*[·|]\s*(?P<disp>[A-Za-z-]+)\s*(?:[·|]\s*(?P<rest>.*))?$")

#: `evidence=` is read as a FIELD only: preceded by start-of-row or whitespace,
#: value taken to the next whitespace or grammar separator. A bare word in
#: prose can never satisfy this, which is the whole point.
_EVIDENCE_RE = re.compile(r"(?:^|\s)evidence=(?P<v>[A-Za-z][A-Za-z-]*)")


class Row:
    __slots__ = ("id", "disposition", "evidence", "evidence_source",
                 "prose", "defects", "raw")

    def __init__(self, id, disposition, evidence, evidence_source, prose,
                 defects, raw):
        self.id = id
        self.disposition = disposition
        self.evidence = evidence
        self.evidence_source = evidence_source
        self.prose = prose
        self.defects = defects
        self.raw = raw

    @property
    def is_first_hand(self) -> bool:
        """The ONLY sanctioned way to ask. Never compare `.evidence` by hand at
        a call site -- a call site that writes `!= "unknown"` treats a defective
        value as first-hand, which is the fail-open direction."""
        return self.evidence == "first-hand" and not self.defects

    def __repr__(self):
        return (f"Row(id={self.id}, {self.disposition}, "
                f"evidence={self.evidence!r} via {self.evidence_source})")


def parse_row(line: str) -> Row | None:
    """Parse one RESOLVED row. Returns None if the line is not a RESOLVED row
    at all (that is not a defect -- lanes carry ordinary prose)."""
    m = _ROW_RE.match(line.rstrip())
    if not m:
        return None
    defects = []
    disp = m.group("disp").upper()
    if disp not in DISPOSITIONS:
        defects.append(f"unknown-disposition:{disp}")
    rest = m.group("rest") or ""

    em = _EVIDENCE_RE.search(rest)
    if em is None:
        # ⛔ THE FAIL-CLOSED BRANCH. An absent field is `unknown`, full stop.
        evidence, source = ABSENT, "absent-field"
    else:
        v = em.group("v").lower()
        if v not in EVIDENCE:
            defects.append(f"unknown-evidence:{v}")
            evidence, source = ABSENT, "unrecognized-value"
        else:
            evidence, source = v, "field"
    return Row(int(m.group("id")), disp, evidence, source, rest, defects, line)


def parse_text(text: str):
    """Every RESOLVED row in a lane file, in order."""
    return [r for r in (parse_row(l) for l in text.splitlines()) if r]


def resolved_ids(text: str):
    """The set difference the watchdog header describes: flagged minus resolved.
    A row with defects still RESOLVES the id -- the disposition is what closes
    it, and the evidence grade is a separate question. Conflating them would
    let a bad `evidence=` value silently re-open a served item."""
    return {r.id for r in parse_text(text)}


# ------------------------------------------------------------------ controls
def _controls() -> int:
    """The control PAIR the U2 commission asks for, plus the prose trap.

    stdout is forced to UTF-8 with a replacement fallback first: the lane's own
    rows carry ✅ and ·, and on this machine the console is cp1252. A harness
    that dies encoding its own fixture reports a crash where it should report a
    verdict -- broken instrument, not a failing subject. [[honest-failure-outcomes]]"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    cases = [
        # (name, line, expect_evidence, expect_first_hand)
        ("pre-amendment row (no evidence= field) reads unknown",
         "- RESOLVED id=80 · SERVED · Ruling served in full; cursor advanced 79→80.",
         "unknown", False),
        ("post-amendment row with evidence=first-hand reads first-hand",
         "- RESOLVED id=95 · SERVED · evidence=first-hand the principal ruled it at the sitting.",
         "first-hand", True),
        # ⭐ the live trap, quoted from intake_to_orch_alerts_2026-08-29.md id=108
        ("PROSE saying FIRST-HAND does NOT upgrade a pre-amendment row",
         "- RESOLVED id=108 · SERVED · \"REQUEST DECISION\" was answered "
         "FIRST-HAND by the principal at 21:57:40 ET on 2026-08-29 as Q1 of the batch.",
         "unknown", False),
        ("evidence= with an unrecognized value falls to unknown, not through",
         "- RESOLVED id=7 · SERVED · evidence=probably prose follows",
         "unknown", False),
        ("evidence=reported is not first-hand",
         "- RESOLVED id=8 · SERVED · evidence=reported owner relayed it.",
         "reported", False),
        ("a defective disposition never reads first-hand even with the field",
         "- RESOLVED id=9 · SORTED · evidence=first-hand prose",
         "first-hand", False),
    ]
    bad = 0
    for name, line, want_ev, want_fh in cases:
        r = parse_row(line)
        if r is None:
            print(f"[FAIL] {name}: line did not parse as a RESOLVED row")
            bad += 1
            continue
        ok = (r.evidence == want_ev) and (r.is_first_hand == want_fh)
        if not ok:
            bad += 1
        print(f"[{'PASS' if ok else 'FAIL'}] {name}\n"
              f"        evidence={r.evidence!r} (want {want_ev!r}) "
              f"first_hand={r.is_first_hand} (want {want_fh}) "
              f"via={r.evidence_source} defects={r.defects}")

    # NEGATIVE CONTROL on the parser itself: ordinary lane prose must not be
    # read as a row. Without this, a parser that matched everything would pass
    # every case above. [[control-passing-for-the-wrong-reason]]
    for junk in ("- RESOLVED the merge conflict by hand",
                 "Some prose mentioning evidence=first-hand in passing.",
                 "## ✅ TRIAGE RECEIPT · 2026-08-30 · owner"):
        r = parse_row(junk)
        ok = r is None
        if not ok:
            bad += 1
        print(f"[{'PASS' if ok else 'FAIL'}] non-row is not parsed as a row: {junk[:52]!r}")

    # ⭐ REAL-CORPUS LEG. The nine cases above are strings written by the same
    # hand that wrote the regex, and they all passed while this parser returned
    # ZERO rows on the actual lane -- the separator is U+00B7 and stdin was
    # cp1252. Synthetic controls cannot catch that class, because they never
    # cross the encoding boundary the real read crosses. A parser is only shown
    # to work by running it on the file it exists to read.
    # [[green-coverage-discipline]] [[test-package-must-assert-its-own-boundary]]
    import glob
    import io
    import os
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lanes = sorted(glob.glob(os.path.join(here, "channel",
                                          "intake_to_orch_alerts_*.md")))
    if not lanes:
        print("[FAIL] real-corpus leg: no intake alert lane found -- an absent "
              "corpus is NOT a passing leg")
        bad += 1
    else:
        total = 0
        for lane in lanes:
            with io.open(lane, "r", encoding="utf-8", errors="replace") as fh:
                total += len(parse_text(fh.read()))
        ok = total > 0
        if not ok:
            bad += 1
        print(f"[{'PASS' if ok else 'FAIL'}] real-corpus leg: parsed {total} "
              f"RESOLVED row(s) across {len(lanes)} live lane file(s) "
              f"(zero would mean the parser reads nothing real)")

    print(f"\n{'GREEN' if bad == 0 else f'RED ({bad} failing)'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    if "--controls" in sys.argv:
        sys.exit(_controls())
    # The grammar's own separator is U+00B7 and the lane header carries U+2705.
    # On this machine stdin defaults to cp1252, which silently mangles both --
    # and a mangled separator makes EVERY row fail to parse while the program
    # exits 0 with no output. That is a zero-row parse indistinguishable from a
    # lane with no rows. [[green-coverage-discipline]]
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    data = sys.stdin.read()
    for r in parse_text(data):
        print(f"{r.id}\t{r.disposition}\t{r.evidence}\t{r.evidence_source}\t"
              f"{'first-hand' if r.is_first_hand else '-'}\t"
              f"{','.join(r.defects) or '-'}")
