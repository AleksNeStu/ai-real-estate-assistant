"""
Unit tests for Query Analyzer.

Tests intent classification, complexity detection, filter extraction,
and tool selection.
"""

import pytest
from agents.query_analyzer import (
    QueryAnalyzer,
    QueryIntent,
    Complexity,
    Tool,
    analyze_query
)


class TestQueryAnalyzer:
    """Test suite for QueryAnalyzer."""

    def test_simple_retrieval_intent(self, query_analyzer):
        """Test simple retrieval intent classification."""
        query = "Show me apartments in Krakow"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.SIMPLE_RETRIEVAL
        assert analysis.complexity == Complexity.SIMPLE
        assert Tool.RAG_RETRIEVAL in analysis.tools_needed
        assert not analysis.requires_computation
        assert not analysis.should_use_agent()

    def test_filtered_search_intent(self, query_analyzer):
        """Test filtered search intent classification."""
        query = "Find 2-bedroom apartments under $1000 with parking"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.FILTERED_SEARCH
        assert analysis.complexity in [Complexity.MEDIUM, Complexity.SIMPLE]
        assert Tool.RAG_RETRIEVAL in analysis.tools_needed

    def test_calculation_intent(self, query_analyzer):
        """Test calculation intent classification."""
        query = "Calculate mortgage for $150,000 property"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.CALCULATION
        assert analysis.complexity == Complexity.COMPLEX
        assert analysis.requires_computation
        assert analysis.should_use_agent()

    def test_comparison_intent(self, query_analyzer):
        """Test comparison intent classification."""
        query = "Compare apartments in Warsaw vs Krakow"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.COMPARISON
        assert analysis.complexity == Complexity.COMPLEX
        assert analysis.requires_comparison
        assert analysis.should_use_agent()

    def test_analysis_intent(self, query_analyzer):
        """Test analysis intent classification."""
        query = "What's the average price per square meter in Krakow?"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.ANALYSIS
        assert analysis.complexity == Complexity.COMPLEX
        assert analysis.requires_computation
        assert Tool.PYTHON_CODE in analysis.tools_needed

    def test_recommendation_intent(self, query_analyzer):
        """Test recommendation intent classification."""
        query = "What's the best value apartment for $1000?"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.RECOMMENDATION
        assert analysis.complexity == Complexity.COMPLEX

    def test_conversation_intent(self, query_analyzer):
        """Test conversation intent classification."""
        query = "Tell me more about the last property"
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.CONVERSATION

    def test_filter_extraction_price(self, query_analyzer):
        """Test price filter extraction."""
        query = "Find apartments under $1000"
        analysis = query_analyzer.analyze(query)

        assert 'max_price' in analysis.extracted_filters
        assert analysis.extracted_filters['max_price'] == 1000.0

    def test_filter_extraction_rooms(self, query_analyzer):
        """Test rooms filter extraction."""
        query = "Find 2-bedroom apartments"
        analysis = query_analyzer.analyze(query)

        assert 'rooms' in analysis.extracted_filters
        assert analysis.extracted_filters['rooms'] == 2

    def test_filter_extraction_city(self, query_analyzer):
        """Test city filter extraction."""
        query = "Show me apartments in Krakow"
        analysis = query_analyzer.analyze(query)

        assert 'city' in analysis.extracted_filters
        assert analysis.extracted_filters['city'] == "Krakow"

    def test_filter_extraction_amenities(self, query_analyzer):
        """Test amenities filter extraction."""
        query = "Find apartments with parking and garden"
        analysis = query_analyzer.analyze(query)

        assert 'has_parking' in analysis.extracted_filters
        assert 'has_garden' in analysis.extracted_filters
        assert analysis.extracted_filters['has_parking'] is True
        assert analysis.extracted_filters['has_garden'] is True

    def test_multi_filter_extraction(self, query_analyzer):
        """Test multiple filter extraction."""
        query = "Find 2-bedroom apartments in Krakow under $1000 with parking"
        analysis = query_analyzer.analyze(query)

        assert 'rooms' in analysis.extracted_filters
        assert 'city' in analysis.extracted_filters
        assert 'max_price' in analysis.extracted_filters
        assert 'has_parking' in analysis.extracted_filters

        assert analysis.extracted_filters['rooms'] == 2
        assert analysis.extracted_filters['city'] == "Krakow"
        assert analysis.extracted_filters['max_price'] == 1000.0
        assert analysis.extracted_filters['has_parking'] is True

    def test_price_range_extraction(self, query_analyzer):
        """Test price range extraction."""
        query = "Find apartments between $800 and $1200"
        analysis = query_analyzer.analyze(query)

        assert 'min_price' in analysis.extracted_filters
        assert 'max_price' in analysis.extracted_filters
        assert analysis.extracted_filters['min_price'] == 800.0
        assert analysis.extracted_filters['max_price'] == 1200.0

    def test_mortgage_tool_selection(self, query_analyzer):
        """Test mortgage calculator tool selection."""
        query = "Calculate mortgage for property"
        analysis = query_analyzer.analyze(query)

        assert Tool.MORTGAGE_CALC in analysis.tools_needed

    def test_comparator_tool_selection(self, query_analyzer):
        """Test comparator tool selection."""
        query = "Compare properties in different cities"
        analysis = query_analyzer.analyze(query)

        assert Tool.COMPARATOR in analysis.tools_needed

    def test_complexity_detection_simple(self, query_analyzer):
        """Test simple complexity detection."""
        query = "Show me apartments"
        analysis = query_analyzer.analyze(query)

        assert analysis.complexity == Complexity.SIMPLE

    def test_complexity_detection_complex(self, query_analyzer):
        """Test complex complexity detection."""
        query = "Calculate the average price and compare"
        analysis = query_analyzer.analyze(query)

        assert analysis.complexity == Complexity.COMPLEX

    def test_should_use_agent_for_complex(self, query_analyzer):
        """Test agent usage for complex queries."""
        query = "Calculate mortgage and compare properties"
        analysis = query_analyzer.analyze(query)

        assert analysis.should_use_agent()

    def test_should_not_use_agent_for_simple(self, query_analyzer):
        """Test no agent for simple queries."""
        query = "Show me apartments"
        analysis = query_analyzer.analyze(query)

        assert not analysis.should_use_agent()

    def test_reasoning_generation(self, query_analyzer):
        """Test reasoning text generation."""
        query = "Calculate mortgage"
        analysis = query_analyzer.analyze(query)

        assert analysis.reasoning is not None
        assert len(analysis.reasoning) > 0
        assert "calculation" in analysis.reasoning.lower()

    def test_confidence_score(self, query_analyzer):
        """Test confidence score is valid."""
        query = "Show me apartments"
        analysis = query_analyzer.analyze(query)

        assert 0.0 <= analysis.confidence <= 1.0

    def test_analyze_query_function(self):
        """Test convenience function."""
        query = "Show me apartments in Krakow"
        analysis = analyze_query(query)

        assert analysis.intent == QueryIntent.SIMPLE_RETRIEVAL
        assert isinstance(analysis.extracted_filters, dict)

    def test_empty_query(self, query_analyzer):
        """Test empty query handling."""
        query = ""
        analysis = query_analyzer.analyze(query)

        assert analysis.intent == QueryIntent.GENERAL_QUESTION
        assert len(analysis.extracted_filters) == 0

    def test_complex_multi_criteria_query(self, query_analyzer):
        """Test complex query with many criteria."""
        query = (
            "Find 2-3 bedroom apartments in Krakow between $800-$1200 "
            "with parking and garden near schools"
        )
        analysis = query_analyzer.analyze(query)

        assert analysis.complexity in [Complexity.MEDIUM, Complexity.COMPLEX]
        assert len(analysis.extracted_filters) >= 3
        assert 'city' in analysis.extracted_filters
        assert 'has_parking' in analysis.extracted_filters


class TestQueryIntentClassification:
    """Test intent classification accuracy."""

    @pytest.mark.parametrize("query,expected_intent", [
        ("Show me apartments", QueryIntent.SIMPLE_RETRIEVAL),
        ("Find properties in Warsaw", QueryIntent.SIMPLE_RETRIEVAL),
        ("List available apartments", QueryIntent.SIMPLE_RETRIEVAL),
        ("Find 2-bed under $1000", QueryIntent.FILTERED_SEARCH),
        ("Search apartments with parking", QueryIntent.FILTERED_SEARCH),
        ("Calculate mortgage", QueryIntent.CALCULATION),
        ("How much is monthly payment", QueryIntent.CALCULATION),
        ("Compare Warsaw vs Krakow", QueryIntent.COMPARISON),
        ("What's the difference between", QueryIntent.COMPARISON),
        ("Average price analysis", QueryIntent.ANALYSIS),
        ("What's the mean price", QueryIntent.ANALYSIS),
        ("Recommend best value", QueryIntent.RECOMMENDATION),
        ("What's the best apartment", QueryIntent.RECOMMENDATION),
    ])
    def test_intent_classification(self, query_analyzer, query, expected_intent):
        """Test various query intents."""
        analysis = query_analyzer.analyze(query)
        assert analysis.intent == expected_intent


class TestFilterExtraction:
    """Test filter extraction accuracy."""

    @pytest.mark.parametrize("query,expected_filters", [
        ("Find apartments in Krakow", {'city': 'Krakow'}),
        ("2-bedroom apartments", {'rooms': 2}),
        ("Under $1000", {'max_price': 1000.0}),
        ("With parking", {'has_parking': True}),
        ("With garden", {'has_garden': True}),
        ("Furnished apartment", {'is_furnished': True}),
    ])
    def test_filter_extraction(self, query_analyzer, query, expected_filters):
        """Test filter extraction for various queries."""
        analysis = query_analyzer.analyze(query)

        for key, value in expected_filters.items():
            assert key in analysis.extracted_filters
            assert analysis.extracted_filters[key] == value
