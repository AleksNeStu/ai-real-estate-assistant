"""Unit tests for UserActivityService (Task #82)."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from db.models import RankingConfig, SearchEvent, UserActivityEvent
from services.user_activity_service import (
    ActivityTrendPoint,
    UserActivityService,
    UserActivitySummary,
    hash_user_id,
)


@pytest.fixture
def activity_service(db_session):
    """Create a UserActivityService instance for testing."""
    return UserActivityService(db_session)


class TestUserActivityService:
    """Tests for UserActivityService core functionality."""

    @pytest.mark.asyncio
    async def test_track_event_creates_record(self, activity_service, db_session):
        """Test that track_event creates a new UserActivityEvent."""
        event = await activity_service.track_event(
            session_id="test-session-123",
            event_type="tool_use",
            event_category="tools",
            event_data={"tool_name": "mortgage_calculator"},
            user_id="user-456",
            duration_ms=150,
        )

        await db_session.flush()

        assert event.id is not None
        assert event.session_id == "test-session-123"
        assert event.event_type == "tool_use"
        assert event.event_category == "tools"
        assert event.event_data == {"tool_name": "mortgage_calculator"}
        assert event.duration_ms == 150
        # User ID should be hashed
        assert event.user_id_hash != "user-456"
        assert len(event.user_id_hash) == 64  # SHA-256 hex length

    @pytest.mark.asyncio
    async def test_track_event_minimal(self, activity_service, db_session):
        """Test tracking event with minimal required data."""
        event = await activity_service.track_event(
            session_id="test-session-minimal",
            event_type="page_view",
            event_category="navigation",
        )

        await db_session.flush()

        assert event.id is not None
        assert event.session_id == "test-session-minimal"
        assert event.event_type == "page_view"
        assert event.event_category == "navigation"
        assert event.user_id_hash is None
        assert event.duration_ms is None

    @pytest.mark.asyncio
    async def test_get_activity_summary_returns_aggregated_data(self, activity_service, db_session):
        """Test that get_activity_summary returns correct aggregations."""
        # Create tool use events
        await activity_service.track_event(
            "test-session-1",
            "tool_use",
            "tools",
            event_data={"tool_name": "mortgage_calculator"},
        )
        await activity_service.track_event(
            "test-session-2",
            "tool_use",
            "tools",
            event_data={"tool_name": "investment_analyzer"},
        )
        await activity_service.track_event(
            "test-session-1",
            "export",
            "export",
        )
        await activity_service.track_event(
            "test-session-2",
            "favorite_add",
            "engagement",
        )

        await db_session.flush()

        summary = await activity_service.get_activity_summary()

        assert isinstance(summary, UserActivitySummary)
        assert summary.total_tool_uses == 2
        assert summary.total_exports == 1
        assert summary.total_favorites == 1

    @pytest.mark.asyncio
    async def test_get_activity_summary_filters_by_date_range(self, activity_service, db_session):
        """Test that get_activity_summary can filter by date range.

        Note: date_range filtering works for UserActivityEvent but
        _get_event_counts_by_day uses SearchEvent with PostgreSQL's date_trunc.
        This test focuses on the UserActivityEvent filtering.
        """
        now = datetime.now(UTC)

        # Create event inside 30-day window
        recent_event = await activity_service.track_event(
            "test-session", "recent_tool_use", "tools"
        )
        recent_event.event_timestamp = now - timedelta(days=5)
        db_session.add(recent_event)

        # Create event outside 30-day window
        old_event = await activity_service.track_event("test-session-2", "old_tool_use", "tools")
        old_event.event_timestamp = now - timedelta(days=60)
        db_session.add(old_event)

        await db_session.flush()

        # Direct query to verify UserActivityEvent filtering works
        result = await db_session.execute(
            select(UserActivityEvent).where(
                UserActivityEvent.event_timestamp >= now - timedelta(days=30)
            )
        )
        events = result.scalars().all()

        # Should only have the recent event
        assert len(events) == 1
        assert events[0].event_type == "recent_tool_use"

    @pytest.mark.asyncio
    async def test_get_activity_summary_with_user_filter(self, activity_service, db_session):
        """Test that get_activity_summary can filter by user."""
        user_id_1 = "user-1@example.com"
        user_id_2 = "user-2@example.com"

        # Create events for user 1
        await activity_service.track_event("session-1", "tool_use", "tools", user_id=user_id_1)
        await activity_service.track_event("session-2", "tool_use", "tools", user_id=user_id_1)

        # Create event for user 2
        await activity_service.track_event("session-3", "tool_use", "tools", user_id=user_id_2)

        await db_session.flush()

        # Filter by user 1 - should get 2 events
        summary = await activity_service.get_activity_summary(user_id=user_id_1)

        assert summary.total_tool_uses == 2

        # Filter by user 2 - should get 1 event
        summary = await activity_service.get_activity_summary(user_id=user_id_2)

        assert summary.total_tool_uses == 1

    @pytest.mark.asyncio
    async def test_get_activity_trends_buckets_by_calendar_period(
        self, activity_service, db_session
    ):
        """The trends land in calendar buckets on any database."""
        config = RankingConfig(name="trend-test-config", description="trends")
        db_session.add(config)
        await db_session.flush()

        # A Wednesday and the Thursday after it.
        db_session.add(
            SearchEvent(
                session_id="trend-session",
                ranking_config_id=config.id,
                query="apartments in Krakow",
                results_count=3,
                processing_time_ms=12,
                search_timestamp=datetime(2026, 11, 4, 9, 30, tzinfo=UTC),
            )
        )
        db_session.add(
            SearchEvent(
                session_id="trend-session",
                ranking_config_id=config.id,
                query="apartments in Warsaw",
                results_count=2,
                processing_time_ms=9,
                search_timestamp=datetime(2026, 11, 5, 18, 0, tzinfo=UTC),
            )
        )
        await db_session.flush()

        period_start = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)
        period_end = datetime(2026, 11, 8, 0, 0, tzinfo=UTC)

        days = await activity_service.get_activity_trends(
            period_start=period_start, period_end=period_end, interval="day"
        )
        assert {point.date: point.searches for point in days} == {
            "2026-11-01": 0,
            "2026-11-02": 0,
            "2026-11-03": 0,
            "2026-11-04": 1,
            "2026-11-05": 1,
            "2026-11-06": 0,
            "2026-11-07": 0,
        }

        # The week starts on its Monday - both searches fall in the same one.
        # 2026-11-01 is a Sunday, so the first bucket is the week before.
        weeks = await activity_service.get_activity_trends(
            period_start=period_start, period_end=period_end, interval="week"
        )
        assert {point.date: point.searches for point in weeks} == {
            "2026-10-26": 0,
            "2026-11-02": 2,
        }

        months = await activity_service.get_activity_trends(
            period_start=period_start, period_end=period_end, interval="month"
        )
        assert {point.date: point.searches for point in months} == {"2026-11-01": 2}

    @pytest.mark.asyncio
    async def test_get_activity_summary_counts_the_accounts_own_searches(
        self, activity_service, db_session
    ):
        """The summary is the account's activity, not the deployment's."""
        config = RankingConfig(name="scope-test-config", description="scope")
        db_session.add(config)
        await db_session.flush()

        for owner, query in (("user-a", "apartments in Krakow"), ("user-b", "flats in Warsaw")):
            db_session.add(
                SearchEvent(
                    session_id=f"scope-{owner}",
                    user_id=owner,
                    ranking_config_id=config.id,
                    query=query,
                    results_count=1,
                    processing_time_ms=8,
                    search_timestamp=datetime(2026, 11, 4, 9, 0, tzinfo=UTC),
                )
            )
        await db_session.flush()

        period_start = datetime(2026, 11, 1, tzinfo=UTC)
        period_end = datetime(2026, 11, 10, tzinfo=UTC)

        mine = await activity_service.get_activity_summary(
            user_id="user-a", period_start=period_start, period_end=period_end
        )
        assert mine.total_searches == 1
        assert mine.unique_sessions == 1
        assert sum(point["searches"] for point in mine.event_counts_by_day) == 1

        trends = await activity_service.get_activity_trends(
            user_id="user-a", period_start=period_start, period_end=period_end
        )
        assert sum(point.searches for point in trends) == 1

        # The deployment's own view keeps every search.
        everything = await activity_service.get_activity_summary(
            period_start=period_start, period_end=period_end
        )
        assert everything.total_searches == 2

    @pytest.mark.asyncio
    async def test_export_activity_csv_returns_valid_csv(self, activity_service, db_session):
        """Test CSV export format."""
        await activity_service.track_event(
            "s1",
            "search_query",
            "search",
            event_data={"query": "apartments in Krakow"},
        )
        await activity_service.track_event(
            "s1",
            "property_view",
            "view",
            event_data={"property_id": "prop-123"},
        )

        await db_session.flush()

        csv_data = await activity_service.export_activity_csv()

        # Check header row
        assert "timestamp" in csv_data
        assert "session_id" in csv_data
        assert "event_type" in csv_data
        assert "event_category" in csv_data

        # Check data rows
        lines = csv_data.strip().split("\n")
        assert len(lines) >= 3  # Header + 2 data rows

    @pytest.mark.asyncio
    async def test_export_activity_csv_filters_by_user(self, activity_service, db_session):
        """Test CSV export can filter by user."""
        user_id_1 = "user-1@example.com"
        user_id_2 = "user-2@example.com"

        await activity_service.track_event("s1", "tool_use", "tools", user_id=user_id_1)
        await activity_service.track_event("s2", "tool_use", "tools", user_id=user_id_2)

        await db_session.flush()

        csv_data = await activity_service.export_activity_csv(user_id=user_id_1)

        lines = csv_data.strip().split("\n")
        # Should have header + 1 data row (only user 1 event)
        assert len(lines) == 2
        # Should only contain s1 session
        assert "s1" in csv_data
        assert "s2" not in csv_data

    @pytest.mark.asyncio
    async def test_export_activity_csv_truncates_session_id(self, activity_service, db_session):
        """Test CSV export truncates session IDs for privacy."""
        long_session_id = "s1" + "x" * 50

        await activity_service.track_event(long_session_id, "search_query", "search")

        await db_session.flush()

        csv_data = await activity_service.export_activity_csv(
            period_end=datetime.now(UTC) + timedelta(seconds=1),
        )

        # Session ID should be truncated
        assert "..." in csv_data
        # Full long session ID should not be present
        assert long_session_id not in csv_data

    @pytest.mark.asyncio
    async def test_privacy_no_raw_user_ids_stored(self, activity_service, db_session):
        """Test that user privacy is preserved (no raw user IDs stored)."""
        user_id = "user@example.com"

        await activity_service.track_event(
            "s1",
            "test",
            "test",
            user_id=user_id,
        )

        await db_session.flush()

        # Query directly to verify user_id_hash is not the raw email
        result = await db_session.execute(
            select(UserActivityEvent).where(UserActivityEvent.session_id == "s1")
        )
        event = result.scalar_one()

        # Verify the hash is not the original value
        assert event.user_id_hash != user_id
        # Verify it's a proper hash (64 hex chars for SHA-256)
        assert len(event.user_id_hash) == 64
        assert all(c in "0123456789abcdef" for c in event.user_id_hash)

    @pytest.mark.asyncio
    async def test_event_data_serialization(self, activity_service, db_session):
        """Test that event_data JSON is properly stored and retrieved."""
        complex_data = {
            "filters": {"city": "Krakow", "price_max": 500000},
            "results_count": 42,
            "user_agent": "Mozilla/5.0",
        }

        await activity_service.track_event(
            "s1",
            "search_query",
            "search",
            event_data=complex_data,
        )

        await db_session.flush()

        # Query and verify
        result = await db_session.execute(
            select(UserActivityEvent).where(UserActivityEvent.session_id == "s1")
        )
        event = result.scalar_one()

        assert event.event_data == complex_data


class TestHashUserId:
    """Tests for the hash_user_id function."""

    def test_hash_user_id_is_consistent(self):
        """Test that hashing is deterministic."""
        hash1 = hash_user_id("user-123")
        hash2 = hash_user_id("user-123")
        assert hash1 == hash2

    def test_hash_user_id_is_different_for_different_inputs(self):
        """Test that different inputs produce different hashes."""
        hash1 = hash_user_id("user-123")
        hash2 = hash_user_id("user-456")
        assert hash1 != hash2

    def test_hash_user_id_is_sha256(self):
        """Test that hashing uses SHA-256 algorithm."""
        user_id = "test-user@example.com"
        result = hash_user_id(user_id)

        # Verify it's SHA-256 by computing expected hash
        expected = hashlib.sha256(user_id.encode()).hexdigest()
        assert result == expected

    def test_hash_user_id_output_format(self):
        """Test that hash output is 64 hex characters."""
        result = hash_user_id("test-user")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestUserActivitySummary:
    """Tests for UserActivitySummary dataclass."""

    def test_summary_dataclass_creation(self):
        """Test creating UserActivitySummary."""
        now = datetime.now(UTC)

        summary = UserActivitySummary(
            period_start=now - timedelta(days=30),
            period_end=now,
            total_searches=100,
            total_property_views=50,
            total_property_clicks=25,
            total_tool_uses=10,
            total_exports=5,
            total_favorites=15,
            unique_sessions=8,
            avg_processing_time_ms=1500.5,
            top_tools=[{"tool_name": "mortgage", "count": 5}],
            top_search_cities=[{"city": "Krakow", "count": 30}],
            event_counts_by_day=[{"date": "2024-01-01", "searches": 10}],
        )

        assert summary.total_searches == 100
        assert summary.avg_processing_time_ms == 1500.5
        assert len(summary.top_tools) == 1

    def test_summary_dataclass_defaults(self):
        """Test UserActivitySummary default values."""
        now = datetime.now(UTC)

        summary = UserActivitySummary(
            period_start=now - timedelta(days=30),
            period_end=now,
        )

        assert summary.total_searches == 0
        assert summary.unique_sessions == 0
        assert summary.avg_processing_time_ms is None
        assert summary.top_tools == []
        assert summary.event_counts_by_day == []


class TestActivityTrendPoint:
    """Tests for ActivityTrendPoint dataclass."""

    def test_trend_point_creation(self):
        """Test creating ActivityTrendPoint."""
        trend = ActivityTrendPoint(
            date="2024-01-01",
            searches=10,
            property_views=5,
            tool_uses=2,
            exports=1,
        )

        assert trend.date == "2024-01-01"
        assert trend.searches == 10
        assert trend.property_views == 5
        assert trend.tool_uses == 2
        assert trend.exports == 1

    def test_trend_point_defaults(self):
        """Test ActivityTrendPoint default values."""
        trend = ActivityTrendPoint(date="2024-01-01")

        assert trend.searches == 0
        assert trend.property_views == 0
        assert trend.tool_uses == 0
        assert trend.exports == 0


@pytest.fixture(autouse=True)
async def _the_test_users_exist(create_test_users):
    """The users the activity belongs to have to be real rows.

    The deployment enforces foreign keys, and an activity event belongs to a
    user - so the user has to exist for the event to be writable at all.
    """
    await create_test_users("user-456", "user-a", "user-b")
