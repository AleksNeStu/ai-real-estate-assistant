"""
Alert manager for detecting and sending property notifications.

Handles:
- Price drop detection
- New property matching against saved searches
- Alert deduplication
- Alert prioritization
"""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

from data.schemas import Property, PropertyCollection
from utils import SavedSearch
from notifications.email_service import EmailService

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    """Types of alerts."""
    PRICE_DROP = "price_drop"
    NEW_PROPERTY = "new_property"
    SAVED_SEARCH_MATCH = "saved_search_match"
    MARKET_UPDATE = "market_update"
    DIGEST = "digest"


@dataclass
class Alert:
    """Alert information."""
    alert_type: AlertType
    user_email: str
    property_id: Optional[str] = None
    subject: str = ""
    message: str = ""
    data: Dict[str, Any] = None
    created_at: datetime = None
    sent_at: Optional[datetime] = None
    priority: int = 1  # 1=high, 2=medium, 3=low

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.data is None:
            self.data = {}


class AlertManager:
    """
    Manager for detecting and sending property alerts.

    Handles price drops, new properties, and saved search matches.
    """

    def __init__(
        self,
        email_service: EmailService,
        storage_path: str = ".alerts"
    ):
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

    def check_price_drops(
        self,
        current_properties: PropertyCollection,
        previous_properties: PropertyCollection,
        threshold_percent: float = 5.0
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
            self._get_property_key(prop): prop.price
            for prop in previous_properties.properties
        }

        # Check for price drops
        for prop in current_properties.properties:
            prop_key = self._get_property_key(prop)

            if prop_key in prev_prices:
                old_price = prev_prices[prop_key]
                new_price = prop.price

                if new_price < old_price:
                    percent_drop = ((old_price - new_price) / old_price) * 100

                    if percent_drop >= threshold_percent:
                        price_drops.append({
                            'property': prop,
                            'old_price': old_price,
                            'new_price': new_price,
                            'percent_drop': percent_drop,
                            'savings': old_price - new_price,
                            'property_key': prop_key
                        })

        return price_drops

    def check_new_property_matches(
        self,
        new_properties: PropertyCollection,
        saved_searches: List[SavedSearch]
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
        self,
        user_email: str,
        property_info: Dict[str, Any],
        send_email: bool = True
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
        prop = property_info['property']

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
            <p><strong>Previous Price:</strong> <span style="text-decoration: line-through;">${property_info['old_price']:.0f}</span></p>
            <p><strong>New Price:</strong> <span style="color: #2ca02c; font-size: 1.2em;">${property_info['new_price']:.0f}</span></p>
            <p><strong>Savings:</strong> <span style="color: #2ca02c;">-{property_info['percent_drop']:.1f}% (${property_info['savings']:.0f})</span></p>

            <div style="margin-top: 15px;">
                <p><strong>Details:</strong></p>
                <ul>
                    <li>{prop.rooms} bedrooms, {prop.bathrooms} bathrooms</li>
                    {'<li>' + str(prop.area_sqm) + ' sqm</li>' if prop.area_sqm else ''}
                </ul>
            </div>
        </div>
        """

        if send_email:
            try:
                self.email_service.send_email(
                    to_email=user_email,
                    subject=subject,
                    body=message,
                    html=True
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
        search_id: str,
        search_name: str,
        matching_properties: List[Property],
        send_email: bool = True
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
                <p>{prop.rooms} bed | {prop.bathrooms} bath{' | ' + str(prop.area_sqm) + ' sqm' if prop.area_sqm else ''}</p>
                <p><strong>Amenities:</strong> {amenities}</p>
            </div>
            """

        if len(matching_properties) > 5:
            properties_html += f"<p><em>...and {len(matching_properties) - 5} more properties</em></p>"

        message = f"""
        <h2 style="color: #1f77b4;">🏠 New Property Matches!</h2>
        <p>We found {len(matching_properties)} new properties matching your search: <strong>{search_name}</strong></p>
        {properties_html}
        """

        if send_email:
            try:
                self.email_service.send_email(
                    to_email=user_email,
                    subject=subject,
                    body=message,
                    html=True
                )
                self._mark_alert_sent(alert_key)
                return True
            except Exception as e:
                logger.warning("Failed to send new property alert: %s", e)
                return False
        else:
            self._mark_alert_sent(alert_key)
            return True

    def send_digest(
        self,
        user_email: str,
        digest_type: str,
        data: Dict[str, Any],
        send_email: bool = True
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
        date_str = datetime.now().strftime("%B %d, %Y")
        subject = f"📊 Your {digest_type.title()} Real Estate Digest - {date_str}"

        message = f"""
        <h2>📊 {digest_type.title()} Real Estate Digest</h2>
        <p style="color: #666;">{date_str}</p>

        <div style="display: flex; justify-content: space-around; margin: 20px 0;">
            <div style="text-align: center;">
                <h3 style="color: #1f77b4; margin: 5px 0;">{data.get('new_properties', 0)}</h3>
                <p style="color: #666; margin: 0;">New Properties</p>
            </div>
            <div style="text-align: center;">
                <h3 style="color: #2ca02c; margin: 5px 0;">{data.get('price_drops', 0)}</h3>
                <p style="color: #666; margin: 0;">Price Drops</p>
            </div>
            <div style="text-align: center;">
                <h3 style="color: #ff7f0e; margin: 5px 0;">${data.get('avg_price', 0):.0f}</h3>
                <p style="color: #666; margin: 0;">Avg Price</p>
            </div>
        </div>

        <h3>📈 Market Summary</h3>
        <ul>
            <li>Total Active Listings: {data.get('total_properties', 0)}</li>
            <li>Average Price: ${data.get('average_price', 0):.0f}</li>
        </ul>
        """

        if send_email:
            try:
                self.email_service.send_email(
                    to_email=user_email,
                    subject=subject,
                    body=message,
                    html=True
                )
                return True
            except Exception as e:
                logger.warning("Failed to send digest: %s", e)
                return False
        else:
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
            str(int(prop.area_sqm)) if prop.area_sqm is not None else "area"
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
            with open(self.sent_alerts_file, 'r') as f:
                data = json.load(f)
                return set(data.get('alerts', []))
        except Exception:
            return set()

    def _save_sent_alerts(self):
        """Save sent alerts to disk."""
        with open(self.sent_alerts_file, 'w') as f:
            json.dump({
                'alerts': list(self._sent_alerts),
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)

    def get_alert_statistics(self) -> Dict[str, int]:
        """
        Get alert statistics.

        Returns:
            Dictionary with alert counts
        """
        return {
            'total_sent': len(self._sent_alerts),
            'pending': len(self._pending_alerts)
        }

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
