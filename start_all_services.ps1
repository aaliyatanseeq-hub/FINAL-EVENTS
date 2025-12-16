# Start All Services - Backend, Frontend, and Database Dashboard
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting All Services" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Kill any existing Python processes
Write-Host "🔄 Clearing existing processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*DoneandDusted*"} | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 1

# Start Backend Server (FastAPI - serves both API and Frontend)
Write-Host "🚀 Starting Backend Server (FastAPI)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\Backend'; Write-Host '🚀 Backend Server (FastAPI)' -ForegroundColor Green; Write-Host '📡 API: http://localhost:8000' -ForegroundColor Cyan; Write-Host '🌐 Frontend: http://localhost:8000' -ForegroundColor Cyan; Write-Host '🔄 Auto-reload enabled' -ForegroundColor Yellow; Write-Host ''; `$env:PYTHONIOENCODING='utf-8'; ..\venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 2

# Start Database Dashboard
Write-Host "📊 Starting Database Dashboard..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; Write-Host '📊 Database Dashboard (Flask)' -ForegroundColor Green; Write-Host '🌐 Dashboard: http://localhost:5001' -ForegroundColor Cyan; Write-Host '🔄 Auto-refresh every 30 seconds' -ForegroundColor Yellow; Write-Host ''; .\venv\Scripts\python.exe Backend\database\database_dashboard.py"

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "✅ All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Access your services:" -ForegroundColor Yellow
Write-Host "   🚀 Backend API:        http://localhost:8000/api/health" -ForegroundColor Cyan
Write-Host "   🌐 Frontend UI:        http://localhost:8000" -ForegroundColor Cyan
Write-Host "   📊 Database Dashboard: http://localhost:5001" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 You should see 2 PowerShell windows:" -ForegroundColor White
Write-Host "   1. Backend server (FastAPI + Frontend)" -ForegroundColor White
Write-Host "   2. Database dashboard" -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit this script (services will keep running)..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

