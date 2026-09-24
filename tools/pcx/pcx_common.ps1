# pcx_common.ps1 — parallel-codex (pcx) phase-0 shared primitives
#
# SPEC OF RECORD: the parallel-codex proposal, r16 (in the private workspace)
#   sha256 7c9add1cc7113ce104700ca9b6a03238c24d1a7399fd3a7248dc413232a0ea5a
# Sections implemented here: §2.1 (registry layout), §3.0.1 (single timestamp
# source / Normalize-IdentityTimestamp), §3.0.3 (reader/mutator share modes).
#
# TARGET HOST: Windows PowerShell 5.1 (the host §3.0.1 was measured on).
#
# This file is dot-sourced by every other pcx script. §3.0.1 requires the
# normalization funnel to be "defined once in codex_slot.ps1 and DOT-SOURCED by
# the watchdog and dispatcher-loop scripts" — phase-0 has no codex_slot.ps1 yet
# (see PHASE0_BUILD_REPORT.md, flagged item F-2), so the funnel lives here and
# every pcx script dot-sources THIS file. The per-script leg of control I39 is
# asserted against this file's consumers.

Set-StrictMode -Version 2.0

# ---------------------------------------------------------------------------
# Win32 interop (atomic replace-move; §3.5 branch 9(v) "temp-write + atomic Move")
# ---------------------------------------------------------------------------
if (-not ('Pcx.Native' -as [type])) {
    Add-Type -Namespace 'Pcx' -Name 'Native' -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true, CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
public static extern bool MoveFileExW(string lpExistingFileName, string lpNewFileName, uint dwFlags);
'@
}
$script:PCX_MOVEFILE_REPLACE_EXISTING = [uint32]0x1
$script:PCX_MOVEFILE_WRITE_THROUGH    = [uint32]0x8

# ---------------------------------------------------------------------------
# Mutation registry — control apparatus ONLY (§5.1 "Mutation (must go RED)")
# ---------------------------------------------------------------------------
# Every named mutation below deliberately breaks ONE spec rule so a control can
# prove that rule is load-bearing. Production callers must never enable one.
# Control C-MUT-0 asserts (a) the default set is empty and (b) no non-test file
# calls Set-PcxMutation.
#
# Fixture injections (prefix "fixture:") are NOT rule breakages — they stage a
# crash at a named cut. They are kept in the same registry so one hygiene
# control covers both surfaces.

$script:PcxMutations = @{}
$script:PcxMutationTrace = New-Object System.Collections.ArrayList

$script:PcxKnownMutations = @(
    'delete-by-age'          # §5.5 "NEVER by age" — deletes on file age instead of the predicate
    'identity-bare-pid'      # §5.5 "NEVER the name's bare pid" — liveness by pid alone
    'unit-temps-only'        # r11's form — GC/success-path unit is the temp alone, not the PAIR
    'epoch-equality'         # OPr11-5 — compares sidecar epoch to record epoch by EQUALITY
    'sidecar-temp-landing'   # r12's form — lands the sidecar via temp+Move instead of CREATE_NEW
    'no-torn-exception'      # CXr13-1 - drops §5.5's torn-sidecar named exception
    'reverse-delete-order'   # OPr14-1 — deletes the SIDECAR first, temp second
)
$script:PcxKnownFixtures = @(
    'fixture:crash-in-unlink-gap'     # kill staged INSIDE the two-unlink window
    'fixture:crash-intra-sidecar-landing' # R dies mid-landing of the .who
)

function Set-PcxMutation {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Name)
    if ($script:PcxKnownMutations -notcontains $Name -and $script:PcxKnownFixtures -notcontains $Name) {
        throw "pcx: unknown mutation/fixture id '$Name'"
    }
    $script:PcxMutations[$Name] = $true
}

# Retire ONE entry — used to end a staged crash fixture: the crashed actor is
# gone, and the audit pass that follows is a DIFFERENT actor which must not
# inherit its injection.
function Remove-PcxMutation {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Name)
    if ($script:PcxMutations.ContainsKey($Name)) { $null = $script:PcxMutations.Remove($Name) }
}

function Clear-PcxMutations {
    $script:PcxMutations = @{}
    $null = $script:PcxMutationTrace.Clear()
}

function Get-PcxActiveMutations { @($script:PcxMutations.Keys | Sort-Object) }

function Test-PcxMutation {
    param([Parameter(Mandatory)][string]$Name)
    if ($script:PcxMutations.ContainsKey($Name)) {
        # Mutation-landed proof: the mutated BRANCH records that it executed.
        # A mutation that is merely "enabled" proves nothing (mutation-test
        # discipline); the trace is what a control asserts.
        $null = $script:PcxMutationTrace.Add($Name)
        return $true
    }
    return $false
}

function Get-PcxMutationTrace { @($script:PcxMutationTrace.ToArray()) }

# ---------------------------------------------------------------------------
# §3.0.1 — Normalize-IdentityTimestamp (THE funnel; both sides of every compare)
# ---------------------------------------------------------------------------
function Normalize-IdentityTimestamp {
    [CmdletBinding()]
    param([Parameter(Mandatory = $false, Position = 0)]$Value)

    if ($null -eq $Value) { return $null }
    if ($Value -is [datetime]) {
        return $Value.ToUniversalTime().ToString('o')
    }
    $s = [string]$Value
    if ([string]::IsNullOrWhiteSpace($s)) { return $null }
    # Full type names: [DateTimeStyles] does not resolve in PowerShell 5.1
    # (OPr4-18) — the implicit System. prefix does not reach System.Globalization.
    $dt = [datetime]::Parse(
        $s,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::RoundtripKind)
    return $dt.ToUniversalTime().ToString('o')
}

function Get-PcxUtcNow { (Get-Date).ToUniversalTime().ToString('o') }

# ---------------------------------------------------------------------------
# Identity triples — {name, pid, creation_utc}
# ---------------------------------------------------------------------------
function Get-PcxProcessTriple {
    [CmdletBinding()]
    param([Parameter(Mandatory)][int]$ProcessId)

    $p = $null
    try {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
    } catch {
        return [pscustomobject]@{ resolved = $false; query_failed = $true; triple = $null }
    }
    if ($null -eq $p) {
        return [pscustomobject]@{ resolved = $false; query_failed = $false; triple = $null }
    }
    # §3.0.1: CreationDate is used directly as the System.DateTime it is on this
    # host; ManagementDateTimeConverter is banned from every code path.
    $triple = [pscustomobject]@{
        name         = [string]$p.Name
        pid          = [int]$p.ProcessId
        creation_utc = (Normalize-IdentityTimestamp $p.CreationDate)
    }
    return [pscustomobject]@{ resolved = $true; query_failed = $false; triple = $triple }
}

function Get-PcxSelfTriple { Get-PcxProcessTriple -ProcessId $PID }

# Liveness of a RECORDED triple. Returns 'ALIVE' | 'DEAD' | 'UNKNOWN'.
#   UNKNOWN is the query-failure outcome and is treated by every §5.5 caller as
#   NOT-DEAD (preserve) — the safe direction. §5.5 licenses deletion only on a
#   positively DEAD creator.
function Test-PcxTripleLiveness {
    [CmdletBinding()]
    param([Parameter(Mandatory)]$Triple)

    if ($null -eq $Triple) { return 'UNKNOWN' }
    $recPid = $null
    try { $recPid = [int]$Triple.pid } catch { return 'UNKNOWN' }

    $live = Get-PcxProcessTriple -ProcessId $recPid
    if ($live.query_failed) { return 'UNKNOWN' }
    if (-not $live.resolved) { return 'DEAD' }

    if (Test-PcxMutation 'identity-bare-pid') {
        # MUTATION (§5.5 "NEVER the name's bare pid"): the pid resolving to ANY
        # process reads ALIVE. A recycled pid then preserves a dead creator's
        # pair forever.
        return 'ALIVE'
    }

    $recName = $null; $recCreation = $null
    try { $recName = [string]$Triple.name } catch { $recName = $null }
    try { $recCreation = Normalize-IdentityTimestamp $Triple.creation_utc } catch { return 'UNKNOWN' }
    if ([string]::IsNullOrWhiteSpace($recName) -or $null -eq $recCreation) { return 'UNKNOWN' }

    # Both sides through the SAME funnel (§3.0.1).
    if (($live.triple.name -eq $recName) -and ($live.triple.creation_utc -eq $recCreation)) {
        return 'ALIVE'
    }
    return 'DEAD'   # pid recycled to a different process — the recorded triple is dead
}

function Test-PcxTripleEqual {
    param($A, $B)
    if ($null -eq $A -or $null -eq $B) { return $false }
    try {
        return (([string]$A.name -eq [string]$B.name) -and
                ([int]$A.pid -eq [int]$B.pid) -and
                ((Normalize-IdentityTimestamp $A.creation_utc) -eq (Normalize-IdentityTimestamp $B.creation_utc)))
    } catch { return $false }
}

# ---------------------------------------------------------------------------
# §2.1 — registry root + layout
# ---------------------------------------------------------------------------
# Root naming is the principal's call (§6 Q5, OPEN). The §2.1 default is used unless
# PCX_REGISTRY_ROOT is set. Controls ALWAYS set it to a scratch dir; nothing in
# phase-0 writes to the real root.
function Get-PcxRegistryRoot {
    if ($env:PCX_REGISTRY_ROOT) { return $env:PCX_REGISTRY_ROOT }
    return (Join-Path $env:USERPROFILE '.fleet\codex_slots')
}

$script:PcxLayoutDirs = @(
    'tombstones', 'seat_tokens', 'seat_queue', 'COOLDOWN_SUSPECT.d',
    'runs', 'displaced', 'reaped', 'ledger.d', 'escalations'
)

function New-PcxRegistryLayout {
    [CmdletBinding()]
    param([string]$Root = (Get-PcxRegistryRoot))
    if (-not (Test-Path -LiteralPath $Root)) { $null = New-Item -ItemType Directory -Path $Root -Force }
    foreach ($d in $script:PcxLayoutDirs) {
        $p = Join-Path $Root $d
        if (-not (Test-Path -LiteralPath $p)) { $null = New-Item -ItemType Directory -Path $p -Force }
    }
    return $Root
}

# ---------------------------------------------------------------------------
# File primitives (§3.0.3 share modes)
# ---------------------------------------------------------------------------

# Reader: Read + FileShare.ReadWrite|Delete — never blocks a mutator or a mover.
function Read-PcxFileText {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)
    $share = ([System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete)
    $fs = $null
    $sr = $null
    try {
        $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, $share)
        $sr = New-Object System.IO.StreamReader($fs, [System.Text.UTF8Encoding]::new($false), $true)
        return $sr.ReadToEnd()
    } finally {
        if ($sr) { $sr.Dispose() } elseif ($fs) { $fs.Dispose() }
    }
}

# Returns [pscustomobject] on success, $null when absent / unreadable / unparseable.
function Read-PcxJson {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $txt = $null
    try { $txt = Read-PcxFileText -Path $Path } catch { return $null }
    if ($null -eq $txt) { return $null }
    # A NUL-padded-complete write reads unparseable though its parseable twin
    # would be preserved (§5.5's torn case, explicitly named).
    try { return ($txt | ConvertFrom-Json) } catch { return $null }
}

# Exclusive create (O_EXCL / CREATE_NEW). Throws if the name already exists —
# "a name collision means a prior lawful sidecar already landed and is deferred
# to" (§3.5 branch 9(v)).
function New-PcxFileExclusive {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content,
        [switch]$CrashBeforeContent    # fixture hook: torn triple-less landing
    )
    $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew,
                                 [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    try {
        if ($CrashBeforeContent) {
            # The final NAME has landed; the content/triple has not. This is the
            # intra-landing cut §5.5's torn-sidecar exception exists for.
            return $false
        }
        $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Content)
        $fs.Write($bytes, 0, $bytes.Length)
        $fs.Flush($true)
        return $true
    } finally { $fs.Dispose() }
}

function Move-PcxFileAtomic {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Source, [Parameter(Mandatory)][string]$Destination)
    $flags = ($script:PCX_MOVEFILE_REPLACE_EXISTING -bor $script:PCX_MOVEFILE_WRITE_THROUGH)
    $ok = [Pcx.Native]::MoveFileExW($Source, $Destination, $flags)
    if (-not $ok) {
        $err = [System.Runtime.InteropServices.Marshal]::GetLastWin32Error()
        throw "pcx: MoveFileExW failed ($Source -> $Destination), win32 error $err"
    }
    return $true
}

function ConvertTo-PcxJson {
    param([Parameter(Mandatory)]$Object)
    return ($Object | ConvertTo-Json -Depth 12)
}
