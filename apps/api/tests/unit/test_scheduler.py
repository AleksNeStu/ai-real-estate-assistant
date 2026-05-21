"""
Comprehensive unit tests for notifications/scheduler.py.

Covers all branches: instant alerts, daily/weekly digests, quiet hours,
queued alerts, price snapshots, anomaly detection, search sync, error handling,
and edge cases.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from data.schemas import Property, PropertyCollection
from notifications.alert_manager import Alert, AlertType
from notifications.notification_history import NotificationType
from notifications.notification_preferences import (
    AlertFrequency,
    DigestDay,
    NotificationPreferences,
)
from notifications.scheduler import NotificationScheduler

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Helper to build NotificationPreferences with sensible defaults
# ---------------------------------------------------------------------------


def _make_prefs(**overrides):
    defaults = dict(
        user_email="user@example.com",
        alert_frequency=AlertFrequency.INSTANT,
        enabled_alerts={AlertType.PRICE_DROP, AlertType.NEW_PROPERTY},
        price_drop_threshold=5.0,
        enabled=True,
        daily_digest_time="09:00",
        weekly_digest_day=DigestDay.MONDAY,
    )
    defaults.update(overrides)
    return NotificationPreferences(**defaults)


def _make_property(**overrides):
    defaults = dict(id="prop-1", price=1000, city="CityA", rooms=2, bathrooms=1)
    defaults.update(overrides)
    return Property(**defaults)


# ===========================================================================
# 1. Thread lifecycle
# ===========================================================================


class TestStartStop:
    def test_start_creates_thread(self, scheduler):
        scheduler.start()
        try:
            assert scheduler._thread is not None
            assert scheduler._thread.is_alive()
            assert scheduler._thread.daemon is True
            assert scheduler._thread.name == "NotificationScheduler"
        finally:
            scheduler.stop()

    def test_start_idempotent(self, scheduler):
        """Second call to start() while thread alive returns immediately."""
        scheduler.start()
        first_thread = scheduler._thread
        scheduler.start()  # should hit the early-return at line 80
        assert scheduler._thread is first_thread
        scheduler.stop()

    def test_stop_without_start(self, scheduler):
        """stop() is safe even if start() was never called."""
        scheduler.stop()  # should not raise


# ===========================================================================
# 2. run_pending orchestration
# ===========================================================================


class TestRunPending:
    @patch("notifications.scheduler.AlertManager")
    def test_run_pending_returns_stats_structure(self, mock_am_cls, scheduler):
        mock_am = mock_am_cls.return_value
        mock_am.list_pending_alerts.return_value = []
        mock_am.process_pending_alerts_with_result.return_value = (0, [])

        scheduler._prefs_manager.get_users_by_frequency.return_value = []

        with (
            patch.object(scheduler, "_refresh_data_sources"),
            patch.object(
                scheduler, "_process_instant_alerts", return_value={"sent": 0, "queued": 0}
            ),
        ):
            now = datetime(2023, 6, 15, 9, 0, 0)
            result = scheduler.run_pending(now=now)

        assert "stats" in result
        assert "errors" in result
        stats = result["stats"]
        for key in (
            "digests_daily",
            "digests_weekly",
            "instant_alerts",
            "queued_alerts",
            "queued_alerts_sent",
            "queued_alerts_deferred",
            "price_snapshots",
            "anomaly_alerts",
        ):
            assert key in stats

    @patch("notifications.scheduler.AlertManager")
    def test_run_pending_catches_exception(self, mock_am_cls, scheduler):
        """Top-level except at line 145-147 captures errors."""
        with patch.object(scheduler, "_refresh_data_sources", side_effect=RuntimeError("boom")):
            result = scheduler.run_pending(now=datetime(2023, 1, 1, 12, 0))

        assert len(result["errors"]) == 1
        assert "boom" in result["errors"][0]

    @patch("notifications.scheduler.AlertManager")
    def test_run_pending_aggregates_all_pipelines(self, mock_am_cls, scheduler):
        """run_pending accumulates stats from digest, instant, queued, snapshot, anomaly."""
        mock_am = mock_am_cls.return_value
        mock_am.list_pending_alerts.return_value = []
        mock_am.process_pending_alerts_with_result.return_value = (0, [])

        scheduler._prefs_manager.get_users_by_frequency.return_value = []

        with (
            patch.object(scheduler, "_refresh_data_sources"),
            patch.object(scheduler, "_send_due_digests", side_effect=lambda freq, now: 2),
            patch.object(
                scheduler, "_process_instant_alerts", return_value={"sent": 3, "queued": 1}
            ),
        ):
            now = datetime(2023, 6, 15, 9, 0, 0)
            result = scheduler.run_pending(now=now)

        stats = result["stats"]
        assert stats["digests_daily"] == 2
        assert stats["digests_weekly"] == 2
        assert stats["instant_alerts"] == 3
        assert stats["queued_alerts"] == 1


# ===========================================================================
# 3. _refresh_data_sources
# ===========================================================================


class TestRefreshDataSources:
    def test_refresh_swallows_prefs_error(self, scheduler):
        scheduler._prefs_manager._load_all_preferences.side_effect = RuntimeError("fail")
        scheduler._search_manager._load_searches.return_value = []
        scheduler._refresh_data_sources()  # should not raise

    def test_refresh_swallows_search_error(self, scheduler):
        scheduler._prefs_manager._load_all_preferences.return_value = None
        scheduler._search_manager._load_searches.side_effect = RuntimeError("fail")
        scheduler._refresh_data_sources()  # should not raise

    def test_refresh_both_succeed(self, scheduler):
        scheduler._prefs_manager._load_all_preferences.return_value = None
        scheduler._search_manager._load_searches.return_value = []
        scheduler._refresh_data_sources()
        scheduler._prefs_manager._load_all_preferences.assert_called_once()
        scheduler._search_manager._load_searches.assert_called_once()


# ===========================================================================
# 4. _send_due_digests — Daily & Weekly
# ===========================================================================


class TestSendDueDigests:
    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    @patch("notifications.scheduler.DigestGenerator")
    @patch("notifications.scheduler.MarketInsights")
    def test_daily_digest_sent(
        self, mock_mi_cls, mock_dg_cls, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        mock_am = mock_am_cls.return_value
        mock_am.send_digest.return_value = True
        mock_record = MagicMock()
        mock_record.id = "rec-1"
        scheduler._history.record_notification.return_value = mock_record

        prefs = _make_prefs(
            alert_frequency=AlertFrequency.DAILY,
            enabled_alerts={AlertType.DIGEST},
            daily_digest_time="09:00",
        )
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        now = datetime(2023, 6, 15, 9, 0, 0)  # Thursday 09:00
        count = scheduler._send_due_digests(AlertFrequency.DAILY, now)
        assert count == 1
        mock_am.send_digest.assert_called_once()

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_daily_digest_skipped_wrong_time(
        self, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        prefs = _make_prefs(
            alert_frequency=AlertFrequency.DAILY,
            enabled_alerts={AlertType.DIGEST},
            daily_digest_time="09:00",
        )
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        now = datetime(2023, 6, 15, 10, 0, 0)  # 10:00 != 09:00
        count = scheduler._send_due_digests(AlertFrequency.DAILY, now)
        assert count == 0

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_weekly_digest_sent_on_correct_day(
        self, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        mock_am = mock_am_cls.return_value
        mock_am.send_digest.return_value = True
        mock_record = MagicMock()
        mock_record.id = "rec-2"
        scheduler._history.record_notification.return_value = mock_record

        prefs = _make_prefs(
            alert_frequency=AlertFrequency.WEEKLY,
            enabled_alerts={AlertType.DIGEST},
            daily_digest_time="09:00",
            weekly_digest_day=DigestDay.THURSDAY,
        )
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        # June 15 2023 is Thursday
        now = datetime(2023, 6, 15, 9, 0, 0)
        with patch.object(scheduler, "_build_digest_data", return_value={"new_properties": 0}):
            count = scheduler._send_due_digests(AlertFrequency.WEEKLY, now)
        assert count == 1

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_weekly_digest_skipped_wrong_day(
        self, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        prefs = _make_prefs(
            alert_frequency=AlertFrequency.WEEKLY,
            enabled_alerts={AlertType.DIGEST},
            daily_digest_time="09:00",
            weekly_digest_day=DigestDay.FRIDAY,
        )
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        # June 15 2023 is Thursday, not Friday
        now = datetime(2023, 6, 15, 9, 0, 0)
        count = scheduler._send_due_digests(AlertFrequency.WEEKLY, now)
        assert count == 0

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_digest_skipped_if_digest_alert_disabled(
        self, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        prefs = _make_prefs(
            alert_frequency=AlertFrequency.DAILY,
            enabled_alerts={AlertType.PRICE_DROP},  # DIGEST not enabled
            daily_digest_time="09:00",
        )
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        now = datetime(2023, 6, 15, 9, 0, 0)
        count = scheduler._send_due_digests(AlertFrequency.DAILY, now)
        assert count == 0

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_digest_dedup_same_minute(self, mock_am_cls, mock_load, mock_load_prev, scheduler):
        """Second call within same minute is deduplicated (line 194)."""
        mock_am = mock_am_cls.return_value
        mock_am.send_digest.return_value = True
        mock_record = MagicMock()
        mock_record.id = "rec-dup"
        scheduler._history.record_notification.return_value = mock_record

        prefs = _make_prefs(
            alert_frequency=AlertFrequency.DAILY,
            enabled_alerts={AlertType.DIGEST},
            daily_digest_time="09:00",
        )
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        now = datetime(2023, 6, 15, 9, 0, 0)
        with patch.object(scheduler, "_build_digest_data", return_value={"new_properties": 0}):
            count1 = scheduler._send_due_digests(AlertFrequency.DAILY, now)
            count2 = scheduler._send_due_digests(AlertFrequency.DAILY, now)
        assert count1 == 1
        assert count2 == 0  # deduplicated

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_digest_error_per_user_continues(
        self, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        """Exception for one user (line 219-220) does not stop other users."""
        mock_am = mock_am_cls.return_value
        mock_am.send_digest.return_value = True
        mock_record = MagicMock()
        mock_record.id = "rec-ok"
        scheduler._history.record_notification.return_value = mock_record

        bad_prefs = _make_prefs(
            user_email="bad@example.com",
            alert_frequency=AlertFrequency.DAILY,
            enabled_alerts={AlertType.DIGEST},
            daily_digest_time="09:00",
        )
        good_prefs = _make_prefs(
            user_email="good@example.com",
            alert_frequency=AlertFrequency.DAILY,
            enabled_alerts={AlertType.DIGEST},
            daily_digest_time="09:00",
        )

        # Make the first call fail for bad_prefs (simulate data build error)
        call_count = [0]

        def failing_build(prefs, now, digest_type):
            call_count[0] += 1
            if prefs.user_email == "bad@example.com":
                raise RuntimeError("build failed")
            return {"new_properties": 0}

        scheduler._prefs_manager.get_users_by_frequency.return_value = [bad_prefs, good_prefs]

        with patch.object(scheduler, "_build_digest_data", side_effect=failing_build):
            now = datetime(2023, 6, 15, 9, 0, 0)
            count = scheduler._send_due_digests(AlertFrequency.DAILY, now)

        assert count == 1  # good user succeeded

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_digest_send_returns_false(self, mock_am_cls, mock_load, mock_load_prev, scheduler):
        """send_digest returning False should not increment count."""
        mock_am = mock_am_cls.return_value
        mock_am.send_digest.return_value = False

        prefs = _make_prefs(
            alert_frequency=AlertFrequency.DAILY,
            enabled_alerts={AlertType.DIGEST},
            daily_digest_time="09:00",
        )
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        now = datetime(2023, 6, 15, 9, 0, 0)
        count = scheduler._send_due_digests(AlertFrequency.DAILY, now)
        assert count == 0

    def test_no_users_returns_zero(self, scheduler):
        scheduler._prefs_manager.get_users_by_frequency.return_value = []
        now = datetime(2023, 6, 15, 9, 0, 0)
        count = scheduler._send_due_digests(AlertFrequency.DAILY, now)
        assert count == 0


# ===========================================================================
# 5. _is_time_match
# ===========================================================================


class TestIsTimeMatch:
    def test_invalid_daily_digest_time(self, scheduler):
        prefs = _make_prefs(daily_digest_time="not-a-time")
        now = datetime(2023, 6, 15, 9, 0, 0)
        assert scheduler._is_time_match(prefs, now, AlertFrequency.DAILY) is False

    def test_daily_match(self, scheduler):
        prefs = _make_prefs(daily_digest_time="09:00")
        now = datetime(2023, 6, 15, 9, 0, 0)
        assert scheduler._is_time_match(prefs, now, AlertFrequency.DAILY) is True

    def test_daily_mismatch(self, scheduler):
        prefs = _make_prefs(daily_digest_time="09:00")
        now = datetime(2023, 6, 15, 10, 0, 0)
        assert scheduler._is_time_match(prefs, now, AlertFrequency.DAILY) is False

    def test_weekly_correct_day(self, scheduler):
        prefs = _make_prefs(daily_digest_time="09:00", weekly_digest_day=DigestDay.THURSDAY)
        # June 15 2023 is Thursday
        now = datetime(2023, 6, 15, 9, 0, 0)
        assert scheduler._is_time_match(prefs, now, AlertFrequency.WEEKLY) is True

    def test_weekly_wrong_day(self, scheduler):
        prefs = _make_prefs(daily_digest_time="09:00", weekly_digest_day=DigestDay.FRIDAY)
        # June 15 2023 is Thursday
        now = datetime(2023, 6, 15, 9, 0, 0)
        assert scheduler._is_time_match(prefs, now, AlertFrequency.WEEKLY) is False

    def test_weekly_string_day_value(self, scheduler):
        """weekly_digest_day as raw string (not Enum) should still match (line 239-243)."""
        prefs = _make_prefs(daily_digest_time="09:00")
        prefs.weekly_digest_day = "thursday"  # raw string, no .value
        now = datetime(2023, 6, 15, 9, 0, 0)
        assert scheduler._is_time_match(prefs, now, AlertFrequency.WEEKLY) is True


# ===========================================================================
# 6. _build_digest_data
# ===========================================================================


class TestBuildDigestData:
    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.MarketInsights")
    @patch("notifications.scheduler.DigestGenerator")
    def test_with_vector_store(
        self, mock_dg_cls, mock_mi_cls, mock_load, mock_load_prev, scheduler
    ):
        mock_gen = mock_dg_cls.return_value
        mock_gen.generate_digest.return_value = {"new_properties": 5}

        mock_load.return_value = PropertyCollection(
            properties=[], total_count=0, source_type="test"
        )
        mock_load_prev.return_value = None

        prefs = _make_prefs()
        now = datetime(2023, 6, 15, 9, 0, 0)
        data = scheduler._build_digest_data(prefs, now, digest_type="daily")

        assert data == {"new_properties": 5}
        mock_dg_cls.assert_called_once()

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    def test_fallback_without_vector_store(self, mock_load, mock_load_prev, scheduler):
        scheduler._vector_store = None  # no vector store

        mock_load.return_value = PropertyCollection(
            properties=[], total_count=0, source_type="test"
        )
        mock_load_prev.return_value = None

        prefs = _make_prefs()
        now = datetime(2023, 6, 15, 9, 0, 0)
        data = scheduler._build_digest_data(prefs, now, digest_type="daily")

        assert data["new_properties"] == 0
        assert data["top_picks"] == []

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    def test_null_collection_creates_empty(self, mock_load, mock_load_prev, scheduler):
        scheduler._vector_store = None
        mock_load.return_value = None  # line 254-255
        mock_load_prev.return_value = None

        prefs = _make_prefs()
        now = datetime(2023, 6, 15, 9, 0, 0)
        data = scheduler._build_digest_data(prefs, now, digest_type="daily")

        assert data["new_properties"] == 0


# ===========================================================================
# 7. Instant alert processing
# ===========================================================================


class TestProcessInstantAlerts:
    def test_no_current_data_returns_zero(self, scheduler):
        with patch("notifications.scheduler.load_collection", return_value=None):
            with patch("notifications.scheduler.load_previous_collection"):
                now = datetime(2023, 1, 1, 12, 0, 0)
                stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 0
        assert stats["queued"] == 0

    def test_empty_properties_returns_zero(self, scheduler):
        empty = PropertyCollection(properties=[], total_count=0, source_type="test")
        with patch("notifications.scheduler.load_collection", return_value=empty):
            with patch("notifications.scheduler.load_previous_collection"):
                now = datetime(2023, 1, 1, 12, 0, 0)
                stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 0

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_price_drop_sent(self, mock_am_cls, mock_load, mock_load_prev, scheduler):
        mock_am = mock_am_cls.return_value
        mock_am._get_property_key.side_effect = lambda p: str(p.id)
        mock_am.check_price_drops.return_value = [
            {
                "property": _make_property(price=900),
                "old_price": 1000,
                "new_price": 900,
                "percent_drop": 10.0,
                "savings": 100,
                "property_key": "prop-1",
            }
        ]
        mock_am.send_price_drop_alert.return_value = True
        mock_record = MagicMock()
        mock_record.id = "rec-pd"
        scheduler._history.record_notification.return_value = mock_record

        current = PropertyCollection(properties=[_make_property(price=900)], total_count=1)
        prev = PropertyCollection(properties=[_make_property(price=1000)], total_count=1)
        mock_load.return_value = current
        mock_load_prev.return_value = prev

        prefs = _make_prefs(enabled_alerts={AlertType.PRICE_DROP})
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        mock_search = MagicMock()
        mock_search.matches.return_value = True
        scheduler._search_manager.get_all_searches.return_value = [mock_search]

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 1
        assert stats["queued"] == 0

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_price_drop_queued_in_quiet_hours(
        self, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        mock_am = mock_am_cls.return_value
        mock_am._get_property_key.side_effect = lambda p: str(p.id)
        mock_am.check_price_drops.return_value = [
            {
                "property": _make_property(price=900),
                "old_price": 1000,
                "new_price": 900,
                "percent_drop": 10.0,
                "savings": 100,
                "property_key": "prop-1",
            }
        ]

        current = PropertyCollection(properties=[_make_property(price=900)], total_count=1)
        prev = PropertyCollection(properties=[_make_property(price=1000)], total_count=1)
        mock_load.return_value = current
        mock_load_prev.return_value = prev

        prefs = _make_prefs(
            enabled_alerts={AlertType.PRICE_DROP},
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
        )
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        mock_search = MagicMock()
        mock_search.matches.return_value = True
        scheduler._search_manager.get_all_searches.return_value = [mock_search]

        now = datetime(2023, 1, 1, 23, 0, 0)  # 23:00 in quiet hours
        stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 0
        assert stats["queued"] == 1
        mock_am.queue_alert.assert_called_once()

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_price_drop_filtered_by_threshold(
        self, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        """Drop below user threshold is not sent."""
        mock_am = mock_am_cls.return_value
        mock_am._get_property_key.side_effect = lambda p: str(p.id)
        mock_am.check_price_drops.return_value = [
            {
                "property": _make_property(price=980),
                "old_price": 1000,
                "new_price": 980,
                "percent_drop": 2.0,  # below 5% threshold
                "savings": 20,
                "property_key": "prop-1",
            }
        ]

        current = PropertyCollection(properties=[_make_property(price=980)], total_count=1)
        prev = PropertyCollection(properties=[_make_property(price=1000)], total_count=1)
        mock_load.return_value = current
        mock_load_prev.return_value = prev

        prefs = _make_prefs(enabled_alerts={AlertType.PRICE_DROP}, price_drop_threshold=5.0)
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]
        scheduler._search_manager.get_all_searches.return_value = []

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 0

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_price_drop_no_matching_search(self, mock_am_cls, mock_load, mock_load_prev, scheduler):
        """Drops not matching any saved search are skipped."""
        mock_am = mock_am_cls.return_value
        mock_am._get_property_key.side_effect = lambda p: str(p.id)
        mock_am.check_price_drops.return_value = [
            {
                "property": _make_property(price=900),
                "old_price": 1000,
                "new_price": 900,
                "percent_drop": 10.0,
                "savings": 100,
                "property_key": "prop-1",
            }
        ]

        current = PropertyCollection(properties=[_make_property(price=900)], total_count=1)
        prev = PropertyCollection(properties=[_make_property(price=1000)], total_count=1)
        mock_load.return_value = current
        mock_load_prev.return_value = prev

        prefs = _make_prefs(enabled_alerts={AlertType.PRICE_DROP})
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        mock_search = MagicMock()
        mock_search.matches.return_value = False  # does not match
        scheduler._search_manager.get_all_searches.return_value = [mock_search]

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 0
        assert stats["queued"] == 0

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_disabled_user_skipped(self, mock_am_cls, mock_load, mock_load_prev, scheduler):
        """User with enabled=False is skipped (line 329)."""
        mock_am = mock_am_cls.return_value
        mock_am._get_property_key.side_effect = lambda p: str(p.id)

        current = PropertyCollection(properties=[_make_property()], total_count=1)
        prev = PropertyCollection(properties=[_make_property()], total_count=1)
        mock_load.return_value = current
        mock_load_prev.return_value = prev

        prefs = _make_prefs(enabled=False)
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 0

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_new_property_alert_sent(self, mock_am_cls, mock_load, mock_load_prev, scheduler):
        """New property matching a saved search triggers alert (lines 373-413)."""
        mock_am = mock_am_cls.return_value
        mock_am._get_property_key.side_effect = lambda p: str(p.id)

        new_prop = _make_property(id="new-1", price=500, city="NewCity")
        current = PropertyCollection(properties=[new_prop], total_count=1)
        prev = PropertyCollection(properties=[_make_property(id="old-1")], total_count=1)
        mock_load.return_value = current
        mock_load_prev.return_value = prev

        # No price drops
        mock_am.check_price_drops.return_value = []

        # Matches
        mock_search = MagicMock()
        mock_search.id = "search-1"
        mock_search.name = "My Search"
        matched_props = [new_prop]
        mock_am.check_new_property_matches.return_value = {"search-1": matched_props}

        mock_am.send_new_property_alerts.return_value = True
        mock_record = MagicMock()
        mock_record.id = "rec-np"
        scheduler._history.record_notification.return_value = mock_record

        prefs = _make_prefs(enabled_alerts={AlertType.NEW_PROPERTY})
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]
        scheduler._search_manager.get_all_searches.return_value = [mock_search]

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 1
        mock_am.send_new_property_alerts.assert_called_once()

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_new_property_queued_in_quiet_hours(
        self, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        mock_am = mock_am_cls.return_value
        mock_am._get_property_key.side_effect = lambda p: str(p.id)

        new_prop = _make_property(id="new-1", price=500, city="NewCity")
        current = PropertyCollection(properties=[new_prop], total_count=1)
        prev = PropertyCollection(properties=[_make_property(id="old-1")], total_count=1)
        mock_load.return_value = current
        mock_load_prev.return_value = prev

        mock_am.check_price_drops.return_value = []

        mock_search = MagicMock()
        mock_search.id = "search-1"
        mock_search.name = "Night Search"
        mock_am.check_new_property_matches.return_value = {"search-1": [new_prop]}

        prefs = _make_prefs(
            enabled_alerts={AlertType.NEW_PROPERTY},
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
        )
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]
        scheduler._search_manager.get_all_searches.return_value = [mock_search]

        now = datetime(2023, 1, 1, 23, 0, 0)  # quiet hours
        stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 0
        assert stats["queued"] == 1
        mock_am.queue_alert.assert_called_once()

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_new_property_search_not_found(self, mock_am_cls, mock_load, mock_load_prev, scheduler):
        """Matches with unknown search_id are skipped (line 386-387)."""
        mock_am = mock_am_cls.return_value
        mock_am._get_property_key.side_effect = lambda p: str(p.id)

        new_prop = _make_property(id="new-1")
        current = PropertyCollection(properties=[new_prop], total_count=1)
        prev = PropertyCollection(properties=[_make_property(id="old-1")], total_count=1)
        mock_load.return_value = current
        mock_load_prev.return_value = prev

        mock_am.check_price_drops.return_value = []
        mock_am.check_new_property_matches.return_value = {"ghost-search": [new_prop]}

        prefs = _make_prefs(enabled_alerts={AlertType.NEW_PROPERTY})
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]
        scheduler._search_manager.get_all_searches.return_value = []  # no matching search

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 0

    @patch("notifications.scheduler.load_previous_collection")
    @patch("notifications.scheduler.load_collection")
    @patch("notifications.scheduler.AlertManager")
    def test_no_previous_collection_no_drops_or_new(
        self, mock_am_cls, mock_load, mock_load_prev, scheduler
    ):
        mock_am = mock_am_cls.return_value
        mock_am._get_property_key.side_effect = lambda p: str(p.id)
        mock_load_prev.return_value = None  # no previous

        current = PropertyCollection(properties=[_make_property()], total_count=1)
        mock_load.return_value = current

        prefs = _make_prefs()
        scheduler._prefs_manager.get_users_by_frequency.return_value = [prefs]

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_instant_alerts(now)
        assert stats["sent"] == 0
        assert stats["queued"] == 0
        mock_am.check_price_drops.assert_not_called()


# ===========================================================================
# 8. _process_queued_alerts
# ===========================================================================


class TestProcessQueuedAlerts:
    @patch("notifications.scheduler.AlertManager")
    def test_queued_price_drop_alert_sent(self, mock_am_cls, scheduler):
        mock_am = mock_am_cls.return_value

        queued_alert = Alert(
            alert_type=AlertType.PRICE_DROP,
            user_email="user@example.com",
            property_id="prop-1",
            data={
                "property": {
                    "id": "prop-1",
                    "city": "CityA",
                    "price": 900,
                    "rooms": 2,
                    "bathrooms": 1,
                },
                "old_price": 1000,
                "new_price": 900,
                "percent_drop": 10.0,
                "savings": 100,
            },
        )

        mock_am.list_pending_alerts.side_effect = [[queued_alert], []]
        mock_am.process_pending_alerts_with_result.return_value = (1, [queued_alert])

        mock_record = MagicMock()
        mock_record.id = "rec-qp"
        scheduler._history.record_notification.return_value = mock_record

        scheduler._prefs_manager.get_preferences.return_value = _make_prefs(
            quiet_hours_start=None, quiet_hours_end=None
        )

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_queued_alerts(now)
        assert stats["sent"] == 1
        assert stats["deferred"] == 0

    @patch("notifications.scheduler.AlertManager")
    def test_queued_alert_deferred_during_quiet_hours(self, mock_am_cls, scheduler):
        mock_am = mock_am_cls.return_value

        queued_alert = Alert(
            alert_type=AlertType.PRICE_DROP,
            user_email="user@example.com",
            property_id="prop-1",
            data={"property": {"id": "prop-1", "city": "CityA"}},
        )

        mock_am.list_pending_alerts.side_effect = [[queued_alert], [queued_alert]]
        mock_am.process_pending_alerts_with_result.return_value = (0, [])

        scheduler._prefs_manager.get_preferences.return_value = _make_prefs(
            quiet_hours_start="22:00", quiet_hours_end="08:00"
        )

        now = datetime(2023, 1, 1, 23, 0, 0)
        stats = scheduler._process_queued_alerts(now)
        assert stats["sent"] == 0
        assert stats["deferred"] == 1

    @patch("notifications.scheduler.AlertManager")
    def test_queued_alert_disabled_user(self, mock_am_cls, scheduler):
        """Disabled user's queued alert is deferred (line 426)."""
        mock_am = mock_am_cls.return_value

        queued_alert = Alert(
            alert_type=AlertType.PRICE_DROP,
            user_email="disabled@example.com",
            data={"property": {}},
        )

        mock_am.list_pending_alerts.side_effect = [[queued_alert], [queued_alert]]
        mock_am.process_pending_alerts_with_result.return_value = (0, [])

        scheduler._prefs_manager.get_preferences.return_value = _make_prefs(enabled=False)

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_queued_alerts(now)
        assert stats["deferred"] == 1

    @patch("notifications.scheduler.AlertManager")
    def test_queued_alert_prefs_exception(self, mock_am_cls, scheduler):
        """Exception in get_preferences causes deferral (lines 428-429)."""
        mock_am = mock_am_cls.return_value

        queued_alert = Alert(
            alert_type=AlertType.PRICE_DROP,
            user_email="user@example.com",
            data={},
        )

        mock_am.list_pending_alerts.side_effect = [[queued_alert], [queued_alert]]
        mock_am.process_pending_alerts_with_result.return_value = (0, [])

        scheduler._prefs_manager.get_preferences.side_effect = RuntimeError("db error")

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_queued_alerts(now)
        assert stats["deferred"] == 1

    @patch("notifications.scheduler.AlertManager")
    def test_queued_new_property_alert_sent(self, mock_am_cls, scheduler):
        mock_am = mock_am_cls.return_value

        queued_alert = Alert(
            alert_type=AlertType.NEW_PROPERTY,
            user_email="user@example.com",
            data={"search_id": "s1", "search_name": "My Search", "properties": []},
        )

        mock_am.list_pending_alerts.side_effect = [[queued_alert], []]
        mock_am.process_pending_alerts_with_result.return_value = (1, [queued_alert])

        mock_record = MagicMock()
        mock_record.id = "rec-np"
        scheduler._history.record_notification.return_value = mock_record

        scheduler._prefs_manager.get_preferences.return_value = _make_prefs(
            quiet_hours_start=None, quiet_hours_end=None
        )

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_queued_alerts(now)
        assert stats["sent"] == 1
        scheduler._history.record_notification.assert_called_once()
        call_kwargs = scheduler._history.record_notification.call_args.kwargs
        assert call_kwargs["notification_type"] == NotificationType.NEW_PROPERTY

    @patch("notifications.scheduler.AlertManager")
    def test_no_pending_alerts(self, mock_am_cls, scheduler):
        mock_am = mock_am_cls.return_value
        mock_am.list_pending_alerts.return_value = []
        mock_am.process_pending_alerts_with_result.return_value = (0, [])

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_queued_alerts(now)
        assert stats["sent"] == 0
        assert stats["deferred"] == 0

    @patch("notifications.scheduler.AlertManager")
    def test_price_drop_property_as_object(self, mock_am_cls, scheduler):
        """Cover line 444: property as object with .city attr."""
        mock_am = mock_am_cls.return_value

        prop_mock = MagicMock()
        prop_mock.city = "Berlin"
        prop_mock.id = "p1"

        queued_alert = Alert(
            alert_type=AlertType.PRICE_DROP,
            user_email="user@example.com",
            property_id="p1",
            data={"property": prop_mock},
        )

        mock_am.list_pending_alerts.side_effect = [[queued_alert], []]
        mock_am.process_pending_alerts_with_result.return_value = (1, [queued_alert])

        mock_record = MagicMock()
        mock_record.id = "rec-obj"
        scheduler._history.record_notification.return_value = mock_record

        scheduler._prefs_manager.get_preferences.return_value = _make_prefs(
            quiet_hours_start=None, quiet_hours_end=None
        )

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_queued_alerts(now)
        assert stats["sent"] == 1

    @patch("notifications.scheduler.AlertManager")
    def test_price_drop_no_property_id(self, mock_am_cls, scheduler):
        """Cover line 451: property_id is None."""
        mock_am = mock_am_cls.return_value

        queued_alert = Alert(
            alert_type=AlertType.PRICE_DROP,
            user_email="user@example.com",
            property_id=None,
            data={"property": {"city": "CityA"}},
        )

        mock_am.list_pending_alerts.side_effect = [[queued_alert], []]
        mock_am.process_pending_alerts_with_result.return_value = (1, [queued_alert])

        mock_record = MagicMock()
        mock_record.id = "rec-noid"
        scheduler._history.record_notification.return_value = mock_record

        scheduler._prefs_manager.get_preferences.return_value = _make_prefs(
            quiet_hours_start=None, quiet_hours_end=None
        )

        now = datetime(2023, 1, 1, 12, 0, 0)
        stats = scheduler._process_queued_alerts(now)
        assert stats["sent"] == 1
        # Verify metadata is empty dict when prop_id is None
        call_kwargs = scheduler._history.record_notification.call_args.kwargs
        assert call_kwargs["metadata"] == {}


# ===========================================================================
# 9. Price Snapshot Capture (Task #38)
# ===========================================================================


class TestPriceSnapshotCapture:
    def test_interval_not_elapsed(self, scheduler):
        """Snapshot skipped if interval hasn't elapsed (lines 481-483)."""
        scheduler._last_price_snapshot = datetime(2023, 1, 1, 12, 0, 0)
        now = datetime(2023, 1, 1, 12, 30, 0)  # 30 min < 1 hour
        stats = scheduler._run_price_snapshot_capture(now)
        assert stats["captured"] == 0
        assert stats.get("reason") == "interval_not_elapsed"

    def test_interval_elapsed_runs_capture(self, scheduler):
        """Snapshot runs after interval elapsed."""
        scheduler._last_price_snapshot = datetime(2023, 1, 1, 10, 0, 0)
        now = datetime(2023, 1, 1, 12, 0, 0)  # 2 hours > 1 hour

        with patch(
            "notifications.scheduler.NotificationScheduler._capture_price_snapshots_async",
            new_callable=AsyncMock,
            return_value={"captured": 5, "skipped": 1},
        ):
            stats = scheduler._run_price_snapshot_capture(now)

        assert stats["captured"] == 5
        assert scheduler._last_price_snapshot == now

    def test_first_run_no_last_snapshot(self, scheduler):
        """First run (no _last_price_snapshot) should execute (line 480 None)."""
        scheduler._last_price_snapshot = None
        now = datetime(2023, 1, 1, 12, 0, 0)

        with patch(
            "notifications.scheduler.NotificationScheduler._capture_price_snapshots_async",
            new_callable=AsyncMock,
            return_value={"captured": 3},
        ):
            stats = scheduler._run_price_snapshot_capture(now)

        assert stats["captured"] == 3

    def test_capture_exception_returns_error(self, scheduler):
        """Exception during capture returns error dict (lines 495-497)."""
        scheduler._last_price_snapshot = None
        now = datetime(2023, 1, 1, 12, 0, 0)

        with patch(
            "notifications.scheduler.NotificationScheduler._capture_price_snapshots_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("db fail"),
        ):
            stats = scheduler._run_price_snapshot_capture(now)

        assert stats["captured"] == 0
        assert "db fail" in stats["error"]

    @pytest.mark.asyncio
    async def test_async_capture_success(self, scheduler):
        with patch("services.price_snapshot_service.get_price_snapshot_service") as mock_get:
            mock_service = MagicMock()
            mock_service.capture_all_property_prices = AsyncMock(
                return_value={"captured": 10, "skipped": 2}
            )
            mock_get.return_value = mock_service

            now = datetime(2023, 1, 1, 12, 0, 0)
            stats = await scheduler._capture_price_snapshots_async(now)

        assert stats["captured"] == 10

    @pytest.mark.asyncio
    async def test_async_capture_exception(self, scheduler):
        """Exception in async capture returns error (lines 521-523)."""
        with patch(
            "services.price_snapshot_service.get_price_snapshot_service",
            side_effect=RuntimeError("service init failed"),
        ):
            now = datetime(2023, 1, 1, 12, 0, 0)
            stats = await scheduler._capture_price_snapshots_async(now)

        assert stats["captured"] == 0
        assert "service init failed" in stats["error"]


# ===========================================================================
# 10. Anomaly Detection (Task #53)
# ===========================================================================


class TestAnomalyDetection:
    def test_interval_not_elapsed(self, scheduler):
        scheduler._last_anomaly_check = datetime(2023, 1, 1, 12, 0, 0)
        now = datetime(2023, 1, 1, 12, 30, 0)
        stats = scheduler._run_anomaly_detection(now)
        assert stats["alerts_sent"] == 0
        assert stats.get("reason") == "interval_not_elapsed"

    def test_interval_elapsed_runs_detection(self, scheduler):
        scheduler._last_anomaly_check = datetime(2023, 1, 1, 10, 0, 0)
        now = datetime(2023, 1, 1, 12, 0, 0)

        with patch(
            "notifications.scheduler.NotificationScheduler._run_anomaly_detection_async",
            new_callable=AsyncMock,
            return_value={"alerts_sent": 2, "total_anomalies": 3},
        ):
            stats = scheduler._run_anomaly_detection(now)

        assert stats["alerts_sent"] == 2
        assert scheduler._last_anomaly_check == now

    def test_first_run_no_last_check(self, scheduler):
        scheduler._last_anomaly_check = None
        now = datetime(2023, 1, 1, 12, 0, 0)

        with patch(
            "notifications.scheduler.NotificationScheduler._run_anomaly_detection_async",
            new_callable=AsyncMock,
            return_value={"alerts_sent": 1},
        ):
            stats = scheduler._run_anomaly_detection(now)

        assert stats["alerts_sent"] == 1

    def test_detection_exception_returns_error(self, scheduler):
        scheduler._last_anomaly_check = None
        now = datetime(2023, 1, 1, 12, 0, 0)

        with patch(
            "notifications.scheduler.NotificationScheduler._run_anomaly_detection_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("oops"),
        ):
            stats = scheduler._run_anomaly_detection(now)

        assert stats["alerts_sent"] == 0
        assert "oops" in stats["error"]

    @pytest.mark.asyncio
    async def test_async_detection_full_flow(self, scheduler):
        """Full async detection flow with mocked DB (lines 580-603)."""
        mock_session = AsyncMock()

        # Build a mock async context manager for get_db_context()
        @asynccontextmanager
        async def mock_get_db_context():
            yield mock_session

        mock_anomaly_repo = MagicMock()
        mock_price_repo = MagicMock()
        mock_stats = {"total_anomalies": 2, "alerts_sent": 1}
        mock_service_instance = MagicMock()
        mock_service_instance.run_daily_analysis = AsyncMock(return_value=mock_stats)

        with (
            patch("db.database.get_db_context", mock_get_db_context),
            patch("db.repositories.AnomalyRepository", return_value=mock_anomaly_repo),
            patch("db.repositories.PriceSnapshotRepository", return_value=mock_price_repo),
            patch("notifications.scheduler.AnomalyService", return_value=mock_service_instance),
        ):
            now = datetime(2023, 1, 1, 12, 0, 0)
            stats = await scheduler._run_anomaly_detection_async(now)

        assert stats["total_anomalies"] == 2
        assert stats["alerts_sent"] == 1


# ===========================================================================
# 11. Search sync methods (add_or_update_search, remove_search, get_search, get_all_searches)
# ===========================================================================


class TestSearchSync:
    def test_add_or_update_search(self, scheduler):
        search = MagicMock()
        search.id = "s1"
        scheduler.add_or_update_search(search)
        scheduler._search_manager.save_search.assert_called_once_with(search)

    def test_remove_search_found(self, scheduler):
        scheduler._search_manager.delete_search.return_value = True
        result = scheduler.remove_search("s1")
        assert result is True
        scheduler._search_manager.delete_search.assert_called_once_with("s1")

    def test_remove_search_not_found(self, scheduler):
        scheduler._search_manager.delete_search.return_value = False
        result = scheduler.remove_search("ghost")
        assert result is False

    def test_get_search(self, scheduler):
        mock_search = MagicMock()
        scheduler._search_manager.get_search.return_value = mock_search
        result = scheduler.get_search("s1")
        assert result is mock_search

    def test_get_search_not_found(self, scheduler):
        scheduler._search_manager.get_search.return_value = None
        result = scheduler.get_search("missing")
        assert result is None

    def test_get_all_searches(self, scheduler):
        mock_searches = [MagicMock(), MagicMock()]
        scheduler._search_manager.get_all_searches.return_value = mock_searches
        result = scheduler.get_all_searches()
        assert result == mock_searches


# ===========================================================================
# 12. _run_loop integration
# ===========================================================================


class TestRunLoop:
    def test_run_loop_stops_on_event(self, scheduler):
        """_run_loop calls run_pending and exits when stop_event is set."""
        scheduler._poll_interval_seconds = 0  # no wait
        call_count = 0

        def counting_run_pending(now=None):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                scheduler._stop_event.set()  # break loop
            return {"stats": {}, "errors": []}

        scheduler.run_pending = counting_run_pending
        scheduler._run_loop()
        assert call_count >= 2


# ===========================================================================
# 13. Edge cases and defaults
# ===========================================================================


class TestEdgeCases:
    def test_default_prefs_manager_created(self, mock_email_service):
        """If no prefs_manager provided, default is created (line 56)."""
        with patch("notifications.scheduler.NotificationPreferencesManager"):
            NotificationScheduler(email_service=mock_email_service)
            # Should not raise

    def test_default_history_created(self, mock_email_service):
        with patch("notifications.scheduler.NotificationHistory"):
            NotificationScheduler(email_service=mock_email_service)

    def test_default_search_manager_created(self, mock_email_service):
        with patch("notifications.scheduler.SavedSearchManager"):
            NotificationScheduler(email_service=mock_email_service)

    def test_poll_interval_default(self, mock_email_service):
        s = NotificationScheduler(email_service=mock_email_service)
        assert s._poll_interval_seconds == 60

    def test_vector_store_none_by_default(self, mock_email_service):
        s = NotificationScheduler(email_service=mock_email_service)
        assert s._vector_store is None

    def test_anomaly_service_none_by_default(self, mock_email_service):
        s = NotificationScheduler(email_service=mock_email_service)
        assert s._anomaly_service is None
