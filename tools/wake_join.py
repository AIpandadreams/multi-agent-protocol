"""U4 -- the causal join.  DESIGN-builder-v4 3.3, graded by U4-ACCEPTANCE-BAR-v1.

v3 asked only: DOES AN EVENT CARRYING T EXIST.  A genuine but causally unrelated
event -- right token, wrong watcher instance, wrong registration, wrong target
session, wrong arm, or simply replayed -- satisfies that while THE REVIEWED HOP
IS DEAD.  That is v4 2 row 5, codex's lead finding, and the precise false-green
this unit exists to kill.

U4 replaces "an event carrying T exists" with:

    THIS event was emitted BY the committed watcher instance, UNDER the reviewed
    registration, TO the target seat/session, FOR this arm, ONCE.

Everything else is REJECTED, not counted.

=====================================================================
 WHERE IDENTITY IS READ FROM -- THE CLAUSE 3.3 DOES NOT STATE
=====================================================================
3.3 requires the join to bind `watcher pid + process-start-time`.  It never
says WHERE those values come from, and that omission decides whether this module
is evidence or theatre:

    If the join compares the EVENT'S SELF-REPORTED pid/start-time against the
    arm, it verifies NOTHING.  A forger -- or an honest-but-wrong emitter --
    writes the expected values and passes.  Self-report is the thing under test;
    it cannot also be the instrument.
    [[self-stamp-probe-copied-or-nothing]] [[reviewer-constraints-are-claims]]

So identity is obtained from a source THE EMITTING PROCESS DOES NOT AUTHOR:

  (A) the ARM's committed watcher identity -- written into the arm BEFORE the
      event existed, so the event cannot have shaped it; or
  (B) an OS process-table oracle -- pid -> start-time, read by the GRADER.

The event's own copy is compared for CONSISTENCY and is never the only reading.
When NEITHER independent source is available the verdict is a named
CANNOT-VERIFY -- not a pass, and not a silent reject.
[[honest-failure-outcomes]] [[lookup-failure-needs-own-outcome]]

=====================================================================
 WHY pid ALONE IS NOT IDENTITY
=====================================================================
Pids are REUSED.  A matching pid whose process-start-time differs is a DIFFERENT
PROCESS WEARING A DEAD ONE'S NUMBER.  A pid-only comparison passes that case, and
a reader who sees "pid is bound" will believe identity is bound.  Control E4
exists for exactly this, and mutation M-U4-1 removes the start-time comparison to
prove E4 was doing the work.

=====================================================================
 THE HONEST CHECK-COUNT (3.7)
=====================================================================
v3 reported "four checks".  There is ONE load-bearing check and THREE
decorations, and this module reports it that way rather than letting a reader
count to four:

  LOAD-BEARING : an event carrying T exists AND binds to this arm/instance
  decoration   : sha256(proof) == commit  -- sound but near-vacuous once T public
  decoration   : notified-at              -- INHERITS the load-bearing check's
                                             integrity entirely; cannot exceed it
  decoration   : notified-at < ack        -- monotone-satisfiable by a patient seat

[[counts-and-relations-discipline]]

=====================================================================
 WHAT THIS MODULE DOES NOT DO
=====================================================================
  * It does NOT establish HONESTY.  v4 1 forbids the claim outright.  A bound
    join says the hop happened; it never says the reporter is truthful.
  * It does NOT close 2 row 7 (grader isolation) -- that is U5.  A fleet role
    name is NOT an OS boundary: every candidate runs as the same principal, and
    row 7 stays honestly uncovered rather than closed by an org chart.
  * `correlation_ack_at` carries NO evidentiary weight (3.4).  It is accepted
    into the record and READ BY NO BRANCH.  Control E11 grades the same failing
    fixture with and without it and requires an IDENTICAL verdict -- if the ack
    can move any verdict, the rename was cosmetic.
  * It does NOT ship the OS-backed oracle.  `ProcessOracle` is the seam; the
    arm-committed path (A) is fully implemented here and closes the clause on its
    own.  A real process-table reader is platform work with its own controls and
    is NOT smuggled in ungraded.
  * It does NOT verify the running watcher's minting routine.  v4 10 item 5:
    T's entropy source has been read by no voice.  `MIN_TOKEN_BITS` grades against
    the STATED bar; whether the live watcher meets it is unmeasured.
"""

import hashlib
import os

import wake_arm

JOIN_V1 = "WAKE-JOIN/1"

# --- closed verdict enum -----------------------------------------------------
V_BOUND = "BOUND"
V_REJECTED = "REJECTED"
V_CANNOT_VERIFY = "CANNOT-VERIFY"
VERDICTS = (V_BOUND, V_REJECTED, V_CANNOT_VERIFY)

# --- closed reason enum ------------------------------------------------------
# Every reason is produced by at least one control.  A reason nothing can produce
# is a branch nothing tests. [[closed-enum-needs-one-key-per-namespace]]
J_OK = "ok"
J_FIELD_MISSING = "event-field-missing"
J_SUBJECT_SEAT = "emitted-by-subject-seat"
J_PID_MISMATCH = "watcher-pid-mismatch"
J_START_MISMATCH = "watcher-start-time-mismatch"
J_ARM_MISMATCH = "different-arm"
J_TOKEN_MISMATCH = "token-mismatch"
J_REPLAY = "event-already-bound"
J_EXPIRED = "arm-expired"
J_TARGET_MISMATCH = "different-target-session"
J_REGISTRATION_MISMATCH = "different-registration"
J_TOKEN_ENTROPY = "token-below-entropy-bar"
J_NO_INDEPENDENT_IDENTITY = "no-independent-identity-source"
J_ARM_NOT_OPEN = "arm-not-open"
J_STORE_UNREADABLE = "store-unreadable"

REASONS = (J_OK, J_FIELD_MISSING, J_SUBJECT_SEAT, J_PID_MISMATCH,
           J_START_MISMATCH, J_ARM_MISMATCH, J_TOKEN_MISMATCH, J_REPLAY,
           J_EXPIRED, J_TARGET_MISMATCH, J_REGISTRATION_MISMATCH,
           J_TOKEN_ENTROPY, J_NO_INDEPENDENT_IDENTITY, J_ARM_NOT_OPEN,
           J_STORE_UNREADABLE)

# The event's declared shape.  Missing fields refuse BY NAME rather than crashing
# mid-derivation -- U1's F4 class, not repeating here.
REQUIRED_EVENT_FIELDS = ("event_id", "arm_id", "token", "emitter_seat",
                         "watcher_pid", "target_session", "registration_id")

# 3.3's stated entropy requirement, flagged in two prior rounds and fixed here
# rather than flagged again.  Graded against U1's own token width.
MIN_TOKEN_BITS = wake_arm.TOKEN_BITS

# 3.7's census, as DATA rather than as prose a reader has to trust.
LOAD_BEARING_CHECKS = ("event-binds-to-this-arm-and-instance",)
DECORATION_CHECKS = (
    "sha256(proof)==commit -- sound but near-vacuous once T is public",
    "notified-at -- inherits the load-bearing check's integrity entirely",
    "notified-at < ack -- monotone-satisfiable by a patient seat",
)

# Fields accepted into the record and READ BY NO BRANCH.  Named explicitly so the
# claim "carries no evidentiary weight" is checkable rather than asserted.
NON_EVIDENTIARY_FIELDS = ("correlation_ack_at",)


class ProcessOracle(object):
    """pid -> process start time, read by the GRADER, not by the emitter.

    This is the SEAM, deliberately.  A real process-table reader is platform
    work with its own controls; smuggling one in here ungraded would be the
    same defect this unit exists to kill.  `lookup` returns None when it cannot
    answer -- which is a FACT about the oracle, never a licence to fall back to
    the event's self-report."""

    def lookup(self, pid):
        raise NotImplementedError


class NullOracle(ProcessOracle):
    """Answers nothing.  With no arm-committed identity either, the join is
    CANNOT-VERIFY -- the honest outcome, not a pass."""

    def lookup(self, pid):
        return None


class DictOracle(ProcessOracle):
    """Test/inject oracle: an explicit pid -> start-time mapping."""

    def __init__(self, table):
        self._t = dict(table)

    def lookup(self, pid):
        return self._t.get(pid)


class SpentLog(object):
    """Event ids already bound.  A bound event is SPENT: presenting it again is
    replay, not a second delivery.

    File-backed rather than in-memory because replay across PROCESSES is the case
    that matters -- an in-memory set would make the rejection true only within one
    run, which is where replay does not happen."""

    def __init__(self, path=None):
        self.path = path
        self._mem = set()
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self._mem.add(line)

    def is_spent(self, event_id):
        return event_id in self._mem

    def mark_spent(self, event_id):
        if event_id in self._mem:
            return False
        self._mem.add(event_id)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(event_id + "\n")
        return True


def check_census():
    """3.7's count, computed from the declared tuples so prose cannot drift
    away from it. [[figures-restated-at-a-fold-are-rederivations]]"""
    return {
        "load_bearing": len(LOAD_BEARING_CHECKS),
        "decorations": len(DECORATION_CHECKS),
        "load_bearing_names": list(LOAD_BEARING_CHECKS),
        "decoration_names": list(DECORATION_CHECKS),
        "statement": ("%d load-bearing check with %d decorations -- NOT %d checks"
                      % (len(LOAD_BEARING_CHECKS), len(DECORATION_CHECKS),
                         len(LOAD_BEARING_CHECKS) + len(DECORATION_CHECKS))),
    }


def _result(verdict, reason, detail, **extra):
    out = {"join_v": JOIN_V1, "verdict": verdict, "reason": reason,
           "detail": detail}
    out.update(extra)
    return out


def _committed_identity(arm):
    """(pid, start) the ARM committed, or (None, None).

    Source (A).  Written into the arm BEFORE the event existed, so the event
    cannot have shaped it."""
    extra = arm.get("extra") or {}
    return extra.get("watcher_pid"), extra.get("watcher_start")


def join(arm, event, oracle=None, subject_seat=None, registration_id=None,
         target_session=None, spent=None, store=None, now=None):
    """Bind ONE event to ONE arm, or say why not.

    Returns a dict carrying a closed `verdict` and a closed `reason`.  Callers
    branch on those codes; the prose `detail` is for humans and is never parsed.
    """
    oracle = oracle or NullOracle()
    spent = spent if spent is not None else SpentLog()

    # --- shape first: refuse BY NAME, never KeyError mid-derivation ----------
    missing = [f for f in REQUIRED_EVENT_FIELDS if f not in event]
    if missing:
        return _result(V_REJECTED, J_FIELD_MISSING,
                       "event is missing declared field(s): %s" % sorted(missing))

    # --- arm keying ----------------------------------------------------------
    if event["arm_id"] != arm.get("arm_id"):
        return _result(V_REJECTED, J_ARM_MISMATCH,
                       "event names arm %r; this arm is %r. A genuine event for "
                       "ANOTHER arm is exactly v4 2 row 5 and is rejected, not "
                       "counted." % (event["arm_id"], arm.get("arm_id")))

    if str(event["token"]) != str(arm.get("token")):
        return _result(V_REJECTED, J_TOKEN_MISMATCH,
                       "token does not match arm %s" % arm.get("arm_id"))

    # --- 3.3 entropy bar, stated and enforced -------------------------------
    tok = str(arm.get("token") or "")
    bits = len(tok) * 4 if _is_hex(tok) else len(tok) * 8
    if bits < MIN_TOKEN_BITS:
        return _result(V_REJECTED, J_TOKEN_ENTROPY,
                       "token carries ~%d bits; the stated bar is %d. A short "
                       "token makes 'an event carrying T' guessable, which "
                       "collapses the one load-bearing check."
                       % (bits, MIN_TOKEN_BITS))

    # --- 3.5 grader isolation, the part U4 CAN enforce -----------------------
    # The seat under test cannot supply its own evidence.  U5 owns the process
    # boundary; this is the name-level exclusion only, and 2 row 7 stays open.
    if subject_seat is not None and event["emitter_seat"] == subject_seat:
        return _result(V_REJECTED, J_SUBJECT_SEAT,
                       "event was emitted by the SUBJECT SEAT (%r). The seat "
                       "under test does not supply its own evidence."
                       % subject_seat)

    # --- registration and target binding ------------------------------------
    if registration_id is not None and event["registration_id"] != registration_id:
        return _result(V_REJECTED, J_REGISTRATION_MISMATCH,
                       "event was emitted under registration %r; the reviewed "
                       "registration is %r."
                       % (event["registration_id"], registration_id))

    if target_session is not None and event["target_session"] != target_session:
        return _result(V_REJECTED, J_TARGET_MISMATCH,
                       "event was delivered to session %r; the target is %r."
                       % (event["target_session"], target_session))

    # --- IDENTITY, from a source the emitter does not author -----------------
    ev_pid = event["watcher_pid"]
    ev_start = event.get("watcher_start")          # SELF-REPORT: consistency only
    arm_pid, arm_start = _committed_identity(arm)
    oracle_start = oracle.lookup(ev_pid)

    independent_start = None
    identity_source = None
    if arm_start is not None:
        independent_start, identity_source = arm_start, "arm-committed"
    elif oracle_start is not None:
        independent_start, identity_source = oracle_start, "process-oracle"

    if arm_pid is not None and ev_pid != arm_pid:
        return _result(V_REJECTED, J_PID_MISMATCH,
                       "event claims watcher pid %r; the arm committed %r."
                       % (ev_pid, arm_pid), identity_source="arm-committed")

    if independent_start is None:
        # NEITHER independent source answered.  The event's own start-time is
        # present and may even look right -- and is worth exactly nothing here.
        return _result(V_CANNOT_VERIFY, J_NO_INDEPENDENT_IDENTITY,
                       "no independent identity source: the arm committed no "
                       "watcher start time and the oracle could not answer for "
                       "pid %r. The event's SELF-REPORTED start (%r) is the "
                       "thing under test and cannot verify itself. This is "
                       "CANNOT-VERIFY, not a pass and not a reject."
                       % (ev_pid, ev_start),
                       self_reported_start=ev_start)

    if str(independent_start) != str(ev_start):
        return _result(V_REJECTED, J_START_MISMATCH,
                       "process start time does not match: %s says %r, event "
                       "self-reports %r. A matching pid with a differing start "
                       "time is a DIFFERENT PROCESS wearing a dead one's number."
                       % (identity_source, independent_start, ev_start),
                       identity_source=identity_source)

    # --- arm must actually be open (expiry, supersession, replay) ------------
    # ⛔ THE REASON CODE IS DERIVED INDEPENDENTLY, NOT SNIFFED OUT OF U1'S PROSE.
    # `check_arm_token` returns (ok, human sentence, rc) and deliberately does not
    # expose a code.  An earlier draft of this branch picked J_EXPIRED by testing
    # `"expired" in why` -- i.e. this module parsed a peer module's prose to make
    # a control-flow decision, which is precisely what THIS module's own
    # TupleRefused-style contract tells its callers never to do.  A reworded
    # sentence upstream would have silently re-labelled every expiry as
    # ARM-NOT-OPEN, with no test able to see it.
    # So: U1 answers the AUTHORITATIVE question (is this arm open here), and the
    # expiry DISTINCTION is re-derived here from the arm's own `expires_at`.
    # [[emitter-and-verifier-are-one-grammar]] [[stated-reason-must-discriminate]]
    expired_now = False
    if arm.get("expires_at"):
        expired_now = wake_arm._parse_iso(arm["expires_at"]) <= (now or wake_arm._now())

    if store is not None:
        # `now` MUST travel with the question.  Without it U1 evaluated against
        # wall-clock while this module evaluated against the caller's `now`, so
        # the store-backed and store-less paths could answer DIFFERENTLY about
        # the same instant -- and the store-backed one is the path production
        # uses.  Caught by control E7b, which existed only because E7 was
        # exercising the fallback. [[true-green-answers-adjacent-question]]
        ok, why, rc = wake_arm.check_arm_token(store, arm["arm_id"],
                                               event["token"], now=now)
        if not ok:
            if rc == wake_arm.RC_CANNOT_RUN:
                return _result(V_CANNOT_VERIFY, J_STORE_UNREADABLE, why)
            return _result(V_REJECTED,
                           J_EXPIRED if expired_now else J_ARM_NOT_OPEN, why)
    elif expired_now and now is not None:
        return _result(V_REJECTED, J_EXPIRED,
                       "arm %s expired at %s"
                       % (arm["arm_id"], arm["expires_at"]))

    # --- replay: a bound event is SPENT --------------------------------------
    if spent.is_spent(event["event_id"]):
        return _result(V_REJECTED, J_REPLAY,
                       "event %s was already bound. A bound event is spent; "
                       "presenting it again is replay, not a second delivery."
                       % event["event_id"])
    spent.mark_spent(event["event_id"])

    return _result(V_BOUND, J_OK,
                   "event %s binds to arm %s: emitted by the committed watcher "
                   "instance (%s), under the reviewed registration, to the "
                   "target session, once."
                   % (event["event_id"], arm["arm_id"], identity_source),
                   identity_source=identity_source,
                   checks=check_census())


def _is_hex(s):
    try:
        int(s, 16)
        return bool(s)
    except (ValueError, TypeError):
        return False


def proof_matches_commit(proof, commit):
    """3.7's first decoration, provided because U4's callers need it -- and
    labelled a DECORATION at the point of use so nobody counts it as a fourth
    independent check.  Sound, and near-vacuous once T is public."""
    return hashlib.sha256(proof.encode("utf-8")).hexdigest() == commit
