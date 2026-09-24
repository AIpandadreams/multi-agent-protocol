#!/usr/bin/env python3
"""fleet_ledger.py -- prerequisite instrument (per a fleet ruling): fleet commission ledger.

Append-only TSV of top-level commissions. Header:
  commission_id, authorized_at, started_at, top_level_unit_id, artifact_pin,
  converged_at, principal_ready_at, principal_resolved_at, owner, status

UNIT DEFINITION DOCTRINE (fleet ruling): one TOP-LEVEL commission is counted
ONCE, at convergence. Cure rounds, subparts, reseals, re-reviews, and any
other descendant activity NEVER mint rows -- they are updates (`set`) to
the one top-level row, or nothing. If work has a parent commission, it has
no row of its own; top_level_unit_id names the single countable unit.

Append-only mechanics: `set` never rewrites a line. It resolves the latest
row for the commission_id, copies it, changes ONE field, and APPENDS the
new full row. The latest row per commission_id wins on read; every prior
row stays in the file as history.

Usage:
  python tools/fleet_ledger.py open --commission <id> --authorized-at <ISO> \
      --owner <who> [--field value overrides via set afterwards] [--ledger <path>]
  python tools/fleet_ledger.py set --commission <id> --field <col> --value <v> \
      [--ledger <path>]
  python tools/fleet_ledger.py report [--since <ISO>] [--ledger <path>]

Report prints: open commissions (status not in {closed, resolved, dropped}),
oldest unstarted (authorized_at set, started_at empty), converged-since
count (converged_at >= --since), and principal-ready queue depth
(principal_ready_at set, principal_resolved_at empty).

Exit codes: 0 ok; 2 usage/unknown field or commission.
"""

import argparse
import os
import sys

COLUMNS = ["commission_id", "authorized_at", "started_at", "top_level_unit_id",
           "artifact_pin", "converged_at", "principal_ready_at", "principal_resolved_at",
           "owner", "status"]
HEADER = "\t".join(COLUMNS) + "\n"
CLOSED_STATUSES = {"closed", "resolved", "dropped"}
DEFAULT_LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "fleet_ledger.tsv")


def ensure_ledger(path):
    if not os.path.exists(path):
        with open(path, "ab") as f:
            f.write(HEADER.encode("utf-8"))


def read_rows(path):
    """All data rows, in file order, as dicts."""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8", newline="") as f:
        for i, line in enumerate(f):
            if i == 0:
                continue
            parts = line.rstrip("\r\n").split("\t")
            if len(parts) != len(COLUMNS):
                continue
            rows.append(dict(zip(COLUMNS, parts)))
    return rows


def resolve_latest(rows):
    """Latest row per commission_id wins (file order = append order)."""
    latest = {}
    for r in rows:
        latest[r["commission_id"]] = r
    return latest


def append_row(path, row):
    """Byte-append one full row; never rewrites existing content."""
    ensure_ledger(path)
    vals = [(row.get(c, "") or "").replace("\t", " ").replace("\n", " ")
            for c in COLUMNS]
    with open(path, "ab") as f:
        f.write(("\t".join(vals) + "\n").encode("utf-8"))


def cmd_open(args):
    row = {c: "" for c in COLUMNS}
    row["commission_id"] = args.commission
    row["authorized_at"] = args.authorized_at
    row["owner"] = args.owner
    row["status"] = args.status
    append_row(args.ledger, row)
    print("opened %s (owner=%s, authorized_at=%s)"
          % (args.commission, args.owner, args.authorized_at))
    return 0


def cmd_set(args):
    if args.field not in COLUMNS:
        sys.stderr.write("unknown field %r (columns: %s)\n"
                         % (args.field, ", ".join(COLUMNS)))
        return 2
    if args.field == "commission_id":
        sys.stderr.write("refusing to rewrite commission_id via set\n")
        return 2
    latest = resolve_latest(read_rows(args.ledger))
    if args.commission not in latest:
        sys.stderr.write("unknown commission_id %r (open it first)\n"
                         % args.commission)
        return 2
    new = dict(latest[args.commission])
    new[args.field] = args.value
    append_row(args.ledger, new)  # supersedes by APPEND; prior rows remain
    print("set %s.%s = %s (superseding row appended)"
          % (args.commission, args.field, args.value))
    return 0


def cmd_report(args):
    latest = resolve_latest(read_rows(args.ledger))
    rows = list(latest.values())

    open_rows = [r for r in rows if r["status"] not in CLOSED_STATUSES]
    print("open commissions (%d):" % len(open_rows))
    for r in sorted(open_rows, key=lambda r: r["commission_id"]):
        print("  %s  owner=%s  status=%s  authorized_at=%s"
              % (r["commission_id"], r["owner"], r["status"] or "-",
                 r["authorized_at"] or "-"))

    unstarted = [r for r in open_rows if r["authorized_at"] and not r["started_at"]]
    if unstarted:
        oldest = min(unstarted, key=lambda r: r["authorized_at"])
        print("oldest unstarted: %s (authorized_at=%s, owner=%s) [of %d unstarted]"
              % (oldest["commission_id"], oldest["authorized_at"],
                 oldest["owner"], len(unstarted)))
    else:
        print("oldest unstarted: none")

    if args.since:
        n = sum(1 for r in rows if r["converged_at"] and r["converged_at"] >= args.since)
        print("converged since %s: %d" % (args.since, n))
    else:
        print("converged since: (no --since given)")

    ready = [r for r in rows if r["principal_ready_at"] and not r["principal_resolved_at"]]
    print("principal-ready queue depth: %d" % len(ready))
    for r in sorted(ready, key=lambda r: r["principal_ready_at"]):
        print("  %s  ready_at=%s" % (r["commission_id"], r["principal_ready_at"]))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    po = sub.add_parser("open", help="open a new top-level commission row")
    po.add_argument("--commission", required=True)
    po.add_argument("--authorized-at", required=True, dest="authorized_at")
    po.add_argument("--owner", required=True)
    po.add_argument("--status", default="open")
    po.add_argument("--ledger", default=DEFAULT_LEDGER)
    po.set_defaults(func=cmd_open)

    ps = sub.add_parser("set", help="update one field by appending a superseding row")
    ps.add_argument("--commission", required=True)
    ps.add_argument("--field", required=True)
    ps.add_argument("--value", required=True)
    ps.add_argument("--ledger", default=DEFAULT_LEDGER)
    ps.set_defaults(func=cmd_set)

    pr = sub.add_parser("report", help="resolve latest rows and report queues")
    pr.add_argument("--since", default="")
    pr.add_argument("--ledger", default=DEFAULT_LEDGER)
    pr.set_defaults(func=cmd_report)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
