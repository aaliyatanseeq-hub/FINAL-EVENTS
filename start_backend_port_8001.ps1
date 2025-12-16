# Start backend on port 8001 (to avoid Windows permission issues on 8000)
Write-Host "Starting Backend on port 8001..." -ForegroundColor Green
Write-Host "(Port 8000 has permission issues, using 8001 instead)" -ForegroundColor Yellow
Write-Host ""

# Kill any existing processes
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*DoneandDusted*"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Start backend on port 8001
Start-Process -FilePath "venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8001" `
    -WorkingDirectory "Backend" `
    -WindowStyle Normal

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "✅ Backend started on port 8001" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Access Points:" -ForegroundColor Cyan
Write-Host "   • Frontend: http://localhost:8001" -ForegroundColor White
Write-Host "   • Backend API: http://localhost:8001/api/health" -ForegroundColor White
Write-Host ""
Write-Host "NOTE: Frontend needs to be updated to use port 8001" -ForegroundColor Yellow
Write-Host "   Or update frontend/js/app.js to use port 8001" -ForegroundColor Yellow
Write-Host ""

