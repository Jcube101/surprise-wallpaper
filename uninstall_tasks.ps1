#Requires -Version 5.1
<#
.SYNOPSIS
  Remove Grok Surprise Wallpaper scheduled tasks.
#>

$ErrorActionPreference = "Continue"
$names = @(
    "GrokWallpaper-DailyMidnight",
    "GrokWallpaper-LogonUnlock",
    "GrokWallpaper-ClearOverlay"
)

foreach ($name in $names) {
    $existing = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Host "Removed: $name"
    }
    else {
        Write-Host "Not found (ok): $name"
    }
}

Write-Host "Done."
