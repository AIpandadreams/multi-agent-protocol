#!/usr/bin/env bash
# opencode_review.sh — dispatch ONE review voice through the opencode CLI.
#
# COMMISSION: orchestrator rulings and the fleet rulings behind them. Sibling of
# openrouter_review.sh and deliberately the same shape: the operational discipline is
# the expensive part and it is already paid for (DESIGN-PACKAGE §2).
#
# ⛔ opencode CAN SPEND — it drives a model through its own provider credentials.
#    It therefore sits behind the SAME live-spend gate as the OpenRouter lane. The
#    gate is checked before anything else that could cost money.
#
# ── THREE INVOCATION TRAPS THIS TOOL FORECLOSES (measured from `--help`, 1.18.10) ──
#  1. `opencode` with no subcommand starts an interactive TUI. Headless, that hangs
#     until a timeout kills it, and the wrapper would report a wedge for what is
#     really a usage error. This tool ALWAYS invokes `run`, never bare opencode.
#  2. `--auto` auto-approves permissions — opencode's own help calls it "(dangerous!)".
#     Never passed, and refused if a caller supplies it.
#  3. `--share` publishes the session. Publication is not this tool's decision to
#     make, so it is refused rather than merely omitted.
#
# ── WHY THE PROMPT GOES VIA -f, NOT ARGV ─────────────────────────────────────────
#    `run [message..]` takes the message as a POSITIONAL ARRAY. Handing a multi-line
#    review prompt to an argv array is the same class as the codex npm shim's
#    "unexpected argument" re-split. `-f/--file` attaches the prompt as a file, which
#    avoids argv quoting entirely.
#    ⚠ CORRECTION to my earlier seat report: npm installs THREE shims — `opencode` (POSIX
#    sh), `.cmd`, and `.ps1`. `Get-Command` reports the .ps1 because PowerShell
#    prefers it, but Git Bash resolves the sh shim, which `exec`s opencode.exe
#    directly. So the PowerShell re-split gotcha does NOT apply on this path. The
#    file-not-argv discipline is kept anyway, on the argv-array ground above.
#
# EXIT: 0 ok · 1 dispatch failed (named, verdict file still written) · 2 usage/gate
#     · 124 timeout/wedge.  ⛔ Only the verdict FILE counts, never the exit status.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIVE_GATE="$HERE/openrouter_live_spend.gate"     # one gate governs every spending lane
ALLOWLIST="$HERE/opencode_allowlist.txt"
LEDGER="$HERE/../spend/openrouter_spend_ledger.tsv"
# A fleet ruling: plain words + nonce (the old `=== … ===` was
# markdown-bait). Same string as openrouter_review.sh — one fleet terminator.
TERMINATOR="END OF VERDICT EOV-7Q4Z"
MODEL=""; PROMPT=""; OUT=""; MAXTIME=600; IDLE=180; DRYRUN=0
OPENCODE="${OPENCODE_BIN:-opencode}"

die2() { echo "opencode_review: $1" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --model)      MODEL="${2:-}"; shift 2 || die2 "--model needs a value" ;;
    --prompt)     PROMPT="${2:-}"; shift 2 || die2 "--prompt needs a value" ;;
    --out)        OUT="${2:-}"; shift 2 || die2 "--out needs a value" ;;
    --allowlist)  ALLOWLIST="${2:-}"; shift 2 || die2 "--allowlist needs a value" ;;
    --ledger)     LEDGER="${2:-}"; shift 2 || die2 "--ledger needs a value" ;;
    --max-time)   MAXTIME="${2:-}"; shift 2 || die2 "--max-time needs a value" ;;
    --idle)       IDLE="${2:-}"; shift 2 || die2 "--idle needs a value" ;;
    --terminator) TERMINATOR="${2:-}"; shift 2 || die2 "--terminator needs a value" ;;
    --dry-run)    DRYRUN=1; shift ;;
    # Refused explicitly rather than silently dropped: a caller who passes these
    # believes they are in effect, and silence would leave that belief intact.
    --auto)       die2 "REFUSED: --auto auto-approves permissions (opencode's own help calls it dangerous). This lane never runs unattended with permissions pre-granted." ;;
    --share)      die2 "REFUSED: --share publishes the session. Publication is not this tool's call." ;;
    -h|--help)    sed -n '2,40p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)            die2 "unrecognized argument: $1" ;;
  esac
done

[ -n "$MODEL" ]  || die2 "missing --model (format: provider/model)"
[ -n "$PROMPT" ] || die2 "missing --prompt"
[ -n "$OUT" ]    || die2 "missing --out"
[ -f "$PROMPT" ] || die2 "no prompt file: $PROMPT"

command -v "$OPENCODE" >/dev/null 2>&1 || die2 "opencode not found on PATH (looked for '$OPENCODE'). Install is the principal's act, not this tool's."

# ── allowlist gate — nothing admitted by default ─────────────────────────────────
[ -f "$ALLOWLIST" ] || die2 "allowlist file not found: $ALLOWLIST (refusing: no policy, no dispatch)"
ALLOW_LINE="$(awk -v m="$MODEL" '{ sub(/#.*/,""); gsub(/\r/,"") } $1==m { print; found=1; exit } END { if (!found) exit 1 }' "$ALLOWLIST")" \
  || die2 "model NOT on the opencode allowlist, refusing: $MODEL
  allowlist: $ALLOWLIST
  (allowlist-not-blocklist: every id in that file is permission to spend.)"
# (per fleet rulings, 2026-09-06) the allowlist's price columns are no longer read: no
# per-run cost is printed or ledgered by this lane.

# ── dry run — no spend, no gate needed ───────────────────────────────────────────
if [ "$DRYRUN" = "1" ]; then
  echo "opencode_review: DRY RUN — no model call made, nothing spent."
  echo "  binary      : $(command -v "$OPENCODE")"
  echo "  version     : $(timeout 25 "$OPENCODE" --version 2>/dev/null | head -1)"
  echo "  subcommand  : run   (NEVER bare 'opencode' — that starts a TUI and hangs headless)"
  echo "  model       : $MODEL   (ON the allowlist)"
  echo "  prompt      : $PROMPT ($(wc -c < "$PROMPT") B) — attached with -f, never as argv"
  echo "  format      : json"
  echo "  refused     : --auto (permission auto-approve), --share (publishes session)"
  echo "  gate        : $([ -f "$LIVE_GATE" ] && echo OPEN || echo 'CLOSED — a live run would refuse, rc=2')"
  echo "  max-time    : ${MAXTIME}s   watchdog idle: ${IDLE}s"
  echo "  verdict out : $OUT"
  exit 0
fi

# ── LIVE-SPEND GATE (per the commissioning orchestrator rulings, which made the mechanism of record) ────
if [ ! -f "$LIVE_GATE" ]; then
  cat >&2 <<EOF
opencode_review: REFUSING TO DISPATCH — the live-spend gate is CLOSED.

  gate file (absent): $LIVE_GATE

opencode drives a model through its own provider credentials, so a run here SPENDS.
The gate opens only when the principal's \$50-cap confirmation AND allowlist ratification are
both in (per a fleet ruling — the orchestrator creates the file, no other seat).

Nothing was dispatched and nothing was spent. --dry-run exercises the whole path.
EOF
  exit 2
fi

WORK="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/ocr.$$")"; mkdir -p "$WORK"
RAW="$WORK/raw.jsonl"
trap 'rm -rf "$WORK"' EXIT INT TERM
: > "$RAW"

# ── dispatch: `run`, prompt as an attached FILE, json events ─────────────────────
"$OPENCODE" run --format json --model "$MODEL" -f "$PROMPT" \
  "Review the attached file and end your verdict with the line: $TERMINATOR" \
  >> "$RAW" 2>"$WORK/err.txt" &
OC_PID=$!
# ⛔ AND its Windows pid, AT SPAWN. bash's $! is an MSYS pid — measured 2026-07-30,
#    $!=8940 vs WINPID=57080 for one process. Handing $! to taskkill kills an
#    unrelated Windows process on this shared machine. Resolve, or do not tree-kill.
OC_WINPID="$(ps 2>/dev/null | awk -v p="$OC_PID" '$1==p {print $4; exit}')"

last=-1; changed=$(date +%s); killed=0; start=$(date +%s)
while kill -0 "$OC_PID" 2>/dev/null; do
  sleep 5
  now=$(date +%s); sz=$(wc -c < "$RAW" 2>/dev/null || echo 0)
  [ "$sz" != "$last" ] && { last=$sz; changed=$now; }
  if [ $((now - changed)) -ge "$IDLE" ] || [ $((now - start)) -ge "$MAXTIME" ]; then
    kill -TERM "$OC_PID" 2>/dev/null
    [ -n "${OC_WINPID:-}" ] && powershell.exe -NoProfile -Command "taskkill /PID $OC_WINPID /T /F" >/dev/null 2>&1
    kill -KILL "$OC_PID" 2>/dev/null
    killed=1; break
  fi
done
wait "$OC_PID" 2>/dev/null; OC_RC=$?

mkdir -p "$(dirname "$OUT")" 2>/dev/null
fail_out() {
  { echo "DISPATCH_STATUS: FAILED"; echo "REASON: $1"; echo "MODEL_REQUESTED: $MODEL"
    echo "VOICE: opencode $( "$OPENCODE" --version 2>/dev/null | head -1 )"; echo ""
    echo "⛔ THIS IS A DISPATCH FAILURE, NOT A CLEAN REVIEW."
    echo "   A voice that failed and a voice that found nothing must never read the"
    echo "   same. Do NOT record this as 'no findings'."; echo ""
    echo "detail: $2"; echo "--- stderr ---"; head -c 800 "$WORK/err.txt" 2>/dev/null
    echo "--- partial output kept as evidence ---"; head -c 2000 "$RAW" 2>/dev/null
  } > "$OUT"
}

if [ "$killed" = "1" ]; then
  fail_out "WEDGE_OR_TIMEOUT" "no growth for ${IDLE}s (or ${MAXTIME}s total); killed bash pid $OC_PID / winpid ${OC_WINPID:-unresolved}. Caller: retry once, then a DIFFERENT voice."
  echo "opencode_review: WEDGE/TIMEOUT — killed at spawn-resolved pid" >&2; exit 124
fi
if [ ! -s "$RAW" ]; then
  # An empty stream with rc=0 is still a failure. "Only the file counts."
  fail_out "EMPTY_OUTPUT_STREAM" "opencode exited rc=$OC_RC producing no events."
  echo "opencode_review: FAILED — empty output stream (rc=$OC_RC)" >&2; exit 1
fi

# ── extract the verdict text from the json event stream ─────────────────────────
CONTENT="$WORK/content.txt"
python - "$RAW" "$CONTENT" <<'PYEOF' 2>/dev/null || true
import json, sys
raw, out = sys.argv[1], sys.argv[2]
parts = []
for line in open(raw, "r", encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line:
        continue
    try:
        ev = json.loads(line)
    except ValueError:
        parts.append(line)          # not JSON: keep it, never silently drop evidence
        continue
    for k in ("text", "content", "message", "delta"):
        v = ev.get(k) if isinstance(ev, dict) else None
        if isinstance(v, str):
            parts.append(v); break
open(out, "w", encoding="utf-8", newline="\n").write("\n".join(parts))
PYEOF
[ -f "$CONTENT" ] || cp "$RAW" "$CONTENT"

# ⛔ MENTION IS NOT COMPLETION (P1c, per an orchestrator ruling, 2026-09-04). This was
#    `grep -qF "$TERMINATOR" "$CONTENT"` -- a MEMBERSHIP test, and this lane is the
#    most exposed one in the fleet to it: the prompt built at :123 says "end your
#    verdict with the line: $TERMINATOR", so the terminator is IN the prompt and an
#    echoed prompt passed the check with no verdict at all. Same defect and same
#    cure as codex_review.sh:493-512, whose reasoning applies here verbatim.
#    The bar is WHOLE-LINE EQUALITY: some physical line, stripped, must EQUAL the
#    terminator. An echo of :123's prompt cannot produce one, because there the
#    terminator sits at the end of a SENTENCE, not on a line of its own -- that is
#    the independent difference the discriminator keys on.
#    ⚠ NOT the stronger final-non-empty-line bar that openrouter_parse.py takes.
#    That parser reads the model's raw content with nothing appended; this content
#    is assembled by the extractor above, which lifts text/content/message/delta
#    from EVERY event, so a trailing session or summary event can legitimately land
#    after the model's last text. A final-line rule would refuse correct verdicts on
#    a shape I have no captured stream to rule out [[honest-failure-outcomes]].
#    CR is stripped first: `grep -F` matched straight through CRLF and whole-line
#    equality would not.
if ! awk -v t="$TERMINATOR" '{ s=$0; sub(/\r$/,"",s); gsub(/^[ \t]+|[ \t]+$/,"",s);
                              if (s==t) { found=1 } }
                            END { exit(found?0:1) }' "$CONTENT" 2>/dev/null; then
  fail_out "NO_TERMINATOR" "The voice never emitted the terminator as a line of its own, so a complete 'no findings' cannot be told from a severed stream or an echoed prompt."
  echo "opencode_review: FAILED — no terminator line" >&2; exit 1
fi

mkdir -p "$(dirname "$LEDGER")" 2>/dev/null
[ -f "$LEDGER" ] || printf 'utc_ts\tmodel_requested\tmodel_answered\tstatus\treason\tprompt_tokens\tcompletion_tokens\tfinish_reason\n' > "$LEDGER"
# ⚠ opencode reports no per-run usage here; tokens are UNKNOWN rather than 0 — a
#   fabricated zero would be a false figure. (Per fleet rulings: no price fields.)
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$MODEL" "$MODEL" "OK" "OK" "UNKNOWN" "UNKNOWN" \
  "opencode-run" >> "$LEDGER"

{ echo "DISPATCH_STATUS: OK"; echo "REASON: OK"; echo "MODEL_REQUESTED: $MODEL"
  echo "VOICE: opencode"; echo "ROLE: SOP-7 review voice. NOT a judge (SOP-3 unchanged)."
  echo "⚠ TOKENS/COST: UNKNOWN here — opencode reports spend via 'opencode stats'."
  echo "---8<--- verdict below ---8<---"; cat "$CONTENT"; } > "$OUT"
echo "opencode_review: OK — verdict → $OUT"
exit 0
