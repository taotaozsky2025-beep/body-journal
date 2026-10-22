param([ValidateSet('pull','upload','configure','setup')][string]$Mode='pull',[string]$RepositoryUrl,[switch]$NonInteractive)
$ErrorActionPreference='Stop'
$python=& (Join-Path $PSScriptRoot 'Ensure-Runtime.ps1')
$localDir=Join-Path $PSScriptRoot '.local'
New-Item -ItemType Directory -Force -Path $localDir | Out-Null
$lock=$null
try {
    $lock=[IO.File]::Open((Join-Path $localDir 'github-sync.lock'),'OpenOrCreate','ReadWrite','None')
    if($NonInteractive){$env:GIT_TERMINAL_PROMPT='0';$env:GCM_INTERACTIVE='never'}
    & $python (Join-Path $PSScriptRoot 'git_sync.py') $Mode $RepositoryUrl
    if($LASTEXITCODE -ne 0){throw 'GitHub sync failed. Local records were retained.'}
} finally {if($lock){$lock.Dispose()}}
