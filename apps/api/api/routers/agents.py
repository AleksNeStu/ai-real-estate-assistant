"""Agent/Broker API endpoints for public directory and contact functionality."""

from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps.auth import get_current_active_user, get_current_user_optional
from db.database import get_db
from db.models import User
from db.repositories import (
    AgentInquiryRepository,
    AgentListingRepository,
    AgentProfileRepository,
    ViewingAppointmentRepository,
)
from db.schemas import (
    AgentInquiryCreate,
    AgentInquiryListResponse,
    AgentInquiryResponse,
    AgentInquiryUpdate,
    AgentListingListResponse,
    AgentListingResponse,
    AgentProfileCreate,
    AgentProfileListResponse,
    AgentProfileResponse,
    AgentProfileUpdate,
    ViewingAppointmentCreate,
    ViewingAppointmentListResponse,
    ViewingAppointmentResponse,
    ViewingAppointmentUpdate,
)

router = APIRouter(prefix="/agents", tags=["Agents"])


# =============================================================================
# Helper Functions
# =============================================================================


async def _build_agent_response(
    profile: Any,
    user: Any = None,
    listings_count: Optional[int] = None,
) -> AgentProfileResponse:
    """Build agent response with user info.

    The user is never lazy-loaded: a lazy relationship load outside an awaited
    query raises MissingGreenlet in an async session, and the deployed demo
    answered 500 for the agent detail because of it. The repository eager-loads
    the relationship, and the endpoints that already hold the user pass it in.

    `listings_count` is the number of that agent's active listings in the
    catalogue - the number the directory shows and sorts by. It is passed in
    because counting it is the repository's job, not this function's.
    """
    user_data = None
    if profile.user_id:
        if user is None:
            user = profile.user
        if user:
            user_data = {
                "name": user.full_name,
                "email": user.email,
            }

    return AgentProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        name=user_data.get("name") if user_data else None,
        email=user_data.get("email") if user_data else None,
        agency_name=profile.agency_name,
        license_number=profile.license_number,
        license_state=profile.license_state,
        professional_email=profile.professional_email,
        professional_phone=profile.professional_phone,
        office_address=profile.office_address,
        specialties=profile.specialties or [],
        service_areas=profile.service_areas or [],
        property_types=profile.property_types or [],
        languages=profile.languages or [],
        average_rating=profile.average_rating,
        total_reviews=profile.total_reviews,
        total_sales=profile.total_sales,
        total_rentals=profile.total_rentals,
        listings_count=listings_count,
        is_verified=profile.is_verified,
        is_active=profile.is_active,
        profile_image_url=profile.profile_image_url,
        bio=profile.bio,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# =============================================================================
# Public Endpoints (no auth required)
# =============================================================================


@router.get(
    "",
    response_model=AgentProfileListResponse,
    summary="List agents",
    description="Get paginated list of agents with optional filters.",
)
async def list_agents(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    city: Optional[str] = Query(None, description="Filter by service area city"),
    specialty: Optional[str] = Query(None, description="Filter by specialty"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    agency_id: Optional[str] = Query(None, description="Filter by agency ID"),
    is_verified: Optional[bool] = Query(None, description="Filter by verified status"),
    language: Optional[str] = Query(None, description="Filter by language"),
    sort_by: str = Query("rating", description="Sort by: rating, listings, reviews, created"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    session: AsyncSession = Depends(get_db),
) -> AgentProfileListResponse:
    """List agents with pagination and filters."""
    # Validate sort_by to prevent attribute access on unexpected ORM fields
    _allowed_agent_sort = {
        "rating",
        "listings",
        "reviews",
        "created",
        "created_at",
        "average_rating",
        "total_sales",
        "total_reviews",
    }
    if sort_by not in _allowed_agent_sort:
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort_by}")

    agent_repo = AgentProfileRepository(session)

    offset = (page - 1) * page_size

    # Get agents with filters
    agents = await agent_repo.get_list(
        city=city,
        specialty=specialty,
        property_type=property_type,
        min_rating=min_rating,
        agency_id=agency_id,
        is_verified=is_verified,
        language=language,
        limit=page_size,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Get total count
    total = await agent_repo.count(
        city=city,
        specialty=specialty,
        property_type=property_type,
        min_rating=min_rating,
        agency_id=agency_id,
        is_verified=is_verified,
        language=language,
    )

    # The number of listings each agent has, counted for the whole page in
    # one query. An agent with no listing reads as zero - the catalogue is
    # empty for them, and zero is the truth about it.
    listing_repo = AgentListingRepository(session)
    listings_counts = await listing_repo.count_by_agents([agent.id for agent in agents])

    # Build response items
    items = []
    for agent in agents:
        items.append(
            await _build_agent_response(
                agent,
                listings_count=listings_counts.get(agent.id, 0),
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return AgentProfileListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{agent_id}",
    response_model=AgentProfileResponse,
    summary="Get agent details",
    description="Get detailed agent profile by ID.",
)
async def get_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db),
) -> AgentProfileResponse:
    """Get agent profile details."""
    agent_repo = AgentProfileRepository(session)

    profile = await agent_repo.get_by_id(agent_id)
    if not profile or not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return await _build_agent_response(profile)


@router.get(
    "/{agent_id}/listings",
    response_model=AgentListingListResponse,
    summary="Get agent listings",
    description="Get properties listed by an agent.",
)
async def get_agent_listings(
    agent_id: str,
    listing_type: Optional[str] = Query(None, description="Filter by listing type (sale/rent)"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_db),
) -> AgentListingListResponse:
    """Get agent's property listings."""
    agent_repo = AgentProfileRepository(session)
    listing_repo = AgentListingRepository(session)

    # Verify agent exists
    profile = await agent_repo.get_by_id(agent_id)
    if not profile or not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    listings = await listing_repo.get_by_agent(
        agent_id=agent_id,
        listing_type=listing_type,
        active_only=True,
        limit=limit,
        offset=offset,
    )

    total = await listing_repo.count_for_agent(agent_id, active_only=True)

    # Build response with property data
    items = []
    for listing in listings:
        items.append(
            AgentListingResponse(
                id=listing.id,
                agent_id=listing.agent_id,
                property_id=listing.property_id,
                listing_type=listing.listing_type,
                is_primary=listing.is_primary,
                is_active=listing.is_active,
                commission_rate=listing.commission_rate,
                created_at=listing.created_at,
                property=None,  # Would need to fetch from ChromaDB
            )
        )

    return AgentListingListResponse(
        items=items,
        total=total,
    )


@router.post(
    "/{agent_id}/contact",
    response_model=AgentInquiryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Contact agent",
    description="Send an inquiry to an agent (contact form).",
)
async def contact_agent(
    agent_id: str,
    body: AgentInquiryCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> AgentInquiryResponse:
    """Send an inquiry to an agent."""
    agent_repo = AgentProfileRepository(session)
    inquiry_repo = AgentInquiryRepository(session)

    # Verify agent exists
    profile = await agent_repo.get_by_id(agent_id)
    if not profile or not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Get optional user info
    user = await get_current_user_optional(request)
    user_id = user.id if user else None
    visitor_id = None  # Could extract from cookie/header

    # Create inquiry
    inquiry = await inquiry_repo.create(
        agent_id=agent_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        property_id=body.property_id,
        inquiry_type=body.inquiry_type,
        message=body.message,
        user_id=user_id,
        visitor_id=visitor_id,
    )

    return AgentInquiryResponse(
        id=inquiry.id,
        agent_id=inquiry.agent_id,
        user_id=inquiry.user_id,
        visitor_id=inquiry.visitor_id,
        name=inquiry.name,
        email=inquiry.email,
        phone=inquiry.phone,
        property_id=inquiry.property_id,
        inquiry_type=inquiry.inquiry_type,
        message=inquiry.message,
        status=inquiry.status,
        created_at=inquiry.created_at,
        read_at=inquiry.read_at,
        responded_at=inquiry.responded_at,
    )


@router.post(
    "/{agent_id}/schedule-viewing",
    response_model=ViewingAppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule viewing",
    description="Request a property viewing appointment with an agent.",
)
async def schedule_viewing(
    agent_id: str,
    body: ViewingAppointmentCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> ViewingAppointmentResponse:
    """Request a viewing appointment."""
    agent_repo = AgentProfileRepository(session)
    appointment_repo = ViewingAppointmentRepository(session)

    # Verify agent exists
    profile = await agent_repo.get_by_id(agent_id)
    if not profile or not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Validate proposed datetime is in the future
    if body.proposed_datetime <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposed datetime must be in the future",
        )

    # Get optional user info
    user = await get_current_user_optional(request)
    user_id = user.id if user else None

    # Create appointment
    appointment = await appointment_repo.create(
        agent_id=agent_id,
        property_id=body.property_id,
        proposed_datetime=body.proposed_datetime,
        duration_minutes=body.duration_minutes,
        client_name=body.client_name,
        client_email=body.client_email,
        client_phone=body.client_phone,
        notes=body.notes,
        user_id=user_id,
    )

    return ViewingAppointmentResponse(
        id=appointment.id,
        agent_id=appointment.agent_id,
        user_id=appointment.user_id,
        visitor_id=appointment.visitor_id,
        client_name=appointment.client_name,
        client_email=appointment.client_email,
        client_phone=appointment.client_phone,
        property_id=appointment.property_id,
        proposed_datetime=appointment.proposed_datetime,
        confirmed_datetime=appointment.confirmed_datetime,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status,
        notes=appointment.notes,
        cancellation_reason=appointment.cancellation_reason,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
        agent_name=profile.user.full_name if profile.user else None,
    )


# =============================================================================
# Protected Endpoints (auth required - agent only)
# =============================================================================


@router.get(
    "/profile",
    response_model=AgentProfileResponse,
    summary="Get own profile",
    description="Get the authenticated agent's profile.",
)
async def get_own_profile(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AgentProfileResponse:
    """Get authenticated agent's profile."""
    agent_repo = AgentProfileRepository(session)

    profile = await agent_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found. Please create one first.",
        )

    return await _build_agent_response(profile)


@router.post(
    "/profile",
    response_model=AgentProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create profile",
    description="Create an agent profile for the authenticated user.",
)
async def create_profile(
    body: AgentProfileCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AgentProfileResponse:
    """Create agent profile for authenticated user."""
    agent_repo = AgentProfileRepository(session)

    # Check if profile already exists
    existing = await agent_repo.get_by_user_id(user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent profile already exists. Use PATCH to update.",
        )

    # Create profile
    profile = await agent_repo.create(
        user_id=user.id,
        **body.model_dump(),
    )

    # The user is passed in: a fresh profile has no loaded relationship, and
    # loading it lazily raises MissingGreenlet in an async session.
    return await _build_agent_response(profile, user=user)


@router.patch(
    "/profile",
    response_model=AgentProfileResponse,
    summary="Update profile",
    description="Update the authenticated agent's profile.",
)
async def update_own_profile(
    body: AgentProfileUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AgentProfileResponse:
    """Update authenticated agent's profile."""
    agent_repo = AgentProfileRepository(session)

    profile = await agent_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found",
        )

    # Update profile
    update_data = body.model_dump(exclude_unset=True)
    profile = await agent_repo.update(profile, **update_data)

    return await _build_agent_response(profile, user=user)


@router.get(
    "/inquiries",
    response_model=AgentInquiryListResponse,
    summary="List inquiries",
    description="Get inquiries for the authenticated agent.",
)
async def list_own_inquiries(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    inquiry_type: Optional[str] = Query(None, description="Filter by inquiry type"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AgentInquiryListResponse:
    """List inquiries for authenticated agent."""
    agent_repo = AgentProfileRepository(session)
    inquiry_repo = AgentInquiryRepository(session)

    profile = await agent_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found",
        )

    offset = (page - 1) * page_size

    inquiries = await inquiry_repo.get_by_agent(
        agent_id=profile.id,
        status=status_filter,
        inquiry_type=inquiry_type,
        limit=page_size,
        offset=offset,
    )

    total = await inquiry_repo.count_for_agent(
        agent_id=profile.id,
        status=status_filter,
    )

    items = [
        AgentInquiryResponse(
            id=i.id,
            agent_id=i.agent_id,
            user_id=i.user_id,
            visitor_id=i.visitor_id,
            name=i.name,
            email=i.email,
            phone=i.phone,
            property_id=i.property_id,
            inquiry_type=i.inquiry_type,
            message=i.message,
            status=i.status,
            created_at=i.created_at,
            read_at=i.read_at,
            responded_at=i.responded_at,
        )
        for i in inquiries
    ]

    total_pages = (total + page_size - 1) // page_size

    return AgentInquiryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/inquiries/{inquiry_id}",
    response_model=AgentInquiryResponse,
    summary="Update inquiry",
    description="Update inquiry status (agent only).",
)
async def update_inquiry(
    inquiry_id: str,
    body: AgentInquiryUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AgentInquiryResponse:
    """Update inquiry status."""
    agent_repo = AgentProfileRepository(session)
    inquiry_repo = AgentInquiryRepository(session)

    profile = await agent_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found",
        )

    inquiry = await inquiry_repo.get_by_id(inquiry_id)
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inquiry not found",
        )

    # Verify ownership
    if inquiry.agent_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this inquiry",
        )

    # Update status
    if body.status:
        if body.status == "read":
            await inquiry_repo.mark_read(inquiry)
        elif body.status == "responded":
            await inquiry_repo.mark_responded(inquiry)
        else:
            await inquiry_repo.update_status(inquiry, body.status)

    return AgentInquiryResponse(
        id=inquiry.id,
        agent_id=inquiry.agent_id,
        user_id=inquiry.user_id,
        visitor_id=inquiry.visitor_id,
        name=inquiry.name,
        email=inquiry.email,
        phone=inquiry.phone,
        property_id=inquiry.property_id,
        inquiry_type=inquiry.inquiry_type,
        message=inquiry.message,
        status=inquiry.status,
        created_at=inquiry.created_at,
        read_at=inquiry.read_at,
        responded_at=inquiry.responded_at,
    )


@router.get(
    "/appointments",
    response_model=ViewingAppointmentListResponse,
    summary="List appointments",
    description="Get viewing appointments for the authenticated agent.",
)
async def list_own_appointments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ViewingAppointmentListResponse:
    """List appointments for authenticated agent."""
    agent_repo = AgentProfileRepository(session)
    appointment_repo = ViewingAppointmentRepository(session)

    profile = await agent_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found",
        )

    offset = (page - 1) * page_size

    appointments = await appointment_repo.get_by_agent(
        agent_id=profile.id,
        status=status_filter,
        limit=page_size,
        offset=offset,
    )

    total = await appointment_repo.count_for_agent(
        agent_id=profile.id,
        status=status_filter,
    )

    items = [
        ViewingAppointmentResponse(
            id=a.id,
            agent_id=a.agent_id,
            user_id=a.user_id,
            visitor_id=a.visitor_id,
            client_name=a.client_name,
            client_email=a.client_email,
            client_phone=a.client_phone,
            property_id=a.property_id,
            proposed_datetime=a.proposed_datetime,
            confirmed_datetime=a.confirmed_datetime,
            duration_minutes=a.duration_minutes,
            status=a.status,
            notes=a.notes,
            cancellation_reason=a.cancellation_reason,
            created_at=a.created_at,
            updated_at=a.updated_at,
            agent_name=user.full_name,
        )
        for a in appointments
    ]

    total_pages = (total + page_size - 1) // page_size

    return ViewingAppointmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/appointments/{appointment_id}",
    response_model=ViewingAppointmentResponse,
    summary="Update appointment",
    description="Update appointment status (agent only).",
)
async def update_appointment(
    appointment_id: str,
    body: ViewingAppointmentUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ViewingAppointmentResponse:
    """Update appointment status."""
    agent_repo = AgentProfileRepository(session)
    appointment_repo = ViewingAppointmentRepository(session)

    profile = await agent_repo.get_by_user_id(user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found",
        )

    appointment = await appointment_repo.get_by_id(appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    # Verify ownership
    if appointment.agent_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this appointment",
        )

    # Update appointment
    update_data = body.model_dump(exclude_unset=True)
    appointment = await appointment_repo.update(appointment, **update_data)

    return ViewingAppointmentResponse(
        id=appointment.id,
        agent_id=appointment.agent_id,
        user_id=appointment.user_id,
        visitor_id=appointment.visitor_id,
        client_name=appointment.client_name,
        client_email=appointment.client_email,
        client_phone=appointment.client_phone,
        property_id=appointment.property_id,
        proposed_datetime=appointment.proposed_datetime,
        confirmed_datetime=appointment.confirmed_datetime,
        duration_minutes=appointment.duration_minutes,
        status=appointment.status,
        notes=appointment.notes,
        cancellation_reason=appointment.cancellation_reason,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
        agent_name=user.full_name,
    )
