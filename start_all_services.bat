@echo off
echo ========================================
echo   Starting All Services
echo ========================================
echo.

REM Start Backend Server
echo Starting Backend Server (FastAPI)...
start "Backend Server" powershell -NoExit -Command "cd Backend; Write-Host '🚀 Backend Server (FastAPI)' -ForegroundColor Green; Write-Host '📡 API: http://localhost:8000' -ForegroundColor Cyan; Write-Host '🌐 Frontend: http://localhost:8000' -ForegroundColor Cyan; $env:PYTHONIOENCODING='utf-8'; ..\venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 /nobreak >nul

REM Start Database Dashboard
echo Starting Database Dashboard...
start "Database Dashboard" powershell -NoExit -Command "cd %~dp0; Write-Host '📊 Database Dashboard (Flask)' -ForegroundColor Green; Write-Host '🌐 Dashboard: http://localhost:5001' -ForegroundColor Cyan; .\venv\Scripts\python.exe Backend\database\database_dashboard.py"

timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo   All Services Started!
echo ========================================
echo.
echo Access your services:
echo   Backend API:        http://localhost:8000/api/health
echo   Frontend UI:        http://localhost:8000
echo   Database Dashboard: http://localhost:5001
echo.
echo You should see 2 new windows:
echo   1. Backend server (FastAPI + Frontend)
echo   2. Database dashboard
echo.
pause

