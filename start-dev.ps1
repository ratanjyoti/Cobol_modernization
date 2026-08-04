$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"
$repoVenvPython = Resolve-Path (Join-Path $root "..\myenv\Scripts\python.exe") -ErrorAction SilentlyContinue
$pythonExe = if ($repoVenvPython) { $repoVenvPython.Path } else { "python" }

Write-Host "Starting backend:  http://127.0.0.1:8010"
Write-Host "Starting frontend: http://127.0.0.1:5173"
Write-Host "Press Ctrl+C to stop both servers."

$backend = Start-Job -Name "modernizer-backend" -ScriptBlock {
  param($dir, $python)
  Set-Location $dir
  & $python -m uvicorn main:app --host 127.0.0.1 --port 8010 --reload
} -ArgumentList $backendDir, $pythonExe

$frontend = Start-Job -Name "modernizer-frontend" -ScriptBlock {
  param($dir)
  Set-Location $dir
  npm run dev -- --host 127.0.0.1
} -ArgumentList $frontendDir

try {
  while ($true) {
    Receive-Job $backend, $frontend

    $stopped = @($backend, $frontend | Where-Object { $_.State -in @("Failed", "Stopped", "Completed") })
    if ($stopped.Count -gt 0) {
      $names = ($stopped | ForEach-Object { "$($_.Name):$($_.State)" }) -join ", "
      throw "A dev server stopped unexpectedly ($names)."
    }

    Start-Sleep -Seconds 1
  }
}
finally {
  Stop-Job $backend, $frontend -ErrorAction SilentlyContinue
  Remove-Job $backend, $frontend -Force -ErrorAction SilentlyContinue
}
