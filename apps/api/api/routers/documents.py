"""Document management API endpoints.

Task #43: Document Management System
"""

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.audit import AuditEvent, AuditEventType, AuditLevel, get_audit_logger
from api.deps.auth import get_current_active_user
from core.security_utils import sanitize_for_log
from db.database import get_db
from db.models import DocumentDB, User
from db.repositories import DocumentRepository
from db.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadResponse,
    ExpiringDocumentsResponse,
)
from services.document_storage import get_document_storage
from services.ocr_service import get_ocr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

# Constants
_READ_CHUNK_BYTES = 1024 * 1024  # 1MB chunks
_MAX_UPLOAD_FILE_BYTES = 10 * 1024 * 1024  # 10MB
_ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}


async def _read_upload_file_limited(file: UploadFile, max_bytes: int) -> tuple[bytes, bool]:
    """Read upload file with size limit.

    Returns:
        Tuple of (data, too_large)
    """
    buf = bytearray()
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            return bytes(buf), False
        if len(buf) + len(chunk) > max_bytes:
            return bytes(buf), True
        buf.extend(chunk)


def _parse_tags(tags_str: Optional[str]) -> Optional[list[str]]:
    """Parse tags from JSON string or comma-separated string."""
    if not tags_str:
        return None
    try:
        tags = json.loads(tags_str)
        if isinstance(tags, list):
            return tags
    except json.JSONDecodeError:
        # Try comma-separated
        return [t.strip() for t in tags_str.split(",") if t.strip()]
    return None


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    description="Upload a document file with optional metadata. "
    "Supports PDF, DOC, DOCX, JPG, PNG. Max size: 10MB.",
)
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="Document file to upload"),
    property_id: Optional[str] = Form(None, description="Associated property ID"),
    category: Optional[str] = Form(None, description="Document category"),
    tags: Optional[str] = Form(None, description="Tags as JSON array or comma-separated"),
    description: Optional[str] = Form(None, description="Document description"),
    expiry_date: Optional[str] = Form(None, description="Expiry date (ISO format)"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a document."""
    audit_logger = get_audit_logger()
    request_id = getattr(request.state, "request_id", "unknown")

    # Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    # Validate file extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {suffix}. Supported: {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    # Read with size limit
    data, too_large = await _read_upload_file_limited(file, _MAX_UPLOAD_FILE_BYTES)
    if too_large:
        audit_logger.log(
            AuditEvent(
                event_type=AuditEventType.SECURITY_RATE_LIMIT,
                level=AuditLevel.MEDIUM,
                user_id=user.id,
                resource="/documents/upload",
                action="upload",
                result="failure",
                request_id=request_id,
                metadata={"reason": "file_too_large", "filename": file.filename},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {_MAX_UPLOAD_FILE_BYTES // (1024 * 1024)}MB)",
        )

    try:
        # Save file to storage
        storage = get_document_storage()
        file_content = BytesIO(data)
        # Create a new UploadFile-like object with the read data
        upload_file = UploadFile(
            filename=file.filename,
            file=file_content,
        )
        storage_path, unique_filename, file_size = await storage.save_file(user.id, upload_file)

        # Parse expiry date
        parsed_expiry = None
        if expiry_date:
            from datetime import datetime

            try:
                parsed_expiry = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
            except ValueError:
                pass  # Invalid date format, ignore

        # Get MIME type
        file_type = storage.get_file_type(file.filename)

        # Parse tags
        parsed_tags = _parse_tags(tags)

        # Create database record
        repo = DocumentRepository(session)
        document = await repo.create(
            user_id=user.id,
            filename=unique_filename,
            original_filename=file.filename,
            storage_path=storage_path,
            file_type=file_type,
            file_size=file_size,
            property_id=property_id,
            category=category,
            tags=parsed_tags,
            description=description,
            expiry_date=parsed_expiry,
        )

        # Log successful upload
        audit_logger.log_data_access(
            operation="upload",
            resource="/documents/upload",
            client_id=user.id,
            result="success",
            request_id=request_id,
            metadata={
                "document_id": document.id,
                "filename": file.filename,
                "size": file_size,
                "category": category,
            },
        )

        # Trigger OCR processing asynchronously (don't wait)
        # In production, this would be a background task
        # For now, we'll process it synchronously for simplicity
        ocr_service = get_ocr_service()
        if ocr_service.is_available():
            try:
                extracted_text, ocr_error = await ocr_service.extract_text(storage_path, file_type)
                if extracted_text:
                    await repo.update(
                        document, ocr_status="completed", extracted_text=extracted_text
                    )
                elif ocr_error:
                    await repo.update(document, ocr_status="failed")
                    logger.warning(
                        "OCR failed for document %s: %s",
                        sanitize_for_log(document.id),
                        sanitize_for_log(ocr_error),
                    )
                else:
                    await repo.update(document, ocr_status="completed")
            except Exception as e:
                logger.error("OCR processing failed: %s", sanitize_for_log(e))
                await repo.update(document, ocr_status="failed")

        return DocumentUploadResponse(
            id=document.id,
            filename=unique_filename,
            original_filename=file.filename,
            file_type=file_type,
            file_size=file_size,
            message="Document uploaded successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Document upload failed: %s", sanitize_for_log(e), exc_info=True)
        audit_logger.log(
            AuditEvent(
                event_type=AuditEventType.API_ERROR,
                level=AuditLevel.HIGH,
                user_id=user.id,
                resource="/documents/upload",
                action="upload",
                result="error",
                request_id=request_id,
                metadata={"error": str(e)},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document",
        ) from e


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
    description="List all documents for the current user with optional filters.",
)
async def list_documents(
    request: Request,
    property_id: Optional[str] = Query(None, description="Filter by property ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    ocr_status: Optional[str] = Query(None, description="Filter by OCR status"),
    search_query: Optional[str] = Query(None, description="Search in filename/description"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List documents for the current user."""
    # Validate sort_by to prevent attribute access on unexpected ORM fields
    _allowed_doc_sort = {"created_at", "updated_at", "filename", "file_size", "category"}
    if sort_by not in _allowed_doc_sort:
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort_by}")

    repo = DocumentRepository(session)

    offset = (page - 1) * page_size

    documents = await repo.get_by_user(
        user_id=user.id,
        property_id=property_id,
        category=category,
        ocr_status=ocr_status,
        search_query=search_query,
        limit=page_size,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total = await repo.count_by_user(
        user_id=user.id,
        property_id=property_id,
        category=category,
        ocr_status=ocr_status,
        search_query=search_query,
    )

    # Convert to response models
    items = []
    for doc in documents:
        doc_dict = _document_to_response(doc)
        items.append(DocumentResponse(**doc_dict))

    total_pages = (total + page_size - 1) // page_size

    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def _document_to_response(doc: DocumentDB) -> dict:
    """Convert DocumentDB to response dict."""
    tags_list = None
    if doc.tags:
        try:
            tags_list = json.loads(doc.tags)
        except (json.JSONDecodeError, TypeError):
            tags_list = None

    return {
        "id": doc.id,
        "user_id": doc.user_id,
        "property_id": doc.property_id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "category": doc.category,
        "tags": tags_list,
        "description": doc.description,
        "expiry_date": doc.expiry_date,
        "ocr_status": doc.ocr_status,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


@router.get(
    "/expiring",
    response_model=ExpiringDocumentsResponse,
    summary="Get expiring documents",
    description="Get documents that will expire within the specified number of days.",
)
async def get_expiring_documents(
    request: Request,
    days_ahead: int = Query(30, ge=1, le=365, description="Days ahead to check"),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ExpiringDocumentsResponse:
    """Get documents expiring soon."""
    repo = DocumentRepository(session)

    documents = await repo.get_expiring_soon(
        user_id=user.id,
        days_ahead=days_ahead,
        limit=limit,
    )

    items = [DocumentResponse(**_document_to_response(doc)) for doc in documents]

    return ExpiringDocumentsResponse(
        items=items,
        total=len(items),
        days_ahead=days_ahead,
    )


@router.get(
    "/{document_id}",
    summary="Download a document",
    description="Download a previously uploaded document.",
    responses={
        200: {"description": "Document file", "content": {"application/octet-stream": {}}},
    },
)
async def download_document(
    document_id: str,
    request: Request,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
):
    """Download a document."""
    audit_logger = get_audit_logger()
    request_id = getattr(request.state, "request_id", "unknown")

    repo = DocumentRepository(session)
    document = await repo.get_by_id(document_id, user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        storage = get_document_storage()
        content = await storage.read_file(document.storage_path)

        # Log download
        audit_logger.log_data_access(
            operation="read",
            resource=f"/documents/{sanitize_for_log(document_id)}",
            client_id=sanitize_for_log(user.id),
            result="success",
            request_id=request_id,
        )

        return StreamingResponse(
            BytesIO(content),
            media_type=document.file_type,
            headers={"Content-Disposition": f'attachment; filename="{document.original_filename}"'},
        )

    except Exception as e:
        logger.error(
            "Failed to read document %s: %s", sanitize_for_log(document_id), sanitize_for_log(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read document",
        ) from e


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update document metadata",
    description="Update document category, tags, description, or expiry date.",
)
async def update_document(
    document_id: str,
    request: Request,
    body: DocumentUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Update document metadata."""
    repo = DocumentRepository(session)
    document = await repo.get_by_id(document_id, user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        return DocumentResponse(**_document_to_response(document))

    document = await repo.update(document, **update_data)
    return DocumentResponse(**_document_to_response(document))


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Delete a document and its associated file.",
)
async def delete_document(
    document_id: str,
    request: Request,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
):
    """Delete a document."""
    audit_logger = get_audit_logger()
    request_id = getattr(request.state, "request_id", "unknown")

    repo = DocumentRepository(session)
    document = await repo.get_by_id(document_id, user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    try:
        # Delete file from storage
        storage = get_document_storage()
        await storage.delete_file(document.storage_path)

        # Delete database record
        await repo.delete(document)

        # Log deletion
        audit_logger.log_data_access(
            operation="delete",
            resource=f"/documents/{sanitize_for_log(document_id)}",
            client_id=sanitize_for_log(user.id),
            result="success",
            request_id=sanitize_for_log(request_id) if request_id else None,
        )

        return None

    except Exception as e:
        logger.error(
            "Failed to delete document %s: %s", sanitize_for_log(document_id), sanitize_for_log(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        ) from e
