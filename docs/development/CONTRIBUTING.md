# Contributing to AI Real Estate Assistant

Thank you for your interest in contributing to the AI Real Estate Assistant! This document provides guidelines and standards for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Documentation](#documentation)

## 🤝 Code of Conduct

### Our Standards

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other contributors

## 🚀 Getting Started

### Prerequisites

- Python 3.12 or higher
- Node.js 18+ and npm
- Git
- API keys for at least one LLM provider (OpenAI, Anthropic, etc.)

### Initial Setup

1. **Fork the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-real-estate-assistant.git
   cd ai-real-estate-assistant
   ```

2. **Backend Setup (FastAPI)**
   ```bash
   # Install uv (fast Python package manager)
   pip install uv

   cd apps/api
   uv venv venv
   # Windows:
   .\venv\Scripts\Activate.ps1
   # Linux/Mac:
   source venv/bin/activate

   uv pip install -r requirements.txt
   ```

3. **Frontend Setup (Next.js)**
   ```bash
   cd apps/web
   npm install
   ```

4. **Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## 💻 Development Setup

### Project Structure

```
ai-real-estate-assistant/
├── apps/
│   ├── api/                 # FastAPI backend (Python)
│   │   ├── api/             # Routers & endpoints
│   │   ├── agents/          # AI agents (Hybrid, Tools)
│   │   ├── models/          # LLM Provider Factory
│   │   ├── data/            # Data providers (CSV, API)
│   │   ├── vector_store/    # ChromaDB integration
│   │   └── tests/           # Pytest suite
│   └── web/                 # Next.js frontend
├── deploy/
│   ├── docker/              # Dockerfiles
│   └── compose/             # docker-compose files
├── scripts/
│   ├── ci/                  # CI/CD scripts
│   ├── dev/                 # Development scripts
│   ├── docker/              # Docker utilities
│   ├── docs/                # Doc generators
│   └── security/            # Security scanning
├── docs/                    # Documentation
└── Makefile                 # Quick commands (make help)
```

### Running Locally

Using the unified launcher (recommended):
```bash
python scripts/start.py --mode local
```

Or run services individually:

1. **Backend**
   ```bash
   cd apps/api
   uvicorn api.main:app --reload --port 8000
   ```

2. **Frontend**
   ```bash
   cd apps/web
   npm run dev
   # Runs on http://localhost:3000
   ```

Or use Makefile targets:
```bash
make dev        # Start both services
make dev-api    # Backend only
make dev-web    # Frontend only
```

## 📝 Code Standards

### Python (Backend)
- **Style**: Follow PEP 8.
- **Linting**: We use `ruff` for linting and formatting.
  ```bash
  cd apps/api
  ruff check .
  ruff format .
  ```
- **Type Hints**: Mandatory for all function signatures.
- **Docstrings**: Google style.

### TypeScript/React (Frontend)
- **Style**: Prettier + ESLint.
- **Components**: Functional components with hooks.
- **UI**: Use Shadcn UI components from `src/components/ui`.

## 🧪 Testing Guidelines

### Backend (Pytest)
```bash
cd apps/api

# Run all tests
python -m pytest

# Run specific category
python -m pytest tests/unit
python -m pytest tests/integration
```

### Frontend (Jest)
```bash
cd apps/web
npm test
```

### Using Makefile
```bash
make test       # Run all tests
make test-api   # Backend only
make test-web   # Frontend only
```

### CI Parity (GitHub Actions)
Run the same checks locally before opening a PR:
```bash
cd apps/api
python -m pip install -r requirements.txt
python -m pip install pytest pytest-asyncio pytest-cov pytest-xdist pytest-timeout ruff mypy httpx types-requests
python -m ruff check .
python -m mypy
python -m pytest -q tests/integration/test_rule_engine_clean.py
python ../../scripts/docs/export_openapi.py --check
python ../../scripts/docs/generate_api_reference.py --check
python -m pytest tests/unit --cov=. --cov-report=xml --cov-report=term -n auto
python ../../scripts/ci/coverage_gate.py diff --coverage-xml coverage.xml --min-coverage 90 --exclude tests/* --exclude scripts/* --exclude workflows/*
python ../../scripts/ci/coverage_gate.py critical --coverage-xml coverage.xml --min-coverage 90 --include api/*.py --include api/routers/*.py --include rules/*.py --include models/provider_factory.py --include models/user_model_preferences.py --include config/*.py
python -m pytest tests/integration --cov=. --cov-report=xml --cov-report=term -n auto
python ../../scripts/ci/coverage_gate.py diff --coverage-xml coverage.xml --min-coverage 70 --exclude tests/* --exclude scripts/* --exclude workflows/*
```

**A changed router line needs a test that calls the handler directly.** The
changed-lines gate compares your changed lines against the coverage report,
and a request handler runs in its own asyncio task — the coverage tracer
does not come back after that task suspends, so the lines of the handler are
missing from the report even though the test exercised them. Call the
endpoint function itself in the test (`await router_module.get_thing(...)`)
next to the HTTP request; the direct call runs in the test's own task and the
lines are recorded. Both suites need it: the unit gate reads the unit
coverage and the integration gate reads the integration coverage.

For frontend parity:
```bash
cd apps/web
npm ci
npm run lint
npm run test -- --ci --coverage
```

Or use Makefile:
```bash
make ci        # Run full CI pipeline
make ci-quick  # Quick CI (skip slower scans)
```

Optional smoke test (requires Docker):
```bash
API_ACCESS_KEY=ci-test-key python scripts/docker/compose_smoke.py --ci --timeout-seconds 300
```

Secrets and env notes:
- CI does not require real API keys; tests use mocks or local fixtures.
- Use `.env` from `.env.example` for local development keys and SMTP settings.
- Pipeline failure notifications are created as GitHub issues and written to the job summary.

## 🌿 Branching & Releases

### Branches
- `dev`: active development branch
- `main`: stable release branch
- Legacy branches: `ver4`, `ver3`, `ver2` (frozen / archived)

### Release Flow
1. Work on `dev` (direct commits are OK for solo development).
2. When ready to release, merge `dev` into `main`.
3. Create a SemVer tag on the release commit (e.g. `v1.0.0`, `v1.1.0`).

## 🔄 Pull Request Process

### Commit Message Convention
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

### Pull Request Template
- **Description**: What changed?
- **Type**: Bug fix / Feature / Docs.
- **Testing**: How was it verified?

### Solo Development Note
If you are the only contributor, you can skip PRs for day-to-day work and push directly to `dev`.
Keep `main` reserved for releases (merge from `dev` when publishing).

## 📚 Documentation
- Keep `README.md` concise.
- Place detailed docs in `docs/`.
- Update `docs/api/API_REFERENCE.md` for API changes.

## ⚖️ License

By contributing to this project, you agree that your contributions will be licensed under the [MIT License](../../LICENSE).
