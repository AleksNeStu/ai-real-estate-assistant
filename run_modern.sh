#!/bin/bash

# Run the modern version of AI Real Estate Assistant

echo "🏠 Starting AI Real Estate Assistant - Modern Version (V3)"
echo "=================================================="
echo ""
echo "Features:"
echo "  ✓ Multiple AI model providers (OpenAI, Anthropic, Google, Ollama)"
echo "  ✓ Persistent ChromaDB vector storage"
echo "  ✓ Hybrid semantic search with MMR"
echo "  ✓ Type-safe Pydantic data models"
echo "  ✓ Modern Streamlit UI"
echo ""
echo "Starting application..."
echo ""

set -euo pipefail

# Ensure virtual environment exists (prefer Python 3.11)
if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment (preferring Python 3.11)..."
  if command -v python3.11 >/dev/null 2>&1; then
    python3.11 -m venv venv
  elif command -v py >/dev/null 2>&1; then
    py -3.11 -m venv venv || py -3 -m venv venv
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m venv venv
  elif command -v python >/dev/null 2>&1; then
    python -m venv venv
  else
    echo "Error: Python 3.11+ not found. Please install Python 3.11 and rerun."
    exit 1
  fi
fi

# Activate virtual environment (Linux/macOS or Windows Git Bash)
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
else
  echo "Could not find an activation script. If you're on Windows PowerShell, run:"
  echo "    .\\venv\\Scripts\\Activate.ps1"
  exit 1
fi

# Dependency installation with caching (skip if up-to-date)
REQ_FILE="requirements.txt"
HASH_FILE="venv/.requirements.sha256"

if [ -f "$REQ_FILE" ]; then
  REQ_HASH=$(python -c "import hashlib,sys;print(hashlib.sha256(open('$REQ_FILE','rb').read()).hexdigest())")
  EXISTING_HASH=""
  if [ -f "$HASH_FILE" ]; then
    EXISTING_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")
  fi

  if [ "$REQ_HASH" = "$EXISTING_HASH" ]; then
    echo "✓ Dependencies up-to-date (no reinstall)"
  else
    echo "Checking installed packages..."
    CHECK=$(python - <<'PY'
try:
    import streamlit, pandas, numpy, pydantic, langchain, chromadb
    print("OK")
except Exception as e:
    print("FAIL")
PY
)
    if [ "$CHECK" = "OK" ]; then
      echo "✓ Required packages already present; skipping reinstall"
      echo "$REQ_HASH" > "$HASH_FILE"
    else
      echo "Installing dependencies (first run or changed requirements)..."
      echo "Upgrading pip and setuptools..."
      python -m pip install --upgrade pip setuptools wheel --quiet
      echo "  [1/4] Installing numpy..."
      python -m pip install "numpy>=1.24.0,<2.0.0" --quiet
      echo "  [2/4] Installing pydantic-core..."
      python -m pip install --no-cache-dir "pydantic-core>=2.14.0,<3.0.0" --quiet
      echo "  [3/4] Installing pandas..."
      python -m pip install --no-cache-dir "pandas>=2.2.0,<2.3.0" --quiet
      echo "  [4/4] Installing remaining packages..."
      python -m pip install -r "$REQ_FILE" --quiet
      echo ""
      echo "✓ Dependencies installed successfully"
      echo "$REQ_HASH" > "$HASH_FILE"
    fi
  fi
fi

# Run the app using the venv Python
python -m streamlit run app_modern.py
