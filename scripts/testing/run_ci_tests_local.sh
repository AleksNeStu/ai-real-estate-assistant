#!/usr/bin/env bash
# Run CI tests locally to replicate GitHub Actions workflow

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Default options
PARALLEL=true
COVERAGE=false
FAST=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-parallel)
            PARALLEL=false
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --fast)
            FAST=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-parallel    Disable parallel test execution"
            echo "  --coverage       Generate coverage reports"
            echo "  --fast           Skip slow tests and type checking"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

START_TIME=$(date +%s)

# Detect Python executable
PYTHON=""
POSSIBLE_PATHS=(
    "apps/api/.venv312/bin/python"
    "apps/api/.venv/bin/python"
    "python3.12"
    "python3"
    "python"
)

for path in "${POSSIBLE_PATHS[@]}"; do
    if command -v "$path" &> /dev/null; then
        VERSION=$($path --version 2>&1)
        if [[ $VERSION =~ Python\ 3\.1[2-9] ]]; then
            PYTHON=$path
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${RED}ERROR: Python 3.12+ not found!${NC}"
    echo -e "${YELLOW}Please create a virtual environment:${NC}"
    echo -e "${YELLOW}  cd apps/api${NC}"
    echo -e "${YELLOW}  python3.12 -m venv .venv312${NC}"
    echo -e "${YELLOW}  source .venv312/bin/activate${NC}"
    echo -e "${YELLOW}  pip install -r requirements.txt${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON --version 2>&1)
echo -e "${CYAN}=== Running CI Tests Locally ===${NC}"
echo -e "${CYAN}Python: $PYTHON_VERSION${NC}"
echo -e "${CYAN}Parallel: $PARALLEL${NC}"
echo -e "${CYAN}Coverage: $COVERAGE${NC}"
echo -e "${CYAN}Fast mode: $FAST${NC}"
echo ""

# Change to API directory
cd apps/api

# 1. Lint (ruff)
echo -e "${YELLOW}[1/8] Running ruff linter...${NC}"
$PYTHON -m ruff check .

# 2. RuleEngine test
echo -e "\n${YELLOW}[2/8] Running RuleEngine test...${NC}"
$PYTHON -m pytest -q tests/integration/test_rule_engine_clean.py

# 3. Forbidden tokens scan
echo -e "\n${YELLOW}[3/8] Running forbidden tokens scan...${NC}"
$PYTHON ../../scripts/security/forbidden_tokens.py

# 4. OpenAPI breaking-change detection
echo -e "\n${YELLOW}[4/8] Running OpenAPI diff...${NC}"
$PYTHON ../../scripts/api/openapi_diff.py --baseline ../../docs/api-v1-baseline.json

# 5. Alembic migration check
echo -e "\n${YELLOW}[5/8] Running Alembic migration check...${NC}"
$PYTHON -m alembic check

# 6. Unit tests
echo -e "\n${YELLOW}[6/8] Running unit tests...${NC}"
UNIT_TEST_ARGS="tests/unit --maxfail=5 -q"

if [ "$PARALLEL" = true ]; then
    UNIT_TEST_ARGS="$UNIT_TEST_ARGS -n auto"
    echo -e "${GRAY}  (parallel execution enabled)${NC}"
fi

if [ "$COVERAGE" = true ]; then
    UNIT_TEST_ARGS="$UNIT_TEST_ARGS --cov=. --cov-report=xml --cov-report=term"
    echo -e "${GRAY}  (coverage enabled)${NC}"
fi

if [ "$FAST" = true ]; then
    UNIT_TEST_ARGS="$UNIT_TEST_ARGS -m 'not slow'"
    echo -e "${GRAY}  (skipping slow tests)${NC}"
fi

$PYTHON -m pytest $UNIT_TEST_ARGS

# 7. Integration tests
echo -e "\n${YELLOW}[7/8] Running integration tests...${NC}"
INTEGRATION_TEST_ARGS="tests/integration -q"

if [ "$PARALLEL" = true ]; then
    INTEGRATION_TEST_ARGS="$INTEGRATION_TEST_ARGS -n auto"
    echo -e "${GRAY}  (parallel execution enabled)${NC}"
fi

if [ "$COVERAGE" = true ]; then
    INTEGRATION_TEST_ARGS="$INTEGRATION_TEST_ARGS --cov=. --cov-report=xml --cov-report=term --cov-append"
    echo -e "${GRAY}  (coverage enabled)${NC}"
fi

$PYTHON -m pytest $INTEGRATION_TEST_ARGS

# 8. Type check (mypy) - optional in fast mode
if [ "$FAST" = false ]; then
    echo -e "\n${YELLOW}[8/8] Running mypy type check...${NC}"
    echo -e "${GRAY}  (errors are non-blocking)${NC}"
    $PYTHON -m mypy . --explicit-package-bases || true
else
    echo -e "\n${GRAY}[8/8] Skipping mypy type check (fast mode)${NC}"
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo -e "\n${GREEN}=== All CI tests passed! ===${NC}"
echo -e "${CYAN}Total time: ${MINUTES}m ${SECONDS}s${NC}"

if [ "$COVERAGE" = true ]; then
    echo -e "${CYAN}Coverage report saved to: coverage.xml${NC}"
fi
