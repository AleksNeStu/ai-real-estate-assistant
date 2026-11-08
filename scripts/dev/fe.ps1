<#
.SYNOPSIS
    Run frontend only with logging and auto-dependencies.
#>
param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $root

# Setup logging
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logDir = Join-Path $root "artifacts\logs"
$logFile = Join-Path $logDir "fe-$timestamp.log"

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

Log "=== FE.PS1 STARTED (frontend only) ==="
Log "Log file: $logFile"
Log "Project root: $root"

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

# Detect available port
$frontendPort = Get-AvailablePort -StartPort 3000
Log "Frontend port: $frontendPort"

Log "Frontend dependencies ready. Starting frontend..."
Log "==========================================================="

# Run start.py
. (Join-Path $root "scripts\shared\resolve_python.ps1")
$invocation = Get-PythonInvocation -ProjectRoot $root

$pythonArgs = @($invocation.Args) + @(
    (Join-Path $root "scripts\start.py"),
    "--mode", "local",
    "--service", "frontend",
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

Log "=== FE.PS1 FINISHED ==="
