# Start server from root directory
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Change to Backend directory
$backendPath = Join-Path $PSScriptRoot "Backend"
if (Test-Path $backendPath) {
    Set-Location $backendPath
    Write-Host "Starting server from: $(Get-Location)" -ForegroundColor Green
    python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
} else {
    Write-Host "Error: Backend directory not found!" -ForegroundColor Red
    exit 1
}

