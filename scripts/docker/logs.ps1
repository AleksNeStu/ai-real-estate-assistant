<#
.SYNOPSIS
    Follow Docker container logs. Zero arguments. Ctrl+C to stop watching.
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot)
$ComposeFile = Join-Path $ProjectRoot "deploy/compose/docker-compose.yml"
$EnvFile = Join-Path $ProjectRoot ".env"

Write-Host "`n  Following logs (Ctrl+C to stop)..." -ForegroundColor Cyan
Push-Location $ProjectRoot
docker compose -f $ComposeFile --env-file $EnvFile logs -f
Pop-Location
