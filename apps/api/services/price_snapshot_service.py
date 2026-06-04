"""Service for capturing and managing property price snapshots.

This module provides functionality to capture price snapshots for properties
stored in ChromaDB, persisting them to SQLite for historical tracking.

Task #38: Price History & Trends
"""

import logging
from typing import Any, Dict, List, Optional

from core.security_utils import sanitize_for_log
from db.database import get_db_context
from db.repositories import PriceSnapshotRepository
from utils.property_cache import load_collection

logger = logging.getLogger(__name__)


class PriceSnapshotService:
    """Service for capturing property price snapshots."""

    def __init__(self):
        """Initialize the price snapshot service."""
        pass

    async def capture_all_property_prices(
        self,
        source: str = "scheduled",
    ) -> Dict[str, Any]:
        """
        Capture current prices for all properties in the cache.

        Called by the scheduler at regular intervals to build price history.

        Args:
            source: Source identifier for the snapshot (e.g., "scheduled", "manual")

        Returns:
            Stats dictionary with capture results:
            - captured: Number of new snapshots created
            - skipped: Number of properties skipped (price unchanged)
            - errors: List of error messages
            - properties_checked: Total properties processed
        """
        stats = {
            "captured": 0,
            "skipped": 0,
            "errors": [],
            "properties_checked": 0,
        }

        try:
            # Load properties from cache
            collection = load_collection()
            if not collection or not collection.properties:
                logger.info("No properties found in cache for price snapshot")
                return stats

            async with get_db_context() as session:
                repo = PriceSnapshotRepository(session)

                for prop in collection.properties:
                    try:
                        property_id = getattr(prop, "id", None)
                        price = getattr(prop, "price", None)

                        if not property_id or price is None:
                            continue

                        stats["properties_checked"] += 1

                        # Calculate price per sqm
                        price_per_sqm = None
                        area_sqm = getattr(prop, "area_sqm", None)
                        if area_sqm and area_sqm > 0:
                            price_per_sqm = price / area_sqm

                        # Get currency
                        currency = getattr(prop, "currency", "PLN")

                        # Check if price changed since last snapshot
                        latest = await repo.get_latest_for_property(str(property_id))
                        if latest and latest.price == price:
                            # Price unchanged, skip
                            stats["skipped"] += 1
                            continue

                        # Create new snapshot
                        await repo.create(
                            property_id=str(property_id),
                            price=float(price),
                            price_per_sqm=price_per_sqm,
                            currency=currency,
                            source=source,
                        )
                        stats["captured"] += 1

                    except Exception as e:
                        error_msg = f"Error capturing price for property {getattr(prop, 'id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        stats["errors"].append(error_msg)

            logger.info(
                "Price snapshot complete: %s captured, %s skipped, %s checked",
                sanitize_for_log(stats["captured"]),
                sanitize_for_log(stats["skipped"]),
                sanitize_for_log(stats["properties_checked"]),
            )

        except Exception as e:
            error_msg = f"Error in price snapshot capture: {e}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)

        return stats

    async def get_price_history(
        self,
        property_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get price history for a specific property.

        Args:
            property_id: Property ID to get history for
            limit: Maximum number of snapshots to return

        Returns:
            List of price snapshot dictionaries
        """
        async with get_db_context() as session:
            repo = PriceSnapshotRepository(session)
            snapshots = await repo.get_by_property(property_id, limit=limit)
            return [
                {
                    "id": s.id,
                    "property_id": s.property_id,
                    "price": s.price,
                    "price_per_sqm": s.price_per_sqm,
                    "currency": s.currency,
                    "source": s.source,
                    "recorded_at": s.recorded_at.isoformat() if s.recorded_at else None,
                }
                for s in snapshots
            ]

    async def cleanup_old_snapshots(self, days_to_keep: int = 365) -> int:
        """
        Remove snapshots older than the specified number of days.

        Args:
            days_to_keep: Number of days to keep snapshots for

        Returns:
            Number of snapshots removed
        """
        async with get_db_context() as session:
            repo = PriceSnapshotRepository(session)
            count = await repo.cleanup_old_snapshots(days_to_keep)
            if count > 0:
                logger.info("Cleaned up %s old price snapshots", sanitize_for_log(count))
            return count


# Module-level service instance for convenience
_service: Optional[PriceSnapshotService] = None


def get_price_snapshot_service() -> PriceSnapshotService:
    """Get or create the price snapshot service instance."""
    global _service
    if _service is None:
        _service = PriceSnapshotService()
    return _service
