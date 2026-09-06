# Scripts Directory

This directory contains utility scripts for development, testing, and CI/CD operations.
All scripts live under a category subfolder; the root holds only this README and `__init__.py` (per
the meta-repo Rule 94: no loose scripts at `scripts/` or `docs/` root).

## 📁 Directory Structure

```
scripts/
├── api/              # API-specific scripts (e.g. openapi_diff.py)
├── ci/               # CI/CD pipeline helpers (ci_parity, coverage_gate, network_isolation)
├── demo/             # Demo-mode helpers (PowerShell, numbered 01-04)
├── deployment/       # Deployment automation (vercel)
├── dev/              # Development server launchers (ps1 + sh pairs)
├── docker/           # Docker Compose wrappers (start, stop, logs, cpu/gpu variants)
├── internal/         # Internal tooling data (git-filter-repo text)
├── local/            # Standalone launchers (no auto-bootstrap)
├── port/             # Dynamic port allocation system
├── security/         # Security scanning (forbidden_tokens, full_scan, local_scan)
├── setup/            # Installation and environment setup (bootstrap.py, setup.{ps1,sh})
├── shared/           # Shared utilities (Python resolver)
├── sprav/            # Pre-release validation (run_validation, defect_tracker, etc.)
├── testing/          # Test execution scripts (ps1 + sh pairs)
├── utils/            # Cross-cutting utilities (kill-port, service_discovery, screenshots)
├── validation/       # System and TaskMaster validation
└── workflows/        # GitHub Actions workflow helpers (full_ci)
```

---

## 🧪 Testing Scripts (`testing/`)

### Simple Scripts (Recommended)

**Don't want to remember parameters? Use these:**

| Script | Purpose | Speed | When to Use |
|--------|---------|-------|-------------|
| `test-fast` | Quick feedback | ⚡ Fastest | During development |
| `test-ci` | Full CI suite | 🐢 Full | Before committing |
| `test-all` | See all failures | 🐢 Full | Fixing multiple issues |
| `test-coverage` | Coverage reports | 🐢 Full | Before PR |

**Windows:**

```powershell
.\scripts\testing\test-fast.ps1       # Quick test during development
.\scripts\testing\test-ci.ps1         # Full CI suite before commit
.\scripts\testing\test-all.ps1        # See all failures at once
.\scripts\testing\test-coverage.ps1   # Generate coverage reports
```

**Linux/macOS:**

```bash
./scripts/testing/test-fast.sh        # Quick test during development
./scripts/testing/test-ci.sh          # Full CI suite before commit
./scripts/testing/test-all.sh         # See all failures at once
./scripts/testing/test-coverage.sh    # Generate coverage reports
```

**See [Testing Guide](../docs/testing/TESTING_GUIDE.md) for detailed usage.**

### Advanced Testing

**`testing/run_ci_tests_local.ps1` / `testing/run_ci_tests_local.sh`**

Full control over test execution:

```powershell
# Windows
.\scripts\testing\run_ci_tests_local.ps1                    # Full test suite
.\scripts\testing\run_ci_tests_local.ps1 -Fast              # Skip slow tests
.\scripts\testing\run_ci_tests_local.ps1 -Coverage          # With coverage
.\scripts\testing\run_ci_tests_local.ps1 -ContinueOnError   # Don't stop on failures
```

```bash
# Linux/macOS
./scripts/testing/run_ci_tests_local.sh                     # Full test suite
./scripts/testing/run_ci_tests_local.sh --fast              # Skip slow tests
./scripts/testing/run_ci_tests_local.sh --coverage          # With coverage
./scripts/testing/run_ci_tests_local.sh --continue-on-error # Don't stop on failures
```

**Test Suite Includes:**

1. Ruff linting
2. RuleEngine integration test
3. Forbidden tokens security scan
4. OpenAPI breaking-change detection
5. Alembic migration check
6. Unit tests (~6,254 tests)
7. Integration tests
8. MyPy type checking (optional)

---

## 🚀 Development Scripts (`dev/`, `local/`)

### Wrapped Mode (`dev/`) — log files, port allocation, monitoring

```powershell
.\scripts\dev\run.ps1         # Start both backend and frontend
.\scripts\dev\be.ps1          # Backend only
.\scripts\dev\fe.ps1          # Frontend only
.\scripts\dev\stop-be.ps1     # Stop backend
.\scripts\dev\stop-fe.ps1     # Stop frontend
```

```bash
./scripts/dev/run.sh          # Start both services (Linux/macOS)
```

### Standalone Mode (`local/`) — simpler launchers, no auto-bootstrap

```powershell
.\scripts\local\run.ps1                       # Start both services
.\scripts\local\run.ps1 --no-bootstrap        # Skip dependency install
.\scripts\local\backend.ps1                   # Backend only
.\scripts\local\frontend.ps1                  # Frontend only
```

---

## 🐳 Docker Scripts (`docker/`)

### Quick Start (Self-Contained)

Zero-argument scripts. No dependencies beyond Docker Desktop.

```powershell
.\scripts\docker\start.ps1    # Build and start full stack
.\scripts\docker\stop.ps1     # Stop containers
.\scripts\docker\logs.ps1     # Follow logs (Ctrl+C to stop)
.\scripts\docker\reset.ps1    # Full reset (deletes data volumes)
```

First run: if no `.env` exists, copies from `.env.example` and opens editor. Add at least one LLM API key, then re-run.

Ports: Backend `:8082`, Frontend `:3082`, Redis `:16379`.

### Advanced Launchers

```powershell
.\scripts\docker\docker.ps1                     # With GPU detection
.\scripts\docker\docker.ps1 --docker-mode cpu   # CPU-only
.\scripts\docker\docker.ps1 --internet          # With web search
```

### Quickstart Verification

```powershell
.\scripts\docker\quickstart-verify.ps1    # Health check all services
```

### CPU/GPU Variants

```bash
./scripts/docker/cpu.sh              # CPU-only
./scripts/docker/gpu.sh              # GPU-enabled
./scripts/docker/cpu-internet.sh     # CPU with internet
./scripts/docker/gpu-internet.sh     # GPU with internet
```

### Smoke Tests

```bash
python scripts/docker/compose_smoke.py --ci --timeout-seconds 600
```

---

## 🔧 Utility Scripts (`utils/`, `port/`)

### Port Management

```powershell
# Kill process on specific port
.\scripts\utils\kill-port.ps1 8000
./scripts/utils/kill-port.sh 8000

# Verify port allocation system
python scripts/utils/verify-port-system.py

# Start with custom ports
python scripts/utils/start-with-ports.py
```

The `port/` directory holds the dynamic port allocator (`port_manager.py` + PowerShell/Bash wrappers).

### Service Discovery

```bash
python scripts/utils/service_discovery.py
```

### Screenshots

```bash
node scripts/utils/take_screenshots.js
```

---

## 📚 API Scripts (`api/`)

### OpenAPI Diff

Detect breaking changes in API schema:

```bash
cd apps/api
python ../../scripts/api/openapi_diff.py --baseline ../../docs/api-v1-baseline.json
```

---

## 🔒 Security Scripts (`security/`)

### Local Scan (Gitleaks, Semgrep, Bandit, pip-audit)

```bash
python scripts/security/local_scan.py            # full local CI parity
python scripts/security/local_scan.py --quick    # skip pip-audit
```

### Forbidden Tokens Scan

```bash
python scripts/security/forbidden_tokens.py
```

### Full Security Scan

```bash
python scripts/security/full_scan.py
```

---

## 🔄 CI/CD Scripts (`ci/`)

### Coverage Gate

```bash
python scripts/ci/coverage_gate.py diff --coverage-xml coverage.xml --min-coverage 90
```

### CI Parity Check

```bash
python scripts/ci/ci_parity.py
```

### Network Isolation Check

```bash
python scripts/ci/network_isolation_check.py
```

---

## 📦 Setup & Installation (`setup/`)

### Bootstrap (Python — cross-platform)

```bash
python scripts/setup/bootstrap.py            # install project deps
python scripts/setup/bootstrap.py --dev      # also install dev deps + pre-commit hooks
```

### Setup (PowerShell / Bash wrappers)

```powershell
.\scripts\setup\setup.ps1
```

```bash
./scripts/setup/setup.sh
```

---

## 📦 Other Directories

- **`deployment/`** — Deployment automation (Vercel `vercel.ps1` / `vercel.sh`)
- **`validation/`** — System and TaskMaster validation
- **`workflows/`** — Local CI orchestration (`workflows/full_ci.py`)
- **`internal/`** — Internal tooling data (git-filter-repo replacement text)
- **`shared/`** — Shared utilities (Python resolver)
- **`sprav/`** — Pre-release validation (`run_validation.py`, `defect_tracker.py`, etc.)
- **`demo/`** — Demo-mode PowerShell helpers (`01-launch-docker`, `02-generate-data`, etc.)

---

## 🎯 Best Practices

### Test Atomicity

All tests must be:

- **Atomic**: Self-contained, no shared state
- **Independent**: No execution order dependencies
- **Isolated**: Clean up resources after execution

This ensures tests can run in parallel without conflicts.

### Python Version

The project requires Python 3.12+ to match CI environment:

- CI uses Python 3.12 (specified in `pyproject.toml`)
- Local development should use Python 3.12 or higher
- Python 3.14+ has breaking changes with type annotations

### Virtual Environment Setup

```bash
# Create Python 3.12 environment
cd apps/api
python3.12 -m venv .venv312
source .venv312/bin/activate  # Linux/macOS
.venv312\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-xdist pytest-cov ruff mypy
```

Or use the bootstrap script which handles venv + dependencies via `uv`:

```bash
python scripts/setup/bootstrap.py --dev
```

---

## 🐛 Troubleshooting

### "Python 3.12+ not found"

Install Python 3.12 or create a virtual environment:

```bash
cd apps/api
python3.12 -m venv .venv312
```

Or use `uv` (handled by `scripts/setup/bootstrap.py`).

### Tests fail in parallel but pass sequentially

Check for:

- Shared state between tests
- Global variable modifications
- Database isolation issues
- File system conflicts

Run with `--no-parallel` to debug:

```bash
./scripts/testing/run_ci_tests_local.sh --no-parallel
```

### Import errors

Ensure all dependencies are installed:

```bash
cd apps/api
pip install -r requirements.txt
```

Or run `python scripts/setup/bootstrap.py --dev`.

---

## 💡 Performance Tips

1. **Use Fast Mode** for quick feedback during development
2. **Run Specific Tests** instead of full suite when debugging
3. **Enable Parallel Execution** for faster results
4. **Use Coverage Selectively** (adds ~20% overhead)

---

## 📚 Related Documentation

- [Testing Guide](../docs/testing/TESTING_GUIDE.md) - Complete testing guide
- [Quick Reference](../docs/testing/QUICK_REFERENCE.md) - One-page cheat sheet
- [Test Optimization](../docs/testing/TEST_OPTIMIZATION.md) - Technical details
- [AGENTS.md](../AGENTS.md) - AI agent instructions

---

## 🤝 Contributing

When adding new scripts:

1. Pick the right category subfolder — never place a script at `scripts/` root
2. Add documentation to this README's matching section
3. Include usage examples
4. Add error handling
5. Support both Windows and Linux/macOS (PowerShell + Bash pair) where applicable
6. Follow existing script patterns

The meta-repo rule 94 is enforced by `scripts/ports/hooks/pre-commit` at the meta-repo level
(not installed in this product yet — see plan 2026-06-17).

---

**Last Updated:** 2026-06-17
**Version:** 2.1.0 (Rule-94 compliance + dead-ref cleanup)
