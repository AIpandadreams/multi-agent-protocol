#!/usr/bin/env python3
"""F3 planted-stale fixture — BOTH heading forms (the ruled acceptance bar).

An orchestrator ruling fixed the binding wording, and it is deliberately stronger than the
paraphrase it replaced:

    the F3 planted-stale fixture fires in BOTH heading forms
    AND the fresh-head negative control PASSES in both forms.

Both halves are load-bearing and they fail in opposite directions
([[instrument-polarity-controls]]):

  * fires-in-both  — a grammar that cannot SEE separator-less entry headings
    builds a TRUNCATED lane sequence, so `behind` is computed over the wrong
    list and a genuinely stale head grades GREEN. That is the silent direction:
    nothing errors, the head is simply never asked to re-render.
  * passes-in-both — the cure must not make F3 fire on FRESH heads. A widened
    grammar that swept up prose would inflate the sequence and push honest
    heads past the threshold, and a check that fires on everything is
    indistinguishable from one that fires on nothing.

⭐ WHAT MAKES THIS A TEST AND NOT A DEMO: leg 3 re-runs the SAME fixture with
the grammar narrowed back to the pre-amendment arm (`ENTRY_ID_RE` alone). The
separator-less stale head must then FAIL to fire. If it still fires, this file
proves nothing about the amendment — the fixture would be firing for some other
reason and the green would be a [[control-passing-for-the-wrong-reason]].

Mechanism is asserted, never just the return code: rc=3 is reachable from a
dozen unrelated problems (missing source, head drift, mtime regression), so
every leg matches the ENTRIES-BEHIND text specifically.

Run: python tools/tests/render_head_f3_both_forms_controls.py
Exit 0 only if all legs pass.
"""
import importlib.util
import pathlib
import sys
import tempfile

# ⛔ THIS FILE IS A SCRIPT, NOT A PYTEST BATTERY, AND WITHOUT THIS GUARD IT TAKES
#    DOWN EVERY OTHER BATTERY IN THE SAME INVOCATION. Everything below runs at MODULE
#    level and reaches `sys.exit(...)`. Under collection that SystemExit escapes into
#    pytest's importer, which reports INTERNALERROR and aborts the WHOLE run at rc 3 --
#    not this file's legs lost, but every battery named alongside it.
#
# ⚠ AIMED AT THE ONE INVOCATION SHAPE THIS FLEET USES. `pytest tools/tests/` collects
#    and never reaches this file: the default `python_files` patterns are `test_*.py`
#    and `*_test.py` and this repo adds no pytest config widening them, so a directory
#    run skips every `*_controls.py`. The batteries are only ever run by NAMING them,
#    and `pytest tools/tests/*_controls.py` is exactly the form that dies at rc 3.
#
#    Swept per a fleet ruling ("sweep the 29 with the same guard, one unit"), the
#    same cure proven on wire_record_import_controls.py under an earlier ruling.
if __name__ != "__main__":
    import pytest

    pytest.skip(
        "render_head_f3_both_forms_controls.py is a SCRIPT leg, not a pytest battery: it does its work at module "
        "level and ends in sys.exit(). Run it directly -- `python tools/tests/render_head_f3_both_forms_controls.py` "
        "-- which is how the leg census counts it (a script leg, not a pytest leg). "
        "Collected here it would abort the whole run at rc 3.",
        allow_module_level=True)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:                                          # noqa: BLE001
    pass

REPO = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("rh_f3", str(REPO / "tools" / "render_head.py"))
RH = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RH)

ROLE = "owner"
LANE = "orch_to_owner_2026-08-01.md"     # recipient MUST be `owner` — F7 rejects
FIRST, COUNT = 1200, 26                  # 26 entries => behind 25 > TICK_MAX_ENTRIES
PREFIX = "SYN"

# The two heading forms. This is the ONLY difference between the two runs, which
# is what lets a divergence be attributed to the grammar rather than the fixture
# [[discriminator-needs-an-independent-difference]].
FORMS = {
    "separated":     lambda n: f"{PREFIX}-{n}",
    "separatorless": lambda n: f"{PREFIX}{n}",
}

fails = []


def ok(cond, msg):
    print(("  ok    " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)


def build_ws(root, form, n_entries):
    """A synthetic workspace with a real rendered head. The head is produced by
    the PRODUCTION renderer, not hand-written: a hand-built footer would be my
    own restatement of the format and would test my copy of it
    [[emitter-and-verifier-are-one-grammar]]."""
    ws = pathlib.Path(root)
    (ws / "channel").mkdir(parents=True)
    (ws / "plans").mkdir()                       # empty: adopted, no open plans
    (ws / "memory" / ROLE).mkdir(parents=True)
    (ws / "memory" / ROLE / "MEMORY.md").write_bytes(
        b"# owner memory\n\n## Next Step\n\nplaceholder\n")
    write_lane(ws, form, n_entries)
    return ws


def write_lane(ws, form, n_entries):
    body = ["# lane\n"]
    for i in range(n_entries):
        body.append(f"\n## {FORMS[form](FIRST + i)} — synthetic entry\n\nbody\n")
    (ws / "channel" / LANE).write_bytes("".join(body).encode("utf-8"))


def render(ws):
    RH.render(ws, ROLE, RH.datetime(2026, 8, 15, 9, 0, 0), adopt=True)


def check(ws):
    """Returns (rc, printed). check() reports through stdout, so the mechanism
    is only assertable by capturing it."""
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = RH.check(ws, ROLE, tick=True)
    return rc, buf.getvalue()


BEHIND = "entries past recorded tail"


def run_form(form, label):
    print(f"\n[{label}] heading form: `## {FORMS[form](FIRST)} — …`")
    # ---- negative control FIRST: a fresh head must PASS ---------------------
    # Ordered first deliberately. If the fixture is broken in a way that makes
    # everything red, the fresh leg says so before the stale leg can be read as
    # a success [[instrument-polarity-controls]].
    with tempfile.TemporaryDirectory() as td:
        ws = build_ws(td, form, COUNT)
        render(ws)
        rc, out = check(ws)
        ok(rc == RH.RC_OK,
           f"[{label}] FRESH head PASSES (rc={rc}, expected {RH.RC_OK}) — {out.strip()[:110]}")

    # ---- planted stale: render at 1 entry, then advance the lane ------------
    with tempfile.TemporaryDirectory() as td:
        ws = build_ws(td, form, 1)
        render(ws)                                # head records tail = FIRST
        write_lane(ws, form, COUNT)               # lane advances 25 entries
        rc, out = check(ws)
        ok(rc == RH.RC_STALE,
           f"[{label}] PLANTED-STALE head FIRES (rc={rc}, expected {RH.RC_STALE})")
        # ⭐ the mechanism, not merely the code: rc=3 is reachable from many
        # unrelated problems and a fixture that accepts any of them is not
        # measuring F3 at all.
        ok(BEHIND in out,
           f"[{label}] …and fires for the ENTRIES-BEHIND reason, not an unrelated "
           f"problem — {out.strip()[:150]}")
        return out


print("=" * 74)
print("F3 planted-stale — BOTH heading forms (the ruled acceptance bar)")

# --- LEG 0: the fixture must actually be able to see the lane it plants ------
# A workspace whose lane the scanner cannot read produces an empty sequence, and
# every downstream leg then measures nothing. Assert the corpus exists before
# grading anything over it [[empty-result-needs-its-count]].
with tempfile.TemporaryDirectory() as td:
    ws = build_ws(td, "separatorless", COUNT)
    seq = RH.lane_entries(ws).get(("orch_to_owner", PREFIX)) or []
    ok(len(seq) == COUNT,
       f"[precondition] separator-less lane yields {len(seq)} entries (expected {COUNT}) — "
       f"the fixture's corpus is visible to the production scanner")
with tempfile.TemporaryDirectory() as td:
    ws = build_ws(td, "separated", COUNT)
    seq = RH.lane_entries(ws).get(("orch_to_owner", PREFIX)) or []
    ok(len(seq) == COUNT,
       f"[precondition] separated lane yields {len(seq)} entries (expected {COUNT})")

out_sep = run_form("separated", "separated")
out_nos = run_form("separatorless", "separator-less")

# --- LEG 3: the discriminator -----------------------------------------------
# Narrow the grammar back to the pre-amendment arm and re-run the separator-less
# fixture. It must STOP firing. Without this leg, both forms passing is equally
# consistent with "the amendment works" and "the fixture never depended on it".
print("\n[discriminator] pre-amendment grammar (ENTRY_ID_RE alone)")
saved = RH.match_entry_id
try:
    RH.match_entry_id = RH.ENTRY_ID_RE.match          # the grammar as it shipped before
    with tempfile.TemporaryDirectory() as td:
        ws = build_ws(td, "separatorless", 1)
        render(ws)
        write_lane(ws, "separatorless", COUNT)
        rc, out = check(ws)
        ok(BEHIND not in out,
           f"⭐ under the OLD grammar the separator-less stale head does NOT fire for "
           f"entries-behind (rc={rc}) — so leg [separator-less] above measures the "
           f"amendment and not the fixture")
    # …and the SEPARATED form must still fire under the old grammar, or the
    # discriminator above would be explained by the narrowing having broken the
    # fixture wholesale rather than by the form.
    with tempfile.TemporaryDirectory() as td:
        ws = build_ws(td, "separated", 1)
        render(ws)
        write_lane(ws, "separated", COUNT)
        rc, out = check(ws)
        ok(BEHIND in out,
           f"⭐ …while the SEPARATED form still fires under the OLD grammar (rc={rc}) — "
           f"the difference is the heading form, not a broken harness")
finally:
    RH.match_entry_id = saved

print("-" * 74)
if fails:
    print(f"⛔ {len(fails)} leg(s) FAILED")
    for f in fails:
        print(f"   - {f}")
    sys.exit(1)
print("✅ F3 fires in BOTH heading forms for the entries-behind reason, the fresh-head")
print("   negative control PASSES in both, and the pre-amendment grammar is shown to")
print("   miss the separator-less case — the bar's F3 clause is met.")
