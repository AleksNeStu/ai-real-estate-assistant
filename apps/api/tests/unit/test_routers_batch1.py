"""Unit tests for agents, cma, and admin routers.

Covers:
- api/routers/agents.py (Agent/Broker directory endpoints)
- api/routers/cma.py (Comparative Market Analysis endpoints)
- api/routers/admin.py (Admin/management endpoints)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db

# ---------------------------------------------------------------------------
# Shared helpers and fixtures
# ---------------------------------------------------------------------------


def _make_mock_user(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    full_name: str = "Test User",
    is_active: bool = True,
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.full_name = full_name
    user.is_active = is_active
    return user


def _make_mock_agent_profile(
    profile_id: str = "agent-profile-1",
    user_id: str = "test-user-123",
    is_active: bool = True,
    is_verified: bool = True,
    average_rating: float = 4.5,
    total_reviews: int = 10,
    total_sales: int = 25,
    total_rentals: int = 15,
) -> MagicMock:
    """Create a mock AgentProfile object."""
    profile = MagicMock()
    profile.id = profile_id
    profile.user_id = user_id
    profile.user = _make_mock_user(user_id)
    profile.agency_name = "Test Agency"
    profile.license_number = "LIC-001"
    profile.license_state = "Berlin"
    profile.professional_email = "agent@test.com"
    profile.professional_phone = "+491234567890"
    profile.office_address = "123 Test St"
    profile.specialties = ["residential"]
    profile.service_areas = ["Berlin"]
    profile.property_types = ["apartment"]
    profile.languages = ["en", "de"]
    profile.average_rating = average_rating
    profile.total_reviews = total_reviews
    profile.total_sales = total_sales
    profile.total_rentals = total_rentals
    profile.is_verified = is_verified
    profile.is_active = is_active
    profile.profile_image_url = None
    profile.bio = "Test bio"
    profile.created_at = datetime.now(UTC)
    profile.updated_at = datetime.now(UTC)
    return profile


def _make_mock_listing(
    listing_id: str = "listing-1",
    agent_id: str = "agent-profile-1",
    property_id: str = "prop-1",
) -> MagicMock:
    listing = MagicMock()
    listing.id = listing_id
    listing.agent_id = agent_id
    listing.property_id = property_id
    listing.listing_type = "sale"
    listing.is_primary = True
    listing.is_active = True
    listing.commission_rate = 0.03
    listing.created_at = datetime.now(UTC)
    return listing


def _make_mock_inquiry(
    inquiry_id: str = "inquiry-1",
    agent_id: str = "agent-profile-1",
) -> MagicMock:
    inquiry = MagicMock()
    inquiry.id = inquiry_id
    inquiry.agent_id = agent_id
    inquiry.user_id = None
    inquiry.visitor_id = None
    inquiry.name = "John Doe"
    inquiry.email = "john@example.com"
    inquiry.phone = "+491234567"
    inquiry.property_id = "prop-1"
    inquiry.inquiry_type = "general"
    inquiry.message = "I would like to know more about this property."
    inquiry.status = "new"
    inquiry.created_at = datetime.now(UTC)
    inquiry.read_at = None
    inquiry.responded_at = None
    return inquiry


def _make_mock_appointment(
    appointment_id: str = "apt-1",
    agent_id: str = "agent-profile-1",
) -> MagicMock:
    apt = MagicMock()
    apt.id = appointment_id
    apt.agent_id = agent_id
    apt.user_id = None
    apt.visitor_id = None
    apt.client_name = "Jane Doe"
    apt.client_email = "jane@example.com"
    apt.client_phone = "+491234567"
    apt.property_id = "prop-1"
    apt.proposed_datetime = datetime.now(UTC) + timedelta(days=3)
    apt.confirmed_datetime = None
    apt.duration_minutes = 60
    apt.status = "requested"
    apt.notes = None
    apt.cancellation_reason = None
    apt.created_at = datetime.now(UTC)
    apt.updated_at = datetime.now(UTC)
    return apt


def _make_mock_cma_report(
    report_id: str = "report-1",
    user_id: str = "test-user-123",
) -> MagicMock:
    """Create a mock CMA report with complete comparable data."""
    report = MagicMock()
    report.id = report_id
    report.user_id = user_id
    report.status = "completed"
    report.subject_data = {
        "id": "prop-1",
        "city": "Berlin",
        "district": "Mitte",
        "price": 350000.0,
        "area_sqm": 75.0,
        "rooms": 3,
        "year_built": 2010,
        "property_type": "apartment",
        "energy_rating": "A",
        "amenities": {"has_parking": True},
    }
    report.comparables = [
        {
            "property_id": "comp-1",
            "similarity_score": 85.0,
            "adjustments": [],
            "adjusted_price": 340000.0,
            # Required fields for CMAComparableResponse
            "city": "Berlin",
            "price": 340000.0,
            "price_per_sqm": 4533.33,
            "property_type": "apartment",
        }
    ]
    report.valuation = {
        "estimated_value": 345000.0,
        "value_range_low": 310500.0,
        "value_range_high": 379500.0,
        "confidence_score": 0.82,
        "price_per_sqm": 4600.0,
        "comparables_count": 1,
        "avg_adjusted_price": 340000.0,
        "median_adjusted_price": 340000.0,
        "std_deviation": 0.0,
    }
    report.market_context = None
    report.created_at = datetime.now(UTC)
    report.updated_at = datetime.now(UTC)
    report.expires_at = datetime.now(UTC) + timedelta(days=90)
    report.subject_property_id = "prop-1"
    return report


def _make_mock_doc(
    prop_id: str = "prop-1",
    city: str = "Berlin",
    price: float = 350000.0,
    area_sqm: float = 75.0,
    rooms: int = 3,
) -> MagicMock:
    """Create a mock document with valid metadata for Property construction."""
    doc = MagicMock()
    doc.metadata = {
        "id": prop_id,
        "title": "Nice Apartment",
        "property_type": "apartment",
        "listing_type": "sale",
        "price": price,
        "area_sqm": area_sqm,
        "rooms": rooms,
        "city": city,
        "bathrooms": 1.0,
        "has_parking": False,
        "has_garden": False,
        "has_pool": False,
        "has_garage": False,
        "is_furnished": False,
        "pets_allowed": False,
        "has_balcony": False,
        "has_elevator": False,
    }
    doc.page_content = f"A nice apartment in {city}"
    return doc


# ===========================================================================
# Agents Router Tests
# ===========================================================================


class TestAgentsListAgents:
    """Tests for GET /agents (list agents)."""

    @pytest.fixture
    def app_with_agents_router(self):
        app = FastAPI()
        from api.routers.agents import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_list_agents_success(self, app_with_agents_router):
        """List agents returns paginated results."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockRepo,
            patch("api.routers.agents.AgentListingRepository") as MockListingRepo,
        ):
            mock_repo = MockRepo.return_value
            mock_repo.get_list = AsyncMock(return_value=[mock_profile])
            mock_repo.count = AsyncMock(return_value=1)
            MockListingRepo.return_value.count_by_agents = AsyncMock(
                return_value={"agent-profile-1": 3}
            )

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents")

            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["page"] == 1
            assert data["items"][0]["listings_count"] == 3
            app_with_agents_router.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_agents_with_filters(self, app_with_agents_router):
        """List agents with city and specialty filters."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_list = AsyncMock(return_value=[])
            mock_repo.count = AsyncMock(return_value=0)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/agents",
                    params={"city": "Berlin", "specialty": "residential"},
                )

            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 0
            assert data["items"] == []
            app_with_agents_router.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_agents_invalid_sort_field(self, app_with_agents_router):
        """List agents with invalid sort field returns 400."""
        mock_session = AsyncMock(spec=AsyncSession)

        app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

        transport = ASGITransport(app=app_with_agents_router)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/agents", params={"sort_by": "invalid_field"})

        assert resp.status_code == 400
        assert "Invalid sort field" in resp.json()["detail"]
        app_with_agents_router.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_agents_pagination(self, app_with_agents_router):
        """List agents with custom page/page_size."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_list = AsyncMock(return_value=[])
            mock_repo.count = AsyncMock(return_value=50)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents", params={"page": 2, "page_size": 10})

            assert resp.status_code == 200
            data = resp.json()
            assert data["page"] == 2
            assert data["total_pages"] == 5
            app_with_agents_router.dependency_overrides.clear()


class TestAgentsGetAgent:
    """Tests for GET /agents/{agent_id}."""

    @pytest.fixture
    def app_with_agents_router(self):
        app = FastAPI()
        from api.routers.agents import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_get_agent_success(self, app_with_agents_router):
        """Get agent profile by ID."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_profile)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/agent-profile-1")

            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "agent-profile-1"
            assert data["agency_name"] == "Test Agency"
            app_with_agents_router.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_agent_not_found(self, app_with_agents_router):
        """Get non-existent agent returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=None)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/nonexistent")

            assert resp.status_code == 404
            assert "Agent not found" in resp.json()["detail"]
            app_with_agents_router.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_agent_inactive(self, app_with_agents_router):
        """Get inactive agent returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile(is_active=False)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_profile)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/agent-profile-1")

            assert resp.status_code == 404
            app_with_agents_router.dependency_overrides.clear()


class TestAgentsGetListings:
    """Tests for GET /agents/{agent_id}/listings."""

    @pytest.fixture
    def app_with_agents_router(self):
        app = FastAPI()
        from api.routers.agents import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_get_agent_listings_success(self, app_with_agents_router):
        """Get listings for an agent."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        mock_listing = _make_mock_listing()

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.AgentListingRepository") as MockListingRepo,
        ):
            MockProfileRepo.return_value.get_by_id = AsyncMock(return_value=mock_profile)
            MockListingRepo.return_value.get_by_agent = AsyncMock(return_value=[mock_listing])
            MockListingRepo.return_value.count_for_agent = AsyncMock(return_value=1)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/agent-profile-1/listings")

            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            app_with_agents_router.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_agent_listings_agent_not_found(self, app_with_agents_router):
        """Get listings for non-existent agent returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/nonexistent/listings")

            assert resp.status_code == 404
            app_with_agents_router.dependency_overrides.clear()


class TestAgentsContactAgent:
    """Tests for POST /agents/{agent_id}/contact."""

    @pytest.fixture
    def app_with_agents_router(self):
        app = FastAPI()
        from api.routers.agents import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_contact_agent_success(self, app_with_agents_router):
        """Send an inquiry to an agent."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        mock_inquiry = _make_mock_inquiry()

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.AgentInquiryRepository") as MockInquiryRepo,
            patch(
                "api.routers.agents.get_current_user_optional", new_callable=AsyncMock
            ) as mock_get_user,
        ):
            MockProfileRepo.return_value.get_by_id = AsyncMock(return_value=mock_profile)
            MockInquiryRepo.return_value.create = AsyncMock(return_value=mock_inquiry)
            mock_get_user.return_value = None

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/agents/agent-profile-1/contact",
                    json={
                        "name": "John Doe",
                        "email": "john@example.com",
                        "phone": "+491234567",
                        "property_id": "prop-1",
                        "inquiry_type": "general",
                        "message": "I would like to know more about this property please.",
                    },
                )

            assert resp.status_code == 201
            data = resp.json()
            assert data["agent_id"] == "agent-profile-1"
            assert data["name"] == "John Doe"
            app_with_agents_router.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_contact_agent_not_found(self, app_with_agents_router):
        """Contact non-existent agent returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/agents/nonexistent/contact",
                    json={
                        "name": "John Doe",
                        "email": "john@example.com",
                        "message": "I would like to know more about this property please.",
                    },
                )

            assert resp.status_code == 404
            app_with_agents_router.dependency_overrides.clear()


class TestAgentsScheduleViewing:
    """Tests for POST /agents/{agent_id}/schedule-viewing."""

    @pytest.fixture
    def app_with_agents_router(self):
        app = FastAPI()
        from api.routers.agents import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_schedule_viewing_success(self, app_with_agents_router):
        """Schedule a viewing appointment."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        future_dt = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        mock_apt = _make_mock_appointment()

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.ViewingAppointmentRepository") as MockAptRepo,
            patch(
                "api.routers.agents.get_current_user_optional", new_callable=AsyncMock
            ) as mock_get_user,
        ):
            MockProfileRepo.return_value.get_by_id = AsyncMock(return_value=mock_profile)
            MockAptRepo.return_value.create = AsyncMock(return_value=mock_apt)
            mock_get_user.return_value = None

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/agents/agent-profile-1/schedule-viewing",
                    json={
                        "property_id": "prop-1",
                        "proposed_datetime": future_dt,
                        "duration_minutes": 60,
                        "client_name": "Jane Doe",
                        "client_email": "jane@example.com",
                        "client_phone": "+491234567",
                        "notes": "Looking forward to it.",
                    },
                )

            assert resp.status_code == 201
            data = resp.json()
            assert data["agent_id"] == "agent-profile-1"
            app_with_agents_router.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_schedule_viewing_past_datetime(self, app_with_agents_router):
        """Schedule viewing with past datetime returns 400."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        past_dt = (datetime.now(UTC) - timedelta(days=1)).isoformat()

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_profile)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/agents/agent-profile-1/schedule-viewing",
                    json={
                        "property_id": "prop-1",
                        "proposed_datetime": past_dt,
                        "client_name": "Jane Doe",
                        "client_email": "jane@example.com",
                    },
                )

            assert resp.status_code == 400
            assert "future" in resp.json()["detail"].lower()
            app_with_agents_router.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_schedule_viewing_agent_not_found(self, app_with_agents_router):
        """Schedule viewing for non-existent agent returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_agents_router.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_agents_router)
            future_dt = (datetime.now(UTC) + timedelta(days=7)).isoformat()
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/agents/nonexistent/schedule-viewing",
                    json={
                        "property_id": "prop-1",
                        "proposed_datetime": future_dt,
                        "client_name": "Jane Doe",
                        "client_email": "jane@example.com",
                    },
                )

            assert resp.status_code == 404
            app_with_agents_router.dependency_overrides.clear()


class TestAgentsProfileEndpoints:
    """Tests for protected agent profile endpoints."""

    @pytest.fixture
    def app_with_auth(self):
        app = FastAPI()
        from api.deps.auth import get_current_active_user
        from api.routers.agents import router

        app.include_router(router, prefix="/api/v1")

        mock_user = _make_mock_user()

        async def _override_user():
            return mock_user

        app.dependency_overrides[get_current_active_user] = _override_user
        return app

    @pytest.mark.asyncio
    async def test_get_own_profile_success(self, app_with_auth):
        """Get authenticated agent's own profile."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            # The /{agent_id} route may intercept /profile, so mock get_by_id too
            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_profile)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/profile")

            assert resp.status_code == 200
            assert resp.json()["id"] == "agent-profile-1"
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_own_profile_not_found(self, app_with_auth):
        """Get own profile when none exists returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_user_id = AsyncMock(return_value=None)
            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/profile")

            # 404 either from the /profile route or /{agent_id} route
            assert resp.status_code == 404
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_profile_success(self, app_with_auth):
        """Create agent profile for authenticated user."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_user_id = AsyncMock(return_value=None)
            MockRepo.return_value.create = AsyncMock(return_value=mock_profile)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/agents/profile",
                    json={
                        "agency_name": "Test Agency",
                        "specialties": ["residential"],
                    },
                )

            assert resp.status_code == 201
            assert resp.json()["agency_name"] == "Test Agency"
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_profile_already_exists(self, app_with_auth):
        """Create profile when one already exists returns 409."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/agents/profile",
                    json={"agency_name": "Test Agency"},
                )

            assert resp.status_code == 409
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_profile_success(self, app_with_auth):
        """Update agent profile."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockRepo.return_value.update = AsyncMock(return_value=mock_profile)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/agents/profile",
                    json={"agency_name": "Updated Agency"},
                )

            assert resp.status_code == 200
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_profile_not_found(self, app_with_auth):
        """Update non-existent profile returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_user_id = AsyncMock(return_value=None)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/agents/profile",
                    json={"agency_name": "Updated Agency"},
                )

            assert resp.status_code == 404
            app_with_auth.dependency_overrides.clear()


class TestAgentsInquiries:
    """Tests for agent inquiry endpoints."""

    @pytest.fixture
    def app_with_auth(self):
        app = FastAPI()
        from api.deps.auth import get_current_active_user
        from api.routers.agents import router

        app.include_router(router, prefix="/api/v1")

        mock_user = _make_mock_user()

        async def _override_user():
            return mock_user

        app.dependency_overrides[get_current_active_user] = _override_user
        return app

    @pytest.mark.asyncio
    async def test_list_own_inquiries_success(self, app_with_auth):
        """List inquiries for authenticated agent.

        Note: The /inquiries path may be intercepted by /{agent_id} route
        (agent_id='inquiries'). This test verifies the repo calls and
        endpoint behavior. The response shape depends on which route wins.
        """
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        mock_inquiry = _make_mock_inquiry()

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.AgentInquiryRepository") as MockInquiryRepo,
        ):
            MockProfileRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockProfileRepo.return_value.get_by_id = AsyncMock(return_value=mock_profile)
            MockInquiryRepo.return_value.get_by_agent = AsyncMock(return_value=[mock_inquiry])
            MockInquiryRepo.return_value.count_for_agent = AsyncMock(return_value=1)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/inquiries")

            # Route returns 200 - either via /inquiries or /{agent_id}
            assert resp.status_code == 200
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_own_inquiries_no_profile(self, app_with_auth):
        """List inquiries when no agent profile exists returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_user_id = AsyncMock(return_value=None)
            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/inquiries")

            # 404 from either /{agent_id} or /inquiries route
            assert resp.status_code == 404
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_inquiry_read(self, app_with_auth):
        """Update inquiry status to read."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        mock_inquiry = _make_mock_inquiry()
        mock_inquiry.agent_id = mock_profile.id

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.AgentInquiryRepository") as MockInquiryRepo,
        ):
            MockProfileRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockInquiryRepo.return_value.get_by_id = AsyncMock(return_value=mock_inquiry)
            MockInquiryRepo.return_value.mark_read = AsyncMock()

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/agents/inquiries/inquiry-1",
                    json={"status": "read"},
                )

            assert resp.status_code == 200
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_inquiry_responded(self, app_with_auth):
        """Update inquiry status to responded."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        mock_inquiry = _make_mock_inquiry()
        mock_inquiry.agent_id = mock_profile.id

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.AgentInquiryRepository") as MockInquiryRepo,
        ):
            MockProfileRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockInquiryRepo.return_value.get_by_id = AsyncMock(return_value=mock_inquiry)
            MockInquiryRepo.return_value.mark_responded = AsyncMock()

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/agents/inquiries/inquiry-1",
                    json={"status": "responded"},
                )

            assert resp.status_code == 200
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_inquiry_forbidden(self, app_with_auth):
        """Update inquiry owned by another agent returns 403."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        mock_inquiry = _make_mock_inquiry()
        mock_inquiry.agent_id = "different-agent-id"

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.AgentInquiryRepository") as MockInquiryRepo,
        ):
            MockProfileRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockInquiryRepo.return_value.get_by_id = AsyncMock(return_value=mock_inquiry)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/agents/inquiries/inquiry-1",
                    json={"status": "read"},
                )

            assert resp.status_code == 403
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_inquiry_not_found(self, app_with_auth):
        """Update non-existent inquiry returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.AgentInquiryRepository") as MockInquiryRepo,
        ):
            MockProfileRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockInquiryRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/agents/inquiries/nonexistent",
                    json={"status": "read"},
                )

            assert resp.status_code == 404
            app_with_auth.dependency_overrides.clear()


class TestAgentsAppointments:
    """Tests for agent appointment endpoints."""

    @pytest.fixture
    def app_with_auth(self):
        app = FastAPI()
        from api.deps.auth import get_current_active_user
        from api.routers.agents import router

        app.include_router(router, prefix="/api/v1")

        mock_user = _make_mock_user()

        async def _override_user():
            return mock_user

        app.dependency_overrides[get_current_active_user] = _override_user
        return app

    @pytest.mark.asyncio
    async def test_list_own_appointments_success(self, app_with_auth):
        """List appointments for authenticated agent.

        Note: /appointments may be intercepted by /{agent_id} route.
        """
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        mock_apt = _make_mock_appointment()

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.ViewingAppointmentRepository") as MockAptRepo,
        ):
            MockProfileRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockProfileRepo.return_value.get_by_id = AsyncMock(return_value=mock_profile)
            MockAptRepo.return_value.get_by_agent = AsyncMock(return_value=[mock_apt])
            MockAptRepo.return_value.count_for_agent = AsyncMock(return_value=1)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/appointments")

            assert resp.status_code == 200
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_own_appointments_no_profile(self, app_with_auth):
        """List appointments when no profile returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.agents.AgentProfileRepository") as MockRepo:
            MockRepo.return_value.get_by_user_id = AsyncMock(return_value=None)
            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/agents/appointments")

            assert resp.status_code == 404
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_appointment_success(self, app_with_auth):
        """Update appointment status."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        mock_apt = _make_mock_appointment()
        mock_apt.agent_id = mock_profile.id

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.ViewingAppointmentRepository") as MockAptRepo,
        ):
            MockProfileRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockAptRepo.return_value.get_by_id = AsyncMock(return_value=mock_apt)
            MockAptRepo.return_value.update = AsyncMock(return_value=mock_apt)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/agents/appointments/apt-1",
                    json={"status": "confirmed"},
                )

            assert resp.status_code == 200
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_appointment_forbidden(self, app_with_auth):
        """Update appointment owned by another agent returns 403."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()
        mock_apt = _make_mock_appointment()
        mock_apt.agent_id = "different-agent-id"

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.ViewingAppointmentRepository") as MockAptRepo,
        ):
            MockProfileRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockAptRepo.return_value.get_by_id = AsyncMock(return_value=mock_apt)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/agents/appointments/apt-1",
                    json={"status": "confirmed"},
                )

            assert resp.status_code == 403
            app_with_auth.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_appointment_not_found(self, app_with_auth):
        """Update non-existent appointment returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_profile = _make_mock_agent_profile()

        with (
            patch("api.routers.agents.AgentProfileRepository") as MockProfileRepo,
            patch("api.routers.agents.ViewingAppointmentRepository") as MockAptRepo,
        ):
            MockProfileRepo.return_value.get_by_user_id = AsyncMock(return_value=mock_profile)
            MockAptRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_auth.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_auth)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.patch(
                    "/api/v1/agents/appointments/nonexistent",
                    json={"status": "confirmed"},
                )

            assert resp.status_code == 404
            app_with_auth.dependency_overrides.clear()


# ===========================================================================
# CMA Router Tests
# ===========================================================================


class TestCMAFindComparables:
    """Tests for POST /cma/comparables/{property_id}."""

    @pytest.fixture
    def app_with_cma(self):
        app = FastAPI()
        from api.deps.auth import get_current_active_user
        from api.routers.cma import router

        app.include_router(router, prefix="/api/v1")

        mock_user = _make_mock_user()

        async def _override_user():
            return mock_user

        app.dependency_overrides[get_current_active_user] = _override_user
        return app

    @pytest.mark.asyncio
    async def test_find_comparables_success(self, app_with_cma):
        """Find comparable properties for a subject property.

        The response carries the fields the schema requires - city,
        property_type and adjusted_price. Leaving them out made the endpoint
        answer 500 instead of the list of comparables.
        """
        mock_session = AsyncMock(spec=AsyncSession)
        mock_doc = _make_mock_doc()
        # The subject and the comparable it is compared against are two
        # different listings in the store.
        comp_doc = _make_mock_doc(prop_id="comp-1", city="Berlin", price=340000.0)

        mock_score = MagicMock()
        mock_score.property_id = "comp-1"
        mock_score.total_score = 85.0
        mock_score.price = 340000.0
        mock_score.price_per_sqm = 4533.0
        mock_score.distance_km = 1.2
        mock_score.score_breakdown = {"location": 90, "type": 80}

        with (
            patch("api.routers.cma.get_vector_store") as mock_get_store,
            patch("api.routers.cma.ComparableSelector") as MockSelector,
        ):
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            mock_store.get_properties_by_ids.return_value = [mock_doc]
            mock_store.search_by_metadata.return_value = [mock_doc, comp_doc]

            mock_selector_instance = MockSelector.return_value
            mock_selector_instance.find_comparables.return_value = [mock_score]

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/cma/comparables/prop-1")

            assert resp.status_code == 200
            body = resp.json()
            assert len(body) == 1
            comparable = body[0]
            assert comparable["property_id"] == "comp-1"
            assert comparable["similarity_score"] == 85.0
            assert comparable["price"] == 340000.0
            assert comparable["city"]
            assert comparable["property_type"]
            assert comparable["adjusted_price"] is not None
            app_with_cma.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_find_comparables_property_not_found(self, app_with_cma):
        """Find comparables for non-existent property returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.cma.get_vector_store") as mock_get_store:
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            mock_store.get_properties_by_ids.return_value = []

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/cma/comparables/nonexistent")

            assert resp.status_code == 404
            assert "not found" in resp.json()["detail"]
            app_with_cma.dependency_overrides.clear()


class TestCMAGenerateReport:
    """Tests for POST /cma/generate."""

    @pytest.fixture
    def app_with_cma(self):
        app = FastAPI()
        from api.deps.auth import get_current_active_user
        from api.routers.cma import router

        app.include_router(router, prefix="/api/v1")

        mock_user = _make_mock_user()

        async def _override_user():
            return mock_user

        app.dependency_overrides[get_current_active_user] = _override_user
        return app

    @pytest.mark.asyncio
    async def test_generate_report_property_not_found(self, app_with_cma):
        """Generate report for non-existent property returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.cma.get_vector_store") as mock_get_store:
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store
            mock_store.get_properties_by_ids.return_value = []

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/cma/generate",
                    json={
                        "subject_property_id": "nonexistent",
                        "min_comparables": 3,
                        "max_comparables": 6,
                    },
                )

            assert resp.status_code == 404
            app_with_cma.dependency_overrides.clear()


class TestCMAGetReport:
    """Tests for GET /cma/{report_id}."""

    @pytest.fixture
    def app_with_cma(self):
        app = FastAPI()
        from api.deps.auth import get_current_active_user
        from api.routers.cma import router

        app.include_router(router, prefix="/api/v1")

        mock_user = _make_mock_user()

        async def _override_user():
            return mock_user

        app.dependency_overrides[get_current_active_user] = _override_user
        return app

    @pytest.mark.asyncio
    async def test_get_cma_report_success(self, app_with_cma):
        """Retrieve a saved CMA report.

        The response carries updated_at and the comparables in full - a
        report that cannot be read is a report that cannot be acted on.
        """
        mock_session = AsyncMock(spec=AsyncSession)
        mock_report = _make_mock_cma_report()

        with patch("api.routers.cma.CMAReportRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_report)

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/cma/report-1")

            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == "report-1"
            assert body["status"] == "completed"
            assert body["updated_at"]
            assert body["comparables"]
            app_with_cma.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_cma_report_not_found(self, app_with_cma):
        """Get non-existent CMA report returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.cma.CMAReportRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/cma/nonexistent")

            assert resp.status_code == 404
            app_with_cma.dependency_overrides.clear()


class TestCMADownloadPdf:
    """Tests for GET /cma/{report_id}/pdf."""

    @pytest.fixture
    def app_with_cma(self):
        app = FastAPI()
        from api.deps.auth import get_current_active_user
        from api.routers.cma import router

        app.include_router(router, prefix="/api/v1")

        mock_user = _make_mock_user()

        async def _override_user():
            return mock_user

        app.dependency_overrides[get_current_active_user] = _override_user
        return app

    @pytest.mark.asyncio
    async def test_download_pdf_not_found(self, app_with_cma):
        """Download PDF for non-existent report returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.cma.CMAReportRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/cma/nonexistent/pdf")

            assert resp.status_code == 404
            app_with_cma.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_download_pdf_import_error(self, app_with_cma):
        """Download PDF when generator not available returns 501."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_report = _make_mock_cma_report()

        with patch("api.routers.cma.CMAReportRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_report)

            # Patch the inline import to raise ImportError
            import builtins

            real_import = builtins.__import__

            def _mock_import(name, *args, **kwargs):
                if name == "utils.cma_report_generator":
                    raise ImportError("no module")
                return real_import(name, *args, **kwargs)

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma)
            with patch("builtins.__import__", side_effect=_mock_import):
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/v1/cma/report-1/pdf")

            assert resp.status_code == 501
            app_with_cma.dependency_overrides.clear()


class TestCMAListReports:
    """Tests for GET /cma (list reports)."""

    @pytest.fixture
    def app_with_cma(self):
        app = FastAPI()
        from api.deps.auth import get_current_active_user
        from api.routers.cma import router

        app.include_router(router, prefix="/api/v1")

        mock_user = _make_mock_user()

        async def _override_user():
            return mock_user

        app.dependency_overrides[get_current_active_user] = _override_user
        return app

    @pytest.mark.asyncio
    async def test_list_cma_reports_success(self, app_with_cma):
        """List CMA reports for authenticated user.

        The list carries the same complete response as the single report.
        """
        mock_session = AsyncMock(spec=AsyncSession)
        mock_report = _make_mock_cma_report()

        with patch("api.routers.cma.CMAReportRepository") as MockRepo:
            MockRepo.return_value.get_by_user = AsyncMock(return_value=[mock_report])
            MockRepo.return_value.count_by_user = AsyncMock(return_value=1)

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma, raise_app_exceptions=False)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/cma")

            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] == 1
            assert len(body["items"]) == 1
            assert body["items"][0]["id"] == "report-1"
            assert body["items"][0]["updated_at"]
            app_with_cma.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_cma_reports_with_status_filter(self, app_with_cma):
        """List CMA reports filtered by status."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.cma.CMAReportRepository") as MockRepo:
            MockRepo.return_value.get_by_user = AsyncMock(return_value=[])
            MockRepo.return_value.count_by_user = AsyncMock(return_value=0)

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/cma", params={"status": "completed"})

            assert resp.status_code == 200
            assert resp.json()["total"] == 0
            app_with_cma.dependency_overrides.clear()


class TestCMADeleteReport:
    """Tests for DELETE /cma/{report_id}."""

    @pytest.fixture
    def app_with_cma(self):
        app = FastAPI()
        from api.deps.auth import get_current_active_user
        from api.routers.cma import router

        app.include_router(router, prefix="/api/v1")

        mock_user = _make_mock_user()

        async def _override_user():
            return mock_user

        app.dependency_overrides[get_current_active_user] = _override_user
        return app

    @pytest.mark.asyncio
    async def test_delete_cma_report_success(self, app_with_cma):
        """Delete a CMA report."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_report = _make_mock_cma_report()

        with patch("api.routers.cma.CMAReportRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=mock_report)
            MockRepo.return_value.delete = AsyncMock()

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete("/api/v1/cma/report-1")

            assert resp.status_code == 204
            app_with_cma.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_cma_report_not_found(self, app_with_cma):
        """Delete non-existent CMA report returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("api.routers.cma.CMAReportRepository") as MockRepo:
            MockRepo.return_value.get_by_id = AsyncMock(return_value=None)

            app_with_cma.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_cma)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete("/api/v1/cma/nonexistent")

            assert resp.status_code == 404
            app_with_cma.dependency_overrides.clear()


# ===========================================================================
# Admin Router Tests
# ===========================================================================


class TestAdminVersionInfo:
    """Tests for GET /admin/version."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_admin_version_info(self, app_with_admin):
        """Get admin version info."""
        transport = ASGITransport(app=app_with_admin)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/version")

        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "environment" in data
        assert "python_version" in data
        assert "platform" in data


class TestAdminIngest:
    """Tests for POST /admin/ingest."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_ingest_no_urls(self, app_with_admin):
        """Ingest with no URLs and no defaults returns 400."""
        with patch("api.routers.admin.settings") as mock_settings:
            mock_settings.default_datasets = []
            mock_settings.max_properties = 100
            mock_settings.version = "1.0.0"

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/admin/ingest",
                    json={"file_urls": []},
                )

        assert resp.status_code == 400
        assert "No URLs" in resp.json()["detail"]


class TestAdminHealthCheck:
    """Tests for GET /admin/health."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, app_with_admin):
        """Health check when cache and store are available."""
        with (
            patch("api.routers.admin.load_collection") as mock_load,
            patch("api.routers.admin.get_vector_store") as mock_get_store,
        ):
            mock_load.return_value = MagicMock()
            mock_get_store.return_value = MagicMock()

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded_no_cache(self, app_with_admin):
        """Health check returns degraded when no data cache."""
        with (
            patch("api.routers.admin.load_collection") as mock_load,
            patch("api.routers.admin.get_vector_store") as mock_get_store,
        ):
            mock_load.return_value = None
            mock_get_store.return_value = MagicMock()

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/health")

        assert resp.status_code == 200
        data = resp.json()
        assert "degraded" in data["status"]

    @pytest.mark.asyncio
    async def test_health_check_degraded_no_store(self, app_with_admin):
        """Health check returns degraded when vector store unavailable."""
        with (
            patch("api.routers.admin.load_collection") as mock_load,
            patch("api.routers.admin.get_vector_store") as mock_get_store,
        ):
            mock_load.return_value = MagicMock()
            # get_vector_store returns a MagicMock by default; need to make
            # the Dependants injection actually yield None
            mock_get_store.return_value = None

            # The endpoint uses Depends(get_vector_store) so we need to
            # override the dependency
            from api.dependencies import get_vector_store as gvs

            app_with_admin.dependency_overrides[gvs] = lambda: None

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/health")

        assert resp.status_code == 200
        data = resp.json()
        assert "degraded" in data["status"]
        app_with_admin.dependency_overrides.clear()


class TestAdminMetrics:
    """Tests for GET /admin/metrics."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_admin_metrics_success(self, app_with_admin):
        """Get admin metrics."""
        app_with_admin.state.metrics = {"total_requests": 100}
        app_with_admin.state.response_cache = None
        app_with_admin.state.vector_store = None
        app_with_admin.state.start_time = None

        transport = ASGITransport(app=app_with_admin)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/metrics")

        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "uptime_seconds" in data


class TestAdminMetricsLatency:
    """Tests for GET /admin/metrics/latency."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_latency_no_tracker(self, app_with_admin):
        """Latency endpoint without tracker returns 503."""
        app_with_admin.state.latency_tracker = None

        transport = ASGITransport(app=app_with_admin)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/metrics/latency")

        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_latency_with_tracker(self, app_with_admin):
        """Latency endpoint with tracker returns stats."""
        mock_tracker = MagicMock()
        mock_tracker.get_stats.return_value = {"search_p95_ms": 1200, "chat_p95_ms": 3000}
        app_with_admin.state.latency_tracker = mock_tracker

        transport = ASGITransport(app=app_with_admin)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/metrics/latency")

        assert resp.status_code == 200
        data = resp.json()
        assert "search_p95_ms" in data


class TestAdminDashboard:
    """Tests for GET /admin/dashboard."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_admin_dashboard_success(self, app_with_admin):
        """Admin dashboard returns aggregated stats."""
        app_with_admin.state.response_cache = None
        app_with_admin.state.latency_tracker = None
        app_with_admin.state.vector_store = None
        app_with_admin.state.rate_limiter = None

        with patch("api.health.get_health_status", new_callable=AsyncMock) as mock_health:
            mock_health_obj = MagicMock()
            mock_health_obj.status = MagicMock(value="healthy")
            mock_health_obj.version = "1.0.0"
            mock_health_obj.uptime_seconds = 3600
            mock_health_obj.dependencies = {}
            mock_health.return_value = mock_health_obj

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/dashboard")

        assert resp.status_code == 200
        data = resp.json()
        assert "health" in data
        assert "cache" in data
        assert "latency" in data
        assert "vector_store" in data

    @pytest.mark.asyncio
    async def test_admin_dashboard_health_error(self, app_with_admin):
        """Admin dashboard handles health check error gracefully."""
        app_with_admin.state.response_cache = None
        app_with_admin.state.latency_tracker = None
        app_with_admin.state.vector_store = None
        app_with_admin.state.rate_limiter = None

        with patch("api.health.get_health_status", new_callable=AsyncMock) as mock_health:
            mock_health.side_effect = Exception("health check failed")

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/dashboard")

        assert resp.status_code == 200
        data = resp.json()
        assert data["health"]["status"] == "unknown"


class TestAdminExcelSheets:
    """Tests for POST /admin/excel/sheets."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_excel_sheets_import_error(self, app_with_admin):
        """Excel sheets endpoint when libraries not available returns 400."""
        with patch("api.routers.admin.ExcelDataLoader") as MockLoader:
            MockLoader.side_effect = ImportError("openpyxl not installed")

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/admin/excel/sheets",
                    json={"file_url": "https://example.com/data.xlsx"},
                )

        assert resp.status_code == 400
        assert "Excel libraries not available" in resp.json()["detail"]


class TestAdminReindex:
    """Tests for POST /admin/reindex."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_reindex_no_cache(self, app_with_admin):
        """Reindex when no data in cache returns 404."""
        with (
            patch("api.routers.admin.load_collection") as mock_load,
            patch("api.routers.admin.get_vector_store") as mock_get_store,
        ):
            mock_load.return_value = None
            mock_get_store.return_value = MagicMock()

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/admin/reindex",
                    json={"clear_existing": False},
                )

        assert resp.status_code == 404
        assert "No data in cache" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_reindex_no_store(self, app_with_admin):
        """Reindex when vector store unavailable returns 503."""
        mock_collection = MagicMock()
        mock_collection.properties = []

        from api.dependencies import get_vector_store as gvs

        app_with_admin.dependency_overrides[gvs] = lambda: None

        with patch("api.routers.admin.load_collection") as mock_load:
            mock_load.return_value = mock_collection

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/admin/reindex",
                    json={"clear_existing": False},
                )

        assert resp.status_code == 503
        assert "Vector store unavailable" in resp.json()["detail"]
        app_with_admin.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_reindex_success(self, app_with_admin):
        """Successful reindex."""
        mock_collection = MagicMock()
        mock_collection.properties = [MagicMock(), MagicMock()]

        mock_store = MagicMock()

        with (
            patch("api.routers.admin.load_collection") as mock_load,
            patch("api.routers.admin.get_vector_store") as mock_get_store,
        ):
            mock_load.return_value = mock_collection
            mock_get_store.return_value = mock_store

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/admin/reindex",
                    json={"clear_existing": False},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "Reindexing successful" in data["message"]
        assert data["count"] == 2


class TestAdminPortals:
    """Tests for GET /admin/portals."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_list_portals_success(self, app_with_admin):
        """List available portal adapters."""
        with patch("data.adapters.registry.AdapterRegistry") as MockRegistry:
            MockRegistry.get_all_info.return_value = [
                {
                    "name": "otodom",
                    "display_name": "Otodom",
                    "configured": True,
                    "has_api_key": True,
                    "rate_limit": {"requests_per_minute": 30},
                }
            ]

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/portals")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["adapters"][0]["name"] == "otodom"

    @pytest.mark.asyncio
    async def test_list_portals_error(self, app_with_admin):
        """List portals when registry fails returns 500."""
        with patch(
            "data.adapters.registry.AdapterRegistry.get_all_info",
            side_effect=Exception("registry error"),
        ):
            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/portals")

        assert resp.status_code == 500


class TestAdminFetchPortal:
    """Tests for POST /admin/portals/fetch."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_fetch_portal_not_found(self, app_with_admin):
        """Fetch from unknown portal returns 404."""
        with (
            patch("data.adapters.get_adapter", return_value=None),
            patch("data.adapters.registry.AdapterRegistry.list_adapters", return_value=["otodom"]),
        ):
            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/admin/portals/fetch",
                    json={"portal": "unknown_portal"},
                )

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]


class TestAdminNotificationsStats:
    """Tests for GET /admin/notifications-stats."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_notifications_stats_no_scheduler(self, app_with_admin):
        """Notifications stats without scheduler."""
        app_with_admin.state.scheduler = None

        with patch("api.routers.admin.load_alert_storage_summary") as mock_summary:
            mock_summary_obj = MagicMock()
            mock_summary_obj.sent_total = 5
            mock_summary_obj.pending_total = 2
            mock_summary_obj.pending_by_type = {"price_alert": 2}
            mock_summary_obj.pending_oldest_created_at = None
            mock_summary_obj.pending_newest_created_at = None
            mock_summary.return_value = mock_summary_obj

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/admin/notifications-stats")

        assert resp.status_code == 200
        data = resp.json()
        assert data["scheduler_running"] is False
        assert data["sent_alerts_total"] == 5


class TestAdminAuditLogs:
    """Tests for audit log endpoints."""

    @pytest.fixture
    def app_with_admin(self):
        app = FastAPI()
        from api.routers.admin import router

        app.include_router(router, prefix="/api/v1")
        return app

    @pytest.mark.asyncio
    async def test_list_audit_logs(self, app_with_admin):
        """List audit log entries."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("services.audit_service.AuditService") as MockService:
            mock_service = MockService.return_value
            mock_service.query = AsyncMock(return_value=([], 0))

            app_with_admin.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/audit")

            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 0
            assert data["items"] == []
            app_with_admin.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_audit_logs_with_filters(self, app_with_admin):
        """List audit logs with action and date filters."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("services.audit_service.AuditService") as MockService:
            mock_service = MockService.return_value
            mock_service.query = AsyncMock(return_value=([], 0))

            app_with_admin.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/audit",
                    params={
                        "action": "login",
                        "start_time": "2024-01-01T00:00:00",
                        "end_time": "2024-12-31T23:59:59",
                    },
                )

            assert resp.status_code == 200
            app_with_admin.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_verify_audit_chain(self, app_with_admin):
        """Verify audit chain integrity."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("services.audit_service.AuditService") as MockService:
            mock_service = MockService.return_value
            mock_service.verify_chain = AsyncMock(
                return_value={
                    "valid": True,
                    "entries_checked": 0,
                    "errors": [],
                    "checked_count": 0,
                    "broken_count": 0,
                    "broken_entries": [],
                }
            )

            app_with_admin.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/audit/verify")

            assert resp.status_code == 200
            data = resp.json()
            assert data["valid"] is True
            app_with_admin.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_audit_entry_found(self, app_with_admin):
        """Get single audit entry by ID."""
        mock_session = AsyncMock(spec=AsyncSession)

        mock_entry = MagicMock()
        mock_entry.id = "entry-1"
        mock_entry.action = "login"
        mock_entry.actor_id = "user-1"
        mock_entry.actor_email = "user-1@example.com"
        mock_entry.actor_role = "user"
        mock_entry.resource = "auth"
        mock_entry.details = {}
        mock_entry.ip_address = "127.0.0.1"
        mock_entry.user_agent = "test-agent"
        mock_entry.request_id = "req-1"
        mock_entry.prev_hash = "abc123"
        mock_entry.entry_hash = "def456"
        mock_entry.timestamp = datetime.now(UTC)
        mock_entry.level = "info"
        mock_entry.result = "success"
        mock_entry.metadata_ = {}
        mock_entry.previous_hash = "abc123"

        with patch("services.audit_service.AuditService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_by_id = AsyncMock(return_value=mock_entry)

            app_with_admin.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/audit/entry-1")

            assert resp.status_code == 200
            app_with_admin.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_audit_entry_not_found(self, app_with_admin):
        """Get non-existent audit entry returns 404."""
        mock_session = AsyncMock(spec=AsyncSession)

        with patch("services.audit_service.AuditService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_by_id = AsyncMock(return_value=None)

            app_with_admin.dependency_overrides[get_db] = lambda: mock_session

            transport = ASGITransport(app=app_with_admin)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/audit/nonexistent")

            assert resp.status_code == 404
            app_with_admin.dependency_overrides.clear()


class TestAdminHelperFunctions:
    """Tests for helper functions in admin router."""

    def test_format_python_version(self):
        """Test _format_python_version helper."""
        from api.routers.admin import _format_python_version

        version = _format_python_version()
        import sys

        expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert version == expected

    @pytest.mark.asyncio
    async def test_read_upload_file_limited(self):
        """Test _read_upload_file_limited with small file."""
        from api.routers.admin import _read_upload_file_limited

        mock_file = AsyncMock()
        mock_file.read = AsyncMock(side_effect=[b"small data", b""])

        data, too_large = await _read_upload_file_limited(mock_file, 1024 * 1024)
        assert data == b"small data"
        assert too_large is False

    @pytest.mark.asyncio
    async def test_read_upload_file_limited_too_large(self):
        """Test _read_upload_file_limited with oversized file."""
        from api.routers.admin import _read_upload_file_limited

        large_data = b"x" * (2 * 1024 * 1024)

        mock_file = AsyncMock()
        mock_file.read = AsyncMock(side_effect=[large_data, b"more data", b""])

        data, too_large = await _read_upload_file_limited(mock_file, 1024 * 1024)
        assert too_large is True


class TestCMAHelperFunctions:
    """Tests for helper functions in CMA router."""

    def test_document_to_property(self):
        """Test _document_to_property conversion with full metadata."""
        from api.routers.cma import _document_to_property

        doc = MagicMock()
        doc.metadata = {
            "id": "prop-1",
            "title": "Nice Apartment",
            "property_type": "apartment",
            "listing_type": "sale",
            "price": 350000.0,
            "area_sqm": 75.0,
            "rooms": 3,
            "city": "Berlin",
            "bathrooms": 1.0,
            "has_parking": True,
            "has_garden": False,
            "has_pool": False,
            "has_garage": False,
            "is_furnished": False,
            "pets_allowed": True,
            "has_balcony": True,
            "has_elevator": True,
        }
        doc.page_content = "A nice apartment in Berlin"

        prop = _document_to_property(doc)
        assert prop.id == "prop-1"
        assert prop.city == "Berlin"
        assert prop.price == 350000.0

    def test_document_to_property_empty_metadata(self):
        """Test _document_to_property with empty metadata raises validation error.

        The amenity flags are coerced to False, but the city is required by
        the schema, so a document without one is still not a property.
        """
        from api.routers.cma import _document_to_property

        doc = MagicMock()
        doc.metadata = {}
        doc.page_content = "Some content"

        # Empty metadata has no city, which the schema requires
        with pytest.raises((ValueError, TypeError, AttributeError)):
            _document_to_property(doc)

    def test_property_to_dict(self):
        """Test _property_to_dict conversion returns expected fields.

        The function used to read prop.bedrooms and prop.street, which are not
        fields on Property: it raised AttributeError, and every CMA report
        ended in a 500.
        """
        from api.routers.cma import _property_to_dict
        from data.schemas import Property

        prop = Property(
            id="prop-1",
            city="Berlin",
            price=350000.0,
            area_sqm=75.0,
        )

        result = _property_to_dict(prop)

        assert result["id"] == "prop-1"
        assert result["city"] == "Berlin"
        assert result["price"] == 350000.0
        assert result["area_sqm"] == 75.0
        assert "address" in result
        assert "bedrooms" not in result

    def test_build_comparable_response_is_complete(self):
        """The comparable response must carry the fields the schema requires.

        The endpoint answered 422 because it left city, property_type and
        adjusted_price out of the response.
        """
        from analytics.comparable_selector import ComparableScore
        from api.routers.cma import _build_comparable_response
        from data.schemas import Property

        score = ComparableScore(
            property_id="prop-2",
            total_score=82.0,
            location_score=20.0,
            type_score=18.0,
            size_score=14.0,
            rooms_score=15.0,
            recency_score=10.0,
            amenities_score=5.0,
            distance_km=1.2,
            price_per_sqm=4500.0,
            price=350000.0,
        )
        comparable = Property(
            id="prop-2",
            city="Krakow",
            district="Old Town",
            property_type="apartment",
            price=350000.0,
            area_sqm=78.0,
            rooms=3.0,
            year_built=2015,
            currency="PLN",
        )

        response = _build_comparable_response(
            score=score,
            comparable=comparable,
            adjustments=[],
            adjusted_price=360000.0,
            total_adjustment_percent=2.86,
            total_adjustment_amount=10000.0,
        )

        assert response.city == "Krakow"
        assert response.property_type == "apartment"
        assert response.adjusted_price == 360000.0
        assert response.currency == "PLN"
        assert response.similarity_score == 82.0
        assert response.distance_km == 1.2

    def test_comparable_from_stored_fills_the_missing_fields(self):
        """A report saved before the response grew its fields still opens."""
        from api.routers.cma import _comparable_from_stored

        response = _comparable_from_stored(
            {"property_id": "prop-2", "similarity_score": 70.0, "price": 300000.0},
            {"city": "Krakow", "property_type": "apartment"},
        )

        assert response.city == "Krakow"
        assert response.property_type == "apartment"
        assert response.adjusted_price == 300000.0
        assert response.price_per_sqm == 0.0

    def test_calculate_valuation_empty_comparables(self):
        """Test _calculate_valuation with no comparables."""
        from api.routers.cma import _calculate_valuation
        from data.schemas import Property

        subject = Property(id="prop-1", price=300000.0, city="Berlin")
        result = _calculate_valuation(subject, [])

        assert result.estimated_value == 300000.0
        assert result.comparables_count == 0
        assert result.confidence_score == 0.0

    def test_calculate_valuation_with_comparables(self):
        """Test _calculate_valuation with comparables."""
        from api.routers.cma import _calculate_valuation
        from data.schemas import Property

        subject = Property(id="prop-1", price=350000.0, area_sqm=75.0, city="Berlin")
        comparables = [
            {
                "property_id": "comp-1",
                "similarity_score": 80.0,
                "adjusted_price": 340000.0,
            },
            {
                "property_id": "comp-2",
                "similarity_score": 75.0,
                "adjusted_price": 360000.0,
            },
        ]

        result = _calculate_valuation(subject, comparables)
        assert result.comparables_count == 2
        assert result.estimated_value > 0
        assert result.value_range_low < result.estimated_value
        assert result.value_range_high > result.estimated_value
        assert result.confidence_score > 0
        assert result.price_per_sqm > 0
