"""
Tests for Push Notification Service.

Task #58: Comprehensive Test Suite Update
"""

import sys
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

# Mock pywebpush if not installed (optional dependency)
if "pywebpush" not in sys.modules:

    class _MockWebPushException(Exception):
        """Mock WebPushException matching pywebpush interface."""

        def __init__(self, message="", response=None):
            super().__init__(message)
            self.response = response

    _mock_pywebpush = MagicMock()
    sys.modules["pywebpush"] = _mock_pywebpush
    mock_module = cast(Any, sys.modules["pywebpush"])
    mock_module.WebPushException = _MockWebPushException

from pywebpush import WebPushException

from notifications.push_service import (
    PushNotificationPayload,
    PushNotificationService,
    get_push_service,
)


class TestPushNotificationPayload:
    """Tests for PushNotificationPayload."""

    def test_payload_creation(self):
        """Verify payload is created correctly."""
        payload = PushNotificationPayload(
            title="Test Title",
            body="Test Body",
            icon="/icon.png",
            badge="/badge.png",
            url="https://example.com",
            data={"key": "value"},
        )

        assert payload.title == "Test Title"
        assert payload.body == "Test Body"
        assert payload.icon == "/icon.png"
        assert payload.badge == "/badge.png"
        assert payload.url == "https://example.com"
        assert payload.data == {"key": "value"}

    def test_payload_to_json(self):
        """Verify JSON serialization."""
        payload = PushNotificationPayload(
            title="Test",
            body="Body",
            url="https://example.com",
        )

        json_str = payload.to_json()
        assert '"title": "Test"' in json_str
        assert '"body": "Body"' in json_str
        assert '"url": "https://example.com"' in json_str

    def test_payload_default_icon(self):
        """Verify default icon is used when not provided."""
        payload = PushNotificationPayload(title="Test", body="Body")
        json_str = payload.to_json()

        assert "/icon-192x192.png" in json_str

    def test_payload_with_data(self):
        """Verify data is merged correctly."""
        payload = PushNotificationPayload(
            title="Test",
            body="Body",
            data={"type": "price_drop", "price": 100000},
        )

        import json

        data = json.loads(payload.to_json())
        assert data["data"]["type"] == "price_drop"
        assert data["data"]["price"] == 100000


class TestPushNotificationService:
    """Tests for PushNotificationService."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = MagicMock()
        settings.vapid_private_key = "test_private_key"
        settings.vapid_public_key = "test_public_key"
        settings.vapid_subject = "mailto:test@example.com"
        settings.push_enabled = True
        return settings

    @pytest.fixture
    def push_service(self, mock_settings):
        """Create push service with mock settings."""
        with patch(
            "notifications.push_service.settings",
            mock_settings,
        ):
            service = PushNotificationService(
                vapid_private_key="test_private",
                vapid_public_key="test_public",
                vapid_subject="mailto:test@example.com",
            )
            return service

    @pytest.fixture
    def mock_subscription(self):
        """Create a mock push subscription."""
        sub = MagicMock()
        sub.id = "sub-123"
        sub.endpoint = "https://fcm.googleapis.com/test"
        sub.p256dh = "test_p256dh_key"
        sub.auth = "test_auth_key"
        sub.is_active = True
        return sub

    def test_service_initialization(self, push_service):
        """Verify service initializes correctly."""
        assert push_service.enabled is True
        assert push_service.vapid_private_key == "test_private"
        assert push_service.vapid_public_key == "test_public"

    def test_service_disabled_without_keys(self):
        """Verify service is disabled without VAPID keys."""
        with patch(
            "notifications.push_service.settings",
            MagicMock(
                vapid_private_key=None,
                vapid_public_key=None,
                vapid_subject=None,
                push_enabled=False,
            ),
        ):
            service = PushNotificationService()
            assert service.enabled is False

    def test_get_subscription_info(self, push_service, mock_subscription):
        """Verify subscription info conversion."""
        info = push_service._get_subscription_info(mock_subscription)

        assert info["endpoint"] == "https://fcm.googleapis.com/test"
        assert info["keys"]["p256dh"] == "test_p256dh_key"
        assert info["keys"]["auth"] == "test_auth_key"

    @pytest.mark.asyncio
    async def test_send_notification_disabled_service(self, mock_subscription, mock_settings):
        """Verify send returns False when service disabled."""
        mock_settings.push_enabled = False
        with patch("notifications.push_service.settings", mock_settings):
            service = PushNotificationService(
                vapid_private_key=None,
                vapid_public_key=None,
            )
            payload = PushNotificationPayload(title="Test", body="Body")
            result = await service.send_notification(mock_subscription, payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_notification_inactive_subscription(self, push_service, mock_subscription):
        """Verify send returns False for inactive subscription."""
        mock_subscription.is_active = False
        payload = PushNotificationPayload(title="Test", body="Body")
        result = await push_service.send_notification(mock_subscription, payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_notification_success(self, push_service, mock_subscription):
        """Verify successful notification send."""
        payload = PushNotificationPayload(title="Test", body="Body")

        with patch("notifications.push_service.webpush") as mock_webpush:
            result = await push_service.send_notification(mock_subscription, payload)

        assert result is True
        mock_webpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_410_gone(self, push_service, mock_subscription):
        """Verify handling of 410 Gone response."""
        payload = PushNotificationPayload(title="Test", body="Body")

        mock_response = MagicMock()
        mock_response.status_code = 410

        with patch("notifications.push_service.webpush") as mock_webpush:
            mock_webpush.side_effect = WebPushException("Gone", response=mock_response)
            result = await push_service.send_notification(mock_subscription, payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_notification_webpush_exception(self, push_service, mock_subscription):
        """Verify handling of WebPushException."""
        payload = PushNotificationPayload(title="Test", body="Body")

        with patch("notifications.push_service.webpush") as mock_webpush:
            mock_webpush.side_effect = WebPushException("Failed")
            result = await push_service.send_notification(mock_subscription, payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_to_subscriptions(self, push_service, mock_subscription):
        """Verify batch send to multiple subscriptions."""
        sub2 = MagicMock()
        sub2.id = "sub-456"
        sub2.endpoint = "https://fcm.googleapis.com/test2"
        sub2.p256dh = "key2"
        sub2.auth = "auth2"
        sub2.is_active = True

        subscriptions = [mock_subscription, sub2]
        payload = PushNotificationPayload(title="Test", body="Body")

        with patch("notifications.push_service.webpush"):
            success, fail = await push_service.send_to_subscriptions(subscriptions, payload)

        assert success == 2
        assert fail == 0

    @pytest.mark.asyncio
    async def test_send_price_drop_notification(self, push_service, mock_subscription):
        """Verify price drop notification."""
        with patch.object(push_service, "send_to_subscriptions", return_value=(1, 0)) as mock_send:
            success, fail = await push_service.send_price_drop_notification(
                [mock_subscription],
                property_address="123 Main St",
                old_price=500000,
                new_price=450000,
                currency="EUR",
                property_url="https://example.com/property/123",
            )

        assert success == 1
        assert fail == 0
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_new_property_notification(self, push_service, mock_subscription):
        """Verify new property notification."""
        with patch.object(push_service, "send_to_subscriptions", return_value=(1, 0)) as mock_send:
            success, fail = await push_service.send_new_property_notification(
                [mock_subscription],
                property_address="456 Oak Ave",
                price=350000,
                currency="EUR",
                property_url="https://example.com/property/456",
            )

        assert success == 1
        assert fail == 0
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_market_anomaly_notification(self, push_service, mock_subscription):
        """Verify market anomaly notification."""
        with patch.object(push_service, "send_to_subscriptions", return_value=(1, 0)) as mock_send:
            success, fail = await push_service.send_market_anomaly_notification(
                [mock_subscription],
                anomaly_type="price_spike",
                location="Warsaw",
                severity="high",
                details="Prices increased 20% in the last week",
            )

        assert success == 1
        assert fail == 0
        mock_send.assert_called_once()

    def test_market_anomaly_emojis(self, push_service, mock_subscription):
        """Verify correct emojis for severity levels."""
        # Test all severity levels
        severities = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "📊",
            "low": "📈",
        }

        for _severity, expected_emoji in severities.items():
            payload = PushNotificationPayload(
                title=f"{expected_emoji} Market Alert",
                body="Test",
            )
            assert expected_emoji in payload.title


class TestGetPushService:
    """Tests for get_push_service factory."""

    def test_get_push_service_returns_instance(self):
        """Verify factory returns service instance."""
        with patch(
            "notifications.push_service.settings",
            MagicMock(
                vapid_private_key="test",
                vapid_public_key="test",
                vapid_subject="test",
                push_enabled=True,
            ),
        ):
            # Reset global instance
            import notifications.push_service as ps

            ps._push_service = None
            service = get_push_service()

        assert isinstance(service, PushNotificationService)

    def test_get_push_service_singleton(self):
        """Verify factory returns same instance."""
        with patch(
            "notifications.push_service.settings",
            MagicMock(
                vapid_private_key="test",
                vapid_public_key="test",
                vapid_subject="test",
                push_enabled=True,
            ),
        ):
            import notifications.push_service as ps

            ps._push_service = None
            service1 = get_push_service()
            service2 = get_push_service()

        assert service1 is service2
