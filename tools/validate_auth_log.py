#!/usr/bin/env python3
"""Auth-log chain validator [PROTOCOL v2.5] — mechanical enforcement of the
exactly-one-landed-CONSUMED audit rule (proxy-auth-core.md) over every
memory/<role>/auth-log.md in this workspace:

  - no duplicate CONSUMED for the same consumption id (relay id or
    grant-id[/D<k>]) — a second CONSUMED for the same id is a violation
  - a relayed CONSUMED (id contains /R) must follow a RECEIVED block for
    that relay id in the SAME log
  - a RECEIVED block must reference a relay id actually RELAY-SENT in some
    log (fabricated relays fail) and must carry a source: provenance line
  - RELAY-SENT only for grants defined in the SAME log; direct CONSUMED
    only of grants defined in the SAME log (unknown ids fail — nothing is
    consumable that was never granted)
  - RELAY-SENT count per grant never exceeds the grant's scope
  - distinct direct CONSUMED ids per grant never exceed the grant's scope

This is the CI layer; the reviewer's semantic audit (words in scope, gate
class on the list, provenance) remains on top. Run from the workspace root.
Exit 0 clean, 1 on violation. Stamped by new_project.py — edit upstream.
"""
import re
import sys
from pathlib import Path

GRANT_RE = re.compile(r"^## GRANT (\S+)")
SCOPE_RE = re.compile(r"^scope:\s*(single|batch-(\d+))")
RELAY_RE = re.compile(r"^RELAY-SENT (\S+) relay=(\S+)")
RECV_RE = re.compile(r"^relay-id:\s*(\S+)")
CONS_RE = re.compile(r"^CONSUMED (\S+)")


RECV_HEAD_RE = re.compile(r"^## RECEIVED ")
SOURCE_RE = re.compile(r"^source:\s*\S+")


def parse_log(log: Path) -> dict:
    d = {"log": log, "grants": {}, "relays": {}, "received": {},
         "consumed": {}, "direct": {}, "cons_lines": []}
    cur = None
    in_recv = None  # relay id of the RECEIVED block being read
    for n, line in enumerate(
            log.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if RECV_HEAD_RE.match(line):
            cur, in_recv = None, "PENDING"
            continue
        m = GRANT_RE.match(line)
        if m:
            cur, in_recv = m.group(1), None
            d["grants"][cur] = 1
            continue
        m = SCOPE_RE.match(line)
        if m and cur:
            d["grants"][cur] = int(m.group(2)) if m.group(2) else 1
            continue
        m = RELAY_RE.match(line)
        if m:
            d["relays"].setdefault(m.group(1), set()).add(m.group(2))
            continue
        m = RECV_RE.match(line)
        if m and in_recv is not None:
            in_recv = m.group(1)
            d["received"][in_recv] = {"line": n, "has_source": False}
            continue
        if SOURCE_RE.match(line) and in_recv and in_recv != "PENDING":
            d["received"][in_recv]["has_source"] = True
            continue
        m = CONS_RE.match(line)
        if m:
            cid = m.group(1)
            d["consumed"][cid] = d["consumed"].get(cid, 0) + 1
            d["cons_lines"].append((cid, n))
            if "/R" not in cid:
                d["direct"].setdefault(cid.split("/")[0], set()).add(cid)
    return d


def check(parsed: list, bad: list) -> None:
    # global sets: every relay id actually SENT, anywhere — and every
    # consumption id, anywhere: exactly-one CONSUMED holds ACROSS logs
    # (the same relay consumed in two different roles' logs is a double
    # spend, not two local singles)
    all_sent = set()
    global_consumed = {}
    for d in parsed:
        for rids in d["relays"].values():
            all_sent |= rids
        for cid, _ in d["cons_lines"]:
            global_consumed.setdefault(cid, []).append(d["log"])
    for cid, where in sorted(global_consumed.items()):
        if len(where) > 1:
            locs = ", ".join(str(w) for w in where)
            bad.append(f"duplicate CONSUMED {cid} - {len(where)} events "
                       f"across: {locs} (exactly-one landed CONSUMED per "
                       "action, global)")
    for d in parsed:
        log = d["log"]
        for cid, n in d["cons_lines"]:
            if "/R" in cid:
                rec = d["received"].get(cid)
                if rec is None:
                    bad.append(f"{log}:{n}: CONSUMED {cid} has no RECEIVED "
                               "block in this log (record before reserve)")
                elif n < rec["line"]:
                    bad.append(f"{log}:{n}: CONSUMED {cid} appears before its "
                               f"RECEIVED block (line {rec['line']}) — a relay "
                               "must be recorded before it is reserved")
            elif cid.split("/")[0] not in d["grants"]:
                bad.append(f"{log}:{n}: direct CONSUMED {cid} of a grant not "
                           "defined in this log (direct consumes live in the "
                           "granting session's own log)")
        for gid, rids in d["relays"].items():
            if gid not in d["grants"]:
                bad.append(f"{log}: RELAY-SENT for unknown grant {gid} "
                           "(relays are appended only to the granting log)")
            elif len(rids) > d["grants"][gid]:
                bad.append(f"{log}: grant {gid} scope {d['grants'][gid]} but "
                           f"{len(rids)} distinct RELAY-SENT ids")
        for rid, info in d["received"].items():
            if rid not in all_sent:
                bad.append(f"{log}:{info['line']}: RECEIVED {rid} matches no "
                           "RELAY-SENT in any log (fabricated relay)")
            if not info["has_source"]:
                bad.append(f"{log}:{info['line']}: RECEIVED {rid} lacks a "
                           "source: provenance line")
        for gid, cids in d["direct"].items():
            if gid in d["grants"] and len(cids) > d["grants"][gid]:
                bad.append(f"{log}: grant {gid} scope {d['grants'][gid]} but "
                           f"{len(cids)} distinct direct CONSUMED ids")


def main() -> int:
    logs = sorted(Path("memory").glob("*/auth-log.md"))
    if not logs:
        print("auth-log validator: no logs found (nothing to check)")
        return 0
    bad: list = []
    check([parse_log(log) for log in logs], bad)
    if bad:
        print("auth-log chain violations:")
        print("\n".join(bad))
        return 1
    print(f"auth-log validator: {len(logs)} log(s) clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
