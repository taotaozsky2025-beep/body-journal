param([switch]$NonInteractive)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Ensure-Settings.ps1')
$folder=Join-Path $PSScriptRoot '.local'
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$lock=$null
$cloud='pending';$github='pending'
function Save-Progress($state,$phase){
    $status=@{State=$state;Phase=$phase;Cloud=$cloud;GitHub=$github;Updated=[DateTime]::UtcNow.ToString('o')}
    $pending=Join-Path $folder 'workflow.pending'
    $status | ConvertTo-Json | Set-Content -LiteralPath $pending -Encoding UTF8
    Move-Item -LiteralPath $pending -Destination (Join-Path $folder 'workflow.json') -Force
}
try {
    $lock=[IO.File]::Open((Join-Path $folder 'workflow.lock'),'OpenOrCreate','ReadWrite','None')
    Save-Progress 'running' 'xiaomi'
    if(Test-Path (Join-Path $PSScriptRoot 'token.dpapi')){
        try {& (Join-Path $PSScriptRoot 'Sync-HD01S.ps1');$cloud='success'} catch {$cloud='failed'}
    } else {$cloud='not_authorized'}
    Save-Progress 'running' 'github'
    if(Test-Path (Join-Path $PSScriptRoot '.local\data-sync.json')){
        try {& (Join-Path $PSScriptRoot 'Git-Sync.ps1') -Mode upload -NonInteractive:$NonInteractive;$github='success'} catch {$github='failed'}
    } else {$github='not_configured'}
    if($github -eq 'failed'){Save-Progress 'error' 'finished';throw 'GitHub sync failed. Local history was retained.'}
    if($github -eq 'not_configured'){
        if($cloud -eq 'failed'){Save-Progress 'error' 'finished';throw 'Xiaomi read failed. Local history was retained.'}
        Save-Progress 'local_only' 'finished';return
    }
    if($cloud -eq 'failed'){Save-Progress 'partial' 'finished';throw 'GitHub synchronized, but Xiaomi read failed. Reauthorize Xiaomi locally if needed.'}
    Save-Progress 'complete' 'finished'
} finally {if($lock){$lock.Dispose()}}
