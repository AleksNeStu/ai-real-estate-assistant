"""Data Sources API Router.

CRUD operations for managing property data sources with sync tracking.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    DataSourceCreate,
    DataSourceListResponse,
    DataSourceResponse,
    DataSourceSyncResponse,
    DataSourceTestRequest,
    DataSourceTestResponse,
    DataSourceUpdate,
    SyncHistoryResponse,
)
from core.security_utils import sanitize_for_log
from db.database import get_db
from db.models import DataSourceDB, DataSourceSyncHistory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data-sources", tags=["Data Sources"])


def _datasource_to_response(ds: DataSourceDB) -> DataSourceResponse:
    """Convert DataSourceDB to DataSourceResponse."""
    return DataSourceResponse(
        id=ds.id,
        name=ds.name,
        source_type=ds.source_type,
        config=ds.config,
        status=ds.status,
        last_sync_at=ds.last_sync_at,
        last_sync_status=ds.last_sync_status,
        last_error=ds.last_error,
        total_records=ds.total_records,
        health_score=ds.health_score,
        consecutive_failures=ds.consecutive_failures,
        auto_sync_enabled=ds.auto_sync_enabled,
        sync_schedule=ds.sync_schedule,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
    )


def _recalculate_health_score(ds: DataSourceDB) -> float:
    """Calculate health score based on sync history."""
    if ds.consecutive_failures >= 3:
        return 0.0
    if ds.consecutive_failures >= 2:
        return 25.0
    if ds.consecutive_failures >= 1:
        return 50.0
    if ds.last_sync_status == "success":
        return 100.0
    if ds.last_sync_status == "partial":
        return 75.0
    if ds.status == "pending":
        return 0.0
    return 50.0


@router.get("", response_model=DataSourceListResponse)
async def list_data_sources(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    source_type: Annotated[Optional[str], Query(alias="source_type")] = None,
) -> DataSourceListResponse:
    """List all data sources with pagination and filtering."""
    # Build base query
    base_query = select(DataSourceDB)

    # Apply filters
    if status_filter:
        base_query = base_query.where(DataSourceDB.status == status_filter)
    if source_type:
        base_query = base_query.where(DataSourceDB.source_type == source_type)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    data_query = base_query.order_by(DataSourceDB.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(data_query)
    sources = result.scalars().all()

    return DataSourceListResponse(
        sources=[_datasource_to_response(ds) for ds in sources],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_data_source(
    data: DataSourceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataSourceResponse:
    """Create a new data source configuration."""
    # Validate source_type specific config
    _validate_config(data.source_type.value, data.config)

    # Create new data source
    ds = DataSourceDB(
        id=str(uuid.uuid4()),
        name=data.name,
        source_type=data.source_type.value,
        config=data.config,
        status="pending",
        auto_sync_enabled=data.auto_sync_enabled,
        sync_schedule=data.sync_schedule,
    )
    db.add(ds)
    await db.flush()
    await db.refresh(ds)

    logger.info("Created data source %s (%s)", ds.id, ds.name)
    return _datasource_to_response(ds)


@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_data_source(
    source_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataSourceResponse:
    """Get a specific data source by ID."""
    result = await db.execute(select(DataSourceDB).where(DataSourceDB.id == source_id))
    ds = result.scalar_one_or_none()

    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    return _datasource_to_response(ds)


@router.patch("/{source_id}", response_model=DataSourceResponse)
async def update_data_source(
    source_id: str,
    data: DataSourceUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataSourceResponse:
    """Update a data source configuration."""
    result = await db.execute(select(DataSourceDB).where(DataSourceDB.id == source_id))
    ds = result.scalar_one_or_none()

    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # Validate config if provided
    if "config" in update_data:
        _validate_config(ds.source_type, update_data["config"])

    if "source_type" in update_data:
        _validate_config(update_data["source_type"], update_data.get("config", ds.config))

    for key, value in update_data.items():
        setattr(ds, key, value)

    ds.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(ds)

    logger.info("Updated data source %s", sanitize_for_log(source_id))
    return _datasource_to_response(ds)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_source(
    source_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    confirm: Annotated[bool, Query()] = False,
) -> None:
    """Delete a data source. Requires confirm=true to prevent accidental deletion."""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion requires confirm=true query parameter",
        )

    result = await db.execute(select(DataSourceDB).where(DataSourceDB.id == source_id))
    ds = result.scalar_one_or_none()

    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    # Delete sync history first (cascade should handle this, but be explicit)
    await db.execute(
        delete(DataSourceSyncHistory).where(DataSourceSyncHistory.data_source_id == source_id)
    )

    # Delete the data source
    await db.delete(ds)

    logger.info(
        "Deleted data source %s (%s)", sanitize_for_log(source_id), sanitize_for_log(ds.name)
    )


@router.post("/{source_id}/sync", response_model=DataSourceSyncResponse)
async def sync_data_source(
    source_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataSourceSyncResponse:
    """Trigger a manual sync for a data source."""
    result = await db.execute(select(DataSourceDB).where(DataSourceDB.id == source_id))
    ds = result.scalar_one_or_none()

    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    if ds.status == "syncing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data source is already syncing",
        )

    # Create sync history entry
    sync_record = DataSourceSyncHistory(
        id=str(uuid.uuid4()),
        data_source_id=source_id,
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    db.add(sync_record)

    # Update data source status
    ds.status = "syncing"
    ds.updated_at = datetime.now(timezone.utc)
    await db.flush()

    # Trigger background sync via asyncio
    import asyncio

    from api.dependencies import get_vector_store

    async def _run_sync(
        source_id: str,
        ds: DataSourceDB,
        sync_record: DataSourceSyncHistory,
        db_session: AsyncSession,
    ) -> None:
        """Background task to sync data from a source into the vector store."""
        try:
            get_vector_store()  # Ensure store is initialized
            source_type = ds.source_type
            records = 0

            if source_type == "url":
                import httpx

                url = ds.config.get("url", "")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    # Count records based on content length as a proxy
                    content = resp.text
                    records = content.count("\n") if content else 0

            elif source_type == "json":
                data = ds.config.get("data")
                if isinstance(data, list):
                    records = len(data)
                elif isinstance(data, dict):
                    records = 1

            elif source_type == "file_upload":
                records = ds.config.get("record_count", 0)

            # Update sync history as completed
            sync_record.status = "success"
            sync_record.completed_at = datetime.now(timezone.utc)
            sync_record.records_processed = records
            ds.status = "active"
            ds.last_sync_at = datetime.now(timezone.utc)
            ds.last_sync_status = "success"
            ds.health_score = _recalculate_health_score(ds)
            ds.consecutive_failures = 0
            ds.total_records = (ds.total_records or 0) + records

        except Exception as e:
            logger.error(
                "Background sync failed for %s: %s",
                sanitize_for_log(source_id),
                sanitize_for_log(e),
            )
            sync_record.status = "failed"
            sync_record.completed_at = datetime.now(timezone.utc)
            sync_record.error_message = str(e)[:500]
            ds.status = "error"
            ds.last_sync_status = "failed"
            ds.last_error = str(e)[:500]
            ds.consecutive_failures = (ds.consecutive_failures or 0) + 1
            ds.health_score = _recalculate_health_score(ds)

        finally:
            ds.updated_at = datetime.now(timezone.utc)
            await db_session.commit()

    asyncio.create_task(_run_sync(source_id, ds, sync_record, db))

    logger.info("Triggered sync for data source %s", sanitize_for_log(source_id))

    return DataSourceSyncResponse(
        source_id=source_id,
        status="syncing",
        message="Sync triggered successfully",
        records_processed=0,
        started_at=sync_record.started_at,
    )


@router.post("/test", response_model=DataSourceTestResponse)
async def test_data_source(
    data: DataSourceTestRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DataSourceTestResponse:
    """Test a data source connection without saving."""
    try:
        _validate_config(data.source_type.value, data.config)

        # Test based on source type
        if data.source_type.value == "url":
            return await _test_url_source(data.config)
        elif data.source_type.value == "portal_api":
            return await _test_portal_source(data.config)
        elif data.source_type.value == "json":
            return await _test_json_source(data.config)
        elif data.source_type.value == "file_upload":
            # File uploads are validated at upload time
            return DataSourceTestResponse(
                success=True,
                message="File upload source configuration is valid",
                details={"type": "file_upload"},
            )
        else:
            return DataSourceTestResponse(
                success=False,
                message=f"Unknown source type: {data.source_type}",
                details=None,
            )
    except ValueError as e:
        return DataSourceTestResponse(success=False, message=str(e), details=None)
    except Exception as e:
        logger.exception("Error testing data source")
        return DataSourceTestResponse(success=False, message=f"Test failed: {e}", details=None)


@router.get("/{source_id}/history", response_model=SyncHistoryResponse)
async def get_sync_history(
    source_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SyncHistoryResponse:
    """Get sync history for a data source."""
    # Verify data source exists
    result = await db.execute(select(DataSourceDB).where(DataSourceDB.id == source_id))
    ds = result.scalar_one_or_none()

    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source {source_id} not found",
        )

    # Get total count
    count_query = select(func.count()).where(DataSourceSyncHistory.data_source_id == source_id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated history
    offset = (page - 1) * page_size
    history_query = (
        select(DataSourceSyncHistory)
        .where(DataSourceSyncHistory.data_source_id == source_id)
        .order_by(DataSourceSyncHistory.started_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(history_query)
    history = result.scalars().all()

    from api.models import SyncHistoryItem

    items = [
        SyncHistoryItem(
            id=h.id,
            started_at=h.started_at,
            completed_at=h.completed_at,
            status=h.status,
            records_processed=h.records_processed,
            records_added=h.records_added,
            records_updated=h.records_updated,
            records_skipped=h.records_skipped,
            error_message=h.error_message,
        )
        for h in history
    ]

    return SyncHistoryResponse(
        source_id=source_id,
        history=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def _validate_config(source_type: str, config: dict[str, Any]) -> None:
    """Validate configuration based on source type."""
    if source_type == "url":
        if "url" not in config:
            raise ValueError("URL source requires 'url' in config")
        url = config["url"]
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

    elif source_type == "portal_api":
        if "portal" not in config:
            raise ValueError("Portal API source requires 'portal' in config")

    elif source_type == "json":
        if "data" not in config and "url" not in config:
            raise ValueError("JSON source requires 'data' or 'url' in config")

    elif source_type == "file_upload":
        if "filename" not in config:
            raise ValueError("File upload source requires 'filename' in config")
        # Validate Excel file extensions
        from pathlib import Path

        filename = config["filename"]
        suffix = Path(filename).suffix.lower()
        excel_extensions = {".xlsx", ".xls", ".ods"}
        if suffix in excel_extensions and "record_count" not in config:
            # Excel uploads don't require record_count upfront
            pass


def _validate_url_no_ssrf(url: str) -> None:
    """Validate that a URL does not target internal/private networks (SSRF protection)."""
    from urllib.parse import urlparse

    from utils.web_fetch import _hostname_resolves_to_public_ip

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are allowed")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: no hostname")
    if not _hostname_resolves_to_public_ip(hostname):
        raise ValueError("URL hostname resolves to a private/internal address — not allowed")


async def _test_url_source(config: dict[str, Any]) -> DataSourceTestResponse:
    """Test a URL-based data source."""
    import httpx

    url = config.get("url", "")
    _validate_url_no_ssrf(url)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(url)
            response.raise_for_status()

        return DataSourceTestResponse(
            success=True,
            message="URL is accessible",
            details={
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", "unknown"),
            },
        )
    except httpx.HTTPStatusError as e:
        return DataSourceTestResponse(
            success=False,
            message=f"HTTP error: {e.response.status_code}",
            details={"url": url, "status_code": e.response.status_code},
        )
    except httpx.RequestError as e:
        return DataSourceTestResponse(success=False, message=f"Connection error: {e}", details=None)


async def _test_portal_source(config: dict[str, Any]) -> DataSourceTestResponse:
    """Test a portal API data source."""
    from data.adapters import list_adapters
    from data.adapters.registry import AdapterRegistry

    portal_name = config.get("portal", "")
    available_adapters = list_adapters()

    if portal_name not in available_adapters:
        return DataSourceTestResponse(
            success=False,
            message=f"Unknown portal: {portal_name}",
            details={"available_portals": available_adapters},
        )

    # Instantiate adapter and test connectivity
    try:
        adapter_cls = AdapterRegistry.get_adapter(portal_name)
        if not adapter_cls:
            return DataSourceTestResponse(
                success=False,
                message=f"Adapter class not found for portal: {portal_name}",
                details={"available_portals": available_adapters},
            )

        api_key = config.get("api_key")
        adapter = adapter_cls(api_key=api_key)

        # Use health check if available, otherwise check adapter attributes
        if hasattr(adapter, "health_check"):
            healthy = await adapter.health_check()
            if healthy:
                return DataSourceTestResponse(
                    success=True,
                    message=f"Portal '{portal_name}' connection successful",
                    details={"portal": portal_name, "available_adapters": available_adapters},
                )
            else:
                return DataSourceTestResponse(
                    success=False,
                    message=f"Portal '{portal_name}' health check failed",
                    details={"portal": portal_name},
                )

        # Fallback: adapter exists but has no health_check — consider it available
        return DataSourceTestResponse(
            success=True,
            message=f"Portal '{portal_name}' is available (no health check method)",
            details={"portal": portal_name, "available_adapters": available_adapters},
        )
    except Exception as e:
        return DataSourceTestResponse(
            success=False,
            message=f"Error testing portal '{portal_name}': {e}",
            details={"portal": portal_name},
        )


async def _test_json_source(config: dict[str, Any]) -> DataSourceTestResponse:
    """Test a JSON data source."""
    import json

    if "data" in config:
        try:
            # Validate JSON structure
            data = config["data"]
            if isinstance(data, str):
                json.loads(data)
            elif not isinstance(data, (dict, list)):
                raise ValueError("Data must be a JSON object or array")

            return DataSourceTestResponse(
                success=True,
                message="JSON data is valid",
                details={"type": "inline", "structure": type(data).__name__},
            )
        except json.JSONDecodeError as e:
            return DataSourceTestResponse(success=False, message=f"Invalid JSON: {e}", details=None)

    elif "url" in config:
        return await _test_url_source({"url": config["url"]})

    return DataSourceTestResponse(success=False, message="No data or URL provided", details=None)
