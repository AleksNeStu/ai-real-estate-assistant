import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from data.schemas import Property, PropertyCollection
from notifications.alert_manager import Alert, AlertType
from notifications.notification_history import NotificationType
from notifications.notification_preferences import AlertFrequency, NotificationPreferences
from notifications.scheduler import NotificationScheduler


@pytest.fixture
def mock_email_service():
    return MagicMock()


@pytest.fixture
def mock_prefs_manager():
    return MagicMock()


@pytest.fixture
def mock_history():
    return MagicMock()


@pytest.fixture
def mock_search_manager():
    return MagicMock()


@pytest.fixture
def mock_vector_store():
    return MagicMock()


@pytest.fixture
def scheduler(
    mock_email_service, mock_prefs_manager, mock_history, mock_search_manager, mock_vector_store
):
    return NotificationScheduler(
        email_service=mock_email_service,
        prefs_manager=mock_prefs_manager,
        history=mock_history,
        search_manager=mock_search_manager,
        vector_store=mock_vector_store,
        storage_path_alerts=".test_alerts",
    )


def test_start_stop(scheduler):
    scheduler.start()
    assert scheduler._thread is not None
    assert scheduler._thread.is_alive()

    scheduler.stop(timeout_seconds=10.0)

    # The scheduler stops by setting an event and joining with a timeout, so
    # the thread can still be winding down when stop() returns - more often
    # on a loaded machine, where its current cycle takes longer than the
    # join waits. Wait for it, with a bound, instead of asserting on the
    # instant.
    deadline = time.time() + 10
    while scheduler._thread.is_alive() and time.time() < deadline:
        time.sleep(0.05)
    assert not scheduler._thread.is_alive()


@patch("notifications.scheduler.load_previous_collection")
@patch("notifications.scheduler.load_collection")
@patch("notifications.scheduler.AlertManager")
def test_process_instant_alerts_price_drop(
    mock_alert_manager_cls, mock_load_collection, mock_load_prev, scheduler
):
    # Setup mocks
    mock_am = mock_alert_manager_cls.return_value
    mock_am._get_property_key.side_effect = lambda p: str(p.id)

    # Mock data
    prop1 = Property(id="1", price=1000, city="CityA", rooms=2, bathrooms=1)  # Old price
    prop1_new = Property(id="1", price=900, city="CityA", rooms=2, bathrooms=1)  # New price (drop)

    current_collection = PropertyCollection(properties=[prop1_new], total_count=1)
    prev_collection = PropertyCollection(properties=[prop1], total_count=1)

    mock_load_collection.return_value = current_collection
    mock_load_prev.return_value = prev_collection

    # Mock AlertManager behavior
    mock_am.check_price_drops.return_value = [
        {
            "property": prop1_new,
            "old_price": 1000,
            "new_price": 900,
            "percent_drop": 10.0,
            "savings": 100,
            "property_key": "1",
        }
    ]

    # Mock Preferences
    user_prefs = NotificationPreferences(
        user_email="user@example.com",
        alert_frequency=AlertFrequency.INSTANT,
        enabled_alerts=[AlertType.PRICE_DROP],
        price_drop_threshold=5.0,
        enabled=True,
    )
    scheduler._prefs_manager.get_users_by_frequency.return_value = [user_prefs]

    # Mock Search Manager (match found)
    mock_search = MagicMock()
    mock_search.matches.return_value = True
    scheduler._search_manager.get_all_searches.return_value = [mock_search]

    # Mock Send success
    mock_am.send_price_drop_alert.return_value = True

    # Run (Ensure not in quiet hours - 12:00 PM)
    now = datetime(2023, 1, 1, 12, 0, 0)
    stats = scheduler._process_instant_alerts(now)

    # Assert
    assert stats["sent"] == 1
    assert stats["queued"] == 0
    mock_am.send_price_drop_alert.assert_called_once()
    scheduler._history.record_notification.assert_called_once()


@patch("notifications.scheduler.load_previous_collection")
@patch("notifications.scheduler.load_collection")
@patch("notifications.scheduler.AlertManager")
def test_process_instant_alerts_quiet_hours(
    mock_alert_manager_cls, mock_load_collection, mock_load_prev, scheduler
):
    # Setup mocks
    mock_am = mock_alert_manager_cls.return_value
    mock_am._get_property_key.side_effect = lambda p: str(p.id)

    # Mock data (Price Drop)
    prop1 = Property(id="1", price=1000, city="CityA", rooms=2, bathrooms=1)
    prop1_new = Property(id="1", price=900, city="CityA", rooms=2, bathrooms=1)

    current_collection = PropertyCollection(properties=[prop1_new], total_count=1)
    prev_collection = PropertyCollection(properties=[prop1], total_count=1)
    mock_load_collection.return_value = current_collection
    mock_load_prev.return_value = prev_collection

    mock_am.check_price_drops.return_value = [
        {
            "property": prop1_new,
            "old_price": 1000,
            "new_price": 900,
            "percent_drop": 10.0,
            "savings": 100,
            "property_key": "1",
        }
    ]

    # Mock Preferences (Quiet Hours Active)
    user_prefs = NotificationPreferences(
        user_email="user@example.com",
        alert_frequency=AlertFrequency.INSTANT,
        enabled_alerts=[AlertType.PRICE_DROP],
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        enabled=True,
    )
    scheduler._prefs_manager.get_users_by_frequency.return_value = [user_prefs]

    mock_search = MagicMock()
    mock_search.matches.return_value = True
    scheduler._search_manager.get_all_searches.return_value = [mock_search]

    # Run at 23:00 (In Quiet Hours)
    now = datetime(2023, 1, 1, 23, 0, 0)
    stats = scheduler._process_instant_alerts(now)

    # Assert
    assert stats["sent"] == 0
    assert stats["queued"] == 1
    mock_am.queue_alert.assert_called_once()
    mock_am.send_price_drop_alert.assert_not_called()


@patch("notifications.scheduler.load_collection")
@patch("notifications.scheduler.AlertManager")
@patch("notifications.scheduler.DigestGenerator")
def test_send_due_digests_daily(
    mock_digest_gen_cls, mock_alert_manager_cls, mock_load_collection, scheduler
):
    # Setup mocks
    mock_am = mock_alert_manager_cls.return_value
    mock_gen = mock_digest_gen_cls.return_value

    # Mock Preferences (Daily Digest at 09:00)
    user_prefs = NotificationPreferences(
        user_email="user@example.com",
        alert_frequency=AlertFrequency.DAILY,
        enabled_alerts={AlertType.DIGEST},
        daily_digest_time="09:00",
        enabled=True,
    )
    scheduler._prefs_manager.get_users_by_frequency.return_value = [user_prefs]

    # Mock Generator Data
    mock_gen.generate_digest.return_value = {"some": "data"}

    # Mock Send success
    mock_am.send_digest.return_value = True

    # Run at 09:00
    now = datetime(2023, 1, 1, 9, 0, 0)
    count = scheduler._send_due_digests(AlertFrequency.DAILY, now)

    # Assert
    assert count == 1
    mock_gen.generate_digest.assert_called_once()
    mock_am.send_digest.assert_called_once_with(
        "user@example.com", "daily", {"some": "data"}, send_email=True
    )
    scheduler._history.record_notification.assert_called_once()


@patch("notifications.scheduler.load_previous_collection")
@patch("notifications.scheduler.load_collection")
@patch("notifications.scheduler.AlertManager")
def test_send_due_digests_wrong_time(
    mock_alert_manager_cls, mock_load_collection, mock_load_prev, scheduler
):
    # Setup mocks
    mock_am = mock_alert_manager_cls.return_value

    # Mock Preferences (Daily Digest at 09:00)
    user_prefs = NotificationPreferences(
        user_email="user@example.com",
        alert_frequency=AlertFrequency.DAILY,
        daily_digest_time="09:00",
        enabled=True,
    )
    scheduler._prefs_manager.get_users_by_frequency.return_value = [user_prefs]

    # Run at 10:00 (Wrong Time)
    now = datetime(2023, 1, 1, 10, 0, 0)
    count = scheduler._send_due_digests(AlertFrequency.DAILY, now)

    # Assert
    assert count == 0
    mock_am.send_digest.assert_not_called()


@patch("notifications.scheduler.AlertManager")
def test_run_pending_processes_queued_alerts(mock_alert_manager_cls, scheduler):
    mock_am = mock_alert_manager_cls.return_value

    queued_alert = Alert(
        alert_type=AlertType.PRICE_DROP,
        user_email="user@example.com",
        property_id="1",
        data={
            "property": {"id": "1", "city": "CityA", "price": 900, "rooms": 2, "bathrooms": 1},
            "old_price": 1000,
            "new_price": 900,
            "percent_drop": 10.0,
            "savings": 100,
        },
    )

    mock_am.list_pending_alerts.side_effect = [[queued_alert], []]
    mock_am.process_pending_alerts_with_result.return_value = (1, [queued_alert])

    scheduler._prefs_manager.get_preferences.return_value = NotificationPreferences(
        user_email="user@example.com",
        alert_frequency=AlertFrequency.INSTANT,
        quiet_hours_start=None,
        quiet_hours_end=None,
        enabled=True,
    )

    with (
        patch.object(scheduler, "_refresh_data_sources"),
        patch.object(scheduler, "_send_due_digests", return_value=0),
        patch.object(scheduler, "_process_instant_alerts", return_value={"sent": 0, "queued": 0}),
    ):
        now = datetime(2023, 1, 1, 12, 0, 0)
        result = scheduler.run_pending(now=now)

    assert result["stats"]["queued_alerts_sent"] == 1
    assert mock_am.process_pending_alerts_with_result.call_count == 1


@patch("notifications.scheduler.AlertManager")
def test_run_pending_defers_queued_alerts_during_quiet_hours(mock_alert_manager_cls, scheduler):
    mock_am = mock_alert_manager_cls.return_value

    queued_alert = Alert(
        alert_type=AlertType.PRICE_DROP,
        user_email="user@example.com",
        property_id="1",
        data={"property": {"id": "1", "city": "CityA"}},
    )

    mock_am.list_pending_alerts.side_effect = [[queued_alert], [queued_alert]]
    mock_am.process_pending_alerts_with_result.return_value = (0, [])

    scheduler._prefs_manager.get_preferences.return_value = NotificationPreferences(
        user_email="user@example.com",
        alert_frequency=AlertFrequency.INSTANT,
        quiet_hours_start="22:00",
        quiet_hours_end="08:00",
        enabled=True,
    )

    with (
        patch.object(scheduler, "_refresh_data_sources"),
        patch.object(scheduler, "_send_due_digests", return_value=0),
        patch.object(scheduler, "_process_instant_alerts", return_value={"sent": 0, "queued": 0}),
    ):
        now = datetime(2023, 1, 1, 23, 0, 0)
        result = scheduler.run_pending(now=now)

    assert result["stats"]["queued_alerts_sent"] == 0
    assert result["stats"]["queued_alerts_deferred"] == 1


@patch("notifications.scheduler.AlertManager")
def test_run_pending_records_new_property_history_for_sent_queued_alerts(
    mock_alert_manager_cls, scheduler
):
    mock_am = mock_alert_manager_cls.return_value

    queued_alert = Alert(
        alert_type=AlertType.NEW_PROPERTY,
        user_email="user@example.com",
        data={"search_id": "s1", "search_name": "My Search", "properties": []},
    )

    mock_am.list_pending_alerts.side_effect = [[queued_alert], []]
    mock_am.process_pending_alerts_with_result.return_value = (1, [queued_alert])

    scheduler._prefs_manager.get_preferences.return_value = NotificationPreferences(
        user_email="user@example.com",
        alert_frequency=AlertFrequency.INSTANT,
        quiet_hours_start=None,
        quiet_hours_end=None,
        enabled=True,
    )

    with (
        patch.object(scheduler, "_refresh_data_sources"),
        patch.object(scheduler, "_send_due_digests", return_value=0),
        patch.object(scheduler, "_process_instant_alerts", return_value={"sent": 0, "queued": 0}),
    ):
        now = datetime(2023, 1, 1, 12, 0, 0)
        scheduler.run_pending(now=now)

    assert scheduler._history.record_notification.call_count == 1
    assert (
        scheduler._history.record_notification.call_args.kwargs["notification_type"]
        == NotificationType.NEW_PROPERTY
    )
