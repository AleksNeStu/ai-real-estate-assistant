import logging
import platform
import sys
import tempfile
from pathlib import Path
from time import time
from typing import Annotated, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_vector_store
from api.models import (
    AdminVersionInfo,
    ExcelSheetsRequest,
    ExcelSheetsResponse,
    HealthCheck,
    IngestRequest,
    IngestResponse,
    NotificationsAdminStats,
    PortalAdapterInfo,
    PortalAdaptersResponse,
    PortalFiltersRequest,
    PortalIngestResponse,
    ReindexRequest,
    ReindexResponse,
)
from config.settings import settings
from core.security_utils import sanitize_for_log
from data.csv_loader import DataLoaderCsv, DataLoaderExcel
from data.excel_loader import ExcelDataLoader
from data.schemas import Property, PropertyCollection
from db.database import get_db
from notifications.alert_storage_stats import load_alert_storage_summary
from utils.property_cache import load_collection, save_collection
from vector_store.chroma_store import ChromaPropertyStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])


async def _invalidate_response_cache(request: Request) -> None:
    """Clear response cache after data mutations (Task #55)."""
    cache = getattr(request.app.state, "response_cache", None)
    if cache:
        await cache.clear_all()
        logger.info("Response cache invalidated after data mutation")


# File upload constants
_READ_CHUNK_BYTES = 1024 * 1024  # 1MB chunks
_MAX_UPLOAD_FILE_BYTES = 25 * 1024 * 1024  # 25MB max file size


async def _read_upload_file_limited(file: UploadFile, max_bytes: int) -> tuple[bytes, bool]:
    """Read upload file with size limit. Returns (data, too_large)."""
    buf = bytearray()
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            return bytes(buf), False
        if len(buf) + len(chunk) > max_bytes:
            return bytes(buf), True
        buf.extend(chunk)


def _format_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


@router.get("/admin/version", response_model=AdminVersionInfo)
async def admin_version_info() -> AdminVersionInfo:
    return AdminVersionInfo(
        version=settings.version,
        environment=settings.environment,
        app_title=settings.app_title,
        python_version=_format_python_version(),
        platform=platform.platform(),
    )


@router.post("/admin/ingest", response_model=IngestResponse)
async def ingest_data(request: IngestRequest, http_request: Request):
    """
    Trigger data ingestion from URLs.
    Downloads CSV/Excel files, processes them, and saves to local cache.
    Does NOT automatically reindex vector store (call /reindex for that).
    Enforces max_properties limit from settings.
    """
    urls = request.file_urls or settings.default_datasets
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided and no defaults configured")

    try:
        all_properties: list[Property] = []
        errors = []
        max_properties = settings.max_properties

        for url in urls:
            try:
                # Detect source type and choose appropriate loader
                source_type = DataLoaderExcel.detect_source_type(url)
                source_name = request.source_name or url

                remaining_capacity = max(0, max_properties - len(all_properties))

                if source_type == "excel":
                    excel_ldr = ExcelDataLoader(
                        url,
                        sheet_name=request.sheet_name,
                        header_row=request.header_row or 0,
                        max_rows=remaining_capacity,
                    )
                    df_formatted = excel_ldr.load_normalized()
                else:
                    loader = DataLoaderCsv(url)
                    df = loader.load_df()
                    df_formatted = loader.load_format_df(df, rows_count=remaining_capacity)

                # Convert to Property objects
                # We use to_dict('records') and validate with Pydantic
                records = df_formatted.to_dict(orient="records")
                props = []
                for record in records:
                    try:
                        # Add source tracking to each property
                        if "source_url" not in record or pd.isna(record.get("source_url")):
                            record["source_url"] = source_name
                        if "source_platform" not in record or pd.isna(
                            record.get("source_platform")
                        ):
                            record["source_platform"] = source_type
                        props.append(Property(**record))
                    except Exception as e:
                        # Log skipped records for debugging (sanitize to avoid PII exposure)
                        record_id = record.get("id", record.get("title", "unknown"))
                        logger.warning(
                            "Skipped invalid property record during ingestion",
                            extra={
                                "record_id": str(record_id)[:50],
                                "error_type": type(e).__name__,
                                "error": str(e)[:200],
                            },
                        )

                all_properties.extend(props)
                logger.info("Loaded %s properties from %s", len(props), sanitize_for_log(url))

                # Stop if we've reached the limit
                if len(all_properties) >= max_properties:
                    logger.warning(
                        "Reached maximum property limit (%s), stopping ingestion",
                        sanitize_for_log(max_properties),
                    )
                    break
            except Exception as e:
                msg = f"Failed to load {url}: {str(e)}"
                logger.error(msg)
                errors.append(msg)

        if not all_properties:
            raise HTTPException(status_code=500, detail="No properties could be loaded")

        # Get source type from first property (all from same source in this implementation)
        source_type_val = None
        source_name_val = None
        if all_properties:
            if all_properties[0].source_platform:
                source_type_val = all_properties[0].source_platform
            if all_properties[0].source_url:
                source_name_val = all_properties[0].source_url

        collection = PropertyCollection(
            properties=all_properties,
            total_count=len(all_properties),
            source=source_name_val,
            source_type=source_type_val,
        )
        save_collection(collection)

        message = "Ingestion successful"
        if len(all_properties) >= max_properties:
            message += f" (reached maximum property limit of {max_properties})"

        return IngestResponse(
            message=message,
            properties_processed=len(all_properties),
            errors=errors,
            source_type=source_type_val,
            source_name=source_name_val,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ingestion failed: %s", sanitize_for_log(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await _invalidate_response_cache(http_request)


@router.post("/admin/excel/sheets", response_model=ExcelSheetsResponse)
async def get_excel_sheets(request: ExcelSheetsRequest):
    """
    Get sheet names from an Excel file.

    Returns available sheets and their row counts for sheet selection UI.
    """
    try:
        loader = ExcelDataLoader(request.file_url)
        sheet_names = loader.get_sheet_names()
        row_counts = {}

        # Get row count for each sheet
        for sheet in sheet_names:
            try:
                sheet_loader = ExcelDataLoader(request.file_url, sheet_name=sheet)
                df = sheet_loader.load()
                row_counts[sheet] = len(df)
            except Exception as e:
                logger.warning(
                    "Could not read sheet '%s': %s", sanitize_for_log(sheet), sanitize_for_log(e)
                )
                row_counts[sheet] = 0

        # Determine default sheet (first non-empty sheet)
        default_sheet = None
        for sheet, count in row_counts.items():
            if count > 0:
                default_sheet = sheet
                break
        if not default_sheet and sheet_names:
            default_sheet = sheet_names[0]

        return ExcelSheetsResponse(
            file_url=request.file_url,
            sheet_names=sheet_names,
            default_sheet=default_sheet,
            row_count=row_counts,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Excel libraries not available: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to get Excel sheets: %s", sanitize_for_log(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/admin/excel/sheets/upload", response_model=ExcelSheetsResponse)
async def get_excel_sheets_upload(
    file: UploadFile = File(..., description="Excel file to inspect"),
):
    """
    Get sheet names from an uploaded Excel file.

    Returns available sheets and their row counts for sheet selection UI.
    Supports: .xlsx, .xls, .ods files.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".xlsx", ".xls", ".ods"}:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {suffix}. Supported: .xlsx, .xls, .ods",
        )

    # Read file with size limit
    data, too_large = await _read_upload_file_limited(file, _MAX_UPLOAD_FILE_BYTES)
    if too_large:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {_MAX_UPLOAD_FILE_BYTES} bytes)",
        )

    # Save to temp file for processing
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        loader = ExcelDataLoader(tmp_path)
        sheet_names = loader.get_sheet_names()
        row_counts = {}

        # Get row count for each sheet
        for sheet in sheet_names:
            try:
                sheet_loader = ExcelDataLoader(tmp_path, sheet_name=sheet)
                df = sheet_loader.load()
                row_counts[sheet] = len(df)
            except Exception as e:
                logger.warning(
                    "Could not read sheet '%s': %s", sanitize_for_log(sheet), sanitize_for_log(e)
                )
                row_counts[sheet] = 0

        # Determine default sheet (first non-empty sheet)
        default_sheet = None
        for sheet, count in row_counts.items():
            if count > 0:
                default_sheet = sheet
                break
        if not default_sheet and sheet_names:
            default_sheet = sheet_names[0]

        return ExcelSheetsResponse(
            file_url=f"upload://{file.filename}",
            sheet_names=sheet_names,
            default_sheet=default_sheet,
            row_count=row_counts,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Excel libraries not available: {str(e)}",
        ) from e
    except Exception as e:
        logger.error("Failed to get Excel sheets from upload: %s", sanitize_for_log(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/admin/ingest/upload", response_model=IngestResponse)
async def ingest_file_upload(
    http_request: Request,
    file: UploadFile = File(..., description="Excel or CSV file to ingest"),
    sheet_name: Optional[str] = Form(None, description="Sheet name for Excel files"),
    header_row: int = Form(0, ge=0, description="Header row (0-indexed)"),
    source_name: Optional[str] = Form(None, description="Source identifier"),
):
    """
    Upload and ingest property data from Excel/CSV files.

    Supports: .xlsx, .xls, .ods, .csv files.
    Maximum file size: 25MB.
    Does NOT automatically reindex vector store (call /reindex for that).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    valid_extensions = {".xlsx", ".xls", ".ods", ".csv"}
    if suffix not in valid_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {suffix}. Supported: {', '.join(valid_extensions)}",
        )

    # Read file with size limit
    data, too_large = await _read_upload_file_limited(file, _MAX_UPLOAD_FILE_BYTES)
    if too_large:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {_MAX_UPLOAD_FILE_BYTES} bytes)",
        )

    # Save to temp file for processing
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        # Determine source type
        source_type = "excel" if suffix in {".xlsx", ".xls", ".ods"} else "csv"
        source_name_val = source_name or file.filename

        # Load and format data
        max_properties = settings.max_properties

        if source_type == "excel":
            excel_loader = ExcelDataLoader(
                tmp_path,
                sheet_name=sheet_name,
                header_row=header_row,
                max_rows=max_properties,
            )
            df_formatted = excel_loader.load_normalized()
        else:
            loader = DataLoaderCsv(tmp_path)
            df = loader.load_df()
            df_formatted = loader.load_format_df(df, rows_count=max_properties)

        # Convert to Property objects
        records = df_formatted.to_dict(orient="records")
        all_properties: list[Property] = []
        errors = []

        for record in records:
            try:
                # Add source tracking to each property
                if "source_url" not in record or pd.isna(record.get("source_url")):
                    record["source_url"] = source_name_val
                if "source_platform" not in record or pd.isna(record.get("source_platform")):
                    record["source_platform"] = source_type
                all_properties.append(Property(**record))
            except Exception as e:
                record_id = record.get("id", record.get("title", "unknown"))
                logger.warning(
                    "Skipped invalid property record during upload ingestion",
                    extra={
                        "record_id": str(record_id)[:50],
                        "error_type": type(e).__name__,
                        "error": str(e)[:200],
                    },
                )
                errors.append(f"Record {record_id}: {type(e).__name__}")

        if not all_properties:
            raise HTTPException(
                status_code=422,
                detail="No valid properties could be extracted from file",
            )

        # Create collection and save
        collection = PropertyCollection(
            properties=all_properties,
            total_count=len(all_properties),
            source=source_name_val,
            source_type=source_type,
        )
        save_collection(collection)

        message = f"Successfully ingested {len(all_properties)} properties from {file.filename}"
        if len(all_properties) >= max_properties:
            message += f" (reached maximum property limit of {max_properties})"

        return IngestResponse(
            message=message,
            properties_processed=len(all_properties),
            errors=errors,
            source_type=source_type,
            source_name=source_name_val,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload ingestion failed: %s", sanitize_for_log(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)
        await _invalidate_response_cache(http_request)


@router.post("/admin/reindex", response_model=ReindexResponse)
async def reindex_data(
    request: ReindexRequest,
    http_request: Request,
    store: Annotated[ChromaPropertyStore, Depends(get_vector_store)],
):
    """
    Reindex data from cache to vector store.
    """
    collection = load_collection()
    if not collection:
        raise HTTPException(
            status_code=404,
            detail="No data in cache. Run ingestion first.",
        )

    try:
        # In a real scenario, we might want to clear the collection first if
        # request.clear_existing is True.
        # Currently ChromaPropertyStore doesn't expose a clear method publicly in the
        # interface we checked.
        # We will just add documents (upsert behavior usually).

        if not store:
            raise HTTPException(status_code=503, detail="Vector store unavailable")

        store.add_properties(collection.properties)

        return ReindexResponse(message="Reindexing successful", count=len(collection.properties))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Reindexing failed: %s", sanitize_for_log(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await _invalidate_response_cache(http_request)


@router.get("/admin/health", response_model=HealthCheck)
async def admin_health_check(
    store: Annotated[ChromaPropertyStore, Depends(get_vector_store)],
):
    """
    Detailed health check for admin.
    """
    status = "healthy"

    # Check cache
    if not load_collection():
        status = "degraded (no data cache)"

    # Check vector store
    if not store:
        status = "degraded (vector store unavailable)"

    return HealthCheck(status=status, version=settings.version)


@router.get("/admin/metrics", response_model=dict)
async def admin_metrics(request: Request):
    """
    Return comprehensive API metrics for monitoring dashboard.
    """
    try:
        # Basic request metrics
        metrics = getattr(request.app.state, "metrics", {})

        # Cache stats
        response_cache = getattr(request.app.state, "response_cache", None)
        cache_stats = response_cache.get_stats() if response_cache else {}

        # Vector store stats
        vector_store = getattr(request.app.state, "vector_store", None)
        vs_stats = vector_store.get_stats() if vector_store else {}

        # Uptime
        start_time = getattr(request.app.state, "start_time", None)
        uptime = (time() - start_time) if start_time else 0

        return {
            "requests": dict(metrics),
            "cache": cache_stats,
            "vector_store": vs_stats,
            "uptime_seconds": uptime,
            "version": settings.version,
        }
    except Exception as e:
        logger.error("Metrics retrieval failed: %s", sanitize_for_log(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/admin/metrics/latency", response_model=dict)
async def admin_latency_metrics(request: Request):
    """
    Return p95 latency metrics for search and chat endpoints (Task #120).

    SLA targets:
      - search: p95 < 2000 ms
      - chat:   p95 < 8000 ms
    """
    tracker = getattr(request.app.state, "latency_tracker", None)
    if tracker is None:
        raise HTTPException(
            status_code=503,
            detail="Latency tracker not initialized",
        )
    return tracker.get_stats()


@router.get("/admin/dashboard", response_model=dict)
async def admin_dashboard(request: Request):
    """
    Aggregated admin dashboard endpoint (Task #67).

    Combines health, cache, latency, vector store, and system stats
    into a single JSON response for frontend admin panel consumption.
    """
    try:
        import psutil

        _has_psutil = True
    except ImportError:
        _has_psutil = False

    # --- Health status ---
    try:
        from api.health import get_health_status

        health = await get_health_status(include_dependencies=True)
        health_data = {
            "status": health.status.value,
            "version": health.version,
            "uptime_seconds": health.uptime_seconds,
            "dependencies": {
                name: {"status": dep.status.value, "latency_ms": dep.latency_ms}
                for name, dep in (health.dependencies or {}).items()
            },
        }
    except Exception:
        health_data = {"status": "unknown", "error": "health check unavailable"}

    # --- Cache stats ---
    response_cache = getattr(request.app.state, "response_cache", None)
    cache_data = response_cache.get_stats() if response_cache else {"enabled": False}

    # --- Latency p95 ---
    tracker = getattr(request.app.state, "latency_tracker", None)
    latency_data = tracker.get_stats() if tracker else {"available": False}

    # --- Vector store stats ---
    vector_store = getattr(request.app.state, "vector_store", None)
    vs_data = vector_store.get_stats() if vector_store else {"available": False}

    # --- Rate limiter stats ---
    rate_limiter = getattr(request.app.state, "rate_limiter", None)
    rate_limit_data = rate_limiter.get_stats() if rate_limiter else {"enabled": False}

    # --- System resources ---
    if _has_psutil:
        try:
            mem = psutil.virtual_memory()
            system_data = {
                "memory_total_mb": round(mem.total / 1024 / 1024),
                "memory_used_mb": round(mem.used / 1024 / 1024),
                "memory_percent": mem.percent,
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "disk_usage_percent": psutil.disk_usage("/").percent,
            }
        except Exception:
            system_data = {"available": False}
    else:
        system_data = {"available": False, "reason": "psutil not installed"}

    return {
        "health": health_data,
        "cache": cache_data,
        "latency": latency_data,
        "vector_store": vs_data,
        "rate_limiter": rate_limit_data,
        "system": system_data,
        "timestamp": time(),
    }


@router.get("/admin/notifications-stats", response_model=NotificationsAdminStats)
async def admin_notifications_stats(request: Request):
    try:
        scheduler = getattr(request.app.state, "scheduler", None)
        scheduler_running = False
        alerts_storage_path = ".alerts"

        if scheduler is not None:
            if hasattr(scheduler, "_thread") and scheduler._thread is not None:
                scheduler_running = bool(scheduler._thread.is_alive())
            if hasattr(scheduler, "_storage_path_alerts"):
                alerts_storage_path = str(scheduler._storage_path_alerts)

        summary = load_alert_storage_summary(alerts_storage_path)

        return NotificationsAdminStats(
            scheduler_running=scheduler_running,
            alerts_storage_path=alerts_storage_path,
            sent_alerts_total=int(summary.sent_total),
            pending_alerts_total=int(summary.pending_total),
            pending_alerts_by_type=dict(summary.pending_by_type),
            pending_alerts_oldest_created_at=summary.pending_oldest_created_at,
            pending_alerts_newest_created_at=summary.pending_newest_created_at,
        )
    except Exception as e:
        logger.error("Notifications stats retrieval failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


# Portal/API Integration Endpoints for TASK-006
@router.get("/admin/portals", response_model=PortalAdaptersResponse)
async def list_portals():
    """
    List all available portal adapters.

    Returns information about each portal including:
    - Whether it's configured (has API key if required)
    - Rate limit information
    """
    try:
        # Import here to avoid circular imports
        from data.adapters.registry import AdapterRegistry

        adapters_info = AdapterRegistry.get_all_info()

        return PortalAdaptersResponse(
            adapters=[
                PortalAdapterInfo(
                    name=info.get("name", ""),
                    display_name=info.get("display_name", ""),
                    configured=info.get("configured", False),
                    has_api_key=info.get("has_api_key", False),
                    rate_limit=info.get("rate_limit"),
                )
                for info in adapters_info
                if info is not None
            ],
            count=len([info for info in adapters_info if info is not None]),
        )
    except Exception as e:
        logger.error("Failed to list portals: %s", sanitize_for_log(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/admin/portals/fetch", response_model=PortalIngestResponse)
async def fetch_from_portal(request: PortalFiltersRequest, http_request: Request):
    """
    Fetch property data from an external portal.

    Uses the specified portal adapter to fetch properties based on filters.
    The fetched data is automatically ingested into the property cache.
    """
    try:
        # Import here to avoid circular imports
        from data.adapters import get_adapter
        from data.adapters.base import PortalFilter

        # Get the adapter
        adapter = get_adapter(request.portal)
        if not adapter:
            available = ", ".join(_get_available_portal_names())
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Portal adapter '{request.portal}' not found. Available portals: {available}"
                ),
            )

        # Build filters
        filters = PortalFilter(
            city=request.city,
            min_price=request.min_price,
            max_price=request.max_price,
            min_rooms=request.min_rooms,
            max_rooms=request.max_rooms,
            property_type=request.property_type,
            listing_type=request.listing_type,
            limit=request.limit,
        )

        # Fetch from portal
        result = adapter.fetch(filters)

        if not result.success:
            return PortalIngestResponse(
                success=False,
                message=f"Failed to fetch from portal: {'; '.join(result.errors)}",
                portal=request.portal,
                properties_processed=0,
                errors=result.errors,
                filters_applied=filters.to_dict(),
            )

        # Convert to Property objects
        all_properties: list[Property] = []
        errors = result.errors.copy()
        max_properties = settings.max_properties

        for record in result.properties:
            try:
                # Add source tracking
                if "source_url" not in record or not record.get("source_url"):
                    record["source_url"] = result.source
                if "source_platform" not in record or not record.get("source_platform"):
                    record["source_platform"] = result.source_type

                # Create Property object (will validate automatically)
                prop = Property(**record)
                all_properties.append(prop)

                # Stop if we've reached the limit
                if len(all_properties) >= max_properties:
                    logger.warning(
                        "Reached maximum property limit (%s)", sanitize_for_log(max_properties)
                    )
                    break
            except Exception as e:
                record_id = record.get("id", record.get("title", "unknown"))
                logger.warning(
                    "Skipped invalid property record from portal",
                    extra={
                        "record_id": str(record_id)[:50],
                        "portal": request.portal,
                        "error_type": type(e).__name__,
                        "error": str(e)[:200],
                    },
                )
                errors.append(f"Failed to validate property: {type(e).__name__}")

        if not all_properties:
            return PortalIngestResponse(
                success=False,
                message="No valid properties could be fetched from portal",
                portal=request.portal,
                properties_processed=0,
                errors=errors,
                filters_applied=filters.to_dict(),
            )

        # Create collection and save
        source_name_val = request.source_name or f"{request.portal}_{filters.city or 'all'}"

        collection = PropertyCollection(
            properties=all_properties,
            total_count=len(all_properties),
            source=source_name_val,
            source_type=result.source_type,
        )
        save_collection(collection)

        message = f"Successfully fetched {len(all_properties)} properties from {request.portal}"
        if len(all_properties) >= max_properties:
            message += f" (reached maximum property limit of {max_properties})"

        return PortalIngestResponse(
            success=True,
            message=message,
            portal=request.portal,
            properties_processed=len(all_properties),
            source_type=result.source_type,
            source_name=source_name_val,
            errors=errors,
            filters_applied=filters.to_dict(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Portal fetch failed: %s", sanitize_for_log(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        await _invalidate_response_cache(http_request)


def _get_available_portal_names() -> list[str]:
    """Helper to get list of available portal names."""
    try:
        from data.adapters.registry import AdapterRegistry

        return AdapterRegistry.list_adapters()
    except Exception:
        return []


# =============================================================================
# Audit Log Endpoints (Task #95)
# =============================================================================


@router.get("/audit", tags=["Audit"])
async def list_audit_logs(
    action: Optional[str] = None,
    actor_id: Optional[str] = None,
    resource: Optional[str] = None,
    request_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """Query audit log entries with filters and pagination."""
    from datetime import UTC, datetime

    from db.schemas import AuditLogEntryResponse, AuditLogListResponse
    from services.audit_service import AuditService

    st = datetime.fromisoformat(start_time).replace(tzinfo=UTC) if start_time else None
    et = datetime.fromisoformat(end_time).replace(tzinfo=UTC) if end_time else None

    service = AuditService(session)
    entries, total = await service.query(
        action=action,
        actor_id=actor_id,
        resource=resource,
        request_id=request_id,
        start_time=st,
        end_time=et,
        limit=limit,
        offset=offset,
    )
    return AuditLogListResponse(
        items=[AuditLogEntryResponse.model_validate(e) for e in entries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/audit/verify", tags=["Audit"])
async def verify_audit_chain(
    limit: int = 1000,
    session: AsyncSession = Depends(get_db),
):
    """Verify hash-chain integrity of the audit log."""
    from db.schemas import ChainVerificationResponse
    from services.audit_service import AuditService

    service = AuditService(session)
    result = await service.verify_chain(limit=limit)
    return ChainVerificationResponse(**result)


@router.get("/audit/{entry_id}", tags=["Audit"])
async def get_audit_entry(
    entry_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Get a single audit log entry by ID."""
    from db.schemas import AuditLogEntryResponse
    from services.audit_service import AuditService

    service = AuditService(session)
    entry = await service.get_by_id(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Audit entry not found")
    return AuditLogEntryResponse.model_validate(entry)
