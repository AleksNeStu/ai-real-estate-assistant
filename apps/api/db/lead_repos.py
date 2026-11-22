"""
Lead management repository classes.

Provides repositories for Lead, LeadInteraction, LeadScore,
and AgentAssignment models.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AgentAssignment,
    Lead,
    LeadInteraction,
    LeadScore,
)


class LeadRepository:
    """Repository for Lead model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        visitor_id: str,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        name: Optional[str] = None,
        source: Optional[str] = None,
        consent_given: bool = False,
    ) -> Lead:
        """Create a new lead."""
        from uuid import uuid4

        lead = Lead(
            id=str(uuid4()),
            visitor_id=visitor_id,
            user_id=user_id,
            email=email.lower().strip() if email else None,
            phone=phone,
            name=name,
            source=source,
            consent_given=consent_given,
            consent_at=datetime.now(UTC) if consent_given else None,
            first_seen_at=datetime.now(UTC),
            last_activity_at=datetime.now(UTC),
        )
        self.session.add(lead)
        await self.session.flush()
        return lead

    async def get_by_id(self, lead_id: str) -> Optional[Lead]:
        """Get lead by ID."""
        result = await self.session.execute(select(Lead).where(Lead.id == lead_id))
        return result.scalar_one_or_none()

    async def get_by_visitor_id(self, visitor_id: str) -> Optional[Lead]:
        """Get lead by visitor ID (cookie UUID)."""
        result = await self.session.execute(select(Lead).where(Lead.visitor_id == visitor_id))
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: str) -> Optional[Lead]:
        """Get lead by linked user ID."""
        result = await self.session.execute(select(Lead).where(Lead.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Lead]:
        """Get lead by email address."""
        result = await self.session.execute(select(Lead).where(Lead.email == email.lower().strip()))
        return result.scalar_one_or_none()

    async def update(self, lead: Lead, **kwargs) -> Lead:
        """Update lead fields."""
        for key, value in kwargs.items():
            if hasattr(lead, key):
                setattr(lead, key, value)
        await self.session.flush()
        return lead

    async def update_last_activity(self, lead: Lead) -> None:
        """Update lead's last activity timestamp."""
        lead.last_activity_at = datetime.now(UTC)
        await self.session.flush()

    async def update_score(self, lead: Lead, score: int) -> None:
        """Update lead's current score (denormalized)."""
        lead.current_score = score
        await self.session.flush()

    async def link_to_user(self, lead: Lead, user_id: str) -> Lead:
        """Link an anonymous lead to a registered user."""
        lead.user_id = user_id
        await self.session.flush()
        return lead

    async def set_consent(self, lead: Lead, consent_given: bool = True) -> Lead:
        """Set GDPR consent for lead."""
        lead.consent_given = consent_given
        lead.consent_at = datetime.now(UTC) if consent_given else None
        await self.session.flush()
        return lead

    async def get_list(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        score_min: Optional[int] = None,
        score_max: Optional[int] = None,
        has_email: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "score",
        sort_order: str = "desc",
    ) -> list[Lead]:
        """Get filtered list of leads."""
        query = select(Lead)

        # Filter by assigned agent
        if agent_id:
            query = query.join(AgentAssignment).where(
                AgentAssignment.agent_id == agent_id,
                AgentAssignment.is_active == True,  # noqa: E712
            )

        # Apply filters
        if status:
            query = query.where(Lead.status == status)
        if score_min is not None:
            query = query.where(Lead.current_score >= score_min)
        if score_max is not None:
            query = query.where(Lead.current_score <= score_max)
        if has_email is True:
            query = query.where(Lead.email.isnot(None))
        elif has_email is False:
            query = query.where(Lead.email.is_(None))

        # Apply sorting
        sort_column = {
            "score": Lead.current_score,
            "last_activity": Lead.last_activity_at,
            "created_at": Lead.created_at,
            "name": Lead.name,
        }.get(sort_by, Lead.current_score)

        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        score_min: Optional[int] = None,
        score_max: Optional[int] = None,
        has_email: Optional[bool] = None,
    ) -> int:
        """Count leads matching filters."""
        query = select(func.count(Lead.id))

        if agent_id:
            query = query.join(AgentAssignment).where(
                AgentAssignment.agent_id == agent_id,
                AgentAssignment.is_active == True,  # noqa: E712
            )

        if status:
            query = query.where(Lead.status == status)
        if score_min is not None:
            query = query.where(Lead.current_score >= score_min)
        if score_max is not None:
            query = query.where(Lead.current_score <= score_max)
        if has_email is True:
            query = query.where(Lead.email.isnot(None))
        elif has_email is False:
            query = query.where(Lead.email.is_(None))

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_high_scoring(
        self,
        threshold: int = 70,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Lead]:
        """Get leads with score above threshold (for notifications)."""
        query = select(Lead).where(Lead.current_score >= threshold)

        if since:
            query = query.where(Lead.updated_at >= since)

        query = query.order_by(Lead.current_score.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_or_create_by_visitor_id(self, visitor_id: str) -> Lead:
        """Get existing lead or create new one by visitor ID.

        The read below and the write that follows it are two statements, and
        two requests for one visitor can arrive at the same time: the landing
        page tracks an interaction and the waitlist form captures the same
        visitor. Both read "no row yet", both write, and the loser of that
        race dies on the UNIQUE constraint - a 500 for a visitor who did
        nothing wrong. On that collision the row the other request wrote is
        read back and returned, so both requests end with the same lead.
        """
        lead = await self.get_by_visitor_id(visitor_id)
        if lead:
            return lead
        try:
            return await self.create(visitor_id=visitor_id)
        except IntegrityError:
            await self.session.rollback()
            lead = await self.get_by_visitor_id(visitor_id)
            if lead is None:
                raise
            return lead

    async def delete(self, lead: Lead) -> None:
        """Delete a lead (GDPR right to be forgotten)."""
        await self.session.delete(lead)


class LeadInteractionRepository:
    """Repository for LeadInteraction model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        lead_id: str,
        interaction_type: str,
        property_id: Optional[str] = None,
        search_query: Optional[str] = None,
        metadata: Optional[dict] = None,
        session_id: Optional[str] = None,
        page_url: Optional[str] = None,
        referrer: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        time_spent_seconds: Optional[int] = None,
    ) -> LeadInteraction:
        """Record a lead interaction."""
        from uuid import uuid4

        interaction = LeadInteraction(
            id=str(uuid4()),
            lead_id=lead_id,
            interaction_type=interaction_type,
            property_id=property_id,
            search_query=search_query,
            interaction_metadata=metadata or {},
            session_id=session_id,
            page_url=page_url,
            referrer=referrer,
            user_agent=user_agent,
            ip_address=ip_address,
            time_spent_seconds=time_spent_seconds,
        )
        self.session.add(interaction)
        await self.session.flush()
        return interaction

    async def get_by_lead(
        self,
        lead_id: str,
        limit: int = 100,
        offset: int = 0,
        interaction_type: Optional[str] = None,
    ) -> list[LeadInteraction]:
        """Get interactions for a lead."""
        query = select(LeadInteraction).where(LeadInteraction.lead_id == lead_id)

        if interaction_type:
            query = query.where(LeadInteraction.interaction_type == interaction_type)

        query = query.order_by(LeadInteraction.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_lead(
        self,
        lead_id: str,
        interaction_type: Optional[str] = None,
    ) -> int:
        """Count interactions for a lead."""
        query = select(func.count(LeadInteraction.id)).where(LeadInteraction.lead_id == lead_id)

        if interaction_type:
            query = query.where(LeadInteraction.interaction_type == interaction_type)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_interaction_stats(self, lead_id: str) -> dict[str, Any]:
        """Get aggregated interaction statistics for a lead."""
        # Count by type
        type_counts_result = await self.session.execute(
            select(
                LeadInteraction.interaction_type,
                func.count(LeadInteraction.id).label("count"),
            )
            .where(LeadInteraction.lead_id == lead_id)
            .group_by(LeadInteraction.interaction_type)
        )
        type_counts = {row.interaction_type: row.count for row in type_counts_result}

        # Total time spent
        time_result = await self.session.execute(
            select(func.sum(LeadInteraction.time_spent_seconds)).where(
                LeadInteraction.lead_id == lead_id,
                LeadInteraction.time_spent_seconds.isnot(None),
            )
        )
        total_time = time_result.scalar() or 0

        # Unique properties viewed
        props_result = await self.session.execute(
            select(func.count(func.distinct(LeadInteraction.property_id))).where(
                LeadInteraction.lead_id == lead_id,
                LeadInteraction.property_id.isnot(None),
            )
        )
        unique_properties = props_result.scalar() or 0

        # Unique searches
        searches_result = await self.session.execute(
            select(func.count(func.distinct(LeadInteraction.search_query))).where(
                LeadInteraction.lead_id == lead_id,
                LeadInteraction.search_query.isnot(None),
            )
        )
        unique_searches = searches_result.scalar() or 0

        # First and last activity
        first_result = await self.session.execute(
            select(func.min(LeadInteraction.created_at)).where(LeadInteraction.lead_id == lead_id)
        )
        first_activity = first_result.scalar()

        last_result = await self.session.execute(
            select(func.max(LeadInteraction.created_at)).where(LeadInteraction.lead_id == lead_id)
        )
        last_activity = last_result.scalar()

        return {
            "type_counts": type_counts,
            "total_time_spent_seconds": total_time,
            "unique_properties_viewed": unique_properties,
            "unique_searches": unique_searches,
            "first_activity_at": first_activity,
            "last_activity_at": last_activity,
            "total_interactions": sum(type_counts.values()),
        }

    async def get_recent_searches(self, lead_id: str, limit: int = 10) -> list[str]:
        """Get recent search queries for a lead."""
        result = await self.session.execute(
            select(LeadInteraction.search_query)
            .where(
                LeadInteraction.lead_id == lead_id,
                LeadInteraction.interaction_type == "search",
                LeadInteraction.search_query.isnot(None),
            )
            .order_by(LeadInteraction.created_at.desc())
            .limit(limit)
        )
        return [row.search_query for row in result if row.search_query]

    async def get_recent_properties(self, lead_id: str, limit: int = 10) -> list[str]:
        """Get recently viewed property IDs for a lead."""
        result = await self.session.execute(
            select(LeadInteraction.property_id)
            .where(
                LeadInteraction.lead_id == lead_id,
                LeadInteraction.interaction_type == "view",
                LeadInteraction.property_id.isnot(None),
            )
            .order_by(LeadInteraction.created_at.desc())
            .limit(limit)
        )
        return [row.property_id for row in result if row.property_id]

    async def cleanup_old_interactions(self, days_to_keep: int = 365) -> int:
        """Remove interactions older than specified days."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)
        result = await self.session.execute(
            select(LeadInteraction).where(LeadInteraction.created_at < cutoff_date)
        )
        old_interactions = result.scalars().all()

        count = 0
        for interaction in old_interactions:
            await self.session.delete(interaction)
            count += 1

        return count


class LeadScoreRepository:
    """Repository for LeadScore model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        lead_id: str,
        total_score: int,
        search_activity_score: int,
        engagement_score: int,
        intent_score: int,
        score_factors: dict,
        recommendations: Optional[list[str]] = None,
        model_version: str = "1.0.0",
    ) -> LeadScore:
        """Create a new lead score record."""
        from uuid import uuid4

        score = LeadScore(
            id=str(uuid4()),
            lead_id=lead_id,
            total_score=total_score,
            search_activity_score=search_activity_score,
            engagement_score=engagement_score,
            intent_score=intent_score,
            score_factors=score_factors,
            recommendations=recommendations,
            model_version=model_version,
        )
        self.session.add(score)
        await self.session.flush()
        return score

    async def get_latest_for_lead(self, lead_id: str) -> Optional[LeadScore]:
        """Get the most recent score for a lead."""
        result = await self.session.execute(
            select(LeadScore)
            .where(LeadScore.lead_id == lead_id)
            .order_by(LeadScore.calculated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_history_for_lead(
        self,
        lead_id: str,
        limit: int = 30,
    ) -> list[LeadScore]:
        """Get score history for a lead."""
        result = await self.session.execute(
            select(LeadScore)
            .where(LeadScore.lead_id == lead_id)
            .order_by(LeadScore.calculated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_leads_needing_recalc(
        self,
        max_age_hours: int = 24,
        limit: int = 100,
    ) -> list[str]:
        """Get lead IDs whose scores need recalculation."""
        cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)

        # Find leads where latest score is older than cutoff or no score
        result = await self.session.execute(
            select(Lead.id)
            .outerjoin(LeadScore, Lead.id == LeadScore.lead_id)
            .where((LeadScore.calculated_at.is_(None)) | (LeadScore.calculated_at < cutoff))
            .distinct()
            .limit(limit)
        )
        return [row.id for row in result]

    async def count_scores_today(self) -> int:
        """Count scores calculated today."""
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(func.count(LeadScore.id)).where(LeadScore.calculated_at >= today_start)
        )
        return result.scalar() or 0


class AgentAssignmentRepository:
    """Repository for AgentAssignment model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        lead_id: str,
        agent_id: str,
        assigned_by: Optional[str] = None,
        notes: Optional[str] = None,
        is_primary: bool = False,
    ) -> AgentAssignment:
        """Create a new agent assignment."""
        from uuid import uuid4

        assignment = AgentAssignment(
            id=str(uuid4()),
            lead_id=lead_id,
            agent_id=agent_id,
            assigned_by=assigned_by,
            notes=notes,
            is_primary=is_primary,
        )
        self.session.add(assignment)
        await self.session.flush()
        return assignment

    async def get_by_id(self, assignment_id: str) -> Optional[AgentAssignment]:
        """Get assignment by ID."""
        result = await self.session.execute(
            select(AgentAssignment).where(AgentAssignment.id == assignment_id)
        )
        return result.scalar_one_or_none()

    async def get_active_for_lead(self, lead_id: str) -> list[AgentAssignment]:
        """Get all active assignments for a lead."""
        result = await self.session.execute(
            select(AgentAssignment)
            .where(
                AgentAssignment.lead_id == lead_id,
                AgentAssignment.is_active == True,  # noqa: E712
            )
            .order_by(
                AgentAssignment.is_primary.desc(),
                AgentAssignment.assigned_at.desc(),
            )
        )
        return list(result.scalars().all())

    async def get_primary_for_lead(self, lead_id: str) -> Optional[AgentAssignment]:
        """Get primary agent assignment for a lead."""
        result = await self.session.execute(
            select(AgentAssignment).where(
                AgentAssignment.lead_id == lead_id,
                AgentAssignment.is_primary == True,  # noqa: E712
                AgentAssignment.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_leads_for_agent(
        self,
        agent_id: str,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentAssignment]:
        """Get all assignments for an agent."""
        query = select(AgentAssignment).where(AgentAssignment.agent_id == agent_id)

        if active_only:
            query = query.where(
                AgentAssignment.is_active == True  # noqa: E712
            )

        query = query.order_by(AgentAssignment.assigned_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def set_primary(self, assignment_id: str) -> None:
        """Set an assignment as primary (unsets other primaries for the lead)."""
        assignment = await self.get_by_id(assignment_id)
        if assignment:
            # Unset other primaries for this lead
            await self.session.execute(
                update(AgentAssignment)
                .where(
                    AgentAssignment.lead_id == assignment.lead_id,
                    AgentAssignment.id != assignment_id,
                )
                .values(is_primary=False)
            )
            # Set this one as primary
            assignment.is_primary = True
            await self.session.flush()

    async def unassign(self, assignment_id: str, unassigned_by: Optional[str] = None) -> None:
        """Deactivate an assignment."""
        await self.session.execute(
            update(AgentAssignment)
            .where(AgentAssignment.id == assignment_id)
            .values(
                is_active=False,
                unassigned_at=datetime.now(UTC),
                unassigned_by=unassigned_by,
            )
        )

    async def assign_lead_to_agent(
        self,
        lead_id: str,
        agent_id: str,
        assigned_by: Optional[str] = None,
        notes: Optional[str] = None,
        is_primary: bool = True,
    ) -> AgentAssignment:
        """Assign a lead to an agent, handling primary status."""
        # Check if already assigned
        existing = await self.get_primary_for_lead(lead_id)
        if existing and existing.agent_id == agent_id:
            return existing

        # If setting as primary, unset existing primary
        if is_primary:
            await self.session.execute(
                update(AgentAssignment)
                .where(
                    AgentAssignment.lead_id == lead_id,
                    AgentAssignment.is_primary == True,  # noqa: E712
                )
                .values(is_primary=False)
            )

        return await self.create(
            lead_id=lead_id,
            agent_id=agent_id,
            assigned_by=assigned_by,
            notes=notes,
            is_primary=is_primary,
        )

    async def count_for_agent(self, agent_id: str, active_only: bool = True) -> int:
        """Count assignments for an agent."""
        query = select(func.count(AgentAssignment.id)).where(AgentAssignment.agent_id == agent_id)

        if active_only:
            query = query.where(
                AgentAssignment.is_active == True  # noqa: E712
            )

        result = await self.session.execute(query)
        return result.scalar() or 0
