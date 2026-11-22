"""
Service for tracking lead interactions and behaviors.

This service handles:
- Recording visitor interactions
- Managing visitor identity (cookies)
- Linking anonymous visitors to registered users
"""

import logging
import re
import secrets
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.security_utils import sanitize_for_log
from db.models import Lead, LeadInteraction
from db.repositories import LeadInteractionRepository, LeadRepository

logger = logging.getLogger(__name__)

# Cookie configuration
VISITOR_COOKIE_NAME = "visitor_id"
VISITOR_COOKIE_MAX_AGE_DAYS = 365
SESSION_TIMEOUT_MINUTES = 30

# The locale of the page an interaction happened on - "pl", "en", "de" ...
# A locale is optional everywhere: a request that carries none is recorded
# as it is, and one that carries a malformed one loses the locale instead of
# the interaction.
LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,8})?$")


def normalize_locale(locale: Optional[str]) -> Optional[str]:
    """The locale a request claims, in the shape the site uses.

    The locale is never worth rejecting a request for - it is a measurement,
    not a condition - so a value that is not a locale is dropped and the
    interaction is still recorded.
    """
    if not locale:
        return None
    candidate = locale.strip().lower()
    return candidate if LOCALE_PATTERN.match(candidate) else None


class LeadTrackingService:
    """Service for tracking lead interactions."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.lead_repo = LeadRepository(session)
        self.interaction_repo = LeadInteractionRepository(session)

    async def track_interaction(
        self,
        visitor_id: str,
        interaction_type: str,
        property_id: Optional[str] = None,
        search_query: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
        page_url: Optional[str] = None,
        referrer: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        time_spent_seconds: Optional[int] = None,
        user_id: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> LeadInteraction:
        """Record a lead interaction.

        Args:
            visitor_id: Unique visitor identifier from cookie
            interaction_type: Type of interaction (search, view, favorite, etc.)
            property_id: Property ID if interaction involves a property
            search_query: Search query if interaction is a search
            metadata: Additional context as JSON
            session_id: Browser session ID
            page_url: URL where interaction occurred
            referrer: Referrer URL
            user_agent: Browser user agent
            ip_address: Client IP address
            time_spent_seconds: Time spent on page
            user_id: Linked user ID if registered
            locale: The locale of the page the interaction happened on

        Returns:
            The created LeadInteraction record
        """
        # Get or create lead
        lead = await self.lead_repo.get_or_create_by_visitor_id(visitor_id)

        # Link to user if provided and not already linked
        if user_id and not lead.user_id:
            await self.lead_repo.link_to_user(lead, user_id)

        # The locale travels with the interaction, in the metadata the
        # aggregation already reads. A request without one keeps the
        # metadata it brought.
        stored_metadata = dict(metadata or {})
        normalized_locale = normalize_locale(locale)
        if normalized_locale:
            stored_metadata["locale"] = normalized_locale

        # Record the interaction
        interaction = await self.interaction_repo.create(
            lead_id=lead.id,
            interaction_type=interaction_type,
            property_id=property_id,
            search_query=search_query,
            metadata=stored_metadata,
            session_id=session_id,
            page_url=page_url,
            referrer=referrer,
            user_agent=user_agent,
            ip_address=ip_address,
            time_spent_seconds=time_spent_seconds,
        )

        # Update lead's last activity timestamp
        await self.lead_repo.update_last_activity(lead)

        query_preview = search_query[:50] if search_query else None
        logger.debug(
            "Tracked interaction: lead=%s, type=%s, property=%s, query=%s",
            sanitize_for_log(lead.id),
            sanitize_for_log(interaction_type),
            sanitize_for_log(property_id),
            sanitize_for_log(query_preview),
        )

        return interaction

    async def get_or_create_visitor(
        self,
        visitor_id: Optional[str] = None,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        source: Optional[str] = None,
        consent_given: bool = False,
    ) -> tuple[Lead, bool]:
        """Get existing lead or create new one.

        Args:
            visitor_id: Existing visitor ID (from cookie)
            user_id: User ID if registered
            email: Email address if provided
            source: Traffic source
            consent_given: GDPR consent status

        Returns:
            Tuple of (Lead, is_new_lead)
        """
        # Try to find existing lead
        lead = None
        if visitor_id:
            lead = await self.lead_repo.get_by_visitor_id(visitor_id)
        if not lead and user_id:
            lead = await self.lead_repo.get_by_user_id(user_id)
        if not lead and email:
            lead = await self.lead_repo.get_by_email(email)

        if lead:
            # Update existing lead if new info provided
            await self._apply_new_information(lead, user_id, email, consent_given)
            return lead, False

        # Create new lead
        if not visitor_id:
            visitor_id = self.generate_visitor_id()

        try:
            lead = await self.lead_repo.create(
                visitor_id=visitor_id,
                user_id=user_id,
                email=email,
                source=source,
                consent_given=consent_given,
            )
        except IntegrityError:
            # Another request created the row between the read and the write:
            # the tracking call and the waitlist capture race for one visitor.
            # The row it wrote is the real one - this request's address is
            # applied to it, and the capture is announced when that address
            # was not on the row before (nobody has told the operator yet).
            await self.session.rollback()
            lead = await self.lead_repo.get_by_visitor_id(visitor_id)
            if lead is None:
                raise
            had_email = bool(lead.email)
            await self._apply_new_information(lead, user_id, email, consent_given)
            return lead, bool(email) and not had_email

        logger.info(
            "Created new lead: visitor_id=%s, source=%s",
            sanitize_for_log(visitor_id),
            sanitize_for_log(source),
        )
        return lead, True

    async def _apply_new_information(
        self,
        lead: Lead,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        consent_given: bool = False,
    ) -> Lead:
        """Apply what a later request brought to a lead that already exists."""
        if user_id and not lead.user_id:
            await self.lead_repo.link_to_user(lead, user_id)
        if email and not lead.email:
            lead.email = email
            await self.session.flush()
        if consent_given and not lead.consent_given:
            await self.lead_repo.set_consent(lead, consent_given)
        return lead

    async def link_visitor_to_user(
        self,
        visitor_id: str,
        user_id: str,
        email: Optional[str] = None,
    ) -> Optional[Lead]:
        """Link an anonymous visitor to a registered user.

        This is called when a visitor registers or logs in.

        Args:
            visitor_id: The visitor's cookie ID
            user_id: The registered user's ID
            email: The user's email

        Returns:
            The updated Lead, or None if not found
        """
        lead = await self.lead_repo.get_by_visitor_id(visitor_id)
        if not lead:
            # Create new lead for this user
            lead = await self.lead_repo.create(
                visitor_id=visitor_id,
                user_id=user_id,
                email=email,
            )
            logger.info("Created lead for new user: user_id=%s", sanitize_for_log(user_id))
        else:
            # Link existing lead to user
            await self.lead_repo.link_to_user(lead, user_id)
            if email:
                lead.email = email
                await self.session.flush()
            log_msg = f"Linked visitor to user: visitor_id={visitor_id}"
            logger.info("%s, user_id=%s", sanitize_for_log(log_msg), sanitize_for_log(user_id))

        return lead

    async def update_lead_profile(
        self,
        visitor_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        preferred_locations: Optional[list[str]] = None,
        consent_given: Optional[bool] = None,
    ) -> Optional[Lead]:
        """Update lead profile information.

        Args:
            visitor_id: Visitor ID to update
            name: Lead name
            email: Lead email
            phone: Lead phone
            budget_min: Minimum budget
            budget_max: Maximum budget
            preferred_locations: List of preferred locations
            consent_given: GDPR consent status

        Returns:
            Updated Lead, or None if not found
        """
        lead = await self.lead_repo.get_by_visitor_id(visitor_id)
        if not lead:
            return None

        update_data: dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name
        if email is not None:
            update_data["email"] = email.lower().strip()
        if phone is not None:
            update_data["phone"] = phone
        if budget_min is not None:
            update_data["budget_min"] = budget_min
        if budget_max is not None:
            update_data["budget_max"] = budget_max
        if preferred_locations is not None:
            update_data["preferred_locations"] = preferred_locations

        if update_data:
            await self.lead_repo.update(lead, **update_data)

        if consent_given is not None:
            await self.lead_repo.set_consent(lead, consent_given)

        return lead

    async def update_lead_status(
        self,
        lead_id: str,
        status: str,
        notes: Optional[str] = None,
    ) -> Optional[Lead]:
        """Update lead status.

        Args:
            lead_id: Lead ID
            status: New status (new, contacted, qualified, converted, lost)
            notes: Optional notes about status change

        Returns:
            Updated Lead, or None if not found
        """
        lead = await self.lead_repo.get_by_id(lead_id)
        if not lead:
            return None

        await self.lead_repo.update(lead, status=status)

        # If notes provided, create a note interaction
        if notes:
            await self.interaction_repo.create(
                lead_id=lead.id,
                interaction_type="status_change",
                metadata={
                    "old_status": lead.status,
                    "new_status": status,
                    "notes": notes,
                },
            )

        logger.info(
            "Updated lead %s status to %s", sanitize_for_log(lead_id), sanitize_for_log(status)
        )
        return lead

    async def get_lead_by_visitor(self, visitor_id: str) -> Optional[Lead]:
        """Get lead by visitor ID.

        Args:
            visitor_id: Visitor cookie ID

        Returns:
            Lead if found, None otherwise
        """
        return await self.lead_repo.get_by_visitor_id(visitor_id)

    async def get_lead_interactions(
        self,
        visitor_id: str,
        limit: int = 50,
        interaction_type: Optional[str] = None,
    ) -> list[LeadInteraction]:
        """Get interactions for a visitor.

        Args:
            visitor_id: Visitor cookie ID
            limit: Maximum interactions to return
            interaction_type: Filter by interaction type

        Returns:
            List of LeadInteraction records
        """
        lead = await self.lead_repo.get_by_visitor_id(visitor_id)
        if not lead:
            return []

        return await self.interaction_repo.get_by_lead(
            lead.id,
            limit=limit,
            interaction_type=interaction_type,
        )

    async def delete_lead_data(self, visitor_id: str) -> bool:
        """Delete all data for a lead (GDPR right to be forgotten).

        Args:
            visitor_id: Visitor cookie ID

        Returns:
            True if lead was deleted, False if not found
        """
        lead = await self.lead_repo.get_by_visitor_id(visitor_id)
        if not lead:
            return False

        # Cascade delete will remove all interactions, scores, assignments
        await self.lead_repo.delete(lead)

        logger.info(
            "Deleted lead and all associated data: visitor_id=%s", sanitize_for_log(visitor_id)
        )
        return True

    async def get_recent_activity(
        self,
        visitor_id: str,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get recent activity summary for a visitor.

        Args:
            visitor_id: Visitor cookie ID
            days: Number of days to look back

        Returns:
            Dict with recent activity summary
        """
        lead = await self.lead_repo.get_by_visitor_id(visitor_id)
        if not lead:
            return {"found": False}

        stats = await self.interaction_repo.get_interaction_stats(lead.id)
        recent_searches = await self.interaction_repo.get_recent_searches(lead.id, limit=5)
        recent_props = await self.interaction_repo.get_recent_properties(lead.id, limit=5)

        return {
            "found": True,
            "lead_id": lead.id,
            "current_score": lead.current_score,
            "status": lead.status,
            "stats": stats,
            "recent_searches": recent_searches,
            "recent_properties_viewed": recent_props,
        }

    @staticmethod
    def generate_visitor_id() -> str:
        """Generate a new unique visitor ID.

        Returns:
            URL-safe visitor ID string
        """
        return secrets.token_urlsafe(16)


async def track_search(
    service: LeadTrackingService,
    visitor_id: str,
    query: str,
    filters: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
    page_url: Optional[str] = None,
) -> LeadInteraction:
    """Convenience function to track a search interaction."""
    return await service.track_interaction(
        visitor_id=visitor_id,
        interaction_type="search",
        search_query=query,
        metadata={"filters": filters or {}},
        session_id=session_id,
        page_url=page_url,
    )


async def track_property_view(
    service: LeadTrackingService,
    visitor_id: str,
    property_id: str,
    session_id: Optional[str] = None,
    page_url: Optional[str] = None,
    time_spent_seconds: Optional[int] = None,
) -> LeadInteraction:
    """Convenience function to track a property view."""
    return await service.track_interaction(
        visitor_id=visitor_id,
        interaction_type="view",
        property_id=property_id,
        session_id=session_id,
        page_url=page_url,
        time_spent_seconds=time_spent_seconds,
    )


async def track_favorite(
    service: LeadTrackingService,
    visitor_id: str,
    property_id: str,
    action: str = "add",  # "add" or "remove"
    session_id: Optional[str] = None,
) -> LeadInteraction:
    """Convenience function to track a favorite action."""
    return await service.track_interaction(
        visitor_id=visitor_id,
        interaction_type="favorite" if action == "add" else "unfavorite",
        property_id=property_id,
        metadata={"action": action},
        session_id=session_id,
    )


async def track_inquiry(
    service: LeadTrackingService,
    visitor_id: str,
    property_id: str,
    message: Optional[str] = None,
    contact_info: Optional[dict[str, str]] = None,
    session_id: Optional[str] = None,
) -> LeadInteraction:
    """Convenience function to track an inquiry submission."""
    return await service.track_interaction(
        visitor_id=visitor_id,
        interaction_type="inquiry",
        property_id=property_id,
        metadata={
            "has_message": bool(message),
            "contact_info_provided": bool(contact_info),
        },
        session_id=session_id,
    )


async def track_contact_request(
    service: LeadTrackingService,
    visitor_id: str,
    contact_type: str,  # "email", "phone", "callback"
    property_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> LeadInteraction:
    """Convenience function to track a contact request."""
    return await service.track_interaction(
        visitor_id=visitor_id,
        interaction_type="contact",
        property_id=property_id,
        metadata={"contact_type": contact_type},
        session_id=session_id,
    )
