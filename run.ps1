$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
& ".\.venv\Scripts\python.exe" -m uvicorn backend.eva.main:app --host 0.0.0.0 --port 8765
