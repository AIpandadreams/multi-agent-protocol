# pcx_launch_record.ps1 — parallel-codex (pcx) phase-0 launch record (the TWIN)
#
# SPEC OF RECORD: a proposal in the private workspace (revision r16)
#   sha256 7c9add1cc7113ce104700ca9b6a03238c24d1a7399fd3a7248dc413232a0ea5a
# Sections implemented: §2.1 ("The launch record is the READABLE TWIN of the
# slot ... written ONCE at registration and never rewritten, so no mid-rewrite
# crash can corrupt it") and §2.7 layer 1 (the persisted classification index).
#
# FIELD SET IS NORMATIVE (§2.7 layer 1), exactly:
#   {dispatch_id, attempt, slot, wrapper_pid, wrapper_identity, job_name,
#    dispatcher_pid, registered_at_utc, generation, ttl_deadline_utc}
# `generation` (OPr9-3) and `ttl_deadline_utc` (OPr8-10) are the two fields the
# r8/r9 twins omitted and whose absence broke the HELD/adoption synthesis and
# the branch-9 fallback clock. Their presence is asserted by control C-LR-3.

Set-StrictMode -Version 2.0
. (Join-Path $PSScriptRoot 'pcx_common.ps1')

$script:PcxLaunchRecordFields = @(
    'dispatch_id', 'attempt', 'slot', 'wrapper_pid', 'wrapper_identity',
    'job_name', 'dispatcher_pid', 'registered_at_utc', 'generation', 'ttl_deadline_utc'
)

function Get-PcxLaunchRecordFieldSet { @($script:PcxLaunchRecordFields) }

function Get-PcxRunDir {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$DispatchId)
    return (Join-Path (Join-Path $Root 'runs') $DispatchId)
}

function Get-PcxLaunchRecordPath {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$DispatchId, [Parameter(Mandatory)][int]$Attempt)
    return (Join-Path (Get-PcxRunDir -Root $Root -DispatchId $DispatchId) "launch_record_a$Attempt.json")
}

# WRITE-ONCE. Exclusive create: a second write MUST fail rather than rewrite —
# that property is the whole reason the twin is trustworthy when the slot is not.
function Write-PcxLaunchRecord {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$DispatchId,
        [Parameter(Mandatory)][int]$Attempt,
        [Parameter(Mandatory)][int]$Slot,
        [Parameter(Mandatory)][int]$WrapperPid,
        [Parameter(Mandatory)]$WrapperIdentity,
        [Parameter(Mandatory)][string]$JobName,
        [Parameter(Mandatory)][int]$DispatcherPid,
        [Parameter(Mandatory)][string]$Generation,
        [Parameter(Mandatory)][string]$TtlDeadlineUtc
    )
    $runDir = Get-PcxRunDir -Root $Root -DispatchId $DispatchId
    if (-not (Test-Path -LiteralPath $runDir)) { $null = New-Item -ItemType Directory -Path $runDir -Force }

    $rec = [ordered]@{
        dispatch_id       = $DispatchId
        attempt           = $Attempt
        slot              = $Slot
        wrapper_pid       = $WrapperPid
        wrapper_identity  = [pscustomobject]@{
            name         = [string]$WrapperIdentity.name
            pid          = [int]$WrapperIdentity.pid
            creation_utc = (Normalize-IdentityTimestamp $WrapperIdentity.creation_utc)
        }
        job_name          = $JobName
        dispatcher_pid    = $DispatcherPid
        registered_at_utc = (Get-PcxUtcNow)
        generation        = $Generation
        ttl_deadline_utc  = (Normalize-IdentityTimestamp $TtlDeadlineUtc)
    }
    $path = Get-PcxLaunchRecordPath -Root $Root -DispatchId $DispatchId -Attempt $Attempt
    $null = New-PcxFileExclusive -Path $path -Content (ConvertTo-PcxJson ([pscustomobject]$rec))
    return $path
}

function Read-PcxLaunchRecord {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$DispatchId, [Parameter(Mandatory)][int]$Attempt)
    return (Read-PcxJson -Path (Get-PcxLaunchRecordPath -Root $Root -DispatchId $DispatchId -Attempt $Attempt))
}

# The index: every launch record under runs\ (§2.7 layer 1). The union with
# live slots and reaped archives is the durable wrapper-pid -> dispatch index;
# phase-0 ships the launch-record leg of it only.
function Get-PcxLaunchRecordIndex {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Root)
    $runs = Join-Path $Root 'runs'
    if (-not (Test-Path -LiteralPath $runs)) { return @() }
    $out = New-Object System.Collections.ArrayList
    foreach ($f in @(Get-ChildItem -LiteralPath $runs -Recurse -File -Filter 'launch_record_a*.json' -ErrorAction SilentlyContinue)) {
        $r = Read-PcxJson -Path $f.FullName
        if ($null -ne $r) { $null = $out.Add($r) }
    }
    return @($out.ToArray())
}
