# AI Real Estate Assistant - Windows PowerShell Launcher
# For Windows users to easily run the modern version

Write-Host "🏠 AI Real Estate Assistant - Modern Version (V3)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Features:" -ForegroundColor Green
Write-Host "  ✓ Multiple AI model providers (OpenAI, Anthropic, Google, Ollama)"
Write-Host "  ✓ Persistent ChromaDB vector storage"
Write-Host "  ✓ Hybrid semantic search with MMR"
Write-Host "  ✓ Type-safe Pydantic data models"
Write-Host "  ✓ Modern Streamlit UI with Dark/Light themes"
Write-Host ""

# Stop on errors
$ErrorActionPreference = "Stop"

# Check if Python 3.11+ is installed
function Get-PythonCommand {
    $pythonCommands = @("py -3.11", "py -3", "python3.11", "python3", "python")

    foreach ($cmd in $pythonCommands) {
        try {
            $version = & $cmd.Split()[0] $cmd.Split()[1..($cmd.Split().Count)] --version 2>$null
            if ($version -match "Python 3\.1[1-9]") {
                return $cmd
                }
        } catch {
            continue
        }
    }
    return $null
}

$pythonCmd = Get-PythonCommand

if (-not $pythonCmd) {
    Write-Host "❌ Error: Python 3.11+ not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.11 or higher from:" -ForegroundColor Yellow
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installation, restart PowerShell and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found Python: $pythonCmd" -ForegroundColor Green
Write-Host ""

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $pythonCmd.Split()[0] $pythonCmd.Split()[1..($pythonCmd.Split().Count)] -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
    Write-Host ""
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

if (-not $?) {
    Write-Host "❌ Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "If you see an execution policy error, run:" -ForegroundColor Yellow
    Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Cyan
    exit 1
}

Write-Host "✓ Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Dependency installation with caching (skip if up-to-date)
$reqFile = "requirements.txt"
$hashFile = "venv\.requirements.sha256"

if (Test-Path $reqFile) {
    # Compute SHA256 of requirements.txt
    try {
        $reqHash = (Get-FileHash -Algorithm SHA256 -Path $reqFile).Hash
    } catch {
        $reqHash = ""
    }

    $existingHash = ""
    if (Test-Path $hashFile) {
        try { $existingHash = Get-Content $hashFile -ErrorAction SilentlyContinue } catch { $existingHash = "" }
    }

    if ($reqHash -ne "" -and $reqHash -eq $existingHash) {
        Write-Host "✓ Dependencies up-to-date (no reinstall)" -ForegroundColor Green
    } else {
        Write-Host "Checking installed packages..." -ForegroundColor Yellow
        $check = python -c "import streamlit, pandas, numpy, pydantic, langchain, chromadb; print('OK')" 2>&1
        if ($check -match "OK") {
            Write-Host "✓ Required packages already present; skipping reinstall" -ForegroundColor Green
            if ($reqHash -ne "") { $reqHash | Out-File -FilePath $hashFile -Encoding ascii }
        } else {
            Write-Host "Installing dependencies (first run or changed requirements)..." -ForegroundColor Yellow
            Write-Host "Upgrading pip and setuptools..." -ForegroundColor Gray
            python -m pip install --upgrade pip setuptools wheel --quiet

            Write-Host "  [1/4] Installing numpy..." -ForegroundColor Gray
            python -m pip install "numpy>=1.24.0,<2.0.0" --quiet

            Write-Host "  [2/4] Installing pydantic-core..." -ForegroundColor Gray
            python -m pip install --no-cache-dir "pydantic-core>=2.14.0,<3.0.0" --quiet

            Write-Host "  [3/4] Installing pandas..." -ForegroundColor Gray
            python -m pip install --no-cache-dir "pandas>=2.2.0,<2.3.0" --quiet

            Write-Host "  [4/4] Installing remaining packages..." -ForegroundColor Gray
            python -m pip install -r $reqFile --quiet

            if ($LASTEXITCODE -ne 0) {
                Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
                Write-Host "" 
                Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
                Write-Host "1. Ensure Microsoft C++ Build Tools are installed" -ForegroundColor Yellow
                Write-Host "   Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Cyan
                Write-Host "2. Try manual installation:" -ForegroundColor Yellow
                Write-Host "   python -m pip install --no-cache-dir -r requirements.txt" -ForegroundColor Cyan
                Write-Host "3. See README.md Troubleshooting section" -ForegroundColor Yellow
                exit 1
            }

            # Verify critical imports
            Write-Host "" 
            Write-Host "Verifying critical packages..." -ForegroundColor Yellow
            $verifyResult = python -c "import numpy; import pandas; import pydantic; print('OK')" 2>&1
            if ($verifyResult -match "OK") {
                Write-Host "✓ All critical packages imported successfully" -ForegroundColor Green
                Write-Host "  ✓ numpy" -ForegroundColor Gray
                Write-Host "  ✓ pandas" -ForegroundColor Gray
                Write-Host "  ✓ pydantic" -ForegroundColor Gray
            } else {
                Write-Host "⚠️  Warning: Import verification failed" -ForegroundColor Yellow
                Write-Host "The app may not work correctly. Check README.md Troubleshooting section." -ForegroundColor Yellow
                Write-Host "" 
                Write-Host "Error details:" -ForegroundColor Red
                Write-Host $verifyResult -ForegroundColor Red
            }
            Write-Host "" 

            if ($reqHash -ne "") { $reqHash | Out-File -FilePath $hashFile -Encoding ascii }
        }
    }
} else {
    Write-Host "⚠️  Warning: requirements.txt not found" -ForegroundColor Yellow
    Write-Host "" 
}

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  Warning: .env file not found" -ForegroundColor Yellow
    Write-Host "Copy .env.example to .env and add your API keys:" -ForegroundColor Yellow
    Write-Host "  Copy-Item .env.example .env" -ForegroundColor Cyan
    Write-Host "  Then edit .env with your API keys" -ForegroundColor Cyan
    Write-Host ""
}

# Run the application
Write-Host "🚀 Starting application..." -ForegroundColor Green
Write-Host "The app will open in your browser at: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the application" -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

python -m streamlit run app_modern.py
