"""Integration tests for CMA (Comparative Market Analysis) router.

Tests full request/response cycles for the CMA API
using in-memory SQLite and dependency overrides.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langchain_core.documents import Document

from api.dependencies import get_vector_store
from api.deps.auth import get_current_active_user
from api.routers import cma
from db.database import get_db
from db.schemas import UserResponse


def _listing(
    property_id: str,
    *,
    title: str = "Two-room apartment in Old Town",
    city: str = "Kraków",
    district: str = "Old Town",
    price: float = 600000,
    area_sqm: float = 60,
    rooms: float = 2,
    lat: float = 50.0625,
    lon: float = 19.939,
    offset: float = 0.0,
):
    """A document as the vector store writes it."""
    return Document(
        page_content=f"Property in {city}. {int(rooms)} rooms and 1 bathroom.",
        metadata={
            "id": property_id,
            "title": title,
            "city": city,
            "district": district,
            "neighborhood": district,
            "price": price,
            "currency": "PLN",
            "area_sqm": area_sqm,
            "rooms": rooms,
            "bathrooms": 1,
            "property_type": "apartment",
            "listing_type": "sale",
            "lat": lat + offset,
            "lon": lon + offset,
            "year_built": 2015,
            "floor": 2,
            "total_floors": 5,
        },
    )


@pytest.fixture
def populated_store():
    """A vector store that holds a subject and three comparables."""
    store = MagicMock()
    subject = _listing("prop-001")
    comparables = [
        _listing("prop-002", price=620000, area_sqm=62, offset=0.001),
        _listing("prop-003", price=590000, area_sqm=58, offset=0.002),
        _listing("prop-004", price=640000, area_sqm=64, offset=0.003),
    ]
    documents = [subject, *comparables]

    def get_properties_by_ids(ids):
        wanted = {str(i) for i in ids}
        return [d for d in documents if str(d.metadata.get("id")) in wanted]

    store.get_properties_by_ids = MagicMock(side_effect=get_properties_by_ids)
    store.search_by_metadata = MagicMock(return_value=documents)
    return store


@pytest.fixture
def mock_vector_store():
    """Create a mock ChromaPropertyStore."""
    store = MagicMock()
    store.get_properties_by_ids = MagicMock(return_value=[])
    store.search = MagicMock(return_value=[])
    return store


@pytest.fixture
def test_app(db_session, mock_vector_store):
    """Create test app with CMA router."""
    app = FastAPI()
    app.include_router(cma.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return UserResponse(
            id="test-user-123",
            email="test@example.com",
            roles=["user"],
            created_at="2024-01-01T00:00:00Z",
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    app.dependency_overrides[get_vector_store] = lambda: mock_vector_store
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestCMAAPI:
    """Integration tests for CMA endpoints."""

    @pytest.mark.asyncio
    async def test_list_cma_reports_empty(self, client):
        resp = await client.get("/api/v1/cma")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_cma_report(self, client):
        resp = await client.post(
            "/api/v1/cma/generate",
            json={
                "subject_property_id": "prop-001",
            },
        )
        # With mock vector store (empty), expect 404 (property not found)
        # or 200/201 if vector store returns something
        assert resp.status_code in (200, 201, 404)

    @pytest.mark.asyncio
    async def test_get_nonexistent_report(self, client):
        resp = await client.get("/api/v1/cma/nonexistent-id")
        assert resp.status_code == 404


class TestCMAComparablesEndpoint:
    """The comparables endpoint must answer with comparables.

    It used to answer 422: the response schema asks for the city, the
    property type and the adjusted price, and the route left them out. The
    integration test above never noticed - its vector store was empty, the
    route answered 404 and the test accepted the 404.

    The router builds its store itself (``get_vector_store()`` instead of
    ``Depends(get_vector_store)``), so the store is patched on the module.
    """

    @pytest.fixture
    def client(self, db_session, populated_store, monkeypatch):
        monkeypatch.setattr(cma, "get_vector_store", lambda: populated_store)

        app = FastAPI()
        app.include_router(cma.router, prefix="/api/v1")

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return UserResponse(
                id="test-user-123",
                email="test@example.com",
                roles=["user"],
                created_at="2024-01-01T00:00:00Z",
            )

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_the_endpoint_answers_with_comparables(self, client):
        resp = await client.post("/api/v1/cma/comparables/prop-001")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data, "the endpoint answered with an empty list"

    @pytest.mark.asyncio
    async def test_every_comparable_carries_the_required_fields(self, client):
        resp = await client.post("/api/v1/cma/comparables/prop-001")

        assert resp.status_code == 200, resp.text
        for comparable in resp.json():
            assert comparable["property_id"]
            assert comparable["city"]
            assert comparable["property_type"]
            assert comparable["adjusted_price"] > 0
            assert 0 <= comparable["similarity_score"] <= 100
            assert comparable["score_breakdown"]

    @pytest.mark.asyncio
    async def test_an_unknown_property_is_a_404(self, client):
        resp = await client.post("/api/v1/cma/comparables/prop-does-not-exist")

        assert resp.status_code == 404
