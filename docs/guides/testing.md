# Testing Guide

This guide covers testing procedures, coverage requirements, and CI/CD parity for the AI Real Estate Assistant project.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Backend Testing](#backend-testing)
- [Frontend Testing](#frontend-testing)
- [Test Coverage Requirements](#test-coverage-requirements)
- [CI/CD Parity](#cicd-parity)
- [Writing Tests](#writing-tests)

---

## Overview

The project uses:

| Component | Tool | Purpose |
|-----------|------|---------|
| Backend | pytest | Python test framework |
| Backend | pytest-cov | Coverage reporting |
| Backend | pytest-xdist | Parallel test execution |
| Frontend | Jest | JavaScript test framework |
| Frontend | React Testing Library | Component testing |

### Coverage Requirements

| Area | Minimum Coverage | Critical Path Coverage |
|------|------------------|------------------------|
| Backend Unit | 90% | 90% |
| Backend Integration | 70% | - |
| Frontend Global | 85% | - |

---

## Prerequisites

### Install Dependencies

```bash
# Backend
make setup
# or
python scripts/setup/bootstrap.py --dev

# Frontend
cd apps/web
npm install
```

### Environment Setup

```bash
# Copy environment file
cp .env.example .env

# Set test environment
ENVIRONMENT=test
API_ACCESS_KEY=dev-secret-key
ENABLE_JWT_AUTH=true
```

---

## Backend Testing

### Running All Backend Tests

```bash
# From project root
make test-api

# Or directly
cd apps/api
pytest tests/unit tests/integration --cov=. --cov-report=term -n auto
```

### Running Specific Tests

```bash
# Single test file
pytest tests/unit/test_query_analyzer.py -v

# Specific test
pytest tests/unit/test_query_analyzer.py -k test_classify_intent -v

# Unit tests only
pytest tests/unit --cov=. --cov-report=term -n auto

# Integration tests only
pytest tests/integration --cov=. --cov-report=term -n auto
```

### Test Options

| Option | Description |
|--------|-------------|
| `-v` | Verbose output |
| `-n auto` | Parallel execution (requires pytest-xdist) |
| `--cov=.` | Coverage report |
| `--cov-report=term` | Terminal coverage report |
| `--cov-report=html` | HTML coverage report |
| `-k expression` | Filter tests by expression |
| `-x` | Stop on first failure |
| `--timeout=300` | Per-test timeout (5 minutes) |

### Key Fixtures

The project provides several useful fixtures in `tests/conftest.py`:

| Fixture | Purpose |
|---------|---------|
| `async_client` | HTTP client with auth headers injected |
| `auth_headers` | Valid `X-API-Key` header |
| `db_session` | In-memory SQLite session |
| `query_analyzer` | QueryAnalyzer instance |
| `sample_properties` | 5 test Property objects |
| `sample_documents` | Document objects from properties |

### Async Test Pattern

```python
@pytest.mark.asyncio
async def test_endpoint(async_client):
    response = await async_client.get("/api/v1/endpoint")
    assert response.status_code == 200
```

---

## Frontend Testing

### Running All Frontend Tests

```bash
# From project root
make test-web

# Or directly
cd apps/web
npm test
```

### Test Commands

| Command | Description |
|---------|-------------|
| `npm test` | Interactive watch mode |
| `npm run test:ci` | CI mode with coverage |
| `npm run test:watch` | Watch mode |
| `npm run test:coverage` | Generate coverage report |

### Running Specific Tests

```bash
# Pattern matching
npm test -- --testNamePattern="should render"

# File matching
npm test -- Button
```

---

## Test Coverage Requirements

### Backend Coverage Gates

The CI pipeline enforces coverage gates:

1. **Diff Coverage** (PR only)
   - Ensures new code meets coverage thresholds
   - 90% minimum for unit tests
   - 70% minimum for integration tests

2. **Critical Path Coverage**
   - Enforces 90% coverage on critical modules:
     - `api/*.py`
     - `api/routers/*.py`
     - `rules/*.py`
     - `models/provider_factory.py`
     - `models/user_model_preferences.py`
     - `config/*.py`

### Checking Coverage Locally

```bash
# Backend
cd apps/api
pytest tests/unit --cov=. --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Frontend
cd apps/web
npm run test:coverage
open coverage/lcov-report/index.html
```

---

## CI/CD Parity

### Running Full CI Locally

```bash
# Quick CI (skips slower scans)
make ci-quick

# Full CI
make ci
# or
python scripts/workflows/full_ci.py
```

### CI Components

The CI pipeline runs the following jobs:

| Job | Purpose | Commands |
|-----|---------|----------|
| gitleaks | Secret scanning | `.gitleaks.toml` rules |
| backend | Lint, type check, tests | ruff, mypy, pytest |
| frontend | Lint, tests | ESLint, Jest |
| security | SAST scanning | bandit, pip-audit |
| semgrep | Security rules | `semgrep.yml` |
| trivy | Container scan | Docker image vulnerability |
| compose_smoke | Docker build test | Build + health check |

### Backend CI Commands

```powershell
# Install uv
pip install uv

# Install dependencies
uv pip install -e .[dev]

# Lint
python -m ruff check .

# Type check
python -m mypy

# Rule engine test
python -m pytest -q tests/integration/test_rule_engine_clean.py

# OpenAPI schema check
python scripts/docs/export_openapi.py --check

# API reference check
python scripts/docs/generate_api_reference.py --check

# Unit tests with coverage
python -m pytest tests/unit --cov=. --cov-report=xml --cov-report=term -n auto

# Coverage gates
python scripts/ci/coverage_gate.py diff --coverage-xml coverage.xml --min-coverage 90 --exclude tests/* --exclude scripts/* --exclude workflows/*
python scripts/ci/coverage_gate.py critical --coverage-xml coverage.xml --min-coverage 90 --include api/*.py --include api/routers/*.py --include rules/*.py --include models/provider_factory.py --include models/user_model_preferences.py --include config/*.py

# Integration tests
python -m pytest tests/integration --cov=. --cov-report=xml --cov-report=term
```

### Frontend CI Commands

```powershell
cd apps/web

# Install dependencies
npm ci

# Lint
npm run lint

# Tests with coverage
npm run test:ci
```

### Security CI Commands

```powershell
# Install tools
uv pip install bandit pip-audit

# Bandit SAST
python -m bandit -r apps/api -x tests,node_modules,.history --severity-level high --confidence-level high -f json -o artifacts/bandit.json

# pip-audit
python -m pip_audit -r requirements.txt -f json -o artifacts/pip-audit.json

# Semgrep (requires Semgrep installed)
semgrep scan --config semgrep.yml --error
```

---

## Writing Tests

### Backend Test Template

```python
"""Test module for feature X."""

import pytest
from httpx import AsyncClient


class TestFeatureX:
    """Test cases for Feature X."""

    @pytest.mark.asyncio
    async def test_endpoint_success(self, async_client: AsyncClient):
        """Test successful endpoint call."""
        response = await async_client.get("/api/v1/feature")
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data

    @pytest.mark.asyncio
    async def test_endpoint_unauthorized(self, unauth_client: AsyncClient):
        """Test unauthorized access is rejected."""
        response = await unauth_client.get("/api/v1/feature")
        assert response.status_code == 401

    def test_function(self):
        """Test a pure function."""
        from module import function
        result = function(input_value)
        assert result == expected_value
```

### Frontend Test Template

```typescript
describe('ComponentName', () => {
  it('should render correctly', () => {
    render(<ComponentName />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('should handle user interaction', async () => {
    const user = userEvent.setup();
    render(<ComponentName />);

    const button = screen.getByRole('button');
    await user.click(button);

    expect(screen.getByText('Success')).toBeInTheDocument();
  });

  it('should match snapshot', () => {
    const { container } = render(<ComponentName />);
    expect(container).toMatchSnapshot();
  });
});
```

### Test Best Practices

1. **Arrange-Act-Assert Pattern**
   ```python
   def test_something():
       # Arrange: Set up test data
       input_data = create_test_data()

       # Act: Execute function
       result = process_data(input_data)

       # Assert: Verify result
       assert result.expected == "value"
   ```

2. **Use Descriptive Names**
   - Bad: `test_1()`
   - Good: ` test_calculate_mortgage_with_zero_down_payment()`

3. **Test One Thing**
   - Each test should verify a single behavior

4. **Use Fixtures**
   - Avoid duplicating setup code
   - Use `conftest.py` for shared fixtures

5. **Mock External Dependencies**
   - Mock API calls, database, LLM providers

---

## Pre-Commit Hooks

The project uses pre-commit hooks for code quality:

```bash
# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Hook configuration in .pre-commit-config.yaml
```

### Hooks That Run

| Hook | Purpose | Files |
|------|---------|-------|
| Gitleaks | Secret detection | All |
| Ruff | Python lint/format | `*.py` |
| Prettier | Code formatting | Frontend files |
| ESLint | JavaScript lint | `*.ts`, `*.tsx` |

---

## Troubleshooting

### Issue: Tests pass locally but fail in CI

**Possible causes:**
1. Environment differences (Python version, dependencies)
2. Time-dependent tests (use fixtures for time)
3. Test isolation issues (tests affecting each other)

**Solution:**
```bash
# Run CI locally
make ci

# Check specific test with verbose output
pytest tests/unit/test_file.py -v -s
```

### Issue: Coverage gate fails

**Solution:**
```bash
# Check coverage report
pytest tests/unit --cov=. --cov-report=html
open htmlcov/index.html

# Find uncovered lines
# Write tests for them
```

### Issue: Async tests hang

**Solution:**
```bash
# Add timeout to pytest
pytest --timeout=10

# Check for missing await statements
# Use pytest-asyncio correctly
```

### Issue: npm EPERM on Windows

```powershell
# Delete node_modules and reinstall
Remove-Item -Recurse -Force apps/web/node_modules
cd apps/web
npm ci
```

---

## Next Steps

- Set up [Local Development](local-development.md)
- Configure [Environment Variables](environment-setup.md)
- Review [CI/CD Pipeline](ci-cd.md)
