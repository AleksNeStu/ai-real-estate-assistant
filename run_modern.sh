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

# Upgrade pip and install dependencies
python -m pip install --upgrade pip wheel
if [ -f "requirements.txt" ]; then
  python -m pip install -r requirements.txt
fi

# Run the app using the venv Python
python -m streamlit run app_modern.py
