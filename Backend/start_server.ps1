$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
# Ensure we're in the Backend directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
Write-Host "Starting server from: $(Get-Location)" -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
# Use 127.0.0.1 instead of 0.0.0.0 to avoid Windows permission issues
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

