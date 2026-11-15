"""
Unit tests for db/analytics_repos.py repository classes.

Covers: PriceSnapshotRepository, AnomalyRepository,
CMAReportRepository, AuditLogRepository.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from db.analytics_repos import (
    AnomalyRepository,
    AuditLogRepository,
    CMAReportRepository,
    PriceSnapshotRepository,
)
from db.models import AuditLogEntry, CMAReportDB, MarketAnomaly, PriceSnapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_session() -> AsyncMock:
    """Create a mock AsyncSession with async flush/delete/execute and sync add."""
    session = AsyncMock()
    # session.add is called synchronously (no await) in the repos
    session.add = MagicMock()
    # flush and delete are awaited — AsyncMock by default, just ensure it
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    return session


def _make_scalar_result(value):
    """Build a mock result whose .scalar() returns *value*."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = value
    return mock_result


def _make_scalars_result(items: list):
    """Build a mock result whose .scalars().all() returns *items*."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result.scalars.return_value = mock_scalars
    return mock_result


def _make_scalar_one_or_none_result(value):
    """Build a mock result whose .scalar_one_or_none() returns *value*."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = value
    return mock_result


def _make_price_snapshot(
    property_id: str = "prop-1",
    price: float = 100_000.0,
    price_per_sqm: float | None = 1000.0,
    recorded_at: datetime | None = None,
) -> MagicMock:
    snap = MagicMock(spec=PriceSnapshot)
    snap.id = "snap-1"
    snap.property_id = property_id
    snap.price = price
    snap.price_per_sqm = price_per_sqm
    snap.currency = "EUR"
    snap.source = "test"
    snap.recorded_at = recorded_at or datetime.now(UTC)
    return snap


def _make_anomaly(**overrides) -> MagicMock:
    defaults = dict(
        id="anom-1",
        anomaly_type="price_spike",
        severity="high",
        scope_type="property",
        scope_id="prop-1",
        algorithm="z_score",
        threshold_used=2.0,
        metric_name="price",
        expected_value=100_000.0,
        actual_value=150_000.0,
        deviation_percent=50.0,
        z_score=3.5,
        baseline_period_start=None,
        baseline_period_end=None,
        comparison_period_start=None,
        comparison_period_end=None,
        context={},
        alert_sent=False,
        alert_sent_at=None,
        dismissed_by=None,
        dismissed_at=None,
        detected_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return MagicMock(spec=MarketAnomaly, **defaults)


def _make_cma_report(**overrides) -> MagicMock:
    defaults = dict(
        id="report-1",
        user_id="user-1",
        status="draft",
        subject_property_id="prop-1",
        subject_data={"address": "Test St 1"},
        comparables=[{"property_id": "comp-1", "similarity_score": 0.9}],
        valuation={"estimated_value": 200_000},
        market_context=None,
        expires_at=datetime.now(UTC) + timedelta(days=90),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    report = MagicMock(spec=CMAReportDB)
    for k, v in defaults.items():
        setattr(report, k, v)
    return report


def _make_audit_entry(**overrides) -> MagicMock:
    defaults: dict[str, Any] = dict(
        id="entry-1",
        actor_id="user-1",
        actor_email="test@example.com",
        actor_role="admin",
        action="login",
        resource="/api/v1/auth",
        details={},
        ip_address="127.0.0.1",
        user_agent="pytest",
        request_id=None,
        prev_hash="",
        entry_hash="abc123",
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    entry = MagicMock(spec=AuditLogEntry)
    for k, v in defaults.items():
        setattr(entry, k, v)
    entry.compute_hash = MagicMock(return_value="abc123")
    return entry


# ===========================================================================
# PriceSnapshotRepository
# ===========================================================================


class TestPriceSnapshotRepository:
    """Tests for PriceSnapshotRepository."""

    @pytest.fixture
    def session(self) -> AsyncMock:
        return _make_mock_session()

    @pytest.fixture
    def repo(self, session: AsyncMock) -> PriceSnapshotRepository:
        return PriceSnapshotRepository(session)

    # -- create --

    async def test_create_returns_snapshot(self, repo: PriceSnapshotRepository, session: AsyncMock):
        snapshot = await repo.create(
            property_id="prop-1", price=150_000, price_per_sqm=1500.0, currency="EUR", source="test"
        )
        assert isinstance(snapshot, PriceSnapshot)
        assert snapshot.property_id == "prop-1"
        assert snapshot.price == 150_000
        assert snapshot.price_per_sqm == 1500.0
        assert snapshot.currency == "EUR"
        assert snapshot.source == "test"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_create_minimal_fields(self, repo: PriceSnapshotRepository, session: AsyncMock):
        snapshot = await repo.create(property_id="prop-2", price=200_000)
        assert snapshot.property_id == "prop-2"
        assert snapshot.price == 200_000
        assert snapshot.price_per_sqm is None
        assert snapshot.currency is None
        assert snapshot.source is None

    # -- get_by_property --

    async def test_get_by_property_returns_list(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        snaps = [_make_price_snapshot(), _make_price_snapshot(property_id="prop-1", price=120_000)]
        session.execute = AsyncMock(return_value=_make_scalars_result(snaps))

        result = await repo.get_by_property("prop-1")
        assert result == snaps
        assert len(result) == 2
        session.execute.assert_awaited_once()

    async def test_get_by_property_with_limit_offset(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        await repo.get_by_property("prop-1", limit=10, offset=5)
        session.execute.assert_awaited_once()

    # -- get_latest_for_property --

    async def test_get_latest_for_property_found(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        snap = _make_price_snapshot()
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(snap))

        result = await repo.get_latest_for_property("prop-1")
        assert result is snap

    async def test_get_latest_for_property_not_found(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(None))

        result = await repo.get_latest_for_property("prop-999")
        assert result is None

    # -- count_for_property --

    async def test_count_for_property_returns_count(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalar_result(42))

        result = await repo.count_for_property("prop-1")
        assert result == 42

    async def test_count_for_property_returns_zero_when_none(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalar_result(None))

        result = await repo.count_for_property("prop-1")
        assert result == 0

    # -- get_snapshots_in_period --

    async def test_get_snapshots_in_period_no_filter(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        snaps = [_make_price_snapshot()]
        session.execute = AsyncMock(return_value=_make_scalars_result(snaps))

        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 12, 31, tzinfo=UTC)
        result = await repo.get_snapshots_in_period(start, end)
        assert result == snaps

    async def test_get_snapshots_in_period_with_property_ids(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        snaps = [_make_price_snapshot(property_id="p1")]
        session.execute = AsyncMock(return_value=_make_scalars_result(snaps))

        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 12, 31, tzinfo=UTC)
        result = await repo.get_snapshots_in_period(start, end, property_ids=["p1"])
        assert result == snaps

    async def test_get_snapshots_in_period_empty(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 12, 31, tzinfo=UTC)
        result = await repo.get_snapshots_in_period(start, end)
        assert result == []

    # -- get_properties_with_price_drops --

    async def test_get_properties_with_price_drops_detects_drop(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        now = datetime.now(UTC)
        old_snap = _make_price_snapshot(
            property_id="p1", price=200_000, recorded_at=now - timedelta(days=5)
        )
        new_snap = _make_price_snapshot(property_id="p1", price=150_000, recorded_at=now)

        session.execute = AsyncMock(return_value=_make_scalars_result([new_snap, old_snap]))

        drops = await repo.get_properties_with_price_drops(threshold_percent=10.0, days_back=7)
        assert len(drops) == 1
        assert drops[0]["property_id"] == "p1"
        assert drops[0]["old_price"] == 200_000
        assert drops[0]["new_price"] == 150_000
        assert drops[0]["percent_drop"] == 25.0

    async def test_get_properties_with_price_drops_below_threshold(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        now = datetime.now(UTC)
        old_snap = _make_price_snapshot(
            property_id="p1", price=100_000, recorded_at=now - timedelta(days=3)
        )
        new_snap = _make_price_snapshot(property_id="p1", price=97_000, recorded_at=now)

        session.execute = AsyncMock(return_value=_make_scalars_result([new_snap, old_snap]))

        drops = await repo.get_properties_with_price_drops(threshold_percent=5.0)
        assert len(drops) == 0

    async def test_get_properties_with_price_drops_single_snapshot(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        snap = _make_price_snapshot(property_id="p1", price=100_000)
        session.execute = AsyncMock(return_value=_make_scalars_result([snap]))

        drops = await repo.get_properties_with_price_drops()
        assert len(drops) == 0

    async def test_get_properties_with_price_drops_empty(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        drops = await repo.get_properties_with_price_drops()
        assert drops == []

    async def test_get_properties_with_price_drops_zero_old_price(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        now = datetime.now(UTC)
        old_snap = _make_price_snapshot(
            property_id="p1", price=0, recorded_at=now - timedelta(days=3)
        )
        new_snap = _make_price_snapshot(property_id="p1", price=100_000, recorded_at=now)

        session.execute = AsyncMock(return_value=_make_scalars_result([new_snap, old_snap]))

        # price=0 should be skipped to avoid division by zero
        drops = await repo.get_properties_with_price_drops()
        assert len(drops) == 0

    # -- cleanup_old_snapshots --

    async def test_cleanup_old_snapshots_deletes(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        snap1 = _make_price_snapshot()
        snap2 = _make_price_snapshot()
        session.execute = AsyncMock(return_value=_make_scalars_result([snap1, snap2]))
        session.delete = AsyncMock()

        count = await repo.cleanup_old_snapshots(days_to_keep=30)
        assert count == 2
        assert session.delete.await_count == 2

    async def test_cleanup_old_snapshots_nothing_to_delete(
        self, repo: PriceSnapshotRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        count = await repo.cleanup_old_snapshots()
        assert count == 0


# ===========================================================================
# AnomalyRepository
# ===========================================================================


class TestAnomalyRepository:
    """Tests for AnomalyRepository."""

    @pytest.fixture
    def session(self) -> AsyncMock:
        return _make_mock_session()

    @pytest.fixture
    def repo(self, session: AsyncMock) -> AnomalyRepository:
        return AnomalyRepository(session)

    # -- create --

    async def test_create_returns_anomaly(self, repo: AnomalyRepository, session: AsyncMock):
        anomaly = await repo.create(
            anomaly_type="price_spike",
            severity="high",
            scope_type="property",
            scope_id="prop-1",
            algorithm="z_score",
            threshold_used=2.0,
            metric_name="price",
            expected_value=100_000,
            actual_value=150_000,
            deviation_percent=50.0,
        )
        assert isinstance(anomaly, MarketAnomaly)
        assert anomaly.anomaly_type == "price_spike"
        assert anomaly.severity == "high"
        assert anomaly.scope_type == "property"
        assert anomaly.scope_id == "prop-1"
        assert anomaly.z_score is None
        assert anomaly.context == {}
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_create_with_all_fields(self, repo: AnomalyRepository, session: AsyncMock):
        now = datetime.now(UTC)
        anomaly = await repo.create(
            anomaly_type="volume_drop",
            severity="critical",
            scope_type="city",
            scope_id="Berlin",
            algorithm="iqr",
            threshold_used=1.5,
            metric_name="volume",
            expected_value=500.0,
            actual_value=50.0,
            deviation_percent=90.0,
            z_score=4.2,
            baseline_period_start=now - timedelta(days=30),
            baseline_period_end=now,
            comparison_period_start=now,
            comparison_period_end=now + timedelta(days=30),
            context={"reason": "test"},
        )
        assert anomaly.z_score == 4.2
        assert anomaly.context == {"reason": "test"}
        assert anomaly.algorithm == "iqr"

    # -- get_by_id --

    async def test_get_by_id_found(self, repo: AnomalyRepository, session: AsyncMock):
        anom = _make_anomaly()
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(anom))

        result = await repo.get_by_id("anom-1")
        assert result is anom

    async def test_get_by_id_not_found(self, repo: AnomalyRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(None))

        result = await repo.get_by_id("nonexistent")
        assert result is None

    # -- get_by_scope --

    async def test_get_by_scope_returns_list(self, repo: AnomalyRepository, session: AsyncMock):
        anom_list = [_make_anomaly(), _make_anomaly(id="anom-2")]
        session.execute = AsyncMock(return_value=_make_scalars_result(anom_list))

        result = await repo.get_by_scope("property", "prop-1")
        assert result == anom_list

    async def test_get_by_scope_with_pagination(self, repo: AnomalyRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        await repo.get_by_scope("property", "prop-1", limit=10, offset=20)
        session.execute.assert_awaited_once()

    # -- get_recent --

    async def test_get_recent_no_filters(self, repo: AnomalyRepository, session: AsyncMock):
        anom_list = [_make_anomaly()]
        session.execute = AsyncMock(return_value=_make_scalars_result(anom_list))

        result = await repo.get_recent()
        assert result == anom_list

    async def test_get_recent_with_severity_filter(
        self, repo: AnomalyRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        await repo.get_recent(severity_filter="high")
        session.execute.assert_awaited_once()

    async def test_get_recent_with_type_filter(self, repo: AnomalyRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        await repo.get_recent(anomaly_type_filter="price_spike")
        session.execute.assert_awaited_once()

    async def test_get_recent_with_both_filters(self, repo: AnomalyRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        await repo.get_recent(severity_filter="critical", anomaly_type_filter="volume_drop")
        session.execute.assert_awaited_once()

    # -- get_undismissed_count --

    async def test_get_undismissed_count(self, repo: AnomalyRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalar_result(7))

        result = await repo.get_undismissed_count()
        assert result == 7

    async def test_get_undismissed_count_returns_zero_when_none(
        self, repo: AnomalyRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalar_result(None))

        result = await repo.get_undismissed_count()
        assert result == 0

    # -- mark_alert_sent --

    async def test_mark_alert_sent(self, repo: AnomalyRepository, session: AsyncMock):
        session.execute = AsyncMock()

        await repo.mark_alert_sent("anom-1")
        session.execute.assert_awaited_once()

    # -- dismiss --

    async def test_dismiss_with_user(self, repo: AnomalyRepository, session: AsyncMock):
        session.execute = AsyncMock()

        await repo.dismiss("anom-1", dismissed_by="admin-1")
        session.execute.assert_awaited_once()

    async def test_dismiss_without_user(self, repo: AnomalyRepository, session: AsyncMock):
        session.execute = AsyncMock()

        await repo.dismiss("anom-1")
        session.execute.assert_awaited_once()

    # -- get_stats --

    async def test_get_stats(self, repo: AnomalyRepository, session: AsyncMock):
        # Mock total count result
        total_result = _make_scalar_result(10)

        # Mock severity result — each row has .severity and .count via side_effect
        severity_row_1 = MagicMock()
        severity_row_1.severity = "high"
        severity_row_1.count = 6
        severity_row_2 = MagicMock()
        severity_row_2.severity = "low"
        severity_row_2.count = 4
        severity_result = MagicMock()
        severity_result.__iter__ = lambda s: iter([severity_row_1, severity_row_2])
        # Need to support `for row in result` pattern
        severity_iter_result = [severity_row_1, severity_row_2]

        # Mock type result
        type_row = MagicMock()
        type_row.anomaly_type = "price_spike"
        type_row.count = 10
        type_iter_result = [type_row]

        # Mock undismissed count result
        undismissed_result = _make_scalar_result(3)

        call_count = 0

        async def mock_execute(_query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return total_result
            elif call_count == 2:
                # severity query — return something iterable
                mock_res = MagicMock()
                mock_res.__iter__ = lambda s: iter(severity_iter_result)
                return mock_res
            elif call_count == 3:
                mock_res = MagicMock()
                mock_res.__iter__ = lambda s: iter(type_iter_result)
                return mock_res
            else:
                return undismissed_result

        session.execute = AsyncMock(side_effect=mock_execute)

        stats = await repo.get_stats()
        assert stats["total"] == 10
        assert stats["by_severity"] == {"high": 6, "low": 4}
        assert stats["by_type"] == {"price_spike": 10}
        assert stats["undismissed"] == 3


# ===========================================================================
# CMAReportRepository
# ===========================================================================


class TestCMAReportRepository:
    """Tests for CMAReportRepository."""

    @pytest.fixture
    def session(self) -> AsyncMock:
        return _make_mock_session()

    @pytest.fixture
    def repo(self, session: AsyncMock) -> CMAReportRepository:
        return CMAReportRepository(session)

    # -- create --

    async def test_create_returns_report(self, repo: CMAReportRepository, session: AsyncMock):
        report = await repo.create(
            user_id="user-1",
            subject_property_id="prop-1",
            subject_data={"address": "Main St"},
            comparables=[{"property_id": "c1"}],
            valuation={"estimated_value": 300_000},
        )
        assert isinstance(report, CMAReportDB)
        assert report.user_id == "user-1"
        assert report.subject_property_id == "prop-1"
        assert report.status == "draft"
        assert report.expires_at is not None
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_create_no_expiry(self, repo: CMAReportRepository, session: AsyncMock):
        report = await repo.create(
            user_id="user-1",
            subject_property_id="prop-1",
            subject_data={},
            comparables=[],
            valuation={},
            expires_in_days=None,
        )
        assert report.expires_at is None

    async def test_create_custom_status(self, repo: CMAReportRepository, session: AsyncMock):
        report = await repo.create(
            user_id="user-1",
            subject_property_id="prop-1",
            subject_data={},
            comparables=[],
            valuation={},
            status="completed",
        )
        assert report.status == "completed"

    async def test_create_with_market_context(self, repo: CMAReportRepository, session: AsyncMock):
        ctx = {"avg_price_per_sqm": 2500.0, "trend": "rising"}
        report = await repo.create(
            user_id="user-1",
            subject_property_id="prop-1",
            subject_data={},
            comparables=[],
            valuation={},
            market_context=ctx,
        )
        assert report.market_context == ctx

    # -- get_by_id --

    async def test_get_by_id_found(self, repo: CMAReportRepository, session: AsyncMock):
        report = _make_cma_report()
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(report))

        result = await repo.get_by_id("report-1", "user-1")
        assert result is report

    async def test_get_by_id_not_found(self, repo: CMAReportRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(None))

        result = await repo.get_by_id("nonexistent", "user-1")
        assert result is None

    # -- get_by_id_unscoped --

    async def test_get_by_id_unscoped_found(self, repo: CMAReportRepository, session: AsyncMock):
        report = _make_cma_report()
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(report))

        result = await repo.get_by_id_unscoped("report-1")
        assert result is report

    async def test_get_by_id_unscoped_not_found(
        self, repo: CMAReportRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(None))

        result = await repo.get_by_id_unscoped("nonexistent")
        assert result is None

    # -- get_by_user --

    async def test_get_by_user_no_filters(self, repo: CMAReportRepository, session: AsyncMock):
        reports = [_make_cma_report()]
        session.execute = AsyncMock(return_value=_make_scalars_result(reports))

        result = await repo.get_by_user("user-1")
        assert result == reports

    async def test_get_by_user_with_status_filter(
        self, repo: CMAReportRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        await repo.get_by_user("user-1", status="completed")
        session.execute.assert_awaited_once()

    async def test_get_by_user_include_expired(self, repo: CMAReportRepository, session: AsyncMock):
        expired_report = _make_cma_report(
            status="expired",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        session.execute = AsyncMock(return_value=_make_scalars_result([expired_report]))

        result = await repo.get_by_user("user-1", include_expired=True)
        assert len(result) == 1

    async def test_get_by_user_with_pagination(self, repo: CMAReportRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        await repo.get_by_user("user-1", limit=10, offset=5)
        session.execute.assert_awaited_once()

    # -- count_by_user --

    async def test_count_by_user(self, repo: CMAReportRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalar_result(3))

        result = await repo.count_by_user("user-1")
        assert result == 3

    async def test_count_by_user_with_status(self, repo: CMAReportRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalar_result(1))

        result = await repo.count_by_user("user-1", status="draft")
        assert result == 1

    async def test_count_by_user_returns_zero_when_none(
        self, repo: CMAReportRepository, session: AsyncMock
    ):
        session.execute = AsyncMock(return_value=_make_scalar_result(None))

        result = await repo.count_by_user("user-1")
        assert result == 0

    # -- update --

    async def test_update_sets_fields(self, repo: CMAReportRepository, session: AsyncMock):
        report = _make_cma_report()

        updated = await repo.update(
            report, status="completed", valuation={"estimated_value": 250_000}
        )
        assert updated.status == "completed"
        assert updated.valuation == {"estimated_value": 250_000}
        assert updated.updated_at is not None
        session.flush.assert_awaited_once()

    async def test_update_sets_updated_at(self, repo: CMAReportRepository, session: AsyncMock):
        report = _make_cma_report()

        updated = await repo.update(report)
        # update always sets updated_at to now, even with no other kwargs
        assert updated.updated_at is not None
        session.flush.assert_awaited_once()

    # -- mark_completed --

    async def test_mark_completed(self, repo: CMAReportRepository, session: AsyncMock):
        report = _make_cma_report(status="draft")

        result = await repo.mark_completed(report)
        assert report.status == "completed"
        assert report.updated_at is not None
        assert result is report
        session.flush.assert_awaited_once()

    # -- mark_expired --

    async def test_mark_expired(self, repo: CMAReportRepository, session: AsyncMock):
        report = _make_cma_report(status="draft")

        result = await repo.mark_expired(report)
        assert report.status == "expired"
        assert report.updated_at is not None
        assert result is report
        session.flush.assert_awaited_once()

    # -- delete --

    async def test_delete(self, repo: CMAReportRepository, session: AsyncMock):
        report = _make_cma_report()
        session.delete = AsyncMock()

        await repo.delete(report)
        session.delete.assert_awaited_once_with(report)

    # -- expire_old_reports --

    async def test_expire_old_reports_expires_some(
        self, repo: CMAReportRepository, session: AsyncMock
    ):
        expired_ids_result = MagicMock()
        expired_scalars = MagicMock()
        expired_scalars.all.return_value = ["r1", "r2", "r3"]
        expired_ids_result.scalars.return_value = expired_scalars

        session.execute = AsyncMock(return_value=expired_ids_result)

        count = await repo.expire_old_reports(batch_size=50)
        assert count == 3
        session.flush.assert_awaited_once()

    async def test_expire_old_reports_none_expired(
        self, repo: CMAReportRepository, session: AsyncMock
    ):
        empty_result = MagicMock()
        empty_scalars = MagicMock()
        empty_scalars.all.return_value = []
        empty_result.scalars.return_value = empty_scalars

        session.execute = AsyncMock(return_value=empty_result)

        count = await repo.expire_old_reports()
        assert count == 0


# ===========================================================================
# AuditLogRepository
# ===========================================================================


class TestAuditLogRepository:
    """Tests for AuditLogRepository."""

    @pytest.fixture
    def session(self) -> AsyncMock:
        return _make_mock_session()

    @pytest.fixture
    def repo(self, session: AsyncMock) -> AuditLogRepository:
        return AuditLogRepository(session)

    # -- append --

    async def test_append_first_entry(self, repo: AuditLogRepository, session: AsyncMock):
        # No previous entry
        prev_result = _make_scalar_one_or_none_result(None)
        session.execute = AsyncMock(return_value=prev_result)

        entry = await repo.append(action="login", actor_id="user-1", actor_email="a@b.com")
        assert isinstance(entry, AuditLogEntry)
        assert entry.action == "login"
        assert entry.actor_id == "user-1"
        assert entry.prev_hash == ""
        assert entry.details == {}
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_append_chains_hash(self, repo: AuditLogRepository, session: AsyncMock):
        prev_entry = _make_audit_entry(entry_hash="prevhash123")
        prev_result = _make_scalar_one_or_none_result(prev_entry)
        session.execute = AsyncMock(return_value=prev_result)

        entry = await repo.append(action="update", resource="/properties/1")
        assert entry.prev_hash == "prevhash123"
        # compute_hash is a real method on AuditLogEntry; verify entry_hash is set
        assert entry.entry_hash is not None
        assert isinstance(entry.entry_hash, str)

    async def test_append_with_all_fields(self, repo: AuditLogRepository, session: AsyncMock):
        prev_result = _make_scalar_one_or_none_result(None)
        session.execute = AsyncMock(return_value=prev_result)

        entry = await repo.append(
            actor_id="user-1",
            actor_email="test@example.com",
            actor_role="admin",
            action="delete",
            resource="/properties/42",
            details={"reason": "spam"},
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
        )
        assert entry.actor_email == "test@example.com"
        assert entry.actor_role == "admin"
        assert entry.resource == "/properties/42"
        assert entry.details == {"reason": "spam"}
        assert entry.ip_address == "10.0.0.1"
        assert entry.user_agent == "Mozilla/5.0"
        assert entry.request_id == "req-123"

    async def test_append_empty_details_default(self, repo: AuditLogRepository, session: AsyncMock):
        prev_result = _make_scalar_one_or_none_result(None)
        session.execute = AsyncMock(return_value=prev_result)

        entry = await repo.append(action="view")
        assert entry.details == {}

    # -- query --

    async def test_query_no_filters(self, repo: AuditLogRepository, session: AsyncMock):
        entries = [_make_audit_entry()]

        call_count = 0

        async def mock_execute(_q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # count query
                return _make_scalar_result(1)
            return _make_scalars_result(entries)

        session.execute = AsyncMock(side_effect=mock_execute)

        results, total = await repo.query()
        assert total == 1
        assert results == entries

    async def test_query_with_filters(self, repo: AuditLogRepository, session: AsyncMock):
        call_count = 0

        async def mock_execute(_q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_scalar_result(0)
            return _make_scalars_result([])

        session.execute = AsyncMock(side_effect=mock_execute)

        now = datetime.now(UTC)
        results, total = await repo.query(
            action="login",
            actor_id="user-1",
            resource="/auth",
            request_id="req-1",
            start_time=now - timedelta(days=1),
            end_time=now,
            limit=10,
            offset=5,
        )
        assert total == 0
        assert results == []

    async def test_query_empty_result(self, repo: AuditLogRepository, session: AsyncMock):
        call_count = 0

        async def mock_execute(_q):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_scalar_result(None)
            return _make_scalars_result([])

        session.execute = AsyncMock(side_effect=mock_execute)

        results, total = await repo.query()
        assert total == 0
        assert results == []

    # -- verify_chain --

    async def test_verify_chain_valid(self, repo: AuditLogRepository, session: AsyncMock):
        entry1 = _make_audit_entry(id="e1", prev_hash="", entry_hash="hash1")
        entry1.compute_hash = MagicMock(return_value="hash1")
        entry2 = _make_audit_entry(id="e2", prev_hash="hash1", entry_hash="hash2")
        entry2.compute_hash = MagicMock(return_value="hash2")

        session.execute = AsyncMock(return_value=_make_scalars_result([entry1, entry2]))

        result = await repo.verify_chain()
        assert result["valid"] is True
        assert result["checked_count"] == 2
        assert result["broken_count"] == 0
        assert result["broken_entries"] == []

    async def test_verify_chain_prev_hash_mismatch(
        self, repo: AuditLogRepository, session: AsyncMock
    ):
        entry1 = _make_audit_entry(id="e1", prev_hash="", entry_hash="hash1")
        entry1.compute_hash = MagicMock(return_value="hash1")
        # entry2 has wrong prev_hash
        entry2 = _make_audit_entry(id="e2", prev_hash="wrong_hash", entry_hash="hash2")
        entry2.compute_hash = MagicMock(return_value="hash2")

        session.execute = AsyncMock(return_value=_make_scalars_result([entry1, entry2]))

        result = await repo.verify_chain()
        assert result["valid"] is False
        assert result["broken_count"] == 1
        assert result["broken_entries"][0]["entry_id"] == "e2"
        assert result["broken_entries"][0]["reason"] == "prev_hash_mismatch"

    async def test_verify_chain_entry_hash_mismatch(
        self, repo: AuditLogRepository, session: AsyncMock
    ):
        entry1 = _make_audit_entry(id="e1", prev_hash="", entry_hash="hash1")
        entry1.compute_hash = MagicMock(return_value="hash1")
        # entry2 has wrong entry_hash
        entry2 = _make_audit_entry(id="e2", prev_hash="hash1", entry_hash="tampered_hash")
        entry2.compute_hash = MagicMock(return_value="correct_hash")

        session.execute = AsyncMock(return_value=_make_scalars_result([entry1, entry2]))

        result = await repo.verify_chain()
        assert result["valid"] is False
        assert result["broken_count"] == 1
        assert result["broken_entries"][0]["reason"] == "entry_hash_mismatch"

    async def test_verify_chain_empty(self, repo: AuditLogRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalars_result([]))

        result = await repo.verify_chain()
        assert result["valid"] is True
        assert result["checked_count"] == 0
        assert result["broken_count"] == 0

    async def test_verify_chain_limits_broken_entries_to_20(
        self, repo: AuditLogRepository, session: AsyncMock
    ):
        # Create 25 entries with mismatched prev_hash
        entries = []
        for i in range(25):
            e = _make_audit_entry(id=f"e{i}", prev_hash="wrong", entry_hash=f"hash{i}")
            e.compute_hash = MagicMock(return_value=f"hash{i}")
            entries.append(e)

        session.execute = AsyncMock(return_value=_make_scalars_result(entries))

        result = await repo.verify_chain()
        assert result["valid"] is False
        assert result["broken_count"] == 25
        assert len(result["broken_entries"]) == 20  # capped at 20

    # -- get_by_id --

    async def test_get_by_id_found(self, repo: AuditLogRepository, session: AsyncMock):
        entry = _make_audit_entry()
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(entry))

        result = await repo.get_by_id("entry-1")
        assert result is entry

    async def test_get_by_id_not_found(self, repo: AuditLogRepository, session: AsyncMock):
        session.execute = AsyncMock(return_value=_make_scalar_one_or_none_result(None))

        result = await repo.get_by_id("nonexistent")
        assert result is None
