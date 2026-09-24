#!/usr/bin/env python3
"""Mutation harness for `render_head_id_grammar_controls.py`.

⭐ THIS EXISTS SO THE CONTROL'S PROOF IS RE-RUNNABLE, NOT QUOTED.
The control file passed on its first run. A control that has never been shown
to FAIL certifies nothing, and "I ran a mutation once and it failed correctly"
is a claim about a session that ended. This harness rebuilds both mutants and
re-runs the control against each, so the discrimination is evidence anyone can
reproduce. [[mutation-test-discipline]] [[self-test-certifies-instrument-not-the-run]]

THREE mutants, because an instrument that only fails one way is half-tested
([[instrument-polarity-controls]]) — and because after a fleet ruling the grammar
has TWO arms, so a suite that mutates only one of them covers half the subject
while reporting on all of it:

  WIDE   — admits unhyphenated ids, multi-recipient headings and the tick
           namespace, i.e. SIMULATES THE FIX. The control's DIVERGENCE legs
           must fire, proving they will notice when the defect is really cured
           rather than silently outliving it.
  NARROW — requires a lowercase id prefix, breaking the canonical `ORCH-<n>`
           form. The control's INVARIANT legs must fire, proving the regression
           half bites.
  FLOOR  — lowers the separator-less arm's >=3-digit floor to >=1, i.e. removes
           the only refusal that arm performs. The control's floor leg must
           fire. This is the arm that ruling added; without this mutant its single
           guard leg would be certified by never having been shown to fail.

⚠ The mutation is located BY SHAPE (the closing line of the `re.compile` call),
never by an escaped string literal. A literal `([A-Z]+)-(\\d+)\\b` also occurs
in a COMMENT earlier in the file, and a `.replace(..., 1)` against it edits the
documentation and leaves the code untouched — the run then "passes" and looks
like a blind control. That happened on 2026-08-11 and is why every mutant here
is verified by comparing the COMPILED pattern, never the file text.

Run: python tools/tests/render_head_id_grammar_mutants.py
Exit 0 only if BOTH mutants are caught AND production is green.
"""
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:                                          # noqa: BLE001
    pass

REPO = pathlib.Path(__file__).resolve().parents[2]
PROD = REPO / "tools" / "render_head.py"
CONTROL = REPO / "tools" / "tests" / "render_head_id_grammar_controls.py"


def compiled_pattern(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    return mod.ENTRY_ID_RE.pattern


def compiled_nosep(path, name):
    """The separator-less arm's compiled pattern — the `floor` mutant's subject."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    return mod.ENTRY_ID_NOSEP_RE.pattern


def build(kind, outdir):
    """Write a mutant and PROVE the mutation reached the compiled pattern."""
    text = PROD.read_text(encoding="utf-8", newline="")
    lines = text.split("\n")
    # ⭐ RE-AIMED AGAIN (2026-08-15). The grammar gained a SECOND arm
    # (ENTRY_ID_NOSEP_RE), whose final line also starts `r"([A-Z]+)` and ends
    # `")` — so this detector found 2 sites and REFUSED, exactly as designed.
    # ⛔ The refusal is why this needed no debugging: an ambiguous anchor that
    # picked the first match would have mutated whichever arm happened to come
    # first in the file and reported a result about the wrong one. Both recipes
    # below target the SEPARATED arm, so the discriminator is the separator
    # class itself — the one thing the two arms cannot share.
    sites = [i for i, l in enumerate(lines)
             if l.strip().startswith('r"([A-Z]+)') and l.rstrip().endswith('")')
             and "[-\\u2011 ]" in l]
    if len(sites) != 1:
        raise SystemExit(f"⛔ separated-arm code site not unique ({len(sites)} found) — refusing to guess")
    # The bare arm must EXIST and must NOT be what we just selected: if it were
    # ever removed, these recipes would still pass while covering half the
    # grammar, and a mutation suite that silently narrows its own scope is the
    # failure this file was written to prevent.
    nosep = [i for i, l in enumerate(lines)
             if l.strip().startswith('r"([A-Z]+)') and "(\\d{3,})" in l]
    if len(nosep) != 1:
        raise SystemExit(f"⛔ bare-arm (>=3 floor) site not found uniquely ({len(nosep)}) — "
                         f"the ruled arm is missing or duplicated; refusing to report a "
                         f"result that would describe only half the grammar")
    # ⭐ THE `floor` MUTANT TARGETS THE OTHER ARM — added 2026-08-15 because
    # the ruled change shipped a new arm with NO mutation coverage at all. Both recipes
    # above deliberately aim at the separated arm, and `nosep` was introduced
    # only as a guard that it EXISTS. That left the >=3-digit floor — the one
    # piece of the new arm doing any refusing — proven by a single control leg
    # that had never been shown to fail. A control that has never failed
    # certifies nothing [[self-test-certifies-instrument-not-the-run]], and the
    # asymmetry was invisible precisely because the suite was green.
    if kind == "floor":
        j = nosep[0]
        before_line = lines[j]
        lines[j] = lines[j].replace("(\\d{3,})", "(\\d+)", 1)
        if lines[j] == before_line:
            raise SystemExit("⛔ floor mutation edited nothing — the >=3 floor is not "
                             "written as (\\d{3,}) any more; repoint rather than guess")
        out = pathlib.Path(outdir) / "mutant_floor.py"
        out.write_text("\n".join(lines), encoding="utf-8", newline="")
        # Compare the NOSEP arm, not ENTRY_ID_RE: this mutation leaves the
        # separated arm byte-identical, so the usual proof would report "did not
        # reach the compiled pattern" and the harness would refuse a mutation
        # that in fact landed perfectly.
        if compiled_nosep(PROD, "_n_prod") == compiled_nosep(out, "_n_mut"):
            raise SystemExit("⛔ floor mutation did NOT reach the compiled NOSEP pattern.")
        print("  floor: mutation landed in the compiled NOSEP pattern ✓")
        return out

    i = sites[0]
    # ⭐ RE-AIMED 2026-08-11 (P5 cure). Both recipes targeted the pre-cure text
    # `([A-Z]+)-(\d+)`, which no longer exists — so both became silent no-ops.
    # The harness caught that itself and REFUSED to report rather than passing
    # on an inert edit, which is the only reason this was noticed
    # [[mutation-test-discipline]]. Recipes now target the cured pattern.
    if kind == "wide":
        # Make the separator OPTIONAL and admit a letter before the digits —
        # this is precisely the widening the 3 surviving divergence legs
        # describe (E730, E1322, ORCH-T008), so all 3 must fire.
        lines[i] = lines[i].replace("[-\\u2011 ](\\d+)", "[-\\u2011 ]?([A-Z]?\\d+)", 1)
    elif kind == "narrow":
        # Lowercase the prefix class: nothing in the corpus matches, so every
        # INVARIANT leg must fire.
        lines[i] = lines[i].replace("([A-Z]+)[-", "([a-z]+)[-", 1)
    else:
        raise SystemExit(f"unknown mutant kind {kind!r}")

    out = pathlib.Path(outdir) / f"mutant_{kind}.py"
    out.write_text("\n".join(lines), encoding="utf-8", newline="")
    before = compiled_pattern(PROD, f"_p_prod_{kind}")
    after = compiled_pattern(out, f"_p_mut_{kind}")
    if before == after:
        raise SystemExit(f"⛔ {kind} mutation did NOT reach the compiled pattern — "
                         f"the harness edited something inert. Refusing to report a result.")
    print(f"  {kind}: mutation landed in the compiled pattern ✓")
    return out


def run_control(binary=None):
    env = dict(os.environ)
    if binary is not None:
        env["RH_ID_CONTROL_MUTANT"] = str(binary)
        env["RH_ID_CONTROL_MUTATION_TEST"] = "i-am-mutating"
    else:
        env.pop("RH_ID_CONTROL_MUTANT", None)
        env.pop("RH_ID_CONTROL_MUTATION_TEST", None)
    # ⚠ encoding is load-bearing, not boilerplate: the control emits ⭐/⛔, and
    # text=True alone decodes the child through the console codepage (cp1252
    # here), which raises UnicodeDecodeError inside subprocess's reader THREAD.
    # p.stdout then comes back None and the harness dies attribute-erroring on
    # a mutant run — i.e. the polarity proof fails for an encoding reason and
    # says nothing about discrimination. Pin utf-8 and never let the console
    # decide. [[honest-failure-outcomes]]
    p = subprocess.run([sys.executable, str(CONTROL)], cwd=str(REPO),
                       capture_output=True, text=True, env=env, timeout=120,
                       encoding="utf-8", errors="replace")
    out = p.stdout or ""
    fails = [l.strip() for l in out.splitlines() if l.startswith("  FAIL")]
    return p.returncode, fails


print("=" * 72)
print("render_head id-grammar MUTATION harness")
bad = 0
with tempfile.TemporaryDirectory() as td:
    wide = build("wide", td)
    narrow = build("narrow", td)
    floor = build("floor", td)
    print()

    rc, fails = run_control(None)
    ok = rc == 0 and not fails
    print(f"  {'ok  ' if ok else 'FAIL'}  production is GREEN (rc={rc}, {len(fails)} failing legs)")
    bad += not ok

    rc, fails = run_control(wide)
    div = [f for f in fails if "[divergence]" in f]
    # 4 -> 3 -> 1. The multi-recipient divergence was cured and promoted by P5;
    # the two ZERO-SEPARATOR divergences were cured and promoted by the ruled grammar change.
    # Only the tick namespace is left to fire.
    #
    # ⚠ THIS EXPECTATION GOT WEAKER AND THAT IS WORTH SAYING OUT LOUD. Each cure
    # converts a divergence leg into an invariant leg, and invariants assert
    # MATCHING — so they cannot catch a WIDENING. The WIDE mutant's detection
    # surface therefore shrinks every time the grammar is legitimately fixed,
    # which is the opposite of how a test suite should age. Compensated in the
    # control file by refusal-class legs that a widened grammar breaks (the
    # date-shaped-number guard, the >=3 floor leg, and the third-axis leg in
    # MECHANISM); those land in `inv` below, not here, so the NARROW check is
    # doing more of the work than its name suggests.
    ok = rc != 0 and len(div) == 1
    print(f"  {'ok  ' if ok else 'FAIL'}  WIDE mutant caught by the DIVERGENCE legs "
          f"(rc={rc}, {len(div)} divergence legs fired, expected 1)")
    bad += not ok

    # ⭐ ADDED 2026-08-15 with the expectation drop above: assert the WIDE mutant
    # is ALSO caught by a refusal leg, so the wide-detection claim does not rest
    # on a single leg that the next cure could promote away. A widened separated
    # arm admits `[A-Z]?\d+`, which makes the date-shaped WAKE heading mint an id
    # — precisely the fabrication the guard exists for.
    ref = [f for f in fails if "[divergence]" not in f]
    ok = rc != 0 and len(ref) >= 1
    print(f"  {'ok  ' if ok else 'FAIL'}  WIDE mutant ALSO caught by a REFUSAL leg "
          f"(rc={rc}, {len(ref)} non-divergence legs fired, expected >=1)")
    bad += not ok

    rc, fails = run_control(narrow)
    inv = [f for f in fails if "[divergence]" not in f]
    ok = rc != 0 and len(inv) >= 4
    print(f"  {'ok  ' if ok else 'FAIL'}  NARROW mutant caught by the INVARIANT legs "
          f"(rc={rc}, {len(inv)} invariant legs fired, expected >=4)")
    bad += not ok

    rc, fails = run_control(floor)
    fl = [f for f in fails if "floor" in f or "1-2 digit" in f]
    ok = rc != 0 and len(fl) >= 1
    print(f"  {'ok  ' if ok else 'FAIL'}  FLOOR mutant caught by the >=3-floor refusal leg "
          f"(rc={rc}, {len(fl)} floor leg(s) fired, expected >=1)")
    bad += not ok
    # Named, not merely counted: the floor leg is the ONLY thing standing
    # between the zero-separator arm and prose, so which leg catches this
    # matters more than how many do [[detector-keyed-to-prediction]].
    if rc != 0 and not fl:
        print(f"        (fired instead: {[f[:70] for f in fails][:3]})")

print("-" * 72)
if bad:
    print(f"⛔ {bad} polarity check(s) FAILED — the control does not discriminate as claimed")
    sys.exit(1)
print("✅ polarity proven: green on production, fails on a widened grammar via the")
print("   divergence + refusal legs, fails on a narrowed grammar via the invariant")
print("   legs, and fails on a LOWERED >=3 floor via the floor refusal leg — so")
print("   both arms of the grammar have mutation coverage, not just the older one.")
