"""E-signature service for document signing.

This module provides:
1. Protocol-based abstraction for e-signature providers
2. HelloSign implementation
3. Service factory
"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


# =============================================================================
# Protocol for E-Signature Providers
# =============================================================================


@runtime_checkable
class ESignatureService(Protocol):
    """Protocol for e-signature provider integration."""

    def create_envelope(
        self,
        document_path: Path,
        signers: list[dict[str, str]],
        title: str,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        expires_days: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Create a signature request envelope.

        Args:
            document_path: Path to the PDF document to sign
            signers: List of signer dicts with email, name, role, order
            title: Title of the document
            subject: Optional email subject
            message: Optional email message
            metadata: Optional metadata to attach (for webhook identification)
            expires_days: Optional days until expiry

        Returns:
            Dictionary with envelope_id and other provider data
        """
        ...

    def get_envelope_status(self, envelope_id: str) -> dict[str, Any]:
        """
        Get the current status of an envelope.

        Args:
            envelope_id: Provider's envelope ID

        Returns:
            Dictionary with status and signer information
        """
        ...

    def download_signed_document(self, envelope_id: str) -> bytes:
        """
        Download the signed document.

        Args:
            envelope_id: Provider's envelope ID

        Returns:
            PDF content as bytes
        """
        ...

    def cancel_envelope(self, envelope_id: str) -> bool:
        """
        Cancel a signature request.

        Args:
            envelope_id: Provider's envelope ID

        Returns:
            True if cancelled successfully
        """
        ...

    def send_reminder(self, envelope_id: str) -> bool:
        """
        Send a reminder email to pending signers.

        Args:
            envelope_id: Provider's envelope ID

        Returns:
            True if reminder sent successfully
        """
        ...

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify webhook callback signature.

        Args:
            payload: Raw request body
            signature: Signature header
            timestamp: Timestamp header (if used)

        Returns:
            True if signature is valid
        """
        ...

    def is_available(self) -> bool:
        """Check if the service is properly configured."""
        ...

    def get_provider_name(self) -> str:
        """Return the provider name."""
        ...


# =============================================================================
# HelloSign Implementation
# =============================================================================


class HelloSignService:
    """HelloSign (Dropbox Sign) e-signature provider implementation."""

    BASE_URL: str = "https://api.hellosign.com/v3"
    SANDBOX_URL: str = "https://api.sandbox.hellosign.com/v3"

    def __init__(
        self,
        api_key: str,
        client_id: Optional[str] = None,
        test_mode: bool = False,
        webhook_secret: Optional[str] = None,
    ):
        """
        Initialize HelloSign service.

        Args:
            api_key: HelloSign API key
            client_id: Optional OAuth client ID
            test_mode: Use sandbox environment
            webhook_secret: Secret for webhook signature verification
        """
        self.api_key = api_key
        self.client_id = client_id
        self.test_mode = test_mode
        self.webhook_secret = webhook_secret
        self.base_url = self.SANDBOX_URL if test_mode else self.BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        self._setup_client()

    def _setup_client(self) -> None:
        """Setup HTTP client with authentication."""
        self.client.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        if self.client_id:
            self.client.headers["Client-Id"] = self.client_id

    def is_available(self) -> bool:
        """Check if HelloSign is configured."""
        return bool(self.api_key)

    def get_provider_name(self) -> str:
        return "hellosign"

    async def create_envelope(
        self,
        document_path: Path,
        signers: list[dict[str, str]],
        title: str,
        subject: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        expires_days: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Create a signature request via HelloSign API.

        Args:
            document_path: Path to PDF document
            signers: List of signer dicts with email, name, role, order
            title: Document title
            subject: Email subject
            message: Email message
            metadata: Metadata to attach
            expires_days: Days until expiry

        Returns:
            Dictionary with envelope_id and signer URLs
        """
        try:
            # Read document
            with open(document_path, "rb") as f:
                files = {"file": (title + ".pdf", f)}

            # Prepare signers for HelloSign format
            hs_signers = []
            for idx, signer in enumerate(signers, start=1):
                hs_signers.append(
                    {
                        "email_address": signer["email"],
                        "name": signer["name"],
                        "order": idx,
                        "role": signer.get("role", "signer"),
                    }
                )

            # Build request payload
            payload = {
                "test_mode": self.test_mode,
                "title": title,
                "subject": subject or f"Please sign: {title}",
                "message": message or "Please review and sign the attached document.",
                "signers": hs_signers,
                "file": [files["file"]],
                "metadata": metadata or {},
            }

            if expires_days:
                payload["expires_at"] = int(
                    (datetime.now(UTC) + timedelta(days=expires_days)).timestamp()
                )

            # Make API request
            response = await self.client.post(
                f"{self.base_url}/signature_request",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            return {
                "envelope_id": data["signature_request_id"],
                "signer_urls": {
                    signer["email"]: data.get("signer_urls", {}).get(signer["email"])
                    for signer in signers
                },
                "status": "sent",
            }

        except httpx.HTTPStatusError as e:
            logger.error("HelloSign API error: %s", sanitize_for_log(e.response.text))
            raise RuntimeError(f"HelloSign API error: {e.response.text}") from e
        except Exception as e:
            logger.error("Error creating HelloSign envelope: %s", sanitize_for_log(e))
            raise

    async def get_envelope_status(self, envelope_id: str) -> dict[str, Any]:
        """
        Get signature request status from HelloSign.

        Args:
            envelope_id: HelloSign signature request ID

        Returns:
            Dictionary with status and signer information
        """
        try:
            response = await self.client.get(f"{self.base_url}/signature_request/{envelope_id}")
            response.raise_for_status()

            data = response.json()

            # Map HelloSign status to our status
            hs_status = data.get("status", "").lower()
            status_map = {
                "draft": "draft",
                "sent": "sent",
                "viewed": "viewed",
                "signed": "partially_signed",
                "completed": "completed",
                "expired": "expired",
                "cancelled": "cancelled",
                "declined": "declined",
            }

            # Extract signer information
            signers = []
            for signer_data in data.get("signatures", []):
                signers.append(
                    {
                        "email": signer_data.get("signer_email_address"),
                        "name": signer_data.get("signer_name"),
                        "status": signer_data.get("status", "pending").lower(),
                        "signed_at": signer_data.get("signed_at"),
                    }
                )

            return {
                "status": status_map.get(hs_status, hs_status),
                "signers": signers,
                "completed_at": data.get("completed_at"),
                "is_complete": hs_status == "completed",
            }

        except httpx.HTTPStatusError as e:
            logger.error("HelloSign API error: %s", sanitize_for_log(e.response.text))
            raise RuntimeError(f"HelloSign API error: {e.response.text}") from e
        except Exception as e:
            logger.error("Error getting HelloSign status: %s", sanitize_for_log(e))
            raise

    async def download_signed_document(self, envelope_id: str) -> bytes:
        """
        Download the completed, signed document from HelloSign.

        Args:
            envelope_id: HelloSign signature request ID

        Returns:
            PDF content as bytes
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/signature_request/{envelope_id}/files",
            )
            response.raise_for_status()

            # Get the signed file URL
            files = response.json().get("files", [])
            if not files:
                raise ValueError("No signed files available")

            # Download the first file (the signed document)
            signed_file_url = files[0].get("file_url")
            if not signed_file_url:
                raise ValueError("No signed file URL in response")

            file_response = await self.client.get(signed_file_url)
            file_response.raise_for_status()

            return file_response.content

        except httpx.HTTPStatusError as e:
            logger.error("HelloSign API error: %s", sanitize_for_log(e.response.text))
            raise RuntimeError(f"HelloSign API error: {e.response.text}") from e
        except Exception as e:
            logger.error("Error downloading signed document: %s", sanitize_for_log(e))
            raise

    async def cancel_envelope(self, envelope_id: str) -> bool:
        """
        Cancel a signature request via HelloSign.

        Args:
            envelope_id: HelloSign signature request ID

        Returns:
            True if cancelled successfully
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/signature_request/cancel/{envelope_id}"
            )
            response.raise_for_status()

            return response.status_code == 200
        except httpx.HTTPStatusError as e:
            logger.error("HelloSign API error: %s", sanitize_for_log(e.response.text))
            if e.response.status_code == 404:
                # Already completed or not found
                return False
            raise
        except Exception as e:
            logger.error("Error cancelling HelloSign envelope: %s", sanitize_for_log(e))
            return False

    async def send_reminder(self, envelope_id: str) -> bool:
        """
        Send reminder to pending signers via HelloSign.

        Args:
            envelope_id: HelloSign signature request ID

        Returns:
            True if reminder sent successfully
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/signature_request/remind/{envelope_id}"
            )
            response.raise_for_status()

            return response.status_code == 200
        except httpx.HTTPStatusError as e:
            logger.error("HelloSign API error: %s", sanitize_for_log(e.response.text))
            return False
        except Exception as e:
            logger.error("Error sending HelloSign reminder: %s", sanitize_for_log(e))
            return False

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Verify HelloSign webhook signature.

        HelloSign uses HMAC-SHA256 for webhook signature verification.

        Args:
            payload: Raw request body bytes
            signature: Signature from HelloSign-Signature header
            timestamp: Timestamp from HelloSign-Timestamp header

        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping signature verification")
            return True  # Allow in development

        try:
            # HelloSign uses hex-encoded HMAC-SHA256
            expected_sig = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(signature.encode(), expected_sig.encode())
        except Exception as e:
            logger.error("Error verifying webhook signature: %s", sanitize_for_log(e))
            return False


# =============================================================================
# Service Factory
# =============================================================================


_esignature_service: Optional[ESignatureService] = None


def get_esignature_service() -> Optional[ESignatureService]:
    """Get the e-signature service instance.

    Returns:
        Configured ESignatureService or None if not configured
    """
    from config.settings import settings

    global _esignature_service

    if _esignature_service is None:
        if settings.hellosign_api_key:
            _esignature_service = HelloSignService(  # type: ignore[assignment]
                api_key=settings.hellosign_api_key,
                test_mode=settings.environment == "development",
                webhook_secret=settings.hellosign_webhook_secret,
            )

    return _esignature_service
