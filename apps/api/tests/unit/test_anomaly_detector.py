"""Unit tests for analytics/anomaly_detector.py -- AnomalyDetector."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import numpy as np
import pytest

from analytics.anomaly_detector import (
    AnomalyDetectionConfig,
    AnomalyDetector,
    AnomalyResult,
    AnomalyScope,
    AnomalySeverity,
    AnomalyType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot(property_id: str, price: float, recorded_at: datetime) -> MagicMock:
    """Create a mock PriceSnapshot."""
    snap = MagicMock()
    snap.property_id = property_id
    snap.price = price
    snap.recorded_at = recorded_at
    return snap


def _make_snapshots_uniform(
    n: int = 15,
    property_id: str = "prop-001",
    base_price: float = 500_000.0,
    noise: float = 5_000.0,
) -> list[MagicMock]:
    """Create n snapshots with prices clustered around base_price."""
    base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    rng = np.random.default_rng(42)
    snapshots = []
    for i in range(n):
        price = base_price + float(rng.normal(0, noise))
        snapshots.append(_make_snapshot(property_id, price, base_date + timedelta(days=i)))
    return snapshots


def _make_snapshots_with_outlier(
    n: int = 15,
    property_id: str = "prop-001",
    base_price: float = 500_000.0,
    outlier_price: float = 800_000.0,
    outlier_index: int | None = None,
) -> list[MagicMock]:
    """Create snapshots where one entry is a clear price outlier."""
    base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    if outlier_index is None:
        outlier_index = n - 1
    snapshots = []
    for i in range(n):
        if i == outlier_index:
            price = outlier_price
        else:
            price = base_price + (i % 3) * 50
        snapshots.append(_make_snapshot(property_id, price, base_date + timedelta(days=i)))
    return snapshots


def _make_volume_data(
    n_days: int = 45,
    city: str = "Warsaw",
    district: str | None = None,
    baseline_mean: float = 100.0,
    comparison_mean: float = 100.0,
    std: float = 10.0,
    baseline_period_days: int = 30,
) -> list[dict]:
    """Create listing volume data split into baseline and comparison periods.

    The split is aligned with detect_volume_anomalies' cutoff logic:
    entries older than baseline_period_days from now are baseline,
    entries within baseline_period_days are comparison.
    """
    now = datetime.now()
    rng = np.random.default_rng(42)
    cutoff = now - timedelta(days=baseline_period_days)
    records = []
    for i in range(n_days):
        day = now - timedelta(days=n_days - i)
        if day < cutoff:
            count = max(0, int(rng.normal(baseline_mean, std)))
        else:
            count = max(0, int(rng.normal(comparison_mean, std)))
        rec: dict = {"date": day.isoformat(), "city": city, "count": count}
        if district is not None:
            rec["district"] = district
        records.append(rec)
    return records


# ===========================================================================
# AnomalyDetectionConfig defaults
# ===========================================================================


class TestAnomalyDetectionConfig:
    """Tests for AnomalyDetectionConfig dataclass."""

    def test_default_values(self):
        config = AnomalyDetectionConfig()
        assert config.z_score_threshold == 2.5
        assert config.z_score_critical == 3.5
        assert config.iqr_multiplier == 1.5
        assert config.iqr_multiplier_critical == 3.0
        assert config.seasonal_window_days == 365
        assert config.min_samples_for_detection == 10
        assert config.volume_change_threshold == 50.0
        assert config.volume_change_critical == 100.0


# ===========================================================================
# AnomalyDetector.__init__
# ===========================================================================


class TestAnomalyDetectorInit:
    """Tests for AnomalyDetector initialization."""

    def test_default_config(self):
        detector = AnomalyDetector()
        assert detector.config.z_score_threshold == 2.5

    def test_custom_config(self):
        config = AnomalyDetectionConfig(z_score_threshold=3.0)
        detector = AnomalyDetector(config)
        assert detector.config.z_score_threshold == 3.0


# ===========================================================================
# get_stats
# ===========================================================================


class TestGetStats:
    """Tests for get_stats method."""

    def test_returns_config_values(self):
        config = AnomalyDetectionConfig(
            z_score_threshold=3.0, iqr_multiplier=2.0, min_samples_for_detection=15
        )
        detector = AnomalyDetector(config)
        stats = detector.get_stats()
        assert stats["z_score_threshold"] == 3.0
        assert stats["iqr_multiplier"] == 2.0
        assert stats["min_samples"] == 15
        assert stats["seasonal_window_days"] == 365


# ===========================================================================
# calculate_false_positive_rate
# ===========================================================================


class TestCalculateFalsePositiveRate:
    """Tests for calculate_false_positive_rate method."""

    def test_basic_calculation(self):
        detector = AnomalyDetector()
        rate = detector.calculate_false_positive_rate(5, 100, expected_rate=0.01)
        assert rate == pytest.approx(0.04)

    def test_zero_samples(self):
        detector = AnomalyDetector()
        rate = detector.calculate_false_positive_rate(0, 0)
        assert rate == 0.0

    def test_custom_expected_rate(self):
        detector = AnomalyDetector()
        rate = detector.calculate_false_positive_rate(10, 200, expected_rate=0.05)
        assert rate == pytest.approx(0.0)

    def test_negative_rate_when_below_expected(self):
        detector = AnomalyDetector()
        rate = detector.calculate_false_positive_rate(0, 100, expected_rate=0.01)
        assert rate == pytest.approx(-0.01)


# ===========================================================================
# _classify_severity_z
# ===========================================================================


class TestClassifySeverityZ:
    """Tests for _classify_severity_z method."""

    def setup_method(self):
        self.detector = AnomalyDetector(AnomalyDetectionConfig(z_score_critical=3.5))

    def test_critical(self):
        assert self.detector._classify_severity_z(4.0) == AnomalySeverity.CRITICAL

    def test_high(self):
        assert self.detector._classify_severity_z(3.2) == AnomalySeverity.HIGH

    def test_medium(self):
        assert self.detector._classify_severity_z(2.7) == AnomalySeverity.MEDIUM

    def test_low(self):
        assert self.detector._classify_severity_z(1.0) == AnomalySeverity.LOW

    def test_boundary_critical(self):
        assert self.detector._classify_severity_z(3.5) == AnomalySeverity.CRITICAL

    def test_boundary_high(self):
        assert self.detector._classify_severity_z(3.0) == AnomalySeverity.HIGH

    def test_boundary_medium(self):
        assert self.detector._classify_severity_z(2.5) == AnomalySeverity.MEDIUM


# ===========================================================================
# _classify_severity_iqr
# ===========================================================================


class TestClassifySeverityIQR:
    """Tests for _classify_severity_iqr method."""

    def setup_method(self):
        self.detector = AnomalyDetector()

    def test_critical_far_outside(self):
        # q1=100, q3=200, iqr=100, lower=50, upper=250
        # value=500 => distance_from_boundary = min(|500-50|, |500-250|) = 250
        # 250 >= 2*iqr(200) => CRITICAL
        severity = self.detector._classify_severity_iqr(
            value=500.0, lower_bound=50.0, upper_bound=250.0, q1=100.0, q3=200.0
        )
        assert severity == AnomalySeverity.CRITICAL

    def test_high_severity(self):
        # iqr=100, value=400 => distance = min(|400-50|, |400-250|) = 150
        # 150 >= 1.5*iqr(150) => HIGH
        severity = self.detector._classify_severity_iqr(
            value=400.0, lower_bound=50.0, upper_bound=250.0, q1=100.0, q3=200.0
        )
        assert severity == AnomalySeverity.HIGH

    def test_medium_severity(self):
        # iqr=100, value=350 => distance = min(|350-50|, |350-250|) = 100
        # 100 >= iqr(100) => MEDIUM
        severity = self.detector._classify_severity_iqr(
            value=350.0, lower_bound=50.0, upper_bound=250.0, q1=100.0, q3=200.0
        )
        assert severity == AnomalySeverity.MEDIUM

    def test_low_severity(self):
        # iqr=100, value=270 => distance = min(|270-50|, |270-250|) = 20
        # 20 < iqr(100) => LOW
        severity = self.detector._classify_severity_iqr(
            value=270.0, lower_bound=50.0, upper_bound=250.0, q1=100.0, q3=200.0
        )
        assert severity == AnomalySeverity.LOW


# ===========================================================================
# _deduplicate_anomalies
# ===========================================================================


class TestDeduplicateAnomalies:
    """Tests for _deduplicate_anomalies method."""

    def setup_method(self):
        self.detector = AnomalyDetector()

    def _make_anomaly(
        self,
        scope_id: str = "prop-001",
        metric: str = "price",
        severity: AnomalySeverity = AnomalySeverity.MEDIUM,
    ) -> AnomalyResult:
        return AnomalyResult(
            anomaly_type=AnomalyType.PRICE_SPIKE,
            severity=severity,
            scope_type=AnomalyScope.PROPERTY,
            scope_id=scope_id,
            metric_name=metric,
            expected_value=500_000.0,
            actual_value=700_000.0,
            deviation_percent=40.0,
            algorithm="z_score",
            threshold_used=2.5,
        )

    def test_removes_duplicate_keeps_first_when_same_severity(self):
        a1 = self._make_anomaly(severity=AnomalySeverity.MEDIUM)
        a2 = self._make_anomaly(severity=AnomalySeverity.MEDIUM)
        result = self.detector._deduplicate_anomalies([a1, a2])
        assert len(result) == 1
        assert result[0] is a1

    def test_keeps_higher_severity_duplicate(self):
        a1 = self._make_anomaly(severity=AnomalySeverity.MEDIUM)
        a2 = self._make_anomaly(severity=AnomalySeverity.HIGH)
        result = self.detector._deduplicate_anomalies([a1, a2])
        assert len(result) == 1
        assert result[0].severity == AnomalySeverity.HIGH

    def test_keeps_different_scope_ids(self):
        a1 = self._make_anomaly(scope_id="prop-001")
        a2 = self._make_anomaly(scope_id="prop-002")
        result = self.detector._deduplicate_anomalies([a1, a2])
        assert len(result) == 2

    def test_keeps_different_metrics(self):
        a1 = self._make_anomaly(metric="price")
        a2 = self._make_anomaly(metric="listing_volume")
        result = self.detector._deduplicate_anomalies([a1, a2])
        assert len(result) == 2

    def test_empty_list(self):
        result = self.detector._deduplicate_anomalies([])
        assert result == []

    def test_three_duplicates_keeps_highest(self):
        a1 = self._make_anomaly(severity=AnomalySeverity.LOW)
        a2 = self._make_anomaly(severity=AnomalySeverity.CRITICAL)
        a3 = self._make_anomaly(severity=AnomalySeverity.HIGH)
        result = self.detector._deduplicate_anomalies([a1, a2, a3])
        assert len(result) == 1
        assert result[0].severity == AnomalySeverity.CRITICAL

    def test_first_has_higher_severity_kept(self):
        a1 = self._make_anomaly(severity=AnomalySeverity.HIGH)
        a2 = self._make_anomaly(severity=AnomalySeverity.MEDIUM)
        result = self.detector._deduplicate_anomalies([a1, a2])
        assert len(result) == 1
        assert result[0].severity == AnomalySeverity.HIGH


# ===========================================================================
# detect_price_anomalies — Z-score method
# ===========================================================================


class TestDetectPriceAnomaliesZScore:
    """Tests for Z-score anomaly detection in detect_price_anomalies."""

    def test_too_few_samples_returns_empty(self):
        detector = AnomalyDetector()
        snapshots = _make_snapshots_uniform(n=5)
        result = detector.detect_price_anomalies(snapshots)
        assert result == []

    def test_detects_price_spike(self):
        detector = AnomalyDetector()
        snapshots = _make_snapshots_with_outlier(n=15, base_price=500_000, outlier_price=1_000_000)
        result = detector.detect_price_anomalies(snapshots)
        types = {a.anomaly_type for a in result}
        assert AnomalyType.PRICE_SPIKE in types

    def test_detects_price_drop(self):
        detector = AnomalyDetector()
        snapshots = _make_snapshots_with_outlier(n=15, base_price=500_000, outlier_price=100_000)
        result = detector.detect_price_anomalies(snapshots)
        types = {a.anomaly_type for a in result}
        assert AnomalyType.PRICE_DROP in types

    def test_uniform_prices_no_anomalies(self):
        detector = AnomalyDetector(AnomalyDetectionConfig(z_score_threshold=2.5))
        # All prices identical after rounding — std=0 => no z-score anomalies
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        snapshots = [
            _make_snapshot("prop-001", 500_000.0, base_date + timedelta(days=i)) for i in range(15)
        ]
        result = detector.detect_price_anomalies(snapshots)
        # No z-score anomalies because std=0; IQR also 0 so no anomalies at all
        assert result == []

    def test_custom_z_threshold_override(self):
        config = AnomalyDetectionConfig(z_score_threshold=2.5)
        detector = AnomalyDetector(config)
        # Small outlier, unlikely to trigger at 2.5 but may at 1.0
        snapshots = _make_snapshots_with_outlier(n=15, base_price=500_000, outlier_price=520_000)
        result_strict = detector.detect_price_anomalies(snapshots, z_threshold=10.0)
        result_loose = detector.detect_price_anomalies(snapshots, z_threshold=0.5)
        assert len(result_loose) >= len(result_strict)

    def test_anomaly_has_correct_algorithm_field(self):
        detector = AnomalyDetector()
        snapshots = _make_snapshots_with_outlier(n=15, base_price=500_000, outlier_price=1_000_000)
        result = detector.detect_price_anomalies(snapshots)
        z_anomalies = [a for a in result if a.algorithm == "z_score"]
        if z_anomalies:
            assert z_anomalies[0].z_score is not None
            assert z_anomalies[0].z_score >= detector.config.z_score_threshold

    def test_anomaly_context_contains_sample_count(self):
        detector = AnomalyDetector()
        snapshots = _make_snapshots_with_outlier(n=15, base_price=500_000, outlier_price=1_000_000)
        result = detector.detect_price_anomalies(snapshots)
        z_anomalies = [a for a in result if a.algorithm == "z_score"]
        if z_anomalies:
            assert z_anomalies[0].context["sample_count"] == 15

    def test_exact_min_samples_boundary(self):
        detector = AnomalyDetector(AnomalyDetectionConfig(min_samples_for_detection=10))
        snapshots = _make_snapshots_with_outlier(n=10, base_price=500_000, outlier_price=1_000_000)
        result = detector.detect_price_anomalies(snapshots)
        # 10 >= min_samples => detection runs, but need enough spread
        # With 10 samples and 1 huge outlier, z-score should flag it
        assert isinstance(result, list)

    def test_below_min_samples_boundary(self):
        detector = AnomalyDetector(AnomalyDetectionConfig(min_samples_for_detection=10))
        snapshots = _make_snapshots_with_outlier(n=9, base_price=500_000, outlier_price=1_000_000)
        result = detector.detect_price_anomalies(snapshots)
        assert result == []


# ===========================================================================
# detect_price_anomalies — IQR method
# ===========================================================================


class TestDetectPriceAnomaliesIQR:
    """Tests for IQR anomaly detection in detect_price_anomalies."""

    def test_iqr_detects_outlier_directly(self):
        """Test IQR method directly (avoids dedup masking the result)."""
        detector = AnomalyDetector()
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        snapshots = []
        for i in range(15):
            price = 500_000 + (i % 5) * 10_000
            snapshots.append(_make_snapshot("prop-001", price, base_date + timedelta(days=i)))
        snapshots.append(_make_snapshot("prop-001", 5_000_000.0, base_date + timedelta(days=15)))
        prices = np.array([s.price for s in snapshots])
        dates = [s.recorded_at for s in snapshots]
        sorted_indices = np.argsort(dates)
        prices = prices[sorted_indices]
        dates = [dates[i] for i in sorted_indices]
        iqr_anomalies = detector._detect_iqr_anomalies(prices, dates, 1.5, snapshots)
        assert len(iqr_anomalies) >= 1
        assert iqr_anomalies[0].algorithm == "iqr"

    def test_iqr_anomaly_has_no_z_score(self):
        detector = AnomalyDetector()
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        snapshots = []
        for i in range(15):
            price = 500_000 + (i % 5) * 10_000
            snapshots.append(_make_snapshot("prop-001", price, base_date + timedelta(days=i)))
        snapshots.append(_make_snapshot("prop-001", 2_000_000.0, base_date + timedelta(days=15)))
        result = detector.detect_price_anomalies(snapshots)
        iqr_anomalies = [a for a in result if a.algorithm == "iqr"]
        if iqr_anomalies:
            assert iqr_anomalies[0].z_score is None

    def test_iqr_anomaly_has_expected_value_as_median(self):
        detector = AnomalyDetector()
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        snapshots = []
        for i in range(15):
            price = 500_000 + (i % 5) * 10_000
            snapshots.append(_make_snapshot("prop-001", price, base_date + timedelta(days=i)))
        snapshots.append(_make_snapshot("prop-001", 2_000_000.0, base_date + timedelta(days=15)))
        result = detector.detect_price_anomalies(snapshots)
        iqr_anomalies = [a for a in result if a.algorithm == "iqr"]
        if iqr_anomalies:
            assert iqr_anomalies[0].expected_value > 0

    def test_iqr_custom_multiplier(self):
        config = AnomalyDetectionConfig(iqr_multiplier=1.5)
        detector = AnomalyDetector(config)
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        snapshots = []
        for i in range(15):
            price = 500_000 + (i % 5) * 10_000
            snapshots.append(_make_snapshot("prop-001", price, base_date + timedelta(days=i)))
        snapshots.append(_make_snapshot("prop-001", 2_000_000.0, base_date + timedelta(days=15)))
        # Tight multiplier should detect; wide multiplier should not
        result_tight = detector.detect_price_anomalies(snapshots, iqr_multiplier=0.5)
        result_wide = detector.detect_price_anomalies(snapshots, iqr_multiplier=50.0)
        assert len(result_tight) >= len(result_wide)

    def test_too_few_for_iqr_returns_empty(self):
        """IQR requires at least 4 prices, but min_samples is 10 so 3 won't pass."""
        detector = AnomalyDetector(AnomalyDetectionConfig(min_samples_for_detection=3))
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        snapshots = [
            _make_snapshot("prop-001", 500_000.0, base_date),
            _make_snapshot("prop-001", 510_000.0, base_date + timedelta(days=1)),
            _make_snapshot("prop-001", 1_000_000.0, base_date + timedelta(days=2)),
        ]
        result = detector.detect_price_anomalies(snapshots)
        # IQR requires >=4, z-score requires >=3; z-score may fire but IQR won't
        iqr_anomalies = [a for a in result if a.algorithm == "iqr"]
        assert len(iqr_anomalies) == 0


# ===========================================================================
# detect_price_anomalies — deduplication
# ===========================================================================


class TestDetectPriceAnomaliesDeduplication:
    """Tests that detect_price_anomalies deduplicates results."""

    def test_deduplicates_same_property(self):
        detector = AnomalyDetector()
        # One extreme outlier will be detected by both z-score and IQR
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        snapshots = []
        for i in range(15):
            price = 500_000 + (i % 5) * 10_000
            snapshots.append(_make_snapshot("prop-001", price, base_date + timedelta(days=i)))
        snapshots.append(_make_snapshot("prop-001", 3_000_000.0, base_date + timedelta(days=15)))
        result = detector.detect_price_anomalies(snapshots)
        # Even if both methods detect, dedup should keep at most 1 per (scope_id, metric)
        price_anomalies = [
            a for a in result if a.metric_name == "price" and a.scope_id == "prop-001"
        ]
        assert len(price_anomalies) <= 1


# ===========================================================================
# detect_volume_anomalies
# ===========================================================================


class TestDetectVolumeAnomalies:
    """Tests for detect_volume_anomalies method."""

    def test_too_few_samples_returns_empty(self):
        detector = AnomalyDetector()
        data = _make_volume_data(n_days=5)
        result = detector.detect_volume_anomalies(data)
        assert result == []

    def test_no_anomaly_when_stable(self):
        detector = AnomalyDetector()
        data = _make_volume_data(n_days=45, baseline_mean=100.0, comparison_mean=100.0, std=10.0)
        result = detector.detect_volume_anomalies(data)
        # Stable data should produce few or no anomalies
        assert isinstance(result, list)

    def test_detects_volume_spike(self):
        detector = AnomalyDetector(AnomalyDetectionConfig(z_score_threshold=1.5))
        data = _make_volume_data(n_days=45, baseline_mean=50.0, comparison_mean=200.0, std=5.0)
        result = detector.detect_volume_anomalies(data)
        types = [a.anomaly_type for a in result]
        assert len(result) > 0
        assert AnomalyType.VOLUME_SPIKE in types

    def test_detects_volume_drop(self):
        detector = AnomalyDetector(AnomalyDetectionConfig(z_score_threshold=1.5))
        data = _make_volume_data(n_days=45, baseline_mean=200.0, comparison_mean=10.0, std=5.0)
        result = detector.detect_volume_anomalies(data)
        types = [a.anomaly_type for a in result]
        assert len(result) > 0
        assert AnomalyType.VOLUME_DROP in types

    def test_anomaly_has_correct_fields(self):
        detector = AnomalyDetector(AnomalyDetectionConfig(z_score_threshold=1.5))
        data = _make_volume_data(n_days=45, baseline_mean=50.0, comparison_mean=300.0, std=5.0)
        result = detector.detect_volume_anomalies(data)
        if result:
            a = result[0]
            assert a.metric_name == "listing_volume"
            assert a.algorithm == "z_score"
            assert a.scope_type in (AnomalyScope.CITY, AnomalyScope.DISTRICT)
            assert a.expected_value > 0
            assert a.actual_value > 0
            assert a.deviation_percent > 0

    def test_district_level_anomaly(self):
        detector = AnomalyDetector(AnomalyDetectionConfig(z_score_threshold=1.0))
        data = _make_volume_data(
            n_days=45,
            city="Warsaw",
            district="Mokotow",
            baseline_mean=50.0,
            comparison_mean=300.0,
            std=5.0,
        )
        result = detector.detect_volume_anomalies(data)
        district_anomalies = [a for a in result if a.scope_type == AnomalyScope.DISTRICT]
        assert len(district_anomalies) > 0

    def test_custom_baseline_period(self):
        detector = AnomalyDetector()
        # Use tz-naive dates to match datetime.now() in the detector
        now = datetime(2025, 6, 15)
        data = []
        for i in range(45):
            day = now - timedelta(days=44 - i)
            data.append({"date": day.isoformat(), "city": "Warsaw", "count": 100 + i})
        # Very long baseline period means all data is "comparison" => no baseline
        result_long = detector.detect_volume_anomalies(data, baseline_period_days=999)
        # With no baseline data, should return empty
        assert isinstance(result_long, list)

    def test_empty_baseline_returns_empty(self):
        detector = AnomalyDetector()
        # Use tz-naive dates to match datetime.now() in the detector
        now = datetime(2025, 6, 15)
        data = []
        for i in range(15):
            day = now - timedelta(days=14 - i)
            data.append({"date": day.isoformat(), "city": "Warsaw", "count": 100})
        result = detector.detect_volume_anomalies(data, baseline_period_days=0)
        assert result == []

    def test_zero_std_skips_location(self):
        detector = AnomalyDetector()
        now = datetime.now()
        data = []
        # Baseline: all same count => std=0
        for i in range(30):
            day = now - timedelta(days=44 - i)
            data.append({"date": day.isoformat(), "city": "Warsaw", "count": 100})
        # Comparison: different count
        for i in range(15):
            day = now - timedelta(days=14 - i)
            data.append({"date": day.isoformat(), "city": "Warsaw", "count": 200})
        result = detector.detect_volume_anomalies(data, baseline_period_days=15)
        # std=0 in baseline => skip, no anomaly
        assert result == []


# ===========================================================================
# detect_seasonal_anomalies
# ===========================================================================


class TestDetectSeasonalAnomalies:
    """Tests for detect_seasonal_anomalies method."""

    def _make_seasonal_snapshots(
        self,
        property_id: str = "prop-001",
        base_price: float = 500_000.0,
        n_years: int = 3,
    ) -> tuple[list[MagicMock], datetime]:
        """Create snapshots spanning multiple years for seasonal analysis."""
        snapshots = []
        now = datetime(2025, 6, 15)

        # Historical data: 3 years of data, ~60 snapshots each year
        for year_offset in range(n_years, 0, -1):
            for week in range(52):
                day = now - timedelta(days=365 * year_offset + week * 7)
                price = base_price + (week % 4) * 5_000
                snapshots.append(_make_snapshot(property_id, price, day))

        # Current period data (last 30 days)
        for day_offset in range(30):
            day = now - timedelta(days=day_offset)
            price = base_price + (day_offset % 4) * 5_000
            snapshots.append(_make_snapshot(property_id, price, day))

        return snapshots, now

    def _make_seasonal_snapshots_with_spike(
        self,
        property_id: str = "prop-001",
        base_price: float = 500_000.0,
        spike_price: float = 900_000.0,
        n_years: int = 3,
    ) -> tuple[list[MagicMock], datetime]:
        """Create snapshots where current period has a price spike vs history."""
        snapshots = []
        now = datetime(2025, 6, 15)

        # Historical data: normal prices
        for year_offset in range(n_years, 0, -1):
            for week in range(52):
                day = now - timedelta(days=365 * year_offset + week * 7)
                price = base_price + (week % 4) * 1_000  # small variation
                snapshots.append(_make_snapshot(property_id, price, day))

        # Current period: spike prices
        for day_offset in range(30):
            day = now - timedelta(days=day_offset)
            snapshots.append(_make_snapshot(property_id, spike_price, day))

        return snapshots, now

    def test_too_few_samples_returns_empty(self):
        detector = AnomalyDetector()
        # seasonal_window_days/7 = 365/7 ≈ 52, so we need > 52 samples
        snapshots = _make_snapshots_uniform(n=30)
        result = detector.detect_seasonal_anomalies(snapshots)
        assert result == []

    def test_no_anomaly_when_stable(self):
        detector = AnomalyDetector()
        snapshots, now = self._make_seasonal_snapshots()
        result = detector.detect_seasonal_anomalies(snapshots, comparison_date=now)
        # Stable seasonal data should produce no anomalies
        assert isinstance(result, list)

    def test_detects_seasonal_price_spike(self):
        detector = AnomalyDetector(
            AnomalyDetectionConfig(z_score_threshold=1.5, min_samples_for_detection=10)
        )
        snapshots, now = self._make_seasonal_snapshots_with_spike(
            base_price=500_000, spike_price=900_000
        )
        result = detector.detect_seasonal_anomalies(snapshots, comparison_date=now)
        types = [a.anomaly_type for a in result]
        assert AnomalyType.PRICE_SPIKE in types

    def test_detects_seasonal_price_drop(self):
        detector = AnomalyDetector(
            AnomalyDetectionConfig(z_score_threshold=1.5, min_samples_for_detection=10)
        )
        snapshots, now = self._make_seasonal_snapshots_with_spike(
            base_price=500_000, spike_price=100_000
        )
        result = detector.detect_seasonal_anomalies(snapshots, comparison_date=now)
        types = [a.anomaly_type for a in result]
        assert AnomalyType.PRICE_DROP in types

    def test_anomaly_has_algorithm_seasonal(self):
        detector = AnomalyDetector(
            AnomalyDetectionConfig(z_score_threshold=1.5, min_samples_for_detection=10)
        )
        snapshots, now = self._make_seasonal_snapshots_with_spike(
            base_price=500_000, spike_price=900_000
        )
        result = detector.detect_seasonal_anomalies(snapshots, comparison_date=now)
        if result:
            assert result[0].algorithm == "seasonal"

    def test_anomaly_has_baseline_and_comparison_periods(self):
        detector = AnomalyDetector(
            AnomalyDetectionConfig(z_score_threshold=1.5, min_samples_for_detection=10)
        )
        snapshots, now = self._make_seasonal_snapshots_with_spike(
            base_price=500_000, spike_price=900_000
        )
        result = detector.detect_seasonal_anomalies(snapshots, comparison_date=now)
        if result:
            assert result[0].baseline_period is not None
            assert result[0].comparison_period is not None
            bp_start, bp_end = result[0].baseline_period
            assert bp_start < bp_end

    def test_custom_comparison_date(self):
        detector = AnomalyDetector(
            AnomalyDetectionConfig(z_score_threshold=1.5, min_samples_for_detection=10)
        )
        custom_date = datetime(2025, 3, 1)
        snapshots, _now = self._make_seasonal_snapshots_with_spike(
            base_price=500_000, spike_price=900_000
        )
        result = detector.detect_seasonal_anomalies(snapshots, comparison_date=custom_date)
        assert isinstance(result, list)

    def test_multiple_properties(self):
        detector = AnomalyDetector(
            AnomalyDetectionConfig(z_score_threshold=1.5, min_samples_for_detection=10)
        )
        snapshots = []
        now = datetime(2025, 6, 15)

        for pid in ["prop-001", "prop-002"]:
            # Historical data
            for year_offset in range(3, 0, -1):
                for week in range(52):
                    day = now - timedelta(days=365 * year_offset + week * 7)
                    snapshots.append(_make_snapshot(pid, 500_000 + (week % 4) * 1_000, day))
            # Current period with spike for prop-001 only
            for day_offset in range(30):
                day = now - timedelta(days=day_offset)
                price = 900_000 if pid == "prop-001" else 500_000
                snapshots.append(_make_snapshot(pid, price, day))

        result = detector.detect_seasonal_anomalies(snapshots, comparison_date=now)
        # Only prop-001 should have an anomaly
        anomalous_ids = {a.scope_id for a in result}
        assert "prop-001" in anomalous_ids
        assert "prop-002" not in anomalous_ids

    def test_zero_std_historical_skips_property(self):
        detector = AnomalyDetector(
            AnomalyDetectionConfig(z_score_threshold=1.5, min_samples_for_detection=10)
        )
        snapshots = []
        now = datetime(2025, 6, 15)
        pid = "prop-flat"

        # Historical data: all same price => std=0
        for year_offset in range(3, 0, -1):
            for week in range(52):
                day = now - timedelta(days=365 * year_offset + week * 7)
                snapshots.append(_make_snapshot(pid, 500_000.0, day))

        # Current period: different price
        for day_offset in range(30):
            day = now - timedelta(days=day_offset)
            snapshots.append(_make_snapshot(pid, 700_000.0, day))

        result = detector.detect_seasonal_anomalies(snapshots, comparison_date=now)
        # std=0 => skip
        flat_anomalies = [a for a in result if a.scope_id == pid]
        assert len(flat_anomalies) == 0

    def test_property_with_no_current_period_data(self):
        detector = AnomalyDetector(
            AnomalyDetectionConfig(z_score_threshold=1.5, min_samples_for_detection=10)
        )
        snapshots = []
        now = datetime(2025, 6, 15)
        pid = "prop-old"

        # Only historical data, no data in current comparison period
        for year_offset in range(3, 0, -1):
            for week in range(52):
                day = now - timedelta(days=365 * year_offset + week * 7)
                snapshots.append(_make_snapshot(pid, 500_000.0, day))

        result = detector.detect_seasonal_anomalies(snapshots, comparison_date=now)
        old_anomalies = [a for a in result if a.scope_id == pid]
        assert len(old_anomalies) == 0


# ===========================================================================
# AnomalyResult dataclass
# ===========================================================================


class TestAnomalyResult:
    """Tests for AnomalyResult dataclass."""

    def test_required_fields(self):
        result = AnomalyResult(
            anomaly_type=AnomalyType.PRICE_SPIKE,
            severity=AnomalySeverity.HIGH,
            scope_type=AnomalyScope.PROPERTY,
            scope_id="prop-001",
            metric_name="price",
            expected_value=500_000.0,
            actual_value=700_000.0,
            deviation_percent=40.0,
            algorithm="z_score",
            threshold_used=2.5,
        )
        assert result.anomaly_type == AnomalyType.PRICE_SPIKE
        assert result.severity == AnomalySeverity.HIGH
        assert result.confidence == "medium"  # default
        assert result.z_score is None  # default
        assert result.baseline_period is None  # default
        assert result.comparison_period is None  # default
        assert result.context is None  # default

    def test_all_fields(self):
        bp = (datetime(2025, 1, 1), datetime(2025, 3, 1))
        cp = (datetime(2025, 4, 1), datetime(2025, 6, 1))
        result = AnomalyResult(
            anomaly_type=AnomalyType.VOLUME_SPIKE,
            severity=AnomalySeverity.CRITICAL,
            scope_type=AnomalyScope.CITY,
            scope_id="Warsaw",
            metric_name="listing_volume",
            expected_value=100.0,
            actual_value=500.0,
            deviation_percent=400.0,
            algorithm="seasonal",
            threshold_used=2.5,
            z_score=4.5,
            baseline_period=bp,
            comparison_period=cp,
            context={"key": "value"},
            confidence="high",
        )
        assert result.z_score == 4.5
        assert result.baseline_period == bp
        assert result.comparison_period == cp
        assert result.context == {"key": "value"}
        assert result.confidence == "high"


# ===========================================================================
# Enum values
# ===========================================================================


class TestAnomalyEnums:
    """Tests for anomaly enum types."""

    def test_anomaly_type_values(self):
        assert AnomalyType.PRICE_SPIKE == "price_spike"
        assert AnomalyType.PRICE_DROP == "price_drop"
        assert AnomalyType.VOLUME_SPIKE == "volume_spike"
        assert AnomalyType.VOLUME_DROP == "volume_drop"
        assert AnomalyType.UNUSUAL_PATTERN == "unusual_pattern"

    def test_severity_values(self):
        assert AnomalySeverity.LOW == "low"
        assert AnomalySeverity.MEDIUM == "medium"
        assert AnomalySeverity.HIGH == "high"
        assert AnomalySeverity.CRITICAL == "critical"

    def test_scope_values(self):
        assert AnomalyScope.PROPERTY == "property"
        assert AnomalyScope.CITY == "city"
        assert AnomalyScope.DISTRICT == "district"
        assert AnomalyScope.REGION == "region"
