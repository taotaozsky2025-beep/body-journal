$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$status=Get-Content (Join-Path $root 'last-success.json') -Raw | ConvertFrom-Json
if(!$status.Success -or $status.Model -ne 'bairen.scales.hd01s' -or !(Test-Path (Join-Path $root 'weights.csv'))){throw 'A successful real export is required before scheduling.'}
$name='SmartScaleConnect-HD01S'
$existing=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
if($existing -and $existing.Actions.Arguments -notmatch [regex]::Escape($root)){throw 'A task with this name belongs to another folder.'}
$powerShell=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$taskArguments='-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy RemoteSigned -File "'+(Join-Path $root 'Sync-And-Upload.ps1')+'" -NonInteractive'
$action=New-ScheduledTaskAction -Execute $powerShell -Argument $taskArguments -WorkingDirectory $root
$trigger=New-ScheduledTaskTrigger -Daily -At '09:00'
$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force -Description 'Read HD01S history, append local CSV, and synchronize the private GitHub repository. Daily 09:00; current user must be logged on.' | Out-Null
Write-Host 'Registered daily 09:00 sync for the currently logged-on Windows user.'
