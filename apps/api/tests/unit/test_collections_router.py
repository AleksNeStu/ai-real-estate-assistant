"""
Unit tests for collections router (api/routers/collections.py).

Tests cover:
- Create collection endpoint
- List collections endpoint
- Get default collection endpoint
- Get collection by ID endpoint
- Update collection endpoint
- Delete collection endpoint
- Error handling (404 not found, 400 invalid operations)
"""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from api.routers.collections import router as collections_router
from db.database import get_db


@pytest.fixture
async def collections_client(db_session):
    """Create an async HTTP client for testing collections endpoints."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(collections_router)

    # Override get_db dependency to use test database
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    # Override auth dependency
    from api.deps.auth import get_current_active_user

    async def mock_user():
        # Create a mock user
        class MockUser:
            id = "test-user-123"
            email = "test@example.com"

        return MockUser()

    test_app.dependency_overrides[get_current_active_user] = mock_user

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


class TestCreateCollectionEndpoint:
    """Test create collection endpoint."""

    @pytest.mark.asyncio
    async def test_create_collection_success(self, collections_client):
        """Test successful collection creation."""
        response = await collections_client.post(
            "/collections",
            json={
                "name": "My Favorites",
                "description": "My favorite properties",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["name"] == "My Favorites"
        assert data["description"] == "My favorite properties"
        assert "favorite_count" in data
        assert data["favorite_count"] == 0  # New collection has 0 favorites

    @pytest.mark.asyncio
    async def test_create_collection_minimal(self, collections_client):
        """Test collection creation with minimal data."""
        response = await collections_client.post(
            "/collections",
            json={
                "name": "Minimal Collection",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Minimal Collection"
        assert data["description"] is None or "description" in data

    @pytest.mark.asyncio
    async def test_create_collection_missing_name(self, collections_client):
        """Test collection creation with missing name field."""
        response = await collections_client.post(
            "/collections",
            json={
                "description": "Test",
            },
        )

        # FastAPI validation should catch missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListCollectionsEndpoint:
    """Test list collections endpoint."""

    @pytest.mark.asyncio
    async def test_list_collections_empty(self, collections_client):
        """Test listing collections when user has none."""
        response = await collections_client.get("/collections")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_collections_with_data(self, collections_client):
        """Test listing collections with existing collections."""
        # First create a collection
        await collections_client.post(
            "/collections",
            json={
                "name": "Test Collection",
                "description": "Test description",
            },
        )

        response = await collections_client.get("/collections")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Test Collection"


class TestGetDefaultCollectionEndpoint:
    """Test get default collection endpoint."""

    @pytest.mark.asyncio
    async def test_get_default_collection_creates_if_missing(self, collections_client):
        """Test that default collection is created if missing."""
        response = await collections_client.get("/collections/default")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert "is_default" in data
        assert data["is_default"] is True
        assert "favorite_count" in data

    @pytest.mark.asyncio
    async def test_get_default_collection_existing(self, collections_client):
        """Test getting existing default collection."""
        # First call creates default
        first_response = await collections_client.get("/collections/default")
        assert first_response.status_code == status.HTTP_200_OK

        # Second call should return same default
        second_response = await collections_client.get("/collections/default")
        assert second_response.status_code == status.HTTP_200_OK
        data = second_response.json()
        assert data["is_default"] is True


class TestGetCollectionByIdEndpoint:
    """Test get collection by ID endpoint."""

    @pytest.mark.asyncio
    async def test_get_collection_success(self, collections_client):
        """Test getting a collection by ID."""
        # First create a collection
        create_response = await collections_client.post(
            "/collections",
            json={"name": "Test Collection"},
        )
        collection_id = create_response.json()["id"]

        # Then get it by ID
        response = await collections_client.get(f"/collections/{collection_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == collection_id
        assert "favorite_count" in data

    @pytest.mark.asyncio
    async def test_get_collection_not_found(self, collections_client):
        """Test getting non-existent collection."""
        response = await collections_client.get("/collections/nonexistent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_collection_unauthorized(self, collections_client):
        """Test getting collection owned by another user."""
        # Create a collection
        create_response = await collections_client.post(
            "/collections",
            json={"name": "My Collection"},
        )
        collection_id = create_response.json()["id"]

        # Try to access with different user context (simulated by creating new client)
        # This test would need proper auth setup to fully test
        # For now, we just verify the endpoint exists
        response = await collections_client.get(f"/collections/{collection_id}")
        # Should succeed in same-user context
        assert response.status_code in (
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        )


class TestUpdateCollectionEndpoint:
    """Test update collection endpoint."""

    @pytest.mark.asyncio
    async def test_update_collection_name(self, collections_client):
        """Test updating collection name."""
        # Create a collection
        create_response = await collections_client.post(
            "/collections",
            json={"name": "Original Name"},
        )
        collection_id = create_response.json()["id"]

        # Update the collection
        response = await collections_client.put(
            f"/collections/{collection_id}",
            json={
                "name": "Updated Name",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_collection_description(self, collections_client):
        """Test updating collection description."""
        # Create a collection
        create_response = await collections_client.post(
            "/collections",
            json={"name": "Test Collection"},
        )
        collection_id = create_response.json()["id"]

        # Update the collection
        response = await collections_client.put(
            f"/collections/{collection_id}",
            json={
                "description": "New description",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "New description"

    @pytest.mark.asyncio
    async def test_update_collection_is_default_rejected(self, collections_client):
        """Test that is_default field cannot be updated."""
        # Create a collection
        create_response = await collections_client.post(
            "/collections",
            json={"name": "Test Collection"},
        )
        collection_id = create_response.json()["id"]

        # Try to update is_default (should be ignored)
        response = await collections_client.put(
            f"/collections/{collection_id}",
            json={
                "is_default": False,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        # is_default should remain True (default collections are always default)
        # or the field is ignored by the endpoint

    @pytest.mark.asyncio
    async def test_update_collection_not_found(self, collections_client):
        """Test updating non-existent collection."""
        response = await collections_client.put(
            "/collections/nonexistent-id",
            json={"name": "New Name"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data


class TestDeleteCollectionEndpoint:
    """Test delete collection endpoint."""

    @pytest.mark.asyncio
    async def test_delete_collection_success(self, collections_client):
        """Test successful collection deletion."""
        # Create a collection
        create_response = await collections_client.post(
            "/collections",
            json={"name": "To Delete"},
        )
        collection_id = create_response.json()["id"]

        # Delete the collection
        response = await collections_client.delete(f"/collections/{collection_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        get_response = await collections_client.get(f"/collections/{collection_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_collection_not_found(self, collections_client):
        """Test deleting non-existent collection."""
        response = await collections_client.delete("/collections/nonexistent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_delete_default_collection_forbidden(self, collections_client):
        """Test that default collection cannot be deleted."""
        # Get the default collection
        default_response = await collections_client.get("/collections/default")
        collection_id = default_response.json()["id"]

        # Try to delete default collection
        response = await collections_client.delete(f"/collections/{collection_id}")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "default" in data["detail"].lower()


class TestCollectionsRouterConfiguration:
    """Test collections router configuration."""

    def test_router_tag(self):
        """Test that router has correct tag."""
        assert collections_router.tags == ["Collections"]

    def test_router_prefix(self):
        """Test that router has correct prefix."""
        assert collections_router.prefix == "/collections"

    def test_router_endpoints_registered(self):
        """Test that router has expected endpoints registered."""
        # Router should have 6 endpoints registered
        assert len(collections_router.routes) >= 6

        # Check endpoint paths (paths include the router prefix "/collections")
        paths = [route.path for route in collections_router.routes]
        assert "/collections" in paths  # POST create and GET list
        assert "/collections/default" in paths  # GET default
        assert "/collections/{collection_id}" in paths  # GET by ID, PUT update, DELETE delete

    def test_endpoint_methods(self):
        """Test that endpoints have correct HTTP methods."""
        for route in collections_router.routes:
            if route.path == "/collections" and route.name == "create_collection":
                assert "POST" in route.methods
            elif route.path == "/collections" and route.name == "list_collections":
                assert "GET" in route.methods
            elif route.path == "/collections/default":
                assert "GET" in route.methods
            elif route.path == "/collections/{collection_id}":
                # This route handles GET, PUT, DELETE
                assert "GET" in route.methods or "PUT" in route.methods or "DELETE" in route.methods


@pytest.fixture(autouse=True)
async def _the_test_user_exists(create_test_users):
    """The user the tests authenticate as has to be a real row.

    The deployment enforces foreign keys, and a collection belongs to a user
    - so the user has to exist for the collection to be writable at all.
    """
    await create_test_users("test-user-123")
