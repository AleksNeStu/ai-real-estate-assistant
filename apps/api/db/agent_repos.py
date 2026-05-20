"""
Agent/Broker system repository classes (Task #45).

Provides repositories for AgentProfile, AgentListing,
AgentInquiry, and ViewingAppointment models.
"""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import (
    AgentInquiry,
    AgentListing,
    AgentProfile,
    ViewingAppointment,
)


class AgentProfileRepository:
    """Repository for agent profile operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        agency_name: Optional[str] = None,
        agency_id: Optional[str] = None,
        license_number: Optional[str] = None,
        license_state: Optional[str] = None,
        professional_email: Optional[str] = None,
        professional_phone: Optional[str] = None,
        office_address: Optional[str] = None,
        specialties: Optional[list[str]] = None,
        service_areas: Optional[list[str]] = None,
        property_types: Optional[list[str]] = None,
        languages: Optional[list[str]] = None,
        bio: Optional[str] = None,
        profile_image_url: Optional[str] = None,
    ) -> AgentProfile:
        """Create a new agent profile."""
        from uuid import uuid4

        profile = AgentProfile(
            id=str(uuid4()),
            user_id=user_id,
            agency_name=agency_name,
            agency_id=agency_id,
            license_number=license_number,
            license_state=license_state,
            professional_email=professional_email,
            professional_phone=professional_phone,
            office_address=office_address,
            specialties=specialties or [],
            service_areas=service_areas or [],
            property_types=property_types or [],
            languages=languages or [],
            bio=bio,
            profile_image_url=profile_image_url,
            is_verified=False,
            is_active=True,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def get_by_id(self, profile_id: str) -> Optional[AgentProfile]:
        """Get agent profile by ID."""
        result = await self.session.execute(
            select(AgentProfile).where(AgentProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: str) -> Optional[AgentProfile]:
        """Get agent profile by user ID."""
        result = await self.session.execute(
            select(AgentProfile).where(AgentProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        city: Optional[str] = None,
        specialty: Optional[str] = None,
        property_type: Optional[str] = None,
        min_rating: Optional[float] = None,
        agency_id: Optional[str] = None,
        is_verified: Optional[bool] = None,
        language: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "rating",
        sort_order: str = "desc",
    ) -> list[AgentProfile]:
        """Get list of agent profiles with filters."""
        query = (
            select(AgentProfile)
            .options(selectinload(AgentProfile.user))
            .where(
                AgentProfile.is_active == True  # noqa: E712
            )
        )

        # Apply filters
        if is_verified is not None:
            query = query.where(AgentProfile.is_verified == is_verified)
        if min_rating is not None:
            query = query.where(AgentProfile.average_rating >= min_rating)
        if agency_id is not None:
            query = query.where(AgentProfile.agency_id == agency_id)
        if city:
            query = query.where(AgentProfile.service_areas.contains([city]))
        if specialty:
            query = query.where(AgentProfile.specialties.contains([specialty]))
        if property_type:
            query = query.where(AgentProfile.property_types.contains([property_type]))
        if language:
            query = query.where(AgentProfile.languages.contains([language]))

        # Apply sorting
        sort_column = getattr(AgentProfile, sort_by, AgentProfile.average_rating)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        city: Optional[str] = None,
        specialty: Optional[str] = None,
        property_type: Optional[str] = None,
        min_rating: Optional[float] = None,
        agency_id: Optional[str] = None,
        is_verified: Optional[bool] = None,
        language: Optional[str] = None,
    ) -> int:
        """Count agent profiles with filters."""
        query = select(func.count(AgentProfile.id)).where(
            AgentProfile.is_active == True  # noqa: E712
        )

        if is_verified is not None:
            query = query.where(AgentProfile.is_verified == is_verified)
        if min_rating is not None:
            query = query.where(AgentProfile.average_rating >= min_rating)
        if agency_id is not None:
            query = query.where(AgentProfile.agency_id == agency_id)
        if city:
            query = query.where(AgentProfile.service_areas.contains([city]))
        if specialty:
            query = query.where(AgentProfile.specialties.contains([specialty]))
        if property_type:
            query = query.where(AgentProfile.property_types.contains([property_type]))
        if language:
            query = query.where(AgentProfile.languages.contains([language]))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update(self, profile: AgentProfile, **kwargs) -> AgentProfile:
        """Update agent profile fields."""
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        await self.session.flush()
        return profile

    async def update_rating(self, profile: AgentProfile, new_rating: float) -> None:
        """Recalculate average rating after new review."""
        profile.average_rating = new_rating
        await self.session.flush()

    async def increment_reviews(self, profile: AgentProfile) -> None:
        """Increment total reviews count."""
        profile.total_reviews += 1
        await self.session.flush()

    async def increment_sales(self, profile: AgentProfile) -> None:
        """Increment total sales count."""
        profile.total_sales += 1
        await self.session.flush()

    async def verify(self, profile: AgentProfile) -> None:
        """Verify an agent profile."""
        profile.is_verified = True
        profile.verification_date = datetime.now(UTC)
        await self.session.flush()

    async def delete(self, profile: AgentProfile) -> None:
        """Delete an agent profile (soft delete via is_active=False)."""
        profile.is_active = False
        await self.session.flush()


class AgentListingRepository:
    """Repository for agent listing operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        agent_id: str,
        property_id: str,
        listing_type: str = "sale",
        is_primary: bool = False,
        commission_rate: Optional[float] = None,
    ) -> AgentListing:
        """Create a new agent listing."""
        from uuid import uuid4

        listing = AgentListing(
            id=str(uuid4()),
            agent_id=agent_id,
            property_id=property_id,
            listing_type=listing_type,
            is_primary=is_primary,
            is_active=True,
            commission_rate=commission_rate,
        )
        self.session.add(listing)
        await self.session.flush()
        return listing

    async def get_by_id(self, listing_id: str) -> Optional[AgentListing]:
        """Get listing by ID."""
        result = await self.session.execute(
            select(AgentListing).where(AgentListing.id == listing_id)
        )
        return result.scalar_one_or_none()

    async def get_by_agent(
        self,
        agent_id: str,
        listing_type: Optional[str] = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentListing]:
        """Get listings for an agent."""
        query = select(AgentListing).where(AgentListing.agent_id == agent_id)
        if active_only:
            query = query.where(
                AgentListing.is_active == True  # noqa: E712
            )
        if listing_type:
            query = query.where(AgentListing.listing_type == listing_type)
        query = query.order_by(AgentListing.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_property(
        self,
        property_id: str,
        active_only: bool = True,
    ) -> list[AgentListing]:
        """Get all agents for a property."""
        query = select(AgentListing).where(AgentListing.property_id == property_id)
        if active_only:
            query = query.where(AgentListing.is_active.is_(True))
        query = query.where(AgentListing.is_primary.is_(True))  # Primary first
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_for_agent(self, agent_id: str, active_only: bool = True) -> int:
        """Count listings for an agent."""
        query = select(func.count(AgentListing.id)).where(AgentListing.agent_id == agent_id)
        if active_only:
            query = query.where(
                AgentListing.is_active == True  # noqa: E712
            )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def set_primary(self, listing: AgentListing) -> None:
        """Set a listing as primary (unsets others for same property)."""
        await self.session.execute(
            update(AgentListing)
            .where(AgentListing.property_id == listing.property_id)
            .where(AgentListing.agent_id == listing.agent_id)
            .values(is_primary=False)
        )
        listing.is_primary = True
        await self.session.flush()

    async def deactivate(self, listing: AgentListing) -> None:
        """Deactivate a listing."""
        listing.is_active = False
        await self.session.flush()

    async def delete(self, listing: AgentListing) -> None:
        """Delete a listing."""
        await self.session.delete(listing)


class AgentInquiryRepository:
    """Repository for agent inquiry operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        agent_id: str,
        name: str,
        email: str,
        inquiry_type: str,
        message: str,
        user_id: Optional[str] = None,
        visitor_id: Optional[str] = None,
        phone: Optional[str] = None,
        property_id: Optional[str] = None,
    ) -> AgentInquiry:
        """Create a new inquiry."""
        from uuid import uuid4

        inquiry = AgentInquiry(
            id=str(uuid4()),
            agent_id=agent_id,
            user_id=user_id,
            visitor_id=visitor_id,
            name=name,
            email=email,
            phone=phone,
            property_id=property_id,
            inquiry_type=inquiry_type,
            message=message,
            status="new",
        )
        self.session.add(inquiry)
        await self.session.flush()
        return inquiry

    async def get_by_id(self, inquiry_id: str) -> Optional[AgentInquiry]:
        """Get inquiry by ID."""
        result = await self.session.execute(
            select(AgentInquiry).where(AgentInquiry.id == inquiry_id)
        )
        return result.scalar_one_or_none()

    async def get_by_agent(
        self,
        agent_id: str,
        status: Optional[str] = None,
        inquiry_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentInquiry]:
        """Get inquiries for an agent."""
        query = select(AgentInquiry).where(AgentInquiry.agent_id == agent_id)
        if status:
            query = query.where(AgentInquiry.status == status)
        if inquiry_type:
            query = query.where(AgentInquiry.inquiry_type == inquiry_type)
        query = query.order_by(AgentInquiry.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_for_agent(
        self,
        agent_id: str,
        status: Optional[str] = None,
    ) -> int:
        """Count inquiries for an agent."""
        query = select(func.count(AgentInquiry.id)).where(AgentInquiry.agent_id == agent_id)
        if status:
            query = query.where(AgentInquiry.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def mark_read(self, inquiry: AgentInquiry) -> None:
        """Mark inquiry as read."""
        inquiry.status = "read"
        inquiry.read_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_responded(self, inquiry: AgentInquiry) -> None:
        """Mark inquiry as responded."""
        inquiry.status = "responded"
        inquiry.responded_at = datetime.now(UTC)
        await self.session.flush()

    async def update_status(self, inquiry: AgentInquiry, status: str) -> None:
        """Update inquiry status."""
        inquiry.status = status
        await self.session.flush()

    async def delete(self, inquiry: AgentInquiry) -> None:
        """Delete an inquiry."""
        await self.session.delete(inquiry)


class ViewingAppointmentRepository:
    """Repository for viewing appointment operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        agent_id: str,
        property_id: str,
        proposed_datetime: datetime,
        client_name: str,
        client_email: str,
        user_id: Optional[str] = None,
        visitor_id: Optional[str] = None,
        client_phone: Optional[str] = None,
        duration_minutes: int = 60,
        notes: Optional[str] = None,
    ) -> ViewingAppointment:
        """Create a new viewing appointment request."""
        from uuid import uuid4

        appointment = ViewingAppointment(
            id=str(uuid4()),
            agent_id=agent_id,
            user_id=user_id,
            visitor_id=visitor_id,
            client_name=client_name,
            client_email=client_email,
            client_phone=client_phone,
            property_id=property_id,
            proposed_datetime=proposed_datetime,
            duration_minutes=duration_minutes,
            notes=notes,
            status="requested",
        )
        self.session.add(appointment)
        await self.session.flush()
        return appointment

    async def get_by_id(self, appointment_id: str) -> Optional[ViewingAppointment]:
        """Get appointment by ID."""
        result = await self.session.execute(
            select(ViewingAppointment).where(ViewingAppointment.id == appointment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_agent(
        self,
        agent_id: str,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ViewingAppointment]:
        """Get appointments for an agent."""
        query = select(ViewingAppointment).where(ViewingAppointment.agent_id == agent_id)
        if status:
            query = query.where(ViewingAppointment.status == status)
        if from_date:
            query = query.where(ViewingAppointment.proposed_datetime >= from_date)
        if to_date:
            query = query.where(ViewingAppointment.proposed_datetime <= to_date)
        query = (
            query.order_by(ViewingAppointment.proposed_datetime.asc()).offset(offset).limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[ViewingAppointment]:
        """Get appointments for a user (client)."""
        query = select(ViewingAppointment).where(ViewingAppointment.user_id == user_id)
        if status:
            query = query.where(ViewingAppointment.status == status)
        query = query.order_by(ViewingAppointment.proposed_datetime.asc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_for_agent(
        self,
        agent_id: str,
        status: Optional[str] = None,
    ) -> int:
        """Count appointments for an agent."""
        query = select(func.count(ViewingAppointment.id)).where(
            ViewingAppointment.agent_id == agent_id
        )
        if status:
            query = query.where(ViewingAppointment.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def confirm(
        self,
        appointment: ViewingAppointment,
        confirmed_datetime: Optional[datetime] = None,
    ) -> None:
        """Confirm an appointment."""
        appointment.status = "confirmed"
        appointment.confirmed_datetime = confirmed_datetime or appointment.proposed_datetime
        await self.session.flush()

    async def cancel(
        self,
        appointment: ViewingAppointment,
        reason: Optional[str] = None,
    ) -> None:
        """Cancel an appointment."""
        appointment.status = "cancelled"
        appointment.cancellation_reason = reason
        await self.session.flush()

    async def complete(self, appointment: ViewingAppointment) -> None:
        """Mark appointment as completed."""
        appointment.status = "completed"
        await self.session.flush()

    async def update(self, appointment: ViewingAppointment, **kwargs) -> ViewingAppointment:
        """Update appointment fields."""
        for key, value in kwargs.items():
            if hasattr(appointment, key):
                setattr(appointment, key, value)
        await self.session.flush()
        return appointment

    async def delete(self, appointment: ViewingAppointment) -> None:
        """Delete an appointment."""
        await self.session.delete(appointment)
