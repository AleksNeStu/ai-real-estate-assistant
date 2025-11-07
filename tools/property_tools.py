"""
Property-specific tools for the agent.

This module provides specialized tools for property analysis, comparison,
and calculations.
"""

import math
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool


class MortgageInput(BaseModel):
    """Input for mortgage calculator."""
    property_price: float = Field(description="Total property price")
    down_payment_percent: float = Field(
        default=20.0,
        description="Down payment as percentage (e.g., 20 for 20%)"
    )
    interest_rate: float = Field(
        default=4.5,
        description="Annual interest rate as percentage (e.g., 4.5 for 4.5%)"
    )
    loan_years: int = Field(default=30, description="Loan term in years")


class MortgageResult(BaseModel):
    """Result from mortgage calculator."""
    monthly_payment: float
    total_interest: float
    total_cost: float
    down_payment: float
    loan_amount: float
    breakdown: Dict[str, float]


class MortgageCalculatorTool(BaseTool):
    """Tool for calculating mortgage payments and costs."""

    name = "mortgage_calculator"
    description = (
        "Calculate mortgage payments for a property. "
        "Input should be property price, down payment %, interest rate %, and loan years. "
        "Returns monthly payment, total interest, and breakdown."
    )

    def _run(
        self,
        property_price: float,
        down_payment_percent: float = 20.0,
        interest_rate: float = 4.5,
        loan_years: int = 30
    ) -> str:
        """Execute mortgage calculation."""
        try:
            # Validate inputs
            if property_price <= 0:
                return "Error: Property price must be positive"

            if not 0 <= down_payment_percent <= 100:
                return "Error: Down payment must be between 0 and 100%"

            if interest_rate < 0:
                return "Error: Interest rate cannot be negative"

            if loan_years <= 0:
                return "Error: Loan term must be positive"

            # Calculate values
            down_payment = property_price * (down_payment_percent / 100)
            loan_amount = property_price - down_payment

            # Monthly interest rate
            monthly_rate = (interest_rate / 100) / 12
            num_payments = loan_years * 12

            # Calculate monthly payment using mortgage formula
            if monthly_rate == 0:
                monthly_payment = loan_amount / num_payments
            else:
                monthly_payment = (
                    loan_amount
                    * monthly_rate
                    * math.pow(1 + monthly_rate, num_payments)
                ) / (math.pow(1 + monthly_rate, num_payments) - 1)

            # Total costs
            total_paid = monthly_payment * num_payments
            total_interest = total_paid - loan_amount
            total_cost = total_paid + down_payment

            # Format result
            result = f"""
Mortgage Calculation for ${property_price:,.2f} Property:

Down Payment ({down_payment_percent}%): ${down_payment:,.2f}
Loan Amount: ${loan_amount:,.2f}

Monthly Payment: ${monthly_payment:,.2f}
Annual Payment: ${monthly_payment * 12:,.2f}

Total Interest ({loan_years} years): ${total_interest:,.2f}
Total Amount Paid: ${total_paid:,.2f}
Total Cost (with down payment): ${total_cost:,.2f}

Breakdown:
- Principal: ${loan_amount:,.2f}
- Interest: ${total_interest:,.2f}
- Down Payment: ${down_payment:,.2f}
"""
            return result.strip()

        except Exception as e:
            return f"Error calculating mortgage: {str(e)}"

    async def _arun(self, *args, **kwargs) -> str:
        """Async version."""
        return self._run(*args, **kwargs)


class PropertyComparisonTool(BaseTool):
    """Tool for comparing properties side-by-side."""

    name = "property_comparator"
    description = (
        "Compare multiple properties based on various criteria. "
        "Input should be a list of property IDs or descriptions. "
        "Returns a detailed comparison with pros/cons."
    )

    def _run(self, properties: str) -> str:
        """
        Compare properties.

        Args:
            properties: String describing properties to compare

        Returns:
            Formatted comparison
        """
        # This is a placeholder - in real implementation,
        # this would retrieve actual properties from the vector store
        return f"""
Property Comparison Tool activated for: {properties}

To properly compare properties, I need specific property IDs or search criteria.
Please provide property details or search results to compare.

Comparison features:
- Price and price per square meter
- Location and amenities
- Size and layout
- Monthly costs (rent + utilities)
- Proximity to facilities
- Pros and cons analysis
"""

    async def _arun(self, properties: str) -> str:
        """Async version."""
        return self._run(properties)


class PriceAnalysisTool(BaseTool):
    """Tool for analyzing property prices and market trends."""

    name = "price_analyzer"
    description = (
        "Analyze property prices, calculate averages, and identify trends. "
        "Input should be a city or property criteria. "
        "Returns statistical analysis of prices."
    )

    def _run(self, criteria: str) -> str:
        """
        Analyze prices.

        Args:
            criteria: Search criteria for properties

        Returns:
            Price analysis
        """
        return f"""
Price Analysis Tool activated for: {criteria}

This tool can provide:
- Average, median, min, max prices
- Price per square meter statistics
- Price distribution by neighborhood
- Trend analysis
- Value for money rankings

To generate accurate analysis, this tool needs access to the property database.
"""

    async def _arun(self, criteria: str) -> str:
        """Async version."""
        return self._run(criteria)


class LocationAnalysisTool(BaseTool):
    """Tool for analyzing property locations and proximity."""

    name = "location_analyzer"
    description = (
        "Analyze property locations, calculate distances, and assess neighborhood quality. "
        "Input should be property address or city. "
        "Returns location quality score and proximity information."
    )

    def _run(self, location: str) -> str:
        """
        Analyze location.

        Args:
            location: Property location

        Returns:
            Location analysis
        """
        return f"""
Location Analysis Tool activated for: {location}

This tool can provide:
- Proximity to schools, hospitals, transport
- Neighborhood quality ratings
- Walkability scores
- Safety statistics
- Future development plans

For accurate location analysis, integration with mapping APIs is recommended.
"""

    async def _arun(self, location: str) -> str:
        """Async version."""
        return self._run(location)


# Factory function to create all tools
def create_property_tools() -> List[BaseTool]:
    """
    Create all property-related tools.

    Returns:
        List of initialized tool instances
    """
    return [
        MortgageCalculatorTool(),
        PropertyComparisonTool(),
        PriceAnalysisTool(),
        LocationAnalysisTool(),
    ]
