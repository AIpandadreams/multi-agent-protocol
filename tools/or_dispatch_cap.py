#!/usr/bin/env python
"""or_dispatch_cap.py — the second mechanism of a fleet ruling: a hard per-run cap on how many arms
a single dispatch run may fire. Each arm CLAIMS a slot before it dispatches; when the
slots are gone, the claim is REFUSED and the arm never runs.

⛔ THE RULE THIS ENFORCES: a run must not be able to spend without bound because a loop
   read wrong, a retry re-entered, or a fan-out was wider than its author believed. The
   cap is not advice printed at the end — it is a gate crossed BEFORE money moves.

⛔⛔ EXIT (4) IS ITS OWN CODE, AND THAT IS THE POINT (the ruling: "a cap hit is its own
   exit code, distinct from any model failure"). The lane's other codes already mean
   things:
       0  proceed
       2  a voice REFUSED / a check FOUND something  (or_rate_assert, opus_review)
       3  could-not-run — the instrument itself failed
       4  ⛔ CAP EXHAUSTED — nothing failed. The run was healthy and WE stopped it.
   Collapsing 4 into 2 or 3 would make "we halted ourselves on budget" indistinguishable
   from "the model broke", and those demand opposite responses: one is re-run after a
   fix, the other is re-run only after a human raises the cap. A caller that cannot tell
   them apart will retry the one thing it must not retry.

⚠ THE CLAIM IS ATOMIC, BY CONSTRUCTION, NOT BY LOCKING.
   Slot N is the FILE `slot-N`, created with O_CREAT|O_EXCL. The filesystem decides the
   winner of a race; two arms cannot both be handed slot 3. A read-then-increment
   counter — the obvious implementation — has a window between the read and the write
   in which every concurrent arm sees the same remaining count and all proceed. That
   window is exactly when a fan-out is at its widest. A control fires 8 parallel claims
   at a cap of 3 and asserts EXACTLY 3 grants.

⚠⚠ WHAT THIS CAP DOES **NOT** DO — stated plainly so nobody leans on it wrongly:
   The cap binds ONE RUN, identified by its `--run-state` directory. A new directory is
   a new budget, and DELETING the directory resets it. That is deliberate: an arm cap
   answers "how wide can this run get", not "how much has been spent overall". The
   second question WAS mechanism 3's (`or_spend_check.py`) -- RETIRED 2026-09-06 under
   a fleet ruling (the principal first-hand) plus a companion ruling: no spend meter exists in this repo and the
   cap lives at OpenRouter's account. ⇒ Nothing here answers the second question, and
   citing this cap as a spend control would be a false assurance.

USAGE
  or_dispatch_cap.py --cap N --run-state DIR --claim LABEL   # claim a slot for one arm
  or_dispatch_cap.py --run-state DIR --status                # report, claim nothing
EXIT
  0  slot GRANTED — this arm may dispatch
  4  ⛔ CAP EXHAUSTED — this arm must NOT dispatch
  3  could-not-run (bad/absent cap, unusable state dir). Never a silent proceed.
"""
import argparse
import errno
import os
import sys
import time

# ⛔ The cp1252 defect that mechanism 1's controls caught, cured here BEFORE it can bite:
# Python's stdout on this host defaults to cp1252 and cannot encode the marker glyphs, so
# every path that prints one dies with UnicodeEncodeError and exits 1 with a traceback.
# In mechanism 1 that hit only the REFUSAL paths — the guard crashed precisely when it had
# something to say, and the happy path passed clean. The same asymmetry would land here:
# rc=4 is the path with the glyph. Carried forward deliberately rather than re-discovered,
# and pinned by its own regression control. [[test-drive-must-match-its-fail-shape]]
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

SLOT = "slot-%d"


def granted_slots(state_dir):
    try:
        return sorted(n for n in os.listdir(state_dir) if n.startswith("slot-"))
    except OSError:
        return []


def claim(state_dir, cap, label):
    """Take the lowest free slot, atomically. Returns (slot_number|None, used, cap)."""
    for i in range(1, cap + 1):
        path = os.path.join(state_dir, SLOT % i)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError as e:
            if e.errno == errno.EEXIST:
                continue                      # someone else holds it; try the next
            raise
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("%s\t%s\tpid=%d\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                           label, os.getpid()))
        return i, i, cap
    return None, len(granted_slots(state_dir)), cap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap")
    ap.add_argument("--run-state", required=True)
    ap.add_argument("--claim")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.status:
        used = granted_slots(args.run_state)
        print("run-state %s: %d slot(s) claimed%s"
              % (args.run_state, len(used), (" [%s]" % ",".join(used)) if used else ""))
        return 0

    if args.claim is None:
        print("or_dispatch_cap: need --claim LABEL (or --status)", file=sys.stderr)
        return 3

    # ⛔ An absent or unparseable cap must be COULD-NOT-RUN, never "unlimited". The
    # fail-open reading is the one that costs money, and it is the reading a caller gets
    # by default from `int(os.environ.get(...) or 0)`-style code.
    if args.cap is None:
        print("or_dispatch_cap: --cap is REQUIRED. An absent cap is not an unlimited cap.",
              file=sys.stderr)
        return 3
    try:
        cap = int(args.cap)
    except ValueError:
        print("or_dispatch_cap: --cap %r is not an integer" % args.cap, file=sys.stderr)
        return 3
    if cap < 0:
        print("or_dispatch_cap: --cap %d is negative" % cap, file=sys.stderr)
        return 3

    try:
        os.makedirs(args.run_state, exist_ok=True)
    except OSError as e:
        print("or_dispatch_cap: cannot use run-state %s: %s" % (args.run_state, e), file=sys.stderr)
        return 3

    # ⛔ cap=0 is a REFUSAL (4), not a could-not-run and not a pass. "Dispatch nothing"
    # is a coherent, sometimes correct instruction — a dry run, a disarmed lane — and the
    # tool must honour it exactly rather than treating 0 as "unset" and opening the gate.
    try:
        slot, used, cap = claim(args.run_state, cap, args.claim)
    except OSError as e:
        print("or_dispatch_cap: cannot write into run-state: %s" % e, file=sys.stderr)
        return 3

    if slot is None:
        print("⛔ CAP EXHAUSTED  %s — %d of %d arm(s) already claimed in this run; "
              "this arm is NOT dispatched." % (args.claim, used, cap))
        print("\n⛔ THIS IS A CAP HIT (rc=4). Nothing failed and no model was called. Do NOT "
              "retry it as a transient error — the cap is only cleared by a human raising "
              "--cap or by starting a genuinely new run.", file=sys.stderr)
        return 4

    print("OK  slot %d of %d granted to %s" % (slot, cap, args.claim))
    return 0


if __name__ == "__main__":
    sys.exit(main())
