#!/bin/sh
# custody_emit_wrapper.candidate.sh — CANDIDATE. NOT DEPLOYED.
#
# ⛔ THIS FILE IS NOT WIRED TO ANYTHING. The live hook is
# `custody_emit_wrapper.sh`, referenced from .claude/settings.json:43. This
# candidate exists as a separate file *because* the live one is a PreToolUse
# hook: editing that file in place takes effect on the very next tool call in
# every session on this machine, so an edit IS a deploy and there is no
# build-then-review window. A wedged PreToolUse hook is the documented
# freeze-forever mode. Promotion = replace the live file's contents with this
# one's, and that is not builder's call.
#   ROLLBACK (one line, after promotion):
#       git checkout <pre-promotion-sha> -- tools/custody/custody_emit_wrapper.sh
#   KILL SWITCH (no redeploy, no git): set CUSTODY_ATTEMPT_LOG=0 in the hook's
#       environment — every added path below short-circuits and this file
#       behaves byte-for-byte as the shipped wrapper does today.
#
# ── WHAT IT ADDS ───────────────────────────────────────────────────────────
# A PARENT-SIDE ATTEMPT RECORD, which custody_attempts.py names as its own
# first residual and explicitly declines to build:
#
#   "The attempt record is written by the emitter, so it exists only once the
#    interpreter is up and the payload parsed. The two MEASURED wedges had the
#    python process at 0.0 s CPU — wedged in interpreter/prelude startup,
#    BEFORE any line of the emitter ran. Such a wedge leaves NO attempt record
#    and is therefore reported GONE, which is wrong. […] Covering it needs a
#    record written by the PARENT."
#
# So the exact class this closes is: a startup wedge currently reads GONE when
# it is FROZEN — and GONE is the reading that gets a live tree discarded.
#
# ⭐ IT MUST BE SHELL-NATIVE, and that is forced, not preferred. The phase being
# recorded is "python has not started yet". Recording it by invoking python
# would be an instrument that cannot observe its own failure mode
# [[emitter-and-verifier-are-one-grammar]] — so the record is written with
# shell primitives, which means the log's grammar now has TWO writers in two
# languages. That is a real hazard and it is why test_wrapper_attempt.sh drives
# the join with the PYTHON reader rather than by string-comparing lines.
#
# ⛔ AN OPEN ATTEMPT ON A KILL IS THE DOCUMENTED SEMANTICS, not a choice made
# here. custody_attempts.py's header enumerates what leaves a record open and
# names this case verbatim: "os._exit() from the watchdog, SIGKILL, SIGTERM
# from the wrapper's `timeout -k` […] → finally NEVER RUNS → open. So 'open'
# means precisely 'this process did not come back under its own power'."
# A bound-killed child did not come back under its own power. So:
#     rc 124 (TERM) / 137 (KILL grace fired) → completion NOT written → FROZEN
#     any other rc                           → completion written, rc recorded
#
# ⛔⛔ THE LINE ABOVE IS FACTUALLY WRONG AND THE WHOLE RC SPLIT IS UNSOUND.
# Corrected 2026-08-17 after a two-anchor review round (opus D11-D13 + codex §3)
# and MY OWN measurement, which settled a point the two anchors disagreed on:
# `timeout -k 2 3` against a TERM-ABSORBING child — i.e. the case where the KILL
# grace demonstrably DID fire — returns **124, not 137**. GNU timeout reports the
# TIMEOUT, not the signal, so "137 (KILL grace fired)" describes a path that
# cannot occur by that mechanism and the 137 arm is dead code for the reason
# given. (137 is still reachable — an EXTERNAL SIGKILL of the child, e.g. the OOM
# killer — but that is a different event than the one named.)
# The split is also wrong in both directions independent of that error: a healthy
# child that VOLUNTARILY exits 124 is recorded FROZEN, and a child killed by any
# other signal (130/134/139/143) has its completion WRITTEN, erasing the evidence.
# rc is the wrong discriminator. The reviewers' cure — gate on ELAPSED ≥ BUDGET,
# or carry an out-of-band "child returned normally" sentinel — is a SHAPE change,
# so it is recorded here and NOT taken unilaterally [[shape-change-is-adjudication]].
# ⛔ VERDICT ON THIS FILE: DO-NOT-PROMOTE, both anchors, 2026-08-17. See
# the review record. Nothing below has been re-fixed; the file stands as reviewed.
# ⚠ The split matters: closing on EVERY rc would mask the wedge (the parent
# survives the kill, so it would happily close a pair the child never finished),
# and leaving it open on EVERY non-zero rc would report FROZEN for an ordinary
# emitter exception — whose own `finally` did run. Both errors are silent.
#
# ⚠ IT ALSO HONOURS THE READER'S CAP. custody_attempts.start() refuses at
# ATTEMPT_MAX_LINES and writes CAP_MARKER once, so that a capped log reports the
# cap instead of a verdict. A second writer that ignored the cap would push the
# file past it and defeat that logic from outside — the reader would go on
# emitting verdicts over a truncated record.
#
# TEST OVERRIDES (test_emit_wrapper.sh / test_wrapper_attempt.sh; production
# never sets them):
#   CUSTODY_EMITTER_PY    — substitute child (wedge stand-in for the replay)
#   CUSTODY_WRAP_BUDGET_S — deadline, default 8
#   CUSTODY_ATTEMPT_LOG   — 0 disables the parent attempt record entirely
#   CUSTODY_SESSION_ID    — override the session id (tests only)

PROJ="${CLAUDE_PROJECT_DIR:-.}"
EMITTER="${CUSTODY_EMITTER_PY:-$PROJ/tools/custody/custody_emitter.py}"
BUDGET="${CUSTODY_WRAP_BUDGET_S:-8}"

# Fail-open guards: no python / no timeout / no emitter → skip silently, exit 0.
command -v python  >/dev/null 2>&1 || exit 0
command -v timeout >/dev/null 2>&1 || exit 0
[ -f "$EMITTER" ] || exit 0

# Firing receipt: a lease mtime cannot say WHICH hook command produced it (the
# old direct-python command and this wrapper write the identical file), and a
# guard is not shipped until it demonstrably fires live — so the wrapper leaves
# its own dated trace. One file, overwritten, never grows.
touch "$PROJ/plans/.custody_wrapper_lastfire" 2>/dev/null || true

# ── parent attempt record ──────────────────────────────────────────────────
# Mirrors custody_attempts.py: SEP=TAB, KIND_ATTEMPT="A", KIND_COMPLETE="C",
# ATTEMPT_PREFIX=".custody_attempts.", ATTEMPT_MAX_LINES=20000,
# CAP_MARKER="# CAPPED", attempt_id = "<pid>-<epoch.6f>".
#
# ⚠ SESSION ID COMES FROM THE ENVIRONMENT, AND THE JOIN WAS VERIFIED, NOT
# ASSUMED. The emitter takes its session from the stdin PAYLOAD
# (custody_emitter.py:362 `payload.get("session_id")`), which this wrapper must
# pass through untouched — reading stdin here would consume the child's input.
# CLAUDE_CODE_SESSION_ID was checked against the emitter's own live output
# (2026-08-17: plans/.custody_attempts.<CLAUDE_CODE_SESSION_ID> is the file the
# emitter was actively writing), so the two ids are the same string. If they
# ever diverge, every parent attempt lands in a file no completion reaches and
# the log MANUFACTURES the FROZEN signature it exists to detect — so
# test_wrapper_attempt.sh asserts the pairing rather than the filename
# [[independently-selected-facts-are-not-paired]].
ATT_ID=""
ATT_LOG=""
if [ "${CUSTODY_ATTEMPT_LOG:-1}" != "0" ]; then
    ATT_SESSION="${CUSTODY_SESSION_ID:-${CLAUDE_CODE_SESSION_ID:-}}"
    # Same shape as custody_attempts._SESSION_RE. A session id that fails this
    # is skipped, never sanitised into a different file's name.
    case "$ATT_SESSION" in
        "" | *[!A-Za-z0-9_-]* ) ATT_SESSION="" ;;
    esac
    if [ -n "$ATT_SESSION" ] && [ ${#ATT_SESSION} -le 64 ] && [ -d "$PROJ/plans" ]; then
        ATT_LOG="$PROJ/plans/.custody_attempts.$ATT_SESSION"
        # Cap check BEFORE writing, exactly where the python writer puts it: a
        # cap enforced at completion time could leave an attempt whose
        # completion was refused, i.e. fabricate a freeze out of bookkeeping.
        ATT_N=0
        [ -f "$ATT_LOG" ] && ATT_N=$(wc -l < "$ATT_LOG" 2>/dev/null || echo 0)
        if [ "$ATT_N" -ge 20000 ]; then
            [ "$ATT_N" -eq 20000 ] && printf '# CAPPED at 20000 lines — this attempt log is TRUNCATED. It is NOT a complete record and its tail must NOT be read as a freeze/gone verdict.\n' >> "$ATT_LOG" 2>/dev/null
            ATT_LOG=""
        else
            ATT_NOW=$(date +%s.%6N 2>/dev/null) || ATT_NOW=""
            if [ -n "$ATT_NOW" ]; then
                ATT_ID="$$-$ATT_NOW"
                printf 'A\t%s\t%s\t%s\twrapper\n' \
                    "$(date +%s.%3N)" "$ATT_ID" "$$" >> "$ATT_LOG" 2>/dev/null \
                    || { ATT_ID=""; ATT_LOG=""; }
            else
                ATT_LOG=""
            fi
        fi
    fi
fi

# stdin (the hook payload) flows straight through to the child; stdout/stderr
# are silenced so the harness's pipes close with this wrapper and nothing the
# child prints can be mistaken for hook output.
timeout -k 2 "$BUDGET" python "$EMITTER" --project-dir "$PROJ" >/dev/null 2>&1
RC=$?

# Completion — written for every outcome EXCEPT the two that mean the bound
# fired. See the header: those must stay OPEN so the reader sees FROZEN.
if [ -n "$ATT_ID" ] && [ -n "$ATT_LOG" ]; then
    case "$RC" in
        124|137) : ;;   # bound fired — deliberately leave the attempt open
        *) printf 'C\t%s\t%s\t%s\t?\twrapper-rc%s\n' \
               "$(date +%s.%3N)" "$ATT_ID" "$$" "$RC" >> "$ATT_LOG" 2>/dev/null || true ;;
    esac
fi

exit 0
