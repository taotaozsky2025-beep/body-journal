$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Ensure-Settings.ps1')
if(Test-Path (Join-Path $PSScriptRoot '.local\data-sync.json')){
    try {& (Join-Path $PSScriptRoot 'Git-Sync.ps1') -Mode pull} catch {Write-Warning 'Could not update from GitHub. Opening the locally saved history.'}
}
& (Join-Path $PSScriptRoot 'Start-Viewer.ps1')
