<#
.SYNOPSIS
    Stop AI Real Estate Assistant Docker containers. Zero arguments.
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot)
$ComposeFile = Join-Path $ProjectRoot "deploy/compose/docker-compose.yml"
$EnvFile = Join-Path $ProjectRoot ".env"

Write-Host "`n  Stopping containers..." -ForegroundColor Cyan
Push-Location $ProjectRoot
docker compose -f $ComposeFile --env-file $EnvFile down --remove-orphans 2>$null
Pop-Location
Write-Host "  OK  Stopped.`n" -ForegroundColor Green
