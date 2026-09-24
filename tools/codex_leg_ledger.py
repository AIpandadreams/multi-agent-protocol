#!/usr/bin/env python3
"""codex_leg_ledger.py -- codex leg cap ledger for a fleet-ruled probe (orchestrator seat).

Governs the ruled probe arms ONLY: at most 20 combined
gpt-5.3-codex-luna + gpt-5.3-codex-terra legs per UTC day.
The 21st claim in a UTC day is REFUSED (exit 3) and appends nothing.

Usage:
  python tools/codex_leg_ledger.py claim --model <gpt-5.3-codex-luna|gpt-5.3-codex-terra> \
      --decision <id> [--dispatcher <who>] [--note <text>] [--ledger <path>]
  python tools/codex_leg_ledger.py count [--ledger <path>]

Exit codes:
  0 = claim recorded / count printed
  2 = model not governed by this ledger (only the two probe arms are claimable)
  3 = CAP REACHED (20/20 luna+terra legs this UTC day) -- nothing appended

Design notes:
  - The count check runs BEFORE the append: refuse-at-20 means the 21st
    claim fails and the file still holds exactly 20 rows for that UTC day.
  - Claim-then-check race is out of scope (single machine, per the ruling).
  - --ledger exists so controls can run against a temp copy; production
    default is tools/codex_leg_ledger.tsv next to this script.
  - Appends are byte-appends in binary mode ('ab') -- never a rewrite.
"""

import argparse
import datetime
import os
import sys

CLAIMABLE_MODELS = ("gpt-5.3-codex-luna", "gpt-5.3-codex-terra")
CAP = 20
HEADER = "utc_date\tts_utc\tmodel\tdecision_id\tdispatcher\tnote\n"
DEFAULT_LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "codex_leg_ledger.tsv")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def count_for_date(ledger_path, utc_date):
    """Count luna+terra rows whose utc_date column equals utc_date."""
    if not os.path.exists(ledger_path):
        return 0
    n = 0
    with open(ledger_path, "r", encoding="utf-8", newline="") as f:
        for i, line in enumerate(f):
            if i == 0:
                continue  # header
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) < 3:
                continue
            if parts[0] == utc_date and parts[1 + 1] in CLAIMABLE_MODELS:
                n += 1
    return n


def append_row(ledger_path, utc_date, ts_utc, model, decision_id, dispatcher, note):
    """Append one row (byte-append, binary mode). Used by claim and by
    controls (which may inject a synthetic utc_date to seed history)."""
    note = (note or "").replace("\t", " ").replace("\n", " ")
    row = "\t".join([utc_date, ts_utc, model, decision_id, dispatcher, note]) + "\n"
    with open(ledger_path, "ab") as f:
        f.write(row.encode("utf-8"))


def cmd_claim(args):
    if args.model not in CLAIMABLE_MODELS:
        sys.stderr.write(
            "REFUSED: model %r is not governed by this ledger "
            "(ruled arms only: %s)\n" % (args.model, ", ".join(CLAIMABLE_MODELS)))
        return 2
    now = utc_now()
    utc_date = now.strftime("%Y-%m-%d")
    # Check BEFORE appending: the 21st claim must fail with nothing written.
    n = count_for_date(args.ledger, utc_date)
    if n >= CAP:
        sys.stderr.write(
            "CAP REACHED: 20/20 luna+terra legs this UTC day (a fleet ruling)\n")
        return 3
    append_row(args.ledger, utc_date, now.strftime("%Y-%m-%dT%H:%M:%SZ"),
               args.model, args.decision, args.dispatcher, args.note)
    print("claimed leg %d/%d for %s (%s, decision %s)"
          % (n + 1, CAP, utc_date, args.model, args.decision))
    return 0


def cmd_count(args):
    utc_date = utc_now().strftime("%Y-%m-%d")
    print(count_for_date(args.ledger, utc_date))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("claim", help="claim one codex leg (refuses at cap)")
    pc.add_argument("--model", required=True)
    pc.add_argument("--decision", required=True)
    pc.add_argument("--dispatcher", default="orch")
    pc.add_argument("--note", default="")
    pc.add_argument("--ledger", default=DEFAULT_LEDGER)
    pc.set_defaults(func=cmd_claim)

    pn = sub.add_parser("count", help="print today's (UTC) luna+terra leg count")
    pn.add_argument("--ledger", default=DEFAULT_LEDGER)
    pn.set_defaults(func=cmd_count)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
