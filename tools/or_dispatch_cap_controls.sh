#!/usr/bin/env bash
# or_dispatch_cap_controls.sh — controls for an orchestrator ruling's second mechanism.
#
# ⛔ THE BAR (fleet standing): a control that never refuses is indistinguishable from no
#    control. Refusal paths first; one OK case exists solely to prove the tool can still
#    grant — without it, "always refuses" and "correctly refuses" look identical.
#
# ⚠⚠ HONEST LIMIT OF THE CONCURRENCY CONTROL — read this before citing it.
#    It asserts the invariant (never more than `cap` grants, one claimant per slot) and
#    the invariant holds. It does NOT demonstrate that the ATOMIC claim is why.
#    Measured 2026-08-01, twice: a deliberately racy read-then-increment implementation
#    was substituted for the real tool and PASSED this control unchanged — 3 granted,
#    5 refused, 3 slot files — first with plain parallel spawn, then again with a
#    2-second barrier holding all 8 arms at the read until released together. The
#    listdir->open window is too narrow to collide on this host.
#    ⇒ This control CANNOT currently tell the two designs apart. The race-freedom of
#      O_EXCL is a CONSTRUCTION argument, not something these controls have shown.
#      Treating a pass here as evidence of atomicity would be
#      [[control-passing-for-the-wrong-reason]] — the outcome is reachable by a broken
#      path. The control is kept because the invariant is worth pinning, but it is
#      pinned as an invariant, not as a proof of mechanism.
#
# ⚠ These controls never dispatch, never touch the network, and never read a key. They
#   exercise a filesystem claim protocol and nothing else.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
T="$HERE/or_dispatch_cap.py"
[ -f "$T" ] || { echo "controls: COULD-NOT-RUN, missing $T" >&2; exit 3; }

D="$(mktemp -d)"; trap 'rm -rf "$D"' EXIT
FAILED=0
N=0

# ⛔ Every python invocation runs a FILE or the tool itself. `python -` (any bare-dash
#   form) reads the script from stdin and, under this agent harness, blocks on a read that
#   never gets EOF. Absolute on purpose: a shipped tool must not require its next reader
#   to adjudicate which stdin variants are safe.
py() { python "$@"; }

chk() { # name want_rc [needle]  — runs whatever CMD holds
  local name="$1" want="$2" needle="${3:-}" got out
  N=$((N+1))
  out="$("${CMD[@]}" 2>&1)"; got=$?
  if [ "$got" != "$want" ]; then
    printf '**FAIL**  %-34s want rc=%s got rc=%s\n' "$name" "$want" "$got"; FAILED=$((FAILED+1))
    printf '%s\n' "$out" | sed 's/^/          /' | head -6; return 0
  fi
  if [ -n "$needle" ] && ! printf '%s' "$out" | grep -q -- "$needle"; then
    printf '**FAIL**  %-34s rc ok but output lacks %s\n' "$name" "$needle"; FAILED=$((FAILED+1))
    printf '%s\n' "$out" | sed 's/^/          /' | head -6; return 0
  fi
  printf 'PASS  %-38s rc=%s\n' "$name" "$got"
  return 0
}

echo "— could-not-run (rc=3): the cap must never be inferred —"
echo "  ⛔ the fail-OPEN reading is the expensive one, so each of these is checked by name"
CMD=(py "$T" --run-state "$D/r0" --claim arm)                  ; chk "no --cap at all"        3 "not an unlimited cap"
CMD=(py "$T" --cap abc --run-state "$D/r0" --claim arm)        ; chk "--cap non-integer"      3 "not an integer"
CMD=(py "$T" --cap -1  --run-state "$D/r0" --claim arm)        ; chk "--cap negative"         3 "negative"
CMD=(py "$T" --cap 3   --run-state "$D/r0")                    ; chk "no --claim label"       3 "need --claim"

echo
echo "— ⛔ cap=0 must REFUSE (rc=4), not read as 'unset' and open the gate —"
CMD=(py "$T" --cap 0 --run-state "$D/rz" --claim arm-1)        ; chk "cap=0 first claim"      4 "CAP EXHAUSTED"

echo
echo "— the OK case: without it, 'always refuses' and 'correctly refuses' are the same —"
for i in 1 2 3; do
  CMD=(py "$T" --cap 3 --run-state "$D/r1" --claim "arm-$i")   ; chk "cap=3 claim $i granted"  0 "slot $i of 3"
done

echo
echo "— the refusal, and it must STAY refused rather than wrap around —"
CMD=(py "$T" --cap 3 --run-state "$D/r1" --claim arm-4)        ; chk "4th claim refused"      4 "3 of 3"
CMD=(py "$T" --cap 3 --run-state "$D/r1" --claim arm-5)        ; chk "5th claim still refused" 4 "3 of 3"

echo
echo "— CONCURRENCY: 8 arms claim at once against cap=3. Asserts the INVARIANT only —"
echo "  ⚠ a racy read-then-increment impl PASSES this too (measured twice, incl. barrier);"
echo "    see the header — this pins the invariant, NOT the atomicity mechanism —"
N=$((N+1))
mkdir -p "$D/rc"
for i in 1 2 3 4 5 6 7 8; do
  ( py "$T" --cap 3 --run-state "$D/rc" --claim "par-$i" >"$D/rc.$i.out" 2>&1; echo $? > "$D/rc.$i.rc" ) &
done
wait
GRANT=0; REFUSE=0; OTHER=0
for i in 1 2 3 4 5 6 7 8; do
  case "$(cat "$D/rc.$i.rc")" in
    0) GRANT=$((GRANT+1)) ;; 4) REFUSE=$((REFUSE+1)) ;; *) OTHER=$((OTHER+1)) ;;
  esac
done
# The slot files are the ground truth: exactly cap of them, each claimed once.
SLOTS="$(ls "$D/rc" | wc -l | tr -d ' ')"
UNIQ="$(cat "$D/rc"/slot-* | cut -f2 | sort -u | wc -l | tr -d ' ')"
if [ "$GRANT" = 3 ] && [ "$REFUSE" = 5 ] && [ "$OTHER" = 0 ] && [ "$SLOTS" = 3 ] && [ "$UNIQ" = 3 ]; then
  printf 'PASS  %-38s 3 granted / 5 refused, %s slot files, %s distinct claimants\n' \
         "8 parallel claims vs cap=3" "$SLOTS" "$UNIQ"
else
  printf '**FAIL**  ⛔ CAP RACED: granted=%s refused=%s other=%s slots=%s distinct=%s (want 3/5/0/3/3)\n' \
         "$GRANT" "$REFUSE" "$OTHER" "$SLOTS" "$UNIQ"; FAILED=$((FAILED+1))
fi

echo
echo "— the cap is PER-RUN: a separate run-state has its own budget, and this is a"
echo "  LIMITATION being pinned, not a feature — deleting the dir resets the cap —"
CMD=(py "$T" --cap 3 --run-state "$D/r2" --claim other-run)    ; chk "fresh run-state grants"  0 "slot 1 of 3"
rm -rf "$D/r1"
CMD=(py "$T" --cap 3 --run-state "$D/r1" --claim after-wipe)   ; chk "wiped run-state RESETS"  0 "slot 1 of 3"
echo "        ⚠ pinned deliberately: an arm cap is NOT a spend control. That is mechanism 3."

echo
echo "— ⛔ the three outcomes must be DISTINGUISHABLE, which is the entire clause the ruling adds —"
N=$((N+1))
py "$T" --cap 3 --run-state "$D/r3" --claim ok >/dev/null 2>&1;  RC_OK=$?
py "$T" --cap 0 --run-state "$D/r4" --claim no >/dev/null 2>&1;  RC_CAP=$?
py "$T" --cap x --run-state "$D/r5" --claim no >/dev/null 2>&1;  RC_BAD=$?
if [ "$RC_OK" = 0 ] && [ "$RC_CAP" = 4 ] && [ "$RC_BAD" = 3 ] \
   && [ "$RC_CAP" != "$RC_BAD" ] && [ "$RC_CAP" != 2 ]; then
  echo "PASS  granted=0  cap-hit=4  could-not-run=3   (4 is not 2 and not 3)"
  echo "        ⇒ 'we stopped ourselves on budget' cannot be misread as 'the model broke'."
else
  echo "**FAIL**  exit codes collide: ok=$RC_OK cap=$RC_CAP bad=$RC_BAD"; FAILED=$((FAILED+1))
fi

echo
echo "— ⛔ REGRESSION control carried forward from mechanism 1: the refusal must survive a"
echo "     stdout that cannot encode its marker glyph. rc=4 is the path that PRINTS one —"
N=$((N+1))
cp_out="$(PYTHONIOENCODING=cp1252 py "$T" --cap 0 --run-state "$D/rcp" --claim arm 2>&1)"; cp_rc=$?
if [ "$cp_rc" = 4 ] && printf '%s' "$cp_out" | grep -q "CAP EXHAUSTED" \
   && ! printf '%s' "$cp_out" | grep -q "UnicodeEncodeError"; then
  echo "PASS  cap refusal survives cp1252 stdout (rc=4, message printed, no traceback)"
else
  echo "**FAIL**  cp1252 regressed the cap refusal: rc=$cp_rc"; FAILED=$((FAILED+1))
  printf '%s' "$cp_out" | sed 's/^/          /' | head -8
fi

echo
echo "— --status must report without claiming (a reporter that consumes budget is a trap) —"
N=$((N+1))
BEFORE="$(ls "$D/rc" | wc -l | tr -d ' ')"
st_out="$(py "$T" --run-state "$D/rc" --status 2>&1)"; st_rc=$?
AFTER="$(ls "$D/rc" | wc -l | tr -d ' ')"
if [ "$st_rc" = 0 ] && [ "$BEFORE" = "$AFTER" ] && printf '%s' "$st_out" | grep -q "3 slot(s) claimed"; then
  echo "PASS  --status reports 3 claimed and consumed nothing ($BEFORE -> $AFTER)"
else
  echo "**FAIL**  --status rc=$st_rc slots $BEFORE -> $AFTER: $st_out"; FAILED=$((FAILED+1))
fi

echo
echo "$N control(s) run."
[ "$FAILED" = 0 ] && { echo "ALL CONTROLS PASS"; exit 0; } || { echo "$FAILED CONTROL(S) FAILED"; exit 2; }
