<#
.SYNOPSIS
    APS1: Launch AI Real Estate Assistant in Docker (Demo Mode)
.DESCRIPTION
    First autonomous process - launches Docker containers with demo mode enabled.
    No API keys required for demo functionality.
.NOTES
    - Run this script first to start Docker containers
    - Then run APS2_Generate_Data.ps1 to populate with comprehensive data
    - Frontend: http://localhost:3082
    - Backend:  http://localhost:8082
#>
$ErrorActionPreference = "Stop"
# Get project root (go up two levels from scripts/demo/ to project root)
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ComposeDir = Join-Path $ProjectRoot "deploy/compose"
$EnvFile = Join-Path $ComposeDir ".env"

function Step($m) { Write-Host "`n  $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  ✅  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  ⚠️  $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "  ❌  $m" -ForegroundColor Red; exit 1 }

Write-Host "`n  ╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     APS1: AI Real Estate Assistant - Docker Launch     ║" -ForegroundColor Cyan
Write-Host  "  ╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Validate Environment ────────────────────────────────────────────────
Step "[1/5] Validating environment..."
if (-not (Test-Path $ComposeDir)) {
    Fail "Docker compose directory not found: $ComposeDir"
}
Ok "Project structure validated"

# ── Check Docker ───────────────────────────────────────────────────────
Step "[2/5] Checking Docker..."
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
} catch {
    Fail "Docker is not running. Start Docker Desktop first."
}
Ok "Docker is running"

# �── Configure Environment ───────────────────────────────────────────────
Step "[3/5] Configuring demo mode..."
if (-not (Test-Path $EnvFile)) {
    $EnvExample = Join-Path $ComposeDir ".env.example"
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Warn "Created .env from .env.example"
    } else {
        Fail "No .env or .env.example found in deploy/compose/"
    }
}

# Enable demo mode
$envContent = Get-Content $EnvFile -Raw
$envContent = $envContent -replace "NEXT_PUBLIC_DEMO_MODE=.*", "NEXT_PUBLIC_DEMO_MODE=true"
$envContent = $envContent -replace "SEED_ON_STARTUP=.*", "SEED_ON_STARTUP=true"
$envContent = $envContent -replace "DEMO_MODE=.*", "DEMO_MODE=true"
Set-Content $EnvFile $envContent -NoNewline
Ok "Demo mode configured (NEXT_PUBLIC_DEMO_MODE=true, SEED_ON_STARTUP=true, DEMO_MODE=true)"

# ── Build and Start ─────────────────────────────────────────────────────
Step "[4/5] Building and starting containers..."
$ComposeFile = Join-Path $ComposeDir "docker-compose.yml"

# Always builds, but Docker uses layer caching:
# - Nothing changed → ~5 sec (all cached)
# - Source changed → ~10 sec (only new layers)
# - Dependencies changed → ~2 min (rebuilds deps)
docker compose -f $ComposeFile up -d --build 2>&1 | ForEach-Object {
    if ($_ -match "error|Error|ERROR|failed|FAILED") { Write-Host "  ❌ $_" -ForegroundColor Red }
    else { Write-Host "  $_" -ForegroundColor DarkGray }
}
if ($LASTEXITCODE -ne 0) { Fail "Docker compose failed." }
Ok "Containers started successfully"

# ── Health Check with Live Logs ──────────────────────────────────────────
Step "[5/5] Waiting for services to be healthy..."
$BackendUrl = "http://localhost:8082"
$FrontendUrl = "http://localhost:3082"
$elapsed = 0; $bOk = $false; $fOk = $false
$lastLogTime = (Get-Date).AddSeconds(-3).ToString("yyyy-MM-ddTHH:mm:ss")
$suppressPattern = "Persistent vector store|sentry-sdk|bcrypt|greenlet|passlib|Centralized error|error_handler|middleware"

while ($elapsed -lt 180 -and -not ($bOk -and $fOk)) {
    Start-Sleep -Seconds 3; $elapsed += 3

    # Fetch recent backend logs and display meaningful progress
    $now = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")
    $newLogs = docker logs --since $lastLogTime ai-backend 2>&1
    $lastLogTime = $now

    $shownLog = $false
    $newLogs | ForEach-Object {
        $line = $_.ToString().Trim()
        if ($line -and $line -notmatch $suppressPattern) {
            # Color-code by severity/content
            if ($line -match "ERROR|Traceback|failed|OOM|Killed") {
                Write-Host "  $($elapsed)s — $line" -ForegroundColor Red; $shownLog = $true
            } elseif ($line -match "WARNING") {
                if ($line -match "seed failed|Auto-seed failed") {
                    Write-Host "  $($elapsed)s — $line" -ForegroundColor Yellow; $shownLog = $true
                }
            } elseif ($line -match "SEED|seed|generat|Generat|batch|Added|complet|Complet|Demo|DEMO|data generat") {
                # Extract message from JSON or loguru format
                $msg = $line
                if ($line -match '"message":\s*"([^"]+)"') { $msg = $Matches[1] }
                elseif ($line -match '\|\s*INFO\s*\|.*\|\s*(.+)') { $msg = $Matches[1].Trim() }
                if ($msg.Length -gt 100) { $msg = $msg.Substring(0, 100) + "..." }
                $ts = "$elapsed"
                Write-Host "  $($ts)s - $msg" -ForegroundColor Cyan; $shownLog = $true
            }
        }
    }

    if (-not $shownLog) { Write-Host "." -NoNewline -ForegroundColor DarkGray }

    # Check health endpoints
    if (-not $bOk) {
        try {
            $r = Invoke-WebRequest -Uri "$BackendUrl/health" -TimeoutSec 3 -SkipHttpErrorCheck -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                $bOk = $true
                Ok "Backend:  $BackendUrl ($($elapsed)s)"
            }
        } catch {}
    }
    if (-not $fOk) {
        try {
            $r = Invoke-WebRequest -Uri "$FrontendUrl/" -TimeoutSec 3 -SkipHttpErrorCheck -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                $fOk = $true
                Ok "Frontend:  $FrontendUrl ($($elapsed)s)"
            }
        } catch {}
    }
}
Write-Host ""

if (-not $bOk) { Fail "Backend did not become healthy within 180s. Check: docker logs ai-backend" }
if (-not $fOk) { Fail "Frontend did not become healthy within 180s. Check: docker logs ai-frontend" }

# ── Summary ───────────────────────────────────────────────────────────────
Write-Host "`n  ╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║              🚀 APS1 Complete!                       ║" -ForegroundColor Cyan
Write-Host "  ╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ✅ Docker containers running successfully" -ForegroundColor Green
Write-Host "  ✅ Demo mode enabled" -ForegroundColor Green
Write-Host "  ✅ Services healthy:" -ForegroundColor Green
Write-Host "    • Frontend:  $FrontendUrl" -ForegroundColor White
Write-Host "    • Backend:   $BackendUrl" -ForegroundColor White
Write-Host ""
Write-Host "  📋 NEXT STEP:" -ForegroundColor Yellow
Write-Host "    Run APS2_Generate_Data.ps1 to populate database with comprehensive demo data" -ForegroundColor White
Write-Host ""
Write-Host "  🛑 To stop: ./stop-docker.ps1 or docker compose down" -ForegroundColor DarkGray
Write-Host ""
