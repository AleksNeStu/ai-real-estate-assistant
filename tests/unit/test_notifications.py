"""
Unit tests for notification system (Phase 5).

Tests:
- Email service
- Alert manager
- Notification preferences
- Email templates
- Notification history
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from data.schemas import Property, PropertyType, PropertyCollection
from utils import SavedSearch
from notifications import (
    # Email Service
    EmailService,
    EmailConfig,
    EmailProvider,
    EmailServiceFactory,
    EmailValidationError,
    EmailSendError,
    # Alert Manager
    AlertManager,
    AlertType,
    Alert,
    # Preferences
    NotificationPreferences,
    NotificationPreferencesManager,
    AlertFrequency,
    DigestDay,
    create_default_preferences,
    # Templates
    PriceDropTemplate,
    NewPropertyTemplate,
    DigestTemplate,
    TestEmailTemplate,
    # History
    NotificationHistory,
    NotificationRecord,
    NotificationStatus,
    NotificationType
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def email_config():
    """Create test email configuration."""
    return EmailConfig(
        provider=EmailProvider.GMAIL,
        smtp_server='smtp.gmail.com',
        smtp_port=587,
        username='test@example.com',
        password='test_password',
        from_email='test@example.com',
        from_name='Test Sender',
        use_tls=True
    )


@pytest.fixture
def sample_properties():
    """Create sample properties for testing."""
    return PropertyCollection(
        properties=[
            Property(
                city="Krakow",
                price=850,
                rooms=2,
                bathrooms=1,
                area_sqm=50,
                property_type=PropertyType.APARTMENT,
                has_parking=True,
                has_garden=False,
                has_pool=False,
                is_furnished=True,
                has_balcony=True,
                has_elevator=False
            ),
            Property(
                city="Warsaw",
                price=1200,
                rooms=3,
                bathrooms=2,
                area_sqm=75,
                property_type=PropertyType.APARTMENT,
                has_parking=True,
                has_garden=True,
                has_pool=False,
                is_furnished=False,
                has_balcony=True,
                has_elevator=True
            ),
        ],
        total_count=2
    )


@pytest.fixture
def sample_property():
    """Create a single sample property."""
    return Property(
        city="Krakow",
        price=850,
        rooms=2,
        bathrooms=1,
        area_sqm=50,
        property_type=PropertyType.APARTMENT,
        has_parking=True,
        is_furnished=True
    )


# ============================================================================
# Email Service Tests
# ============================================================================

class TestEmailService:
    """Tests for email service."""

    def test_email_config_creation(self, email_config):
        """Test creating email configuration."""
        assert email_config.provider == EmailProvider.GMAIL
        assert email_config.smtp_server == 'smtp.gmail.com'
        assert email_config.smtp_port == 587
        assert email_config.use_tls is True

    def test_email_validation_valid(self):
        """Test email validation with valid emails."""
        config = EmailConfig(
            provider=EmailProvider.GMAIL,
            smtp_server='smtp.gmail.com',
            smtp_port=587,
            username='test@example.com',
            password='password',
            from_email='test@example.com'
        )
        service = EmailService(config)

        assert service.validate_email('user@example.com') is True
        assert service.validate_email('user.name@example.co.uk') is True
        assert service.validate_email('user+tag@example.com') is True

    def test_email_validation_invalid(self):
        """Test email validation with invalid emails."""
        config = EmailConfig(
            provider=EmailProvider.GMAIL,
            smtp_server='smtp.gmail.com',
            smtp_port=587,
            username='test@example.com',
            password='password',
            from_email='test@example.com'
        )
        service = EmailService(config)

        assert service.validate_email('invalid') is False
        assert service.validate_email('invalid@') is False
        assert service.validate_email('@example.com') is False
        assert service.validate_email('user@') is False

    def test_gmail_service_factory(self):
        """Test Gmail service creation via factory."""
        service = EmailServiceFactory.create_gmail_service(
            username='test@gmail.com',
            password='app_password'
        )

        assert isinstance(service, EmailService)
        assert service.config.provider == EmailProvider.GMAIL
        assert service.config.smtp_server == 'smtp.gmail.com'
        assert service.config.smtp_port == 587

    def test_outlook_service_factory(self):
        """Test Outlook service creation via factory."""
        service = EmailServiceFactory.create_outlook_service(
            username='test@outlook.com',
            password='password'
        )

        assert isinstance(service, EmailService)
        assert service.config.provider == EmailProvider.OUTLOOK
        assert service.config.smtp_server == 'smtp-mail.outlook.com'

    def test_email_statistics(self, email_config):
        """Test email sending statistics."""
        service = EmailService(email_config)

        stats = service.get_statistics()
        assert stats['sent'] == 0
        assert stats['failed'] == 0
        assert stats['total'] == 0
        assert stats['success_rate'] == 0


# ============================================================================
# Alert Manager Tests
# ============================================================================

class TestAlertManager:
    """Tests for alert manager."""

    @pytest.fixture
    def mock_email_service(self):
        """Create mock email service."""
        service = Mock(spec=EmailService)
        service.send_email = Mock(return_value=True)
        return service

    @pytest.fixture
    def alert_manager(self, mock_email_service, temp_dir):
        """Create alert manager with mock email service."""
        return AlertManager(
            email_service=mock_email_service,
            storage_path=temp_dir
        )

    def test_alert_manager_initialization(self, alert_manager):
        """Test alert manager initialization."""
        assert alert_manager.email_service is not None
        assert alert_manager.storage_path.exists()

    def test_check_price_drops(self, alert_manager):
        """Test price drop detection."""
        current = PropertyCollection(
            properties=[
                Property(
                    city="Krakow",
                    price=800,  # Dropped from 1000
                    rooms=2,
                    bathrooms=1,
                    area_sqm=50,
                    property_type=PropertyType.APARTMENT
                )
            ],
            total_count=1
        )

        previous = PropertyCollection(
            properties=[
                Property(
                    city="Krakow",
                    price=1000,
                    rooms=2,
                    bathrooms=1,
                    area_sqm=50,
                    property_type=PropertyType.APARTMENT
                )
            ],
            total_count=1
        )

        drops = alert_manager.check_price_drops(current, previous, threshold_percent=5.0)

        assert len(drops) == 1
        assert drops[0]['old_price'] == 1000
        assert drops[0]['new_price'] == 800
        assert drops[0]['percent_drop'] == 20.0
        assert drops[0]['savings'] == 200

    def test_check_price_drops_below_threshold(self, alert_manager):
        """Test price drops below threshold are ignored."""
        current = PropertyCollection(
            properties=[
                Property(
                    city="Krakow",
                    price=980,  # Only 2% drop
                    rooms=2,
                    bathrooms=1,
                    area_sqm=50,
                    property_type=PropertyType.APARTMENT
                )
            ],
            total_count=1
        )

        previous = PropertyCollection(
            properties=[
                Property(
                    city="Krakow",
                    price=1000,
                    rooms=2,
                    bathrooms=1,
                    area_sqm=50,
                    property_type=PropertyType.APARTMENT
                )
            ],
            total_count=1
        )

        drops = alert_manager.check_price_drops(current, previous, threshold_percent=5.0)

        assert len(drops) == 0

    def test_alert_statistics(self, alert_manager):
        """Test getting alert statistics."""
        stats = alert_manager.get_alert_statistics()

        assert 'total_sent' in stats
        assert 'pending' in stats
        assert stats['total_sent'] >= 0


# ============================================================================
# Notification Preferences Tests
# ============================================================================

class TestNotificationPreferences:
    """Tests for notification preferences."""

    def test_default_preferences(self):
        """Test creating default preferences."""
        prefs = create_default_preferences('user@example.com')

        assert prefs.user_email == 'user@example.com'
        assert prefs.alert_frequency == AlertFrequency.DAILY
        assert AlertType.PRICE_DROP in prefs.enabled_alerts
        assert prefs.price_drop_threshold == 5.0
        assert prefs.enabled is True

    def test_is_alert_enabled(self):
        """Test checking if alert type is enabled."""
        prefs = NotificationPreferences(
            user_email='user@example.com',
            enabled_alerts={AlertType.PRICE_DROP, AlertType.NEW_PROPERTY}
        )

        assert prefs.is_alert_enabled(AlertType.PRICE_DROP) is True
        assert prefs.is_alert_enabled(AlertType.NEW_PROPERTY) is True
        assert prefs.is_alert_enabled(AlertType.MARKET_UPDATE) is False

    def test_quiet_hours_check(self):
        """Test quiet hours checking."""
        prefs = NotificationPreferences(
            user_email='user@example.com',
            quiet_hours_start='22:00',
            quiet_hours_end='08:00'
        )

        # Test during quiet hours (11 PM)
        check_time = datetime.now().replace(hour=23, minute=0)
        assert prefs.is_in_quiet_hours(check_time) is True

        # Test outside quiet hours (2 PM)
        check_time = datetime.now().replace(hour=14, minute=0)
        assert prefs.is_in_quiet_hours(check_time) is False

    def test_should_send_alert(self):
        """Test alert sending decision logic."""
        prefs = NotificationPreferences(
            user_email='user@example.com',
            enabled_alerts={AlertType.PRICE_DROP},
            max_alerts_per_day=10
        )

        # Should send - alert enabled, not at limit
        assert prefs.should_send_alert(AlertType.PRICE_DROP, alerts_sent_today=5) is True

        # Should not send - disabled alert type
        assert prefs.should_send_alert(AlertType.MARKET_UPDATE, alerts_sent_today=5) is False

        # Should not send - at daily limit
        assert prefs.should_send_alert(AlertType.PRICE_DROP, alerts_sent_today=10) is False

    def test_preferences_to_dict_and_back(self):
        """Test serialization and deserialization."""
        prefs = NotificationPreferences(
            user_email='user@example.com',
            alert_frequency=AlertFrequency.WEEKLY,
            enabled_alerts={AlertType.PRICE_DROP}
        )

        # Convert to dict
        prefs_dict = prefs.to_dict()
        assert isinstance(prefs_dict, dict)
        assert prefs_dict['user_email'] == 'user@example.com'

        # Convert back
        restored = NotificationPreferences.from_dict(prefs_dict)
        assert restored.user_email == prefs.user_email
        assert restored.alert_frequency == prefs.alert_frequency


class TestNotificationPreferencesManager:
    """Tests for preferences manager."""

    @pytest.fixture
    def prefs_manager(self, temp_dir):
        """Create preferences manager with temp storage."""
        return NotificationPreferencesManager(storage_path=temp_dir)

    def test_get_preferences_creates_defaults(self, prefs_manager):
        """Test that getting preferences for new user creates defaults."""
        prefs = prefs_manager.get_preferences('newuser@example.com')

        assert prefs.user_email == 'newuser@example.com'
        assert prefs.enabled is True

    def test_save_and_load_preferences(self, prefs_manager):
        """Test saving and loading preferences."""
        prefs = NotificationPreferences(
            user_email='user@example.com',
            alert_frequency=AlertFrequency.INSTANT,
            price_drop_threshold=10.0
        )

        prefs_manager.save_preferences(prefs)

        # Create new manager to test loading
        new_manager = NotificationPreferencesManager(storage_path=prefs_manager.storage_path)
        loaded = new_manager.get_preferences('user@example.com')

        assert loaded.alert_frequency == AlertFrequency.INSTANT
        assert loaded.price_drop_threshold == 10.0

    def test_update_preferences(self, prefs_manager):
        """Test updating specific preference fields."""
        prefs_manager.get_preferences('user@example.com')  # Create initial

        updated = prefs_manager.update_preferences(
            'user@example.com',
            price_drop_threshold=15.0,
            max_alerts_per_day=5
        )

        assert updated.price_drop_threshold == 15.0
        assert updated.max_alerts_per_day == 5

    def test_get_users_by_frequency(self, prefs_manager):
        """Test filtering users by alert frequency."""
        prefs_manager.update_preferences(
            'user1@example.com',
            alert_frequency=AlertFrequency.DAILY
        )
        prefs_manager.update_preferences(
            'user2@example.com',
            alert_frequency=AlertFrequency.INSTANT
        )
        prefs_manager.update_preferences(
            'user3@example.com',
            alert_frequency=AlertFrequency.DAILY
        )

        daily_users = prefs_manager.get_users_by_frequency(AlertFrequency.DAILY)
        assert len(daily_users) == 2

    def test_get_statistics(self, prefs_manager):
        """Test getting preference statistics."""
        prefs_manager.get_preferences('user1@example.com')
        prefs_manager.get_preferences('user2@example.com')
        prefs_manager.update_preferences('user2@example.com', enabled=False)

        stats = prefs_manager.get_statistics()

        assert stats['total_users'] == 2
        assert stats['enabled_users'] == 1
        assert stats['disabled_users'] == 1


# ============================================================================
# Email Templates Tests
# ============================================================================

class TestEmailTemplates:
    """Tests for email templates."""

    def test_price_drop_template(self, sample_property):
        """Test price drop email template rendering."""
        property_info = {
            'property': sample_property,
            'old_price': 1000,
            'new_price': 850,
            'percent_drop': 15.0,
            'savings': 150
        }

        subject, html = PriceDropTemplate.render(property_info)

        assert '🔔' in subject or 'Price Drop' in subject
        assert 'Krakow' in subject
        assert '$850' in html or '850' in html
        assert '$1,000' in html or '1000' in html

    def test_new_property_template(self, sample_properties):
        """Test new property match template rendering."""
        subject, html = NewPropertyTemplate.render(
            search_name='My Search',
            properties=sample_properties.properties,
            max_display=5
        )

        assert 'My Search' in subject
        assert '2' in subject  # Number of properties
        assert 'Krakow' in html
        assert 'Warsaw' in html

    def test_digest_template(self):
        """Test digest email template rendering."""
        data = {
            'new_properties': 15,
            'price_drops': 5,
            'avg_price': 950,
            'total_properties': 1234,
            'average_price': 975
        }

        subject, html = DigestTemplate.render(
            digest_type='daily',
            data=data
        )

        assert 'Daily' in subject or 'daily' in subject.lower()
        assert '15' in html  # New properties count
        assert '5' in html   # Price drops count

    def test_test_email_template(self):
        """Test email template rendering."""
        subject, html = TestEmailTemplate.render(user_name='John')

        assert 'Test' in subject
        assert 'John' in html or 'Hi' in html
        assert 'configuration' in html.lower()


# ============================================================================
# Notification History Tests
# ============================================================================

class TestNotificationHistory:
    """Tests for notification history."""

    @pytest.fixture
    def history(self, temp_dir):
        """Create notification history with temp storage."""
        return NotificationHistory(storage_path=temp_dir)

    def test_record_notification(self, history):
        """Test recording a new notification."""
        record = history.record_notification(
            user_email='user@example.com',
            notification_type=NotificationType.PRICE_DROP,
            subject='Price Drop Alert',
            metadata={'property_id': 'prop123'}
        )

        assert record.user_email == 'user@example.com'
        assert record.notification_type == NotificationType.PRICE_DROP
        assert record.status == NotificationStatus.PENDING
        assert record.metadata['property_id'] == 'prop123'

    def test_mark_sent(self, history):
        """Test marking notification as sent."""
        record = history.record_notification(
            user_email='user@example.com',
            notification_type=NotificationType.PRICE_DROP,
            subject='Test'
        )

        history.mark_sent(record.id)
        updated = history.get_notification(record.id)

        assert updated.status == NotificationStatus.SENT
        assert updated.sent_at is not None

    def test_mark_delivered(self, history):
        """Test marking notification as delivered."""
        record = history.record_notification(
            user_email='user@example.com',
            notification_type=NotificationType.PRICE_DROP,
            subject='Test'
        )

        history.mark_delivered(record.id)
        updated = history.get_notification(record.id)

        assert updated.status == NotificationStatus.DELIVERED
        assert updated.delivered_at is not None

    def test_mark_failed(self, history):
        """Test marking notification as failed."""
        record = history.record_notification(
            user_email='user@example.com',
            notification_type=NotificationType.PRICE_DROP,
            subject='Test'
        )

        history.mark_failed(record.id, 'SMTP error', add_to_retry_queue=True)
        updated = history.get_notification(record.id)

        assert updated.status == NotificationStatus.FAILED
        assert updated.error_message == 'SMTP error'
        assert updated.retry_count == 1

    def test_get_user_notifications(self, history):
        """Test getting notifications for a user."""
        history.record_notification(
            'user1@example.com',
            NotificationType.PRICE_DROP,
            'Alert 1'
        )
        history.record_notification(
            'user1@example.com',
            NotificationType.NEW_PROPERTY,
            'Alert 2'
        )
        history.record_notification(
            'user2@example.com',
            NotificationType.PRICE_DROP,
            'Alert 3'
        )

        user1_notifications = history.get_user_notifications('user1@example.com')
        assert len(user1_notifications) == 2

        user2_notifications = history.get_user_notifications('user2@example.com')
        assert len(user2_notifications) == 1

    def test_get_user_statistics(self, history):
        """Test getting user notification statistics."""
        record1 = history.record_notification(
            'user@example.com',
            NotificationType.PRICE_DROP,
            'Alert 1'
        )
        record2 = history.record_notification(
            'user@example.com',
            NotificationType.NEW_PROPERTY,
            'Alert 2'
        )

        history.mark_sent(record1.id)
        history.mark_delivered(record1.id)
        history.mark_failed(record2.id, 'Error')

        stats = history.get_user_statistics('user@example.com')

        assert stats['total_sent'] == 2
        assert stats['total_delivered'] == 1
        assert stats['total_failed'] == 1
        assert stats['delivery_rate'] == 50.0

    def test_get_overall_statistics(self, history):
        """Test getting overall notification statistics."""
        history.record_notification(
            'user1@example.com',
            NotificationType.PRICE_DROP,
            'Alert 1'
        )
        history.record_notification(
            'user2@example.com',
            NotificationType.NEW_PROPERTY,
            'Alert 2'
        )

        stats = history.get_overall_statistics()

        assert stats['total_notifications'] == 2
        assert stats['total_users'] == 2

    def test_cleanup_old_records(self, history):
        """Test cleaning up old notification records."""
        # Create old record
        old_record = history.record_notification(
            'user@example.com',
            NotificationType.PRICE_DROP,
            'Old Alert'
        )
        # Manually set creation date to 100 days ago
        history._history[old_record.id].created_at = datetime.now() - timedelta(days=100)

        # Create recent record
        recent_record = history.record_notification(
            'user@example.com',
            NotificationType.NEW_PROPERTY,
            'Recent Alert'
        )

        # Cleanup records older than 90 days
        history.cleanup_old_records(days=90)

        assert history.get_notification(old_record.id) is None
        assert history.get_notification(recent_record.id) is not None
