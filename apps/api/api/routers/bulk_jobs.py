"""Bulk Jobs API Router.

Async import/export job management with background task execution.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_vector_store
from api.models import (
    BulkExportRequest,
    BulkImportRequest,
    BulkJobCreateResponse,
    BulkJobListResponse,
    BulkJobResponse,
    BulkJobSourceType,
    BulkJobStatus,
    BulkJobType,
)
from core.security_utils import sanitize_for_log
from db.database import get_db
from db.models import BulkJob
from utils.exporters import ExportFormat, PropertyExporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bulk-jobs", tags=["Bulk Jobs"])

# Job result expiration time in hours
JOB_RESULT_EXPIRATION_HOURS = 24


def _job_to_response(job: BulkJob) -> BulkJobResponse:
    """Convert BulkJob database model to response schema."""
    return BulkJobResponse(
        id=job.id,
        job_type=job.job_type,
        source_type=job.source_type,
        status=job.status,
        records_total=job.records_total,
        records_processed=job.records_processed,
        records_failed=job.records_failed,
        progress_percent=job.progress_percent,
        result_url=job.result_url,
        result_data=job.result_data,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
    )


def _calculate_progress_percent(processed: int, total: int) -> float:
    """Calculate progress percentage safely."""
    if total <= 0:
        return 0.0
    return min(100.0, (processed / total) * 100)


async def _run_import_job(job_id: str, db_url: str) -> None:
    """Background task to execute an import job.

    Args:
        job_id: UUID of the job to execute
        db_url: Database URL for creating new session
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Fetch the job
            result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error("Job %s not found", job_id)
                return

            # Update status to running
            job.status = BulkJobStatus.RUNNING.value
            job.started_at = datetime.now(UTC)
            await db.commit()

            # Process based on source type
            source_type = job.source_type
            config = job.config

            if source_type == BulkJobSourceType.URL.value:
                await _process_url_import(job, config, db)
            elif source_type == BulkJobSourceType.FILE_UPLOAD.value:
                await _process_file_import(job, config, db)
            elif source_type == BulkJobSourceType.PORTAL_API.value:
                await _process_portal_import(job, config, db)
            else:
                job.status = BulkJobStatus.FAILED.value
                job.error_message = f"Unknown source type: {source_type}"
                job.completed_at = datetime.now(UTC)
                await db.commit()
                return

            # Mark as completed
            job.status = BulkJobStatus.COMPLETED.value
            job.progress_percent = 100.0
            job.completed_at = datetime.now(UTC)
            job.expires_at = datetime.now(UTC) + timedelta(hours=JOB_RESULT_EXPIRATION_HOURS)
            job.result_data = {
                "records_processed": job.records_processed,
                "records_failed": job.records_failed,
                "source_type": source_type,
            }
            await db.commit()
            logger.info("Job %s completed successfully", job_id)

        except Exception as e:
            logger.exception("Job %s failed", job_id)
            # Try to update job status to failed
            try:
                result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = BulkJobStatus.FAILED.value
                    job.error_message = str(e)
                    job.error_details = {"exception_type": type(e).__name__}
                    job.completed_at = datetime.now(UTC)
                    await db.commit()
            except Exception:
                logger.exception("Failed to update job status for %s", job_id)
        finally:
            await engine.dispose()


async def _process_url_import(job: BulkJob, config: dict[str, Any], db: AsyncSession) -> None:
    """Process import from URL sources (CSV, Excel, JSON)."""
    from data.loaders import DataLoaderCsv, DataLoaderExcel

    file_urls = config.get("file_urls", [])
    sheet_name = config.get("sheet_name")
    header_row = config.get("header_row", 0)

    total_records = 0
    processed_records = 0
    failed_records = 0

    job.records_total = len(file_urls)
    await db.commit()

    for url in file_urls:
        try:
            if url.endswith(".csv"):
                loader = DataLoaderCsv(url, header_row=header_row)
            elif url.endswith((".xlsx", ".xls")):
                loader = DataLoaderExcel(url, sheet_name=sheet_name, header_row=header_row)
            else:
                failed_records += 1
                continue

            records = await loader.load()
            total_records += len(records)
            processed_records += len(records)

            # Update progress
            job.records_processed = processed_records
            job.records_failed = failed_records
            job.progress_percent = _calculate_progress_percent(processed_records, total_records)
            await db.commit()

        except Exception as e:
            logger.warning("Failed to process URL %s: %s", url, e)
            failed_records += 1

    job.records_total = total_records
    job.records_processed = processed_records
    job.records_failed = failed_records


async def _process_file_import(job: BulkJob, config: dict[str, Any], db: AsyncSession) -> None:
    """Process import from uploaded files."""
    # File upload processing would integrate with the existing ingest endpoint
    # For now, we just simulate the processing
    temp_file_path = config.get("temp_file_path")
    filename = config.get("filename")

    if not temp_file_path:
        raise ValueError("temp_file_path is required for file_upload source")

    # Placeholder for actual file processing
    # In production, this would use DataLoaderCsv/DataLoaderExcel
    job.records_total = 1
    job.records_processed = 1
    job.progress_percent = 100.0
    logger.info("Processed file upload: %s", filename)


async def _process_portal_import(job: BulkJob, config: dict[str, Any], db: AsyncSession) -> None:
    """Process import from portal APIs (Overpass, etc.)."""
    from data.adapters import get_adapter

    portal = config.get("portal")
    city = config.get("city")
    filters = config.get("filters", {})
    limit = config.get("limit", 50)

    if not portal:
        raise ValueError("portal is required for portal_api source")

    try:
        adapter = get_adapter(portal)
        # Fetch data from portal
        # This is a simplified version - real implementation would
        # paginate through results
        results = await adapter.fetch_properties(
            city=city,
            listing_type=filters.get("listing_type", "rent"),
            limit=limit,
        )

        job.records_total = len(results)
        job.records_processed = len(results)
        job.progress_percent = 100.0
        logger.info("Processed portal import from %s: %d records", portal, len(results))

    except Exception as e:
        logger.error("Portal import failed: %s", e)
        raise


async def _run_export_job(job_id: str, db_url: str) -> None:
    """Background task to execute an export job.

    Args:
        job_id: UUID of the job to execute
        db_url: Database URL for creating new session
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Fetch the job
            result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error("Job %s not found", job_id)
                return

            # Update status to running
            job.status = BulkJobStatus.RUNNING.value
            job.started_at = datetime.now(UTC)
            await db.commit()

            config = job.config
            export_format = config.get("format", "json")
            columns = job.config.get("columns")
            include_header = job.config.get("include_header", True)

            # Get data from vector store
            store = get_vector_store()
            if not store:
                raise ValueError("Vector store is not available")

            documents = []
            if job.source_type == BulkJobSourceType.SEARCH.value:
                query = config.get("query", "")
                filters = config.get("filters")
                limit = config.get("limit", 100)
                results = store.hybrid_search(query=query, k=limit, filters=filters)
                documents = [doc for doc, _score in results]
            elif "property_ids" in config:
                property_ids = config["property_ids"]
                documents = store.get_properties_by_ids(property_ids)

            job.records_total = len(documents)
            job.progress_percent = 50.0
            await db.commit()

            # Convert to export rows
            rows = []
            for doc in documents:
                metadata = dict(doc.metadata or {})
                if "id" not in metadata:
                    metadata["id"] = "unknown"
                rows.append(metadata)

            # Export to format
            exporter = PropertyExporter(rows)
            format_enum = ExportFormat(export_format)

            # Generate export content (in production, upload to S3/cloud storage)
            _content = exporter.export(format_enum, columns=columns, include_header=include_header)

            # Store result summary stats
            job.result_data = {
                "format": export_format,
                "records_exported": len(rows),
                "columns": columns or list(exporter.df.columns),
            }
            job.records_processed = len(rows)
            job.progress_percent = 100.0

            # Mark as completed
            job.status = BulkJobStatus.COMPLETED.value
            job.completed_at = datetime.now(UTC)
            job.expires_at = datetime.now(UTC) + timedelta(hours=JOB_RESULT_EXPIRATION_HOURS)
            await db.commit()
            logger.info("Export job %s completed successfully", job_id)

        except Exception as e:
            logger.exception("Export job %s failed", job_id)
            try:
                result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
                job = result.scalar_one_or_none()
                if job:
                    job.status = BulkJobStatus.FAILED.value
                    job.error_message = str(e)
                    job.error_details = {"exception_type": type(e).__name__}
                    job.completed_at = datetime.now(UTC)
                    await db.commit()
            except Exception:
                logger.exception("Failed to update job status for %s", job_id)
        finally:
            await engine.dispose()


@router.post("/import", response_model=BulkJobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_import_job(
    request: BulkImportRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkJobCreateResponse:
    """Start a new bulk import job.

    The import runs in the background using FastAPI BackgroundTasks.
    Use GET /bulk-jobs/{job_id} to check progress.
    """
    # Validate config based on source type
    _validate_import_config(request.source_type, request.config)

    # Create job record
    job_id = str(uuid.uuid4())
    job = BulkJob(
        id=job_id,
        job_type=BulkJobType.IMPORT.value,
        source_type=request.source_type.value,
        config={
            **request.config,
            "source_name": request.source_name,
        },
        status=BulkJobStatus.PENDING.value,
    )
    db.add(job)
    await db.commit()

    # Get database URL for background task
    from config.settings import get_settings

    settings = get_settings()
    db_url = settings.database_url

    # Queue background task
    background_tasks.add_task(_run_import_job, job_id, db_url)

    logger.info(
        "Created import job %s (source_type=%s)",
        sanitize_for_log(job_id),
        sanitize_for_log(request.source_type),
    )

    return BulkJobCreateResponse(
        id=job_id,
        job_type=BulkJobType.IMPORT.value,
        status=BulkJobStatus.PENDING.value,
        message="Import job started",
        created_at=job.created_at,
    )


@router.post("/export", response_model=BulkJobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_export_job(
    request: BulkExportRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkJobCreateResponse:
    """Start a new bulk export job.

    The export runs in the background using FastAPI BackgroundTasks.
    Use GET /bulk-jobs/{job_id} to check progress and get download URL.
    """
    # Validate export format
    valid_formats = {"csv", "json", "xlsx", "md", "pdf", "parquet"}
    if request.format not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format '{request.format}'. Valid formats: {valid_formats}",
        )

    # Validate config
    _validate_export_config(request.source_type, request.config)

    # Create job record
    job_id = str(uuid.uuid4())
    job = BulkJob(
        id=job_id,
        job_type=BulkJobType.EXPORT.value,
        source_type=request.source_type.value,
        config={
            **request.config,
            "format": request.format,
            "columns": request.columns,
            "include_header": request.include_header,
        },
        status=BulkJobStatus.PENDING.value,
    )
    db.add(job)
    await db.commit()

    # Get database URL for background task
    from config.settings import get_settings

    settings = get_settings()
    db_url = settings.database_url

    # Queue background task
    background_tasks.add_task(_run_export_job, job_id, db_url)

    logger.info(
        "Created export job %s (format=%s)",
        sanitize_for_log(job_id),
        sanitize_for_log(request.format),
    )

    return BulkJobCreateResponse(
        id=job_id,
        job_type=BulkJobType.EXPORT.value,
        status=BulkJobStatus.PENDING.value,
        message="Export job started",
        created_at=job.created_at,
    )


@router.get("", response_model=BulkJobListResponse)
async def list_bulk_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    job_type: Annotated[Optional[str], Query(alias="job_type")] = None,
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    source_type: Annotated[Optional[str], Query(alias="source_type")] = None,
) -> BulkJobListResponse:
    """List bulk jobs with pagination and filtering.

    Supports filtering by:
    - job_type: import or export
    - status: pending, running, completed, failed, cancelled
    - source_type: url, file_upload, portal_api, search
    """
    # Build base query
    base_query = select(BulkJob)

    # Apply filters
    if job_type:
        base_query = base_query.where(BulkJob.job_type == job_type)
    if status_filter:
        base_query = base_query.where(BulkJob.status == status_filter)
    if source_type:
        base_query = base_query.where(BulkJob.source_type == source_type)

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * page_size
    data_query = base_query.order_by(BulkJob.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(data_query)
    jobs = result.scalars().all()

    return BulkJobListResponse(
        jobs=[_job_to_response(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=BulkJobResponse)
async def get_bulk_job(
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkJobResponse:
    """Get details and status of a specific bulk job."""
    result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bulk job {job_id} not found",
        )

    return _job_to_response(job)


@router.post("/{job_id}/cancel", response_model=BulkJobResponse)
async def cancel_bulk_job(
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkJobResponse:
    """Cancel a running bulk job.

    Only jobs in 'pending' or 'running' status can be cancelled.
    """
    result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bulk job {job_id} not found",
        )

    if job.status not in (BulkJobStatus.PENDING.value, BulkJobStatus.RUNNING.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status '{job.status}'",
        )

    # Update status to cancelled
    job.status = BulkJobStatus.CANCELLED.value
    job.completed_at = datetime.now(UTC)
    job.error_message = "Job cancelled by user"
    await db.commit()

    logger.info("Cancelled bulk job %s", sanitize_for_log(job_id))
    return _job_to_response(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bulk_job(
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a bulk job record.

    Only completed, failed, or cancelled jobs can be deleted.
    """
    result = await db.execute(select(BulkJob).where(BulkJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bulk job {job_id} not found",
        )

    if job.status in (BulkJobStatus.PENDING.value, BulkJobStatus.RUNNING.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete active job. Cancel it first.",
        )

    await db.delete(job)
    logger.info("Deleted bulk job %s", sanitize_for_log(job_id))


def _validate_import_config(source_type: BulkJobSourceType, config: dict[str, Any]) -> None:
    """Validate import configuration based on source type."""
    if source_type == BulkJobSourceType.URL:
        if "file_urls" not in config:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="URL source requires 'file_urls' in config",
            )
        if not isinstance(config["file_urls"], list):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="file_urls must be a list of URLs",
            )
        for url in config["file_urls"]:
            if not url.startswith(("http://", "https://")):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid URL: {url}",
                )

    elif source_type == BulkJobSourceType.FILE_UPLOAD:
        if "temp_file_path" not in config:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="File upload source requires 'temp_file_path' in config",
            )

    elif source_type == BulkJobSourceType.PORTAL_API:
        if "portal" not in config:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Portal API source requires 'portal' in config",
            )


def _validate_export_config(source_type: BulkJobSourceType, config: dict[str, Any]) -> None:
    """Validate export configuration based on source type."""
    if source_type == BulkJobSourceType.SEARCH:
        # Search requires at least a query or filters or property_ids
        if "query" not in config and "filters" not in config and "property_ids" not in config:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Export requires 'query', 'filters', or 'property_ids' in config",
            )
