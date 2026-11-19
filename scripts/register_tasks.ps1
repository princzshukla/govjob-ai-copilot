# scripts/register_tasks.ps1
# Registers hidden GovJob workers as Windows Scheduled Tasks.
#
#   powershell -ExecutionPolicy Bypass -File scripts\register_tasks.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\register_tasks.ps1 -Unregister
#
# Execution method: pythonw.exe runs scripts\run_worker.py with NO console and
# NO cmd.exe. The launcher redirects stdout/stderr to logs\*.log, captures
# uncaught Python exceptions with tracebacks, chdir's to backend, and holds an
# OS-level lock so two workers can never overlap. Task Scheduler itself uses
# MultipleInstancesPolicy=IgnoreNew as a second layer of protection.
#
# Schedules: Poller every 1 minute; Layer 2 every 15 minutes;
# Jobs Watchdog daily at 03:30 (independent from the admit-card watchdog).

param(
    [switch]$Unregister,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PythonW = Join-Path $RepoRoot "backend\venv312\Scripts\pythonw.exe"
$Launcher = Join-Path $RepoRoot "scripts\run_worker.py"
$LogDir = Join-Path $RepoRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

if (-not (Test-Path $PythonW)) { throw "pythonw.exe not found: $PythonW" }
if (-not (Test-Path $Launcher)) { throw "launcher not found: $Launcher" }

$tasks = @(
    @{ Name = "GovJob-Poller"; Frequency = "MINUTE"; Modifier = 1; Args = "--worker poller" },
    @{ Name = "GovJob-Layer2"; Frequency = "MINUTE"; Modifier = 15; Args = "--worker layer2" },
    @{ Name = "GovJob-JobsWatchdog"; Frequency = "DAILY"; Modifier = 1; StartTime = "03:30"; Args = "--worker jobswatchdog" }
)

foreach ($t in $tasks) {
    if ($WhatIf) {
        Write-Host "[WhatIf] would $(if ($Unregister) {'delete'} else {'create'}) $($t.Name)"
        continue
    }
    if ($Unregister) {
        schtasks /Delete /TN $t.Name /F 2>$null | Out-Null
        Write-Host "deleted $($t.Name)"
        continue
    }

    # Quoted /TR: pythonw.exe with the hidden launcher; no cmd.exe at all.
    $command = '"{0}" "{1}" {2}' -f $PythonW, $Launcher, $t.Args
    $schtaskArgs = @("/Create", "/TN", $t.Name, "/TR", $command, "/SC", $t.Frequency, "/MO", $t.Modifier, "/F")
    if ($t.StartTime) { $schtaskArgs += @("/ST", $t.StartTime) }
    $result = & schtasks @schtaskArgs 2>&1
    if ($LASTEXITCODE -ne 0) { throw "failed to create $($t.Name): $result" }
    Write-Host "registered $($t.Name)  ->  pythonw.exe (hidden), $($t.Args)"
}

if (-not $Unregister -and -not $WhatIf) {
    # Harden settings (no battery blocks, IgnoreNew, start-if-missed).
    $py = Join-Path $RepoRoot "backend/venv312/Scripts/python.exe"
    $hardener = Join-Path $PSScriptRoot "harden_tasks.py"
    & $py $hardener
    Write-Host ""
    Write-Host "Logs: $LogDir\poller.log, $LogDir\layer2.log and $LogDir\jobs_watchdog.log"
    Write-Host "Run now: schtasks /Run /TN GovJob-Poller ; schtasks /Run /TN GovJob-Layer2 ; schtasks /Run /TN GovJob-JobsWatchdog"
}
