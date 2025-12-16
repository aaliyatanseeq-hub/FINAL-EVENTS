# Run this script as Administrator to avoid port permission issues
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  This script requires Administrator privileges!" -ForegroundColor Yellow
    Write-Host "Right-click PowerShell and select 'Run as Administrator', then run this script again." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Alternatively, use start_server.ps1 which uses 127.0.0.1 instead of 0.0.0.0" -ForegroundColor Cyan
    pause
    exit
}

# Kill any processes on port 8000
Write-Host "Checking port 8000..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($connections) {
    $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $processIds) {
        Write-Host "Killing process $procId on port 8000..." -ForegroundColor Cyan
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Host "✅ Port 8000 freed" -ForegroundColor Green
}

# Ensure we're in the Backend directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
Write-Host "Starting server from: $(Get-Location)" -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Green
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

