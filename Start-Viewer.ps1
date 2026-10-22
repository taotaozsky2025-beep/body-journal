$ErrorActionPreference='Stop'
$url='http://127.0.0.1:19842/'
$ready=$false
try {$health=Invoke-RestMethod ($url+'api/health') -TimeoutSec 2; $ready=$health.application -eq 'local-scale-dashboard'; if($ready -and $health.root -and $health.root -ne $PSScriptRoot){throw 'Another checkout is already serving this port.'}} catch {if($_.Exception.Message -like 'Another checkout*'){throw}}
if($ready -and $health.version -lt 2){
    $viewerPath=Join-Path $PSScriptRoot 'viewer_server.py'
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {$_.CommandLine -match [regex]::Escape($viewerPath)} | ForEach-Object {Stop-Process -Id $_.ProcessId}
    $ready=$false
}
if(!$ready){
    $python=& (Join-Path $PSScriptRoot 'Ensure-Runtime.ps1')
    Start-Process -FilePath $python -ArgumentList ('"'+(Join-Path $PSScriptRoot 'viewer_server.py')+'"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    for($attempt=0;$attempt -lt 30;$attempt++){
        Start-Sleep -Milliseconds 200
        try {$health=Invoke-RestMethod ($url+'api/health') -TimeoutSec 1; if($health.application -eq 'local-scale-dashboard'){$ready=$true;break}} catch {}
    }
}
if(!$ready){throw 'The local dashboard did not start. Port 19842 may be in use.'}
Start-Process $url
