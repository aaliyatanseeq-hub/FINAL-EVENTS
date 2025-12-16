@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo Starting server from: %CD%

REM Kill processes on port 8000
echo Checking port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process %%a on port 8000...
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

