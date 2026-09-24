#!/usr/bin/env python3
"""stop_ledger_rollup — SG8 part (b): turn the per-session stop receipts into
one machine-readable ledger plus the per-seat count token the sitrep carries.

WHAT IT READS: every plans/.stop_log.<session> the Stop path has written.
WHAT IT WRITES: ops/stop_ledger.tsv (header row first) and, on --token, the
block a sitrep edition embeds. ⚠ The TSV is REGENERATED IN FULL on every run,
not appended to -- it is a derived projection, and the append-only layer is the
per-session receipts it reads. Saying "append-only" of a file this rewrites
would mislead the next hand into treating a rewrite as corruption.

⚠ WHAT THE NUMBER MEANS, AND WHAT IT DOES NOT. stop_observer's own docstring
names a mis-count in BOTH directions and nothing here repeals it:
  UNDER — obligations living in channel entries, head dispatch regions and the
          auth-log are not ledgered, so a seat holding one counts clean.
  OVER  — a stale `state: open` plan hits at every turn boundary, and an
          in-flight dispatch (a codex round, a spawned agent) keeps a seat
          RUNNABLE while it MUST end the turn to receive the result.
So `stops_with_runnable` is a STOP COUNT on days when a seat has any open work,
not a defect count: at builder's seat on 2026-08-30 it was 4 of 4 stops, and one
of those four was a correct stop. Reporting it alone would hand the principal a number
whose good and bad cases are indistinguishable. [[honest-failure-outcomes]]

That is why the `announce` column exists beside it: the announce classes are the
triage the raw count has always needed. They are still not a defect count -- an
announcement with work genuinely in flight is a correct stop -- but they are the
narrower population, and the two are reported SEPARATELY rather than blended.

EVERY path emits a row, including unreadable logs and unresolved seats: a silent
drop would make this instrument's death look like a quiet fleet, which is the
exact failure stop_observer was written to avoid. [[lane-silence-measures-the-lane]]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

HEADER = ("date\tseat\tstops\tstops_measured\tstops_with_runnable"
          "\tannounce_census\tannounce_v2\tblocks\tsessions\tnote")

ROW_RE = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2})T\S+\s+session=(?P<session>\S+)\s+"
    r"(?:seat=(?P<seat>[A-Za-z]+)\((?P<how>[^)]*)\)|(?P<subagent>SUBAGENT-EXEMPT))")
RUNNABLE_RE = re.compile(r"\brunnable=(?P<v>\d+|n/a|skip)\b")
DECISION_RE = re.compile(r"\bdecision=(?P<v>\S+)\s*$")
CLASS_RE = re.compile(r"\bclass=(?P<v>\S+)\b")


def parse_log(path: Path):
    """Yield parsed rows. An unparseable line is YIELDED as a defect, never
    skipped — a dropped line is a silent under-count of the thing being counted."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        yield {"defect": f"unreadable:{path.name}:{exc.__class__.__name__}"}
        return
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = ROW_RE.match(raw)
        if not m:
            yield {"defect": f"unparseable-row:{path.name}"}
            continue
        if m.group("subagent"):
            continue                      # subagents own no ledger steps
        r = RUNNABLE_RE.search(raw)
        d = DECISION_RE.search(raw)
        c = CLASS_RE.search(raw)
        runnable = r.group("v") if r else None
        yield {
            "date": m.group("stamp"),
            "seat": (m.group("seat") or "").lower(),
            "session": m.group("session"),
            "runnable": runnable,
            "has_runnable": runnable not in (None, "0", "n/a", "skip"),
            "decision": d.group("v") if d else "-",
            "klass": c.group("v") if c else None,
        }


def collect(workspace: Path):
    agg = defaultdict(lambda: {
        "stops": 0, "measured": 0, "with_runnable": 0,
        "ann_census": 0, "ann_v2": 0,
        "blocks": 0, "sessions": set(), "notes": []})
    defects = []
    logs = sorted((workspace / "plans").glob(".stop_log.*"))
    for lg in logs:
        for row in parse_log(lg):
            if "defect" in row:
                defects.append(row["defect"])
                continue
            if not row["seat"]:
                continue
            k = (row["date"], row["seat"])
            a = agg[k]
            a["stops"] += 1
            a["sessions"].add(row["session"])
            # `runnable=skip` means the projection was NEVER COMPUTED on that
            # path (the guard exits before touching the ledger). Folding it in
            # as a zero would print an unmeasured seat as a clean one -- the
            # defect this instrument exists to avoid. [[honest-failure-outcomes]]
            if row["runnable"] not in ("skip", "n/a", None):
                a["measured"] += 1
            if row["has_runnable"]:
                a["with_runnable"] += 1
            dec = row["decision"]
            if dec in ("block", "would-block"):
                a["blocks"] += 1
            kl = row["klass"] or ""
            if "announce-own-act-v2" in kl:
                a["ann_v2"] += 1
            elif "announce-own-act" in kl or dec.startswith("allow-announce"):
                a["ann_census"] += 1
    return agg, defects, len(logs)


def render_rows(agg, defects):
    """⚠ A PARSE DEFECT IS NOT ATTRIBUTABLE TO A SEAT-DAY, so it does not get
    written onto one. The previous form stamped `defects=N` into the note column
    of EVERY row whenever ANY log anywhere had one bad line -- 94 rows all
    claiming the same N, none of them the row it came from. A reader lands on
    builder/2026-08-07, sees `defects=3`, and concludes builder's log had three.
    The defect is real but its OWNER is unknown by construction: an unparseable
    row is unparseable precisely because the seat could not be read out of it,
    and an unreadable file never yielded a seat at all.

    So it goes in its own row, in the same machine-readable grammar, with the
    date and seat fields explicitly `-`. The count stays in the file (dropping
    it would hide a real signal from anyone reading the TSV alone) without
    asserting a seat that was never measured.
    [[fabricated-specifics-discipline]] [[counts-and-relations-discipline]]"""
    out = [HEADER]
    for (date, seat) in sorted(agg):
        a = agg[(date, seat)]
        out.append("\t".join([
            date, seat, str(a["stops"]), str(a["measured"]),
            str(a["with_runnable"]),
            str(a["ann_census"]), str(a["ann_v2"]), str(a["blocks"]),
            str(len(a["sessions"])), "-"]))
    if defects:
        out.append("\t".join(
            ["-", "-", "0", "0", "0", "0", "0", "0", "0",
             f"unattributable-parse-defects={len(defects)}"]))
    return out


def render_token(agg, day: str) -> str:
    """The block a sitrep edition embeds. The token name is fixed so SG8's
    done_when can grep for it; the caveat ships WITH the number, in the same
    block, so a number cannot be lifted out of its bound."""
    rows = [(s, a) for (d, s), a in sorted(agg.items()) if d == day]
    lines = [f'<!-- SG8-RUNNABLE-COUNT day="{day}" -->',
             '<div class="sg8-runnable-count">',
             f'<b>stopped-with-runnable-work — {day}</b>',
             '<table><tr><th>seat</th><th>stops</th><th>with runnable</th>'
             '<th>announce</th></tr>']
    if not rows:
        # `found 0` and `empty` are different facts and must render differently.
        lines.append('<tr><td colspan="4"><i>no stop receipts for this day '
                     '— instrument silent, NOT a measured zero</i></td></tr>')
    for seat, a in rows:
        # A seat whose every stop took a path that never computed the projection
        # (orchestrator exits at `allow-orchestrator`, before the ledger is
        # touched) has NO measurement. Printing "0" there would read as a clean
        # seat; it means "not measured" and must say so.
        if a["measured"] == 0:
            wr = 'n/m'
        elif a["measured"] < a["stops"]:
            wr = f'{a["with_runnable"]} <small>of {a["measured"]} measured</small>'
        else:
            wr = str(a["with_runnable"])
        # ⚠ MEASURED, AND IT FALSIFIES THIS CELL'S OLD FALLBACK. The comment
        # here used to say the column "CANNOT be non-zero" until v2 is wired,
        # and rendered every zero as 'not wired'. But the CENSUS class is
        # tagged by the live guard today and HAS fired: ops/stop_ledger.tsv
        # carries `2026-08-18 creator ... announce_census=1`. So the sum being
        # zero is a REAL zero -- an observation -- and printing 'not wired'
        # over it tells the principal an armed instrument is absent. That is
        # the same unknown-vs-zero confusion this file guards everywhere else,
        # running in the opposite direction. A measured zero renders as 0.
        #
        # The v2 SUB-count is genuinely unpopulatable (built add-only, not yet
        # wired into the live emitter), so that bound moves to the caveat where
        # it can be stated precisely instead of overwriting the whole cell.
        # [[honest-failure-outcomes]] [[closed-enum-needs-one-key-per-namespace]]
        ann = a["ann_census"] + a["ann_v2"]
        ann_cell = str(ann)
        lines.append(f'<tr><td>{seat}</td><td>{a["stops"]}</td>'
                     f'<td>{wr}</td><td>{ann_cell}</td></tr>')
    lines += ['</table>',
              '<p class="caveat">Counts STOPS taken while the ledger showed open '
              'work — not defects. Known over-count: a seat with a dispatch in '
              'flight must end the turn to receive it. Known under-count: work '
              'living only in channel entries is not ledgered. The announce '
              'column is the narrower triage class, not a verdict. It counts the '
              'census class only: the v2 class is built but not yet '
              'wired into the live emitter, so its sub-count cannot be '
              'non-zero yet and a zero there is not evidence of absence.</p>',
              '</div>']
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--out", default="ops/stop_ledger.tsv")
    ap.add_argument("--token", metavar="YYYY-MM-DD",
                    help="print the sitrep block for this day and exit")
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()
    agg, defects, nlogs = collect(ws)

    if args.token:
        print(render_token(agg, args.token))
        if defects:
            sys.stderr.write(f"[rollup] {len(defects)} parse defect(s)\n")
        return 0

    rows = render_rows(agg, defects)
    out = ws / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    print(f"logs read      : {nlogs}")
    print(f"seat-days      : {len(agg)}")
    print(f"parse defects  : {len(defects)}")
    for d in defects[:5]:
        print(f"  {d}")
    print(f"wrote          : {out.relative_to(ws)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
