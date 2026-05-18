<#
.SYNOPSIS
    Full reset: stop containers, delete volumes. Zero arguments.
    Run start.ps1 afterwards to rebuild.
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot)
$ComposeFile = Join-Path $ProjectRoot "deploy/compose/docker-compose.yml"
$EnvFile = Join-Path $ProjectRoot ".env"

Write-Host "`n  Full reset — removing containers and data volumes..." -ForegroundColor Yellow
Push-Location $ProjectRoot
docker compose -f $ComposeFile --env-file $EnvFile down -v --remove-orphans 2>$null
Pop-Location
Write-Host "  OK  Cleaned. Run scripts/docker/start.ps1 to rebuild.`n" -ForegroundColor Green
