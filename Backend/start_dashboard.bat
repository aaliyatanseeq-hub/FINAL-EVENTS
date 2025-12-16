@echo off
echo 📊 Starting Database Dashboard...
echo 🌐 Dashboard will be available at: http://localhost:8080
echo 🔄 Auto-refresh every 30 seconds
echo.

cd ..
venv\Scripts\python.exe Backend\database\database_dashboard.py
pause

