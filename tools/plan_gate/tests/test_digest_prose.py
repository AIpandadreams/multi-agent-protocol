#!/usr/bin/env python3
"""Positive control for the P0 digest/head prose fix (owner, 2026-08-09).

WHAT WENT WRONG. PLAN_SCHEMA names `question` on gates and `rule` on
constraints. Most of the live ledger writes that prose under `desc`.

  * plan_common.render_digest interpolated `g.get('question')` /
    `c.get('rule')` directly, so a divergent row rendered a literal
    `— None`. Measured on the production digest 2026-08-09: 19 such lines
    (16/16 constraints, 3/4 unruled gates).
  * render_head.py passed the miss through `flat()`, which maps None to "",
    so those rows rendered with an EMPTY body — including the head's own
    "Parked on gate <id> — " dispatch line.

Both are silent falsification of a carrier of record: the reader cannot tell
"this row has no prose" from "the prose was dropped".

WHAT THIS ASSERTS. The bar orch set — no rendered GATE/CONSTRAINT line ends
in `— None` — is necessary but NOT sufficient: `flat()` already made
render_head's misses end in `— ` instead, which passes that bar while
dropping just as much. So the control asserts CONTENT, on both renderers,
against synthetic fixtures AND against the live ledger.

Every green here carries a mutation proving it can go red. Mutations are
applied to a TEMP COPY of the tool, never to the live file: a test that
edits a shared fleet tool in place leaves it mutated if the run dies.

Run:  python tools/plan_gate/tests/test_digest_prose.py
"""
from __future__ import annotations

import datetime
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

# ⛔ CONSOLE-ENCODING GUARD (Q5 round, per a fleet ruling). Python selects the
#   locale codec (cp1252 here) whenever this stream is PIPED OR REDIRECTED --
#   which is the normal condition under a scheduled task, a hook, or any
#   dispatcher that captures output -- even on a cp65001 console. Without this,
#   one marker glyph raises UnicodeEncodeError and the process exits rc=1, and
#   in this fleet's grammar rc=1 means THE SUBJECT REGRESSED. The encoding
#   fault would be published as a verdict about the thing under test.
# ⭐ `errors=` is the half that gets forgotten: a stream reconfigured to utf-8
#   but left at errors='strict' is still one character from rc=1.
# ⚠ TypeError is load-bearing -- the `errors=` keyword raises it on a custom
#   stream whose reconfigure() accepts only `encoding`, and that shape once
#   shipped as a new crash one import earlier. Shape copied from
#   tools/append_co.py:182-195 per INVENTORY.md §3.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, TypeError, ValueError, OSError):
        pass

HERE = Path(__file__).resolve().parent
PLAN_GATE = HERE.parent
TOOLS = PLAN_GATE.parent
WS = TOOLS.parent

sys.path.insert(0, str(PLAN_GATE))
sys.path.insert(0, str(TOOLS))

FAILURES: list[str] = []
CHECKS = 0


def ok(cond: bool, label: str) -> bool:
    global CHECKS
    CHECKS += 1
    if cond:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}")
        FAILURES.append(label)
    return bool(cond)


def load_module(path: Path, name: str):
    """Import a module from an explicit path (used for mutated temp copies)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


NOW = datetime.datetime(2026, 8, 9, 12, 0, 0, tzinfo=datetime.timezone.utc)


def fixture_plans() -> list[dict]:
    """Four rows spanning the whole matrix: canonical vs divergent field,
    enforceable vs inert constraint. A fixture set that only carried the
    broken shape could not show the fix leaves conforming rows alone."""
    return [{
        "id": "fixture-plan",
        "state": "open",
        "owner_seat": "owner",
        "title": "prose-control fixture",
        "steps": [{"id": "S1", "status": "pending", "owner": "owner",
                   "desc": "a step"}],
        "gates": [
            {"id": "G-CANON", "ruler": "principal-first-hand", "unblocks": ["S1"],
             "ruled": None, "question": "CANONICAL GATE PROSE"},
            {"id": "G-DIVERGENT", "ruler": "principal-first-hand",
             "unblocks": ["S1"], "ruled": None, "desc": "DIVERGENT GATE PROSE"},
        ],
        "constraints": [
            {"id": "K-CANON", "until": "close", "rule": "CANONICAL RULE PROSE",
             "blocks": {"tool": "Bash", "arg_pattern": "rm -rf"}},
            {"id": "K-DIVERGENT", "until": "close",
             "desc": "DIVERGENT RULE PROSE"},
        ],
    }]


def digest_lines(pc_mod, plans) -> list[str]:
    out = pc_mod.render_digest(plans, [], "control", NOW)
    return out if isinstance(out, list) else str(out).splitlines()


def rows(lines, kind) -> list[str]:
    return [ln for ln in lines if ln.strip().startswith(kind)]


def body(line: str) -> str:
    """Text after the final ' — ' separator: what a reader actually gets."""
    return line.rsplit(" — ", 1)[-1].strip() if " — " in line else ""


def head_body(line: str) -> str:
    """Prose of a render_head line, isolated from its trailing clauses.

    Head GATE lines are `... unruled — <prose> → unblocks [...]`. Using
    body() here read the `→ unblocks [...]` tail as content, so a gate whose
    prose was EMPTY still measured non-empty and the M5 mutation could not
    turn the control red. The assertion has to be keyed to the span it
    claims to measure, not to the whole line.
    """
    t = body(line)
    # Anchor on the arrow ALONE. Matching " → unblocks " with a leading space
    # failed the moment the prose went empty: body() strips, so the tail
    # arrives as "→ unblocks [...]" with no leading space, the split never
    # fired, and the tail measured as content — the second time this helper
    # passed for the wrong reason. Key on the narrowest stable token.
    if "→ unblocks" in t:
        t = t.split("→ unblocks", 1)[0]
    return t.strip()


# ---------------------------------------------------------------- digest ---
def check_digest(pc_mod, label="live") -> list[str]:
    lines = digest_lines(pc_mod, fixture_plans())
    gates = rows(lines, "GATE")
    cons = rows(lines, "CONSTRAINT")

    ok(len(gates) == 2, f"[{label}] both unruled gates rendered (got {len(gates)})")
    ok(len(cons) == 2, f"[{label}] both active constraints rendered (got {len(cons)})")

    # The bar orch set.
    ok(not [l for l in gates + cons if l.rstrip().endswith("— None")],
       f"[{label}] no GATE/CONSTRAINT line ends in '— None'")
    # The stronger bar: no row renders an EMPTY body either.
    ok(all(body(l) for l in gates + cons),
       f"[{label}] no GATE/CONSTRAINT line renders an empty body")

    # Content actually survives, from BOTH field names.
    ok(any("CANONICAL GATE PROSE" in l for l in gates),
       f"[{label}] canonical gate prose carried")
    ok(any("DIVERGENT GATE PROSE" in l for l in gates),
       f"[{label}] divergent gate prose carried (read from `desc`)")
    ok(any("CANONICAL RULE PROSE" in l for l in cons),
       f"[{label}] canonical constraint prose carried")
    ok(any("DIVERGENT RULE PROSE" in l for l in cons),
       f"[{label}] divergent constraint prose carried (read from `desc`)")

    # The fallback is LOUD, and only on the rows that need it.
    dv = [l for l in gates + cons if "schema-divergent" in l]
    ok(len(dv) == 2, f"[{label}] exactly the 2 divergent rows are marked (got {len(dv)})")
    ok(not [l for l in dv if "CANONICAL" in l],
       f"[{label}] conforming rows are NOT marked divergent")

    # Inert constraints say so; enforceable ones do not.
    inert = [l for l in cons if "ENFORCEMENT=NONE" in l]
    ok(len(inert) == 1 and "K-DIVERGENT" in inert[0],
       f"[{label}] only the constraint with no `blocks` is marked ENFORCEMENT=NONE")
    ok(any("K-CANON" in l and "arg_pattern" not in l.split(" — ")[0].replace(
        "pattern=", "arg_pattern=") for l in cons) or
       any("K-CANON" in l and "ENFORCEMENT=NONE" not in l for l in cons),
       f"[{label}] the constraint WITH `blocks` is not marked inert")
    return lines


# ------------------------------------------------------------------ head ---
HEAD_SEAT = "orchestrator"
"""Seat the live head leg reads.

MEASURED 2026-08-09: seat_digest renders gates/constraints ONLY for
`orchestrator` — owner, builder and creator each get 0 gates and 0
constraints across all 10 open plans, because every plan carrying them is
orchestrator-owned and the render is plan-ownership scoped. Pointing this
leg at `owner` made it assert over an EMPTY list, so the M4/M5 mutations
"went red" on the empty-list check rather than on anything they mutated —
a control passing (and failing) for the wrong reason. It reads the seat
that actually renders the rows.

Separately, and NOT this control's business to fix: fleet-binding
constraints (C3 public surfaces, PC1 no autonomous push to origin/main,
SGC1 live-flip bar) therefore never render into the heads of the seats
they bind. Filed, not cured here.
"""


FIXTURE_WS: Path | None = None  # set in main(); holds a synthetic plans/ dir


def make_fixture_ws(root: Path) -> Path:
    """A synthetic workspace whose ledger PERMANENTLY carries the divergent
    shape (prose under `desc`, no `rule`/`question`) alongside canonical rows.

    WHY THIS EXISTS (2026-08-10): the M4/M5 go-red proofs originally ran over
    the LIVE ledger, and their premise — at least one live row is divergent —
    is corpus state, not code. On 2026-08-09 it held; by 2026-08-10 every
    live constraint carried `rule`, M4's mutation rendered nothing empty, and
    the control could no longer go red (controls-pinned-to-current-value:
    the ledger healed out from under the proof). M5 survived only because 3
    gates happened to remain question-less — one plan edit from the same
    failure. So: the ALWAYS-RUN greens stay pointed at the live ledger
    (guards-must-point-at-production), but the CAN-GO-RED proofs run over
    this fixture, whose divergence no ledger hygiene can heal."""
    plans = root / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    (plans / "head-fixture.plan.yaml").write_text(
        "schema_version: 1\n"
        "project_id: head-prose-fixture\n"
        "title: prose-control head fixture\n"
        "state: open\n"
        "owner_seat: orchestrator\n"
        "steps:\n"
        "  - id: S1\n"
        "    status: pending\n"
        "    owner: orchestrator\n"
        "    desc: a step\n"
        "gates:\n"
        "  - id: G-CANON\n"
        "    ruled: null\n"
        "    unblocks: [S1]\n"
        "    question: CANONICAL GATE PROSE\n"
        "  - id: G-DIVERGENT\n"
        "    ruled: null\n"
        "    unblocks: [S1]\n"
        "    desc: DIVERGENT GATE PROSE\n"
        "constraints:\n"
        "  - id: K-CANON\n"
        "    until: close\n"
        "    rule: CANONICAL RULE PROSE\n"
        "  - id: K-DIVERGENT\n"
        "    until: close\n"
        "    desc: DIVERGENT RULE PROSE\n",
        encoding="utf-8")
    return root


def check_head(rh_mod, label="live", ws: Path | None = None):
    """render_head's seat_digest over the LIVE ledger — the surface a waking
    seat dispatches from. Live for the always-run greens
    (guards-must-point-at-production); the mutation probes pass ws=FIXTURE_WS
    (see make_fixture_ws for why the go-red premise cannot ride the live
    corpus)."""
    _ids, lines, _st = rh_mod.seat_digest(ws if ws is not None else WS,
                                          HEAD_SEAT, NOW)
    gs = [l for l in lines if l.startswith("- gate ")]
    cs = [l for l in lines if l.startswith("- constraint ")]
    ok(bool(cs), f"[{label}] head renders at least one live constraint (got {len(cs)})")
    empty = [l for l in gs + cs if not head_body(l)]
    ok(not empty,
       f"[{label}] no head gate/constraint line renders an empty body "
       f"({len(empty)} empty)")
    ok(not [l for l in gs + cs if l.rstrip().endswith("— None")],
       f"[{label}] no head gate/constraint line ends in '— None'")
    return lines


# -------------------------------------------------------------- mutations ---
def mutation(label: str, src: Path, old: str, new: str, probe, modname: str):
    """Apply a textual mutation to a COPY, import it, and require the probe
    to FAIL. Proves the assertion is load-bearing, not incidentally true.
    Also proves the mutation actually landed (mutation-test-discipline)."""
    global FAILURES, CHECKS
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # plan_common is imported by name from its own dir; copy the whole dir.
        shutil.copytree(src.parent, d / "pkg", dirs_exist_ok=True)
        target = d / "pkg" / src.name
        text = target.read_text(encoding="utf-8")
        if old not in text:
            print(f"  FAIL {label}: mutation anchor NOT FOUND — mutation did not land")
            FAILURES.append(f"{label}: anchor missing")
            CHECKS += 1
            return
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        ok(target.read_text(encoding="utf-8") != text, f"{label}: mutation landed in the copy")

        sys.path.insert(0, str(d / "pkg"))
        saved = {k: v for k, v in sys.modules.items() if k == modname}
        sys.modules.pop(modname, None)
        try:
            mod = load_module(target, modname)
            before = len(FAILURES)
            print(f"  -- under mutation ({label}); failures below are EXPECTED --")
            try:
                probe(mod, label="MUTANT")
            except Exception as e:  # a crash is also a red
                print(f"     mutant raised {type(e).__name__}: {e}")
                FAILURES.append(f"{label}: mutant raised")
            went_red = len(FAILURES) > before
            # Discard the expected reds; keep only the verdict.
            del FAILURES[before:]
            ok(went_red, f"{label}: control GOES RED under mutation")
        finally:
            sys.path.remove(str(d / "pkg"))
            sys.modules.pop(modname, None)
            sys.modules.update(saved)


def main() -> int:
    print("== P0 prose control: plan_common.render_digest (fixtures) ==")
    import plan_common as pc
    check_digest(pc)

    print("\n== P0 prose control: render_head.seat_digest (LIVE ledger) ==")
    import render_head as rh
    check_head(rh)

    print("\n== fixture ws: divergent corpus renders clean under UNMUTATED code ==")
    global FIXTURE_WS
    fix_td = tempfile.TemporaryDirectory()
    FIXTURE_WS = make_fixture_ws(Path(fix_td.name))
    # Control-design discipline: the fixture is proven against the un-neutered
    # rule BEFORE it is trusted to turn a mutation red — a fixture that fails
    # here would make every "went red" below pass for the wrong reason.
    check_head(rh, label="fixture", ws=FIXTURE_WS)

    def check_head_fixture(mod, label="MUTANT"):
        check_head(mod, label=label, ws=FIXTURE_WS)

    print("\n== mutations: each green above must be able to go red ==")
    mutation(
        "M1 digest gate reverts to bare g.get('question')",
        PLAN_GATE / "plan_common.py",
        "f\"unblocks={g.get('unblocks')} — {_prose(g, 'question')}\"",
        "f\"unblocks={g.get('unblocks')} — {g.get('question')}\"",
        check_digest, "plan_common")
    mutation(
        "M2 digest constraint reverts to bare c.get('rule')",
        PLAN_GATE / "plan_common.py",
        "f\"until={c.get('until')} — {_prose(c, 'rule')}\"",
        "f\"until={c.get('until')} — {c.get('rule')}\"",
        check_digest, "plan_common")
    mutation(
        "M3 digest drops the ENFORCEMENT=NONE disclosure",
        PLAN_GATE / "plan_common.py",
        "enf = (\"ENFORCEMENT=NONE (no `blocks` key — plan_gate \"",
        "enf = (\"blocks tool=None pattern=None (no `blocks` key — plan_gate \"",
        check_digest, "plan_common")
    mutation(
        "M4 head constraint reverts to flat(c.get('rule',''))",
        TOOLS / "render_head.py",
        "body = prose(c, \"rule\")",
        "body = flat(c.get('rule', ''))",
        check_head_fixture, "render_head")
    mutation(
        "M5 head gate reverts to flat(g.get('question',''))",
        TOOLS / "render_head.py",
        "unruled — {gate_pointer(g)} →",
        "unruled — {flat(g.get('question', ''))} →",
        check_head_fixture, "render_head")

    print(f"\n{CHECKS} checks, {len(FAILURES)} failures")
    for f in FAILURES:
        print(f"  FAILED: {f}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
