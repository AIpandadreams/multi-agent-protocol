"""SG8 — second battery for stop_ledger_rollup, covering the claims the first
one does not reach.

⚠ READ THIS BEFORE ADDING ANYTHING HERE. `test_stop_ledger_rollup.py` already
exists (builder, de15af08b, 2026-08-30) and covers 11 legs: aggregation,
skip-is-not-a-measured-zero, n/m rendering, unreadable and unparseable defects,
subagent exclusion, the two cured defects (defect-not-stamped-on-seat-rows and
measured-zero-renders-0), census rendering, empty-day silence, and header
ARITY. **None of that is repeated here.** I found the first battery only after
overwriting it — the SG8 plan row still read "REMAINING at builder = the rollup
TEST (shipped untested)", which was true when written and had been false since
de15af08b, and I took the row's prose as current state. The file was restored
byte-identical from HEAD. [[record-and-instruction-have-opposite-staleness-tolerances]]

WHAT THIS FILE ADDS, all of it claims the module makes that nothing tested:

  * **the TSV is a PROJECTION, regenerated in full** — the docstring says so in
    those words, and an append implementation passes every existing leg;
  * **byte hygiene at the write site** — `newline=""` is passed precisely so
    Windows does not insert CRs, and CR bytes are invisible to `grep`, to
    `splitlines()` and to the `head -1 | grep` bar that gates this row;
  * **`--token` is a READ** and must not write the ledger;
  * **the announce branches are an if/elif over a SHARED PREFIX** —
    `announce-own-act` is a prefix of `announce-own-act-v2`, so a reordering
    silently double-counts;
  * **`would-block` counts as a block**, and an allowed stop does not;
  * **the partial-measurement denominator** (`N of M measured`), which is the
    difference between a number and a number you can trust;
  * **the caveat travels INSIDE the rendered block**, after the table — a
    number liftable out of its bound is the failure mode it exists for;
  * **header COLUMN NAMES**, not just arity: the existing arity leg compares
    rows against the HEADER constant, so renaming a column moves both sides
    together and the leg stays green;
  * **seat-day keying across dates and seats**, and seat case normalisation.

⚠ FIXTURE GRAMMAR: the line below is copied field-for-field from a live receipt
(`plans/.stop_log.00b87712-…`), including a `notes=` value containing a `|` and
prose. The sibling battery builds its fixtures from the emitter's field order
instead; both are legitimate and they fail differently, which is the reason to
keep two. A fixture derived from the regex could not catch a regex that is
wrong about production input [[test-drive-must-match-its-fail-shape]].

⚠ RED-CAPABILITY IS MACHINE-CHECKED, not asserted: `mutate_stop_ledger_rollup.py`
breaks one claim at a time and requires the named test — in EITHER battery — to
go red. Green here is not evidence on its own [[mutation-test-discipline]].
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "plan_gate"))

import stop_ledger_rollup as slr  # noqa: E402

LINE = ("{date}T02:35:35.063596+00:00 session={sess} seat={seat}(session-lock) "
        "runnable={runnable} ids=fleet-dashboard-2026-08-07/DP-CONSUMER-1 "
        "pause=- permit=absent class={klass} "
        "notes=plans=20 open=11 | intake-pwa-2026-08-05/S19CD: blocked, believed "
        "(unruled gate G-S19CD-DESIGN) decision={decision}")


def line(date="2026-08-30", sess="s1", seat="builder", runnable="4",
         klass="-", decision="allow-no-pause"):
    return LINE.format(date=date, sess=sess, seat=seat, runnable=runnable,
                       klass=klass, decision=decision)


def ws(tmp_path, **logs):
    (tmp_path / "plans").mkdir(parents=True, exist_ok=True)
    for name, text in logs.items():
        (tmp_path / "plans" / f".stop_log.{name}").write_text(
            text, encoding="utf-8")
    return tmp_path


def agg_of(tmp_path, **logs):
    return slr.collect(ws(tmp_path, **logs))


# ── the file is a projection, not a log ────────────────────────────────────

def test_the_tsv_is_regenerated_in_full_so_stale_seat_days_disappear(tmp_path):
    """The module's own words: 'REGENERATED IN FULL on every run, not appended
    to.' Driven by DELETING a source log and re-running — an append
    implementation passes a re-run that only adds rows, and fails this."""
    root = ws(tmp_path, a=line(seat="builder"), b=line(seat="owner", sess="s2"))
    old = sys.argv
    try:
        sys.argv = ["stop_ledger_rollup.py", "--workspace", str(root)]
        assert slr.main() == 0
        first = (root / "ops" / "stop_ledger.tsv").read_text(encoding="utf-8")
        assert "owner" in first, "positive control: the seat was there to lose"
        (root / "plans" / ".stop_log.b").unlink()
        assert slr.main() == 0
        second = (root / "ops" / "stop_ledger.tsv").read_text(encoding="utf-8")
    finally:
        sys.argv = old
    assert "owner" not in second, "a removed source survived — this is appending"
    assert "builder" in second
    assert second.count(slr.HEADER) == 1, "one header, not one per run"


def test_written_file_carries_no_cr_bytes(tmp_path):
    """Counted in RAW BYTES. `grep`, `splitlines()` and PowerShell's
    `Get-Content` all handle CRLF transparently and CANNOT see this — a CR
    check run through any of them is worthless."""
    root = ws(tmp_path, a=line())
    old = sys.argv
    try:
        sys.argv = ["stop_ledger_rollup.py", "--workspace", str(root)]
        assert slr.main() == 0
    finally:
        sys.argv = old
    raw = (root / "ops" / "stop_ledger.tsv").read_bytes()
    assert raw.count(b"\r") == 0, "CR bytes in a file written with newline=''"
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")


def test_token_mode_does_not_write_the_ledger(tmp_path):
    """`--token` prints and exits. A render that also rewrote the ledger would
    turn every read of the sitrep number into a write of the file it reads."""
    root = ws(tmp_path, a=line())
    old = sys.argv
    try:
        sys.argv = ["stop_ledger_rollup.py", "--workspace", str(root),
                    "--token", "2026-08-30"]
        assert slr.main() == 0
    finally:
        sys.argv = old
    assert not (root / "ops" / "stop_ledger.tsv").exists()


# ── classification ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("decision", ["block", "would-block"])
def test_both_block_decisions_count(tmp_path, decision):
    agg, _, _ = agg_of(tmp_path, a=line(decision=decision))
    assert agg[("2026-08-30", "builder")]["blocks"] == 1


def test_an_allowed_stop_is_not_a_block(tmp_path):
    """Polarity control — without it the leg above passes against a counter
    that increments on everything."""
    agg, _, _ = agg_of(tmp_path, a=line(decision="allow-no-pause"))
    assert agg[("2026-08-30", "builder")]["blocks"] == 0


def test_v2_class_does_not_also_count_as_census(tmp_path):
    """`announce-own-act` is a PREFIX of `announce-own-act-v2`, and the two are
    an if/elif. Order-dependent code over a shared prefix is exactly what
    double-counts when someone reorders the branches; nothing else pins it."""
    agg, _, _ = agg_of(tmp_path, a=line(klass="announce-own-act-v2"))
    a = agg[("2026-08-30", "builder")]
    assert (a["ann_v2"], a["ann_census"]) == (1, 0)


def test_allow_announce_decision_also_lands_in_census(tmp_path):
    """A second, independent path into the census count — `dec.startswith`,
    not the class field. A test on the class path alone leaves it unmeasured."""
    agg, _, _ = agg_of(tmp_path, a=line(klass="-", decision="allow-announce-own-act"))
    assert agg[("2026-08-30", "builder")]["ann_census"] == 1


# ── rendering: the number and its bound ────────────────────────────────────

def test_partial_measurement_states_its_denominator(tmp_path):
    """Some stops measured, some not. `2` alone and `2 of 3 measured` are
    different claims and the cell must make the second one."""
    agg, _, _ = agg_of(
        tmp_path, a=line(runnable="4") + "\n" + line(runnable="skip") + "\n")
    tok = slr.render_token(agg, "2026-08-30")
    assert "of 1 measured" in tok, tok


def test_the_caveat_ships_inside_the_block_after_the_table(tmp_path):
    """The caveat is in the same rendered block, positioned AFTER the table, so
    a number cannot be lifted out of its bound. Position is part of the claim
    here, not decoration [[position-is-normative]]."""
    agg, _, _ = agg_of(tmp_path, a=line())
    tok = slr.render_token(agg, "2026-08-30")
    assert 'SG8-RUNNABLE-COUNT day="2026-08-30"' in tok
    assert "not defects" in tok and "over-count" in tok and "under-count" in tok
    assert tok.index("caveat") > tok.index("<td>builder</td>"), \
        "the caveat must travel with the table, not precede it"


# ── header: names, not just arity ──────────────────────────────────────────

def test_header_column_names_are_pinned_not_only_their_count(tmp_path):
    """⚠ WHY THIS IS NOT A DUPLICATE of the sibling's arity leg. That leg
    compares each row's field count against `HEADER` — so renaming a column
    moves BOTH sides of the comparison together and the leg stays green while
    every consumer keying on the name breaks. This pins the names themselves,
    including the `date` that SG8's own done_when greps for."""
    agg, defects, _ = agg_of(tmp_path, a=line())
    rows = slr.render_rows(agg, defects)
    assert rows[0].split("\t") == [
        "date", "seat", "stops", "stops_measured", "stops_with_runnable",
        "announce_census", "announce_v2", "blocks", "sessions", "note"]


# ── keying ─────────────────────────────────────────────────────────────────

def test_seat_days_are_distinct_across_dates_and_seats(tmp_path):
    """The sibling battery dedups sessions WITHIN one seat-day. This checks the
    key itself splits on both axes — a rollup that collapsed dates would report
    a month of stops as one day's."""
    agg, _, _ = agg_of(
        tmp_path,
        a=(line(date="2026-08-30", seat="builder", sess="s1") + "\n" +
           line(date="2026-08-30", seat="builder", sess="s1") + "\n" +
           line(date="2026-08-31", seat="builder", sess="s2") + "\n" +
           line(date="2026-08-30", seat="owner", sess="s3") + "\n"))
    assert set(agg) == {("2026-08-30", "builder"), ("2026-08-31", "builder"),
                        ("2026-08-30", "owner")}
    b = agg[("2026-08-30", "builder")]
    assert b["stops"] == 2 and len(b["sessions"]) == 1


def test_seat_case_is_normalised(tmp_path):
    """`Builder` and `builder` must not become two seat-days."""
    agg, _, _ = agg_of(tmp_path, a=line(seat="Builder"))
    assert ("2026-08-30", "builder") in agg
