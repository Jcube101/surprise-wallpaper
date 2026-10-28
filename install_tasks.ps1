#Requires -Version 5.1
<#
.SYNOPSIS
  Register Windows Task Scheduler jobs for Grok Surprise Wallpaper Rotator.

.DESCRIPTION
  Creates two tasks (idempotent — re-run overwrites the same names):

    1. GrokWallpaper-DailyMidnight
       Triggers daily at 00:00 (machine local time).
       Runs run_daily_generate.py → create today's themed wallpaper if
       missing (GTM / literary / painting), track xAI cost, set desktop.
       Requires XAI_API_KEY in project .env for generation.

    2. GrokWallpaper-LogonUnlock
       Triggers at user logon AND on workstation unlock.
       run_rotator.py only SETs (skips if already set today).

    3. GrokWallpaper-ClearOverlay
       Every minute while logged on, plus at logon.
       run_clear_overlay.py hides a fullscreen Windows Input Experience
       window. It does not change the wallpaper. That window is a Windows
       bug: it paints nothing and eats clicks, so the desktop looks blank.

  Both run whether the user is logged on or not is NOT required —
  we use Interactive token so the wallpaper API applies to the desktop.

.PARAMETER PythonPath
  Full path to python.exe. Default: whatever `python` resolves to on PATH.

.PARAMETER ProjectRoot
  Project folder containing run_rotator.py. Default: this script's directory.

.EXAMPLE
  .\install_tasks.ps1
  .\install_tasks.ps1 -PythonPath "C:\Users\you\AppData\Local\Programs\Python\Python312\python.exe"
#>

param(
    [string]$PythonPath = "",
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) {
    $ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$ProjectRoot = (Resolve-Path $ProjectRoot).Path
$RunnerSet = Join-Path $ProjectRoot "run_rotator.py"
$RunnerGen = Join-Path $ProjectRoot "run_daily_generate.py"

if (-not (Test-Path $RunnerSet)) {
    Write-Error "run_rotator.py not found at $RunnerSet"
}
if (-not (Test-Path $RunnerGen)) {
    Write-Error "run_daily_generate.py not found at $RunnerGen"
}

if (-not $PythonPath) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Error "python not on PATH. Pass -PythonPath 'C:\...\python.exe'"
    }
    $PythonPath = $cmd.Source
}

if (-not (Test-Path $PythonPath)) {
    Write-Error "Python not found: $PythonPath"
}

# python.exe is a console program. A once-a-minute task using it flashes a
# terminal. pythonw.exe is the same interpreter with no console window.
$PythonWPath = Join-Path (Split-Path -Parent $PythonPath) "pythonw.exe"
if (-not (Test-Path $PythonWPath)) {
    Write-Error "pythonw.exe not found next to $PythonPath. The overlay guard needs it so no console flashes."
}

Write-Host "Project : $ProjectRoot"
Write-Host "Python  : $PythonPath"
Write-Host "Midnight: $RunnerGen"
Write-Host "Logon   : $RunnerSet"
Write-Host ""

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 25) `
    -MultipleInstances IgnoreNew

# Run as current user, only when logged on (needed for desktop wallpaper)
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

# --- Task 1: daily midnight GENERATE (local clock ≈ IST if TZ is India) ---
$actionGen = New-ScheduledTaskAction `
    -Execute $PythonWPath `
    -Argument "`"$RunnerGen`"" `
    -WorkingDirectory $ProjectRoot

$dailyTrigger = New-ScheduledTaskTrigger -Daily -At "00:00"

Register-ScheduledTask `
    -TaskName "GrokWallpaper-DailyMidnight" `
    -Action $actionGen `
    -Trigger $dailyTrigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Grok wallpaper: GENERATE today's theme at midnight (GTM/literary/painting) + set; costs logged." `
    -Force | Out-Null

Write-Host "Registered: GrokWallpaper-DailyMidnight (00:00 generate+set)"

# --- Task 2: logon + unlock SET only ---
$actionSet = New-ScheduledTaskAction `
    -Execute $PythonWPath `
    -Argument "`"$RunnerSet`"" `
    -WorkingDirectory $ProjectRoot

$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

Register-ScheduledTask `
    -TaskName "GrokWallpaper-LogonUnlock" `
    -Action $actionSet `
    -Trigger $logonTrigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Grok wallpaper: at logon/unlock SET only; skips if already set today." `
    -Force | Out-Null

# Add SessionStateChange (unlock) trigger via task XML
try {
    $task = Get-ScheduledTask -TaskName "GrokWallpaper-LogonUnlock"
    $xml = Export-ScheduledTask -TaskName "GrokWallpaper-LogonUnlock"

    # SessionStateChangeTrigger: StateChange 8 = SESSION_UNLOCK
    $unlockTrigger = @"
  <SessionStateChangeTrigger>
    <Enabled>true</Enabled>
    <StateChange>SessionUnlock</StateChange>
    <UserId>$($env:USERDOMAIN)\$($env:USERNAME)</UserId>
  </SessionStateChangeTrigger>
"@

    if ($xml -notmatch "SessionStateChangeTrigger") {
        # Insert before </Triggers>
        $xml = $xml -replace "</Triggers>", "$unlockTrigger`r`n  </Triggers>"
        Register-ScheduledTask -TaskName "GrokWallpaper-LogonUnlock" -Xml $xml -Force | Out-Null
        Write-Host "Registered: GrokWallpaper-LogonUnlock (At log on + Session unlock)"
    }
    else {
        Write-Host "Registered: GrokWallpaper-LogonUnlock (triggers already present)"
    }
}
catch {
    Write-Warning "Logon task created, but unlock trigger patch failed: $_"
    Write-Warning "You can add 'On workstation unlock' manually in Task Scheduler."
}

# --- Task 3: keep a blank Input Experience window from sticking ---
# Windows can open this window at any time (often just after a wallpaper
# change). Hiding it on set/unlock is not enough if the session stays open.
$RunnerGuard = Join-Path $ProjectRoot "run_clear_overlay.py"
if (-not (Test-Path $RunnerGuard)) {
    Write-Error "run_clear_overlay.py not found at $RunnerGuard"
}

$guardSettings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

$actionGuard = New-ScheduledTaskAction `
    -Execute $PythonWPath `
    -Argument "`"$RunnerGuard`"" `
    -WorkingDirectory $ProjectRoot

# Once-per-minute for a long span. Task Scheduler's repetition cap is finite;
# 9999 days is the practical "while this PC is in use" window.
$guardRepeat = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes 1) `
    -RepetitionDuration (New-TimeSpan -Days 9999)
$guardLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

Register-ScheduledTask `
    -TaskName "GrokWallpaper-ClearOverlay" `
    -Action $actionGuard `
    -Trigger @($guardRepeat, $guardLogon) `
    -Settings $guardSettings `
    -Principal $principal `
    -Description "Grok wallpaper: once a minute, hide a fullscreen Windows Input Experience window that blanks the desktop. Does not change the wallpaper." `
    -Force | Out-Null

Write-Host "Registered: GrokWallpaper-ClearOverlay (every 1 min + at log on)"

Write-Host ""
Write-Host "Done. Test with:"
Write-Host "  python `"$RunnerGen`""
Write-Host "  python `"$ProjectRoot\wallpaper.py`" --new"
Write-Host "  python `"$ProjectRoot\wallpaper.py`" status"
Write-Host ""
Write-Host "View tasks: taskschd.msc  →  Task Scheduler Library"
Write-Host "Remove:     .\uninstall_tasks.ps1"

