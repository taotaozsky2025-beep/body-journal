$ErrorActionPreference='Stop'
$settings=Join-Path $PSScriptRoot 'settings.json'
if(!(Test-Path $settings)){
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'settings.example.json') -Destination $settings
}
