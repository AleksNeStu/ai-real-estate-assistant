"""E-signature API endpoints.

Task #57: E-Signature Integration

Provides endpoints for:
- Creating and managing signature requests
- Template management
- Webhook handling for HelloSign callbacks
"""

import logging
import tempfile
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.audit import AuditEvent, AuditEventType, AuditLevel, get_audit_logger
from api.deps.auth import get_current_active_user
from core.security_utils import sanitize_for_log
from db.database import get_db
from db.models import User
from db.repositories import (
    DocumentRepository,
    DocumentTemplateRepository,
    SignatureRequestRepository,
    SignedDocumentRepository,
)
from db.schemas import (
    DocumentTemplateCreate,
    DocumentTemplateResponse,
    DocumentTemplateUpdate,
    SignatureRequestCreate,
    SignatureRequestFilters,
    SignatureRequestListResponse,
    SignatureRequestResponse,
)
from services.document_storage import DocumentStorageService, get_document_storage
from services.esignature_service import ESignatureService, get_esignature_service
from services.template_service import TemplateService, get_template_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signatures", tags=["E-Signatures"])


# =============================================================================
# Signature Request Endpoints
# =============================================================================


@router.post(
    "/request",
    response_model=SignatureRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a signature request",
    description="Create a new signature request from a template or existing document.",
)
async def create_signature_request(
    request_data: SignatureRequestCreate,
    request: Request,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
    esignature_service: Optional[ESignatureService] = Depends(get_esignature_service),
    template_service: Optional[TemplateService] = Depends(get_template_service),
    document_storage: DocumentStorageService = Depends(get_document_storage),
) -> SignatureRequestResponse:
    """Create a new signature request.

    This endpoint:
    1. Validates the request
    2. Renders the document from template or uses existing document
    3. Creates the signature request in the e-signature provider
    4. Stores the request in the database
    5. Returns the request details with signer URLs
    """
    # Check if e-signature service is available
    if not esignature_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="E-signature service is not configured",
        )

    # Check if template service is available (required for template rendering)
    if request_data.template_id and not template_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Template service is not configured",
        )

    # Initialize repositories
    sig_repo = SignatureRequestRepository(session)

    # Create the signature request record (initially in draft status)
    expires_at = None
    if request_data.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=request_data.expires_in_days)

    # Create initial signer list
    signers = [
        {
            "email": s.email,
            "name": s.name,
            "role": s.role.value,
            "order": s.order,
            "status": "pending",
            "signed_at": None,
        }
        for s in request_data.signers
    ]

    signature_request = await sig_repo.create(
        user_id=user.id,
        title=request_data.title,
        provider=esignature_service.get_provider_name(),
        document_id=request_data.document_id,
        template_id=request_data.template_id,
        property_id=request_data.property_id,
        subject=request_data.subject,
        message=request_data.message,
        variables=request_data.variables,
        signers=signers,
        status="draft",
        expires_at=expires_at,
    )

    # Generate the document
    document_path: Optional[Path] = None

    try:
        if request_data.template_id and template_service:
            # Render from template
            template = await _get_template(session, request_data.template_id, user.id)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template {request_data.template_id} not found",
                )

            # Render the template with variables
            document_content = template_service.render_template(
                template.content,
                request_data.variables or {},
            )

            # Generate PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                success, error = template_service.generate_pdf(
                    document_content,
                    tmp_path,
                    title=request_data.title,
                )
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to generate PDF: {error}",
                    )

                document_path = tmp_path

                # Compute hash for integrity
                content_hash = template_service.compute_hash(document_content)

                # Update request with hash
                signature_request.document_content_hash = content_hash
                await session.flush()

        elif request_data.document_id:
            # Use existing document
            doc_repo = DocumentRepository(session)
            document = await doc_repo.get_by_id(request_data.document_id, user.id)
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {request_data.document_id} not found",
                )

            document_path = Path(document.storage_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either template_id or document_id is required",
            )

        # Create the signature request in the e-signature provider
        envelope_result = await esignature_service.create_envelope(
            document_path=document_path,
            signers=signers,
            title=request_data.title,
            subject=request_data.subject,
            message=request_data.message,
            metadata={
                "request_id": signature_request.id,
                "user_id": user.id,
                "property_id": request_data.property_id,
            },
            expires_days=request_data.expires_in_days,
        )

        # Update the signature request with provider info
        signature_request.provider_envelope_id = envelope_result.get("envelope_id")
        signature_request.status = "sent"
        signature_request.sent_at = datetime.now(UTC)

        # Update signer URLs
        if envelope_result.get("signer_urls"):
            for signer in signers:
                signer_url = envelope_result["signer_urls"].get(signer["email"])
                if signer_url:
                    signer["signature_url"] = signer_url

        signature_request.signers = signers
        await session.flush()

        # Log audit event
        audit_logger = get_audit_logger()
        await audit_logger.log_event(  # type: ignore[attr-defined]
            AuditEvent(
                event_type=AuditEventType.DOCUMENT_SIGNED,  # type: ignore[attr-defined]
                level=AuditLevel.INFO,
                user_id=user.id,
                resource=f"signature_request:{signature_request.id}",
                action=f"Signature request created: {request_data.title}",
                result="success",
                metadata={
                    "provider": signature_request.provider,
                    "envelope_id": signature_request.provider_envelope_id,
                    "signer_count": len(signers),
                },
            )
        )

        return SignatureRequestResponse.model_validate(signature_request)

    except HTTPException:
        # Clean up temp file on re-raise
        if document_path and document_path.exists():
            document_path.unlink()
        raise
    except Exception as e:
        logger.error("Error creating signature request: %s", sanitize_for_log(e))
        # Clean up temp file
        if document_path and document_path.exists():
            document_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create signature request: {str(e)}",
        ) from None


async def _get_template(
    session: AsyncSession,
    template_id: str,
    user_id: str,
) -> Any:
    """Get template by ID."""
    from db.repositories import DocumentTemplateRepository

    repo = DocumentTemplateRepository(session)
    return await repo.get_by_id(template_id, user_id)


@router.get(
    "",
    response_model=SignatureRequestListResponse,
    summary="List signature requests",
    description="Get paginated list of user's signature requests with optional filtering.",
)
async def list_signature_requests(
    filters: SignatureRequestFilters = Depends(),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SignatureRequestListResponse:
    """List user's signature requests with filtering."""
    repo = SignatureRequestRepository(session)

    requests = await repo.get_by_user(
        user_id=user.id,
        status=filters.status if filters.status else None,  # type: ignore[union-attr]
        property_id=filters.property_id,
        page=filters.page,
        page_size=filters.page_size,
    )

    total = await repo.count_by_user(
        user_id=user.id,
        status=filters.status if filters.status else None,  # type: ignore[union-attr]
    )

    total_pages = (total + filters.page_size - 1) // filters.page_size

    return SignatureRequestListResponse(
        items=[SignatureRequestResponse.model_validate(r) for r in requests],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{request_id}",
    response_model=SignatureRequestResponse,
    summary="Get signature request details",
    description="Get detailed information about a specific signature request.",
)
async def get_signature_request(
    request_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SignatureRequestResponse:
    """Get signature request details."""
    repo = SignatureRequestRepository(session)

    signature_request = await repo.get_by_id(request_id, user.id)
    if not signature_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signature request {request_id} not found",
        )

    return SignatureRequestResponse.model_validate(signature_request)


@router.post(
    "/{request_id}/cancel",
    summary="Cancel a signature request",
    description="Cancel a pending signature request.",
)
async def cancel_signature_request(
    request_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
    esignature_service: Optional[ESignatureService] = Depends(get_esignature_service),
) -> dict[str, Any]:
    """Cancel a pending signature request."""
    repo = SignatureRequestRepository(session)

    signature_request = await repo.get_by_id(request_id, user.id)
    if not signature_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signature request {request_id} not found",
        )

    # Check if request can be cancelled
    if signature_request.status not in ["draft", "sent", "viewed", "partially_signed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel request in status: {signature_request.status}",
        )

    # Cancel in provider
    if esignature_service and signature_request.provider_envelope_id:
        try:
            await esignature_service.cancel_envelope(signature_request.provider_envelope_id)
        except Exception as e:
            logger.warning("Failed to cancel in provider: %s", sanitize_for_log(e))

    # Update in database
    signature_request = await repo.cancel(signature_request)

    # Log audit event
    audit_logger = get_audit_logger()
    await audit_logger.log_event(  # type: ignore[attr-defined]
        AuditEvent(
            event_type=AuditEventType.DOCUMENT_SIGNED,  # type: ignore[attr-defined]
            level=AuditLevel.INFO,
            user_id=user.id,
            resource=f"signature_request:{signature_request.id}",
            action=f"Signature request cancelled: {signature_request.title}",
            result="success",
        )
    )

    return {"status": "cancelled", "request_id": request_id}


@router.post(
    "/{request_id}/reminder",
    summary="Send reminder to signers",
    description="Send a reminder email to pending signers.",
)
async def send_signature_reminder(
    request_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
    esignature_service: Optional[ESignatureService] = Depends(get_esignature_service),
) -> dict[str, Any]:
    """Send reminder to pending signers."""
    repo = SignatureRequestRepository(session)

    signature_request = await repo.get_by_id(request_id, user.id)
    if not signature_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signature request {request_id} not found",
        )

    # Check if request is in a state that allows reminders
    if signature_request.status not in ["sent", "viewed", "partially_signed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot send reminder for request in status: {signature_request.status}",
        )

    # Check reminder limit
    if signature_request.reminder_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum number of reminders (3) already sent",
        )

    # Send reminder via provider
    if esignature_service and signature_request.provider_envelope_id:
        success = await esignature_service.send_reminder(signature_request.provider_envelope_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send reminder",
            )

    # Update reminder tracking
    signature_request = await repo.mark_reminder_sent(signature_request)

    return {"status": "reminder_sent", "request_id": request_id}


@router.get(
    "/{request_id}/download",
    summary="Download signed document",
    description="Download the completed, signed document.",
)
async def download_signed_document(
    request_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
    esignature_service: Optional[ESignatureService] = Depends(get_esignature_service),
    document_storage: DocumentStorageService = Depends(get_document_storage),
):
    """Download the signed document."""
    repo = SignatureRequestRepository(session)
    signed_doc_repo = SignedDocumentRepository(session)

    signature_request = await repo.get_by_id(request_id, user.id)
    if not signature_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signature request {request_id} not found",
        )

    # Check if request is completed
    if signature_request.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signed document is not yet available",
        )

    # Check if we already have the signed document
    signed_doc = await signed_doc_repo.get_by_signature_request(request_id)

    if not signed_doc:
        # Download from provider
        if not esignature_service or not signature_request.provider_envelope_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Signed document not available",
            )

        try:
            pdf_content = await esignature_service.download_signed_document(
                signature_request.provider_envelope_id
            )

            # Store the signed document
            filename = f"{signature_request.title}_signed.pdf"
            storage_path, str, int = await document_storage.save_file(
                user_id=user.id,
                file=type("file", (BytesIO(pdf_content), filename)),  # Mock UploadFile
                max_size_bytes=20 * 1024 * 1024,  # 20MB
            )

            # Create signed document record
            signed_doc = await signed_doc_repo.create(
                signature_request_id=request_id,
                storage_path=storage_path,
                file_size=len(pdf_content),
                document_id=signature_request.document_id,
                provider_document_id=signature_request.provider_envelope_id,
            )

        except Exception as e:
            logger.error("Error downloading signed document: %s", sanitize_for_log(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download signed document: {str(e)}",
            ) from None

    # Stream the file
    def iterfile():
        with open(signed_doc.storage_path, "rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{signature_request.title}_signed.pdf"'
        },
    )


# =============================================================================
# Template Endpoints
# =============================================================================


@router.get(
    "/templates",
    summary="List document templates",
    description="Get paginated list of document templates.",
)
async def list_templates(
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
):
    """List document templates."""
    from db.repositories import DocumentTemplateRepository
    from db.schemas import DocumentTemplateListResponse

    repo = DocumentTemplateRepository(session)

    templates = await repo.get_by_user(
        user_id=user.id,
        template_type=template_type,
        page=page,
        page_size=page_size,
    )

    total = await repo.count_by_user(user.id, template_type)

    total_pages = (total + page_size - 1) // page_size

    return DocumentTemplateListResponse(
        items=templates,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/templates/{template_id}",
    summary="Get template details",
    description="Get detailed information about a specific template.",
)
async def get_template(
    template_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentTemplateResponse:
    """Get template details."""
    repo = DocumentTemplateRepository(session)
    template = await repo.get_by_id(template_id, user.id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )
    return DocumentTemplateResponse.model_validate(template)


@router.post(
    "/templates",
    status_code=status.HTTP_201_CREATED,
    summary="Create document template",
    description="Create a new document template with Jinja2 content.",
)
async def create_template(
    template_data: DocumentTemplateCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentTemplateResponse:
    """Create document template."""
    repo = DocumentTemplateRepository(session)

    template = await repo.create(
        user_id=user.id,
        name=template_data.name,
        template_type=template_data.template_type.value,
        content=template_data.content,
        description=template_data.description,
        variables=template_data.variables,
        is_default=template_data.is_default,
    )

    return DocumentTemplateResponse.model_validate(template)


@router.put(
    "/templates/{template_id}",
    summary="Update template",
    description="Update an existing template.",
)
async def update_template(
    template_id: str,
    template_data: DocumentTemplateUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentTemplateResponse:
    """Update template."""
    repo = DocumentTemplateRepository(session)
    template = await repo.get_by_id(template_id, user.id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )
    # Update fields
    if template_data.name is not None:
        template.name = template_data.name
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.content is not None:
        template.content = template_data.content
    if template_data.variables is not None:
        template.variables = template_data.variables
    if template_data.is_default is not None:
        template.is_default = template_data.is_default

    await session.flush()
    return DocumentTemplateResponse.model_validate(template)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete template",
    description="Delete a document template.",
)
async def delete_template(
    template_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete template."""
    from db.repositories import DocumentTemplateRepository

    repo = DocumentTemplateRepository(session)

    template = await repo.get_by_id(template_id, user.id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )

    await repo.delete(template)

    return None
