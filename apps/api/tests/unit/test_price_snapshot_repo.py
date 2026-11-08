"""Unit tests for PriceSnapshotRepository.

Task #38: Price History & Trends
"""

from datetime import UTC, datetime, timedelta

import pytest

from db.repositories import PriceSnapshotRepository


@pytest.fixture
def repo(db_session):
    """Create a repository instance."""
    return PriceSnapshotRepository(db_session)


@pytest.fixture
def frozen_clock(monkeypatch):
    """Freeze the clock the repository reads, so two snapshots share one tick."""
    from db import analytics_repos

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 1, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(analytics_repos, "datetime", _FrozenDatetime)
    return _FrozenDatetime


class TestPriceSnapshotRepository:
    """Tests for PriceSnapshotRepository."""

    @pytest.mark.asyncio
    async def test_create_snapshot(self, repo):
        """Test creating a price snapshot."""
        snapshot = await repo.create(
            property_id="test-prop-1",
            price=500000.0,
            price_per_sqm=5000.0,
            currency="PLN",
            source="test",
        )

        assert snapshot.id is not None
        assert snapshot.property_id == "test-prop-1"
        assert snapshot.price == 500000.0
        assert snapshot.price_per_sqm == 5000.0
        assert snapshot.currency == "PLN"
        assert snapshot.source == "test"
        assert snapshot.recorded_at is not None

    @pytest.mark.asyncio
    async def test_create_snapshot_minimal(self, repo):
        """Test creating a price snapshot with minimal data."""
        snapshot = await repo.create(
            property_id="test-prop-2",
            price=300000.0,
        )

        assert snapshot.id is not None
        assert snapshot.property_id == "test-prop-2"
        assert snapshot.price == 300000.0
        assert snapshot.price_per_sqm is None
        assert snapshot.currency is None
        assert snapshot.source is None

    @pytest.mark.asyncio
    async def test_get_by_property(self, repo):
        """Test getting price history for a property."""
        # Create multiple snapshots
        for i in range(5):
            await repo.create(
                property_id="test-prop-1",
                price=500000.0 + (i * 10000),
            )

        snapshots = await repo.get_by_property("test-prop-1")

        assert len(snapshots) == 5
        # Should be ordered by recorded_at desc
        assert snapshots[0].price == 540000.0  # Most recent

    @pytest.mark.asyncio
    async def test_get_by_property_with_limit(self, repo):
        """Test getting price history with limit."""
        # Create multiple snapshots
        for i in range(10):
            await repo.create(
                property_id="test-prop-1",
                price=500000.0 + (i * 10000),
            )

        snapshots = await repo.get_by_property("test-prop-1", limit=3)

        assert len(snapshots) == 3

    @pytest.mark.asyncio
    async def test_get_by_property_empty(self, repo):
        """Test getting price history for non-existent property."""
        snapshots = await repo.get_by_property("nonexistent")

        assert len(snapshots) == 0

    @pytest.mark.asyncio
    async def test_get_latest_for_property(self, repo):
        """Test getting the latest snapshot for a property."""
        # Create multiple snapshots
        await repo.create(property_id="test-prop-1", price=500000.0)
        await repo.create(property_id="test-prop-1", price=510000.0)
        await repo.create(property_id="test-prop-1", price=520000.0)

        latest = await repo.get_latest_for_property("test-prop-1")

        assert latest is not None
        assert latest.price == 520000.0

    @pytest.mark.asyncio
    async def test_get_latest_for_property_empty(self, repo):
        """Test getting latest snapshot for non-existent property."""
        latest = await repo.get_latest_for_property("nonexistent")

        assert latest is None

    @pytest.mark.asyncio
    async def test_count_for_property(self, repo):
        """Test counting snapshots for a property."""
        for _ in range(3):
            await repo.create(
                property_id="test-prop-1",
                price=500000.0,
            )

        count = await repo.count_for_property("test-prop-1")
        assert count == 3

        count_empty = await repo.count_for_property("nonexistent")
        assert count_empty == 0

    @pytest.mark.asyncio
    async def test_get_snapshots_in_period(self, repo):
        """Test getting snapshots within a time period."""
        now = datetime.now(UTC)

        # Create snapshots
        await repo.create(property_id="prop-1", price=100000.0)
        await repo.create(property_id="prop-2", price=200000.0)

        # Get snapshots from last hour
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        snapshots = await repo.get_snapshots_in_period(start, end)

        assert len(snapshots) == 2

    @pytest.mark.asyncio
    async def test_get_snapshots_in_period_with_filter(self, repo):
        """Test getting snapshots within a time period with property filter."""
        now = datetime.now(UTC)

        # Create snapshots for multiple properties
        await repo.create(property_id="prop-1", price=100000.0)
        await repo.create(property_id="prop-2", price=200000.0)
        await repo.create(property_id="prop-3", price=300000.0)

        # Get snapshots only for specific properties
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)

        snapshots = await repo.get_snapshots_in_period(
            start, end, property_ids=["prop-1", "prop-2"]
        )

        assert len(snapshots) == 2

    @pytest.mark.asyncio
    async def test_get_properties_with_price_drops(self, repo):
        """Test detecting properties with price drops."""
        # Create snapshots showing a price drop
        # First, create an older higher price
        await repo.create(property_id="prop-1", price=500000.0)

        # Then create a lower price (simulating a drop)
        await repo.create(property_id="prop-1", price=450000.0)

        drops = await repo.get_properties_with_price_drops(
            threshold_percent=5.0,
            days_back=7,
        )

        # Should detect the drop (10% drop from 500k to 450k)
        assert len(drops) >= 1
        found_drop = next((d for d in drops if d["property_id"] == "prop-1"), None)
        assert found_drop is not None
        assert found_drop["old_price"] == 500000.0
        assert found_drop["new_price"] == 450000.0

    @pytest.mark.asyncio
    async def test_get_properties_with_price_drops_no_drop(self, repo):
        """Test that stable prices are not detected as drops."""
        # Create snapshots with stable price
        await repo.create(property_id="prop-stable", price=300000.0)
        await repo.create(property_id="prop-stable", price=300000.0)

        drops = await repo.get_properties_with_price_drops(
            threshold_percent=5.0,
            days_back=7,
        )

        # Should not detect a drop
        stable_drop = next((d for d in drops if d["property_id"] == "prop-stable"), None)
        assert stable_drop is None

    @pytest.mark.asyncio
    async def test_get_properties_with_price_drops_below_threshold(self, repo):
        """Test that small price changes below threshold are ignored."""
        # Create snapshots with small price change (2%)
        await repo.create(property_id="prop-small", price=300000.0)
        await repo.create(property_id="prop-small", price=294000.0)  # 2% drop

        drops = await repo.get_properties_with_price_drops(
            threshold_percent=5.0,  # 5% threshold
            days_back=7,
        )

        # Should not detect the 2% drop when threshold is 5%
        small_drop = next((d for d in drops if d["property_id"] == "prop-small"), None)
        assert small_drop is None

    @pytest.mark.asyncio
    async def test_recorded_at_is_strictly_increasing(self, repo, frozen_clock):
        """Two snapshots taken in the same clock tick still keep their order."""
        first = await repo.create(property_id="prop-tick", price=500000.0)
        second = await repo.create(property_id="prop-tick", price=450000.0)

        assert second.recorded_at > first.recorded_at

    @pytest.mark.asyncio
    async def test_price_drop_detected_within_a_single_clock_tick(self, repo, frozen_clock):
        """A price drop is still detected when both snapshots share a timestamp."""
        await repo.create(property_id="prop-frozen", price=500000.0)
        await repo.create(property_id="prop-frozen", price=450000.0)

        drops = await repo.get_properties_with_price_drops(
            threshold_percent=5.0,
            days_back=7,
        )

        found_drop = next((d for d in drops if d["property_id"] == "prop-frozen"), None)
        assert found_drop is not None
        assert found_drop["old_price"] == 500000.0
        assert found_drop["new_price"] == 450000.0
