# Start All Services - Fixed Version
# This script starts Backend, Frontend, and Database Dashboard

Write-Host "Starting Event Intelligence Platform..." -ForegroundColor Cyan
Write-Host ""

# Check if venv exists
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "   Please run: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# Stop any existing Python processes on ports 8000 and 5001
Write-Host "Stopping existing services..." -ForegroundColor Yellow
# Kill processes using ports 8000 and 5001
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
$port5001 = Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue
if ($port8000) {
    $pid8000 = ($port8000 | Select-Object -First 1).OwningProcess
    Stop-Process -Id $pid8000 -Force -ErrorAction SilentlyContinue
}
if ($port5001) {
    $pid5001 = ($port5001 | Select-Object -First 1).OwningProcess
    Stop-Process -Id $pid5001 -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1


# Check if PostgreSQL is running
Write-Host ""
Write-Host "Checking PostgreSQL..." -ForegroundColor Yellow
$pgService = Get-Service -Name "postgresql-x64-18" -ErrorAction SilentlyContinue
if ($pgService -and $pgService.Status -eq "Running") {
    Write-Host "   OK: PostgreSQL is running" -ForegroundColor Green
} else {
    Write-Host "   WARNING: PostgreSQL might not be running" -ForegroundColor Yellow
    Write-Host "      Attempting to start PostgreSQL service..." -ForegroundColor Yellow
    Start-Service -Name "postgresql-x64-18" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    if ((Get-Service -Name "postgresql-x64-18" -ErrorAction SilentlyContinue).Status -eq "Running") {
        Write-Host "   OK: PostgreSQL started successfully" -ForegroundColor Green
    } else {
        Write-Host "   WARNING: Could not start PostgreSQL automatically" -ForegroundColor Yellow
        Write-Host "      Please start it manually if needed" -ForegroundColor Yellow
    }
}

# Initialize database tables
Write-Host ""
Write-Host "Initializing database tables..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" -c "from Backend.database.database import init_database; init_database()" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   OK: Database tables initialized" -ForegroundColor Green
} else {
    Write-Host "   WARNING: Database initialization had issues (may already exist)" -ForegroundColor Yellow
}

# Start Backend (FastAPI)
Write-Host ""
Write-Host "Starting Backend (FastAPI) on port 8000..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000", "--reload" `
    -WorkingDirectory "Backend" `
    -WindowStyle Normal `
    -PassThru

Start-Sleep -Seconds 4

# Start Database Dashboard (Flask)
Write-Host "Starting Database Dashboard on port 5001..." -ForegroundColor Yellow
$dashboardJob = Start-Process -FilePath "venv\Scripts\python.exe" `
    -ArgumentList "database\database_dashboard.py" `
    -WorkingDirectory "Backend" `
    -WindowStyle Normal `
    -PassThru

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "OK: All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "   • Frontend: http://localhost:8000" -ForegroundColor White
Write-Host "   • Backend API: http://localhost:8000/api/health" -ForegroundColor White
Write-Host "   • Database Dashboard: http://localhost:5001" -ForegroundColor White
Write-Host ""
Write-Host "Testing connections..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

# Test backend
try {
    $healthCheck = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   OK: Backend is responding" -ForegroundColor Green
} catch {
    Write-Host "   WARNING: Backend not responding yet (may need a few more seconds)" -ForegroundColor Yellow
}

# Test dashboard
try {
    $dashboardCheck = Invoke-WebRequest -Uri "http://localhost:5001" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    Write-Host "   OK: Database Dashboard is responding" -ForegroundColor Green
} catch {
    Write-Host "   WARNING: Dashboard not responding yet (may need a few more seconds)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "NOTE: Close the windows to stop the services" -ForegroundColor Yellow
Write-Host "   Or press Ctrl+C in each window" -ForegroundColor Yellow
Write-Host ""

