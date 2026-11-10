"""API tests for user activity endpoints (Task #82)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient


class TestUserActivityAPI:
    """Tests for user activity API endpoints."""

    @pytest.fixture
    async def test_client(self, db_session):
        """Create a test client with auth override."""
        from fastapi import FastAPI

        from api.deps.auth import get_current_active_user
        from api.routers import user_activity
        from db.database import get_db
        from db.models import User

        # Create test app
        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        # Override DB dependency
        async def override_get_db():
            yield db_session

        # Mock user for auth
        async def override_get_current_user():
            return User(
                id="test-user-123",
                email="test@example.com",
                role="user",
                created_at=datetime.now(UTC),
            )

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Cleanup
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_summary_success(self, test_client):
        """Test GET /user-activity/summary returns summary."""
        response = await test_client.get("/api/v1/user-activity/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "period_start" in data
        assert "period_end" in data
        assert "total_searches" in data
        assert "total_property_views" in data
        assert "total_tool_uses" in data

    @pytest.mark.asyncio
    async def test_get_summary_with_date_range(self, test_client):
        """Test GET /user-activity/summary with date range."""
        params = {
            "period_start": (datetime.now(UTC) - timedelta(days=7)).isoformat(),
            "period_end": datetime.now(UTC).isoformat(),
        }
        response = await test_client.get("/api/v1/user-activity/summary", params=params)

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_get_trends_success(self, test_client):
        """Test GET /user-activity/trends returns trends."""
        response = await test_client.get("/api/v1/user-activity/trends")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "trends" in data
        assert "interval" in data
        assert isinstance(data["trends"], list)

    @pytest.mark.asyncio
    async def test_get_trends_with_interval(self, test_client):
        """Test GET /user-activity/trends with interval parameter."""
        response = await test_client.get(
            "/api/v1/user-activity/trends", params={"interval": "week"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["interval"] == "week"

    @pytest.mark.asyncio
    async def test_export_csv_success(self, test_client):
        """Test GET /user-activity/export returns CSV."""
        response = await test_client.get("/api/v1/user-activity/export")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "content-disposition" in response.headers

        # Verify it's CSV format
        content = response.text
        assert "timestamp" in content
        assert "event_type" in content


class TestUserActivityAdminAPI:
    """Tests for admin-only user activity endpoints."""

    @pytest.fixture
    async def admin_client(self, db_session):
        """Create a test client with admin auth override."""
        from fastapi import FastAPI

        from api.deps.auth import get_current_active_user
        from api.routers import user_activity
        from db.database import get_db
        from db.models import User

        # Create test app
        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        # Override DB dependency
        async def override_get_db():
            yield db_session

        # Mock admin user for auth
        async def override_get_current_user():
            return User(
                id="admin-user-123",
                email="admin@example.com",
                role="admin",
                created_at=datetime.now(UTC),
            )

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Cleanup
        test_app.dependency_overrides.clear()

    @pytest.fixture
    async def regular_user_client(self, db_session):
        """Create a test client with regular user auth override."""
        from fastapi import FastAPI

        from api.deps.auth import get_current_active_user
        from api.routers import user_activity
        from db.database import get_db
        from db.models import User

        # Create test app
        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        # Override DB dependency
        async def override_get_db():
            yield db_session

        # Mock regular user for auth
        async def override_get_current_user():
            return User(
                id="user-123",
                email="user@example.com",
                role="user",  # Not admin
                created_at=datetime.now(UTC),
            )

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Cleanup
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_admin_summary_success(self, admin_client):
        """Test GET /user-activity/admin/summary for admin.

        XFail: Uses SearchEvent with PostgreSQL's date_trunc function.
        """
        response = await admin_client.get("/api/v1/user-activity/admin/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "period_start" in data
        assert "total_searches" in data

    @pytest.mark.asyncio
    async def test_admin_summary_forbidden_for_regular_user(self, regular_user_client):
        """Test GET /user-activity/admin/summary fails for non-admin."""
        response = await regular_user_client.get("/api/v1/user-activity/admin/summary")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_admin_trends_success(self, admin_client):
        """Test GET /user-activity/admin/trends for admin.

        XFail: Uses SearchEvent with PostgreSQL's date_trunc function.
        """
        response = await admin_client.get("/api/v1/user-activity/admin/trends")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "trends" in data

    @pytest.mark.asyncio
    async def test_admin_trends_forbidden_for_regular_user(self, regular_user_client):
        """Test GET /user-activity/admin/trends fails for non-admin."""
        response = await regular_user_client.get("/api/v1/user-activity/admin/trends")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestUserActivityAPIUnauthenticated:
    """Tests for authentication requirements on user activity endpoints."""

    @pytest.fixture
    async def unauth_client(self, db_session):
        """Create a test client without auth override."""
        from fastapi import FastAPI

        from api.routers import user_activity
        from db.database import get_db

        # Create test app WITHOUT auth override
        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        # Override DB dependency only
        async def override_get_db():
            yield db_session

        test_app.dependency_overrides[get_db] = override_get_db

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Cleanup
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_summary_requires_auth(self, unauth_client):
        """Test GET /user-activity/summary requires authentication."""
        response = await unauth_client.get("/api/v1/user-activity/summary")

        # Should return 401 (Unauthorized) or 403 (Forbidden)
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_trends_requires_auth(self, unauth_client):
        """Test GET /user-activity/trends requires authentication."""
        response = await unauth_client.get("/api/v1/user-activity/trends")

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.asyncio
    async def test_export_requires_auth(self, unauth_client):
        """Test GET /user-activity/export requires authentication."""
        response = await unauth_client.get("/api/v1/user-activity/export")

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )


class TestUserActivityAPIInputValidation:
    """Tests for input validation on user activity endpoints."""

    @pytest.fixture
    async def test_client(self, db_session):
        """Create a test client with auth override."""
        from fastapi import FastAPI

        from api.deps.auth import get_current_active_user
        from api.routers import user_activity
        from db.database import get_db
        from db.models import User

        # Create test app
        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        # Override dependencies
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return User(
                id="test-user-123",
                email="test@example.com",
                role="user",
                created_at=datetime.now(UTC),
            )

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Cleanup
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_trends_invalid_interval(self, test_client):
        """Test GET /user-activity/trends with invalid interval."""
        response = await test_client.get(
            "/api/v1/user-activity/trends", params={"interval": "invalid"}
        )

        # Should validate interval parameter
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_trends_valid_intervals(self, test_client):
        """Test GET /user-activity/trends with valid intervals.

        XFail: Uses SearchEvent with PostgreSQL's date_trunc function.
        """
        valid_intervals = ["day", "week", "month"]

        for interval in valid_intervals:
            response = await test_client.get(
                "/api/v1/user-activity/trends", params={"interval": interval}
            )
            assert response.status_code == status.HTTP_200_OK


class TestUserActivityAPIPrivacy:
    """Tests for privacy compliance in user activity API."""

    @pytest.fixture
    async def test_client(self, db_session):
        """Create a test client with auth override."""
        from fastapi import FastAPI

        from api.deps.auth import get_current_active_user
        from api.routers import user_activity
        from db.database import get_db
        from db.models import User

        # Create test app
        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        # Override dependencies
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return User(
                id="test-user-123",
                email="test@example.com",
                role="user",
                created_at=datetime.now(UTC),
            )

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Cleanup
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_csv_truncates_session_ids(self, test_client):
        """Test CSV export truncates session IDs for privacy."""
        response = await test_client.get("/api/v1/user-activity/export")

        assert response.status_code == status.HTTP_200_OK

        # Session IDs should be truncated (showing only first 8 chars + ...)
        content = response.text
        # Check for truncation pattern (if there are events)
        if "session_id" in content:
            assert "..." in content or len(content.split("\n")) <= 2  # Header only or truncated

    @pytest.mark.asyncio
    async def test_summary_no_raw_user_ids(self, test_client):
        """Test summary does not expose raw user IDs.

        XFail: Uses SearchEvent with PostgreSQL's date_trunc function.
        """
        response = await test_client.get("/api/v1/user-activity/summary")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should not contain raw user ID fields
        assert "user_id" not in data
        assert "email" not in data
        # May contain hashed values for internal use, but not raw IDs


class TestUserActivityAPICSVFormat:
    """Tests for CSV export format and content."""

    @pytest.fixture
    async def test_client(self, db_session):
        """Create a test client with auth override."""
        from fastapi import FastAPI

        from api.deps.auth import get_current_active_user
        from api.routers import user_activity
        from db.database import get_db
        from db.models import User

        # Create test app
        test_app = FastAPI()
        test_app.include_router(user_activity.router, prefix="/api/v1")

        # Override dependencies
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return User(
                id="test-user-123",
                email="test@example.com",
                role="user",
                created_at=datetime.now(UTC),
            )

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        # Cleanup
        test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_csv_headers(self, test_client):
        """Test CSV export has correct headers."""
        response = await test_client.get("/api/v1/user-activity/export")

        assert response.status_code == status.HTTP_200_OK

        # Check content type
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

        # Check content disposition header
        disposition = response.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert "filename" in disposition

    @pytest.mark.asyncio
    async def test_export_csv_columns(self, test_client):
        """Test CSV export has expected columns."""
        response = await test_client.get("/api/v1/user-activity/export")

        assert response.status_code == status.HTTP_200_OK

        content = response.text
        lines = content.strip().split("\n")

        # First line should be headers
        if lines:
            headers = lines[0]
            expected_columns = [
                "timestamp",
                "event_type",
                "event_category",
                "session_id",
                "duration_ms",
                "event_data",
            ]
            for col in expected_columns:
                assert col in headers
