#!/usr/bin/env bash
# opencode_review_controls.sh — controls for opencode_review.sh
#
# ⛔ NO CONTROL MAKES A MODEL CALL. opencode spends, so every control here stops at
#    or before the gate. The only opencode invocations are --version and --help,
#    which are non-spending, and they are bounded by `timeout`.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL="$HERE/opencode_review.sh"
W="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/ocrc.$$")"; mkdir -p "$W"
trap 'rm -rf "$W"' EXIT
# Production gate fingerprinted at SUITE START — see the note in
# openrouter_review_controls.sh: a tamper check scoped to one block certifies that
# block, not the file, and the control that destroyed the real gate sat elsewhere.
# This suite writes nothing under $HERE (audited), so this should never move.
PROD_GATE="$HERE/openrouter_live_spend.gate"
PROD_GATE_AT_START="$( [ -f "$PROD_GATE" ] && sha256sum "$PROD_GATE" | cut -c1-16 || echo ABSENT )"
# The SHARED spend ledger, same treatment and for the same reason (see D10-L).
PROD_LEDGER="$HERE/../spend/openrouter_spend_ledger.tsv"
PROD_LEDGER_AT_START="$( [ -f "$PROD_LEDGER" ] && sha256sum "$PROD_LEDGER" | cut -c1-16 || echo ABSENT )"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ✅ %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  ❌ %s\n     %s\n' "$1" "${2:-}"; }
chk() { if [ "$2" = "$3" ]; then ok "$1 ($2)"; else bad "$1" "expected [$3] got [$2]"; fi; }

printf 'Review this unit.\n' > "$W/prompt.txt"
printf 'demo/model-a  1.00  2.00\n' > "$W/allow.txt"

echo "=== opencode_review controls ==="; echo

echo "D1 binary resolves and is the sh shim (not the PS one) on this path"
if command -v opencode >/dev/null 2>&1; then ok "opencode on PATH: $(command -v opencode)"; else bad "opencode on PATH" "absent"; fi
v="$(timeout 25 opencode --version 2>/dev/null | head -1)"
if [ -n "$v" ]; then ok "version responds: $v"; else bad "version responds" "no output"; fi
# The sh shim exec's the .exe directly, which is why the PowerShell re-split gotcha
# does not apply here. Asserted so an earlier correction cannot silently rot.
if head -1 "$(command -v opencode)" | grep -q '^#!/bin/sh'; then ok "D1b resolved shim is POSIX sh (PS re-split gotcha N/A on this path)"; else bad "D1b sh shim" "not a sh script"; fi

echo "D2 the three invocation traps are foreclosed"
out="$(bash "$TOOL" --model demo/model-a --prompt "$W/prompt.txt" --out "$W/d2.out" --allowlist "$W/allow.txt" --auto 2>&1)"; rc=$?
chk "D2 --auto refused rc=2" "$rc" "2"
case "$out" in *"REFUSED: --auto"*) ok "D2 refusal names --auto and why";; *) bad "D2 names --auto" "$out";; esac
out="$(bash "$TOOL" --model demo/model-a --prompt "$W/prompt.txt" --out "$W/d2b.out" --allowlist "$W/allow.txt" --share 2>&1)"; rc=$?
chk "D2b --share refused rc=2" "$rc" "2"
case "$out" in *"REFUSED: --share"*) ok "D2b refusal names --share (publication is not the tool's call)";; *) bad "D2b names --share" "";; esac
# D2c — the tool must never invoke bare `opencode` (that starts a TUI and hangs).
if grep -qE '"\$OPENCODE" run' "$TOOL"; then ok "D2c always invokes the 'run' subcommand"; else bad "D2c invokes run" "not found"; fi
# D2d — every invocation of the binary must carry `run`, `--version` or `--help`.
# ⚠ REWRITTEN: the first version of this control was VACUOUS — it piped `grep -q`
#   (which emits nothing) into `grep -v`, so the test could never be true and the
#   pass branch always ran. A control that cannot fail proves nothing, and it is the
#   same fail-open shape being audited elsewhere in this suite. This one enumerates
#   the actual invocation lines and fails on any that is bare.
bare=$(grep -nE '"\$OPENCODE"' "$TOOL" | grep -vE 'command -v|run |--version|--help' | wc -l)
chk "D2d every \$OPENCODE invocation carries run/--version/--help" "$bare" "0"
# D2e — and the control is not vacuous: the pattern DOES match the real lines.
seen=$(grep -cE '"\$OPENCODE"' "$TOOL")
if [ "$seen" -ge 2 ]; then ok "D2e pattern matches $seen real invocation lines (D2d not vacuous)"; else bad "D2e pattern matches invocations" "only $seen"; fi

echo "D3 prompt travels as a FILE, never as an argv message array"
if grep -q -- '-f "\$PROMPT"' "$TOOL"; then ok "D3 prompt attached with -f"; else bad "D3 prompt via -f" "not found"; fi

echo "D4 allowlist gate"
out="$(bash "$TOOL" --model "someone/else" --prompt "$W/prompt.txt" --out "$W/d4.out" --allowlist "$W/allow.txt" 2>&1)"; rc=$?
chk "D4 off-list model refused rc=2" "$rc" "2"
case "$out" in *"NOT on the opencode allowlist"*) ok "D4 refusal names the allowlist";; *) bad "D4 names allowlist" "$out";; esac
out="$(bash "$TOOL" --model demo/model-a --prompt "$W/prompt.txt" --out "$W/d4b.out" --allowlist "$W/allow.txt" --dry-run 2>&1)"; rc=$?
chk "D4b on-list model passes the gate (D4 not vacuous)" "$rc" "0"
out="$(bash "$TOOL" --model demo/model-a --prompt "$W/prompt.txt" --out "$W/d4c.out" --allowlist "$W/none.txt" 2>&1)"; rc=$?
chk "D4c missing allowlist refuses" "$rc" "2"
# D4d — the SHIPPED allowlist is empty of routes, so every live dispatch refuses.
n=$(awk '{sub(/#.*/,"")} /[^[:space:]]/ {c++} END {print c+0}' "$HERE/opencode_allowlist.txt")
chk "D4d shipped allowlist carries zero live routes" "$n" "0"

echo "D5 live-spend gate"
# ⚠ REWRITTEN (2026-07-30) after a fleet ruling OPENED the gate — same defect as C15 in the
#   openrouter suite: D5/D5a asserted a CIRCUMSTANCE ("no gate file exists") instead of
#   the rule ("no gate ⇒ no dispatch"), so a legitimate change in the world turned them
#   red while nothing was broken. Both branches now run against a FIXTURE COPY whose
#   gate path this suite owns. ⛔ The SHARED gate is never created, moved or deleted
#   here — other seats read it.
GATE="$PROD_GATE"
if [ -f "$GATE" ]; then
  if [ -s "$GATE" ]; then ok "D5 gate is OPEN and carries an auth id ($(tr -d '\n' < "$GATE"))"
  else bad "D5 an open gate must name its authorization" "gate file is EMPTY — it opens the lane while recording nothing"; fi
else
  ok "D5 gate ABSENT ⇒ no live opencode dispatch (closed state)"
fi
OCFIX="$W/ocfix"; mkdir -p "$OCFIX"
cp "$TOOL" "$OCFIX/opencode_review.sh"
FIXTOOL="$OCFIX/opencode_review.sh"; FIXGATE="$OCFIX/openrouter_live_spend.gate"
rm -f "$FIXGATE"
out="$(bash "$FIXTOOL" --model demo/model-a --prompt "$W/prompt.txt" --out "$W/d5.out" --allowlist "$W/allow.txt" 2>&1)"; rc=$?
chk "D5a on-list + gate closed ⇒ rc=2" "$rc" "2"
case "$out" in *"live-spend gate is CLOSED"*) ok "D5a refusal names the gate";; *) bad "D5a names the gate" "$out";; esac
# D5b — one gate governs BOTH lanes; a second gate file would be a way to open one
# lane while believing both were shut.
if grep -q 'LIVE_GATE="\$HERE/openrouter_live_spend.gate"' "$TOOL"; then ok "D5b shares ONE gate file with the openrouter lane"; else bad "D5b shared gate" "separate gate path"; fi
# ── D5c  ⭐ GATE-OPEN branch, observed WITHOUT spending ─────────────────────────
# ⛔ This lane has NO second guard: past the gate, opencode_review.sh dispatches
#    immediately through the provider's own credentials — unlike the openrouter lane,
#    where an absent key stops it. So an open fixture gate would SPEND. The seam that
#    makes the branch observable is the tool's existing OPENCODE_BIN override, pointed
#    at a stub that records its argv and exits.
#
#    ⚠ Disclosed, because it cuts both ways: OPENCODE_BIN lets any caller substitute the
#    program this tool executes. It is a legitimate test seam and it is also an
#    arbitrary-program seam; it is recorded here rather than left for someone to find.
#
#    What this buys: D2's invocation rules were asserted by GREPPING THE SOURCE. Source
#    order is not call shape — the flags that reach the binary are what matter, and now
#    they are read off an actual invocation.
# ⚠ The stub APPENDS one record per invocation. The first version overwrote a single
#   file, so it reported only the LAST call — and the tool legitimately calls the binary
#   more than once (a `--version` at report time, after the backgrounded `run`). It read
#   as "the dispatch is a bare --version", which would have sent me to fix a tool that
#   was behaving correctly. A control that models one call cannot observe a sequence.
cat > "$OCFIX/stub" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$OCSTUB_ARGV"
exit 0
STUB
chmod +x "$OCFIX/stub"
printf 'fixture-auth-id\n' > "$FIXGATE"
ARGV="$OCFIX/argv.txt"; rm -f "$ARGV"; : > "$ARGV"
OCSTUB_ARGV="$ARGV" OPENCODE_BIN="$OCFIX/stub" \
  bash "$FIXTOOL" --model demo/model-a --prompt "$W/prompt.txt" --out "$W/d5c.out" \
       --allowlist "$W/allow.txt" >/dev/null 2>&1
if [ -s "$ARGV" ]; then
  ok "D5c open gate REACHES dispatch ($(wc -l < "$ARGV" | tr -d ' ') invocation(s) recorded — D5a is not vacuous)"
  # The DISPATCH is the invocation carrying `run`; the others are version probes.
  disp="$(grep -m1 '^run ' "$ARGV")"
  if [ -n "$disp" ]; then
    ok "D5c-1 the dispatch invokes the 'run' subcommand, never a bare TUI start"
    case "$disp" in *"--format json"*) ok "D5c-2 observed --format json";; *) bad "D5c-2 --format json observed" "$disp";; esac
    case "$disp" in *" -f "*) ok "D5c-3 prompt passed as an attached FILE (-f), not as argv text";; *) bad "D5c-3 -f observed" "$disp";; esac
    case "$disp" in *--auto*|*--share*) bad "D5c-4 dangerous flags never reach the binary" "$disp";;
                    *) ok "D5c-4 neither --auto nor --share reaches the binary (observed, not grepped)";; esac
  else
    bad "D5c-1 a 'run' invocation was recorded" "recorded: $(tr '\n' '|' < "$ARGV")"
  fi
  # D5c-5 — non-vacuity of the record itself: no invocation may be bare.
  if grep -qx '' "$ARGV"; then bad "D5c-5 no bare invocation reached the binary" "an empty argv was recorded"; else ok "D5c-5 no bare (argument-less) invocation reached the binary"; fi
else
  bad "D5c open gate reaches dispatch" "the stub never ran — either the gate branch is dead or OPENCODE_BIN is not honoured; D5a would then be vacuous"
fi
# D5d — the shared gate must be exactly as this suite found it.
GATE_SHA_AFTER="$( [ -f "$PROD_GATE" ] && sha256sum "$PROD_GATE" | cut -c1-16 || echo ABSENT )"
chk "D5d production gate unchanged across the WHOLE suite" "$GATE_SHA_AFTER" "$PROD_GATE_AT_START"

echo "D6 dry-run spends nothing and needs no gate"
out="$(bash "$TOOL" --model demo/model-a --prompt "$W/prompt.txt" --out "$W/d6.out" --allowlist "$W/allow.txt" --dry-run 2>&1)"; rc=$?
chk "D6 dry-run rc=0 regardless of gate state" "$rc" "0"
case "$out" in *"no model call made"*) ok "D6 declares no call";; *) bad "D6 declares no call" "";; esac
# ⚠ THIRD instance tonight of a control pinned to the ambient gate state — this one
#   asserted the dry-run prints "CLOSED", which was only true while the gate happened to
#   be down. The RULE is that the dry-run reports the gate state HONESTLY, so the
#   assertion has to track reality in BOTH directions. Stated as a claim about
#   correspondence, it can never be invalidated by the gate legitimately moving — and it
#   now also catches a dry-run that LIES about an open gate, which the old form could not.
if [ -f "$PROD_GATE" ]; then
  case "$out" in *"gate        : OPEN"*) ok "D6 dry-run reports the gate as OPEN, matching reality";;
                  *) bad "D6 dry-run gate state matches reality" "gate is present but the dry-run did not say OPEN";; esac
else
  case "$out" in *CLOSED*) ok "D6 dry-run reports the gate as CLOSED, matching reality";;
                  *) bad "D6 dry-run gate state matches reality" "gate is absent but the dry-run did not say CLOSED";; esac
fi
if [ -f "$W/d6.out" ]; then bad "D6b dry-run writes no verdict file" "written"; else ok "D6b dry-run writes no verdict file"; fi

echo "D7 watchdog uses the resolve-at-spawn cure, not bash \$!"
if grep -qE 'taskkill /PID \$OC_PID\b' "$TOOL"; then bad "D7 bash \$! never handed to taskkill" "found it"; else ok "D7 bash \$! never handed to taskkill"; fi
if grep -q 'OC_WINPID="\$(ps' "$TOOL"; then ok "D7b windows pid resolved AT SPAWN"; else bad "D7b WINPID at spawn" "not found"; fi
if grep -q 'taskkill /PID \$OC_WINPID /T /F' "$TOOL"; then ok "D7c tree-kill targets the resolved WINDOWS pid"; else bad "D7c tree-kill target" "not found"; fi

echo "D8 unrecognized argument is loud"
out="$(bash "$TOOL" --model demo/model-a --prompt "$W/prompt.txt" --out "$W/d8.out" --allowlist "$W/allow.txt" --dry-runn 2>&1)"; rc=$?
chk "D8 typo flag rc=2" "$rc" "2"
case "$out" in *"unrecognized argument: --dry-runn"*) ok "D8 names the offending argument";; *) bad "D8 names it" "$out";; esac

# ── D10  P1c — MENTION IS NOT COMPLETION ──────────────────────
# The terminator check at opencode_review.sh:190 was `grep -qF "$TERMINATOR"` — a
# MEMBERSHIP test — and had NO control of any kind. This lane is the fleet's most
# exposed to that: the prompt built at :123 reads "end your verdict with the line:
# $TERMINATOR", so the terminator is IN the prompt and an echoed prompt certified
# as a clean review.
#
# The seam is the tool's existing OPENCODE_BIN override, already disclosed at D5c;
# the stub here goes one step further than D5c's and WRITES an event stream on
# stdout, which is what the tool appends to $RAW. Nothing spends: no real binary is
# invoked, and the fixture tool's ledger lands under $W, never at $PROD_LEDGER
# (D9 above proves that at the bytes, across this block too).
echo "D10 P1c: the terminator must appear as a LINE OF ITS OWN"
cat > "$OCFIX/stub_stream" <<'STREAMSTUB'
#!/usr/bin/env bash
if [ "$1" = "run" ]; then cat "$OCSTUB_STREAM"; fi
exit 0
STREAMSTUB
chmod +x "$OCFIX/stub_stream"
printf 'fixture-auth-id\n' > "$FIXGATE"
TERM_LINE="END OF VERDICT EOV-7Q4Z"

# $1 leg id, $2 tool to run, $3.. the event lines (already JSON-escaped)
oc_stream() {
  local id="$1" tool="$2"; shift 2
  : > "$OCFIX/stream.jsonl"
  for l in "$@"; do printf '%s\n' "$l" >> "$OCFIX/stream.jsonl"; done
  OCSTUB_STREAM="$OCFIX/stream.jsonl" OPENCODE_BIN="$OCFIX/stub_stream" \
    bash "$tool" --model demo/model-a --prompt "$W/prompt.txt" \
         --out "$OCFIX/$id.out" --allowlist "$W/allow.txt" >/dev/null 2>&1
  return $?
}

# D10a ⭐ THE DEFECT'S OWN STATE. The voice echoes the dispatch prompt — which
#   carries the terminator inside a SENTENCE — and says nothing else. Under
#   `grep -qF` this was a clean review.
oc_stream d10a "$FIXTOOL" '{"text":"Review the attached file and end your verdict with the line: END OF VERDICT EOV-7Q4Z"}'
chk "D10a rc=1 on an echoed prompt (terminator present, but inside a sentence)" "$?" "1"
if grep -q "REASON: NO_TERMINATOR" "$OCFIX/d10a.out" 2>/dev/null; then
  ok "D10a the echo is recorded as a DISPATCH FAILURE, never as 'no findings'"
else bad "D10a echo named NO_TERMINATOR" "$(head -3 "$OCFIX/d10a.out" 2>/dev/null)"; fi

# D10b POSITIVE — a real verdict with the terminator on a line of its own passes.
#   Without this the cure could be "refuse everything" and D10a would still be green.
oc_stream d10b "$FIXTOOL" '{"text":"No defects found.\nEND OF VERDICT EOV-7Q4Z"}'
chk "D10b rc=0 on a real verdict ending with the terminator line" "$?" "0"
if grep -q "DISPATCH_STATUS: OK" "$OCFIX/d10b.out" 2>/dev/null; then
  ok "D10b a clean verdict is OK (D10a is not 'refuse everything')"
else bad "D10b clean verdict OK" "$(head -3 "$OCFIX/d10b.out" 2>/dev/null)"; fi

# D10c the terminator absent entirely — unchanged behaviour, and the leg that keeps
#   D10a from being the only negative shape the suite knows.
oc_stream d10c "$FIXTOOL" '{"text":"I reviewed the unit and found no defects."}'
chk "D10c rc=1 when the terminator is absent" "$?" "1"

# D10d POSITIVE — an INDENTED terminator still counts (the awk strips leading and
#   trailing blanks, matching codex_review.sh:512).
oc_stream d10d "$FIXTOOL" '{"text":"No defects.\n   END OF VERDICT EOV-7Q4Z   "}'
chk "D10d rc=0 on an indented terminator" "$?" "0"

# D10e ⭐ POSITIVE, AND THE REASON THIS LANE TAKES A WEAKER BAR THAN
#   openrouter_parse.py. The extractor lifts text/content/message/delta from EVERY
#   event, so a trailing session/summary event lands AFTER the model's last text.
#   Under a FINAL-non-empty-line rule this correct verdict would be refused; under
#   whole-line equality it passes. This leg is what makes the difference between the
#   two lanes a measured choice rather than an inconsistency.
oc_stream d10e "$FIXTOOL" '{"text":"No defects.\nEND OF VERDICT EOV-7Q4Z"}' '{"message":"session complete"}'
chk "D10e rc=0 when a trailing session event follows the terminator" "$?" "0"

# D10f ⭐ MUTATION — restore `grep -qF` in a copy and D10a must be ADMITTED. Without
#   it every leg above proves only that my fixtures are shaped the way I shaped them,
#   and the pre-cure tool would pass this suite [[unfalsifiable-by-construction]].
MUTTOOL="$OCFIX/opencode_review.membership.sh"
sed 's#^if ! awk -v t="\$TERMINATOR".*#if ! grep -qF "$TERMINATOR" "$CONTENT" 2>/dev/null; then#' "$FIXTOOL" \
  | sed '/^ *if (s==t) { found=1 } }$/d; /^ *END { exit(found?0:1) }.\{0,40\}$/d' > "$MUTTOOL"
if cmp -s "$FIXTOOL" "$MUTTOOL"; then
  bad "D10f mutation actually landed" "the sed matched nothing — this leg is VOID, not green"
elif ! bash -n "$MUTTOOL" 2>/dev/null; then
  bad "D10f mutant parses" "the membership copy is not valid shell — VOID, not green"
else
  ok "D10f mutation landed and parses (the copy differs from the cured tool)"
  oc_stream d10f "$MUTTOOL" '{"text":"Review the attached file and end your verdict with the line: END OF VERDICT EOV-7Q4Z"}'
  chk "D10f-a membership form re-admits the echo (rc=0)" "$?" "0"
  oc_stream d10fc "$MUTTOOL" '{"text":"I reviewed the unit and found no defects."}'
  chk "D10f-c the mutation does NOT rescue the absent case (still rc=1)" "$?" "1"
fi


echo "D9 no ledger row was written by any control"
# ⚠ RE-AIMED 2026-09-04 (P1c round). This read "a ledger file exists ⇒ something
#   dispatched" — a CIRCUMSTANCE, not the rule. The ledger is SHARED with the
#   OpenRouter lane and was created 2026-07-30T20:45:45, sixteen minutes after this
#   suite was last written (20:29:13). It has been red ever since, through 287 rows,
#   and it fails the whole suite — so a real regression here would have arrived into
#   a run everyone already knew was red. The rule this leg means is "THIS SUITE adds
#   no row", and that is testable against the fingerprint taken at suite start,
#   exactly as D5d does for the gate [[anchor-validity-discipline]].
LEDGER_SHA_AFTER="$( [ -f "$PROD_LEDGER" ] && sha256sum "$PROD_LEDGER" | cut -c1-16 || echo ABSENT )"
chk "D9 shared spend ledger byte-identical across the WHOLE suite" "$LEDGER_SHA_AFTER" "$PROD_LEDGER_AT_START"
# D9b — non-vacuity. If the ledger is ABSENT at both ends the check above passes
#   while measuring nothing, and that is the state this suite shipped in. Say which
#   of the two greens was earned [[instrument-must-prove-it-fired]].
if [ "$PROD_LEDGER_AT_START" = "ABSENT" ]; then
  ok "D9b (weak) no ledger existed at suite start — D9 compared ABSENT to ABSENT"
else
  ok "D9b D9 compared a REAL ledger fingerprint ($PROD_LEDGER_AT_START, $(wc -l < "$PROD_LEDGER" | tr -d " ") rows)"
fi

echo
echo "=== $PASS passed, $FAIL failed ==="
[ "$FAIL" = "0" ] || exit 1
