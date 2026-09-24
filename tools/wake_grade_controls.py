#!/usr/bin/env python3
"""Controls for U2 (tools/wake_grade.py).  DESIGN-builder-v4 3.1.

ACCEPTANCE BAR: fixed in an acceptance-bar document in the private workspace,
committed BEFORE this file existed (2f519550b), so
the bar could not be shaped by what the code turned out to do.

  (a) controls C1-C9,
  (b) TWO mandatory red mutations whose LANDING IS ASSERTED, not assumed,
  (c) an explicit statement of what is NOT covered.

(b) is spelled that way because of a defect this seat shipped on 2026-08-05: a
negative control reported a clean 36/36 while the mutation had never landed --
a Bash heredoc ate the backslashes, the file was never modified, and an
unmutated file passing is not evidence about a control.  So each mutation here
asserts its anchor is UNIQUE, applies it, asserts the resulting source DIFFERS
by digest, asserts the mutant ACTUALLY RAN by printing its own result rows, and
prints the same fixture's verdict under both graders side by side.

  ** If any of those three cannot be shown, U2 is UNGRADED, not green. **

The mutants are built IN MEMORY from the shipped source and exec'd into throwaway
namespaces.  Nothing on disk is modified, so a crash mid-run cannot leave a
mutated grader behind -- the 2026-08-05 defect had a restore step that could
itself fail, and not needing one is better than checking one.

NOT COVERED -- restated at the code, because a limitation that lives only in a
workpaper is one refactor from being lost:
  * Nothing here grades HONESTY.  A green means the discrimination works, not
    that any seat is truthful.  Tamper-EVIDENT, never tamper-proof.
  * Nothing here is a CAUSAL claim.  The join is U4.
  * Nothing here says WHO ran the grader.  Isolation is U5.
  * Every store here is a FIXTURE built by this file.  No live transcript
    directory is read or written, and a NOT-DELIVERED from U2 bounds ONE STORE,
    not the world (v4 10 item 3: sink enumeration is unresolved).
  * The live store's real record shape is `{"type":"queue-operation",
    "operation":"enqueue"}` and ENQUEUED IS THE WEAKEST VERB IN THE CHAIN
    (v4 3.8).  C4 uses it as a NEGATIVE on purpose.  Nothing here licenses
    treating enqueue as delivery.
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import wake_grade  # noqa: E402
import wake_arm    # noqa: E402

SRC_PATH = os.path.join(HERE, "wake_grade.py")
with open(SRC_PATH, "r", encoding="utf-8") as _f:
    SHIPPED_SRC = _f.read()

SESSION = "SESSION-AAA-0000-1111"
OTHER_SESSION = "SESSION-ZZZ-9999-8888"
ARM_ID = "a1b2c3d4e5f60718"
TOKEN = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"
KINDS = {"wake-delivery"}

ARM = {
    "v": "WAKE-ARM/1",
    "arm_id": ARM_ID,
    "scope": "builder",
    "token": TOKEN,
    "token_bits": 128,
    "minted_at": "2026-08-27T07:00:00-04:00",
    "expires_at": "2026-08-27T08:00:00-04:00",
    "supersedes": None,
    "prev_sha256": None,
    "extra": {"session_id": SESSION},
}

# The full envelope text a seat could cause to be TRANSCRIBED with no write.
ENVELOPE = ("WAKE-ARM/1 arm_id=%s token=%s scope=builder session=%s"
            % (ARM_ID, TOKEN, SESSION))

REC_REAL = {"type": "wake-delivery", "operation": "surface",
            "sessionId": SESSION, "armId": ARM_ID}
REC_ECHO = {"type": "user", "sessionId": SESSION,
            "message": {"role": "user", "content":
                        "here is the file I read:\n" + ENVELOPE + "\n"}}
REC_WRONG_SESSION = {"type": "wake-delivery", "operation": "surface",
                     "sessionId": OTHER_SESSION, "armId": ARM_ID}
REC_WRONG_KIND = {"type": "queue-operation", "operation": "enqueue",
                  "sessionId": SESSION, "armId": ARM_ID}
REC_UNDECLARED = {"type": "totally-undeclared-kind", "operation": "surface",
                  "sessionId": SESSION, "armId": ARM_ID}

FAILURES = []
PASSES = [0]


def check(label, got, want, why):
    ok = (got == want)
    PASSES[0] += 1
    print("%-46s : %-15s %s" % (label, got, "[PASS]" if ok else
                                ("[*** FAIL *** expected: %s]" % want)))
    print("    %s" % why)
    if not ok:
        FAILURES.append(label)


def write_store(tmp, name, records):
    p = os.path.join(tmp, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")
    return p


def build_mutant(name, anchor, replacement):
    """Return (module_namespace, shipped_digest, mutant_digest).

    Asserts the anchor is UNIQUE and that the bytes actually changed.  A
    non-unique anchor is refused rather than replaced-everywhere: 'it applied
    somewhere' is not the same claim as 'it applied HERE'.
    """
    n = SHIPPED_SRC.count(anchor)
    if n != 1:
        raise AssertionError(
            "MUTATION %s DID NOT LAND: anchor occurs %d times, expected exactly 1"
            % (name, n))
    mutated = SHIPPED_SRC.replace(anchor, replacement)
    if mutated == SHIPPED_SRC:
        raise AssertionError("MUTATION %s DID NOT LAND: source unchanged" % name)
    d_ship = hashlib.sha256(SHIPPED_SRC.encode("utf-8")).hexdigest()[:16]
    d_mut = hashlib.sha256(mutated.encode("utf-8")).hexdigest()[:16]
    if d_ship == d_mut:
        raise AssertionError("MUTATION %s DID NOT LAND: digests equal" % name)
    ns = {"__name__": "wake_grade_mutant_" + name}
    exec(compile(mutated, "<mutant %s>" % name, "exec"), ns)
    return ns, d_ship, d_mut


def main():
    tmp = tempfile.mkdtemp(prefix="u2ctl-")
    try:
        print("=" * 70)
        print(" U2 CONTROLS - structural grader (DESIGN-builder-v4 3.1)")
        print("=" * 70)
        print("fixture dir: %s" % tmp)
        print("")

        # --- schema agreement with U1 -----------------------------------
        check("U0 arm schema agrees with U1",
              wake_grade.ARM_RECORD_V1, wake_arm.ARM_RECORD_V1,
              "U2 states the U1 version it was written against instead of "
              "importing it, so a U1 bump breaks here LOUDLY rather than "
              "grading a shape nobody checked. This arm asserts they agree today.")

        # --- C1 : the positive control ----------------------------------
        s = write_store(tmp, "c1.jsonl", [REC_REAL])
        r1 = wake_grade.grade(ARM, s, KINDS)
        check("C1 genuine top-level delivery",
              r1["outcome"], wake_grade.DELIVERED,
              "THE POSITIVE CONTROL. Without it every NOT-DELIVERED below is "
              "vacuous - a grader that answered NOT-DELIVERED unconditionally "
              "would pass C2-C8 and prove nothing. [[control-design-discipline]]")

        # --- C2 : the content echo, the arm the mutation must flip ------
        s = write_store(tmp, "c2.jsonl", [REC_ECHO])
        r2 = wake_grade.grade(ARM, s, KINDS)
        check("C2 content echo is NOT a delivery",
              r2["outcome"], wake_grade.NOT_DELIVERED,
              "v4 2 row 2 - THE ARM M-U2-1 MUST FLIP. The full envelope, "
              "token included, is present in the file as transcribed content. "
              "A `token in raw_bytes` grader calls this DELIVERED with no write "
              "having happened anywhere.")
        check("C2 token IS present in the raw bytes",
              TOKEN in open(s, encoding="utf-8").read(), True,
              "the control's PREMISE, asserted rather than assumed: if the token "
              "were absent, C2 would pass for a reason that has nothing to do "
              "with structure and the mutation could not flip it. "
              "[[control-passing-for-the-wrong-reason]]")

        # --- C3 : wrong session at top level ----------------------------
        s = write_store(tmp, "c3.jsonl", [REC_WRONG_SESSION])
        r3 = wake_grade.grade(ARM, s, KINDS)
        check("C3 right shape, WRONG sessionId",
              r3["outcome"], wake_grade.NOT_DELIVERED,
              "v4 2 row 3 - a right-shaped record in the right file is still "
              "the wrong session. This is the arm M-U2-2 must flip.")

        # --- C4 : wrong kind (and the measured weak verb) ---------------
        s = write_store(tmp, "c4.jsonl", [REC_WRONG_KIND])
        r4 = wake_grade.grade(ARM, s, KINDS)
        check("C4 right session, WRONG record kind",
              r4["outcome"], wake_grade.NOT_DELIVERED,
              "the kind half of the match is load-bearing, not decoration. The "
              "fixture is the shape actually MEASURED in the live store - "
              "queue-operation/enqueue - used as a NEGATIVE, because enqueued "
              "is not surfaced-to-the-model and not read (v4 3.8, row 9).")

        # --- C5 : empty store -------------------------------------------
        s = write_store(tmp, "c5.jsonl", [])
        r5 = wake_grade.grade(ARM, s, KINDS)
        check("C5 empty store",
              r5["outcome"], wake_grade.NOT_DELIVERED, "an empty store is a real negative")
        check("C5 ...and the count rides the answer",
              r5["records_parsed"], 0,
              "an empty answer must come from a query that RAN. A negative with "
              "no count is indistinguishable from a query that never executed. "
              "[[empty-result-needs-its-count]]")

        # --- C6 : unparseable -------------------------------------------
        p = os.path.join(tmp, "c6.jsonl")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(REC_REAL) + "\n")
            f.write("{this is not json at all\n")
        r6 = wake_grade.grade(ARM, p, KINDS)
        check("C6 unparseable store",
              r6["outcome"], wake_grade.UNPARSEABLE,
              "UNKNOWN MUST NOT COLLAPSE INTO NO. Note the fixture holds a VALID "
              "delivery record on line 1: a grader that judged what it could "
              "parse and ignored the rest would answer DELIVERED here and would "
              "be reporting a fact about a file it could not read. "
              "[[honest-failure-outcomes]] [[lookup-failure-needs-own-outcome]]")

        # --- C7 : store absent ------------------------------------------
        r7 = wake_grade.grade(ARM, os.path.join(tmp, "does-not-exist.jsonl"), KINDS)
        check("C7 store absent",
              r7["outcome"], wake_grade.STORE_ABSENT,
              "absent is not empty and is not unparseable. Three different facts "
              "about the world, only one of which is evidence about delivery.")

        # --- C8 : undeclared kind carrying the token at top level -------
        s = write_store(tmp, "c8.jsonl", [REC_UNDECLARED])
        r8 = wake_grade.grade(ARM, s, KINDS)
        check("C8 top-level bind, UNDECLARED kind",
              r8["outcome"], wake_grade.NOT_DELIVERED,
              "the enum is CLOSED: an unknown kind is not a delivery. This is the "
              "arm that stops `kinds` degenerating into 'any record that binds'.")

        # --- C9 : both, and the pass must attribute ---------------------
        s = write_store(tmp, "c9.jsonl", [REC_ECHO, REC_REAL])
        r9 = wake_grade.grade(ARM, s, KINDS)
        check("C9 echo + real record",
              r9["outcome"], wake_grade.DELIVERED, "the real record must win")
        check("C9 ...and the pass NAMES the record",
              (r9["matched"] or {}).get("line"), 2,
              "THE ARM I EXPECT TO BE ARGUED ABOUT, and it is here on purpose. "
              "Without attribution a store holding both an echo and a real "
              "record cannot tell a reader WHICH one satisfied the grader - so "
              "C1 and C2 become indistinguishable in the wild and a right answer "
              "for the wrong reason reads as a green.")

        # --- ARM-INVALID reachability -----------------------------------
        bad = dict(ARM)
        bad.pop("extra")
        s = write_store(tmp, "cinv.jsonl", [REC_REAL])
        rinv = wake_grade.grade(bad, s, KINDS)
        check("C10 arm naming no session",
              rinv["outcome"], wake_grade.ARM_INVALID,
              "the fifth outcome must be REACHABLE - an outcome no control can "
              "produce is an outcome nothing tests. Refusing here is v4 2 row "
              "3: without a session in the arm, the caller is choosing the "
              "evidence, which is equivalent to authoring it.")
        check("C11 no kinds declared",
              wake_grade.grade(ARM, s, set())["outcome"], wake_grade.ARM_INVALID,
              "refusing to invent a delivery kind. v4 3.8: v3 never defined "
              "what 'event' meant and so attested the weakest verb in the chain.")

        # ================================================================
        print("")
        print("=" * 70)
        print(" MANDATORY RED MUTATIONS - landing ASSERTED in three parts")
        print("=" * 70)

        # --- M-U2-1 : the textual grader the design forbids --------------
        anchor1 = "    for n, rec in records:\n        if rec.get(TYPE_KEY) not in kinds:\n"
        repl1 = (
            "    with open(store, 'r', encoding='utf-8') as _mf:\n"
            "        if arm['token'] in _mf.read():\n"
            "            result['outcome'] = DELIVERED\n"
            "            result['matched'] = {'line': -1, 'type': '<text-search>',\n"
            "                                 'operation': None, 'bind_key': '<raw-bytes>'}\n"
            "            result['reason'] = 'MUTANT M-U2-1: token found by TEXT SEARCH'\n"
            "            return result\n"
            + anchor1)
        m1, d_ship, d_mut = build_mutant("M-U2-1", anchor1, repl1)
        print("(1) source differs at the parse site: shipped=%s mutant=%s" % (d_ship, d_mut))

        s2 = os.path.join(tmp, "c2.jsonl")
        s1 = os.path.join(tmp, "c1.jsonl")
        m1_c2 = m1["grade"](ARM, s2, KINDS)
        m1_c1 = m1["grade"](ARM, s1, KINDS)
        print("(2) the mutant RAN - its own rows, not a claim that it ran:")
        print("      mutant C2 -> %-14s reason=%s" % (m1_c2["outcome"], m1_c2["reason"]))
        print("      mutant C1 -> %-14s" % m1_c1["outcome"])
        print("(3) same fixture, both graders, side by side:")
        print("      C2 shipped=%-14s mutant=%s" % (r2["outcome"], m1_c2["outcome"]))

        check("M-U2-1 flips C2 to DELIVERED",
              m1_c2["outcome"], wake_grade.DELIVERED,
              "THE WHOLE POINT. The forbidden grader calls the content echo a "
              "delivery. That the shipped grader does not is the correctness "
              "claim of this unit, and this is the arm that makes it non-vacuous.")
        check("M-U2-1 leaves C1 DELIVERED",
              m1_c1["outcome"], wake_grade.DELIVERED,
              "a mutation that ALSO broke the positive control would prove "
              "nothing about the discrimination - it would only show the mutant "
              "is broken. C1 must survive for C2's flip to mean anything. "
              "[[discriminator-needs-an-independent-difference]]")

        # --- M-U2-2 : drop the session comparison ------------------------
        anchor2 = "        if rec.get(SESSION_KEY) != session_id:\n            continue\n"
        repl2 = "        pass  # MUTANT M-U2-2: sessionId comparison REMOVED\n"
        m2, d_ship2, d_mut2 = build_mutant("M-U2-2", anchor2, repl2)
        print("")
        print("(1) source differs at the session check: shipped=%s mutant=%s"
              % (d_ship2, d_mut2))
        s3 = os.path.join(tmp, "c3.jsonl")
        m2_c3 = m2["grade"](ARM, s3, KINDS)
        m2_c1 = m2["grade"](ARM, s1, KINDS)
        print("(2) the mutant RAN:")
        print("      mutant C3 -> %-14s reason=%s" % (m2_c3["outcome"], m2_c3["reason"]))
        print("(3) C3 shipped=%-14s mutant=%s" % (r3["outcome"], m2_c3["outcome"]))

        check("M-U2-2 flips C3 to DELIVERED",
              m2_c3["outcome"], wake_grade.DELIVERED,
              "without this, C3 could be passing on the KIND check alone and the "
              "session binding would be entirely untested - a conjunction whose "
              "members are never varied separately is one condition wearing "
              "three names.")
        check("M-U2-2 leaves C1 DELIVERED",
              m2_c1["outcome"], wake_grade.DELIVERED,
              "same paired requirement as M-U2-1")

        # --- the enum is closed and fully exercised ----------------------
        seen = {r1["outcome"], r2["outcome"], r5["outcome"], r6["outcome"],
                r7["outcome"], rinv["outcome"]}
        check("C12 every outcome is reachable",
              sorted(seen), sorted(set(wake_grade.OUTCOMES)),
              "the enum is CLOSED and every member was produced by a control in "
              "THIS run - not enumerated in a comment. [[closed-enum-needs-one-key-per-namespace]]")

        print("")
        print("=" * 70)
        print(" U2 RESULT: %d assertions, %d failed" % (PASSES[0], len(FAILURES)))
        if FAILURES:
            for f in FAILURES:
                print("   FAILED: %s" % f)
            print(" U2 VERDICT: RED (rc=1)")
            return 1
        print(" U2 VERDICT: ALL GREEN (rc=0)")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
