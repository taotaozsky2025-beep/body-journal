$ErrorActionPreference='Stop'
$root=$PSScriptRoot
& (Join-Path $root 'Ensure-Settings.ps1')
$python=& (Join-Path $root 'Ensure-Runtime.ps1') -WithScale
$lock=$null
$process=$null
try {
    $lock=[IO.File]::Open((Join-Path $root 'sync.lock'),'OpenOrCreate','ReadWrite','None')
    $protected=(Get-Content (Join-Path $root 'token.dpapi') -Raw).Trim() | ConvertTo-SecureString
    $credential=New-Object Management.Automation.PSCredential('token',$protected)
    $info=New-Object Diagnostics.ProcessStartInfo
    $info.FileName=$python
    $info.Arguments='"'+(Join-Path $root 'hd01s_sync.py')+'"'
    $info.WorkingDirectory=$root
    $info.UseShellExecute=$false
    $info.CreateNoWindow=$true
    $info.RedirectStandardInput=$true
    $info.RedirectStandardOutput=$true
    $info.RedirectStandardError=$true
    $info.EnvironmentVariables['PYTHONUTF8']='1'
    $process=New-Object Diagnostics.Process
    $process.StartInfo=$info
    [void]$process.Start()
    $stdout=$process.StandardOutput.ReadToEndAsync()
    $stderr=$process.StandardError.ReadToEndAsync()
    $encoding=New-Object Text.UTF8Encoding($false)
    $writer=New-Object IO.StreamWriter($process.StandardInput.BaseStream,$encoding)
    $writer.Write($credential.GetNetworkCredential().Password)
    $writer.Close()
    $credential=$null
    if(!$process.WaitForExit(300000)){throw 'Sync timed out; previous CSV retained.'}
    if($process.ExitCode -ne 0){throw 'HD01S sync failed. Consult diagnostic.json for the safe error category.'}
    $result=$stdout.Result | ConvertFrom-Json
    if(!$result.Success){throw 'HD01S sync returned failure.'}
    $result | ConvertTo-Json -Depth 5
} finally {
    $credential=$null
    if($process){if(!$process.HasExited){$process.Kill();$process.WaitForExit()};$process.Dispose()}
    if($lock){$lock.Dispose()}
}
