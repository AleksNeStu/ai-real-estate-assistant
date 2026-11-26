"""The admin API belongs to the operator - an anonymous visitor must not reach it.

The frontend proxy injects the API key for every path it forwards, so a
route that is gated by the API key alone is public on the deployed demo.
These tests pin the gate that replaced it: an administrator is an
identity, not a key.
"""

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import require_admin_access
from api.routers import admin
from config.settings import settings
from core.jwt import create_access_token
from db.database import get_db
from db.models import User

API_KEY = "test-admin-key"  # pragma: allowlist secret - a test fixture, not a credential


async def _make_user(
    session: AsyncSession,
    *,
    user_id: str,
    email: str,
    role: str = "user",
) -> User:
    user = User(
        id=user_id,
        email=email,
        full_name=email.split("@")[0],
        is_active=True,
        is_verified=True,
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
def clean_settings(monkeypatch):
    """A deployment with one API key, no demo bypass and no admin list."""
    monkeypatch.setattr(settings, "demo_api_key_bypass", False)
    monkeypatch.setattr(settings, "admin_emails", [])
    monkeypatch.setattr(settings, "api_access_key", API_KEY)
    monkeypatch.setattr(settings, "api_access_keys", [])
    monkeypatch.setattr(settings, "environment", "local")
    return settings


@pytest.fixture
def admin_app(db_session):
    """The admin router behind the gate, exactly as main.py mounts it."""
    app = FastAPI()
    app.include_router(admin.router, prefix="/api/v1", dependencies=[Depends(require_admin_access)])

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
async def client(admin_app):
    transport = ASGITransport(app=admin_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _bearer(user_id: str) -> dict[str, str]:
    token = create_access_token(subject=user_id, roles=["user"])
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.usefixtures("clean_settings")
class TestAdminAccessGate:
    """Who may reach /api/v1/admin/*."""

    @pytest.mark.asyncio
    async def test_anonymous_visitor_is_refused_when_an_admin_exists(self, client, db_session):
        await _make_user(db_session, user_id="admin-1", email="admin@example.com", role="admin")

        response = await client.get("/api/v1/admin/version")

        assert response.status_code == 403
        assert "Administrator" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_anonymous_visitor_is_refused_with_the_api_key_alone(self, client, db_session):
        """The key is injected by the proxy for every path - it is not a gate."""
        await _make_user(db_session, user_id="admin-1", email="admin@example.com", role="admin")

        response = await client.get("/api/v1/admin/version", headers={"X-API-Key": API_KEY})

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_the_api_key_still_opens_a_deployment_without_an_administrator(
        self, client, db_session
    ):
        """A self-hoster who has not created an admin account keeps the old way in."""
        await _make_user(db_session, user_id="user-1", email="user@example.com")

        response = await client.get("/api/v1/admin/version", headers={"X-API-Key": API_KEY})

        assert response.status_code == 200
        assert response.json()["version"]

    @pytest.mark.asyncio
    async def test_a_request_without_the_key_is_refused_on_a_fresh_deployment(
        self, client, db_session
    ):
        await _make_user(db_session, user_id="user-1", email="user@example.com")

        response = await client.get("/api/v1/admin/version")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_the_admin_role_opens_the_panel(self, client, db_session):
        await _make_user(db_session, user_id="admin-1", email="admin@example.com", role="admin")

        response = await client.get("/api/v1/admin/version", headers=_bearer("admin-1"))

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_a_signed_in_visitor_is_refused(self, client, db_session):
        await _make_user(db_session, user_id="admin-1", email="admin@example.com", role="admin")
        await _make_user(db_session, user_id="user-1", email="visitor@example.com")

        response = await client.get("/api/v1/admin/version", headers=_bearer("user-1"))

        assert response.status_code == 403
        assert "Administrator" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_the_admin_email_list_opens_the_panel(self, client, db_session, clean_settings):
        """A Google sign-in that is not in the database as an admin still gets in."""
        await _make_user(db_session, user_id="user-1", email="operator@example.com")
        clean_settings.admin_emails = ["operator@example.com"]

        response = await client.get("/api/v1/admin/version", headers=_bearer("user-1"))

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_the_admin_email_list_alone_closes_the_anonymous_door(
        self, client, db_session, clean_settings
    ):
        await _make_user(db_session, user_id="user-1", email="visitor@example.com")
        clean_settings.admin_emails = ["operator@example.com"]

        response = await client.get("/api/v1/admin/version", headers={"X-API-Key": API_KEY})

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_the_demo_bypass_does_not_open_the_admin_api(
        self, client, db_session, clean_settings
    ):
        """On a demo deployment the key is not even checked - the gate is the identity."""
        clean_settings.demo_api_key_bypass = True
        await _make_user(db_session, user_id="user-1", email="visitor@example.com")

        response = await client.get("/api/v1/admin/version")

        assert response.status_code == 403


class TestTheMountsCarryTheGate:
    """The gate is only worth what main.py mounts behind it."""

    @staticmethod
    def _gated_paths() -> set[str]:
        from api.deps.auth import require_admin_access
        from api.main import app

        gated = set()
        for route in app.routes:
            dependant = getattr(route, "dependant", None)
            if dependant is None:
                continue
            for dependency in dependant.dependencies:
                if dependency.call is require_admin_access:
                    gated.add(route.path)
        return gated

    def test_the_operator_routes_are_mounted_behind_the_gate(self):
        gated = self._gated_paths()

        for path in (
            "/api/v1/admin/version",
            "/api/v1/admin/ingest",
            "/api/v1/admin/reindex",
            "/api/v1/audit",
            "/api/v1/data-sources",
            "/api/v1/bulk-jobs",
            "/api/v1/mcp/connectors",
            "/api/v1/admin/mcp/audit",
        ):
            assert path in gated, f"{path} is not behind the gate"

    def test_the_public_routes_are_not(self):
        gated = self._gated_paths()

        for path in ("/api/v1/search", "/api/v1/chat", "/api/v1/properties"):
            assert path not in gated
