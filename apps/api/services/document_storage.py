"""Document storage service for file management.

This module provides services for storing, retrieving, and managing
document files in the filesystem or cloud storage.
"""

import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile

from config.settings import settings
from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

# Constants
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
MIME_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


class DocumentStorageError(Exception):
    """Exception raised for document storage errors."""

    pass


class DocumentStorageService:
    """Service for managing document file storage.

    Supports local filesystem storage with configurable base path.
    Can be extended to support S3/cloud storage in the future.
    """

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize the storage service.

        Args:
            storage_path: Base path for document storage. Defaults to
                         DOCUMENT_STORAGE_PATH from settings or 'uploads/documents'.
        """
        self.storage_path = Path(
            storage_path or getattr(settings, "DOCUMENT_STORAGE_PATH", "uploads/documents")
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(
            "DocumentStorageService initialized with path: %s", sanitize_for_log(self.storage_path)
        )

    def _get_user_dir(self, user_id: str) -> Path:
        """Get the storage directory for a specific user.

        Args:
            user_id: User's unique identifier

        Returns:
            Path to user's document directory
        """
        user_dir = self.storage_path / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _generate_filename(self, original_filename: str) -> str:
        """Generate a unique filename to prevent collisions.

        Args:
            original_filename: Original upload filename

        Returns:
            Unique filename with UUID prefix
        """
        ext = Path(original_filename).suffix.lower()
        unique_id = str(uuid4())[:8]
        base_name = Path(original_filename).stem
        # Sanitize base name
        safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in base_name)[:50]
        return f"{unique_id}_{safe_base}{ext}"

    def validate_file(self, file: UploadFile) -> tuple[bool, Optional[str]]:
        """Validate an uploaded file.

        Args:
            file: FastAPI UploadFile object

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file.filename:
            return False, "No filename provided"

        # Check extension
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Invalid file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"

        # Check content type
        expected_type = MIME_TYPE_MAP.get(ext)
        if (
            file.content_type
            and expected_type
            and not file.content_type.startswith(expected_type.split("/")[0])
        ):
            logger.warning(
                "Content type mismatch: expected %s, got %s",
                sanitize_for_log(expected_type),
                sanitize_for_log(file.content_type),
            )
            # Don't fail on mismatch, just log

        return True, None

    def get_file_type(self, filename: str) -> str:
        """Get MIME type for a filename.

        Args:
            filename: File name with extension

        Returns:
            MIME type string
        """
        ext = Path(filename).suffix.lower()
        return MIME_TYPE_MAP.get(ext, "application/octet-stream")

    async def save_file(
        self,
        user_id: str,
        file: UploadFile,
        max_size_bytes: int = MAX_FILE_SIZE_BYTES,
    ) -> tuple[str, str, int]:
        """Save an uploaded file to storage.

        Args:
            user_id: User's unique identifier
            file: FastAPI UploadFile object
            max_size_bytes: Maximum allowed file size

        Returns:
            Tuple of (storage_path, unique_filename, file_size)

        Raises:
            DocumentStorageError: If save fails
        """
        try:
            user_dir = self._get_user_dir(user_id)
            unique_filename = self._generate_filename(file.filename)
            file_path = user_dir / unique_filename

            # Read and save with size check
            size = 0
            with open(file_path, "wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_size_bytes:
                        # Clean up partial file
                        file_path.unlink(missing_ok=True)
                        raise DocumentStorageError(
                            f"File too large: {size} bytes (max {max_size_bytes})"
                        )
                    f.write(chunk)

            logger.info(
                "Saved file %s for user %s, size: %s",
                sanitize_for_log(unique_filename),
                sanitize_for_log(user_id),
                sanitize_for_log(size),
            )
            return str(file_path), unique_filename, size

        except DocumentStorageError:
            raise
        except Exception as e:
            logger.error("Failed to save file: %s", sanitize_for_log(e))
            raise DocumentStorageError(f"Failed to save file: {e}") from e

    async def read_file(self, storage_path: str) -> bytes:
        """Read a file from storage.

        Args:
            storage_path: Full path to the stored file

        Returns:
            File content as bytes

        Raises:
            DocumentStorageError: If read fails
        """
        try:
            path = Path(storage_path)
            if not path.exists():
                raise DocumentStorageError(f"File not found: {storage_path}")

            with open(path, "rb") as f:
                return f.read()

        except DocumentStorageError:
            raise
        except Exception as e:
            logger.error(
                "Failed to read file %s: %s", sanitize_for_log(storage_path), sanitize_for_log(e)
            )
            raise DocumentStorageError(f"Failed to read file: {e}") from e

    async def delete_file(self, storage_path: str) -> None:
        """Delete a file from storage.

        Args:
            storage_path: Full path to the stored file

        Raises:
            DocumentStorageError: If delete fails
        """
        try:
            path = Path(storage_path)
            if path.exists():
                path.unlink()
                logger.info("Deleted file: %s", sanitize_for_log(storage_path))
            else:
                logger.warning("File not found for deletion: %s", sanitize_for_log(storage_path))

        except Exception as e:
            logger.error(
                "Failed to delete file %s: %s", sanitize_for_log(storage_path), sanitize_for_log(e)
            )
            raise DocumentStorageError(f"Failed to delete file: {e}") from e

    async def delete_user_files(self, user_id: str) -> int:
        """Delete all files for a user.

        Args:
            user_id: User's unique identifier

        Returns:
            Number of files deleted

        Raises:
            DocumentStorageError: If delete fails
        """
        try:
            user_dir = self._get_user_dir(user_id)
            if not user_dir.exists():
                return 0

            count = 0
            for file_path in user_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
                    count += 1

            # Remove user directory
            user_dir.rmdir()
            logger.info(
                "Deleted %s files for user %s", sanitize_for_log(count), sanitize_for_log(user_id)
            )
            return count

        except Exception as e:
            logger.error("Failed to delete user files: %s", sanitize_for_log(e))
            raise DocumentStorageError(f"Failed to delete user files: {e}") from e

    def get_storage_stats(self, user_id: str) -> dict:
        """Get storage statistics for a user.

        Args:
            user_id: User's unique identifier

        Returns:
            Dictionary with storage statistics
        """
        user_dir = self._get_user_dir(user_id)
        if not user_dir.exists():
            return {"file_count": 0, "total_size_bytes": 0}

        file_count = 0
        total_size = 0

        for file_path in user_dir.iterdir():
            if file_path.is_file():
                file_count += 1
                total_size += file_path.stat().st_size

        return {
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


# Global instance
_document_storage: Optional[DocumentStorageService] = None


def get_document_storage() -> DocumentStorageService:
    """Get the global document storage service instance.

    Returns:
        DocumentStorageService instance
    """
    global _document_storage
    if _document_storage is None:
        _document_storage = DocumentStorageService()
    return _document_storage
