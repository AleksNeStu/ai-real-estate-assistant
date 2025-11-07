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

__all__ = [
    'EmailService',
    'EmailConfig',
    'EmailProvider',
    'EmailServiceFactory',
    'EmailValidationError',
    'EmailSendError',
]
