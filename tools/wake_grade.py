"""U2 -- the STRUCTURAL grader.  DESIGN-builder-v4 3.1, IMPL-PLAN-builder-v1 U2.

Answers exactly one question: *was a wake for THIS arm delivered into THAT
session's store* -- by parsing the store's records and matching TOP-LEVEL typed
fields, never by searching the store's text for the arm token.

WHY STRUCTURAL, AND WHAT A TEXTUAL GRADER WOULD GET WRONG (v4 2 row 2):
a seat can cause the arm envelope to appear in the store as transcribed CONTENT,
with no write at all, simply by reading a file that contains it.  A bare hex
token is reachable that way, so `token in raw_bytes` grades that as DELIVERED --
the false green this unit exists to kill.  A top-level typed record carrying a
matching `sessionId` is NOT reachable that way: transcribed content lands nested
inside a record's message body, JSON-escaped, and does not become a top-level
field of a new record of a declared kind.

  => The correctness claim of this module is precisely: *the discrimination
     between a top-level typed field and nested content is the thing doing the
     work.*  `wake_grade_controls.py` exists to prove that claim is not vacuous,
     by building the forbidden textual grader as a MUTANT and showing the
     content-echo control flips.

THE STORE IS NAMED BY THE ARM, NEVER BY THE SUBJECT (v4 2 row 3).  Choosing
the evidence file is equivalent to authoring it.  The arm carries the session
id; a record whose top-level `sessionId` differs from the arm's is REFUSED even
when it sits in the file this grader was pointed at.

WHAT A GREEN FROM THIS MODULE IS NOT (v4 1, IMPL-PLAN 5, and the U2
acceptance bar 6 -- restated at the code because a limitation that lives only
in a workpaper is one refactor from being lost):
  * NOT evidence any seat is honest.  The chain is tamper-EVIDENT against a
    broken seat and tamper-TRANSPARENT against a determined one.  Nothing here
    may be described as unforgeable or tamper-proof.
  * NOT a causal claim.  The join -- commit, receipt, notification, watcher pid
    and start time, seat, proof, ack -- is U4.  This is a MEMBERSHIP question
    about one store.
  * NOT a statement about who ran the computation.  Grader isolation is U5.
  * NOT a statement about the world.  Sink enumeration is unresolved (v4 10
    item 3): a NOT-DELIVERED bounds ONE STORE, not every path a wake could take.

VERB STRENGTH (v4 3.8, row 9).  The one record shape actually measured in the
live store is `{"type":"queue-operation","operation":"enqueue"}` -- and ENQUEUED
IS NOT SURFACED-TO-THE-MODEL AND NOT READ.  v3 never defined what "event" meant
and so attested the weakest verb in the chain.  This module therefore refuses to
carry a default kind set: `kinds` is REQUIRED, closed, and the result NAMES the
kind and operation that satisfied it, so a caller can see that it graded on a
weak verb instead of discovering it two rounds later.
"""

import json
import os

# --- The outcome enum.  CLOSED, and every member is reachable by a control. ---
# An outcome no control can produce is an outcome nothing tests; an outcome that
# collapses into another is a lie about what was learned.  In particular
# UNPARSEABLE and STORE-ABSENT are NOT spellings of NOT-DELIVERED: "I could not
# read it" and "it is not there" are different facts about the world, and only
# one of them is evidence about delivery.
DELIVERED = "DELIVERED"
NOT_DELIVERED = "NOT-DELIVERED"
UNPARSEABLE = "UNPARSEABLE"
STORE_ABSENT = "STORE-ABSENT"
ARM_INVALID = "ARM-INVALID"
OUTCOMES = (DELIVERED, NOT_DELIVERED, UNPARSEABLE, STORE_ABSENT, ARM_INVALID)

# U1's record shape (wake_arm.ARM_RECORD_V1).  Duplicated as a STRING rather
# than imported so that this module states the version it was written against;
# a U1 bump must break here loudly instead of silently grading a shape nobody
# checked.  The controls assert the two agree.
ARM_RECORD_V1 = "WAKE-ARM/1"
ARM_REQUIRED = ("v", "arm_id", "token", "scope")

# Top-level keys a delivery record may carry the arm binding under.  Closed, and
# the KEY MUST BE TOP LEVEL -- that requirement is the whole defence, so it is
# expressed as a dict lookup on the record itself and never as a recursive walk.
BIND_KEYS = ("armId", "arm_id", "taskId", "task-id")

# Top-level key carrying the session the record belongs to.  Measured, not
# assumed: 400/400 records in the sampled live store carry top-level `type` and
# `sessionId`.
SESSION_KEY = "sessionId"
TYPE_KEY = "type"
OP_KEY = "operation"


class ArmInvalid(Exception):
    pass


def _check_arm(arm):
    """Refuse BY NAME at the read, not by KeyError halfway through a match."""
    if not isinstance(arm, dict):
        raise ArmInvalid("arm is not a JSON object")
    if arm.get("v") != ARM_RECORD_V1:
        raise ArmInvalid(
            "arm version %r is not %s -- refusing to guess its shape"
            % (arm.get("v"), ARM_RECORD_V1))
    missing = [k for k in ARM_REQUIRED if k not in arm]
    if missing:
        raise ArmInvalid("arm is missing required field(s): %s" % ", ".join(missing))
    sid = arm_session_id(arm)
    if not sid:
        raise ArmInvalid(
            "arm names no session id -- the store must be named BY THE ARM "
            "(v4 2 row 3); grading a caller-chosen store is authoring the "
            "evidence")
    return sid


def arm_session_id(arm):
    """The session the arm targets.

    U1 as built carries the tuple's optional members under `extra`; U3 restores
    them to first-class fields.  Both spellings are accepted HERE so that U3's
    landing does not silently change what U2 grades -- and neither is invented:
    if the arm names no session, `_check_arm` refuses rather than defaulting.
    """
    if isinstance(arm.get("session_id"), str) and arm["session_id"]:
        return arm["session_id"]
    extra = arm.get("extra")
    if isinstance(extra, dict):
        for k in ("session_id", "sessionId"):
            v = extra.get(k)
            if isinstance(v, str) and v:
                return v
    return None


def _binds_to_arm(rec, arm):
    """True iff `rec` carries this arm's id/token in a TOP-LEVEL binding key.

    Deliberately NOT a recursive search.  A nested hit is exactly the
    content-echo channel, and a walk that found it would reintroduce the defect
    this module exists to remove.
    """
    wanted = (arm["arm_id"], arm["token"])
    for k in BIND_KEYS:
        if k in rec and rec[k] in wanted:
            return k
    return None


def grade(arm, store, kinds, ops=None):
    """Grade one arm against one store.  Returns a result dict; never raises
    for an ordinary negative -- an exception here would be a THIRD channel for
    "no" and would not be distinguishable from the honest outcomes.

    `kinds` is REQUIRED and closed (see the VERB STRENGTH note in the module
    docstring).  `ops`, when given, further restricts `operation`.
    """
    result = {
        "outcome": None,
        "store": store,
        "records_scanned": 0,
        "records_parsed": 0,
        "matched": None,
        "reason": "",
        "kinds": sorted(kinds),
        "ops": (sorted(ops) if ops else None),
    }

    if not kinds:
        result["outcome"] = ARM_INVALID
        result["reason"] = (
            "no delivery kinds declared -- refusing to invent one. v4 3.8: "
            "an undeclared 'event' attests the weakest verb in the chain")
        return result

    try:
        session_id = _check_arm(arm)
    except ArmInvalid as e:
        result["outcome"] = ARM_INVALID
        result["reason"] = str(e)
        return result
    result["arm_id"] = arm["arm_id"]
    result["session_id"] = session_id

    if not os.path.exists(store):
        result["outcome"] = STORE_ABSENT
        result["reason"] = "store does not exist: %s" % store
        return result

    # Parse the WHOLE store before judging.  A store we cannot fully parse is a
    # store we cannot reason about: partial parsing would let an unreadable tail
    # be reported as a clean NOT-DELIVERED. [[honest-failure-outcomes]]
    records = []
    try:
        with open(store, "r", encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                result["records_scanned"] += 1
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except ValueError as e:
                    result["outcome"] = UNPARSEABLE
                    result["reason"] = "%s:%d is not valid JSON (%s)" % (store, n, e)
                    return result
                if not isinstance(rec, dict):
                    result["outcome"] = UNPARSEABLE
                    result["reason"] = "%s:%d is not a JSON object" % (store, n)
                    return result
                records.append((n, rec))
    except (IOError, OSError, UnicodeDecodeError) as e:
        result["outcome"] = UNPARSEABLE
        result["reason"] = "store could not be read as UTF-8 JSONL: %s" % e
        return result

    result["records_parsed"] = len(records)

    # THE MATCH.  Three independent top-level conditions, each of which some
    # control below turns off on its own, because a conjunction whose members
    # are never varied separately is one condition wearing three names.
    for n, rec in records:
        if rec.get(TYPE_KEY) not in kinds:
            continue
        if ops is not None and rec.get(OP_KEY) not in ops:
            continue
        if rec.get(SESSION_KEY) != session_id:
            continue
        bind = _binds_to_arm(rec, arm)
        if not bind:
            continue
        result["outcome"] = DELIVERED
        # C9: a pass must ATTRIBUTE.  Without naming the record, a store holding
        # both a real delivery and a content echo cannot tell a reader whether
        # the grader answered for the right reason.
        result["matched"] = {
            "line": n,
            TYPE_KEY: rec.get(TYPE_KEY),
            OP_KEY: rec.get(OP_KEY),
            "bind_key": bind,
        }
        # The reason reports what was OBSERVED IN THE RECORD, never what was
        # sought.  Under this grader the two are equal because the match
        # required it -- but printing `session_id` here would make the sentence
        # true by construction rather than by reading, and a reason that cannot
        # be wrong cannot be evidence.  (Caught by M-U2-2's own output: with the
        # session check removed, the seeking-form still printed the ARM's
        # session beside a record carrying a different one.)
        # [[stated-reason-must-discriminate]]
        result["reason"] = (
            "top-level %s=%r, %s=%r (record's own value), %s bound to arm at line %d"
            % (TYPE_KEY, rec.get(TYPE_KEY), SESSION_KEY, rec.get(SESSION_KEY), bind, n))
        return result

    result["outcome"] = NOT_DELIVERED
    # The count rides the negative ON PURPOSE: an empty answer has to come from
    # a query that ran. [[empty-result-needs-its-count]]
    result["reason"] = (
        "no record matched all of: top-level %s in %s%s, top-level %s == %r, "
        "and an arm binding in a TOP-LEVEL key of %s. %d record(s) parsed."
        % (TYPE_KEY, sorted(kinds),
           ("" if ops is None else (" and %s in %s" % (OP_KEY, sorted(ops)))),
           SESSION_KEY, session_id, list(BIND_KEYS), len(records)))
    return result
