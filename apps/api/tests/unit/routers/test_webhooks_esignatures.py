"""
Unit tests for webhook handlers in api/routers/webhooks/esignatures.py.

Tests cover:
- Signature verification (HMAC-SHA256)
- Webhook event processing (sent, viewed, signed, declined, canceled, file_error)
- Envelope ID resolution (primary + metadata fallback)
- Signed document download and storage on completion
- Error handling (invalid JSON, missing envelope ID, unhandled events)
- Audit event logging
"""

import hashlib
import hmac
import json
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.routers.webhooks.esignatures import (
    _verify_hellosign_signature,
)
from api.routers.webhooks.esignatures import (
    router as webhook_router,
)
from db.database import get_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_signature(secret: str, payload: bytes) -> str:
    """Compute a valid HelloSign HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()


def _make_signature_request(
    request_id: str = "sig-1",
    user_id: str = "test-user-123",
    title: str = "Rental Agreement",
    provider: str = "hellosign",
    envelope_id: str = "env-001",
    signers: list[dict] | None = None,
):
    """Create a mock SignatureRequestDB-like object."""
    sr = MagicMock()
    sr.id = request_id
    sr.user_id = user_id
    sr.title = title
    sr.provider = provider
    sr.provider_envelope_id = envelope_id
    sr.document_id = "doc-1"
    sr.status = "pending"
    sr.signers = signers or [
        {
            "email": "signer@example.com",
            "name": "John Signer",
            "role": "tenant",
            "order": 1,
            "status": "pending",
            "signed_at": None,
        }
    ]
    sr.sent_at = None
    sr.viewed_at = None
    sr.completed_at = None
    sr.cancelled_at = None
    sr.error_message = None
    return sr


def _make_webhook_payload(
    event_type: str,
    envelope_id: str = "env-001",
    signer_data: list[dict] | None = None,
    metadata: dict | None = None,
) -> dict:
    """Build a HelloSign webhook payload."""
    payload: dict[str, Any] = {
        "event": {"event_type": event_type},
        "signature_request": {
            "signature_request_id": envelope_id,
        },
    }
    if signer_data:
        payload["signature_request"]["signatures"] = signer_data
    if metadata:
        payload["signature_request"]["metadata"] = metadata
    return payload


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log_event = AsyncMock()
    return logger


@pytest.fixture
def mock_esignature_service():
    svc = MagicMock()
    svc.download_signed_document = AsyncMock(return_value=b"%PDF-1.4 signed content")
    return svc


@pytest.fixture(scope="function")
async def webhook_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing webhook endpoints."""
    test_app = FastAPI()
    test_app.include_router(webhook_router)

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


# ===========================================================================
# Test: _verify_hellosign_signature
# ===========================================================================


class TestVerifyHellosignSignature:
    """Tests for the HMAC-SHA256 signature verification function."""

    def test_returns_true_when_no_secret_configured(self):
        """No webhook secret means verification is skipped (dev mode)."""
        with patch("api.routers.webhooks.esignatures.settings") as mock_settings:
            mock_settings.hellosign_webhook_secret = None
            assert _verify_hellosign_signature(b"payload", "any_sig") is True

    def test_returns_true_when_secret_is_empty_string(self):
        """Empty webhook secret also skips verification."""
        with patch("api.routers.webhooks.esignatures.settings") as mock_settings:
            mock_settings.hellosign_webhook_secret = ""
            assert _verify_hellosign_signature(b"payload", "any_sig") is True

    def test_returns_true_for_valid_signature(self):
        """Correctly computed HMAC signature passes verification."""
        secret = "test-secret-key"
        payload = b'{"event":{"event_type":"test"}}'
        expected_sig = _compute_signature(secret, payload)

        with patch("api.routers.webhooks.esignatures.settings") as mock_settings:
            mock_settings.hellosign_webhook_secret = secret
            assert _verify_hellosign_signature(payload, expected_sig) is True

    def test_returns_false_for_invalid_signature(self):
        """Incorrect signature fails verification."""
        secret = "test-secret-key"
        payload = b'{"event":{"event_type":"test"}}'

        with patch("api.routers.webhooks.esignatures.settings") as mock_settings:
            mock_settings.hellosign_webhook_secret = secret
            assert _verify_hellosign_signature(payload, "invalid_signature") is False

    def test_returns_false_for_tampered_payload(self):
        """Valid signature but different payload fails verification."""
        secret = "test-secret-key"
        original_payload = b'{"event":{"event_type":"test"}}'
        tampered_payload = b'{"event":{"event_type":"tampered"}}'
        sig = _compute_signature(secret, original_payload)

        with patch("api.routers.webhooks.esignatures.settings") as mock_settings:
            mock_settings.hellosign_webhook_secret = secret
            assert _verify_hellosign_signature(tampered_payload, sig) is False

    def test_returns_false_on_exception_during_verification(self):
        """Any exception during HMAC computation returns False."""
        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch(
                "api.routers.webhooks.esignatures.hmac.new",
                side_effect=RuntimeError("HMAC error"),
            ),
        ):
            mock_settings.hellosign_webhook_secret = "secret"
            assert _verify_hellosign_signature(b"payload", "sig") is False


# ===========================================================================
# Test: Webhook signature verification via HTTP
# ===========================================================================


class TestWebhookSignatureVerification:
    """Tests for signature verification in the HTTP endpoint."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_signature(self, webhook_client):
        """Invalid signature returns 401."""
        payload = _make_webhook_payload("signature_request_sent")
        body = json.dumps(payload).encode("utf-8")

        with patch("api.routers.webhooks.esignatures.settings") as mock_settings:
            mock_settings.hellosign_webhook_secret = "my-secret"
            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "HelloSign-Signature": "invalid_sig",
                },
            )

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid webhook signature" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_accepts_valid_signature(self, webhook_client):
        """Valid signature passes verification and processes the webhook."""
        secret = "my-secret"
        payload = _make_webhook_payload("signature_request_sent")
        body = json.dumps(payload).encode("utf-8")
        sig = _compute_signature(secret, body)

        mock_sr = _make_signature_request()

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = secret
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "HelloSign-Signature": sig,
                },
            )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "processed"


# ===========================================================================
# Test: Webhook payload parsing
# ===========================================================================


class TestWebhookPayloadParsing:
    """Tests for JSON parsing and envelope ID resolution."""

    @pytest.mark.asyncio
    async def test_rejects_invalid_json(self, webhook_client):
        """Malformed JSON returns 400."""
        with patch("api.routers.webhooks.esignatures.settings") as mock_settings:
            mock_settings.hellosign_webhook_secret = None
            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=b"not valid json{{{",
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid JSON" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_no_envelope_id_returns_ignored(self, webhook_client):
        """Payload without envelope_id returns 'ignored'."""
        payload = {"event": {"event_type": "signature_request_sent"}}
        body = json.dumps(payload).encode("utf-8")

        with patch("api.routers.webhooks.esignatures.settings") as mock_settings:
            mock_settings.hellosign_webhook_secret = None
            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "no_envelope_id"

    @pytest.mark.asyncio
    async def test_envelope_id_from_metadata_fallback(self, webhook_client):
        """Envelope ID resolved from metadata when primary field is empty."""
        payload = _make_webhook_payload(
            "signature_request_sent",
            envelope_id=None,
            metadata={"request_id": "meta-env-001"},
        )
        # Remove the null envelope ID
        payload["signature_request"].pop("signature_request_id")
        body = json.dumps(payload).encode("utf-8")

        mock_sr = _make_signature_request(envelope_id="meta-env-001")

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "processed"

    @pytest.mark.asyncio
    async def test_signature_request_not_found_returns_ignored(self, webhook_client):
        """Envelope ID exists but no matching DB record returns 'ignored'."""
        payload = _make_webhook_payload("signature_request_sent", envelope_id="env-unknown")
        body = json.dumps(payload).encode("utf-8")

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
        ):
            mock_settings.hellosign_webhook_secret = None

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "not_found"


# ===========================================================================
# Test: Event type handling
# ===========================================================================


class TestWebhookEventTypes:
    """Tests for each supported event type."""

    @pytest.mark.asyncio
    async def test_signature_request_sent(self, webhook_client):
        """'sent' event updates status and sets sent_at."""
        payload = _make_webhook_payload("signature_request_sent")
        body = json.dumps(payload).encode("utf-8")
        mock_sr = _make_signature_request()

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.status == "sent"
        assert mock_sr.sent_at is not None

    @pytest.mark.asyncio
    async def test_signature_request_viewed(self, webhook_client):
        """'viewed' event updates status and sets viewed_at."""
        payload = _make_webhook_payload("signature_request_viewed")
        body = json.dumps(payload).encode("utf-8")
        mock_sr = _make_signature_request()

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.status == "viewed"
        assert mock_sr.viewed_at is not None

    @pytest.mark.asyncio
    async def test_signature_request_signed_all_signers(self, webhook_client):
        """All signers signed -> status becomes 'completed'."""
        signers = [
            {"email": "signer@example.com", "signer_email_address": "signer@example.com"},
        ]
        payload = _make_webhook_payload(
            "signature_request_signed",
            signer_data=signers,
        )
        body = json.dumps(payload).encode("utf-8")

        mock_signers = [{"email": "signer@example.com", "status": "pending", "signed_at": None}]
        mock_sr = _make_signature_request(signers=mock_signers)

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
            patch("api.routers.webhooks.esignatures.get_esignature_service") as mock_get_svc,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()
            mock_get_svc.return_value = None  # skip download

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.status == "completed"
        assert mock_sr.completed_at is not None

    @pytest.mark.asyncio
    async def test_signature_request_signed_partial(self, webhook_client):
        """Not all signers signed -> status becomes 'partially_signed'."""
        signers = [
            {"email": "signer1@example.com", "signer_email_address": "signer1@example.com"},
        ]
        payload = _make_webhook_payload(
            "signature_request_signed",
            signer_data=signers,
        )
        body = json.dumps(payload).encode("utf-8")

        mock_signers = [
            {"email": "signer1@example.com", "status": "pending", "signed_at": None},
            {"email": "signer2@example.com", "status": "pending", "signed_at": None},
        ]
        mock_sr = _make_signature_request(signers=mock_signers)

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.status == "partially_signed"

    @pytest.mark.asyncio
    async def test_signature_request_declined(self, webhook_client):
        """'declined' event updates status and signer status."""
        signers = [
            {"email": "signer@example.com", "signer_email_address": "signer@example.com"},
        ]
        payload = _make_webhook_payload(
            "signature_request_declined",
            signer_data=signers,
        )
        body = json.dumps(payload).encode("utf-8")

        mock_signers = [{"email": "signer@example.com", "status": "pending"}]
        mock_sr = _make_signature_request(signers=mock_signers)

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.status == "declined"
        assert mock_sr.signers[0]["status"] == "declined"

    @pytest.mark.asyncio
    async def test_signature_request_canceled(self, webhook_client):
        """'canceled' event updates status and sets cancelled_at."""
        payload = _make_webhook_payload("signature_request_canceled")
        body = json.dumps(payload).encode("utf-8")
        mock_sr = _make_signature_request()

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.status == "cancelled"
        assert mock_sr.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_file_error_event(self, webhook_client):
        """'file_error' event sets error_message on the request."""
        payload = _make_webhook_payload("file_error")
        payload["error"] = "Document processing failed"
        body = json.dumps(payload).encode("utf-8")
        mock_sr = _make_signature_request()

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.error_message == "Document processing failed"

    @pytest.mark.asyncio
    async def test_file_error_event_with_default_message(self, webhook_client):
        """file_error without 'error' field uses 'Unknown error'."""
        payload = _make_webhook_payload("file_error")
        body = json.dumps(payload).encode("utf-8")
        mock_sr = _make_signature_request()

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.error_message == "Unknown error"

    @pytest.mark.asyncio
    async def test_unhandled_event_type(self, webhook_client):
        """Unknown event type returns 'ignored' with 'unhandled_event'."""
        payload = _make_webhook_payload("some_unknown_event")
        body = json.dumps(payload).encode("utf-8")
        mock_sr = _make_signature_request()

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
        ):
            mock_settings.hellosign_webhook_secret = None

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == "ignored"
        assert data["reason"] == "unhandled_event"

    @pytest.mark.asyncio
    async def test_event_type_from_top_level(self, webhook_client):
        """Event type read from top-level 'event_type' when nested is absent."""
        payload = {
            "event_type": "signature_request_sent",
            "signature_request": {"signature_request_id": "env-001"},
        }
        body = json.dumps(payload).encode("utf-8")
        mock_sr = _make_signature_request()

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.status == "sent"


# ===========================================================================
# Test: Signed document download on completion
# ===========================================================================


class TestSignedDocumentDownload:
    """Tests for downloading and storing signed documents on completion."""

    @pytest.mark.asyncio
    async def test_completed_triggers_document_download(
        self, webhook_client, mock_esignature_service
    ):
        """Completed status triggers download_and_store_signed_document."""
        signers = [
            {"email": "signer@example.com", "signer_email_address": "signer@example.com"},
        ]
        payload = _make_webhook_payload(
            "signature_request_signed",
            signer_data=signers,
        )
        body = json.dumps(payload).encode("utf-8")

        mock_signers = [{"email": "signer@example.com", "status": "pending", "signed_at": None}]
        mock_sr = _make_signature_request(signers=mock_signers)

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
            patch("api.routers.webhooks.esignatures.get_esignature_service") as mock_get_svc,
            patch(
                "api.routers.webhooks.esignatures._download_and_store_signed_document",
                new_callable=AsyncMock,
            ) as mock_download,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()
            mock_get_svc.return_value = mock_esignature_service

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.status == "completed"
        mock_download.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_failure_does_not_fail_webhook(
        self, webhook_client, mock_esignature_service
    ):
        """Download failure is logged but webhook still returns 'processed'."""
        signers = [
            {"email": "signer@example.com", "signer_email_address": "signer@example.com"},
        ]
        payload = _make_webhook_payload(
            "signature_request_signed",
            signer_data=signers,
        )
        body = json.dumps(payload).encode("utf-8")

        mock_signers = [{"email": "signer@example.com", "status": "pending", "signed_at": None}]
        mock_sr = _make_signature_request(signers=mock_signers)

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
            patch("api.routers.webhooks.esignatures.get_esignature_service") as mock_get_svc,
            patch(
                "api.routers.webhooks.esignatures._download_and_store_signed_document",
                new_callable=AsyncMock,
                side_effect=RuntimeError("Storage failure"),
            ),
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()
            mock_get_svc.return_value = mock_esignature_service

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        # Webhook still succeeds despite download failure
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "processed"

    @pytest.mark.asyncio
    async def test_no_service_skips_download(self, webhook_client):
        """No esignature service means download is skipped entirely."""
        signers = [
            {"email": "signer@example.com", "signer_email_address": "signer@example.com"},
        ]
        payload = _make_webhook_payload(
            "signature_request_signed",
            signer_data=signers,
        )
        body = json.dumps(payload).encode("utf-8")

        mock_signers = [{"email": "signer@example.com", "status": "pending", "signed_at": None}]
        mock_sr = _make_signature_request(signers=mock_signers)

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.webhooks.esignatures.get_audit_logger") as mock_get_logger,
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
            patch(
                "api.routers.webhooks.esignatures.get_esignature_service",
                return_value=None,
            ),
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"
            mock_get_logger.return_value.log_event = AsyncMock()

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_sr.status == "completed"


# ===========================================================================
# Test: _download_and_store_signed_document (unit-level)
# ===========================================================================


class TestDownloadAndStoreSignedDocument:
    """Tests for the _download_and_store_signed_document helper."""

    @pytest.mark.asyncio
    async def test_downloads_and_stores_document(self, tmp_path):
        """Successfully downloads PDF and stores it in user directory."""
        from api.routers.webhooks.esignatures import _download_and_store_signed_document

        mock_session = MagicMock()
        mock_sr = MagicMock()
        mock_sr.user_id = "user-1"
        mock_sr.title = "Agreement"
        mock_sr.provider_envelope_id = "env-001"
        mock_sr.id = "sig-1"
        mock_sr.document_id = "doc-1"

        mock_svc = MagicMock()
        mock_svc.download_signed_document = AsyncMock(return_value=b"%PDF-1.4 content")

        mock_storage = MagicMock()
        mock_storage.user_dir = tmp_path

        mock_signed_doc_repo = MagicMock()
        mock_signed_doc_repo.create = AsyncMock()

        with (
            patch(
                "services.document_storage.get_document_storage",
                return_value=mock_storage,
            ),
            patch(
                "api.routers.webhooks.esignatures.SignedDocumentRepository",
                return_value=mock_signed_doc_repo,
            ),
        ):
            await _download_and_store_signed_document(mock_session, mock_sr, mock_svc)

        mock_svc.download_signed_document.assert_called_once_with("env-001")
        mock_signed_doc_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_on_download_failure(self, tmp_path):
        """Exception during download propagates."""
        from api.routers.webhooks.esignatures import _download_and_store_signed_document

        mock_session = MagicMock()
        mock_sr = MagicMock()
        mock_sr.user_id = "user-1"
        mock_sr.title = "Agreement"
        mock_sr.provider_envelope_id = "env-001"

        mock_svc = MagicMock()
        mock_svc.download_signed_document = AsyncMock(side_effect=RuntimeError("Provider error"))

        mock_storage = MagicMock()
        mock_storage.user_dir = tmp_path

        with (
            patch(
                "services.document_storage.get_document_storage",
                return_value=mock_storage,
            ),
        ):
            with pytest.raises(RuntimeError, match="Provider error"):
                await _download_and_store_signed_document(mock_session, mock_sr, mock_svc)


# ===========================================================================
# Test: Audit logging
# ===========================================================================


class TestWebhookAuditLogging:
    """Tests for audit event logging on webhook processing."""

    @pytest.mark.asyncio
    async def test_audit_event_logged_on_processed_event(self, webhook_client, mock_audit_logger):
        """Processed events log an audit event."""
        payload = _make_webhook_payload("signature_request_sent")
        body = json.dumps(payload).encode("utf-8")
        mock_sr = _make_signature_request()

        with (
            patch("api.routers.webhooks.esignatures.settings") as mock_settings,
            patch("api.routers.webhooks.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch(
                "api.routers.webhooks.esignatures.get_audit_logger",
                return_value=mock_audit_logger,
            ),
            patch("api.routers.webhooks.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.webhooks.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.webhooks.esignatures.AuditLevel") as mock_al,
        ):
            mock_settings.hellosign_webhook_secret = None
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_al.INFO = "info"

            mock_repo = MagicMock()
            mock_repo.get_by_provider_envelope_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        mock_audit_logger.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_audit_for_ignored_events(self, webhook_client, mock_audit_logger):
        """Ignored events (no envelope ID) do not log audit events."""
        payload = {"event": {"event_type": "signature_request_sent"}}
        body = json.dumps(payload).encode("utf-8")

        with patch("api.routers.webhooks.esignatures.settings") as mock_settings:
            mock_settings.hellosign_webhook_secret = None
            resp = await webhook_client.post(
                "/webhooks/esignatures/hellosign",
                content=body,
                headers={"Content-Type": "application/json"},
            )

        assert resp.status_code == status.HTTP_200_OK
        mock_audit_logger.log_event.assert_not_called()
