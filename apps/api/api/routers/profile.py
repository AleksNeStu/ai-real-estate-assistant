"""Profile management router (Task #88: User Profile Management)."""

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user
from core.security_utils import sanitize_for_log
from db.database import get_db_context
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["Profile"])


# Configuration
_AVATAR_UPLOAD_DIR = "uploads/avatars"
_AVATAR_MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB
_AVATAR_ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}

# In-memory storage for export jobs (dev mode)
_export_jobs: dict[str, dict] = {}


# --- Pydantic Models ---


class ProfileUpdate(BaseModel):
    """Schema for profile update (partial)."""

    full_name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


class ProfileResponse(BaseModel):
    """Schema for profile response."""

    id: str
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"
    bio: Optional[str] = None
    privacy_settings: dict = {}
    is_active: bool = True
    is_verified: bool = False
    role: str = "user"
    created_at: datetime
    last_login_at: Optional[datetime] = None
    gdpr_consent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PrivacySettings(BaseModel):
    """Schema for privacy settings."""

    profile_visible: bool = True
    activity_visible: bool = False
    show_email: bool = False
    show_phone: bool = False
    allow_contact: bool = True


class AvatarUploadResponse(BaseModel):
    """Schema for avatar upload response."""

    avatar_url: str
    message: str = "Avatar uploaded successfully"


class DataExportRequest(BaseModel):
    """Schema for requesting GDPR data export."""

    format: str = "json"  # json or csv
    include_favorites: bool = True
    include_search_history: bool = True
    include_documents: bool = True


class DataExportResponse(BaseModel):
    """GDPR data export response."""

    export_id: str
    status: str = "pending"  # pending, processing, completed, failed
    format: str
    includes: list[str]
    created_at: datetime


class DataExportStatusResponse(BaseModel):
    """Schema for export job status."""

    export_id: str
    status: str
    progress_percent: int = 0
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# --- Helper Functions ---


def _get_export_includes(export_request: DataExportRequest) -> list[str]:
    """Get list of included data types for export."""
    includes = []
    if export_request.include_favorites:
        includes.append("favorites")
    if export_request.include_search_history:
        includes.append("saved_searches")
    if export_request.include_documents:
        includes.append("documents")
    return includes


def _delete_avatar_file(avatar_path: str) -> None:
    """Delete avatar file from storage."""
    try:
        if os.path.exists(avatar_path):
            os.remove(avatar_path)
    except Exception as e:
        logger.warning(
            "Failed to delete avatar file %s: %s",
            sanitize_for_log(avatar_path),
            sanitize_for_log(e),
        )


# --- API Endpoints ---


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user: User = Depends(get_current_active_user),
):
    """Get current user's profile."""
    return ProfileResponse.model_validate(user)


@router.put("", response_model=ProfileResponse)
async def update_profile(
    profile_update: ProfileUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_context),
):
    """Update current user's profile (partial update)."""
    update_data = profile_update.model_dump(exclude_unset=True)
    if not update_data:
        return ProfileResponse.model_validate(user)

    # Apply partial updates
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return ProfileResponse.model_validate(user)


@router.post("/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_context),
):
    """Upload avatar image."""
    # Validate file type
    if file.content_type not in _AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: PNG, JPG, WEBP",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Check file size
    if file_size > _AVATAR_MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {_AVATAR_MAX_SIZE_BYTES // (1024 * 1024)} MB",
        )

    # Validate file content (basic check for valid image header)
    header = content[:8]
    is_valid_image = (
        header.startswith(b"\x89PNG\r\n\x1a\n")  # PNG
        or header.startswith(b"\xff\xd8\xff")  # JPEG
        or header.startswith(b"RIFF")  # WEBP
    )
    if not is_valid_image:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file",
        )

    # Ensure upload directory exists
    os.makedirs(_AVATAR_UPLOAD_DIR, exist_ok=True)

    # Generate unique filename
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    file_ext = (
        file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "png"
    )
    unique_filename = f"avatar_{user.id}_{timestamp}.{file_ext}"
    avatar_path = os.path.join(_AVATAR_UPLOAD_DIR, unique_filename)

    # Save file
    with open(avatar_path, "wb") as f:
        f.write(content)

    # Generate URL
    avatar_url = f"/uploads/avatars/{unique_filename}"

    # Update user
    user.avatar_url = avatar_url
    session.add(user)
    await session.commit()

    return AvatarUploadResponse(
        avatar_url=avatar_url,
        message="Avatar uploaded successfully",
    )


@router.delete("/avatar")
async def delete_avatar(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_context),
):
    """Delete user's avatar."""
    if not user.avatar_url:
        return {"message": "No avatar to delete"}

    # Delete from storage
    if user.avatar_url:
        # Extract filename from URL
        filename = user.avatar_url.split("/")[-1]
        avatar_path = os.path.join(_AVATAR_UPLOAD_DIR, filename)
        _delete_avatar_file(avatar_path)

    # Update user
    user.avatar_url = None
    session.add(user)
    await session.commit()

    return {"message": "Avatar deleted successfully"}


@router.put("/privacy", response_model=ProfileResponse)
async def update_privacy_settings(
    privacy_settings: PrivacySettings,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_context),
):
    """Update privacy settings."""
    user.privacy_settings = privacy_settings.model_dump()
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return ProfileResponse.model_validate(user)


@router.post("/export", response_model=DataExportResponse)
async def request_data_export(
    export_request: DataExportRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_context),
):
    """Request GDPR data export (async processing)."""
    # Check rate limit (1 export per day per user)
    if user.data_export_requested_at:
        # Handle both timezone-aware and naive datetimes
        last_request = user.data_export_requested_at
        if last_request.tzinfo is None:
            # Naive datetime - assume UTC
            last_request = last_request.replace(tzinfo=UTC)
        time_since_last = datetime.now(UTC) - last_request
        if time_since_last.total_seconds() < 86400:  # 24 hours
            wait_seconds = int(86400 - time_since_last.total_seconds())
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Please wait {wait_seconds // 3600} hours before requesting another export.",
            )

    # Create export job
    export_id = f"export_{user.id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    # Initialize job status
    _export_jobs[export_id] = {
        "export_id": export_id,
        "status": "pending",
        "progress_percent": 0,
        "user_id": user.id,
        "created_at": datetime.now(UTC),
    }

    # Update user's export request timestamp
    user.data_export_requested_at = datetime.now(UTC)
    session.add(user)
    await session.commit()

    # Start background export processing
    background_tasks.add_task(
        _process_data_export,
        user.id,
        export_id,
        export_request.model_dump(),
    )

    return DataExportResponse(
        export_id=export_id,
        status="pending",
        format=export_request.format,
        includes=_get_export_includes(export_request),
        created_at=datetime.now(UTC),
    )


@router.get("/export/{export_id}", response_model=DataExportStatusResponse)
async def get_export_status(
    export_id: str,
    user: User = Depends(get_current_active_user),
):
    """Get data export job status."""
    job = _export_jobs.get(export_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    # Check if job belongs to user
    if job["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return DataExportStatusResponse(
        export_id=job["export_id"],
        status=job["status"],
        progress_percent=job["progress_percent"],
        download_url=job.get("download_url"),
        expires_at=job.get("expires_at"),
        error_message=job.get("error_message"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
    )


# --- Background Task Functions ---


async def _process_data_export(
    user_id: str,
    export_id: str,
    export_request: dict,
) -> None:
    """Process GDPR data export in background."""
    try:
        _export_jobs[export_id]["status"] = "processing"
        _export_jobs[export_id]["progress_percent"] = 10

        # Get user from database
        from db.database import get_db_context

        async with get_db_context() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError(f"User {user_id} not found")

            # Gather all user data
            export_data = {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "bio": user.bio,
                    "timezone": user.timezone,
                    "language": user.language,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                },
                "privacy_settings": user.privacy_settings,
            }

            _export_jobs[export_id]["progress_percent"] = 30

            # Add favorites if requested
            if export_request.get("include_favorites"):
                from db.repositories import FavoriteRepository

                fav_repo = FavoriteRepository(session)
                favorites = await fav_repo.get_by_user(user_id)
                export_data["favorites"] = [
                    {
                        "id": fav.id,
                        "property_id": fav.property_id,
                        "notes": fav.notes,
                        "created_at": fav.created_at.isoformat() if fav.created_at else None,
                    }
                    for fav in favorites
                ]

            _export_jobs[export_id]["progress_percent"] = 50

            # Add saved searches if requested
            if export_request.get("include_search_history"):
                from db.repositories import SavedSearchRepository

                search_repo = SavedSearchRepository(session)
                searches = await search_repo.get_by_user(user_id)
                export_data["saved_searches"] = [
                    {
                        "id": s.id,
                        "name": s.name,
                        "filters": s.filters,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in searches
                ]

            _export_jobs[export_id]["progress_percent"] = 70

            # Add documents metadata if requested
            if export_request.get("include_documents"):
                from db.models import DocumentDB

                docs_result = await session.execute(
                    select(DocumentDB).where(DocumentDB.user_id == user_id)
                )
                docs = docs_result.scalars().all()
                export_data["documents"] = [
                    {
                        "id": doc.id,
                        "original_filename": doc.original_filename,
                        "file_type": doc.file_type,
                        "category": doc.category,
                        "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    }
                    for doc in docs
                ]

            _export_jobs[export_id]["progress_percent"] = 90

        # Generate JSON export
        export_json = json.dumps(export_data, indent=2, default=str)

        # Ensure export directory exists
        export_dir = "uploads/exports"
        os.makedirs(export_dir, exist_ok=True)

        # Save to file
        export_path = os.path.join(export_dir, f"{export_id}.json")
        with open(export_path, "w") as f:
            f.write(export_json)

        # Generate download URL (expires in 24 hours)
        expires_at = datetime.now(UTC) + timedelta(hours=24)

        # Update job status
        _export_jobs[export_id].update(
            {
                "status": "completed",
                "progress_percent": 100,
                "download_url": f"/uploads/exports/{export_id}.json",
                "expires_at": expires_at,
                "completed_at": datetime.now(UTC),
            }
        )

        logger.info(
            "Data export %s completed for user %s",
            sanitize_for_log(export_id),
            sanitize_for_log(user_id),
        )

    except Exception as e:
        logger.error("Data export failed: %s", sanitize_for_log(e))
        _export_jobs[export_id].update(
            {
                "status": "failed",
                "error_message": str(e),
            }
        )
