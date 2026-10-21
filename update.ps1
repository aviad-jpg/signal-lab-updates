$ErrorActionPreference = "Stop"

$AppDir = "C:\Signal-Lab\System\Signal_Lab_Shadow"
$ChannelRoot = "https://raw.githubusercontent.com/aviad-jpg/signal-lab-updates/main"
$ManifestUrl = "$ChannelRoot/version.json"
$TempDir = Join-Path $env:TEMP ("signal-lab-update-" + [guid]::NewGuid().ToString("N"))
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupDir = Join-Path $AppDir ("backups\" + $Stamp)

New-Item -ItemType Directory -Force -Path $AppDir, $TempDir, $BackupDir | Out-Null

try {
    Write-Host "Checking Signal Lab updates..."
    $ManifestPath = Join-Path $TempDir "version.json"
    Invoke-WebRequest -UseBasicParsing -Uri $ManifestUrl -OutFile $ManifestPath
    $Manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json

    foreach ($File in $Manifest.files) {
        $RelativePath = [string]$File.path
        if ($RelativePath.Contains("..") -or [System.IO.Path]::IsPathRooted($RelativePath)) {
            throw "Unsafe update path: $RelativePath"
        }

        $DownloadPath = Join-Path $TempDir $RelativePath
        $Destination = Join-Path $AppDir $RelativePath
        $DownloadParent = Split-Path -Parent $DownloadPath
        $DestinationParent = Split-Path -Parent $Destination
        New-Item -ItemType Directory -Force -Path $DownloadParent, $DestinationParent | Out-Null

        $FileUrl = "$ChannelRoot/releases/$($Manifest.version)/$RelativePath"
        Invoke-WebRequest -UseBasicParsing -Uri $FileUrl -OutFile $DownloadPath
        $ActualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $DownloadPath).Hash.ToLowerInvariant()
        if ($ActualHash -ne ([string]$File.sha256).ToLowerInvariant()) {
            throw "Integrity check failed for $RelativePath"
        }
    }

    foreach ($File in $Manifest.files) {
        $RelativePath = [string]$File.path
        $DownloadPath = Join-Path $TempDir $RelativePath
        $Destination = Join-Path $AppDir $RelativePath
        if (Test-Path -LiteralPath $Destination) {
            $BackupPath = Join-Path $BackupDir $RelativePath
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $BackupPath) | Out-Null
            Copy-Item -LiteralPath $Destination -Destination $BackupPath -Force
        }
        Copy-Item -LiteralPath $DownloadPath -Destination $Destination -Force
    }

    Set-Content -LiteralPath (Join-Path $AppDir "installed_version.txt") -Value $Manifest.version -Encoding ASCII
    $Runner = Join-Path $AppDir "RUN_BACKTEST_V6.bat"
    if (Test-Path -LiteralPath $Runner) {
        $Shell = New-Object -ComObject WScript.Shell
        $Shortcut = $Shell.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), "Signal Lab Backtest v6.lnk"))
        $Shortcut.TargetPath = $Runner
        $Shortcut.WorkingDirectory = $AppDir
        $Shortcut.Save()
    }
    $Collector = Join-Path $AppDir "COLLECT_SHADOW_RESULTS.bat"
    if (Test-Path -LiteralPath $Collector) {
        $Shell = New-Object -ComObject WScript.Shell
        $Shortcut = $Shell.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath("Desktop"), "Signal Lab Shadow Results.lnk"))
        $Shortcut.TargetPath = $Collector
        $Shortcut.WorkingDirectory = $AppDir
        $Shortcut.Save()
    }
    $DailyShadowInstaller = Join-Path $AppDir "install_daily_shadow.ps1"
    if (Test-Path -LiteralPath $DailyShadowInstaller) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $DailyShadowInstaller
        if ($LASTEXITCODE -ne 0) {
            throw "Could not install the automatic Daily Shadow task."
        }
    }
    Write-Host "Signal Lab updated successfully to version $($Manifest.version)."
    Write-Host "Backup: $BackupDir"
}
finally {
    Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}
