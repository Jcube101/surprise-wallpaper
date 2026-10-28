#Requires -Version 5.1
<#
.SYNOPSIS
  Add a Wallpaper section to the desktop background context menu.

.DESCRIPTION
  Registers under HKCU:\Software\Classes\DesktopBackground\Shell\
  (right-click empty desktop background — not on an icon).

  Windows 11's compact menu does not expand registry flyouts, so these are
  five top-level items grouped with separators (one visual section):

    - Reject today (NASA APOD)   → wallpaper reject
    - New Grok wallpaper         → wallpaper new --force
    - Previous Grok wallpaper    → wallpaper prev
    - Read about this wallpaper  → wallpaper about --dialog
    - Next Grok wallpaper        → wallpaper next

  Prefers the `wallpaper` console script from a venv (pip install -e .),
  else falls back to: python wallpaper.py <cmd>
  "Read about" launches pythonw.exe with absolute paths (no cmd.exe —
  that wrapper was the empty console behind the card).

.PARAMETER PythonPath
  Full path to python.exe. Default: project .venv, else `python` on PATH.

.PARAMETER ProjectRoot
  Project folder. Default: this script's directory.

.EXAMPLE
  pip install -e .
  .\install_desktop_menu.ps1
  .\install_desktop_menu.ps1 -PythonPath "$PWD\.venv\Scripts\python.exe"
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
$WallpaperPy = Join-Path $ProjectRoot "wallpaper.py"

if (-not (Test-Path $WallpaperPy)) {
    Write-Error "wallpaper.py not found at $WallpaperPy"
}

if (-not $PythonPath) {
    $venvPy = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        $PythonPath = $venvPy
    }
    else {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if (-not $cmd) {
            Write-Error "python not found. Pass -PythonPath 'C:\...\python.exe'"
        }
        $PythonPath = $cmd.Source
    }
}

if (-not (Test-Path $PythonPath)) {
    Write-Error "Python not found: $PythonPath"
}

$scriptsDir = Split-Path -Parent $PythonPath
$wallpaperExe = Join-Path $scriptsDir "wallpaper.exe"
$pythonwExe = Join-Path $scriptsDir "pythonw.exe"
$useConsoleScript = Test-Path $wallpaperExe
$usePythonw = Test-Path $pythonwExe

function Get-WallpaperCommandLine {
    param(
        [string]$Subcommand,
        [switch]$NoConsole
    )
    # Avoid nested quote breakage: cmd /c cd /d "path" && "exe" args
    if ($NoConsole) {
        # Do not wrap pythonw in cmd.exe — cmd is a visible empty console
        # that stays open until the about card is dismissed.
        $exe = if ($usePythonw) { $pythonwExe } else { $PythonPath }
        return "`"$exe`" `"$WallpaperPy`" $Subcommand"
    }
    if ($useConsoleScript) {
        return "cmd.exe /c cd /d `"$ProjectRoot`" && `"$wallpaperExe`" $Subcommand"
    }
    return "cmd.exe /c cd /d `"$ProjectRoot`" && `"$PythonPath`" wallpaper.py $Subcommand"
}

function Remove-DesktopVerb {
    param([string]$KeyName)
    $path = "HKCU:\Software\Classes\DesktopBackground\Shell\$KeyName"
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force
    }
}

# Remove cascade parent + any prior verb names so we don't leave a dead flyout.
@(
    "GrokWallpaper",
    "GrokWallpaperNew",
    "GrokWallpaperReject",
    "GrokWallpaperNext",
    "GrokWallpaperPrev",
    "GrokWallpaperAbout",
    "GrokWallpaper01Reject",
    "GrokWallpaper02New",
    "GrokWallpaper03Prev",
    "GrokWallpaper04About",
    "GrokWallpaper05Next"
) | ForEach-Object { Remove-DesktopVerb $_ }

function Register-DesktopVerb {
    param(
        [string]$KeyName,
        [string]$MenuLabel,
        [string]$Subcommand,
        [string]$Icon = "imageres.dll,67",
        [switch]$NoConsole,
        [switch]$SeparatorBefore,
        [switch]$SeparatorAfter
    )
    $base = "HKCU:\Software\Classes\DesktopBackground\Shell\$KeyName"
    New-Item -Path $base -Force | Out-Null
    New-ItemProperty -Path $base -Name "(Default)" -Value $MenuLabel -Force | Out-Null
    New-ItemProperty -Path $base -Name "MUIVerb" -Value $MenuLabel -Force | Out-Null
    # All Top so they sit together (not split across the menu).
    New-ItemProperty -Path $base -Name "Position" -Value "Top" -Force | Out-Null
    New-ItemProperty -Path $base -Name "Icon" -Value $Icon -Force | Out-Null
    if ($SeparatorBefore) {
        New-ItemProperty -Path $base -Name "SeparatorBefore" -Value "" -Force | Out-Null
    }
    if ($SeparatorAfter) {
        New-ItemProperty -Path $base -Name "SeparatorAfter" -Value "" -Force | Out-Null
    }

    $cmdKey = Join-Path $base "command"
    New-Item -Path $cmdKey -Force | Out-Null
    $cmdLine = Get-WallpaperCommandLine -Subcommand $Subcommand -NoConsole:$NoConsole
    Set-ItemProperty -Path $cmdKey -Name "(Default)" -Value $cmdLine

    $via = if ($NoConsole -and $usePythonw) {
        "pythonw wallpaper.py"
    }
    elseif ($useConsoleScript -and -not $NoConsole) {
        "wallpaper.exe"
    }
    else {
        "python wallpaper.py"
    }
    Write-Host "Registered: $MenuLabel -> $via $Subcommand"
}

# Numbered key names keep the five items adjacent and in this order.
Register-DesktopVerb -KeyName "GrokWallpaper01Reject" `
    -MenuLabel "Reject today (NASA APOD)" `
    -Subcommand "reject" `
    -Icon "imageres.dll,84" `
    -SeparatorBefore

Register-DesktopVerb -KeyName "GrokWallpaper02New" `
    -MenuLabel "New Grok wallpaper" `
    -Subcommand "new --force" `
    -Icon "imageres.dll,109"

Register-DesktopVerb -KeyName "GrokWallpaper03Prev" `
    -MenuLabel "Previous Grok wallpaper" `
    -Subcommand "prev"

Register-DesktopVerb -KeyName "GrokWallpaper04About" `
    -MenuLabel "Read about this wallpaper" `
    -Subcommand "about --dialog" `
    -Icon "imageres.dll,76" `
    -NoConsole

Register-DesktopVerb -KeyName "GrokWallpaper05Next" `
    -MenuLabel "Next Grok wallpaper" `
    -Subcommand "next" `
    -SeparatorAfter

Write-Host ""
Write-Host "Project : $ProjectRoot"
Write-Host "Python  : $PythonPath"
if ($useConsoleScript) {
    Write-Host "CLI     : $wallpaperExe  (console script)"
}
else {
    Write-Host "CLI     : python wallpaper.py  (tip: pip install -e . for 'wallpaper' on PATH)"
}
Write-Host ""
Write-Host "Right-click the DESKTOP BACKGROUND (empty area, not an icon)."
Write-Host "Wallpaper section (grouped at the top):"
Write-Host "  Reject today (NASA APOD)"
Write-Host "  New Grok wallpaper"
Write-Host "  Previous Grok wallpaper"
Write-Host "  Read about this wallpaper"
Write-Host "  Next Grok wallpaper"
Write-Host ""
Write-Host "Note: New may take 30-90s and uses xAI (costs apply)."
Write-Host "If missing: restart Explorer (Task Manager > Windows Explorer > Restart)."
Write-Host "Remove:     .\uninstall_desktop_menu.ps1"
