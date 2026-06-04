"""
Alert manager for detecting and sending property notifications.

Handles:
- Price drop detection
- New property matching against saved searches
- Alert deduplication
- Alert prioritization
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, cast

from core.security_utils import sanitize_for_log
from data.schemas import Property, PropertyCollection
from notifications.email_service import EmailService
from notifications.email_templates import DigestTemplate
from utils import SavedSearch, UserPreferences

if False:  # TYPE_CHECKING
    from notifications.digest_generator import DigestGenerator

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    """Types of alerts."""

    PRICE_DROP = "price_drop"
    NEW_PROPERTY = "new_property"
    SAVED_SEARCH_MATCH = "saved_search_match"
    MARKET_UPDATE = "market_update"
    DIGEST = "digest"
    ANOMALY = "anomaly"  # Market anomaly detected
    HIGH_VALUE_LEAD = "high_value_lead"  # High-value lead detected


@dataclass
class Alert:
    """Alert information."""

    alert_type: AlertType
    user_email: str
    property_id: Optional[str] = None
    subject: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    priority: int = 1  # 1=high, 2=medium, 3=low

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class AlertManager:
    """
    Manager for detecting and sending property alerts.

    Handles price drops, new properties, and saved search matches.
    """

    def __init__(self, email_service: EmailService, storage_path: str = ".alerts"):
        """
        Initialize alert manager.

        Args:
            email_service: Email service for sending alerts
            storage_path: Path to store alert history
        """
        self.email_service = email_service
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        self.sent_alerts_file = self.storage_path / "sent_alerts.json"
        self.pending_alerts_file = self.storage_path / "pending_alerts.json"

        self._sent_alerts: Set[str] = self._load_sent_alerts()
        self._pending_alerts: List[Alert] = []

    def queue_alert(self, alert: Alert):
        """
        Queue an alert for later delivery.

        Args:
            alert: Alert object to queue
        """
        self._pending_alerts.append(self._normalize_alert_for_storage(alert))
        self._save_pending_alerts()
        logger.info(
            "Queued alert %s for %s",
            sanitize_for_log(alert.alert_type),
            sanitize_for_log(alert.user_email),
        )

    def list_pending_alerts(self) -> List[Alert]:
        return self._load_pending_alerts()

    def process_pending_alerts(self, should_send: Optional[Callable[[Alert], bool]] = None) -> int:
        sent_count, _sent_alerts = self.process_pending_alerts_with_result(should_send=should_send)
        return sent_count

    def process_pending_alerts_with_result(
        self, *, should_send: Optional[Callable[[Alert], bool]] = None
    ) -> tuple[int, List[Alert]]:
        sent_count = 0
        sent_alerts: List[Alert] = []
        remaining_alerts: List[Alert] = []
        should_send_fn = should_send or (lambda _alert: True)

        self._pending_alerts = self._load_pending_alerts()

        for alert in self._pending_alerts:
            success = False
            try:
                if not should_send_fn(alert):
                    remaining_alerts.append(alert)
                    continue

                if self._is_alert_already_sent(alert):
                    continue

                if alert.alert_type == AlertType.PRICE_DROP:
                    price_drop_data = self._normalize_price_drop_data_for_send(alert.data)
                    success = self.send_price_drop_alert(
                        alert.user_email,
                        price_drop_data,
                        send_email=True,
                    )
                elif alert.alert_type == AlertType.NEW_PROPERTY:
                    props_data = alert.data.get("properties", [])
                    props = [Property(**p) for p in props_data]
                    search_id = alert.data.get("search_id")
                    search_name = alert.data.get("search_name")
                    success = self.send_new_property_alerts(
                        alert.user_email,
                        search_id if isinstance(search_id, str) else None,
                        search_name if isinstance(search_name, str) else None,
                        props,
                        send_email=True,
                    )
                elif alert.alert_type == AlertType.DIGEST:
                    digest_type = alert.data.get("digest_type")
                    content = alert.data.get("content")
                    success = self.send_digest(
                        alert.user_email,
                        digest_type if isinstance(digest_type, str) else None,
                        content if isinstance(content, dict) else None,
                        send_email=True,
                    )

                if success:
                    sent_count += 1
                    sent_alerts.append(alert)
                else:
                    remaining_alerts.append(alert)
            except Exception as e:
                logger.error("Error processing pending alert: %s", sanitize_for_log(e))
                remaining_alerts.append(alert)

        self._pending_alerts = remaining_alerts
        self._save_pending_alerts()
        return sent_count, sent_alerts

    def _normalize_alert_for_storage(self, alert: Alert) -> Alert:
        if alert.alert_type != AlertType.PRICE_DROP:
            return alert

        data = dict(alert.data or {})
        prop = data.get("property")
        if isinstance(prop, Property):
            try:
                prop_dict = cast(Any, prop).model_dump(mode="json")
            except Exception:
                try:
                    prop_dict = json.loads(cast(Any, prop).json())
                except Exception:
                    prop_dict = prop.dict()
            data["property"] = prop_dict
            if alert.property_id is None:
                alert.property_id = (
                    str(prop_dict.get("id")) if prop_dict.get("id") is not None else None
                )
        return Alert(
            alert_type=alert.alert_type,
            user_email=alert.user_email,
            property_id=alert.property_id,
            subject=alert.subject,
            message=alert.message,
            data=data,
            created_at=alert.created_at,
            sent_at=alert.sent_at,
            priority=alert.priority,
        )

    def _normalize_price_drop_data_for_send(self, data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(data or {})
        prop = normalized.get("property")
        if isinstance(prop, dict):
            normalized["property"] = Property(**prop)
        return normalized

    def _is_alert_already_sent(self, alert: Alert) -> bool:
        if alert.alert_type == AlertType.PRICE_DROP:
            data = self._normalize_price_drop_data_for_send(alert.data)
            prop = data.get("property")
            if prop is None:
                return False
            key = f"price_drop_{self._get_property_key(prop)}_{alert.user_email}"
            return key in self._sent_alerts

        if alert.alert_type == AlertType.NEW_PROPERTY:
            search_id = alert.data.get("search_id")
            props = alert.data.get("properties") or []
            key = f"new_match_{search_id}_{len(props)}_{alert.user_email}"
            return key in self._sent_alerts

        if alert.alert_type == AlertType.DIGEST:
            digest_type = alert.data.get("digest_type")
            date_key = datetime.now().strftime("%Y-%m-%d")
            key = f"digest_{digest_type}_{date_key}_{alert.user_email}"
            return key in self._sent_alerts

        return False

    def _load_pending_alerts(self) -> List[Alert]:
        """Load pending alerts from disk."""
        if not self.pending_alerts_file.exists():
            return []

        try:
            with open(self.pending_alerts_file, "r") as f:
                data = json.load(f)
                alerts = []
                for a_data in data.get("alerts", []):
                    # Convert dict back to Alert object
                    # Handle datetime conversion
                    if "created_at" in a_data and a_data["created_at"]:
                        a_data["created_at"] = datetime.fromisoformat(a_data["created_at"])
                    if "sent_at" in a_data and a_data["sent_at"]:
                        a_data["sent_at"] = datetime.fromisoformat(a_data["sent_at"])

                    alerts.append(Alert(**a_data))
                return alerts
        except Exception as e:
            logger.error("Error loading pending alerts: %s", sanitize_for_log(e))
            return []

    def _save_pending_alerts(self):
        """Save pending alerts to disk."""
        try:
            with open(self.pending_alerts_file, "w") as f:
                # Convert alerts to dicts, handling datetime
                alerts_data = []
                for alert in self._pending_alerts:
                    a_dict = (
                        asdict(alert) if hasattr(alert, "__dataclass_fields__") else alert.__dict__
                    )
                    if a_dict.get("created_at"):
                        a_dict["created_at"] = a_dict["created_at"].isoformat()
                    if a_dict.get("sent_at"):
                        a_dict["sent_at"] = a_dict["sent_at"].isoformat()
                    alerts_data.append(a_dict)

                json.dump(
                    {"alerts": alerts_data, "last_updated": datetime.now().isoformat()},
                    f,
                    indent=2,
                    default=str,
                )
        except Exception as e:
            logger.error("Error saving pending alerts: %s", sanitize_for_log(e))

    def check_price_drops(
        self,
        current_properties: PropertyCollection,
        previous_properties: PropertyCollection,
        threshold_percent: float = 5.0,
    ) -> List[Dict[str, Any]]:
        """
        Detect price drops between property listings.

        Args:
            current_properties: Current property listings
            previous_properties: Previous property listings
            threshold_percent: Minimum % drop to alert (default 5%)

        Returns:
            List of price drop information
        """
        price_drops = []

        # Create lookup dict for previous prices
        prev_prices = {
            self._get_property_key(prop): prop.price for prop in previous_properties.properties
        }

        # Check for price drops
        for prop in current_properties.properties:
            prop_key = self._get_property_key(prop)

            if prop_key in prev_prices:
                old_price = prev_prices[prop_key]
                new_price = prop.price

                # Both prices must not be None for comparison
                if new_price is not None and old_price is not None and new_price < old_price:
                    percent_drop = ((old_price - new_price) / old_price) * 100

                    if percent_drop >= threshold_percent:
                        price_drops.append(
                            {
                                "property": prop,
                                "old_price": old_price,
                                "new_price": new_price,
                                "percent_drop": percent_drop,
                                "savings": old_price - new_price,
                                "property_key": prop_key,
                            }
                        )

        return price_drops

    def check_new_property_matches(
        self, new_properties: PropertyCollection, saved_searches: List[SavedSearch]
    ) -> Dict[str, List[Property]]:
        """
        Find new properties matching saved searches.

        Args:
            new_properties: Newly listed properties
            saved_searches: User's saved searches

        Returns:
            Dictionary mapping search_id to matching properties
        """
        matches = {}

        for search in saved_searches:
            matching_props = []

            for prop in new_properties.properties:
                prop_dict = prop.dict()

                if search.matches(prop_dict):
                    matching_props.append(prop)

            if matching_props:
                matches[search.id] = matching_props

        return matches

    def send_price_drop_alert(
        self, user_email: str, property_info: Dict[str, Any], send_email: bool = True
    ) -> bool:
        """
        Send price drop alert to user.

        Args:
            user_email: User's email address
            property_info: Price drop information from check_price_drops
            send_email: Whether to actually send email (False for testing)

        Returns:
            True if sent successfully
        """
        prop = property_info["property"]
        if isinstance(prop, dict):
            prop = Property(**prop)
            property_info = dict(property_info)
            property_info["property"] = prop

        # Check if already alerted
        alert_key = f"price_drop_{self._get_property_key(prop)}_{user_email}"
        if alert_key in self._sent_alerts:
            return False  # Already sent this alert

        # Create alert
        subject = f"🔔 Price Drop Alert - {prop.city}"

        message = f"""
        <h2 style="color: #2ca02c;">💰 Price Drop Alert!</h2>
        <p>A property you're watching has dropped in price:</p>

        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
            <h3>{prop.property_type} in {prop.city}</h3>
            <p><strong>Previous Price:</strong> <span style="text-decoration: line-through;">${property_info["old_price"]:.0f}</span></p>
            <p><strong>New Price:</strong> <span style="color: #2ca02c; font-size: 1.2em;">${property_info["new_price"]:.0f}</span></p>
            <p><strong>Savings:</strong> <span style="color: #2ca02c;">-{property_info["percent_drop"]:.1f}% (${property_info["savings"]:.0f})</span></p>

            <div style="margin-top: 15px;">
                <p><strong>Details:</strong></p>
                <ul>
                    <li>{prop.rooms} bedrooms, {prop.bathrooms} bathrooms</li>
                    {"<li>" + str(prop.area_sqm) + " sqm</li>" if prop.area_sqm else ""}
                </ul>
            </div>
        </div>
        """

        if send_email:
            try:
                self.email_service.send_email(
                    to_email=user_email, subject=subject, body=message, html=True
                )
                self._mark_alert_sent(alert_key)
                return True
            except Exception as e:
                logger.warning("Failed to send price drop alert: %s", e)
                return False
        else:
            # Testing mode - just mark as sent
            self._mark_alert_sent(alert_key)
            return True

    def send_new_property_alerts(
        self,
        user_email: str,
        search_id: Optional[str],
        search_name: Optional[str],
        matching_properties: List[Property],
        send_email: bool = True,
    ) -> bool:
        """
        Send new property match alert to user.

        Args:
            user_email: User's email address
            search_id: ID of the saved search
            search_name: Name of the saved search
            matching_properties: Properties matching the search
            send_email: Whether to actually send email

        Returns:
            True if sent successfully
        """
        # Check if already alerted for these properties
        alert_key = f"new_match_{search_id}_{len(matching_properties)}_{user_email}"
        if alert_key in self._sent_alerts:
            return False

        subject = f"🏠 {len(matching_properties)} New Properties Match Your Search - {search_name}"

        # Build property list HTML
        properties_html = ""
        for prop in matching_properties[:5]:  # Max 5 in email
            amenities = self._format_amenities(prop)
            properties_html += f"""
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #1f77b4;">
                <h3 style="margin-top: 0;">{prop.city} - ${prop.price}/month</h3>
                <p>{prop.rooms} bed | {prop.bathrooms} bath{" | " + str(prop.area_sqm) + " sqm" if prop.area_sqm else ""}</p>
                <p><strong>Amenities:</strong> {amenities}</p>
            </div>
            """

        if len(matching_properties) > 5:
            properties_html += (
                f"<p><em>...and {len(matching_properties) - 5} more properties</em></p>"
            )

        message = f"""
        <h2 style="color: #1f77b4;">🏠 New Property Matches!</h2>
        <p>We found {len(matching_properties)} new properties matching your search: <strong>{search_name}</strong></p>
        {properties_html}
        """

        if send_email:
            try:
                self.email_service.send_email(
                    to_email=user_email, subject=subject, body=message, html=True
                )
                self._mark_alert_sent(alert_key)
                return True
            except Exception as e:
                logger.warning("Failed to send new property alert: %s", e)
                return False
        else:
            self._mark_alert_sent(alert_key)
            return True

    def process_digest(
        self,
        user_email: str,
        user_prefs: UserPreferences,
        saved_searches: List[SavedSearch],
        digest_generator: "DigestGenerator",
        digest_type: str = "daily",
        send_email: bool = True,
    ) -> bool:
        """
        Generate and send a digest for a user.

        Args:
            user_email: User's email address
            user_prefs: User preferences
            saved_searches: List of saved searches
            digest_generator: Generator instance to create digest data
            digest_type: 'daily' or 'weekly'
            send_email: Whether to actually send email

        Returns:
            True if sent successfully
        """
        try:
            data = digest_generator.generate_digest(user_prefs, saved_searches, digest_type)
            return self.send_digest(user_email, digest_type, data, send_email)
        except Exception as e:
            logger.error(
                "Error processing digest for %s: %s",
                sanitize_for_log(user_email),
                sanitize_for_log(e),
            )
            return False

    def send_digest(
        self,
        user_email: str,
        digest_type: Optional[str],
        data: Optional[Dict[str, Any]],
        send_email: bool = True,
    ) -> bool:
        """
        Send daily or weekly digest to user.

        Args:
            user_email: User's email address
            digest_type: 'daily' or 'weekly'
            data: Digest data (new_properties, price_drops, etc.)
            send_email: Whether to actually send email

        Returns:
            True if sent successfully
        """
        date_key = datetime.now().strftime("%Y-%m-%d")
        alert_key = f"digest_{digest_type}_{date_key}_{user_email}"
        if alert_key in self._sent_alerts:
            return False

        subject, message = DigestTemplate.render(
            digest_type or "daily",
            data or {},
            user_name=user_email.split("@")[0],  # type: ignore[arg-type]
        )

        if send_email:
            try:
                self.email_service.send_email(
                    to_email=user_email, subject=subject, body=message, html=True
                )
                self._mark_alert_sent(alert_key)
                return True
            except Exception as e:
                logger.warning("Failed to send digest: %s", e)
                return False
        else:
            self._mark_alert_sent(alert_key)
            return True

    def _get_property_key(self, prop: Property) -> str:
        """Generate stable unique key for a property independent of price.

        Prefer the `id` if available; otherwise use non-price attributes that
        remain stable across price updates.
        """
        if prop.id:
            return str(prop.id)
        key_parts = [
            prop.city,
            str(prop.property_type),
            str(int(prop.rooms)) if prop.rooms is not None else "rooms",
            str(int(prop.bathrooms)) if prop.bathrooms is not None else "baths",
            str(int(prop.area_sqm)) if prop.area_sqm is not None else "area",
        ]
        return "_".join(key_parts)

    def _format_amenities(self, prop: Property) -> str:
        """Format amenities as string."""
        amenities = []
        if prop.has_parking:
            amenities.append("Parking")
        if prop.has_garden:
            amenities.append("Garden")
        if prop.has_pool:
            amenities.append("Pool")
        if prop.is_furnished:
            amenities.append("Furnished")
        if prop.has_balcony:
            amenities.append("Balcony")
        if prop.has_elevator:
            amenities.append("Elevator")

        return ", ".join(amenities) if amenities else "None"

    def _mark_alert_sent(self, alert_key: str):
        """Mark an alert as sent to prevent duplicates."""
        self._sent_alerts.add(alert_key)
        self._save_sent_alerts()

    def _load_sent_alerts(self) -> Set[str]:
        """Load sent alerts from disk."""
        if not self.sent_alerts_file.exists():
            return set()

        try:
            with open(self.sent_alerts_file, "r") as f:
                data = json.load(f)
                return set(data.get("alerts", []))
        except Exception:
            return set()

    def _save_sent_alerts(self):
        """Save sent alerts to disk."""
        with open(self.sent_alerts_file, "w") as f:
            json.dump(
                {"alerts": list(self._sent_alerts), "last_updated": datetime.now().isoformat()},
                f,
                indent=2,
            )

    def get_alert_statistics(self) -> Dict[str, int]:
        """
        Get alert statistics.

        Returns:
            Dictionary with alert counts
        """
        return {"total_sent": len(self._sent_alerts), "pending": len(self._pending_alerts)}

    def clear_old_alerts(self, days: int = 30):
        """
        Clear alert history older than specified days.

        Args:
            days: Number of days to keep
        """
        # For now, this is a simple implementation
        # In production, you'd track timestamps and clean accordingly
        if len(self._sent_alerts) > 10000:  # Arbitrary limit
            # Keep last 5000
            self._sent_alerts = set(list(self._sent_alerts)[-5000:])
            self._save_sent_alerts()
