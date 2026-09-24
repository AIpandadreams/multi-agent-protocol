#!/usr/bin/env python3
"""Controls for the READY-CANDIDATE COMPANION in render_head.py.

Ruling of record: an orchestrator ruling, §1(a)/(b)/(c); implementation assigned to builder at
a follow-up ruling. The ruling deliberately pinned a PROPERTY and no field list —
"a reader must be able to REJECT a candidate from the render alone wherever the
ledger's typed fields carry the grounds, and any truncation announces itself" —
because pinning a field list at ruling grain is how the first proposal died: one
specimen refuted it. These controls therefore assert the PROPERTY against the two
named specimens, not a field list.

    C1  acceptance pair — DP-TEE-1 renders rejectable, DP-UX1 renders READY
    C2  anti-vacuity    — the candidate set is non-empty
    C3  truncation announces itself with REAL numbers, never a bare ellipsis
    C4  residual is printed AND POINTED at the cure
    C5  UNRESOLVED fires on a dangling precondition — MUTATION, in memory
    C6  ...and ONLY on lookup failure: a real-but-unmet precondition is neither
        ready nor unresolved (the discriminator — without it C5 proves only
        "something disqualifies", not that the ruled outcome is the one firing)
    C7  no generated line opens a structural surface

⛔ READ-ONLY. Specimens are ORCHESTRATOR-owned, so the digest is rendered for the
orchestrator seat — rendering the running seat would return a different set and
could pass by finding nothing. Nothing is written; C5/C6 mutate the loaded plan
dicts IN MEMORY only, because three other seats work in this tree.
"""
import pathlib
import sys
from datetime import datetime, timezone

# ⛔ CONSOLE-ENCODING GUARD (Q5 round, a fleet ruling). Python selects the
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

HERE = pathlib.Path(__file__).resolve().parent
WS = HERE.parent.parent
sys.path.insert(0, str(WS / "tools"))
import render_head as R  # noqa: E402

NOW = datetime.now(timezone.utc).astimezone()
SEAT = "orchestrator"
READY_SPECIMEN = "DP-UX1"
REJECTABLE_SPECIMEN = "DP-TEE-1"
DANGLING = "NO-SUCH-ID-PLANTED-BY-CONTROL"

fails = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        fails.append(name)


def digest_with(patch):
    real = R.load_open_plans

    def fake(ws):
        plans = real(ws)
        for p in plans:
            for s in p.get("steps") or []:
                patch(s)
        return plans

    R.load_open_plans = fake
    try:
        return R.seat_digest(WS, SEAT, NOW)[2]
    finally:
        R.load_open_plans = real


def bucket_of(actions, sid):
    for b in ("ready", "unresolved"):
        for _pid, s, pcs in actions.get(b) or []:
            if s.get("id") == sid:
                return b, pcs
    return "neither", None


def main() -> int:
    print(f"render_head COMPANION controls — workspace {WS}")
    print("-" * 72)
    actions = R.seat_digest(WS, SEAT, NOW)[2]
    block = R.render_companion(SEAT, actions)
    text = "\n".join(block)

    # C2 first: every assertion below is worthless over an empty candidate set.
    n = len(actions["ready"]) + len(actions["unresolved"])
    check("C2 anti-vacuity: candidate set non-empty", n > 0, f"{n} candidates")

    # C1a — DP-UX1 READY.
    ux = [l for l in block if READY_SPECIMEN in l and "**" in l]
    check(f"C1a {READY_SPECIMEN} renders READY",
          any("READY" in l for l in ux), (ux[0].strip()[:70] if ux else "not rendered"))

    # C1b — DP-TEE-1 rejectable WITHOUT opening the step. Its grounds live in
    # `evidence`; a desc-only render was refuted precisely because it is blind
    # to that field, so this asserts the grounds SURVIVE the budget, not merely
    # that the field is present.
    i = next((k for k, l in enumerate(block) if REJECTABLE_SPECIMEN in l and "**" in l), None)
    tee = "\n".join(block[i:i + 6]) if i is not None else ""
    check(f"C1b {REJECTABLE_SPECIMEN} renders its evidence field", "evidence:" in tee)
    check(f"C1b {REJECTABLE_SPECIMEN} rejection grounds survive the budget",
          "OPEN:" in tee, "the open-issue text inside evidence")

    # C3 — truncation announces itself with numbers.
    trunc = [l for l in block if "TRUNCATED" in l]
    check("C3 truncation announces original→cut and remainder",
          bool(trunc) and all("chars" in l and "not shown" in l for l in trunc),
          f"{len(trunc)} truncated field(s)")

    # C4 — residual printed AND pointed.
    res = [l for l in block if "RESIDUAL" in l]
    check("C4 residual printed", bool(res))
    check("C4 residual POINTED at the cure",
          any("belongs in" in l and "preconditions" in l for l in res))

    # C5 — MUTATION: a dangling precondition must disqualify and be named.
    def plant_dangling(s):
        if s.get("id") == READY_SPECIMEN:
            s["preconditions"] = [DANGLING]

    a1 = digest_with(plant_dangling)
    b1, pcs1 = bucket_of(a1, READY_SPECIMEN)
    check("C5 dangling precondition → UNRESOLVED, never ready", b1 == "unresolved", b1)
    check("C5 the render NAMES the offending id",
          any(p[0] == DANGLING and p[1] == R.PC_UNRESOLVED for p in (pcs1 or [])))

    # C6 — DISCRIMINATOR: a REAL but unmet precondition must be neither. Taken
    # from the specimen's OWN plan: resolution is PLAN-LOCAL, so a foreign id
    # would be unresolvable for the wrong reason and the arm would measure the
    # wrong thing.
    real_unmet = None
    for p in R.load_open_plans(WS):
        if not any(s.get("id") == READY_SPECIMEN for s in (p.get("steps") or [])):
            continue
        real_unmet = next((g["id"] for g in (p.get("gates") or [])
                           if g.get("ruled") is None), None)
        if real_unmet is None:
            real_unmet = next((s["id"] for s in (p.get("steps") or [])
                               if s.get("status") != "done" and s.get("id") != READY_SPECIMEN), None)
        break
    check("C6 a same-plan unmet reference was found to test with", real_unmet is not None)
    if real_unmet:
        def plant_unmet(s):
            if s.get("id") == READY_SPECIMEN:
                s["preconditions"] = [real_unmet]
        b2, _ = bucket_of(digest_with(plant_unmet), READY_SPECIMEN)
        check("C6 real-but-unmet → neither ready NOR unresolved", b2 == "neither",
              f"{real_unmet} → {b2}")

    # C7 — no generated line may open a structural surface. This is the defect
    # the first implementation actually shipped (a `###` heading, rc 5 from the
    # renderer's own invariant); it is pinned here so it cannot return silently.
    bad = [l for l in block if l.lstrip().startswith("#")]
    check("C7 no companion line opens a structural surface", not bad,
          (bad[0][:60] if bad else "none"))

    print("-" * 72)
    print("✅ render_head companion controls: all green" if not fails
          else f"⛔ {len(fails)} FAILED: {', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
