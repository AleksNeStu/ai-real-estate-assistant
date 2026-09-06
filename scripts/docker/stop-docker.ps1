<#
.SYNOPSIS
    Stop AI Real Estate Assistant Docker containers
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot)
$ComposeDir = Join-Path $ProjectRoot "deploy/compose"
$EnvFile = Join-Path $ComposeDir ".env"

Write-Host "`n  Stopping AI Real Estate Assistant..." -ForegroundColor Cyan
Push-Location $ComposeDir
docker compose down --remove-orphans 2>$null
Pop-Location
Write-Host "  OK  Stopped.`n" -ForegroundColor Green
