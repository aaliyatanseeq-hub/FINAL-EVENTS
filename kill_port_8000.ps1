# Kill all processes on port 8000
Write-Host "Killing processes on port 8000..." -ForegroundColor Yellow

$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($connections) {
    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $processIds) {
        Write-Host "Killing process $procId..." -ForegroundColor Cyan
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host "✅ Processes killed" -ForegroundColor Green
} else {
    Write-Host "✅ Port 8000 is free" -ForegroundColor Green
}

# Also kill all Python processes from this project
Write-Host "Killing Python processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.Path -like "*DoneandDusted*"} | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Write-Host "✅ Done" -ForegroundColor Green

