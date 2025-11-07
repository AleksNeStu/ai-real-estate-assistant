"""
Notification system for email alerts and updates.

Provides email notifications for:
- Price drops
- New property matches
- Saved search alerts
- Market updates
- Daily/weekly digests
"""

from .email_service import (
    EmailService,
    EmailConfig,
    EmailProvider,
    EmailServiceFactory,
    EmailValidationError,
    EmailSendError
)

from .alert_manager import (
    AlertManager,
    AlertType,
    Alert
)

from .notification_preferences import (
    NotificationPreferences,
    NotificationPreferencesManager,
    AlertFrequency,
    DigestDay,
    create_default_preferences
)

from .email_templates import (
    EmailTemplate,
    PriceDropTemplate,
    NewPropertyTemplate,
    DigestTemplate,
    TestEmailTemplate,
    MarketUpdateTemplate
)

from .notification_history import (
    NotificationHistory,
    NotificationRecord,
    NotificationStatus,
    NotificationType
)

__all__ = [
    # Email Service
    'EmailService',
    'EmailConfig',
    'EmailProvider',
    'EmailServiceFactory',
    'EmailValidationError',
    'EmailSendError',
    # Alert Manager
    'AlertManager',
    'AlertType',
    'Alert',
    # Notification Preferences
    'NotificationPreferences',
    'NotificationPreferencesManager',
    'AlertFrequency',
    'DigestDay',
    'create_default_preferences',
    # Email Templates
    'EmailTemplate',
    'PriceDropTemplate',
    'NewPropertyTemplate',
    'DigestTemplate',
    'TestEmailTemplate',
    'MarketUpdateTemplate',
    # Notification History
    'NotificationHistory',
    'NotificationRecord',
    'NotificationStatus',
    'NotificationType',
]
