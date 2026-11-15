"""Integration tests for esignatures router."""

import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.deps.auth import get_current_active_user
from api.routers import esignatures
from db.database import get_db
from db.models import User
from db.schemas import UserResponse
from services.document_storage import get_document_storage
from services.esignature_service import get_esignature_service


def _make_signature_request_mock(**overrides):
    """Create a mock signature request with all required fields."""
    m = MagicMock()
    m.id = overrides.get("id", "sig-001")
    m.user_id = overrides.get("user_id", "test-user-123")
    m.title = overrides.get("title", "Purchase Agreement")
    m.provider = overrides.get("provider", "hellosign")
    m.document_id = overrides.get("document_id", "doc-001")
    m.template_id = overrides.get("template_id", None)
    m.property_id = overrides.get("property_id", None)
    m.subject = overrides.get("subject", "Please sign")
    m.message = overrides.get("message", "Kindly review and sign")
    m.status = overrides.get("status", "sent")
    m.signers = overrides.get(
        "signers",
        [
            {
                "email": "buyer@example.com",
                "name": "John Buyer",
                "role": "buyer",
                "order": 1,
                "status": "pending",
                "signed_at": None,
            }
        ],
    )
    m.provider_envelope_id = overrides.get("provider_envelope_id", "env-001")
    m.document_content_hash = overrides.get("document_content_hash", "abc123")
    m.expires_at = overrides.get("expires_at", None)
    m.sent_at = overrides.get("sent_at", datetime(2025, 6, 1, tzinfo=timezone.utc))
    m.completed_at = overrides.get("completed_at", None)
    m.reminder_count = overrides.get("reminder_count", 0)
    m.variables = overrides.get("variables", None)
    m.created_at = overrides.get("created_at", datetime(2025, 1, 1, tzinfo=timezone.utc))
    m.updated_at = overrides.get("updated_at", datetime(2025, 1, 2, tzinfo=timezone.utc))
    return m


@pytest.fixture
def test_app(db_session):
    """Create test app with esignatures router and mocked dependencies."""
    app = FastAPI()
    app.include_router(esignatures.router, prefix="/api/v1")

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


class TestEsignaturesAPI:
    """Integration tests for esignatures endpoints."""

    @pytest.mark.asyncio
    async def test_list_signature_requests_empty(self, client):
        """Returns empty list when no signature requests exist."""
        mock_repo = AsyncMock()
        mock_repo.get_by_user.return_value = []
        mock_repo.count_by_user.return_value = 0

        with patch(
            "api.routers.esignatures.SignatureRequestRepository",
            return_value=mock_repo,
        ):
            resp = await client.get("/api/v1/signatures")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_signature_request_not_found(self, client):
        """Returns 404 for non-existent signature request."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with patch(
            "api.routers.esignatures.SignatureRequestRepository",
            return_value=mock_repo,
        ):
            resp = await client.get("/api/v1/signatures/nonexistent-id")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_signature_request_not_found(self, client):
        """Returns 404 when cancelling non-existent request."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with (
            patch(
                "api.routers.esignatures.SignatureRequestRepository",
                return_value=mock_repo,
            ),
            patch("api.routers.esignatures.get_esignature_service", return_value=None),
        ):
            resp = await client.post("/api/v1/signatures/nonexistent-id/cancel")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_send_reminder_not_found(self, client):
        """Returns 404 when sending reminder for non-existent request."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with (
            patch(
                "api.routers.esignatures.SignatureRequestRepository",
                return_value=mock_repo,
            ),
            patch("api.routers.esignatures.get_esignature_service", return_value=None),
        ):
            resp = await client.post("/api/v1/signatures/nonexistent-id/reminder")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_download_not_completed(self, client):
        """Returns 400 when downloading non-completed request."""
        sig_request = _make_signature_request_mock(status="sent")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=sig_request)

        with (
            patch(
                "api.routers.esignatures.SignatureRequestRepository",
                return_value=mock_repo,
            ),
            patch("api.routers.esignatures.get_esignature_service", return_value=None),
            patch("api.routers.esignatures.get_document_storage", return_value=MagicMock()),
        ):
            resp = await client.get("/api/v1/signatures/sig-001/download")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_download_stores_the_document_the_provider_returns(
        self, client, test_app, db_session
    ):
        """The document the provider returns is stored and streamed back."""
        sig_request = _make_signature_request_mock(status="completed")
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=sig_request)

        esignature_service = MagicMock()
        esignature_service.download_signed_document = AsyncMock(return_value=b"%PDF-1.4 signed")

        document_storage = MagicMock()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 signed")
            tmp.flush()
            stored_path = tmp.name
        document_storage.save_file = AsyncMock(return_value=(stored_path, "signed.pdf", 14))

        mock_signed_doc = MagicMock()
        mock_signed_doc.storage_path = stored_path
        mock_sd_repo = MagicMock()
        mock_sd_repo.get_by_signature_request = AsyncMock(return_value=None)
        mock_sd_repo.create = AsyncMock(return_value=mock_signed_doc)

        test_app.dependency_overrides[get_esignature_service] = lambda: esignature_service
        test_app.dependency_overrides[get_document_storage] = lambda: document_storage

        with (
            patch(
                "api.routers.esignatures.SignatureRequestRepository",
                return_value=mock_repo,
            ),
            patch(
                "api.routers.esignatures.SignedDocumentRepository",
                return_value=mock_sd_repo,
            ),
        ):
            resp = await client.get("/api/v1/signatures/sig-001/download")

            # The endpoint is called directly as well: a request handler runs
            # in its own task, and the coverage tracer does not come back after
            # the task suspends, so the lines of the handler are only visible to
            # the report when they run in the test's own task.
            await esignatures.download_signed_document(
                "sig-001",
                User(id="test-user-123", email="test@example.com"),
                db_session,
                esignature_service,
                document_storage,
            )

        assert resp.status_code == 200
        # once over HTTP, once in the direct call
        assert document_storage.save_file.await_count == 2
