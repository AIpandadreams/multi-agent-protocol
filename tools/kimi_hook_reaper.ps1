# kimi_hook_reaper.ps1 — TRANSITION guard after D3 (the principal clickable 2026-08-08 ~02:4x).
# The kimi plugin Stop hook was deregistered machine-wide, but sessions ALREADY RUNNING
# snapshotted the old hook config at session start and keep spawning review-gate-stop.js
# at every turn-stop until they restart. This reaper kills only ORPHANED instances
# (parent dead) so a wedge lasts <=5 min instead of forever. Remove the schtask
# (KimiHookOrphanReaper) once all seat sessions have cycled past 2026-08-08 02:44 ET.
$procs = Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
  Where-Object { $_.CommandLine -match 'review-gate-stop\.js' }
foreach ($p in $procs) {
  $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)" -ErrorAction SilentlyContinue
  if (-not $parent) {
    # Dead parent = the harness that spawned it is gone or the pipe is abandoned; safe kill.
    & taskkill /PID $p.ProcessId /F 2>$null
    Add-Content -Path "$PSScriptRoot\..\workpapers\p5-confirm-2026-08-08\reaper_log.txt" `
      -Value "$(Get-Date -Format o) killed orphan review-gate-stop PID $($p.ProcessId) (parent $($p.ParentProcessId) dead)"
  }
}
