#!/usr/bin/env python3
"""Heartbeat-lease custody probe — the liveness half of D-1 (DESIGN §2.4).

Answers exactly one question: **is another seat live in this working tree right now?**

⛔ WHY A LEASE AND NOT THE THREE OBVIOUS THINGS. The design measured the alternatives and
each fails differently: `plans/.seat.*` files carry no liveness semantics and no expiry (7
were present, two of them test fixtures); transcript mtime measures the HARNESS, not tree
custody, so a seat can hold the tree while sitting silent; a plain lock file survives its
owner's crash and blocks the whole fleet forever. A lease is a lock with an expiry, which
is the only one of the three that degrades correctly.

⛔ THE TTL IS NOT DEFAULTED, AND THAT IS THE POINT (design O-1). It must exceed the longest
gap between a live seat's consecutive writes, and that distribution HAS NOT BEEN MEASURED.
A guessed TTL fails in one of two ways, both bad: too short green-lights a discard against
a peer who is merely thinking; too long blocks a fleet whose seats have all exited. So
`ttl_seconds` is a REQUIRED argument and a missing one RAISES — never silently becomes a
number somebody picked once [[missing-symbol-must-raise-not-default]], [[stated-bound-is-an-open]].

⛔ EVERY FAILURE PATH RAISES. There is no return value meaning "could not tell". A probe
that cannot answer must not be readable as "nobody is live" — that fail-OPEN shape is the
exact destruction class this whole unit exists to prevent [[unknown-is-not-unparseable]].
Callers catch CustodyProbeError and REFUSE the verb; they never treat it as a clear tree.
"""
import os, re, time, pathlib, errno

LEASE_DIR_NAME = "plans"
LEASE_PREFIX = ".custody."
# <seat>.<session> — both restricted so a crafted filename cannot escape the directory or
# smuggle separators into the parsed identity.
LEASE_RE = re.compile(r"^\.custody\.([a-z][a-z0-9-]{0,31})\.([A-Za-z0-9_-]{1,64})$")


class CustodyProbeError(Exception):
    """The probe could not answer. Callers MUST refuse the guarded verb, never proceed."""


def _lease_dir(workspace):
    d = pathlib.Path(workspace) / LEASE_DIR_NAME
    if not d.is_dir():
        # A missing ledger dir is not "no peers" — it means we are not where we think we
        # are, and every reading that follows would be about the wrong tree.
        raise CustodyProbeError("no %s/ directory under %s — probe cannot answer" % (LEASE_DIR_NAME, workspace))
    return d


def touch(workspace, seat, session, tree=None):
    """Renew this seat's lease. Called on every tool-use boundary.

    Writes the wall-clock stamp as the file's CONTENT as well as its mtime: mtime alone is
    lost by copies, archives and some sync tools, and a lease whose age silently resets is
    worse than no lease [[carried-artifacts-expire]].

    `tree` is the WORKING TREE this seat is typing in, written on line 2. Omitted, the
    lease is byte-identical to the pre-CUSTODY-LEASE-TREE form, and a tree-scoped census
    counts it (see the module note above): the field is additive and no caller is required
    to pass it before its own row lands.
    """
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", seat or ""):
        raise CustodyProbeError("refusing to write a lease for malformed seat %r" % (seat,))
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session or ""):
        raise CustodyProbeError("refusing to write a lease for malformed session %r" % (session,))
    if tree is not None and not str(tree).strip():
        # An empty string is not "no tree" -- it is a resolver that failed and was written
        # anyway, and it would read back as an unrecorded tree, i.e. as a peer in EVERY
        # tree. Refuse it at the write, where the caller can still tell the difference.
        raise CustodyProbeError("refusing to write a blank tree field; pass None instead")
    p = _lease_dir(workspace) / ("%s%s.%s" % (LEASE_PREFIX, seat, session))
    body = "%.3f\n" % time.time()
    if tree is not None:
        body += "%s\n" % str(tree).strip()
    p.write_text(body, encoding="utf-8")
    return p


# --- CUSTODY-LEASE-TREE (a fleet ruling; the builder's entry) ------------------------
# ⛔ A LEASE RECORDED WHICH SEAT IS ALIVE AND NEVER WHICH TREE IT TYPES IN. The lease
#    NAMESPACE was the workspace; the destruction RADIUS is the working tree. Those
#    coincided while every seat shared one checkout. A later fleet ruling put publication into
#    linked worktrees and they came apart IN BOTH DIRECTIONS, measured on the shipping
#    registration rather than reasoned about:
#
#      false-REFUSE  custody_emit_wrapper.sh runs the emitter with
#                    `--project-dir "$CLAUDE_PROJECT_DIR"`, so a seat typing in a linked
#                    worktree writes its lease into the LIVE tree's plans/. A discard in
#                    the live tree is then refused on account of a peer who is somewhere
#                    else entirely and cannot be touched by it.
#      fail-OPEN     the guard's scope test clears any cwd outside the guarded workspace,
#                    so a discard INSIDE a worktree is never gated at all -- even with a
#                    peer live in that same worktree. That is arm C of
#                    tools/tests/custody_guard_worktree_scope_controls.py, and it lives in
#                    the HOOK's scope test, not here: the tree field is what makes a
#                    tree-scoped census possible, and closing arm C additionally requires
#                    the hook to run the census in a worktree at all. Named, not implied.
#
# ⭐ THE UNKNOWN TREE COUNTS AS A PEER. A lease written before this change carries no
#    tree line, and a tree-scoped census must decide what to do with it. Dropping it is
#    FAIL-OPEN -- a peer disappears from the census because of a format detail -- and
#    fail-open is the single class this whole module exists to prevent. So an unrecorded
#    tree is COUNTED, which can only ever cost a false refusal, never a lost peer.
#    [[honest-failure-outcomes]] [[unknown-is-not-unparseable]]


def worktree_root(start):
    """The working-tree root containing `start`, or None.

    Walks up for a `.git` entry. A linked worktree carries `.git` as a FILE (a
    `gitdir:` pointer) and the primary checkout carries it as a DIRECTORY -- BOTH stop
    the walk, and that is precisely what makes this resolver see the two as different
    trees rather than collapsing a worktree onto its parent repo.

    ⭐ NO SUBPROCESS. `git rev-parse --git-common-dir` would answer the same question
    and would cost a process spawn on every tool call; git_guard_hook.py's own docstring
    names spawn cost as the measured cause of hook cancellation, i.e. of this guard's
    fail-open mode. A cure that buys correctness with the guard's own disarming is not a
    cure. This is a bounded parent walk over paths that already exist.
    """
    try:
        p = pathlib.Path(start).resolve()
    except OSError:
        return None
    for cand in [p] + list(p.parents):
        if (cand / ".git").exists():
            return str(cand)
    return None


def _same_tree(a, b):
    """Path equality for two tree roots, normalised for case and separators.

    NOT `os.path.samefile`: a peer's worktree may have been REMOVED since the lease was
    written, and samefile raises on a missing path -- turning a stale lease into a probe
    error and a refusal of an unrelated verb. String comparison degrades to 'not the same
    tree', which for a vanished tree is the true answer.
    """
    if a is None or b is None:
        return False
    n = lambda s: os.path.normcase(os.path.normpath(os.path.abspath(str(s))))
    return n(a) == n(b)


def _lease_lines(p):
    """Raw lines of a lease, or None if it vanished between listing and reading."""
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as e:
        if e.errno == errno.ENOENT:
            return None
        raise CustodyProbeError("lease %s unreadable: %s" % (p.name, e))
    return raw.split("\n")


def _tree_of(p):
    """The tree root a lease records, or None when it records none.

    ⚠ Read SEPARATELY from _age_of rather than by widening it to return a pair.
    test_custody.py's M4 mutation control monkeypatches `_age_of(p, now)` wholesale to
    prove the expiry check is live; changing that function's arity or return type would
    make the mutant stop mutating while the control still reported green. The surface a
    control patches is part of that control's contract.
    [[a-mutation-control-needs-a-no-op-mutant]]
    """
    lines = _lease_lines(p)
    if lines is None or len(lines) < 2:
        return None
    tree = lines[1].strip()
    return tree or None


def _age_of(p, now):
    """Age in seconds, preferring the written stamp over mtime; unreadable => raise."""
    lines = _lease_lines(p)
    if lines is None:
        # Vanished between listing and reading. A peer exiting mid-probe is normal;
        # treat as absent rather than as an error.
        return None
    # ⛔ THE FIRST LINE, not the whole file. A lease may now carry a tree on line 2, and
    #    `float(whole_file)` would raise on every NEW lease -- which fails CLOSED (the
    #    caller refuses the verb) but for a reason that has nothing to do with custody.
    #    An OLD one-line lease reads identically here, so the two formats coexist.
    #    [[emitter-and-verifier-are-one-grammar]]
    raw = lines[0].strip()
    try:
        stamped = float(raw)
    except ValueError:
        # Present but garbage is NOT absent. Refuse rather than skip the row — a corrupt
        # lease is exactly the state an attacker or a crash would leave behind, and
        # skipping it silently converts it into "no peer here".
        raise CustodyProbeError("lease %s has an unparseable stamp %r" % (p.name, raw[:40]))
    age = now - stamped
    if age < 0:
        # Future-dated: clock skew or corruption. Never a silent pass — the same rule the
        # wake protocol applies to the daemon heartbeat.
        raise CustodyProbeError("lease %s is future-dated by %.1fs — clock skew or corruption" % (p.name, -age))
    return age


def live_peers(workspace, self_session, ttl_seconds, tree=None):
    """Return [(seat, session, age_seconds)] for every OTHER seat holding a fresh lease.

    ttl_seconds is REQUIRED. Passing None raises — see the module docstring.

    `tree` scopes the census to one WORKING TREE. Omitted (the default), every fresh peer
    is returned and the behaviour is byte-for-byte what it was before
    CUSTODY-LEASE-TREE — the two shipping callers (git_guard.py, escalation_liveness.py)
    pass three positional arguments and are untouched by this change.

    Given a tree, a peer is counted when its lease records THAT tree, or when its lease
    records NO tree at all. The second half is deliberate and is the whole safety
    property: an unrecorded tree is unknown, not absent, and dropping it would remove a
    live peer from the census on a formatting detail. Counting can only cost a false
    refusal; dropping costs a destroyed tree. [[honest-failure-outcomes]]
    """
    if ttl_seconds is None:
        raise CustodyProbeError(
            "ttl_seconds is REQUIRED and unmeasured (design O-1). Refusing to guess: too "
            "short green-lights a discard against a live peer, too long blocks an empty "
            "fleet. Measure seat write-cadence, then pass the number explicitly.")
    if not isinstance(ttl_seconds, (int, float)) or ttl_seconds <= 0:
        raise CustodyProbeError("ttl_seconds must be a positive number, got %r" % (ttl_seconds,))
    d = _lease_dir(workspace)
    now = time.time()
    out = []
    try:
        names = os.listdir(d)
    except OSError as e:
        raise CustodyProbeError("cannot list %s: %s" % (d, e))
    for name in sorted(names):
        m = LEASE_RE.match(name)
        if not m:
            continue
        seat, session = m.group(1), m.group(2)
        if session == self_session:
            continue
        age = _age_of(d / name, now)
        if age is None:
            continue
        if age > ttl_seconds:
            continue
        if tree is not None:
            peer_tree = _tree_of(d / name)
            if peer_tree is not None and not _same_tree(peer_tree, tree):
                continue
        out.append((seat, session, age))
    return out


def self_lease_fresh(workspace, self_session, ttl_seconds):
    """True iff THIS session holds a lease within TTL — i.e. the emitter is
    demonstrably RUNNING.

    ⛔ WHY THIS EXISTS (owner E1245 §3, builder-built per their hand-off).
    `live_peers` returns [] for two states that are not the same fact:

        (1) the emitter is running and there genuinely are no peers
        (2) the emitter is NOT RUNNING, so nobody writes leases at all

    `git_guard` reads [] as EXIT_CLEAR and lets a destructive verb through. So
    under (2) the guard is disarmed while looking green. That became reachable
    the moment the emitter gained a `|| exit 0` launch wrapper (cure (a)): a
    launch failure used to BLOCK loudly, and now it is silent. ⛔ And the
    operation class that makes the emitter file vanish — checkout / reset /
    rename — is the SAME class git_guard exists to gate, so one seat rewinding
    the tree disarms the guard for every seat.

    The separating information was already inside `live_peers` and discarded at
    the `session == self_session` skip: if the emitter is alive, it fired on the
    very tool call that is running this check, so SELF's lease is fresh. Absence
    of one's OWN lease is therefore evidence about the MECHANISM, not about
    peers [[unknown-is-not-unparseable]].

    ⚠ Deliberately a separate predicate rather than a change to `live_peers`'
    return type: that function is consumed by the guard and by two suites, and
    widening its contract to carry a second fact would make every caller
    re-interpret a value they already read correctly.
    """
    if ttl_seconds is None or not isinstance(ttl_seconds, (int, float)) or ttl_seconds <= 0:
        raise CustodyProbeError(
            "ttl_seconds must be a positive number, got %r" % (ttl_seconds,))
    d = _lease_dir(workspace)
    now = time.time()
    try:
        names = os.listdir(d)
    except OSError as e:
        raise CustodyProbeError("cannot list %s: %s" % (d, e))
    for name in sorted(names):
        m = LEASE_RE.match(name)
        if not m or m.group(2) != self_session:
            continue
        age = _age_of(d / name, now)
        if age is not None and age <= ttl_seconds:
            return True
    return False
