#!/bin/bash

# Test runner script for AI Real Estate Assistant
# Provides different testing modes for all phases (2-5) validation

set -e

echo "🧪 AI Real Estate Assistant - Test Suite (All Phases)"
echo "======================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found. Installing test dependencies...${NC}"
    pip install pytest pytest-cov pytest-asyncio pytest-mock
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

    "phase2")
        echo -e "${YELLOW}🧠 Running Phase 2 Tests Only${NC}"
        echo ""
        pytest tests/unit/test_query_analyzer.py \
               tests/unit/test_tools.py \
               tests/unit/test_reranker.py \
               -v
        ;;

    "phase3")
        echo -e "${YELLOW}🚀 Running Phase 3 Tests Only${NC}"
        echo ""
        pytest tests/unit/test_market_insights.py \
               tests/unit/test_exporters.py \
               tests/unit/test_saved_searches.py \
               tests/unit/test_session_tracker.py \
               tests/unit/test_comparison_viz.py \
               -v
        ;;

    "insights")
        echo -e "${YELLOW}📈 Testing Market Insights${NC}"
        echo ""
        pytest tests/unit/test_market_insights.py -v
        ;;

    "exporters")
        echo -e "${YELLOW}💾 Testing Exporters${NC}"
        echo ""
        pytest tests/unit/test_exporters.py -v
        ;;

    "searches")
        echo -e "${YELLOW}🔍 Testing Saved Searches${NC}"
        echo ""
        pytest tests/unit/test_saved_searches.py -v
        ;;

    "tracker")
        echo -e "${YELLOW}📊 Testing Session Tracker${NC}"
        echo ""
        pytest tests/unit/test_session_tracker.py -v
        ;;

    "comparison")
        echo -e "${YELLOW}🔄 Testing Property Comparison${NC}"
        echo ""
        pytest tests/unit/test_comparison_viz.py -v
        ;;

    "phase4")
        echo -e "${YELLOW}🚀 Running Phase 4 Tests Only${NC}"
        echo ""
        pytest tests/unit/test_radar_charts.py \
               tests/unit/test_metrics.py \
               -v
        ;;

    "radar")
        echo -e "${YELLOW}📊 Testing Radar Charts${NC}"
        echo ""
        pytest tests/unit/test_radar_charts.py -v
        ;;

    "metrics")
        echo -e "${YELLOW}📈 Testing Metrics${NC}"
        echo ""
        pytest tests/unit/test_metrics.py -v
        ;;

    "phase5")
        echo -e "${YELLOW}🚀 Running Phase 5 Tests Only${NC}"
        echo ""
        pytest tests/unit/test_notifications.py -v
        ;;

    "notifications")
        echo -e "${YELLOW}🔔 Testing Notification System${NC}"
        echo ""
        pytest tests/unit/test_notifications.py -v
        ;;

    "full"|"all")
        echo -e "${YELLOW}📊 Running Full Test Suite (All Phases)${NC}"
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
        echo "General modes:"
        echo "  quick       - Run essential tests only (~2 min)"
        echo "  unit        - Run all unit tests (~10 min)"
        echo "  full        - Run complete test suite (~12 min)"
        echo "  coverage    - Run tests with coverage report"
        echo "  markers     - Show available test markers"
        echo ""
        echo "Phase-specific modes:"
        echo "  phase2      - Run Phase 2 tests only (Intelligence)"
        echo "  phase3      - Run Phase 3 tests only (Advanced Features)"
        echo "  phase4      - Run Phase 4 tests only (Visualizations)"
        echo "  phase5      - Run Phase 5 tests only (Notification System)"
        echo ""
        echo "Phase 2 component tests:"
        echo "  analyzer    - Test query analyzer only"
        echo "  tools       - Test tools only"
        echo "  reranker    - Test reranker only"
        echo ""
        echo "Phase 3 component tests:"
        echo "  insights    - Test market insights only"
        echo "  exporters   - Test exporters only"
        echo "  searches    - Test saved searches only"
        echo "  tracker     - Test session tracker only"
        echo "  comparison  - Test property comparison only"
        echo ""
        echo "Phase 4 component tests:"
        echo "  radar       - Test radar charts only"
        echo "  metrics     - Test metrics utilities only"
        echo ""
        echo "Phase 5 component tests:"
        echo "  notifications - Test notification system only"
        echo ""
        echo "Help:"
        echo "  help        - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh quick       # Quick validation"
        echo "  ./run_tests.sh phase3      # Test all Phase 3 features"
        echo "  ./run_tests.sh insights    # Test market insights"
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
