"""U6 -- condition detectors with DISTINGUISHABLE diagnoses.
DESIGN-builder-v4 5 (i)(j)(k), graded by 6.
Bar: an acceptance-bar document in the private workspace.

6 rules that A GENERIC DELIVERY TIMEOUT IS A FAIL, because "a cure that reports
every death as the same death cannot be acted on".

=====================================================================
 THE PROPERTY THIS MODULE OWES IS DISCRIMINATION, NOT DETECTION
=====================================================================
Three detectors can each be individually green and the set still be useless.
"Each detector fires on its own condition" and "each condition yields a diagnosis
DIFFERENT FROM EVERY OTHER condition's" are DIFFERENT CLAIMS, and only the second
is what 6 demands.  So this module is graded by a CONFUSION MATRIX: every
condition is presented to the WHOLE set, the right detector must fire on the
diagonal, and no other condition may produce that diagnosis off it.
[[stated-reason-must-discriminate]] [[detector-keyed-to-prediction]]

=====================================================================
 THE TWO OUTCOMES WITHOUT WHICH THE MATRIX LIES
=====================================================================
HEALTHY -- without it, every detector could return its own condition
    unconditionally and the diagonal would be perfect.

UNDETERMINED-<c> -- the detector COULD NOT READ ITS OWN SIGNAL.  This must never
    collapse into HEALTHY.  A detector that reports "fine" when it means "I could
    not look" is the exact false green this design exists to kill.
    [[honest-failure-outcomes]] [[lookup-failure-needs-own-outcome]]

=====================================================================
 WHAT EACH DETECTOR KEYS ON -- AND WHAT IT MUST NOT
=====================================================================
(i) keys on ITEM-PRESENT and PENDING-ABSENT together.  NOT on latency: latency is
    the generic timeout this unit exists to replace.
(j) keys on the TASK'S OWN REPORTED STATE.  NOT on absence of output -- a healthy
    task with nothing to do produces none either.
(k) keys on RESOLVED SUBJECT SET vs the arm's EXPECTATION (U3's tuple).  NOT on
    anything failure-shaped: (k) is LIVE AND DELIVERING with every liveness
    signal green, which is precisely what makes it the dangerous one.

Machine-off/asleep DEFERS TO (i) -- v4 5 writes that down rather than leaving
it silent, so it is encoded here EXPLICITLY rather than falling out of ordering.

=====================================================================
 WHAT THIS MODULE DOES NOT DO
=====================================================================
  * It DETECTS; it does not CURE.  Nothing here restarts a poller, re-enables a
    task, or re-arms a glob.  A "fixed" report must never stand in for a
    measurement.
  * It touches NO live poller, NO live scheduled task, NO live arm.  Every signal
    is an INJECTED SEAM, the same posture as U4's ProcessOracle.  Reading live
    task state is adjacent to a standing fleet ruling and is not smuggled in under a detector.
  * It does NOT escalate.  6 names "condition-specific detection AND escalation
    outcome"; only the DETECTION half is here.  The escalation lane is tier-2
    outward, blocked on a pending item of that ruling.
  * A DISTINGUISHABLE diagnosis is not a CORRECT one.  This proves the three are
    told apart, never that the taxonomy carves reality at its joints.
"""

CONDITIONS_V1 = "WAKE-CONDITIONS/1"

# --- the closed diagnosis enum ----------------------------------------------
D_HEALTHY = "HEALTHY"
D_I = "UPSTREAM-CANONICAL-BLIND"
D_J = "OS-TASK-COMMON-MODE-DOWN"
D_K = "ARMED-WRONG-SUBJECT"
# ⛔ NOT a condition.  Named so that "we timed out and do not know why" is
# SAYABLE.  6: reporting a timeout AS a condition is the FAIL.
D_TIMEOUT = "DELIVERY-TIMEOUT-UNDIAGNOSED"
D_UNDET_I = "UNDETERMINED-i"
D_UNDET_J = "UNDETERMINED-j"
D_UNDET_K = "UNDETERMINED-k"

DIAGNOSES = (D_HEALTHY, D_I, D_J, D_K, D_TIMEOUT,
             D_UNDET_I, D_UNDET_J, D_UNDET_K)

# The three condition codes, kept separate from the enum above because "is this
# a CONDITION" is a different question from "is this a valid diagnosis".
CONDITION_CODES = (D_I, D_J, D_K)

# Task states that mean the shared tier-1/tier-2 task is down.  Enumerated rather
# than inferred: "not Ready" would also swallow Running, which is healthy.
TASK_DOWN_STATES = ("Disabled", "Missed", "LauncherDead", "Stopped")
TASK_OK_STATES = ("Ready", "Running")

# Machine states that DEFER to (i), per v4 5's written-down clause.
MACHINE_DEFERS_TO_I = ("asleep", "off")


class Unreadable(object):
    """Sentinel: a source that could not answer.

    Distinct from None-as-empty.  A source returning `UNREADABLE` is saying "I
    could not look", and every caller below must route that to UNDETERMINED
    rather than to a negative finding."""

    def __repr__(self):
        return "UNREADABLE"


UNREADABLE = Unreadable()


def _finding(code, detail, keyed_on):
    """Every finding carries WHAT IT KEYED ON, so a reader can check the
    detector against 3's table instead of trusting the code."""
    return {"code": code, "detail": detail, "keyed_on": keyed_on}


# --- (i) ---------------------------------------------------------------------
def detect_i(items, pending, machine_state=None):
    """UPSTREAM-CANONICAL-BLIND: item exists at intake, pending never written.

    Tiers 0/1/2 go blind TOGETHER while everything reads green, which is why
    this cannot key on latency -- there is nothing late, there is nothing at all.
    """
    if machine_state in MACHINE_DEFERS_TO_I:
        return _finding(D_I,
                        "machine is %r; v4 5 DEFERS machine-off/asleep to (i) "
                        "explicitly rather than leaving it silent." % machine_state,
                        "machine-state deferral")
    if items is UNREADABLE or pending is UNREADABLE:
        return _finding(D_UNDET_I,
                        "intake source unreadable (items=%r pending=%r). NOT "
                        "healthy -- the detector could not look."
                        % (items, pending),
                        "intake readability")
    if items and not pending:
        return _finding(D_I,
                        "%d item(s) at intake and canonical pending NEVER "
                        "WRITTEN. Tiers 0/1/2 blind together while every "
                        "surface reads green." % len(items),
                        "item-present AND pending-absent")
    return None


# --- (j) ---------------------------------------------------------------------
def detect_j(task_state):
    """OS-TASK-COMMON-MODE-DOWN: the shared tier-1/tier-2 task is down.

    Keys on the task's OWN reported state.  Absence of output is not a signal --
    a healthy task with nothing to do produces none either."""
    if task_state is UNREADABLE or task_state is None:
        return _finding(D_UNDET_J,
                        "task state could not be read. NOT healthy -- 'I could "
                        "not look' and 'it is fine' are different answers.",
                        "task-state readability")
    if task_state in TASK_DOWN_STATES:
        return _finding(D_J,
                        "shared tier-1/tier-2 task reports %r -- common-mode "
                        "down: BOTH tiers share it." % task_state,
                        "task's own reported state")
    if task_state not in TASK_OK_STATES:
        # An unrecognised state is not a pass.  The enum is closed on purpose;
        # a new state string is a fact about the world we have not modelled.
        return _finding(D_UNDET_J,
                        "task reports unmodelled state %r -- neither a known "
                        "down state nor a known healthy one." % (task_state,),
                        "task-state enum coverage")
    return None


# --- (k) ---------------------------------------------------------------------
def detect_k(arm, resolved_now):
    """ARMED-WRONG-SUBJECT: live and delivering, glob covering the wrong lane.

    ⛔ THE DANGEROUS ONE.  Every liveness signal is green; the arm mints, the
    watcher runs, events arrive.  A detector keyed to anything failure-shaped
    will never see it.  So this keys on the SUBJECT SETS and nothing else."""
    if resolved_now is UNREADABLE:
        return _finding(D_UNDET_K,
                        "current subject resolution unreadable. NOT healthy.",
                        "subject-set readability")
    extra = (arm or {}).get("extra") or {}
    expected = extra.get("subject_expected")
    if expected is None:
        return _finding(D_UNDET_K,
                        "arm carries no subject expectation (no U3 tuple), so "
                        "'wrong subject' is not a decidable question here.",
                        "arm tuple presence")
    expected = set(expected)
    resolved = set(resolved_now or [])
    missing = expected - resolved
    if missing:
        return _finding(D_K,
                        "arm is LIVE and its glob no longer covers %d expected "
                        "subject(s): %s. Every liveness signal is green; the "
                        "arm is simply watching the wrong lane."
                        % (len(missing), sorted(missing)),
                        "resolved subject set vs arm expectation")
    return None


# --- the whole set -----------------------------------------------------------
def detect_all(items=None, pending=None, task_state=None, arm=None,
               resolved_now=None, machine_state=None, delivery_overdue=False):
    """Present the world to the WHOLE detector set.

    Returns every finding, not the first.  A set that reports the first hit
    hides the second, and two conditions at once is a real state (control G12).
    """
    findings = []
    for f in (detect_i(items, pending, machine_state),
              detect_j(task_state),
              detect_k(arm, resolved_now)):
        if f is not None:
            findings.append(f)

    conditions = [f for f in findings if f["code"] in CONDITION_CODES]
    undetermined = [f for f in findings if f["code"] not in CONDITION_CODES]

    if not conditions and delivery_overdue:
        # ⛔ 6's rule, enforced: this is REPORTED AS ITS OWN OUTCOME and is
        # never dressed up as one of the three.  "Late, and we do not know why"
        # is an honest answer; "late, therefore (j)" is the FAIL.
        findings.append(_finding(
            D_TIMEOUT,
            "delivery is overdue and NO condition signal is present. This is "
            "NOT (i), (j) or (k): naming a condition here would be inventing a "
            "diagnosis from a symptom.",
            "overdue with no condition signal"))

    # HEALTHY only when nothing fired AND nothing was unreadable.  An
    # UNDETERMINED alongside silence is not health.
    if not findings:
        findings.append(_finding(D_HEALTHY,
                                 "no condition present and every signal was "
                                 "readable.",
                                 "all sources readable, none tripped"))

    codes = [f["code"] for f in findings]
    return {
        "conditions_v": CONDITIONS_V1,
        "findings": findings,
        "codes": codes,
        "condition_codes": [f["code"] for f in conditions],
        "undetermined_codes": [f["code"] for f in undetermined],
        "healthy": codes == [D_HEALTHY],
    }
