"""Integration tests for collections router.

Tests full request/response cycles for the Collections API
using in-memory SQLite and dependency overrides.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import collections
from db.database import get_db
from db.models import User
from db.schemas import UserResponse


@pytest.fixture
async def test_app(db_session):
    """Create test app with collections router and mocked dependencies."""
    app = FastAPI()
    app.include_router(collections.router, prefix="/api/v1")

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


class TestCollectionsAPI:
    """Integration tests for collections CRUD."""

    @pytest.mark.asyncio
    async def test_create_collection(self, client):
        resp = await client.post(
            "/api/v1/collections",
            json={"name": "My Apartments", "description": "Saved apartments"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Apartments"
        assert data["description"] == "Saved apartments"
        assert data["favorite_count"] == 0

    @pytest.mark.asyncio
    async def test_list_collections_empty(self, client):
        resp = await client.get("/api/v1/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_and_list_collections(self, client):
        # Create two collections
        await client.post(
            "/api/v1/collections",
            json={"name": "Collection A"},
        )
        await client.post(
            "/api/v1/collections",
            json={"name": "Collection B"},
        )

        resp = await client.get("/api/v1/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    @pytest.mark.asyncio
    async def test_get_default_collection(self, client):
        resp = await client.get("/api/v1/collections/default")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Favorites"

    @pytest.mark.asyncio
    async def test_get_collection_by_id(self, client):
        create_resp = await client.post(
            "/api/v1/collections",
            json={"name": "Test Collection"},
        )
        collection_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/collections/{collection_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Collection"

    @pytest.mark.asyncio
    async def test_get_nonexistent_collection(self, client):
        resp = await client.get("/api/v1/collections/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_collection(self, client):
        create_resp = await client.post(
            "/api/v1/collections",
            json={"name": "Original Name"},
        )
        collection_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/collections/{collection_id}",
            json={"name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_collection(self, client):
        create_resp = await client.post(
            "/api/v1/collections",
            json={"name": "To Delete"},
        )
        collection_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/collections/{collection_id}")
        assert resp.status_code == 204

        # Verify deleted
        get_resp = await client.get(f"/api/v1/collections/{collection_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_delete_default_collection(self, client):
        # Get default collection
        default_resp = await client.get("/api/v1/collections/default")
        collection_id = default_resp.json()["id"]

        # Try to delete
        resp = await client.delete(f"/api/v1/collections/{collection_id}")
        assert resp.status_code == 400
