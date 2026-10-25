$ErrorActionPreference = "Stop"

$AppDir = "C:\Signal-Lab\System\Signal_Lab_Shadow"
$Runner = Join-Path $AppDir "RUN_DAILY_SHADOW_V6.bat"
$TaskName = "Signal Lab Daily Shadow v6.6"

@("Signal Lab Daily Shadow v6.1", "Signal Lab Daily Shadow v6.2", "Signal Lab Daily Shadow v6.3", "Signal Lab Daily Shadow v6.4", "Signal Lab Daily Shadow v6.5") | ForEach-Object {
    if (Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $_ -Confirm:$false
    }
}

if (-not (Test-Path -LiteralPath $Runner)) {
    throw "Daily Shadow runner is missing: $Runner"
}

$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$Runner`""
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Minutes 30)
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger `
    -Settings $Settings -Principal $Principal -Force | Out-Null

Write-Host "Automatic Daily Shadow task installed: $TaskName"
