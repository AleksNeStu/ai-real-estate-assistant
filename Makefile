# AI Real Estate Assistant - Makefile
# Quick commands for development, testing, and CI/CD
#
# Usage:
#   make help         - Show all available targets
#   make security     - Run security scans
#   make check-deps   - Verify Python dependencies resolve (run before tagging)
#   make test         - Run all tests
#   make lint         - Run linting
#   make dev          - Start development servers
#   make docker-up    - Start Docker containers
#   make docker-down  - Stop Docker containers
#   make ci           - Run full CI locally

# Variables
PYTHON := python
DOCKER_COMPOSE := docker compose
DOCKER_COMPOSE_FILE := deploy/compose/docker-compose.yml
SCRIPTS_DIR := scripts

# Colors for help output
BLUE := \033[34m
GREEN := \033[32m
RESET := \033[0m

# Phony targets
.PHONY: help security security-quick test test-api test-web e2e lint lint-api lint-web format
.PHONY: docker-up docker-down docker-logs docker-build
.PHONY: ci ci-quick setup clean install docs
.PHONY: sprav sprav-quick sprav-json benchmark-search benchmark-chat load-test
.PHONY: migrate-check migrate-up migrate-down smoke-test test-resilience quickstart
.PHONY: api-diff api-diff-baseline
.PHONY: seed
.PHONY: rule5-guard

# Default target
.DEFAULT_GOAL := help

## ============================================================================
## HELP
## ============================================================================

help: ## Show this help message
	@echo "$(BLUE)AI Real Estate Assistant - Available Commands$(RESET)"
	@echo ""
	@echo "$(GREEN)Security:$(RESET)"
	@sed -n 's/^## security/\tmake &/p' $(MAKEFILE_LIST)
	@sed -n 's/^## security-quick/\tmake &/p' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Testing:$(RESET)"
	@sed -n 's/^## test/\tmake &/p' $(MAKEFILE_LIST) | head -3
	@sed -n 's/^## benchmark/\tmake &/p' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Linting & Formatting:$(RESET)"
	@sed -n 's/^## lint/\tmake &/p' $(MAKEFILE_LIST)
	@sed -n 's/^## format/\tmake &/p' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Development:$(RESET)"
	@sed -n 's/^## dev/\tmake &/p' $(MAKEFILE_LIST) | head -2
	@sed -n 's/^## setup/\tmake &/p' $(MAKEFILE_LIST)
	@sed -n 's/^## install/\tmake &/p' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Docker:$(RESET)"
	@sed -n 's/^## docker/\tmake &/p' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)CI/CD:$(RESET)"
	@sed -n 's/^## ci/\tmake &/p' $(MAKEFILE_LIST)
	@sed -n 's/^## docs/\tmake &/p' $(MAKEFILE_LIST)
	@sed -n 's/^## api-diff/\tmake &/p' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)SPRAV (Pre-Release Validation):$(RESET)"
	@sed -n 's/^## sprav/\tmake &/p' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Maintenance:$(RESET)"
	@sed -n 's/^## clean/\tmake &/p' $(MAKEFILE_LIST)
	@sed -n 's/^## smoke-test/\tmake &/p' $(MAKEFILE_LIST)

## ============================================================================
## SECURITY
## ============================================================================

## security: Run all security scans (Gitleaks, Semgrep, Bandit, pip-audit)
security:
	$(PYTHON) $(SCRIPTS_DIR)/security/local_scan.py

## security-quick: Run quick security scan (skip pip-audit)
security-quick:
	$(PYTHON) $(SCRIPTS_DIR)/security/local_scan.py --quick

## check-deps: Verify Python deps in apps/api/requirements.txt actually resolve.
## Run this BEFORE pushing any v* tag. Exits 1 on unsatisfiable constraints,
## so a v5.0.7 protobuf-style regression cannot reach the GHCR publish
## step. Cheap (~10s) because pip only resolves, doesn't install.
check-deps:
	cd apps/api && $(PYTHON) -m pip install --dry-run -r requirements.txt

## security-pre-push: Quick security check for pre-push (semgrep errors only)
security-pre-push:
	$(PYTHON) $(SCRIPTS_DIR)/security/local_scan.py --scan-only=semgrep --quick

## rule5-guard: Verify CLAUDE.md Rule 5 protected paths are not tracked.
## Catches regression where someone runs `git add -f .mcp.json` (or any other
## force-add of a gitignored path) into the public, frozen repo.
## Exit 1 = drift; remediation is `git rm --cached <path>`.
rule5-guard:
	$(PYTHON) $(SCRIPTS_DIR)/rule5_guard/gitignored_tracked_check.py

## ============================================================================
## TESTING
## ============================================================================

## test: Run all tests (backend + frontend)
test: test-api test-web

## test-api: Run backend tests with coverage
test-api:
	cd apps/api && $(PYTHON) -m pytest tests/unit tests/integration --cov=. --cov-report=term

## test-dev: Run tests in dev mode (stop on first fail, rerun failed first)
test-dev:
	cd apps/api && $(PYTHON) -m pytest tests/unit tests/integration -x --ff

## benchmark-search: Run search p95 benchmark tests (Task #50)
benchmark-search:
	cd apps/api && $(PYTHON) -m pytest tests/performance/test_search_p95.py -v -m benchmark

## benchmark-chat: Run chat p95 benchmark tests (Task #51)
benchmark-chat:
	cd apps/api && $(PYTHON) -m pytest tests/performance/test_chat_p95.py -v -m benchmark

## load-test: Run concurrent load tests with baseline benchmarks (Task #65)
load-test:
	cd apps/api && $(PYTHON) -m pytest tests/performance/test_load_concurrent.py -v -m load

## test-web: Run frontend tests
test-web:
	cd apps/web && npm test

## e2e: Run backend E2E tests
e2e:
	cd apps/api && $(PYTHON) -m pytest tests/e2e_backend -v

## migrate-check: Validate Alembic migrations are consistent (Task #63)
migrate-check:
	cd apps/api && $(PYTHON) -m alembic check

## migrate-up: Apply all pending migrations
migrate-up:
	cd apps/api && $(PYTHON) -m alembic upgrade head

## migrate-down: Rollback last migration
migrate-down:
	cd apps/api && $(PYTHON) -m alembic downgrade -1

## ============================================================================
## LINTING & FORMATTING
## ============================================================================

## lint: Run all linting (backend + frontend)
lint: lint-api lint-web

## lint-api: Run backend linting (ruff)
lint-api:
	cd apps/api && $(PYTHON) -m ruff check .

## lint-web: Run frontend linting (ESLint)
lint-web:
	cd apps/web && npm run lint

## format: Format all code (backend + frontend)
format:
	cd apps/api && $(PYTHON) -m ruff format .
	cd apps/web && npm run format || true

## ============================================================================
## DEVELOPMENT
## ============================================================================

# Note: dev / dev-api / dev-web targets were removed on 2026-06-17.
# They referenced scripts/start.py which no longer exists in this repo.
# Use the cross-platform launchers directly:
#   bash scripts/dev/run.sh                 # both backend + frontend (Linux/macOS)
#   pwsh scripts/dev/run.ps1                # both (Windows PowerShell)
#   bash scripts/dev/{be,fe}.sh              # backend/frontend only (Linux/macOS)
#   pwsh scripts/dev/{be,fe}.ps1             # backend/frontend only (Windows)
# Standalone (no auto-bootstrap) variants in scripts/local/.

## setup: Run environment setup (first-time setup)
setup:
	$(PYTHON) $(SCRIPTS_DIR)/setup/bootstrap.py

## install: Install all dependencies
install:
	cd apps/api && uv pip install -e .[dev]
	cd apps/web && npm install

## seed: Seed ChromaDB with sample property data (60 listings)
seed:
	cd apps/api && $(PYTHON) scripts/seed_properties.py

## seed-force: Re-seed ChromaDB even if data already exists
seed-force:
	cd apps/api && $(PYTHON) scripts/seed_properties.py --force

## seed-100: Seed ChromaDB with 100 property listings
seed-100:
	cd apps/api && $(PYTHON) scripts/seed_properties.py --count 100

## ============================================================================
## DOCKER
## ============================================================================

## docker-up: Start Docker containers (background)
docker-up:
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) up -d

## docker-down: Stop Docker containers
docker-down:
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) down

## docker-logs: Show Docker container logs
docker-logs:
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) logs -f

## docker-build: Build Docker images
docker-build:
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) build

## docker-gpu: Start Docker with GPU support (Ollama)
docker-gpu:
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) --profile local-llm --profile gpu up -d

## docker-internet: Start Docker with internet search (SearXNG)
docker-internet:
	$(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) --profile internet up -d

## ============================================================================
## CI/CD
## ============================================================================

## docs: OpenAPI spec lives in docs/api/openapi.json (hand-maintained; generator scripts removed)
docs:
	@test -f docs/api/openapi.json && echo "OpenAPI spec: docs/api/openapi.json (committed)" || (echo "ERROR: docs/api/openapi.json missing" && exit 1)

## api-diff: Check OpenAPI schema for breaking changes vs baseline (Task #70)
api-diff:
	$(PYTHON) scripts/api/openapi_diff.py --baseline docs/api-v1-baseline.json

## api-diff-baseline: Regenerate the API baseline schema (run after intentional breaking changes)
api-diff-baseline:
	$(PYTHON) -c "import json; schema=json.load(open('docs/api/openapi.json','r')); paths={k:v for k,v in schema.get('paths',{}).items() if k.startswith('/api/v1/')}; schema['paths']=paths; json.dump(schema, open('docs/api-v1-baseline.json','w'), indent=2)"
	@echo "Baseline updated: docs/api-v1-baseline.json"

## ci: Run full CI pipeline locally
ci:
	$(PYTHON) $(SCRIPTS_DIR)/workflows/full_ci.py

## ci-quick: Run quick CI (skip slower scans)
ci-quick:
	$(PYTHON) $(SCRIPTS_DIR)/ci/ci_parity.py --quick

## ============================================================================
## SPRAV - Pre-Release Acceptance Validation
## ============================================================================

## sprav: Run full SPRAV validation
sprav:
	$(PYTHON) $(SCRIPTS_DIR)/sprav/run_validation.py --output docs/releases/sprav-report.md

## sprav-quick: Run quick SPRAV validation (skip slow checks)
sprav-quick:
	$(PYTHON) $(SCRIPTS_DIR)/sprav/run_validation.py --quick --output docs/releases/sprav-report.md

## sprav-json: Run SPRAV validation and output JSON
sprav-json:
	$(PYTHON) $(SCRIPTS_DIR)/sprav/run_validation.py --json --output docs/releases/sprav-results.json

## ============================================================================
## MAINTENANCE
## ============================================================================

## clean: Clean build artifacts and caches
clean:
	rm -rf apps/api/.pytest_cache apps/api/__pycache__ apps/api/.coverage apps/api/.ruff_cache
	rm -rf apps/api/**/__pycache__ apps/api/**/*.pyc
	rm -rf apps/web/.next apps/web/node_modules/.cache apps/web/coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

## clean-all: Deep clean (includes node_modules, .venv)
clean-all: clean
	rm -rf apps/web/node_modules
	rm -rf node_modules
	rm -rf .venv venv .venv_ci

## smoke-test: Build + bring up compose stack and verify health (Task #69)
smoke-test:
	$(PYTHON) scripts/docker/compose_smoke.py

## test-resilience: Run graceful degradation and resilience tests (Task #69)
test-resilience:
	cd apps/api && $(PYTHON) -m pytest tests/resilience/ -v

## quickstart: Start app with pre-built GHCR images (no build needed, Task #67)
quickstart:
	@test -f deploy/compose/.env || cp deploy/compose/.env.example deploy/compose/.env
	@echo "Starting AI Real Estate Assistant with pre-built images..."
	@echo "Edit deploy/compose/.env to add your LLM API key."
	docker compose -f deploy/compose/docker-compose.quick.yml up -d
	@echo ""
	@echo "Waiting for services to start..."
	@sleep 5
	@echo "Frontend: http://localhost:3082"
	@echo "Backend:  http://localhost:8082/docs"
	@echo "Health:   http://localhost:8082/health"

## deploy-prod: Start production stack (compose + prod overlay + postgres)
deploy-prod:
	@test -f deploy/compose/.env || cp deploy/compose/.env.example deploy/compose/.env
	@echo "Starting production stack..."
	docker compose \
		-f deploy/compose/docker-compose.yml \
		-f deploy/compose/docker-compose.prod.yml \
		--profile postgres up -d
	@echo ""
	@echo "Production stack started."
	@echo "Run 'make smoke-test' to verify."

## deploy-validate: Validate deployment configs without deploying
deploy-validate:
	@echo "Validating deployment configs..."
	@for f in render.yaml vercel.json deploy/docker/Dockerfile.backend deploy/docker/Dockerfile.frontend deploy/compose/docker-compose.yml; do \
		if [ ! -f "$$f" ]; then echo "ERROR: Missing $$f"; exit 1; fi; \
		echo "  ✓ $$f"; \
	done
	@if grep -q "REPLACE_WITH" deploy/compose/.env.example; then \
		echo "  ✓ .env.example has expected placeholders"; \
	fi
	@echo "All configs valid."
