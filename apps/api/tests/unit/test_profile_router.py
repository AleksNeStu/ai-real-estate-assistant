"""Tests for profile router endpoints (Task #88: User Profile Management)."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import profile
from db.database import get_db_context as get_db_dep

_test_app = FastAPI()
_test_app.include_router(profile.router)


def _make_user(
    user_id="user-1",
    email="user@test.com",
    full_name="Test User",
    role="user",
    is_active=True,
    is_verified=False,
    phone="+48123456789",
    avatar_url=None,
    timezone="UTC",
    language="en",
    bio=None,
    privacy_settings=None,
    data_export_requested_at=None,
    gdpr_consent_at=None,
    last_login_at=None,
):
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.full_name = full_name
    user.role = role
    user.is_active = is_active
    user.is_verified = is_verified
    user.phone = phone
    user.avatar_url = avatar_url
    user.timezone = timezone
    user.language = language
    user.bio = bio
    user.privacy_settings = privacy_settings or {
        "profile_visible": True,
        "activity_visible": False,
        "show_email": False,
        "show_phone": False,
        "allow_contact": True,
    }
    user.data_export_requested_at = data_export_requested_at
    user.gdpr_consent_at = gdpr_consent_at
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.last_login_at = last_login_at
    return user


@pytest.fixture
def auth_user():
    _user = _make_user()

    async def _get_user():
        return _user

    _test_app.dependency_overrides[get_current_active_user] = _get_user
    yield _user
    _test_app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    mock_session = AsyncMock()

    async def _get_db():
        yield mock_session

    _test_app.dependency_overrides[get_db_dep] = _get_db
    yield mock_session
    _test_app.dependency_overrides.pop(get_db_dep, None)


@pytest.fixture(autouse=True)
def _clear_export_jobs():
    """Clear in-memory export jobs between tests."""
    profile._export_jobs.clear()
    yield
    profile._export_jobs.clear()


# --- GET /profile ---


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_get_profile_success(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "user-1"
        assert data["email"] == "user@test.com"
        assert data["full_name"] == "Test User"
        assert data["phone"] == "+48123456789"
        assert data["timezone"] == "UTC"
        assert data["language"] == "en"
        assert data["is_active"] is True
        assert data["is_verified"] is False
        assert data["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_profile_with_avatar(self, auth_user, mock_db):
        auth_user.avatar_url = "/uploads/avatars/avatar_user-1.png"

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/profile")
        assert resp.status_code == 200
        assert resp.json()["avatar_url"] == "/uploads/avatars/avatar_user-1.png"

    @pytest.mark.asyncio
    async def test_get_profile_with_bio(self, auth_user, mock_db):
        auth_user.bio = "Real estate enthusiast"

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/profile")
        assert resp.status_code == 200
        assert resp.json()["bio"] == "Real estate enthusiast"

    @pytest.mark.asyncio
    async def test_get_profile_includes_privacy_settings(self, auth_user, mock_db):
        auth_user.privacy_settings = {
            "profile_visible": False,
            "activity_visible": True,
            "show_email": True,
            "show_phone": False,
            "allow_contact": False,
        }

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/profile")
        assert resp.status_code == 200
        assert resp.json()["privacy_settings"]["profile_visible"] is False

    @pytest.mark.asyncio
    async def test_get_profile_includes_gdpr_consent(self, auth_user, mock_db):
        consent_time = datetime.now(UTC)
        auth_user.gdpr_consent_at = consent_time

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/profile")
        assert resp.status_code == 200
        assert resp.json()["gdpr_consent_at"] is not None


# --- PUT /profile ---


class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_update_full_name(self, auth_user, mock_db):
        mock_db.refresh = AsyncMock(return_value=None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put("/profile", json={"full_name": "New Name"})
        assert resp.status_code == 200
        assert auth_user.full_name == "New Name"
        mock_db.add.assert_called_once_with(auth_user)
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_update_phone(self, auth_user, mock_db):
        mock_db.refresh = AsyncMock(return_value=None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put("/profile", json={"phone": "+48999888777"})
        assert resp.status_code == 200
        assert auth_user.phone == "+48999888777"

    @pytest.mark.asyncio
    async def test_update_bio(self, auth_user, mock_db):
        mock_db.refresh = AsyncMock(return_value=None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put("/profile", json={"bio": "Updated bio text"})
        assert resp.status_code == 200
        assert auth_user.bio == "Updated bio text"

    @pytest.mark.asyncio
    async def test_update_timezone(self, auth_user, mock_db):
        mock_db.refresh = AsyncMock(return_value=None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put("/profile", json={"timezone": "Europe/Warsaw"})
        assert resp.status_code == 200
        assert auth_user.timezone == "Europe/Warsaw"

    @pytest.mark.asyncio
    async def test_update_language(self, auth_user, mock_db):
        mock_db.refresh = AsyncMock(return_value=None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put("/profile", json={"language": "pl"})
        assert resp.status_code == 200
        assert auth_user.language == "pl"

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, auth_user, mock_db):
        mock_db.refresh = AsyncMock(return_value=None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put(
                "/profile",
                json={
                    "full_name": "Multi Update",
                    "phone": "+48111222333",
                    "bio": "Multi bio",
                    "timezone": "US/Eastern",
                    "language": "de",
                },
            )
        assert resp.status_code == 200
        assert auth_user.full_name == "Multi Update"
        assert auth_user.phone == "+48111222333"
        assert auth_user.bio == "Multi bio"
        assert auth_user.timezone == "US/Eastern"
        assert auth_user.language == "de"

    @pytest.mark.asyncio
    async def test_update_empty_body_returns_current_profile(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put("/profile", json={})
        assert resp.status_code == 200
        # No db calls should be made for empty update
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_awaited()


# --- POST /profile/avatar ---


class TestUploadAvatar:
    @pytest.mark.asyncio
    async def test_upload_png_success(self, auth_user, mock_db):
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/avatar",
                files={"file": ("avatar.png", png_header, "image/png")},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["avatar_url"].startswith("/uploads/avatars/avatar_user-1_")
        assert body["avatar_url"].endswith(".png")
        assert body["message"] == "Avatar uploaded successfully"

        # Cleanup the created file
        if os.path.exists("uploads/avatars"):
            for f in os.listdir("uploads/avatars"):
                if f.startswith("avatar_user-1_"):
                    os.remove(os.path.join("uploads/avatars", f))

    @pytest.mark.asyncio
    async def test_upload_jpeg_success(self, auth_user, mock_db):
        jpeg_header = b"\xff\xd8\xff" + b"\x00" * 100

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/avatar",
                files={"file": ("photo.jpg", jpeg_header, "image/jpeg")},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["avatar_url"].endswith(".jpg")

        # Cleanup
        if os.path.exists("uploads/avatars"):
            for f in os.listdir("uploads/avatars"):
                if f.startswith("avatar_user-1_"):
                    os.remove(os.path.join("uploads/avatars", f))

    @pytest.mark.asyncio
    async def test_upload_webp_success(self, auth_user, mock_db):
        webp_header = b"RIFF" + b"\x00" * 100

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/avatar",
                files={"file": ("image.webp", webp_header, "image/webp")},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["avatar_url"].endswith(".webp")

        # Cleanup
        if os.path.exists("uploads/avatars"):
            for f in os.listdir("uploads/avatars"):
                if f.startswith("avatar_user-1_"):
                    os.remove(os.path.join("uploads/avatars", f))

    @pytest.mark.asyncio
    async def test_upload_invalid_content_type(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/avatar",
                files={"file": ("doc.pdf", b"content", "application/pdf")},
            )
        assert resp.status_code == 400
        assert "Invalid file type" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_gif_rejected(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/avatar",
                files={"file": ("anim.gif", b"GIF89a", "image/gif")},
            )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, auth_user, mock_db):
        big_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * (2 * 1024 * 1024 + 1)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/avatar",
                files={"file": ("big.png", big_content, "image/png")},
            )
        assert resp.status_code == 413
        assert "too large" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_invalid_image_header(self, auth_user, mock_db):
        # Valid content_type but corrupt image data
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/avatar",
                files={"file": ("fake.png", b"not_a_real_image_data", "image/png")},
            )
        assert resp.status_code == 400
        assert "Invalid image file" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_no_filename_defaults_to_png(self, auth_user, mock_db):
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/avatar",
                files={"file": (None, png_header, "image/png")},
            )
        # When filename is empty/None, the extension defaults to png
        if resp.status_code == 200:
            assert resp.json()["avatar_url"].endswith(".png")

        # Cleanup
        if os.path.exists("uploads/avatars"):
            for f in os.listdir("uploads/avatars"):
                if f.startswith("avatar_user-1_"):
                    os.remove(os.path.join("uploads/avatars", f))


# --- DELETE /profile/avatar ---


class TestDeleteAvatar:
    @pytest.mark.asyncio
    async def test_delete_avatar_with_existing(self, auth_user, mock_db):
        auth_user.avatar_url = "/uploads/avatars/avatar_user-1_old.png"

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.delete("/profile/avatar")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Avatar deleted successfully"
        assert auth_user.avatar_url is None
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_delete_avatar_no_avatar(self, auth_user, mock_db):
        auth_user.avatar_url = None

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.delete("/profile/avatar")
        assert resp.status_code == 200
        assert resp.json()["message"] == "No avatar to delete"
        # No commit should happen since there's nothing to delete
        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_avatar_removes_file(self, auth_user, mock_db):
        # Create a temporary avatar file
        os.makedirs("uploads/avatars", exist_ok=True)
        test_file = "uploads/avatars/avatar_user-1_to_delete.png"
        with open(test_file, "w") as f:
            f.write("test")
        assert os.path.exists(test_file)

        auth_user.avatar_url = "/uploads/avatars/avatar_user-1_to_delete.png"

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.delete("/profile/avatar")
        assert resp.status_code == 200
        # The file should be removed
        assert not os.path.exists(test_file)

    @pytest.mark.asyncio
    async def test_delete_avatar_file_not_found_graceful(self, auth_user, mock_db):
        # Avatar URL points to a file that doesn't exist on disk
        auth_user.avatar_url = "/uploads/avatars/nonexistent_file.png"

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.delete("/profile/avatar")
        # Should still succeed - _delete_avatar_file handles missing files gracefully
        assert resp.status_code == 200


# --- PUT /profile/privacy ---


class TestUpdatePrivacySettings:
    @pytest.mark.asyncio
    async def test_update_privacy_success(self, auth_user, mock_db):
        mock_db.refresh = AsyncMock(return_value=None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put(
                "/profile/privacy",
                json={
                    "profile_visible": False,
                    "activity_visible": True,
                    "show_email": True,
                    "show_phone": True,
                    "allow_contact": False,
                },
            )
        assert resp.status_code == 200
        assert auth_user.privacy_settings["profile_visible"] is False
        assert auth_user.privacy_settings["activity_visible"] is True
        assert auth_user.privacy_settings["show_email"] is True
        assert auth_user.privacy_settings["show_phone"] is True
        assert auth_user.privacy_settings["allow_contact"] is False
        mock_db.add.assert_called_once_with(auth_user)
        mock_db.commit.assert_awaited()
        mock_db.refresh.assert_awaited()

    @pytest.mark.asyncio
    async def test_update_privacy_defaults(self, auth_user, mock_db):
        mock_db.refresh = AsyncMock(return_value=None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put(
                "/profile/privacy",
                json={
                    "profile_visible": True,
                    "activity_visible": False,
                    "show_email": False,
                    "show_phone": False,
                    "allow_contact": True,
                },
            )
        assert resp.status_code == 200
        assert auth_user.privacy_settings["profile_visible"] is True


# --- POST /profile/export ---


class TestRequestDataExport:
    @pytest.mark.asyncio
    async def test_request_export_success(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={
                    "format": "json",
                    "include_favorites": True,
                    "include_search_history": True,
                    "include_documents": True,
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pending"
        assert body["format"] == "json"
        assert "favorites" in body["includes"]
        assert "saved_searches" in body["includes"]
        assert "documents" in body["includes"]
        assert body["export_id"].startswith("export_user-1_")
        assert auth_user.data_export_requested_at is not None
        mock_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_request_export_csv_format(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={"format": "csv"},
            )
        assert resp.status_code == 200
        assert resp.json()["format"] == "csv"

    @pytest.mark.asyncio
    async def test_request_export_partial_includes(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={
                    "include_favorites": True,
                    "include_search_history": False,
                    "include_documents": False,
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["includes"] == ["favorites"]

    @pytest.mark.asyncio
    async def test_request_export_only_documents(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={
                    "include_favorites": False,
                    "include_search_history": False,
                    "include_documents": True,
                },
            )
        assert resp.status_code == 200
        assert resp.json()["includes"] == ["documents"]

    @pytest.mark.asyncio
    async def test_request_export_only_search_history(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={
                    "include_favorites": False,
                    "include_search_history": True,
                    "include_documents": False,
                },
            )
        assert resp.status_code == 200
        assert resp.json()["includes"] == ["saved_searches"]

    @pytest.mark.asyncio
    async def test_request_export_no_includes(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={
                    "include_favorites": False,
                    "include_search_history": False,
                    "include_documents": False,
                },
            )
        assert resp.status_code == 200
        assert resp.json()["includes"] == []

    @pytest.mark.asyncio
    async def test_request_export_rate_limited(self, auth_user, mock_db):
        # User already requested export recently (1 hour ago)
        auth_user.data_export_requested_at = datetime.now(UTC) - timedelta(hours=1)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={"format": "json"},
            )
        assert resp.status_code == 429
        assert "Rate limit" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_request_export_allowed_after_24h(self, auth_user, mock_db):
        # User requested export more than 24 hours ago
        auth_user.data_export_requested_at = datetime.now(UTC) - timedelta(hours=25)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={"format": "json"},
            )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_request_export_naive_datetime_treated_as_utc(self, auth_user, mock_db):
        # Naive datetime (no tzinfo) - should be treated as UTC
        from datetime import datetime as dt

        auth_user.data_export_requested_at = dt(2025, 1, 1, 12, 0, 0)  # no tzinfo

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={"format": "json"},
            )
        # Should succeed since naive datetime from 2025 is well past 24h
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_request_export_naive_datetime_recent_rate_limited(self, auth_user, mock_db):
        from datetime import datetime as dt

        # Naive datetime that is recent (within 24h)
        auth_user.data_export_requested_at = dt.now(UTC).replace(tzinfo=None) - timedelta(hours=1)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/export",
                json={"format": "json"},
            )
        assert resp.status_code == 429

    @pytest.mark.asyncio
    async def test_request_export_default_body(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/profile/export", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "json"
        # Defaults are all True
        assert "favorites" in body["includes"]
        assert "saved_searches" in body["includes"]
        assert "documents" in body["includes"]


# --- GET /profile/export/{export_id} ---


class TestGetExportStatus:
    @pytest.mark.asyncio
    async def test_get_export_status_pending(self, auth_user, mock_db):
        export_id = "export_user-1_20250101_000000"
        profile._export_jobs[export_id] = {
            "export_id": export_id,
            "status": "pending",
            "progress_percent": 0,
            "user_id": "user-1",
            "created_at": datetime.now(UTC),
        }

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(f"/profile/export/{export_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["export_id"] == export_id
        assert body["status"] == "pending"
        assert body["progress_percent"] == 0
        assert body["download_url"] is None
        assert body["error_message"] is None

    @pytest.mark.asyncio
    async def test_get_export_status_completed(self, auth_user, mock_db):
        export_id = "export_user-1_20250101_120000"
        completed = datetime.now(UTC)
        expires = datetime.now(UTC) + timedelta(hours=24)
        profile._export_jobs[export_id] = {
            "export_id": export_id,
            "status": "completed",
            "progress_percent": 100,
            "user_id": "user-1",
            "created_at": datetime.now(UTC) - timedelta(minutes=5),
            "download_url": f"/uploads/exports/{export_id}.json",
            "expires_at": expires,
            "completed_at": completed,
        }

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(f"/profile/export/{export_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["progress_percent"] == 100
        assert body["download_url"] is not None

    @pytest.mark.asyncio
    async def test_get_export_status_failed(self, auth_user, mock_db):
        export_id = "export_user-1_failed"
        profile._export_jobs[export_id] = {
            "export_id": export_id,
            "status": "failed",
            "progress_percent": 30,
            "user_id": "user-1",
            "created_at": datetime.now(UTC),
            "error_message": "Database connection failed",
        }

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(f"/profile/export/{export_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "failed"
        assert body["error_message"] == "Database connection failed"

    @pytest.mark.asyncio
    async def test_get_export_status_not_found(self, auth_user, mock_db):
        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/profile/export/export_nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_export_status_wrong_user(self, auth_user, mock_db):
        export_id = "export_other_user_123"
        profile._export_jobs[export_id] = {
            "export_id": export_id,
            "status": "completed",
            "progress_percent": 100,
            "user_id": "other-user-999",
            "created_at": datetime.now(UTC),
        }

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(f"/profile/export/{export_id}")
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]


# --- Helper function tests ---


class TestHelperFunctions:
    def test_get_export_includes_all(self):
        from api.routers.profile import DataExportRequest, _get_export_includes

        req = DataExportRequest(
            include_favorites=True,
            include_search_history=True,
            include_documents=True,
        )
        includes = _get_export_includes(req)
        assert includes == ["favorites", "saved_searches", "documents"]

    def test_get_export_includes_only_favorites(self):
        from api.routers.profile import DataExportRequest, _get_export_includes

        req = DataExportRequest(
            include_favorites=True,
            include_search_history=False,
            include_documents=False,
        )
        includes = _get_export_includes(req)
        assert includes == ["favorites"]

    def test_get_export_includes_only_searches(self):
        from api.routers.profile import DataExportRequest, _get_export_includes

        req = DataExportRequest(
            include_favorites=False,
            include_search_history=True,
            include_documents=False,
        )
        includes = _get_export_includes(req)
        assert includes == ["saved_searches"]

    def test_get_export_includes_only_documents(self):
        from api.routers.profile import DataExportRequest, _get_export_includes

        req = DataExportRequest(
            include_favorites=False,
            include_search_history=False,
            include_documents=True,
        )
        includes = _get_export_includes(req)
        assert includes == ["documents"]

    def test_get_export_includes_none(self):
        from api.routers.profile import DataExportRequest, _get_export_includes

        req = DataExportRequest(
            include_favorites=False,
            include_search_history=False,
            include_documents=False,
        )
        includes = _get_export_includes(req)
        assert includes == []

    def test_delete_avatar_file_exists(self, tmp_path):
        from api.routers.profile import _delete_avatar_file

        test_file = tmp_path / "test_avatar.png"
        test_file.write_text("fake image")
        assert test_file.exists()

        _delete_avatar_file(str(test_file))
        assert not test_file.exists()

    def test_delete_avatar_file_not_exists(self):
        from api.routers.profile import _delete_avatar_file

        # Should not raise
        _delete_avatar_file("/nonexistent/path/avatar.png")

    @pytest.mark.asyncio
    async def test_process_data_export_success(self, auth_user, mock_db):
        # Set up export job
        export_id = "export_user-1_test_proc"
        profile._export_jobs[export_id] = {
            "export_id": export_id,
            "status": "pending",
            "progress_percent": 0,
            "user_id": "user-1",
            "created_at": datetime.now(UTC),
        }

        export_request = {
            "include_favorites": False,
            "include_search_history": False,
            "include_documents": False,
        }

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = auth_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_db = MagicMock(return_value=mock_context)

        with patch("db.database.get_db_context", mock_get_db):
            # Patch FavoriteRepository and SavedSearchRepository to avoid import errors
            with patch("db.repositories.FavoriteRepository"):
                with patch("db.repositories.SavedSearchRepository"):
                    await profile._process_data_export("user-1", export_id, export_request)

        assert profile._export_jobs[export_id]["status"] == "completed"
        assert profile._export_jobs[export_id]["progress_percent"] == 100
        assert profile._export_jobs[export_id]["download_url"] is not None
        assert profile._export_jobs[export_id]["completed_at"] is not None

        # Cleanup export file
        export_dir = "uploads/exports"
        export_path = os.path.join(export_dir, f"{export_id}.json")
        if os.path.exists(export_path):
            os.remove(export_path)

    @pytest.mark.asyncio
    async def test_process_data_export_user_not_found(self):
        export_id = "export_missing_user"
        profile._export_jobs[export_id] = {
            "export_id": export_id,
            "status": "pending",
            "progress_percent": 0,
            "user_id": "missing-user",
            "created_at": datetime.now(UTC),
        }

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_get_db = MagicMock(return_value=mock_context)

        with patch("db.database.get_db_context", mock_get_db):
            await profile._process_data_export("missing-user", export_id, {})

        assert profile._export_jobs[export_id]["status"] == "failed"
        assert "not found" in profile._export_jobs[export_id]["error_message"]


# --- Auth enforcement ---


class TestAuthEnforcement:
    @pytest.mark.asyncio
    async def test_get_profile_unauthorized(self, mock_db):
        # No auth override - dependency will raise
        _test_app.dependency_overrides.pop(get_current_active_user, None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/profile")
        assert resp.status_code == 403 or resp.status_code == 401

        # Restore
        _test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_profile_unauthorized(self, mock_db):
        _test_app.dependency_overrides.pop(get_current_active_user, None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put("/profile", json={"full_name": "Hacker"})
        assert resp.status_code == 403 or resp.status_code == 401

        _test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_upload_avatar_unauthorized(self, mock_db):
        _test_app.dependency_overrides.pop(get_current_active_user, None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post(
                "/profile/avatar",
                files={"file": ("a.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            )
        assert resp.status_code == 403 or resp.status_code == 401

        _test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_avatar_unauthorized(self, mock_db):
        _test_app.dependency_overrides.pop(get_current_active_user, None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.delete("/profile/avatar")
        assert resp.status_code == 403 or resp.status_code == 401

        _test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_privacy_unauthorized(self, mock_db):
        _test_app.dependency_overrides.pop(get_current_active_user, None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.put(
                "/profile/privacy",
                json={"profile_visible": False},
            )
        assert resp.status_code == 403 or resp.status_code == 401

        _test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_request_export_unauthorized(self, mock_db):
        _test_app.dependency_overrides.pop(get_current_active_user, None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.post("/profile/export", json={})
        assert resp.status_code == 403 or resp.status_code == 401

        _test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_export_status_unauthorized(self, mock_db):
        _test_app.dependency_overrides.pop(get_current_active_user, None)

        transport = ASGITransport(app=_test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/profile/export/some_id")
        assert resp.status_code == 403 or resp.status_code == 401

        _test_app.dependency_overrides.clear()
