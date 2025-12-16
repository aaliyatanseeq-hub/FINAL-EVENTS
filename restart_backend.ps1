# Quick script to restart just the backend
Write-Host "Restarting Backend Server..." -ForegroundColor Yellow
Write-Host ""

# Kill existing backend processes on port 8000
Write-Host "Stopping existing backend..." -ForegroundColor Yellow
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    $pid8000 = ($port8000 | Select-Object -First 1).OwningProcess
    Write-Host "  Found process on port 8000 (PID: $pid8000)" -ForegroundColor Cyan
    Stop-Process -Id $pid8000 -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "  Backend stopped" -ForegroundColor Green
} else {
    Write-Host "  No process found on port 8000" -ForegroundColor Cyan
}

# Wait a moment for port to be released
Start-Sleep -Seconds 1

# Start backend - using port 8001 if 8000 is blocked
Write-Host ""
$port = 8000
$portCheck = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($portCheck) {
    Write-Host "Port 8000 is in use, trying port 8001..." -ForegroundColor Yellow
    $port = 8001
} else {
    Write-Host "Starting Backend on port 8000..." -ForegroundColor Green
}

Start-Process -FilePath "venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "$port", "--reload" `
    -WorkingDirectory "Backend" `
    -WindowStyle Normal

Start-Sleep -Seconds 4

# Test connection
Write-Host ""
Write-Host "Testing backend connection..." -ForegroundColor Yellow
try {
    $healthCheck = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    if ($healthCheck.StatusCode -eq 200) {
        Write-Host "  OK: Backend is responding!" -ForegroundColor Green
        $data = $healthCheck.Content | ConvertFrom-Json
        Write-Host "  Database status: $($data.database)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "  WARNING: Backend not responding yet (may need a few more seconds)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Backend restarted!" -ForegroundColor Green
Write-Host "Access at: http://localhost:8000" -ForegroundColor Cyan
Write-Host ""
