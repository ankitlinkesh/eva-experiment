$ErrorActionPreference = "Stop"
$matches = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
  Where-Object { $_.CommandLine -like '*backend.eva.main:app*' -and $_.CommandLine -like '*8765*' }

if (-not $matches) {
  Write-Host "Eva server is not running on the usual command."
  exit 0
}

foreach ($process in $matches) {
  Stop-Process -Id $process.ProcessId -Force
  Write-Host "Stopped Eva server process $($process.ProcessId)."
}
