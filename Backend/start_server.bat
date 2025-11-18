@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
echo Starting server from: %CD%
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

