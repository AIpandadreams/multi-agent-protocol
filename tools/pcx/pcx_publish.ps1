# pcx_publish.ps1 — parallel-codex (pcx) phase-0 publication primitive
#
# SPEC OF RECORD: the phase-0 proposal (revision 16) in the private workspace
#   sha256 7c9add1cc7113ce104700ca9b6a03238c24d1a7399fd3a7248dc413232a0ea5a
# Sections implemented: §3.5 branch 9(v) (PUBLISH-FIRST landing — sidecar by
# exclusive-create, THEN the temp, THEN the atomic Move), §5.5 (the {temp,
# sidecar} PAIR is ONE lifecycle unit, deleted temp-FIRST sidecar-SECOND).
#
# SCOPE NOTE: this file implements the LANDING MECHANISM only. The branch-9
# state machine around it (R1 fence, E_promote pre-pin, W' spawn/confirm, the
# candidate mark) is NOT built in phase-0 scope as delivered — see
# PHASE0_BUILD_REPORT.md flagged items.

Set-StrictMode -Version 2.0
. (Join-Path $PSScriptRoot 'pcx_common.ps1')

# ---------------------------------------------------------------------------
# Names (§3.5 branch 9(v), §6 Q2)
#   temp    : slot_<n>.json.tmp_<pid>_<epoch>
#   sidecar : slot_<n>.json.tmp_<pid>_<epoch>.who
# Per-reaper-unique so racing takes never collide.
# ---------------------------------------------------------------------------
function Get-PcxTempName {
    param([Parameter(Mandatory)][int]$Slot, [Parameter(Mandatory)][int]$CreatorPid, [Parameter(Mandatory)][int]$Epoch)
    return "slot_$Slot.json.tmp_${CreatorPid}_${Epoch}"
}
function Get-PcxSidecarName {
    param([Parameter(Mandatory)][int]$Slot, [Parameter(Mandatory)][int]$CreatorPid, [Parameter(Mandatory)][int]$Epoch)
    return ((Get-PcxTempName -Slot $Slot -CreatorPid $CreatorPid -Epoch $Epoch) + '.who')
}
function Get-PcxSlotRecordName {
    param([Parameter(Mandatory)][int]$Slot)
    return "slot_$Slot.json"
}

# The sidecar name is the parse authority for the publication key and, in the
# torn case ONLY, for creator identity (§5.5's ONE named exception).
$script:PcxSidecarNameRegex = '^slot_(?<slot>\d+)\.json\.tmp_(?<pid>\d+)_(?<epoch>\d+)\.who$'
$script:PcxTempNameRegex    = '^slot_(?<slot>\d+)\.json\.tmp_(?<pid>\d+)_(?<epoch>\d+)$'

function ConvertFrom-PcxSidecarName {
    param([Parameter(Mandatory)][string]$Name)
    $m = [regex]::Match($Name, $script:PcxSidecarNameRegex)
    if (-not $m.Success) { return $null }
    return [pscustomobject]@{
        slot      = [int]$m.Groups['slot'].Value
        name_pid  = [int]$m.Groups['pid'].Value
        epoch     = [int]$m.Groups['epoch'].Value
        temp_name = $Name.Substring(0, $Name.Length - 4)
    }
}
function ConvertFrom-PcxTempName {
    param([Parameter(Mandatory)][string]$Name)
    $m = [regex]::Match($Name, $script:PcxTempNameRegex)
    if (-not $m.Success) { return $null }
    return [pscustomobject]@{
        slot         = [int]$m.Groups['slot'].Value
        name_pid     = [int]$m.Groups['pid'].Value
        epoch        = [int]$m.Groups['epoch'].Value
        sidecar_name = $Name + '.who'
    }
}

# ---------------------------------------------------------------------------
# Unlink instrumentation — the ORDER is normative (§5.5), so it is observable.
# ---------------------------------------------------------------------------
$script:PcxUnlinkTrace = New-Object System.Collections.ArrayList
function Clear-PcxUnlinkTrace { $null = $script:PcxUnlinkTrace.Clear() }
function Get-PcxUnlinkTrace  { @($script:PcxUnlinkTrace.ToArray()) }
function Remove-PcxTracked {
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][ValidateSet('temp','sidecar')][string]$Kind)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
        $null = $script:PcxUnlinkTrace.Add($Kind)
        return $true
    }
    return $false
}

# ---------------------------------------------------------------------------
# §5.5 — ordered pair delete: temp FIRST, sidecar SECOND.
#
# Why the order is normative: a crash in the two-unlink gap under this order
# leaves a SIDECAR WITH NO TEMP, which the §5.5 predicate already reaches. The
# reverse order leaves a TEMP WITH NO SIDECAR that NO predicate reaches
# (bare-pid banned, age banned, the torn exception scoped to sidecars) — a
# permanent non-slot file on face D (OPr14-1).
# ---------------------------------------------------------------------------
function Remove-PcxPublicationPair {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][string]$SidecarName
    )
    $parsed = ConvertFrom-PcxSidecarName -Name $SidecarName
    if ($null -eq $parsed) { throw "pcx: '$SidecarName' is not a publication sidecar name" }

    $tempPath    = Join-Path $Root $parsed.temp_name
    $sidecarPath = Join-Path $Root $SidecarName

    if (Test-PcxMutation 'reverse-delete-order') {
        # MUTATION (OPr14-1): sidecar first. A crash in the gap orphans the temp.
        $null = Remove-PcxTracked -Path $sidecarPath -Kind 'sidecar'
        if (Test-PcxMutation 'fixture:crash-in-unlink-gap') { throw 'pcx-fixture: staged crash inside the two-unlink window' }
        $null = Remove-PcxTracked -Path $tempPath -Kind 'temp'
        return
    }

    # LAWFUL ORDER
    $null = Remove-PcxTracked -Path $tempPath -Kind 'temp'
    if (Test-PcxMutation 'fixture:crash-in-unlink-gap') { throw 'pcx-fixture: staged crash inside the two-unlink window' }
    $null = Remove-PcxTracked -Path $sidecarPath -Kind 'sidecar'
}

# ---------------------------------------------------------------------------
# The landing (§3.5 branch 9(v))
#   (1) sidecar by EXCLUSIVE-CREATE on its final name — no separate temp, so no
#       staging artifact can leak on a crash inside the landing;
#   (2) THEN the temp carrying the record;
#   (3) THEN the atomic Move temp -> slot_<n>.json;
#   (4) THEN the success-path pair delete (the Move consumed the temp; the
#       sidecar is deleted WITH it — §5.5's unit is the PAIR).
#
# -StopAfter stages the R-death cuts without killing a process: the function
# returns at the named cut leaving exactly the on-disk residue that cut leaves.
# ---------------------------------------------------------------------------
function Invoke-PcxPublication {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Root,
        [Parameter(Mandatory)][int]$Slot,
        [Parameter(Mandatory)][int]$Attempt,
        [Parameter(Mandatory)][int]$Epoch,             # E_promote (pre-pinned at R1)
        [Parameter(Mandatory)]$Record,                 # the slot record to publish
        $CreatorTriple = $null,                        # defaults to this process
        [ValidateSet('none','after-sidecar','after-temp','after-move')][string]$StopAfter = 'none'
    )

    if ($null -eq $CreatorTriple) {
        $self = Get-PcxSelfTriple
        if (-not $self.resolved) { throw 'pcx: cannot resolve own identity triple' }
        $CreatorTriple = $self.triple
    }

    $creatorPid  = [int]$CreatorTriple.pid
    $tempName    = Get-PcxTempName    -Slot $Slot -CreatorPid $creatorPid -Epoch $Epoch
    $sidecarName = Get-PcxSidecarName -Slot $Slot -CreatorPid $creatorPid -Epoch $Epoch
    $tempPath    = Join-Path $Root $tempName
    $sidecarPath = Join-Path $Root $sidecarName
    $slotPath    = Join-Path $Root (Get-PcxSlotRecordName -Slot $Slot)

    # ---- (1) the sidecar -----------------------------------------------------
    $sidecar = [pscustomobject]@{
        schema_version = 5
        kind           = 'pcx-publication-sidecar'
        creator        = [pscustomobject]@{
            name         = [string]$CreatorTriple.name
            pid          = $creatorPid
            creation_utc = (Normalize-IdentityTimestamp $CreatorTriple.creation_utc)
        }
        slot           = $Slot
        attempt        = $Attempt
        epoch          = $Epoch          # E_promote; the in-progress record sits at E_promote - 1
        created_at_utc = (Get-PcxUtcNow)
    }
    $sidecarJson = ConvertTo-PcxJson $sidecar

    if (Test-PcxMutation 'sidecar-temp-landing') {
        # MUTATION (CXr12-1): land the sidecar via temp+Move. The staging file
        # matches NO §5.5 predicate, so a crash at the intra-landing cut leaves
        # a permanent non-slot file.
        $stage = $sidecarPath + '.tmp'
        [System.IO.File]::WriteAllText($stage, $sidecarJson, [System.Text.UTF8Encoding]::new($false))
        if (Test-PcxMutation 'fixture:crash-intra-sidecar-landing') { return [pscustomobject]@{ stopped_at = 'intra-sidecar-landing'; sidecar = $sidecarPath; temp = $tempPath } }
        $null = Move-PcxFileAtomic -Source $stage -Destination $sidecarPath
    }
    else {
        $torn = (Test-PcxMutation 'fixture:crash-intra-sidecar-landing')
        $null = New-PcxFileExclusive -Path $sidecarPath -Content $sidecarJson -CrashBeforeContent:$torn
        if ($torn) {
            # Final NAME landed, triple did not: the torn case.
            return [pscustomobject]@{ stopped_at = 'intra-sidecar-landing'; sidecar = $sidecarPath; temp = $tempPath }
        }
    }
    if ($StopAfter -eq 'after-sidecar') {
        return [pscustomobject]@{ stopped_at = 'after-sidecar'; sidecar = $sidecarPath; temp = $tempPath }
    }

    # ---- (2) the temp --------------------------------------------------------
    [System.IO.File]::WriteAllText($tempPath, (ConvertTo-PcxJson $Record), [System.Text.UTF8Encoding]::new($false))
    if ($StopAfter -eq 'after-temp') {
        return [pscustomobject]@{ stopped_at = 'after-temp'; sidecar = $sidecarPath; temp = $tempPath }
    }

    # ---- (3) the atomic Move -------------------------------------------------
    $null = Move-PcxFileAtomic -Source $tempPath -Destination $slotPath
    if ($StopAfter -eq 'after-move') {
        return [pscustomobject]@{ stopped_at = 'after-move'; sidecar = $sidecarPath; temp = $tempPath; slot_record = $slotPath }
    }

    # ---- (4) success-path pair delete ---------------------------------------
    if (Test-PcxMutation 'unit-temps-only') {
        # MUTATION (CXr11-3 / OPr11-4): the unit is the temp alone. The Move
        # already consumed the temp, so this deletes nothing and EVERY success
        # leaves a permanent sidecar.
    }
    else {
        Remove-PcxPublicationPair -Root $Root -SidecarName $sidecarName
    }

    return [pscustomobject]@{ stopped_at = 'complete'; sidecar = $sidecarPath; temp = $tempPath; slot_record = $slotPath }
}

# Confirm-failure route (§3.5 branch 9(v)): W' terminated, slot stays REAPING,
# NOTHING killed — and the publication pair is retired through the SAME ordered
# delete.
function Undo-PcxPublicationAttempt {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][int]$Slot,
          [Parameter(Mandatory)][int]$CreatorPid, [Parameter(Mandatory)][int]$Epoch)
    Remove-PcxPublicationPair -Root $Root -SidecarName (Get-PcxSidecarName -Slot $Slot -CreatorPid $CreatorPid -Epoch $Epoch)
}
