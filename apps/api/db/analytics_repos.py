"""
Analytics repository classes.

Provides repositories for PriceSnapshot, MarketAnomaly,
CMAReport, and AuditLog models.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AuditLogEntry,
    CMAReportDB,
    MarketAnomaly,
    PriceSnapshot,
)

# Stable reference to the real datetime class. The module attribute ``datetime``
# can be swapped out (tests freeze the clock), this one always stays put.
_DATETIME = datetime


class PriceSnapshotRepository:
    """Repository for PriceSnapshot model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        property_id: str,
        price: float,
        price_per_sqm: Optional[float] = None,
        currency: Optional[str] = None,
        source: Optional[str] = None,
    ) -> PriceSnapshot:
        """Create a new price snapshot.

        ``recorded_at`` is kept strictly increasing per property. The clock can
        hand out the same tick twice (Windows ticks in milliseconds) and the
        snapshot id is a random UUID, so without this the price history order
        would be a coin flip - and a real price drop could go unnoticed.
        """
        from uuid import uuid4

        snapshot = PriceSnapshot(
            id=str(uuid4()),
            property_id=property_id,
            price=price,
            price_per_sqm=price_per_sqm,
            currency=currency,
            source=source,
            recorded_at=await self._next_recorded_at(property_id),
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def _next_recorded_at(self, property_id: str) -> datetime:
        """Return the timestamp to store for the next snapshot of a property."""
        now = datetime.now(UTC)
        latest = await self.get_latest_for_property(property_id)
        if latest is None:
            return now

        previous = getattr(latest, "recorded_at", None)
        if not isinstance(previous, _DATETIME):
            return now
        if previous.tzinfo is None:
            # SQLite drops the timezone on the way in and hands it back naive.
            previous = previous.replace(tzinfo=UTC)

        if now <= previous:
            return previous + timedelta(microseconds=1)
        return now

    async def get_by_property(
        self,
        property_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PriceSnapshot]:
        """Get price history for a property."""
        result = await self.session.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.property_id == property_id)
            .order_by(PriceSnapshot.recorded_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_for_property(self, property_id: str) -> Optional[PriceSnapshot]:
        """Get the most recent price snapshot for a property."""
        result = await self.session.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.property_id == property_id)
            .order_by(PriceSnapshot.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_for_property(self, property_id: str) -> int:
        """Count snapshots for a property."""
        result = await self.session.execute(
            select(func.count(PriceSnapshot.id)).where(PriceSnapshot.property_id == property_id)
        )
        return result.scalar() or 0

    async def get_snapshots_in_period(
        self,
        start_date: datetime,
        end_date: datetime,
        property_ids: Optional[list[str]] = None,
    ) -> list[PriceSnapshot]:
        """Get all snapshots in a time period, optionally filtered."""
        query = select(PriceSnapshot).where(
            PriceSnapshot.recorded_at >= start_date,
            PriceSnapshot.recorded_at <= end_date,
        )
        if property_ids:
            query = query.where(PriceSnapshot.property_id.in_(property_ids))
        query = query.order_by(PriceSnapshot.recorded_at.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_properties_with_price_drops(
        self,
        threshold_percent: float = 5.0,
        days_back: int = 7,
    ) -> list[dict[str, Any]]:
        """Find properties with price drops exceeding threshold."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_back)

        # Get recent snapshots ordered by property and date. recorded_at is
        # strictly increasing per property, so the id tiebreaker only settles
        # rows written before that invariant existed.
        result = await self.session.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.recorded_at >= cutoff_date)
            .order_by(
                PriceSnapshot.property_id, PriceSnapshot.recorded_at.desc(), PriceSnapshot.id.desc()
            )
        )
        snapshots = result.scalars().all()

        # Group by property and detect drops
        property_prices: dict[str, list[PriceSnapshot]] = {}
        for snap in snapshots:
            if snap.property_id not in property_prices:
                property_prices[snap.property_id] = []
            property_prices[snap.property_id].append(snap)

        drops = []
        for prop_id, snaps in property_prices.items():
            if len(snaps) >= 2:
                # Compare most recent to oldest in the period
                latest = snaps[0]  # Most recent (first due to desc order)
                oldest = snaps[-1]  # Oldest (last in the list)
                if oldest.price > 0:
                    change_pct = ((oldest.price - latest.price) / oldest.price) * 100
                    if change_pct >= threshold_percent:
                        drops.append(
                            {
                                "property_id": prop_id,
                                "old_price": oldest.price,
                                "new_price": latest.price,
                                "percent_drop": change_pct,
                                "recorded_at": latest.recorded_at,
                            }
                        )

        return drops

    async def cleanup_old_snapshots(self, days_to_keep: int = 365) -> int:
        """Remove snapshots older than specified days."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)
        result = await self.session.execute(
            select(PriceSnapshot).where(PriceSnapshot.recorded_at < cutoff_date)
        )
        old_snapshots = result.scalars().all()

        count = 0
        for snapshot in old_snapshots:
            await self.session.delete(snapshot)
            count += 1

        return count


class AnomalyRepository:
    """Repository for MarketAnomaly model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        anomaly_type: str,
        severity: str,
        scope_type: str,
        scope_id: str,
        algorithm: str,
        threshold_used: float,
        metric_name: str,
        expected_value: float,
        actual_value: float,
        deviation_percent: float,
        z_score: Optional[float] = None,
        baseline_period_start: Optional[datetime] = None,
        baseline_period_end: Optional[datetime] = None,
        comparison_period_start: Optional[datetime] = None,
        comparison_period_end: Optional[datetime] = None,
        context: Optional[dict] = None,
    ):
        """Create a new market anomaly record."""
        from uuid import uuid4

        anomaly = MarketAnomaly(
            id=str(uuid4()),
            anomaly_type=anomaly_type,
            severity=severity,
            scope_type=scope_type,
            scope_id=scope_id,
            algorithm=algorithm,
            threshold_used=threshold_used,
            metric_name=metric_name,
            expected_value=expected_value,
            actual_value=actual_value,
            deviation_percent=deviation_percent,
            z_score=z_score,
            baseline_period_start=baseline_period_start,
            baseline_period_end=baseline_period_end,
            comparison_period_start=comparison_period_start,
            comparison_period_end=comparison_period_end,
            context=context or {},
        )
        self.session.add(anomaly)
        await self.session.flush()
        return anomaly

    async def get_by_id(self, anomaly_id: str):
        """Get anomaly by ID."""
        result = await self.session.execute(
            select(MarketAnomaly).where(MarketAnomaly.id == anomaly_id)
        )
        return result.scalar_one_or_none()

    async def get_by_scope(
        self,
        scope_type: str,
        scope_id: str,
        limit: int = 50,
        offset: int = 0,
    ):
        """Get anomalies for a specific scope."""
        result = await self.session.execute(
            select(MarketAnomaly)
            .where(
                MarketAnomaly.scope_type == scope_type,
                MarketAnomaly.scope_id == scope_id,
            )
            .order_by(MarketAnomaly.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(
        self,
        limit: int = 50,
        severity_filter: Optional[str] = None,
        anomaly_type_filter: Optional[str] = None,
    ):
        """Get recent anomalies, optional filters."""
        query = select(MarketAnomaly)

        if severity_filter:
            query = query.where(MarketAnomaly.severity == severity_filter)
        if anomaly_type_filter:
            query = query.where(MarketAnomaly.anomaly_type == anomaly_type_filter)

        query = query.order_by(MarketAnomaly.detected_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_undismissed_count(self) -> int:
        """Count undismissed anomalies."""
        result = await self.session.execute(
            select(func.count(MarketAnomaly.id)).where(MarketAnomaly.dismissed_at.is_(None))
        )
        return result.scalar() or 0

    async def mark_alert_sent(self, anomaly_id: str) -> None:
        """Mark that an alert has been sent for this anomaly."""
        await self.session.execute(
            update(MarketAnomaly)
            .where(MarketAnomaly.id == anomaly_id)
            .values(alert_sent=True, alert_sent_at=datetime.now(UTC))
        )

    async def dismiss(self, anomaly_id: str, dismissed_by: Optional[str] = None) -> None:
        """Dismiss an anomaly."""
        await self.session.execute(
            update(MarketAnomaly)
            .where(MarketAnomaly.id == anomaly_id)
            .values(dismissed_at=datetime.now(UTC), dismissed_by=dismissed_by)
        )

    async def get_stats(self) -> dict[str, Any]:
        """Get anomaly statistics."""
        # Total count
        total_result = await self.session.execute(select(func.count(MarketAnomaly.id)))
        total = total_result.scalar() or 0

        # Count by severity
        severity_result = await self.session.execute(
            select(
                MarketAnomaly.severity,
                func.count(MarketAnomaly.id),
            ).group_by(MarketAnomaly.severity)
        )
        severity_counts = {row.severity: row.count for row in severity_result}

        # Count by type
        type_result = await self.session.execute(
            select(
                MarketAnomaly.anomaly_type,
                func.count(MarketAnomaly.id),
            ).group_by(MarketAnomaly.anomaly_type)
        )
        type_counts = {row.anomaly_type: row.count for row in type_result}

        # Undismissed count
        undismissed = await self.get_undismissed_count()

        return {
            "total": total,
            "by_severity": severity_counts,
            "by_type": type_counts,
            "undismissed": undismissed,
        }


class CMAReportRepository:
    """Repository for CMAReportDB model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        subject_property_id: str,
        subject_data: dict,
        comparables: list,
        valuation: dict,
        market_context: Optional[dict] = None,
        status: str = "draft",
        expires_in_days: Optional[int] = 90,
    ) -> CMAReportDB:
        """Create a new CMA report."""
        from uuid import uuid4

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        report = CMAReportDB(
            id=str(uuid4()),
            user_id=user_id,
            status=status,
            subject_property_id=subject_property_id,
            subject_data=subject_data,
            comparables=comparables,
            valuation=valuation,
            market_context=market_context,
            expires_at=expires_at,
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def get_by_id(self, report_id: str, user_id: str) -> Optional[CMAReportDB]:
        """Get CMA report by ID (scoped to user)."""
        result = await self.session.execute(
            select(CMAReportDB).where(CMAReportDB.id == report_id, CMAReportDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_unscoped(self, report_id: str) -> Optional[CMAReportDB]:
        """Get CMA report by ID without user scoping (for sharing)."""
        result = await self.session.execute(select(CMAReportDB).where(CMAReportDB.id == report_id))
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        include_expired: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CMAReportDB]:
        """Get all CMA reports for a user."""
        query = select(CMAReportDB).where(CMAReportDB.user_id == user_id)

        if status:
            query = query.where(CMAReportDB.status == status)

        if not include_expired:
            query = query.where(
                or_(
                    CMAReportDB.expires_at.is_(None),
                    CMAReportDB.expires_at > datetime.now(UTC),
                )
            )

        query = query.order_by(CMAReportDB.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        include_expired: bool = False,
    ) -> int:
        """Count CMA reports for a user."""
        query = select(func.count(CMAReportDB.id)).where(CMAReportDB.user_id == user_id)

        if status:
            query = query.where(CMAReportDB.status == status)

        if not include_expired:
            query = query.where(
                or_(
                    CMAReportDB.expires_at.is_(None),
                    CMAReportDB.expires_at > datetime.now(UTC),
                )
            )

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update(self, report: CMAReportDB, **kwargs) -> CMAReportDB:
        """Update CMA report fields."""
        for key, value in kwargs.items():
            if hasattr(report, key):
                setattr(report, key, value)
        report.updated_at = datetime.now(UTC)
        await self.session.flush()
        return report

    async def mark_completed(self, report: CMAReportDB) -> CMAReportDB:
        """Mark report as completed."""
        report.status = "completed"
        report.updated_at = datetime.now(UTC)
        await self.session.flush()
        return report

    async def mark_expired(self, report: CMAReportDB) -> CMAReportDB:
        """Mark report as expired."""
        report.status = "expired"
        report.updated_at = datetime.now(UTC)
        await self.session.flush()
        return report

    async def delete(self, report: CMAReportDB) -> None:
        """Delete a CMA report."""
        await self.session.delete(report)

    async def expire_old_reports(self, batch_size: int = 100) -> int:
        """Expire reports past their expiration date."""
        result = await self.session.execute(
            update(CMAReportDB)
            .where(
                CMAReportDB.status != "expired",
                CMAReportDB.expires_at.isnot(None),
                CMAReportDB.expires_at <= datetime.now(UTC),
            )
            .values(status="expired")
            .returning(CMAReportDB.id)
        )
        expired_ids = list(result.scalars().all())
        await self.session.flush()
        return len(expired_ids)


class AuditLogRepository:
    """Repository for AuditLogEntry operations with hash-chain integrity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def append(
        self,
        *,
        actor_id: Optional[str] = None,
        actor_email: Optional[str] = None,
        actor_role: Optional[str] = None,
        action: str,
        resource: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLogEntry:
        """Create a new audit log entry linked to the hash chain."""
        from uuid import uuid4

        # Get previous hash from the most recent entry
        prev = await self.session.execute(
            select(AuditLogEntry).order_by(AuditLogEntry.created_at.desc()).limit(1)
        )
        prev_entry = prev.scalar_one_or_none()
        prev_hash = prev_entry.entry_hash if prev_entry else ""

        now = datetime.now(UTC)
        entry_id = str(uuid4())
        entry = AuditLogEntry(
            id=entry_id,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            action=action,
            resource=resource,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            prev_hash=prev_hash,
            created_at=now,
        )
        entry.entry_hash = entry.compute_hash(prev_hash)
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def query(
        self,
        *,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource: Optional[str] = None,
        request_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLogEntry], int]:
        """Query audit log entries with filters. Returns (entries, total)."""
        conditions = []
        if action:
            conditions.append(AuditLogEntry.action == action)
        if actor_id:
            conditions.append(AuditLogEntry.actor_id == actor_id)
        if resource:
            conditions.append(AuditLogEntry.resource == resource)
        if request_id:
            conditions.append(AuditLogEntry.request_id == request_id)
        if start_time:
            conditions.append(AuditLogEntry.created_at >= start_time)
        if end_time:
            conditions.append(AuditLogEntry.created_at <= end_time)

        base = select(AuditLogEntry)
        for c in conditions:
            base = base.where(c)

        # Count
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.session.execute(count_q)).scalar() or 0

        # Fetch page
        rows = await self.session.execute(
            base.order_by(AuditLogEntry.created_at.desc()).limit(limit).offset(offset)
        )
        entries = list(rows.scalars().all())
        return entries, total

    async def verify_chain(self, limit: int = 1000) -> dict[str, Any]:
        """Verify hash-chain integrity of the last N entries.

        Returns dict with 'valid' bool and list of broken entries.
        """
        rows = await self.session.execute(
            select(AuditLogEntry).order_by(AuditLogEntry.created_at.asc()).limit(limit)
        )
        entries = list(rows.scalars().all())

        broken: list[dict[str, Any]] = []
        prev_hash = ""
        for entry in entries:
            if entry.prev_hash != prev_hash:
                broken.append(
                    {
                        "entry_id": entry.id,
                        "reason": "prev_hash_mismatch",
                        "expected": prev_hash,
                        "actual": entry.prev_hash,
                    }
                )
            expected_hash = entry.compute_hash(prev_hash)
            if entry.entry_hash != expected_hash:
                broken.append(
                    {
                        "entry_id": entry.id,
                        "reason": "entry_hash_mismatch",
                        "expected": expected_hash,
                        "actual": entry.entry_hash,
                    }
                )
            prev_hash = entry.entry_hash

        return {
            "valid": len(broken) == 0,
            "checked_count": len(entries),
            "broken_count": len(broken),
            "broken_entries": broken[:20],
        }

    async def get_by_id(self, entry_id: str) -> Optional[AuditLogEntry]:
        """Get a single audit log entry by ID."""
        result = await self.session.execute(
            select(AuditLogEntry).where(AuditLogEntry.id == entry_id)
        )
        return result.scalar_one_or_none()
