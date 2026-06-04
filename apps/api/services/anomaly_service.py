"""
Service for detecting and managing market anomalies.

This service provides high-level business logic for:
- Running scheduled anomaly detection
- Storing and retrieving anomalies from the database
- Triggering alerts for significant anomalies
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from analytics.anomaly_detector import AnomalyDetector
from core.security_utils import sanitize_for_log
from db.repositories import AnomalyRepository, PriceSnapshotRepository
from db.schemas import (
    AnomalyListResponse,
    AnomalyResponse,
)
from notifications.alert_manager import AlertManager

logger = logging.getLogger(__name__)


class AnomalyService:
    """Service for detecting and managing market anomalies."""

    def __init__(
        self,
        anomaly_repo: AnomalyRepository,
        price_snapshot_repo: PriceSnapshotRepository,
        alert_manager: Optional[AlertManager] = None,
    ):
        self.anomaly_repo = anomaly_repo
        self.price_snapshot_repo = price_snapshot_repo
        self.alert_manager = alert_manager
        self.detector = AnomalyDetector()

    async def run_daily_analysis(self) -> dict[str, Any]:
        """Run daily batch analysis of all market data.

        Returns:
            Dict with counts of anomalies detected by type
        """
        logger.info("Starting daily anomaly analysis")
        results: dict[str, Any] = {
            "price_anomalies": 0,
            "volume_anomalies": 0,
            "total_anomalies": 0,
            "alerts_sent": 0,
            "errors": [],
        }

        try:
            # 1. Analyze price anomalies for properties
            price_anomalies = await self._analyze_property_price_anomalies()
            results["price_anomalies"] = price_anomalies

            # 2. Analyze volume anomalies by city
            volume_anomalies = await self._analyze_volume_anomalies()
            results["volume_anomalies"] = volume_anomalies

            # 3. Store anomalies in database
            all_anomalies = price_anomalies + volume_anomalies
            results["total_anomalies"] = len(all_anomalies)

            # 4. Send alerts for high/critical anomalies
            if self.alert_manager:
                alerts_sent = await self._send_anomaly_alerts(all_anomalies)
                results["alerts_sent"] = alerts_sent

            logger.info("Daily analysis complete: %s", sanitize_for_log(results))

        except Exception as e:
            logger.error("Error in daily analysis: %s", sanitize_for_log(e))
            results["errors"].append(str(e))

        return results

    async def _analyze_property_price_anomalies(self) -> list[dict[str, Any]]:
        """Analyze price anomalies for individual properties."""
        # Get all property IDs with recent snapshots
        # Group by property_id and get latest snapshots
        anomalies = []

        # Get all snapshots from the past 30 days
        cutoff_date = datetime.now(UTC) - timedelta(days=30)
        snapshots = await self.price_snapshot_repo.get_snapshots_in_period(
            cutoff_date, datetime.now(UTC)
        )

        if not snapshots:
            return anomalies

        # Group by property
        property_snapshots: dict[str, list] = {}
        for snap in snapshots:
            if snap.property_id not in property_snapshots:
                property_snapshots[snap.property_id] = []
            property_snapshots[snap.property_id].append(snap)

        # Detect anomalies for each property
        for _prop_id, prop_snaps in property_snapshots.items():
            if len(prop_snaps) < 10:  # Need minimum samples
                continue

            # Sort by recorded_at
            prop_snaps.sort(key=lambda x: x.recorded_at)

            # Detect anomalies
            detected = self.detector.detect_price_anomalies(prop_snaps)

            for anomaly in detected:
                # Store in database
                db_anomaly = await self.anomaly_repo.create(
                    anomaly_type=anomaly.anomaly_type.value,
                    severity=anomaly.severity.value,
                    scope_type=anomaly.scope_type.value,
                    scope_id=anomaly.scope_id,
                    algorithm=anomaly.algorithm,
                    threshold_used=anomaly.threshold_used,
                    metric_name=anomaly.metric_name,
                    expected_value=anomaly.expected_value,
                    actual_value=anomaly.actual_value,
                    deviation_percent=anomaly.deviation_percent,
                    z_score=anomaly.z_score,
                    context=anomaly.context,
                )
                anomalies.append(
                    {
                        "id": db_anomaly.id,
                        "type": db_anomaly.anomaly_type,
                        "severity": db_anomaly.severity,
                        "scope_id": db_anomaly.scope_id,
                    }
                )

        return anomalies

    async def _analyze_volume_anomalies(self) -> list[dict[str, Any]]:
        """Analyze volume anomalies by city/district."""
        # This would require property listing data which we can get from ChromaDB
        # For now, return empty list as this requires integration with property data
        return []

    async def _send_anomaly_alerts(self, anomalies: list[dict[str, Any]]) -> int:
        """Send alerts for high/critical anomalies via AlertManager."""
        if not self.alert_manager:
            return 0

        from notifications.alert_manager import Alert, AlertType

        alerts_sent = 0
        for anomaly in anomalies:
            # Only send alerts for high/critical severity
            if anomaly.get("severity") not in ("high", "critical"):
                continue

            try:
                anomaly_id = anomaly.get("id", "unknown")
                anomaly_type = anomaly.get("type", "unknown")
                severity = anomaly.get("severity", "unknown")
                scope_id = anomaly.get("scope_id", "unknown")

                alert = Alert(
                    alert_type=AlertType.ANOMALY,
                    user_email="",  # AlertManager queues for broadcast; consumers handle routing
                    subject=f"Market Anomaly Detected: {anomaly_type} ({severity})",
                    message=f"A {severity} {anomaly_type} anomaly was detected for {scope_id}. "
                    f"Anomaly ID: {anomaly_id}",
                    data={
                        "anomaly_id": anomaly_id,
                        "anomaly_type": anomaly_type,
                        "severity": severity,
                        "scope_id": scope_id,
                    },
                    priority=1 if severity == "critical" else 2,
                )
                self.alert_manager.queue_alert(alert)

                await self.anomaly_repo.mark_alert_sent(anomaly_id)
                alerts_sent += 1
            except Exception as e:
                logger.error(
                    "Error sending alert for anomaly %s: %s",
                    sanitize_for_log(anomaly.get("id", "?")),
                    sanitize_for_log(e),
                )

        return alerts_sent

    async def get_anomalies(
        self,
        limit: int = 50,
        offset: int = 0,
        severity_filter: Optional[str] = None,
        anomaly_type_filter: Optional[str] = None,
        scope_type_filter: Optional[str] = None,
        scope_id_filter: Optional[str] = None,
    ) -> AnomalyListResponse:
        """Get anomalies with filters."""
        anomalies = await self.anomaly_repo.get_recent(
            limit=limit,
            severity_filter=severity_filter,
            anomaly_type_filter=anomaly_type_filter,
        )

        # Apply additional filters
        if scope_type_filter:
            anomalies = [a for a in anomalies if a.scope_type == scope_type_filter]
        if scope_id_filter:
            anomalies = [a for a in anomalies if a.scope_id == scope_id_filter]

        # Convert to response models
        anomaly_responses = [AnomalyResponse.model_validate(a) for a in anomalies]

        return AnomalyListResponse(
            anomalies=anomaly_responses,
            total=len(anomaly_responses),
            limit=limit,
            offset=offset,
        )

    async def get_anomaly_by_id(self, anomaly_id: str) -> Optional[dict[str, Any]]:
        """Get a single anomaly by ID."""
        anomaly = await self.anomaly_repo.get_by_id(anomaly_id)
        if not anomaly:
            return None
        return anomaly.__dict__

    async def dismiss_anomaly(self, anomaly_id: str, dismissed_by: Optional[str] = None) -> bool:
        """Dismiss an anomaly.

        Returns:
            True if anomaly was found and dismissed, False if not found.
        """
        try:
            # First check if anomaly exists
            anomaly = await self.anomaly_repo.get_by_id(anomaly_id)
            if not anomaly:
                return False
            await self.anomaly_repo.dismiss(anomaly_id, dismissed_by)
            return True
        except Exception as e:
            logger.error(
                "Error dismissing anomaly %s: %s", sanitize_for_log(anomaly_id), sanitize_for_log(e)
            )
            return False

    async def get_anomaly_stats(self) -> dict[str, Any]:
        """Get anomaly statistics."""
        return await self.anomaly_repo.get_stats()
