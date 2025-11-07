"""
Tests for session analytics and tracking module.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from analytics import SessionTracker, SessionStats, EventType


@pytest.fixture
def temp_analytics():
    """Create temporary analytics directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def session_tracker(temp_analytics):
    """Create SessionTracker with temp storage."""
    return SessionTracker(session_id="test_session_123", storage_path=temp_analytics)


class TestEventType:
    """Tests for EventType enum."""

    def test_event_type_values(self):
        """Test EventType enum values."""
        assert EventType.QUERY.value == "query"
        assert EventType.PROPERTY_VIEW.value == "property_view"
        assert EventType.SEARCH.value == "search"
        assert EventType.EXPORT.value == "export"
        assert EventType.FAVORITE.value == "favorite"
        assert EventType.MODEL_CHANGE.value == "model_change"
        assert EventType.TOOL_USE.value == "tool_use"
        assert EventType.ERROR.value == "error"


class TestSessionTracker:
    """Tests for SessionTracker class."""

    def test_initialization(self, temp_analytics):
        """Test tracker initialization."""
        tracker = SessionTracker(session_id="init_test", storage_path=temp_analytics)

        assert tracker.session_id == "init_test"
        assert tracker.session_start is not None
        assert len(tracker.events) == 0
        assert Path(temp_analytics).exists()

    def test_track_event_basic(self, session_tracker):
        """Test tracking a basic event."""
        session_tracker.track_event(
            event_type=EventType.QUERY,
            data={'query': 'test query'}
        )

        assert len(session_tracker.events) == 1
        event = session_tracker.events[0]
        assert event.event_type == EventType.QUERY
        assert event.data['query'] == 'test query'

    def test_track_event_with_duration(self, session_tracker):
        """Test tracking event with duration."""
        session_tracker.track_event(
            event_type=EventType.QUERY,
            data={'query': 'test'},
            duration_ms=250
        )

        event = session_tracker.events[0]
        assert event.duration_ms == 250

    def test_track_query(self, session_tracker):
        """Test tracking a query event."""
        session_tracker.track_query(
            query="Find apartments in Krakow",
            intent="simple_retrieval",
            complexity="simple",
            processing_time_ms=180
        )

        assert len(session_tracker.events) == 1
        event = session_tracker.events[0]
        assert event.event_type == EventType.QUERY
        assert event.data['query'] == "Find apartments in Krakow"
        assert event.data['intent'] == "simple_retrieval"
        assert event.data['complexity'] == "simple"
        assert event.duration_ms == 180

    def test_track_property_view(self, session_tracker):
        """Test tracking a property view event."""
        session_tracker.track_property_view(
            property_id="prop123",
            property_city="Krakow",
            property_price=950.0
        )

        assert len(session_tracker.events) == 1
        event = session_tracker.events[0]
        assert event.event_type == EventType.PROPERTY_VIEW
        assert event.data['property_id'] == "prop123"
        assert event.data['city'] == "Krakow"
        assert event.data['price'] == 950.0

    def test_track_search(self, session_tracker):
        """Test tracking a search event."""
        session_tracker.track_search(
            search_criteria={'city': 'Krakow', 'max_price': 1000},
            results_count=15
        )

        event = session_tracker.events[0]
        assert event.event_type == EventType.SEARCH
        assert event.data['criteria']['city'] == 'Krakow'
        assert event.data['results_count'] == 15

    def test_track_export(self, session_tracker):
        """Test tracking an export event."""
        session_tracker.track_export(
            format="excel",
            property_count=25
        )

        event = session_tracker.events[0]
        assert event.event_type == EventType.EXPORT
        assert event.data['format'] == "excel"
        assert event.data['property_count'] == 25

    def test_track_favorite(self, session_tracker):
        """Test tracking a favorite event."""
        session_tracker.track_favorite(
            property_id="fav123",
            action="add"
        )

        event = session_tracker.events[0]
        assert event.event_type == EventType.FAVORITE
        assert event.data['property_id'] == "fav123"
        assert event.data['action'] == "add"

    def test_track_model_change(self, session_tracker):
        """Test tracking a model change event."""
        session_tracker.track_model_change(
            old_model="gpt-3.5-turbo",
            new_model="gpt-4o"
        )

        event = session_tracker.events[0]
        assert event.event_type == EventType.MODEL_CHANGE
        assert event.data['old_model'] == "gpt-3.5-turbo"
        assert event.data['new_model'] == "gpt-4o"

    def test_track_tool_use(self, session_tracker):
        """Test tracking a tool use event."""
        session_tracker.track_tool_use(
            tool_name="mortgage_calculator",
            parameters={'price': 200000, 'rate': 4.5}
        )

        event = session_tracker.events[0]
        assert event.event_type == EventType.TOOL_USE
        assert event.data['tool_name'] == "mortgage_calculator"
        assert event.data['parameters']['price'] == 200000

    def test_track_error(self, session_tracker):
        """Test tracking an error event."""
        session_tracker.track_error(
            error_type="ValueError",
            error_message="Invalid input"
        )

        event = session_tracker.events[0]
        assert event.event_type == EventType.ERROR
        assert event.data['error_type'] == "ValueError"
        assert event.data['error_message'] == "Invalid input"

    def test_multiple_events(self, session_tracker):
        """Test tracking multiple events."""
        session_tracker.track_query("query 1", "simple", "simple", 100)
        session_tracker.track_query("query 2", "complex", "complex", 200)
        session_tracker.track_property_view("prop1", "Krakow", 900)
        session_tracker.track_export("csv", 10)

        assert len(session_tracker.events) == 4

        query_events = [e for e in session_tracker.events if e.event_type == EventType.QUERY]
        assert len(query_events) == 2

    def test_get_session_stats(self, session_tracker):
        """Test getting session statistics."""
        # Add various events
        session_tracker.track_query("q1", "simple", "simple", 100)
        session_tracker.track_query("q2", "complex", "complex", 200)
        session_tracker.track_property_view("p1", "Krakow", 900)
        session_tracker.track_property_view("p2", "Warsaw", 1200)
        session_tracker.track_export("excel", 15)
        session_tracker.track_favorite("fav1", "add")
        session_tracker.track_model_change(None, "gpt-4o")
        session_tracker.track_tool_use("calculator", {})

        stats = session_tracker.get_session_stats()

        assert isinstance(stats, SessionStats)
        assert stats.session_id == "test_session_123"
        assert stats.total_queries == 2
        assert stats.total_property_views == 2
        assert stats.total_exports == 1
        assert stats.total_favorites == 1
        assert len(stats.unique_models_used) == 1
        assert "gpt-4o" in stats.unique_models_used
        assert len(stats.tools_used) == 1
        assert stats.errors_encountered == 0
        assert stats.total_duration_minutes > 0

    def test_get_session_stats_with_errors(self, session_tracker):
        """Test session stats includes error count."""
        session_tracker.track_error("TypeError", "Test error")
        session_tracker.track_error("ValueError", "Another error")

        stats = session_tracker.get_session_stats()
        assert stats.errors_encountered == 2

    def test_get_popular_queries(self, session_tracker):
        """Test getting popular query patterns."""
        session_tracker.track_query("q1", "simple_retrieval", "simple")
        session_tracker.track_query("q2", "simple_retrieval", "simple")
        session_tracker.track_query("q3", "filtered_search", "medium")
        session_tracker.track_query("q4", "simple_retrieval", "simple")
        session_tracker.track_query("q5", "calculation", "complex")

        popular = session_tracker.get_popular_queries(top_n=3)

        assert len(popular) <= 3
        # simple_retrieval should be most common (3 occurrences)
        assert popular[0]['intent'] == 'simple_retrieval'
        assert popular[0]['count'] == 3

    def test_get_popular_queries_empty(self, session_tracker):
        """Test popular queries with no query events."""
        popular = session_tracker.get_popular_queries()
        assert len(popular) == 0

    def test_get_avg_processing_time(self, session_tracker):
        """Test calculating average processing time."""
        session_tracker.track_query("q1", "simple", "simple", 100)
        session_tracker.track_query("q2", "simple", "simple", 200)
        session_tracker.track_query("q3", "simple", "simple", 300)

        avg_time = session_tracker.get_avg_processing_time(EventType.QUERY)

        assert avg_time == 200.0  # (100 + 200 + 300) / 3

    def test_get_avg_processing_time_no_data(self, session_tracker):
        """Test average processing time with no data."""
        avg_time = session_tracker.get_avg_processing_time(EventType.QUERY)
        assert avg_time is None

    def test_get_avg_processing_time_no_duration(self, session_tracker):
        """Test average processing time when events have no duration."""
        session_tracker.track_query("q1", "simple", "simple")  # No duration
        avg_time = session_tracker.get_avg_processing_time(EventType.QUERY)
        assert avg_time is None


class TestSessionPersistence:
    """Tests for session data persistence."""

    def test_session_file_created(self, temp_analytics):
        """Test that session file is created."""
        tracker = SessionTracker("persist_test", storage_path=temp_analytics)
        tracker.track_query("test query", "simple", "simple")

        # Force save by tracking 10 events (auto-save threshold)
        for i in range(10):
            tracker.track_event(EventType.QUERY, data={'test': i})

        # Check file exists
        session_file = Path(temp_analytics) / "session_persist_test.json"
        assert session_file.exists()

    def test_session_file_content(self, temp_analytics):
        """Test session file contains valid JSON."""
        tracker = SessionTracker("content_test", storage_path=temp_analytics)
        tracker.track_query("test query", "simple", "simple", 150)

        # Trigger save
        for i in range(10):
            tracker.track_event(EventType.QUERY, data={'test': i})

        session_file = Path(temp_analytics) / "session_content_test.json"
        with open(session_file, 'r') as f:
            data = json.load(f)

        assert 'session_id' in data
        assert 'events' in data
        assert 'stats' in data
        assert data['session_id'] == "content_test"

    def test_finalize_session(self, temp_analytics):
        """Test finalizing session saves data."""
        tracker = SessionTracker("finalize_test", storage_path=temp_analytics)
        tracker.track_query("test", "simple", "simple")
        tracker.finalize_session()

        session_file = Path(temp_analytics) / "session_finalize_test.json"
        assert session_file.exists()

    def test_aggregate_stats_created(self, temp_analytics):
        """Test aggregate stats file is created."""
        tracker = SessionTracker("agg_test", storage_path=temp_analytics)
        tracker.track_query("test", "simple", "simple")

        # Force save
        for i in range(10):
            tracker.track_event(EventType.QUERY, data={'test': i})

        agg_file = Path(temp_analytics) / "aggregate_stats.json"
        assert agg_file.exists()

    def test_aggregate_stats_content(self, temp_analytics):
        """Test aggregate stats contains expected data."""
        tracker = SessionTracker("agg_content_test", storage_path=temp_analytics)
        tracker.track_query("test", "simple", "simple")
        tracker.track_export("excel", 5)

        # Force save
        for i in range(10):
            tracker.track_event(EventType.QUERY, data={'test': i})

        agg_file = Path(temp_analytics) / "aggregate_stats.json"
        with open(agg_file, 'r') as f:
            data = json.load(f)

        assert 'total_sessions' in data
        assert 'total_queries' in data
        assert 'total_exports' in data
        assert data['total_sessions'] >= 1

    def test_aggregate_stats_accumulation(self, temp_analytics):
        """Test aggregate stats accumulate across sessions."""
        # First session
        tracker1 = SessionTracker("agg_sess1", storage_path=temp_analytics)
        tracker1.track_query("query1", "simple", "simple")
        for i in range(10):
            tracker1.track_event(EventType.QUERY, data={'test': i})

        # Second session
        tracker2 = SessionTracker("agg_sess2", storage_path=temp_analytics)
        tracker2.track_query("query2", "simple", "simple")
        tracker2.track_query("query3", "simple", "simple")
        for i in range(10):
            tracker2.track_event(EventType.QUERY, data={'test': i})

        agg_file = Path(temp_analytics) / "aggregate_stats.json"
        with open(agg_file, 'r') as f:
            data = json.load(f)

        # Should have accumulated from both sessions
        assert data['total_sessions'] >= 2
        assert data['total_queries'] >= 3  # 1 from first + 2 from second


class TestGetAggregateStats:
    """Tests for class method get_aggregate_stats."""

    def test_get_aggregate_stats_exists(self, temp_analytics):
        """Test getting aggregate stats when file exists."""
        # Create session to generate aggregate file
        tracker = SessionTracker("get_agg", storage_path=temp_analytics)
        tracker.track_query("test", "simple", "simple")
        for i in range(10):
            tracker.track_event(EventType.QUERY, data={'test': i})

        # Get aggregate stats via class method
        stats = SessionTracker.get_aggregate_stats(storage_path=temp_analytics)

        assert 'total_sessions' in stats
        assert 'total_queries' in stats
        assert stats['total_sessions'] >= 1

    def test_get_aggregate_stats_nonexistent(self, temp_analytics):
        """Test getting aggregate stats when file doesn't exist."""
        stats = SessionTracker.get_aggregate_stats(storage_path=temp_analytics)

        assert stats['total_sessions'] == 0
        assert stats['total_queries'] == 0
        assert 'message' in stats


class TestSessionStats:
    """Tests for SessionStats dataclass."""

    def test_session_stats_creation(self):
        """Test creating SessionStats."""
        stats = SessionStats(
            session_id="stats_test",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_queries=10,
            total_property_views=5,
            total_searches=3,
            total_exports=2,
            total_favorites=1,
            unique_models_used=["gpt-4o", "claude-3.5"],
            tools_used=["calculator", "comparator"],
            errors_encountered=0,
            total_duration_minutes=15.5
        )

        assert stats.session_id == "stats_test"
        assert stats.total_queries == 10
        assert stats.total_property_views == 5
        assert len(stats.unique_models_used) == 2
        assert len(stats.tools_used) == 2
        assert stats.total_duration_minutes == 15.5


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_session(self, session_tracker):
        """Test session with no events."""
        stats = session_tracker.get_session_stats()

        assert stats.total_queries == 0
        assert stats.total_property_views == 0
        assert stats.total_exports == 0
        assert len(stats.unique_models_used) == 0
        assert len(stats.tools_used) == 0

    def test_very_long_session_id(self, temp_analytics):
        """Test with very long session ID."""
        long_id = "x" * 200
        tracker = SessionTracker(long_id, storage_path=temp_analytics)
        tracker.track_query("test", "simple", "simple")

        stats = tracker.get_session_stats()
        assert stats.session_id == long_id

    def test_special_characters_in_data(self, session_tracker):
        """Test tracking events with special characters."""
        session_tracker.track_query(
            query="Test with special chars: <>&\"'",
            intent="test",
            complexity="simple"
        )

        event = session_tracker.events[0]
        assert "<>&\"'" in event.data['query']

    def test_large_data_payload(self, session_tracker):
        """Test tracking event with large data payload."""
        large_data = {'data': 'x' * 10000}  # 10KB of data
        session_tracker.track_event(EventType.SEARCH, data=large_data)

        assert len(session_tracker.events) == 1

    def test_many_events(self, session_tracker):
        """Test tracking many events."""
        for i in range(100):
            session_tracker.track_query(f"query_{i}", "simple", "simple", i)

        assert len(session_tracker.events) == 100
        stats = session_tracker.get_session_stats()
        assert stats.total_queries == 100

    def test_session_duration_calculation(self, session_tracker):
        """Test session duration is calculated correctly."""
        import time

        # Track initial event
        session_tracker.track_query("first", "simple", "simple")

        # Wait a bit
        time.sleep(0.1)

        # Track another event
        session_tracker.track_query("second", "simple", "simple")

        stats = session_tracker.get_session_stats()
        # Duration should be > 0
        assert stats.total_duration_minutes > 0

    def test_none_values_in_optional_fields(self, session_tracker):
        """Test handling None values in optional fields."""
        session_tracker.track_query(
            query="test",
            intent=None,
            complexity=None,
            processing_time_ms=None
        )

        event = session_tracker.events[0]
        assert event.data['intent'] is None
        assert event.duration_ms is None
