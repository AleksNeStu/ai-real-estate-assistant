"""
Unit tests for tools router (api/routers/tools.py).

Tests cover:
- GET /tools — list available tools
- POST /tools/mortgage-calculator — mortgage payment calculation
- POST /tools/tco-calculator — total cost of ownership
- POST /tools/tco-comparison — compare TCO between two scenarios
- GET /tools/tco-location-defaults — location-based cost defaults
- GET /tools/tco-available-locations — list available locations
- POST /tools/investment-analysis — investment property metrics
- POST /tools/advanced-investment-analysis — advanced investment analytics
- POST /tools/portfolio-analysis — portfolio analysis
- POST /tools/rent-vs-buy — rent vs buy comparison
- POST /tools/neighborhood-quality — neighborhood quality index
- POST /tools/compare-properties — compare multiple properties
- POST /tools/price-analysis — price statistics for query
- POST /tools/location-analysis — location data for a property
- POST /tools/valuation — property valuation
- POST /tools/legal-check — contract text risk check
- POST /tools/enrich-address — address enrichment
- POST /tools/crm-sync-contact — CRM contact sync
- POST /tools/commute-time — commute time analysis
- POST /tools/commute-ranking — commute ranking
- POST /tools/generate-listing — listing generation
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from langchain_core.documents import Document

from api.dependencies import (
    get_crm_connector,
    get_data_enrichment_service,
    get_legal_check_service,
    get_valuation_provider,
    get_vector_store,
)
from api.routers.tools import (
    router as tools_router,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_store_mock(docs_by_ids=None, search_results=None):
    """Create a mock ChromaPropertyStore."""
    store = MagicMock()
    store.get_properties_by_ids = MagicMock(return_value=docs_by_ids or [])
    store.search = MagicMock(return_value=search_results or [])
    return store


def _make_property_doc(
    pid="p1",
    price=300000,
    price_per_sqm=5000,
    city="Berlin",
    rooms=3,
    bathrooms=2,
    area_sqm=60,
    year_built=2010,
    property_type="apartment",
    lat=52.52,
    lon=13.405,
    neighborhood="Mitte",
    country="DE",
    description="Nice apartment",
    has_parking=True,
    has_garden=False,
    has_balcony=True,
    has_elevator=True,
    has_pool=False,
    is_furnished=False,
    currency="EUR",
):
    """Create a Document with property metadata."""
    return Document(
        page_content=f"Property {pid}",
        metadata={
            "id": pid,
            "price": price,
            "price_per_sqm": price_per_sqm,
            "city": city,
            "rooms": rooms,
            "bathrooms": bathrooms,
            "area_sqm": area_sqm,
            "year_built": year_built,
            "property_type": property_type,
            "lat": lat,
            "lon": lon,
            "neighborhood": neighborhood,
            "country": country,
            "description": description,
            "has_parking": has_parking,
            "has_garden": has_garden,
            "has_balcony": has_balcony,
            "has_elevator": has_elevator,
            "has_pool": has_pool,
            "is_furnished": is_furnished,
            "currency": currency,
        },
    )


@pytest.fixture
def mock_store():
    """Return a default mock vector store."""
    return _make_store_mock()


@pytest.fixture
def mock_store_with_property():
    """Return a mock vector store that returns a single property by ID."""
    doc = _make_property_doc()
    store = _make_store_mock(docs_by_ids=[doc])
    return store


@pytest.fixture
def mock_store_with_properties():
    """Return a mock vector store that returns multiple properties."""
    docs = [
        _make_property_doc(pid="p1", price=300000, price_per_sqm=5000, property_type="apartment"),
        _make_property_doc(pid="p2", price=450000, price_per_sqm=4500, property_type="apartment"),
        _make_property_doc(pid="p3", price=200000, price_per_sqm=4000, property_type="house"),
    ]
    store = _make_store_mock(docs_by_ids=docs)
    store.search = MagicMock(return_value=[(doc, 0.9) for doc in docs])
    return store


def _build_app(store=None, provider=None, legal_service=None, enrichment=None, crm=None):
    """Build a FastAPI test app with the tools router and dependency overrides."""
    app = FastAPI()
    app.include_router(tools_router, prefix="/api/v1")

    app.dependency_overrides[get_vector_store] = lambda: store
    app.dependency_overrides[get_valuation_provider] = lambda: provider
    app.dependency_overrides[get_legal_check_service] = lambda: legal_service
    app.dependency_overrides[get_data_enrichment_service] = lambda: enrichment
    app.dependency_overrides[get_crm_connector] = lambda: crm

    return app


@pytest.fixture
async def client(mock_store):
    """Async HTTP client with tools router mounted and default mock store."""
    app = _build_app(store=mock_store)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def client_with_property(mock_store_with_property):
    """Async HTTP client with a mock store that returns a property."""
    app = _build_app(store=mock_store_with_property)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def client_with_properties(mock_store_with_properties):
    """Async HTTP client with a mock store that returns multiple properties."""
    app = _build_app(store=mock_store_with_properties)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ===========================================================================
# Test: GET /tools
# ===========================================================================


class TestListTools:
    """Tests for the list tools endpoint."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_200(self, client):
        response = await client.get("/api/v1/tools")
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_list_tools_returns_list(self, client):
        response = await client.get("/api/v1/tools")
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_list_tools_items_have_name_and_description(self, client):
        response = await client.get("/api/v1/tools")
        data = response.json()
        for item in data:
            assert "name" in item
            assert "description" in item

    @pytest.mark.asyncio
    async def test_list_tools_includes_ce_stubs(self, client):
        response = await client.get("/api/v1/tools")
        names = [item["name"] for item in response.json()]
        assert "valuation" in names
        assert "legal_check" in names
        assert "enrich_address" in names
        assert "crm_sync_contact" in names

    @pytest.mark.asyncio
    async def test_list_tools_includes_mortgage_calculator(self, client):
        response = await client.get("/api/v1/tools")
        names = [item["name"] for item in response.json()]
        assert "mortgage_calculator" in names


# ===========================================================================
# Test: POST /tools/mortgage-calculator
# ===========================================================================


class TestMortgageCalculator:
    """Tests for the mortgage calculator endpoint."""

    @pytest.mark.asyncio
    async def test_mortgage_valid_input(self, client):
        response = await client.post(
            "/api/v1/tools/mortgage-calculator",
            json={
                "property_price": 300000,
                "down_payment_percent": 20.0,
                "interest_rate": 4.5,
                "loan_years": 30,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["monthly_payment"] > 0
        assert data["total_cost"] > data["total_interest"]
        assert data["down_payment"] == 60000.0
        assert data["loan_amount"] == 240000.0

    @pytest.mark.asyncio
    async def test_mortgage_uses_defaults(self, client):
        response = await client.post(
            "/api/v1/tools/mortgage-calculator",
            json={"property_price": 500000},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["monthly_payment"] > 0

    @pytest.mark.asyncio
    async def test_mortgage_zero_price_returns_422(self, client):
        """Pydantic gt=0 catches zero before the tool's ValueError."""
        response = await client.post(
            "/api/v1/tools/mortgage-calculator",
            json={"property_price": 0},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_mortgage_negative_price_returns_422(self, client):
        response = await client.post(
            "/api/v1/tools/mortgage-calculator",
            json={"property_price": -100000},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_mortgage_missing_price_returns_422(self, client):
        response = await client.post(
            "/api/v1/tools/mortgage-calculator",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Test: POST /tools/tco-calculator
# ===========================================================================


class TestTCOCalculator:
    """Tests for the TCO calculator endpoint."""

    @pytest.mark.asyncio
    async def test_tco_valid_input(self, client):
        response = await client.post(
            "/api/v1/tools/tco-calculator",
            json={
                "property_price": 300000,
                "down_payment_percent": 20.0,
                "interest_rate": 4.5,
                "loan_years": 30,
                "monthly_hoa": 200,
                "annual_property_tax": 3000,
                "annual_insurance": 1200,
                "monthly_utilities": 150,
                "monthly_internet": 40,
                "monthly_parking": 50,
                "maintenance_percent": 1.0,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["monthly_payment"] > 0
        assert data["total_interest"] > 0

    @pytest.mark.asyncio
    async def test_tco_minimal_input(self, client):
        response = await client.post(
            "/api/v1/tools/tco-calculator",
            json={"property_price": 200000},
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_tco_zero_price_returns_422(self, client):
        """Pydantic gt=0 catches zero before the tool's ValueError."""
        response = await client.post(
            "/api/v1/tools/tco-calculator",
            json={"property_price": 0},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_tco_missing_required_field(self, client):
        response = await client.post(
            "/api/v1/tools/tco-calculator",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Test: POST /tools/tco-comparison
# ===========================================================================


class TestTCOComparison:
    """Tests for the TCO comparison endpoint."""

    @pytest.mark.asyncio
    async def test_tco_comparison_valid(self, client):
        """TCO comparison with mocked tool to avoid coupling to internal logic."""
        from tools.tco_tools import (
            EnhancedTCOResult,
            TCOComparisonResult,
        )

        def _make_enhanced(monthly_payment):
            """Build a minimal EnhancedTCOResult."""
            return EnhancedTCOResult(
                monthly_payment=monthly_payment,
                total_interest=100000.0,
                down_payment=60000.0,
                loan_amount=240000.0,
                monthly_mortgage=monthly_payment,
                monthly_property_tax=250.0,
                monthly_insurance=100.0,
                monthly_hoa=200.0,
                monthly_utilities=150.0,
                monthly_internet=40.0,
                monthly_parking=50.0,
                monthly_maintenance=250.0,
                monthly_tco=monthly_payment + 1040.0,
                annual_mortgage=monthly_payment * 12,
                annual_property_tax=3000.0,
                annual_insurance=1200.0,
                annual_hoa=2400.0,
                annual_utilities=1800.0,
                annual_internet=480.0,
                annual_parking=600.0,
                annual_maintenance=3000.0,
                annual_tco=(monthly_payment + 1040.0) * 12,
                total_ownership_cost=400000.0,
                total_all_costs=460000.0,
                breakdown={},
            )

        mock_result = TCOComparisonResult(
            scenario_a=_make_enhanced(1215.0),
            scenario_b=_make_enhanced(1600.0),
            scenario_a_name="Property A",
            scenario_b_name="Property B",
            monthly_cost_difference=-385.0,
            total_cost_difference=-50000.0,
            equity_difference=10000.0,
            break_even_years=7.5,
            a_advantages=["Lower monthly cost"],
            b_advantages=["Better location"],
            recommendation="scenario_a",
            recommendation_reason="Lower total cost",
            priority_score_a=75.0,
            priority_score_b=60.0,
        )

        with patch("api.routers.tools.TCOComparisonTool.calculate", return_value=mock_result):
            payload = {
                "scenario_a": {
                    "property_price": 300000,
                    "down_payment_percent": 20.0,
                    "interest_rate": 4.5,
                    "loan_years": 30,
                },
                "scenario_b": {
                    "property_price": 400000,
                    "down_payment_percent": 15.0,
                    "interest_rate": 5.0,
                    "loan_years": 25,
                },
            }
            response = await client.post(
                "/api/v1/tools/tco-comparison",
                json=payload,
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["recommendation"] == "scenario_a"

    @pytest.mark.asyncio
    async def test_tco_comparison_missing_scenarios(self, client):
        response = await client.post(
            "/api/v1/tools/tco-comparison",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Test: GET /tools/tco-location-defaults
# ===========================================================================


class TestLocationDefaults:
    """Tests for the TCO location defaults endpoint."""

    @pytest.mark.asyncio
    async def test_location_defaults_valid_country(self, client):
        response = await client.get(
            "/api/v1/tools/tco-location-defaults",
            params={"country": "DE", "region": "berlin"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["country"] == "DE"
        assert data["region"] == "berlin"
        assert "property_tax_rate" in data
        assert "avg_insurance_rate" in data
        assert "avg_utilities_per_sqm" in data
        assert "avg_internet" in data
        assert "avg_parking" in data
        assert data["currency"] == "EUR"

    @pytest.mark.asyncio
    async def test_location_defaults_without_region(self, client):
        response = await client.get(
            "/api/v1/tools/tco-location-defaults",
            params={"country": "DE"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["country"] == "DE"
        assert data["region"] == "default"

    @pytest.mark.asyncio
    async def test_location_defaults_missing_country_param(self, client):
        response = await client.get("/api/v1/tools/tco-location-defaults")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_location_defaults_us_country(self, client):
        response = await client.get(
            "/api/v1/tools/tco-location-defaults",
            params={"country": "US", "region": "new_york"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["country"] == "US"


# ===========================================================================
# Test: GET /tools/tco-available-locations
# ===========================================================================


class TestAvailableLocations:
    """Tests for the available locations endpoint."""

    @pytest.mark.asyncio
    async def test_available_locations_returns_200(self, client):
        response = await client.get("/api/v1/tools/tco-available-locations")
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_available_locations_structure(self, client):
        response = await client.get("/api/v1/tools/tco-available-locations")
        data = response.json()
        assert "locations" in data
        locations = data["locations"]
        assert isinstance(locations, dict)
        assert "DE" in locations
        assert isinstance(locations["DE"], list)
        assert "berlin" in locations["DE"]


# ===========================================================================
# Test: POST /tools/investment-analysis
# ===========================================================================


class TestInvestmentAnalysis:
    """Tests for the investment analysis endpoint."""

    @pytest.mark.asyncio
    async def test_investment_valid_input(self, client):
        response = await client.post(
            "/api/v1/tools/investment-analysis",
            json={
                "property_price": 300000,
                "monthly_rent": 2000,
                "down_payment_percent": 20.0,
                "interest_rate": 4.5,
                "loan_years": 30,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "monthly_cash_flow" in data or "roi" in data or "cap_rate" in data

    @pytest.mark.asyncio
    async def test_investment_missing_price(self, client):
        response = await client.post(
            "/api/v1/tools/investment-analysis",
            json={"monthly_rent": 2000},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_investment_zero_price(self, client):
        """Pydantic gt=0 catches zero before the tool's ValueError."""
        response = await client.post(
            "/api/v1/tools/investment-analysis",
            json={"property_price": 0, "monthly_rent": 2000},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_investment_negative_rent(self, client):
        response = await client.post(
            "/api/v1/tools/investment-analysis",
            json={"property_price": 300000, "monthly_rent": -100},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Test: POST /tools/advanced-investment-analysis
# ===========================================================================


class TestAdvancedInvestmentAnalysis:
    """Tests for the advanced investment analysis endpoint."""

    @pytest.mark.asyncio
    async def test_advanced_investment_valid(self, client):
        response = await client.post(
            "/api/v1/tools/advanced-investment-analysis",
            json={
                "property_price": 300000,
                "monthly_rent": 2000,
                "down_payment_percent": 20.0,
                "interest_rate": 4.5,
                "loan_years": 30,
                "projection_years": 10,
                "appreciation_rate": 3.0,
                "rent_growth_rate": 2.0,
                "marginal_tax_rate": 25.0,
                "land_value_ratio": 0.3,
                "market_volatility": 0.15,
            },
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_advanced_investment_missing_fields(self, client):
        response = await client.post(
            "/api/v1/tools/advanced-investment-analysis",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_advanced_investment_zero_price(self, client):
        """Pydantic gt=0 catches zero before the tool's ValueError."""
        response = await client.post(
            "/api/v1/tools/advanced-investment-analysis",
            json={"property_price": 0, "monthly_rent": 2000},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Test: POST /tools/portfolio-analysis
# ===========================================================================


class TestPortfolioAnalysis:
    """Tests for the portfolio analysis endpoint."""

    @pytest.mark.asyncio
    async def test_portfolio_valid_input(self, client):
        response = await client.post(
            "/api/v1/tools/portfolio-analysis",
            json={
                "properties": [
                    {
                        "city": "Berlin",
                        "property_type": "apartment",
                        "property_price": 300000,
                        "monthly_rent": 1500,
                        "monthly_cash_flow": 700,
                        "cap_rate": 4.5,
                    },
                    {
                        "city": "Munich",
                        "property_type": "apartment",
                        "property_price": 400000,
                        "monthly_rent": 2000,
                        "monthly_cash_flow": 900,
                        "cap_rate": 5.0,
                    },
                ],
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metrics" in data
        assert "diversification" in data
        assert "risk_assessment" in data

    @pytest.mark.asyncio
    async def test_portfolio_empty_properties(self, client):
        response = await client.post(
            "/api/v1/tools/portfolio-analysis",
            json={"properties": []},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_portfolio_missing_properties(self, client):
        response = await client.post(
            "/api/v1/tools/portfolio-analysis",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Test: POST /tools/rent-vs-buy
# ===========================================================================


class TestRentVsBuy:
    """Tests for the rent vs buy calculator endpoint."""

    @pytest.mark.asyncio
    async def test_rent_vs_buy_valid(self, client):
        response = await client.post(
            "/api/v1/tools/rent-vs-buy",
            json={
                "property_price": 300000,
                "monthly_rent": 1500,
                "down_payment_percent": 20.0,
                "interest_rate": 4.5,
                "loan_years": 30,
                "projection_years": 15,
            },
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_rent_vs_buy_missing_fields(self, client):
        response = await client.post(
            "/api/v1/tools/rent-vs-buy",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_rent_vs_buy_zero_price(self, client):
        """Pydantic gt=0 catches zero before the tool's ValueError."""
        response = await client.post(
            "/api/v1/tools/rent-vs-buy",
            json={"property_price": 0, "monthly_rent": 1500},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Test: POST /tools/neighborhood-quality
# ===========================================================================


class TestNeighborhoodQuality:
    """Tests for the neighborhood quality index endpoint."""

    @pytest.mark.asyncio
    async def test_neighborhood_quality_valid(self, client):
        from unittest.mock import Mock

        from data.adapters.air_quality_adapter import AirQualityAdapter, AirQualityResult
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter
        from data.adapters.noise_adapter import NoiseAdapter, NoiseResult
        from data.adapters.safety_adapter import SafetyAdapter, SafetyResult
        from data.adapters.transport_adapter import TransportAdapter

        mock_na_inst = Mock(spec=NeighborhoodAdapter)
        mock_na_inst.count_schools.return_value = 5
        mock_na_inst.count_amenities.return_value = 10
        mock_na_inst.calculate_walkability.return_value = 70.0
        mock_na_inst.count_green_spaces.return_value = 3

        mock_sa_inst = Mock(spec=SafetyAdapter)
        mock_sa_inst.get_safety_score.return_value = SafetyResult(
            score=75.0,
            police_stations_nearby=2,
            emergency_services_nearby=1,
            lighting_score=None,
            pois=[],
            data_source="osm_overpass_api",
            confidence=0.7,
        )

        mock_aq_inst = Mock(spec=AirQualityAdapter)
        mock_aq_inst.get_aqi_score.return_value = AirQualityResult(
            score=70.0,
            aqi_value=None,
            pm25=None,
            pm10=None,
            data_source="fallback",
            confidence=0.3,
            station_name=None,
        )

        mock_noise_inst = Mock(spec=NoiseAdapter)
        mock_noise_inst.estimate_noise_level.return_value = NoiseResult(
            score=65.0,
            estimated_db=50.0,
            noise_sources=[],
            data_source="fallback",
            confidence=0.3,
            query_latitude=None,
            query_longitude=None,
        )

        mock_transport_inst = Mock(spec=TransportAdapter)
        mock_transport_inst.calculate_accessibility_score.return_value = 60.0

        with (
            patch(
                "data.adapters.neighborhood_adapter.get_neighborhood_adapter",
                return_value=mock_na_inst,
            ),
            patch("data.adapters.safety_adapter.get_safety_adapter", return_value=mock_sa_inst),
            patch(
                "data.adapters.air_quality_adapter.get_air_quality_adapter",
                return_value=mock_aq_inst,
            ),
            patch("data.adapters.noise_adapter.get_noise_adapter", return_value=mock_noise_inst),
            patch(
                "data.adapters.transport_adapter.get_transport_adapter",
                return_value=mock_transport_inst,
            ),
        ):
            response = await client.post(
                "/api/v1/tools/neighborhood-quality",
                json={
                    "property_id": "prop-123",
                    "latitude": 52.52,
                    "longitude": 13.405,
                    "city": "Berlin",
                    "neighborhood": "Mitte",
                },
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "property_id" in data
        assert "overall_score" in data
        assert "safety_score" in data

    @pytest.mark.asyncio
    async def test_neighborhood_quality_with_custom_weights(self, client):
        from unittest.mock import Mock

        from data.adapters.air_quality_adapter import AirQualityAdapter, AirQualityResult
        from data.adapters.neighborhood_adapter import NeighborhoodAdapter
        from data.adapters.noise_adapter import NoiseAdapter, NoiseResult
        from data.adapters.safety_adapter import SafetyAdapter, SafetyResult
        from data.adapters.transport_adapter import TransportAdapter

        mock_na_inst = Mock(spec=NeighborhoodAdapter)
        mock_na_inst.count_schools.return_value = 5
        mock_na_inst.count_amenities.return_value = 10
        mock_na_inst.calculate_walkability.return_value = 70.0
        mock_na_inst.count_green_spaces.return_value = 3

        mock_sa_inst = Mock(spec=SafetyAdapter)
        mock_sa_inst.get_safety_score.return_value = SafetyResult(
            score=75.0,
            police_stations_nearby=2,
            emergency_services_nearby=1,
            lighting_score=None,
            pois=[],
            data_source="osm_overpass_api",
            confidence=0.7,
        )

        mock_aq_inst = Mock(spec=AirQualityAdapter)
        mock_aq_inst.get_aqi_score.return_value = AirQualityResult(
            score=70.0,
            aqi_value=None,
            pm25=None,
            pm10=None,
            data_source="fallback",
            confidence=0.3,
            station_name=None,
        )

        mock_noise_inst = Mock(spec=NoiseAdapter)
        mock_noise_inst.estimate_noise_level.return_value = NoiseResult(
            score=65.0,
            estimated_db=50.0,
            noise_sources=[],
            data_source="fallback",
            confidence=0.3,
            query_latitude=None,
            query_longitude=None,
        )

        mock_transport_inst = Mock(spec=TransportAdapter)
        mock_transport_inst.calculate_accessibility_score.return_value = 60.0

        with (
            patch(
                "data.adapters.neighborhood_adapter.get_neighborhood_adapter",
                return_value=mock_na_inst,
            ),
            patch("data.adapters.safety_adapter.get_safety_adapter", return_value=mock_sa_inst),
            patch(
                "data.adapters.air_quality_adapter.get_air_quality_adapter",
                return_value=mock_aq_inst,
            ),
            patch("data.adapters.noise_adapter.get_noise_adapter", return_value=mock_noise_inst),
            patch(
                "data.adapters.transport_adapter.get_transport_adapter",
                return_value=mock_transport_inst,
            ),
        ):
            response = await client.post(
                "/api/v1/tools/neighborhood-quality",
                json={
                    "property_id": "prop-123",
                    "latitude": 52.52,
                    "longitude": 13.405,
                    "custom_weights": {
                        "safety": 0.3,
                        "schools": 0.2,
                        "amenities": 0.2,
                        "walkability": 0.15,
                        "green_space": 0.15,
                    },
                    "compare_to_city_average": False,
                    "include_pois": False,
                },
            )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_neighborhood_quality_missing_property_id(self, client):
        response = await client.post(
            "/api/v1/tools/neighborhood-quality",
            json={"latitude": 52.52, "longitude": 13.405},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===========================================================================
# Test: POST /tools/compare-properties
# ===========================================================================


class TestCompareProperties:
    """Tests for the compare properties endpoint."""

    @pytest.mark.asyncio
    async def test_compare_properties_with_ids(self, client_with_properties):
        response = await client_with_properties.post(
            "/api/v1/tools/compare-properties",
            json={"property_ids": ["p1", "p2", "p3"]},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "properties" in data
        assert "summary" in data
        assert data["summary"]["count"] == 3

    @pytest.mark.asyncio
    async def test_compare_properties_with_prices(self, client_with_properties):
        response = await client_with_properties.post(
            "/api/v1/tools/compare-properties",
            json={"property_ids": ["p1", "p2", "p3"]},
        )
        data = response.json()
        summary = data["summary"]
        assert summary["min_price"] == 200000
        assert summary["max_price"] == 450000
        assert summary["price_difference"] == 250000

    @pytest.mark.asyncio
    async def test_compare_properties_empty_ids(self, client):
        response = await client.post(
            "/api/v1/tools/compare-properties",
            json={"property_ids": ["", "  "]},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_compare_properties_no_store(self):
        """Test when vector store is unavailable."""
        app = _build_app(store=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/compare-properties",
                json={"property_ids": ["p1"]},
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_compare_properties_not_found(self, mock_store):
        """Test when store returns no documents."""
        mock_store.get_properties_by_ids = MagicMock(return_value=[])
        app = _build_app(store=mock_store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/compare-properties",
                json={"property_ids": ["nonexistent"]},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_compare_properties_property_fields(self, client_with_properties):
        response = await client_with_properties.post(
            "/api/v1/tools/compare-properties",
            json={"property_ids": ["p1"]},
        )
        assert response.status_code == status.HTTP_200_OK
        props = response.json()["properties"]
        assert len(props) >= 1
        prop = props[0]
        assert prop["id"] == "p1"
        assert prop["price"] == 300000
        assert prop["city"] == "Berlin"


# ===========================================================================
# Test: POST /tools/price-analysis
# ===========================================================================


class TestPriceAnalysis:
    """Tests for the price analysis endpoint."""

    @pytest.mark.asyncio
    async def test_price_analysis_valid(self, client_with_properties):
        response = await client_with_properties.post(
            "/api/v1/tools/price-analysis",
            json={"query": "apartments in Berlin"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["query"] == "apartments in Berlin"
        assert data["count"] == 3
        assert data["average_price"] is not None
        assert data["median_price"] is not None
        assert data["min_price"] is not None
        assert data["max_price"] is not None
        assert "distribution_by_type" in data

    @pytest.mark.asyncio
    async def test_price_analysis_empty_query(self, client_with_properties):
        response = await client_with_properties.post(
            "/api/v1/tools/price-analysis",
            json={"query": "   "},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_price_analysis_no_store(self):
        app = _build_app(store=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/price-analysis",
                json={"query": "test"},
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_price_analysis_no_results(self, mock_store):
        mock_store.search = MagicMock(return_value=[])
        app = _build_app(store=mock_store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/price-analysis",
                json={"query": "nonexistent"},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# Test: POST /tools/location-analysis
# ===========================================================================


class TestLocationAnalysis:
    """Tests for the location analysis endpoint."""

    @pytest.mark.asyncio
    async def test_location_analysis_valid(self, client_with_property):
        response = await client_with_property.post(
            "/api/v1/tools/location-analysis",
            json={"property_id": "p1"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["property_id"] == "p1"
        assert data["city"] == "Berlin"
        assert data["lat"] == 52.52
        assert data["lon"] == 13.405

    @pytest.mark.asyncio
    async def test_location_analysis_empty_id(self, client_with_property):
        response = await client_with_property.post(
            "/api/v1/tools/location-analysis",
            json={"property_id": "   "},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_location_analysis_no_store(self):
        app = _build_app(store=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/location-analysis",
                json={"property_id": "p1"},
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_location_analysis_not_found(self, mock_store):
        mock_store.get_properties_by_ids = MagicMock(return_value=[])
        app = _build_app(store=mock_store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/location-analysis",
                json={"property_id": "nonexistent"},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# Test: POST /tools/valuation
# ===========================================================================


class TestValuation:
    """Tests for the property valuation endpoint."""

    @pytest.mark.asyncio
    async def test_valuation_valid(self, mock_store_with_property):
        provider = MagicMock()
        provider.estimate_value = MagicMock(return_value=320000.0)
        app = _build_app(store=mock_store_with_property, provider=provider)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/valuation",
                json={"property_id": "p1"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["property_id"] == "p1"
        assert data["estimated_value"] == 320000.0

    @pytest.mark.asyncio
    async def test_valuation_no_store(self):
        app = _build_app(store=None, provider=MagicMock())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/valuation",
                json={"property_id": "p1"},
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_valuation_disabled(self, mock_store_with_property):
        app = _build_app(store=mock_store_with_property, provider=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/valuation",
                json={"property_id": "p1"},
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_valuation_empty_id(self, mock_store_with_property):
        provider = MagicMock()
        app = _build_app(store=mock_store_with_property, provider=provider)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/valuation",
                json={"property_id": "   "},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_valuation_property_not_found(self, mock_store):
        mock_store.get_properties_by_ids = MagicMock(return_value=[])
        provider = MagicMock()
        app = _build_app(store=mock_store, provider=provider)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/valuation",
                json={"property_id": "nonexistent"},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# Test: POST /tools/legal-check
# ===========================================================================


class TestLegalCheck:
    """Tests for the legal check endpoint."""

    @pytest.mark.asyncio
    async def test_legal_check_valid(self, client):
        service = MagicMock()
        service.analyze_contract = MagicMock(
            return_value={"risks": [{"type": "high", "text": "Hidden fees"}], "score": 0.75}
        )
        app = _build_app(legal_service=service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/legal-check",
                json={"text": "The tenant agrees to pay all hidden fees."},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "risks" in data
        assert data["score"] == 0.75

    @pytest.mark.asyncio
    async def test_legal_check_disabled(self, client):
        app = _build_app(legal_service=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/legal-check",
                json={"text": "Some text"},
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_legal_check_empty_text(self, client):
        service = MagicMock()
        app = _build_app(legal_service=service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/legal-check",
                json={"text": "   "},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ===========================================================================
# Test: POST /tools/enrich-address
# ===========================================================================


class TestEnrichAddress:
    """Tests for the address enrichment endpoint."""

    @pytest.mark.asyncio
    async def test_enrich_address_valid(self, client):
        service = MagicMock()
        service.enrich = MagicMock(return_value={"postal_code": "10115", "country": "DE"})
        app = _build_app(enrichment=service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/enrich-address",
                json={"address": "Berlin, Germany"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["address"] == "Berlin, Germany"
        assert data["data"]["postal_code"] == "10115"

    @pytest.mark.asyncio
    async def test_enrich_address_disabled(self, client):
        app = _build_app(enrichment=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/enrich-address",
                json={"address": "Berlin"},
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_enrich_address_empty(self, client):
        service = MagicMock()
        app = _build_app(enrichment=service)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/enrich-address",
                json={"address": "   "},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ===========================================================================
# Test: POST /tools/crm-sync-contact
# ===========================================================================


class TestCRMSyncContact:
    """Tests for the CRM contact sync endpoint."""

    @pytest.mark.asyncio
    async def test_crm_sync_valid(self, client):
        connector = MagicMock()
        connector.sync_contact = MagicMock(return_value="crm-contact-123")
        app = _build_app(crm=connector)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/crm-sync-contact",
                json={"name": "John Doe", "phone": "+1234567890", "email": "john@example.com"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "crm-contact-123"

    @pytest.mark.asyncio
    async def test_crm_sync_not_configured(self, client):
        app = _build_app(crm=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/crm-sync-contact",
                json={"name": "John Doe"},
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_crm_sync_failure(self, client):
        connector = MagicMock()
        connector.sync_contact = MagicMock(return_value=None)
        app = _build_app(crm=connector)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/crm-sync-contact",
                json={"name": "John Doe"},
            )
        assert response.status_code == status.HTTP_502_BAD_GATEWAY

    @pytest.mark.asyncio
    async def test_crm_sync_failure_empty_string(self, client):
        connector = MagicMock()
        connector.sync_contact = MagicMock(return_value="")
        app = _build_app(crm=connector)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/crm-sync-contact",
                json={"name": "John Doe"},
            )
        assert response.status_code == status.HTTP_502_BAD_GATEWAY


# ===========================================================================
# Test: POST /tools/commute-time
# ===========================================================================


class TestCommuteTime:
    """Tests for the commute time analysis endpoint."""

    @pytest.mark.asyncio
    async def test_commute_time_valid(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)

        mock_result = MagicMock()
        mock_result.property_id = "p1"
        mock_result.origin_lat = 52.52
        mock_result.origin_lon = 13.405
        mock_result.destination_lat = 52.53
        mock_result.destination_lon = 13.44
        mock_result.destination_name = "Alexanderplatz"
        mock_result.duration_seconds = 1200
        mock_result.duration_text = "20 mins"
        mock_result.distance_meters = 5000
        mock_result.distance_text = "5 km"
        mock_result.mode = "transit"
        mock_result.polyline = "abc123"
        mock_result.arrival_time = None
        mock_result.departure_time = None

        with patch("utils.commute_client.CommuteTimeClient") as MockClient:
            instance = MockClient.return_value
            instance.get_commute_time = AsyncMock(return_value=mock_result)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/commute-time",
                    json={
                        "property_id": "p1",
                        "destination_lat": 52.53,
                        "destination_lon": 13.44,
                        "mode": "transit",
                        "destination_name": "Alexanderplatz",
                    },
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"]["duration_seconds"] == 1200
        assert data["result"]["property_id"] == "p1"

    @pytest.mark.asyncio
    async def test_commute_time_no_store(self):
        app = _build_app(store=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-time",
                json={
                    "property_id": "p1",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                },
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_commute_time_empty_property_id(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-time",
                json={
                    "property_id": "   ",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                },
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_commute_time_property_not_found(self):
        store = _make_store_mock(docs_by_ids=[])
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-time",
                json={
                    "property_id": "nonexistent",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                },
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_commute_time_no_coordinates(self):
        doc = Document(
            page_content="Property",
            metadata={"id": "p_nocoord", "city": "Berlin"},
        )
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-time",
                json={
                    "property_id": "p_nocoord",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                },
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_commute_time_invalid_departure_time(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-time",
                json={
                    "property_id": "p1",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                    "departure_time": "not-a-valid-datetime",
                },
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_commute_time_with_departure_time(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)

        mock_result = MagicMock()
        mock_result.property_id = "p1"
        mock_result.origin_lat = 52.52
        mock_result.origin_lon = 13.405
        mock_result.destination_lat = 52.53
        mock_result.destination_lon = 13.44
        mock_result.destination_name = None
        mock_result.duration_seconds = 900
        mock_result.duration_text = "15 mins"
        mock_result.distance_meters = 3000
        mock_result.distance_text = "3 km"
        mock_result.mode = "driving"
        mock_result.polyline = None
        mock_result.arrival_time = datetime(2024, 1, 15, 9, 0, 0)
        mock_result.departure_time = datetime(2024, 1, 15, 8, 45, 0)

        with patch("utils.commute_client.CommuteTimeClient") as MockClient:
            instance = MockClient.return_value
            instance.get_commute_time = AsyncMock(return_value=mock_result)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/commute-time",
                    json={
                        "property_id": "p1",
                        "destination_lat": 52.53,
                        "destination_lon": 13.44,
                        "mode": "driving",
                        "departure_time": "2024-01-15T08:45:00",
                    },
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["result"]["arrival_time"] is not None
        assert data["result"]["departure_time"] is not None


# ===========================================================================
# Test: POST /tools/commute-ranking
# ===========================================================================


class TestCommuteRanking:
    """Tests for the commute ranking endpoint."""

    @pytest.mark.asyncio
    async def test_commute_ranking_valid(self):
        docs = [
            _make_property_doc(pid="p1", lat=52.52, lon=13.405),
            _make_property_doc(pid="p2", lat=52.50, lon=13.38),
        ]
        store = _make_store_mock(docs_by_ids=docs)
        app = _build_app(store=store)

        mock_rankings = [
            MagicMock(
                property_id="p2",
                origin_lat=52.50,
                origin_lon=13.38,
                destination_lat=52.53,
                destination_lon=13.44,
                destination_name=None,
                duration_seconds=600,
                duration_text="10 mins",
                distance_meters=2000,
                distance_text="2 km",
                mode="driving",
                polyline=None,
                arrival_time=None,
                departure_time=None,
            ),
            MagicMock(
                property_id="p1",
                origin_lat=52.52,
                origin_lon=13.405,
                destination_lat=52.53,
                destination_lon=13.44,
                destination_name=None,
                duration_seconds=900,
                duration_text="15 mins",
                distance_meters=4000,
                distance_text="4 km",
                mode="driving",
                polyline=None,
                arrival_time=None,
                departure_time=None,
            ),
        ]

        with patch("utils.commute_client.CommuteTimeClient") as MockClient:
            instance = MockClient.return_value
            instance.rank_properties_by_commute = AsyncMock(return_value=mock_rankings)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/commute-ranking",
                    json={
                        "property_ids": "p1,p2",
                        "destination_lat": 52.53,
                        "destination_lon": 13.44,
                        "mode": "driving",
                    },
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 2
        assert data["fastest_duration_seconds"] == 600
        assert data["slowest_duration_seconds"] == 900
        assert len(data["rankings"]) == 2

    @pytest.mark.asyncio
    async def test_commute_ranking_no_store(self):
        app = _build_app(store=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-ranking",
                json={
                    "property_ids": "p1,p2",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                },
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_commute_ranking_empty_ids(self):
        store = _make_store_mock()
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-ranking",
                json={
                    "property_ids": " , , ",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                },
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_commute_ranking_no_properties_found(self):
        store = _make_store_mock(docs_by_ids=[])
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-ranking",
                json={
                    "property_ids": "p1",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                },
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_commute_ranking_no_valid_coordinates(self):
        docs = [
            Document(page_content="Prop", metadata={"id": "p_nocoord", "city": "Berlin"}),
        ]
        store = _make_store_mock(docs_by_ids=docs)
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-ranking",
                json={
                    "property_ids": "p_nocoord",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                },
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_commute_ranking_invalid_departure_time(self):
        docs = [_make_property_doc(pid="p1")]
        store = _make_store_mock(docs_by_ids=docs)
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/commute-ranking",
                json={
                    "property_ids": "p1",
                    "destination_lat": 52.53,
                    "destination_lon": 13.44,
                    "departure_time": "invalid",
                },
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_commute_ranking_api_failure(self):
        docs = [_make_property_doc(pid="p1")]
        store = _make_store_mock(docs_by_ids=docs)
        app = _build_app(store=store)

        with patch("utils.commute_client.CommuteTimeClient") as MockClient:
            instance = MockClient.return_value
            instance.rank_properties_by_commute = AsyncMock(return_value=[])
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/commute-ranking",
                    json={
                        "property_ids": "p1",
                        "destination_lat": 52.53,
                        "destination_lon": 13.44,
                    },
                )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ===========================================================================
# Test: POST /tools/generate-listing
# ===========================================================================


class TestGenerateListing:
    """Tests for the listing generation endpoint."""

    @pytest.mark.asyncio
    async def test_generate_listing_valid(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)

        mock_desc_tool = MagicMock()
        mock_desc_tool._run = MagicMock(return_value="A beautiful apartment in Berlin.")

        mock_headline_tool = MagicMock()
        mock_headline_tool._run = MagicMock(
            return_value="Dream Home in Berlin [catchy]\nBest Location [catchy]"
        )

        mock_social_tool = MagicMock()
        mock_social_tool._run = MagicMock(
            return_value="=== Facebook Post ===\nCheck out this amazing property!"
        )

        with (
            patch(
                "api.routers.tools.PropertyDescriptionGeneratorTool", return_value=mock_desc_tool
            ),
            patch("api.routers.tools.HeadlineGeneratorTool", return_value=mock_headline_tool),
            patch(
                "api.routers.tools.SocialMediaContentGeneratorTool", return_value=mock_social_tool
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/generate-listing",
                    json={"property_id": "p1"},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] is not None
        assert "char_counts" in data

    @pytest.mark.asyncio
    async def test_generate_listing_no_store(self):
        app = _build_app(store=None)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/generate-listing",
                json={"property_id": "p1"},
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @pytest.mark.asyncio
    async def test_generate_listing_invalid_tone(self):
        store = _make_store_mock()
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/generate-listing",
                json={"property_id": "p1", "tone": "invalid_tone"},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_generate_listing_invalid_language(self):
        store = _make_store_mock()
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/generate-listing",
                json={"property_id": "p1", "language": "xx"},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_generate_listing_invalid_headline_style(self):
        store = _make_store_mock()
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/generate-listing",
                json={"property_id": "p1", "headline_style": "invalid"},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_generate_listing_invalid_social_platform(self):
        store = _make_store_mock()
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/generate-listing",
                json={"property_id": "p1", "social_platform": "myspace"},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_generate_listing_empty_property_id(self):
        store = _make_store_mock()
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/generate-listing",
                json={"property_id": "   "},
            )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_generate_listing_property_not_found(self):
        store = _make_store_mock(docs_by_ids=[])
        app = _build_app(store=store)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.post(
                "/api/v1/tools/generate-listing",
                json={"property_id": "nonexistent"},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_generate_listing_description_error(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)

        mock_desc_tool = MagicMock()
        mock_desc_tool._run = MagicMock(return_value="Error: LLM unavailable")

        with (
            patch(
                "api.routers.tools.PropertyDescriptionGeneratorTool", return_value=mock_desc_tool
            ),
            patch("api.routers.tools.HeadlineGeneratorTool"),
            patch("api.routers.tools.SocialMediaContentGeneratorTool"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/generate-listing",
                    json={"property_id": "p1"},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] is None
        assert data["error"] is not None

    @pytest.mark.asyncio
    async def test_generate_listing_skip_headlines_and_social(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)

        mock_desc_tool = MagicMock()
        mock_desc_tool._run = MagicMock(return_value="Nice apartment.")

        with (
            patch(
                "api.routers.tools.PropertyDescriptionGeneratorTool", return_value=mock_desc_tool
            ),
            patch("api.routers.tools.HeadlineGeneratorTool"),
            patch("api.routers.tools.SocialMediaContentGeneratorTool"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/generate-listing",
                    json={
                        "property_id": "p1",
                        "generate_headlines": False,
                        "generate_social": False,
                    },
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] is not None
        assert data["headlines"] is None
        assert data["social_content"] is None

    @pytest.mark.asyncio
    async def test_generate_listing_exception_during_generation(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)

        mock_desc_tool = MagicMock()
        mock_desc_tool._run = MagicMock(side_effect=RuntimeError("Boom"))

        with (
            patch(
                "api.routers.tools.PropertyDescriptionGeneratorTool", return_value=mock_desc_tool
            ),
            patch("api.routers.tools.HeadlineGeneratorTool"),
            patch("api.routers.tools.SocialMediaContentGeneratorTool"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/generate-listing",
                    json={"property_id": "p1"},
                )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["error"] is not None
        assert "Boom" in data["error"]


class TestGenerateListingWithoutAProvider:
    """The endpoint must answer on a deployment that holds no provider key.

    The model used to come from a dependency, so the dependency was resolved
    before the handler ran: a request with a wrong tone was answered with
    500 instead of 400, and a deployment without a key could not serve the
    endpoint at all.
    """

    @pytest.mark.asyncio
    async def test_a_wrong_tone_is_answered_with_400(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)

        with (
            patch(
                "api.routers.tools.get_optional_llm",
                AsyncMock(return_value=None),
            ),
            patch("api.routers.tools.resolve_tool_llm", return_value=None),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/generate-listing",
                    json={"property_id": "p1", "tone": "nonsense"},
                )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_the_endpoint_answers_and_says_that_no_model_is_there(self):
        doc = _make_property_doc()
        store = _make_store_mock(docs_by_ids=[doc])
        app = _build_app(store=store)

        with (
            patch(
                "api.routers.tools.get_optional_llm",
                AsyncMock(return_value=None),
            ),
            patch("api.routers.tools.resolve_tool_llm", return_value=None),
            patch("tools.listing_generator_tools.resolve_tool_llm", return_value=None),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                response = await c.post(
                    "/api/v1/tools/generate-listing",
                    json={"property_id": "p1"},
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["error"] is not None
        assert "LLM not available" in data["error"]


# ===========================================================================
# Test: Helper functions _to_float / _to_int
# ===========================================================================


class TestHelperFunctions:
    """Tests for the internal helper functions."""

    def test_to_float_with_none(self):
        from api.routers.tools import _to_float

        assert _to_float(None) is None

    def test_to_float_with_int(self):
        from api.routers.tools import _to_float

        assert _to_float(42) == 42.0

    def test_to_float_with_string(self):
        from api.routers.tools import _to_float

        assert _to_float("3.14") == 3.14

    def test_to_float_with_invalid_string(self):
        from api.routers.tools import _to_float

        assert _to_float("not-a-number") is None

    def test_to_int_with_none(self):
        from api.routers.tools import _to_int

        assert _to_int(None) is None

    def test_to_int_with_float(self):
        from api.routers.tools import _to_int

        assert _to_int(3.7) == 3

    def test_to_int_with_string(self):
        from api.routers.tools import _to_int

        assert _to_int("42") == 42

    def test_to_int_with_invalid_string(self):
        from api.routers.tools import _to_int

        assert _to_int("abc") is None
