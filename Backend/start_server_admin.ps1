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

# Ensure we're in the Backend directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
Write-Host "Starting server from: $(Get-Location)" -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Green
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

