# scripts/register_tasks.ps1
# Registers the GovJob workers as Windows Scheduled Tasks so job/admit-card
# updates keep flowing without anyone opening a terminal.
#
# Run elevated (Administrator):
#   powershell -ExecutionPolicy Bypass -File scripts\register_tasks.ps1
# Preview without writing:
#   powershell -ExecutionPolicy Bypass -File scripts\register_tasks.ps1 -WhatIf
# Remove both tasks:
#   powershell -ExecutionPolicy Bypass -File scripts\register_tasks.ps1 -Unregister
#
# Creates:
#   GovJob-Poller   - Layer-1 discovery loop (polls sources every N sec),
#                     starts at logon, restarts on failure, runs as SYSTEM
#   GovJob-Layer2   - Layer-2 LLM extraction + publish gate, every 15 min
#
# Prereqs: backend\venv312 exists and `alembic upgrade head` already applied.
# Logs:    poller -> logs\poller.log, layer2 -> logs\layer2.log

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
    throw "Python not found at $Python - create the venv first (python -m venv backend\venv312; pip install -r requirements.txt)"
}

$tasks = @(
    @{
        Name = "GovJob-Poller"
        Args = "-m app.services.layer1_poller --loop"
        Trigger = New-ScheduledTaskTrigger -AtLogOn
        Description = "GovJob Layer-1 poller: hash-gated polling of official notification sources"
    },
    @{
        Name = "GovJob-Layer2"
        Args = "-m app.services.layer2_worker --max-docs 10"
        Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
            | ForEach-Object {
                $t = $_
                $t.Repetition = (New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -Once -At (Get-Date)).Repetition
                $t
            }
        Description = "GovJob Layer-2 worker: PDF download, LLM extraction, publish gate (jobs + admit cards)"
    }
)

foreach ($t in $tasks) {
    if ($Unregister) {
        if ($WhatIf) { Write-Host "[WhatIf] would unregister $($t.Name)"; continue }
        Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "unregistered $($t.Name)"
        continue
    }

    $action = New-ScheduledTaskAction `
        -Execute $Python `
        -Argument $t.Args `
        -WorkingDirectory $Backend `
        -RedirectStandardOutput (Join-Path $LogDir ($t.Name -replace 'GovJob-', '').ToLower() + ".log") `
        -RedirectStandardError (Join-Path $LogDir ($t.Name -replace 'GovJob-', '').ToLower() + ".err")

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 2) `
        -MultipleInstances IgnoreNew `
        -StartWhenAvailable

    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

    if ($WhatIf) { Write-Host "[WhatIf] would register $($t.Name): $Python $($t.Args) in $Backend"; continue }

    Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $t.Trigger -Settings $settings -Principal $principal -Description $t.Description | Out-Null
    Write-Host "registered $($t.Name)"
}

if (-not $Unregister -and -not $WhatIf) {
    Write-Host ""
    Write-Host "Done. Start them now:"
    Write-Host "  Start-ScheduledTask -TaskName GovJob-Poller"
    Write-Host "  Start-ScheduledTask -TaskName GovJob-Layer2"
    Write-Host ""
    Write-Host "Logs: $LogDir"
    Write-Host "Verify: schtasks /query /tn GovJob-Layer2 /v | findstr Status"
}
