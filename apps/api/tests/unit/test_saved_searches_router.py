"""
Unit tests for saved searches router (api/routers/saved_searches.py).

Tests cover:
- Create saved search endpoint
- List saved searches endpoint
- Get saved search by ID endpoint
- Update saved search endpoint
- Delete saved search endpoint
- Toggle alert endpoint
- Mark search as used endpoint
- Error handling (404 not found, 400 invalid operations)
"""

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from api.routers.saved_searches import router as saved_searches_router
from db.database import get_db


@pytest.fixture
async def saved_searches_client(db_session):
    """Create an async HTTP client for testing saved searches endpoints."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(saved_searches_router)

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


class TestCreateSavedSearchEndpoint:
    """Test create saved search endpoint."""

    @pytest.mark.asyncio
    async def test_create_saved_search_success(self, saved_searches_client):
        """Test successful saved search creation."""
        response = await saved_searches_client.post(
            "/saved-searches",
            json={
                "name": "Berlin Apartments",
                "description": "2-bedroom apartments under 500k",
                "filters": {"city": "Berlin", "max_price": 500000},
                "alert_frequency": "daily",
                "notify_on_new": True,
                "notify_on_price_drop": False,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "id" in data
        assert data["name"] == "Berlin Apartments"
        assert data["description"] == "2-bedroom apartments under 500k"
        assert data["filters"]["city"] == "Berlin"
        assert data["alert_frequency"] == "daily"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_saved_search_minimal(self, saved_searches_client):
        """Test saved search creation with minimal data."""
        response = await saved_searches_client.post(
            "/saved-searches",
            json={
                "name": "Quick Search",
                "filters": {"city": "Warsaw"},
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Quick Search"
        assert data["filters"]["city"] == "Warsaw"
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_saved_search_missing_name(self, saved_searches_client):
        """Test saved search creation with missing name field."""
        response = await saved_searches_client.post(
            "/saved-searches",
            json={
                "filters": {"city": "Berlin"},
            },
        )

        # FastAPI validation should catch missing required field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_saved_search_missing_filters(self, saved_searches_client):
        """Test saved search creation with missing filters field."""
        response = await saved_searches_client.post(
            "/saved-searches",
            json={
                "name": "Test Search",
            },
        )

        # filters has default_factory=dict, so this is valid
        assert response.status_code == status.HTTP_201_CREATED


class TestListSavedSearchesEndpoint:
    """Test list saved searches endpoint."""

    @pytest.mark.asyncio
    async def test_list_saved_searches_empty(self, saved_searches_client):
        """Test listing saved searches when user has none."""
        response = await saved_searches_client.get("/saved-searches")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_saved_searches_with_data(self, saved_searches_client):
        """Test listing saved searches with existing searches."""
        # First create a saved search
        await saved_searches_client.post(
            "/saved-searches",
            json={
                "name": "Test Search",
                "filters": {"city": "Krakow"},
            },
        )

        response = await saved_searches_client.get("/saved-searches")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Test Search"

    @pytest.mark.asyncio
    async def test_list_saved_searches_include_inactive(self, saved_searches_client):
        """Test listing saved searches with inactive flag."""
        # Create two searches, then mark one as inactive
        await saved_searches_client.post(
            "/saved-searches",
            json={
                "name": "Active Search",
                "filters": {"city": "Gdansk"},
            },
        )

        response2 = await saved_searches_client.post(
            "/saved-searches",
            json={
                "name": "Inactive Search",
                "filters": {"city": "Poznan"},
            },
        )
        search_id_2 = response2.json()["id"]

        # Toggle one search to inactive
        await saved_searches_client.post(
            f"/saved-searches/{search_id_2}/toggle-alert?enabled=False"
        )

        # List without inactive (should return 1)
        response = await saved_searches_client.get("/saved-searches?include_inactive=false")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1

        # List with inactive (should return 2)
        response = await saved_searches_client.get("/saved-searches?include_inactive=true")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2


class TestGetSavedSearchByIdEndpoint:
    """Test get saved search by ID endpoint."""

    @pytest.mark.asyncio
    async def test_get_saved_search_success(self, saved_searches_client):
        """Test getting a saved search by ID."""
        # First create a saved search
        create_response = await saved_searches_client.post(
            "/saved-searches",
            json={"name": "Test Search", "filters": {"city": "Wroclaw"}},
        )
        search_id = create_response.json()["id"]

        # Then get it by ID
        response = await saved_searches_client.get(f"/saved-searches/{search_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == search_id
        assert data["name"] == "Test Search"

    @pytest.mark.asyncio
    async def test_get_saved_search_not_found(self, saved_searches_client):
        """Test getting non-existent saved search."""
        response = await saved_searches_client.get("/saved-searches/nonexistent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data


class TestUpdateSavedSearchEndpoint:
    """Test update saved search endpoint."""

    @pytest.mark.asyncio
    async def test_update_saved_search_name(self, saved_searches_client):
        """Test updating saved search name."""
        # Create a saved search
        create_response = await saved_searches_client.post(
            "/saved-searches",
            json={"name": "Original Name", "filters": {"city": "Lodz"}},
        )
        search_id = create_response.json()["id"]

        # Update the saved search
        response = await saved_searches_client.patch(
            f"/saved-searches/{search_id}",
            json={"name": "Updated Name"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_saved_search_filters(self, saved_searches_client):
        """Test updating saved search filters."""
        # Create a saved search
        create_response = await saved_searches_client.post(
            "/saved-searches",
            json={"name": "Test Search", "filters": {"city": "Katowice"}},
        )
        search_id = create_response.json()["id"]

        # Update the saved search
        response = await saved_searches_client.patch(
            f"/saved-searches/{search_id}",
            json={"filters": {"city": "Szczecin", "max_price": 400000}},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filters"]["city"] == "Szczecin"

    @pytest.mark.asyncio
    async def test_update_saved_search_not_found(self, saved_searches_client):
        """Test updating non-existent saved search."""
        response = await saved_searches_client.patch(
            "/saved-searches/nonexistent-id",
            json={"name": "New Name"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data


class TestDeleteSavedSearchEndpoint:
    """Test delete saved search endpoint."""

    @pytest.mark.asyncio
    async def test_delete_saved_search_success(self, saved_searches_client):
        """Test successful saved search deletion."""
        # Create a saved search
        create_response = await saved_searches_client.post(
            "/saved-searches",
            json={"name": "To Delete", "filters": {"city": "Bialystok"}},
        )
        search_id = create_response.json()["id"]

        # Delete the saved search
        response = await saved_searches_client.delete(f"/saved-searches/{search_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        get_response = await saved_searches_client.get(f"/saved-searches/{search_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_saved_search_not_found(self, saved_searches_client):
        """Test deleting non-existent saved search."""
        response = await saved_searches_client.delete("/saved-searches/nonexistent-id")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data


class TestToggleAlertEndpoint:
    """Test toggle alert endpoint."""

    @pytest.mark.asyncio
    async def test_toggle_alert_enable(self, saved_searches_client):
        """Test enabling alerts for a saved search."""
        # Create a saved search
        create_response = await saved_searches_client.post(
            "/saved-searches",
            json={"name": "Test Search", "filters": {"city": "Radom"}},
        )
        search_id = create_response.json()["id"]

        # Disable alerts first
        await saved_searches_client.post(f"/saved-searches/{search_id}/toggle-alert?enabled=False")

        # Enable alerts
        response = await saved_searches_client.post(
            f"/saved-searches/{search_id}/toggle-alert?enabled=True"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_toggle_alert_disable(self, saved_searches_client):
        """Test disabling alerts for a saved search."""
        # Create a saved search
        create_response = await saved_searches_client.post(
            "/saved-searches",
            json={"name": "Test Search", "filters": {"city": "Opole"}},
        )
        search_id = create_response.json()["id"]

        # Disable alerts
        response = await saved_searches_client.post(
            f"/saved-searches/{search_id}/toggle-alert?enabled=False"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_toggle_alert_not_found(self, saved_searches_client):
        """Test toggling alerts for non-existent saved search."""
        response = await saved_searches_client.post(
            "/saved-searches/nonexistent-id/toggle-alert?enabled=True"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data


class TestMarkSearchUsedEndpoint:
    """Test mark search as used endpoint."""

    @pytest.mark.asyncio
    async def test_mark_search_used_success(self, saved_searches_client):
        """Test marking a saved search as used."""
        # Create a saved search
        create_response = await saved_searches_client.post(
            "/saved-searches",
            json={"name": "Test Search", "filters": {"city": "Rzeszow"}},
        )
        search_id = create_response.json()["id"]

        # Mark as used
        response = await saved_searches_client.post(f"/saved-searches/{search_id}/use")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["use_count"] == 1  # Should increment from 0 to 1

    @pytest.mark.asyncio
    async def test_mark_search_used_multiple(self, saved_searches_client):
        """Test marking a saved search as used multiple times."""
        # Create a saved search
        create_response = await saved_searches_client.post(
            "/saved-searches",
            json={"name": "Test Search", "filters": {"city": "Suwalki"}},
        )
        search_id = create_response.json()["id"]

        # Mark as used multiple times
        await saved_searches_client.post(f"/saved-searches/{search_id}/use")
        await saved_searches_client.post(f"/saved-searches/{search_id}/use")
        await saved_searches_client.post(f"/saved-searches/{search_id}/use")

        response = await saved_searches_client.post(f"/saved-searches/{search_id}/use")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["use_count"] == 4

    @pytest.mark.asyncio
    async def test_mark_search_used_not_found(self, saved_searches_client):
        """Test marking non-existent saved search as used."""
        response = await saved_searches_client.post("/saved-searches/nonexistent-id/use")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data


class TestSavedSearchesRouterConfiguration:
    """Test saved searches router configuration."""

    def test_router_tag(self):
        """Test that router has correct tag."""
        assert saved_searches_router.tags == ["Saved Searches"]

    def test_router_prefix(self):
        """Test that router has correct prefix."""
        assert saved_searches_router.prefix == "/saved-searches"

    def test_router_endpoints_registered(self):
        """Test that router has expected endpoints registered."""
        # Router should have 7 endpoints registered
        assert len(saved_searches_router.routes) >= 7

        # Check endpoint paths
        paths = [route.path for route in saved_searches_router.routes]
        assert "/saved-searches" in paths  # POST create, GET list
        assert "/saved-searches/{search_id}" in paths  # GET by ID, PATCH update, DELETE delete
        assert "/saved-searches/{search_id}/toggle-alert" in paths  # POST toggle
        assert "/saved-searches/{search_id}/use" in paths  # POST mark used

    def test_endpoint_methods(self):
        """Test that endpoints have correct HTTP methods."""
        for route in saved_searches_router.routes:
            if route.path == "/saved-searches" and route.name == "create_saved_search":
                assert "POST" in route.methods
            elif route.path == "/saved-searches" and route.name == "list_saved_searches":
                assert "GET" in route.methods
            elif route.path == "/saved-searches/{search_id}" and route.name == "get_saved_search":
                assert "GET" in route.methods
            elif (
                route.path == "/saved-searches/{search_id}" and route.name == "update_saved_search"
            ):
                assert "PATCH" in route.methods
            elif (
                route.path == "/saved-searches/{search_id}" and route.name == "delete_saved_search"
            ):
                assert "DELETE" in route.methods
            elif route.path == "/saved-searches/{search_id}/toggle-alert":
                assert "POST" in route.methods
            elif route.path == "/saved-searches/{search_id}/use":
                assert "POST" in route.methods


@pytest.fixture(autouse=True)
async def _the_test_user_exists(create_test_users):
    """The user the tests authenticate as has to be a real row.

    The deployment enforces foreign keys, and a saved search belongs to a user
    - so the user has to exist for the search to be writable at all.
    """
    await create_test_users("test-user-123")
