"""
User Activity Analytics Service (Task #82).

This service provides:
- Aggregated user activity metrics
- Activity trends over time
- CSV export functionality
- Integration with SearchEvent and UserActivityEvent models
"""

import csv
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from typing import Any, Optional

from sqlalchemy import and_, desc, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import SearchEvent, SearchResultInteraction, UserActivityEvent

logger = logging.getLogger(__name__)


def _dialect_name(session: AsyncSession) -> str:
    """The name of the database dialect behind a session."""
    try:
        return session.get_bind().dialect.name
    except Exception:  # pragma: no cover - an unbound session
        return "sqlite"


def _bucket_date(moment: datetime, interval: str) -> date:
    """The first day of the calendar period a moment falls in.

    Day buckets are the day itself, week buckets the Monday of that week,
    month buckets the first of that month - the same three rules the SQL
    expression applies, so both sides of the comparison agree.
    """
    if interval == "month":
        return moment.date().replace(day=1)
    if interval == "week":
        return moment.date() - timedelta(days=moment.date().weekday())
    return moment.date()


def _next_month(first: date) -> date:
    """The first day of the month after the one that starts on `first`."""
    if first.month == 12:
        return date(first.year + 1, 1, 1)
    return date(first.year, first.month + 1, 1)


def hash_user_id(user_id: str) -> str:
    """Hash user ID for privacy using SHA-256.

    Args:
        user_id: Raw user ID

    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(user_id.encode()).hexdigest()


@dataclass
class UserActivitySummary:
    """Aggregated user activity summary."""

    period_start: datetime
    period_end: datetime
    total_searches: int = 0
    total_property_views: int = 0
    total_property_clicks: int = 0
    total_tool_uses: int = 0
    total_exports: int = 0
    total_favorites: int = 0
    unique_sessions: int = 0
    avg_processing_time_ms: Optional[float] = None
    top_tools: list[dict[str, Any]] = field(default_factory=list)
    top_search_cities: list[dict[str, Any]] = field(default_factory=list)
    event_counts_by_day: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ActivityTrendPoint:
    """Single point in activity trends."""

    date: str
    searches: int = 0
    property_views: int = 0
    tool_uses: int = 0
    exports: int = 0


class UserActivityService:
    """Service for user activity analytics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service.

        Args:
            session: Database session
        """
        self.session = session

    def _bucket_expression(self, column: Any, interval: str) -> Any:
        """An SQL expression that buckets a timestamp into a calendar period.

        PostgreSQL has `date_trunc`; SQLite does not. Both sides are asked
        for the same 'YYYY-MM-DD' key - the first day of the day, week or
        month the timestamp falls in - so the rows bucket the same way on
        either database and the Python side can compare them as plain dates.
        """
        if _dialect_name(self.session) == "postgresql":
            return func.to_char(func.date_trunc(interval, column), "YYYY-MM-DD")
        if interval == "month":
            return func.strftime("%Y-%m-01", column)
        if interval == "week":
            # The Monday of the week, like PostgreSQL's date_trunc('week').
            return func.strftime("%Y-%m-%d", column, "weekday 0", "-6 days")
        return func.strftime("%Y-%m-%d", column)

    def _searches_of(self, user_id: Optional[str]) -> Any:
        """The clause that narrows a search query to one account.

        Without an account every search is in scope - that is the
        administrator's view of the deployment.
        """
        if not user_id:
            return true()
        return SearchEvent.user_id == user_id

    def _interactions_of(self, user_id: Optional[str]) -> Any:
        """The clause that narrows an interaction query to one account.

        An interaction belongs to the search that produced it, and the search
        carries the account.
        """
        if not user_id:
            return true()
        return SearchResultInteraction.search_event_id.in_(
            select(SearchEvent.id).where(SearchEvent.user_id == user_id)
        )

    async def get_activity_summary(
        self,
        user_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> UserActivitySummary:
        """Get aggregated activity summary for a user.

        Args:
            user_id: Optional user ID to filter by (will be hashed)
            period_start: Start of period (default: 30 days ago)
            period_end: End of period (default: now)

        Returns:
            UserActivitySummary with aggregated metrics
        """
        if period_end is None:
            period_end = datetime.now(UTC)
        if period_start is None:
            period_start = period_end - timedelta(days=30)

        user_id_hash = hash_user_id(user_id) if user_id else None

        # The searches, the views and the clicks belong to the account that
        # asks: the summary is "your activity", not the deployment's. An
        # administrator's view of the whole deployment asks without an
        # account and keeps every row.
        searches_of = self._searches_of(user_id)
        interactions_of = self._interactions_of(user_id)

        # Get search metrics from SearchEvent
        search_query = select(func.count(SearchEvent.id)).where(
            and_(
                SearchEvent.search_timestamp >= period_start,
                SearchEvent.search_timestamp < period_end,
                searches_of,
            )
        )

        result = await self.session.execute(search_query)
        total_searches = result.scalar() or 0

        # Get property views from SearchResultInteraction
        views_query = select(func.count(SearchResultInteraction.id)).where(
            and_(
                SearchResultInteraction.interaction_timestamp >= period_start,
                SearchResultInteraction.interaction_timestamp < period_end,
                SearchResultInteraction.viewed.is_(True),
                interactions_of,
            )
        )
        result = await self.session.execute(views_query)
        total_property_views = result.scalar() or 0

        # Get property clicks
        clicks_query = select(func.count(SearchResultInteraction.id)).where(
            and_(
                SearchResultInteraction.interaction_timestamp >= period_start,
                SearchResultInteraction.interaction_timestamp < period_end,
                SearchResultInteraction.clicked.is_(True),
                interactions_of,
            )
        )
        result = await self.session.execute(clicks_query)
        total_property_clicks = result.scalar() or 0

        # Get unique sessions
        sessions_query = select(func.count(func.distinct(SearchEvent.session_id))).where(
            and_(
                SearchEvent.search_timestamp >= period_start,
                SearchEvent.search_timestamp < period_end,
                searches_of,
            )
        )
        result = await self.session.execute(sessions_query)
        unique_sessions = result.scalar() or 0

        # Get average processing time
        avg_time_query = select(func.avg(SearchEvent.processing_time_ms)).where(
            and_(
                SearchEvent.search_timestamp >= period_start,
                SearchEvent.search_timestamp < period_end,
                searches_of,
            )
        )
        result = await self.session.execute(avg_time_query)
        avg_processing_time_ms = result.scalar()

        # Get tool uses from UserActivityEvent
        tool_uses_query = select(func.count(UserActivityEvent.id)).where(
            and_(
                UserActivityEvent.event_timestamp >= period_start,
                UserActivityEvent.event_timestamp < period_end,
                UserActivityEvent.event_type == "tool_use",
            )
        )
        if user_id_hash:
            tool_uses_query = tool_uses_query.where(UserActivityEvent.user_id_hash == user_id_hash)
        result = await self.session.execute(tool_uses_query)
        total_tool_uses = result.scalar() or 0

        # Get exports from UserActivityEvent
        exports_query = select(func.count(UserActivityEvent.id)).where(
            and_(
                UserActivityEvent.event_timestamp >= period_start,
                UserActivityEvent.event_timestamp < period_end,
                UserActivityEvent.event_type == "export",
            )
        )
        if user_id_hash:
            exports_query = exports_query.where(UserActivityEvent.user_id_hash == user_id_hash)
        result = await self.session.execute(exports_query)
        total_exports = result.scalar() or 0

        # Get favorites (add + remove)
        favorites_query = select(func.count(UserActivityEvent.id)).where(
            and_(
                UserActivityEvent.event_timestamp >= period_start,
                UserActivityEvent.event_timestamp < period_end,
                UserActivityEvent.event_type.in_(["favorite_add", "favorite_remove"]),
            )
        )
        if user_id_hash:
            favorites_query = favorites_query.where(UserActivityEvent.user_id_hash == user_id_hash)
        result = await self.session.execute(favorites_query)
        total_favorites = result.scalar() or 0

        # Get top tools
        top_tools = await self._get_top_tools(user_id_hash, period_start, period_end)

        # Get top search cities (from SearchEvent.filters)
        top_search_cities = await self._get_top_search_cities(period_start, period_end, user_id)

        # Get event counts by day
        event_counts_by_day = await self._get_event_counts_by_day(period_start, period_end, user_id)

        return UserActivitySummary(
            period_start=period_start,
            period_end=period_end,
            total_searches=total_searches,
            total_property_views=total_property_views,
            total_property_clicks=total_property_clicks,
            total_tool_uses=total_tool_uses,
            total_exports=total_exports,
            total_favorites=total_favorites,
            unique_sessions=unique_sessions,
            avg_processing_time_ms=avg_processing_time_ms,
            top_tools=top_tools,
            top_search_cities=top_search_cities,
            event_counts_by_day=event_counts_by_day,
        )

    async def _get_top_tools(
        self,
        user_id_hash: Optional[str],
        period_start: datetime,
        period_end: datetime,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get most used tools in period.

        Args:
            user_id_hash: Optional hashed user ID for filtering
            period_start: Start of period
            period_end: End of period
            limit: Maximum results

        Returns:
            List of {tool_name, count} dicts
        """
        # Extract tool name from event_data->tool_name
        query = (
            select(
                UserActivityEvent.event_data["tool_name"].label("tool_name"),
                func.count(UserActivityEvent.id).label("count"),
            )
            .where(
                and_(
                    UserActivityEvent.event_timestamp >= period_start,
                    UserActivityEvent.event_timestamp < period_end,
                    UserActivityEvent.event_type == "tool_use",
                )
            )
            .group_by(UserActivityEvent.event_data["tool_name"])
            .order_by(desc("count"))
            .limit(limit)
        )

        if user_id_hash:
            query = query.where(UserActivityEvent.user_id_hash == user_id_hash)

        result = await self.session.execute(query)
        rows = result.all()

        return [{"tool_name": row.tool_name or "unknown", "count": row.count} for row in rows]

    async def _get_top_search_cities(
        self,
        period_start: datetime,
        period_end: datetime,
        user_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get most searched cities in period.

        Args:
            period_start: Start of period
            period_end: End of period
            user_id: The account whose searches are counted, or None for all
            limit: Maximum results

        Returns:
            List of {city, count} dicts
        """
        # Extract city from filters->city
        query = (
            select(
                SearchEvent.filters["city"].label("city"),
                func.count(SearchEvent.id).label("count"),
            )
            .where(
                and_(
                    SearchEvent.search_timestamp >= period_start,
                    SearchEvent.search_timestamp < period_end,
                    SearchEvent.filters["city"].is_not(None),
                    self._searches_of(user_id),
                )
            )
            .group_by(SearchEvent.filters["city"])
            .order_by(desc("count"))
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.all()

        return [{"city": row.city or "unknown", "count": row.count} for row in rows]

    async def _get_event_counts_by_day(
        self,
        period_start: datetime,
        period_end: datetime,
        user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Get event counts grouped by day.

        Args:
            period_start: Start of period
            period_end: End of period
            user_id: The account whose searches are counted, or None for all

        Returns:
            List of {date, searches, views, clicks, tool_uses, exports} dicts
        """
        # Get search counts by day
        day_key = self._bucket_expression(SearchEvent.search_timestamp, "day").label("day")
        searches_query = (
            select(day_key, func.count(SearchEvent.id).label("event_count"))
            .where(
                and_(
                    SearchEvent.search_timestamp >= period_start,
                    SearchEvent.search_timestamp < period_end,
                    self._searches_of(user_id),
                )
            )
            .group_by(day_key)
            .order_by(day_key)
        )

        result = await self.session.execute(searches_query)
        search_by_day = {key: int(count) for key, count in result.all()}

        # Build daily summary
        daily_counts = []
        current = period_start.date()
        end = period_end.date()

        while current < end:
            day_str = current.isoformat()

            daily_counts.append(
                {
                    "date": day_str,
                    "searches": search_by_day.get(day_str, 0),
                }
            )
            current += timedelta(days=1)

        return daily_counts

    async def get_activity_trends(
        self,
        user_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        interval: str = "day",
    ) -> list[ActivityTrendPoint]:
        """Get activity trends over time.

        Args:
            user_id: Optional user ID to filter by
            period_start: Start of period (default: 30 days ago)
            period_end: End of period (default: now)
            interval: Time grouping (day, week, month)

        Returns:
            List of ActivityTrendPoint
        """
        if period_end is None:
            period_end = datetime.now(UTC)
        if period_start is None:
            period_start = period_end - timedelta(days=30)

        trends = []

        # The bucket the rows fall into, and the step the buckets advance by.
        bucket = self._bucket_expression(SearchEvent.search_timestamp, interval)

        # Get searches per interval
        search_query = (
            select(bucket.label("period"), func.count(SearchEvent.id).label("event_count"))
            .where(
                and_(
                    SearchEvent.search_timestamp >= period_start,
                    SearchEvent.search_timestamp < period_end,
                    self._searches_of(user_id),
                )
            )
            .group_by(bucket)
            .order_by(bucket)
        )

        result = await self.session.execute(search_query)
        searches_by_period = {key: int(count) for key, count in result.all()}

        # Generate trend points, one per calendar bucket.
        current = _bucket_date(period_start, interval)
        while current < period_end.date():
            key = current.isoformat()

            trends.append(
                ActivityTrendPoint(
                    date=key,
                    searches=searches_by_period.get(key, 0),
                )
            )
            if interval == "month":
                current = _next_month(current)
            elif interval == "week":
                current += timedelta(weeks=1)
            else:
                current += timedelta(days=1)

        return trends

    async def export_activity_csv(
        self,
        user_id: Optional[str] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> str:
        """Export user activity as CSV.

        Args:
            user_id: Optional user ID to filter by
            period_start: Start of period (default: 30 days ago)
            period_end: End of period (default: now)

        Returns:
            CSV string
        """
        if period_end is None:
            period_end = datetime.now(UTC)
        if period_start is None:
            period_start = period_end - timedelta(days=30)

        user_id_hash = hash_user_id(user_id) if user_id else None

        output = StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "timestamp",
                "event_type",
                "event_category",
                "session_id",
                "duration_ms",
                "event_data",
            ]
        )

        # Query events
        query = (
            select(UserActivityEvent)
            .where(
                and_(
                    UserActivityEvent.event_timestamp >= period_start,
                    UserActivityEvent.event_timestamp < period_end,
                )
            )
            .order_by(UserActivityEvent.event_timestamp)
        )

        if user_id_hash:
            query = query.where(UserActivityEvent.user_id_hash == user_id_hash)

        result = await self.session.execute(query)
        events = result.scalars().all()

        for event in events:
            writer.writerow(
                [
                    event.event_timestamp.isoformat(),
                    event.event_type,
                    event.event_category,
                    event.session_id[:8] + "...",  # Truncate for privacy
                    event.duration_ms or "",
                    str(event.event_data) if event.event_data else "",
                ]
            )

        return output.getvalue()

    async def track_event(
        self,
        session_id: str,
        event_type: str,
        event_category: str,
        user_id: Optional[str] = None,
        event_data: Optional[dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ) -> UserActivityEvent:
        """Record a user activity event.

        Args:
            session_id: Session identifier
            event_type: Type of event (search_query, property_view, etc.)
            event_category: Category (engagement, feature_use, etc.)
            user_id: Optional user ID (will be hashed)
            event_data: Optional event metadata
            duration_ms: Optional duration in milliseconds

        Returns:
            Created UserActivityEvent
        """
        hashed_user_id = hash_user_id(user_id) if user_id else None

        event = UserActivityEvent(
            user_id_hash=hashed_user_id,
            session_id=session_id,
            event_type=event_type,
            event_category=event_category,
            event_data=event_data,
            duration_ms=duration_ms,
        )

        self.session.add(event)
        await self.session.flush()

        user_display = f"{hashed_user_id[:8]}..." if hashed_user_id else "anonymous"
        logger.info("Recorded activity event: %s for user %s", event_type, user_display)

        return event
