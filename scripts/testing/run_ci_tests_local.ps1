#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run CI tests locally to replicate GitHub Actions workflow

.DESCRIPTION
    This script runs the same test suite as CI/CD pipeline locally.
    It automatically detects the Python environment and runs tests in parallel.

.PARAMETER Parallel
    Enable parallel test execution (default: true)

.PARAMETER Coverage
    Generate coverage reports (default: false)

.PARAMETER ContinueOnError
    Continue running all tests even if some fail (default: false)
    Useful for seeing the full picture of all issues at once

.EXAMPLE
    .\scripts\run_ci_tests_local.ps1 -ContinueOnError
    Run all tests without stopping on failures

.EXAMPLE
    .\scripts\run_ci_tests_local.ps1 -Coverage
    Run tests with coverage reports

.EXAMPLE
    .\scripts\run_ci_tests_local.ps1 -Fast
    Run only fast tests
#>

param(
    [switch]$Parallel = $true,
    [switch]$Coverage = $false,
    [switch]$Fast = $false,
    [switch]$ContinueOnError = $false
)

$ErrorActionPreference = "Stop"
$StartTime = Get-Date

# Detect Python executable
$PYTHON = $null
$PossiblePaths = @(
    "apps\api\.venv312\Scripts\python.exe",  # Python 3.12 venv
    "apps\api\.venv\Scripts\python.exe",     # Default venv
    "python"                                  # System Python
)

foreach ($path in $PossiblePaths) {
    if (Test-Path $path -ErrorAction SilentlyContinue) {
        $PYTHON = $path
        break
    } elseif ($path -eq "python") {
        try {
            $version = & python --version 2>&1
            if ($version -match "Python 3\.1[2-9]") {
                $PYTHON = "python"
                break
            }
        } catch {
            continue
        }
    }
}

if (-not $PYTHON) {
    Write-Host "ERROR: Python 3.12+ not found!" -ForegroundColor Red
    Write-Host "Please create a virtual environment:" -ForegroundColor Yellow
    Write-Host "  cd apps\api" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv312" -ForegroundColor Yellow
    Write-Host "  .venv312\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Check Python version
$PythonVersion = & $PYTHON --version 2>&1
Write-Host "=== Running CI Tests Locally ===" -ForegroundColor Cyan
Write-Host "Python: $PythonVersion" -ForegroundColor Cyan
Write-Host "Parallel: $Parallel" -ForegroundColor Cyan
Write-Host "Coverage: $Coverage" -ForegroundColor Cyan
Write-Host "Fast mode: $Fast" -ForegroundColor Cyan
Write-Host "Continue on error: $ContinueOnError" -ForegroundColor Cyan
Write-Host ""

# Change to API directory
Push-Location apps\api

# Track failures
$FailedSteps = @()

try {
    # 1. Lint (ruff)
    Write-Host "[1/8] Running ruff linter..." -ForegroundColor Yellow
    & $PYTHON -m ruff check .
    if ($LASTEXITCODE -ne 0) {
        $FailedSteps += "Ruff linting"
        if (-not $ContinueOnError) {
            throw "Ruff linting failed!"
        }
        Write-Host "  FAILED (continuing...)" -ForegroundColor Red
    }

    # 2. RuleEngine test
    Write-Host "`n[2/8] Running RuleEngine test..." -ForegroundColor Yellow
    & $PYTHON -m pytest -q tests/integration/test_rule_engine_clean.py
    if ($LASTEXITCODE -ne 0) {
        $FailedSteps += "RuleEngine test"
        if (-not $ContinueOnError) {
            throw "RuleEngine test failed!"
        }
        Write-Host "  FAILED (continuing...)" -ForegroundColor Red
    }

    # 3. Forbidden tokens scan
    Write-Host "`n[3/8] Running forbidden tokens scan..." -ForegroundColor Yellow
    & $PYTHON ..\..\scripts\security\forbidden_tokens.py
    if ($LASTEXITCODE -ne 0) {
        $FailedSteps += "Forbidden tokens scan"
        if (-not $ContinueOnError) {
            throw "Forbidden tokens scan failed!"
        }
        Write-Host "  FAILED (continuing...)" -ForegroundColor Red
    }

    # 4. OpenAPI breaking-change detection
    Write-Host "`n[4/8] Running OpenAPI diff..." -ForegroundColor Yellow
    & $PYTHON ..\..\scripts\api\openapi_diff.py --baseline ..\..\docs\api-v1-baseline.json
    if ($LASTEXITCODE -ne 0) {
        $FailedSteps += "OpenAPI diff"
        if (-not $ContinueOnError) {
            throw "OpenAPI diff failed!"
        }
        Write-Host "  FAILED (continuing...)" -ForegroundColor Red
    }

    # 5. Alembic migration check
    Write-Host "`n[5/8] Running Alembic migration check..." -ForegroundColor Yellow
    & $PYTHON -m alembic check
    if ($LASTEXITCODE -ne 0) {
        $FailedSteps += "Alembic migration check"
        if (-not $ContinueOnError) {
            throw "Alembic migration check failed!"
        }
        Write-Host "  FAILED (continuing...)" -ForegroundColor Red
    }

    # 6. Unit tests
    Write-Host "`n[6/8] Running unit tests..." -ForegroundColor Yellow
    $UnitTestArgs = @("tests/unit", "-q")

    # Add maxfail only if NOT in ContinueOnError mode
    if (-not $ContinueOnError) {
        $UnitTestArgs += "--maxfail=5"
    } else {
        Write-Host "  (running ALL tests, no early exit)" -ForegroundColor Gray
    }

    if ($Parallel) {
        $UnitTestArgs += "-n", "auto"
        Write-Host "  (parallel execution enabled)" -ForegroundColor Gray
    }

    if ($Coverage) {
        $UnitTestArgs += "--cov=.", "--cov-report=xml", "--cov-report=term"
        Write-Host "  (coverage enabled)" -ForegroundColor Gray
    }

    if ($Fast) {
        $UnitTestArgs += "-m", "not slow"
        Write-Host "  (skipping slow tests)" -ForegroundColor Gray
    }

    & $PYTHON -m pytest @UnitTestArgs
    if ($LASTEXITCODE -ne 0) {
        $FailedSteps += "Unit tests"
        if (-not $ContinueOnError) {
            throw "Unit tests failed!"
        }
        Write-Host "  FAILED (continuing...)" -ForegroundColor Red
    }

    # 7. Integration tests
    Write-Host "`n[7/8] Running integration tests..." -ForegroundColor Yellow
    $IntegrationTestArgs = @("tests/integration", "-q")

    # Add maxfail only if NOT in ContinueOnError mode
    if (-not $ContinueOnError) {
        # No maxfail for integration tests by default
    } else {
        Write-Host "  (running ALL tests, no early exit)" -ForegroundColor Gray
    }

    if ($Parallel) {
        $IntegrationTestArgs += "-n", "auto"
        Write-Host "  (parallel execution enabled)" -ForegroundColor Gray
    }

    if ($Coverage) {
        $IntegrationTestArgs += "--cov=.", "--cov-report=xml", "--cov-report=term", "--cov-append"
        Write-Host "  (coverage enabled)" -ForegroundColor Gray
    }

    & $PYTHON -m pytest @IntegrationTestArgs
    if ($LASTEXITCODE -ne 0) {
        $FailedSteps += "Integration tests"
        if (-not $ContinueOnError) {
            throw "Integration tests failed!"
        }
        Write-Host "  FAILED (continuing...)" -ForegroundColor Red
    }

    # 8. Type check (mypy) - optional in fast mode
    if (-not $Fast) {
        Write-Host "`n[8/8] Running mypy type check..." -ForegroundColor Yellow
        Write-Host "  (errors are non-blocking)" -ForegroundColor Gray
        & $PYTHON -m mypy . --explicit-package-bases
        # Don't fail on mypy errors (continue-on-error: true in CI)
    } else {
        Write-Host "`n[8/8] Skipping mypy type check (fast mode)" -ForegroundColor Gray
    }

    $EndTime = Get-Date
    $Duration = $EndTime - $StartTime

    # Summary
    if ($FailedSteps.Count -eq 0) {
        Write-Host "`n=== All CI tests passed! ===" -ForegroundColor Green
    } else {
        Write-Host "`n=== Test run completed with failures ===" -ForegroundColor Yellow
        Write-Host "`nFailed steps ($($FailedSteps.Count)):" -ForegroundColor Red
        foreach ($step in $FailedSteps) {
            Write-Host "  ✗ $step" -ForegroundColor Red
        }

        if ($ContinueOnError) {
            Write-Host "`nNote: ContinueOnError mode was enabled - all tests were executed" -ForegroundColor Cyan
            Write-Host "Fix the issues above and re-run without -ContinueOnError flag" -ForegroundColor Cyan
        }
    }

    Write-Host "Total time: $($Duration.ToString('mm\:ss'))" -ForegroundColor Cyan

    if ($Coverage) {
        Write-Host "`nCoverage report saved to: coverage.xml" -ForegroundColor Cyan
    }

    # Exit with error if there were failures
    if ($FailedSteps.Count -gt 0) {
        Pop-Location
        exit 1
    }

} catch {
    Write-Host "`nERROR: $_" -ForegroundColor Red
    Pop-Location
    exit 1
} finally {
    Pop-Location
}
