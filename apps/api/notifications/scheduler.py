"""
Notification scheduler for managing alerts and digests.

Handles:
- Periodic checks for new properties and price drops (Instant alerts)
- Daily/Weekly digest generation and sending
- Quiet hours enforcement (queuing alerts)
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from analytics import MarketInsights
from core.security_utils import sanitize_for_log
from data.schemas import PropertyCollection
from notifications.alert_manager import Alert, AlertManager, AlertType
from notifications.digest_generator import DigestGenerator
from notifications.email_service import EmailService
from notifications.notification_history import (
    NotificationHistory,
    NotificationType,
)
from notifications.notification_preferences import (
    AlertFrequency,
    NotificationPreferences,
    NotificationPreferencesManager,
)
from services.anomaly_service import AnomalyService
from utils.property_cache import load_collection, load_previous_collection
from utils.saved_searches import SavedSearch, SavedSearchManager
from vector_store.chroma_store import ChromaPropertyStore

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """
    Scheduler for running notification pipelines.

    Combines instant alert checks and digest generation.
    """

    def __init__(
        self,
        email_service: EmailService,
        prefs_manager: Optional[NotificationPreferencesManager] = None,
        history: Optional[NotificationHistory] = None,
        search_manager: Optional[SavedSearchManager] = None,
        poll_interval_seconds: int = 60,
        storage_path_alerts: str = ".alerts",
        vector_store: Optional[ChromaPropertyStore] = None,
    ):
        self._email_service = email_service
        self._prefs_manager = prefs_manager or NotificationPreferencesManager()
        self._history = history or NotificationHistory()
        self._search_manager = search_manager or SavedSearchManager()
        self._poll_interval_seconds = poll_interval_seconds
        self._storage_path_alerts = storage_path_alerts
        self._vector_store = vector_store  # Needed for digest generator

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_attempt_minute: Dict[tuple[str, NotificationType], str] = {}
        self._last_instant_check: Optional[datetime] = None

        # Price snapshot tracking (Task #38: Price History & Trends)
        self._price_snapshot_interval_seconds: int = 3600  # 1 hour default
        self._last_price_snapshot: Optional[datetime] = None

        # Anomaly detection tracking (Task #53: Market Anomaly Detection)
        self._anomaly_service: Optional[AnomalyService] = None
        self._anomaly_check_interval_seconds: float = 3600.0  # 1 hour default
        self._last_anomaly_check: Optional[datetime] = None

    def start(self) -> None:
        """Start the scheduler thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="NotificationScheduler"
        )
        self._thread.start()
        logger.info("Notification scheduler started")

    def stop(self, timeout_seconds: float = 2.0) -> None:
        """Stop the scheduler thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout_seconds)
        logger.info("Notification scheduler stopped")

    def run_pending(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Run pending tasks (digests, instant alerts).

        Args:
            now: Current time override (for testing)

        Returns:
            Stats dictionary
        """
        check_time = now or datetime.now()
        stats = {
            "digests_daily": 0,
            "digests_weekly": 0,
            "instant_alerts": 0,
            "queued_alerts": 0,
            "queued_alerts_sent": 0,
            "queued_alerts_deferred": 0,
            "price_snapshots": 0,
            "anomaly_alerts": 0,
        }
        errors: List[str] = []

        try:
            self._refresh_data_sources()

            # 1. Process Digests
            stats["digests_daily"] += self._send_due_digests(AlertFrequency.DAILY, check_time)
            stats["digests_weekly"] += self._send_due_digests(AlertFrequency.WEEKLY, check_time)

            # 2. Process Instant Alerts (Price Drops, New Properties)
            # We run this check periodically (e.g. every 5 minutes or every poll)
            # For simplicity, we run it every poll but rely on data changes to trigger actual alerts.
            # In a real system, we'd check if ingestion happened recently.
            instant_stats = self._process_instant_alerts(check_time)
            stats["instant_alerts"] += instant_stats["sent"]
            stats["queued_alerts"] += instant_stats["queued"]

            queued_stats = self._process_queued_alerts(check_time)
            stats["queued_alerts_sent"] += queued_stats["sent"]
            stats["queued_alerts_deferred"] += queued_stats["deferred"]

            # 3. Price Snapshot Capture (hourly) - Task #38
            snapshot_stats = self._run_price_snapshot_capture(check_time)
            stats["price_snapshots"] = snapshot_stats.get("captured", 0)

            # 4. Anomaly Detection (hourly) - Task #53
            anomaly_stats = self._run_anomaly_detection(check_time)
            stats["anomaly_alerts"] = anomaly_stats.get("alerts_sent", 0)

        except Exception as e:
            logger.error("Scheduler run error: %s", sanitize_for_log(e))
            errors.append(str(e))

        return {"stats": stats, "errors": errors}

    def _refresh_data_sources(self) -> None:
        try:
            self._prefs_manager._load_all_preferences()
        except Exception:
            pass

        try:
            self._search_manager.saved_searches = self._search_manager._load_searches()
        except Exception:
            pass

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_pending()
            self._stop_event.wait(self._poll_interval_seconds)

    # -------------------------------------------------------------------------
    # Digest Logic
    # -------------------------------------------------------------------------

    def _send_due_digests(self, frequency: AlertFrequency, now: datetime) -> int:
        sent_count = 0
        am = AlertManager(email_service=self._email_service, storage_path=self._storage_path_alerts)
        users = self._prefs_manager.get_users_by_frequency(frequency)

        for prefs in users:
            try:
                if not self._is_time_match(prefs, now, frequency):
                    continue

                if not prefs.is_alert_enabled(AlertType.DIGEST):
                    continue

                notification_type = (
                    NotificationType.DIGEST_DAILY
                    if frequency == AlertFrequency.DAILY
                    else NotificationType.DIGEST_WEEKLY
                )

                # Check duplication via minute key (avoid sending multiple times in same minute)
                attempt_key = (prefs.user_email, notification_type)
                minute_key = now.strftime("%Y-%m-%d %H:%M")
                if self._last_attempt_minute.get(attempt_key) == minute_key:
                    continue
                self._last_attempt_minute[attempt_key] = minute_key

                # Check if already sent today (via history/alert manager)
                # AlertManager has its own duplication check for digests (date_key)

                digest_type = "daily" if frequency == AlertFrequency.DAILY else "weekly"

                # Generate Data
                data = self._build_digest_data(prefs, now, digest_type=digest_type)

                # Send
                # We use a dummy generator because we already built the data
                # Or we can refactor AlertManager.process_digest to take data directly.
                # AlertManager.send_digest takes data.
                if am.send_digest(prefs.user_email, digest_type, data, send_email=True):
                    sent_count += 1
                    record = self._history.record_notification(
                        user_email=prefs.user_email,
                        notification_type=notification_type,
                        subject=f"Your {digest_type.title()} Real Estate Digest",
                        metadata={"digest_type": digest_type},
                    )
                    self._history.mark_sent(record.id)

            except Exception as e:
                logger.error(
                    "Error sending digest to %s: %s",
                    sanitize_for_log(prefs.user_email),
                    sanitize_for_log(e),
                )

        return sent_count

    def _is_time_match(
        self, prefs: NotificationPreferences, now: datetime, frequency: AlertFrequency
    ) -> bool:
        try:
            target_time = datetime.strptime(prefs.daily_digest_time, "%H:%M").time()
        except Exception:
            return False

        # Allow 1 minute window
        if now.time().strftime("%H:%M") != target_time.strftime("%H:%M"):
            return False

        if frequency == AlertFrequency.WEEKLY:
            current_day = now.strftime("%A").lower()
            # Handle case where weekly_digest_day is Enum or string
            day_val = (
                prefs.weekly_digest_day.value
                if hasattr(prefs.weekly_digest_day, "value")
                else prefs.weekly_digest_day
            )
            return current_day == day_val

        return True

    def _build_digest_data(
        self, prefs: NotificationPreferences, now: datetime, digest_type: str
    ) -> Dict[str, Any]:
        """Build digest data using DigestGenerator logic."""
        # Load fresh data
        current = load_collection()
        if current is None:
            current = PropertyCollection(properties=[], total_count=0, source_type="digest")
        load_previous_collection()

        # We need a vector store for DigestGenerator
        # If not provided, we might have limited functionality
        # For now, we mock or skip parts requiring vector store if missing

        market_insights = MarketInsights(current)

        # We need to construct a DigestGenerator instance
        # If vector_store is None, we can't fully use it.
        # But for this task, we assume it's available or we implement fallback.

        # Let's replicate the logic from DigestGenerator manually here or use it if available
        # The DigestGenerator expects vector_store.
        if self._vector_store:
            generator = DigestGenerator(market_insights, self._vector_store)
            saved_searches = self._search_manager.get_all_searches()
            digest_result = generator.generate_digest(prefs, saved_searches, digest_type)  # type: ignore[arg-type]
            return cast(Dict[str, Any], digest_result)

        # Fallback if no vector store (e.g. testing)
        return {
            "new_properties": 0,
            "price_drops": 0,
            "trending_cities": [],
            "saved_searches": [],
            "top_picks": [],
            "expert": None,
        }

    # -------------------------------------------------------------------------
    # Instant Alert Logic
    # -------------------------------------------------------------------------

    def _process_instant_alerts(self, now: datetime) -> Dict[str, int]:
        """Check and send instant alerts."""
        sent = 0
        queued = 0

        # Load Data
        current = load_collection()
        previous = load_previous_collection()

        if not current or not current.properties:
            return {"sent": 0, "queued": 0}

        am = AlertManager(email_service=self._email_service, storage_path=self._storage_path_alerts)

        # Detect Changes
        # 1. Price Drops
        drops = []
        if previous:
            # We check drops with a low threshold to capture all, then filter per user
            # Or we iterate users first?
            # Iterating users is safer for personalized thresholds.
            # But checking drops globally is more efficient.
            # Let's check globally with 0% threshold to get ALL drops, then filter.
            drops = am.check_price_drops(current, previous, threshold_percent=0.1)

        # 2. New Properties (vs previous)
        # We need to identify which properties are 'new'.
        # Assuming 'current' has everything and 'previous' has old state.
        # New properties are in current but not previous.
        new_props = []
        if previous:
            prev_ids = {am._get_property_key(p) for p in previous.properties}
            new_props = [p for p in current.properties if am._get_property_key(p) not in prev_ids]

        # Iterate Instant Users
        instant_users = self._prefs_manager.get_users_by_frequency(AlertFrequency.INSTANT)

        for prefs in instant_users:
            if not prefs.enabled:
                continue

            # --- Price Drops ---
            if AlertType.PRICE_DROP in prefs.enabled_alerts and drops:
                user_drops = [d for d in drops if d["percent_drop"] >= prefs.price_drop_threshold]

                # Filter by saved searches? (Optional, implies "Watchlist")
                # For now, we send all drops that meet threshold? No, that's spam.
                # Let's assume we filter by saved searches matching the property.
                user_searches = self._search_manager.get_all_searches()
                relevant_drops = []
                for d in user_drops:
                    prop = d["property"]
                    # If matches ANY saved search
                    if any(s.matches(prop.dict()) for s in user_searches):
                        relevant_drops.append(d)

                for drop in relevant_drops:
                    alert = Alert(
                        alert_type=AlertType.PRICE_DROP,
                        user_email=prefs.user_email,
                        data=drop,
                        property_id=str(drop["property"].id),
                    )

                    if prefs.is_in_quiet_hours(now):
                        am.queue_alert(alert)
                        queued += 1
                    else:
                        # Check max alerts
                        # We need to count sent today.
                        # This requires history check.
                        if am.send_price_drop_alert(prefs.user_email, drop, send_email=True):
                            sent += 1
                            record = self._history.record_notification(
                                user_email=prefs.user_email,
                                notification_type=NotificationType.PRICE_DROP,
                                subject=f"Price Drop: {drop['property'].city}",
                                metadata={"property_id": str(drop["property"].id)},
                            )
                            self._history.mark_sent(record.id)

            # --- New Properties ---
            if AlertType.NEW_PROPERTY in prefs.enabled_alerts and new_props:
                user_searches = self._search_manager.get_all_searches()
                # Group by search
                matches = am.check_new_property_matches(
                    PropertyCollection(
                        properties=new_props,
                        total_count=len(new_props),
                        source_type="instant_alert",
                    ),
                    user_searches,
                )

                for search_id, props in matches.items():
                    search = next((s for s in user_searches if s.id == search_id), None)
                    if not search:
                        continue

                    alert = Alert(
                        alert_type=AlertType.NEW_PROPERTY,
                        user_email=prefs.user_email,
                        data={
                            "search_id": search_id,
                            "search_name": search.name,
                            "properties": [p.dict() for p in props],
                        },
                    )

                    if prefs.is_in_quiet_hours(now):
                        am.queue_alert(alert)
                        queued += 1
                    else:
                        if am.send_new_property_alerts(
                            prefs.user_email, search_id, search.name, props, send_email=True
                        ):
                            sent += 1
                            record = self._history.record_notification(
                                user_email=prefs.user_email,
                                notification_type=NotificationType.NEW_PROPERTY,
                                subject=f"New Matches: {search.name}",
                                metadata={"search_id": search_id},
                            )
                            self._history.mark_sent(record.id)

        return {"sent": sent, "queued": queued}

    def _process_queued_alerts(self, now: datetime) -> Dict[str, int]:
        am = AlertManager(email_service=self._email_service, storage_path=self._storage_path_alerts)

        pending_before = am.list_pending_alerts()

        def should_send(alert: Alert) -> bool:
            try:
                prefs = self._prefs_manager.get_preferences(alert.user_email)
                if not prefs.enabled:
                    return False
                return not prefs.is_in_quiet_hours(now)
            except Exception:
                return False

        deferred = 0
        for alert in pending_before:
            if not should_send(alert):
                deferred += 1

        sent, sent_alerts = am.process_pending_alerts_with_result(should_send=should_send)
        remaining = len(am.list_pending_alerts())

        for alert in sent_alerts:
            if alert.alert_type == AlertType.PRICE_DROP:
                data = alert.data or {}
                prop = data.get("property") or {}
                prop_city = (
                    prop.get("city") if isinstance(prop, dict) else getattr(prop, "city", "")
                )
                prop_id = alert.property_id or getattr(prop, "id", None)
                record = self._history.record_notification(
                    user_email=alert.user_email,
                    notification_type=NotificationType.PRICE_DROP,
                    subject=f"Price Drop: {prop_city}",
                    metadata={"property_id": str(prop_id)} if prop_id is not None else {},
                )
                self._history.mark_sent(record.id)
            elif alert.alert_type == AlertType.NEW_PROPERTY:
                record = self._history.record_notification(
                    user_email=alert.user_email,
                    notification_type=NotificationType.NEW_PROPERTY,
                    subject=f"New Matches: {alert.data.get('search_name', '')}",
                    metadata={"search_id": alert.data.get("search_id")},
                )
                self._history.mark_sent(record.id)

        return {"sent": sent, "deferred": deferred, "remaining": remaining}

    # -------------------------------------------------------------------------
    # Price Snapshot Capture (Task #38: Price History & Trends)
    # -------------------------------------------------------------------------

    def _run_price_snapshot_capture(self, now: datetime) -> Dict[str, Any]:
        """
        Synchronous wrapper for price snapshot capture.

        Args:
            now: Current timestamp

        Returns:
            Stats dictionary with capture results
        """
        # Check if we should run (hourly interval)
        if self._last_price_snapshot is not None:
            elapsed = (now - self._last_price_snapshot).total_seconds()
            if elapsed < self._price_snapshot_interval_seconds:
                return {"captured": 0, "skipped": 0, "reason": "interval_not_elapsed"}

        try:
            # Run async capture in new event loop
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                stats = loop.run_until_complete(self._capture_price_snapshots_async(now))
                self._last_price_snapshot = now
                return stats
            finally:
                loop.close()
        except Exception as e:
            logger.error("Price snapshot capture failed: %s", sanitize_for_log(e))
            return {"captured": 0, "error": str(e)}

    async def _capture_price_snapshots_async(self, now: datetime) -> Dict[str, Any]:
        """
        Async implementation of price snapshot capture.

        Args:
            now: Current timestamp

        Returns:
            Stats dictionary with capture results
        """
        try:
            from services.price_snapshot_service import get_price_snapshot_service

            service = get_price_snapshot_service()
            stats = await service.capture_all_property_prices(source="scheduled")

            logger.info(
                "Captured %s price snapshots (skipped: %s)",
                sanitize_for_log(stats.get("captured", 0)),
                sanitize_for_log(stats.get("skipped", 0)),
            )
            return stats

        except Exception as e:
            logger.error("Price snapshot async capture failed: %s", sanitize_for_log(e))
            return {"captured": 0, "error": str(e)}

    # -------------------------------------------------------------------------
    # Anomaly Detection (Task #53: Market Anomaly Detection)
    # -------------------------------------------------------------------------

    def _run_anomaly_detection(self, now: datetime) -> Dict[str, Any]:
        """
        Synchronous wrapper for anomaly detection.

        Runs daily analysis to detect price spikes, drops, and unusual patterns.
        Sends alerts for high/critical severity anomalies.

        Args:
            now: Current timestamp

        Returns:
            Stats dictionary with detection results
        """
        # Check if we should run (hourly interval)
        if self._last_anomaly_check is not None:
            elapsed = (now - self._last_anomaly_check).total_seconds()
            if elapsed < self._anomaly_check_interval_seconds:
                return {"alerts_sent": 0, "skipped": 0, "reason": "interval_not_elapsed"}

        try:
            # Run async detection in new event loop
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                stats = loop.run_until_complete(self._run_anomaly_detection_async(now))
                self._last_anomaly_check = now
                return stats
            finally:
                loop.close()
        except Exception as e:
            logger.error("Anomaly detection failed: %s", sanitize_for_log(e))
            return {"alerts_sent": 0, "error": str(e)}

    async def _run_anomaly_detection_async(self, now: datetime) -> Dict[str, Any]:
        """
        Async implementation of anomaly detection.

        Uses AnomalyService to run daily analysis and send alerts
        for high/critical severity anomalies.

        Args:
            now: Current timestamp

        Returns:
            Stats dictionary with detection results
        """
        try:
            from db.database import get_db_context
            from db.repositories import AnomalyRepository, PriceSnapshotRepository

            async with get_db_context() as session:
                anomaly_repo = AnomalyRepository(session)
                price_snapshot_repo = PriceSnapshotRepository(session)

                # Create anomaly service with alert manager
                am = AlertManager(
                    email_service=self._email_service,
                    storage_path=self._storage_path_alerts,
                )

                service = AnomalyService(
                    anomaly_repo=anomaly_repo,
                    price_snapshot_repo=price_snapshot_repo,
                    alert_manager=am,
                )

                # Run daily analysis
                stats = await service.run_daily_analysis()

                logger.info(
                    "Anomaly detection complete: %s anomalies found, %s alerts sent",
                    sanitize_for_log(stats.get("total_anomalies", 0)),
                    sanitize_for_log(stats.get("alerts_sent", 0)),
                )
                return stats

        except Exception as e:
            logger.error("Anomaly detection async failed: %s", sanitize_for_log(e))
            return {"alerts_sent": 0, "error": str(e)}

    # -------------------------------------------------------------------------
    # DB Search Sync Methods
    # -------------------------------------------------------------------------

    def add_or_update_search(self, search: SavedSearch) -> None:
        """
        Add or update a search in the in-memory manager.

        Called from API when a search is created or updated.
        This keeps the scheduler's view of searches in sync with the database.

        Args:
            search: SavedSearch Pydantic model
        """
        self._search_manager.save_search(search)
        logger.debug("Synced search to scheduler: %s", sanitize_for_log(search.id))

    def remove_search(self, search_id: str) -> bool:
        """
        Remove a search from the in-memory manager.

        Called from API when a search is deleted.

        Args:
            search_id: ID of the search to remove

        Returns:
            True if removed, False if not found
        """
        result = self._search_manager.delete_search(search_id)
        if result:
            logger.debug("Removed search from scheduler: %s", sanitize_for_log(search_id))
        return result

    def get_search(self, search_id: str) -> Optional[SavedSearch]:
        """
        Get a search by ID from the in-memory manager.

        Args:
            search_id: Search ID

        Returns:
            SavedSearch or None
        """
        return self._search_manager.get_search(search_id)

    def get_all_searches(self) -> List[SavedSearch]:
        """
        Get all searches from the in-memory manager.

        Returns:
            List of all SavedSearch instances
        """
        return self._search_manager.get_all_searches()
