<#
.SYNOPSIS
    Show logs from AI Real Estate Assistant Docker containers
.DESCRIPTION
    Displays logs from all running containers.
    Arguments: backend, frontend, redis (optional, shows all if omitted)
.EXAMPLE
    .\logs-docker.ps1          # Show all logs
    .\logs-docker.ps1 backend   # Show backend logs only
#>
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path (Split-Path $PSScriptRoot)
$ComposeDir = Join-Path $ProjectRoot "deploy/compose"

$service = if ($args.Count -gt 0) { $args[0] } else { "" }

Write-Host "`n  Showing logs for: " -NoNewline -ForegroundColor Cyan
if ($service) { Write-Host "$service" -ForegroundColor Yellow } else { Write-Host "all services" -ForegroundColor Yellow }
Write-Host " (Ctrl+C to exit)`n" -ForegroundColor DarkGray

Push-Location $ComposeDir
if ($service) {
    docker compose logs -f $service
} else {
    docker compose logs -f
}
Pop-Location
