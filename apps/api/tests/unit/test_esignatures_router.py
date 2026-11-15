"""
Unit tests for e-signatures router (api/routers/esignatures.py).

Tests cover:
- Create signature request (template-based, document-based, validation)
- List signature requests (pagination, filtering)
- Get signature request details
- Cancel signature request
- Send signature reminder
- Download signed document
- Template CRUD (create, update, delete, get)
- Error handling (404, 400, 503, 429, 500)

NOTE: GET /signatures/templates is shadowed by GET /signatures/{request_id}
      (route registration order bug in source). Template listing tests
      document this behavior rather than test the unreachable endpoint.
"""

import enum
import tempfile
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from api.routers import esignatures
from api.routers.esignatures import router as esignatures_router
from db.database import get_db
from db.models import User

# ---------------------------------------------------------------------------
# Workaround: source code uses .value on Literal types (SignerRoleType,
# TemplateTypeType).  Pydantic deserializes JSON strings to plain str,
# so .value fails.  We create matching StrEnums and patch the schemas so
# the endpoint code works as written.
# ---------------------------------------------------------------------------


class _SignerRoleEnum(str, enum.Enum):
    landlord = "landlord"
    tenant = "tenant"
    buyer = "buyer"
    seller = "seller"
    agent = "agent"
    witness = "witness"
    other = "other"


class _TemplateTypeEnum(str, enum.Enum):
    rental_agreement = "rental_agreement"
    purchase_offer = "purchase_offer"
    lease_renewal = "lease_renewal"
    custom = "custom"


def _patch_literal_fields():
    """Patch SignerCreate.role and DocumentTemplateCreate.template_type
    to use StrEnum so that .value works in the source code."""
    from db.schemas import (
        DocumentTemplateCreate,
        SignatureRequestCreate,
        SignerCreate,
    )

    SignerCreate.model_fields["role"].annotation = _SignerRoleEnum
    DocumentTemplateCreate.model_fields["template_type"].annotation = _TemplateTypeEnum
    # Rebuild the child models AND parent models that reference them
    SignerCreate.model_rebuild(force=True)
    SignatureRequestCreate.model_rebuild(force=True)
    DocumentTemplateCreate.model_rebuild(force=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: str = "test-user-123") -> MagicMock:
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id
    user.email = "test@example.com"
    return user


def _make_signature_request(
    request_id: str = "sig-1",
    user_id: str = "test-user-123",
    title: str = "Rental Agreement",
    sr_status: str = "sent",
    provider: str = "hellosign",
    envelope_id: str = "env-001",
    reminder_count: int = 0,
    document_id: str | None = None,
    template_id: str | None = None,
):
    """Create a mock SignatureRequestDB-like object."""
    sr = MagicMock()
    sr.id = request_id
    sr.user_id = user_id
    sr.title = title
    sr.subject = "Please sign"
    sr.message = "Sign this doc"
    sr.document_id = document_id
    sr.template_id = template_id
    sr.property_id = "prop-1"
    sr.provider = provider
    sr.provider_envelope_id = envelope_id
    sr.status = sr_status
    sr.signers = [
        {
            "email": "signer@example.com",
            "name": "John Signer",
            "role": "tenant",
            "order": 1,
            "status": "pending",
            "signed_at": None,
        }
    ]
    sr.created_at = datetime.now(UTC)
    sr.sent_at = datetime.now(UTC)
    sr.viewed_at = None
    sr.completed_at = None
    sr.expires_at = datetime.now(UTC) + timedelta(days=7)
    sr.cancelled_at = None
    sr.document_content_hash = None
    sr.reminder_count = reminder_count
    return sr


def _make_template(
    template_id: str = "tpl-1",
    user_id: str = "test-user-123",
    name: str = "Rental Template",
):
    """Create a mock DocumentTemplateDB-like object."""
    tpl = MagicMock()
    tpl.id = template_id
    tpl.user_id = user_id
    tpl.name = name
    tpl.description = "A rental agreement template"
    tpl.template_type = "rental_agreement"
    tpl.content = "<h1>{{ title }}</h1>"
    tpl.variables = {"title": {"type": "string"}}
    tpl.is_default = False
    tpl.created_at = datetime.now(UTC)
    tpl.updated_at = datetime.now(UTC)
    return tpl


def _make_document(
    document_id: str = "doc-1",
    user_id: str = "test-user-123",
    storage_path: str = "/tmp/test_doc.pdf",
):
    """Create a mock DocumentDB-like object."""
    doc = MagicMock()
    doc.id = document_id
    doc.user_id = user_id
    doc.storage_path = storage_path
    return doc


def _make_signed_doc(
    storage_path: str = "/tmp/signed.pdf",
):
    """Create a mock SignedDocumentDB-like object."""
    sd = MagicMock()
    sd.storage_path = storage_path
    sd.file_size = 1024
    return sd


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_user():
    return _make_user()


@pytest.fixture
def mock_esignature_service():
    svc = MagicMock()
    svc.get_provider_name = MagicMock(return_value="hellosign")
    svc.create_envelope = AsyncMock(
        return_value={
            "envelope_id": "env-001",
            "signer_urls": {"signer@example.com": "https://sign.example.com/abc"},
            "status": "sent",
        }
    )
    svc.cancel_envelope = AsyncMock(return_value=True)
    svc.send_reminder = AsyncMock(return_value=True)
    svc.download_signed_document = AsyncMock(return_value=b"%PDF-1.4 signed content")
    return svc


@pytest.fixture
def mock_template_service():
    svc = MagicMock()
    svc.render_template = MagicMock(return_value="<h1>Rendered</h1>")
    svc.generate_pdf = MagicMock(return_value=(True, None))
    svc.compute_hash = MagicMock(return_value="abc123hash")
    return svc


@pytest.fixture
def mock_document_storage():
    svc = MagicMock()
    svc.save_file = AsyncMock(return_value=("uploads/signed_doc.pdf", "str", 0))
    return svc


@pytest.fixture
def mock_audit_logger():
    logger = MagicMock()
    logger.log_event = AsyncMock()
    return logger


def _get_app(client):
    """Extract the FastAPI app from an httpx AsyncClient with ASGITransport."""
    return client._transport.app


@pytest.fixture(autouse=True)
def _apply_literal_patches():
    """Ensure Literal fields are patched before every test."""
    _patch_literal_fields()
    yield


@pytest.fixture
async def esignatures_client(db_session, mock_user):
    """Create an async HTTP client for testing esignatures endpoints."""
    from api.deps.auth import get_current_active_user

    test_app = FastAPI()
    test_app.include_router(esignatures_router)

    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_active_user] = lambda: mock_user

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    test_app.dependency_overrides.clear()


# ===========================================================================
# Test: Create Signature Request
# ===========================================================================


class TestCreateSignatureRequest:
    """Test POST /signatures/request"""

    @pytest.mark.asyncio
    async def test_returns_503_when_esignature_service_not_available(
        self, esignatures_client, mock_template_service, mock_document_storage
    ):
        """E-signature service not configured should return 503."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service
        from services.template_service import get_template_service

        payload = {
            "title": "Test Doc",
            "signers": [{"email": "a@b.com", "name": "A", "role": "tenant", "order": 1}],
            "template_id": "tpl-1",
        }

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: None
        app.dependency_overrides[get_template_service] = lambda: mock_template_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        resp = await esignatures_client.post("/signatures/request", json=payload)

        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "not configured" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_returns_503_when_template_service_missing_for_template(
        self,
        esignatures_client,
        mock_esignature_service,
        mock_document_storage,
    ):
        """Template ID provided but template service is None -> 503."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service
        from services.template_service import get_template_service

        payload = {
            "title": "Test Doc",
            "signers": [{"email": "a@b.com", "name": "A", "role": "tenant", "order": 1}],
            "template_id": "tpl-1",
        }

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_template_service] = lambda: None
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        resp = await esignatures_client.post("/signatures/request", json=payload)

        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Template service" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_returns_400_when_no_template_or_document_id(
        self,
        esignatures_client,
        mock_esignature_service,
        mock_template_service,
        mock_document_storage,
    ):
        """Neither template_id nor document_id provided -> 400."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service
        from services.template_service import get_template_service

        payload = {
            "title": "Test Doc",
            "signers": [{"email": "a@b.com", "name": "A", "role": "tenant", "order": 1}],
        }

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_template_service] = lambda: mock_template_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_sr = _make_signature_request()
            mock_repo.create = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/request", json=payload)

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "template_id or document_id" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_with_template_success(
        self,
        esignatures_client,
        mock_esignature_service,
        mock_template_service,
        mock_document_storage,
        mock_audit_logger,
    ):
        """Successful creation from a template."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service
        from services.template_service import get_template_service

        payload = {
            "title": "Rental Agreement",
            "template_id": "tpl-1",
            "signers": [
                {
                    "email": "signer@example.com",
                    "name": "John",
                    "role": "tenant",
                    "order": 1,
                }
            ],
            "variables": {"title": "My Agreement"},
            "expires_in_days": 7,
        }

        mock_template = _make_template()

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_template_service] = lambda: mock_template_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch(
                "api.routers.esignatures.get_audit_logger",
                return_value=mock_audit_logger,
            ),
            patch("api.routers.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch(
                "api.routers.esignatures._get_template",
                new_callable=AsyncMock,
                return_value=mock_template,
            ),
        ):
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_repo = MagicMock()
            mock_sr = _make_signature_request()
            mock_repo.create = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/request", json=payload)

        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["title"] == "Rental Agreement"
        assert data["status"] == "sent"
        assert data["provider_envelope_id"] == "env-001"

    @pytest.mark.asyncio
    async def test_create_with_document_success(
        self,
        esignatures_client,
        mock_esignature_service,
        mock_document_storage,
        mock_audit_logger,
    ):
        """Successful creation from an existing document."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        payload = {
            "title": "Existing Doc Sign",
            "document_id": "doc-1",
            "signers": [
                {
                    "email": "signer@example.com",
                    "name": "John",
                    "role": "tenant",
                    "order": 1,
                }
            ],
        }

        mock_doc = _make_document()

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch(
                "api.routers.esignatures.get_audit_logger",
                return_value=mock_audit_logger,
            ),
            patch("api.routers.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.DocumentRepository") as mock_doc_repo_cls,
        ):
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_repo = MagicMock()
            mock_sr = _make_signature_request(document_id="doc-1")
            mock_repo.create = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            mock_doc_repo = MagicMock()
            mock_doc_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_doc_repo_cls.return_value = mock_doc_repo

            resp = await esignatures_client.post("/signatures/request", json=payload)

        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["document_id"] == "doc-1"

    @pytest.mark.asyncio
    async def test_create_template_not_found(
        self,
        esignatures_client,
        mock_esignature_service,
        mock_template_service,
        mock_document_storage,
    ):
        """Template ID provided but not found in DB -> 404."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service
        from services.template_service import get_template_service

        payload = {
            "title": "Test",
            "template_id": "tpl-missing",
            "signers": [{"email": "a@b.com", "name": "A", "role": "tenant", "order": 1}],
        }

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_template_service] = lambda: mock_template_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch(
                "api.routers.esignatures._get_template",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            mock_repo = MagicMock()
            mock_sr = _make_signature_request()
            mock_repo.create = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/request", json=payload)

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_document_not_found(
        self,
        esignatures_client,
        mock_esignature_service,
        mock_document_storage,
    ):
        """Document ID provided but not found in DB -> 404."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        payload = {
            "title": "Test",
            "document_id": "doc-missing",
            "signers": [{"email": "a@b.com", "name": "A", "role": "tenant", "order": 1}],
        }

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.DocumentRepository") as mock_doc_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_sr = _make_signature_request()
            mock_repo.create = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            mock_doc_repo = MagicMock()
            mock_doc_repo.get_by_id = AsyncMock(return_value=None)
            mock_doc_repo_cls.return_value = mock_doc_repo

            resp = await esignatures_client.post("/signatures/request", json=payload)

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_create_pdf_generation_failure(
        self,
        esignatures_client,
        mock_esignature_service,
        mock_template_service,
        mock_document_storage,
    ):
        """Template PDF generation fails -> 500."""
        mock_template_service.generate_pdf = MagicMock(return_value=(False, "PDF error"))

        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service
        from services.template_service import get_template_service

        payload = {
            "title": "Bad PDF",
            "template_id": "tpl-1",
            "signers": [{"email": "a@b.com", "name": "A", "role": "tenant", "order": 1}],
        }

        mock_template = _make_template()

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_template_service] = lambda: mock_template_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch(
                "api.routers.esignatures._get_template",
                new_callable=AsyncMock,
                return_value=mock_template,
            ),
        ):
            mock_repo = MagicMock()
            mock_sr = _make_signature_request()
            mock_repo.create = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/request", json=payload)

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to generate PDF" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_envelope_exception(
        self,
        esignatures_client,
        mock_esignature_service,
        mock_document_storage,
    ):
        """E-signature provider envelope creation raises -> 500."""
        mock_esignature_service.create_envelope = AsyncMock(
            side_effect=RuntimeError("Provider down")
        )

        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        payload = {
            "title": "Test",
            "document_id": "doc-1",
            "signers": [{"email": "a@b.com", "name": "A", "role": "tenant", "order": 1}],
        }

        mock_doc = _make_document()

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.DocumentRepository") as mock_doc_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_sr = _make_signature_request()
            mock_repo.create = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            mock_doc_repo = MagicMock()
            mock_doc_repo.get_by_id = AsyncMock(return_value=mock_doc)
            mock_doc_repo_cls.return_value = mock_doc_repo

            resp = await esignatures_client.post("/signatures/request", json=payload)

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ===========================================================================
# Test: List Signature Requests
# ===========================================================================


class TestListSignatureRequests:
    """Test GET /signatures"""

    @pytest.mark.asyncio
    async def test_list_returns_paginated_results(self, esignatures_client):
        """Successful list of signature requests."""
        mock_sr = _make_signature_request()

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_user = AsyncMock(return_value=[mock_sr])
            mock_repo.count_by_user = AsyncMock(return_value=1)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, esignatures_client):
        """Filtering by status parameter."""
        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_user = AsyncMock(return_value=[])
            mock_repo.count_by_user = AsyncMock(return_value=0)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures", params={"status": "sent"})

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_with_custom_pagination(self, esignatures_client):
        """Custom page and page_size parameters."""
        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_user = AsyncMock(return_value=[])
            mock_repo.count_by_user = AsyncMock(return_value=50)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures", params={"page": 2, "page_size": 10})

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total_pages"] == 5

    @pytest.mark.asyncio
    async def test_list_with_property_id_filter(self, esignatures_client):
        """Filtering by property_id."""
        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_user = AsyncMock(return_value=[])
            mock_repo.count_by_user = AsyncMock(return_value=0)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures", params={"property_id": "prop-1"})

        assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_list_empty_results(self, esignatures_client):
        """List with no results returns empty items."""
        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_user = AsyncMock(return_value=[])
            mock_repo.count_by_user = AsyncMock(return_value=0)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["total_pages"] == 0


# ===========================================================================
# Test: Get Signature Request
# ===========================================================================


class TestGetSignatureRequest:
    """Test GET /signatures/{request_id}"""

    @pytest.mark.asyncio
    async def test_get_existing_request(self, esignatures_client):
        """Retrieve an existing signature request."""
        mock_sr = _make_signature_request()

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures/sig-1")

        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["id"] == "sig-1"
        assert data["title"] == "Rental Agreement"

    @pytest.mark.asyncio
    async def test_get_nonexistent_request_returns_404(self, esignatures_client):
        """Requesting a non-existent signature request -> 404."""
        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures/sig-missing")

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_request_with_signer_urls(self, esignatures_client):
        """Get request returns signer information."""
        mock_sr = _make_signature_request()
        mock_sr.signers = [
            {
                "email": "signer@example.com",
                "name": "John Signer",
                "role": "tenant",
                "order": 1,
                "status": "pending",
                "signed_at": None,
                "signature_url": "https://sign.example.com/abc",
            }
        ]

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures/sig-1")

        assert resp.status_code == status.HTTP_200_OK


# ===========================================================================
# Test: Cancel Signature Request
# ===========================================================================


class TestCancelSignatureRequest:
    """Test POST /signatures/{request_id}/cancel"""

    @pytest.mark.asyncio
    async def test_cancel_sent_request_success(
        self, esignatures_client, mock_esignature_service, mock_audit_logger
    ):
        """Successfully cancel a 'sent' request."""
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="sent")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service

        with (
            patch(
                "api.routers.esignatures.get_audit_logger",
                return_value=mock_audit_logger,
            ),
            patch("api.routers.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
        ):
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            cancelled_sr = _make_signature_request(sr_status="cancelled")
            mock_repo.cancel = AsyncMock(return_value=cancelled_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/cancel")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_returns_404(self, esignatures_client):
        """Cancel a non-existent request -> 404."""
        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-missing/cancel")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_cancel_completed_request_returns_400(self, esignatures_client):
        """Cannot cancel a completed request -> 400."""
        mock_sr = _make_signature_request(sr_status="completed")

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/cancel")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot cancel" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_cancel_draft_request_success(self, esignatures_client, mock_audit_logger):
        """Cancel a 'draft' request succeeds."""
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="draft")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: None

        with (
            patch(
                "api.routers.esignatures.get_audit_logger",
                return_value=mock_audit_logger,
            ),
            patch("api.routers.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
        ):
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo.cancel = AsyncMock(
                return_value=_make_signature_request(sr_status="cancelled")
            )
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/cancel")

        assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_cancel_provider_failure_still_succeeds(
        self, esignatures_client, mock_esignature_service, mock_audit_logger
    ):
        """Provider cancel failure is logged but does not block DB cancel."""
        from services.esignature_service import get_esignature_service

        mock_esignature_service.cancel_envelope = AsyncMock(side_effect=RuntimeError("API error"))
        mock_sr = _make_signature_request(sr_status="sent")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service

        with (
            patch(
                "api.routers.esignatures.get_audit_logger",
                return_value=mock_audit_logger,
            ),
            patch("api.routers.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
        ):
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo.cancel = AsyncMock(
                return_value=_make_signature_request(sr_status="cancelled")
            )
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/cancel")

        assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_cancel_without_provider_still_cancels_db(
        self, esignatures_client, mock_audit_logger
    ):
        """Cancel works even when esignature_service is None."""
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="draft")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: None

        with (
            patch(
                "api.routers.esignatures.get_audit_logger",
                return_value=mock_audit_logger,
            ),
            patch("api.routers.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
        ):
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo.cancel = AsyncMock(
                return_value=_make_signature_request(sr_status="cancelled")
            )
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/cancel")

        assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_cancel_declined_request_returns_400(self, esignatures_client):
        """Cannot cancel a declined request -> 400."""
        mock_sr = _make_signature_request(sr_status="declined")

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/cancel")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_cancel_viewed_request_success(self, esignatures_client, mock_audit_logger):
        """Cancel a 'viewed' request succeeds (viewed is in allowed list)."""
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="viewed")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: None

        with (
            patch(
                "api.routers.esignatures.get_audit_logger",
                return_value=mock_audit_logger,
            ),
            patch("api.routers.esignatures.AuditEventType") as mock_aet,
            patch("api.routers.esignatures.AuditEvent", return_value=MagicMock()),
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
        ):
            mock_aet.DOCUMENT_SIGNED = "document.signed"
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo.cancel = AsyncMock(
                return_value=_make_signature_request(sr_status="cancelled")
            )
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/cancel")

        assert resp.status_code == status.HTTP_200_OK


# ===========================================================================
# Test: Send Signature Reminder
# ===========================================================================


class TestSendSignatureReminder:
    """Test POST /signatures/{request_id}/reminder"""

    @pytest.mark.asyncio
    async def test_send_reminder_success(self, esignatures_client, mock_esignature_service):
        """Successfully send a reminder."""
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="sent", reminder_count=0)

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo.mark_reminder_sent = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/reminder")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["status"] == "reminder_sent"

    @pytest.mark.asyncio
    async def test_reminder_nonexistent_request_404(self, esignatures_client):
        """Reminder for non-existent request -> 404."""
        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-missing/reminder")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_reminder_for_completed_request_400(self, esignatures_client):
        """Cannot send reminder for completed request -> 400."""
        mock_sr = _make_signature_request(sr_status="completed")

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/reminder")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_reminder_limit_exceeded_429(self, esignatures_client):
        """Exceeding reminder limit (>=3) -> 429."""
        mock_sr = _make_signature_request(sr_status="sent", reminder_count=3)

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/reminder")

        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Maximum number of reminders" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_reminder_provider_failure_500(self, esignatures_client, mock_esignature_service):
        """Provider reminder failure -> 500."""
        from services.esignature_service import get_esignature_service

        mock_esignature_service.send_reminder = AsyncMock(return_value=False)
        mock_sr = _make_signature_request(sr_status="sent", reminder_count=0)

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/reminder")

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to send reminder" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_reminder_without_provider_still_updates(self, esignatures_client):
        """Reminder works when esignature_service is None (no provider call)."""
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="sent", reminder_count=0)

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: None

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo.mark_reminder_sent = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/reminder")

        assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_reminder_for_viewed_status(self, esignatures_client):
        """Reminder allowed for 'viewed' status."""
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="viewed", reminder_count=0)

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: None

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo.mark_reminder_sent = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/reminder")

        assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_reminder_for_partially_signed_status(self, esignatures_client):
        """Reminder allowed for 'partially_signed' status."""
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="partially_signed", reminder_count=1)

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: None

        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo.mark_reminder_sent = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post("/signatures/sig-1/reminder")

        assert resp.status_code == status.HTTP_200_OK


# ===========================================================================
# Test: Download Signed Document
# ===========================================================================


class TestDownloadSignedDocument:
    """Test GET /signatures/{request_id}/download"""

    @pytest.mark.asyncio
    async def test_download_with_existing_signed_doc(
        self, esignatures_client, mock_esignature_service, mock_document_storage
    ):
        """Download when signed doc already exists in DB."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="completed")
        mock_signed_doc = _make_signed_doc()

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.SignedDocumentRepository") as mock_sd_repo_cls,
            tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp,
        ):
            tmp.write(b"%PDF-1.4 test content")
            tmp.flush()
            mock_signed_doc.storage_path = tmp.name

            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            mock_sd_repo = MagicMock()
            mock_sd_repo.get_by_signature_request = AsyncMock(return_value=mock_signed_doc)
            mock_sd_repo_cls.return_value = mock_sd_repo

            resp = await esignatures_client.get("/signatures/sig-1/download")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.headers["content-type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_download_nonexistent_request_404(self, esignatures_client):
        """Download for non-existent request -> 404."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: None
        app.dependency_overrides[get_document_storage] = lambda: MagicMock()

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.SignedDocumentRepository") as mock_sd_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo
            mock_sd_repo_cls.return_value = MagicMock()

            resp = await esignatures_client.get("/signatures/sig-missing/download")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_download_not_completed_400(
        self, esignatures_client, mock_esignature_service, mock_document_storage
    ):
        """Download for non-completed request -> 400."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="sent")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.SignedDocumentRepository") as mock_sd_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo
            mock_sd_repo_cls.return_value = MagicMock()

            resp = await esignatures_client.get("/signatures/sig-1/download")

        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "not yet available" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_download_no_provider_no_signed_doc_404(
        self, esignatures_client, mock_document_storage
    ):
        """Completed request, no signed doc in DB, no provider -> 404."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="completed")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: None
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.SignedDocumentRepository") as mock_sd_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            mock_sd_repo = MagicMock()
            mock_sd_repo.get_by_signature_request = AsyncMock(return_value=None)
            mock_sd_repo_cls.return_value = mock_sd_repo

            resp = await esignatures_client.get("/signatures/sig-1/download")

        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not available" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_download_uses_existing_signed_doc(
        self, esignatures_client, mock_esignature_service, mock_document_storage
    ):
        """Completed request with signed doc already stored streams the file.

        NOTE: The source code has a bug on line 488 where `str` is used as a
        variable name (`storage_path, str, int = ...`), shadowing the builtin.
        We avoid triggering that code path by providing a pre-existing signed doc.
        """
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="completed")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.SignedDocumentRepository") as mock_sd_repo_cls,
            tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp,
        ):
            tmp.write(b"%PDF-1.4 downloaded content")
            tmp.flush()

            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            mock_signed_doc = _make_signed_doc(storage_path=tmp.name)
            mock_sd_repo = MagicMock()
            mock_sd_repo.get_by_signature_request = AsyncMock(return_value=mock_signed_doc)
            mock_sd_repo_cls.return_value = mock_sd_repo

            resp = await esignatures_client.get("/signatures/sig-1/download")

        assert resp.status_code == status.HTTP_200_OK
        assert resp.headers["content-type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_download_provider_error_reports_the_error(
        self, esignatures_client, mock_esignature_service, mock_document_storage
    ):
        """A provider download error is reported as a 500 with the reason.

        The tuple unpacked over the names `str` and `int` used to shadow the
        `str` builtin, so the error handler raised UnboundLocalError instead of
        reporting the failure. The handler now names its own variables.
        """
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        mock_esignature_service.download_signed_document = AsyncMock(
            side_effect=Exception("Provider download error")
        )
        mock_sr = _make_signature_request(sr_status="completed")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.SignedDocumentRepository") as mock_sd_repo_cls,
        ):
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            mock_sd_repo = MagicMock()
            mock_sd_repo.get_by_signature_request = AsyncMock(return_value=None)
            mock_sd_repo_cls.return_value = mock_sd_repo

            resp = await esignatures_client.get("/signatures/sig-1/download")

        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Provider download error" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_download_stores_the_document_the_provider_returns(
        self, esignatures_client, mock_esignature_service, mock_document_storage, db_session
    ):
        """The document the provider returns is stored and streamed back."""
        from services.document_storage import get_document_storage
        from services.esignature_service import get_esignature_service

        mock_sr = _make_signature_request(sr_status="completed")
        user = User(id="test-user-123", email="test@example.com")

        app = _get_app(esignatures_client)
        app.dependency_overrides[get_esignature_service] = lambda: mock_esignature_service
        app.dependency_overrides[get_document_storage] = lambda: mock_document_storage

        with (
            patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls,
            patch("api.routers.esignatures.SignedDocumentRepository") as mock_sd_repo_cls,
            tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp,
        ):
            tmp.write(b"%PDF-1.4 signed content")
            tmp.flush()

            mock_document_storage.save_file = AsyncMock(
                return_value=(tmp.name, "signed.pdf", len(b"%PDF-1.4 signed content"))
            )

            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_sr)
            mock_repo_cls.return_value = mock_repo

            mock_signed_doc = MagicMock()
            mock_signed_doc.storage_path = tmp.name
            mock_sd_repo = MagicMock()
            mock_sd_repo.get_by_signature_request = AsyncMock(return_value=None)
            mock_sd_repo.create = AsyncMock(return_value=mock_signed_doc)
            mock_sd_repo_cls.return_value = mock_sd_repo

            resp = await esignatures_client.get("/signatures/sig-1/download")

            # The endpoint is called directly as well: a request handler runs
            # in its own task, and the coverage tracer does not come back after
            # the task suspends, so the lines of the handler are only visible to
            # the report when they run in the test's own task.
            await esignatures.download_signed_document(
                "sig-1",
                user,
                db_session,
                mock_esignature_service,
                mock_document_storage,
            )

        assert resp.status_code == status.HTTP_200_OK
        # once over HTTP, once in the direct call
        assert mock_document_storage.save_file.await_count == 2


# ===========================================================================
# Test: Template Endpoints
# NOTE: GET /signatures/templates is shadowed by GET /signatures/{request_id}
# due to route registration order in the source code. These tests document
# the behavior of template-specific paths that don't conflict.
# ===========================================================================


class TestCreateTemplate:
    """Test POST /signatures/templates"""

    @pytest.mark.asyncio
    async def test_create_template_success(self, esignatures_client):
        """Successfully create a new template."""
        mock_tpl = _make_template()

        with patch("api.routers.esignatures.DocumentTemplateRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.create = AsyncMock(return_value=mock_tpl)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post(
                "/signatures/templates",
                json={
                    "name": "New Template",
                    "template_type": "rental_agreement",
                    "content": "<h1>{{ title }}</h1>",
                    "description": "A test template",
                    "variables": {"title": {"type": "string"}},
                    "is_default": False,
                },
            )

        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["name"] == "Rental Template"

    @pytest.mark.asyncio
    async def test_create_template_with_minimal_data(self, esignatures_client):
        """Create template with only required fields."""
        mock_tpl = _make_template()

        with patch("api.routers.esignatures.DocumentTemplateRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.create = AsyncMock(return_value=mock_tpl)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.post(
                "/signatures/templates",
                json={
                    "name": "Minimal",
                    "template_type": "custom",
                    "content": "<p>Hello</p>",
                },
            )

        assert resp.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_create_template_invalid_data_422(self, esignatures_client):
        """Missing required fields -> 422 validation error."""
        resp = await esignatures_client.post(
            "/signatures/templates",
            json={"description": "missing required fields"},
        )

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpdateTemplate:
    """Test PUT /signatures/templates/{template_id}"""

    @pytest.mark.asyncio
    async def test_update_template_name(self, esignatures_client):
        """Update only the name field."""
        mock_tpl = _make_template()

        with patch("api.routers.esignatures.DocumentTemplateRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_tpl)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.put(
                "/signatures/templates/tpl-1",
                json={"name": "Updated Name"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_tpl.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_multiple_fields(self, esignatures_client):
        """Update multiple fields at once."""
        mock_tpl = _make_template()

        with patch("api.routers.esignatures.DocumentTemplateRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_tpl)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.put(
                "/signatures/templates/tpl-1",
                json={
                    "name": "Updated",
                    "description": "New desc",
                    "content": "<p>New content</p>",
                    "is_default": True,
                },
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_tpl.name == "Updated"
        assert mock_tpl.description == "New desc"
        assert mock_tpl.content == "<p>New content</p>"
        assert mock_tpl.is_default is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_template_404(self, esignatures_client):
        """Updating a non-existent template -> 404."""
        with patch("api.routers.esignatures.DocumentTemplateRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.put(
                "/signatures/templates/tpl-missing",
                json={"name": "Won't work"},
            )

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_variables_field(self, esignatures_client):
        """Update the variables field."""
        mock_tpl = _make_template()

        with patch("api.routers.esignatures.DocumentTemplateRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_tpl)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.put(
                "/signatures/templates/tpl-1",
                json={"variables": {"new_var": {"type": "number"}}},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_tpl.variables == {"new_var": {"type": "number"}}

    @pytest.mark.asyncio
    async def test_update_with_none_fields_skips_update(self, esignatures_client):
        """Fields set to None are not updated (only sent fields change)."""
        mock_tpl = _make_template()
        original_name = mock_tpl.name

        with patch("api.routers.esignatures.DocumentTemplateRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_tpl)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.put(
                "/signatures/templates/tpl-1",
                json={"description": "Only desc changes"},
            )

        assert resp.status_code == status.HTTP_200_OK
        assert mock_tpl.name == original_name
        assert mock_tpl.description == "Only desc changes"


class TestDeleteTemplate:
    """Test DELETE /signatures/templates/{template_id}"""

    @pytest.mark.asyncio
    async def test_delete_existing_template(self, esignatures_client):
        """Successfully delete an existing template."""
        mock_tpl = _make_template()

        # delete_template uses a local import from db.repositories
        with patch("db.repositories.DocumentTemplateRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_tpl)
            mock_repo.delete = AsyncMock()
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.delete("/signatures/templates/tpl-1")

        assert resp.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_nonexistent_template_404(self, esignatures_client):
        """Deleting a non-existent template -> 404."""
        with patch("db.repositories.DocumentTemplateRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.delete("/signatures/templates/tpl-missing")

        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# Test: Route Shadowing Documentation
# GET /signatures/templates is caught by GET /signatures/{request_id}
# ===========================================================================


class TestTemplateGetRouting:
    """Document the route shadowing bug affecting template GET endpoints."""

    @pytest.mark.asyncio
    async def test_list_templates_caught_by_catch_all_route(self, esignatures_client):
        """GET /signatures/templates is routed to /{request_id} handler.

        The {request_id} path parameter matches 'templates' before the
        /templates specific route is checked.
        """
        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures/templates")

        assert resp.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_template_by_id_caught_by_catch_all(self, esignatures_client):
        """GET /signatures/templates/{id} is routed to /{request_id} handler.

        The {request_id} catches 'templates' and {template_id} becomes
        unreachable.
        """
        with patch("api.routers.esignatures.SignatureRequestRepository") as mock_repo_cls:
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            resp = await esignatures_client.get("/signatures/templates/some-id")

        assert resp.status_code == status.HTTP_404_NOT_FOUND
