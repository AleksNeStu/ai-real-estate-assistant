<#
.SYNOPSIS
    APS3: Stop AI Real Estate Assistant Docker Containers
.DESCRIPTION
    Third autonomous process - stops all Docker containers and optionally cleans up data.
    Run this when you're done with the demo environment.
.NOTES
    - Gracefully stops all containers (frontend, backend, redis)
    - Option to remove volumes and delete demo data
    - Containers can be restarted later with APS1_Launch_Docker.ps1
#>
$ErrorActionPreference = "Stop"
# Get project root (go up two levels from scripts/demo/ to project root)
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ComposeDir = Join-Path $ProjectRoot "deploy/compose"

function Step($m) { Write-Host "`n  $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  ✅  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  ⚠️  $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "  ❌  $m" -ForegroundColor Red; exit 1 }

Write-Host "`n  ╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     APS3: AI Real Estate Assistant - Stop Docker      ║" -ForegroundColor Cyan
Write-Host  "  ╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Check Docker ───────────────────────────────────────────────────────
Step "[1/3] Checking Docker..."
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
} catch {
    Fail "Docker is not running."
}
Ok "Docker is running"

# ── Check Running Containers ─────────────────────────────────────────────
Step "[2/3] Checking running containers..."
$ComposeFile = Join-Path $ComposeDir "docker-compose.yml"
$runningContainers = docker compose -f $ComposeFile ps -q 2>&1

if ($LASTEXITCODE -ne 0 -or -not $runningContainers) {
    Warn "No containers are currently running"
    exit 0
}

$containerCount = ($runningContainers | Measure-Object).Count
Ok "Found $containerCount running container(s)"

# ── Stop Containers ───────────────────────────────────────────────────────
Step "[3/3] Stopping containers..."

Write-Host "  Stopping containers..." -ForegroundColor Cyan
docker compose -f $ComposeFile down 2>&1 | ForEach-Object {
    if ($_ -match "error|Error|ERROR") { Write-Host "  ❌ $_" -ForegroundColor Red }
    else { Write-Host "  $_" -ForegroundColor DarkGray }
}

if ($LASTEXITCODE -eq 0) {
    Ok "All containers stopped successfully"
} else {
    Fail "Failed to stop containers"
}

# ── Summary ───────────────────────────────────────────────────────────────
Write-Host "`n  ╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║              🛑 APS3 Complete!                       ║" -ForegroundColor Cyan
Write-Host  "  ╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ✅ All containers stopped" -ForegroundColor Green
Write-Host "  ✅ Docker resources cleaned up" -ForegroundColor Green
Write-Host ""
Write-Host "  📋 To restart:" -ForegroundColor Yellow
Write-Host "    Run .\scripts\demo\01-launch-docker.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  🗑️  To remove demo data:" -ForegroundColor Yellow
Write-Host "    Run .\scripts\docker\reset.ps1" -ForegroundColor White
Write-Host "    Or: docker compose -f deploy/compose/docker-compose.yml down -v" -ForegroundColor White
Write-Host ""
