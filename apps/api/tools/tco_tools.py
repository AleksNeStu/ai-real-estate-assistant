"""
Total Cost of Ownership (TCO) and Rent vs Buy calculation tools.

Provides TCO calculator, TCO comparison between two scenarios,
and rent vs buy decision analysis.

The interest rate of the TCO calculator is read from the NBP reference rate
when the caller does not supply one, and every answer names the rate it used
and the date that rate was published.
"""

import math
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from tools.mortgage_tools import MortgageCalculatorTool, resolve_interest_rate


class TCOInput(BaseModel):
    """Input for Total Cost of Ownership calculator."""

    # Mortgage inputs (required)
    property_price: float = Field(description="Total property price", gt=0)
    down_payment_percent: float = Field(
        default=20.0, description="Down payment as percentage (e.g., 20 for 20%)", ge=0, le=100
    )
    interest_rate: Optional[float] = Field(
        default=None,
        description=(
            "Annual interest rate as percentage (e.g., 4.5 for 4.5%). "
            "Omit it to use the NBP reference rate, which is read at request time."
        ),
        ge=0,
    )
    loan_years: int = Field(default=30, description="Loan term in years", gt=0, le=50)

    # Additional ownership costs (optional, default to 0)
    monthly_hoa: float = Field(default=0.0, description="Monthly HOA/condo fees", ge=0)
    annual_property_tax: float = Field(default=0.0, description="Annual property tax", ge=0)
    annual_insurance: float = Field(default=0.0, description="Annual home insurance", ge=0)
    monthly_utilities: float = Field(
        default=0.0, description="Monthly utilities (electric, gas, water)", ge=0
    )
    monthly_internet: float = Field(default=0.0, description="Monthly internet/cable", ge=0)
    monthly_parking: float = Field(default=0.0, description="Monthly parking cost", ge=0)
    maintenance_percent: float = Field(
        default=1.0, description="Annual maintenance as % of property value", ge=0, le=5
    )


class TCOResult(BaseModel):
    """Result from Total Cost of Ownership calculator."""

    # Mortgage components
    monthly_payment: float
    total_interest: float
    down_payment: float
    loan_amount: float

    # TCO components (monthly)
    monthly_mortgage: float
    monthly_property_tax: float
    monthly_insurance: float
    monthly_hoa: float
    monthly_utilities: float
    monthly_internet: float
    monthly_parking: float
    monthly_maintenance: float
    monthly_tco: float

    # TCO components (annual)
    annual_mortgage: float
    annual_property_tax: float
    annual_insurance: float
    annual_hoa: float
    annual_utilities: float
    annual_internet: float
    annual_parking: float
    annual_maintenance: float
    annual_tco: float

    # Total over loan term
    total_ownership_cost: float
    total_all_costs: float  # Including down payment

    breakdown: Dict[str, float]

    # The rate the numbers were computed with
    interest_rate: Optional[float] = Field(
        default=None, description="The annual rate the costs were computed with"
    )
    interest_rate_source: Optional[str] = Field(
        default=None, description="Where that rate came from, with the date it was published"
    )


# Task #52: Enhanced TCO Models
class TCOProjection(BaseModel):
    """Year-by-year TCO projection for multi-year analysis."""

    year: int = Field(description="Year number (1, 5, 10, 20, etc.)")
    cumulative_cost: float = Field(description="Total cumulative cost up to this year")
    cumulative_principal_paid: float = Field(description="Total principal paid on mortgage")
    cumulative_interest_paid: float = Field(description="Total interest paid on mortgage")
    cumulative_equity: float = Field(description="Equity built (down payment + principal paid)")
    property_value_estimate: float = Field(description="Estimated property value at this year")
    loan_balance: float = Field(description="Remaining loan balance")
    annual_cost: float = Field(description="Total cost in this specific year")


class TCOLocationDefaults(BaseModel):
    """Location-based default cost estimates for TCO calculations."""

    country: str = Field(description="Country code (e.g., 'DE', 'US')")
    region: str = Field(description="Region/city name")
    property_tax_rate: float = Field(description="Annual property tax as % of property value")
    avg_insurance_rate: float = Field(description="Annual insurance as % of property value")
    avg_utilities_per_sqm: float = Field(description="Average monthly utilities per sqm")
    avg_internet: float = Field(description="Average monthly internet cost")
    avg_parking: float = Field(description="Average monthly parking cost")
    currency: str = Field(default="USD", description="Default currency")


class EnhancedTCOResult(BaseModel):
    """Extended TCO result with projections and analysis."""

    # Base TCO components (inherited from TCOResult)
    monthly_payment: float
    total_interest: float
    down_payment: float
    loan_amount: float

    # TCO components (monthly)
    monthly_mortgage: float
    monthly_property_tax: float
    monthly_insurance: float
    monthly_hoa: float
    monthly_utilities: float
    monthly_internet: float
    monthly_parking: float
    monthly_maintenance: float
    monthly_tco: float

    # TCO components (annual)
    annual_mortgage: float
    annual_property_tax: float
    annual_insurance: float
    annual_hoa: float
    annual_utilities: float
    annual_internet: float
    annual_parking: float
    annual_maintenance: float
    annual_tco: float

    # Total over loan term
    total_ownership_cost: float
    total_all_costs: float
    breakdown: Dict[str, float]

    # The rate the numbers were computed with
    interest_rate: Optional[float] = Field(
        default=None, description="The annual rate the costs were computed with"
    )
    interest_rate_source: Optional[str] = Field(
        default=None, description="Where that rate came from, with the date it was published"
    )

    # Enhanced fields
    projections: List[TCOProjection] = Field(
        default_factory=list, description="Multi-year projections at 5, 10, 20 years"
    )
    percentage_breakdown: Dict[str, float] = Field(
        default_factory=dict, description="Cost category percentages for pie charts"
    )
    fixed_costs_monthly: float = Field(
        default=0.0, description="Fixed monthly costs (mortgage, HOA, insurance)"
    )
    variable_costs_monthly: float = Field(
        default=0.0, description="Variable monthly costs (utilities, maintenance)"
    )
    discretionary_costs_monthly: float = Field(
        default=0.0, description="Discretionary costs (parking, internet)"
    )


class TCOComparisonInput(BaseModel):
    """Input for comparing two property TCO scenarios."""

    # Scenario A
    scenario_a: TCOInput = Field(description="First property scenario")
    scenario_a_name: str = Field(default="Property A", description="Name for scenario A")

    # Scenario B
    scenario_b: TCOInput = Field(description="Second property scenario")
    scenario_b_name: str = Field(default="Property B", description="Name for scenario B")

    # Comparison settings
    comparison_years: int = Field(
        default=10, description="Number of years for comparison", gt=0, le=30
    )
    appreciation_rate: float = Field(
        default=3.0, description="Annual property appreciation rate %", ge=0
    )

    # User priorities for recommendation (weights 0-1)
    priority_monthly_cashflow: float = Field(
        default=0.3, description="Weight for monthly cashflow priority", ge=0, le=1
    )
    priority_long_term_equity: float = Field(
        default=0.4, description="Weight for long-term equity building", ge=0, le=1
    )
    priority_total_cost: float = Field(
        default=0.3, description="Weight for minimizing total cost", ge=0, le=1
    )


class TCOComparisonResult(BaseModel):
    """Result comparing two TCO scenarios with recommendations."""

    # Individual scenario results
    scenario_a: EnhancedTCOResult
    scenario_b: EnhancedTCOResult
    scenario_a_name: str
    scenario_b_name: str

    # Comparison metrics
    monthly_cost_difference: float = Field(
        description="Monthly cost difference (A - B). Positive means A costs more."
    )
    total_cost_difference: float = Field(
        description="Total cost difference over comparison period (A - B)"
    )
    equity_difference: float = Field(
        description="Equity difference at comparison period end (A - B)"
    )
    break_even_years: Optional[float] = Field(
        default=None, description="Years until costs equalize (if applicable)"
    )

    # Trade-off analysis
    a_advantages: List[str] = Field(default_factory=list, description="Advantages of scenario A")
    b_advantages: List[str] = Field(default_factory=list, description="Advantages of scenario B")

    # Recommendation
    recommendation: str = Field(description="'scenario_a', 'scenario_b', or 'neutral'")
    recommendation_reason: str = Field(description="Explanation for the recommendation")
    priority_score_a: float = Field(description="Weighted priority score for A (0-100)")
    priority_score_b: float = Field(description="Weighted priority score for B (0-100)")


# Task #42: Rent vs Buy Calculator Models
class RentVsBuyInput(BaseModel):
    """Input for Rent vs Buy calculator."""

    # Core inputs
    property_price: float = Field(description="Property purchase price", gt=0)
    monthly_rent: float = Field(description="Current monthly rent", ge=0)

    # Mortgage parameters
    down_payment_percent: float = Field(
        default=20.0, description="Down payment as percentage", ge=0, le=100
    )
    interest_rate: float = Field(
        default=6.5, description="Annual interest rate as percentage", ge=0
    )
    loan_years: int = Field(default=30, description="Loan term in years", gt=0, le=50)

    # Ownership costs
    annual_property_tax: float = Field(default=0.0, description="Annual property tax", ge=0)
    annual_insurance: float = Field(default=1200.0, description="Annual home insurance", ge=0)
    monthly_hoa: float = Field(default=0.0, description="Monthly HOA fees", ge=0)
    maintenance_percent: float = Field(
        default=1.0, description="Annual maintenance as percentage of property value", ge=0, le=5
    )

    # Growth rates
    appreciation_rate: float = Field(
        default=3.0, description="Annual property appreciation rate", ge=-10, le=20
    )
    rent_increase_rate: float = Field(
        default=2.5, description="Annual rent increase rate", ge=0, le=15
    )
    investment_return_rate: float = Field(
        default=7.0,
        description="Expected investment return rate for down payment alternative",
        ge=0,
        le=20,
    )

    # Tax parameters
    marginal_tax_rate: float = Field(
        default=24.0, description="Marginal tax rate for deductions", ge=0, le=50
    )

    # Analysis settings
    projection_years: int = Field(default=30, description="Number of years to project", gt=0, le=50)


class YearlyBreakdown(BaseModel):
    """Year-by-year cost breakdown for rent vs buy analysis."""

    year: int

    # Renting
    annual_rent: float
    cumulative_rent: float
    invested_savings_value: float  # Opportunity cost if down payment was invested

    # Buying
    annual_mortgage: float
    annual_property_tax: float
    annual_insurance: float
    annual_maintenance: float
    annual_hoa: float
    annual_total_ownership_cost: float
    cumulative_ownership_cost: float
    property_value: float
    loan_balance: float
    equity: float
    tax_savings: float
    net_ownership_cost: float  # After tax savings

    # Comparison
    net_benefit: float  # Positive = buying better, Negative = renting better


class RentVsBuyResult(BaseModel):
    """Result from Rent vs Buy calculator."""

    # Summary metrics
    monthly_mortgage: float
    monthly_rent_initial: float
    break_even_years: Optional[float] = None  # When buying becomes cheaper
    recommendation: str  # "rent" | "buy" | "neutral"

    # Totals at projection end
    total_rent_paid: float
    total_ownership_cost: float
    total_equity_built: float
    final_property_value: float
    opportunity_cost_of_buying: float  # Lost investment returns on down payment

    # Net comparison
    net_buying_advantage: float  # Can be negative

    # Year-by-year breakdown
    yearly_breakdown: List[YearlyBreakdown]


class TCOCalculatorTool(BaseTool):
    """Tool for calculating Total Cost of Ownership."""

    name: str = "tco_calculator"
    description: str = (
        "Calculate the Total Cost of Ownership for a property. "
        "Includes mortgage, property taxes, insurance, HOA fees, "
        "utilities, maintenance, and parking. "
        "Returns monthly and annual breakdowns."
    )
    args_schema: type[TCOInput] = TCOInput

    @staticmethod
    def calculate(
        property_price: float,
        down_payment_percent: float = 20.0,
        interest_rate: Optional[float] = None,
        loan_years: int = 30,
        monthly_hoa: float = 0.0,
        annual_property_tax: float = 0.0,
        annual_insurance: float = 0.0,
        monthly_utilities: float = 0.0,
        monthly_internet: float = 0.0,
        monthly_parking: float = 0.0,
        maintenance_percent: float = 1.0,
    ) -> TCOResult:
        """Calculate Total Cost of Ownership."""
        # A rate that was not supplied is read from NBP now, not from a constant.
        interest_rate, rate_source = resolve_interest_rate(interest_rate)

        # First, calculate mortgage components
        mortgage_result = MortgageCalculatorTool.calculate(
            property_price, down_payment_percent, interest_rate, loan_years
        )

        # Calculate monthly ownership costs
        monthly_property_tax = annual_property_tax / 12
        monthly_insurance = annual_insurance / 12
        monthly_maintenance = (property_price * maintenance_percent / 100) / 12

        # Total monthly TCO (excluding down payment)
        monthly_tco = (
            mortgage_result.monthly_payment
            + monthly_property_tax
            + monthly_insurance
            + monthly_hoa
            + monthly_utilities
            + monthly_internet
            + monthly_parking
            + monthly_maintenance
        )

        # Calculate annual totals
        annual_mortgage = mortgage_result.monthly_payment * 12
        annual_hoa = monthly_hoa * 12
        annual_utilities = monthly_utilities * 12
        annual_internet = monthly_internet * 12
        annual_parking = monthly_parking * 12
        annual_maintenance = monthly_maintenance * 12
        annual_tco = monthly_tco * 12

        # Total over loan term
        total_ownership_cost = annual_tco * loan_years
        total_all_costs = total_ownership_cost + mortgage_result.down_payment

        return TCOResult(
            # Mortgage components
            monthly_payment=mortgage_result.monthly_payment,
            total_interest=mortgage_result.total_interest,
            down_payment=mortgage_result.down_payment,
            loan_amount=mortgage_result.loan_amount,
            # TCO components (monthly)
            monthly_mortgage=mortgage_result.monthly_payment,
            monthly_property_tax=monthly_property_tax,
            monthly_insurance=monthly_insurance,
            monthly_hoa=monthly_hoa,
            monthly_utilities=monthly_utilities,
            monthly_internet=monthly_internet,
            monthly_parking=monthly_parking,
            monthly_maintenance=monthly_maintenance,
            monthly_tco=monthly_tco,
            # TCO components (annual)
            annual_mortgage=annual_mortgage,
            annual_property_tax=annual_property_tax,
            annual_insurance=annual_insurance,
            annual_hoa=annual_hoa,
            annual_utilities=annual_utilities,
            annual_internet=annual_internet,
            annual_parking=annual_parking,
            annual_maintenance=annual_maintenance,
            annual_tco=annual_tco,
            # Total over loan term
            total_ownership_cost=total_ownership_cost,
            total_all_costs=total_all_costs,
            breakdown={
                "mortgage": mortgage_result.monthly_payment,
                "property_tax": monthly_property_tax,
                "insurance": monthly_insurance,
                "hoa": monthly_hoa,
                "utilities": monthly_utilities,
                "internet": monthly_internet,
                "parking": monthly_parking,
                "maintenance": monthly_maintenance,
            },
            interest_rate=interest_rate,
            interest_rate_source=rate_source,
        )

    def _run(
        self,
        property_price: float,
        down_payment_percent: float = 20.0,
        interest_rate: Optional[float] = None,
        loan_years: int = 30,
        monthly_hoa: float = 0.0,
        annual_property_tax: float = 0.0,
        annual_insurance: float = 0.0,
        monthly_utilities: float = 0.0,
        monthly_internet: float = 0.0,
        monthly_parking: float = 0.0,
        maintenance_percent: float = 1.0,
    ) -> str:
        """Execute TCO calculation."""
        try:
            result = self.calculate(
                property_price,
                down_payment_percent,
                interest_rate,
                loan_years,
                monthly_hoa,
                annual_property_tax,
                annual_insurance,
                monthly_utilities,
                monthly_internet,
                monthly_parking,
                maintenance_percent,
            )

            formatted = f"""
Total Cost of Ownership for ${property_price:,.2f} Property:

Interest Rate: {result.interest_rate}% ({result.interest_rate_source})

=== Monthly Costs ===
Mortgage Payment:        ${result.monthly_mortgage:,.2f}
Property Tax:            ${result.monthly_property_tax:,.2f}
Home Insurance:          ${result.monthly_insurance:,.2f}
HOA Fees:                ${result.monthly_hoa:,.2f}
Utilities:               ${result.monthly_utilities:,.2f}
Internet/Cable:          ${result.monthly_internet:,.2f}
Parking:                 ${result.monthly_parking:,.2f}
Maintenance (1% rule):   ${result.monthly_maintenance:,.2f}
─────────────────────────────────────────
MONTHLY TCO:             ${result.monthly_tco:,.2f}

=== Annual Costs ===
Annual Mortgage:         ${result.annual_mortgage:,.2f}
Annual Property Tax:     ${result.annual_property_tax:,.2f}
Annual Insurance:        ${result.annual_insurance:,.2f}
Annual HOA:              ${result.annual_hoa:,.2f}
Annual Utilities:        ${result.annual_utilities:,.2f}
Annual Internet:         ${result.annual_internet:,.2f}
Annual Parking:          ${result.annual_parking:,.2f}
Annual Maintenance:      ${result.annual_maintenance:,.2f}
─────────────────────────────────────────
ANNUAL TCO:              ${result.annual_tco:,.2f}

=== Total Over {loan_years} Years ===
Total Ownership Cost:    ${result.total_ownership_cost:,.2f}
Plus Down Payment:       ${result.down_payment:,.2f}
─────────────────────────────────────────
TOTAL ALL-IN COST:       ${result.total_all_costs:,.2f}
"""
            return formatted.strip()

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error calculating TCO: {str(e)}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async version."""
        return self._run(*args, **kwargs)


# Task #52: TCO Comparison Tool
class TCOComparisonTool(BaseTool):
    """Tool for comparing Total Cost of Ownership between two property scenarios."""

    name: str = "tco_comparison"
    description: str = (
        "Compare the Total Cost of Ownership between two property scenarios. "
        "Analyzes trade-offs, calculates break-even points, and provides recommendations "
        "based on user priorities (monthly cashflow, long-term equity, total cost)."
    )
    args_schema: type[TCOComparisonInput] = TCOComparisonInput

    @staticmethod
    def _calculate_enhanced_tco(
        input_data: TCOInput, projection_years: List[int], appreciation_rate: float
    ) -> EnhancedTCOResult:
        """Calculate enhanced TCO with projections."""
        # A rate that was not supplied is read from NBP now, not from a constant.
        interest_rate, rate_source = resolve_interest_rate(input_data.interest_rate)

        # Get base TCO result
        base_result = TCOCalculatorTool.calculate(
            property_price=input_data.property_price,
            down_payment_percent=input_data.down_payment_percent,
            interest_rate=interest_rate,
            loan_years=input_data.loan_years,
            monthly_hoa=input_data.monthly_hoa,
            annual_property_tax=input_data.annual_property_tax,
            annual_insurance=input_data.annual_insurance,
            monthly_utilities=input_data.monthly_utilities,
            monthly_internet=input_data.monthly_internet,
            monthly_parking=input_data.monthly_parking,
            maintenance_percent=input_data.maintenance_percent,
        )

        # Calculate percentage breakdown for pie chart
        total_monthly = base_result.monthly_tco
        percentage_breakdown = {}
        if total_monthly > 0:
            for key, value in base_result.breakdown.items():
                percentage_breakdown[key] = round((value / total_monthly) * 100, 1)

        # Group costs by category
        fixed_costs = (
            base_result.monthly_mortgage
            + base_result.monthly_hoa
            + base_result.monthly_insurance
            + base_result.monthly_property_tax
        )
        variable_costs = base_result.monthly_utilities + base_result.monthly_maintenance
        discretionary_costs = base_result.monthly_internet + base_result.monthly_parking

        # Calculate projections
        projections = []
        loan_amount = base_result.loan_amount
        monthly_rate = (interest_rate / 100) / 12
        down_payment = base_result.down_payment

        cumulative_cost = 0.0
        cumulative_principal = 0.0
        cumulative_interest = 0.0
        property_value = input_data.property_price

        for year in range(1, input_data.loan_years + 1):
            # Annual costs for this year
            annual_cost = base_result.annual_tco
            cumulative_cost += annual_cost

            # Calculate principal and interest for this year (12 payments)
            year_principal = 0.0
            year_interest = 0.0

            for _ in range(12):
                if loan_amount > 0:
                    interest_payment = loan_amount * monthly_rate
                    principal_payment = base_result.monthly_payment - interest_payment
                    year_principal += principal_payment
                    year_interest += interest_payment
                    loan_amount = max(0, loan_amount - principal_payment)

            cumulative_principal += year_principal
            cumulative_interest += year_interest

            # Property value appreciation
            property_value *= 1 + appreciation_rate / 100

            # Equity = down payment + principal paid
            equity = down_payment + cumulative_principal

            if year in projection_years:
                projections.append(
                    TCOProjection(
                        year=year,
                        cumulative_cost=cumulative_cost + down_payment,
                        cumulative_principal_paid=cumulative_principal,
                        cumulative_interest_paid=cumulative_interest,
                        cumulative_equity=equity,
                        property_value_estimate=property_value,
                        loan_balance=loan_amount,
                        annual_cost=annual_cost,
                    )
                )

        return EnhancedTCOResult(
            # Copy base fields
            monthly_payment=base_result.monthly_payment,
            total_interest=base_result.total_interest,
            down_payment=base_result.down_payment,
            loan_amount=base_result.loan_amount,
            monthly_mortgage=base_result.monthly_mortgage,
            monthly_property_tax=base_result.monthly_property_tax,
            monthly_insurance=base_result.monthly_insurance,
            monthly_hoa=base_result.monthly_hoa,
            monthly_utilities=base_result.monthly_utilities,
            monthly_internet=base_result.monthly_internet,
            monthly_parking=base_result.monthly_parking,
            monthly_maintenance=base_result.monthly_maintenance,
            monthly_tco=base_result.monthly_tco,
            annual_mortgage=base_result.annual_mortgage,
            annual_property_tax=base_result.annual_property_tax,
            annual_insurance=base_result.annual_insurance,
            annual_hoa=base_result.annual_hoa,
            annual_utilities=base_result.annual_utilities,
            annual_internet=base_result.annual_internet,
            annual_parking=base_result.annual_parking,
            annual_maintenance=base_result.annual_maintenance,
            annual_tco=base_result.annual_tco,
            total_ownership_cost=base_result.total_ownership_cost,
            total_all_costs=base_result.total_all_costs,
            breakdown=base_result.breakdown,
            interest_rate=interest_rate,
            interest_rate_source=rate_source,
            # Enhanced fields
            projections=projections,
            percentage_breakdown=percentage_breakdown,
            fixed_costs_monthly=fixed_costs,
            variable_costs_monthly=variable_costs,
            discretionary_costs_monthly=discretionary_costs,
        )

    @staticmethod
    def calculate(
        scenario_a: TCOInput,
        scenario_b: TCOInput,
        scenario_a_name: str = "Property A",
        scenario_b_name: str = "Property B",
        comparison_years: int = 10,
        appreciation_rate: float = 3.0,
        priority_monthly_cashflow: float = 0.3,
        priority_long_term_equity: float = 0.4,
        priority_total_cost: float = 0.3,
    ) -> TCOComparisonResult:
        """
        Compare two TCO scenarios and provide recommendation.

        Args:
            scenario_a: First property TCO input
            scenario_b: Second property TCO input
            scenario_a_name: Name for scenario A
            scenario_b_name: Name for scenario B
            comparison_years: Years to compare over
            appreciation_rate: Annual property appreciation %
            priority_monthly_cashflow: Weight for monthly cashflow (0-1)
            priority_long_term_equity: Weight for equity building (0-1)
            priority_total_cost: Weight for minimizing total cost (0-1)

        Returns:
            TCOComparisonResult with comparison and recommendation
        """
        # Calculate enhanced TCO for both scenarios
        projection_years = [5, 10, 15, 20, comparison_years]
        projection_years = sorted(set(projection_years))

        result_a = TCOComparisonTool._calculate_enhanced_tco(
            scenario_a, projection_years, appreciation_rate
        )
        result_b = TCOComparisonTool._calculate_enhanced_tco(
            scenario_b, projection_years, appreciation_rate
        )

        # Calculate comparison metrics
        monthly_diff = result_a.monthly_tco - result_b.monthly_tco

        # Find projections for comparison years
        proj_a = next((p for p in result_a.projections if p.year == comparison_years), None)
        proj_b = next((p for p in result_b.projections if p.year == comparison_years), None)

        total_cost_diff = 0.0
        equity_diff = 0.0
        break_even_years = None

        if proj_a and proj_b:
            total_cost_diff = proj_a.cumulative_cost - proj_b.cumulative_cost
            equity_diff = proj_a.cumulative_equity - proj_b.cumulative_equity

            # Calculate break-even if one is cheaper monthly but has different equity
            if monthly_diff != 0:
                # Simple break-even: when cumulative cost difference equals equity difference
                for year in range(1, comparison_years + 1):
                    pa = next((p for p in result_a.projections if p.year == year), None)
                    pb = next((p for p in result_b.projections if p.year == year), None)
                    if pa and pb:
                        net_a = pa.cumulative_equity - pa.cumulative_cost
                        net_b = pb.cumulative_equity - pb.cumulative_cost
                        if (net_a > net_b) != (result_a.monthly_tco < result_b.monthly_tco):
                            break_even_years = float(year)
                            break

        # Build advantages lists
        a_advantages = []
        b_advantages = []

        if result_a.monthly_tco < result_b.monthly_tco:
            a_advantages.append(f"Lower monthly cost by ${abs(monthly_diff):,.0f}/month")
        else:
            b_advantages.append(f"Lower monthly cost by ${abs(monthly_diff):,.0f}/month")

        if proj_a and proj_b:
            if proj_a.cumulative_equity > proj_b.cumulative_equity:
                a_advantages.append(
                    f"Builds ${abs(equity_diff):,.0f} more equity over {comparison_years} years"
                )
            else:
                b_advantages.append(
                    f"Builds ${abs(equity_diff):,.0f} more equity over {comparison_years} years"
                )

            if proj_a.cumulative_cost < proj_b.cumulative_cost:
                a_advantages.append(
                    f"Lower total cost by ${abs(total_cost_diff):,.0f} "
                    f"over {comparison_years} years"
                )
            else:
                b_advantages.append(
                    f"Lower total cost by ${abs(total_cost_diff):,.0f} "
                    f"over {comparison_years} years"
                )

        if scenario_a.property_price < scenario_b.property_price:
            a_advantages.append(
                f"Lower purchase price (${scenario_a.property_price:,.0f} "
                f"vs ${scenario_b.property_price:,.0f})"
            )
        else:
            b_advantages.append(
                f"Lower purchase price (${scenario_b.property_price:,.0f} "
                f"vs ${scenario_a.property_price:,.0f})"
            )

        # Calculate priority scores (normalize to 0-100)
        # Monthly cashflow score: lower is better
        max_monthly = max(result_a.monthly_tco, result_b.monthly_tco)
        min_monthly = min(result_a.monthly_tco, result_b.monthly_tco)
        if max_monthly > min_monthly:
            score_monthly_a = 100 * (
                1 - (result_a.monthly_tco - min_monthly) / (max_monthly - min_monthly)
            )
            score_monthly_b = 100 * (
                1 - (result_b.monthly_tco - min_monthly) / (max_monthly - min_monthly)
            )
        else:
            score_monthly_a = score_monthly_b = 50

        # Equity score: higher is better
        if proj_a and proj_b:
            max_equity = max(proj_a.cumulative_equity, proj_b.cumulative_equity)
            min_equity = min(proj_a.cumulative_equity, proj_b.cumulative_equity)
            if max_equity > min_equity:
                score_equity_a = (
                    100 * (proj_a.cumulative_equity - min_equity) / (max_equity - min_equity)
                )
                score_equity_b = (
                    100 * (proj_b.cumulative_equity - min_equity) / (max_equity - min_equity)
                )
            else:
                score_equity_a = score_equity_b = 50
        else:
            score_equity_a = score_equity_b = 50

        # Total cost score: lower is better
        if proj_a and proj_b:
            max_cost = max(proj_a.cumulative_cost, proj_b.cumulative_cost)
            min_cost = min(proj_a.cumulative_cost, proj_b.cumulative_cost)
            if max_cost > min_cost:
                score_cost_a = 100 * (
                    1 - (proj_a.cumulative_cost - min_cost) / (max_cost - min_cost)
                )
                score_cost_b = 100 * (
                    1 - (proj_b.cumulative_cost - min_cost) / (max_cost - min_cost)
                )
            else:
                score_cost_a = score_cost_b = 50
        else:
            score_cost_a = score_cost_b = 50

        # Weighted total scores
        priority_score_a = (
            score_monthly_a * priority_monthly_cashflow
            + score_equity_a * priority_long_term_equity
            + score_cost_a * priority_total_cost
        )
        priority_score_b = (
            score_monthly_b * priority_monthly_cashflow
            + score_equity_b * priority_long_term_equity
            + score_cost_b * priority_total_cost
        )

        # Determine recommendation
        score_diff = priority_score_a - priority_score_b
        if abs(score_diff) < 5:
            recommendation = "neutral"
            recommendation_reason = (
                f"Both properties have similar overall scores "
                f"({priority_score_a:.0f} vs {priority_score_b:.0f}). "
                f"Consider non-financial factors like location, "
                f"size, and personal preferences."
            )
        elif score_diff > 0:
            recommendation = "scenario_a"
            recommendation_reason = (
                f"{scenario_a_name} scores higher "
                f"({priority_score_a:.0f} vs {priority_score_b:.0f}) "
                f"based on your priorities. "
                f"Key advantages: {'; '.join(a_advantages[:2])}"
            )
        else:
            recommendation = "scenario_b"
            recommendation_reason = (
                f"{scenario_b_name} scores higher "
                f"({priority_score_b:.0f} vs {priority_score_a:.0f}) "
                f"based on your priorities. "
                f"Key advantages: {'; '.join(b_advantages[:2])}"
            )

        return TCOComparisonResult(
            scenario_a=result_a,
            scenario_b=result_b,
            scenario_a_name=scenario_a_name,
            scenario_b_name=scenario_b_name,
            monthly_cost_difference=monthly_diff,
            total_cost_difference=total_cost_diff,
            equity_difference=equity_diff,
            break_even_years=break_even_years,
            a_advantages=a_advantages,
            b_advantages=b_advantages,
            recommendation=recommendation,
            recommendation_reason=recommendation_reason,
            priority_score_a=round(priority_score_a, 1),
            priority_score_b=round(priority_score_b, 1),
        )

    def _run(
        self,
        scenario_a: dict,
        scenario_b: dict,
        scenario_a_name: str = "Property A",
        scenario_b_name: str = "Property B",
        comparison_years: int = 10,
        appreciation_rate: float = 3.0,
        priority_monthly_cashflow: float = 0.3,
        priority_long_term_equity: float = 0.4,
        priority_total_cost: float = 0.3,
    ) -> str:
        """Execute TCO comparison."""
        try:
            # Convert dicts to TCOInput models
            input_a = TCOInput(**scenario_a)
            input_b = TCOInput(**scenario_b)

            result = self.calculate(
                scenario_a=input_a,
                scenario_b=input_b,
                scenario_a_name=scenario_a_name,
                scenario_b_name=scenario_b_name,
                comparison_years=comparison_years,
                appreciation_rate=appreciation_rate,
                priority_monthly_cashflow=priority_monthly_cashflow,
                priority_long_term_equity=priority_long_term_equity,
                priority_total_cost=priority_total_cost,
            )

            # Format output
            costlier = scenario_a_name if result.monthly_cost_difference > 0 else scenario_b_name
            proj_a_cost = next(
                (
                    p.cumulative_cost
                    for p in result.scenario_a.projections
                    if p.year == comparison_years
                ),
                0,
            )
            proj_b_cost = next(
                (
                    p.cumulative_cost
                    for p in result.scenario_b.projections
                    if p.year == comparison_years
                ),
                0,
            )
            proj_a_equity = next(
                (
                    p.cumulative_equity
                    for p in result.scenario_a.projections
                    if p.year == comparison_years
                ),
                0,
            )
            proj_b_equity = next(
                (
                    p.cumulative_equity
                    for p in result.scenario_b.projections
                    if p.year == comparison_years
                ),
                0,
            )
            a_adv_str = (
                "; ".join(result.a_advantages[:3]) if result.a_advantages else "None identified"
            )
            b_adv_str = (
                "; ".join(result.b_advantages[:3]) if result.b_advantages else "None identified"
            )
            output = f"""
=== TCO COMPARISON: {scenario_a_name} vs {scenario_b_name} ===

INTEREST RATE:
  {scenario_a_name}: {result.scenario_a.interest_rate}% \
({result.scenario_a.interest_rate_source})
  {scenario_b_name}: {result.scenario_b.interest_rate}% \
({result.scenario_b.interest_rate_source})

MONTHLY COSTS:
  {scenario_a_name}: ${result.scenario_a.monthly_tco:,.0f}
  {scenario_b_name}: ${result.scenario_b.monthly_tco:,.0f}
  Difference: ${abs(result.monthly_cost_difference):,.0f}/month ({costlier} costs more)

{comparison_years}-YEAR OUTLOOK:
  {scenario_a_name} Total Cost: ${proj_a_cost:,.0f}
  {scenario_b_name} Total Cost: ${proj_b_cost:,.0f}
  {scenario_a_name} Equity Built: ${proj_a_equity:,.0f}
  {scenario_b_name} Equity Built: ${proj_b_equity:,.0f}

ADVANTAGES:
  {scenario_a_name}: {a_adv_str}
  {scenario_b_name}: {b_adv_str}

RECOMMENDATION: {result.recommendation.upper()}
  {result.recommendation_reason}

Priority Scores: {scenario_a_name}={result.priority_score_a}, \
{scenario_b_name}={result.priority_score_b}
"""
            return output.strip()

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error comparing TCO: {str(e)}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async version."""
        return self._run(*args, **kwargs)


# Task #42: Rent vs Buy Calculator Tool
class RentVsBuyCalculatorTool(BaseTool):
    """Tool for comparing renting vs buying a property over time."""

    name: str = "rent_vs_buy_calculator"
    description: str = (
        "Compare the financial implications of renting vs buying a property over time. "
        "Calculates break-even point, total costs, tax benefits, "
        "opportunity costs, and provides a recommendation. "
        "Input includes property price, monthly rent, mortgage parameters, and growth rates."
    )
    args_schema: type[RentVsBuyInput] = RentVsBuyInput

    @staticmethod
    def calculate(
        property_price: float,
        monthly_rent: float,
        down_payment_percent: float = 20.0,
        interest_rate: float = 6.5,
        loan_years: int = 30,
        annual_property_tax: float = 0.0,
        annual_insurance: float = 1200.0,
        monthly_hoa: float = 0.0,
        maintenance_percent: float = 1.0,
        appreciation_rate: float = 3.0,
        rent_increase_rate: float = 2.5,
        investment_return_rate: float = 7.0,
        marginal_tax_rate: float = 24.0,
        projection_years: int = 30,
    ) -> RentVsBuyResult:
        """
        Calculate comprehensive rent vs buy comparison.

        Args:
            property_price: Property purchase price
            monthly_rent: Current monthly rent
            down_payment_percent: Down payment percentage (default 20%)
            interest_rate: Annual mortgage interest rate (default 6.5%)
            loan_years: Loan term in years (default 30)
            annual_property_tax: Annual property tax
            annual_insurance: Annual home insurance
            monthly_hoa: Monthly HOA fees
            maintenance_percent: Annual maintenance as % of property value
            appreciation_rate: Annual property appreciation rate
            rent_increase_rate: Annual rent increase rate
            investment_return_rate: Expected investment return for down payment alternative
            marginal_tax_rate: Marginal tax rate for deductions
            projection_years: Number of years to project

        Returns:
            RentVsBuyResult with yearly breakdown and recommendation
        """
        # Validate inputs
        if property_price <= 0:
            raise ValueError("Property price must be positive")
        if monthly_rent < 0:
            raise ValueError("Monthly rent cannot be negative")

        # Calculate mortgage components
        down_payment = property_price * (down_payment_percent / 100)
        loan_amount = property_price - down_payment
        monthly_rate = (interest_rate / 100) / 12
        num_payments = loan_years * 12

        # Monthly mortgage payment (standard amortization formula)
        if monthly_rate == 0:
            monthly_mortgage = loan_amount / num_payments
        else:
            monthly_mortgage = (
                loan_amount * monthly_rate * math.pow(1 + monthly_rate, num_payments)
            ) / (math.pow(1 + monthly_rate, num_payments) - 1)

        # Year-by-year calculations
        yearly_breakdown: List[YearlyBreakdown] = []
        cumulative_rent = 0.0
        cumulative_ownership_cost = 0.0
        current_rent = monthly_rent
        current_property_value = property_price
        current_loan_balance = loan_amount
        break_even_years: Optional[float] = None

        # Track invested down payment (opportunity cost)
        invested_down_payment = down_payment

        for year in range(1, projection_years + 1):
            # === RENTING COSTS ===
            annual_rent = current_rent * 12
            cumulative_rent += annual_rent

            # Opportunity cost: down payment invested instead
            invested_down_payment = invested_down_payment * (1 + investment_return_rate / 100)

            # === BUYING COSTS ===
            annual_mortgage = monthly_mortgage * 12
            annual_maintenance = property_price * (maintenance_percent / 100)
            annual_hoa = monthly_hoa * 12
            annual_total_ownership = (
                annual_mortgage
                + annual_property_tax
                + annual_insurance
                + annual_maintenance
                + annual_hoa
            )

            # Tax savings (mortgage interest + property tax deduction)
            # Interest portion of mortgage payment (higher in early years)
            interest_this_year = current_loan_balance * (interest_rate / 100)
            # Mortgage interest deduction (capped at $750k loan)
            deductible_interest = min(
                interest_this_year, min(loan_amount, 750000) * (interest_rate / 100)
            )
            # Property tax deduction (SALT cap at $10k)
            deductible_tax = min(annual_property_tax, 10000)
            # Total tax savings
            tax_savings = (deductible_interest + deductible_tax) * (marginal_tax_rate / 100)

            net_ownership_cost = annual_total_ownership - tax_savings
            cumulative_ownership_cost += net_ownership_cost

            # Property appreciation
            current_property_value = current_property_value * (1 + appreciation_rate / 100)

            # Loan balance reduction (amortization)
            principal_this_year = annual_mortgage - interest_this_year
            current_loan_balance = max(0, current_loan_balance - principal_this_year)

            # Equity built
            equity = current_property_value - current_loan_balance

            # Net benefit calculation:
            # Compare total cost of renting (including opportunity cost)
            # vs total cost of owning (offset by equity built)
            rent_total_position = cumulative_rent + invested_down_payment
            buy_total_position = cumulative_ownership_cost - equity
            net_benefit = rent_total_position - buy_total_position

            # Track break-even point
            if break_even_years is None and net_benefit > 0:
                break_even_years = float(year)

            yearly_breakdown.append(
                YearlyBreakdown(
                    year=year,
                    annual_rent=annual_rent,
                    cumulative_rent=cumulative_rent,
                    invested_savings_value=invested_down_payment,
                    annual_mortgage=annual_mortgage,
                    annual_property_tax=annual_property_tax,
                    annual_insurance=annual_insurance,
                    annual_maintenance=annual_maintenance,
                    annual_hoa=annual_hoa,
                    annual_total_ownership_cost=annual_total_ownership,
                    cumulative_ownership_cost=cumulative_ownership_cost,
                    property_value=current_property_value,
                    loan_balance=current_loan_balance,
                    equity=equity,
                    tax_savings=tax_savings,
                    net_ownership_cost=net_ownership_cost,
                    net_benefit=net_benefit,
                )
            )

            # Increase rent for next year
            current_rent = current_rent * (1 + rent_increase_rate / 100)

        # Determine recommendation
        if break_even_years is None:
            recommendation = "rent"
        elif break_even_years <= 5:
            recommendation = "buy"
        elif break_even_years <= 10:
            recommendation = "neutral"
        else:
            recommendation = "rent"

        # Final calculations
        final_breakdown = yearly_breakdown[-1]
        opportunity_cost = invested_down_payment - down_payment

        return RentVsBuyResult(
            monthly_mortgage=monthly_mortgage,
            monthly_rent_initial=monthly_rent,
            break_even_years=break_even_years,
            recommendation=recommendation,
            total_rent_paid=cumulative_rent,
            total_ownership_cost=cumulative_ownership_cost,
            total_equity_built=final_breakdown.equity,
            final_property_value=final_breakdown.property_value,
            opportunity_cost_of_buying=opportunity_cost,
            net_buying_advantage=final_breakdown.net_benefit,
            yearly_breakdown=yearly_breakdown,
        )

    def _run(
        self,
        property_price: float,
        monthly_rent: float,
        down_payment_percent: float = 20.0,
        interest_rate: float = 6.5,
        loan_years: int = 30,
        annual_property_tax: float = 0.0,
        annual_insurance: float = 1200.0,
        monthly_hoa: float = 0.0,
        maintenance_percent: float = 1.0,
        appreciation_rate: float = 3.0,
        rent_increase_rate: float = 2.5,
        investment_return_rate: float = 7.0,
        marginal_tax_rate: float = 24.0,
        projection_years: int = 30,
    ) -> str:
        """Execute rent vs buy calculation."""
        try:
            result = self.calculate(
                property_price,
                monthly_rent,
                down_payment_percent,
                interest_rate,
                loan_years,
                annual_property_tax,
                annual_insurance,
                monthly_hoa,
                maintenance_percent,
                appreciation_rate,
                rent_increase_rate,
                investment_return_rate,
                marginal_tax_rate,
                projection_years,
            )

            # Format result for display
            break_even_str = (
                f"{result.break_even_years:.1f} years"
                if result.break_even_years
                else "Not within projection period"
            )

            formatted = f"""
Rent vs Buy Analysis for ${property_price:,.2f} Property (Current Rent: ${monthly_rent:,.2f}/mo)

=== Summary ===
Monthly Mortgage:      ${result.monthly_mortgage:,.2f}
Monthly Rent:           ${result.monthly_rent_initial:,.2f}
Break-Even Point:       {break_even_str}
Recommendation:         {result.recommendation.upper()}

=== 30-Year Projections ===
Total Rent Paid:        ${result.total_rent_paid:,.2f}
Total Ownership Cost:   ${result.total_ownership_cost:,.2f}
Equity Built:           ${result.total_equity_built:,.2f}
Final Property Value:   ${result.final_property_value:,.2f}

Net Buying Advantage:  ${result.net_buying_advantage:,.2f}
(Positive = buying better, Negative = renting better)
"""
            return formatted.strip()

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error calculating rent vs buy: {str(e)}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async version."""
        return self._run(*args, **kwargs)
