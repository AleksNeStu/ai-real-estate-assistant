"""
Notification preferences management.

Handles:
- User notification preferences (frequency, alert types, thresholds)
- Quiet hours enforcement
- Alert frequency control (instant, daily, weekly)
- Per-search notification settings
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, time
from enum import Enum
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class AlertFrequency(str, Enum):
    """Alert delivery frequency options."""
    INSTANT = "instant"  # Send immediately when triggered
    HOURLY = "hourly"    # Batch and send hourly
    DAILY = "daily"      # Daily digest at specified time
    WEEKLY = "weekly"    # Weekly digest on specified day


class AlertType(str, Enum):
    """Types of alerts that can be enabled/disabled."""
    PRICE_DROP = "price_drop"
    NEW_PROPERTY = "new_property"
    SAVED_SEARCH_MATCH = "saved_search_match"
    MARKET_UPDATE = "market_update"
    DIGEST = "digest"


class DigestDay(str, Enum):
    """Days of week for weekly digests."""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


@dataclass
class NotificationPreferences:
    """
    User notification preferences.

    Attributes:
        user_email: User's email address
        alert_frequency: How often to send alerts
        enabled_alerts: Types of alerts user wants to receive
        price_drop_threshold: Minimum % price drop to trigger alert (default 5%)
        quiet_hours_start: Start of quiet hours (no alerts sent)
        quiet_hours_end: End of quiet hours
        daily_digest_time: Time to send daily digest (24-hour format)
        weekly_digest_day: Day to send weekly digest
        max_alerts_per_day: Maximum alerts to send per day
        per_search_settings: Custom settings for specific saved searches
        enabled: Whether notifications are enabled at all
    """
    user_email: str
    alert_frequency: AlertFrequency = AlertFrequency.INSTANT
    enabled_alerts: Set[AlertType] = field(default_factory=lambda: {
        AlertType.PRICE_DROP,
        AlertType.NEW_PROPERTY,
        AlertType.SAVED_SEARCH_MATCH
    })
    price_drop_threshold: float = 5.0  # Minimum % drop
    quiet_hours_start: Optional[str] = "22:00"  # 10 PM
    quiet_hours_end: Optional[str] = "08:00"    # 8 AM
    daily_digest_time: str = "09:00"  # 9 AM
    weekly_digest_day: DigestDay = DigestDay.MONDAY
    max_alerts_per_day: int = 10
    per_search_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary for serialization."""
        data = asdict(self)
        # Convert sets to lists for JSON serialization
        data['enabled_alerts'] = [alert.value for alert in self.enabled_alerts]
        data['alert_frequency'] = self.alert_frequency.value
        data['weekly_digest_day'] = self.weekly_digest_day.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationPreferences':
        """Create preferences from dictionary."""
        # Convert alert types back to set
        if 'enabled_alerts' in data:
            data['enabled_alerts'] = {AlertType(a) for a in data['enabled_alerts']}

        # Convert enums
        if 'alert_frequency' in data:
            data['alert_frequency'] = AlertFrequency(data['alert_frequency'])

        if 'weekly_digest_day' in data:
            data['weekly_digest_day'] = DigestDay(data['weekly_digest_day'])

        # Convert datetime strings
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])

        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        return cls(**data)

    def is_alert_enabled(self, alert_type: AlertType) -> bool:
        """Check if a specific alert type is enabled."""
        return self.enabled and alert_type in self.enabled_alerts

    def is_in_quiet_hours(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if current time is in quiet hours.

        Args:
            check_time: Time to check (defaults to now)

        Returns:
            True if in quiet hours
        """
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False

        if check_time is None:
            check_time = datetime.now()

        current_time = check_time.time()
        start = datetime.strptime(self.quiet_hours_start, "%H:%M").time()
        end = datetime.strptime(self.quiet_hours_end, "%H:%M").time()

        # Handle quiet hours that span midnight
        if start <= end:
            return start <= current_time <= end
        else:
            return current_time >= start or current_time <= end

    def should_send_alert(
        self,
        alert_type: AlertType,
        alerts_sent_today: int = 0,
        check_time: Optional[datetime] = None
    ) -> bool:
        """
        Determine if an alert should be sent based on preferences.

        Args:
            alert_type: Type of alert to send
            alerts_sent_today: Number of alerts already sent today
            check_time: Time to check (defaults to now)

        Returns:
            True if alert should be sent
        """
        # Check if notifications enabled
        if not self.enabled:
            return False

        # Check if this alert type is enabled
        if not self.is_alert_enabled(alert_type):
            return False

        # Respect quiet hours only for non-instant delivery modes
        if self.alert_frequency != AlertFrequency.INSTANT and self.is_in_quiet_hours(check_time):
            return False

        # Check daily limit
        if alerts_sent_today >= self.max_alerts_per_day:
            return False

        # For digest alerts, check if it's time
        if alert_type == AlertType.DIGEST:
            if self.alert_frequency == AlertFrequency.WEEKLY:
                # Check if today is the digest day
                if check_time is None:
                    check_time = datetime.now()
                current_day = check_time.strftime("%A").lower()
                return current_day == self.weekly_digest_day.value

        return True

    def get_search_preferences(self, search_id: str) -> Dict[str, Any]:
        """
        Get preferences for a specific saved search.

        Args:
            search_id: ID of the saved search

        Returns:
            Dictionary of search-specific preferences
        """
        return self.per_search_settings.get(search_id, {})

    def set_search_preferences(
        self,
        search_id: str,
        enabled: Optional[bool] = None,
        alert_frequency: Optional[AlertFrequency] = None,
        price_threshold: Optional[float] = None
    ):
        """
        Set preferences for a specific saved search.

        Args:
            search_id: ID of the saved search
            enabled: Whether alerts are enabled for this search
            alert_frequency: Custom frequency for this search
            price_threshold: Custom price drop threshold
        """
        if search_id not in self.per_search_settings:
            self.per_search_settings[search_id] = {}

        if enabled is not None:
            self.per_search_settings[search_id]['enabled'] = enabled

        if alert_frequency is not None:
            self.per_search_settings[search_id]['alert_frequency'] = alert_frequency.value

        if price_threshold is not None:
            self.per_search_settings[search_id]['price_threshold'] = price_threshold

        self.updated_at = datetime.now()


class NotificationPreferencesManager:
    """
    Manager for storing and retrieving notification preferences.

    Handles persistence of user preferences to disk.
    """

    def __init__(self, storage_path: str = ".preferences"):
        """
        Initialize preferences manager.

        Args:
            storage_path: Directory to store preference files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        self.preferences_file = self.storage_path / "notification_preferences.json"
        self._preferences_cache: Dict[str, NotificationPreferences] = {}

        self._load_all_preferences()

    def get_preferences(self, user_email: str) -> NotificationPreferences:
        """
        Get preferences for a user.

        Args:
            user_email: User's email address

        Returns:
            User's notification preferences (creates defaults if not found)
        """
        if user_email not in self._preferences_cache:
            # Create default preferences
            prefs = NotificationPreferences(user_email=user_email)
            self._preferences_cache[user_email] = prefs
            self.save_preferences(prefs)

        return self._preferences_cache[user_email]

    def save_preferences(self, preferences: NotificationPreferences):
        """
        Save user preferences.

        Args:
            preferences: Preferences to save
        """
        preferences.updated_at = datetime.now()
        self._preferences_cache[preferences.user_email] = preferences
        self._save_all_preferences()

    def update_preferences(
        self,
        user_email: str,
        **kwargs
    ) -> NotificationPreferences:
        """
        Update specific preference fields for a user.

        Args:
            user_email: User's email address
            **kwargs: Fields to update

        Returns:
            Updated preferences
        """
        prefs = self.get_preferences(user_email)

        for key, value in kwargs.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)

        prefs.updated_at = datetime.now()
        self.save_preferences(prefs)

        return prefs

    def delete_preferences(self, user_email: str):
        """
        Delete preferences for a user.

        Args:
            user_email: User's email address
        """
        if user_email in self._preferences_cache:
            del self._preferences_cache[user_email]
            self._save_all_preferences()

    def get_all_preferences(self) -> List[NotificationPreferences]:
        """
        Get preferences for all users.

        Returns:
            List of all user preferences
        """
        return list(self._preferences_cache.values())

    def get_users_by_frequency(
        self,
        frequency: AlertFrequency
    ) -> List[NotificationPreferences]:
        """
        Get all users with a specific alert frequency.

        Args:
            frequency: Alert frequency to filter by

        Returns:
            List of user preferences matching frequency
        """
        return [
            prefs for prefs in self._preferences_cache.values()
            if prefs.alert_frequency == frequency and prefs.enabled
        ]

    def get_users_with_alert_enabled(
        self,
        alert_type: AlertType
    ) -> List[NotificationPreferences]:
        """
        Get all users who have a specific alert type enabled.

        Args:
            alert_type: Type of alert

        Returns:
            List of user preferences with alert enabled
        """
        return [
            prefs for prefs in self._preferences_cache.values()
            if prefs.is_alert_enabled(alert_type)
        ]

    def _load_all_preferences(self):
        """Load all preferences from disk."""
        if not self.preferences_file.exists():
            return

        try:
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)

            for user_email, prefs_data in data.items():
                prefs = NotificationPreferences.from_dict(prefs_data)
                self._preferences_cache[user_email] = prefs

        except Exception as e:
            logger.warning("Error loading preferences: %s", e)

    def _save_all_preferences(self):
        """Save all preferences to disk."""
        data = {
            email: prefs.to_dict()
            for email, prefs in self._preferences_cache.items()
        }

        with open(self.preferences_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about notification preferences.

        Returns:
            Dictionary with preference statistics
        """
        total_users = len(self._preferences_cache)
        enabled_users = sum(1 for p in self._preferences_cache.values() if p.enabled)

        frequency_counts = {}
        for freq in AlertFrequency:
            frequency_counts[freq.value] = len(self.get_users_by_frequency(freq))

        alert_type_counts = {}
        for alert_type in AlertType:
            alert_type_counts[alert_type.value] = len(
                self.get_users_with_alert_enabled(alert_type)
            )

        return {
            'total_users': total_users,
            'enabled_users': enabled_users,
            'disabled_users': total_users - enabled_users,
            'by_frequency': frequency_counts,
            'by_alert_type': alert_type_counts
        }


def create_default_preferences(user_email: str) -> NotificationPreferences:
    """
    Create default notification preferences for a new user.

    Args:
        user_email: User's email address

    Returns:
        Default NotificationPreferences
    """
    return NotificationPreferences(
        user_email=user_email,
        alert_frequency=AlertFrequency.DAILY,
        enabled_alerts={
            AlertType.PRICE_DROP,
            AlertType.NEW_PROPERTY,
            AlertType.SAVED_SEARCH_MATCH
        },
        price_drop_threshold=5.0,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        daily_digest_time="09:00",
        weekly_digest_day=DigestDay.MONDAY,
        max_alerts_per_day=10,
        enabled=True
    )
