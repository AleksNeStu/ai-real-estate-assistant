<#
.SYNOPSIS
    Run backend only with logging and auto-dependencies.
#>
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

# Setup logging
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logDir = Join-Path $root "artifacts\logs"
$logFile = Join-Path $logDir "be-$timestamp.log"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

function Log {
    param([string]$msg)
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

function Get-AvailablePort {
    param([int]$StartPort)
    $port = $StartPort
    while ($port -lt ($StartPort + 100)) {
        $inUse = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if (-not $inUse) { return $port }
        $port++
    }
    return $StartPort
}

Log "=== BE.PS1 STARTED (backend only) ==="
Log "Log file: $logFile"
Log "Project root: $root"

# Check uv
Log "Checking uv..."
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Log "ERROR: uv is not installed. Install with: pip install uv"
    Log "See: https://docs.astral.sh/uv/"
    exit 1
}
Log "uv found: $(uv --version)"

# Check .venv
$venvPath = Join-Path $root ".venv"
if (-not (Test-Path $venvPath)) {
    Log ".venv not found. Running bootstrap..."
    python scripts/setup/bootstrap.py --dev 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) {
        Log "ERROR: Bootstrap failed"
        exit 1
    }
}

# Detect available port
$backendPort = Get-AvailablePort -StartPort 8000
Log "Backend port: $backendPort"

Log "Backend dependencies ready. Starting backend..."
Log "========================================================="

# Run start.py
. (Join-Path $root "scripts\shared\resolve_python.ps1")
$invocation = Get-PythonInvocation -ProjectRoot $root

$pythonArgs = @($invocation.Args) + @(
    (Join-Path $root "scripts\start.py"),
    "--mode", "local",
    "--service", "backend",
    "--backend-port", $backendPort
) + $Args

try {
    & $invocation.Python @pythonArgs 2>&1 | ForEach-Object { Log $_ }
}
catch {
    Log "ERROR: $($_.Exception.Message)"
    Log "Check log for details: $logFile"
    exit 1
}

Log "=== BE.PS1 FINISHED ==="
