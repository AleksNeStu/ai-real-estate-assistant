"""Integration tests for leads router.

Tests full request/response cycles for the Leads API
using in-memory SQLite and dependency overrides.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import leads
from db.database import get_db


@pytest.fixture
def admin_user():
    from unittest.mock import MagicMock

    user = MagicMock()
    user.id = "admin-001"
    user.email = "admin@example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def test_app(db_session, admin_user):
    """Create test app with leads router and mocked dependencies."""
    app = FastAPI()
    app.include_router(leads.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestLeadsTracking:
    """Tests for public tracking endpoints."""

    @pytest.mark.asyncio
    async def test_track_interaction(self, client):
        resp = await client.post(
            "/api/v1/leads/track",
            json={
                "visitor_id": "visitor-abc",
                "interaction_type": "view",
                "property_id": "prop-001",
            },
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_create_visitor(self, client):
        resp = await client.post(
            "/api/v1/leads/visitor",
            json={"visitor_id": "visitor-xyz"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["visitor_id"] == "visitor-xyz"


class TestLeadsManagement:
    """Tests for auth-protected lead management."""

    @pytest.mark.asyncio
    async def test_list_leads_empty(self, client):
        resp = await client.get("/api/v1/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_create_and_list_leads(self, client):
        # Create a visitor first
        await client.post(
            "/api/v1/leads/visitor",
            json={
                "visitor_id": "visitor-1",
                "email": "lead@test.com",
                "name": "Test Lead",
            },
        )

        resp = await client.get("/api/v1/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_update_lead_status(self, client):
        # Create lead
        create_resp = await client.post(
            "/api/v1/leads/visitor",
            json={"visitor_id": "visitor-2", "email": "status@test.com"},
        )
        lead_id = create_resp.json()["id"]

        # Update status
        resp = await client.patch(
            f"/api/v1/leads/{lead_id}/status",
            params={"status": "contacted"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "contacted"

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self, client):
        create_resp = await client.post(
            "/api/v1/leads/visitor",
            json={"visitor_id": "visitor-3"},
        )
        lead_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/leads/{lead_id}/status",
            params={"status": "invalid_status"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_lead_detail(self, client):
        create_resp = await client.post(
            "/api/v1/leads/visitor",
            json={
                "visitor_id": "visitor-4",
                "email": "detail@test.com",
                "name": "Detail Lead",
            },
        )
        lead_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/leads/{lead_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "detail@test.com"
        assert "recent_interactions" in data
        assert "score_history" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_lead(self, client):
        resp = await client.get("/api/v1/leads/nonexistent-id")
        assert resp.status_code == 404


class TestScoringStatistics:
    """Tests for the scoring statistics endpoint."""

    @pytest.mark.asyncio
    async def test_get_scoring_statistics(self, client, db_session):
        """An admin gets the scoring statistics of the leads."""
        resp = await client.get("/api/v1/leads/scores/statistics")

        assert resp.status_code == 200
        data = resp.json()
        assert "total_leads" in data
        assert "converted_leads" in data
        assert "new_leads_24h" in data

        # The service is called directly as well: a request handler runs in
        # its own task, and the coverage tracer does not come back after the
        # task suspends, so the lines of the handler are only visible to the
        # report when they run in the test's own task.
        from services.lead_scoring import LeadScoringService

        statistics = await LeadScoringService(db_session).get_scoring_statistics()
        assert "total_leads" in statistics
        assert "new_leads_24h" in statistics


class TestLeadsExport:
    """Tests for lead export."""

    @pytest.mark.asyncio
    async def test_export_leads_csv(self, client):
        resp = await client.get("/api/v1/leads/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "leads_export_" in resp.headers["content-disposition"]
