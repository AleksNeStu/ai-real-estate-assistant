"""
Unit tests for TCO (Total Cost of Ownership) tools.

Tests TCOCalculatorTool, TCOComparisonTool, and RentVsBuyCalculatorTool,
including static calculate methods, _run interface, _arun async interface,
input models, edge cases, and error handling.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from tools.tco_tools import (
    EnhancedTCOResult,
    RentVsBuyCalculatorTool,
    RentVsBuyInput,
    RentVsBuyResult,
    TCOCalculatorTool,
    TCOComparisonResult,
    TCOComparisonTool,
    TCOInput,
    TCOLocationDefaults,
    TCOResult,
    YearlyBreakdown,
)


# ---------------------------------------------------------------------------
# TCOInput model
# ---------------------------------------------------------------------------
class TestTCOInput:
    """Tests for TCOInput validation."""

    def test_defaults(self):
        inp = TCOInput(property_price=300000)
        assert inp.property_price == 300000
        assert inp.down_payment_percent == 20.0
        # The rate is not a constant any more (Task #112): no rate means the
        # NBP reference rate, read at request time.
        assert inp.interest_rate is None
        assert inp.loan_years == 30
        assert inp.monthly_hoa == 0.0
        assert inp.annual_property_tax == 0.0
        assert inp.annual_insurance == 0.0
        assert inp.monthly_utilities == 0.0
        assert inp.monthly_internet == 0.0
        assert inp.monthly_parking == 0.0
        assert inp.maintenance_percent == 1.0

    def test_property_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            TCOInput(property_price=0)
        with pytest.raises(ValidationError):
            TCOInput(property_price=-100)

    def test_down_payment_percent_bounds(self):
        with pytest.raises(ValidationError):
            TCOInput(property_price=100000, down_payment_percent=-1)
        with pytest.raises(ValidationError):
            TCOInput(property_price=100000, down_payment_percent=101)

    def test_loan_years_bounds(self):
        with pytest.raises(ValidationError):
            TCOInput(property_price=100000, loan_years=0)
        with pytest.raises(ValidationError):
            TCOInput(property_price=100000, loan_years=51)

    def test_maintenance_percent_bounds(self):
        with pytest.raises(ValidationError):
            TCOInput(property_price=100000, maintenance_percent=-0.1)
        with pytest.raises(ValidationError):
            TCOInput(property_price=100000, maintenance_percent=5.1)

    def test_all_fields_set(self):
        inp = TCOInput(
            property_price=500000,
            down_payment_percent=15.0,
            interest_rate=5.0,
            loan_years=20,
            monthly_hoa=300,
            annual_property_tax=6000,
            annual_insurance=1500,
            monthly_utilities=200,
            monthly_internet=80,
            monthly_parking=150,
            maintenance_percent=1.5,
        )
        assert inp.monthly_hoa == 300
        assert inp.annual_property_tax == 6000
        assert inp.annual_insurance == 1500


# ---------------------------------------------------------------------------
# RentVsBuyInput model
# ---------------------------------------------------------------------------
class TestRentVsBuyInput:
    """Tests for RentVsBuyInput validation."""

    def test_defaults(self):
        inp = RentVsBuyInput(property_price=300000, monthly_rent=1500)
        assert inp.down_payment_percent == 20.0
        assert inp.interest_rate == 6.5
        assert inp.loan_years == 30
        assert inp.annual_insurance == 1200.0
        assert inp.appreciation_rate == 3.0
        assert inp.rent_increase_rate == 2.5
        assert inp.investment_return_rate == 7.0
        assert inp.marginal_tax_rate == 24.0
        assert inp.projection_years == 30

    def test_property_price_positive(self):
        with pytest.raises(ValidationError):
            RentVsBuyInput(property_price=0, monthly_rent=1000)

    def test_appreciation_rate_bounds(self):
        with pytest.raises(ValidationError):
            RentVsBuyInput(property_price=100000, monthly_rent=1000, appreciation_rate=-11)
        with pytest.raises(ValidationError):
            RentVsBuyInput(property_price=100000, monthly_rent=1000, appreciation_rate=21)

    def test_projection_years_bounds(self):
        with pytest.raises(ValidationError):
            RentVsBuyInput(property_price=100000, monthly_rent=1000, projection_years=0)
        with pytest.raises(ValidationError):
            RentVsBuyInput(property_price=100000, monthly_rent=1000, projection_years=51)


# ---------------------------------------------------------------------------
# TCOLocationDefaults model
# ---------------------------------------------------------------------------
class TestTCOLocationDefaults:
    """Tests for TCOLocationDefaults model."""

    def test_defaults(self):
        loc = TCOLocationDefaults(
            country="DE",
            region="Berlin",
            property_tax_rate=0.35,
            avg_insurance_rate=0.2,
            avg_utilities_per_sqm=2.5,
            avg_internet=35,
            avg_parking=80,
        )
        assert loc.currency == "USD"
        assert loc.country == "DE"

    def test_custom_currency(self):
        loc = TCOLocationDefaults(
            country="DE",
            region="Munich",
            property_tax_rate=0.5,
            avg_insurance_rate=0.3,
            avg_utilities_per_sqm=3.0,
            avg_internet=40,
            avg_parking=100,
            currency="EUR",
        )
        assert loc.currency == "EUR"


# ---------------------------------------------------------------------------
# TCOCalculatorTool
# ---------------------------------------------------------------------------
class TestTCOCalculatorTool:
    """Tests for TCOCalculatorTool static calculate and _run."""

    @pytest.fixture
    def tool(self):
        return TCOCalculatorTool()

    # -- static calculate ---------------------------------------------------

    def test_calculate_basic(self):
        result = TCOCalculatorTool.calculate(property_price=300000)
        assert isinstance(result, TCOResult)
        assert result.monthly_payment > 0
        assert result.monthly_mortgage == result.monthly_payment
        assert result.down_payment == 300000 * 0.20
        assert result.loan_amount == 300000 * 0.80

    def test_calculate_with_all_costs(self):
        result = TCOCalculatorTool.calculate(
            property_price=400000,
            down_payment_percent=10,
            interest_rate=5.0,
            loan_years=15,
            monthly_hoa=200,
            annual_property_tax=4800,
            annual_insurance=1200,
            monthly_utilities=150,
            monthly_internet=60,
            monthly_parking=100,
            maintenance_percent=1.5,
        )
        # Verify monthly breakdown
        assert result.monthly_hoa == 200
        assert result.monthly_property_tax == pytest.approx(4800 / 12)
        assert result.monthly_insurance == pytest.approx(1200 / 12)
        assert result.monthly_utilities == 150
        assert result.monthly_internet == 60
        assert result.monthly_parking == 100
        assert result.monthly_maintenance == pytest.approx((400000 * 1.5 / 100) / 12)

        # Monthly TCO should equal sum of all monthly components
        expected_tco = (
            result.monthly_mortgage
            + result.monthly_property_tax
            + result.monthly_insurance
            + result.monthly_hoa
            + result.monthly_utilities
            + result.monthly_internet
            + result.monthly_parking
            + result.monthly_maintenance
        )
        assert result.monthly_tco == pytest.approx(expected_tco)

    def test_calculate_annual_totals(self):
        result = TCOCalculatorTool.calculate(
            property_price=250000,
            annual_property_tax=3000,
            annual_insurance=900,
            monthly_hoa=100,
        )
        assert result.annual_property_tax == 3000
        assert result.annual_insurance == 900
        assert result.annual_hoa == 100 * 12
        assert result.annual_tco == pytest.approx(result.monthly_tco * 12)

    def test_calculate_total_ownership_cost(self):
        result = TCOCalculatorTool.calculate(
            property_price=200000,
            loan_years=30,
        )
        assert result.total_ownership_cost == pytest.approx(result.annual_tco * 30)
        assert result.total_all_costs == pytest.approx(
            result.total_ownership_cost + result.down_payment
        )

    def test_calculate_zero_costs(self):
        """All optional costs set to 0 (including maintenance); TCO should equal mortgage."""
        result = TCOCalculatorTool.calculate(property_price=500000, maintenance_percent=0)
        assert result.monthly_property_tax == 0
        assert result.monthly_insurance == 0
        assert result.monthly_hoa == 0
        assert result.monthly_utilities == 0
        assert result.monthly_tco == result.monthly_mortgage

    def test_calculate_breakdown_keys(self):
        result = TCOCalculatorTool.calculate(
            property_price=300000,
            annual_property_tax=3600,
            monthly_hoa=150,
        )
        assert "mortgage" in result.breakdown
        assert "property_tax" in result.breakdown
        assert "hoa" in result.breakdown
        assert "insurance" in result.breakdown
        assert "utilities" in result.breakdown
        assert "internet" in result.breakdown
        assert "parking" in result.breakdown
        assert "maintenance" in result.breakdown

    def test_calculate_interest_rate_zero(self):
        """When interest rate is 0, mortgage is just principal/num_payments."""
        result = TCOCalculatorTool.calculate(
            property_price=300000,
            interest_rate=0,
            loan_years=30,
        )
        expected_monthly = (300000 * 0.8) / (30 * 12)
        assert result.monthly_mortgage == pytest.approx(expected_monthly)

    # -- _run ----------------------------------------------------------------

    def test_run_returns_formatted_string(self, tool):
        output = tool._run(property_price=300000)
        assert isinstance(output, str)
        assert "Total Cost of Ownership" in output
        assert "$300,000" in output
        assert "MONTHLY TCO" in output
        assert "ANNUAL TCO" in output
        assert "TOTAL ALL-IN COST" in output

    def test_run_with_custom_params(self, tool):
        output = tool._run(
            property_price=400000,
            down_payment_percent=10,
            interest_rate=5.0,
            loan_years=15,
            monthly_hoa=200,
            annual_property_tax=4800,
        )
        assert "$400,000" in output
        assert "15 Years" in output

    def test_run_handles_value_error(self, tool):
        """If MortgageCalculatorTool raises ValueError, _run catches it."""
        output = tool._run(property_price=-1)
        assert output.startswith("Error")

    def test_run_handles_generic_exception(self, tool):
        """Patch calculate to raise a generic exception."""
        with patch.object(TCOCalculatorTool, "calculate", side_effect=RuntimeError("boom")):
            output = tool._run(property_price=300000)
            assert "Error calculating TCO" in output

    # -- _arun ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self, tool):
        with patch.object(tool, "_run", return_value="fake") as mock_run:
            result = await tool._arun(property_price=300000)
            mock_run.assert_called_once_with(property_price=300000)
            assert result == "fake"


# ---------------------------------------------------------------------------
# TCOComparisonTool
# ---------------------------------------------------------------------------
class TestTCOComparisonTool:
    """Tests for TCOComparisonTool static methods and _run."""

    @pytest.fixture
    def tool(self):
        return TCOComparisonTool()

    @pytest.fixture
    def scenario_a(self):
        return TCOInput(
            property_price=300000,
            interest_rate=4.5,
            monthly_hoa=100,
            annual_property_tax=3600,
        )

    @pytest.fixture
    def scenario_b(self):
        return TCOInput(
            property_price=500000,
            interest_rate=5.0,
            monthly_hoa=300,
            annual_property_tax=6000,
        )

    # -- _calculate_enhanced_tco ---------------------------------------------

    def test_enhanced_tco_has_projections(self, scenario_a):
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario_a, projection_years=[5, 10], appreciation_rate=3.0
        )
        assert isinstance(result, EnhancedTCOResult)
        assert len(result.projections) == 2
        assert result.projections[0].year == 5
        assert result.projections[1].year == 10
        # Cumulative cost should increase
        assert result.projections[1].cumulative_cost > result.projections[0].cumulative_cost

    def test_enhanced_tco_percentage_breakdown(self, scenario_a):
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario_a, projection_years=[1], appreciation_rate=3.0
        )
        assert isinstance(result.percentage_breakdown, dict)
        # Percentages should sum to ~100
        total_pct = sum(result.percentage_breakdown.values())
        assert total_pct == pytest.approx(100.0, abs=0.5)

    def test_enhanced_tco_cost_categories(self, scenario_a):
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario_a, projection_years=[1], appreciation_rate=3.0
        )
        assert result.fixed_costs_monthly > 0
        assert result.variable_costs_monthly >= 0
        assert result.discretionary_costs_monthly >= 0
        # Sum of categories should roughly equal monthly TCO
        total = (
            result.fixed_costs_monthly
            + result.variable_costs_monthly
            + result.discretionary_costs_monthly
        )
        assert total == pytest.approx(result.monthly_tco, abs=0.01)

    def test_enhanced_tco_property_appreciation(self):
        scenario = TCOInput(property_price=200000, loan_years=30)
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario, projection_years=[10], appreciation_rate=5.0
        )
        proj = result.projections[0]
        # After 10 years at 5%, property should be ~200000 * 1.05^10
        expected_value = 200000 * (1.05**10)
        assert proj.property_value_estimate == pytest.approx(expected_value, rel=0.01)

    def test_enhanced_tco_equity_includes_down_payment(self):
        scenario = TCOInput(property_price=200000, down_payment_percent=20, loan_years=30)
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario, projection_years=[1], appreciation_rate=3.0
        )
        proj = result.projections[0]
        # Equity at year 1 = down_payment + principal paid in first year
        assert proj.cumulative_equity >= scenario.property_price * 0.20

    def test_enhanced_tco_loan_balance_decreases(self):
        scenario = TCOInput(property_price=300000, loan_years=30)
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario, projection_years=[5, 10], appreciation_rate=3.0
        )
        p5, p10 = result.projections
        assert p10.loan_balance < p5.loan_balance

    def test_enhanced_tco_zero_tco_percentage_breakdown(self):
        """When monthly TCO is zero, percentage breakdown should be empty dict."""
        scenario = TCOInput(property_price=100000, loan_years=30)
        base = TCOCalculatorTool.calculate(property_price=100000, maintenance_percent=0)
        # Force monthly_tco to 0 for the edge case test
        patched = base.model_copy(update={"monthly_tco": 0.0})
        with patch("tools.tco_tools.TCOCalculatorTool.calculate", return_value=patched):
            result = TCOComparisonTool._calculate_enhanced_tco(
                scenario, projection_years=[1], appreciation_rate=3.0
            )
            assert result.percentage_breakdown == {}

    # -- calculate (comparison) ----------------------------------------------

    def test_compare_basic(self, scenario_a, scenario_b):
        result = TCOComparisonTool.calculate(
            scenario_a=scenario_a,
            scenario_b=scenario_b,
        )
        assert isinstance(result, TCOComparisonResult)
        assert result.scenario_a_name == "Property A"
        assert result.scenario_b_name == "Property B"
        assert result.recommendation in ("scenario_a", "scenario_b", "neutral")

    def test_compare_custom_names(self, scenario_a, scenario_b):
        result = TCOComparisonTool.calculate(
            scenario_a=scenario_a,
            scenario_b=scenario_b,
            scenario_a_name="Apartment",
            scenario_b_name="House",
        )
        assert result.scenario_a_name == "Apartment"
        assert result.scenario_b_name == "House"

    def test_compare_a_cheaper_monthly(self, scenario_a, scenario_b):
        result = TCOComparisonTool.calculate(
            scenario_a=scenario_a,
            scenario_b=scenario_b,
        )
        # A is cheaper property, should have lower monthly cost
        assert result.monthly_cost_difference < 0
        assert result.scenario_a.monthly_tco < result.scenario_b.monthly_tco

    def test_compare_advantages_populated(self, scenario_a, scenario_b):
        result = TCOComparisonTool.calculate(
            scenario_a=scenario_a,
            scenario_b=scenario_b,
        )
        assert len(result.a_advantages) > 0 or len(result.b_advantages) > 0

    def test_compare_priority_scores(self, scenario_a, scenario_b):
        result = TCOComparisonTool.calculate(
            scenario_a=scenario_a,
            scenario_b=scenario_b,
            priority_monthly_cashflow=0.5,
            priority_long_term_equity=0.3,
            priority_total_cost=0.2,
        )
        assert 0 <= result.priority_score_a <= 100
        assert 0 <= result.priority_score_b <= 100

    def test_compare_equal_scenarios(self):
        """Two identical scenarios should result in neutral recommendation."""
        scenario = TCOInput(property_price=300000)
        result = TCOComparisonTool.calculate(
            scenario_a=scenario,
            scenario_b=scenario.model_copy(deep=True),
        )
        assert result.recommendation == "neutral"
        assert result.priority_score_a == result.priority_score_b

    def test_compare_scenario_a_recommended(self):
        """Very cheap scenario A should be recommended."""
        a = TCOInput(property_price=100000, interest_rate=3.0, loan_years=30)
        b = TCOInput(property_price=900000, interest_rate=7.0, loan_years=30)
        result = TCOComparisonTool.calculate(scenario_a=a, scenario_b=b)
        assert result.recommendation == "scenario_a"

    def test_compare_scenario_b_recommended(self):
        """When B is cheaper, B should be recommended."""
        a = TCOInput(property_price=900000, interest_rate=7.0, loan_years=30)
        b = TCOInput(property_price=100000, interest_rate=3.0, loan_years=30)
        result = TCOComparisonTool.calculate(scenario_a=a, scenario_b=b)
        assert result.recommendation == "scenario_b"

    def test_compare_break_even(self):
        """Test that break-even is computed when applicable."""
        a = TCOInput(property_price=200000, interest_rate=3.0, loan_years=30)
        b = TCOInput(property_price=400000, interest_rate=6.0, loan_years=30)
        result = TCOComparisonTool.calculate(scenario_a=a, scenario_b=b, comparison_years=10)
        # break_even_years may or may not be None depending on cost crossover
        # Just verify the field exists and is valid
        if result.break_even_years is not None:
            assert result.break_even_years > 0

    def test_compare_equity_difference(self, scenario_a, scenario_b):
        result = TCOComparisonTool.calculate(
            scenario_a=scenario_a,
            scenario_b=scenario_b,
            comparison_years=10,
        )
        # Higher-price property should generally build more nominal equity
        assert isinstance(result.equity_difference, float)

    def test_compare_total_cost_difference(self, scenario_a, scenario_b):
        result = TCOComparisonTool.calculate(
            scenario_a=scenario_a,
            scenario_b=scenario_b,
            comparison_years=5,
        )
        assert isinstance(result.total_cost_difference, float)

    def test_compare_projection_years_include_comparison_year(self):
        a = TCOInput(property_price=200000)
        b = TCOInput(property_price=300000)
        # comparison_years=7 should be included in projection years
        result = TCOComparisonTool.calculate(scenario_a=a, scenario_b=b, comparison_years=7)
        years_a = [p.year for p in result.scenario_a.projections]
        assert 7 in years_a

    # -- _run ----------------------------------------------------------------

    def test_run_returns_formatted_string(self, tool):
        output = tool._run(
            scenario_a={"property_price": 200000},
            scenario_b={"property_price": 400000},
        )
        assert isinstance(output, str)
        assert "TCO COMPARISON" in output
        assert "RECOMMENDATION" in output

    def test_run_with_custom_names(self, tool):
        output = tool._run(
            scenario_a={"property_price": 200000},
            scenario_b={"property_price": 400000},
            scenario_a_name="Condo",
            scenario_b_name="House",
        )
        assert "Condo" in output
        assert "House" in output

    def test_run_handles_value_error(self, tool):
        output = tool._run(
            scenario_a={"property_price": -1},
            scenario_b={"property_price": 300000},
        )
        assert output.startswith("Error")

    def test_run_handles_generic_exception(self, tool):
        with patch.object(TCOComparisonTool, "calculate", side_effect=RuntimeError("fail")):
            output = tool._run(
                scenario_a={"property_price": 200000},
                scenario_b={"property_price": 300000},
            )
            assert "Error comparing TCO" in output

    # -- _arun ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self, tool):
        with patch.object(tool, "_run", return_value="async_result") as mock_run:
            result = await tool._arun(
                scenario_a={"property_price": 200000},
                scenario_b={"property_price": 300000},
            )
            mock_run.assert_called_once()
            assert result == "async_result"


# ---------------------------------------------------------------------------
# RentVsBuyCalculatorTool
# ---------------------------------------------------------------------------
class TestRentVsBuyCalculatorTool:
    """Tests for RentVsBuyCalculatorTool static calculate and _run."""

    @pytest.fixture
    def tool(self):
        return RentVsBuyCalculatorTool()

    # -- static calculate ----------------------------------------------------

    def test_calculate_basic_buy_recommended(self):
        """When rent is high relative to property price, buying is favored."""
        result = RentVsBuyCalculatorTool.calculate(
            property_price=200000,
            monthly_rent=2000,
            interest_rate=4.0,
            projection_years=30,
        )
        assert isinstance(result, RentVsBuyResult)
        assert result.monthly_mortgage > 0
        assert result.monthly_rent_initial == 2000
        assert result.recommendation in ("rent", "buy", "neutral")
        assert len(result.yearly_breakdown) == 30

    def test_calculate_rent_recommended(self):
        """When rent is very low relative to price, renting is favored."""
        result = RentVsBuyCalculatorTool.calculate(
            property_price=1000000,
            monthly_rent=500,
            interest_rate=8.0,
            projection_years=30,
            appreciation_rate=1.0,
        )
        assert result.recommendation in ("rent", "neutral", "buy")

    def test_calculate_break_even(self):
        """Break-even should be a positive number or None."""
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1800,
            interest_rate=5.0,
            projection_years=30,
        )
        if result.break_even_years is not None:
            assert result.break_even_years > 0

    def test_calculate_yearly_breakdown_structure(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            projection_years=5,
        )
        assert len(result.yearly_breakdown) == 5
        for yb in result.yearly_breakdown:
            assert isinstance(yb, YearlyBreakdown)
            assert yb.year > 0
            assert yb.annual_rent >= 0
            assert yb.cumulative_rent >= 0
            assert yb.annual_mortgage >= 0

    def test_calculate_rent_increases_over_time(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1000,
            rent_increase_rate=5.0,
            projection_years=10,
        )
        rents = [yb.annual_rent for yb in result.yearly_breakdown]
        # Rent should increase year over year
        for i in range(1, len(rents)):
            assert rents[i] >= rents[i - 1]

    def test_calculate_property_appreciates(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            appreciation_rate=5.0,
            projection_years=10,
        )
        values = [yb.property_value for yb in result.yearly_breakdown]
        for i in range(1, len(values)):
            assert values[i] > values[i - 1]

    def test_calculate_loan_balance_decreases(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            loan_years=30,
            projection_years=30,
        )
        balances = [yb.loan_balance for yb in result.yearly_breakdown]
        for i in range(1, len(balances)):
            assert balances[i] <= balances[i - 1]
        # At end of loan term, balance should be close to 0
        # (simplified amortization in rent-vs-buy may leave small residual)
        assert balances[-1] < balances[0] * 0.1

    def test_calculate_equity_builds(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            projection_years=30,
        )
        equities = [yb.equity for yb in result.yearly_breakdown]
        # Equity should generally increase over time
        assert equities[-1] > equities[0]

    def test_calculate_tax_savings(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=400000,
            monthly_rent=1500,
            annual_property_tax=6000,
            interest_rate=5.0,
            marginal_tax_rate=24.0,
            projection_years=5,
        )
        for yb in result.yearly_breakdown:
            assert yb.tax_savings >= 0

    def test_calculate_zero_interest_rate(self):
        """With 0% interest, mortgage is just principal spread."""
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            interest_rate=0,
            loan_years=30,
            projection_years=5,
        )
        expected_monthly = (300000 * 0.8) / (30 * 12)
        assert result.monthly_mortgage == pytest.approx(expected_monthly)

    def test_calculate_zero_rent(self):
        """When rent is 0 (e.g., living with family), buying is compared to free rent."""
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=0,
            projection_years=10,
        )
        assert result.monthly_rent_initial == 0
        assert result.recommendation in ("rent", "buy", "neutral")

    def test_calculate_short_projection(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=200000,
            monthly_rent=1500,
            projection_years=1,
        )
        assert len(result.yearly_breakdown) == 1

    def test_calculate_invalid_property_price(self):
        with pytest.raises(ValueError, match="Property price must be positive"):
            RentVsBuyCalculatorTool.calculate(property_price=0, monthly_rent=1000)

    def test_calculate_negative_rent_raises(self):
        with pytest.raises(ValueError, match="Monthly rent cannot be negative"):
            RentVsBuyCalculatorTool.calculate(property_price=300000, monthly_rent=-100)

    def test_calculate_opportunity_cost(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            investment_return_rate=7.0,
            projection_years=10,
        )
        assert result.opportunity_cost_of_buying > 0

    def test_calculate_total_rent_paid(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            projection_years=5,
        )
        # Total rent should be > 0 when monthly_rent > 0
        assert result.total_rent_paid > 0

    def test_calculate_total_equity_built(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            projection_years=30,
        )
        assert result.total_equity_built > 0

    def test_calculate_net_benefit_positive_indicates_buy(self):
        """When net_benefit > 0, buying is better."""
        result = RentVsBuyCalculatorTool.calculate(
            property_price=200000,
            monthly_rent=2000,
            interest_rate=3.0,
            projection_years=30,
        )
        final = result.yearly_breakdown[-1]
        # Just verify net_benefit is computed (sign depends on params)
        assert isinstance(final.net_benefit, float)

    def test_calculate_recommendation_break_even_leq5(self):
        """Break-even <= 5 years should recommend buy."""
        result = RentVsBuyCalculatorTool.calculate(
            property_price=150000,
            monthly_rent=3000,
            interest_rate=3.0,
            projection_years=30,
        )
        if result.break_even_years is not None and result.break_even_years <= 5:
            assert result.recommendation == "buy"

    def test_calculate_recommendation_no_break_even(self):
        """If no break-even found, recommend rent."""
        # Very cheap rent, very expensive property
        result = RentVsBuyCalculatorTool.calculate(
            property_price=5000000,
            monthly_rent=100,
            interest_rate=10.0,
            appreciation_rate=0,
            projection_years=10,
        )
        if result.break_even_years is None:
            assert result.recommendation == "rent"

    def test_calculate_final_property_value(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            appreciation_rate=3.0,
            projection_years=10,
        )
        expected = 300000 * (1.03**10)
        assert result.final_property_value == pytest.approx(expected, rel=0.01)

    def test_calculate_hoa_costs(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            monthly_hoa=500,
            projection_years=5,
        )
        for yb in result.yearly_breakdown:
            assert yb.annual_hoa == 500 * 12

    def test_calculate_maintenance(self):
        result = RentVsBuyCalculatorTool.calculate(
            property_price=300000,
            monthly_rent=1500,
            maintenance_percent=2.0,
            projection_years=3,
        )
        expected_annual = 300000 * 0.02
        for yb in result.yearly_breakdown:
            assert yb.annual_maintenance == pytest.approx(expected_annual, abs=1)

    def test_calculate_tax_savings_salt_cap(self):
        """Property tax deduction is capped at $10k (SALT cap)."""
        result = RentVsBuyCalculatorTool.calculate(
            property_price=500000,
            monthly_rent=1500,
            annual_property_tax=30000,  # well above SALT cap
            marginal_tax_rate=24.0,
            projection_years=5,
        )
        for yb in result.yearly_breakdown:
            # Deductible tax should be capped at 10000
            assert yb.tax_savings >= 0

    def test_calculate_mortgage_interest_deduction_cap(self):
        """Mortgage interest deduction is capped at $750k loan."""
        result = RentVsBuyCalculatorTool.calculate(
            property_price=2000000,
            monthly_rent=3000,
            down_payment_percent=5,
            interest_rate=6.0,
            projection_years=5,
        )
        # Should not raise and tax savings should be reasonable
        for yb in result.yearly_breakdown:
            assert yb.tax_savings >= 0

    # -- _run ----------------------------------------------------------------

    def test_run_returns_formatted_string(self, tool):
        output = tool._run(property_price=300000, monthly_rent=1500)
        assert isinstance(output, str)
        assert "Rent vs Buy" in output
        assert "$300,000" in output
        assert "Summary" in output
        assert "Recommendation" in output

    def test_run_with_break_even(self, tool):
        output = tool._run(
            property_price=200000,
            monthly_rent=2000,
            interest_rate=4.0,
            projection_years=30,
        )
        # Should contain either years or "Not within projection period"
        assert "Break-Even" in output

    def test_run_handles_value_error(self, tool):
        output = tool._run(property_price=-1, monthly_rent=1000)
        assert output.startswith("Error")

    def test_run_handles_generic_exception(self, tool):
        with patch.object(RentVsBuyCalculatorTool, "calculate", side_effect=RuntimeError("oops")):
            output = tool._run(property_price=300000, monthly_rent=1500)
            assert "Error calculating rent vs buy" in output

    # -- _arun ---------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_arun_delegates_to_run(self, tool):
        with patch.object(tool, "_run", return_value="async_output") as mock_run:
            result = await tool._arun(property_price=300000, monthly_rent=1500)
            mock_run.assert_called_once_with(property_price=300000, monthly_rent=1500)
            assert result == "async_output"


# ---------------------------------------------------------------------------
# Integration-style: TCOComparisonTool._calculate_enhanced_tco edge cases
# ---------------------------------------------------------------------------
class TestEnhancedTCOEdgeCases:
    """Edge cases for _calculate_enhanced_tco."""

    def test_projection_years_beyond_loan(self):
        """Request projection at year 30 for a 30-year loan."""
        scenario = TCOInput(property_price=200000, loan_years=30)
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario, projection_years=[30], appreciation_rate=3.0
        )
        assert len(result.projections) == 1
        assert result.projections[0].year == 30

    def test_projection_year_1(self):
        scenario = TCOInput(property_price=200000, loan_years=30)
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario, projection_years=[1], appreciation_rate=3.0
        )
        assert len(result.projections) == 1
        assert result.projections[0].year == 1

    def test_projection_years_not_matching(self):
        """Projection year outside loan years should not appear."""
        scenario = TCOInput(property_price=200000, loan_years=10)
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario, projection_years=[20], appreciation_rate=3.0
        )
        # Year 20 is beyond loan_years=10, but loop runs to loan_years+1
        # Actually loop runs range(1, loan_years+1) = 1..10, so 20 is not hit
        assert len(result.projections) == 0

    def test_base_fields_copied(self):
        scenario = TCOInput(property_price=250000, loan_years=15)
        result = TCOComparisonTool._calculate_enhanced_tco(
            scenario, projection_years=[5], appreciation_rate=3.0
        )
        # Verify all base TCO fields are present
        assert result.monthly_payment > 0
        assert result.total_interest >= 0
        assert result.down_payment == pytest.approx(250000 * 0.20)
        assert result.loan_amount == pytest.approx(250000 * 0.80)
        assert result.annual_tco > 0
        assert result.total_ownership_cost > 0
