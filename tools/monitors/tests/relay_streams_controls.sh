#!/bin/sh
# Two-sided control for the DECLARED-STREAM guard in watch_relay_inbox.sh
# (an orchestrator ruling, adopting the owner seat's domain split; supersedes the option-(c)
# WARN-only shape I built in an earlier round and never committed).
#
# WHAT THIS GUARD'S GREEN IS INDISTINGUISHABLE FROM — stated because a fleet ruling
# requires it of every control landed this week, and because this guard has ALREADY
# been the wrong shape once:
#
#   (1) a guard that resolves each declared stream and aborts when one is missing,
#   (2) a guard whose matcher is loose enough that a DEAD stream resolves on a
#       NEIGHBOUR's traffic and can therefore never abort at all.
#
# Those two are indistinguishable on any healthy inbox, and (2) is not
# hypothetical: naive `orch_to_t2` matches 27 lifetime files, of which 10 are
# t1orch_to_t2engine and 1 is paorch_to_t2. Arm 4 is the separating assertion --
# a planted file carrying ONLY the neighbour token must NOT satisfy the dead
# family's declaration [[discriminator-needs-an-independent-difference]].
#
#   (3) a third reading, which arm 5 separates: a guard keyed to the 24h WINDOW
#       rather than the lifetime corpus. Four of the six declared streams show 0
#       in a 24h view, so a windowed guard would abort on a healthy inbox. The
#       domain is the whole ruling and it must be asserted, not assumed.
#
# Isolated: RELAY_DIR is a temp dir, the manifest is a temp file. The real inbox
# is never read and nothing in the workspace is written.
set -u
WATCH=$(cd "$(dirname "$0")/.." && pwd)/watch_relay_inbox.sh
TMP=$(mktemp -d "${TMPDIR:-/tmp}/relaystr.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
# Machine-dependent, for the reason measured in an earlier seat report.
# Per an orchestrator ruling and the owner seat's reply: a budget is variance-tested, not
# proximity-tested. The observed band on identical small-fixture work is
# 13-67 s across seats -- 5x -- so no multiple-of-TYPICAL survives. This is a
# FLOOR with headroom over the observed MAXIMUM, not a guess at the average
# [[budgets-are-variance-tested-not-proximity-tested]].
TIMEOUT_S="${TIMEOUT_S:-150}"

stage() {                       # $1 = space-separated filenames to create
  rm -rf "$TMP/inbox"; mkdir -p "$TMP/inbox"
  for f in $1; do printf '## staged\n' > "$TMP/inbox/$f"; done
}
manifest() {                    # $1 = space-separated tokens to declare
  : > "$TMP/man.txt"
  printf '# control manifest\n' >> "$TMP/man.txt"
  for t in $1; do printf '%s\n' "$t" >> "$TMP/man.txt"; done
}

run() {                         # output -> stdout ; rc -> $TMP/rc
  # Budget is a CEILING, not a sleep -- same correction as the declared-source
  # control. An arm that arms polls forever, so waiting the full floor made every
  # healthy arm cost the maximum. Wait for the VERDICT; the ceiling still bounds a
  # genuinely dark run. ⚠ Kill by the PID captured at spawn, never by name: this
  # machine runs peers' watchers concurrently (WATCHDOG PID RULE).
  RELAY_DIR="$TMP/inbox" RELAY_POLL_S=5 RELAY_STREAMS_MANIFEST="$1" \
    timeout "$TIMEOUT_S" sh "$WATCH" < /dev/null > "$TMP/out" 2>&1 &
  _pid=$!
  _waited=0
  while kill -0 "$_pid" 2>/dev/null; do
    if grep -q 'RELAY INBOX WATCH ARMED' "$TMP/out" 2>/dev/null; then
      kill "$_pid" 2>/dev/null; wait "$_pid" 2>/dev/null
      echo 124 > "$TMP/rc"
      cat "$TMP/out"
      return 0
    fi
    sleep 1
    _waited=$((_waited+1))
    [ "$_waited" -ge "$TIMEOUT_S" ] && break
  done
  wait "$_pid" 2>/dev/null
  echo $? > "$TMP/rc"
  # This watcher ARMS then polls forever, so rc=124 is the NORMAL outcome for a
  # healthy arm and cannot mean outage by itself. Discriminator: rc=124 with no
  # banner at all. Owner (E1281 §2) was one entry from filing a fail-open charge
  # sourced entirely from a dark rig; a control that cannot tell its own outage
  # from a verdict will eventually publish one as the other.
  if [ "$(cat "$TMP/rc")" = "124" ] && ! grep -q 'RELAY INBOX WATCH' "$TMP/out"; then
    : > "$TMP/outage"
  fi
  cat "$TMP/out"
}
rc_of() { cat "$TMP/rc"; }

check() {                       # $1 label  $2 expected-substring  $3 output
  if [ -f "$TMP/outage" ]; then
    printf '\n  ⛔ INSTRUMENT OUTAGE — killed at %ss having emitted NOTHING.\n' "$TIMEOUT_S"
    printf '     NOT a result about the guard. Re-run with a larger TIMEOUT_S.\n'
    printf '     Grading STOPPED at "%s" so a dark rig cannot be published as behaviour.\n' "$1"
    exit 3
  fi
  if printf '%s' "$3" | grep -q -- "$2"; then
    pass=$((pass+1)); printf '  PASS  %s\n' "$1"
  else
    fail=$((fail+1)); printf '  FAIL  %s\n     wanted: %s\n     got:    %s\n' \
      "$1" "$2" "$(printf '%s' "$3" | tr '\n' ' ' | cut -c1-220)"
  fi
}

echo "RELAY DECLARED-STREAM GUARD -- two-sided control"
echo "isolated at $TMP ; the real inbox is never read"
echo

# --- 1: every declared token resolves -> ARMS
stage "RELAY_engine_to_paorch_a_2026-08-10.md relay_paorch_to_engine_b_2026-08-10.md"
manifest "engine_to_paorch paorch_to_engine"
o=$(run "$TMP/man.txt")
check "1 all declared tokens resolve -> ARMS" "RELAY INBOX WATCH ARMED" "$o"
check "1b banner carries lifetime/window per stream" "engine_to_paorch=1/1" "$o"
check "1c banner states the residual out loud" "NOT inbox coverage" "$o"
# 1d: per-seat disambiguation (a seam an orchestrator review named). Two seats arm this same script
# on one machine, distinguishable otherwise only by pid — the banner must name
# the manifest so "which declaration set is this arm enforcing" is answerable
# from what was printed at arm, not reconstructed afterwards.
check "1d ARMED banner names the manifest it enforces" "manifest $TMP/man.txt" "$o"

# --- 2: a declared token with no file -> ABORT (the red path is reachable)
stage "RELAY_engine_to_paorch_a_2026-08-10.md"
manifest "engine_to_paorch paorch_to_engine"
o=$(run "$TMP/man.txt")
check "2 declared token resolves ZERO -> ABORT" "resolved ZERO over the LIFETIME corpus" "$o"
check "2b abort NAMES the missing stream" "paorch_to_engine" "$o"
check "2c abort exits rc=2, not a silent pass" "^2$" "$(rc_of)"

# --- 3: the same file absent but UNDECLARED -> ARMS. Without this, arm 2 passes
# for a guard that aborts on any thin inbox regardless of what was declared.
stage "RELAY_engine_to_paorch_a_2026-08-10.md"
manifest "engine_to_paorch"
o=$(run "$TMP/man.txt")
check "3 same file absent but UNDECLARED -> ARMS" "RELAY INBOX WATCH ARMED" "$o"

# --- 4: PLANTED COLLISION (per the orchestrator ruling and the owner seat's split). The inbox contains
# ONLY neighbour-token traffic. A substring matcher resolves orch_to_t2 on these
# and arms; the anchored matcher must abort. This is the arm that separates
# reading (1) from reading (2).
stage "t1orch_to_t2engine_x_2026-08-10.md paorch_to_t2_y_2026-08-10.md"
manifest "orch_to_t2"
o=$(run "$TMP/man.txt")
check "4 dead stream does NOT resolve on neighbour tokens -> ABORT" \
      "resolved ZERO over the LIFETIME corpus" "$o"
check "4b ...naming the dead stream, not the neighbours" "orch_to_t2" "$o"

# --- 4c: and the neighbours themselves must still resolve on that same corpus,
# so arm 4 is the ANCHOR working and not the matcher being broken for everyone.
manifest "t1orch_to_t2engine paorch_to_t2"
o=$(run "$TMP/man.txt")
check "4c ...while the neighbour tokens DO resolve on the same files" \
      "RELAY INBOX WATCH ARMED" "$o"

# --- 5: THE DOMAIN. A file older than the event window must still satisfy the
# LIFETIME declaration. If this ever fails, the guard has been re-keyed to the
# window and will abort on healthy streams -- the shape the orchestrator ruling superseded.
stage "RELAY_engine_to_paorch_old_2026-07-03.md"
touch -d '30 days ago' "$TMP/inbox/RELAY_engine_to_paorch_old_2026-07-03.md" 2>/dev/null \
  || touch -t 202607030900 "$TMP/inbox/RELAY_engine_to_paorch_old_2026-07-03.md"
manifest "engine_to_paorch"
o=$(run "$TMP/man.txt")
check "5 a file OUTSIDE the 24h window still satisfies the LIFETIME check" \
      "RELAY INBOX WATCH ARMED" "$o"
check "5b ...and it is reported as lifetime-present, window-zero" "engine_to_paorch=1/0" "$o"

# --- 6: no manifest at all -> ABORT, never a silent blind arm.
stage "RELAY_engine_to_paorch_a_2026-08-10.md"
o=$(run "$TMP/nonexistent.txt")
check "6 no manifest -> ABORT" "no declared-stream manifest" "$o"

# --- 7: TOKEN VALIDATION (owner E1289). A declaration is documented as a literal
# but interpolated into an ERE, so a metacharacter resolves as a PATTERN while
# reading as a name. Measured on the real corpus: `orch.to.t2` matches ZERO files
# literally and resolves 16 through the regex -- a typo'd declaration goes green
# while the family it names is dark.
stage "t1orch_to_t2engine_x_2026-08-10.md paorch_to_t2_y_2026-08-10.md"
manifest "orch.to.t2"
o=$(run "$TMP/man.txt")
check "7 a metachar token is matched LITERALLY -> resolves ZERO, does not pattern-match" \
      "resolved ZERO over the LIFETIME corpus" "$o"
check "7b ...and the abort names the MANIFEST as the place to look, not the corpus" \
      "check the MANIFEST spelling" "$o"
# 7c is the separating half: the SAME staged files with the correctly-spelled
# literal token must abort for the OTHER reason (dead stream), proving arm 7 keys
# on the token's spelling and not on this fixture being unsatisfiable.
manifest "orch_to_t2"
o=$(run "$TMP/man.txt")
check "7c ...while the correctly-spelled token aborts as a DEAD STREAM instead" \
      "resolved ZERO over the LIFETIME corpus" "$o"

# SUITE COMPLETENESS (creator CB-008). Grading an arm set by its TOTAL is exactly
# the masking the guard under test exists to defeat: pass+fail is non-zero, nothing
# is declared, and a missing arm is invisible. rc=2, NOT fail++ -- a short run has
# not failed a check, it has failed to be evidence.
# FIXED assignment, deliberately NOT env-overridable (CB-009 s3: the `:-` form
# let the run supply the one number it must not supply about itself
# [[protected-class-keyed-to-artifacts-own-signal]]).
# DERIVATION RULE FOR THIS SUITE: line-initial `check` calls EXACTLY (17); no
# arm increments pass/fail directly. declared_sources_controls.sh derives
# DIFFERENTLY under the same name (check calls + 2 direct arms) -- learn the
# rule from the suite you are editing, not its neighbour (CB-009 s3).
EXPECT_ARMS=17
printf '\n%d passed, %d failed\n' "$pass" "$fail"
if [ $((pass + fail)) -ne "$EXPECT_ARMS" ]; then
  printf '⛔ SUITE INCOMPLETE: ran %d arm(s), declared %d. A short run is NOT a green run.\n' \
    "$((pass + fail))" "$EXPECT_ARMS"
  exit 2
fi
[ "$fail" -eq 0 ]
