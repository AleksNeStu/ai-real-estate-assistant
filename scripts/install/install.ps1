# One command from nothing to a running demo (Windows).
#
# The README quick start is eight lines: clone, copy the .env, make the data
# directories, bring the compose stack up, wait. This script is those eight
# lines, with the two things a person gets wrong handled for them - the
# secrets in the .env are generated rather than left as placeholders, and the
# script waits for the health check instead of telling you to.
#
# It needs Docker and Git, and it needs no API key: the stack starts in demo
# mode and the assistant answers with the built-in demo model until you put a
# provider key in the .env.
#
# It is reachable before the repository is cloned:
#
#   irm https://raw.githubusercontent.com/AleksNeStu/ai-real-estate-assistant/main/scripts/install/install.ps1 | iex
#
# Optional environment variables:
#   AIRE_HOME       where the checkout goes (default: .\ai-real-estate-assistant)
#   AIRE_TIMEOUT    seconds to wait for the health check (default: 300)
#
#Requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$RepoUrl = 'https://github.com/AleksNeStu/ai-real-estate-assistant.git'
$RepoName = 'ai-real-estate-assistant'
$TargetDir = if ($env:AIRE_HOME) { $env:AIRE_HOME } else { Join-Path (Get-Location).Path $RepoName }
$Timeout = if ($env:AIRE_TIMEOUT) { [int]$env:AIRE_TIMEOUT } else { 300 }
$ComposeFile = 'deploy/compose/docker-compose.yml'
$EnvFile = 'deploy/compose/.env'
$EnvExample = 'deploy/compose/.env.example'
$DataDirs = @('chroma_db', 'data/audit', '.preferences', '.notifications', '.sessions')

function Write-Step { param([string]$Message) Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Write-Info { param([string]$Message) Write-Host "    $Message" }
function Stop-Install {
    param([string]$Reason)
    Write-Host "`nInstallation failed: $Reason" -ForegroundColor Red
    Write-Host "`nTo finish it by hand, from the checkout:" -ForegroundColor Yellow
    Write-Host "  cd $TargetDir"
    Write-Host "  copy $EnvExample $EnvFile      # only if the .env is missing"
    Write-Host "  New-Item -ItemType Directory -Force deploy/compose\chroma_db,deploy/compose\data\audit,deploy/compose\.preferences,deploy/compose\.notifications,deploy/compose\.sessions"
    Write-Host "  docker compose -f $ComposeFile up --build -d"
    exit 1
}

function New-RandomHex {
    param([int]$Bytes = 16)
    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
    return -join ($buffer | ForEach-Object { $_.ToString('x2') })
}

function Test-CommandExists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Step 'Checking the tools'
if (-not (Test-CommandExists 'docker')) { Stop-Install 'docker is required and was not found on the PATH.' }
if (-not (Test-CommandExists 'git')) { Stop-Install 'git is required and was not found on the PATH.' }
try {
    docker info *> $null
} catch {
    Stop-Install 'Docker is installed but not running. Start Docker Desktop and run this again.'
}
Write-Info (docker --version)

# ---------------------------------------------------------------- the checkout
Write-Step 'Preparing the checkout'
if (Test-Path (Join-Path $TargetDir '.git')) {
    Write-Info "reusing $TargetDir"
} elseif (Test-Path $TargetDir) {
    Stop-Install "$TargetDir exists and is not a checkout. Move it aside, or set AIRE_HOME to another directory."
} else {
    Write-Info "cloning into $TargetDir"
    git clone --depth 1 $RepoUrl $TargetDir
    if ($LASTEXITCODE -ne 0) { Stop-Install 'the clone failed - check the network and try again.' }
}
Set-Location $TargetDir
if (-not (Test-Path $ComposeFile)) { Stop-Install "$ComposeFile is missing from the checkout." }

# -------------------------------------------------------------------- the .env
Write-Step 'Preparing the environment file'
if (Test-Path $EnvFile) {
    $backup = "$EnvFile.backup-$(Get-Date -Format 'yyyyMMddHHmmss')"
    Copy-Item $EnvFile $backup
    Write-Info "an .env already existed - it was kept, and a copy is at $backup"
} else {
    if (-not (Test-Path $EnvExample)) { Stop-Install "$EnvExample is missing from the checkout." }
    # Written to a temporary file and moved into place, so an interrupted run
    # never leaves a half-written .env behind.
    $tmpEnv = "$EnvFile.tmp"
    Copy-Item $EnvExample $tmpEnv
    $content = Get-Content $tmpEnv -Raw
    $apiKey = New-RandomHex
    $pgPassword = New-RandomHex
    # The placeholders in the example are literal - a stack started with them
    # would carry a public secret and a public database password.
    $content = $content -replace '(?m)^API_ACCESS_KEY=.*$', "API_ACCESS_KEY=$apiKey"
    $content = $content -replace '(?m)^POSTGRES_PASSWORD=.*$', "POSTGRES_PASSWORD=$pgPassword"
    $content = $content -replace '(?m)^DATABASE_URL=.*$', "DATABASE_URL=postgresql+asyncpg://sprav_dev:${pgPassword}@postgres:5432/realestate_db"
    $content = $content -replace '(?m)^SEARXNG_SECRET=.*$', "SEARXNG_SECRET=$(New-RandomHex)"
    # The JWT secret is commented out in the example; it is filled in anyway,
    # so uncommenting the line does not expose a published secret.
    $content = $content -replace 'REPLACE_WITH_SECURE_JWT_SECRET_32_CHARS', (New-RandomHex)
    # The demo answers with the built-in model, so the stack starts with no
    # provider key at all.
    if ($content -notmatch '(?m)^DEMO_LLM_MODE=') {
        $content += "`n# Set by the installer: the assistant answers with the built-in demo`n# model, so no provider key is needed. Put a key in MINIMAX_API_KEY and set`n# this to false to use a real model.`nDEMO_LLM_MODE=true`n"
    }
    Set-Content -Path $tmpEnv -Value $content -NoNewline -Encoding utf8
    Move-Item -Path $tmpEnv -Destination $EnvFile -Force
    Write-Info "wrote $EnvFile with a generated API key and database password"
}

# ------------------------------------------------------------- the data dirs
Write-Step 'Creating the data directories'
foreach ($dir in $DataDirs) {
    $path = Join-Path 'deploy/compose' $dir
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}
Write-Info 'the state directories are in place'

# ---------------------------------------------------------------- the stack
Write-Step 'Starting the stack (the first build takes a few minutes)'
docker compose -f $ComposeFile up --build -d
if ($LASTEXITCODE -ne 0) { Stop-Install 'docker compose failed - the output above says why.' }

$envLines = Get-Content $EnvFile
$backendPort = ($envLines | Where-Object { $_ -match '^BACKEND_HOST_PORT=' } | Select-Object -Last 1) -replace '^BACKEND_HOST_PORT=', ''
$frontendPort = ($envLines | Where-Object { $_ -match '^FRONTEND_HOST_PORT=' } | Select-Object -Last 1) -replace '^FRONTEND_HOST_PORT=', ''
if (-not $backendPort) { $backendPort = '8082' }
if (-not $frontendPort) { $frontendPort = '3082' }

Write-Step 'Waiting for the backend to answer'
$elapsed = 0
$healthy = $false
while ($elapsed -lt $Timeout) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$backendPort/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) { $healthy = $true; break }
    } catch {
        # not up yet
    }
    Start-Sleep -Seconds 3
    $elapsed += 3
    if ($elapsed % 30 -eq 0) { Write-Info "still starting ($elapsed s)..." }
}
if (-not $healthy) {
    Stop-Install "the backend did not answer /health within $Timeout s. Check the logs with: docker compose -f $ComposeFile logs -f backend"
}

Write-Step 'It is running'
Write-Host ''
Write-Host "    Frontend   http://localhost:$frontendPort"
Write-Host "    API docs   http://localhost:$backendPort/docs"
Write-Host "    Health     http://localhost:$backendPort/health"
Write-Host ''
Write-Host '    The assistant answers with the built-in demo model. To use a real one,'
Write-Host "    put a provider key in $EnvFile and set DEMO_LLM_MODE=false."
Write-Host ''
Write-Host "    Stop it with: docker compose -f $ComposeFile down"
Write-Host ''
