"""
Enrichment Status Tracking (Task #78).

This module provides status tracking and fallback handling for enrichment
operations.

Features:
- Per-property enrichment status tracking
- Fallback value management
- Error recovery strategies
- Status history for debugging
"""

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.security_utils import sanitize_for_log
from data.enrichment.hooks import EnrichmentResult, EnrichmentStatus

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentStatusEntry:
    """Entry tracking enrichment status for a property."""

    property_id: str
    source: str
    enrichment_field: str
    status: EnrichmentStatus
    value: Any = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    attempts: int = 1
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "property_id": self.property_id,
            "source": self.source,
            "field": self.enrichment_field,
            "status": self.status.value,
            "value": self.value,
            "error": self.error,
            "timestamp": self.timestamp,
            "attempts": self.attempts,
            "execution_time_ms": self.execution_time_ms,
        }


class EnrichmentStatusTracker:
    """
    Tracks enrichment status for properties.

    Maintains status history for debugging and monitoring.
    Thread-safe implementation.
    """

    def __init__(self, max_history: int = 10000):
        """
        Initialize status tracker.

        Args:
            max_history: Maximum number of status entries to retain
        """
        self._status: Dict[str, Dict[str, EnrichmentStatusEntry]] = defaultdict(dict)
        self._history: List[EnrichmentStatusEntry] = []
        self._max_history = max_history
        self._lock = threading.RLock()

    def update(self, result: EnrichmentResult, property_id: str) -> None:
        """
        Update status from enrichment result.

        Args:
            result: Enrichment result
            property_id: Property identifier
        """
        entry = EnrichmentStatusEntry(
            property_id=property_id,
            source=result.source,
            enrichment_field=result.enrichment_field,
            status=result.status,
            value=result.value,
            error=result.error,
            execution_time_ms=result.execution_time_ms,
        )

        with self._lock:
            key = f"{result.source}:{result.enrichment_field}"
            existing = self._status[property_id].get(key)

            if existing:
                entry.attempts = existing.attempts + 1

            self._status[property_id][key] = entry
            self._history.append(entry)

            # Trim history if needed
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

    def get_status(
        self,
        property_id: str,
        source: Optional[str] = None,
        field: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get enrichment status for a property.

        Args:
            property_id: Property identifier
            source: Optional source filter
            field: Optional field filter

        Returns:
            Dictionary with status information
        """
        with self._lock:
            property_status = self._status.get(property_id, {})

            if source and field:
                key = f"{source}:{field}"
                entry = property_status.get(key)
                return entry.to_dict() if entry else {}

            if source:
                filtered = {k: v for k, v in property_status.items() if v.source == source}
            elif field:
                filtered = {k: v for k, v in property_status.items() if v.enrichment_field == field}
            else:
                filtered = property_status

            return {
                "property_id": property_id,
                "enrichments": {k: v.to_dict() for k, v in filtered.items()},
                "summary": self._summarize(filtered),
            }

    def _summarize(
        self,
        entries: Dict[str, EnrichmentStatusEntry],
    ) -> Dict[str, Any]:
        """Generate summary statistics."""
        if not entries:
            return {"total": 0}

        status_counts: Dict[str, int] = defaultdict(int)
        total_time = 0.0

        for entry in entries.values():
            status_counts[entry.status.value] += 1
            total_time += entry.execution_time_ms

        return {
            "total": len(entries),
            "status_counts": dict(status_counts),
            "avg_execution_time_ms": total_time / len(entries) if entries else 0,
        }

    def get_pending(self, property_id: str) -> List[str]:
        """
        Get list of pending enrichments for a property.

        Args:
            property_id: Property identifier

        Returns:
            List of pending source:field keys
        """
        with self._lock:
            property_status = self._status.get(property_id, {})
            return [
                f"{v.source}:{v.enrichment_field}"
                for v in property_status.values()
                if v.status in {EnrichmentStatus.PENDING, EnrichmentStatus.IN_PROGRESS}
            ]

    def get_failed(self, property_id: str) -> List[EnrichmentStatusEntry]:
        """
        Get failed enrichments for a property.

        Args:
            property_id: Property identifier

        Returns:
            List of failed entries
        """
        with self._lock:
            property_status = self._status.get(property_id, {})
            return [v for v in property_status.values() if v.status == EnrichmentStatus.FAILED]

    def clear_property(self, property_id: str) -> None:
        """Clear status for a property."""
        with self._lock:
            if property_id in self._status:
                del self._status[property_id]

    def clear_all(self) -> None:
        """Clear all status entries."""
        with self._lock:
            self._status.clear()
            self._history.clear()

    def get_history(
        self,
        property_id: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get enrichment history.

        Args:
            property_id: Optional property filter
            source: Optional source filter
            limit: Maximum entries to return

        Returns:
            List of history entries
        """
        with self._lock:
            history = self._history

            if property_id:
                history = [e for e in history if e.property_id == property_id]
            if source:
                history = [e for e in history if e.source == source]

            return [e.to_dict() for e in history[-limit:]]


class FallbackHandler:
    """
    Handles fallback behavior for failed enrichments.

    Provides strategies for graceful degradation when enrichment sources fail.
    """

    def __init__(
        self,
        default_fallbacks: Optional[Dict[str, Any]] = None,
        custom_handlers: Optional[Dict[str, Callable[[], Any]]] = None,
    ):
        """
        Initialize fallback handler.

        Args:
            default_fallbacks: Default fallback values by field
            custom_handlers: Custom fallback generators by field
        """
        self._default_fallbacks = default_fallbacks or {}
        self._custom_handlers = custom_handlers or {}
        self._failure_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()

    def get_fallback(
        self,
        source: str,
        field: str,
        error: Optional[str] = None,
    ) -> Any:
        """
        Get fallback value for failed enrichment.

        Args:
            source: Enrichment source name
            field: Field name
            error: Error message (for logging)

        Returns:
            Fallback value
        """
        # Track failure
        with self._lock:
            key = f"{source}:{field}"
            self._failure_counts[key] += 1

        logger.warning(
            "Using fallback for %s:%s - error: %s",
            sanitize_for_log(source),
            sanitize_for_log(field),
            sanitize_for_log(error),
        )

        # Try custom handler first
        if field in self._custom_handlers:
            try:
                return self._custom_handlers[field]()
            except Exception as e:
                logger.error(
                    "Custom fallback handler failed for %s: %s",
                    sanitize_for_log(field),
                    sanitize_for_log(e),
                )

        # Use default fallback
        if field in self._default_fallbacks:
            return self._default_fallbacks[field]

        # Return None as ultimate fallback
        return None

    def register_fallback(
        self,
        field: str,
        value: Any,
    ) -> None:
        """
        Register a fallback value for a field.

        Args:
            field: Field name
            value: Fallback value
        """
        self._default_fallbacks[field] = value

    def register_handler(
        self,
        field: str,
        handler: Callable[[], Any],
    ) -> None:
        """
        Register a custom fallback handler for a field.

        Args:
            field: Field name
            handler: Function that returns fallback value
        """
        self._custom_handlers[field] = handler

    def get_failure_count(self, source: str, field: str) -> int:
        """Get failure count for a source:field."""
        with self._lock:
            return self._failure_counts.get(f"{source}:{field}", 0)

    def reset_counts(self) -> None:
        """Reset failure counts."""
        with self._lock:
            self._failure_counts.clear()


# Global instances
_status_tracker: Optional[EnrichmentStatusTracker] = None
_fallback_handler: Optional[FallbackHandler] = None
_tracker_lock = threading.Lock()


def get_status_tracker() -> EnrichmentStatusTracker:
    """Get the global status tracker instance."""
    global _status_tracker
    if _status_tracker is None:
        with _tracker_lock:
            if _status_tracker is None:
                _status_tracker = EnrichmentStatusTracker()
    return _status_tracker


def get_fallback_handler() -> FallbackHandler:
    """Get the global fallback handler instance."""
    global _fallback_handler
    if _fallback_handler is None:
        with _tracker_lock:
            if _fallback_handler is None:
                # Initialize with sensible defaults
                _fallback_handler = FallbackHandler(
                    default_fallbacks={
                        "air_quality_index": None,
                        "noise_level": None,
                        "safety_score": None,
                        "transport_score": None,
                        "neighborhood_score": None,
                    }
                )
    return _fallback_handler
