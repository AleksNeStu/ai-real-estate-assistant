"""Integration tests for user activity router.

Tests full request/response cycles for the User Activity API
using in-memory SQLite and dependency overrides.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import user_activity
from db.database import get_db
from db.schemas import UserResponse


@pytest.fixture
def test_app(db_session):
    """Create test app with user_activity router."""
    app = FastAPI()
    app.include_router(user_activity.router, prefix="/api/v1")

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
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestUserActivityAPI:
    """Integration tests for user activity endpoints."""

    @pytest.mark.asyncio
    async def test_get_activity_summary(self, client):
        resp = await client.get("/api/v1/user-activity/summary")
        assert resp.status_code == 200
        data = resp.json()
        # The summary is an aggregate over the period, not over one user:
        # it carries the period it covers and the totals of that period.
        assert "period_start" in data
        assert "period_end" in data
        assert data["total_searches"] >= 0

    @pytest.mark.asyncio
    async def test_get_activity_summary_with_dates(self, client):
        resp = await client.get(
            "/api/v1/user-activity/summary",
            params={
                "period_start": "2025-01-01T00:00:00Z",
                "period_end": "2025-01-31T23:59:59Z",
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_activity_trends(self, client):
        resp = await client.get("/api/v1/user-activity/trends")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_export_activity_csv(self, client):
        resp = await client.get("/api/v1/user-activity/export")
        assert resp.status_code in (200, 204)
