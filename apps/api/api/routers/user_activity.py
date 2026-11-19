"""User Activity Analytics API endpoints (Task #82).

This module provides endpoints for:
- Aggregated activity metrics
- Activity trends over time
- CSV export of activity data
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user
from db.database import get_db
from db.models import User
from db.schemas import (
    UserActivitySummary,
    UserActivityTrendPoint,
    UserActivityTrendsResponse,
)
from services.user_activity_service import UserActivityService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user-activity", tags=["User Activity Analytics"])


# =============================================================================
# User Activity Endpoints
# =============================================================================


@router.get(
    "/summary",
    response_model=UserActivitySummary,
    summary="Get activity summary",
    description="Get aggregated activity metrics for the current user.",
)
async def get_activity_summary(
    period_start: datetime | None = Query(
        None, description="Start of analysis period (default: 30 days ago)"
    ),
    period_end: datetime | None = Query(None, description="End of analysis period (default: now)"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserActivitySummary:
    """Get activity summary for the current user."""
    service = UserActivityService(session)
    summary = await service.get_activity_summary(
        user_id=user.id,
        period_start=period_start,
        period_end=period_end,
    )

    return UserActivitySummary(
        period_start=summary.period_start,
        period_end=summary.period_end,
        total_searches=summary.total_searches,
        total_property_views=summary.total_property_views,
        total_property_clicks=summary.total_property_clicks,
        total_tool_uses=summary.total_tool_uses,
        total_exports=summary.total_exports,
        total_favorites=summary.total_favorites,
        unique_sessions=summary.unique_sessions,
        avg_processing_time_ms=summary.avg_processing_time_ms,
        top_tools=summary.top_tools,
        top_search_cities=summary.top_search_cities,
        visitors_by_locale=summary.visitors_by_locale,
        event_counts_by_day=summary.event_counts_by_day,
    )


@router.get(
    "/trends",
    response_model=UserActivityTrendsResponse,
    summary="Get activity trends",
    description="Get activity trends over time with configurable intervals.",
)
async def get_activity_trends(
    interval: str = Query(
        "day",
        pattern="^(day|week|month)$",
        description="Time interval for grouping",
    ),
    period_start: datetime | None = Query(
        None, description="Start of analysis period (default: 30 days ago)"
    ),
    period_end: datetime | None = Query(None, description="End of analysis period (default: now)"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserActivityTrendsResponse:
    """Get activity trends for the current user."""
    service = UserActivityService(session)
    trends = await service.get_activity_trends(
        user_id=user.id,
        period_start=period_start,
        period_end=period_end,
        interval=interval,
    )

    return UserActivityTrendsResponse(
        trends=[
            UserActivityTrendPoint(
                date=t.date,
                searches=t.searches,
                property_views=t.property_views,
                tool_uses=t.tool_uses,
                exports=t.exports,
            )
            for t in trends
        ],
        interval=interval,
    )


@router.get(
    "/export",
    summary="Export activity data",
    description="Export user activity data as CSV file.",
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "CSV file with activity data",
        }
    },
)
async def export_activity_data(
    period_start: datetime | None = Query(
        None, description="Start of analysis period (default: 30 days ago)"
    ),
    period_end: datetime | None = Query(None, description="End of analysis period (default: now)"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export user activity data as CSV."""
    service = UserActivityService(session)
    csv_data = await service.export_activity_csv(
        user_id=user.id,
        period_start=period_start,
        period_end=period_end,
    )

    # Format period_start for filename
    period_str = period_start.strftime("%Y%m%d") if period_start else "all"
    filename = f"activity_{user.id}_{period_str}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# =============================================================================
# Admin Endpoints - Global Analytics
# =============================================================================


@router.get(
    "/admin/summary",
    response_model=UserActivitySummary,
    summary="Get global activity summary (admin)",
    description="Get aggregated activity metrics for all users (admin only).",
)
async def get_global_activity_summary(
    period_start: datetime | None = Query(
        None, description="Start of analysis period (default: 30 days ago)"
    ),
    period_end: datetime | None = Query(None, description="End of analysis period (default: now)"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserActivitySummary:
    """Get global activity summary (admin only)."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access global analytics",
        )

    service = UserActivityService(session)
    summary = await service.get_activity_summary(
        user_id=None,  # No user filter = all users
        period_start=period_start,
        period_end=period_end,
    )

    return UserActivitySummary(
        period_start=summary.period_start,
        period_end=summary.period_end,
        total_searches=summary.total_searches,
        total_property_views=summary.total_property_views,
        total_property_clicks=summary.total_property_clicks,
        total_tool_uses=summary.total_tool_uses,
        total_exports=summary.total_exports,
        total_favorites=summary.total_favorites,
        unique_sessions=summary.unique_sessions,
        avg_processing_time_ms=summary.avg_processing_time_ms,
        top_tools=summary.top_tools,
        top_search_cities=summary.top_search_cities,
        visitors_by_locale=summary.visitors_by_locale,
        event_counts_by_day=summary.event_counts_by_day,
    )


@router.get(
    "/admin/trends",
    response_model=UserActivityTrendsResponse,
    summary="Get global activity trends (admin)",
    description="Get activity trends over time for all users (admin only).",
)
async def get_global_activity_trends(
    interval: str = Query(
        "day",
        pattern="^(day|week|month)$",
        description="Time interval for grouping",
    ),
    period_start: datetime | None = Query(
        None, description="Start of analysis period (default: 30 days ago)"
    ),
    period_end: datetime | None = Query(None, description="End of analysis period (default: now)"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserActivityTrendsResponse:
    """Get global activity trends (admin only)."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access global analytics",
        )

    service = UserActivityService(session)
    trends = await service.get_activity_trends(
        user_id=None,  # No user filter = all users
        period_start=period_start,
        period_end=period_end,
        interval=interval,
    )

    return UserActivityTrendsResponse(
        trends=[
            UserActivityTrendPoint(
                date=t.date,
                searches=t.searches,
                property_views=t.property_views,
                tool_uses=t.tool_uses,
                exports=t.exports,
            )
            for t in trends
        ],
        interval=interval,
    )
