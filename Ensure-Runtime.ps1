param([switch]$WithScale,[switch]$WithLogin)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
if(![Environment]::Is64BitOperatingSystem){throw 'This package requires 64-bit Windows.'}
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$runtime=Join-Path $root '.runtime'
$downloads=Join-Path $runtime 'downloads'
New-Item -ItemType Directory -Force -Path $downloads | Out-Null
function Get-Sha256($path){
    $stream=[IO.File]::OpenRead($path)
    $algorithm=[Security.Cryptography.SHA256]::Create()
    try {return [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-','').ToLowerInvariant()}
    finally {$stream.Dispose();$algorithm.Dispose()}
}
function Get-VerifiedArchive($url,$name,$sha256){
    $path=Join-Path $downloads $name
    if(!(Test-Path $path) -or (Get-Sha256 $path) -ne $sha256){
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $path
    }
    if((Get-Sha256 $path) -ne $sha256){throw ('Checksum mismatch: '+$name)}
    return $path
}
$python=Join-Path $runtime 'python\python.exe'
if(!(Test-Path $python)){
    Write-Host 'Preparing portable Python from python.org (first launch only)...'
    $archive=Get-VerifiedArchive 'https://www.python.org/ftp/python/3.14.4/python-3.14.4-embeddable-amd64.zip' 'python-3.14.4.zip' 'fa2e63e9f0607e34d8841cc8080641069b71d2bddb5a69fa30c24eb5599da9fe'
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $runtime 'python') -Force
}
if($WithScale){
    $exe=Join-Path $root 'scaleconnect.exe'
    if(!(Test-Path $exe) -or (Get-Sha256 $exe) -ne '62635BF795340992F3AEB73584D4765BECC957A081016987753EE7E3C1E43ADA'){
        $archive=Get-VerifiedArchive 'https://github.com/AlexxIT/SmartScaleConnect/releases/download/v0.4.1/scaleconnect_win64.zip' 'scaleconnect-v0.4.1.zip' '83e76a5fc74e9fdfa3f6456f15243ab7aa3f27e39a4bfd339736babd0173126d'
        $unpack=Join-Path $runtime 'scaleconnect'
        Expand-Archive -LiteralPath $archive -DestinationPath $unpack -Force
        Copy-Item -LiteralPath (Join-Path $unpack 'scaleconnect.exe') -Destination $exe -Force
    }
}
if($WithLogin){
    $helper=Join-Path $root 'auth-helper'
    New-Item -ItemType Directory -Force -Path $helper | Out-Null
    $sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl=New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false);$acl.SetOwner($sid)
    $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')))
    Set-Acl -LiteralPath $helper -AclObject $acl
    $exe=Join-Path $helper 'go2rtc.exe'
    if(!(Test-Path $exe)){
        $archive=Get-VerifiedArchive 'https://github.com/AlexxIT/go2rtc/releases/download/v1.9.14/go2rtc_win64.zip' 'go2rtc-v1.9.14.zip' 'dd4167d75cb04abe618855b7c71f8658bd009f60c1a71835d134d2c11c939907'
        Expand-Archive -LiteralPath $archive -DestinationPath $helper -Force
    }
}
$python
