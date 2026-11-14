"""Integration tests for favorites router.

Tests full request/response cycles for the Favorites API
using in-memory SQLite and dependency overrides.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import favorites
from db.database import get_db
from db.models import User
from db.schemas import UserResponse


@pytest.fixture
async def test_app(db_session):
    """Create test app with favorites router and mocked dependencies."""
    app = FastAPI()
    app.include_router(favorites.router, prefix="/api/v1")

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

    # The deployment enforces foreign keys, and a row that belongs to a user
    # needs that user to exist. The tests authenticate as one, so it is
    # created here rather than left pointing at nothing.
    db_session.add(User(id="test-user-123", email="test@example.com", is_active=True))
    await db_session.flush()

    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestFavoritesAPI:
    """Integration tests for favorites CRUD."""

    @pytest.mark.asyncio
    async def test_add_favorite(self, client):
        resp = await client.post(
            "/api/v1/favorites",
            json={"property_id": "prop-001"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["property_id"] == "prop-001"

    @pytest.mark.asyncio
    async def test_add_duplicate_favorite_returns_409(self, client):
        await client.post("/api/v1/favorites", json={"property_id": "prop-001"})
        resp = await client.post("/api/v1/favorites", json={"property_id": "prop-001"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_list_favorites(self, client):
        await client.post("/api/v1/favorites", json={"property_id": "prop-001"})
        await client.post("/api/v1/favorites", json={"property_id": "prop-002"})

        resp = await client.get("/api/v1/favorites")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_check_favorite_true(self, client):
        await client.post("/api/v1/favorites", json={"property_id": "prop-001"})

        resp = await client.get("/api/v1/favorites/check/prop-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_favorited"] is True

    @pytest.mark.asyncio
    async def test_check_favorite_false(self, client):
        resp = await client.get("/api/v1/favorites/check/prop-999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_favorited"] is False

    @pytest.mark.asyncio
    async def test_get_favorite_ids(self, client):
        await client.post("/api/v1/favorites", json={"property_id": "prop-001"})
        await client.post("/api/v1/favorites", json={"property_id": "prop-002"})

        resp = await client.get("/api/v1/favorites/ids")
        assert resp.status_code == 200
        ids = resp.json()
        assert "prop-001" in ids
        assert "prop-002" in ids

    @pytest.mark.asyncio
    async def test_delete_favorite(self, client):
        create_resp = await client.post(
            "/api/v1/favorites",
            json={"property_id": "prop-001"},
        )
        fav_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/favorites/{fav_id}")
        assert resp.status_code == 204

        # Verify deleted
        check_resp = await client.get("/api/v1/favorites/check/prop-001")
        assert check_resp.json()["is_favorited"] is False

    @pytest.mark.asyncio
    async def test_delete_by_property_id(self, client):
        await client.post("/api/v1/favorites", json={"property_id": "prop-001"})

        resp = await client.delete("/api/v1/favorites/by-property/prop-001")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_favorite(self, client):
        resp = await client.delete("/api/v1/favorites/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_favorite_with_notes(self, client):
        resp = await client.post(
            "/api/v1/favorites",
            json={"property_id": "prop-003", "notes": "Great location!"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["notes"] == "Great location!"
