# Local Development Guide

This guide covers setting up a local development environment for the AI Real Estate Assistant project.

> **New here?** Start with the [5-Minute Quickstart](../QUICKSTART_5MIN.md) for the fastest path to a running app.
> This guide goes deeper into Docker profiles, local non-Docker setup, and development workflows.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Docker Development](#docker-development)
- [Local Development (Non-Docker)](#local-development-non-docker)
- [Bring Your Own Key (BYOK)](#bring-your-own-key-byok)
- [Development Workflow](#development-workflow)
- [IDE Setup](#ide-setup)
- [Validation](#validation)

---

## Prerequisites

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 20+ | Frontend runtime |
| Git | Latest | Version control |
| Docker | 20.10+ | Container runtime (optional) |
| Docker Compose | 2.0+ | Multi-container orchestration (optional) |

### Recommended Tools

| Tool | Purpose |
|------|---------|
| `uv` | Fast Python package manager |
| `pre-commit` | Git hooks for code quality |
| `Make` | Run development commands |

### Installing Prerequisites

#### Windows (PowerShell)

```powershell
# Install Python 3.12
winget install Python.Python.3.12

# Install Node.js 20
winget install OpenJS.NodeJS.LTS

# Install Docker Desktop
winget install Docker.DockerDesktop

# Install uv (Python package manager)
pip install uv

# Install pre-commit (optional)
uv pip install pre-commit
```

#### macOS (Homebrew)

```bash
# Install Python 3.12
brew install python@3.12

# Install Node.js 20
brew install node

# Install Docker Desktop
brew install --cask docker

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pre-commit
uv pip install pre-commit
```

#### Linux (Ubuntu/Debian)

```bash
# Install Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pre-commit
uv pip install pre-commit
```

---

## Quick Start

The fastest way to get started is using Docker:

```bash
# 1. Clone the repository
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# 2. Copy environment file
cp .env.example .env

# 3. Edit .env and add at least one LLM provider key:
#    OPENAI_API_KEY=sk-...
#    or ANTHROPIC_API_KEY=sk-ant-...
#    or GOOGLE_API_KEY=...

# 4. Start all services
make dev

# Or use Docker directly
docker compose -f deploy/compose/docker-compose.yml up --build
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Docker Development

Docker is the recommended development method as it provides consistent environments across all platforms.

### Starting Services

```bash
# Start all services (auto-detects GPU if available)
make dev

# Or use the start script
python scripts/start.py --mode auto

# Start with GPU support (if available)
python scripts/start.py --mode docker --docker-mode gpu

# Start with internet search capability
python scripts/start.py --mode docker --internet
```

### Docker Compose Profiles

The project supports multiple Docker Compose profiles:

| Profile | Services | Use Case |
|---------|----------|----------|
| default | backend, frontend, redis | Standard development |
| local-llm | + ollama | Local LLM support |
| gpu | + ollama_gpu | GPU-accelerated local LLM |
| internet | + searxng | Web search integration |

#### Starting with Specific Profiles

```bash
# CPU-only with local LLM
docker compose -f deploy/compose/docker-compose.yml --profile local-llm up

# GPU with local LLM (requires NVIDIA GPU)
docker compose -f deploy/compose/docker-compose.yml --profile local-llm --profile gpu up

# With internet search
docker compose -f deploy/compose/docker-compose.yml --profile internet up

# All features
docker compose -f deploy/compose/docker-compose.yml \
  --profile local-llm --profile gpu --profile internet up
```

### Docker Commands

```bash
# View logs
make docker-logs
# or
docker compose -f deploy/compose/docker-compose.yml logs -f

# Stop services
make docker-down
# or
docker compose -f deploy/compose/docker-compose.yml down

# Rebuild images
make docker-build
# or
docker compose -f deploy/compose/docker-compose.yml build

# Start only Redis (for caching/sessions)
docker compose -f deploy/compose/docker-compose.yml up -d redis

# Stop and remove all volumes (clean slate)
docker compose -f deploy/compose/docker-compose.yml down -v
```

### Docker Troubleshooting

**Issue: Container exits immediately**

```bash
# Check logs
docker compose logs backend

# Common issue: Missing API keys
# Solution: Edit .env and add required keys
```

**Issue: Port already in use**

```bash
# Find process using port
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # macOS/Linux

# Kill process or change port in docker-compose.yml
```

**Issue: GPU not detected**

```bash
# Verify NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Ensure NVIDIA Container Toolkit is installed
# See: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
```

---

## Local Development (Non-Docker)

For local development without Docker, you'll need to run services directly.

### Step 1: Environment Setup

```bash
# Copy environment file
cp .env.example .env

# Edit .env and configure:
# - ENVIRONMENT=development
# - API_ACCESS_KEY=dev-secret-key (or generate one)
# - At least one LLM provider key
```

### Step 2: Backend Setup

```bash
# Install Python dependencies
make setup
# or
python scripts/setup/bootstrap.py --dev

# Activate virtual environment (if not using uv)
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Start backend only
make dev-api
# or
python scripts/start.py --mode local --service backend
```

The backend will be available at http://localhost:8000

### Step 3: Frontend Setup

```bash
# Install Node dependencies (in apps/web/)
cd apps/web
npm install

# Start frontend only
npm run dev
# or from project root:
make dev-web
# or
python scripts/start.py --mode local --service frontend
```

The frontend will be available at http://localhost:3000

### Step 4: Optional Services

**Redis (for caching/sessions)**

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
```

**Ollama (for local LLM)**

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.2:3b

# Configure in .env
# OLLAMA_API_BASE=http://localhost:11434
```

---

## Bring Your Own Key (BYOK)

The AI Real Estate Assistant supports multiple LLM providers. You only need **one** key to get started.

### Supported Providers

| Provider | Environment Variable | Cost | Get Key |
|----------|---------------------|------|---------|
| OpenAI | `OPENAI_API_KEY` | Paid | <https://platform.openai.com/api-keys> |
| Anthropic | `ANTHROPIC_API_KEY` | Paid | <https://console.anthropic.com/settings/keys> |
| Google Gemini | `GOOGLE_API_KEY` | **Free tier** | <https://aistudio.google.com/app/apikey> |
| xAI Grok | `XAI_API_KEY` | Paid | <https://console.x.ai> |
| DeepSeek | `DEEPSEEK_API_KEY` | Paid | <https://platform.deepseek.com> |
| Ollama (local) | `OLLAMA_API_BASE` | **Free** | <https://ollama.com> |

### Zero-Cost Setup (Ollama)

Run entirely offline with no API keys:

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull llama3.2:3b

# 3. Configure .env
# DEFAULT_PROVIDER=ollama
# OLLAMA_API_BASE=http://localhost:11434

# 4. Start with Ollama profile (Docker)
docker compose -f deploy/compose/docker-compose.yml --profile local-llm up --build
```

### Port Reference

| Mode | Frontend | Backend API | API Docs |
|------|----------|-------------|----------|
| Docker (compose) | `localhost:3082` | `localhost:8082` | `localhost:8082/docs` |
| Local (native) | `localhost:3000` | `localhost:8000` | `localhost:8000/docs` |

Docker ports are configured in `deploy/compose/.env` (`WEB_PORT` and `BACKEND_PORT`).

---

## Development Workflow

### Installing Pre-Commit Hooks

```bash
# From project root
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Running Tests

```bash
# All tests
make test

# Backend tests only
make test-api
# or
cd apps/api
pytest tests/unit tests/integration --cov=. --cov-report=term -n auto

# Frontend tests only
make test-web
# or
cd apps/web
npm test

# Specific test file
pytest tests/unit/test_query_analyzer.py -v

# Specific test
pytest tests/unit/test_query_analyzer.py -k test_classify_intent -v
```

### Code Quality

```bash
# Lint all code
make lint

# Format all code
make format

# Run security scans
make security
```

### Recommended Workflow

1. Create a feature branch from `dev`
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature
   ```

2. Make changes and test locally
   ```bash
   make test
   make lint
   ```

3. Commit with conventional format
   ```bash
   git commit -m "feat(scope): description (Task #XX)"
   ```

4. Push and create PR to `dev`

---

## IDE Setup

### VS Code

Recommended extensions:

| Extension | Purpose |
|-----------|---------|
| Python | Python language support |
| Pylance | Python IntelliSense |
| ESLint | JavaScript/TypeScript linting |
| Prettier | Code formatting |
| GitLens | Git supercharged |
| Docker | Docker file support |

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/.next": true,
    "**/node_modules": true
  }
}
```

### PyCharm

1. Open project directory
2. Configure Python interpreter to use `.venv`
3. Enable "Use pytest" for tests
4. Configure code style to match Ruff (100 character line length)

---

## Validation

### Verify Backend

```bash
# Health check
curl http://localhost:8000/health

# Expected response
# {"status":"healthy","version":"4.0.0","timestamp":"...","uptime_seconds":...}

# API documentation
open http://localhost:8000/docs
```

### Verify Frontend

```bash
# Open browser
open http://localhost:3000

# Check for console errors
# Developer Tools > Console
```

### Run Full Test Suite

```bash
# Quick test
make ci-quick

# Full CI
make ci
```

---

## Next Steps

- Configure [Environment Variables](environment-setup.md)
- Learn about [Testing](testing.md)
- Prepare for [Deployment](deployment.md)
- Read [Architecture Documentation](../architecture/ARCHITECTURE.md)
