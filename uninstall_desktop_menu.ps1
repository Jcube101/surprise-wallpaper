#Requires -Version 5.1
<#
.SYNOPSIS
  Remove Grok wallpaper items from the desktop background context menu.
#>

$ErrorActionPreference = "Continue"
$names = @(
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
)

foreach ($name in $names) {
    $path = "HKCU:\Software\Classes\DesktopBackground\Shell\$name"
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force
        Write-Host "Removed: $name"
    }
    else {
        Write-Host "Not found (ok): $name"
    }
}

Write-Host "Done."
