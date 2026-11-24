"""Data Sources API Router.

CRUD operations for managing property data sources with sync tracking.
"""

import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
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
from config.settings import settings
from core.security_utils import sanitize_for_log
from data.schemas import Property
from db.database import get_database_url, get_db
from db.models import DataSourceDB, DataSourceSyncHistory
from services.property_import import (
    SUPPORTED_SUFFIXES,
    load_properties,
    properties_from_records,
    save_imported_properties,
    source_suffix,
)

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

    # The sync runs in a session of its own: the request that triggered it is
    # over by the time the work starts, and a record written on a closed
    # session is a record nobody can read. Its own session reads the rows the
    # request wrote, so they are committed before it starts.
    await db.commit()
    db_url = get_database_url()

    import asyncio

    asyncio.create_task(_run_sync(source_id, sync_record.id, db_url))

    logger.info("Triggered sync for data source %s", sanitize_for_log(source_id))

    return DataSourceSyncResponse(
        source_id=source_id,
        status="syncing",
        message="Sync triggered successfully",
        records_processed=0,
        started_at=sync_record.started_at,
    )


async def _run_sync(source_id: str, sync_id: str, db_url: str) -> None:
    """Sync a data source into the catalogue.

    The properties the source carries are written to the vector store (the
    place the product reads from) and to the JSON cache (the place
    ``/admin/reindex`` reads from), and ``total_records`` counts the records
    that landed - not the records that were read.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from api.dependencies import get_vector_store
    from db.database import create_engine

    engine = create_engine(db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        source_result = await session.execute(
            select(DataSourceDB).where(DataSourceDB.id == source_id)
        )
        ds = source_result.scalar_one_or_none()
        record_result = await session.execute(
            select(DataSourceSyncHistory).where(DataSourceSyncHistory.id == sync_id)
        )
        sync_record = record_result.scalar_one_or_none()

        if ds is None or sync_record is None:
            logger.error(
                "Sync %s has no data source to run against",
                sanitize_for_log(sync_id),
            )
            await engine.dispose()
            return

        try:
            properties = await _collect_properties(ds)

            store = get_vector_store()
            if store is None:
                raise RuntimeError("the vector store is unavailable")

            landed = 0
            if properties:
                landed = int(store.add_properties(properties))
                save_imported_properties(properties, ds.name, ds.source_type)

            # Update sync history as completed
            sync_record.status = "success"
            sync_record.completed_at = datetime.now(timezone.utc)
            sync_record.records_processed = landed
            ds.status = "active"
            ds.last_sync_at = datetime.now(timezone.utc)
            ds.last_sync_status = "success"
            ds.health_score = _recalculate_health_score(ds)
            ds.consecutive_failures = 0
            ds.total_records = (ds.total_records or 0) + landed

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
            await session.commit()
            await engine.dispose()


async def _collect_properties(ds: DataSourceDB) -> list[Property]:
    """Read the source into properties, through the shared import chain.

    Every source type reads the same way the bulk-job import reads: the
    loaders for a file, the records for a JSON document or a portal answer.
    """
    source_type = ds.source_type
    config = ds.config or {}

    if source_type == "file_upload":
        path = config.get("file_path") or config.get("filename")
        if not path:
            raise ValueError("a file_upload source needs 'file_path' in its config")
        properties, _errors = load_properties(
            str(path),
            sheet_name=config.get("sheet_name"),
            header_row=int(config.get("header_row") or 0),
            max_rows=settings.max_properties,
            source_name=ds.name,
            source_type="file_upload",
        )
        return properties

    if source_type == "url":
        url = str(config.get("url") or "")
        if not url:
            raise ValueError("a url source needs 'url' in its config")
        _validate_url_no_ssrf(url)
        suffix = source_suffix(url)
        if suffix == ".json":
            payload = await _fetch_url_json(url)
            return properties_from_records(
                _records_from_payload(payload),
                source_name=ds.name,
                source_type="url",
            )[0]
        if suffix not in SUPPORTED_SUFFIXES:
            raise ValueError(
                f"unsupported file type '{suffix}' - a url source reads "
                f"{sorted(SUPPORTED_SUFFIXES)} or .json"
            )
        return await _load_url_file(url, suffix, ds)

    if source_type == "json":
        payload = config.get("data")
        if payload is None and config.get("url"):
            payload = await _fetch_url_json(str(config["url"]))
        if payload is None:
            raise ValueError("a json source needs 'data' or 'url' in its config")
        return properties_from_records(
            _records_from_payload(payload),
            source_name=ds.name,
            source_type="json",
        )[0]

    if source_type == "portal_api":
        return _collect_portal_properties(ds, config)

    raise ValueError(f"unsupported source type '{source_type}'")


async def _load_url_file(url: str, suffix: str, ds: DataSourceDB) -> list[Property]:
    """Download a file and read it through the loaders."""
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        payload = response.content

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = tmp.name

    try:
        properties, _errors = load_properties(
            tmp_path,
            max_rows=settings.max_properties,
            source_name=ds.name,
            source_type="url",
        )
        return properties
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _fetch_url_json(url: str) -> Any:
    """Read a JSON document from a URL."""
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


def _records_from_payload(payload: Any) -> list[dict[str, Any]]:
    """A JSON document is either a list of records or one record."""
    if isinstance(payload, list):
        return [record for record in payload if isinstance(record, dict)]
    if isinstance(payload, dict):
        return [payload]
    raise ValueError("a json source must carry a record or a list of records")


def _collect_portal_properties(ds: DataSourceDB, config: dict[str, Any]) -> list[Property]:
    """Read a portal answer into properties, through the shared adapter."""
    from data.adapters import get_adapter
    from data.adapters.base import PortalFilter

    portal = config.get("portal")
    if not portal:
        raise ValueError("a portal_api source needs 'portal' in its config")

    adapter = get_adapter(portal)
    if adapter is None:
        raise ValueError(f"unknown portal: {portal}")

    filters = config.get("filters") or {}
    result = adapter.fetch(
        PortalFilter(
            city=config.get("city"),
            listing_type=filters.get("listing_type", "rent"),
            limit=config.get("limit", 50),
        )
    )
    return properties_from_records(
        [record for record in result.properties if isinstance(record, dict)],
        source_name=ds.name,
        source_type="portal_api",
    )[0]


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
    # Its own name: `result` already holds the data source, and reusing the
    # name for a different row type is what made mypy read the history rows
    # as data sources.
    history_result = await db.execute(history_query)
    history = history_result.scalars().all()

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
    from data.adapters.registry import AdapterRegistry

    portal_name = config.get("portal", "")
    available_adapters = AdapterRegistry.list_adapters()

    if portal_name not in available_adapters:
        return DataSourceTestResponse(
            success=False,
            message=f"Unknown portal: {portal_name}",
            details={"available_portals": available_adapters},
        )

    # Instantiate adapter and test connectivity
    try:
        adapter = AdapterRegistry.get_adapter(portal_name, api_key=config.get("api_key"))
        if not adapter:
            return DataSourceTestResponse(
                success=False,
                message=f"Adapter not found for portal: {portal_name}",
                details={"available_portals": available_adapters},
            )

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
