"""builder (2026-08-30) — stop_ledger_rollup had NO test at all.

The module shipped at 8c6254855 as SG8 part (b) and renders a per-seat NUMBER
into fleet sitreps. `tools/plan_gate/tests/` held 28 test files and none of them
touched it: a figure the principal reads as fact, with no instrument on it.
That absence is what this file closes.

Writing the tests surfaced TWO defects in the module, both cured in the same
commit. Each carries a leg here that goes RED against the pre-cure source, so
these are not tests written to match whatever the code already did:

  A. `render_rows` stamped `note=defects=N` onto EVERY seat-day row whenever ANY
     log anywhere had one bad line. 94 rows would all claim the same N and none
     of them was the row it came from. A parse defect is UNATTRIBUTABLE by
     construction — an unparseable row is unparseable precisely because the seat
     could not be read out of it — so it now gets its own `-`/`-` row instead of
     being written onto seats that were never measured.

  B. `render_token` rendered the announce cell as the literal string
     'not wired' whenever the sum was zero, on the stated ground that the column
     "CANNOT be non-zero" until the v2 class is wired. That ground is false: the
     CENSUS class is tagged by the live guard and has fired — the shipped
     ops/stop_ledger.tsv carries `2026-08-18 creator ... announce_census=1`. So a
     zero is a real observation, and printing 'not wired' over it tells the
     principal an armed instrument is absent. Same unknown-vs-zero confusion the
     module guards everywhere else, pointed the other way.

Legs:
  1  a normal receipt aggregates: stops / measured / with_runnable / sessions
  2  runnable=skip is NOT folded in as a measured zero (the module's own bar)
  3  runnable=n/a likewise; and a seat whose every stop was unmeasured renders
     'n/m', never '0'
  4  an unreadable log yields a defect rather than vanishing
  5  an unparseable line yields a defect rather than being skipped
  6  SUBAGENT-EXEMPT rows are excluded from every count
  7  DEFECT A red-arm: a defect in one log does NOT stamp a note on any seat row,
     and IS reported on its own unattributable row
  8  DEFECT B red-arm: a measured zero in the announce column renders '0'
  9  a genuinely non-zero announce census renders its number
 10  an empty day renders 'instrument silent', never a measured zero
 11  NEGATIVE CONTROL: the header is a fixed grammar and every emitted row has
     exactly as many fields as the header — a row that grew a column would be
     read as another column's value by any consumer splitting on tab
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from stop_ledger_rollup import (  # noqa: E402
    HEADER, collect, parse_log, render_rows, render_token)


# --------------------------------------------------------------------------
# fixture helpers — the receipt grammar is stop_guard.py:1200-1204, and the
# `decision=` field MUST stay last (stop_guard.py:1195-1199 marks the position
# load-bearing). These builders keep that order so the fixtures cannot drift
# into a shape the live emitter never produces.
# --------------------------------------------------------------------------
def receipt(date="2026-08-30", session="s1", seat="builder", how="env",
            runnable="3", klass="-", decision="allow", notes="-"):
    run_part = f"runnable={runnable} ids=-" if runnable is not None else ""
    return (f"{date}T12:00:00-04:00 session={session} seat={seat}({how}) "
            f"{run_part} pause=no permit=- class={klass} "
            f"notes={notes} decision={decision}")


def write_log(ws: Path, session: str, lines):
    (ws / "plans").mkdir(parents=True, exist_ok=True)
    p = ws / "plans" / f".stop_log.{session}"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return p


# --------------------------------------------------------------------------
# 1 — a normal receipt aggregates
# --------------------------------------------------------------------------
def test_normal_receipts_aggregate(tmp_path):
    write_log(tmp_path, "s1", [
        receipt(session="s1", runnable="3"),
        receipt(session="s1", runnable="0"),
        receipt(session="s2", runnable="2"),
    ])
    agg, defects, nlogs = collect(tmp_path)
    assert nlogs == 1
    assert defects == []
    a = agg[("2026-08-30", "builder")]
    assert a["stops"] == 3
    assert a["measured"] == 3          # 0 IS a measurement
    assert a["with_runnable"] == 2     # 3 and 2; the 0 is a measured clean stop
    assert len(a["sessions"]) == 2


# --------------------------------------------------------------------------
# 2 — runnable=skip is not a measured zero
# --------------------------------------------------------------------------
def test_skip_is_not_folded_in_as_a_measured_zero(tmp_path):
    write_log(tmp_path, "s1", [
        receipt(runnable="skip"),
        receipt(runnable="4"),
    ])
    agg, _, _ = collect(tmp_path)
    a = agg[("2026-08-30", "builder")]
    assert a["stops"] == 2
    assert a["measured"] == 1, "skip means NEVER COMPUTED, not measured-zero"
    assert a["with_runnable"] == 1


# --------------------------------------------------------------------------
# 3 — an entirely unmeasured seat renders n/m, never 0
# --------------------------------------------------------------------------
def test_wholly_unmeasured_seat_renders_nm_not_zero(tmp_path):
    write_log(tmp_path, "s1", [
        receipt(seat="orchestrator", runnable="skip"),
        receipt(seat="orchestrator", runnable="n/a"),
    ])
    agg, _, _ = collect(tmp_path)
    a = agg[("2026-08-30", "orchestrator")]
    assert a["stops"] == 2 and a["measured"] == 0

    tok = render_token(agg, "2026-08-30")
    assert "n/m" in tok
    # the exact failure this guards: a 0 in that cell reads as a clean seat
    assert "<td>0</td><td>" not in tok.replace("<td>2</td>", "")


# --------------------------------------------------------------------------
# 4 — an unreadable log is a defect, not a silence
# --------------------------------------------------------------------------
def test_unreadable_log_yields_a_defect(tmp_path):
    (tmp_path / "plans").mkdir(parents=True)
    # a directory named like a log: read_text raises OSError, which is the
    # branch under test. Using a real unreadable path keeps this honest rather
    # than monkeypatching the reader.
    (tmp_path / "plans" / ".stop_log.dir_shaped").mkdir()
    rows = list(parse_log(tmp_path / "plans" / ".stop_log.dir_shaped"))
    assert len(rows) == 1
    assert rows[0]["defect"].startswith("unreadable:")


# --------------------------------------------------------------------------
# 5 — an unparseable line is a defect, not a skip
# --------------------------------------------------------------------------
def test_unparseable_line_yields_a_defect(tmp_path):
    write_log(tmp_path, "s1", [
        receipt(),
        "this line is not a receipt at all",
    ])
    agg, defects, _ = collect(tmp_path)
    assert len(defects) == 1
    assert defects[0].startswith("unparseable-row:")
    assert agg[("2026-08-30", "builder")]["stops"] == 1


# --------------------------------------------------------------------------
# 6 — subagent rows own no ledger steps and are excluded
# --------------------------------------------------------------------------
def test_subagent_rows_are_excluded_without_being_defects(tmp_path):
    write_log(tmp_path, "s1", [
        receipt(),
        "2026-08-30T12:00:00-04:00 session=s1 SUBAGENT-EXEMPT decision=allow",
    ])
    agg, defects, _ = collect(tmp_path)
    assert defects == [], "an exempt row is understood, not a parse failure"
    assert agg[("2026-08-30", "builder")]["stops"] == 1


# --------------------------------------------------------------------------
# 7 — DEFECT A red-arm
# --------------------------------------------------------------------------
def test_a_parse_defect_is_not_stamped_onto_seat_rows(tmp_path):
    """RED against the pre-cure source, which wrote `defects=1` into the note
    column of every seat-day row including ones from a different log entirely."""
    write_log(tmp_path, "s1", [receipt(date="2026-08-28", seat="builder")])
    write_log(tmp_path, "s2", [receipt(date="2026-08-29", seat="creator"),
                               "garbage"])
    agg, defects, _ = collect(tmp_path)
    assert len(defects) == 1

    rows = render_rows(agg, defects)
    assert rows[0] == HEADER
    seat_rows = [r for r in rows[1:] if not r.startswith("-\t-\t")]
    assert len(seat_rows) == 2
    for r in seat_rows:
        note = r.split("\t")[-1]
        assert note == "-", (
            "a defect that could not be attributed to a seat must not be "
            f"written onto one; got note={note!r} on row {r!r}")

    unattributed = [r for r in rows[1:] if r.startswith("-\t-\t")]
    assert len(unattributed) == 1, "the count must still reach the file"
    assert unattributed[0].endswith("unattributable-parse-defects=1")


def test_no_defects_means_no_unattributable_row(tmp_path):
    """The companion direction: the extra row appears only when earned."""
    write_log(tmp_path, "s1", [receipt()])
    agg, defects, _ = collect(tmp_path)
    rows = render_rows(agg, defects)
    assert not any(r.startswith("-\t-\t") for r in rows)


# --------------------------------------------------------------------------
# 8 — DEFECT B red-arm
# --------------------------------------------------------------------------
def test_a_measured_zero_announce_renders_zero_not_not_wired(tmp_path):
    """RED against the pre-cure source, which rendered the literal 'not wired'.

    The census class IS tagged by the live guard — ops/stop_ledger.tsv carries
    `2026-08-18 creator ... announce_census=1` — so zero here is an observation,
    and 'not wired' asserts the instrument is absent when it is armed."""
    write_log(tmp_path, "s1", [receipt(klass="-", decision="allow")])
    agg, _, _ = collect(tmp_path)
    assert agg[("2026-08-30", "builder")]["ann_census"] == 0

    tok = render_token(agg, "2026-08-30")
    assert "not wired" not in tok, (
        "a measured zero must not render as an absent instrument")
    assert "<td>0</td>" in tok


# --------------------------------------------------------------------------
# 9 — a real announce census renders its number
# --------------------------------------------------------------------------
def test_announce_census_counts_and_renders(tmp_path):
    write_log(tmp_path, "s1", [
        receipt(klass="announce-own-act"),
        receipt(decision="allow-announce-own-act"),
        receipt(klass="announce-own-act-v2"),
        receipt(),
    ])
    agg, _, _ = collect(tmp_path)
    a = agg[("2026-08-30", "builder")]
    assert a["ann_census"] == 2, "class hit + decision-prefix hit"
    assert a["ann_v2"] == 1, "v2 is its own bucket, not folded into census"

    tok = render_token(agg, "2026-08-30")
    assert "<td>3</td>" in tok


# --------------------------------------------------------------------------
# 10 — an empty day is silence, not zero
# --------------------------------------------------------------------------
def test_empty_day_renders_silence_not_a_measured_zero(tmp_path):
    write_log(tmp_path, "s1", [receipt(date="2026-08-30")])
    agg, _, _ = collect(tmp_path)
    tok = render_token(agg, "2026-08-29")   # a day with no receipts
    assert "instrument silent" in tok
    assert "NOT a measured zero" in tok
    assert 'SG8-RUNNABLE-COUNT day="2026-08-29"' in tok


# --------------------------------------------------------------------------
# 11 — NEGATIVE CONTROL on the row grammar
# --------------------------------------------------------------------------
def test_every_emitted_row_has_exactly_the_header_arity(tmp_path):
    """Not a claim about values — a claim about SHAPE. Any consumer of this TSV
    splits on tab and reads by index; a row with a different field count silently
    hands one column's value to another column's reader. Includes the
    unattributable row, which is the newest and least-exercised shape."""
    write_log(tmp_path, "s1", [receipt(), "garbage"])
    agg, defects, _ = collect(tmp_path)
    rows = render_rows(agg, defects)
    width = len(HEADER.split("\t"))
    assert width == 10
    for r in rows:
        assert len(r.split("\t")) == width, f"arity drift on row {r!r}"
