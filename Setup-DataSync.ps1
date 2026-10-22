param([string]$RepositoryUrl)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Ensure-Settings.ps1')
if(!$RepositoryUrl){$RepositoryUrl=Read-Host 'HTTPS URL of your PRIVATE GitHub data repository (main branch)'}
& (Join-Path $PSScriptRoot 'Git-Sync.ps1') -Mode setup -RepositoryUrl $RepositoryUrl
& (Join-Path $PSScriptRoot 'Git-Sync.ps1') -Mode pull
Write-Host 'Private archive connected. The PUBLIC source repository never receives measurement data.'
