# scripts/register_tasks.ps1
# Registers the GovJob workers as Windows Scheduled Tasks so job/admit-card
# updates keep running without anyone opening a terminal. Uses schtasks.exe
# (works unelevated for per-user tasks; PowerShell's Register-ScheduledTask
# can be denied by policy on some machines).
#
#   powershell -ExecutionPolicy Bypass -File scripts\register_tasks.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\register_tasks.ps1 -Unregister
#
# Creates:
#   GovJob-Poller   - Layer 1 discovery loop (starts at logon, restarts itself)
#   GovJob-Layer2   - Layer 2 extraction + publish gate, every 15 min, ALL sources drained
# Both write to logs\poller.log and logs\layer2.log.
# Prereq: backend\venv312 exists and `alembic upgrade head` already applied.

param(
    [switch]$Unregister,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $RepoRoot "backend"
$Python = Join-Path $Backend "venv312\Scripts\python.exe"
$LogDir = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if (-not (Test-Path $Python)) {
    throw "Python not found at $Python - create the venv first"
}

$tasks = @(
    @{
        Name = "GovJob-Poller"
        Frequency = "MINUTE"
        Modifier = 1
        Command = 'cmd /c cd /d "{0}" && "{1}" -m app.services.layer1_poller --once >> "{2}" 2>&1' -f $Backend, $Python, (Join-Path $LogDir "poller.log")
    },
    @{
        Name = "GovJob-Layer2"
        Frequency = "MINUTE"
        Modifier = 15
        Command = 'cmd /c cd /d "{0}" && "{1}" -m app.services.layer2_worker --all-sources --drain --max-docs 50 >> "{2}" 2>&1' -f $Backend, $Python, (Join-Path $LogDir "layer2.log")
    }
)

foreach ($t in $tasks) {
    if ($WhatIf) {
        Write-Host "[WhatIf] would $(if ($Unregister) {'delete'} else {'create'}) task $($t.Name)"
        continue
    }
    if ($Unregister) {
        schtasks /Delete /TN $t.Name /F 2>$null | Out-Null
        Write-Host "deleted $($t.Name)"
        continue
    }
    $schtaskArgs = @("/Create", "/TN", $t.Name, "/TR", $t.Command, "/SC", $t.Frequency)
    if ($t.Modifier) { $schtaskArgs += @("/MO", $t.Modifier) }
    $schtaskArgs += "/F"
    $result = & schtasks @schtaskArgs 2>&1
    if ($LASTEXITCODE -ne 0) { throw "failed to create $($t.Name): $result" }
    Write-Host "registered $($t.Name)"
}

if (-not $Unregister -and -not $WhatIf) {
    Write-Host ""
    Write-Host "Start now: schtasks /Run /TN GovJob-Poller ; schtasks /Run /TN GovJob-Layer2"
    Write-Host "Verify:    schtasks /Query /TN GovJob-Layer2 /V /FO LIST"
    Write-Host "Logs:      $LogDir"
}
