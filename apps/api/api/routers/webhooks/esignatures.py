"""Webhook handlers for e-signature provider callbacks.

Task #57: E-Signature Integration

Handles webhook callbacks from HelloSign (Dropbox Sign) to update signature request status.
"""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from api.audit import AuditEvent, AuditEventType, AuditLevel, get_audit_logger
from config.settings import settings
from core.security_utils import sanitize_for_log
from db.database import get_db
from db.repositories import SignatureRequestRepository, SignedDocumentRepository
from services.esignature_service import get_esignature_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/esignatures", tags=["Webhooks"])


def _verify_hellosign_signature(
    payload: bytes,
    signature: str,
    timestamp: Optional[str] = None,
) -> bool:
    """Verify HelloSign webhook signature."""
    if not settings.hellosign_webhook_secret:
        logger.warning("No webhook secret configured, skipping signature verification")
        return True  # Allow in development

    try:
        # HelloSign uses hex-encoded HMAC-SHA256
        expected_sig = hmac.new(
            settings.hellosign_webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature.encode(), expected_sig.encode())
    except Exception as e:
        logger.error("Error verifying webhook signature: %s", sanitize_for_log(e))
        return False


@router.post(
    "/hellosign",
    status_code=status.HTTP_200_OK,
    summary="Handle HelloSign webhook",
    description="Receive and process HelloSign webhook callbacks.",
)
async def handle_hellosign_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Handle HelloSign webhook callback."""
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("HelloSign-Signature", "")
    timestamp = request.headers.get("HelloSign-Timestamp")

    # Verify signature
    if not _verify_hellosign_signature(body, signature, timestamp):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # Parse payload
    try:
        payload_str = body.decode("utf-8")
        data = json.loads(payload_str)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse webhook payload: %s", sanitize_for_log(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        ) from None

    event_type = data.get("event", {}).get("event_type")
    if not event_type:
        event_type = data.get("event_type")

    logger.info("Received HelloSign webhook: %s", sanitize_for_log(event_type))

    # Get the signature request by provider envelope ID
    envelope_id = data.get("signature_request", {}).get("signature_request_id")
    if not envelope_id:
        metadata = data.get("signature_request", {}).get("metadata", {})
        envelope_id = metadata.get("request_id")

    if not envelope_id:
        logger.warning("No envelope ID in webhook payload")
        return {"status": "ignored", "reason": "no_envelope_id"}

    repo = SignatureRequestRepository(session)
    signature_request = await repo.get_by_provider_envelope_id("hellosign", envelope_id)

    if not signature_request:
        logger.warning(
            "Signature request not found for envelope: %s", sanitize_for_log(envelope_id)
        )
        return {"status": "ignored", "reason": "not_found"}

    # Update signature request based on event type
    now = datetime.now(UTC)

    if event_type == "signature_request_sent":
        signature_request.status = "sent"
        signature_request.sent_at = now

    elif event_type == "signature_request_viewed":
        signature_request.status = "viewed"
        signature_request.viewed_at = now

    elif event_type == "signature_request_signed":
        signer_data = data.get("signature_request", {}).get("signatures", [])
        for sig in signer_data:
            signer_email = sig.get("signer_email_address")
            if signer_email:
                for signer in signature_request.signers:
                    if signer["email"] == signer_email:
                        signer["status"] = "signed"
                        signer["signed_at"] = now
                        break

        all_signed = all(s.get("status") == "signed" for s in signature_request.signers)
        if all_signed:
            signature_request.status = "completed"
            signature_request.completed_at = now
        else:
            signature_request.status = "partially_signed"

    elif event_type == "signature_request_declined":
        signature_request.status = "declined"
        signer_data = data.get("signature_request", {}).get("signatures", [])
        for sig in signer_data:
            signer_email = sig.get("signer_email_address")
            if signer_email:
                for signer in signature_request.signers:
                    if signer["email"] == signer_email:
                        signer["status"] = "declined"
                        break

    elif event_type == "signature_request_canceled":
        signature_request.status = "cancelled"
        signature_request.cancelled_at = now

    elif event_type == "file_error":
        logger.error("HelloSign file error for envelope: %s", sanitize_for_log(envelope_id))
        signature_request.error_message = sanitize_for_log(data.get("error", "Unknown error"))

    else:
        logger.info("Unhandled event type: %s", sanitize_for_log(event_type))
        return {"status": "ignored", "reason": "unhandled_event"}

    await session.flush()

    # Log audit event
    audit_logger = get_audit_logger()
    await audit_logger.log_event(  # type: ignore[attr-defined]
        AuditEvent(
            event_type=AuditEventType.DOCUMENT_SIGNED,  # type: ignore[attr-defined]
            level=AuditLevel.INFO,
            user_id=signature_request.user_id,
            resource=f"signature_request:{signature_request.id}",
            action=f"Signature request {event_type}: {signature_request.title}",
            result="success",
            metadata={
                "event_type": event_type,
                "status": signature_request.status,
                "provider_envelope_id": envelope_id,
            },
        )
    )

    # If completed, download and store the signed document
    if signature_request.status == "completed":
        esignature_service = get_esignature_service()
        if esignature_service:
            try:
                await _download_and_store_signed_document(
                    session=session,
                    signature_request=signature_request,
                    esignature_service=esignature_service,
                )
            except Exception as e:
                logger.error("Failed to download signed document: %s", sanitize_for_log(e))

    return {"status": "processed", "event_type": event_type}


async def _download_and_store_signed_document(
    session: AsyncSession,
    signature_request: Any,
    esignature_service: Any,
) -> None:
    """Download and store the signed document after completion."""
    from services.document_storage import get_document_storage

    try:
        pdf_content = await esignature_service.download_signed_document(
            signature_request.provider_envelope_id
        )

        storage = get_document_storage()
        user_dir = storage.user_dir / signature_request.user_id

        filename = (
            f"{signature_request.title}_signed_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        storage_path = user_dir / "signed_documents" / filename

        storage_path.parent.mkdir(parents=True, exist_ok=True)

        with open(storage_path, "wb") as f:
            f.write(pdf_content)

        signed_doc_repo = SignedDocumentRepository(session)
        await signed_doc_repo.create(
            signature_request_id=signature_request.id,
            storage_path=str(storage_path),
            file_size=len(pdf_content),
            document_id=signature_request.document_id,
            provider_document_id=signature_request.provider_envelope_id,
        )

        logger.info(
            "Stored signed document for request: %s", sanitize_for_log(signature_request.id)
        )

    except Exception as e:
        logger.error("Error storing signed document: %s", sanitize_for_log(e))
        raise
