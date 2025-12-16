@echo off
echo Starting Frontend Server on port 4000...
echo.
echo Frontend will be available at: http://localhost:4000
echo.
echo Note: Frontend is already served by backend at http://localhost:8000
echo This is only if you want to run frontend separately for development.
echo.
cd /d "%~dp0"
python -m http.server 4000
pause

