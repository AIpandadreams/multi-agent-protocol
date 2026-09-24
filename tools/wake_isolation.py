"""U5 — grader isolation.

Bar: the U5 acceptance bar, v1 (in the private workspace).
Design: DESIGN-builder-v4 §3.5, and §2 rows 7 and 8.

U5 decides WHO may run the grader. It never touches WHAT the grader computes.

Three clauses from the bar are load-bearing here, and each is marked at its site:

  1. The barred set is the TRANSITIVE CLOSURE of the spawn graph rooted at the
     subject seat.  A bar over direct children passes a grandchild.
  2. Parentage is DERIVED from a source the candidate does not author.  A
     candidate's own claim about its parent is exactly the thing under test.
  3. Isolation is NOT a boolean.  §2 row 7 — impersonate the grader under the
     shared principal — is UNCOVERED by mechanism, so every result carries that
     residual on its face, including every ALLOW.
"""

ISO_V1 = "WAKE-ISOLATION/1"

# ── verdicts ──────────────────────────────────────────────────────────────────
V_ALLOWED = "ALLOWED"
V_BARRED = "BARRED"
V_CANNOT_ESTABLISH = "CANNOT-ESTABLISH"

# ── reason codes — closed enum, travelling as CODES ───────────────────────────
# They are never parsed out of another module's prose.  (An earlier entry's defect.)
I_OK = "I_OK"
I_SUBJECT_SEAT = "I_SUBJECT_SEAT"
I_DESCENDANT = "I_DESCENDANT"
I_GRAPH_UNAVAILABLE = "I_GRAPH_UNAVAILABLE"
I_NO_PROCESS_IDENTITY = "I_NO_PROCESS_IDENTITY"
I_NO_LAUNCH_AUTHORITY = "I_NO_LAUNCH_AUTHORITY"
I_ROLE_NAME_ONLY = "I_ROLE_NAME_ONLY"

REASON_CODES = (
    I_OK, I_SUBJECT_SEAT, I_DESCENDANT, I_GRAPH_UNAVAILABLE,
    I_NO_PROCESS_IDENTITY, I_NO_LAUNCH_AUTHORITY, I_ROLE_NAME_ONLY,
)

# ⛔ §2 row 7, carried on EVERY result — see `_result`.
ROW7_RESIDUAL = (
    "UNCOVERED: grader impersonation under the shared principal. Every candidate "
    "runs as the same OS principal; a fleet role name is not an OS boundary. "
    "This verdict closes DESIGN-builder-v4 §2 row 7 under §1 only, never by "
    "mechanism."
)

# A fleet role name is an ADDRESSING convention, not an identity.  Naming one of
# these does not tell you which process is speaking.
FLEET_ROLE_NAMES = (
    "owner", "builder", "orchestrator", "creator", "engine", "helper", "orch",
)

# Read for disclosure only.  Nothing below may branch on these.
NON_EVIDENTIARY_FIELDS = ("declared_parent",)


class Unavailable(object):
    """Sentinel: the oracle could not look.  Distinct from 'looked, found none'."""

    def __repr__(self):
        return "UNAVAILABLE"


UNAVAILABLE = Unavailable()


# ── the spawn-graph seam ──────────────────────────────────────────────────────
class SpawnGraphOracle(object):
    """Answers `parent_of(agent_id)` from a source the CANDIDATE does not author.

    ⛔ Clause 2.  The production wiring of this seam is out of U5's scope and is
    stated as non-coverage in the bar §8.4: U5 grades the graph it is handed.
    """

    def __init__(self, edges):
        # edges: {child_id: parent_id}
        self._edges = dict(edges)

    def parent_of(self, agent_id):
        return self._edges.get(agent_id)


class NullGraphOracle(object):
    """Cannot look at all — every query is UNAVAILABLE, never 'no parent'."""

    def parent_of(self, agent_id):
        return UNAVAILABLE


class ProcessIdentityOracle(object):
    """pid + process-start-time, per U4's oracle discipline (bar §5)."""

    def __init__(self, table):
        # table: {agent_id: (pid, start_time)}
        self._table = dict(table)

    def identify(self, agent_id):
        return self._table.get(agent_id)


class LaunchAuthorityOracle(object):
    """The concrete launcher identity, checkable against something the grader
    does not author (bar §5)."""

    def __init__(self, table):
        self._table = dict(table)

    def authority_for(self, agent_id):
        return self._table.get(agent_id)


# ── result construction ───────────────────────────────────────────────────────
def _result(verdict, reason, detail, **extra):
    """⛔ Clause 3 lives here.  There is ONE constructor and it always attaches
    the row-7 residual, so an ALLOW cannot be minted without it.
    """
    assert reason in REASON_CODES, "reason code outside the closed enum: %r" % (reason,)
    out = {
        "schema": ISO_V1,
        "verdict": verdict,
        "reason": reason,
        "detail": detail,
        "residual": ROW7_RESIDUAL,
    }
    out.update(extra)
    return out


# ── the closure ───────────────────────────────────────────────────────────────
def ancestors(candidate_id, graph):
    """Walk UP the spawn graph from `candidate_id`, transitively.

    ⛔ Clause 1.  Returns (chain, ok):
      chain — every ancestor reached, nearest first
      ok    — False if the oracle could not look at any step

    A `seen` set makes a cyclic graph terminate rather than hang (bar J15);
    cycles happen in real graphs and a hang is not a verdict.
    """
    chain = []
    seen = set([candidate_id])
    current = candidate_id
    while True:
        parent = graph.parent_of(current)
        if parent is UNAVAILABLE:
            return chain, False
        if parent is None:
            return chain, True
        if parent in seen:
            # Cycle. Everything reachable is already in `chain`; stop.
            return chain, True
        chain.append(parent)
        seen.add(parent)
        current = parent


def check(candidate, subject_seat, graph=None, identity=None, authority=None):
    """Decide whether `candidate` may run the grader.

    `candidate` is a dict carrying at least `agent_id`.  A `declared_parent`, if
    present, is NON-EVIDENTIARY: it is echoed for disclosure and never branched on.

    ORDER IS DELIBERATE — the bar (§6 J2/J3/J4) requires a barred candidate to be
    reported BARRED even when its process cannot be resolved.  So the closure is
    consulted FIRST and identity second: the failure direction is toward BARRED,
    never toward ALLOWED.
    """
    agent_id = candidate.get("agent_id")
    if agent_id is None:
        return _result(V_CANNOT_ESTABLISH, I_NO_PROCESS_IDENTITY,
                       "candidate carries no agent_id")

    declared = dict((k, candidate.get(k)) for k in NON_EVIDENTIARY_FIELDS
                    if k in candidate)

    graph = graph if graph is not None else NullGraphOracle()

    # ── clause 1 + clause 2 ───────────────────────────────────────────────────
    if agent_id == subject_seat:
        return _result(V_BARRED, I_SUBJECT_SEAT,
                       "candidate IS the subject seat %r" % (subject_seat,),
                       spawn_path=[agent_id], non_evidentiary=declared)

    chain, ok = ancestors(agent_id, graph)
    if not ok:
        # ⛔ 'could not look' is its own outcome and never reads as 'not barred'.
        return _result(V_CANNOT_ESTABLISH, I_GRAPH_UNAVAILABLE,
                       "spawn-graph source could not be read for %r" % (agent_id,),
                       spawn_path=[agent_id] + chain, non_evidentiary=declared)

    if subject_seat in chain:
        hops = chain.index(subject_seat) + 1
        return _result(
            V_BARRED, I_DESCENDANT,
            "candidate is %d hop(s) below the subject seat %r in the DERIVED "
            "spawn graph" % (hops, subject_seat),
            spawn_path=[agent_id] + chain, hops=hops, non_evidentiary=declared)

    # ── clause: naming (bar §5) ───────────────────────────────────────────────
    if agent_id in FLEET_ROLE_NAMES:
        return _result(V_CANNOT_ESTABLISH, I_ROLE_NAME_ONLY,
                       "candidate is named only by the fleet role %r, which is an "
                       "addressing convention and not an identity" % (agent_id,),
                       spawn_path=[agent_id] + chain, non_evidentiary=declared)

    ident = identity.identify(agent_id) if identity is not None else None
    if not ident:
        return _result(V_CANNOT_ESTABLISH, I_NO_PROCESS_IDENTITY,
                       "no pid+start-time resolves for %r" % (agent_id,),
                       spawn_path=[agent_id] + chain, non_evidentiary=declared)

    auth = authority.authority_for(agent_id) if authority is not None else None
    if not auth:
        return _result(V_CANNOT_ESTABLISH, I_NO_LAUNCH_AUTHORITY,
                       "no launch authority resolves for %r" % (agent_id,),
                       spawn_path=[agent_id] + chain, grader_process=ident,
                       non_evidentiary=declared)

    return _result(V_ALLOWED, I_OK,
                   "no path from the subject seat %r; identity and launch "
                   "authority both resolve" % (subject_seat,),
                   spawn_path=[agent_id] + chain, grader_process=ident,
                   launch_authority=auth, non_evidentiary=declared)
