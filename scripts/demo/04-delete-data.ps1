<#
.SYNOPSIS
    APS4: Remove All Demo Data and Containers
.DESCRIPTION
    Fourth autonomous process - completely removes demo environment including data.
    Use this when you want to start fresh with a completely clean slate.
.NOTES
    - Stops all containers (frontend, backend, redis)
    - Removes all Docker volumes (deletes all demo data)
    - Removes built images (optional, for complete cleanup)
    - Useful for starting completely fresh or freeing disk space
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
Write-Host "  ║   APS4: AI Real Estate Assistant - Reset Demo       ║" -ForegroundColor Cyan
Write-Host  "  ╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Warning ─────────────────────────────────────────────────────────────
Write-Host "  ⚠️  WARNING: This will delete ALL demo data!" -ForegroundColor Yellow
Write-Host "  • All database data (250+ properties, users, etc.)" -ForegroundColor Yellow
Write-Host "  • All Docker volumes" -ForegroundColor Yellow
Write-Host "  • All containers" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "  Type 'DELETE' to confirm data destruction"
if ($confirm -ne "DELETE") {
    Write-Host "  ❌ Cancelled - No data was deleted" -ForegroundColor Red
    exit 0
}

# ── Check Docker ───────────────────────────────────────────────────────
Step "[1/4] Checking Docker..."
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
} catch {
    Fail "Docker is not running."
}
Ok "Docker is running"

# ── Stop and Remove ─────────────────────────────────────────────────────
Step "[2/4] Stopping containers and removing volumes..."
$ComposeFile = Join-Path $ComposeDir "docker-compose.yml"

Write-Host "  Stopping containers and removing volumes..." -ForegroundColor Cyan
docker compose -f $ComposeFile down -v 2>&1 | ForEach-Object {
    if ($_ -match "error|Error|ERROR") { Write-Host "  ❌ $_" -ForegroundColor Red }
    else { Write-Host "  $_" -ForegroundColor DarkGray }
}

if ($LASTEXITCODE -eq 0) {
    Ok "Containers stopped and volumes removed"
} else {
    Warn "Some cleanup had issues (non-critical)"
}

# ── Remove Orphaned Containers ───────────────────────────────────────────
Step "[3/4] Removing orphaned containers..."
Write-Host "  Checking for orphaned containers..." -ForegroundColor Cyan

$orphanContainers = docker ps -a -q --filter "name=ai-"
if ($orphanContainers) {
    Write-Host "  Found orphaned containers, removing..." -ForegroundColor Yellow
    docker rm -f $orphanContainers 2>&1 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor DarkGray
    }
    Ok "Orphaned containers removed"
} else {
    Ok "No orphaned containers found"
}

# ── Optional: Remove Images ─────────────────────────────────────────────
Step "[4/4] Optional: Remove built images?"
Write-Host "  Remove built Docker images to free disk space?" -ForegroundColor Cyan
Write-Host "  This will require rebuilding images next time (slower startup)." -ForegroundColor Yellow
$removeImages = Read-Host "  Remove images? (y/N): "

if ($removeImages -eq "y" -or $removeImages -eq "Y") {
    Write-Host "  Removing images..." -ForegroundColor Cyan

    $images = docker images "realt-frontend,realt-backend" -q
    if ($images) {
        docker rmi -f $images 2>&1 | ForEach-Object {
            Write-Host "  $_" -ForegroundColor DarkGray
        }
        Ok "Images removed"
    } else {
        Ok "No demo images found"
    }
} else {
    Ok "Images preserved (faster restart next time)"
}

# ── Summary ───────────────────────────────────────────────────────────────
Write-Host "`n  ╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║              🗑️  APS4 Complete!                       ║" -ForegroundColor Cyan
Write-Host  "  ╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ✅ All demo data removed" -ForegroundColor Green
Write-Host "  ✅ Docker volumes deleted" -ForegroundColor Green
Write-Host "  ✅ Containers cleaned up" -ForegroundColor Green
Write-Host ""
Write-Host "  📋 To start fresh:" -ForegroundColor Yellow
Write-Host "    Run .\scripts\demo\01-launch-docker.ps1" -ForegroundColor White
Write-Host "    This will rebuild everything from scratch" -ForegroundColor White
Write-Host ""
Write-Host "  💡 Note: If images were removed, next startup will take longer" -ForegroundColor Yellow
Write-Host "         as images need to be rebuilt (5-8 minutes)" -ForegroundColor White
Write-Host ""
