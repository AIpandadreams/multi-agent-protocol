<#
.SYNOPSIS
  Pre-dispatch canary for the shared codex models-cache corruption, built to the amended
  interim SOP: CONSUMERS-FIRST IS A GATE ON THE RENAME, not a step that follows it.

.DESCRIPTION
  The failure this exists to catch returns rc=0 with the prompt ECHOED BACK and no verdict,
  while logging a models_manager TTL-renewal error. It is shared: one corrupt cache fails
  codex at every seat and the reviewer-poller scheduled task identically.

  ⛔ rc=0 IS NOT A VERDICT. Acceptance is a TERMINATOR IN THE VERDICT FILE and nothing else.
     An exit code over an unread target is the defect class this whole instrument answers.

  ⛔ THE FILE'S OWN VERSION STAMP IS NOT EVIDENCE OF THE SCHEMA IT CONTAINS. TTL renewal is a
     PARTIAL write: it rewrites client_version/fetched_at in place while leaving the models
     array as the other version wrote it. So this classifies on the PROBE'S BEHAVIOUR, never
     on the cache file's stamp.

  ⛔ NEVER RENAME THE SHARED CACHE WHILE ANOTHER SEAT'S RUN IS LIVE. Enumeration comes FIRST
     and gates the rename:
        zero live consumers  -> rename-aside, re-probe, dispatch in the fresh window
        any live consumer    -> DO NOT RENAME. Dispatch on the corrupt cache with
                                terminator-only acceptance; if that lands echo-shaped or
                                dead, rename-aside AFTER the peer exits and re-dispatch.

  ⛔ NEVER identify codex processes BY NAME for any consequential act. The desktop app-server
     is a long-lived process that shares ~/.codex and must be SPARED; it is excluded here by
     IMAGE PATH, and the exclusion is reported so a wrong exclusion is visible rather than
     silent.

.PARAMETER DryRun
  Classify a saved probe output instead of dispatching. Used to prove the classifier
  DISCRIMINATES - a classifier only ever shown healthy output has never been tested.

.PARAMETER SampleFile
  With -DryRun, the saved probe output to classify.

.PARAMETER TimeoutSec
  Inactivity watchdog for the probe. Default 45.
#>
[CmdletBinding()]
param(
  [switch]$DryRun,
  [string]$SampleFile,
  [int]$TimeoutSec = 45
)

$ErrorActionPreference = 'Stop'
$CacheFile = Join-Path $env:USERPROFILE '.codex\models_cache.json'
$TERMINATOR = 'CANARY-OK-TERMINATOR'

function Write-Head($t) { Write-Output ''; Write-Output ("=== $t ===") }

# --------------------------------------------------------------- classification
function Classify($text) {
  # Order matters: the TTL signature is checked BEFORE the terminator, because a run can
  # echo a prompt that CONTAINS the terminator string. ⭐ A TERMINATOR THAT THE ECHO CAN
  # SUPPLY IS NOT A TERMINATOR - so the probe asks for it on its OWN line, alone.
  if ($null -eq $text -or $text.Trim().Length -eq 0) { return 'DEAD-EMPTY' }
  if ($text -match 'failed to renew cache TTL' -or $text -match 'missing field') {
    return 'CACHE-CORRUPT'
  }
  if ($text -match 'This content was flagged') { return 'CONTENT-FLAGGED' }
  # ⭐ A REFUSAL ABOUT THE CWD IS NOT A STATEMENT ABOUT THE CACHE. Named separately so it can
  #   never be laundered into CACHE-CORRUPT and answered with a rename.
  if ($text -match 'trusted directory') { return 'CWD-NOT-TRUSTED' }
  if ($text -match 'unexpected argument' -or $text -match 'error: unrecognized') { return 'CLI-ARG-FORM' }
  if ($text -match 'try again at' -or $text -match 'usage limit') { return 'QUOTA' }
  if ($text -match 'code-mode host closed') { return 'HOST-DEATH' }
  if ($text -match "(?m)^\s*$([regex]::Escape($TERMINATOR))\s*$") { return 'OK' }
  return 'ECHO-OR-NO-VERDICT'
}

# --------------------------------------------------------------- consumers
function Get-CodexConsumers {
  # Returns codex.exe processes EXCLUDING the desktop app-server, identified by image path.
  # ⚠ The exclusion is reported, not assumed: a wrong exclusion must be visible.
  $all = @(Get-CimInstance Win32_Process -Filter "Name='codex.exe'" -ErrorAction SilentlyContinue)
  $spared = @($all | Where-Object { $_.ExecutablePath -and $_.ExecutablePath -match 'WindowsApps' })
  $live   = @($all | Where-Object { -not ($_.ExecutablePath -and $_.ExecutablePath -match 'WindowsApps') })
  [pscustomobject]@{ All = $all; Spared = $spared; Live = $live }
}

# --------------------------------------------------------------- probe
function Invoke-Probe {
  $dir = Join-Path $env:TEMP ("codex-canary-" + [guid]::NewGuid().ToString('N').Substring(0,8))
  New-Item -ItemType Directory -Path $dir | Out-Null
  $prompt = Join-Path $dir 'prompt.txt'
  $out    = Join-Path $dir 'out.txt'

  # Deliberately trivial: this measures whether codex RUNS, not whether it reasons.
  $body = @"
Reply with exactly two lines and nothing else.
Line 1: the number of letters in the word cache
Line 2: $TERMINATOR
"@
  [System.IO.File]::WriteAllText($prompt, $body, (New-Object System.Text.UTF8Encoding($false)))

  # PID captured AT SPAWN. ⛔ This is the only identifier the watchdog may kill by, and /T is
  #    load-bearing: one dispatch owns two codex.exe and codex's parent is node.exe.
  # ⛔ --skip-git-repo-check IS LOAD-BEARING HERE. codex refuses a non-trusted cwd, and this
  #    probe deliberately runs in a scratch dir. Without the flag the refusal arrives as a
  #    non-verdict and the canary would report a CWD problem as a CACHE problem - an
  #    instrument that misattributes its own failure is worse than no instrument.
  # CODEX_HOME pinned per-dispatch to the dedicated CLI home (a fleet ruling): inherited by
  # cmd.exe -> codex.exe; the desktop app keeps ~/.codex untouched. ⚠ The canary now
  # certifies the home the REVIEW LANE actually uses — a canary probing the shared home
  # would certify an instrument the dispatches no longer run on.
  $env:CODEX_HOME = "$env:USERPROFILE\.codex-cli"
  $p = Start-Process -FilePath 'cmd.exe' `
        -ArgumentList "/c codex exec --skip-git-repo-check - < `"$prompt`" > `"$out`" 2>&1" `
        -WorkingDirectory $dir -PassThru -WindowStyle Hidden
  $killed = $false
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while (-not $p.HasExited) {
    if ((Get-Date) -gt $deadline) {
      taskkill /PID $p.Id /T /F | Out-Null
      $killed = $true
      break
    }
    Start-Sleep -Milliseconds 500
  }
  $text = if (Test-Path $out) { [System.IO.File]::ReadAllText($out) } else { '' }
  [pscustomobject]@{
    Text = $text; Rc = $(if ($killed) { 'WATCHDOG-KILL' } else { $p.ExitCode })
    Dir = $dir; Killed = $killed
  }
}

# =============================================================== main
Write-Head 'codex canary'
Write-Output ("cache : {0}" -f $CacheFile)
if (Test-Path $CacheFile) {
  $fi = Get-Item $CacheFile
  Write-Output ("        {0} B, mtime {1}  <- SIZE AND STAMP ARE NOT EVIDENCE OF SCHEMA" -f $fi.Length, $fi.LastWriteTime)
} else {
  Write-Output '        ABSENT (codex will refetch)'
}

if ($DryRun) {
  if (-not $SampleFile -or -not (Test-Path $SampleFile)) {
    Write-Output 'DRYRUN requires -SampleFile pointing at a saved probe output.'
    exit 2
  }
  $verdict = Classify ([System.IO.File]::ReadAllText($SampleFile))
  Write-Output ("DRYRUN {0} -> {1}" -f (Split-Path $SampleFile -Leaf), $verdict)
  exit 0
}

$probe = Invoke-Probe
$verdict = Classify $probe.Text
Write-Output ("probe : rc={0}  verdict={1}" -f $probe.Rc, $verdict)
Write-Output ("        output kept at {0}" -f $probe.Dir)

if ($verdict -eq 'OK') {
  Write-Output 'GO - codex answered with its terminator. Dispatch normally.'
  exit 0
}

Write-Head 'consumers-first gate'
$c = Get-CodexConsumers
Write-Output ("codex.exe total {0}; spared as desktop app-server {1}; LIVE CONSUMERS {2}" -f `
              $c.All.Count, $c.Spared.Count, $c.Live.Count)
foreach ($s in $c.Spared) { Write-Output ("   spared  PID {0}  {1}" -f $s.ProcessId, $s.ExecutablePath) }
foreach ($l in $c.Live)   { Write-Output ("   LIVE    PID {0}  {1}" -f $l.ProcessId, $l.ExecutablePath) }

if ($verdict -ne 'CACHE-CORRUPT') {
  Write-Output ''
  Write-Output ("STOP - the probe failed as {0}, which the rename does not cure." -f $verdict)
  Write-Output '       Renaming the shared cache here would be a substitution for a diagnosis.'
  exit 1
}

if ($c.Live.Count -gt 0) {
  Write-Output ''
  Write-Output 'DO NOT RENAME - a peer run is live on the shared cache.'
  Write-Output '  Dispatch on the corrupt cache with TERMINATOR-ONLY acceptance. Only if that'
  Write-Output '  run lands echo-shaped or dead, rename-aside AFTER the peer exits, then'
  Write-Output '  re-dispatch. The rename is gated on the enumeration, not the other way round.'
  exit 3
}

Write-Output ''
Write-Output 'ZERO live consumers -> rename-aside is permitted. Proposed, NOT performed:'
$aside = "$CacheFile.bad_" + (Get-Date -Format 'yyyy-MM-dd_HHmmss')
Write-Output ("  Move-Item `"$CacheFile`" `"$aside`"")
Write-Output '  then re-run this canary; dispatch inside the fresh window.'
Write-Output '⚠ The set-aside file may be a GOOD cache - two of three set aside on 08-08 were.'
Write-Output '  Keep it; do not delete it.'
exit 4
