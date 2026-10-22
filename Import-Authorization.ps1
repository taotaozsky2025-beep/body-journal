$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$yamlPath=Join-Path $root 'auth-helper/go2rtc.yaml'
$yaml=Get-Content -LiteralPath $yamlPath -Raw
# Only accept the documented numeric-account to V1-token mapping.
$pattern=@'
^\s+["']?(\d+)["']?:\s*["']?(V1:[A-Za-z0-9+/_=.-]+)["']?\s*$
'@
$matchesFound=[regex]::Matches($yaml,$pattern,[Text.RegularExpressions.RegexOptions]::Multiline)
if($matchesFound.Count -ne 1){throw 'Expected exactly one authorized Xiaomi account. No token was imported.'}
$accountId=$matchesFound[0].Groups[1].Value
$passToken=$matchesFound[0].Groups[2].Value
$tokenMap=@{}
$tokenMap['xiaomi:'+$accountId]=$accountId+':'+$passToken
$tokenJson=$tokenMap | ConvertTo-Json -Compress
$tokenJson | ConvertTo-SecureString -AsPlainText -Force | ConvertFrom-SecureString | Set-Content (Join-Path $root 'token.dpapi')
@{Id=$accountId} | ConvertTo-Json | Set-Content (Join-Path $root 'account.json')
# Verify that the current Windows user can decrypt exactly what was saved.
$secure=(Get-Content (Join-Path $root 'token.dpapi') -Raw).Trim() | ConvertTo-SecureString
$check=New-Object Management.Automation.PSCredential('check',$secure)
if($check.GetNetworkCredential().Password -cne $tokenJson){throw 'Encrypted token verification failed.'}
$pidFile=Join-Path $root 'auth-helper/process.id'
if(Test-Path $pidFile){
    $helperProcess=Get-Process -Id ([int](Get-Content $pidFile)) -ErrorAction SilentlyContinue
    if($helperProcess -and $helperProcess.Path -eq (Join-Path $root 'auth-helper/go2rtc.exe')){Stop-Process -Id $helperProcess.Id}
}
# Remove the plaintext token from this private temporary configuration only
# after encryption verification and helper shutdown.
Copy-Item -LiteralPath (Join-Path $root 'go2rtc-login.yaml') -Destination $yamlPath -Force
$yaml=$null; $passToken=$null; $tokenJson=$null; $tokenMap=$null; $check=$null
Write-Host 'Authorization encrypted for this Windows user. Local login helper stopped. No password was saved.'
