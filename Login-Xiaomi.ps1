$ErrorActionPreference='Stop'
$null=& (Join-Path $PSScriptRoot 'Ensure-Runtime.ps1') -WithScale -WithLogin
$helper=Join-Path $PSScriptRoot 'auth-helper'
$config=Join-Path $helper 'go2rtc.yaml'
if((Test-Path $config) -and (Get-Content $config -Raw) -match 'V1:'){
    & (Join-Path $PSScriptRoot 'Import-Authorization.ps1')
} else {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'go2rtc-login.yaml') -Destination $config -Force
    $process=Start-Process -FilePath (Join-Path $helper 'go2rtc.exe') -ArgumentList '-config',('"'+$config+'"') -WorkingDirectory $helper -WindowStyle Hidden -PassThru
    $process.Id | Set-Content (Join-Path $helper 'process.id')
    Start-Sleep -Seconds 1
    Start-Process 'http://127.0.0.1:19841/add.html#xiaomi'
    Write-Host 'In the local browser, open Xiaomi, sign in, and complete any verification. Do not share passwords or codes.'
    $deadline=[DateTime]::UtcNow.AddMinutes(15)
    $authorized=$false
    while([DateTime]::UtcNow -lt $deadline){
        if((Get-Content $config -Raw) -match 'V1:'){$authorized=$true;break}
        if($process.HasExited){break}
        Start-Sleep -Seconds 1
    }
    if(!$authorized){if(!$process.HasExited){Stop-Process -Id $process.Id};throw 'Local authorization was not completed. Run this entry again to retry.'}
    & (Join-Path $PSScriptRoot 'Import-Authorization.ps1')
}
& (Join-Path $PSScriptRoot 'Sync-And-Upload.ps1')
& (Join-Path $PSScriptRoot 'Start-Viewer.ps1')
