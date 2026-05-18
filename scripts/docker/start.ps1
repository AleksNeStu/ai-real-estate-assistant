<#
.SYNOPSIS
    Start AI Real Estate Assistant in Docker. Zero arguments.
.DESCRIPTION
    Builds and runs the full stack (backend + frontend + Redis).
    Checks Docker, validates .env, waits for health checks.
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot)
$ComposeFile = Join-Path $ProjectRoot "deploy/compose/docker-compose.yml"
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

function Step($m) { Write-Host "`n  $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  OK  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  !!  $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "  X   $m" -ForegroundColor Red; exit 1 }

# ── Docker ────────────────────────────────────────────────────────────
Step "[1/5] Checking Docker..."
try { $null = docker info 2>&1; if ($LASTEXITCODE -ne 0) { throw } } catch {
    Fail "Docker is not running. Start Docker Desktop first."
}
Ok "Docker is running"

# ── .env ──────────────────────────────────────────────────────────────
Step "[2/5] Checking .env..."
if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Warn "Created .env from .env.example"
        Warn "Add at least one LLM key (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY), then re-run."
        Start-Process notepad $EnvFile -Wait
        if (-not (Test-Path $EnvFile)) { Fail ".env was deleted." }
    } else {
        Fail "No .env or .env.example found."
    }
}
Ok ".env exists"

# ── Validate LLM key ─────────────────────────────────────────────────
Step "[3/5] Validating .env..."
$envContent = Get-Content $EnvFile -Raw
$hasLlm = @("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY", "DEEPSEEK_API_KEY", "ZAI_API_KEY") | Where-Object {
    $envContent -match "(?m)^$_=(?!$|your-|sk-your|REPLACE)"
}
if ($hasLlm) { Ok "LLM key found" } else { Warn "No LLM key — app will run in demo mode" }

# ── Build and start ───────────────────────────────────────────────────
Step "[4/5] Building and starting containers..."
Push-Location $ProjectRoot
docker compose -f $ComposeFile --env-file $EnvFile up -d --build 2>&1 | ForEach-Object {
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
    if (-not $fOk) { try { $r = Invoke-WebRequest -Uri "$FrontendUrl/" -TimeoutSec 3 -SkipHttpErrorCheck -ErrorAction Stop; if ($r.StatusCode -eq 200) { $fOk = $true; Ok "Frontend: $FrontendUrl (${elapsed}s)" } } catch {} }
    if (-not ($bOk -and $fOk)) { Write-Host "." -NoNewline -ForegroundColor DarkGray }
}
Write-Host ""

# ── Summary ───────────────────────────────────────────────────────────
Write-Host "`n  =====================================" -ForegroundColor Cyan
Write-Host "  AI Real Estate Assistant — Docker" -ForegroundColor Cyan
Write-Host "  =====================================" -ForegroundColor Cyan
if ($bOk) { Write-Host "  Backend:   $BackendUrl" -ForegroundColor Green }
else      { Write-Host "  Backend:   $BackendUrl (still starting...)" -ForegroundColor Yellow }
if ($fOk) { Write-Host "  Frontend:  $FrontendUrl" -ForegroundColor Green }
else      { Write-Host "  Frontend:  $FrontendUrl (still starting...)" -ForegroundColor Yellow }
Write-Host ""
Write-Host "  scripts/docker/stop.ps1   — stop" -ForegroundColor DarkGray
Write-Host "  scripts/docker/logs.ps1   — watch logs" -ForegroundColor DarkGray
Write-Host "  scripts/docker/reset.ps1  — full clean" -ForegroundColor DarkGray
Write-Host ""
