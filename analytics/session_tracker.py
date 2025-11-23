"""
Session analytics and usage tracking.

Tracks user interactions, queries, and behavior patterns to improve
the user experience and understand usage patterns.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import json
from pathlib import Path
from collections import Counter


class EventType(str, Enum):
    """Types of tracked events."""
    QUERY = "query"
    PROPERTY_VIEW = "property_view"
    SEARCH = "search"
    EXPORT = "export"
    FAVORITE = "favorite"
    MODEL_CHANGE = "model_change"
    TOOL_USE = "tool_use"
    ERROR = "error"


class SessionEvent(BaseModel):
    """A single tracked event."""
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[int] = None


class SessionStats(BaseModel):
    """Statistics for a session."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_queries: int = 0
    total_property_views: int = 0
    total_searches: int = 0
    total_exports: int = 0
    total_favorites: int = 0
    unique_models_used: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    errors_encountered: int = 0
    total_duration_minutes: Optional[float] = None


class SessionTracker:
    """
    Tracks user interactions and session analytics.

    Provides insights into user behavior, popular features,
    and usage patterns.
    """

    def __init__(
        self,
        session_id: str,
        storage_path: str = ".analytics"
    ):
        """
        Initialize session tracker.

        Args:
            session_id: Unique session identifier
            storage_path: Path to store analytics data
        """
        self.session_id = session_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        self.session_file = self.storage_path / f"session_{session_id}.json"
        self.aggregate_file = self.storage_path / "aggregate_stats.json"

        self.events: List[SessionEvent] = []
        self.session_start = datetime.now()

    def track_event(
        self,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None
    ):
        """
        Track a user event.

        Args:
            event_type: Type of event
            data: Optional event data
            duration_ms: Optional event duration in milliseconds
        """
        event = SessionEvent(
            event_type=event_type,
            data=data or {},
            duration_ms=duration_ms
        )
        self.events.append(event)

        # Auto-save periodically (every 10 events)
        if len(self.events) % 10 == 0:
            self._save_session()

    def track_query(
        self,
        query: str,
        intent: Optional[str] = None,
        complexity: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ):
        """Track a user query."""
        self.track_event(
            EventType.QUERY,
            data={
                'query': query,
                'intent': intent,
                'complexity': complexity
            },
            duration_ms=processing_time_ms
        )

    def track_property_view(
        self,
        property_id: str,
        property_city: Optional[str] = None,
        property_price: Optional[float] = None
    ):
        """Track a property view."""
        self.track_event(
            EventType.PROPERTY_VIEW,
            data={
                'property_id': property_id,
                'city': property_city,
                'price': property_price
            }
        )

    def track_search(
        self,
        search_criteria: Dict[str, Any],
        results_count: int
    ):
        """Track a search operation."""
        self.track_event(
            EventType.SEARCH,
            data={
                'criteria': search_criteria,
                'results_count': results_count
            }
        )

    def track_export(
        self,
        format: str,
        property_count: int
    ):
        """Track an export operation."""
        self.track_event(
            EventType.EXPORT,
            data={
                'format': format,
                'property_count': property_count
            }
        )

    def track_favorite(
        self,
        property_id: str,
        action: str  # "add" or "remove"
    ):
        """Track a favorite operation."""
        self.track_event(
            EventType.FAVORITE,
            data={
                'property_id': property_id,
                'action': action
            }
        )

    def track_model_change(
        self,
        old_model: Optional[str],
        new_model: str
    ):
        """Track a model change."""
        self.track_event(
            EventType.MODEL_CHANGE,
            data={
                'old_model': old_model,
                'new_model': new_model
            }
        )

    def track_tool_use(
        self,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """Track tool usage."""
        self.track_event(
            EventType.TOOL_USE,
            data={
                'tool_name': tool_name,
                'parameters': parameters
            }
        )

    def track_error(
        self,
        error_type: str,
        error_message: str
    ):
        """Track an error."""
        self.track_event(
            EventType.ERROR,
            data={
                'error_type': error_type,
                'error_message': error_message
            }
        )

    def get_session_stats(self) -> SessionStats:
        """
        Get statistics for current session.

        Returns:
            SessionStats with aggregated metrics
        """
        query_events = [e for e in self.events if e.event_type == EventType.QUERY]
        property_view_events = [e for e in self.events if e.event_type == EventType.PROPERTY_VIEW]
        search_events = [e for e in self.events if e.event_type == EventType.SEARCH]
        export_events = [e for e in self.events if e.event_type == EventType.EXPORT]
        favorite_events = [e for e in self.events if e.event_type == EventType.FAVORITE]
        model_change_events = [e for e in self.events if e.event_type == EventType.MODEL_CHANGE]
        tool_events = [e for e in self.events if e.event_type == EventType.TOOL_USE]
        error_events = [e for e in self.events if e.event_type == EventType.ERROR]

        # Unique models used
        models = [e.data.get('new_model') for e in model_change_events if e.data.get('new_model')]
        unique_models = list(set(models))

        # Tools used
        tools = [e.data.get('tool_name') for e in tool_events if e.data.get('tool_name')]

        # Calculate duration
        session_end = self.events[-1].timestamp if self.events else datetime.now()
        duration_minutes = (session_end - self.session_start).total_seconds() / 60
        if self.events and duration_minutes <= 0:
            duration_minutes = 0.01

        return SessionStats(
            session_id=self.session_id,
            start_time=self.session_start,
            end_time=session_end,
            total_queries=len(query_events),
            total_property_views=len(property_view_events),
            total_searches=len(search_events),
            total_exports=len(export_events),
            total_favorites=len(favorite_events),
            unique_models_used=unique_models,
            tools_used=tools,
            errors_encountered=len(error_events),
            total_duration_minutes=duration_minutes
        )

    def get_popular_queries(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Get most common query patterns.

        Args:
            top_n: Number of top queries to return

        Returns:
            List of query statistics
        """
        query_events = [e for e in self.events if e.event_type == EventType.QUERY]

        # Group by intent
        intents = [e.data.get('intent') for e in query_events if e.data.get('intent')]
        intent_counts = Counter(intents)

        return [
            {'intent': intent, 'count': count}
            for intent, count in intent_counts.most_common(top_n)
        ]

    def get_avg_processing_time(self, event_type: EventType) -> Optional[float]:
        """
        Get average processing time for event type.

        Args:
            event_type: Type of event

        Returns:
            Average duration in milliseconds or None
        """
        events = [e for e in self.events if e.event_type == event_type and e.duration_ms is not None]

        if not events:
            return None

        return sum(e.duration_ms for e in events) / len(events)

    def _save_session(self):
        """Save session data to disk."""
        session_data = {
            'session_id': self.session_id,
            'session_start': self.session_start.isoformat(),
            'events': [
                {
                    'event_type': e.event_type.value,
                    'timestamp': e.timestamp.isoformat(),
                    'data': e.data,
                    'duration_ms': e.duration_ms
                }
                for e in self.events
            ],
            'stats': self.get_session_stats().dict()
        }

        with open(self.session_file, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)

        # Update aggregate stats
        self._update_aggregate_stats()

    def _update_aggregate_stats(self):
        """Update aggregate statistics across all sessions."""
        # Load existing aggregate stats
        if self.aggregate_file.exists():
            with open(self.aggregate_file, 'r') as f:
                aggregate = json.load(f)
        else:
            aggregate = {
                'total_sessions': 0,
                'total_queries': 0,
                'total_property_views': 0,
                'total_exports': 0,
                'popular_intents': {},
                'popular_tools': {},
                'last_updated': None
            }

        # Update with current session
        stats = self.get_session_stats()
        aggregate['total_sessions'] += 1
        aggregate['total_queries'] += stats.total_queries
        aggregate['total_property_views'] += stats.total_property_views
        aggregate['total_exports'] += stats.total_exports

        # Update popular intents
        for query_stat in self.get_popular_queries(top_n=100):
            intent = query_stat['intent']
            aggregate['popular_intents'][intent] = aggregate['popular_intents'].get(intent, 0) + query_stat['count']

        # Update popular tools
        for tool in stats.tools_used:
            aggregate['popular_tools'][tool] = aggregate['popular_tools'].get(tool, 0) + 1

        aggregate['last_updated'] = datetime.now().isoformat()

        # Save aggregate
        with open(self.aggregate_file, 'w') as f:
            json.dump(aggregate, f, indent=2, default=str)

    def finalize_session(self):
        """Finalize and save the session."""
        self._save_session()

    @classmethod
    def get_aggregate_stats(cls, storage_path: str = ".analytics") -> Dict[str, Any]:
        """
        Get aggregate statistics across all sessions.

        Args:
            storage_path: Path where analytics are stored

        Returns:
            Dictionary with aggregate statistics
        """
        aggregate_file = Path(storage_path) / "aggregate_stats.json"

        if not aggregate_file.exists():
            return {
                'total_sessions': 0,
                'total_queries': 0,
                'message': 'No analytics data available yet'
            }

        with open(aggregate_file, 'r') as f:
            return json.load(f)
