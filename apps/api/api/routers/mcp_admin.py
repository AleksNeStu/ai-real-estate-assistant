"""
MCP Connector Registry Admin API Router.

Provides endpoints for managing and monitoring MCP connectors.
This is part of Task #68: MCP Allowlist Governance and Task #71: MCP Registry API.

Endpoints:
- GET /api/v1/mcp/allowlist - List current allowlist
- POST /api/v1/mcp/allowlist - Add connector to allowlist
- DELETE /api/v1/mcp/allowlist/{name} - Remove from allowlist
- GET /api/v1/mcp/allowlist/violations - List violations for audit
- DELETE /api/v1/mcp/allowlist/violations - Clear all violations
- POST /api/v1/mcp/allowlist/reload - Reload from YAML
- GET /api/v1/mcp/connectors - List all connectors with status
- GET /api/v1/mcp/connectors/{name} - Get single connector details
- GET /api/v1/mcp/connectors/{name}/health - Health check single connector
- GET /api/v1/mcp/health - Health check all connectors
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import get_api_key
from core.security_utils import sanitize_for_log
from mcp import (
    AllowlistConfig,
    AllowlistEntry,
    MCPConnectorRegistry,
    MCPEdition,
    get_allowlist_validator,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/mcp",
    tags=["MCP Admin"],
    dependencies=[Depends(get_api_key)],
)


# ============================================================================
# Pydantic Models for API
# ============================================================================


class MCPAllowlistEntryResponse(BaseModel):
    """Response model for allowlist entry."""

    name: str
    display_name: str
    description: str = ""
    enabled: bool = True
    edition: str = "community"
    added_at: Optional[str] = None
    added_by: str = "system"


class MCPAllowlistResponse(BaseModel):
    """Response model for allowlist listing."""

    edition: str
    allowlist: List[MCPAllowlistEntryResponse]
    restricted: List[MCPAllowlistEntryResponse]
    total_allowed: int
    total_restricted: int
    loaded_at: Optional[str] = None
    config_path: Optional[str] = None


class MCPAllowlistAddRequest(BaseModel):
    """Request model for adding connector to allowlist."""

    name: str = Field(..., description="Connector identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field("", description="Connector description")
    edition: str = Field("community", description="Edition level")
    added_by: str = Field("admin", description="Who added this entry")


class MCPViolationResponse(BaseModel):
    """Response model for allowlist violation."""

    timestamp: str
    connector: str
    operation: str
    context: Dict[str, Any] = Field(default_factory=dict)
    config_edition: str


class MCPViolationsListResponse(BaseModel):
    """Response model for violations list."""

    violations: List[MCPViolationResponse]
    total: int


class ConnectorStatus:
    """Connector status enum."""

    ACTIVE = "active"  # Connected and healthy
    DISABLED = "disabled"  # Configured but not enabled
    ERROR = "error"  # Has connection/health issues
    NOT_INSTANTIATED = "not_instantiated"  # Registered but no instance
    UNKNOWN = "unknown"


class MCPConnectorInfoResponse(BaseModel):
    """
    Response model for connector info.

    Status values:
    - active: Connector is connected and healthy
    - disabled: Connector is configured but not enabled
    - error: Connector has connection/health issues
    - not_instantiated: Connector registered but no instance
    """

    name: str
    display_name: str
    description: str = ""
    enabled: bool = True
    edition: str
    status: str  # ConnectorStatus values
    accessible_in_ce: bool
    registered: bool = False
    has_instance: bool = False
    requires_api_key: bool = False
    supports_streaming: bool = False
    min_edition: str = "community"
    last_health_check: Optional[str] = None
    error_message: Optional[str] = None


class MCPConnectorDetailResponse(BaseModel):
    """
    Detailed response model for single connector.

    Includes all info fields plus rate limit and health details.
    """

    name: str
    display_name: str
    description: str = ""
    enabled: bool = True
    edition: str
    status: str
    accessible_in_ce: bool
    registered: bool = False
    has_instance: bool = False
    requires_api_key: bool = False
    supports_streaming: bool = False
    min_edition: str = "community"
    last_health_check: Optional[str] = None
    error_message: Optional[str] = None
    rate_limit: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None
    instance_status: Optional[Dict[str, Any]] = None


class MCPConnectorHealthResponse(BaseModel):
    """Response model for single connector health check."""

    name: str
    status: str  # "healthy", "unhealthy", "error"
    success: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    response_time_ms: Optional[float] = None
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class MCPConnectorsListResponse(BaseModel):
    """Response model for connectors list."""

    connectors: List[MCPConnectorInfoResponse]
    edition: str
    total: int


class MCPHealthResponse(BaseModel):
    """Response model for MCP health check."""

    status: str  # "healthy", "degraded", "unhealthy"
    edition: str
    connectors_checked: int
    results: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class MCPReloadResponse(BaseModel):
    """Response model for allowlist reload."""

    message: str
    allowlist_count: int
    restricted_count: int
    edition: str
    loaded_at: str


# ============================================================================
# Helper Functions
# ============================================================================


def _entry_to_response(entry: AllowlistEntry) -> MCPAllowlistEntryResponse:
    """Convert AllowlistEntry to response model."""
    return MCPAllowlistEntryResponse(
        name=entry.name,
        display_name=entry.display_name,
        description=entry.description,
        enabled=entry.enabled,
        edition=entry.edition.value,
        added_at=entry.added_at.isoformat() if entry.added_at else None,
        added_by=entry.added_by,
    )


def _config_to_response(config: AllowlistConfig) -> MCPAllowlistResponse:
    """Convert AllowlistConfig to response model."""
    return MCPAllowlistResponse(
        edition=config.edition.value,
        allowlist=[_entry_to_response(e) for e in config.allowlist],
        restricted=[_entry_to_response(e) for e in config.restricted],
        total_allowed=len([e for e in config.allowlist if e.enabled]),
        total_restricted=len(config.restricted),
        loaded_at=config.loaded_at.isoformat() if config.loaded_at else None,
        config_path=str(config.config_path) if config.config_path else None,
    )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/allowlist", response_model=MCPAllowlistResponse)
async def get_allowlist():
    """
    Get current MCP connector allowlist configuration.

    Returns the full allowlist including:
    - Current edition
    - Allowlisted connectors (CE accessible)
    - Restricted connectors (PRO/Enterprise only)
    """
    validator = get_allowlist_validator()
    config = validator.config
    return _config_to_response(config)


@router.post(
    "/allowlist",
    response_model=MCPAllowlistEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_allowlist(request: MCPAllowlistAddRequest):
    """
    Add a connector to the allowlist at runtime.

    Note: This modifies the in-memory config only.
    For persistence, update the YAML file directly.
    """
    validator = get_allowlist_validator()

    # Parse edition
    try:
        edition = MCPEdition(request.edition.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid edition: {request.edition}. Valid: community, pro, enterprise",
        ) from None

    entry = validator.add_connector(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        edition=edition,
        added_by=request.added_by,
    )

    logger.info(
        "Added connector '%s' to allowlist via API by %s",
        sanitize_for_log(request.name),
        sanitize_for_log(request.added_by),
    )

    return _entry_to_response(entry)


@router.delete("/allowlist/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_allowlist(name: str):
    """
    Remove a connector from the allowlist.

    Note: This modifies the in-memory config only.
    For persistence, update the YAML file directly.
    """
    validator = get_allowlist_validator()
    removed = validator.remove_connector(name)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{name}' not found in allowlist",
        )

    logger.info("Removed connector '%s' from allowlist via API", sanitize_for_log(name))


@router.get("/allowlist/violations", response_model=MCPViolationsListResponse)
async def get_violations():
    """
    Get all logged allowlist violations for audit.

    Returns violation records including:
    - Timestamp
    - Connector name
    - Operation attempted
    - Context and edition info
    """
    validator = get_allowlist_validator()
    violations = validator.get_violations()

    return MCPViolationsListResponse(
        violations=[MCPViolationResponse(**v) for v in violations],
        total=len(violations),
    )


@router.delete("/allowlist/violations", status_code=status.HTTP_204_NO_CONTENT)
async def clear_violations():
    """
    Clear all logged allowlist violations.

    Use with caution - this removes audit trail.
    """
    validator = get_allowlist_validator()
    validator.clear_violations()
    logger.info("Allowlist violations cleared via API")


@router.post("/allowlist/reload", response_model=MCPReloadResponse)
async def reload_allowlist():
    """
    Reload allowlist configuration from YAML file.

    Use this after updating the YAML file to apply changes
    without restarting the application.
    """
    validator = get_allowlist_validator()
    config = validator.reload_config()

    # Also update registry
    MCPConnectorRegistry.set_edition(config.edition)
    MCPConnectorRegistry.set_allowlist(config.get_allowlist_names())

    logger.info("Allowlist reloaded from YAML via API")

    return MCPReloadResponse(
        message="Allowlist reloaded successfully",
        allowlist_count=len(config.allowlist),
        restricted_count=len(config.restricted),
        edition=config.edition.value,
        loaded_at=config.loaded_at.isoformat(),
    )


def _calculate_connector_status(
    name: str,
    enabled: bool,
    has_instance: bool,
    connector_class: Optional[Any] = None,
) -> tuple[str, Optional[str]]:
    """
    Calculate connector status based on configuration and instance state.

    Args:
        name: Connector name
        enabled: Whether connector is enabled
        has_instance: Whether connector has an instance
        connector_class: Optional connector class for additional info

    Returns:
        Tuple of (status, error_message)
    """
    if not enabled:
        return ConnectorStatus.DISABLED, None

    if not has_instance:
        return ConnectorStatus.NOT_INSTANTIATED, None

    # Check instance status if available
    if name in MCPConnectorRegistry._instances:
        instance = MCPConnectorRegistry._instances[name]
        try:
            instance_status = instance.get_status()
            if instance_status.get("error"):
                return ConnectorStatus.ERROR, instance_status.get("error_message")
            if instance_status.get("connected", False):
                return ConnectorStatus.ACTIVE, None
        except Exception as e:
            return ConnectorStatus.ERROR, str(e)

    return ConnectorStatus.NOT_INSTANTIATED, None


def _get_connector_class_info(name: str) -> Dict[str, Any]:
    """Get connector class information if registered."""
    connector_class = MCPConnectorRegistry._connectors.get(name)
    if not connector_class:
        return {}

    return {
        "requires_api_key": getattr(connector_class, "requires_api_key", False),
        "supports_streaming": getattr(connector_class, "supports_streaming", False),
        "min_edition": getattr(connector_class, "min_edition", MCPEdition.COMMUNITY).value,
        "display_name": getattr(connector_class, "display_name", name),
        "description": getattr(connector_class, "description", ""),
    }


@router.get("/connectors", response_model=MCPConnectorsListResponse)
async def list_connectors():
    """
    List all connectors with status.

    Returns all registered connectors with their current status:
    - **active**: Connector is connected and healthy
    - **disabled**: Connector is configured but not enabled
    - **error**: Connector has connection/health issues
    - **not_instantiated**: Connector registered but no instance

    Combines information from:
    - Allowlist config (YAML)
    - Registry (registered connectors)
    """
    validator = get_allowlist_validator()
    config = validator.config

    # Get all known connectors
    all_connectors_info = validator.get_all_connectors_info()

    # Add registry status
    result = []
    for name, info in all_connectors_info.items():
        registered = name in MCPConnectorRegistry.list_connectors(include_non_accessible=True)
        has_instance = name in MCPConnectorRegistry._instances
        enabled = info.get("enabled", True)

        # Get class info
        class_info = _get_connector_class_info(name)

        # Calculate status
        status, error_message = _calculate_connector_status(name, enabled, has_instance)

        result.append(
            MCPConnectorInfoResponse(
                name=name,
                display_name=info.get("display_name", class_info.get("display_name", name)),
                description=info.get("description", class_info.get("description", "")),
                enabled=enabled,
                edition=info.get("edition", "community"),
                status=status,
                accessible_in_ce=info.get("accessible_in_ce", False),
                registered=registered,
                has_instance=has_instance,
                requires_api_key=class_info.get("requires_api_key", False),
                supports_streaming=class_info.get("supports_streaming", False),
                min_edition=class_info.get("min_edition", "community"),
                error_message=error_message,
            )
        )

    return MCPConnectorsListResponse(
        connectors=result,
        edition=config.edition.value,
        total=len(result),
    )


@router.get(
    "/connectors/{name}",
    response_model=MCPConnectorDetailResponse,
    responses={
        200: {"description": "Connector details"},
        404: {"description": "Connector not found"},
    },
)
async def get_connector_details(name: str):
    """
    Get detailed information about a specific connector.

    Returns comprehensive connector information including:
    - Basic info (name, description, status)
    - Configuration details (sanitized)
    - Rate limit settings
    - Instance status if available
    """
    validator = get_allowlist_validator()

    # Check if connector exists in registry or allowlist
    all_connectors_info = validator.get_all_connectors_info()

    if name not in all_connectors_info and name not in MCPConnectorRegistry._connectors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{name}' not found",
        )

    # Get info from allowlist config
    info = all_connectors_info.get(name, {})
    registered = name in MCPConnectorRegistry.list_connectors(include_non_accessible=True)
    has_instance = name in MCPConnectorRegistry._instances
    enabled = info.get("enabled", True)

    # Get class info
    class_info = _get_connector_class_info(name)

    # Calculate status
    connector_status, error_message = _calculate_connector_status(name, enabled, has_instance)

    # Get instance status if available
    instance_status = None
    if has_instance:
        try:
            instance_status = MCPConnectorRegistry._instances[name].get_status()
        except Exception as e:
            instance_status = {"error": True, "error_message": str(e)}

    # Get config (sanitized)
    config_info = None
    if name in MCPConnectorRegistry._configs:
        config_info = MCPConnectorRegistry._configs[name].to_dict()

    # Get rate limit info
    rate_limit_info = None
    try:
        from mcp.rate_limiter import get_connector_rate_limiter

        limiter = get_connector_rate_limiter()
        rate_limit_info = limiter.get_status(name)
    except ImportError:
        pass  # Rate limiter not available

    return MCPConnectorDetailResponse(
        name=name,
        display_name=info.get("display_name", class_info.get("display_name", name)),
        description=info.get("description", class_info.get("description", "")),
        enabled=enabled,
        edition=info.get("edition", "community"),
        status=connector_status,
        accessible_in_ce=info.get("accessible_in_ce", False),
        registered=registered,
        has_instance=has_instance,
        requires_api_key=class_info.get("requires_api_key", False),
        supports_streaming=class_info.get("supports_streaming", False),
        min_edition=class_info.get("min_edition", "community"),
        error_message=error_message,
        rate_limit=rate_limit_info,
        config=config_info,
        instance_status=instance_status,
    )


@router.get(
    "/connectors/{name}/health",
    response_model=MCPConnectorHealthResponse,
    responses={
        200: {"description": "Health check completed"},
        404: {"description": "Connector not found"},
        503: {"description": "Connector unhealthy"},
    },
)
async def health_check_connector(name: str):
    """
    Perform health check on a specific connector.

    Returns health status including:
    - Success/failure status
    - Response time in milliseconds
    - Any errors or warnings
    - Detailed health information
    """

    get_allowlist_validator()

    # Check if connector exists
    if name not in MCPConnectorRegistry._connectors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{name}' not found",
        )

    # Check if connector has an instance
    if name not in MCPConnectorRegistry._instances:
        return MCPConnectorHealthResponse(
            name=name,
            status="unhealthy",
            success=False,
            errors=["Connector not instantiated"],
            timestamp=datetime.utcnow().isoformat(),
        )

    # Perform health check
    instance = MCPConnectorRegistry._instances[name]
    start_time = time.time()

    try:
        result = await instance.health_check()
        response_time_ms = (time.time() - start_time) * 1000

        health_check_status = "healthy" if result.success else "unhealthy"

        return MCPConnectorHealthResponse(
            name=name,
            status=health_check_status,
            success=result.success,
            errors=result.errors,
            warnings=result.warnings if hasattr(result, "warnings") else [],
            response_time_ms=round(response_time_ms, 2),
            timestamp=datetime.utcnow().isoformat(),
            details=result.data if result.success else None,
        )
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(
            "Health check failed for connector '%s': %s",
            sanitize_for_log(name),
            sanitize_for_log(e),
        )

        return MCPConnectorHealthResponse(
            name=name,
            status="error",
            success=False,
            errors=[str(e)],
            response_time_ms=round(response_time_ms, 2),
            timestamp=datetime.utcnow().isoformat(),
        )


@router.get("/health", response_model=MCPHealthResponse)
async def health_check():
    """
    Health check for MCP connector system.

    Returns:
    - Overall status (healthy/degraded/unhealthy)
    - Health check results for each instantiated connector
    """
    validator = get_allowlist_validator()
    config = validator.config

    # Run health checks on all instantiated connectors

    health_results = {}
    try:
        health_results = await MCPConnectorRegistry.health_check_all()
    except Exception as e:
        logger.error("Health check failed: %s", sanitize_for_log(e))

    # Determine overall status
    total = len(health_results)
    if total == 0:
        overall_status = "healthy"  # No connectors = healthy
    else:
        successful = sum(1 for r in health_results.values() if r.success)
        if successful == total:
            overall_status = "healthy"
        elif successful > 0:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

    return MCPHealthResponse(
        status=overall_status,
        edition=config.edition.value,
        connectors_checked=total,
        results={
            name: {"success": r.success, "errors": r.errors} for name, r in health_results.items()
        },
        timestamp=datetime.utcnow().isoformat(),
    )
