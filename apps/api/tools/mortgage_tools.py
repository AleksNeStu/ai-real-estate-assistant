"""
Mortgage calculation tools.

Provides mortgage payment calculator with breakdown calculations.

The interest rate is never a constant here: a rate the caller supplies is
used as it is, and a missing rate is read from the NBP reference rate at
request time. Every answer names the rate it used and the date that rate
was published.
"""

import math
from typing import Any, Dict, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from services.fx_rates import get_nbp_reference_rate


def resolve_interest_rate(interest_rate: Optional[float]) -> tuple[float, str]:
    """The rate to compute with, and the name the answer gives it.

    A rate the caller supplied is used as it is. A missing rate is read from
    the NBP reference rate, so a payment is never computed from a number the
    code made up.
    """
    if interest_rate is not None:
        return interest_rate, "caller-specified rate"

    reference = get_nbp_reference_rate()
    return reference.rate, reference.label


class MortgageInput(BaseModel):
    """Input for mortgage calculator."""

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


class MortgageResult(BaseModel):
    """Result from mortgage calculator."""

    monthly_payment: float
    total_interest: float
    total_cost: float
    down_payment: float
    loan_amount: float
    breakdown: Dict[str, float]
    interest_rate: Optional[float] = Field(
        default=None, description="The annual rate the payment was computed with"
    )
    interest_rate_source: Optional[str] = Field(
        default=None, description="Where that rate came from, with the date it was published"
    )


class MortgageCalculatorTool(BaseTool):
    """Tool for calculating mortgage payments and costs."""

    name: str = "mortgage_calculator"
    description: str = (
        "Calculate mortgage payments for a property. "
        "Input should be property price, down payment %, interest rate %, and loan years. "
        "When no interest rate is given the NBP reference rate is used. "
        "Returns monthly payment, total interest, the rate used, and breakdown."
    )

    @staticmethod
    def calculate(
        property_price: float,
        down_payment_percent: float = 20.0,
        interest_rate: Optional[float] = None,
        loan_years: int = 30,
    ) -> MortgageResult:
        """Pure calculation logic returning structured data."""
        # Validate inputs (raising ValueError instead of returning string error)
        if property_price <= 0:
            raise ValueError("Property price must be positive")
        if not 0 <= down_payment_percent <= 100:
            raise ValueError("Down payment must be between 0 and 100%")
        if interest_rate is not None and interest_rate < 0:
            raise ValueError("Interest rate cannot be negative")
        if loan_years <= 0:
            raise ValueError("Loan term must be positive")

        # A rate that was not supplied is read from NBP now, not from a constant.
        interest_rate, rate_source = resolve_interest_rate(interest_rate)

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
                loan_amount * monthly_rate * math.pow(1 + monthly_rate, num_payments)
            ) / (math.pow(1 + monthly_rate, num_payments) - 1)

        # Total costs
        total_paid = monthly_payment * num_payments
        total_interest = total_paid - loan_amount
        total_cost = total_paid + down_payment

        return MortgageResult(
            monthly_payment=monthly_payment,
            total_interest=total_interest,
            total_cost=total_cost,
            down_payment=down_payment,
            loan_amount=loan_amount,
            breakdown={
                "principal": loan_amount,
                "interest": total_interest,
                "down_payment": down_payment,
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
    ) -> str:
        """Execute mortgage calculation."""
        try:
            result = self.calculate(property_price, down_payment_percent, interest_rate, loan_years)

            # Format result
            formatted = f"""
Mortgage Calculation for ${property_price:,.2f} Property:

Interest Rate: {result.interest_rate}% ({result.interest_rate_source})
Down Payment ({down_payment_percent}%): ${result.down_payment:,.2f}
Loan Amount: ${result.loan_amount:,.2f}

Monthly Payment: ${result.monthly_payment:,.2f}
Annual Payment: ${result.monthly_payment * 12:,.2f}

Total Interest ({loan_years} years): ${result.total_interest:,.2f}
Total Amount Paid: ${result.total_cost - result.down_payment:,.2f}
Total Cost (with down payment): ${result.total_cost:,.2f}

Breakdown:
- Principal: ${result.loan_amount:,.2f}
- Interest: ${result.total_interest:,.2f}
- Down Payment: ${result.down_payment:,.2f}
"""
            return formatted.strip()

        except ValueError as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error calculating mortgage: {str(e)}"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        """Async version."""
        return self._run(*args, **kwargs)
