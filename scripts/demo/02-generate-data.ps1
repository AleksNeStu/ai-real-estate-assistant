<#
.SYNOPSIS
    APS2: Generate Comprehensive Demo Data for AI Real Estate Assistant
.DESCRIPTION
    Second autonomous process - populates database with comprehensive demo data.
    Run AFTER APS1_Launch_Docker.ps1 has started the containers.
.NOTES
    - Requires Docker containers to be running (run APS1 first)
    - Generates 250+ properties, 50 users, 100 searches, 200 favorites, and more
    - Works with SQLite database in Docker
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
Write-Host "  ║  APS2: AI Real Estate Assistant - Data Generator   ║" -ForegroundColor Cyan
Write-Host  "  ╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Validate Docker Containers ────────────────────────────────────────────
Step "[1/4] Checking Docker containers..."
$ComposeFile = Join-Path $ComposeDir "docker-compose.yml"
$containerStatus = docker compose -f $ComposeFile ps -q ai-backend 2>&1
if ($LASTEXITCODE -ne 0 -or -not $containerStatus) {
    Fail "Backend container not running. Run APS1_Launch_Docker.ps1 first."
}
Ok "Backend container is running"

# ── Trigger Data Generation ────────────────────────────────────────────────
Step "[2/4] Generating comprehensive demo data..."

Write-Host "  This will generate maximum mock data to showcase ALL features:" -ForegroundColor Cyan
Write-Host "    • 250+ properties across 5 Polish cities" -ForegroundColor White
Write-Host "    • 50 users with different roles" -ForegroundColor White
Write-Host "    • 100 saved searches" -ForegroundColor White
Write-Host "    • 200 favorites" -ForegroundColor White
Write-Host "    • 15 AI agent profiles" -ForegroundColor White
Write-Host "    • 150 leads/inquiries" -ForegroundColor White
Write-Host "    • 300 activity events" -ForegroundColor White
Write-Host "    • 40 preference profiles" -ForegroundColor White
Write-Host "    • 20 CMA reports" -ForegroundColor White
Write-Host ""
Write-Host "  ℹ️  Existing demo data will be cleared first for clean state" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ⏳ This may take 2-3 minutes... (generating 250+ properties with ChromaDB)" -ForegroundColor Cyan
Write-Host ""

docker exec ai-backend python -c "
import asyncio
import sys
import logging
from alembic.demo_data_generator import generate_comprehensive_demo_data
from db.database import get_db_context

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def main():
    try:
        async with get_db_context() as session:
            results = await generate_comprehensive_demo_data(session)
            print()
            print('✅ Comprehensive demo data generated successfully!')
            for key, value in results.items():
                print(f'   • {value} {key}')
        return 0
    except Exception as e:
        print(f'❌ Error: {e}', file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

exit_code = asyncio.run(main())
sys.exit(exit_code)
" 2>&1 | ForEach-Object {
    if ($_ -match "Error|error|ERROR|Exception|Traceback") { Write-Host "  $_" -ForegroundColor Red }
    elseif ($_ -match "✅|successfully") { Write-Host "  $_" -ForegroundColor Green }
    elseif ($_ -match "INFO") { Write-Host "  $_" -ForegroundColor Cyan }
    elseif ($_ -match "WARNING|⚠") { Write-Host "  $_" -ForegroundColor Yellow }
    else { Write-Host "  $_" -ForegroundColor White }
}

if ($LASTEXITCODE -eq 0) {
    Ok "Comprehensive demo data generated successfully"
} else {
    Fail "Data generation failed with exit code $LASTEXITCODE. Check the errors above."
}

# ── Verify Data Generation ─────────────────────────────────────────────────
Step "[3/4] Verifying generated data..."
Start-Sleep -Seconds 2

$BackendUrl = "http://localhost:8082"
$FrontendUrl = "http://localhost:3082"

try {
    $checkResponse = Invoke-WebRequest -Uri "$BackendUrl/health" -TimeoutSec 10

    if ($checkResponse.StatusCode -eq 200) {
        Ok "Backend health check passed - container is ready"
    } else {
        Warn "Health check returned status $($checkResponse.StatusCode)"
    }
} catch {
    Warn "Health check failed: $_"
}

# ── Summary ─────────────────────────────────────────────────────────────────
Write-Host "`n  ╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║              🎉 APS2 Complete!                       ║" -ForegroundColor Cyan
Write-Host  "  ╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ✅ Comprehensive demo data generated" -ForegroundColor Green
Write-Host "  ✅ Maximum mock data for feature showcase" -ForegroundColor Green
Write-Host ""
Write-Host "  📊 Generated Data:" -ForegroundColor Yellow
Write-Host "    • 250+ properties across 5 Polish cities" -ForegroundColor White
Write-Host "    • 50 users with different roles" -ForegroundColor White
Write-Host "    • 100 saved searches" -ForegroundColor White
Write-Host "    • 200 favorites" -ForegroundColor White
Write-Host "    • 15 AI agent profiles" -ForegroundColor White
Write-Host "    • 150 leads/inquiries" -ForegroundColor White
Write-Host "    • 300 activity events" -ForegroundColor White
Write-Host "    • 40 preference profiles" -ForegroundColor White
Write-Host "    • 20 CMA reports" -ForegroundColor White
Write-Host ""
Write-Host "  🌐 Access Your Demo:" -ForegroundColor Yellow
Write-Host "    • Frontend:  http://localhost:3082" -ForegroundColor White
Write-Host "    • Backend:   http://localhost:8082" -ForegroundColor White
Write-Host "    • API Docs:  http://localhost:8082/docs" -ForegroundColor White
Write-Host ""
Write-Host "  💡 Next Steps:" -ForegroundColor Yellow
Write-Host "    1. Open http://localhost:3082 in your browser" -ForegroundColor White
Write-Host "    2. Explore property search with 250+ listings" -ForegroundColor White
Write-Host "    3. Test AI chat with comprehensive data" -ForegroundColor White
Write-Host "    4. Try saved searches, favorites, and analytics" -ForegroundColor White
Write-Host "    5. Experience ALL features with maximum demo data" -ForegroundColor White
Write-Host ""
Write-Host "  🛑 To stop containers: ./stop-docker.ps1 or docker compose down" -ForegroundColor DarkGray
Write-Host ""
