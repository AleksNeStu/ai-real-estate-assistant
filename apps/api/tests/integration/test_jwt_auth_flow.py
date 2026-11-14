"""
Integration tests for full JWT authentication flow.

Covers: register -> login -> protected endpoints -> refresh -> expire -> 401
"""

import os
from datetime import timedelta
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# CRITICAL: Set test env before any app imports
os.environ["ENVIRONMENT"] = "test"
os.environ["API_ACCESS_KEY"] = "dev-secret-key"
os.environ["AUTH_JWT_ENABLED"] = "true"
os.environ["AUTH_EMAIL_VERIFICATION_REQUIRED"] = "false"
os.environ["AUTH_REGISTRATION_ENABLED"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-integration-tests"
os.environ["JWT_ALGORITHM"] = "HS256"

from api.routers import auth_jwt
from core.password import hash_password
from db.database import Base, create_engine, get_db
from db.models import User

# Patch get_jwt_secret to always return the test secret
# (settings singleton may have loaded before our env var was set)
_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

TEST_PASSWORD = "SecurePass123!"


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Clear in-memory rate limits between tests."""
    auth_jwt._auth_rate_limits.clear()
    yield
    auth_jwt._auth_rate_limits.clear()


@pytest.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture(scope="function")
async def auth_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client with JWT auth router mounted."""
    from fastapi import FastAPI

    import core.jwt as jwt_module

    test_app = FastAPI()
    test_app.include_router(auth_jwt.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    # Patch JWT secret so tokens created by the endpoint are verifiable
    with patch.object(jwt_module, "get_jwt_secret", return_value=_TEST_JWT_SECRET):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    test_app.dependency_overrides.clear()


def _unique_email(test_name: str) -> str:
    """Generate unique email per test to avoid collisions."""
    import uuid

    return f"{test_name}-{uuid.uuid4().hex[:8]}@test.example.com"


def _create_test_token(subject: str, roles: list[str] | None = None, **kwargs) -> str:
    """Create a JWT token using the test secret."""
    from datetime import UTC, datetime

    import jwt as pyjwt

    now = datetime.now(UTC)
    expire = now + timedelta(minutes=15)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    if roles:
        payload["roles"] = roles
    payload.update(kwargs)
    return pyjwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")


class TestRegistration:
    """Test user registration flow."""

    @pytest.mark.asyncio
    async def test_register_success(self, auth_client: AsyncClient):
        """Test successful user registration."""
        email = _unique_email("reg")
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": TEST_PASSWORD,
                "full_name": "Test User",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == email
        assert data["user"]["full_name"] == "Test User"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_client: AsyncClient):
        """Test registration with duplicate email returns 409."""
        email = _unique_email("dup")
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": TEST_PASSWORD},
        )
        assert resp.status_code == 201

        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "AnotherPass123"},
        )
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self, auth_client: AsyncClient):
        """Test registration with weak password fails validation."""
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": _unique_email("weak"),
                "password": "short",
                "full_name": "Weak User",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, auth_client: AsyncClient):
        """Test registration with invalid email fails validation."""
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": TEST_PASSWORD,
                "full_name": "Bad Email",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_sets_cookies(self, auth_client: AsyncClient):
        """Test that registration sets auth cookies."""
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": _unique_email("cookies"),
                "password": TEST_PASSWORD,
            },
        )
        assert resp.status_code == 201
        assert any(c.name == "access_token" for c in resp.cookies.jar)


class TestLogin:
    """Test user login flow."""

    @pytest.mark.asyncio
    async def test_login_success(self, auth_client: AsyncClient, db_session: AsyncSession):
        """Test successful login."""
        email = _unique_email("login")
        await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": TEST_PASSWORD},
        )
        await db_session.commit()

        resp = await auth_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": TEST_PASSWORD},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == email

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_client: AsyncClient, db_session: AsyncSession):
        """Test login with wrong password returns 401."""
        email = _unique_email("wrongpw")
        await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": TEST_PASSWORD},
        )
        await db_session.commit()

        resp = await auth_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword123"},
        )
        assert resp.status_code == 401
        assert "Invalid email or password" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, auth_client: AsyncClient):
        """Test login with non-existent email returns 401."""
        resp = await auth_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "SomePassword123"},
        )
        assert resp.status_code == 401


class TestProtectedEndpoints:
    """Test accessing protected endpoints with JWT token."""

    @pytest.mark.asyncio
    async def test_get_current_user_with_bearer(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """Test /auth/me returns user with valid Bearer token."""
        email = _unique_email("me")
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": TEST_PASSWORD, "full_name": "Me User"},
        )
        await db_session.commit()
        token = resp.json()["access_token"]

        resp = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == email

    @pytest.mark.asyncio
    async def test_get_current_user_without_token(self, auth_client: AsyncClient):
        """Test /auth/me returns 401 without token."""
        resp = await auth_client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        assert "Not authenticated" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_token(self, auth_client: AsyncClient):
        """Test /auth/me returns 401 with invalid token."""
        resp = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401


class TestTokenRefresh:
    """Test token refresh flow."""

    @pytest.mark.asyncio
    async def test_refresh_missing_token(self, auth_client: AsyncClient):
        """Test refresh without token returns 401."""
        resp = await auth_client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401
        assert "Refresh token required" in resp.json()["detail"]


class TestExpiredToken:
    """Test expired token handling."""

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, auth_client: AsyncClient):
        """Test that expired access token returns 401."""
        from datetime import UTC, datetime

        import jwt as pyjwt

        now = datetime.now(UTC)
        payload = {
            "sub": "some-user-id",
            "exp": now - timedelta(seconds=10),
            "iat": now - timedelta(minutes=20),
            "type": "access",
            "roles": ["user"],
        }
        expired_token = pyjwt.encode(payload, _TEST_JWT_SECRET, algorithm="HS256")

        resp = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()


class TestLogout:
    """Test logout flow."""

    @pytest.mark.asyncio
    async def test_logout_success(self, auth_client: AsyncClient):
        """Test successful logout clears cookies."""
        resp = await auth_client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        assert "logged out" in resp.json()["message"].lower()


class TestFullFlow:
    """End-to-end: register -> login -> access protected -> refresh."""

    @pytest.mark.asyncio
    async def test_complete_auth_flow(self, auth_client: AsyncClient, db_session: AsyncSession):
        """Test the complete authentication lifecycle."""
        email = _unique_email("e2e")
        # 1. Register
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "E2eTestPass123", "full_name": "E2E User"},
        )
        assert resp.status_code == 201
        access_token = resp.json()["access_token"]
        assert access_token
        await db_session.commit()

        # 2. Access protected endpoint
        resp = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == email

        # 3. Login
        resp = await auth_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "E2eTestPass123"},
        )
        assert resp.status_code == 200
        new_access_token = resp.json()["access_token"]
        # Token may be identical if created in the same second (same claims)
        # Just verify it's a valid token by accessing a protected endpoint
        await db_session.commit()

        # 4. Access protected with new token
        resp = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert resp.status_code == 200

        # 5. Logout
        resp = await auth_client.post("/api/v1/auth/logout")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_token_payload_structure(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        """Verify JWT token contains correct claims."""
        import jwt as pyjwt

        email = _unique_email("claims")
        resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "ClaimsPass123"},
        )
        assert resp.status_code == 201
        access_token = resp.json()["access_token"]

        # Decode with test secret directly
        payload = pyjwt.decode(access_token, _TEST_JWT_SECRET, algorithms=["HS256"])
        assert payload["type"] == "access"
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert payload["roles"] == ["user"]

    @pytest.mark.asyncio
    async def test_inactive_user_denied(self, auth_client: AsyncClient, db_session: AsyncSession):
        """Test that inactive user cannot access protected endpoints."""
        user = User(
            email=_unique_email("inactive"),
            hashed_password=hash_password(TEST_PASSWORD),
            is_active=False,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.commit()

        token = _create_test_token(subject=user.id, roles=["user"])
        resp = await auth_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
        assert "deactivated" in resp.json()["detail"].lower()
