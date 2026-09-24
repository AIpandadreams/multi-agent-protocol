#!/usr/bin/env python3
"""U1 — the wake-delivery ARM MINTER.  (T0, DESIGN-builder-v4.md §3.3)

WHY THIS FILE EXISTS AT ALL
---------------------------
v4 §10 item 5 carried an UNCHECKED item worded as *"T's entropy -- the running
watcher's minting routine has not been read by any voice"*.  It was measured on
2026-08-05: there are ZERO entropy sources anywhere in `tools/heartbeat/`, the
watcher mints nothing, and a live wake entry carries a timestamp, a seat, a
watch and a reason -- no token, no arm id, no correlation key.

  => There was no incumbent minting routine to read.  The item presupposed one.
     That is the same shape as §8's own finding about the escalation id: a
     missing OBJECT, not a missing definition.  So §3.3's "T gets a stated
     entropy/uniqueness requirement" is a BUILD ORDER, and this is the build.

WHAT THIS DOES **NOT** DO -- read before citing any green from it
----------------------------------------------------------------
Per v4 §1 the whole unit is graded against ONE adversary: a **broken** delivery
chain.  It is tamper-EVIDENT against that, and tamper-TRANSPARENT against a
determined seat.

  * NOTHING here is unforgeable, tamper-proof, or cryptographically guaranteed.
    Every seat on this machine runs as the same OS principal with FullControl
    over this store; a determined seat can author any record in it.  §2 rows 1
    and 7 have NO mechanism and close under §1 only.
  * A green from this module is evidence the chain is ALIVE.  It is never
    evidence that any seat is HONEST.
  * `check_arm_token()` answers "is this arm open and does the token match".  It does NOT
    establish delivery -- that is the causal join (U4, §3.3), which binds the
    watcher pid + process-start-time, the target session, and the registration.
    An arm that verifies here has proved only that it was minted here.

APPEND-ONLY -- the honest form (v4 §3.6)
----------------------------------------
v3 cited "(§7 identity rules)" for append-only and §7 contained no such rule;
that dangling reference was withdrawn.  So, named rather than claimed:

  * PATH      : the store path is explicit (--store), never implicit.
  * CUSTODIAN : this module is the only writer, and it only ever APPENDS one
                complete record per call.  There is no update-in-place path.
  * DETECTION : a rewrite is *detectable*, not prevented -- each record carries
                `prev_sha256`, the digest of the whole file BEFORE its own bytes
                were appended, so an independent copy comparison localises any
                edit to the first record whose chain link breaks (`audit()`).
    (!) This is DETECTION under the broken-seat adversary.  A determined seat
        can rewrite the file and recompute every link.  Stated, not hidden.

STATE IS DERIVED, NEVER STORED
------------------------------
Supersession must be ATOMIC (§3.3).  Two appends -- "close the old" then "open
the new" -- are not atomic: a crash between them leaves zero open arms or two.
So this module NEVER writes a state field.  It writes one record per mint, the
new record names what it `supersedes`, and every state question is answered by
replaying the log.  ONE append is the atomic act.
"""

import argparse
import hashlib
import json
import os
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone

# --- the stated entropy requirement (v4 §3.3 asks for it BY NAME) ------------
# 16 bytes = 128 bits from the OS CSPRNG.  Stated here so the number is a
# reviewable constant and not an artifact of whichever call site was written
# first.  A token is the thing an attacker would have to GUESS to forge a
# correlation under the broken-seat adversary; 128 bits is the floor.
TOKEN_BYTES = 16
TOKEN_BITS = TOKEN_BYTES * 8
ARM_ID_BYTES = 8

DEFAULT_TTL_S = 900  # explicit expiry (§3.3); no arm is open forever.

RC_OK, RC_REFUSED, RC_CANNOT_RUN = 0, 2, 3

# The declared record interface.  Consumers MUST match this literal and MUST
# refuse an unknown version rather than guess.  Changing the shape means minting
# V2, not editing this.
ARM_RECORD_V1 = "WAKE-ARM/1"

# F4 (ORCH-1920): record SHAPE is part of the declared interface, not a thing to
# discover by KeyError halfway through a derivation.  A version-correct record
# missing `scope` used to crash mid-replay; now it refuses BY NAME, at the read.
REQUIRED_FIELDS = ("v", "arm_id", "scope", "token", "minted_at", "expires_at",
                   "prev_sha256")

# --- F1 (ORCH-1920): the one-open-arm invariant needs inter-process exclusion --
# DISPOSITION: TAKE THE LOCK.  The alternative offered was to document
# dual-mint-corrupts-chain as a DETECTED state with audit() as the detector.
# Refused, and the reason is not the race:
#   a legitimate concurrent mint and a TAMPERED store produce the SAME reading
#   (audit -> BROKEN).  Documenting that makes the module's only detection
#   mechanism ambiguous exactly where it is load-bearing, and teaches a reader to
#   discount BROKEN as "probably just the race".  A detector that cries wolf by
#   design is worse than the fault it reports. [[lookup-failure-needs-own-outcome]]
# The check-then-act window is real: mint() reads the store to decide whether an
# arm is open, then appends.  Two minters both read live=None and both append.
LOCK_TIMEOUT_S = 5.0      # bounded wait; a mint is milliseconds of work
LOCK_POLL_S = 0.05
LOCK_STALE_S = 30.0       # older than this and we REFUSE, naming the remedy


class StoreLocked(Exception):
    """Raised when the store lock cannot be taken.  Deliberately NOT caught into
    a silent retry: a lock we cannot take is a fact about the system, and the
    honest outcome is RC_CANNOT_RUN with the holder named."""


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _file_sha256(path):
    """Digest of the file as it stands.  Missing file hashes as empty --
    the genesis link, so the first record's chain check is well defined."""
    h = hashlib.sha256()
    if os.path.exists(path):
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    return h.hexdigest()


class _arm_lock(object):
    """Exclusive lock around the read->append critical section (F1).

    `O_CREAT|O_EXCL` is atomic on both POSIX and Windows, so the winner is
    decided by the OS, not by our own check-then-act -- using a check-then-act
    lock to fix a check-then-act bug would be theatre.

    ⛔ A STALE LOCK IS NEVER SILENTLY STOLEN.  Auto-stealing after a timeout
    reintroduces the exact race this exists to close: two minters can both judge
    the lock stale and both steal it.  We REFUSE and name the holder and the
    remedy.  A wedged lock is a loud operator problem, not a silent corruption.
    [[gate-must-admit-the-honest-answer]]"""

    def __init__(self, store, timeout=LOCK_TIMEOUT_S):
        self.path = store + ".lock"
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        d = os.path.dirname(self.path)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        deadline = time.time() + self.timeout
        while True:
            try:
                self.fd = os.open(self.path,
                                  os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, ("pid=%d at=%s\n"
                                   % (os.getpid(), _iso(_now()))).encode())
                return self
            except FileExistsError:
                pass
            if time.time() >= deadline:
                raise StoreLocked(
                    "could not take %s within %.1fs (holder: %s). If no minter "
                    "is running the lock is stale -- inspect it and remove it "
                    "by hand. It is NOT auto-stolen: two minters could both "
                    "judge it stale and both steal it, which is the race this "
                    "lock exists to close."
                    % (self.path, self.timeout, self._holder()))
            time.sleep(LOCK_POLL_S)

    def _holder(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                txt = f.read().strip()
            age = time.time() - os.path.getmtime(self.path)
            return "%s, age %.1fs%s" % (
                txt, age, " -- STALE" if age > LOCK_STALE_S else "")
        except OSError:
            return "unreadable"

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        try:
            os.unlink(self.path)
        except OSError:
            pass
        return False


def read_records(store):
    """Every record, in file order.  A malformed line RAISES -- it is never
    skipped.  A store we cannot fully parse is a store we cannot reason about,
    and silently dropping a line is how a superseding record goes missing and
    a stale arm reads OPEN."""
    out = []
    if not os.path.exists(store):
        return out
    with open(store, "r", encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError as e:
                raise ValueError("%s:%d is not valid JSON (%s)" % (store, n, e))
            _check_record(rec, store, n)
            out.append(rec)
    return out


def _check_record(rec, store, n):
    """Version AND shape, refused by name (F4).  One grammar, used by every
    reader in this module -- read_records and audit both call it, so the
    verifier can never accept what the emitter would refuse.
    [[emitter-and-verifier-are-one-grammar]]"""
    if not isinstance(rec, dict):
        raise ValueError("%s:%d is not a JSON object" % (store, n))
    if rec.get("v") != ARM_RECORD_V1:
        raise ValueError(
            "%s:%d has unknown record version %r -- refusing to guess "
            "its shape" % (store, n, rec.get("v")))
    missing = [k for k in REQUIRED_FIELDS if k not in rec]
    if missing:
        raise ValueError(
            "%s:%d declares %s but is missing required field(s): %s -- "
            "refusing rather than crashing mid-derivation"
            % (store, n, ARM_RECORD_V1, ", ".join(missing)))


def _superseded_ids(records):
    return {r["supersedes"] for r in records if r.get("supersedes")}


def open_arm(store, scope, now=None):
    """The ONE arm open for `scope`, or None.  Reads the store ONCE (F2).

    Derived by replay, never read from a state field.  An arm is open iff it is
    the newest record for the scope, nothing supersedes it, and it has not
    expired.  Expiry is evaluated at CALL time, so an arm that aged out while
    nobody looked is not open when someone finally does."""
    return _open_arm_from(read_records(store), scope, now=now)


def _open_arm_from(records, scope, now=None):
    """The derivation, over an ALREADY-READ record list.

    F2 (ORCH-1920): the previous form called read_records() TWICE -- once for the
    supersession set and once for the candidates -- so a write landing between
    the two reads produced a TORN view: a record could be counted as a candidate
    while its superseding record was invisible, reading a closed arm as open.
    Both derivations now come from ONE snapshot.  Callers that already hold the
    records pass them straight in, which also removes the read mint() was doing
    twice over. [[live-instruments-must-be-frozen-or-swapped]]"""
    now = now or _now()
    superseded = _superseded_ids(records)
    candidates = [r for r in records if r["scope"] == scope]
    for rec in reversed(candidates):
        if rec["arm_id"] in superseded:
            return None  # the newest arm for this scope was closed out
        if _parse_iso(rec["expires_at"]) <= now:
            return None
        return rec
    return None


def count_open(store, now=None):
    """How many scopes have an open arm -- the invariant §3.3 calls
    'one open arm at a time' is per-scope, so this is a census, not a bound."""
    records = read_records(store)          # one read, one snapshot (F2)
    scopes = {r["scope"] for r in records}
    return sum(1 for s in scopes
               if _open_arm_from(records, s, now=now) is not None)


def mint(store, scope, ttl_s=DEFAULT_TTL_S, supersede=False, now=None,
         extra=None):
    """Mint one arm for `scope`.  Returns (rc, record_or_None, message).

    REFUSES when an arm is already open for the scope unless `supersede` is
    set.  That refusal IS the one-open-arm invariant -- an invariant enforced
    only by convention is not enforced.

    Supersession is ONE append.  The new record names the old in `supersedes`,
    and `open_arm` honours that on replay, so there is no window in which zero
    or two arms are open."""
    now = now or _now()
    # ⛔ THE CRITICAL SECTION IS read -> decide -> append, AS ONE (F1). Taking the
    # lock only around the append would leave the invariant exactly as broken:
    # the decision "is an arm already open" is what the other minter invalidates.
    try:
        lock = _arm_lock(store)
        lock.__enter__()
    except StoreLocked as e:
        return RC_CANNOT_RUN, None, str(e)
    try:
        return _mint_locked(store, scope, ttl_s, supersede, now, extra)
    finally:
        lock.__exit__(None, None, None)


def _mint_locked(store, scope, ttl_s, supersede, now, extra):
    try:
        records = read_records(store)
    except ValueError as e:
        return RC_CANNOT_RUN, None, "store unreadable: %s" % e

    # Same snapshot the invariant was decided on (F2) -- not a re-read.
    live = _open_arm_from(records, scope, now=now)
    if live is not None and not supersede:
        return (RC_REFUSED, None,
                "an arm is already open for scope %r (arm_id=%s, expires %s); "
                "pass --supersede to replace it"
                % (scope, live["arm_id"], live["expires_at"]))

    token = secrets.token_hex(TOKEN_BYTES)
    arm_id = secrets.token_hex(ARM_ID_BYTES)

    # Uniqueness, MECHANICAL rather than assumed.  At 128 bits a collision is
    # not the live risk -- a broken CSPRNG or a copied store is, and both show
    # up here.  Cheap check, real failure mode.
    seen_tokens = {r["token"] for r in records}
    seen_ids = {r["arm_id"] for r in records}
    if token in seen_tokens or arm_id in seen_ids:
        return (RC_CANNOT_RUN, None,
                "minted a value already present in the store -- refusing. This "
                "indicates a broken entropy source or a duplicated store, and "
                "retrying would paper over it.")

    rec = {
        "v": ARM_RECORD_V1,
        "arm_id": arm_id,
        "scope": scope,
        "token": token,
        "token_bits": TOKEN_BITS,
        "minted_at": _iso(now),
        "expires_at": _iso(now + timedelta(seconds=ttl_s)),
        "supersedes": live["arm_id"] if (live is not None and supersede) else None,
        "prev_sha256": _file_sha256(store),
    }
    if extra:
        rec["extra"] = extra

    line = json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n"
    d = os.path.dirname(store)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    # Append only.  No truncate, no seek, no rewrite path in this module.
    with open(store, "a", encoding="utf-8", newline="\n") as f:
        f.write(line)
    return RC_OK, rec, "minted %s for %s" % (arm_id, scope)


def check_arm_token(store, arm_id, token, now=None):
    """(ok, reason, rc).  Rejects replay, expiry, supersession, token mismatch.

    ⛔ RENAMED FROM `verify` (ORCH-1920 §3b), while consumers were still zero.
    `verify` is what a hurried caller reads as "delivery verified", and this
    function establishes nothing of the sort.  After U4 exists, `verify` should
    name NOTHING in this module -- the only thing worthy of the word is the
    causal join.

    (!) This answers ONLY 'is this arm open here and does the token match'.
    It does NOT establish that anything was delivered -- see the module
    docstring.  A caller citing this as delivery proof is over-claiming it.

    THE THIRD RETURN VALUE EXISTS BECAUSE THE TWO FAILURES ARE NOT THE SAME (F3).
    A store we cannot parse is RC_CANNOT_RUN -- we did not evaluate the arm and
    have no opinion about it.  An arm we evaluated and rejected is RC_REFUSED.
    Collapsing both to (False, reason) made the CLI exit REFUSED for a corrupt
    store, i.e. report a confident negative verdict it never reached.
    [[lookup-failure-needs-own-outcome]] [[unknown-is-not-unparseable]]"""
    now = now or _now()
    try:
        records = read_records(store)
    except ValueError as e:
        return False, "store unreadable: %s" % e, RC_CANNOT_RUN

    rec = next((r for r in records if r["arm_id"] == arm_id), None)
    if rec is None:
        return False, "no such arm %r" % arm_id, RC_REFUSED
    # Compare the secret in constant time.  The threat model does not include a
    # timing attacker, but a variable-time compare on a secret is the kind of
    # detail that is free now and awkward to retrofit.
    if not secrets.compare_digest(str(rec["token"]), str(token)):
        return False, "token mismatch for arm %s" % arm_id, RC_REFUSED
    if rec["arm_id"] in _superseded_ids(records):
        return False, "arm %s was superseded -- replay rejected" % arm_id, RC_REFUSED
    if _parse_iso(rec["expires_at"]) <= now:
        return False, "arm %s expired at %s" % (arm_id, rec["expires_at"]), RC_REFUSED
    return True, "arm %s open and token matches" % arm_id, RC_OK


def audit(store):
    """Walk the prev_sha256 chain.  Returns (ok, findings).

    Localises an edit to the FIRST record whose link breaks.  Detection, not
    prevention (§3.6): a determined seat recomputes the chain.  Under the
    broken-seat adversary this catches truncation, reordering and in-place
    edits, which is what it is for."""
    findings = []
    if not os.path.exists(store):
        return True, ["store does not exist yet"]
    with open(store, "rb") as f:
        raw = f.read()
    lines = [l for l in raw.split(b"\n") if l.strip()]
    running = hashlib.sha256()
    for i, line in enumerate(lines, 1):
        try:
            rec = json.loads(line.decode("utf-8"))
        except ValueError as e:
            findings.append("record %d: unparseable (%s)" % (i, e))
            return False, findings
        # F3: ONE grammar.  audit() used to check only the chain, so a record
        # with an unknown version or a missing required field passed the audit
        # while read_records() refused the very same store -- the verifier
        # accepting what the emitter rejects.  A store cannot be simultaneously
        # "AUDIT OK" and unreadable. [[emitter-and-verifier-are-one-grammar]]
        try:
            _check_record(rec, store, i)
        except ValueError as e:
            findings.append("record %d: %s" % (i, e))
            return False, findings
        expect = running.hexdigest()
        if rec.get("prev_sha256") != expect:
            findings.append(
                "record %d (arm_id=%s): prev_sha256 %s does not match the "
                "digest of everything before it (%s) -- the store was edited, "
                "truncated or reordered at or before this record"
                % (i, rec.get("arm_id"), rec.get("prev_sha256"), expect))
            return False, findings
        running.update(line + b"\n")
    return True, findings


def main(argv=None):
    p = argparse.ArgumentParser(description="U1 wake-delivery arm minter")
    p.add_argument("--store", required=True)
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("mint")
    m.add_argument("--scope", required=True)
    m.add_argument("--ttl", type=int, default=DEFAULT_TTL_S)
    m.add_argument("--supersede", action="store_true")

    # Subcommand renamed with the function (ORCH-1920 §3b): `verify` must not
    # name anything here, at the API or the CLI.
    v = sub.add_parser("check-token")
    v.add_argument("--arm-id", required=True)
    v.add_argument("--token", required=True)

    s = sub.add_parser("status")
    s.add_argument("--scope", required=True)

    sub.add_parser("audit")

    a = p.parse_args(argv)
    if a.cmd == "mint":
        rc, rec, msg = mint(a.store, a.scope, ttl_s=a.ttl, supersede=a.supersede)
        if rc == RC_OK:
            print(json.dumps(rec, sort_keys=True))
        else:
            sys.stderr.write(msg + "\n")
        return rc
    if a.cmd == "check-token":
        ok, why, rc = check_arm_token(a.store, a.arm_id, a.token)
        (sys.stdout if ok else sys.stderr).write(why + "\n")
        return rc          # RC_CANNOT_RUN for a corrupt store, never REFUSED
    if a.cmd == "status":
        try:
            rec = open_arm(a.store, a.scope)
        except ValueError as e:
            sys.stderr.write("store unreadable: %s\n" % e)
            return RC_CANNOT_RUN
        print(json.dumps(rec, sort_keys=True) if rec else "no open arm")
        return RC_OK if rec else RC_REFUSED
    if a.cmd == "audit":
        ok, findings = audit(a.store)
        for f in findings:
            print(f)
        print("AUDIT %s" % ("OK" if ok else "BROKEN"))
        return RC_OK if ok else RC_REFUSED
    return RC_CANNOT_RUN


if __name__ == "__main__":
    sys.exit(main())
