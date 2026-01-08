# Start Database Dashboard
Write-Host "📊 Starting Database Dashboard..." -ForegroundColor Green
Write-Host "🌐 Dashboard will be available at: http://localhost:5001" -ForegroundColor Cyan
Write-Host "🔄 Auto-refresh every 30 seconds" -ForegroundColor Yellow
Write-Host "⚠️  Note: Port 8080 might be used by PostgreSQL web interface" -ForegroundColor Red
Write-Host ""

# Activate venv and run dashboard
$env:PYTHONIOENCODING="utf-8"
Set-Location ..
.\venv\Scripts\python.exe Backend\database\database_dashboard.py
