"""
Unit tests for investment property analysis tools.

Tests investment calculator, ROI calculations, cap rate, cash flow, and scoring.
"""

import pytest

from tools.property_tools import (
    InvestmentCalculatorTool,
    create_property_tools,
)


class TestInvestmentCalculatorTool:
    """Test suite for InvestmentCalculatorTool."""

    @pytest.fixture
    def investment_calc(self):
        """Fixture for investment calculator."""
        return InvestmentCalculatorTool()

    def test_basic_investment_calculation(self, investment_calc):
        """Test basic investment calculation."""
        result = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1000,
            down_payment_percent=20,
            interest_rate=4.0,
            loan_years=30,
        )

        assert result.monthly_cash_flow is not None
        assert result.cash_on_cash_roi is not None
        assert result.cap_rate is not None
        assert 0 <= result.investment_score <= 100

    def test_roi_calculation_positive_cash_flow(self, investment_calc):
        """Test ROI calculation with positive cash flow."""
        result = InvestmentCalculatorTool.calculate(
            property_price=200000,
            monthly_rent=2000,  # Strong rent-to-price ratio
            down_payment_percent=20,
            closing_costs=5000,
            interest_rate=4.5,
            loan_years=30,
        )

        # With good numbers, should have positive metrics
        assert result.cash_on_cash_roi >= -100  # Allow negative but not extreme
        assert result.cap_rate >= 0
        assert result.gross_yield > 0

    def test_cap_rate_calculation(self, investment_calc):
        """Test cap rate calculation accuracy."""
        # Cap Rate = NOI / Property Price
        # NOI = Annual Rent - Operating Expenses (excluding mortgage)

        result = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1000,
            down_payment_percent=20,
            interest_rate=4.5,
            loan_years=30,
            property_tax_monthly=100,
            insurance_monthly=50,
            hoa_monthly=0,
            maintenance_percent=1,
            vacancy_rate=5,
        )

        # Annual rent = 1000 * 12 = 12000
        # Operating expenses = (100 + 50 + (100000*0.01/12) + (1000*0.05)) * 12 ≈ (150 + 83 + 50) * 12 ≈ 3396
        # NOI ≈ 12000 - 3396 = 8604
        # Cap Rate ≈ 8604 / 100000 = 8.6%
        assert 7 <= result.cap_rate <= 10  # Allow some tolerance

    def test_cash_on_cash_roi_calculation(self, investment_calc):
        """Test cash on cash ROI calculation."""
        result = InvestmentCalculatorTool.calculate(
            property_price=150000,
            monthly_rent=1500,
            down_payment_percent=25,
            closing_costs=3000,
            interest_rate=4.0,
            loan_years=30,
        )

        # Total invested = down_payment + closing_costs
        # Down payment = 150000 * 0.25 = 37500
        # Total invested = 37500 + 3000 = 40500
        # CoC ROI = Annual Cash Flow / Total Invested
        assert -200 <= result.cash_on_cash_roi <= 200  # Reasonable bounds
        assert result.total_investment > 0

    def test_vacancy_rate_impact(self, investment_calc):
        """Test that vacancy rate affects cash flow."""
        # Low vacancy
        result_low = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1000,
            vacancy_rate=0,
            down_payment_percent=20,
            interest_rate=4.0,
            loan_years=30,
        )

        # High vacancy
        result_high = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1000,
            vacancy_rate=10,  # 10% vacancy
            down_payment_percent=20,
            interest_rate=4.0,
            loan_years=30,
        )

        # Higher vacancy should reduce cash flow
        assert result_low.monthly_cash_flow >= result_high.monthly_cash_flow

    def test_negative_cash_flow_scenario(self, investment_calc):
        """Test scenario with negative cash flow."""
        result = InvestmentCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,  # Low rent relative to price
            down_payment_percent=20,
            interest_rate=6.0,  # High interest
            loan_years=30,
            property_tax_monthly=300,
            insurance_monthly=150,
        )

        # With these numbers, cash flow could be negative
        assert result.monthly_cash_flow is not None
        # Investment score should be lower for negative cash flow
        assert result.investment_score < 80  # Not an excellent investment

    def test_investment_score_ranges(self, investment_calc):
        """Test investment score is always 0-100."""
        for price in [50000, 100000, 200000, 500000]:
            for rent in [500, 1000, 2000, 4000]:
                result = InvestmentCalculatorTool.calculate(
                    property_price=price,
                    monthly_rent=rent,
                    down_payment_percent=20,
                    interest_rate=4.5,
                    loan_years=30,
                )
                assert 0 <= result.investment_score <= 100
                # Score breakdown should sum to total
                assert abs(sum(result.score_breakdown.values()) - result.investment_score) < 0.1

    def test_yield_calculations(self, investment_calc):
        """Test gross and net yield calculations."""
        result = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1000,
            down_payment_percent=20,
            interest_rate=4.5,
            loan_years=30,
        )

        # Gross yield = (Annual Rent / Property Price) * 100
        # (12000 / 100000) * 100 = 12%
        assert 11 <= result.gross_yield <= 13  # Allow some variance for expenses

        # Net yield should be lower than gross yield
        assert result.net_yield <= result.gross_yield

    def test_total_investment_calculation(self, investment_calc):
        """Test total investment includes all costs."""
        result = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1000,
            down_payment_percent=20,
            closing_costs=5000,
            renovation_costs=10000,
            interest_rate=4.5,
            loan_years=30,
        )

        # Down payment = 100000 * 0.20 = 20000
        # Total investment = 20000 + 5000 + 10000 = 35000
        expected_investment = 35000
        assert result.total_investment == expected_investment

    def test_zero_expenses(self, investment_calc):
        """Test with minimal operating expenses."""
        result = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1200,
            down_payment_percent=20,
            interest_rate=4.0,
            loan_years=30,
            property_tax_monthly=0,
            insurance_monthly=0,
            hoa_monthly=0,
            maintenance_percent=0,
            vacancy_rate=0,
        )

        # With minimal expenses, should have better metrics
        assert result.monthly_cash_flow is not None

    def test_tool_name_and_description(self, investment_calc):
        """Test tool metadata."""
        assert investment_calc.name == "investment_analyzer"
        assert len(investment_calc.description) > 0
        assert "investment" in investment_calc.description.lower()

    def test_score_breakdown_components(self, investment_calc):
        """Test that score breakdown has all expected components."""
        result = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1000,
            down_payment_percent=20,
            interest_rate=4.5,
            loan_years=30,
        )

        expected_keys = {
            "yield_score",
            "cap_rate_score",
            "cash_flow_score",
            "net_yield_score",
            "risk_score",
        }
        assert set(result.score_breakdown.keys()) == expected_keys

    def test_maintenance_percent_calculation(self, investment_calc):
        """Test that maintenance is calculated as percentage of property value."""
        result = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1000,
            down_payment_percent=20,
            interest_rate=4.5,
            loan_years=30,
            maintenance_percent=1,  # 1% annual
        )

        # Monthly maintenance = (100000 * 0.01) / 12 ≈ 83.33
        # Check that maintenance is included in expenses
        assert result.monthly_expenses > result.monthly_mortgage

    def test_management_fee_calculation(self, investment_calc):
        """Test that management fee is calculated as percentage of rent."""
        result = InvestmentCalculatorTool.calculate(
            property_price=100000,
            monthly_rent=1000,
            down_payment_percent=20,
            interest_rate=4.5,
            loan_years=30,
            management_percent=10,  # 10% of rent
        )

        # Management fee = 1000 * 0.10 = 100
        # This should be in the expenses
        assert result.monthly_expenses > result.monthly_mortgage + 100


class TestInvestmentToolFactory:
    """Test investment tool in factory function."""

    def test_investment_tool_in_factory(self):
        """Test that InvestmentCalculatorTool is included in factory."""
        tools = create_property_tools()
        tool_names = {tool.name for tool in tools}

        assert "investment_analyzer" in tool_names
        # Task #114: Added commute_analysis, multi_origin_commute
        # Task #115: Added negotiation_helper (17 total tools)
        # v5.1: Added price_forecast, neighborhood_summary (19 total tools)
        assert len(tools) == 19

    def test_all_expected_tools_present(self):
        """Test that all expected tools including investment are created."""
        tools = create_property_tools()
        tool_names = {tool.name for tool in tools}

        # Task #114: Added commute_analysis, multi_origin_commute
        # Task #115: Added negotiation_helper (17 total tools)
        # v5.1: Added price_forecast, neighborhood_summary (19 total tools)
        expected_names = {
            "mortgage_calculator",
            "tco_calculator",
            "investment_analyzer",
            "neighborhood_quality_index",
            "property_comparator",
            "price_analyzer",
            "location_analyzer",
            "commute_time_analyzer",
            "commute_ranking",
            "listing_description_generator",  # TASK-023
            "listing_headline_generator",  # TASK-023
            "social_media_content_generator",  # TASK-023
            "advanced_investment_analyzer",  # TASK-039
            "rent_vs_buy_calculator",  # Task #42
            "commute_analysis",  # Task #114
            "multi_origin_commute",  # Task #114
            "negotiation_helper",  # Task #115
            "price_forecast",  # v5.1
            "neighborhood_summary",  # v5.1
        }

        assert tool_names == expected_names
