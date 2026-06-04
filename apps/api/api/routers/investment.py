"""Investment analysis router.

Provides endpoints for investment property analysis including
metrics calculation, cash flow projections, and report generation.
"""

import json
import logging
from datetime import datetime
from enum import Enum
from io import BytesIO

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from analytics.investment_analytics import (
    InvestmentAnalyticsCalculator,
)
from core.security_utils import sanitize_for_log
from tools.property_tools import (
    AdvancedInvestmentInput,
    AdvancedInvestmentResult,
    AdvancedInvestmentTool,
    InvestmentAnalysisResult,
    InvestmentCalculatorTool,
)
from utils.investment_report_generator import InvestmentReportGenerator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Investment"])


# ============================================================================
# Report Format Options
# ============================================================================


class ReportFormat(str, Enum):
    """Supported report formats."""

    PDF = "pdf"
    MARKDOWN = "md"
    JSON = "json"


# ============================================================================
# Request/Response Models
# ============================================================================


class InvestmentReportRequest(BaseModel):
    """Request for investment analysis report."""

    # Property basics
    property_price: float = Field(  # type: ignore[call-overload]
        description="Purchase price of the property", gt=0, example=350000
    )
    monthly_rent: float = Field(  # type: ignore[call-overload]
        description="Expected monthly rental income", gt=0, example=2800
    )

    # Purchase costs
    down_payment_percent: float = Field(
        default=20.0,
        description="Down payment as percentage (e.g., 20 for 20%)",
        ge=0,
        le=100,
    )
    closing_costs: float = Field(  # type: ignore[call-overload]
        default=0.0, description="Closing costs (one-time)", ge=0, example=5000
    )
    renovation_costs: float = Field(  # type: ignore[call-overload]
        default=0.0,
        description="Renovation/buy-and-hold costs (one-time)",
        ge=0,
        example=0,
    )

    # Financing
    interest_rate: float = Field(
        default=4.5,
        description="Annual interest rate as percentage (e.g., 4.5 for 4.5%)",
        ge=0,
    )
    loan_years: int = Field(  # type: ignore[call-overload]
        default=30, description="Loan term in years", gt=0, le=50, example=30
    )

    # Operating expenses (monthly)
    property_tax_monthly: float = Field(  # type: ignore[call-overload]
        default=0.0, description="Monthly property tax", ge=0, example=350
    )
    insurance_monthly: float = Field(  # type: ignore[call-overload]
        default=0.0, description="Monthly home insurance", ge=0, example=150
    )
    hoa_monthly: float = Field(  # type: ignore[call-overload]
        default=0.0, description="Monthly HOA/condo fees", ge=0, example=0
    )
    maintenance_percent: float = Field(  # type: ignore[call-overload]
        default=1.0,
        description="Annual maintenance as % of property value",
        ge=0,
        example=1.0,
    )
    vacancy_rate: float = Field(  # type: ignore[call-overload]
        default=5.0, description="Vacancy rate percentage", ge=0, le=100, example=5.0
    )
    management_percent: float = Field(  # type: ignore[call-overload]
        default=8.0,
        description="Property management fee as % of rent",
        ge=0,
        le=100,
        example=8.0,
    )

    # Projection options (for advanced report)
    include_projection: bool = Field(
        default=False,
        description="Include multi-year cash flow projection in report",
    )
    projection_years: int = Field(
        default=10,
        description="Number of years for projection (1-30)",
        ge=1,
        le=30,
    )
    appreciation_rate: float = Field(
        default=3.0,
        description="Annual property appreciation rate (%)",
        ge=-10,
        le=20,
    )
    rent_growth_rate: float = Field(
        default=2.0,
        description="Annual rent growth rate (%)",
        ge=0,
        le=20,
    )


class InvestmentReportMetadata(BaseModel):
    """Metadata for generated report."""

    format: str
    generated_at: str
    property_price: float
    monthly_rent: float
    investment_score: float
    cash_on_cash_roi: float
    cap_rate: float
    monthly_cash_flow: float


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/investment/report",
    responses={
        200: {
            "description": "Investment report generated successfully",
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
                "text/markdown": {"schema": {"type": "string"}},
                "application/json": {"schema": {"type": "object"}},
            },
        }
    },
    tags=["Investment"],
)
async def generate_investment_report(
    request: InvestmentReportRequest,
    format: ReportFormat = Query(
        ReportFormat.PDF,
        description="Report format (pdf, md, or json)",
    ),
):
    """
    Generate downloadable investment analysis report.

    Provides comprehensive investment analysis including:
    - Key metrics (ROI, cap rate, cash flow, rental yield)
    - Monthly/annual breakdown of income and expenses
    - Investment score with category breakdown
    - Optional multi-year projection with cash flow forecasts

    **Report Formats:**
    - **PDF**: Professional formatted document with tables and visualizations
    - **Markdown**: Plain text report for easy viewing and archiving
    - **JSON**: Structured data for programmatic access

    **Example Request:**
    ```json
    {
      "property_price": 350000,
      "monthly_rent": 2800,
      "down_payment_percent": 20,
      "interest_rate": 4.5,
      "loan_years": 30,
      "property_tax_monthly": 350,
      "insurance_monthly": 150,
      "include_projection": true,
      "projection_years": 10
    }
    ```
    """
    try:
        # Calculate basic investment metrics
        result = InvestmentCalculatorTool.calculate(
            property_price=request.property_price,
            monthly_rent=request.monthly_rent,
            down_payment_percent=request.down_payment_percent,
            closing_costs=request.closing_costs,
            renovation_costs=request.renovation_costs,
            interest_rate=request.interest_rate,
            loan_years=request.loan_years,
            property_tax_monthly=request.property_tax_monthly,
            insurance_monthly=request.insurance_monthly,
            hoa_monthly=request.hoa_monthly,
            maintenance_percent=request.maintenance_percent,
            vacancy_rate=request.vacancy_rate,
            management_percent=request.management_percent,
        )

        # Convert to dict for report generation
        result_dict = result.model_dump()

        # Add monthly expense breakdown for report
        result_dict["property_tax_monthly"] = request.property_tax_monthly
        result_dict["insurance_monthly"] = request.insurance_monthly
        result_dict["hoa_monthly"] = request.hoa_monthly
        result_dict["maintenance_monthly"] = (
            request.property_price * request.maintenance_percent / 100 / 12
        )
        result_dict["vacancy_monthly"] = request.monthly_rent * request.vacancy_rate / 100
        result_dict["management_monthly"] = request.monthly_rent * request.management_percent / 100

        # Generate projection if requested
        projection = None
        if request.include_projection:
            projection = InvestmentAnalyticsCalculator.project_cash_flows(
                property_price=request.property_price,
                monthly_rent=request.monthly_rent,
                appreciation_rate=request.appreciation_rate,
                rent_growth_rate=request.rent_growth_rate,
                projection_years=request.projection_years,
                # Default mortgage and expenses (simplified for projection)
            )

        # Generate report based on format
        generator = InvestmentReportGenerator()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == ReportFormat.PDF:
            pdf_bytes = generator.generate_pdf(result_dict, projection)
            filename = f"investment_report_{timestamp}.pdf"

            return StreamingResponse(
                BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Type": "application/pdf",
                },
            )

        elif format == ReportFormat.MARKDOWN:
            markdown_content = generator.generate_markdown(result_dict)
            filename = f"investment_report_{timestamp}.md"

            return Response(
                content=markdown_content,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )

        elif format == ReportFormat.JSON:
            # Build comprehensive JSON response
            json_data = {
                "metadata": {
                    "format": "json",
                    "generated_at": datetime.now().isoformat(),
                    "property_price": request.property_price,
                    "monthly_rent": request.monthly_rent,
                },
                "analysis": result_dict,
            }

            if projection:
                json_data["projection"] = {
                    "property_price": projection.property_price,
                    "projection_years": projection.projection_years,
                    "total_cash_flow": projection.total_cash_flow,
                    "total_principal_paid": projection.total_principal_paid,
                    "final_equity": projection.final_equity,
                    "irr": projection.irr,
                    "yearly_breakdown": [
                        {
                            "year": y.year,
                            "gross_income": y.gross_income,
                            "operating_expenses": y.operating_expenses,
                            "mortgage_payment": y.mortgage_payment,
                            "noi": y.noi,
                            "cash_flow": y.cash_flow,
                            "cumulative_cash_flow": y.cumulative_cash_flow,
                            "property_value": y.property_value,
                            "equity": y.equity,
                            "loan_balance": y.loan_balance,
                        }
                        for y in projection.yearly_breakdown
                    ],
                }

            filename = f"investment_report_{timestamp}.json"
            return Response(
                content=json.dumps(json_data, default=str),
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Report generation failed: %s", sanitize_for_log(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        ) from e


@router.post(
    "/investment/analyze",
    response_model=InvestmentAnalysisResult,
    tags=["Investment"],
)
async def analyze_investment(request: InvestmentReportRequest):
    """
    Calculate investment property metrics.

    Returns comprehensive investment analysis including:
    - Cash on Cash ROI
    - Capitalization Rate (Cap Rate)
    - Gross and Net Rental Yield
    - Monthly and Annual Cash Flow
    - Investment Score (0-100)

    This endpoint returns JSON only. For downloadable reports,
    use the `/investment/report` endpoint.
    """
    try:
        return InvestmentCalculatorTool.calculate(
            property_price=request.property_price,
            monthly_rent=request.monthly_rent,
            down_payment_percent=request.down_payment_percent,
            closing_costs=request.closing_costs,
            renovation_costs=request.renovation_costs,
            interest_rate=request.interest_rate,
            loan_years=request.loan_years,
            property_tax_monthly=request.property_tax_monthly,
            insurance_monthly=request.insurance_monthly,
            hoa_monthly=request.hoa_monthly,
            maintenance_percent=request.maintenance_percent,
            vacancy_rate=request.vacancy_rate,
            management_percent=request.management_percent,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Investment analysis failed: %s", sanitize_for_log(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        ) from e


@router.post(
    "/investment/analyze/advanced",
    response_model=AdvancedInvestmentResult,
    tags=["Investment"],
)
async def analyze_investment_advanced(request: AdvancedInvestmentInput):
    """
    Advanced investment analysis with multi-year projections.

    Provides:
    - Multi-year cash flow projections
    - Tax implications (depreciation, deductions)
    - Appreciation scenarios (pessimistic, realistic, optimistic)
    - Risk assessment scoring

    This is the same as the `/tools/advanced-investment-analysis` endpoint
    but grouped under the investment router for better organization.
    """
    try:
        return AdvancedInvestmentTool.calculate(
            property_price=request.property_price,
            monthly_rent=request.monthly_rent,
            down_payment_percent=request.down_payment_percent,
            interest_rate=request.interest_rate,
            loan_years=request.loan_years,
            property_tax_monthly=request.property_tax_monthly,
            insurance_monthly=request.insurance_monthly,
            hoa_monthly=request.hoa_monthly,
            maintenance_percent=request.maintenance_percent,
            vacancy_rate=request.vacancy_rate,
            management_percent=request.management_percent,
            projection_years=request.projection_years,
            appreciation_rate=request.appreciation_rate,
            rent_growth_rate=request.rent_growth_rate,
            marginal_tax_rate=request.marginal_tax_rate,
            land_value_ratio=request.land_value_ratio,
            market_volatility=request.market_volatility,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Advanced investment analysis failed: %s", sanitize_for_log(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Advanced analysis failed: {str(e)}",
        ) from e
