"""
Tests for the property page's API endpoints.

The property page is public: a visitor who clicks a listing is nobody until
they sign in, so these endpoints read without a session.
"""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_vector_store
from api.routers import properties
from db.database import get_db


@pytest.fixture
def mock_store():
    """A vector store holding two listings of the same city."""
    store = MagicMock()

    def make_document(doc_id: str, title: str, city: str, price: float):
        doc = MagicMock()
        doc.metadata = {
            "id": doc_id,
            "title": title,
            "city": city,
            "country": "Poland",
            "price": price,
            "currency": "PLN",
            "rooms": 2.0,
            "bathrooms": 1.0,
            "area_sqm": 50.0,
            "property_type": "apartment",
            "listing_type": "rent",
            "lat": 50.06,
            "lon": 19.94,
            "has_parking": False,
        }
        doc.page_content = f"{title} in {city}"
        return doc

    subject = make_document("prop-1", "Bright flat", "Kraków", 2800.0)
    other = make_document("prop-2", "Similar flat", "Kraków", 2900.0)

    store.get_properties_by_ids = MagicMock(
        side_effect=lambda ids: [subject] if "prop-1" in ids else []
    )
    store.search_by_metadata = MagicMock(return_value=[subject, other])
    return store


@pytest.fixture(scope="function")
async def properties_client(
    mock_store: MagicMock,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """A client for the property endpoints, with a catalogue that holds one."""
    test_app = FastAPI()
    test_app.include_router(properties.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db
    # The store comes from the dependency, not from app.state: the app never
    # puts a live store there, so a test that mocks app.state would pass
    # against a store the deployment never hands out.
    test_app.dependency_overrides[get_vector_store] = lambda: mock_store

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


class TestGetProperty:
    """The listing itself."""

    @pytest.mark.asyncio
    async def test_returns_the_listing(self, properties_client: AsyncClient):
        """The catalogue's listing arrives with its fields."""
        response = await properties_client.get("/api/v1/properties/prop-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "prop-1"
        assert data["title"] == "Bright flat"
        assert data["city"] == "Kraków"
        assert data["price"] == 2800.0
        assert data["currency"] == "PLN"
        assert data["property_type"] == "apartment"

    @pytest.mark.asyncio
    async def test_translates_the_coordinates(self, properties_client: AsyncClient):
        """The vector store writes lat/lon; the schema names them differently."""
        response = await properties_client.get("/api/v1/properties/prop-1")

        data = response.json()
        assert data["latitude"] == pytest.approx(50.06)
        assert data["longitude"] == pytest.approx(19.94)

    @pytest.mark.asyncio
    async def test_unknown_listing_is_a_refusal(self, properties_client: AsyncClient):
        """A listing the catalogue does not hold is a 404, not an empty page."""
        response = await properties_client.get("/api/v1/properties/does-not-exist")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_id_is_a_refusal(self, properties_client: AsyncClient):
        """An empty id is refused before the catalogue is asked."""
        response = await properties_client.get("/api/v1/properties/%20")

        assert response.status_code in (400, 404)


class TestRelatedProperties:
    """The comparables."""

    @pytest.mark.asyncio
    async def test_returns_the_other_listings(self, properties_client: AsyncClient):
        """The listing itself is never among its own comparables."""
        response = await properties_client.get("/api/v1/properties/prop-1/related")

        assert response.status_code == 200
        data = response.json()
        ids = [item["id"] for item in data["properties"]]
        assert "prop-2" in ids
        assert "prop-1" not in ids

    @pytest.mark.asyncio
    async def test_unknown_listing_is_a_refusal(self, properties_client: AsyncClient):
        """There are no comparables for a listing that is not there."""
        response = await properties_client.get("/api/v1/properties/does-not-exist/related")

        assert response.status_code == 404


class TestWithoutACatalogue:
    """What the page answers when the catalogue is not there."""

    @pytest.mark.asyncio
    async def test_a_missing_store_is_a_refusal(self, db_session: AsyncSession):
        """No catalogue means 503, not a stack trace and not an empty page.

        This is the shape the deployment actually takes when the embedding
        model is unavailable: the page must say so instead of pretending
        the listing does not exist.
        """
        test_app = FastAPI()
        test_app.include_router(properties.router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_vector_store] = lambda: None

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/properties/prop-1")
            related = await client.get("/api/v1/properties/prop-1/related")

        assert response.status_code == 503
        assert related.status_code == 503


class TestPriceHistory:
    """The price history."""

    @pytest.mark.asyncio
    async def test_returns_the_recorded_points(self, properties_client: AsyncClient):
        """The history is what the repository holds for that listing."""
        response = await properties_client.get("/api/v1/properties/prop-1/price-history")

        assert response.status_code == 200
        data = response.json()
        assert data["property_id"] == "prop-1"
        assert "snapshots" in data
        assert "total" in data
