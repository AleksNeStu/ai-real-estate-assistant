"""
MCP Audit Log Query API (Task #69).

Admin endpoints for querying MCP connector audit logs:
- List audit entries with filters
- Get audit entry details
- Storage metrics
- Cleanup management
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from api.deps.auth import require_admin_access
from mcp.audit import MCPAuditLogger, get_mcp_audit_logger
from mcp.retention import MCPAuditRetention, get_retention_manager

router = APIRouter(prefix="/admin/mcp/audit", tags=["MCP Audit"])


# Request/Response Models
class AuditQueryParams(BaseModel):
    """Parameters for querying audit logs."""

    connector_name: Optional[str] = None
    operation: Optional[str] = None
    status: Optional[str] = None
    request_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditEntry(BaseModel):
    """Single audit log entry."""

    timestamp: str
    event_type: str
    level: str
    connector_name: str
    operation: Optional[str] = None
    status: str
    duration_ms: Optional[int] = None
    request_id: Optional[str] = None
    params_meta: Optional[dict[str, Any]] = None
    result_meta: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class AuditListResponse(BaseModel):
    """Response for audit log list endpoint."""

    entries: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    has_more: bool


class StorageMetricsResponse(BaseModel):
    """Response for storage metrics endpoint."""

    log_directory: str
    file_count: int
    total_size_bytes: int
    total_size_mb: float
    oldest_log_date: Optional[str] = None
    newest_log_date: Optional[str] = None
    retention_days: int
    expired_files: int


class CleanupResponse(BaseModel):
    """Response for cleanup endpoint."""

    files_found: int
    files_removed: int
    bytes_freed: int
    errors: list[str]
    dry_run: bool


class CleanupRequest(BaseModel):
    """Request for cleanup endpoint."""

    dry_run: bool = Field(default=True, description="If True, don't actually delete files")


def get_audit_logger() -> MCPAuditLogger:
    """Dependency to get MCP audit logger."""
    return get_mcp_audit_logger()


def get_retention() -> MCPAuditRetention:
    """Dependency to get retention manager."""
    return get_retention_manager()


@router.get("", response_model=AuditListResponse)
async def list_audit_entries(
    connector_name: Optional[str] = Query(None, description="Filter by connector name"),
    operation: Optional[str] = Query(None, description="Filter by operation"),
    status: Optional[str] = Query(None, description="Filter by status (success, failure, error)"),
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _: None = Depends(require_admin_access),
    audit_logger: MCPAuditLogger = Depends(get_audit_logger),
) -> AuditListResponse:
    """
    Query MCP audit logs with filters.

    Requires API key authentication.

    Returns paginated audit log entries matching the specified filters.
    """
    entries = audit_logger.query(
        connector_name=connector_name,
        operation=operation,
        status=status,
        request_id=request_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit + 1,  # Fetch one extra to check for has_more
        offset=offset,
    )

    has_more = len(entries) > limit
    if has_more:
        entries = entries[:limit]

    return AuditListResponse(
        entries=entries,
        total=len(entries),  # Note: actual total would require counting all matches
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/storage", response_model=StorageMetricsResponse)
async def get_storage_metrics(
    _: None = Depends(require_admin_access),
    retention: MCPAuditRetention = Depends(get_retention),
) -> StorageMetricsResponse:
    """
    Get storage metrics for MCP audit logs.

    Requires API key authentication.

    Returns information about log file storage including:
    - Number of files
    - Total size
    - Date range
    - Expired files count
    """
    metrics = retention.get_storage_metrics()
    return StorageMetricsResponse(**metrics)


@router.post("/cleanup", response_model=CleanupResponse)
async def run_cleanup(
    request: CleanupRequest,
    _: None = Depends(require_admin_access),
    retention: MCPAuditRetention = Depends(get_retention),
) -> CleanupResponse:
    """
    Run cleanup of expired MCP audit logs.

    Requires API key authentication.

    By default, runs in dry-run mode (no files deleted).
    Set dry_run=false to actually delete files.
    """
    result = retention.cleanup(dry_run=request.dry_run)
    return CleanupResponse(**result)


@router.get("/request/{request_id}")
async def get_entries_by_request_id(
    request_id: str,
    _: None = Depends(require_admin_access),
    audit_logger: MCPAuditLogger = Depends(get_audit_logger),
) -> list[dict[str, Any]]:
    """
    Get all audit entries for a specific request ID.

    Requires API key authentication.

    Useful for tracing a request through multiple connector calls.
    """
    entries = audit_logger.query(request_id=request_id, limit=1000)
    return entries


@router.get("/connector/{connector_name}")
async def get_entries_by_connector(
    connector_name: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_admin_access),
    audit_logger: MCPAuditLogger = Depends(get_audit_logger),
) -> AuditListResponse:
    """
    Get audit entries for a specific connector.

    Requires API key authentication.

    Returns paginated entries for the specified connector.
    """
    entries = audit_logger.query(
        connector_name=connector_name,
        limit=limit + 1,
        offset=offset,
    )

    has_more = len(entries) > limit
    if has_more:
        entries = entries[:limit]

    return AuditListResponse(
        entries=entries,
        total=len(entries),
        limit=limit,
        offset=offset,
        has_more=has_more,
    )
