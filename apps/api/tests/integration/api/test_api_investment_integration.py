"""Integration tests for investment router."""

import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# --- Setup: stub heavy imports so the router module can load ---

for mod_name in [
    "langchain_core",
    "langchain_core.tools",
    "tools.mortgage_tools",
    "models.provider_factory",
    "models.providers",
    "models.providers.anthropic",
    "models.providers.openai_provider",
    "models.providers.google",
    "models.providers.ollama_provider",
    "analytics.investment_analytics",
    "utils.investment_report_generator",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Import real Pydantic models (they work fine even with mocked BaseTool)
# Make tools.property_tools a real module-like object with the real classes
from tools import investment_tools as _inv_tools  # noqa: E402
from tools.investment_tools import (  # noqa: E402
    AdvancedInvestmentInput,
    AdvancedInvestmentResult,
    InvestmentAnalysisResult,
)

# Only create a stub if the real module isn't already loaded
if "tools.property_tools" not in sys.modules:
    _pt: Any = types.ModuleType("tools.property_tools")
    _pt.InvestmentCalculatorTool = _inv_tools.InvestmentCalculatorTool
    _pt.InvestmentAnalysisResult = InvestmentAnalysisResult
    _pt.AdvancedInvestmentTool = _inv_tools.AdvancedInvestmentTool
    _pt.AdvancedInvestmentInput = AdvancedInvestmentInput
    _pt.AdvancedInvestmentResult = AdvancedInvestmentResult
    sys.modules["tools.property_tools"] = _pt

from api.routers import investment  # noqa: E402


@pytest.fixture
def test_app():
    """Create test app with investment router."""
    app = FastAPI()
    app.include_router(investment.router, prefix="/api/v1")
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _analysis_result(**overrides):
    """Create InvestmentAnalysisResult instance."""
    return InvestmentAnalysisResult(
        investment_score=overrides.get("investment_score", 72.5),
        monthly_cash_flow=overrides.get("monthly_cash_flow", 450.0),
        annual_cash_flow=overrides.get("annual_cash_flow", 5400.0),
        cash_on_cash_roi=overrides.get("cash_on_cash_roi", 8.5),
        cap_rate=overrides.get("cap_rate", 6.2),
        gross_yield=overrides.get("gross_yield", 9.6),
        net_yield=overrides.get("net_yield", 7.1),
        total_investment=overrides.get("total_investment", 78000.0),
        monthly_income=overrides.get("monthly_income", 2800.0),
        monthly_expenses=overrides.get("monthly_expenses", 2350.0),
        annual_income=overrides.get("annual_income", 33600.0),
        annual_expenses=overrides.get("annual_expenses", 28200.0),
        monthly_mortgage=overrides.get("monthly_mortgage", 1890.0),
        score_breakdown=overrides.get("score_breakdown", {"roi": 25.0, "cash_flow": 20.0}),
    )


def _advanced_result(**overrides):
    """Create AdvancedInvestmentResult instance."""
    return AdvancedInvestmentResult(
        monthly_cash_flow=overrides.get("monthly_cash_flow", 500.0),
        annual_cash_flow=overrides.get("annual_cash_flow", 6000.0),
        cap_rate=overrides.get("cap_rate", 6.5),
        cash_on_cash_roi=overrides.get("cash_on_cash_roi", 9.0),
        total_investment=overrides.get("total_investment", 80000.0),
    )


class TestInvestmentAnalyze:
    """Tests for investment analysis endpoint."""

    @pytest.mark.asyncio
    async def test_analyze_basic_investment(self, client):
        """Returns investment metrics for basic analysis."""
        mock_calc = MagicMock(return_value=_analysis_result())
        with patch.object(investment, "InvestmentCalculatorTool") as mock_cls:
            mock_cls.calculate = mock_calc
            resp = await client.post(
                "/api/v1/investment/analyze",
                json={"property_price": 350000, "monthly_rent": 2800},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "investment_score" in data
        assert "monthly_cash_flow" in data

    @pytest.mark.asyncio
    async def test_analyze_with_full_params(self, client):
        """Returns metrics with all parameters specified."""
        mock_calc = MagicMock(return_value=_analysis_result())
        with patch.object(investment, "InvestmentCalculatorTool") as mock_cls:
            mock_cls.calculate = mock_calc
            resp = await client.post(
                "/api/v1/investment/analyze",
                json={
                    "property_price": 500000,
                    "monthly_rent": 3500,
                    "down_payment_percent": 25,
                    "closing_costs": 8000,
                    "interest_rate": 5.0,
                    "loan_years": 30,
                    "property_tax_monthly": 400,
                    "insurance_monthly": 150,
                    "hoa_monthly": 200,
                    "maintenance_percent": 1.5,
                    "vacancy_rate": 5.0,
                    "management_percent": 8.0,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["investment_score"] > 0

    @pytest.mark.asyncio
    async def test_analyze_invalid_price(self, client):
        """Returns 422 for zero/negative property price."""
        resp = await client.post(
            "/api/v1/investment/analyze",
            json={"property_price": 0, "monthly_rent": 1000},
        )
        assert resp.status_code == 422


class TestInvestmentAdvanced:
    """Tests for advanced investment analysis endpoint."""

    @pytest.mark.asyncio
    async def test_advanced_analysis(self, client):
        """Returns advanced metrics with multi-year projections."""
        mock_calc = MagicMock(return_value=_advanced_result())
        with patch.object(investment, "AdvancedInvestmentTool") as mock_cls:
            mock_cls.calculate = mock_calc
            resp = await client.post(
                "/api/v1/investment/analyze/advanced",
                json={
                    "property_price": 400000,
                    "monthly_rent": 3000,
                    "projection_years": 5,
                    "appreciation_rate": 3.0,
                    "rent_growth_rate": 2.0,
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "monthly_cash_flow" in data
        assert "cash_on_cash_roi" in data

    @pytest.mark.asyncio
    async def test_advanced_with_tax_params(self, client):
        """Includes tax implications when tax params provided."""
        mock_calc = MagicMock(return_value=_advanced_result())
        with patch.object(investment, "AdvancedInvestmentTool") as mock_cls:
            mock_cls.calculate = mock_calc
            resp = await client.post(
                "/api/v1/investment/analyze/advanced",
                json={
                    "property_price": 300000,
                    "monthly_rent": 2500,
                    "marginal_tax_rate": 24.0,
                    "land_value_ratio": 0.2,
                },
            )
        assert resp.status_code == 200


class TestInvestmentReport:
    """Tests for investment report generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_json_report(self, client):
        """Returns JSON report with analysis data."""
        mock_calc = MagicMock(return_value=_analysis_result())
        with patch.object(investment, "InvestmentCalculatorTool") as mock_cls:
            mock_cls.calculate = mock_calc
            resp = await client.post(
                "/api/v1/investment/report",
                json={"property_price": 350000, "monthly_rent": 2800},
                params={"format": "json"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "metadata" in data
        assert "analysis" in data
        assert data["metadata"]["format"] == "json"

    @pytest.mark.asyncio
    async def test_generate_markdown_report(self, client):
        """Returns markdown report as text."""
        mock_calc = MagicMock(return_value=_analysis_result())
        mock_generator = MagicMock()
        mock_generator.generate_markdown.return_value = "# Investment Report\nTest"
        with (
            patch.object(investment, "InvestmentCalculatorTool") as mock_cls,
            patch.object(investment, "InvestmentReportGenerator", return_value=mock_generator),
        ):
            mock_cls.calculate = mock_calc
            resp = await client.post(
                "/api/v1/investment/report",
                json={"property_price": 350000, "monthly_rent": 2800},
                params={"format": "md"},
            )
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_generate_report_with_projection(self, client):
        """Returns report with multi-year projection when requested."""
        mock_calc = MagicMock(return_value=_analysis_result())
        mock_projection = MagicMock()
        mock_projection.property_price = 350000
        mock_projection.projection_years = 10
        mock_projection.total_cash_flow = 50000.0
        mock_projection.total_principal_paid = 30000.0
        mock_projection.final_equity = 200000.0
        mock_projection.irr = 0.12
        mock_projection.yearly_breakdown = []

        with (
            patch.object(investment, "InvestmentCalculatorTool") as mock_cls,
            patch.object(
                investment.InvestmentAnalyticsCalculator,
                "project_cash_flows",
                return_value=mock_projection,
            ),
        ):
            mock_cls.calculate = mock_calc
            resp = await client.post(
                "/api/v1/investment/report",
                json={
                    "property_price": 350000,
                    "monthly_rent": 2800,
                    "include_projection": True,
                    "projection_years": 10,
                },
                params={"format": "json"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "projection" in data
