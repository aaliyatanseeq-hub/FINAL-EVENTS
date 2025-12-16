$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Kill any processes on port 8000
Write-Host "Checking port 8000..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($connections) {
    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $processIds) {
        Write-Host "Killing process $procId on port 8000..." -ForegroundColor Cyan
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host "✅ Port 8000 freed" -ForegroundColor Green
}

# Ensure we're in the Backend directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
Write-Host "Starting server from: $(Get-Location)" -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
# Use 127.0.0.1 instead of 0.0.0.0 to avoid Windows permission issues
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

