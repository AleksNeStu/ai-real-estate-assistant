<#
.SYNOPSIS
    Start AI Real Estate Assistant in Docker (Demo Mode)
.DESCRIPTION
    Quick start script for demo mode with MockLLM and seeded data.
    No API keys required for demo functionality.
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot)
$ComposeDir = Join-Path $ProjectRoot "deploy/compose"
$ComposeFile = Join-Path $ComposeDir "docker-compose.yml"
$EnvFile = Join-Path $ComposeDir ".env"

function Step($m) { Write-Host "`n  $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "  X   $m" -ForegroundColor Red; exit 1 }

Write-Host "`n  =====================================" -ForegroundColor Cyan
Write-Host "  AI Real Estate Assistant - Docker" -ForegroundColor Cyan
Write-Host "  Demo Mode Start" -ForegroundColor Cyan
Write-Host "  =====================================`n" -ForegroundColor Cyan

# ── Docker ────────────────────────────────────────────────────────────
Step "[1/5] Checking Docker..."
try { $null = docker info 2>&1; if ($LASTEXITCODE -ne 0) { throw } } catch {
    Fail "Docker is not running. Start Docker Desktop first."
}
Ok "Docker is running"

# ── .env ──────────────────────────────────────────────────────────────
Step "[2/5] Checking .env..."
if (-not (Test-Path $EnvFile)) {
    $EnvExample = Join-Path $ComposeDir ".env.example"
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Warn "Created .env from .env.example"
        Warn "Demo mode enabled by default"
    } else {
        Fail "No .env or .env.example found in deploy/compose/"
    }
}
Ok ".env exists"

# ── Demo Mode ────────────────────────────────────────────────────────
Step "[3/5] Enabling Demo Mode..."
$envContent = Get-Content $EnvFile -Raw
if ($envContent -notmatch "NEXT_PUBLIC_DEMO_MODE=true") {
    Warn "Enabling demo mode in .env..."
    $envContent = $envContent -replace "NEXT_PUBLIC_DEMO_MODE=.*", "NEXT_PUBLIC_DEMO_MODE=true"
    $envContent = $envContent -replace "SEED_ON_STARTUP=.*", "SEED_ON_STARTUP=true"
    $envContent = $envContent -replace "DEMO_MODE=.*", "DEMO_MODE=false"
    Set-Content $EnvFile $envContent -NoNewline
}
Ok "Demo mode configured"

# ── Build and start ───────────────────────────────────────────────────
Step "[4/5] Building and starting containers..."
Push-Location $ComposeDir
docker compose up -d --build 2>&1 | ForEach-Object {
    if ($_ -match "error|Error|ERROR|failed|FAILED") { Write-Host "  X $_" -ForegroundColor Red }
    else { Write-Host "  $_" -ForegroundColor DarkGray }
}
Pop-Location
if ($LASTEXITCODE -ne 0) { Fail "Docker compose failed." }
Ok "Containers started"

# ── Health check ──────────────────────────────────────────────────────
Step "[5/5] Waiting for health checks (up to 120s)..."
$BackendUrl = "http://localhost:8082"
$FrontendUrl = "http://localhost:3082"
$elapsed = 0; $bOk = $false; $fOk = $false

while ($elapsed -lt 120 -and -not ($bOk -and $fOk)) {
    Start-Sleep -Seconds 3; $elapsed += 3
    if (-not $bOk) { try { $r = Invoke-WebRequest -Uri "$BackendUrl/health" -TimeoutSec 3 -SkipHttpErrorCheck -ErrorAction Stop; if ($r.StatusCode -eq 200) { $bOk = $true; Ok "Backend:  $BackendUrl (${elapsed}s)" } } catch {} }
    if (-not $fOk) { try { $r = Invoke-WebRequest -Uri "$FrontendUrl/" -TimeoutSec 3 -SkipHttpErrorCheck -ErrorAction Stop; if ($r.StatusCode -eq 200) { $fOk = $true; Ok "Frontend:  $FrontendUrl (${elapsed}s)" } } catch {} }
    if (-not ($bOk -and $fOk)) { Write-Host "." -NoNewline -ForegroundColor DarkGray }
}
Write-Host ""

# ── Summary ───────────────────────────────────────────────────────────
Write-Host "`n  =====================================" -ForegroundColor Cyan
Write-Host "  🚀 Ready!" -ForegroundColor Green
Write-Host "  =====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend:  $FrontendUrl" -ForegroundColor Green
Write-Host "  Backend:   $BackendUrl" -ForegroundColor Green
Write-Host ""
Write-Host "  Demo Mode:  " -NoNewline -ForegroundColor Cyan
Write-Host "Enabled (toggleable via UI)" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Yellow
Write-Host "    • Open frontend in browser" -ForegroundColor White
Write-Host "    • Toggle demo mode ON/OFF via banner" -ForegroundColor White
Write-Host "    • Take screenshots for documentation" -ForegroundColor White
Write-Host ""
Write-Host "  Stop: ./stop-docker.ps1" -ForegroundColor DarkGray
Write-Host ""
