<#
.SYNOPSIS
    Run the app locally (backend + frontend) with logging and auto-dependencies.
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
$logFile = Join-Path $logDir "run-$timestamp.log"

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

Log "=== RUN.PS1 STARTED ==="
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

# Check npm
Log "Checking npm..."
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Log "ERROR: npm is not installed. Install Node.js from: https://nodejs.org/"
    exit 1
}
Log "npm found: $(npm --version)"

# Clean corrupted root node_modules (npm workspace symlinks can break)
$rootNodeModules = Join-Path $root "node_modules"
if (Test-Path $rootNodeModules) {
    Log "Cleaning root node_modules (workspace symlinks)..."
    # Use cmd for more reliable deletion on Windows
    cmd /c "rmdir /s /q `"$rootNodeModules`"" 2>$null
    Remove-Item -Recurse -Force $rootNodeModules -ErrorAction SilentlyContinue
}

# Check apps/web/node_modules
$webNodeModules = Join-Path $root "apps\web\node_modules"
if (-not (Test-Path $webNodeModules)) {
    Log "apps/web/node_modules not found. Running npm install..."

    # Temporarily disable workspaces to avoid symlink issues on Windows
    $rootPackageJson = Join-Path $root "package.json"
    $rootPackageJsonBak = Join-Path $root "package.json.bak"
    $workspacesDisabled = $false

    if (Test-Path $rootPackageJson) {
        $pkg = Get-Content $rootPackageJson -Raw | ConvertFrom-Json
        if ($pkg.workspaces) {
            Log "Temporarily disabling workspaces..."
            Move-Item $rootPackageJson $rootPackageJsonBak -Force
            $pkg.PSObject.Properties.Remove('workspaces')
            $pkg | ConvertTo-Json -Depth 10 | Set-Content $rootPackageJson
            $workspacesDisabled = $true
        }
    }

    Push-Location (Join-Path $root "apps\web")
    npm install --legacy-peer-deps 2>&1 | ForEach-Object { Log $_ }
    Pop-Location

    # Restore workspaces
    if ($workspacesDisabled -and (Test-Path $rootPackageJsonBak)) {
        Log "Restoring workspaces..."
        Move-Item $rootPackageJsonBak $rootPackageJson -Force
    }

    if ($LASTEXITCODE -ne 0) {
        Log "ERROR: npm install failed"
        exit 1
    }
}

# Detect available ports
$backendPort = Get-AvailablePort -StartPort 8000
$frontendPort = Get-AvailablePort -StartPort 3000
Log "Backend port: $backendPort"
Log "Frontend port: $frontendPort"

Log "All dependencies ready. Starting app..."
Log "========================================"

# Run start.py
. (Join-Path $root "scripts\shared\resolve_python.ps1")
$invocation = Get-PythonInvocation -ProjectRoot $root

$pythonArgs = @($invocation.Args) + @(
    (Join-Path $root "scripts\start.py"),
    "--mode", "local",
    "--backend-port", $backendPort,
    "--frontend-port", $frontendPort
) + $Args

try {
    & $invocation.Python @pythonArgs 2>&1 | ForEach-Object { Log $_ }
}
catch {
    Log "ERROR: $($_.Exception.Message)"
    Log "Check log for details: $logFile"
    exit 1
}

Log "=== RUN.PS1 FINISHED ==="
