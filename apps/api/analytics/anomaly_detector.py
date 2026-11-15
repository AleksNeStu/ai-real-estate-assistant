"""
Market anomaly detection algorithms.

This module provides statistical methods for detecting unusual market conditions
including price spikes, drops, and volume anomalies, and seasonal adjustments.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from db.models import PriceSnapshot


class AnomalyType(str, Enum):
    """Types of market anomalies."""

    PRICE_SPIKE = "price_spike"
    PRICE_DROP = "price_drop"
    VOLUME_SPIKE = "volume_spike"
    VOLUME_DROP = "volume_drop"
    UNUSUAL_PATTERN = "unusual_pattern"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyScope(str, Enum):
    """Scope of the anomaly."""

    PROPERTY = "property"
    CITY = "city"
    DISTRICT = "district"
    REGION = "region"


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""

    anomaly_type: AnomalyType
    severity: AnomalySeverity
    scope_type: AnomalyScope
    scope_id: str
    metric_name: str
    expected_value: float
    actual_value: float
    deviation_percent: float
    algorithm: str  # z_score, iqr, seasonal - NO DEFAULT - REQUIRED
    threshold_used: float
    z_score: Optional[float] = None
    baseline_period: Optional[Tuple[datetime, datetime]] = None
    comparison_period: Optional[Tuple[datetime, datetime]] = None
    context: Optional[dict] = None
    confidence: str = "medium"  # high, medium, low - HAS DEFAULT


@dataclass
class AnomalyDetectionConfig:
    """Configuration for anomaly detection."""

    # Z-score thresholds
    z_score_threshold: float = 2.5  # anomalies above this are flagged
    z_score_critical: float = 3.5  # anomalies above this are critical

    # IQR thresholds
    iqr_multiplier: float = 1.5  # values outside IQR * multiplier are flagged
    iqr_multiplier_critical: float = 3.0  # values outside IQR * multiplier are critical

    # Seasonal adjustment
    seasonal_window_days: int = 365  # days of data for seasonal patterns
    min_samples_for_detection: int = 10  # minimum samples needed

    # Volume anomaly thresholds
    volume_change_threshold: float = 50.0  # % change in listing volume
    volume_change_critical: float = 100.0  # % change for critical


class AnomalyDetector:
    """
    Detector for market anomalies using statistical methods.

    Uses multiple algorithms:
    - Z-score analysis for outlier detection
    - IQR (Interquartile Range) for robust outlier detection
    - Seasonal decomposition for time-series patterns
    """

    def __init__(self, config: Optional[AnomalyDetectionConfig] = None):
        self.config = config or AnomalyDetectionConfig()

    def detect_price_anomalies(
        self,
        snapshots: List[PriceSnapshot],
        z_threshold: Optional[float] = None,
        iqr_multiplier: Optional[float] = None,
    ) -> List[AnomalyResult]:
        """
        Detect price anomalies using Z-score and IQR methods.

        Args:
            snapshots: List of price snapshots to analyze
            z_threshold: Z-score threshold (overrides config)
            iqr_multiplier: IQR multiplier (overrides config)

        Returns:
            List of detected anomalies
        """
        if len(snapshots) < self.config.min_samples_for_detection:
            return []

        z_thresh = z_threshold or self.config.z_score_threshold
        iqr_mult = iqr_multiplier or self.config.iqr_multiplier

        # Extract prices and sort by date
        prices = np.array([s.price for s in snapshots])
        dates = [s.recorded_at for s in snapshots]

        # Sort by date
        sorted_indices = np.argsort(np.array(dates))
        prices = prices[sorted_indices]
        dates = [dates[i] for i in sorted_indices]

        anomalies = []

        # Z-score detection
        z_anomalies = self._detect_z_score_anomalies(prices, dates, z_thresh, snapshots)
        anomalies.extend(z_anomalies)

        # IQR detection
        iqr_anomalies = self._detect_iqr_anomalies(prices, dates, iqr_mult, snapshots)
        anomalies.extend(iqr_anomalies)

        # Remove duplicates (same property detected by multiple methods)
        unique_anomalies = self._deduplicate_anomalies(anomalies)

        return unique_anomalies

    def _detect_z_score_anomalies(
        self,
        prices: np.ndarray,
        dates: List,
        threshold: float,
        snapshots: List[PriceSnapshot],
    ) -> List[AnomalyResult]:
        """Detect anomalies using Z-score method."""
        if len(prices) < 3:
            return []

        anomalies = []
        mean = np.mean(prices)
        std = np.std(prices)

        if std == 0:
            return []

        # Calculate Z-scores
        z_scores = np.abs((prices - mean) / std)

        # Find anomalies
        for i, (z_score, price, date) in enumerate(zip(z_scores, prices, dates, strict=True)):
            if z_score >= threshold:
                snapshot = snapshots[i]
                severity = self._classify_severity_z(z_score)

                anomalies.append(
                    AnomalyResult(
                        anomaly_type=AnomalyType.PRICE_SPIKE
                        if price > mean
                        else AnomalyType.PRICE_DROP,
                        severity=severity,
                        scope_type=AnomalyScope.PROPERTY,
                        scope_id=snapshot.property_id,
                        metric_name="price",
                        expected_value=float(mean),
                        actual_value=float(price),
                        deviation_percent=float(abs(price - mean) / mean * 100),
                        z_score=float(z_score),
                        confidence="high" if z_score >= 3 else "medium",
                        algorithm="z_score",
                        threshold_used=threshold,
                        context={
                            "property_id": snapshot.property_id,
                            "recorded_at": str(date),
                            "sample_count": len(prices),
                            "baseline_mean": float(mean),
                            "baseline_std": float(std),
                        },
                    )
                )

        return anomalies

    def _detect_iqr_anomalies(
        self,
        prices: np.ndarray,
        dates: List,
        multiplier: float,
        snapshots: List[PriceSnapshot],
    ) -> List[AnomalyResult]:
        """Detect anomalies using IQR method."""
        if len(prices) < 4:
            return []

        anomalies = []

        # Calculate quartiles
        q1 = np.percentile(prices, 25)
        q3 = np.percentile(prices, 75)
        iqr = q3 - q1

        # Define bounds
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr

        # Find anomalies
        for i, (price, date) in enumerate(zip(prices, dates, strict=True)):
            if price < lower_bound or price > upper_bound:
                snapshot = snapshots[i]
                severity = self._classify_severity_iqr(price, lower_bound, upper_bound, q1, q3)

                anomalies.append(
                    AnomalyResult(
                        anomaly_type=AnomalyType.PRICE_SPIKE
                        if price > upper_bound
                        else AnomalyType.PRICE_DROP,
                        severity=severity,
                        scope_type=AnomalyScope.PROPERTY,
                        scope_id=snapshot.property_id,
                        metric_name="price",
                        expected_value=float((q1 + q3) / 2),  # median
                        actual_value=float(price),
                        deviation_percent=float(abs(price - (q1 + q3) / 2) / ((q1 + q3) / 2) * 100),
                        z_score=None,
                        confidence="high",
                        algorithm="iqr",
                        threshold_used=multiplier,
                        context={
                            "property_id": snapshot.property_id,
                            "recorded_at": str(date),
                            "lower_bound": float(lower_bound),
                            "upper_bound": float(upper_bound),
                        },
                    )
                )

        return anomalies

    def detect_volume_anomalies(
        self,
        listing_counts: List[dict],
        baseline_period_days: int = 30,
    ) -> List[AnomalyResult]:
        """
        Detect anomalies in listing volume.

        Args:
            listing_counts: List of dicts with 'date', 'city', 'count', 'district' (optional)
            baseline_period_days: Days to use as baseline for comparison

        Returns:
            List of detected volume anomalies
        """
        if len(listing_counts) < self.config.min_samples_for_detection:
            return []

        # Convert to DataFrame
        df = pd.DataFrame(listing_counts)
        df["date"] = pd.to_datetime(df["date"])

        # Calculate baseline
        cutoff_date = datetime.now() - timedelta(days=baseline_period_days)
        baseline_df = df[df["date"] < cutoff_date]
        comparison_df = df[df["date"] >= cutoff_date]

        if len(baseline_df) == 0 or len(comparison_df) == 0:
            return []

        anomalies = []

        # Group by location
        groupings: list[list[str]] = [["city"]]
        if "district" in df.columns:
            groupings.append(["city", "district"])
        for group_cols in groupings:
            # Calculate baseline statistics
            baseline_stats = baseline_df.groupby(group_cols)["count"].agg(["mean", "std"])
            comparison_stats = comparison_df.groupby(group_cols)["count"].agg(["mean"])

            # Compare
            for idx, row in comparison_stats.iterrows():
                location_value = idx if isinstance(idx, tuple) else (idx,)
                location_id = str(location_value)

                if idx not in baseline_stats.index:
                    continue

                baseline_row = baseline_stats.loc[idx]
                baseline_mean = baseline_row["mean"]
                baseline_std = baseline_row.get("std", 0)

                if baseline_std == 0:
                    continue

                comparison_mean = row["mean"]
                change_percent = ((comparison_mean - baseline_mean) / baseline_mean) * 100

                # Z-score for volume
                z_score = abs(comparison_mean - baseline_mean) / baseline_std

                if z_score >= self.config.z_score_threshold:
                    scope_type = (
                        AnomalyScope.CITY if len(group_cols) == 1 else AnomalyScope.DISTRICT
                    )

                    severity = self._classify_severity_z(z_score)

                    anomalies.append(
                        AnomalyResult(
                            anomaly_type=AnomalyType.VOLUME_SPIKE
                            if change_percent > 0
                            else AnomalyType.VOLUME_DROP,
                            severity=severity,
                            scope_type=scope_type,
                            scope_id=location_id,
                            metric_name="listing_volume",
                            expected_value=float(baseline_mean),
                            actual_value=float(comparison_mean),
                            deviation_percent=float(abs(change_percent)),
                            z_score=float(z_score),
                            confidence="high" if z_score >= 3 else "medium",
                            algorithm="z_score",
                            threshold_used=self.config.z_score_threshold,
                            context={
                                "baseline_period_days": baseline_period_days,
                                "group_cols": group_cols,
                            },
                        )
                    )

        return anomalies

    def detect_seasonal_anomalies(
        self,
        snapshots: List[PriceSnapshot],
        comparison_date: Optional[datetime] = None,
    ) -> List[AnomalyResult]:
        """
        Detect anomalies adjusted for seasonal patterns.

        Uses historical data to establish seasonal baseline and detects
        deviations from expected seasonal values.

        Args:
            snapshots: List of price snapshots
            comparison_date: Date to compare against (defaults to now)

        Returns:
            List of detected seasonal anomalies
        """
        if len(snapshots) < self.config.seasonal_window_days / 7:
            return []

        comparison_date = comparison_date or datetime.now()

        # Extract prices and dates
        df = pd.DataFrame(
            [
                {"date": s.recorded_at, "price": s.price, "property_id": s.property_id}
                for s in snapshots
            ]
        )
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        # Get comparison period data
        comparison_start = comparison_date - timedelta(days=30)
        _comparison_df = df[df["date"] >= comparison_start]  # noqa: F841

        # Get historical data for same period in previous years
        anomalies = []

        for property_id in df["property_id"].unique():
            prop_df = df[df["property_id"] == property_id]

            if len(prop_df) < self.config.min_samples_for_detection:
                continue

            # Get comparison period prices
            current_prices = prop_df[prop_df["date"] >= comparison_start]["price"].values

            if len(current_prices) == 0:
                continue

            # Get historical prices for same months in previous years
            historical_prices = []
            for year_offset in range(1, 4):  # Look at up to 3 years back
                hist_start = comparison_start - timedelta(days=365 * year_offset)
                hist_end = comparison_date - timedelta(days=365 * year_offset)
                hist_prices = prop_df[
                    (prop_df["date"] >= hist_start) & (prop_df["date"] < hist_end)
                ]["price"].values
                historical_prices.extend(hist_prices)

            if len(historical_prices) < self.config.min_samples_for_detection:
                continue

            # Calculate expected seasonal value
            expected_mean = np.mean(historical_prices)
            expected_std = np.std(historical_prices)

            if expected_std == 0:
                continue

            # Compare current to expected
            current_mean = np.mean(current_prices)
            z_score = abs(current_mean - expected_mean) / expected_std

            if z_score >= self.config.z_score_threshold:
                severity = self._classify_severity_z(z_score)

                anomalies.append(
                    AnomalyResult(
                        anomaly_type=AnomalyType.PRICE_SPIKE
                        if current_mean > expected_mean
                        else AnomalyType.PRICE_DROP,
                        severity=severity,
                        scope_type=AnomalyScope.PROPERTY,
                        scope_id=property_id,
                        metric_name="seasonal_adjusted_price",
                        expected_value=float(expected_mean),
                        actual_value=float(current_mean),
                        deviation_percent=float(
                            abs(current_mean - expected_mean) / expected_mean * 100
                        ),
                        z_score=float(z_score),
                        confidence="high" if len(historical_prices) >= 20 else "medium",
                        algorithm="seasonal",
                        threshold_used=self.config.z_score_threshold,
                        baseline_period=(
                            comparison_start - timedelta(days=365 * 3),
                            comparison_start - timedelta(days=365),
                        ),
                        comparison_period=(comparison_start, comparison_date),
                        context={
                            "property_id": property_id,
                            "historical_years": len(historical_prices) // 30,
                        },
                    )
                )

        return anomalies

    def _classify_severity_z(self, z_score: float) -> AnomalySeverity:
        """Classify anomaly severity based on Z-score."""
        if z_score >= self.config.z_score_critical:
            return AnomalySeverity.CRITICAL
        elif z_score >= 3.0:
            return AnomalySeverity.HIGH
        elif z_score >= 2.5:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def _classify_severity_iqr(
        self,
        value: float,
        lower_bound: float,
        upper_bound: float,
        q1: float,
        q3: float,
    ) -> AnomalySeverity:
        """Classify anomaly severity based on IQR distance."""
        iqr = q3 - q1
        distance_from_boundary = min(abs(value - lower_bound), abs(value - upper_bound))

        # Severity based on how far outside the IQR bounds
        if distance_from_boundary >= 2 * iqr:
            return AnomalySeverity.CRITICAL
        elif distance_from_boundary >= 1.5 * iqr:
            return AnomalySeverity.HIGH
        elif distance_from_boundary >= iqr:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def _deduplicate_anomalies(
        self,
        anomalies: List[AnomalyResult],
    ) -> List[AnomalyResult]:
        """Remove duplicate anomalies for the same property."""
        seen = {}
        unique = []

        for anomaly in anomalies:
            key = (anomaly.scope_id, anomaly.metric_name)

            if key not in seen:
                seen[key] = anomaly
                unique.append(anomaly)
            else:
                # Keep the one with higher severity
                existing = seen[key]
                severity_order = [
                    AnomalySeverity.LOW,
                    AnomalySeverity.MEDIUM,
                    AnomalySeverity.HIGH,
                    AnomalySeverity.CRITICAL,
                ]
                if severity_order.index(anomaly.severity) > severity_order.index(existing.severity):
                    # Replace with higher severity
                    unique.remove(existing)
                    unique.append(anomaly)
                    seen[key] = anomaly

        return unique

    def calculate_false_positive_rate(
        self,
        detected_anomalies: int,
        total_samples: int,
        expected_rate: float = 0.01,  # 1% expected
    ) -> float:
        """
        Calculate the false positive rate for validation.

        Args:
            detected_anomalies: Number of anomalies detected
            total_samples: Total samples analyzed
            expected_rate: Expected false positive rate (default 1%)

        Returns:
            Estimated false positive rate
        """
        if total_samples == 0:
            return 0.0

        return detected_anomalies / total_samples - expected_rate

    def get_stats(self) -> dict:
        """
        Get overall statistics for the detector.

        Returns:
            Dict with detection statistics
        """
        return {
            "z_score_threshold": self.config.z_score_threshold,
            "iqr_multiplier": self.config.iqr_multiplier,
            "min_samples": self.config.min_samples_for_detection,
            "seasonal_window_days": self.config.seasonal_window_days,
        }
