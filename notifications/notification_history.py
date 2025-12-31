"""
Notification history tracking and analytics.

Handles:
- Recording sent notifications
- Delivery status tracking
- User notification statistics
- Failure tracking and retry queue
- Notification analytics
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class NotificationStatus(str, Enum):
    """Status of a notification."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"


class NotificationType(str, Enum):
    """Types of notifications."""
    PRICE_DROP = "price_drop"
    NEW_PROPERTY = "new_property"
    SAVED_SEARCH = "saved_search"
    MARKET_UPDATE = "market_update"
    DIGEST_DAILY = "digest_daily"
    DIGEST_WEEKLY = "digest_weekly"
    TEST = "test"


@dataclass
class NotificationRecord:
    """
    Record of a sent notification.

    Attributes:
        id: Unique identifier for the notification
        user_email: Recipient email
        notification_type: Type of notification
        subject: Email subject
        status: Current delivery status
        sent_at: When notification was sent
        delivered_at: When notification was delivered
        opened_at: When notification was opened
        clicked_at: When notification was clicked
        failed_at: When notification failed
        error_message: Error message if failed
        metadata: Additional metadata (property_id, search_id, etc.)
        retry_count: Number of retry attempts
    """
    id: str
    user_email: str
    notification_type: NotificationType
    subject: str
    status: NotificationStatus = NotificationStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['notification_type'] = self.notification_type.value
        data['status'] = self.status.value

        # Convert datetime to ISO format
        for field_name in ['sent_at', 'delivered_at', 'opened_at', 'clicked_at', 'failed_at', 'created_at']:
            if data[field_name]:
                data[field_name] = data[field_name].isoformat()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationRecord':
        """Create from dictionary."""
        # Convert enums
        if 'notification_type' in data:
            data['notification_type'] = NotificationType(data['notification_type'])
        if 'status' in data:
            data['status'] = NotificationStatus(data['status'])

        # Convert datetime strings
        for field_name in ['sent_at', 'delivered_at', 'opened_at', 'clicked_at', 'failed_at', 'created_at']:
            if data.get(field_name) and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])

        return cls(**data)


class NotificationHistory:
    """
    Manager for notification history and analytics.

    Tracks all sent notifications and provides statistics.
    """

    def __init__(self, storage_path: str = ".notifications"):
        """
        Initialize notification history manager.

        Args:
            storage_path: Directory to store history files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        self.history_file = self.storage_path / "notification_history.json"
        self.failed_queue_file = self.storage_path / "failed_notifications.json"

        self._history: Dict[str, NotificationRecord] = {}
        self._failed_queue: List[NotificationRecord] = []

        self._load_history()
        self._load_failed_queue()

    def record_notification(
        self,
        user_email: str,
        notification_type: NotificationType,
        subject: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationRecord:
        """
        Record a new notification.

        Args:
            user_email: Recipient email
            notification_type: Type of notification
            subject: Email subject
            metadata: Additional metadata

        Returns:
            NotificationRecord
        """
        # Generate unique ID
        notification_id = f"{notification_type.value}_{user_email}_{datetime.now().timestamp()}"

        record = NotificationRecord(
            id=notification_id,
            user_email=user_email,
            notification_type=notification_type,
            subject=subject,
            metadata=metadata or {}
        )

        self._history[notification_id] = record
        self._save_history()

        return record

    def mark_sent(self, notification_id: str):
        """Mark notification as sent."""
        if notification_id in self._history:
            self._history[notification_id].status = NotificationStatus.SENT
            self._history[notification_id].sent_at = datetime.now()
            self._save_history()

    def mark_delivered(self, notification_id: str):
        """Mark notification as delivered."""
        if notification_id in self._history:
            self._history[notification_id].status = NotificationStatus.DELIVERED
            self._history[notification_id].delivered_at = datetime.now()
            self._save_history()

    def mark_opened(self, notification_id: str):
        """Mark notification as opened."""
        if notification_id in self._history:
            self._history[notification_id].status = NotificationStatus.OPENED
            self._history[notification_id].opened_at = datetime.now()
            self._save_history()

    def mark_clicked(self, notification_id: str):
        """Mark notification link as clicked."""
        if notification_id in self._history:
            self._history[notification_id].status = NotificationStatus.CLICKED
            self._history[notification_id].clicked_at = datetime.now()
            self._save_history()

    def mark_failed(
        self,
        notification_id: str,
        error_message: str,
        add_to_retry_queue: bool = True
    ):
        """
        Mark notification as failed.

        Args:
            notification_id: Notification ID
            error_message: Error message
            add_to_retry_queue: Whether to add to retry queue
        """
        if notification_id in self._history:
            record = self._history[notification_id]
            record.status = NotificationStatus.FAILED
            record.failed_at = datetime.now()
            record.error_message = error_message
            record.retry_count += 1

            if add_to_retry_queue and record.retry_count < 3:
                self._failed_queue.append(record)
                self._save_failed_queue()

            self._save_history()

    def get_notification(self, notification_id: str) -> Optional[NotificationRecord]:
        """Get notification record by ID."""
        return self._history.get(notification_id)

    def get_user_notifications(
        self,
        user_email: str,
        limit: Optional[int] = None,
        notification_type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None
    ) -> List[NotificationRecord]:
        """
        Get notifications for a user.

        Args:
            user_email: User's email
            limit: Maximum number of records to return
            notification_type: Filter by type
            status: Filter by status

        Returns:
            List of notification records
        """
        records = [
            record for record in self._history.values()
            if record.user_email == user_email
        ]

        # Apply filters
        if notification_type:
            records = [r for r in records if r.notification_type == notification_type]

        if status:
            records = [r for r in records if r.status == status]

        # Sort by creation date (newest first)
        records.sort(key=lambda x: x.created_at, reverse=True)

        if limit:
            records = records[:limit]

        return records

    def get_recent_notifications(
        self,
        days: int = 7,
        limit: Optional[int] = None
    ) -> List[NotificationRecord]:
        """
        Get recent notifications.

        Args:
            days: Number of days to look back
            limit: Maximum number of records

        Returns:
            List of notification records
        """
        cutoff = datetime.now() - timedelta(days=days)

        records = [
            record for record in self._history.values()
            if record.created_at >= cutoff
        ]

        records.sort(key=lambda x: x.created_at, reverse=True)

        if limit:
            records = records[:limit]

        return records

    def get_failed_notifications(self) -> List[NotificationRecord]:
        """Get all failed notifications from retry queue."""
        return self._failed_queue.copy()

    def remove_from_retry_queue(self, notification_id: str):
        """Remove notification from retry queue."""
        self._failed_queue = [
            n for n in self._failed_queue
            if n.id != notification_id
        ]
        self._save_failed_queue()

    def get_user_statistics(self, user_email: str) -> Dict[str, Any]:
        """
        Get notification statistics for a user.

        Args:
            user_email: User's email

        Returns:
            Dictionary with statistics
        """
        user_records = self.get_user_notifications(user_email)

        if not user_records:
            return {
                'total_sent': 0,
                'total_delivered': 0,
                'total_opened': 0,
                'total_clicked': 0,
                'total_failed': 0,
                'delivery_rate': 0.0,
                'open_rate': 0.0,
                'click_rate': 0.0,
                'by_type': {}
            }

        total = len(user_records)
        delivered = sum(1 for r in user_records if r.status in [
            NotificationStatus.DELIVERED,
            NotificationStatus.OPENED,
            NotificationStatus.CLICKED
        ])
        opened = sum(1 for r in user_records if r.status in [
            NotificationStatus.OPENED,
            NotificationStatus.CLICKED
        ])
        clicked = sum(1 for r in user_records if r.status == NotificationStatus.CLICKED)
        failed = sum(1 for r in user_records if r.status == NotificationStatus.FAILED)

        # Count by type
        by_type = defaultdict(int)
        for record in user_records:
            by_type[record.notification_type.value] += 1

        return {
            'total_sent': total,
            'total_delivered': delivered,
            'total_opened': opened,
            'total_clicked': clicked,
            'total_failed': failed,
            'delivery_rate': (delivered / total * 100) if total > 0 else 0.0,
            'open_rate': (opened / delivered * 100) if delivered > 0 else 0.0,
            'click_rate': (clicked / delivered * 100) if delivered > 0 else 0.0,
            'by_type': dict(by_type)
        }

    def get_overall_statistics(self) -> Dict[str, Any]:
        """
        Get overall notification statistics.

        Returns:
            Dictionary with overall statistics
        """
        all_records = list(self._history.values())

        if not all_records:
            return {
                'total_notifications': 0,
                'total_users': 0,
                'total_delivered': 0,
                'total_opened': 0,
                'total_clicked': 0,
                'total_failed': 0,
                'delivery_rate': 0.0,
                'open_rate': 0.0,
                'click_rate': 0.0,
                'by_type': {},
                'by_status': {}
            }

        total = len(all_records)
        unique_users = len(set(r.user_email for r in all_records))

        delivered = sum(1 for r in all_records if r.status in [
            NotificationStatus.DELIVERED,
            NotificationStatus.OPENED,
            NotificationStatus.CLICKED
        ])
        opened = sum(1 for r in all_records if r.status in [
            NotificationStatus.OPENED,
            NotificationStatus.CLICKED
        ])
        clicked = sum(1 for r in all_records if r.status == NotificationStatus.CLICKED)
        failed = sum(1 for r in all_records if r.status == NotificationStatus.FAILED)

        # Count by type
        by_type = defaultdict(int)
        for record in all_records:
            by_type[record.notification_type.value] += 1

        # Count by status
        by_status = defaultdict(int)
        for record in all_records:
            by_status[record.status.value] += 1

        return {
            'total_notifications': total,
            'total_users': unique_users,
            'total_delivered': delivered,
            'total_opened': opened,
            'total_clicked': clicked,
            'total_failed': failed,
            'delivery_rate': (delivered / total * 100) if total > 0 else 0.0,
            'open_rate': (opened / delivered * 100) if delivered > 0 else 0.0,
            'click_rate': (clicked / delivered * 100) if delivered > 0 else 0.0,
            'by_type': dict(by_type),
            'by_status': dict(by_status)
        }

    def cleanup_old_records(self, days: int = 90):
        """
        Remove notification records older than specified days.

        Args:
            days: Number of days to keep
        """
        cutoff = datetime.now() - timedelta(days=days)

        self._history = {
            id: record for id, record in self._history.items()
            if record.created_at >= cutoff
        }

        self._save_history()

    def _load_history(self):
        """Load notification history from disk."""
        if not self.history_file.exists():
            return

        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)

            for notification_id, record_data in data.items():
                record = NotificationRecord.from_dict(record_data)
                self._history[notification_id] = record

        except Exception as e:
            logger.warning("Error loading notification history: %s", e)

    def _save_history(self):
        """Save notification history to disk."""
        data = {
            id: record.to_dict()
            for id, record in self._history.items()
        }

        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_failed_queue(self):
        """Load failed notifications queue from disk."""
        if not self.failed_queue_file.exists():
            return

        try:
            with open(self.failed_queue_file, 'r') as f:
                data = json.load(f)

            self._failed_queue = [
                NotificationRecord.from_dict(record_data)
                for record_data in data
            ]

        except Exception as e:
            logger.warning("Error loading failed queue: %s", e)

    def _save_failed_queue(self):
        """Save failed notifications queue to disk."""
        data = [record.to_dict() for record in self._failed_queue]

        with open(self.failed_queue_file, 'w') as f:
            json.dump(data, f, indent=2)
