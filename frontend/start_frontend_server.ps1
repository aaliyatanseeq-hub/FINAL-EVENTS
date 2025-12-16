# Start Frontend Server (Optional - Frontend is already served by backend)
Write-Host "Starting Frontend Server on port 4000..." -ForegroundColor Green
Write-Host ""
Write-Host "Frontend will be available at: http://localhost:4000" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  Note: Frontend is already served by backend at http://localhost:8000" -ForegroundColor Yellow
Write-Host "   This is only if you want to run frontend separately for development." -ForegroundColor Yellow
Write-Host ""

Set-Location $PSScriptRoot
python -m http.server 4000

