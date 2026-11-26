"""Integration tests for profile router.

Tests full request/response cycles for the Profile API
using in-memory SQLite and dependency overrides.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user
from api.routers import profile
from db.database import get_db, get_db_context
from db.models import User


async def _create_test_user(session: AsyncSession) -> User:
    """Create and persist a real User in the test DB."""
    user = User(
        id="test-user-123",
        email="test@example.com",
        full_name="Test User",
        phone="+48123456789",
        timezone="UTC",
        language="en",
        is_active=True,
        is_verified=False,
        role="user",
    )
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
async def test_app(db_session):
    """Create test app with profile router."""
    app = FastAPI()
    app.include_router(profile.router, prefix="/api/v1")

    # Create a real user in the DB before overriding deps
    user = await _create_test_user(db_session)

    async def override_get_db():
        yield db_session

    async def override_get_db_context():
        yield db_session

    async def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db_context] = override_get_db_context
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestProfileAPI:
    """Integration tests for profile endpoints."""

    @pytest.mark.asyncio
    async def test_get_profile(self, client):
        resp = await client.get("/api/v1/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["id"] == "test-user-123"

    @pytest.mark.asyncio
    async def test_update_profile_name(self, client):
        resp = await client.put(
            "/api/v1/profile",
            json={"full_name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_profile_language(self, client):
        resp = await client.put(
            "/api/v1/profile",
            json={"language": "pl"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_privacy_settings(self, client):
        resp = await client.put(
            "/api/v1/profile/privacy",
            json={
                "profile_visible": False,
                "activity_visible": True,
                "show_email": False,
                "show_phone": False,
                "allow_contact": True,
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_update_returns_profile(self, client):
        resp = await client.put("/api/v1/profile", json={})
        assert resp.status_code == 200


class TestProfileSessionDependency:
    """The router must take its session from a FastAPI dependency.

    The fixture above overrides ``get_db_context``, which hides the defect it
    exists to find: ``get_db_context`` is an ``@asynccontextmanager``, so
    FastAPI hands the route the context manager itself instead of a session,
    and every write in the router fails with an AttributeError. The fixture
    below overrides only ``get_db`` - the dependency the router really uses.
    """

    @pytest.fixture
    async def unoverridden_client(self, db_session):
        app = FastAPI()
        app.include_router(profile.router, prefix="/api/v1")

        user = await _create_test_user(db_session)

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = override_get_current_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    @pytest.mark.asyncio
    async def test_update_profile_writes_the_change(self, unoverridden_client):
        resp = await unoverridden_client.put("/api/v1/profile", json={"full_name": "Written"})
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Written"
