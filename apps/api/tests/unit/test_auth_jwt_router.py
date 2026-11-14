"""Unit tests for api/routers/auth_jwt.py.

Tests cover: rate limiting, helper functions, cookie management, and
endpoint-level behavior with mocked dependencies.

Coverage areas:
- Helper functions: _get_client_ip, _get_client_info, rate limit logic, cookies
- Register: success, registration disabled, duplicate email
- Login: success, user not found, invalid password, locked account, inactive user
- Logout: with and without refresh token cookie
- Refresh: missing token, invalid token, inactive user, success
- /me: returns current user
- Verify email: missing token, invalid token, success
- Resend verification: missing email, user not found, already verified, sends email
- Forgot password: missing email, user not found, sends email
- Reset password: missing fields, weak password, invalid token, success
- Admin unlock: non-admin rejected, missing user_id, user not found, success
- OAuth Google: disabled, not configured, returns URL
- OAuth callback: error, missing params, invalid state, success flows
- OAuth Apple: disabled, not configured, no private key, returns URL, key file not found
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.routers.auth_jwt import (
    _auth_rate_limits,
    _check_auth_rate_limit,
    _clear_auth_cookies,
    _get_client_info,
    _get_client_ip,
    _set_auth_cookies,
)
from api.routers.auth_jwt import (
    router as auth_jwt_router,
)
from db.database import get_db


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    _auth_rate_limits.clear()
    yield
    _auth_rate_limits.clear()


def _make_mock_user(
    id="user-123",
    email="test@example.com",
    full_name="Test User",
    role="user",
    is_active=True,
    is_verified=True,
    hashed_password="$2b$12$hash",
    failed_login_attempts=0,
):
    user = MagicMock(
        spec=[
            "id",
            "email",
            "full_name",
            "role",
            "is_active",
            "is_verified",
            "hashed_password",
            "failed_login_attempts",
            "created_at",
            "last_login_at",
        ]
    )
    user.id = id
    user.email = email
    user.full_name = full_name
    user.role = role
    user.is_active = is_active
    user.is_verified = is_verified
    user.hashed_password = hashed_password
    user.failed_login_attempts = failed_login_attempts
    user.created_at = "2024-01-01T00:00:00Z"
    user.last_login_at = None
    return user


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
async def auth_client(mock_session):
    test_app = FastAPI()
    test_app.include_router(auth_jwt_router, prefix="/api/v1")

    async def override_get_db():
        yield mock_session

    test_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    test_app.dependency_overrides.clear()


# --- Helper Function Tests ---


class TestGetClientIp:
    def test_forwarded_for_header(self):
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.client = None
        assert _get_client_ip(request) == "1.2.3.4"

    def test_no_header_with_client(self):
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        assert _get_client_ip(request) == "10.0.0.1"

    def test_no_header_no_client(self):
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == "unknown"


class TestGetClientInfo:
    def test_extracts_user_agent_and_ip(self):
        request = MagicMock()
        request.headers = {"user-agent": "TestBrowser/1.0", "x-forwarded-for": "1.2.3.4"}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        ua, ip = _get_client_info(request)
        assert ua == "TestBrowser/1.0"
        assert ip == "1.2.3.4"

    def test_no_headers(self):
        request = MagicMock()
        request.headers = {}
        request.client = None
        ua, ip = _get_client_info(request)
        assert ua is None
        assert ip is None

    def test_comma_separated_ip(self):
        request = MagicMock()
        request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"
        ua, ip = _get_client_info(request)
        assert ip == "1.2.3.4"


class TestAuthRateLimitHelper:
    def test_allows_under_limit(self):
        allowed, retry = _check_auth_rate_limit("test-key", max_requests=3)
        assert allowed is True
        assert retry == 0

    def test_blocks_over_limit(self):
        for _ in range(3):
            _check_auth_rate_limit("test-key-2", max_requests=3)
        allowed, retry = _check_auth_rate_limit("test-key-2", max_requests=3)
        assert allowed is False
        assert retry >= 1

    def test_separate_keys_independent(self):
        for _ in range(3):
            _check_auth_rate_limit("key-a", max_requests=3)
        allowed, _ = _check_auth_rate_limit("key-b", max_requests=3)
        assert allowed is True

    def test_window_expiry(self):
        # Fill limit, then shift timestamps into past
        from api.routers import auth_jwt as aj

        key = "test-expiry-key"
        aj._auth_rate_limits[key] = [time.time() - 100, time.time() - 100, time.time() - 100]
        allowed, _ = _check_auth_rate_limit(key, max_requests=3, window_seconds=10)
        assert allowed is True


class TestSetAuthCookies:
    def test_sets_cookies(self):
        response = MagicMock()
        with (
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
        ):
            mock_settings.return_value.environment = "development"
            _set_auth_cookies(response, "access-tok", "refresh-tok", "csrf-tok")
        assert response.set_cookie.call_count == 3

    def test_no_csrf_token(self):
        response = MagicMock()
        with (
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
        ):
            mock_settings.return_value.environment = "production"
            _set_auth_cookies(response, "access-tok", "refresh-tok")
        assert response.set_cookie.call_count == 2

    def test_production_secure_cookies(self):
        response = MagicMock()
        with (
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
        ):
            mock_settings.return_value.environment = "production"
            _set_auth_cookies(response, "at", "rt")
        for call in response.set_cookie.call_args_list:
            assert call.kwargs.get("secure") is True


class TestClearAuthCookies:
    def test_clears_all_cookies(self):
        response = MagicMock()
        _clear_auth_cookies(response)
        assert response.delete_cookie.call_count == 3
        calls = response.delete_cookie.call_args_list
        deleted_keys = set()
        for call in calls:
            deleted_keys.add(call.kwargs.get("key", call.args[0] if call.args else ""))
        assert "access_token" in deleted_keys
        assert "refresh_token" in deleted_keys
        assert "csrf_token" in deleted_keys


# --- Endpoint Tests ---


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, auth_client):
        mock_user = _make_mock_user()
        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_repo_cls,
            patch("api.routers.auth_jwt.hash_password", return_value="hashed"),
            patch("api.routers.auth_jwt.create_access_token", return_value="access-tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh-tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_registration_enabled = True
            mock_settings_obj.auth_email_verification_required = False
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            mock_user_repo = MagicMock()
            mock_user_repo_cls.return_value = mock_user_repo
            mock_user_repo.get_by_email = AsyncMock(return_value=None)
            mock_user_repo.create = AsyncMock(return_value=mock_user)

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.create = AsyncMock()

            response = await auth_client.post(
                "/api/v1/auth/register",
                json={"email": "new@example.com", "password": "Str0ngP@ss1"},
            )
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["access_token"] == "access-tok"
            assert data["refresh_token"] == "refresh-tok"
            assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_registration_disabled(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_registration_enabled = False
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.post(
                "/api/v1/auth/register",
                json={"email": "new@example.com", "password": "Str0ngP@ss1"},
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "disabled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_client):
        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_repo_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_registration_enabled = True
            mock_settings.return_value = mock_settings_obj

            mock_user_repo = MagicMock()
            mock_user_repo_cls.return_value = mock_user_repo
            mock_user_repo.get_by_email = AsyncMock(return_value=_make_mock_user())

            response = await auth_client.post(
                "/api/v1/auth/register",
                json={"email": "test@example.com", "password": "Str0ngP@ss1"},
            )
            assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_register_rate_limited(self, auth_client):
        """Register endpoint returns 429 when rate limit is exceeded."""
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_registration_enabled = True
            mock_settings.return_value = mock_settings_obj

            # Exhaust the rate limit (max_requests=3 for register)
            for _ in range(3):
                await auth_client.post(
                    "/api/v1/auth/register",
                    json={"email": "test@example.com", "password": "Str0ngP@ss1"},
                )

            # 4th request should be rate limited
            response = await auth_client.post(
                "/api/v1/auth/register",
                json={"email": "test@example.com", "password": "Str0ngP@ss1"},
            )
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, auth_client):
        mock_user = _make_mock_user()
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_repo_cls,
            patch("api.routers.auth_jwt.AccountLockoutService") as mock_lockout_cls,
            patch("api.routers.auth_jwt.get_audit_logger") as mock_audit,
            patch("api.routers.auth_jwt.verify_password", return_value=True),
            patch("api.routers.auth_jwt.needs_rehash", return_value=False),
            patch("api.routers.auth_jwt.create_access_token", return_value="access-tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh-tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo_cls.return_value = mock_user_repo
            mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)
            mock_user_repo.update_last_login = AsyncMock()

            mock_lockout = MagicMock()
            mock_lockout_cls.return_value = mock_lockout
            mock_lockout.check_lockout = AsyncMock(return_value=(False, None))
            mock_lockout.clear_failed_attempts = AsyncMock()

            mock_audit.return_value = MagicMock()
            mock_audit.return_value.log = MagicMock()

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.create = AsyncMock()

            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Str0ngP@ss1"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "access-tok"
            assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_client):
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_repo_cls,
            patch("api.routers.auth_jwt.AccountLockoutService") as mock_lockout_cls,
            patch("api.routers.auth_jwt.get_audit_logger") as mock_audit,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo_cls.return_value = mock_user_repo
            mock_user_repo.get_by_email = AsyncMock(return_value=None)

            mock_lockout = MagicMock()
            mock_lockout_cls.return_value = mock_lockout

            mock_audit.return_value = MagicMock()
            mock_audit.return_value.log = MagicMock()

            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "nobody@example.com", "password": "Str0ngP@ss1"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, auth_client):
        mock_user = _make_mock_user()
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_repo_cls,
            patch("api.routers.auth_jwt.AccountLockoutService") as mock_lockout_cls,
            patch("api.routers.auth_jwt.get_audit_logger") as mock_audit,
            patch("api.routers.auth_jwt.verify_password", return_value=False),
        ):
            mock_user_repo = MagicMock()
            mock_user_repo_cls.return_value = mock_user_repo
            mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)

            mock_lockout = MagicMock()
            mock_lockout_cls.return_value = mock_lockout
            mock_lockout.check_lockout = AsyncMock(return_value=(False, None))
            mock_lockout.record_failed_attempt = AsyncMock(return_value=(False, 0))

            mock_audit.return_value = MagicMock()
            mock_audit.return_value.log = MagicMock()

            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "WrongP@ss1"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_locked_account(self, auth_client):
        mock_user = _make_mock_user()
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_repo_cls,
            patch("api.routers.auth_jwt.AccountLockoutService") as mock_lockout_cls,
            patch("api.routers.auth_jwt.get_audit_logger") as mock_audit,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo_cls.return_value = mock_user_repo
            mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)

            mock_lockout = MagicMock()
            mock_lockout_cls.return_value = mock_lockout
            mock_lockout.check_lockout = AsyncMock(return_value=(True, 300))

            mock_audit.return_value = MagicMock()
            mock_audit.return_value.log = MagicMock()

            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Str0ngP@ss1"},
            )
            assert response.status_code == status.HTTP_423_LOCKED
            assert "locked" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, auth_client):
        mock_user = _make_mock_user(is_active=False)
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_repo_cls,
            patch("api.routers.auth_jwt.AccountLockoutService") as mock_lockout_cls,
            patch("api.routers.auth_jwt.get_audit_logger") as mock_audit,
            patch("api.routers.auth_jwt.verify_password", return_value=True),
        ):
            mock_user_repo = MagicMock()
            mock_user_repo_cls.return_value = mock_user_repo
            mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)

            mock_lockout = MagicMock()
            mock_lockout_cls.return_value = mock_lockout
            mock_lockout.check_lockout = AsyncMock(return_value=(False, None))
            mock_lockout.clear_failed_attempts = AsyncMock()

            mock_audit.return_value = MagicMock()
            mock_audit.return_value.log = MagicMock()

            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Str0ngP@ss1"},
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "deactivated" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_rehashes_password(self, auth_client):
        mock_user = _make_mock_user()
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_repo_cls,
            patch("api.routers.auth_jwt.AccountLockoutService") as mock_lockout_cls,
            patch("api.routers.auth_jwt.get_audit_logger") as mock_audit,
            patch("api.routers.auth_jwt.verify_password", return_value=True),
            patch("api.routers.auth_jwt.needs_rehash", return_value=True),
            patch("api.routers.auth_jwt.hash_password", return_value="new-hash"),
            patch("api.routers.auth_jwt.create_access_token", return_value="access-tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh-tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo_cls.return_value = mock_user_repo
            mock_user_repo.get_by_email = AsyncMock(return_value=mock_user)
            mock_user_repo.update_last_login = AsyncMock()
            mock_user_repo.set_password = AsyncMock()

            mock_lockout = MagicMock()
            mock_lockout_cls.return_value = mock_lockout
            mock_lockout.check_lockout = AsyncMock(return_value=(False, None))
            mock_lockout.clear_failed_attempts = AsyncMock()

            mock_audit.return_value = MagicMock()
            mock_audit.return_value.log = MagicMock()

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.create = AsyncMock()

            response = await auth_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Str0ngP@ss1"},
            )
            assert response.status_code == status.HTTP_200_OK
            mock_user_repo.set_password.assert_called_once_with(mock_user, "new-hash")


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_with_valid_refresh_token(self, auth_client):
        mock_stored_token = MagicMock()
        with (
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_token = AsyncMock(return_value=mock_stored_token)
            mock_repo.revoke = AsyncMock()

            response = await auth_client.post(
                "/api/v1/auth/logout",
                cookies={"refresh_token": "valid-refresh-tok"},
            )
            assert response.status_code == status.HTTP_200_OK
            assert "logged out" in response.json()["message"].lower()
            mock_repo.revoke.assert_called_once_with(mock_stored_token)

    @pytest.mark.asyncio
    async def test_logout_without_refresh_token(self, auth_client):
        response = await auth_client.post("/api/v1/auth/logout")
        assert response.status_code == status.HTTP_200_OK
        assert "logged out" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_logout_with_invalid_refresh_token(self, auth_client):
        with (
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_token = AsyncMock(return_value=None)

            response = await auth_client.post(
                "/api/v1/auth/logout",
                cookies={"refresh_token": "unknown-token"},
            )
            assert response.status_code == status.HTTP_200_OK


class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_refresh_missing_token(self, auth_client):
        response = await auth_client.post("/api/v1/auth/refresh")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "required" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, auth_client):
        with (
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_token = AsyncMock(return_value=None)

            response = await auth_client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": "bad-token"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_inactive_user(self, auth_client):
        mock_stored_token = MagicMock()
        mock_stored_token.is_valid = True
        mock_stored_token.user_id = "user-123"
        mock_inactive_user = _make_mock_user(is_active=False)

        with (
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
        ):
            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.get_by_token = AsyncMock(return_value=mock_stored_token)

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_inactive_user)

            response = await auth_client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": "valid-token"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_refresh_success(self, auth_client):
        mock_user = _make_mock_user()
        mock_stored_token = MagicMock()
        mock_stored_token.is_valid = True
        mock_stored_token.user_id = "user-123"

        with (
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.create_access_token", return_value="new-access"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="new-refresh"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
        ):
            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.get_by_token = AsyncMock(return_value=mock_stored_token)
            mock_refresh_repo.revoke = AsyncMock()
            mock_refresh_repo.create = AsyncMock()

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)

            response = await auth_client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": "valid-token"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "new-access"
            assert data["refresh_token"] == "new-refresh"
            mock_refresh_repo.revoke.assert_called_once_with(mock_stored_token)
            mock_refresh_repo.create.assert_called_once()


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_me_returns_user(self, auth_client):
        from api.deps.auth import get_current_active_user

        mock_user = _make_mock_user()

        # Override the auth dependency to return our mock user
        async def override_auth():
            return mock_user

        # We need a fresh app with the override
        test_app = FastAPI()
        test_app.include_router(auth_jwt_router, prefix="/api/v1")

        async def override_get_db():
            yield AsyncMock()

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_auth

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/auth/me")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == "user-123"
            assert data["email"] == "test@example.com"


class TestVerifyEmail:
    @pytest.mark.asyncio
    async def test_verify_email_missing_token(self, auth_client):
        response = await auth_client.post("/api/v1/auth/verify-email", json={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, auth_client):
        with patch("db.repositories.EmailVerificationTokenRepository") as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo_cls.return_value = mock_repo
            mock_token = MagicMock()
            mock_token.is_valid = False
            mock_repo.get_by_token.return_value = mock_token

            response = await auth_client.post(
                "/api/v1/auth/verify-email", json={"token": "bad-token"}
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_verify_email_success(self, auth_client):
        mock_user = _make_mock_user()
        mock_stored_token = MagicMock()
        mock_stored_token.is_valid = True
        mock_stored_token.user_id = "user-123"

        with (
            patch("db.repositories.EmailVerificationTokenRepository") as mock_token_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
        ):
            mock_token_repo = MagicMock()
            mock_token_cls.return_value = mock_token_repo
            mock_token_repo.get_by_token = AsyncMock(return_value=mock_stored_token)
            mock_token_repo.mark_used = AsyncMock()

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_user_repo.set_verified = AsyncMock()

            response = await auth_client.post(
                "/api/v1/auth/verify-email", json={"token": "valid-token"}
            )
            assert response.status_code == status.HTTP_200_OK
            assert "verified" in response.json()["message"].lower()
            mock_user_repo.set_verified.assert_called_once_with(mock_user)
            mock_token_repo.mark_used.assert_called_once_with(mock_stored_token)

    @pytest.mark.asyncio
    async def test_verify_email_user_not_found(self, auth_client):
        mock_stored_token = MagicMock()
        mock_stored_token.is_valid = True
        mock_stored_token.user_id = "nonexistent"

        with (
            patch("db.repositories.EmailVerificationTokenRepository") as mock_token_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
        ):
            mock_token_repo = MagicMock()
            mock_token_cls.return_value = mock_token_repo
            mock_token_repo.get_by_token = AsyncMock(return_value=mock_stored_token)

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=None)

            response = await auth_client.post(
                "/api/v1/auth/verify-email", json={"token": "valid-token"}
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestResendVerification:
    @pytest.mark.asyncio
    async def test_resend_missing_email(self, auth_client):
        response = await auth_client.post("/api/v1/auth/resend-verification", json={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_resend_user_not_found_returns_ok(self, auth_client):
        with patch("api.routers.auth_jwt.UserRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_email = AsyncMock(return_value=None)

            response = await auth_client.post(
                "/api/v1/auth/resend-verification", json={"email": "nobody@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_resend_already_verified_returns_ok(self, auth_client):
        with patch("api.routers.auth_jwt.UserRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_email = AsyncMock(return_value=_make_mock_user(is_verified=True))

            response = await auth_client.post(
                "/api/v1/auth/resend-verification", json={"email": "test@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_resend_sends_email_for_unverified_user(self, auth_client):
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("db.repositories.EmailVerificationTokenRepository") as mock_token_cls,
            patch("api.routers.auth_jwt.get_email_service") as mock_email_svc,
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.jwt.generate_verification_token", return_value="vtoken123"),
        ):
            mock_user = MagicMock()
            mock_user_cls.return_value = mock_user
            mock_user.get_by_email = AsyncMock(return_value=_make_mock_user(is_verified=False))

            mock_token = MagicMock()
            mock_token_cls.return_value = mock_token
            mock_token.invalidate_for_user = AsyncMock()
            mock_token.create = AsyncMock()

            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "development"
            mock_settings_obj.frontend_url = "http://localhost:3000"
            mock_settings.return_value = mock_settings_obj

            mock_email = AsyncMock()
            mock_email_svc.return_value = mock_email

            response = await auth_client.post(
                "/api/v1/auth/resend-verification", json={"email": "test@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK


class TestForgotPassword:
    @pytest.mark.asyncio
    async def test_forgot_missing_email(self, auth_client):
        response = await auth_client.post("/api/v1/auth/forgot-password", json={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_forgot_user_not_found(self, auth_client):
        with patch("api.routers.auth_jwt.UserRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_email = AsyncMock(return_value=None)

            response = await auth_client.post(
                "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_forgot_sends_email(self, auth_client):
        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("db.repositories.PasswordResetTokenRepository") as mock_token_cls,
            patch("api.routers.auth_jwt.get_email_service") as mock_email_svc,
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.jwt.generate_password_reset_token", return_value="reset-tok-123"),
        ):
            mock_user = MagicMock()
            mock_user_cls.return_value = mock_user
            mock_user.get_by_email = AsyncMock(return_value=_make_mock_user())

            mock_token = MagicMock()
            mock_token_cls.return_value = mock_token
            mock_token.create = AsyncMock()

            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "development"
            mock_settings_obj.frontend_url = "http://localhost:3000"
            mock_settings.return_value = mock_settings_obj

            mock_email = AsyncMock()
            mock_email_svc.return_value = mock_email

            response = await auth_client.post(
                "/api/v1/auth/forgot-password", json={"email": "test@example.com"}
            )
            assert response.status_code == status.HTTP_200_OK
            mock_email.send_password_reset_email.assert_called_once()


class TestResetPassword:
    @pytest.mark.asyncio
    async def test_reset_missing_fields(self, auth_client):
        response = await auth_client.post("/api/v1/auth/reset-password", json={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_reset_weak_password(self, auth_client):
        with patch("core.password.validate_password_strength", return_value=(False, "Too short")):
            response = await auth_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "some-token", "new_password": "short"},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Too short" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reset_invalid_token(self, auth_client):
        with (
            patch("core.password.validate_password_strength", return_value=(True, "")),
            patch("db.repositories.PasswordResetTokenRepository") as mock_repo_cls,
        ):
            mock_repo = AsyncMock()
            mock_repo_cls.return_value = mock_repo
            mock_repo.get_by_token.return_value = None

            response = await auth_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "bad-token", "new_password": "Str0ngP@ssw0rd"},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reset_success(self, auth_client):
        mock_user = _make_mock_user()
        mock_stored_token = MagicMock()
        mock_stored_token.is_valid = True
        mock_stored_token.user_id = "user-123"

        with (
            patch("core.password.validate_password_strength", return_value=(True, "")),
            patch("db.repositories.PasswordResetTokenRepository") as mock_token_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.hash_password", return_value="new-hashed"),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_token_repo = MagicMock()
            mock_token_cls.return_value = mock_token_repo
            mock_token_repo.get_by_token = AsyncMock(return_value=mock_stored_token)
            mock_token_repo.mark_used = AsyncMock()

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_user_repo.set_password = AsyncMock()

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.revoke_all_for_user = AsyncMock()

            response = await auth_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "valid-token", "new_password": "Str0ngP@ssw0rd"},
            )
            assert response.status_code == status.HTTP_200_OK
            assert "reset" in response.json()["message"].lower()
            mock_user_repo.set_password.assert_called_once_with(mock_user, "new-hashed")
            mock_token_repo.mark_used.assert_called_once_with(mock_stored_token)
            mock_refresh_repo.revoke_all_for_user.assert_called_once_with("user-123")

    @pytest.mark.asyncio
    async def test_reset_user_not_found(self, auth_client):
        mock_stored_token = MagicMock()
        mock_stored_token.is_valid = True
        mock_stored_token.user_id = "nonexistent"

        with (
            patch("core.password.validate_password_strength", return_value=(True, "")),
            patch("db.repositories.PasswordResetTokenRepository") as mock_token_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
        ):
            mock_token_repo = MagicMock()
            mock_token_cls.return_value = mock_token_repo
            mock_token_repo.get_by_token = AsyncMock(return_value=mock_stored_token)

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=None)

            response = await auth_client.post(
                "/api/v1/auth/reset-password",
                json={"token": "valid-token", "new_password": "Str0ngP@ssw0rd"},
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAdminUnlockAccount:
    @pytest.mark.asyncio
    async def test_admin_unlock_non_admin_rejected(self, auth_client):
        from api.deps.auth import get_current_active_user

        mock_regular_user = _make_mock_user(role="user")

        test_app = FastAPI()
        test_app.include_router(auth_jwt_router, prefix="/api/v1")

        async def override_get_db():
            yield AsyncMock()

        async def override_auth():
            return mock_regular_user

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_auth

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/admin/unlock-account",
                json={"user_id": "locked-user-123"},
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "admin" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_admin_unlock_missing_user_id(self, auth_client):
        from api.deps.auth import get_current_active_user

        mock_admin = _make_mock_user(role="admin")

        test_app = FastAPI()
        test_app.include_router(auth_jwt_router, prefix="/api/v1")

        async def override_get_db():
            yield AsyncMock()

        async def override_auth():
            return mock_admin

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_auth

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/admin/unlock-account",
                json={},
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_admin_unlock_user_not_found(self, auth_client):
        from api.deps.auth import get_current_active_user

        mock_admin = _make_mock_user(role="admin")

        test_app = FastAPI()
        test_app.include_router(auth_jwt_router, prefix="/api/v1")

        async def override_get_db():
            yield AsyncMock()

        async def override_auth():
            return mock_admin

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_auth

        with patch("api.routers.auth_jwt.UserRepository") as mock_user_cls:
            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=None)

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/admin/unlock-account",
                    json={"user_id": "nonexistent-user"},
                )
                assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_admin_unlock_success(self, auth_client):
        from api.deps.auth import get_current_active_user

        mock_admin = _make_mock_user(id="admin-1", role="admin")
        mock_locked_user = _make_mock_user(id="locked-1", email="locked@example.com")

        test_app = FastAPI()
        test_app.include_router(auth_jwt_router, prefix="/api/v1")

        mock_session = AsyncMock()

        async def override_get_db():
            yield mock_session

        async def override_auth():
            return mock_admin

        test_app.dependency_overrides[get_db] = override_get_db
        test_app.dependency_overrides[get_current_active_user] = override_auth

        with (
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.AccountLockoutService") as mock_lockout_cls,
        ):
            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_locked_user)

            mock_lockout = MagicMock()
            mock_lockout_cls.return_value = mock_lockout
            mock_lockout.unlock_account = AsyncMock()

            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/admin/unlock-account",
                    json={"user_id": "locked-1"},
                )
                assert response.status_code == status.HTTP_200_OK
                assert "unlocked" in response.json()["message"].lower()
                mock_lockout.unlock_account.assert_called_once_with(mock_locked_user)


class TestGoogleOAuth:
    @pytest.mark.asyncio
    async def test_google_oauth_disabled(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_google_enabled = False
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/google")
            assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_google_oauth_not_configured(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_google_enabled = True
            mock_settings_obj.google_client_id = None
            mock_settings_obj.google_client_secret = None
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/google")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_google_oauth_returns_url(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_google_enabled = True
            mock_settings_obj.google_client_id = "test-client-id"
            mock_settings_obj.google_client_secret = "test-secret"
            mock_settings_obj.google_redirect_uri = "http://localhost/callback"
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            with patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls:
                mock_provider = MagicMock()
                mock_provider_cls.return_value = mock_provider
                mock_provider.generate_pkce_verifier.return_value = "verifier"
                mock_provider.generate_pkce_challenge.return_value = "challenge"
                mock_provider.get_authorization_url.return_value = (
                    "https://accounts.google.com/auth?state=abc"
                )

                response = await auth_client.get("/api/v1/auth/oauth/google")
                assert response.status_code == status.HTTP_200_OK
                assert "authorization_url" in response.json()


class TestOAuthCallback:
    @pytest.mark.asyncio
    async def test_callback_with_error(self, auth_client):
        response = await auth_client.get("/api/v1/auth/oauth/callback?error=access_denied")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "access_denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_missing_params(self, auth_client):
        response = await auth_client.get("/api/v1/auth/oauth/callback")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_invalid_state(self, auth_client):
        response = await auth_client.get("/api/v1/auth/oauth/callback?code=abc&state=wrong")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "state" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_callback_success_existing_oauth_user(self, auth_client):
        """OAuth callback with existing linked OAuth account."""
        mock_user = _make_mock_user()
        mock_user_info = MagicMock()
        mock_user_info.provider = "google"
        mock_user_info.provider_user_id = "google-123"
        mock_user_info.email = "test@example.com"
        mock_user_info.name = "Test User"
        mock_user_info.email_verified = True

        mock_oauth_account = MagicMock()
        mock_oauth_account.user_id = "user-123"

        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.OAuthAccountRepository") as mock_oauth_cls,
            patch("api.routers.auth_jwt.create_access_token", return_value="access-tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh-tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.google_client_id = "test-id"
            mock_settings_obj.google_client_secret = "test-secret"
            mock_settings_obj.google_redirect_uri = "http://localhost/callback"
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider
            mock_provider.verify_and_get_user = AsyncMock(return_value=mock_user_info)

            mock_oauth_repo = MagicMock()
            mock_oauth_cls.return_value = mock_oauth_repo
            mock_oauth_repo.get_by_provider = AsyncMock(return_value=mock_oauth_account)

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_user_repo.update_last_login = AsyncMock()

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.create = AsyncMock()

            response = await auth_client.get(
                "/api/v1/auth/oauth/callback?code=valid-code&state=test-state",
                cookies={
                    "oauth_state": "test-state",
                    "oauth_code_verifier": "test-verifier",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "access-tok"

    @pytest.mark.asyncio
    async def test_callback_redirects_to_the_frontend_when_one_is_configured(self, auth_client):
        """A deployment with a frontend URL ends the flow on the interface.

        The tokens belong in httpOnly cookies, and that is where they are set.
        A JSON body would put them into the page the visitor is looking at, so
        the callback sends the browser to the frontend's own callback page
        instead.
        """
        mock_user = _make_mock_user()
        mock_user_info = MagicMock()
        mock_user_info.provider = "google"
        mock_user_info.provider_user_id = "google-123"
        mock_user_info.email = "test@example.com"
        mock_user_info.name = "Test User"
        mock_user_info.email_verified = True

        mock_oauth_account = MagicMock()
        mock_oauth_account.user_id = "user-123"

        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.OAuthAccountRepository") as mock_oauth_cls,
            patch("api.routers.auth_jwt.create_access_token", return_value="access-tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh-tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.google_client_id = "test-id"
            mock_settings_obj.google_client_secret = "test-secret"
            mock_settings_obj.google_redirect_uri = "http://localhost/callback"
            mock_settings_obj.environment = "development"
            mock_settings_obj.frontend_url = "https://realty.kittray.com"
            mock_settings.return_value = mock_settings_obj

            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider
            mock_provider.verify_and_get_user = AsyncMock(return_value=mock_user_info)

            mock_oauth_repo = MagicMock()
            mock_oauth_cls.return_value = mock_oauth_repo
            mock_oauth_repo.get_by_provider = AsyncMock(return_value=mock_oauth_account)

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_user)
            mock_user_repo.update_last_login = AsyncMock()

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.create = AsyncMock()

            response = await auth_client.get(
                "/api/v1/auth/oauth/callback?code=valid-code&state=test-state",
                cookies={
                    "oauth_state": "test-state",
                    "oauth_code_verifier": "test-verifier",
                },
            )
            assert response.status_code == status.HTTP_302_FOUND
            assert response.headers["location"] == "https://realty.kittray.com/auth/oauth/callback"
            # The session is in the cookies of the redirect, not in a body.
            assert "access_token=access-tok" in response.headers.get("set-cookie", "")

    @pytest.mark.asyncio
    async def test_callback_reprovisions_a_user_the_oauth_link_outlived(self, auth_client):
        """An OAuth link whose user is gone must not lock the account out.

        The demo's re-seed deletes every user on startup and SQLite does not
        enforce ON DELETE CASCADE, so a link can outlive the user it points
        at. The sign-in used to die with a 500 there, and nothing ever
        removed the link, so the account could never sign in again.
        """
        mock_user_info = MagicMock()
        mock_user_info.provider = "google"
        mock_user_info.provider_user_id = "google-123"
        mock_user_info.email = "test@example.com"
        mock_user_info.name = "Test User"
        mock_user_info.email_verified = True

        mock_oauth_account = MagicMock()
        mock_oauth_account.id = "oauth-1"
        mock_oauth_account.user_id = "user-that-no-longer-exists"
        mock_oauth_account.provider_email = "test@example.com"

        mock_new_user = _make_mock_user(id="reprovisioned-user")

        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.OAuthAccountRepository") as mock_oauth_cls,
            patch("api.routers.auth_jwt.create_access_token", return_value="access-tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh-tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.google_client_id = "test-id"
            mock_settings_obj.google_client_secret = "test-secret"
            mock_settings_obj.google_redirect_uri = "http://localhost/callback"
            mock_settings_obj.environment = "development"
            mock_settings_obj.frontend_url = "https://realty.kittray.com"
            mock_settings.return_value = mock_settings_obj

            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider
            mock_provider.verify_and_get_user = AsyncMock(return_value=mock_user_info)

            mock_oauth_repo = MagicMock()
            mock_oauth_cls.return_value = mock_oauth_repo
            mock_oauth_repo.get_by_provider = AsyncMock(return_value=mock_oauth_account)

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            # The user the link points at is gone.
            mock_user_repo.get_by_id = AsyncMock(return_value=None)
            mock_user_repo.create = AsyncMock(return_value=mock_new_user)
            mock_user_repo.update_last_login = AsyncMock()

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.create = AsyncMock()

            response = await auth_client.get(
                "/api/v1/auth/oauth/callback?code=valid-code&state=test-state",
                cookies={
                    "oauth_state": "test-state",
                    "oauth_code_verifier": "test-verifier",
                },
            )
            # The visitor is signed in, not locked out.
            assert response.status_code == status.HTTP_302_FOUND
            assert "access_token=access-tok" in response.headers.get("set-cookie", "")
            # The user was provisioned again...
            mock_user_repo.create.assert_called_once()
            assert mock_user_repo.create.call_args.kwargs["email"] == "test@example.com"
            # ...and the link was repointed at it.
            assert mock_oauth_account.user_id == "reprovisioned-user"

    @pytest.mark.asyncio
    async def test_callback_success_new_oauth_user(self, auth_client):
        """OAuth callback creating a new user via OAuth."""
        mock_new_user = _make_mock_user(id="new-user-1")
        mock_user_info = MagicMock()
        mock_user_info.provider = "google"
        mock_user_info.provider_user_id = "google-new"
        mock_user_info.email = "newuser@example.com"
        mock_user_info.name = "New User"
        mock_user_info.email_verified = True

        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.OAuthAccountRepository") as mock_oauth_cls,
            patch("api.routers.auth_jwt.create_access_token", return_value="access-tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh-tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.google_client_id = "test-id"
            mock_settings_obj.google_client_secret = "test-secret"
            mock_settings_obj.google_redirect_uri = "http://localhost/callback"
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider
            mock_provider.verify_and_get_user = AsyncMock(return_value=mock_user_info)

            mock_oauth_repo = MagicMock()
            mock_oauth_cls.return_value = mock_oauth_repo
            # No existing OAuth account
            mock_oauth_repo.get_by_provider = AsyncMock(return_value=None)
            mock_oauth_repo.create = AsyncMock()

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            # No existing user by email
            mock_user_repo.get_by_email = AsyncMock(return_value=None)
            mock_user_repo.create = AsyncMock(return_value=mock_new_user)
            mock_user_repo.update_last_login = AsyncMock()

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.create = AsyncMock()

            response = await auth_client.get(
                "/api/v1/auth/oauth/callback?code=valid-code&state=test-state",
                cookies={
                    "oauth_state": "test-state",
                    "oauth_code_verifier": "test-verifier",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["access_token"] == "access-tok"

    @pytest.mark.asyncio
    async def test_callback_link_existing_user_by_email(self, auth_client):
        """OAuth callback links OAuth to existing user by matching email."""
        mock_existing_user = _make_mock_user()
        mock_user_info = MagicMock()
        mock_user_info.provider = "google"
        mock_user_info.provider_user_id = "google-new"
        mock_user_info.email = "test@example.com"
        mock_user_info.name = "Test User"
        mock_user_info.email_verified = True

        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.OAuthAccountRepository") as mock_oauth_cls,
            patch("api.routers.auth_jwt.create_access_token", return_value="access-tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh-tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.google_client_id = "test-id"
            mock_settings_obj.google_client_secret = "test-secret"
            mock_settings_obj.google_redirect_uri = "http://localhost/callback"
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider
            mock_provider.verify_and_get_user = AsyncMock(return_value=mock_user_info)

            mock_oauth_repo = MagicMock()
            mock_oauth_cls.return_value = mock_oauth_repo
            mock_oauth_repo.get_by_provider = AsyncMock(return_value=None)
            mock_oauth_repo.create = AsyncMock()

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_email = AsyncMock(return_value=mock_existing_user)
            mock_user_repo.update_last_login = AsyncMock()

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.create = AsyncMock()

            response = await auth_client.get(
                "/api/v1/auth/oauth/callback?code=valid-code&state=test-state",
                cookies={
                    "oauth_state": "test-state",
                    "oauth_code_verifier": "test-verifier",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            # OAuth account should be linked to existing user
            mock_oauth_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_oauth_error(self, auth_client):
        """OAuth callback when provider raises OAuthError."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.google_client_id = "test-id"
        mock_settings_obj.google_client_secret = "test-secret"
        mock_settings_obj.google_redirect_uri = "http://localhost/callback"
        mock_settings_obj.environment = "development"

        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls,
        ):
            mock_settings.return_value = mock_settings_obj

            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider

            # Create an OAuthError
            from core.oauth import OAuthError

            mock_provider.verify_and_get_user = AsyncMock(
                side_effect=OAuthError("Invalid authorization code")
            )

            response = await auth_client.get(
                "/api/v1/auth/oauth/callback?code=bad-code&state=test-state",
                cookies={
                    "oauth_state": "test-state",
                    "oauth_code_verifier": "test-verifier",
                },
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid authorization code" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_callback_inactive_oauth_user(self, auth_client):
        """OAuth callback rejects deactivated users."""
        mock_inactive_user = _make_mock_user(is_active=False)
        mock_user_info = MagicMock()
        mock_user_info.provider = "google"
        mock_user_info.provider_user_id = "google-123"
        mock_user_info.email = "test@example.com"
        mock_user_info.name = "Inactive User"
        mock_user_info.email_verified = True

        mock_oauth_account = MagicMock()
        mock_oauth_account.user_id = "user-123"

        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.OAuthAccountRepository") as mock_oauth_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.google_client_id = "test-id"
            mock_settings_obj.google_client_secret = "test-secret"
            mock_settings_obj.google_redirect_uri = "http://localhost/callback"
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider
            mock_provider.verify_and_get_user = AsyncMock(return_value=mock_user_info)

            mock_oauth_repo = MagicMock()
            mock_oauth_cls.return_value = mock_oauth_repo
            mock_oauth_repo.get_by_provider = AsyncMock(return_value=mock_oauth_account)

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.get_by_id = AsyncMock(return_value=mock_inactive_user)

            response = await auth_client.get(
                "/api/v1/auth/oauth/callback?code=valid-code&state=test-state",
                cookies={
                    "oauth_state": "test-state",
                    "oauth_code_verifier": "test-verifier",
                },
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "deactivated" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_callback_oauth_user_without_email(self, auth_client):
        """OAuth callback creates user without email when provider doesn't provide one."""
        mock_new_user = _make_mock_user(id="no-email-user")
        mock_user_info = MagicMock()
        mock_user_info.provider = "google"
        mock_user_info.provider_user_id = "google-no-email"
        mock_user_info.email = None
        mock_user_info.name = "No Email"
        mock_user_info.email_verified = False

        with (
            patch("api.routers.auth_jwt.get_settings") as mock_settings,
            patch("core.oauth.GoogleOAuthProvider") as mock_provider_cls,
            patch("api.routers.auth_jwt.UserRepository") as mock_user_cls,
            patch("api.routers.auth_jwt.OAuthAccountRepository") as mock_oauth_cls,
            patch("api.routers.auth_jwt.create_access_token", return_value="access-tok"),
            patch("api.routers.auth_jwt.generate_refresh_token", return_value="refresh-tok"),
            patch("api.routers.auth_jwt.get_access_token_expire_minutes", return_value=15),
            patch("api.routers.auth_jwt.get_refresh_token_expire_days", return_value=7),
            patch("api.routers.auth_jwt.RefreshTokenRepository") as mock_refresh_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.google_client_id = "test-id"
            mock_settings_obj.google_client_secret = "test-secret"
            mock_settings_obj.google_redirect_uri = "http://localhost/callback"
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            mock_provider = MagicMock()
            mock_provider_cls.return_value = mock_provider
            mock_provider.verify_and_get_user = AsyncMock(return_value=mock_user_info)

            mock_oauth_repo = MagicMock()
            mock_oauth_cls.return_value = mock_oauth_repo
            mock_oauth_repo.get_by_provider = AsyncMock(return_value=None)
            mock_oauth_repo.create = AsyncMock()

            mock_user_repo = MagicMock()
            mock_user_cls.return_value = mock_user_repo
            mock_user_repo.create = AsyncMock(return_value=mock_new_user)
            mock_user_repo.update_last_login = AsyncMock()

            mock_refresh_repo = MagicMock()
            mock_refresh_cls.return_value = mock_refresh_repo
            mock_refresh_repo.create = AsyncMock()

            response = await auth_client.get(
                "/api/v1/auth/oauth/callback?code=valid-code&state=test-state",
                cookies={
                    "oauth_state": "test-state",
                    "oauth_code_verifier": "test-verifier",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            # Verify user was created with generated email
            user_create_call = mock_user_repo.create.call_args
            assert "oauth.local" in user_create_call.kwargs.get("email", "")


class TestAppleOAuth:
    @pytest.mark.asyncio
    async def test_apple_oauth_disabled(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = False
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/apple")
            assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_apple_oauth_not_configured(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = True
            mock_settings_obj.apple_client_id = None
            mock_settings_obj.apple_team_id = None
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/apple")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_apple_oauth_no_private_key(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = True
            mock_settings_obj.apple_client_id = "com.test.app"
            mock_settings_obj.apple_team_id = "team123"
            mock_settings_obj.apple_key_id = "key123"
            mock_settings_obj.apple_private_key_path = None
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/apple")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_apple_oauth_returns_url(self, auth_client, tmp_path):
        key_file = tmp_path / "apple_key.p8"
        key_file.write_text("-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----")

        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = True
            mock_settings_obj.apple_client_id = "com.test.app"
            mock_settings_obj.apple_team_id = "team123"
            mock_settings_obj.apple_key_id = "key123"
            mock_settings_obj.apple_private_key_path = str(key_file)
            mock_settings_obj.google_redirect_uri = "http://localhost/auth/google/callback"
            mock_settings_obj.environment = "development"
            mock_settings.return_value = mock_settings_obj

            with patch("core.oauth.AppleOAuthProvider") as mock_provider_cls:
                mock_provider = MagicMock()
                mock_provider_cls.return_value = mock_provider
                mock_provider.generate_pkce_verifier.return_value = "verifier"
                mock_provider.generate_pkce_challenge.return_value = "challenge"
                mock_provider.get_authorization_url.return_value = (
                    "https://appleid.apple.com/auth?state=xyz"
                )

                response = await auth_client.get("/api/v1/auth/oauth/apple")
                assert response.status_code == status.HTTP_200_OK
                assert "authorization_url" in response.json()

    @pytest.mark.asyncio
    async def test_apple_oauth_key_file_not_found(self, auth_client):
        with patch("api.routers.auth_jwt.get_settings") as mock_settings:
            mock_settings_obj = MagicMock()
            mock_settings_obj.auth_oauth_apple_enabled = True
            mock_settings_obj.apple_client_id = "com.test.app"
            mock_settings_obj.apple_team_id = "team123"
            mock_settings_obj.apple_key_id = "key123"
            mock_settings_obj.apple_private_key_path = "/nonexistent/key.p8"
            mock_settings.return_value = mock_settings_obj

            response = await auth_client.get("/api/v1/auth/oauth/apple")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
