"""
Service for calculating agent performance metrics.

This service provides:
- Individual agent metrics (leads, deals, conversion rates)
- Team comparison metrics
- Performance trends over time
- Strength analysis
- Coaching recommendations
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Optional, cast

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AgentAssignment,
    AgentGoal,
    Commission,
    Deal,
    Lead,
    User,
)
from db.repositories import AgentAssignmentRepository, LeadRepository

logger = logging.getLogger(__name__)


@dataclass
class AgentMetrics:
    """Comprehensive agent performance metrics."""

    # Lead metrics
    total_leads: int = 0
    active_leads: int = 0
    new_leads_week: int = 0
    high_value_leads: int = 0  # Score >= 70

    # Deal metrics
    total_deals: int = 0
    active_deals: int = 0
    closed_deals: int = 0
    fell_through_deals: int = 0

    # Conversion metrics
    lead_to_qualified_rate: float = 0.0  # percentage 0-100
    qualified_to_deal_rate: float = 0.0
    overall_conversion_rate: float = 0.0

    # Time metrics
    avg_time_to_first_contact_hours: Optional[float] = None
    avg_time_to_qualify_days: Optional[float] = None
    avg_time_to_close_days: Optional[float] = None

    # Financial metrics
    total_deal_value: float = 0.0
    avg_deal_value: float = 0.0
    total_commission: float = 0.0
    pending_commission: float = 0.0

    # Strengths analysis
    top_property_types: list[dict[str, Any]] = field(default_factory=list)
    top_locations: list[dict[str, Any]] = field(default_factory=list)
    avg_lead_score: float = 0.0

    # Period comparison
    deals_change_percent: Optional[float] = None
    revenue_change_percent: Optional[float] = None


@dataclass
class TeamComparison:
    """Agent comparison to team averages."""

    agent_id: str
    agent_name: str

    # Rank in team
    rank_by_deals: int = 0
    rank_by_revenue: int = 0
    rank_by_conversion: int = 0
    total_agents: int = 0

    # Comparison to average
    deals_vs_avg_percent: float = 0.0
    revenue_vs_avg_percent: float = 0.0
    conversion_vs_avg_percent: float = 0.0
    time_to_close_vs_avg_percent: float = 0.0

    # Team averages
    team_avg_deals: float = 0.0
    team_avg_revenue: float = 0.0
    team_avg_conversion: float = 0.0
    team_avg_time_to_close_days: float = 0.0


@dataclass
class PerformanceTrend:
    """Performance data point for a time period."""

    period: str
    period_start: datetime
    period_end: datetime
    leads: int = 0
    deals_closed: int = 0
    revenue: float = 0.0
    conversion_rate: float = 0.0
    avg_deal_value: float = 0.0


@dataclass
class CoachingInsight:
    """AI-generated coaching insight for agents."""

    category: str  # strength, improvement, opportunity
    title: str
    description: str
    actionable_recommendation: str
    priority: int  # 1-5, 1 being highest


class AgentPerformanceService:
    """Service for agent performance analytics."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.lead_repo = LeadRepository(session)
        self.assignment_repo = AgentAssignmentRepository(session)

    async def get_agent_metrics(
        self,
        agent_id: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> AgentMetrics:
        """Calculate comprehensive metrics for an agent.

        Args:
            agent_id: The agent's user ID
            period_start: Start of the analysis period (default: 30 days ago)
            period_end: End of the analysis period (default: now)

        Returns:
            AgentMetrics with all calculated values
        """
        if period_end is None:
            period_end = datetime.now(UTC)
        if period_start is None:
            period_start = period_end - timedelta(days=30)

        metrics = AgentMetrics()

        # Get lead metrics
        await self._calculate_lead_metrics(metrics, agent_id, period_start, period_end)

        # Get deal metrics
        await self._calculate_deal_metrics(metrics, agent_id, period_start, period_end)

        # Get conversion metrics
        await self._calculate_conversion_metrics(metrics, agent_id, period_start, period_end)

        # Get time metrics
        await self._calculate_time_metrics(metrics, agent_id, period_start, period_end)

        # Get financial metrics
        await self._calculate_financial_metrics(metrics, agent_id, period_start, period_end)

        # Get strengths analysis
        await self._calculate_strengths(metrics, agent_id, period_start, period_end)

        # Get period comparison
        await self._calculate_period_comparison(metrics, agent_id, period_start, period_end)

        return metrics

    async def _calculate_lead_metrics(
        self,
        metrics: AgentMetrics,
        agent_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """Calculate lead-related metrics."""
        # Total leads assigned (active assignments)
        total_leads_query = select(func.count(AgentAssignment.id)).where(
            and_(
                AgentAssignment.agent_id == agent_id,
                AgentAssignment.is_active.is_(True),
            )
        )
        result = await self.session.execute(total_leads_query)
        metrics.total_leads = result.scalar() or 0

        # Active leads (leads with recent activity)
        week_ago = period_end - timedelta(days=7)
        active_leads_query = (
            select(func.count(func.distinct(AgentAssignment.lead_id)))
            .select_from(AgentAssignment)
            .join(Lead, AgentAssignment.lead_id == Lead.id)
            .where(
                and_(
                    AgentAssignment.agent_id == agent_id,
                    AgentAssignment.is_active.is_(True),
                    Lead.last_activity_at >= week_ago,
                )
            )
        )
        result = await self.session.execute(active_leads_query)
        metrics.active_leads = result.scalar() or 0

        # New leads this week
        new_leads_query = select(func.count(AgentAssignment.id)).where(
            and_(
                AgentAssignment.agent_id == agent_id,
                AgentAssignment.assigned_at >= week_ago,
            )
        )
        result = await self.session.execute(new_leads_query)
        metrics.new_leads_week = result.scalar() or 0

        # High value leads (score >= 70)
        high_value_query = (
            select(func.count(func.distinct(AgentAssignment.lead_id)))
            .select_from(AgentAssignment)
            .join(Lead, AgentAssignment.lead_id == Lead.id)
            .where(
                and_(
                    AgentAssignment.agent_id == agent_id,
                    AgentAssignment.is_active.is_(True),
                    Lead.current_score >= 70,
                )
            )
        )
        result = await self.session.execute(high_value_query)
        metrics.high_value_leads = result.scalar() or 0

        # Average lead score
        avg_score_query = (
            select(func.avg(Lead.current_score))
            .select_from(AgentAssignment)
            .join(Lead, AgentAssignment.lead_id == Lead.id)
            .where(
                and_(
                    AgentAssignment.agent_id == agent_id,
                    AgentAssignment.is_active.is_(True),
                )
            )
        )
        result = await self.session.execute(avg_score_query)
        metrics.avg_lead_score = float(result.scalar() or 0)

    async def _calculate_deal_metrics(
        self,
        metrics: AgentMetrics,
        agent_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """Calculate deal-related metrics."""
        # Total deals in period
        total_query = select(func.count(Deal.id)).where(
            and_(
                Deal.agent_id == agent_id,
                Deal.offer_submitted_at >= period_start,
                Deal.offer_submitted_at <= period_end,
            )
        )
        result = await self.session.execute(total_query)
        metrics.total_deals = result.scalar() or 0

        # Active deals (not closed or fell through)
        active_query = select(func.count(Deal.id)).where(
            and_(
                Deal.agent_id == agent_id,
                Deal.status.in_(["offer_submitted", "offer_accepted", "contract_signed"]),
            )
        )
        result = await self.session.execute(active_query)
        metrics.active_deals = result.scalar() or 0

        # Closed deals
        closed_query = select(func.count(Deal.id)).where(
            and_(
                Deal.agent_id == agent_id,
                Deal.status == "closed",
                Deal.closed_at >= period_start,
                Deal.closed_at <= period_end,
            )
        )
        result = await self.session.execute(closed_query)
        metrics.closed_deals = result.scalar() or 0

        # Fell through deals
        fell_through_query = select(func.count(Deal.id)).where(
            and_(
                Deal.agent_id == agent_id,
                Deal.status == "fell_through",
                Deal.offer_submitted_at >= period_start,
                Deal.offer_submitted_at <= period_end,
            )
        )
        result = await self.session.execute(fell_through_query)
        metrics.fell_through_deals = result.scalar() or 0

    async def _calculate_conversion_metrics(
        self,
        metrics: AgentMetrics,
        agent_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """Calculate conversion rate metrics."""
        # Lead to qualified rate
        qualified_query = (
            select(func.count(func.distinct(AgentAssignment.lead_id)))
            .select_from(AgentAssignment)
            .join(Lead, AgentAssignment.lead_id == Lead.id)
            .where(
                and_(
                    AgentAssignment.agent_id == agent_id,
                    AgentAssignment.assigned_at >= period_start,
                    AgentAssignment.assigned_at <= period_end,
                    Lead.status.in_(["qualified", "converted"]),
                )
            )
        )
        result = await self.session.execute(qualified_query)
        qualified_count = result.scalar() or 0

        if metrics.total_leads > 0:
            metrics.lead_to_qualified_rate = round((qualified_count / metrics.total_leads) * 100, 1)

        # Qualified to deal rate
        if qualified_count > 0 and metrics.closed_deals > 0:
            metrics.qualified_to_deal_rate = round(
                (metrics.closed_deals / qualified_count) * 100, 1
            )

        # Overall conversion rate
        total_assigned = metrics.total_leads
        if total_assigned > 0 and metrics.closed_deals > 0:
            metrics.overall_conversion_rate = round(
                (metrics.closed_deals / total_assigned) * 100, 1
            )

    async def _calculate_time_metrics(
        self,
        metrics: AgentMetrics,
        agent_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """Calculate time-based metrics."""
        # Average time to close (for closed deals)
        closed_deals_query = select(Deal.offer_submitted_at, Deal.closed_at).where(
            and_(
                Deal.agent_id == agent_id,
                Deal.status == "closed",
                Deal.closed_at.isnot(None),
                Deal.closed_at >= period_start,
                Deal.closed_at <= period_end,
            )
        )
        result = await self.session.execute(closed_deals_query)
        deals = result.fetchall()

        if deals:
            total_days = 0
            for deal in deals:
                if deal.closed_at and deal.offer_submitted_at:
                    delta = deal.closed_at - deal.offer_submitted_at
                    total_days += delta.total_seconds() / 86400  # seconds to days
            metrics.avg_time_to_close_days = round(total_days / len(deals), 1)

    async def _calculate_financial_metrics(
        self,
        metrics: AgentMetrics,
        agent_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """Calculate financial metrics."""
        # Total deal value (closed deals)
        value_query = select(func.sum(Deal.deal_value)).where(
            and_(
                Deal.agent_id == agent_id,
                Deal.status == "closed",
                Deal.closed_at >= period_start,
                Deal.closed_at <= period_end,
            )
        )
        result = await self.session.execute(value_query)
        metrics.total_deal_value = float(result.scalar() or 0)

        # Average deal value
        if metrics.closed_deals > 0:
            metrics.avg_deal_value = round(metrics.total_deal_value / metrics.closed_deals, 2)

        # Commission metrics
        total_commission_query = select(func.sum(Commission.commission_amount)).where(
            and_(
                Commission.agent_id == agent_id,
                Commission.status.in_(["paid", "approved"]),
            )
        )
        result = await self.session.execute(total_commission_query)
        metrics.total_commission = float(result.scalar() or 0)

        pending_commission_query = select(func.sum(Commission.commission_amount)).where(
            and_(
                Commission.agent_id == agent_id,
                Commission.status == "pending",
            )
        )
        result = await self.session.execute(pending_commission_query)
        metrics.pending_commission = float(result.scalar() or 0)

    async def _calculate_strengths(
        self,
        metrics: AgentMetrics,
        agent_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """Calculate agent strengths based on closed deals."""
        # Top property types
        property_types_query = (
            select(
                Deal.property_type,
                func.count(Deal.id).label("count"),
            )
            .where(
                and_(
                    Deal.agent_id == agent_id,
                    Deal.status == "closed",
                    Deal.property_type.isnot(None),
                    Deal.closed_at >= period_start,
                    Deal.closed_at <= period_end,
                )
            )
            .group_by(Deal.property_type)
            .order_by(desc("count"))
            .limit(5)
        )
        result = await self.session.execute(property_types_query)
        rows = result.fetchall()

        total = sum(row.count for row in rows) if rows else 0  # type: ignore[misc]
        metrics.top_property_types = [
            {
                "type": row.property_type,
                "count": row.count,  # type: ignore[misc]
                "percentage": round((row.count / total) * 100, 1) if total > 0 else 0,  # type: ignore[operator]
            }
            for row in rows
        ]

        # Top locations (cities)
        locations_query = (
            select(
                Deal.property_city,
                func.count(Deal.id).label("count"),
            )
            .where(
                and_(
                    Deal.agent_id == agent_id,
                    Deal.status == "closed",
                    Deal.property_city.isnot(None),
                    Deal.closed_at >= period_start,
                    Deal.closed_at <= period_end,
                )
            )
            .group_by(Deal.property_city)
            .order_by(desc("count"))
            .limit(5)
        )
        result = await self.session.execute(locations_query)
        rows = result.fetchall()

        total = sum(row.count for row in rows) if rows else 0  # type: ignore[misc]
        metrics.top_locations = [
            {
                "location": row.property_city,
                "count": row.count,  # type: ignore[misc]
                "percentage": round((row.count / total) * 100, 1) if total > 0 else 0,  # type: ignore[operator]
            }
            for row in rows
        ]

    async def _calculate_period_comparison(
        self,
        metrics: AgentMetrics,
        agent_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> None:
        """Calculate comparison to previous period."""
        period_length = (period_end - period_start).days
        prev_start = period_start - timedelta(days=period_length)
        prev_end = period_start

        # Previous period closed deals
        prev_deals_query = select(func.count(Deal.id)).where(
            and_(
                Deal.agent_id == agent_id,
                Deal.status == "closed",
                Deal.closed_at >= prev_start,
                Deal.closed_at <= prev_end,
            )
        )
        result = await self.session.execute(prev_deals_query)
        prev_deals = result.scalar() or 0

        if prev_deals > 0:
            change = ((metrics.closed_deals - prev_deals) / prev_deals) * 100
            metrics.deals_change_percent = round(change, 1)

        # Previous period revenue
        prev_revenue_query = select(func.sum(Deal.deal_value)).where(
            and_(
                Deal.agent_id == agent_id,
                Deal.status == "closed",
                Deal.closed_at >= prev_start,
                Deal.closed_at <= prev_end,
            )
        )
        result = await self.session.execute(prev_revenue_query)
        prev_revenue = float(result.scalar() or 0)

        if prev_revenue > 0:
            change = ((metrics.total_deal_value - prev_revenue) / prev_revenue) * 100
            metrics.revenue_change_percent = round(change, 1)

    async def get_team_comparison(
        self,
        agent_id: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> TeamComparison:
        """Compare agent performance to team averages.

        Args:
            agent_id: The agent's user ID
            period_start: Start of the analysis period
            period_end: End of the analysis period

        Returns:
            TeamComparison with ranking and comparison data
        """
        if period_end is None:
            period_end = datetime.now(UTC)
        if period_start is None:
            period_start = period_end - timedelta(days=30)

        # Get agent name
        agent_query = select(User.full_name, User.email).where(User.id == agent_id)
        result = await self.session.execute(agent_query)
        agent_row = result.fetchone()
        agent_name = agent_row.full_name if agent_row else "Unknown"

        comparison = TeamComparison(
            agent_id=agent_id,
            agent_name=agent_name,
        )

        # Get all agents with their metrics for ranking
        agents_stats = await self._get_all_agents_stats(period_start, period_end)

        if not agents_stats:
            return comparison

        comparison.total_agents = len(agents_stats)

        # Find current agent stats
        agent_stats = None
        for stats in agents_stats:
            if stats["agent_id"] == agent_id:
                agent_stats = stats
                break

        if not agent_stats:
            return comparison

        # Calculate rankings
        sorted_by_deals = sorted(agents_stats, key=lambda x: x["deals"], reverse=True)
        sorted_by_revenue = sorted(agents_stats, key=lambda x: x["revenue"], reverse=True)
        sorted_by_conversion = sorted(
            agents_stats, key=lambda x: x["conversion_rate"], reverse=True
        )

        for i, stats in enumerate(sorted_by_deals, 1):
            if stats["agent_id"] == agent_id:
                comparison.rank_by_deals = i
                break

        for i, stats in enumerate(sorted_by_revenue, 1):
            if stats["agent_id"] == agent_id:
                comparison.rank_by_revenue = i
                break

        for i, stats in enumerate(sorted_by_conversion, 1):
            if stats["agent_id"] == agent_id:
                comparison.rank_by_conversion = i
                break

        # Calculate team averages
        total_deals = sum(s["deals"] for s in agents_stats)
        total_revenue = sum(s["revenue"] for s in agents_stats)

        comparison.team_avg_deals = round(total_deals / len(agents_stats), 1)
        comparison.team_avg_revenue = round(total_revenue / len(agents_stats), 2)

        agents_with_conversion = [s for s in agents_stats if s["conversion_rate"] > 0]
        if agents_with_conversion:
            comparison.team_avg_conversion = round(
                sum(s["conversion_rate"] for s in agents_with_conversion)
                / len(agents_with_conversion),
                1,
            )

        agents_with_time = [s for s in agents_stats if s["avg_time_to_close"]]
        if agents_with_time:
            comparison.team_avg_time_to_close_days = round(
                sum(s["avg_time_to_close"] for s in agents_with_time) / len(agents_with_time), 1
            )

        # Calculate vs average percentages
        if comparison.team_avg_deals > 0:
            comparison.deals_vs_avg_percent = round(
                ((agent_stats["deals"] - comparison.team_avg_deals) / comparison.team_avg_deals)
                * 100,
                1,
            )

        if comparison.team_avg_revenue > 0:
            comparison.revenue_vs_avg_percent = round(
                (
                    (agent_stats["revenue"] - comparison.team_avg_revenue)
                    / comparison.team_avg_revenue
                )
                * 100,
                1,
            )

        if comparison.team_avg_conversion > 0 and agent_stats["conversion_rate"] > 0:
            comparison.conversion_vs_avg_percent = round(
                (
                    (agent_stats["conversion_rate"] - comparison.team_avg_conversion)
                    / comparison.team_avg_conversion
                )
                * 100,
                1,
            )

        if comparison.team_avg_time_to_close_days > 0 and agent_stats["avg_time_to_close"]:
            comparison.time_to_close_vs_avg_percent = round(
                (
                    (agent_stats["avg_time_to_close"] - comparison.team_avg_time_to_close_days)
                    / comparison.team_avg_time_to_close_days
                )
                * 100,
                1,
            )

        return comparison

    async def _get_all_agents_stats(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> list[dict[str, Any]]:
        """Get stats for all agents."""
        # Query to get all agents with deal stats
        query = (
            select(
                User.id.label("agent_id"),
                func.count(Deal.id).filter(Deal.status == "closed").label("deals"),
                func.coalesce(func.sum(Deal.deal_value).filter(Deal.status == "closed"), 0).label(
                    "revenue"
                ),
            )
            .select_from(User)
            .outerjoin(
                Deal,
                and_(
                    Deal.agent_id == User.id,
                    Deal.closed_at >= period_start,
                    Deal.closed_at <= period_end,
                ),
            )
            .where(User.role == "agent")
            .group_by(User.id)
        )

        result = await self.session.execute(query)
        rows = result.fetchall()

        stats = []
        for row in rows:
            # Calculate conversion rate and avg time to close for each agent
            agent_id = row.agent_id

            # Get leads count for conversion
            leads_query = select(func.count(AgentAssignment.id)).where(
                and_(
                    AgentAssignment.agent_id == agent_id,
                    AgentAssignment.assigned_at >= period_start,
                    AgentAssignment.assigned_at <= period_end,
                )
            )
            leads_result = await self.session.execute(leads_query)
            leads_count = leads_result.scalar() or 0

            conversion_rate = 0.0
            if leads_count > 0 and row.deals > 0:
                conversion_rate = round((row.deals / leads_count) * 100, 1)

            # Get avg time to close
            time_query = select(
                func.avg(func.extract("epoch", Deal.closed_at - Deal.offer_submitted_at) / 86400)
            ).where(
                and_(
                    Deal.agent_id == agent_id,
                    Deal.status == "closed",
                    Deal.closed_at.isnot(None),
                    Deal.closed_at >= period_start,
                    Deal.closed_at <= period_end,
                )
            )
            time_result = await self.session.execute(time_query)
            avg_time = time_result.scalar()
            avg_time_float = float(avg_time) if avg_time else None

            stats.append(
                {
                    "agent_id": agent_id,
                    "deals": row.deals or 0,
                    "revenue": float(row.revenue or 0),
                    "conversion_rate": conversion_rate,
                    "avg_time_to_close": avg_time_float,
                }
            )

        return stats

    async def get_performance_trends(
        self,
        agent_id: str,
        interval: str = "month",  # day, week, month, quarter
        periods: int = 12,
    ) -> list[PerformanceTrend]:
        """Get performance trends over time.

        Args:
            agent_id: The agent's user ID
            interval: Time interval (day, week, month, quarter)
            periods: Number of periods to return

        Returns:
            List of PerformanceTrend data points
        """
        trends = []
        now = datetime.now(UTC)

        # Calculate period boundaries
        for i in range(periods - 1, -1, -1):
            if interval == "day":
                period_end = now - timedelta(days=i)
                period_start = period_end - timedelta(days=1)
                period_label = period_start.strftime("%Y-%m-%d")
            elif interval == "week":
                period_end = now - timedelta(weeks=i)
                period_start = period_end - timedelta(weeks=1)
                period_label = period_start.strftime("%Y-W%W")
            elif interval == "quarter":
                # Approximate quarter calculation
                period_end = now - timedelta(days=i * 90)
                period_start = period_end - timedelta(days=90)
                quarter = (period_start.month - 1) // 3 + 1
                period_label = f"{period_start.year}-Q{quarter}"
            else:  # month (default)
                period_end = now - timedelta(days=i * 30)
                period_start = period_end - timedelta(days=30)
                period_label = period_start.strftime("%Y-%m")

            # Get leads for this period
            leads_query = select(func.count(AgentAssignment.id)).where(
                and_(
                    AgentAssignment.agent_id == agent_id,
                    AgentAssignment.assigned_at >= period_start,
                    AgentAssignment.assigned_at < period_end,
                )
            )
            result = await self.session.execute(leads_query)
            leads_count = cast(int, result.scalar() or 0)

            # Get closed deals for this period
            deals_query = select(
                func.count(Deal.id).label("count"),
                func.coalesce(func.sum(Deal.deal_value), 0).label("value"),
            ).where(
                and_(
                    Deal.agent_id == agent_id,
                    Deal.status == "closed",
                    Deal.closed_at >= period_start,
                    Deal.closed_at < period_end,
                )
            )
            result = await self.session.execute(deals_query)
            deals_row = result.fetchone()

            deals_closed = cast(int, deals_row.count) if deals_row else 0
            revenue = float(deals_row.value) if deals_row else 0.0  # type: ignore[misc]

            # Calculate conversion rate
            conversion_rate = 0.0
            if leads_count > 0 and deals_closed > 0:  # type: ignore[operator]
                conversion_rate = round((deals_closed / leads_count) * 100, 1)

            # Calculate average deal value
            avg_deal_value = 0.0
            if deals_closed > 0:  # type: ignore[operator]
                avg_deal_value = round(revenue / deals_closed, 2)  # type: ignore[operator]

            trends.append(
                PerformanceTrend(
                    period=period_label,
                    period_start=period_start,
                    period_end=period_end,
                    leads=leads_count,
                    deals_closed=deals_closed,  # type: ignore[arg-type]
                    revenue=revenue,
                    conversion_rate=conversion_rate,
                    avg_deal_value=avg_deal_value,
                )
            )

        return trends

    async def get_coaching_insights(
        self,
        agent_id: str,
    ) -> list[CoachingInsight]:
        """Generate AI-powered coaching insights.

        Args:
            agent_id: The agent's user ID

        Returns:
            List of CoachingInsight with actionable recommendations
        """
        insights = []

        # Get current metrics
        metrics = await self.get_agent_metrics(agent_id)

        # Strength insights
        if metrics.closed_deals > 5:
            insights.append(
                CoachingInsight(
                    category="strength",
                    title="Consistent Deal Closer",
                    description=f"You've closed {metrics.closed_deals} deals in the analysis period.",
                    actionable_recommendation="Continue your current approach with lead follow-ups.",
                    priority=3,
                )
            )

        if metrics.avg_lead_score > 60:
            insights.append(
                CoachingInsight(
                    category="strength",
                    title="Quality Lead Pipeline",
                    description=f"Your leads have an average score of {metrics.avg_lead_score:.0f}.",
                    actionable_recommendation="Focus on converting high-score leads first.",
                    priority=3,
                )
            )

        if metrics.top_property_types:
            top_type = metrics.top_property_types[0]
            insights.append(
                CoachingInsight(
                    category="strength",
                    title=f"{top_type['type']} Specialist",
                    description=f"{top_type['percentage']:.0f}% of your deals are {top_type['type']} properties.",
                    actionable_recommendation="Position yourself as a specialist in this property type.",
                    priority=2,
                )
            )

        # Improvement insights
        if metrics.avg_time_to_close_days and metrics.avg_time_to_close_days > 60:
            insights.append(
                CoachingInsight(
                    category="improvement",
                    title="Reduce Time to Close",
                    description=f"Your average time to close is {metrics.avg_time_to_close_days:.0f} days.",
                    actionable_recommendation="Set up automated follow-ups at each deal stage.",
                    priority=1,
                )
            )

        if metrics.overall_conversion_rate < 10 and metrics.total_leads > 10:
            insights.append(
                CoachingInsight(
                    category="improvement",
                    title="Improve Conversion Rate",
                    description=f"Your conversion rate is {metrics.overall_conversion_rate:.1f}%.",
                    actionable_recommendation="Focus on leads with scores above 70 and follow up within 24 hours.",
                    priority=1,
                )
            )

        if metrics.fell_through_deals > metrics.closed_deals:
            insights.append(
                CoachingInsight(
                    category="improvement",
                    title="Reduce Deal Fall-Through",
                    description=f"{metrics.fell_through_deals} deals fell through vs {metrics.closed_deals} closed.",
                    actionable_recommendation="Review lost deals to identify common patterns.",
                    priority=2,
                )
            )

        # Opportunity insights
        if metrics.high_value_leads > 0 and metrics.high_value_leads > metrics.active_leads * 0.3:
            insights.append(
                CoachingInsight(
                    category="opportunity",
                    title="High-Value Leads Ready",
                    description=f"You have {metrics.high_value_leads} high-value leads (score >= 70).",
                    actionable_recommendation="Prioritize personal outreach to these leads this week.",
                    priority=1,
                )
            )

        if metrics.pending_commission > 0:
            insights.append(
                CoachingInsight(
                    category="opportunity",
                    title="Pending Commission",
                    description=f"You have €{metrics.pending_commission:,.0f} in pending commissions.",
                    actionable_recommendation="Follow up on deals awaiting commission approval.",
                    priority=2,
                )
            )

        if metrics.new_leads_week > 5:
            insights.append(
                CoachingInsight(
                    category="opportunity",
                    title="Strong Lead Inflow",
                    description=f"You received {metrics.new_leads_week} new leads this week.",
                    actionable_recommendation="Ensure all new leads receive initial contact within 1 hour.",
                    priority=2,
                )
            )

        # Sort by priority
        insights.sort(key=lambda x: x.priority)

        return insights

    async def get_top_performers(
        self,
        metric: str = "deals",  # deals, revenue, conversion
        limit: int = 10,
        period_days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get top performing agents by metric.

        Args:
            metric: The metric to rank by
            limit: Maximum number of results
            period_days: Number of days to analyze

        Returns:
            List of top performers with their stats
        """
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=period_days)

        agents_stats = await self._get_all_agents_stats(period_start, period_end)

        # Sort by the requested metric
        if metric == "revenue":
            sorted_agents = sorted(agents_stats, key=lambda x: x["revenue"], reverse=True)
        elif metric == "conversion":
            sorted_agents = sorted(agents_stats, key=lambda x: x["conversion_rate"], reverse=True)
        else:  # deals (default)
            sorted_agents = sorted(agents_stats, key=lambda x: x["deals"], reverse=True)

        # Get agent names
        performers = []
        for i, stats in enumerate(sorted_agents[:limit], 1):
            agent_query = select(User.full_name, User.email).where(User.id == stats["agent_id"])
            result = await self.session.execute(agent_query)
            agent_row = result.fetchone()

            performers.append(
                {
                    "agent_id": stats["agent_id"],
                    "agent_name": agent_row.full_name if agent_row else "Unknown",
                    "agent_email": agent_row.email if agent_row else None,
                    "metric_value": stats[metric]
                    if metric != "conversion"
                    else stats["conversion_rate"],
                    "rank": i,
                }
            )

        return performers

    async def get_agents_needing_support(
        self,
        threshold_days: int = 30,
    ) -> list[dict[str, Any]]:
        """Identify agents who may need coaching support.

        Args:
            threshold_days: Days without a deal to flag as needing support

        Returns:
            List of agents needing support with suggested actions
        """
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=threshold_days)

        # Find agents with no closed deals in the period
        query = select(
            User.id,
            User.full_name,
            User.email,
        ).where(User.role == "agent")

        result = await self.session.execute(query)
        all_agents = result.fetchall()

        agents_needing_support = []

        for agent in all_agents:
            # Check for closed deals
            deals_query = select(func.count(Deal.id)).where(
                and_(
                    Deal.agent_id == agent.id,
                    Deal.status == "closed",
                    Deal.closed_at >= period_start,
                )
            )
            result = await self.session.execute(deals_query)
            closed_count = result.scalar() or 0

            if closed_count == 0:
                # Get last deal date
                last_deal_query = select(func.max(Deal.closed_at)).where(
                    and_(
                        Deal.agent_id == agent.id,
                        Deal.status == "closed",
                    )
                )
                result = await self.session.execute(last_deal_query)
                last_deal_at = result.scalar()

                # Calculate days without deal
                if last_deal_at:
                    days_without = (period_end - last_deal_at).days
                else:
                    days_without = 999  # Never closed a deal

                # Get current leads count
                leads_query = select(func.count(AgentAssignment.id)).where(
                    and_(
                        AgentAssignment.agent_id == agent.id,
                        AgentAssignment.is_active.is_(True),
                    )
                )
                result = await self.session.execute(leads_query)
                total_leads = result.scalar() or 0

                # Calculate conversion rate
                conversion_rate = 0.0
                if total_leads > 0:
                    total_closed_query = select(func.count(Deal.id)).where(
                        and_(
                            Deal.agent_id == agent.id,
                            Deal.status == "closed",
                        )
                    )
                    result = await self.session.execute(total_closed_query)
                    total_closed = result.scalar() or 0
                    conversion_rate = round((total_closed / total_leads) * 100, 1)

                # Generate suggested actions
                suggested_actions = []
                if total_leads == 0:
                    suggested_actions.append("Assign leads to this agent")
                elif total_leads > 10 and conversion_rate < 5:
                    suggested_actions.append("Review lead qualification process")
                    suggested_actions.append("Schedule one-on-one coaching")
                else:
                    suggested_actions.append("Review recent lost opportunities")
                    suggested_actions.append("Pair with top performer for mentoring")

                agents_needing_support.append(
                    {
                        "agent_id": agent.id,
                        "agent_name": agent.full_name or "Unknown",
                        "agent_email": agent.email,
                        "days_without_deal": days_without,
                        "total_leads": total_leads,
                        "conversion_rate": conversion_rate,
                        "last_deal_at": last_deal_at,
                        "suggested_actions": suggested_actions,
                    }
                )

        # Sort by days without deal (most urgent first)
        agents_needing_support.sort(key=lambda x: x["days_without_deal"], reverse=True)

        return agents_needing_support

    async def get_goal_progress(
        self,
        agent_id: str,
    ) -> list[dict[str, Any]]:
        """Get progress towards goals.

        Args:
            agent_id: The agent's user ID

        Returns:
            List of goal progress data
        """
        now = datetime.now(UTC)

        # Get active goals
        query = (
            select(AgentGoal)
            .where(
                and_(
                    AgentGoal.agent_id == agent_id,
                    AgentGoal.is_active.is_(True),
                    AgentGoal.period_start <= now,
                    AgentGoal.period_end >= now,
                )
            )
            .order_by(AgentGoal.period_end)
        )

        result = await self.session.execute(query)
        goals = result.scalars().all()

        goal_progress = []
        for goal in goals:
            # Calculate current value based on goal type
            current_value = await self._calculate_goal_current_value(
                agent_id, goal.goal_type, goal.period_start, goal.period_end
            )

            # Update the goal's current value in memory
            progress_percent = 0.0
            if goal.target_value > 0:
                progress_percent = min(100.0, (current_value / goal.target_value) * 100)

            days_remaining = (goal.period_end - now).days

            goal_progress.append(
                {
                    "id": goal.id,
                    "goal_type": goal.goal_type,
                    "target_value": goal.target_value,
                    "current_value": current_value,
                    "progress_percent": round(progress_percent, 1),
                    "period_type": goal.period_type,
                    "period_start": goal.period_start,
                    "period_end": goal.period_end,
                    "is_achieved": progress_percent >= 100,
                    "days_remaining": max(0, days_remaining),
                }
            )

        return goal_progress

    async def _calculate_goal_current_value(
        self,
        agent_id: str,
        goal_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> float:
        """Calculate current value for a goal based on its type."""
        if goal_type == "leads":
            query = select(func.count(AgentAssignment.id)).where(
                and_(
                    AgentAssignment.agent_id == agent_id,
                    AgentAssignment.assigned_at >= period_start,
                    AgentAssignment.assigned_at <= period_end,
                )
            )
            result = await self.session.execute(query)
            return float(result.scalar() or 0)

        elif goal_type == "deals":
            query = select(func.count(Deal.id)).where(
                and_(
                    Deal.agent_id == agent_id,
                    Deal.status == "closed",
                    Deal.closed_at >= period_start,
                    Deal.closed_at <= period_end,
                )
            )
            result = await self.session.execute(query)
            return float(result.scalar() or 0)

        elif goal_type == "revenue":
            query = select(func.sum(Deal.deal_value)).where(  # type: ignore[assignment]
                and_(
                    Deal.agent_id == agent_id,
                    Deal.status == "closed",
                    Deal.closed_at >= period_start,
                    Deal.closed_at <= period_end,
                )
            )
            result = await self.session.execute(query)
            return float(result.scalar() or 0)

        elif goal_type == "gci":
            query = select(func.sum(Commission.commission_amount)).where(  # type: ignore[assignment]
                and_(
                    Commission.agent_id == agent_id,
                    Commission.status.in_(["paid", "approved"]),
                )
            )
            result = await self.session.execute(query)
            return float(result.scalar() or 0)

        return 0.0
