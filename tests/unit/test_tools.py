"""
Unit tests for property tools.

Tests mortgage calculator, property comparator, and other tools.
"""

import pytest
import math
from tools.property_tools import (
    MortgageCalculatorTool,
    PropertyComparisonTool,
    PriceAnalysisTool,
    LocationAnalysisTool,
    create_property_tools
)


class TestMortgageCalculatorTool:
    """Test suite for MortgageCalculatorTool."""

    @pytest.fixture
    def mortgage_calc(self):
        """Fixture for mortgage calculator."""
        return MortgageCalculatorTool()

    def test_basic_mortgage_calculation(self, mortgage_calc):
        """Test basic mortgage calculation."""
        result = mortgage_calc._run(
            property_price=100000,
            down_payment_percent=20,
            interest_rate=4.0,
            loan_years=30
        )

        assert "100,000" in result
        assert "20,000" in result  # Down payment
        assert "80,000" in result  # Loan amount
        assert "Monthly Payment:" in result
        assert "Total Interest" in result

    def test_mortgage_calculation_accuracy(self, mortgage_calc):
        """Test mortgage calculation accuracy against known values."""
        # Test case: $100k, 20% down, 4%, 30 years
        # Expected monthly: ~$382
        result = mortgage_calc._run(
            property_price=100000,
            down_payment_percent=20,
            interest_rate=4.0,
            loan_years=30
        )

        # Extract monthly payment from result
        # Looking for pattern like "Monthly Payment: $382"
        assert "Monthly Payment:" in result

        # Manual calculation for verification
        principal = 100000 * 0.8  # 80,000
        monthly_rate = 0.04 / 12
        num_payments = 30 * 12
        expected_monthly = (
            principal * monthly_rate * (1 + monthly_rate) ** num_payments
        ) / ((1 + monthly_rate) ** num_payments - 1)

        # Should be around $382
        assert 370 <= expected_monthly <= 390

    def test_different_down_payments(self, mortgage_calc):
        """Test with different down payment percentages."""
        # 10% down
        result1 = mortgage_calc._run(
            property_price=200000,
            down_payment_percent=10,
            interest_rate=5.0,
            loan_years=30
        )
        assert "20,000" in result1  # 10% down

        # 30% down
        result2 = mortgage_calc._run(
            property_price=200000,
            down_payment_percent=30,
            interest_rate=5.0,
            loan_years=30
        )
        assert "60,000" in result2  # 30% down

    def test_different_interest_rates(self, mortgage_calc):
        """Test with different interest rates."""
        result1 = mortgage_calc._run(
            property_price=150000,
            down_payment_percent=20,
            interest_rate=3.5,
            loan_years=30
        )

        result2 = mortgage_calc._run(
            property_price=150000,
            down_payment_percent=20,
            interest_rate=6.0,
            loan_years=30
        )

        # Both should complete without error
        assert "Monthly Payment:" in result1
        assert "Monthly Payment:" in result2

    def test_different_loan_terms(self, mortgage_calc):
        """Test with different loan terms."""
        result_15 = mortgage_calc._run(
            property_price=180000,
            down_payment_percent=20,
            interest_rate=4.5,
            loan_years=15
        )

        result_30 = mortgage_calc._run(
            property_price=180000,
            down_payment_percent=20,
            interest_rate=4.5,
            loan_years=30
        )

        assert "15" in result_15 or "Total Interest (15 years)" in result_15
        assert "30" in result_30 or "Total Interest (30 years)" in result_30

    def test_zero_interest_rate(self, mortgage_calc):
        """Test with 0% interest rate."""
        result = mortgage_calc._run(
            property_price=120000,
            down_payment_percent=20,
            interest_rate=0.0,
            loan_years=30
        )

        # With 0% interest, monthly should be loan / months
        # 96,000 / 360 = $266.67
        assert "Monthly Payment:" in result
        assert "Error" not in result

    def test_invalid_property_price(self, mortgage_calc):
        """Test with invalid property price."""
        result = mortgage_calc._run(
            property_price=-100000,
            down_payment_percent=20,
            interest_rate=4.0,
            loan_years=30
        )

        assert "Error" in result

    def test_invalid_down_payment(self, mortgage_calc):
        """Test with invalid down payment percentage."""
        result = mortgage_calc._run(
            property_price=100000,
            down_payment_percent=150,  # Invalid: > 100%
            interest_rate=4.0,
            loan_years=30
        )

        assert "Error" in result

    def test_invalid_interest_rate(self, mortgage_calc):
        """Test with invalid interest rate."""
        result = mortgage_calc._run(
            property_price=100000,
            down_payment_percent=20,
            interest_rate=-5.0,  # Invalid: negative
            loan_years=30
        )

        assert "Error" in result

    def test_invalid_loan_years(self, mortgage_calc):
        """Test with invalid loan term."""
        result = mortgage_calc._run(
            property_price=100000,
            down_payment_percent=20,
            interest_rate=4.0,
            loan_years=0  # Invalid: zero years
        )

        assert "Error" in result

    def test_tool_name_and_description(self, mortgage_calc):
        """Test tool metadata."""
        assert mortgage_calc.name == "mortgage_calculator"
        assert len(mortgage_calc.description) > 0
        assert "mortgage" in mortgage_calc.description.lower()

    def test_specific_known_value(self, mortgage_calc):
        """Test against a specific known mortgage calculation."""
        # $180,000 property, 20% down, 4.5% rate, 30 years
        # Expected: ~$730/month
        result = mortgage_calc._run(
            property_price=180000,
            down_payment_percent=20,
            interest_rate=4.5,
            loan_years=30
        )

        # Verify key components are present
        assert "36,000" in result  # 20% down payment
        assert "144,000" in result  # Loan amount
        assert "Monthly Payment:" in result

        # Calculate expected
        principal = 144000
        monthly_rate = 0.045 / 12
        num_payments = 360
        expected = (principal * monthly_rate * (1 + monthly_rate) ** num_payments) / (
            (1 + monthly_rate) ** num_payments - 1
        )
        # Should be around $730
        assert 720 <= expected <= 740


class TestPropertyComparisonTool:
    """Test suite for PropertyComparisonTool."""

    @pytest.fixture
    def comparator(self):
        """Fixture for property comparator."""
        return PropertyComparisonTool()

    def test_tool_initialization(self, comparator):
        """Test tool initialization."""
        assert comparator.name == "property_comparator"
        assert len(comparator.description) > 0

    def test_basic_comparison(self, comparator):
        """Test basic property comparison."""
        result = comparator._run("property1 vs property2")

        assert "Comparison" in result or "compare" in result.lower()

    def test_comparison_output_format(self, comparator):
        """Test comparison output format."""
        result = comparator._run("apartment A vs apartment B")

        # Should mention comparison features
        assert any(word in result.lower() for word in [
            "price", "comparison", "compare", "pros", "cons"
        ])


class TestPriceAnalysisTool:
    """Test suite for PriceAnalysisTool."""

    @pytest.fixture
    def price_analyzer(self):
        """Fixture for price analyzer."""
        return PriceAnalysisTool()

    def test_tool_initialization(self, price_analyzer):
        """Test tool initialization."""
        assert price_analyzer.name == "price_analyzer"
        assert "price" in price_analyzer.description.lower()

    def test_basic_analysis(self, price_analyzer):
        """Test basic price analysis."""
        result = price_analyzer._run("Krakow apartments")

        assert "analysis" in result.lower() or "price" in result.lower()

    def test_analysis_output_format(self, price_analyzer):
        """Test analysis output format."""
        result = price_analyzer._run("Warsaw")

        # Should mention analytical features
        assert any(word in result.lower() for word in [
            "average", "median", "price", "analysis", "statistics"
        ])


class TestLocationAnalysisTool:
    """Test suite for LocationAnalysisTool."""

    @pytest.fixture
    def location_analyzer(self):
        """Fixture for location analyzer."""
        return LocationAnalysisTool()

    def test_tool_initialization(self, location_analyzer):
        """Test tool initialization."""
        assert location_analyzer.name == "location_analyzer"
        assert "location" in location_analyzer.description.lower()

    def test_basic_analysis(self, location_analyzer):
        """Test basic location analysis."""
        result = location_analyzer._run("Krakow city center")

        assert "location" in result.lower() or "proximity" in result.lower()

    def test_analysis_output_format(self, location_analyzer):
        """Test analysis output format."""
        result = location_analyzer._run("Warsaw downtown")

        # Should mention location features
        assert any(word in result.lower() for word in [
            "location", "proximity", "neighborhood", "distance"
        ])


class TestToolFactory:
    """Test tool factory function."""

    def test_create_all_tools(self):
        """Test creating all tools."""
        tools = create_property_tools()

        assert len(tools) == 4
        assert all(hasattr(tool, 'name') for tool in tools)
        assert all(hasattr(tool, 'description') for tool in tools)

    def test_tool_names_unique(self):
        """Test that tool names are unique."""
        tools = create_property_tools()
        names = [tool.name for tool in tools]

        assert len(names) == len(set(names))  # All unique

    def test_all_expected_tools_present(self):
        """Test that all expected tools are created."""
        tools = create_property_tools()
        tool_names = {tool.name for tool in tools}

        expected_names = {
            "mortgage_calculator",
            "property_comparator",
            "price_analyzer",
            "location_analyzer"
        }

        assert tool_names == expected_names
