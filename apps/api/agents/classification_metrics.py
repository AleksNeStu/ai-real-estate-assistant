"""
Classification metrics logging for query intent classification.

This module provides SQLite-based storage for classification quality metrics,
enabling analysis and improvement of the classification system.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.query_analyzer import Complexity, QueryIntent

# Default path for metrics database
METRICS_DB_PATH = Path("data/classification_metrics.db")


@dataclass
class ClassificationMetrics:
    """Metrics for a single classification event."""

    timestamp: datetime
    session_id: Optional[str]
    query: str
    query_length: int
    primary_intent: QueryIntent
    secondary_intents: List[QueryIntent]
    confidence: float
    complexity: Complexity
    processing_time_ms: float
    route_taken: str
    tools_used: List[str]
    user_feedback: Optional[str]
    language_detected: str
    ambiguity_signals: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "query": self.query,
            "query_length": self.query_length,
            "primary_intent": self.primary_intent.value,
            "secondary_intents": [i.value for i in self.secondary_intents],
            "confidence": self.confidence,
            "complexity": self.complexity.value,
            "processing_time_ms": self.processing_time_ms,
            "route_taken": self.route_taken,
            "tools_used": self.tools_used,
            "user_feedback": self.user_feedback,
            "language_detected": self.language_detected,
            "ambiguity_signals": self.ambiguity_signals,
        }


def _connect(db_path: Path) -> sqlite3.Connection:
    """Open the metrics database with the schema's foreign keys enforced.

    SQLite does not enforce foreign keys unless it is told to, and the
    pragma is per connection - so it has to be set on every one of them.
    This database declares no relations today; the rule is uniform so that
    adding one later does not silently come unenforced.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_metrics_db(db_path: Path = METRICS_DB_PATH) -> None:
    """Initialize the metrics database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = _connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS classification_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT,
            query TEXT NOT NULL,
            query_length INTEGER,
            primary_intent TEXT NOT NULL,
            secondary_intents TEXT,
            confidence REAL NOT NULL,
            complexity TEXT NOT NULL,
            processing_time_ms REAL,
            route_taken TEXT,
            tools_used TEXT,
            user_feedback TEXT,
            language_detected TEXT,
            ambiguity_signals TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON classification_metrics(timestamp)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_primary_intent
        ON classification_metrics(primary_intent)
    """)
    conn.commit()
    conn.close()


def log_classification_metrics(
    metrics: ClassificationMetrics, db_path: Path = METRICS_DB_PATH
) -> None:
    """Log classification metrics to the database."""
    conn = _connect(db_path)
    conn.execute(
        """
        INSERT INTO classification_metrics (
            timestamp, session_id, query, query_length, primary_intent,
            secondary_intents, confidence, complexity, processing_time_ms,
            route_taken, tools_used, user_feedback, language_detected,
            ambiguity_signals
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            metrics.timestamp.isoformat(),
            metrics.session_id,
            metrics.query,
            metrics.query_length,
            metrics.primary_intent.value,
            json.dumps([i.value for i in metrics.secondary_intents]),
            metrics.confidence,
            metrics.complexity.value,
            metrics.processing_time_ms,
            metrics.route_taken,
            json.dumps(metrics.tools_used),
            metrics.user_feedback,
            metrics.language_detected,
            json.dumps(metrics.ambiguity_signals),
        ),
    )
    conn.commit()
    conn.close()


def get_classification_counts_by_intent(
    db_path: Path = METRICS_DB_PATH,
    days: int = 7,
) -> Dict[str, int]:
    """Get classification counts grouped by intent for the last N days."""
    cutoff = datetime.now() - timedelta(days=days)

    conn = _connect(db_path)
    cursor = conn.execute(
        """
        SELECT primary_intent, COUNT(*) as count
        FROM classification_metrics
        WHERE timestamp >= ?
        GROUP BY primary_intent
        ORDER BY count DESC
    """,
        (cutoff.isoformat(),),
    )

    result = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return result


def get_avg_confidence_by_intent(
    db_path: Path = METRICS_DB_PATH,
    days: int = 7,
) -> Dict[str, float]:
    """Get average confidence grouped by intent for the last N days."""
    cutoff = datetime.now() - timedelta(days=days)

    conn = _connect(db_path)
    cursor = conn.execute(
        """
        SELECT primary_intent, AVG(confidence) as avg_confidence
        FROM classification_metrics
        WHERE timestamp >= ?
        GROUP BY primary_intent
        ORDER BY avg_confidence DESC
    """,
        (cutoff.isoformat(),),
    )

    result = {row[0]: round(row[1], 2) for row in cursor.fetchall()}
    conn.close()
    return result


def get_low_confidence_count(
    db_path: Path = METRICS_DB_PATH,
    threshold: float = 0.5,
    days: int = 7,
) -> int:
    """Get count of classifications below confidence threshold."""
    cutoff = datetime.now() - timedelta(days=days)

    conn = _connect(db_path)
    cursor = conn.execute(
        """
        SELECT COUNT(*)
        FROM classification_metrics
        WHERE timestamp >= ? AND confidence < ?
    """,
        (cutoff.isoformat(), threshold),
    )

    result = cursor.fetchone()[0]
    conn.close()
    return result  # type: ignore[no-any-return]


def cleanup_old_metrics(
    db_path: Path = METRICS_DB_PATH,
    retention_days: int = 90,
) -> int:
    """Remove metrics older than retention period. Returns count deleted."""
    cutoff = datetime.now() - timedelta(days=retention_days)

    conn = _connect(db_path)
    cursor = conn.execute(
        "DELETE FROM classification_metrics WHERE timestamp < ?",
        (cutoff.isoformat(),),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_metrics_summary(
    db_path: Path = METRICS_DB_PATH,
    days: int = 7,
) -> Dict[str, Any]:
    """Get a comprehensive summary of classification metrics."""
    return {
        "counts_by_intent": get_classification_counts_by_intent(db_path, days),
        "avg_confidence_by_intent": get_avg_confidence_by_intent(db_path, days),
        "low_confidence_count": get_low_confidence_count(db_path, days=days),
        "period_days": days,
    }
