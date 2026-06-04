"""Agent Performance Analytics API endpoints.

This module provides endpoints for:
- Agent performance metrics
- Team comparison
- Performance trends
- Coaching insights
- Deal management
- Goal tracking
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user
from core.security_utils import sanitize_for_log
from db.database import get_db
from db.models import Deal, User
from db.schemas import (
    AgentMetricsResponse,
    AgentNeedingSupport,
    AgentsNeedingSupportResponse,
    CoachingInsightResponse,
    CoachingInsightsResponse,
    DealCreate,
    DealListResponse,
    DealResponse,
    DealUpdate,
    GoalProgressListResponse,
    GoalProgressResponse,
    PerformanceTrendPoint,
    PerformanceTrendsResponse,
    TeamComparisonResponse,
    TopPerformerEntry,
    TopPerformersResponse,
)
from services.agent_performance import AgentPerformanceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-analytics", tags=["Agent Analytics"])


# =============================================================================
# Agent Metrics Endpoints
# =============================================================================


@router.get(
    "/me",
    response_model=AgentMetricsResponse,
    summary="Get my performance metrics",
    description="Get comprehensive performance metrics for the current agent including leads, deals, conversion rates, and financial data.",
)
async def get_my_metrics(
    period_start: Optional[datetime] = Query(
        None, description="Start of analysis period (default: 30 days ago)"
    ),
    period_end: Optional[datetime] = Query(
        None, description="End of analysis period (default: now)"
    ),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AgentMetricsResponse:
    """Get performance metrics for the current agent."""
    if user.role not in ("agent", "admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents and admins can access agent analytics",
        )

    service = AgentPerformanceService(session)
    metrics = await service.get_agent_metrics(
        agent_id=user.id,
        period_start=period_start,
        period_end=period_end,
    )

    return AgentMetricsResponse(
        total_leads=metrics.total_leads,
        active_leads=metrics.active_leads,
        new_leads_week=metrics.new_leads_week,
        high_value_leads=metrics.high_value_leads,
        total_deals=metrics.total_deals,
        active_deals=metrics.active_deals,
        closed_deals=metrics.closed_deals,
        fell_through_deals=metrics.fell_through_deals,
        lead_to_qualified_rate=metrics.lead_to_qualified_rate,
        qualified_to_deal_rate=metrics.qualified_to_deal_rate,
        overall_conversion_rate=metrics.overall_conversion_rate,
        avg_time_to_first_contact_hours=metrics.avg_time_to_first_contact_hours,
        avg_time_to_qualify_days=metrics.avg_time_to_qualify_days,
        avg_time_to_close_days=metrics.avg_time_to_close_days,
        total_deal_value=metrics.total_deal_value,
        avg_deal_value=metrics.avg_deal_value,
        total_commission=metrics.total_commission,
        pending_commission=metrics.pending_commission,
        top_property_types=metrics.top_property_types,
        top_locations=metrics.top_locations,
        avg_lead_score=metrics.avg_lead_score,
        deals_change_percent=metrics.deals_change_percent,
        revenue_change_percent=metrics.revenue_change_percent,
    )


@router.get(
    "/me/comparison",
    response_model=TeamComparisonResponse,
    summary="Get team comparison",
    description="Compare current agent's performance to team averages with rankings.",
)
async def get_my_team_comparison(
    period_start: Optional[datetime] = Query(None),
    period_end: Optional[datetime] = Query(None),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TeamComparisonResponse:
    """Compare current agent's performance to team averages."""
    if user.role not in ("agent", "admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents and admins can access agent analytics",
        )

    service = AgentPerformanceService(session)
    comparison = await service.get_team_comparison(
        agent_id=user.id,
        period_start=period_start,
        period_end=period_end,
    )

    return TeamComparisonResponse(
        agent_id=comparison.agent_id,
        agent_name=comparison.agent_name,
        rank_by_deals=comparison.rank_by_deals,
        rank_by_revenue=comparison.rank_by_revenue,
        rank_by_conversion=comparison.rank_by_conversion,
        total_agents=comparison.total_agents,
        deals_vs_avg_percent=comparison.deals_vs_avg_percent,
        revenue_vs_avg_percent=comparison.revenue_vs_avg_percent,
        conversion_vs_avg_percent=comparison.conversion_vs_avg_percent,
        time_to_close_vs_avg_percent=comparison.time_to_close_vs_avg_percent,
        team_avg_deals=comparison.team_avg_deals,
        team_avg_revenue=comparison.team_avg_revenue,
        team_avg_conversion=comparison.team_avg_conversion,
        team_avg_time_to_close_days=comparison.team_avg_time_to_close_days,
    )


@router.get(
    "/me/trends",
    response_model=PerformanceTrendsResponse,
    summary="Get performance trends",
    description="Get performance trends over time with configurable intervals.",
)
async def get_my_trends(
    interval: str = Query("month", regex="^(day|week|month|quarter)$", description="Time interval"),
    periods: int = Query(12, ge=1, le=52, description="Number of periods to return"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PerformanceTrendsResponse:
    """Get performance trends over time."""
    if user.role not in ("agent", "admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents and admins can access agent analytics",
        )

    service = AgentPerformanceService(session)
    trends = await service.get_performance_trends(
        agent_id=user.id,
        interval=interval,
        periods=periods,
    )

    return PerformanceTrendsResponse(
        trends=[
            PerformanceTrendPoint(
                period=t.period,
                period_start=t.period_start,
                period_end=t.period_end,
                leads=t.leads,
                deals_closed=t.deals_closed,
                revenue=t.revenue,
                conversion_rate=t.conversion_rate,
                avg_deal_value=t.avg_deal_value,
            )
            for t in trends
        ],
        interval=interval,
    )


@router.get(
    "/me/insights",
    response_model=CoachingInsightsResponse,
    summary="Get coaching insights",
    description="Get AI-powered coaching insights with actionable recommendations.",
)
async def get_my_insights(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> CoachingInsightsResponse:
    """Get AI-powered coaching insights."""
    if user.role not in ("agent", "admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents and admins can access agent analytics",
        )

    service = AgentPerformanceService(session)
    insights = await service.get_coaching_insights(agent_id=user.id)

    return CoachingInsightsResponse(
        insights=[
            CoachingInsightResponse(
                category=i.category,
                title=i.title,
                description=i.description,
                actionable_recommendation=i.actionable_recommendation,
                priority=i.priority,
            )
            for i in insights
        ]
    )


@router.get(
    "/me/goals",
    response_model=GoalProgressListResponse,
    summary="Get goal progress",
    description="Get progress towards active goals.",
)
async def get_my_goals(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> GoalProgressListResponse:
    """Get progress towards goals."""
    if user.role not in ("agent", "admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents and admins can access agent analytics",
        )

    service = AgentPerformanceService(session)
    goals = await service.get_goal_progress(agent_id=user.id)

    return GoalProgressListResponse(goals=[GoalProgressResponse(**g) for g in goals])


# =============================================================================
# Admin Endpoints - Team Analytics
# =============================================================================


@router.get(
    "/top-performers",
    response_model=TopPerformersResponse,
    summary="Get top performers",
    description="Get leaderboard of top performing agents (admin only).",
)
async def get_top_performers(
    metric: str = Query(
        "deals", regex="^(deals|revenue|conversion)$", description="Metric to rank by"
    ),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    period_days: int = Query(30, ge=7, le=365, description="Analysis period in days"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TopPerformersResponse:
    """Get top performing agents (admin only)."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view top performers",
        )

    service = AgentPerformanceService(session)
    performers = await service.get_top_performers(
        metric=metric,
        limit=limit,
        period_days=period_days,
    )

    return TopPerformersResponse(
        performers=[TopPerformerEntry(**p) for p in performers],
        metric=metric,
        period_days=period_days,
    )


@router.get(
    "/needs-support",
    response_model=AgentsNeedingSupportResponse,
    summary="Get agents needing support",
    description="Identify agents who may need coaching support (admin only).",
)
async def get_agents_needing_support(
    threshold_days: int = Query(30, ge=7, le=365, description="Days without deal to flag"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AgentsNeedingSupportResponse:
    """Identify agents who may need coaching support (admin only)."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view agents needing support",
        )

    service = AgentPerformanceService(session)
    agents = await service.get_agents_needing_support(threshold_days=threshold_days)

    return AgentsNeedingSupportResponse(
        agents=[AgentNeedingSupport(**a) for a in agents],
        threshold_days=threshold_days,
    )


# =============================================================================
# Deal Management Endpoints
# =============================================================================


@router.post(
    "/deals",
    response_model=DealResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create deal",
    description="Create a new deal when a lead converts.",
)
async def create_deal(
    body: DealCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DealResponse:
    """Create a new deal when a lead converts."""
    if user.role not in ("agent", "admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents can create deals",
        )

    # Create deal
    deal = Deal(
        lead_id=body.lead_id,
        agent_id=user.id,
        property_id=body.property_id,
        deal_type=body.deal_type,
        deal_value=body.deal_value,
        property_type=body.property_type,
        property_city=body.property_city,
        property_district=body.property_district,
        notes=body.notes,
    )

    session.add(deal)
    await session.flush()
    await session.refresh(deal)

    logger.info(
        "Deal created: %s by agent %s", sanitize_for_log(deal.id), sanitize_for_log(user.id)
    )

    return _deal_to_response(deal)


@router.get(
    "/deals",
    response_model=DealListResponse,
    summary="List my deals",
    description="List deals for the current agent with optional filtering.",
)
async def list_my_deals(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by deal status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DealListResponse:
    """List deals for current agent."""
    if user.role not in ("agent", "admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents can view deals",
        )

    from sqlalchemy import func, select

    # Count total
    count_query = select(func.count(Deal.id)).where(Deal.agent_id == user.id)
    if status_filter:
        count_query = count_query.where(Deal.status == status_filter)

    result = await session.execute(count_query)
    total = result.scalar() or 0

    # Get paginated results
    query = (
        select(Deal)
        .where(Deal.agent_id == user.id)
        .order_by(Deal.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    if status_filter:
        query = query.where(Deal.status == status_filter)

    result = await session.execute(query)
    deals = result.scalars().all()

    return DealListResponse(
        items=[_deal_to_response(d) for d in deals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/deals/{deal_id}",
    response_model=DealResponse,
    summary="Get deal details",
    description="Get detailed information about a specific deal.",
)
async def get_deal(
    deal_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DealResponse:
    """Get deal by ID."""
    from sqlalchemy import select

    query = select(Deal).where(Deal.id == deal_id)
    result = await session.execute(query)
    deal = result.scalar_one_or_none()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    # Check access (agent can only see their own deals, admins can see all)
    if user.role not in ("admin", "superuser") and deal.agent_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own deals",
        )

    return _deal_to_response(deal)


@router.patch(
    "/deals/{deal_id}",
    response_model=DealResponse,
    summary="Update deal",
    description="Update deal status and other fields.",
)
async def update_deal(
    deal_id: str,
    body: DealUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> DealResponse:
    """Update a deal."""
    from sqlalchemy import select

    query = select(Deal).where(Deal.id == deal_id)
    result = await session.execute(query)
    deal = result.scalar_one_or_none()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    # Check access
    if user.role not in ("admin", "superuser") and deal.agent_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own deals",
        )

    # Update fields
    update_data = body.model_dump(exclude_unset=True)

    # Handle status transitions
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == "offer_accepted" and deal.offer_accepted_at is None:
            deal.offer_accepted_at = (
                datetime.now(deal.offer_accepted_at.tzinfo)
                if deal.offer_accepted_at
                else datetime.now()
            )
        elif new_status == "contract_signed" and deal.contract_signed_at is None:
            deal.contract_signed_at = datetime.now()
        elif new_status == "closed" and deal.closed_at is None:
            deal.closed_at = datetime.now()

    for field, value in update_data.items():
        setattr(deal, field, value)

    await session.flush()
    await session.refresh(deal)

    logger.info("Deal updated: %s by user %s", sanitize_for_log(deal.id), sanitize_for_log(user.id))

    return _deal_to_response(deal)


def _deal_to_response(deal: Deal) -> DealResponse:
    """Convert Deal model to response schema."""
    days_to_close = None
    if deal.closed_at and deal.offer_submitted_at:
        delta = deal.closed_at - deal.offer_submitted_at
        days_to_close = delta.days

    return DealResponse(
        id=deal.id,
        lead_id=deal.lead_id,
        agent_id=deal.agent_id,
        property_id=deal.property_id,
        deal_type=deal.deal_type,
        deal_value=deal.deal_value,
        currency=deal.currency,
        status=deal.status,
        property_type=deal.property_type,
        property_city=deal.property_city,
        property_district=deal.property_district,
        offer_submitted_at=deal.offer_submitted_at,
        offer_accepted_at=deal.offer_accepted_at,
        contract_signed_at=deal.contract_signed_at,
        closed_at=deal.closed_at,
        days_to_close=days_to_close,
        created_at=deal.created_at,
    )
