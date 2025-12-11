# Installation Guide (V3)

This guide provides platform‑specific installation steps and best practices for running the AI Real Estate Assistant.

## Prerequisites
- Python 3.12+
- pip
- Git
- At least one API key: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GOOGLE_API_KEY`
- Optional: Ollama for local models

## Option A — Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Environment
cp .env.example .env
# Edit .env and add your API keys

# Start
docker-compose up -d
# Visit http://localhost:8501
```

## Option B — Local Installation

### Windows (PowerShell)
```powershell
# Clone repository
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Virtual environment
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# Dependencies
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

# Run
streamlit run app_modern.py
```

### macOS
```bash
# Clone
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Python 3.12 (Homebrew)
brew install python@3.12
python3.12 -m venv venv
source venv/bin/activate

# Dependencies
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

# Run
streamlit run app_modern.py
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3.12 python3.12-venv python3-pip git -y

# Clone
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Dependencies
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

# Run
streamlit run app_modern.py
```

## Configure API Keys

Set environment variables:

Windows (PowerShell):
```powershell
$env:OPENAI_API_KEY="your-openai-key"
$env:ANTHROPIC_API_KEY="your-anthropic-key"
$env:GOOGLE_API_KEY="your-google-key"
```

macOS/Linux:
```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"
```

Persistent (Windows):
```powershell
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "your-key", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your-key", "User")
[System.Environment]::SetEnvironmentVariable("GOOGLE_API_KEY", "your-key", "User")
```

Alternatively use `.streamlit/secrets.toml`.

## Local Models (Ollama)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.3

# Run Ollama service
ollama serve

# Run the app
streamlit run app_modern.py
```

In the app: select provider “Ollama (Local)” and choose your downloaded model.

## Screenshots (Playwright)

```bash
npx playwright install
npm run screenshots
# Optional: APP_URL=http://localhost:8502 npm run screenshots
```

## System Requirements
- OS: Windows 11, macOS 13+, Ubuntu 22.04+
- Python: 3.11+
- RAM: 4GB minimum (8GB recommended)
- Disk: ≥1GB free (more for ChromaDB)
- Browser: Chromium/Firefox/WebKit
