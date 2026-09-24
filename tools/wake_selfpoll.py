"""Self-poll overlap detector -- U7's own prerequisite.
DESIGN-builder-v4 6: "self-poll overlap -- WHICH FIRST NEEDS ITS DETECTOR,
since v3's 'not citable' was unenforceable."

⚠ WHY THIS LIVES IN U7 AND NOT U6.  U6 built 5's (i)/(j)/(k).  Self-poll
overlap is a FOURTH condition, outside 5's list, and no other unit claims it.
6 makes the detector a PREREQUISITE of the mutation, so U7 builds it.

⛔ AND THE HAZARD THAT CREATES, NAMED AT THE SITE: a mutation graded by a
detector built in the SAME unit can be "passed" by tuning the detector until the
mutation stops firing.  The guard is that this detector is written against the
CONDITION, is fixed before the mutation row runs, and carries its own positive
control and its own UNDETERMINED -- the same discipline U6 shipped.
[[emitter-and-verifier-are-one-grammar]]

WHAT "SELF-POLL OVERLAP" IS.  A poller whose run N has not finished when run N+1
starts.  The second run observes the first's in-flight state and can read a
half-written world as a settled one.  v3 said such a reading was "not citable",
which is a rule with no instrument -- unenforceable is the same as absent.

WHAT THIS DOES NOT DO.  It reads INTERVALS it is handed.  It does not attach to a
live poller, does not stop one, and does not decide whether an overlap actually
corrupted a particular reading -- only that the window in which it could was open.
"""

SELFPOLL_V1 = "WAKE-SELFPOLL/1"

SP_OK = "SELFPOLL-OK"
SP_OVERLAP = "SELFPOLL-OVERLAP"
SP_UNDETERMINED = "SELFPOLL-UNDETERMINED"
SELFPOLL_CODES = (SP_OK, SP_OVERLAP, SP_UNDETERMINED)


def _f(code, detail, pairs=()):
    return {"selfpoll_v": SELFPOLL_V1, "code": code, "detail": detail,
            "overlapping_pairs": list(pairs)}


def detect(intervals):
    """`intervals` is a sequence of (run_id, start, end).

    Endpoints are compared as given; they must be mutually comparable numbers or
    ISO strings of equal shape.  A run whose end is MISSING (None) is still
    RUNNING -- that is not unknown, it is the overlap case if anything starts
    after it, and it is treated as such rather than skipped.
    """
    if intervals is None:
        return _f(SP_UNDETERMINED,
                  "no interval source: the detector could not look. NOT 'no "
                  "overlap' -- absence of data is not absence of the condition.")
    runs = list(intervals)
    if len(runs) < 2:
        return _f(SP_OK,
                  "%d run(s) observed: overlap is not expressible with fewer "
                  "than two, and this is reported as OK rather than as a "
                  "detection." % len(runs))

    for rid, start, end in runs:
        if start is None:
            return _f(SP_UNDETERMINED,
                      "run %r has no start time; ordering is undecidable and a "
                      "guess here would manufacture either verdict." % (rid,))

    ordered = sorted(runs, key=lambda r: r[1])
    pairs = []
    for i in range(len(ordered) - 1):
        rid_a, start_a, end_a = ordered[i]
        rid_b, start_b, _ = ordered[i + 1]
        if end_a is None:
            # Still running when the next one started.
            pairs.append((rid_a, rid_b, "run %r had not finished" % (rid_a,)))
        elif start_b < end_a:
            pairs.append((rid_a, rid_b,
                          "run %r started at %r, before run %r ended at %r"
                          % (rid_b, start_b, rid_a, end_a)))

    if pairs:
        return _f(SP_OVERLAP,
                  "%d overlapping run pair(s): a later poll observed an earlier "
                  "poll's IN-FLIGHT state and can read a half-written world as "
                  "a settled one." % len(pairs), pairs)
    return _f(SP_OK, "%d runs, none overlapping." % len(runs))
