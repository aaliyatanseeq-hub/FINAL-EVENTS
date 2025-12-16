@echo off
echo ========================================
echo   Starting Database Dashboard
echo ========================================
echo.
echo Dashboard will be available at:
echo   http://localhost:5001
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

cd ..
venv\Scripts\python.exe Backend\database\database_dashboard.py

