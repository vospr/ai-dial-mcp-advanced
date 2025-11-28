# Advanced MCP - Test Runner Script for Windows PowerShell
# This script sets up the environment and runs the test suite

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Advanced MCP - Test Runner" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".venv\Scripts\Activate.ps1"

# Install/upgrade dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

# Check Docker service
Write-Host ""
Write-Host "Checking Docker User Service (port 8041)..." -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8041/health" -TimeoutSec 5 -UseBasicParsing
    Write-Host "✅ Docker User Service is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker User Service is NOT running" -ForegroundColor Red
    Write-Host ""
    Write-Host "Starting Docker services..." -ForegroundColor Yellow
    docker compose up -d
    Start-Sleep -Seconds 5
    
    # Check again
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8041/health" -TimeoutSec 5 -UseBasicParsing
        Write-Host "✅ Docker User Service is now running" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to start Docker User Service" -ForegroundColor Red
        Write-Host "Please check Docker and try: docker compose up -d" -ForegroundColor Yellow
        exit 1
    }
}

# Check MCP Server
Write-Host ""
Write-Host "Checking MCP Server (port 8006)..." -ForegroundColor Cyan
try {
    $body = @{
        jsonrpc = "2.0"
        id = "health-check"
        method = "initialize"
        params = @{
            protocolVersion = "2024-11-05"
            capabilities = @{}
            clientInfo = @{
                name = "test"
                version = "1.0"
            }
        }
    } | ConvertTo-Json -Depth 10
    
    $headers = @{
        "Content-Type" = "application/json"
        "Accept" = "application/json, text/event-stream"
    }
    
    $response = Invoke-WebRequest -Uri "http://localhost:8006/mcp" -Method Post -Body $body -Headers $headers -TimeoutSec 5 -UseBasicParsing
    Write-Host "✅ MCP Server is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  MCP Server is NOT running" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please start the MCP server in a separate terminal:" -ForegroundColor Yellow
    Write-Host "  cd $ScriptDir" -ForegroundColor Yellow
    Write-Host "  .venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  `$env:DIAL_API_KEY='your_api_key'" -ForegroundColor Yellow
    Write-Host "  python mcp_server/server.py" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to continue anyway, or Ctrl+C to cancel"
}

# Check DIAL_API_KEY
Write-Host ""
if (-not $env:DIAL_API_KEY) {
    Write-Host "⚠️  DIAL_API_KEY environment variable is not set" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please set it:" -ForegroundColor Yellow
    Write-Host "  `$env:DIAL_API_KEY='your_dial_api_key'" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to continue anyway, or Ctrl+C to cancel"
} else {
    Write-Host "✅ DIAL_API_KEY is set" -ForegroundColor Green
}

# Run tests
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Running Test Suite" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

python test.py

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "✅ All tests completed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Some tests failed" -ForegroundColor Red
}

exit $exitCode

