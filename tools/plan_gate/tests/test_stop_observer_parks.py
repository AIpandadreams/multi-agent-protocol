"""owner E1604 cure (2026-08-18) — the "Runnable now" list is a dispatch surface
that must SEE a live freeze constraint.

Motivating defect: FZ1 (fleet-dashboard plan) parked P10 / PD3 / SO2 in prose;
the stop-hook's Runnable-now list (stop_observer.runnable) read only step
status + preconditions and listed all three as runnable. Cure: a live
constraint may carry a `PARKS: <plan>/<step>, ...` token; runnable() excludes
those ids with a `parked-by:` note.

Legs: (1) the defect replayed — parked step excluded, note names the
constraint; (2) POSITIVE CONTROL — same fixture with the gate RULED -> the
constraint is no longer live -> the step is runnable again (proves the
exclusion is keyed on liveness, not on the token's mere presence);
(3) cross-plan — a constraint on plan A parks a step on plan B; (4) a step NOT
named stays runnable (the token does not over-park); (5) mutation landing —
the token grammar closes at a period, so trailing prose does not leak into an
id.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from stop_observer import runnable, parked_by_constraints  # noqa: E402


def head(pid: str, seat: str = "owner") -> str:
    return (
        "schema_version: 1\n"
        f"project_id: {pid}\n"
        "title: parks fixture\n"
        "state: open\n"
        f"owner_seat: {seat}\n"
        "coordinates: {repos: [], paths: [], branches: [], ids: []}\n"
        "clocks: []\n"
        "authorities: []\n"
    )


def step(sid: str, seat: str = "owner") -> str:
    return (
        f"  - id: {sid}\n"
        "    desc: fixture step\n"
        f"    owner: {seat}\n"
        "    status: pending\n"
        "    preconditions: []\n"
        "    evidence: null\n"
    )


def plan_a(ruled: str, parks: str) -> str:
    return (
        head("plan-a")
        + "gates:\n  - id: GX\n    question: ship gate\n"
        + f"    ruled: {ruled}\n"
        + "constraints:\n  - id: FZ\n"
        + f'    rule: "FREEZE prose. {parks} More prose after the token."\n'
        + "    until: gate:GX\n"
        + "    desc: freeze carrier\n"
        + "steps:\n" + step("P10") + step("FREE")
    )


def plan_b() -> str:
    return head("plan-b") + "gates: []\nconstraints: []\nsteps:\n" + step("PD3")


def write(ws: Path, name: str, text: str) -> None:
    (ws / "plans").mkdir(parents=True, exist_ok=True)
    (ws / "plans" / f"{name}.plan.yaml").write_text(text, encoding="utf-8")


PARKS = "PARKS: plan-a/P10, plan-b/PD3."


class TestParks:
    def test_live_constraint_parks_named_steps(self, tmp_path):
        write(tmp_path, "plan-a", plan_a("null", PARKS))
        write(tmp_path, "plan-b", plan_b())
        ids, notes = runnable(tmp_path, "owner")
        assert "plan-a/P10" not in ids
        assert "plan-b/PD3" not in ids            # cross-plan park
        assert "plan-a/FREE" in ids               # not named -> not parked
        assert any(n == "plan-a/P10: parked-by:plan-a/FZ" for n in notes)
        assert any(n == "plan-b/PD3: parked-by:plan-a/FZ" for n in notes)

    def test_ruled_gate_unparks_positive_control(self, tmp_path):
        # Same token, gate RULED -> constraint not live -> nothing parked.
        write(tmp_path, "plan-a", plan_a("ruled 2026-08-18 by orch", PARKS))
        write(tmp_path, "plan-b", plan_b())
        ids, notes = runnable(tmp_path, "owner")
        assert sorted(ids) == ["plan-a/FREE", "plan-a/P10", "plan-b/PD3"]
        assert not any("parked-by" in n for n in notes)

    def test_token_grammar_closes_at_period(self):
        opens = [{"project_id": "plan-a", "gates": [],
                  "steps": [{"id": "P10"}],
                  "constraints": [
            {"id": "FZ", "until": "close",
             "rule": "x PARKS: plan-a/P10, plan-b/PD3. Not-an-id/HERE"}]},
                 {"project_id": "plan-b", "gates": [], "constraints": [],
                  "steps": [{"id": "PD3"}, {"id": "HERE"}]}]
        notes: list[str] = []
        parked = parked_by_constraints(opens, None, notes)
        assert set(parked) == {"plan-a/P10", "plan-b/PD3"}
        # the period closed the token: the trailing id-shaped prose was never
        # parsed, so it produced neither a park nor a resolve note
        assert notes == []

    def test_no_token_parks_nothing(self, tmp_path):
        write(tmp_path, "plan-a", plan_a("null", "no token here"))
        ids, notes = runnable(tmp_path, "owner")
        assert "plan-a/P10" in ids and "plan-a/FREE" in ids


class TestParksResolve:
    # owner E1606: an unresolvable entry is inert enforcement - it must be LOUD.
    def test_unresolved_and_bare_entries_note_loudly(self, tmp_path):
        write(tmp_path, "plan-a", plan_a("null", "PARKS: plan-a/P10, plan-a/NOPE, P10, plan-b/PD3."))
        write(tmp_path, "plan-b", plan_b())
        ids, notes = runnable(tmp_path, "owner")
        assert "plan-a/P10" not in ids and "plan-b/PD3" not in ids
        assert any("'plan-a/NOPE' names no open step" in n for n in notes)
        assert any("'P10' has no '/'" in n for n in notes)
        # the bare/unresolved entries never park anything by accident
        assert "plan-a/FREE" in ids

    def test_clean_token_emits_no_resolve_notes(self, tmp_path):
        write(tmp_path, "plan-a", plan_a("null", PARKS))
        write(tmp_path, "plan-b", plan_b())
        _, notes = runnable(tmp_path, "owner")
        assert not any("parks NOTHING" in n for n in notes)
