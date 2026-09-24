<#
.SYNOPSIS
  Three-state liveness probe for a dispatched wrapper process.

.DESCRIPTION
  Replaces the inline monitor check `tasklist //FI "PID eq $PID" | grep -q "$PID"`, which was
  FAIL-OPEN in the precise way this workspace's own memory warns about: it had only two outcomes,
  so "the probe could not answer" and "the process has exited" were the SAME answer. A watchdog
  reading that cannot tell a dead process from a broken instrument, and it kills on both.

  It was also a SUBSTRING match. `grep -q "5402"` matches a line containing 154028, and it matches
  the PID appearing in any other column, so it could report ALIVE for a process that had exited.
  Wrong in both directions from one expression.

  This reports THREE states and never collapses them:
    exit 0  ALIVE    -- the process exists and, if -StartedUtc was given, is the SAME process
    exit 1  EXITED   -- POSITIVELY established that it is gone, by the one measured error identity
    exit 2  UNKNOWN  -- the probe itself could not answer. NOT a kill signal. A caller that treats
                        this as EXITED has rebuilt the defect this script exists to remove.

  ⚠ Q1-G4 (codex r44, DRIVEN; reproduced first-hand before this edit). THE FIRST VERSION OF THIS
  SCRIPT REBUILT THAT DEFECT ONE LAYER DOWN. It called `Get-Process -ErrorAction SilentlyContinue`
  and read `$null` as "no such process". But the cmdlet-level `-ErrorAction` overrides
  `$ErrorActionPreference = "Stop"` for NONTERMINATING errors, so a cmdlet that FAILED also
  produced `$null` -- and the script emitted `PROC_ALIVE=EXITED reason=no-such-process`, the kill
  state, for a probe that never answered. Measured, with Get-Process swapped at the boundary:

      genuinely no such process -> PROC_ALIVE=EXITED  ... reason=no-such-process
      NONTERMINATING failure    -> PROC_ALIVE=EXITED  ... reason=no-such-process   <- IDENTICAL
      terminating failure       -> PROC_ALIVE=UNKNOWN ... reason=probe-threw

  My own pre-review measurement missed this because I drove the ARGUMENT space -- four process ids,
  none of which threw -- and concluded the catch was unreachable through the parameter. That was
  true and it was aimed at the wrong property. The independent opus leg cleared this bar using the
  same frame, against the real cmdlet. Two of us, separately, measured the thing that was fine.

  THE CURE IS THE RULE, not a patch: **only a POSITIVELY IDENTIFIED "no such process" may say
  EXITED.** Every other outcome -- terminating, nonterminating, a null return with no error at all
  -- is UNKNOWN. The identity is measured, not guessed:

      Get-Process -Id <missing> -ErrorAction Stop
        type     = Microsoft.PowerShell.Commands.ProcessCommandException
        FQID     = NoProcessFoundForGivenId,Microsoft.PowerShell.Commands.GetProcessCommand
        category = ObjectNotFound
      (stable across several missing ids; a live id still returns normally under -ErrorAction Stop)

  THE MARKER LINE IS THE AUTHORITY, NOT THE EXIT CODE, and that is not a stylistic preference.
  Caught while testing the first version: invoking it via `-File` with an EMPTY -StartedUtc makes
  PowerShell's own parameter binder fail, and the binder exits 1 -- which under an exit-code-only
  contract is indistinguishable from EXITED, i.e. the kill signal, produced by a script that never
  ran. (Independently reproduced by the opus r44 leg, which also noted the live caller shape: a
  caller building `-StartedUtc $started` where the spawn-time StartTime read came back empty.)

  ⚠ Q1-G6 (opus r44). The marker must be matched ANCHORED AND WHOLE-FIELD, and the first version's
  recommended predicate was an unanchored substring over the whole captured stream -- while the
  ALIVE line echoed the PROCESS NAME, an externally-influenced value, into that same stream. A
  caller folding in stderr, a log, or this file's own source could match a marker that was never a
  verdict. That is the completion-watch marker-echo class. Two changes: the marker line now carries
  ONLY script-minted tokens (the process name moved to its own PROC_NAME= line, which is
  informational and NOT part of the verdict contract), and the predicate below anchors to line
  start and takes the first whitespace-delimited field.

  Correct monitor predicate:

      state=$(powershell -NoProfile -File tools/proc_alive.ps1 -ProcessId "$PID" -StartedUtc "$T" \
              | grep -m1 '^PROC_ALIVE=' | cut -d' ' -f1)
      case "$state" in
        PROC_ALIVE=EXITED)           ... the ONLY state that may stop a watch or kill ;;
        PROC_ALIVE=ALIVE)            ... keep waiting ;;
        PROC_ALIVE=ALIVE-UNVERIFIED) ... keep waiting; the PID is NOT pinned to your process ;;
        *)                           ... UNKNOWN or no marker: keep waiting, AND SAY SO ;;
      esac

  ⚠ Q1-N3: ALIVE-UNVERIFIED is a distinct STATE TOKEN, not a trailing field, precisely because
  this predicate keeps field 1 and discards the rest. A caller who has not updated its case
  statement falls to `*)` and keeps waiting -- safe by default. If you spawned the process, pass
  -StartedUtc; if you cannot read StartTime at spawn, treat ALIVE-UNVERIFIED as "still running,
  identity unproven" and never as a licence to conclude the leg you launched is the one alive.

  (Every marker string in this header is indented, so `^PROC_ALIVE=` cannot match this file's own
  source if a caller ever cats it into the stream. That is deliberate, not incidental.)

  PID REUSE, and ⚠ Q1-G5 (opus r44): THE REUSE GUARD IS OPT-IN, so it must SAY when it is off.
  Windows recycles PIDs, so a PID alone does not identify a process. Pass the start time captured
  at spawn ((Get-Process -Id $p.Id).StartTime.ToUniversalTime().ToString("o")) and a recycled PID
  reports EXITED instead of keeping a watchdog waiting on a stranger forever -- ⚠ WITH A BOUND,
  added at r51 (opus) at the claim site rather than appended below it. That sentence was written
  when the comparison was two-valued. The r51 band (see the tolerance note at the comparison) makes
  it true only for a start-time difference GREATER THAN 2s. Inside that window a recycled PID
  reports ALIVE-UNVERIFIED / reuse-check=INCONCLUSIVE -- keep waiting, identity unproven -- NOT
  EXITED. The mechanism was amended and this guarantee was left whole, which is precisely the
  amend-at-the-claim-site defect: a withdrawn claim standing upstream of its own withdrawal reads
  as current to everyone who stops at the header. The narrower true statement: a recycled PID whose
  stranger started more than 2s from the original reports EXITED; nearer than that, this script
  says it cannot tell, and a caller must not read that as identity. Omitting -StartedUtc
  is legitimate (you did not spawn the process), but the first version disabled the check SILENTLY,
  so a recycled PID reported ALIVE for a stranger with nothing in the output saying the guard was
  down. Every ALIVE line now carries `reuse-check=ON` or `reuse-check=DISABLED`. The capability is
  not removed -- its state is computed and reported.

.EXAMPLE
  $p = Start-Process cmd.exe -ArgumentList '/c','...' -PassThru
  $started = (Get-Process -Id $p.Id).StartTime.ToUniversalTime().ToString("o")
  powershell -NoProfile -File tools\proc_alive.ps1 -ProcessId $p.Id -StartedUtc $started
#>
param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [string]$StartedUtc = ""
)

$ErrorActionPreference = "Stop"

# Q1-G6: marker tokens are script-minted only. No externally-influenced value is ever interpolated
# into a PROC_ALIVE= line, so the line cannot be spoofed by what a process happens to be called.
function Emit-Verdict {
    param([string]$State, [string]$Tail, [int]$Code)
    Write-Output ("PROC_ALIVE={0} pid={1}{2}" -f $State, $ProcessId, $(if ($Tail) { " $Tail" } else { "" }))
    exit $Code
}

$proc = $null
try {
    # -ErrorAction Stop, NOT SilentlyContinue: every failure must reach this catch so it can be
    # CLASSIFIED. Silencing them is what made a failed probe indistinguishable from a dead process.
    $proc = Get-Process -Id $ProcessId -ErrorAction Stop
} catch {
    if ($_.FullyQualifiedErrorId -like "NoProcessFoundForGivenId,*") {
        Emit-Verdict "EXITED" "reason=no-such-process" 1
    }
    # Anything else: the probe failed, which is not evidence about the process.
    Emit-Verdict "UNKNOWN" ("reason=probe-failed:{0}" -f $_.Exception.GetType().Name) 2
}

if ($null -eq $proc) {
    # No object and no error. Nothing was established, so nothing may be concluded -- and in
    # particular this is NOT the EXITED branch, which is exactly the confusion G4 removed.
    Emit-Verdict "UNKNOWN" "reason=no-object-no-error" 2
}

$reuse = "DISABLED"
if ($StartedUtc -ne "") {
    try {
        $actual = $proc.StartTime.ToUniversalTime().ToString("o")
    } catch {
        # A live process whose StartTime is unreadable (access denied on a foreign process) is
        # NOT evidence of exit. Say so rather than guessing in either direction.
        Emit-Verdict "UNKNOWN" "reason=starttime-unreadable" 2
    }
    try {
        $rt = [System.Globalization.DateTimeStyles]::RoundtripKind
        $want = ([datetime]::Parse($StartedUtc, $null, $rt)).ToUniversalTime()
        $got = ([datetime]::Parse($actual, $null, $rt)).ToUniversalTime()
    } catch {
        # A malformed -StartedUtc used to throw out of the script with NO marker at all. The
        # contract makes marker-absence UNKNOWN, so that was safe -- but a stated UNKNOWN with a
        # reason beats an absence a caller has to interpret.
        Emit-Verdict "UNKNOWN" "reason=starttime-unparseable" 2
    }
    # ⚠ Q1-(b) TOLERANCE (opus r50). The comparison was `Abs(diff) -gt 2` seconds, so any process
    # whose start time landed within two seconds of the one we spawned satisfied the reuse check
    # and was reported `ALIVE reuse-check=ON` -- a STRANGER's identity asserted as PROVEN. Windows
    # recycles PIDs, and two seconds is a wide door on a machine where several agents and the
    # reviewer poller spawn processes concurrently. Both sides of this comparison come from the
    # SAME expression (`.StartTime.ToUniversalTime().ToString("o")`, round-trip, 100ns ticks), so
    # equality is the honest test and a tolerance was never buying precision.
    #
    # ⚠ But tightening it to `-ne` alone would be a REGRESSION, not a fix: it would route a mere
    # formatting or precision mismatch straight to EXITED, and EXITED is the one state this script
    # says may stop a watch or kill. That trades a false ALIVE for a false KILL SIGNAL, which is
    # strictly worse. So the band is split three ways, and only the middle one is new:
    #     ticks EQUAL          -> ALIVE, reuse-check=ON   (identity PROVEN, and now only then)
    #     0 < diff <= 2s       -> ALIVE-UNVERIFIED        (identity UNPROVEN; keep waiting)
    #     diff > 2s            -> EXITED, pid-reused      (unchanged)
    # Nothing that used to report EXITED changes. The window that used to claim a verified match
    # now says, in the state token itself, that it cannot prove one -- which the sanctioned
    # `cut -d' ' -f1` reader sees, per Q1-N3, and which falls to `*)` (keep waiting) in an
    # unmodified caller. Safe by default without the caller being updated first.
    $deltaSec = [math]::Abs(($want - $got).TotalSeconds)
    if ($deltaSec -gt 2) {
        Emit-Verdict "EXITED" ("reason=pid-reused want={0} got={1}" -f $StartedUtc, $actual) 1
    }
    if ($want.Ticks -ne $got.Ticks) {
        Emit-Verdict "ALIVE-UNVERIFIED" ("reuse-check=INCONCLUSIVE reason=starttime-mismatch " +
            "want={0} got={1}" -f $StartedUtc, $actual) 0
    }
    $reuse = "ON"
}

# Informational, and deliberately NOT on the marker line: the process name is chosen by whoever
# created the executable, so it is the one value here an outsider can influence.
Write-Output ("PROC_NAME={0}" -f $proc.ProcessName)
# ⚠ Q1-N3 (opus r45 PATH 5). `reuse-check=DISABLED` used to ride an `ALIVE` verdict as a TRAILING
# field -- and this file's own sanctioned predicate is `cut -d' ' -f1`, which throws every trailing
# field away. So the disclosure added by G5 was invisible to the only reader this script tells
# people to use: a caller that spawned its leg but read an empty StartTime got a bare
# `PROC_ALIVE=ALIVE` and could wait forever on a recycled stranger. A disclosure placed in a field
# the recommended reader discards is not a disclosure.
#
# The state token itself now carries it. `ALIVE-UNVERIFIED` matches neither `PROC_ALIVE=ALIVE` nor
# `PROC_ALIVE=EXITED`, so an UNMODIFIED caller using the predicate above falls to `*)` -- keep
# waiting, and say so -- which is the safe direction, and it is safe WITHOUT the caller being
# updated first. Only EXITED may stop a watch, and that branch is untouched.
$state = if ($reuse -eq "ON") { "ALIVE" } else { "ALIVE-UNVERIFIED" }
Emit-Verdict $state ("reuse-check={0}" -f $reuse) 0
