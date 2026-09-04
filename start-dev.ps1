param (
    [switch]$Unified
)

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ($Unified) {
    Write-Host "Starting TripAgent Backend & Frontend in single terminal (Ctrl+C to stop both)..." -ForegroundColor Cyan
    npx -y concurrently `
        -n "backend,frontend" `
        -c "cyan,magenta" `
        "uv run uvicorn app.main:app --reload --port 8000 --env-file .env" `
        "npm --prefix web start"
} else {
    Write-Host "Starting TripAgent Backend & Frontend in separate windows..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir'; uv run uvicorn app.main:app --reload --port 8000 --env-file .env"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$rootDir\web'; npm start"
}
