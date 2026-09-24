"""Blocked-exit ruling cure tests — the believed-blocked exit.

Replays the motivating defect and its inversion per cure-discipline:
a legitimately blocked seat that AUTHORS its blocker as a gate precondition
is believed; every other form of `status: blocked` still counts. The old
`blocked_by` key must no longer believe anything (mutation-landing proof).

Direct unit tests against stop_observer.runnable() — the single
implementation both the observer and the live guard import.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from stop_observer import runnable  # noqa: E402


PLAN_HEAD = (
    "schema_version: 1\n"
    "project_id: fixture-023\n"
    "title: believed-blocked fixture\n"
    "state: open\n"
    "owner_seat: builder\n"
    "coordinates: {repos: [], paths: [], branches: [], ids: []}\n"
    "constraints: []\n"
    "clocks: []\n"
    "authorities: []\n"
)


def write_plan(ws: Path, *, gates: str, step_tail: str) -> None:
    (ws / "plans").mkdir(parents=True, exist_ok=True)
    (ws / "plans" / "fixture-023.plan.yaml").write_text(
        PLAN_HEAD + gates +
        "steps:\n"
        "  - id: S1\n"
        "    desc: fixture step\n"
        "    owner: builder\n"
        + step_tail,
        encoding="utf-8")


UNRULED_GATE = (
    "gates:\n"
    "  - id: G1\n"
    "    question: fixture gate\n"
    "    ruled: null\n"
)
RULED_GATE = (
    "gates:\n"
    "  - id: G1\n"
    "    question: fixture gate\n"
    "    ruled: ruled yes on 2026-08-13\n"
)


class TestBelievedBlocked:
    def test_unruled_gate_precondition_is_believed(self, tmp_path):
        # THE MOTIVATING DEFECT, cured: before that ruling no authored field
        # could make a blocked row believed. Now an unruled-gate
        # precondition does exactly that.
        write_plan(tmp_path, gates=UNRULED_GATE, step_tail=(
            "    preconditions: [G1]\n"
            "    status: blocked\n"
            "    evidence: null\n"))
        ids, notes = runnable(tmp_path, "builder")
        assert ids == []
        assert any("blocked, believed" in n and "G1" in n for n in notes)

    def test_ruled_gate_precondition_is_not_believed(self, tmp_path):
        # The gate ruled -> the stated blocker is gone -> the row counts.
        write_plan(tmp_path, gates=RULED_GATE, step_tail=(
            "    preconditions: [G1]\n"
            "    status: blocked\n"
            "    evidence: null\n"))
        ids, notes = runnable(tmp_path, "builder")
        assert ids == ["fixture-023/S1"]
        assert any("blocked without unruled-gate precondition" in n
                   for n in notes)

    def test_bare_blocked_still_counts(self, tmp_path):
        # Anti-gaming invariant: unsubstantiated `blocked` is runnable.
        write_plan(tmp_path, gates="gates: []\n", step_tail=(
            "    preconditions: []\n"
            "    status: blocked\n"
            "    evidence: null\n"))
        ids, notes = runnable(tmp_path, "builder")
        assert ids == ["fixture-023/S1"]
        assert any("blocked without unruled-gate precondition" in n
                   for n in notes)

    def test_blocked_by_no_longer_believes(self, tmp_path):
        # Mutation-landing proof: the pre-cure escape (`blocked_by`) is
        # gone — a row carrying it, with no gate precondition, now COUNTS.
        # Before the cure this exact fixture was silently excluded.
        write_plan(tmp_path, gates="gates: []\n", step_tail=(
            "    preconditions: []\n"
            "    status: blocked\n"
            "    blocked_by: some-derived-value\n"
            "    evidence: null\n"))
        ids, _notes = runnable(tmp_path, "builder")
        assert ids == ["fixture-023/S1"]

    def test_unknown_ref_is_not_believed(self, tmp_path):
        # An unknown reference never makes the believed list. (It is still
        # excluded from runnable by the frozen FD-3 generic precondition
        # check — pre-existing, any-status semantics this cure leaves
        # untouched — so the assertion here is on the belief NOTE, which is
        # what the receipt audits.)
        write_plan(tmp_path, gates="gates: []\n", step_tail=(
            "    preconditions: [NO-SUCH-ID]\n"
            "    status: blocked\n"
            "    evidence: null\n"))
        _ids, notes = runnable(tmp_path, "builder")
        assert not any("blocked, believed" in n for n in notes)
        assert any("blocked without unruled-gate precondition" in n
                   for n in notes)
