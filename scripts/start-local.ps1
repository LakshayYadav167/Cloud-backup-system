# ==============================================================================
# Cloud Backup System - Windows PowerShell Local Startup Script
# ==============================================================================
# Starts the Cloud Backup System locally under the strict ₹0 budget constraint.
# Operates in local filesystem mode without requiring Docker or Floci.
#
# Usage:
#   .\scripts\start-local.ps1              # Starts backend with interactive guidance
#   .\scripts\start-local.ps1 -BackendOnly # Starts only FastAPI backend (Port 8000)
#   .\scripts\start-local.ps1 -FrontendOnly# Starts only Vite frontend (Port 5173)
# ==============================================================================

param (
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "=================================================================" -ForegroundColor White
Write-Host " Cloud Backup System - Local Development Startup Workflow" -ForegroundColor Green
Write-Host " Workspace: $ProjectRoot" -ForegroundColor Gray
Write-Host " ₹0 Budget Mandate: Strictly Local Compute and Storage" -ForegroundColor Gray
Write-Host "=================================================================" -ForegroundColor White

# 1. Check Python
try {
    $pyVer = & python --version 2>&1
    Write-Host "[OK] Python detected: $pyVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# 2. Check Node
try {
    $nodeVer = & node --version 2>&1
    Write-Host "[OK] Node.js detected: $nodeVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Node.js is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# 3. Ensure Environment Template
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"
if (-not (Test-Path $EnvFile) -and (Test-Path $EnvExample)) {
    Write-Host "[INFO] Creating '.env' from '.env.example'..." -ForegroundColor Cyan
    Copy-Item $EnvExample $EnvFile
}

# 4. Ensure Local Storage Directories
$StorageDir = Join-Path $ProjectRoot "backend\data\storage"
if (-not (Test-Path $StorageDir)) {
    Write-Host "[INFO] Initializing local storage directory: $StorageDir" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $StorageDir -Force | Out-Null
}

if ($FrontendOnly) {
    Write-Host "`nStarting Frontend on http://localhost:5173..." -ForegroundColor Cyan
    Set-Location (Join-Path $ProjectRoot "frontend")
    & npm.cmd run dev
    exit 0
}

if ($BackendOnly) {
    Write-Host "`nStarting Backend on http://127.0.0.1:8000..." -ForegroundColor Cyan
    Set-Location (Join-Path $ProjectRoot "backend")
    & python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    exit 0
}

# Default: Start Backend in current shell and provide frontend command
Write-Host "`n[STARTUP INSTRUCTIONS]" -ForegroundColor Yellow
Write-Host "1. This window will now launch the FastAPI Backend on http://127.0.0.1:8000" -ForegroundColor White
Write-Host "2. In a second PowerShell window, launch the Frontend Dashboard via:" -ForegroundColor White
Write-Host "     cd $ProjectRoot\frontend" -ForegroundColor Cyan
Write-Host "     npm run dev" -ForegroundColor Cyan
Write-Host "3. Access the Web Dashboard at: http://localhost:5173" -ForegroundColor Green
Write-Host "4. Access the REST API Docs at:  http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "`nPress Ctrl+C at any time to gracefully stop the server.`n" -ForegroundColor DarkGray

Set-Location (Join-Path $ProjectRoot "backend")
& python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
