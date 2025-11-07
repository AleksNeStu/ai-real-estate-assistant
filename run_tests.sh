#!/bin/bash

# Test runner script for AI Real Estate Assistant
# Provides different testing modes for Phase 2 validation

set -e

echo "🧪 AI Real Estate Assistant - Phase 2 Test Suite"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found. Installing test dependencies...${NC}"
    poetry install --with dev
fi

# Parse command line arguments
TEST_MODE=${1:-"quick"}

case $TEST_MODE in
    "quick")
        echo -e "${YELLOW}🚀 Running Quick Test Suite (essential tests only)${NC}"
        echo ""
        pytest tests/unit/test_query_analyzer.py::TestQueryAnalyzer::test_simple_retrieval_intent \
               tests/unit/test_query_analyzer.py::TestQueryAnalyzer::test_filtered_search_intent \
               tests/unit/test_query_analyzer.py::TestQueryAnalyzer::test_calculation_intent \
               tests/unit/test_tools.py::TestMortgageCalculatorTool::test_basic_mortgage_calculation \
               tests/unit/test_tools.py::TestMortgageCalculatorTool::test_mortgage_calculation_accuracy \
               tests/unit/test_reranker.py::TestPropertyReranker::test_basic_reranking \
               -v
        ;;

    "unit")
        echo -e "${YELLOW}🔬 Running All Unit Tests${NC}"
        echo ""
        pytest tests/unit/ -v
        ;;

    "analyzer")
        echo -e "${YELLOW}🧠 Testing Query Analyzer${NC}"
        echo ""
        pytest tests/unit/test_query_analyzer.py -v
        ;;

    "tools")
        echo -e "${YELLOW}🛠️ Testing Tools${NC}"
        echo ""
        pytest tests/unit/test_tools.py -v
        ;;

    "reranker")
        echo -e "${YELLOW}✨ Testing Reranker${NC}"
        echo ""
        pytest tests/unit/test_reranker.py -v
        ;;

    "full"|"all")
        echo -e "${YELLOW}📊 Running Full Test Suite${NC}"
        echo ""
        pytest tests/ -v
        ;;

    "coverage")
        echo -e "${YELLOW}📈 Running Tests with Coverage Report${NC}"
        echo ""
        pytest tests/ --cov=. --cov-report=html --cov-report=term -v
        echo ""
        echo -e "${GREEN}✅ Coverage report generated in htmlcov/index.html${NC}"
        ;;

    "markers")
        echo -e "${YELLOW}🏷️ Running Tests by Marker${NC}"
        echo ""
        echo "Available markers:"
        pytest --markers
        ;;

    "help"|"-h"|"--help")
        echo "Usage: ./run_tests.sh [MODE]"
        echo ""
        echo "Available modes:"
        echo "  quick       - Run essential tests only (~2 min)"
        echo "  unit        - Run all unit tests (~5 min)"
        echo "  analyzer    - Test query analyzer only"
        echo "  tools       - Test tools only"
        echo "  reranker    - Test reranker only"
        echo "  full        - Run complete test suite (~10 min)"
        echo "  coverage    - Run tests with coverage report"
        echo "  markers     - Show available test markers"
        echo "  help        - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh quick       # Quick validation"
        echo "  ./run_tests.sh analyzer    # Test query analyzer"
        echo "  ./run_tests.sh coverage    # Generate coverage"
        ;;

    *)
        echo -e "${RED}❌ Unknown test mode: $TEST_MODE${NC}"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Tests passed!${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Tests failed!${NC}"
    echo ""
    exit 1
fi
