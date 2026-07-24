#!/usr/bin/env python3
"""Generic wave coverage checker [PROTOCOL v2.8] — the scripted-scoring rule.

Control arithmetic, coverage checks, and tallies MUST be script-produced,
never narrated (wave-census-protocol §5). This is the generic checker every
wave parameterizes; waves may extend it, never replace it with prose.

Input: a wave manifest (JSON) + the wave's consolidated results (JSON).

Manifest shape:
{
  "wave": "<wave id>",
  "slices": ["slice-a", "slice-b", ...],          // every slice that must return
  "population": ["item-1", "item-2", ...],        // every item that must be covered
  "controls": [                                    // planted positives, keyed fixtures
    {"id": "C1", "item": "item-3", "field": "notes", "occurrence": 1},
    ...
  ],
  "floors": {"aggregate": 1.0, "per_stratum": {"stratum-x": 1.0}},   // hit-rate floors
  "strata": {"stratum-x": ["C1", "C2"], ...}       // optional control grouping
}

Results shape:
{
  "returns": [{"slice": "slice-a", "items": ["item-1", ...]}, ...],
  "control_hits": ["C1", "C2", ...],               // controls the wave surfaced
  "disputed_controls": ["C3", ...],                // criterion-dispute: expected
                                                   // answer contested -> FAMILY-STOP
  "disclosures": [{"id": "D1", "text": "..."}],    // numbered, B-D convention
  "rows": [{"item": "item-1", "status": "clean|flagged|...",
            "evidence": {"quote": "<verbatim>", "anchor": "<file/line/id>"},
            "disposition": "<required when not clean>",
            "disclosures": ["D1"]}, ...]           // refs must exist
}

FAMILY-STOP (wave-census §6): a disputed control is INERT — excluded from
floor arithmetic in both directions; every stratum containing one is
reported STOPPED/UNRESOLVED (routed to the criterion owner) and its floor
is not scored until the ruling.

Exit codes: 0 = all checks pass and no disputes · 1 = violations ·
2 = no violations but FAMILY-STOP active (register state STOPPED/UNRESOLVED
— results are not final). Every number in a results memo should be
reproducible by re-running this.
"""
import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--results", required=True)
    args = ap.parse_args()

    man = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    res = json.loads(Path(args.results).read_text(encoding="utf-8"))
    flags = []

    # 1. Slice coverage: every declared slice returned, no phantom slices.
    want_slices = set(man.get("slices", []))
    got_slices = {r["slice"] for r in res.get("returns", [])}
    for s in sorted(want_slices - got_slices):
        flags.append(f"MISSING SLICE: {s} never returned")
    for s in sorted(got_slices - want_slices):
        flags.append(f"PHANTOM SLICE: {s} returned but is not in the manifest")

    # 2. Population coverage: every item read exactly once across slices.
    want_items = set(man.get("population", []))
    seen: dict = {}
    for r in res.get("returns", []):
        for it in r.get("items", []):
            seen[it] = seen.get(it, 0) + 1
    for it in sorted(want_items - set(seen)):
        flags.append(f"UNCOVERED ITEM: {it}")
    for it, n in sorted(seen.items()):
        if n > 1:
            flags.append(f"DOUBLE-READ ITEM: {it} appears in {n} slices")
        if it not in want_items:
            flags.append(f"PHANTOM ITEM: {it} not in the manifest population")

    # 3. Control arithmetic: hits vs planted, aggregate + per-stratum floors.
    #    Disputed controls (criterion-dispute) are INERT: excluded from floor
    #    arithmetic; their strata are STOPPED/UNRESOLVED (FAMILY-STOP).
    controls = {c["id"] for c in man.get("controls", [])}
    disputed = set(res.get("disputed_controls", [])) | {
        c["id"] for c in man.get("controls", []) if c.get("disputed")}
    for c in sorted(disputed - controls):
        flags.append(f"UNKNOWN DISPUTED CONTROL: {c} is not a planted control")
    disputed &= controls
    scoring = controls - disputed
    hits = set(res.get("control_hits", []))
    bogus = hits - controls
    for c in sorted(bogus):
        flags.append(f"UNKNOWN CONTROL HIT: {c} is not a planted control")
    missed = scoring - hits
    rate = (len(hits & scoring) / len(scoring)) if scoring else 1.0
    floor = man.get("floors", {}).get("aggregate", 1.0)
    print(f"controls: {len(hits & scoring)}/{len(scoring)} hit "
          f"(rate {rate:.2%}, floor {floor:.2%}"
          + (f"; {len(disputed)} disputed -> inert" if disputed else "") + ")")
    if rate < floor:
        flags.append(f"AGGREGATE FLOOR MISS: {rate:.2%} < {floor:.2%}; "
                     f"missed: {', '.join(sorted(missed))}")
    stopped = []
    for stratum, ids in man.get("strata", {}).items():
        sids = set(ids)
        sdisp = sids & disputed
        if sdisp:
            stopped.append(stratum)
            print(f"stratum {stratum}: FAMILY-STOP — STOPPED/UNRESOLVED "
                  f"(disputed: {', '.join(sorted(sdisp))} routed to the "
                  "criterion owner; controls inert, floor not scored)")
            continue
        srate = (len(hits & sids) / len(sids)) if sids else 1.0
        sfloor = man.get("floors", {}).get("per_stratum", {}).get(stratum, floor)
        print(f"stratum {stratum}: {len(hits & sids)}/{len(sids)} "
              f"(rate {srate:.2%}, floor {sfloor:.2%})")
        if srate < sfloor:
            flags.append(f"STRATUM FLOOR MISS [{stratum}]: {srate:.2%} < "
                         f"{sfloor:.2%}; missed: {', '.join(sorted(sids - hits))}")

    # 4. Results-record minimum (wave-census §8): per-row quote-anchored
    #    evidence; numbered disclosures with unique ids; row disclosure refs
    #    resolve; every non-clean row has an explicit disposition.
    disc_ids = []
    for disc in res.get("disclosures", []):
        if not disc.get("id") or not disc.get("text"):
            flags.append(f"MALFORMED DISCLOSURE: {disc} needs id + text")
        else:
            disc_ids.append(disc["id"])
    if len(disc_ids) != len(set(disc_ids)):
        flags.append("DUPLICATE DISCLOSURE IDS: "
                     + ", ".join(sorted({d for d in disc_ids
                                         if disc_ids.count(d) > 1})))
    known_disc = set(disc_ids)
    for row in res.get("rows", []):
        item = row.get("item", "?")
        ev = row.get("evidence") or {}
        if not ev.get("quote") or not ev.get("anchor"):
            flags.append(f"UNANCHORED ROW: {item} lacks quote-anchored "
                         "evidence (quote + anchor)")
        for ref in row.get("disclosures", []):
            if ref not in known_disc:
                flags.append(f"DANGLING DISCLOSURE REF: {item} cites {ref} "
                             "which is not in the disclosures list")
        if row.get("status", "clean") != "clean" and not row.get("disposition"):
            flags.append(f"UNDISPOSED ROW: {item} is "
                         f"'{row.get('status')}' with no disposition")

    print(f"slices {len(got_slices & want_slices)}/{len(want_slices)} | "
          f"items {len(want_items & set(seen))}/{len(want_items)} | "
          f"rows {len(res.get('rows', []))} | "
          f"disclosures {len(known_disc)}")
    if flags:
        print("FLAGS:")
        print("\n".join(f"  {f}" for f in flags))
        return 1
    if stopped:
        print(f"FAMILY-STOP ACTIVE: strata {', '.join(stopped)} are "
              "STOPPED/UNRESOLVED until the criterion owner rules — "
              "results are NOT final")
        return 2
    print("coverage check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
