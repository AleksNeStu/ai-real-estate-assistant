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

# The backend the end-to-end suite runs against. Empty means "in-process".
E2E_BASE_URL ?=

# Colors for help output
BLUE := \033[34m
GREEN := \033[32m
RESET := \033[0m

# Phony targets
.PHONY: help security security-quick test test-api test-web e2e e2e-real-provider lint lint-api lint-web format
.PHONY: dev dev-api dev-web
.PHONY: docker-up docker-down docker-logs docker-build
.PHONY: ci ci-quick setup clean install docs
.PHONY: sprav sprav-quick sprav-json benchmark-search benchmark-chat load-test
.PHONY: perf-budget perf-preflight
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
	@sed -n 's/^## e2e/\tmake &/p' $(MAKEFILE_LIST)
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

## ============================================================================
## PERFORMANCE (Task #93)
## ============================================================================
## The p95 and the load suites are NOT in the pull-request path, and that is a
## decision, not an omission: a percentile measured on a shared runner is a
## measurement of the runner, not of the product. A suite that fails on the
## runner's load belongs on a schedule, not on every pull request - and a
## suite nobody trusts is a suite nobody reads.
##
## They run here, on demand, against a backend you name, and the budget is
## stated: PERF_BASE_URL says which machine, and `make perf-budget` prints
## the numbers the product is measured against.

## perf-base-url: The backend the performance suites measure.
PERF_BASE_URL ?= http://localhost:8000

## perf-budget: The response times the product is measured against.
## The same numbers the suites assert on (tests/performance/conftest.py).
PERF_SEARCH_P95_BUDGET ?= 2.0
PERF_CHAT_P95_BUDGET ?= 8.0
PERF_HEALTH_P95_BUDGET ?= 0.1
PERF_SUCCESS_RATE_BUDGET ?= 99.0

## perf-budget: Print the budget the p95 and load suites are measured against.
perf-budget:
	@echo "PERF_BASE_URL               = $(PERF_BASE_URL)"
	@echo "search p95                  <= $(PERF_SEARCH_P95_BUDGET)s"
	@echo "chat p95                    <= $(PERF_CHAT_P95_BUDGET)s"
	@echo "health p95                  <= $(PERF_HEALTH_P95_BUDGET)s"
	@echo "success rate                >= $(PERF_SUCCESS_RATE_BUDGET)%"
	@echo ""
	@echo "The backend under measurement needs its rate limit above the suite's"
	@echo "request count (API_RATE_LIMIT_RPM) - otherwise the suite measures the"
	@echo "limiter and says so."

## perf-preflight: Fail loudly when there is no backend to measure.
## The measurement needs a backend; a missing one is a mistake in the
## invocation, not a reason to report a number that means nothing.
perf-preflight:
	@$(PYTHON) -c "import urllib.request; urllib.request.urlopen('$(PERF_BASE_URL)/health', timeout=5)" 2>/dev/null || (echo "no backend at $(PERF_BASE_URL) - start one and set PERF_BASE_URL" && exit 1)

## benchmark-search: Run search p95 benchmark tests (Task #50)
benchmark-search: perf-preflight
	cd apps/api && PERF_BASE_URL=$(PERF_BASE_URL) $(PYTHON) -m pytest tests/performance/test_search_p95.py -v -m benchmark

## benchmark-chat: Run chat p95 benchmark tests (Task #51)
benchmark-chat: perf-preflight
	cd apps/api && PERF_BASE_URL=$(PERF_BASE_URL) $(PYTHON) -m pytest tests/performance/test_chat_p95.py -v -m benchmark

## load-test: Run concurrent load tests with baseline benchmarks (Task #65)
load-test:
	cd apps/api && $(PYTHON) -m pytest tests/performance/test_load_concurrent.py -v -m load

## test-web: Run frontend tests
test-web:
	cd apps/web && npm test

## e2e: Run backend E2E tests
## In-process by default. Set E2E_BASE_URL to run them against a running
## backend instead (the compose stack serves http://localhost:8082).
e2e:
	cd apps/api && E2E_BASE_URL=$(E2E_BASE_URL) $(PYTHON) -m pytest tests/e2e_backend -v

## ============================================================================
## THE REAL-PROVIDER PROOF (Task #97)
## ============================================================================
## The demo's headline claim is that it answers with a real model. The mock
## answers too - with four canned sentences - so a green suite on the mock
## proves nothing about the provider. This target brings the stack up with a
## REAL provider and runs the spec that says so.
##
## The default provider is the local Ollama one: the "local-llm" compose
## profile, no API key, no cost, nothing leaves the machine. The model is
## pulled by the container on first start (~2GB, slow) and the volume is kept
## afterwards, so the second run starts immediately. Point E2E_PROVIDER at a
## hosted provider to prove that one instead, and give it its own model id:
##   make e2e-real-provider E2E_PROVIDER=minimax E2E_PROVIDER_MODEL=MiniMax-M3.1-Flash
## (the key goes in deploy/compose/.env).
##
## The stack is torn down at the end, whether the proof passed or failed.

## E2E_PROVIDER - The provider the proof stack answers with.
E2E_PROVIDER ?= ollama

## E2E_PROVIDER_MODEL - The model id that provider is asked for. It follows
## the provider: Ollama takes a local model id, a hosted provider takes its
## own. A mismatch here is the incoherence the compose file no longer has.
E2E_PROVIDER_MODEL ?= llama3.2:3b

## E2E_OLLAMA_HOST_PORT - The host port the proof stack publishes Ollama on.
## The backend reaches the model over the compose network, so this port is
## for a human - but 11434 is the default port of every Ollama on the
## machine, and a developer's own Ollama holds it. Move it when it is taken.
E2E_OLLAMA_HOST_PORT ?= 11434

## E2E_REAL_BASE_URL - Where the proof stack serves the backend.
## The ports come from the environment, because the compose file reads them
## from there: the workstation carries its own BACKEND_HOST_PORT (the
## non-Docker stack needs it), and the proof has to ask the stack for the
## port the stack actually opened - not the one the file defaults to.
BACKEND_HOST_PORT ?= 8082
FRONTEND_HOST_PORT ?= 3082
E2E_REAL_BASE_URL ?= http://localhost:$(BACKEND_HOST_PORT)

## E2E_REAL_API_KEY - The key the stack is started with, and the one the
## spec authenticates with.
E2E_REAL_API_KEY ?= dev-secret-key

## E2E_REAL_CORS_ORIGIN - An origin the stack allows (the preflight is
## checked against the stack's own origins).
E2E_REAL_CORS_ORIGIN ?= http://localhost:$(FRONTEND_HOST_PORT)

## E2E_REAL_PROJECT - The compose project the proof stack runs under. It is
## its own, so the teardown at the end of the target removes the proof and
## not the stack the developer has running.
E2E_REAL_PROJECT ?= e2e-real-provider

## E2E_REAL_CATALOGUE_WAIT - How many attempts the wait loop spends waiting
## for the demo catalogue to fill before it stops waiting. The catalogue is
## seeded in the background, so the API answers before it is there, and a
## proof that runs against an empty catalogue can go red for a reason that
## has nothing to do with the provider. The wait is bounded, so the target
## never fails where it would have passed.
E2E_REAL_CATALOGUE_WAIT ?= 30

## e2e-real-provider: Prove the demo answers with a real model, not the mock.
e2e-real-provider:
	@test -f apps/api/tests/e2e_backend/test_real_provider.py || (echo "ERROR: the proof spec is missing - apps/api/tests/e2e_backend/test_real_provider.py" && exit 1)
	@echo "Starting the stack with the $(E2E_PROVIDER) provider..."
	@status=0; \
	trap '$(DOCKER_COMPOSE) -p $(E2E_REAL_PROJECT) -f $(DOCKER_COMPOSE_FILE) --profile local-llm down --remove-orphans' EXIT; \
	export POSTGRES_PASSWORD=not-started \
		API_ACCESS_KEY=$(E2E_REAL_API_KEY) \
		BACKEND_HOST_PORT=$(BACKEND_HOST_PORT) \
		FRONTEND_HOST_PORT=$(FRONTEND_HOST_PORT) \
		CORS_ALLOW_ORIGINS=$(E2E_REAL_CORS_ORIGIN),$(E2E_REAL_BASE_URL) \
		DEMO_MODE=true DEMO_DATA_MODE=true \
		DEMO_LLM_MODE=false \
		OPENAI_API_KEY= ANTHROPIC_API_KEY= GOOGLE_API_KEY= \
		MINIMAX_API_KEY= REALT_MINIMAX_API_KEY= \
		XAI_API_KEY= DEEPSEEK_API_KEY= OPENROUTER_API_KEY= \
		DEFAULT_PROVIDER=$(E2E_PROVIDER) \
		DEFAULT_MODEL=$(E2E_PROVIDER_MODEL) \
		OLLAMA_API_BASE=http://ollama:11434 \
		OLLAMA_HOST_PORT=$(E2E_OLLAMA_HOST_PORT) \
		FORCE_HTTPS=false; \
	$(DOCKER_COMPOSE) -p $(E2E_REAL_PROJECT) -f $(DOCKER_COMPOSE_FILE) --profile local-llm up -d --build || exit 1; \
	echo "Waiting for the local model and the backend..."; \
	for attempt in $$(seq 1 240); do \
		oid=$$($(DOCKER_COMPOSE) -p $(E2E_REAL_PROJECT) -f $(DOCKER_COMPOSE_FILE) --profile local-llm ps -q ollama); \
		if [ -n "$$oid" ] \
			&& [ "$$(docker inspect --format '{{.State.Health.Status}}' $$oid 2>/dev/null)" = "healthy" ] \
			&& curl -sf "$(E2E_REAL_BASE_URL)/health" >/dev/null 2>&1; then \
			if curl -sf "$(E2E_REAL_BASE_URL)/api/v1/properties?limit=1" 2>/dev/null | grep -q '"count": *[1-9]' \
				|| [ $$attempt -ge $(E2E_REAL_CATALOGUE_WAIT) ]; then \
				echo "the stack is ready"; break; \
			fi; \
			echo "waiting for the demo catalogue ($$attempt/$(E2E_REAL_CATALOGUE_WAIT))"; \
		fi; \
		if [ $$attempt -eq 240 ]; then echo "ERROR: the stack never became ready"; exit 1; fi; \
		echo "waiting for the stack ($$attempt/240)"; sleep 10; \
	done; \
	( cd apps/api && \
		E2E_BASE_URL=$(E2E_REAL_BASE_URL) \
		E2E_REQUIRE_REAL_PROVIDER=1 \
		API_ACCESS_KEY=$(E2E_REAL_API_KEY) \
		E2E_API_KEY=$(E2E_REAL_API_KEY) \
		E2E_CORS_ORIGIN=$(E2E_REAL_CORS_ORIGIN) \
		$(PYTHON) -m pytest tests/e2e_backend/test_real_provider.py -v --tb=short ) || status=$$?; \
	exit $$status

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

# The dev / dev-api / dev-web targets were removed on 2026-06-17 together with
# scripts/start.py. The launcher is back, so the targets are back too.
# Cross-platform launchers remain the primary entry point:
#   bash scripts/dev/run.sh                 # both backend + frontend (Linux/macOS)
#   pwsh scripts/dev/run.ps1                # both (Windows PowerShell)
#   bash scripts/dev/{be,fe}.sh              # backend/frontend only (Linux/macOS)
#   pwsh scripts/dev/{be,fe}.ps1             # backend/frontend only (Windows)
# Standalone (no auto-bootstrap) variants in scripts/local/.

## dev: Start development servers (auto mode: Docker if available, else local)
dev:
	$(PYTHON) $(SCRIPTS_DIR)/start.py --mode auto

## dev-api: Start backend development server only
dev-api:
	$(PYTHON) $(SCRIPTS_DIR)/start.py --mode local --service backend

## dev-web: Start frontend development server only
dev-web:
	$(PYTHON) $(SCRIPTS_DIR)/start.py --mode local --service frontend

## setup: Run environment setup (first-time setup)
setup:
	$(PYTHON) $(SCRIPTS_DIR)/setup/bootstrap.py

## install: Install all dependencies
## The backend manifests are pinned: the runtime manifest first, then the gate
## tooling, then the project itself installed WITHOUT its own dependency
## resolution, so the pins decide the versions in every environment.
install:
	cd apps/api && uv pip install -r requirements.lock.txt -r requirements-dev.txt
	cd apps/api && uv pip install --no-deps -e .
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
	$(PYTHON) $(SCRIPTS_DIR)/ci/ci_parity.py --unit-only

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
	@for f in vercel.json deploy/docker/Dockerfile.backend deploy/docker/Dockerfile.frontend deploy/compose/docker-compose.yml; do \
		if [ ! -f "$$f" ]; then echo "ERROR: Missing $$f"; exit 1; fi; \
		echo "  ✓ $$f"; \
	done
	@if grep -q "REPLACE_WITH" deploy/compose/.env.example; then \
		echo "  ✓ .env.example has expected placeholders"; \
	fi
	@echo "All configs valid."
