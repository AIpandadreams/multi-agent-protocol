#!/usr/bin/env python3
"""Controlled derivation over ``plans/*.plan.yaml`` for AD-HOC derivers.

WHY THIS EXISTS (commissioned by the orchestrator on a builder report)
--------------------------------------------------------------------
The wake digest (``render_head.py``) is careful: it rebuilds ``pid_map`` fresh
inside the plan loop, so it cannot collapse cross-plan id reuse. **Throwaway
probes are not careful.** A builder-seat probe on 2026-08-28 keyed steps by
``id`` alone, and the open ledger reuses ids heavily -- measured that day,
**153 step rows carried 113 distinct ids, so keying by id alone silently
discarded 40 rows (26%)**. The probe printed a full, plausible row for ``S6``
that belonged to a different plan and a different seat, with rc=0.

Two further defects from the same sitting, both of which this module makes
hard to repeat:

* **Namespace error.** Preconditions were resolved against the set of *steps*
  with ``status: done``. Gates do not live there -- they live in ``gates`` and
  carry ``ruled``. Two RULED gates were reported UNMET.
* **A filter written to paper over it.** ``not p.startswith("DPUX1-GATE")`` was
  added so the probe would return an answer, which made it report the author's
  own assumption back as a measurement.

⛔ **THIS MODULE DOES NOT RE-IMPLEMENT PRECONDITION RESOLUTION.** It imports
``render_head.precondition_state`` and the ``PC_*`` constants. A second
implementation would be a second grammar, free to drift from the instrument of
record, and the whole point is that ad-hoc derivations agree with the wake
digest. [[emitter-and-verifier-are-one-grammar]]

WHAT IT ADDS that render_head does not have: an always-running uniqueness
invariant. ``render_head`` builds its per-plan ``pid_map`` last-writer-wins
across ``steps``/``gates``/``clocks`` and never asserts; a within-plan
cross-collection id reuse would collapse there silently. Measured 2026-08-28:
**0 such collisions live** -- latent, not active. A zero is exactly the result
that needs a positive control, so ``--selftest`` proves the detector fires.

Usage
-----
    from ledger_derive import build_index, open_steps, precondition_report
    idx = build_index(Path("<the private workspace>"))
    for key, coll, step in open_steps(idx, seat="builder"):
        ...

    python tools/ledger_derive.py --selftest     # must-fail drive, rc 0/1
    python tools/ledger_derive.py --seat builder # live derivation
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_head as RH  # noqa: E402  (path set above)

PC_MET, PC_UNMET, PC_UNRESOLVED = RH.PC_MET, RH.PC_UNMET, RH.PC_UNRESOLVED
COLLECTIONS = ("steps", "gates", "clocks")
#: YAML collection name -> the kind vocabulary ``render_head.precondition_state``
#: switches on. Kept as an explicit table, not a ``rstrip("s")``, so a new
#: collection fails loudly with a KeyError instead of resolving to a kind the
#: resolver has no branch for and silently answering UNRESOLVED.
_KIND = {"steps": "step", "gates": "gate", "clocks": "clock"}
OPEN_STATUSES = ("pending", "in-progress", "blocked")


class LedgerIndexError(Exception):
    """A structural defect that makes derivation unsound. Never a warning.

    Raised only for conditions under which a derived answer would be WRONG
    rather than incomplete -- a collapsed row is invisible downstream, so it
    must stop the caller rather than degrade quietly.
    """


class LedgerIndex:
    """Rows keyed by ``(project_id, id)`` -- never by ``id`` alone.

    ``reused_ids`` is INFORMATIONAL, never an alarm: cross-plan id reuse is the
    ledger's normal shape (every plan numbers its own steps ``S1``, ``S2``...).
    Reporting it as a problem would train the reader to ignore the one report
    that matters. What IS an error is a *within-plan* collision, because that is
    the only one that can silently discard a row.
    """

    def __init__(self, rows, plans, paths, reused_ids):
        self.rows = rows
        self.plans = plans
        self.paths = paths
        self.reused_ids = reused_ids

    def pid_map(self, project_id):
        """A ``render_head``-shaped map for one plan, for precondition_state.

        ⛔ The kind is translated to ``render_head``'s SINGULAR vocabulary.
        ``rows`` keys collections by their YAML name (``steps``/``gates``/
        ``clocks``); ``precondition_state`` switches on ``step``/``gate``/
        ``clock`` and has no else-branch for an unknown kind -- it falls through
        to UNRESOLVED. Passing the plural made every precondition in this
        module's own self-test resolve UNRESOLVED, including a RULED gate and a
        done step, which is a *more permissive-looking* failure than the bug
        this module was written to prevent and would have read as "nothing
        resolves" rather than as a defect. Caught by the must-fail drive on its
        first run; it is exactly the two-grammars drift the module exists to
        stop, reproduced inside the module. [[emitter-and-verifier-are-one-grammar]]
        """
        return {i: (_KIND[coll], obj)
                for (p, i), (coll, obj) in self.rows.items() if p == project_id}

    @property
    def distinct_ids(self):
        return {i for (_, i) in self.rows}

    def summary(self):
        return ("%d rows / %d distinct ids across %d open plans "
                "(%d ids reused across plans -- EXPECTED)"
                % (len(self.rows), len(self.distinct_ids), len(self.plans),
                   len(self.reused_ids)))


def _load_raw(ws: Path):
    """Load open plans WITH their paths.

    ``render_head.load_open_plans`` returns bare dicts, so it cannot supply the
    filename this module reports collisions against. The set of plans the two
    loaders see is cross-checked in ``build_index`` -- a divergence would mean
    this module is deriving over a different corpus than the wake digest, which
    is the failure this whole file exists to prevent.
    """
    out = []
    d = ws / "plans"
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*.plan.yaml")):
        data = yaml.safe_load(p.read_bytes().decode("utf-8"))
        if isinstance(data, dict) and data.get("state") == "open":
            out.append((p, data))
    return out


def build_index(ws: Path, _raw=None) -> LedgerIndex:
    """Index every open-plan row by ``(project_id, id)``, asserting soundness.

    Raises ``LedgerIndexError`` on: a duplicate ``project_id`` across open
    plans; a within-plan cross-collection id collision; a row with no ``id``.
    Each of these makes ``(project_id, id)`` non-unique, i.e. makes the key this
    module promises silently lossy.
    """
    raw = _raw if _raw is not None else _load_raw(ws)

    # Cross-check the corpus against the instrument of record. Skipped when a
    # caller injects fixtures (_raw), which have no directory to re-read.
    if _raw is None:
        try:
            rh_n = len(RH.load_open_plans(ws))
        except Exception:                                   # pragma: no cover
            rh_n = None
        if rh_n is not None and rh_n != len(raw):
            raise LedgerIndexError(
                "corpus divergence: this module sees %d open plans, "
                "render_head sees %d -- derivations would disagree with the "
                "wake digest" % (len(raw), rh_n))

    rows, plans, paths = {}, {}, {}
    for path, plan in raw:
        pid = RH.flat(plan.get("project_id", "?"))
        if pid in plans:
            raise LedgerIndexError(
                "duplicate project_id %r: %s and %s -- (project_id,id) is not "
                "unique, so rows WILL collapse" % (pid, paths[pid].name, path.name))
        plans[pid], paths[pid] = plan, path
        for coll in COLLECTIONS:
            for obj in (plan.get(coll) or []):
                if not isinstance(obj, dict) or not obj.get("id"):
                    raise LedgerIndexError(
                        "%s: a %s row carries no id -- it cannot be keyed, and "
                        "dropping it would be a silent loss" % (path.name, coll))
                key = (pid, obj["id"])
                if key in rows:
                    prev = rows[key][0]
                    raise LedgerIndexError(
                        "%s: id %r appears in BOTH %s and %s -- render_head's "
                        "pid_map is last-writer-wins across collections, so one "
                        "row would be silently discarded"
                        % (path.name, obj["id"], prev, coll))
                rows[key] = (coll, obj)

    by_id = {}
    for (pid, i) in rows:
        by_id.setdefault(i, []).append(pid)
    reused = {i: sorted(v) for i, v in by_id.items() if len(v) > 1}
    return LedgerIndex(rows, plans, paths, reused)


def open_steps(index: LedgerIndex, seat=None, statuses=OPEN_STATUSES):
    """Yield ``((project_id, id), collection, obj)`` for open steps.

    ``seat`` is compared through ``render_head.norm_seat`` so the wake aliases
    (``engine``->owner, ``helper``->builder) resolve identically here.
    A step with no ``owner`` is a schema defect: it is yielded for EVERY seat
    rather than silently attributed or dropped.
    """
    want = RH.norm_seat(seat) if seat else None
    for key, (coll, obj) in sorted(index.rows.items()):
        if coll != "steps" or obj.get("status") not in statuses:
            continue
        owner = obj.get("owner")
        if want is not None:
            if owner is None or str(owner).strip() == "":
                pass                      # schema defect -> visible everywhere
            elif RH.norm_seat(owner) != want:
                continue
        yield key, coll, obj


def precondition_report(index: LedgerIndex, project_id, step, now=None):
    """Resolve every precondition of ``step`` -- three outcomes, never two.

    Delegates to ``render_head.precondition_state``. UNRESOLVED is returned for
    an id that names nothing in this plan; it is NOT folded into UNMET, because
    "names nothing" and "names something not yet done" are different facts and
    only one of them is about the step. [[lookup-failure-needs-own-outcome]]
    """
    from datetime import datetime, timezone
    now = now or datetime.now(timezone.utc)
    pm = index.pid_map(project_id)
    ledger_ids = index.distinct_ids
    out = []
    for ref in (step.get("preconditions") or []):
        state, reason = RH.precondition_state(pm, ref, now, ledger_ids)
        out.append((ref, state, reason))
    return out


def ready(index: LedgerIndex, project_id, step, now=None):
    """True only if EVERY precondition is MET.

    An UNRESOLVED precondition never reads as ready -- a dangling id is the one
    case where a permissive default would dispatch work on a typo.
    """
    return all(s == PC_MET for _, s, _ in
               precondition_report(index, project_id, step, now))


# ---------------------------------------------------------------- self-test --

def _fx(pid, steps=(), gates=(), clocks=()):
    return (Path(pid + ".plan.yaml"),
            {"state": "open", "project_id": pid, "steps": list(steps),
             "gates": list(gates), "clocks": list(clocks)})


def _selftest():
    """Must-fail drive. Every arm names the ONE thing it may fail for.

    Arms 1-3 are POSITIVE CONTROLS for detectors that currently measure ZERO on
    the live ledger. A detector that has only ever returned 0 is
    indistinguishable from a detector that cannot return anything else, and the
    live within-plan collision count IS 0 today. [[instrument-polarity-controls]]
    """
    fails, ran = [], 0

    def arm(name, fn, want_raise):
        nonlocal ran
        ran += 1
        try:
            fn()
            got = None
        except LedgerIndexError as e:
            got = str(e)
        ok = (got is not None) if want_raise else (got is None)
        print("  %-5s %s%s" % ("PASS" if ok else "FAIL", name,
                               "" if ok else "\n           got=%r" % (got,)))
        if not ok:
            fails.append(name)

    print("must-fail drive: detectors that read 0 on the live ledger")
    # 1 -- the collision detector CAN fire (live count is 0)
    arm("within-plan collision (step id == gate id) RAISES",
        lambda: build_index(None, _raw=[_fx("P1", steps=[{"id": "X", "owner": "builder"}],
                                            gates=[{"id": "X"}])]), True)
    # 2 -- duplicate project_id
    arm("duplicate project_id RAISES",
        lambda: build_index(None, _raw=[_fx("P1"), _fx("P1")]), True)
    # 3 -- a row with no id
    arm("id-less row RAISES",
        lambda: build_index(None, _raw=[_fx("P1", steps=[{"owner": "builder"}])]), True)
    # 4 -- NEGATIVE CONTROL. Without this, arms 1-3 pass for a build_index that
    #      raises unconditionally, which is the classic always-red control.
    arm("clean fixture does NOT raise",
        lambda: build_index(None, _raw=[_fx("P1", steps=[{"id": "S1", "owner": "builder"}]),
                                        _fx("P2", steps=[{"id": "S1", "owner": "owner"}])]),
        False)

    def ck(name, cond, detail=""):
        nonlocal ran
        ran += 1
        print("  %-5s %s%s" % ("PASS" if cond else "FAIL", name,
                               "" if cond else "\n           " + detail))
        if not cond:
            fails.append(name)

    # 5 -- cross-plan reuse is REPORTED, never raised (arm 4 proved no raise)
    idx = build_index(None, _raw=[_fx("P1", steps=[{"id": "S1", "owner": "builder"}]),
                                  _fx("P2", steps=[{"id": "S1", "owner": "owner"}])])
    ck("cross-plan id reuse is reported, not alarmed",
       idx.reused_ids == {"S1": ["P1", "P2"]}, "got=%r" % (idx.reused_ids,))
    ck("keying by (project_id,id) keeps BOTH reused rows",
       len(idx.rows) == 2 and len(idx.distinct_ids) == 1,
       "rows=%d distinct=%d" % (len(idx.rows), len(idx.distinct_ids)))

    print("\nresolution grammar (the exact errors of 2026-08-28)")
    # 6 -- THE NAMESPACE BUG: a RULED gate must read MET, not UNMET.
    idx = build_index(None, _raw=[_fx(
        "P1",
        steps=[{"id": "B", "owner": "builder", "status": "pending",
                "preconditions": ["G", "A", "NOPE"]},
               {"id": "A", "owner": "builder", "status": "done"}],
        gates=[{"id": "G", "ruled": "RULED 2026-08-20"}])])
    rep = dict((r, s) for r, s, _ in
               precondition_report(idx, "P1", idx.rows[("P1", "B")][1]))
    ck("RULED gate resolves MET (not UNMET -- the namespace bug)",
       rep.get("G") == PC_MET, "got=%r" % (rep.get("G"),))
    ck("done step precondition resolves MET", rep.get("A") == PC_MET,
       "got=%r" % (rep.get("A"),))
    ck("dangling id resolves UNRESOLVED (not UNMET)",
       rep.get("NOPE") == PC_UNRESOLVED, "got=%r" % (rep.get("NOPE"),))
    ck("a step carrying an UNRESOLVED precondition is NOT ready",
       not ready(idx, "P1", idx.rows[("P1", "B")][1]))
    # 7 -- unruled gate must still read UNMET, or arm 6 would pass for a
    #      resolver that answers MET unconditionally.
    idx2 = build_index(None, _raw=[_fx(
        "P1", steps=[{"id": "B", "owner": "builder", "status": "pending",
                      "preconditions": ["G"]}],
        gates=[{"id": "G", "ruled": None}])])
    rep2 = dict((r, s) for r, s, _ in
                precondition_report(idx2, "P1", idx2.rows[("P1", "B")][1]))
    ck("UNRULED gate resolves UNMET (polarity control for the arm above)",
       rep2.get("G") == PC_UNMET, "got=%r" % (rep2.get("G"),))

    print("\n%d arms, %d failed" % (ran, len(fails)))
    return 1 if fails else 0


def main(argv):
    ws = Path(__file__).resolve().parent.parent
    if "--selftest" in argv:
        return _selftest()
    seat = None
    if "--seat" in argv:
        seat = argv[argv.index("--seat") + 1]
    idx = build_index(ws)
    print(idx.summary())
    if idx.reused_ids:
        worst = max(idx.reused_ids.items(), key=lambda kv: len(kv[1]))
        print("  reuse is normal; widest: %r in %d plans" % (worst[0], len(worst[1])))
    print()
    for (pid, sid), _, st in open_steps(idx, seat=seat):
        rep = precondition_report(idx, pid, st)
        bad = [(r, s) for r, s, _ in rep if s != PC_MET]
        print("  %-34s %-12s %-12s %s"
              % (pid[:34], sid, st.get("status"), bad or "preconditions all MET"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
