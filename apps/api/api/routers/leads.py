"""Lead Scoring and Tracking API endpoints."""

import csv
import io
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user, get_current_user_optional
from db.database import get_db
from db.models import User
from db.repositories import (
    AgentAssignmentRepository,
    LeadInteractionRepository,
    LeadRepository,
    LeadScoreRepository,
)
from db.schemas import (
    AgentAssignmentCreate,
    AgentAssignmentResponse,
    AgentFunnelResponse,
    BulkAssignRequest,
    BulkOperationResponse,
    BulkStatusUpdateRequest,
    CreateAndScoreLeadRequest,
    LeadCreate,
    LeadDetailResponse,
    LeadInteractionResponse,
    LeadListResponse,
    LeadResponse,
    LeadScoreBreakdown,
    LeadScoreInputSchema,
    LeadScoreResponse,
    LeadUpdate,
    LeadWithScoreResponse,
    MessageResponse,
    PrioritizedScoreResponse,
    RecalculateScoresRequest,
    RecalculateScoresResponse,
    TrackInteractionRequest,
)
from services.lead_scoring import (
    LeadScoringInput,
    LeadScoringService,
    PrioritizedLeadScoringService,
)
from services.lead_tracking import LeadTrackingService

router = APIRouter(prefix="/leads", tags=["Lead Scoring"])


# =============================================================================
# PII redaction
# =============================================================================
#
# In demo mode `api.deps.auth.get_current_user` hands EVERY caller the synthetic
# admin account (id="demo-user-id"), so an anonymous visitor would otherwise be
# able to list every lead and read every lead's real email address. The helpers
# below redact the contact fields for that actor while leaving the behaviour of a
# genuinely authenticated admin/agent untouched.

DEMO_USER_ID = "demo-user-id"
DEMO_USER_EMAIL = "demo@example.com"


def _is_demo_actor(user: Optional[User]) -> bool:
    """True when the caller is the synthetic demo/anonymous identity."""
    if user is None:
        return True
    if getattr(user, "id", None) == DEMO_USER_ID:
        return True
    if getattr(user, "email", None) == DEMO_USER_EMAIL:
        return True
    return False


def _mask_email(email: Optional[str]) -> Optional[str]:
    """Reduce an email address to a non-identifying hint (e.g. ``a***@example.com``)."""
    if not email:
        return None
    local, separator, domain = email.partition("@")
    if not separator:
        return "***"
    masked_local = "*" if len(local) <= 1 else f"{local[0]}***"
    return f"{masked_local}@{domain}"


def _mask_phone(phone: Optional[str]) -> Optional[str]:
    """Reduce a phone number to its last two digits."""
    if not phone:
        return None
    digits = "".join(char for char in phone if char.isdigit())
    if len(digits) <= 2:
        return "***"
    return f"***{digits[-2:]}"


def _mask_name(name: Optional[str]) -> Optional[str]:
    """Reduce a person's name to a non-identifying initial (e.g. ``A***``).

    A visitor's name is personal detail exactly as much as their address is,
    and the public lead endpoints collect one (``POST /leads`` takes a name, a
    phone number and an email address). Masking only the address would leave
    the other two columns readable.
    """
    if not name:
        return None
    stripped = name.strip()
    if not stripped:
        return None
    return f"{stripped[0]}***"


def _redact_contact(
    email: Optional[str],
    phone: Optional[str],
    *,
    keep_email: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Return an ``(email, phone)`` pair that is safe to hand to the caller.

    The email is preserved only when it is exactly the address the caller
    submitted (their own input, so echoing it leaks nothing new). Every other
    address is masked. The phone is always masked: a phone number is never
    supplied by the caller on the public tracking endpoints.
    """
    if keep_email and email and email.strip().lower() == keep_email.strip().lower():
        visible_email = email
    else:
        visible_email = _mask_email(email)
    return visible_email, _mask_phone(phone)


def _redact_lead_identity(
    lead: Any,
    *,
    keep_email: Optional[str] = None,
    keep_name: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return the ``(email, phone, name)`` triple that is safe to hand out.

    A field is left readable only when it is exactly what the caller just
    submitted — their own input, echoed back, which leaks nothing new. Every
    other visitor's details are masked.
    """
    email, phone = _redact_contact(lead.email, lead.phone, keep_email=keep_email)
    name = lead.name
    if keep_name and name and name.strip().lower() == keep_name.strip().lower():
        visible_name = name
    else:
        visible_name = _mask_name(name)
    return email, phone, visible_name


# =============================================================================
# Public Tracking Endpoints (no auth required)
# =============================================================================


@router.post(
    "/track",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Track visitor interaction",
    description="Record a visitor interaction for lead scoring. Uses visitor_id cookie.",
)
async def track_interaction(
    body: TrackInteractionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    user: Optional = Depends(get_current_user_optional),
) -> None:
    """Track a visitor interaction."""
    tracking_service = LeadTrackingService(session)

    # Get optional user ID if logged in
    user_id = user.id if user else None

    await tracking_service.track_interaction(
        visitor_id=body.visitor_id,
        interaction_type=body.interaction_type,
        property_id=body.property_id,
        search_query=body.search_query,
        metadata=body.metadata,
        session_id=body.session_id,
        page_url=body.page_url,
        referrer=body.referrer,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        time_spent_seconds=body.time_spent_seconds,
        user_id=user_id,
    )


@router.post(
    "/visitor",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or get visitor",
    description="Create a new visitor record or get existing one by visitor_id.",
)
async def get_or_create_visitor(
    body: LeadCreate,
    session: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """Get or create a visitor lead record."""
    tracking_service = LeadTrackingService(session)
    lead, is_new = await tracking_service.get_or_create_visitor(
        visitor_id=body.visitor_id,
        user_id=body.user_id,
        email=body.email,
        source=body.source,
        consent_given=body.consent_given,
    )

    # The contact fields are redacted: this endpoint is public, so the caller
    # may not own the lead that was found by visitor_id.
    visible_email, visible_phone, visible_name = _redact_lead_identity(lead, keep_email=body.email)
    response = LeadResponse.model_validate(lead)
    response.email = visible_email
    response.phone = visible_phone
    response.name = visible_name
    return response


# =============================================================================
# Task #113: Prioritized Lead Scoring Endpoints
# =============================================================================


@router.post(
    "",
    response_model=LeadWithScoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and score a lead",
    description="Create a new lead and immediately calculate its priority score "
    "based on budget fit, urgency, and engagement signals.",
)
async def create_and_score_lead(
    body: CreateAndScoreLeadRequest,
    session: AsyncSession = Depends(get_db),
) -> LeadWithScoreResponse:
    """Create a lead and score it in one request."""
    tracking_service = LeadTrackingService(session)
    lead, is_new = await tracking_service.get_or_create_visitor(
        visitor_id=body.visitor_id,
        user_id=body.user_id,
        email=body.email,
        source=body.source,
        consent_given=body.consent_given,
    )

    # Update budget if provided
    if body.budget_min is not None or body.budget_max is not None:
        lead_repo = LeadRepository(session)
        await lead_repo.update(
            lead,
            budget_min=body.budget_min,
            budget_max=body.budget_max,
        )

    # Score using PrioritizedLeadScoringService
    scoring_svc = PrioritizedLeadScoringService(session)
    lead_input = LeadScoringInput(
        budget_min=body.budget_min,
        budget_max=body.budget_max,
        target_price_min=body.target_price_min,
        target_price_max=body.target_price_max,
        has_email=body.email is not None,
        has_phone=body.phone is not None,
        has_name=body.name is not None,
        source=body.source,
        agent_id=body.agent_id,
        property_id=body.property_id,
        desired_move_date=body.desired_move_date,
    )
    result = scoring_svc.score_lead(lead_input)

    # Also run the standard scoring if there are interactions
    std_scoring = LeadScoringService(session)
    await std_scoring.score_lead(lead.id)

    visible_email, visible_phone, visible_name = _redact_lead_identity(
        lead, keep_email=body.email, keep_name=body.name
    )

    return LeadWithScoreResponse(
        id=lead.id,
        visitor_id=lead.visitor_id,
        user_id=lead.user_id,
        email=visible_email,
        phone=visible_phone,
        name=visible_name,
        budget_min=lead.budget_min,
        budget_max=lead.budget_max,
        preferred_locations=lead.preferred_locations,
        status=lead.status,
        source=lead.source,
        current_score=lead.current_score,
        first_seen_at=lead.first_seen_at,
        last_activity_at=lead.last_activity_at,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        consent_given=lead.consent_given,
        consent_at=lead.consent_at,
        assigned_agent_id=None,
        assigned_agent_name=None,
        latest_score=None,
        interaction_count=0,
        priority_score=PrioritizedScoreResponse(
            score=result.score,
            budget_fit=result.budget_fit,
            urgency=result.urgency,
            engagement=result.engagement,
            priority_tier=result.priority_tier,
            factors=result.factors,
            recommendations=result.recommendations,
        ),
    )


@router.post(
    "/scores",
    response_model=PrioritizedScoreResponse,
    summary="Score lead data",
    description="Calculate priority score for provided lead data without creating a record. "
    "Returns budget fit, urgency, and engagement breakdown.",
)
async def score_lead_data(
    body: LeadScoreInputSchema,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PrioritizedScoreResponse:
    """Score lead data and return breakdown without persisting."""
    scoring_svc = PrioritizedLeadScoringService(session)

    lead_input = LeadScoringInput(
        budget_min=body.budget_min,
        budget_max=body.budget_max,
        target_price_min=body.target_price_min,
        target_price_max=body.target_price_max,
        searches=body.searches,
        property_views=body.property_views,
        favorites=body.favorites,
        inquiries=body.inquiries,
        contact_requests=body.contact_requests,
        desired_move_date=body.desired_move_date,
        days_since_first_seen=body.days_since_first_seen,
        days_since_last_activity=body.days_since_last_activity,
        has_email=body.has_email,
        has_phone=body.has_phone,
        has_name=body.has_name,
        source=body.source,
        agent_id=body.agent_id,
        property_id=body.property_id,
    )
    result = scoring_svc.score_lead(lead_input)

    return PrioritizedScoreResponse(
        score=result.score,
        budget_fit=result.budget_fit,
        urgency=result.urgency,
        engagement=result.engagement,
        priority_tier=result.priority_tier,
        factors=result.factors,
        recommendations=result.recommendations,
    )


@router.get(
    "/funnel",
    response_model=AgentFunnelResponse,
    summary="Get agent lead funnel",
    description="Get lead funnel statistics for the current agent or a specified agent. "
    "Shows leads by priority tier and status for visualization.",
)
async def get_agent_funnel(
    agent_id: Optional[str] = Query(
        None, description="Agent ID (admin only, defaults to current user)"
    ),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AgentFunnelResponse:
    """Get lead funnel visualization data per agent."""
    # Determine which agent's funnel to show
    target_agent = agent_id
    if target_agent is None:
        target_agent = user.id
    elif user.role not in ("admin", "superuser"):
        # Non-admin can only see their own funnel
        target_agent = user.id

    scoring_svc = PrioritizedLeadScoringService(session)
    funnel = await scoring_svc.get_agent_funnel(target_agent)

    return AgentFunnelResponse(**funnel)


# =============================================================================
# Lead Management Endpoints (requires auth)
# =============================================================================


@router.get(
    "",
    response_model=LeadListResponse,
    summary="List leads",
    description="Get paginated list of leads. Agents see their assigned leads, admins see all.",
)
async def list_leads(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    score_min: Optional[int] = Query(None, ge=0, le=100, description="Minimum score"),
    score_max: Optional[int] = Query(None, ge=0, le=100, description="Maximum score"),
    source: Optional[str] = Query(None, description="Filter by source"),
    has_email: Optional[bool] = Query(None, description="Filter by has email"),
    sort_by: str = Query("score", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> LeadListResponse:
    """List leads with filtering and pagination."""
    lead_repo = LeadRepository(session)
    score_repo = LeadScoreRepository(session)
    assignment_repo = AgentAssignmentRepository(session)

    # Determine agent filter based on role
    agent_id = None
    if user.role not in ("admin", "superuser"):
        # Non-admin users only see their assigned leads
        agent_id = user.id

    offset = (page - 1) * page_size

    # Get leads
    leads = await lead_repo.get_list(
        agent_id=agent_id,
        status=status,
        score_min=score_min,
        score_max=score_max,
        has_email=has_email,
        limit=page_size,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Get total count
    total = await lead_repo.count(
        agent_id=agent_id,
        status=status,
        score_min=score_min,
        score_max=score_max,
        has_email=has_email,
    )

    # Build response with scores
    # A demo/anonymous caller must never read another visitor's real contact
    # details, so the contact fields are masked for that actor only.
    redact = _is_demo_actor(user)
    items = []
    for lead in leads:
        latest_score = await score_repo.get_latest_for_lead(lead.id)
        assignment = await assignment_repo.get_primary_for_lead(lead.id)

        if redact:
            visible_email, visible_phone, visible_name = _redact_lead_identity(lead)
        else:
            visible_email, visible_phone, visible_name = lead.email, lead.phone, lead.name

        lead_data = LeadWithScoreResponse(
            id=lead.id,
            visitor_id=lead.visitor_id,
            user_id=lead.user_id,
            email=visible_email,
            phone=visible_phone,
            name=visible_name,
            budget_min=lead.budget_min,
            budget_max=lead.budget_max,
            preferred_locations=lead.preferred_locations,
            status=lead.status,
            source=lead.source,
            current_score=lead.current_score,
            first_seen_at=lead.first_seen_at,
            last_activity_at=lead.last_activity_at,
            created_at=lead.created_at,
            updated_at=lead.updated_at,
            consent_given=lead.consent_given,
            consent_at=lead.consent_at,
            assigned_agent_id=assignment.agent_id if assignment else None,
            assigned_agent_name=None,  # Would need to join with User
            latest_score=LeadScoreResponse.model_validate(latest_score) if latest_score else None,
            interaction_count=0,  # Would need to count
        )
        items.append(lead_data)

    return LeadListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/high-value",
    response_model=list[LeadWithScoreResponse],
    summary="Get high-value leads",
    description="Get leads with scores above threshold (70+).",
)
async def get_high_value_leads(
    threshold: int = Query(70, ge=0, le=100, description="Score threshold"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[LeadWithScoreResponse]:
    """Get high-value leads above score threshold."""
    scoring_service = LeadScoringService(session)

    # Determine agent filter
    agent_id = None if user.role in ("admin", "superuser") else user.id

    leads = await scoring_service.get_high_value_leads(
        threshold=threshold,
        limit=limit,
        assigned_to_agent=agent_id,
    )

    redact = _is_demo_actor(user)
    results = []
    for lead in leads:
        if redact:
            visible_email, visible_phone = _redact_contact(lead.get("email"), lead.get("phone"))
            visible_name = _mask_name(lead.get("name"))
            lead = {
                **lead,
                "email": visible_email,
                "phone": visible_phone,
                "name": visible_name,
            }
        results.append(LeadWithScoreResponse(**lead))
    return results


# =============================================================================
# Export Endpoint (admin only) — must be before /{lead_id} routes
# =============================================================================


@router.get(
    "/export",
    summary="Export leads",
    description="Export leads to CSV. Admin only.",
)
async def export_leads(
    lead_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    score_min: Optional[int] = Query(None, description="Minimum score"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export leads to CSV."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can export leads",
        )

    lead_repo = LeadRepository(session)

    # Get all leads matching filters
    leads = await lead_repo.get_list(
        status=lead_status,
        score_min=score_min,
        limit=10000,  # Max export size
    )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(
        [
            "ID",
            "Visitor ID",
            "Email",
            "Name",
            "Phone",
            "Status",
            "Source",
            "Current Score",
            "First Seen",
            "Last Activity",
            "Created At",
            "Consent Given",
            "Budget Min",
            "Budget Max",
        ]
    )

    # Write data rows
    redact = _is_demo_actor(user)
    for lead in leads:
        if redact:
            visible_email, visible_phone, visible_name = _redact_lead_identity(lead)
        else:
            visible_email, visible_phone, visible_name = lead.email, lead.phone, lead.name
        writer.writerow(
            [
                lead.id,
                lead.visitor_id,
                visible_email or "",
                visible_name or "",
                visible_phone or "",
                lead.status,
                lead.source or "",
                lead.current_score,
                lead.first_seen_at.isoformat() if lead.first_seen_at else "",
                lead.last_activity_at.isoformat() if lead.last_activity_at else "",
                lead.created_at.isoformat() if lead.created_at else "",
                lead.consent_given,
                lead.budget_min or "",
                lead.budget_max or "",
            ]
        )

    output.seek(0)

    # Generate filename with timestamp
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"leads_export_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{lead_id}",
    response_model=LeadDetailResponse,
    summary="Get lead details",
    description="Get detailed lead information including interactions and score history.",
)
async def get_lead(
    lead_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> LeadDetailResponse:
    """Get detailed lead information."""
    lead_repo = LeadRepository(session)
    score_repo = LeadScoreRepository(session)
    interaction_repo = LeadInteractionRepository(session)
    assignment_repo = AgentAssignmentRepository(session)

    lead = await lead_repo.get_by_id(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Check access (agents can only see their assigned leads)
    if user.role not in ("admin", "superuser"):
        assignment = await assignment_repo.get_primary_for_lead(lead_id)
        if not assignment or assignment.agent_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this lead",
            )

    # Get related data
    latest_score = await score_repo.get_latest_for_lead(lead_id)
    score_history = await score_repo.get_history_for_lead(lead_id, limit=10)
    interactions = await interaction_repo.get_by_lead(lead_id, limit=20)
    assignment = await assignment_repo.get_primary_for_lead(lead_id)

    if _is_demo_actor(user):
        visible_email, visible_phone, visible_name = _redact_lead_identity(lead)
    else:
        visible_email, visible_phone, visible_name = lead.email, lead.phone, lead.name

    return LeadDetailResponse(
        id=lead.id,
        visitor_id=lead.visitor_id,
        user_id=lead.user_id,
        email=visible_email,
        phone=visible_phone,
        name=visible_name,
        budget_min=lead.budget_min,
        budget_max=lead.budget_max,
        preferred_locations=lead.preferred_locations,
        status=lead.status,
        source=lead.source,
        current_score=lead.current_score,
        first_seen_at=lead.first_seen_at,
        last_activity_at=lead.last_activity_at,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        consent_given=lead.consent_given,
        consent_at=lead.consent_at,
        assigned_agent_id=assignment.agent_id if assignment else None,
        assigned_agent_name=None,
        latest_score=LeadScoreResponse.model_validate(latest_score) if latest_score else None,
        interaction_count=len(interactions),
        recent_interactions=[
            LeadInteractionResponse(
                id=i.id,
                lead_id=i.lead_id,
                interaction_type=i.interaction_type,
                property_id=i.property_id,
                search_query=i.search_query,
                created_at=i.created_at,
            )
            for i in interactions
        ],
        score_history=[
            LeadScoreResponse(
                id=s.id,
                lead_id=s.lead_id,
                total_score=s.total_score,
                search_activity_score=s.search_activity_score,
                engagement_score=s.engagement_score,
                intent_score=s.intent_score,
                score_factors=s.score_factors,
                recommendations=s.recommendations,
                model_version=s.model_version,
                calculated_at=s.calculated_at,
            )
            for s in score_history
        ],
    )


@router.get(
    "/{lead_id}/score",
    response_model=LeadScoreBreakdown,
    summary="Get lead score breakdown",
    description="Get detailed score breakdown with factors and recommendations.",
)
async def get_lead_score(
    lead_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> LeadScoreBreakdown:
    """Get detailed lead score breakdown."""
    scoring_service = LeadScoringService(session)

    breakdown = await scoring_service.get_lead_score_breakdown(lead_id)
    if not breakdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    latest = breakdown.get("latest_score")
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No score available for lead",
        )

    return LeadScoreBreakdown(
        total_score=latest["total_score"],
        components={
            "search_activity": latest["search_activity_score"],
            "engagement": latest["engagement_score"],
            "intent": latest["intent_score"],
        },
        factors=latest["score_factors"],
        weights={
            "search_activity": 0.25,
            "engagement": 0.35,
            "intent": 0.40,
        },
        recommendations=latest.get("recommendations", []),
        percentile=None,  # Would need to calculate
    )


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Update lead",
    description="Update lead information.",
)
async def update_lead(
    lead_id: str,
    body: LeadUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """Update lead information."""
    lead_repo = LeadRepository(session)
    assignment_repo = AgentAssignmentRepository(session)

    lead = await lead_repo.get_by_id(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Check access
    if user.role not in ("admin", "superuser"):
        assignment = await assignment_repo.get_primary_for_lead(lead_id)
        if not assignment or assignment.agent_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this lead",
            )

    updated_lead = await lead_repo.update(lead, **body.model_dump(exclude_unset=True))

    response = LeadResponse.model_validate(updated_lead)
    if _is_demo_actor(user):
        visible_email, visible_phone, visible_name = _redact_lead_identity(updated_lead)
        response.email = visible_email
        response.phone = visible_phone
        response.name = visible_name
    return response


@router.patch(
    "/{lead_id}/status",
    response_model=LeadResponse,
    summary="Update lead status",
    description="Update lead status (new, contacted, qualified, converted, lost).",
)
async def update_lead_status(
    lead_id: str,
    new_status: str = Query(..., alias="status", description="New status"),
    notes: Optional[str] = Query(None, description="Status change notes"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> LeadResponse:
    """Update lead status."""
    valid_statuses = ["new", "contacted", "qualified", "converted", "lost"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    tracking_service = LeadTrackingService(session)
    lead = await tracking_service.update_lead_status(lead_id, new_status, notes)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    response = LeadResponse.model_validate(lead)
    if _is_demo_actor(user):
        visible_email, visible_phone, visible_name = _redact_lead_identity(lead)
        response.email = visible_email
        response.phone = visible_phone
        response.name = visible_name
    return response


# =============================================================================
# Agent Assignment Endpoints (admin/agents only)
# =============================================================================


@router.post(
    "/{lead_id}/assign",
    response_model=AgentAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign agent to lead",
    description="Assign an agent to a lead. Admin only.",
)
async def assign_agent(
    lead_id: str,
    body: AgentAssignmentCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AgentAssignmentResponse:
    """Assign an agent to a lead."""
    if user.role not in ("admin", "superuser", "agent"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and agents can assign leads",
        )

    lead_repo = LeadRepository(session)
    assignment_repo = AgentAssignmentRepository(session)

    # Verify lead exists
    lead = await lead_repo.get_by_id(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    assignment = await assignment_repo.assign_lead_to_agent(
        lead_id=lead_id,
        agent_id=body.agent_id,
        assigned_by=user.id,
        notes=body.notes,
        is_primary=body.is_primary,
    )

    return AgentAssignmentResponse.model_validate(assignment)


@router.post(
    "/bulk/assign",
    response_model=BulkOperationResponse,
    summary="Bulk assign leads",
    description="Assign multiple leads to an agent. Admin only.",
)
async def bulk_assign_leads(
    body: BulkAssignRequest,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BulkOperationResponse:
    """Bulk assign leads to an agent."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can bulk assign leads",
        )

    assignment_repo = AgentAssignmentRepository(session)

    success_count = 0
    failed_ids = []

    for lead_id in body.lead_ids:
        try:
            await assignment_repo.assign_lead_to_agent(
                lead_id=lead_id,
                agent_id=body.agent_id,
                assigned_by=user.id,
                notes=body.notes,
                is_primary=True,
            )
            success_count += 1
        except Exception:
            failed_ids.append(lead_id)

    return BulkOperationResponse(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids if failed_ids else None,
        message=f"Assigned {success_count} leads to agent",
    )


@router.post(
    "/bulk/status",
    response_model=BulkOperationResponse,
    summary="Bulk update status",
    description="Update status for multiple leads.",
)
async def bulk_update_status(
    body: BulkStatusUpdateRequest,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BulkOperationResponse:
    """Bulk update lead status."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can bulk update lead status",
        )

    tracking_service = LeadTrackingService(session)

    success_count = 0
    failed_ids = []

    for lead_id in body.lead_ids:
        try:
            result = await tracking_service.update_lead_status(lead_id, body.status)
            if result:
                success_count += 1
            else:
                failed_ids.append(lead_id)
        except Exception:
            failed_ids.append(lead_id)

    return BulkOperationResponse(
        success_count=success_count,
        failed_count=len(failed_ids),
        failed_ids=failed_ids if failed_ids else None,
        message=f"Updated status for {success_count} leads",
    )


# =============================================================================
# Scoring Endpoints (admin only)
# =============================================================================


@router.post(
    "/scores/recalculate",
    response_model=RecalculateScoresResponse,
    summary="Recalculate lead scores",
    description="Trigger recalculation of lead scores. Admin only.",
)
async def recalculate_scores(
    body: Optional[RecalculateScoresRequest] = None,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> RecalculateScoresResponse:
    """Recalculate lead scores."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can recalculate scores",
        )

    import time

    start_time = time.time()

    scoring_service = LeadScoringService(session)
    result = await scoring_service.recalculate_all_scores(
        lead_ids=body.lead_ids if body else None,
        max_age_hours=24,
        force=body.force if body else False,
    )

    duration = time.time() - start_time

    return RecalculateScoresResponse(
        recalculated_count=result["recalculated"],
        failed_count=result["failed"],
        duration_seconds=duration,
        message=f"Recalculated {result['recalculated']} scores in {duration:.2f}s",
    )


@router.get(
    "/scores/statistics",
    response_model=dict[str, Any],
    summary="Get scoring statistics",
    description="Get overall lead scoring statistics.",
)
async def get_scoring_statistics(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get scoring statistics."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view scoring statistics",
        )

    scoring_service = LeadScoringService(session)
    return await scoring_service.get_scoring_statistics()


# =============================================================================
# GDPR Endpoints
# =============================================================================


@router.delete(
    "/{lead_id}",
    response_model=MessageResponse,
    summary="Delete lead data",
    description="Delete all lead data (GDPR right to be forgotten).",
)
async def delete_lead(
    lead_id: str,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Delete lead and all associated data."""
    if user.role not in ("admin", "superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete leads",
        )

    lead_repo = LeadRepository(session)
    lead = await lead_repo.get_by_id(lead_id)

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    await lead_repo.delete(lead)

    return MessageResponse(
        message="Lead deleted successfully",
        detail=f"All data for lead {lead_id} has been permanently removed",
    )
