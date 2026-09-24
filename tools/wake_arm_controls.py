#!/usr/bin/env python3
"""Controls for U1 (tools/wake_arm.py).  T0 / DESIGN-builder-v4.md §3.3.

ACCEPTANCE BAR (fixed in IMPL-PLAN-builder-v1.md §4 BEFORE any code existed,
because v3's conviction was shipping a rule with zero graded rows):

  (a) controls,
  (b) at least one MANDATORY RED MUTATION **whose landing is asserted**,
  (c) an explicit statement of what is NOT covered.

(b) is spelled that way because of a defect this seat shipped on 2026-08-05:
a negative control reported a clean 36/36 while the mutation had never landed
-- a Bash heredoc ate the backslashes, the file was never modified, and an
unmutated file passing is not evidence about a control.  So every mutation here
asserts the substitution was unique, applies it, asserts the bytes CHANGED, and
asserts the file was restored afterwards.  A mutation that cannot be shown to
have landed leaves the suite UNGRADED, never green.

NOT COVERED, stated so no report reads this as more than it is:
  * Nothing here grades DELIVERY.  U1 mints and verifies arms; the causal join
    (U4) is what binds an arm to a real hop.  A green suite means the minter is
    sound, not that anything was delivered.
  * Nothing here covers the determined adversary (v4 §1, §2 rows 1 and 7).  The
    chain audit detects edits by a broken chain; it does not prevent them, and
    a determined seat recomputes every link.  That is UNCOVERED and stays so.
  * The CSPRNG itself is not tested -- `secrets` is trusted.  The uniqueness
    check catches a duplicated store or a catastrophically broken source, not a
    subtly biased one.
"""

import json
import os
import shutil
import sys
import tempfile
import time
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wake_arm as W  # noqa: E402

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, ok, detail=""):
    results.append((name, PASS if ok else FAIL, detail))
    print("  [%s] %s%s" % (PASS if ok else FAIL, name,
                           (" -- " + detail) if detail else ""))
    return ok


def tmpstore():
    d = tempfile.mkdtemp(prefix="wakearm_")
    return os.path.join(d, "arms.jsonl"), d


# --------------------------------------------------------------------------
# 1. Entropy and shape -- the requirement §3.3 asks for BY NAME.
# --------------------------------------------------------------------------
def c1_entropy():
    print("\n1. token entropy + record shape")
    s, d = tmpstore()
    try:
        rc, rec, msg = W.mint(s, "builder/chan")
        check("1a mint returns RC_OK", rc == W.RC_OK, msg)
        check("1b token is 128 bits of hex", len(rec["token"]) == 32
              and rec["token_bits"] == 128, rec["token"][:12] + "...")
        int(rec["token"], 16)  # raises if not hex
        check("1c record declares its version", rec["v"] == W.ARM_RECORD_V1)
        check("1d expiry is explicit and in the future",
              W._parse_iso(rec["expires_at"]) > W._parse_iso(rec["minted_at"]))
        # Distinctness across many mints -- a constant generator passes 1b.
        toks = set()
        for i in range(200):
            _, r, _ = W.mint(s, "scope%d" % i)
            toks.add(r["token"])
        check("1e 200 mints produced 200 distinct tokens", len(toks) == 200,
              "%d distinct" % len(toks))
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------
# 2. One open arm at a time, and atomic supersession.
# --------------------------------------------------------------------------
def c2_one_open():
    print("\n2. one-open-arm invariant + atomic supersession")
    s, d = tmpstore()
    try:
        rc1, r1, _ = W.mint(s, "builder/chan")
        rc2, r2, msg2 = W.mint(s, "builder/chan")
        check("2a a second mint on an open scope REFUSES", rc2 == W.RC_REFUSED, msg2)
        check("2b the refusal did not append", len(W.read_records(s)) == 1)
        rc3, r3, _ = W.mint(s, "builder/chan", supersede=True)
        check("2c --supersede mints", rc3 == W.RC_OK)
        check("2d the new record NAMES the one it replaced",
              r3["supersedes"] == r1["arm_id"])
        check("2e exactly ONE arm is open for the scope afterwards",
              W.count_open(s) == 1)
        check("2f the superseded arm is no longer the open one",
              W.open_arm(s, "builder/chan")["arm_id"] == r3["arm_id"])
        # Atomicity: supersession is ONE append, so no intermediate file state
        # can show zero or two open arms.
        check("2g supersession cost exactly one append",
              len(W.read_records(s)) == 2)
        # A different scope is unaffected -- the invariant is per-scope.
        W.mint(s, "owner/chan")
        check("2h a different scope may hold its own open arm",
              W.count_open(s) == 2)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------
# 3. Replay / expiry / mismatch rejection.
# --------------------------------------------------------------------------
def c3_reject():
    print("\n3. verify() rejects replay, expiry and mismatch")
    s, d = tmpstore()
    try:
        _, r1, _ = W.mint(s, "builder/chan")
        ok, why, _rc = W.check_arm_token(s, r1["arm_id"], r1["token"])
        check("3a a live arm with the right token verifies", ok, why)
        ok, why, _rc = W.check_arm_token(s, r1["arm_id"], "0" * 32)
        check("3b a wrong token is rejected", not ok, why)
        ok, why, _rc = W.check_arm_token(s, "deadbeefdeadbeef", r1["token"])
        check("3c an unknown arm id is rejected", not ok, why)

        _, r2, _ = W.mint(s, "builder/chan", supersede=True)
        ok, why, _rc = W.check_arm_token(s, r1["arm_id"], r1["token"])
        check("3d REPLAY of a superseded arm is rejected", not ok, why)
        check("3d' and the rejection SAYS superseded, not merely 'invalid'",
              "supersede" in why.lower(), why)

        future = W._now() + timedelta(seconds=W.DEFAULT_TTL_S + 60)
        ok, why, _rc = W.check_arm_token(s, r2["arm_id"], r2["token"], now=future)
        check("3e an EXPIRED arm is rejected", not ok, why)
        check("3e' and the rejection SAYS expired -- a generic failure would "
              "not discriminate", "expired" in why.lower(), why)
        check("3f an expired arm is not 'open'",
              W.open_arm(s, "builder/chan", now=future) is None)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------
# 4. Store integrity -- and the parser refuses rather than skips.
# --------------------------------------------------------------------------
def c4_integrity():
    print("\n4. chain audit + refusing parser")
    s, d = tmpstore()
    try:
        for i in range(4):
            W.mint(s, "scope%d" % i)
        ok, findings = W.audit(s)
        check("4a an untouched store audits OK", ok, "; ".join(findings))

        # In-place EDIT of an early record.
        raw = open(s, "rb").read().split(b"\n")
        rec = json.loads(raw[1])
        rec["scope"] = "TAMPERED"
        raw[1] = json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()
        open(s, "wb").write(b"\n".join(raw))
        ok, findings = W.audit(s)
        check("4b an in-place edit BREAKS the chain", not ok,
              findings[0][:90] if findings else "")
        check("4c the finding localises to the first broken link",
              bool(findings) and "record 3" in findings[0],
              findings[0][:60] if findings else "")

        # TRUNCATION.
        s2, d2 = tmpstore()
        try:
            for i in range(4):
                W.mint(s2, "scope%d" % i)
            # The independent copy taken BEFORE the damage -- this is the
            # object v4 §3.6 names as the remedy, so the control needs it to
            # exist rather than to be described.
            shutil.copyfile(s2, s2 + ".bak")
            lines = open(s2, "rb").read().split(b"\n")
            open(s2, "wb").write(b"\n".join(lines[:2]) + b"\n")
            ok2, _ = W.audit(s2)
            # §3(a) ORCH-1920: INVERTED from a disclosure into a BOUNDARY
            # ASSERTION. This row does not describe a non-capability -- it
            # ENFORCES the stated limit. The chain attests order and content
            # but NOT length, so a truncated prefix is self-consistent. The day
            # audit() gains length attestation this row goes RED, which is
            # correct: the claim surface must then be re-graded rather than
            # silently improved. [[test-package-must-assert-its-own-boundary]]
            check("4d BOUNDARY: audit() still does NOT detect truncation "
                  "(a prefix is self-consistent; RED here means the limit "
                  "moved and the claim surface needs re-grading)", ok2)
            # ⚠ AND THE NAMED REMEDY IS NOW EXERCISED, NOT JUST CITED. v4 §3.6
            # says truncation "needs an independent copy comparison". Asserting
            # the hole while never testing the thing that closes it leaves a
            # documented hazard standing in for a defended one.
            # [[announced-action-must-be-taken]]
            full = open(s2 + ".bak", "rb").read() if os.path.exists(s2 + ".bak") else None
            check("4d' the REMEDY works: an independent copy comparison "
                  "DOES detect what the chain cannot",
                  full is not None and full != open(s2, "rb").read(),
                  "copy=%s bytes vs live=%s bytes"
                  % (len(full) if full else "n/a",
                     os.path.getsize(s2)))
        finally:
            shutil.rmtree(d2, ignore_errors=True)

        # Unknown version must REFUSE, not be skipped.
        s3, d3 = tmpstore()
        try:
            W.mint(s3, "a")
            with open(s3, "a", encoding="utf-8") as f:
                f.write(json.dumps({"v": "WAKE-ARM/2", "arm_id": "x"}) + "\n")
            try:
                W.read_records(s3)
                check("4e an unknown record version REFUSES", False,
                      "it parsed instead")
            except ValueError as e:
                check("4e an unknown record version REFUSES", True, str(e)[:70])
        finally:
            shutil.rmtree(d3, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------
# 5. MANDATORY RED MUTATIONS -- each asserts its own landing.
# --------------------------------------------------------------------------
MUTATIONS = [
    # (name, needle, replacement, which control must go RED, why it matters)
    ("M1 shrink the token to 32 bits",
     "TOKEN_BYTES = 16", "TOKEN_BYTES = 4", "1b",
     "a weakened entropy floor must not pass the stated-requirement control"),
    ("M2 drop the supersedes link",
     '"supersedes": live["arm_id"] if (live is not None and supersede) else None,',
     '"supersedes": None,', "2d",
     "without the link, replay of a superseded arm would be accepted"),
    ("M3 stop honouring expiry in check_arm_token()",
     '    if _parse_iso(rec["expires_at"]) <= now:\n        return False, "arm %s expired at %s" % (arm_id, rec["expires_at"]), RC_REFUSED',
     '    if False:\n        return False, "arm %s expired at %s" % (arm_id, rec["expires_at"]), RC_REFUSED',
     "3e", "an arm that never expires is an arm that replays forever"),
    # --- ORCH-1920 mechanisms. Each mutation is SINGLE-POINT and aimed at the
    # mechanism the finding names, not at an outcome that several paths reach.
    ("M5 drop O_EXCL -- the lock stops excluding",
     "os.O_CREAT | os.O_EXCL | os.O_WRONLY", "os.O_CREAT | os.O_WRONLY", "F1a",
     "a lock that both minters can take is not a lock; F1 returns in full"),
    ("M6 let audit() skip the record grammar",
     "            _check_record(rec, store, i)", "            pass", "F3a",
     "the verifier would again accept a store the emitter refuses"),
    ("M7 let read_records() skip the shape check",
     "            _check_record(rec, store, n)", "            pass", "F4a",
     "a missing field returns to crashing mid-derivation instead of refusing"),
    ("M4 make the one-open-arm check vacuous",
     "if live is not None and not supersede:",
     "if False:", "2a",
     "the invariant is enforced by that refusal or it is not enforced"),
]


def c5_mutations(src):
    """Mutations run against a FROZEN COPY, never the live file.

    Earlier on 2026-08-05 this seat edited a live shared instrument in place;
    between two edits the shared tree carried a tool that appended correctly and
    exited 1, and a peer hit it.  Mutating `tools/wake_arm.py` in place here
    would be the same defect wearing a test's clothes: for the duration of the
    run, any peer importing the tool gets a deliberately broken one.

    So the suite copies the source into a temp dir, puts that dir FIRST on
    sys.path, and mutates only the copy.  The live file is never opened for
    writing.  [[live-instruments-must-be-frozen-or-swapped]]"""
    print("\n5. mandatory red mutations (each asserts it LANDED)")
    original = open(src, "r", encoding="utf-8").read()
    live_before = original
    mut_dir = tempfile.mkdtemp(prefix="wakearm_mut_")
    copy_src = os.path.join(mut_dir, "wake_arm.py")
    shutil.copyfile(src, copy_src)
    sys.path.insert(0, mut_dir)
    all_ok = True
    for name, needle, repl, expect_red, why in MUTATIONS:
        n = original.count(needle)
        if n != 1:
            check("%s: needle is unique" % name, False,
                  "found %d occurrences -- refusing to mutate blind" % n)
            all_ok = False
            continue
        mutated = original.replace(needle, repl)
        if mutated == original:
            check("%s: mutation LANDED" % name, False, "bytes unchanged")
            all_ok = False
            continue
        open(copy_src, "w", encoding="utf-8").write(mutated)
        try:
            on_disk = open(copy_src, "r", encoding="utf-8").read()
            landed = (on_disk == mutated) and (on_disk != original)
            if not check("%s: mutation LANDED on disk" % name, landed):
                all_ok = False
                continue
            # Re-import the mutated module and re-run the whole suite.
            for m in list(sys.modules):
                if m == "wake_arm":
                    del sys.modules[m]
            import importlib
            global W
            W = importlib.import_module("wake_arm")
            before = len(results)
            try:
                # ⛔ EVERY section, or a mutation is graded against a suite that
                # never runs the control naming it. Adding c6 to run() but not
                # here made M5/M6/M7 land correctly and then report "reds: none"
                # -- the mutation was real, the grader was blind. A re-run set
                # that drifts from the suite is a silent coverage hole.
                # [[mutation-test-discipline]] [[vacuity-cannot-attribute]]
                c1_entropy(); c2_one_open(); c3_reject(); c4_integrity()
                c6_orch1920()
            except Exception as e:
                results.append(("%s crashed the suite" % name, FAIL, str(e)[:80]))
            reds = [r for r in results[before:] if r[1] == FAIL]
            hit = any(r[0].startswith(expect_red) for r in reds)
            del results[before:]
            if not check("%s: turns %s RED (%s)" % (name, expect_red, why), hit,
                         "reds: " + ", ".join(r[0] for r in reds) or "none"):
                all_ok = False
        finally:
            open(copy_src, "w", encoding="utf-8").write(original)
            restored = open(copy_src, "r", encoding="utf-8").read() == original
            if not check("%s: mutated COPY restored byte-exact" % name, restored):
                all_ok = False
            for m in list(sys.modules):
                if m == "wake_arm":
                    del sys.modules[m]
            import importlib
            W = importlib.import_module("wake_arm")

    # The point of the whole arrangement, asserted rather than assumed: the
    # LIVE file must be byte-identical to what it was before the suite ran.
    # If a future edit re-points a mutation at `src`, this goes red.
    sys.path.remove(mut_dir)
    shutil.rmtree(mut_dir, ignore_errors=True)
    live_after = open(src, "r", encoding="utf-8").read()
    if not check("5z the LIVE instrument was never written",
                 live_after == live_before,
                 "mutations ran against a temp copy, not the shared tool"):
        all_ok = False
    for m in list(sys.modules):
        if m == "wake_arm":
            del sys.modules[m]
    import importlib
    W = importlib.import_module("wake_arm")
    return all_ok


def c6_orch1920():
    """The four ORCH-1920 findings, each with a control that FAILS without the
    fix.  Grouped so a reviewer can see the finding-to-control mapping without
    reading the whole suite."""
    print("\n6. ORCH-1920 findings F1-F4")

    # ---- F1: inter-process exclusion around read->append.
    s, d = tmpstore()
    try:
        lk = W._arm_lock(s)
        lk.__enter__()
        # A second minter must NOT proceed. It must refuse LOUDLY, and it must
        # refuse with CANNOT_RUN -- "I did not evaluate" -- never REFUSED,
        # which would assert a verdict about the invariant it never reached.
        t0 = time.time()
        rc, rec, msg = W.mint(s, "builder/chan")
        waited = time.time() - t0
        check("F1a a second minter cannot enter the critical section",
              rc == W.RC_CANNOT_RUN and rec is None, "rc=%s %s" % (rc, msg[:60]))
        check("F1b it BLOCKS first and only then refuses (not an instant fail)",
              waited >= W.LOCK_TIMEOUT_S * 0.8, "waited %.2fs" % waited)
        check("F1c the refusal names the holder and the manual remedy",
              "pid=" in msg and "stale" in msg.lower(), msg[:80])
        # THE DISCRIMINATOR: the lock must not be a permanent wedge. Once
        # released, minting proceeds -- otherwise F1a would pass for a module
        # that simply never mints. [[control-passing-for-the-wrong-reason]]
        lk.__exit__(None, None, None)
        rc2, rec2, _ = W.mint(s, "builder/chan")
        check("F1d discriminator: after release the SAME mint succeeds",
              rc2 == W.RC_OK and rec2 is not None, "rc=%s" % rc2)
        check("F1e the lock file does not survive a completed mint",
              not os.path.exists(s + ".lock"))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ---- F2: one snapshot, not two reads.
    s, d = tmpstore()
    try:
        W.mint(s, "a")
        calls = []
        real = W.read_records
        W.read_records = lambda st, _r=real: (calls.append(st), _r(st))[1]
        try:
            W.open_arm(s, "a")
        finally:
            W.read_records = real
        check("F2a open_arm() reads the store exactly ONCE (torn view closed)",
              len(calls) == 1, "read_records called %d time(s)" % len(calls))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ---- F3: one grammar, and two distinct failure codes.
    s, d = tmpstore()
    try:
        W.mint(s, "a")
        # ⛔ THE FIXTURE MUST BE CHAIN-VALID, OR THIS CONTROL PASSES FOR THE
        #    WRONG REASON. A naively appended bogus record ALSO breaks the
        #    prev_sha256 chain, so audit() would go red via the chain check and
        #    the grammar check would never be exercised -- M6 proved exactly
        #    that (mutation landed, "reds: none"). So the record below carries a
        #    CORRECT prev_sha256: the chain leg passes, and ONLY the grammar leg
        #    can catch it. [[control-passing-for-the-wrong-reason]]
        #    [[control-design-discipline]]
        bogus = {"v": "WAKE-ARM/2", "arm_id": "x",
                 "prev_sha256": W._file_sha256(s)}
        with open(s, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(bogus, sort_keys=True,
                               separators=(",", ":")) + "\n")
        ok, findings = W.audit(s)
        check("F3a audit() REFUSES a record read_records() would refuse "
              "(verifier grammar == emitter grammar)",
              not ok, (findings[0][:70] if findings else "audited OK"))
        check("F3a' and it is the GRAMMAR that caught it, not the chain "
              "(the fixture's chain link is valid)",
              bool(findings) and "version" in findings[0].lower(),
              (findings[0][:70] if findings else "no findings"))
        okv, why, rc = W.check_arm_token(s, "whatever", "whatever")
        check("F3b a CORRUPT store returns CANNOT_RUN, not REFUSED "
              "(no verdict was reached, so none is reported)",
              (not okv) and rc == W.RC_CANNOT_RUN, "rc=%s %s" % (rc, why[:50]))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    # F3b discriminator: a genuinely rejected arm must still be REFUSED, else
    # F3b would pass for a module that returned CANNOT_RUN for everything.
    s, d = tmpstore()
    try:
        _, r1, _ = W.mint(s, "a")
        okv, why, rc = W.check_arm_token(s, r1["arm_id"], "0" * 32)
        check("F3c discriminator: an EVALUATED rejection is still REFUSED",
              (not okv) and rc == W.RC_REFUSED, "rc=%s" % rc)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ---- F4: shape refused by name, not by KeyError.
    s, d = tmpstore()
    try:
        W.mint(s, "a")
        with open(s, "a", encoding="utf-8") as f:
            f.write(json.dumps({"v": W.ARM_RECORD_V1, "arm_id": "y"}) + "\n")
        try:
            W.read_records(s)
            check("F4a a version-correct record with a missing field REFUSES",
                  False, "it parsed")
        except KeyError as e:
            check("F4a a version-correct record with a missing field REFUSES",
                  False, "crashed with KeyError %s instead of refusing" % e)
        except ValueError as e:
            check("F4a a version-correct record with a missing field REFUSES",
                  True, str(e)[:70])
            check("F4b and the refusal NAMES the missing field(s)",
                  "scope" in str(e) and "missing" in str(e).lower(),
                  str(e)[:70])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run():
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wake_arm.py")
    print("U1 wake_arm controls -- %s" % src)
    c1_entropy()
    c2_one_open()
    c3_reject()
    c4_integrity()
    c6_orch1920()
    c5_mutations(src)
    npass = sum(1 for _, s, _ in results if s == PASS)
    total = len(results)
    print("\n%d/%d" % (npass, total))
    for name, st, detail in results:
        if st == FAIL:
            print("  FAILED: %s -- %s" % (name, detail))
    return 0 if npass == total else 1


if __name__ == "__main__":
    sys.exit(run())
