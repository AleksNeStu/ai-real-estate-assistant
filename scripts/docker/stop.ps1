<#
.SYNOPSIS
    Stop AI Real Estate Assistant Docker containers. Zero arguments.
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot)
$ComposeDir = Join-Path $ProjectRoot "deploy/compose"
$ComposeFile = Join-Path $ComposeDir "docker-compose.yml"
$EnvFile = Join-Path $ComposeDir ".env"

Write-Host "`n  Stopping containers..." -ForegroundColor Cyan
Push-Location $ComposeDir
docker compose -f $ComposeFile --env-file $EnvFile down --remove-orphans 2>$null
Pop-Location
Write-Host "  OK  Stopped.`n" -ForegroundColor Green
