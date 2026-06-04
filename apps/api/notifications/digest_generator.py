"""
Digest generator for creating consumer and expert digests.

This module is responsible for gathering data from various sources (saved searches,
market analytics, property store) to construct the payload for digest emails.
"""

import logging
from typing import Any, Dict, List

from analytics.market_insights import MarketInsights
from core.security_utils import sanitize_for_log
from utils.saved_searches import SavedSearch, UserPreferences
from vector_store.chroma_store import ChromaPropertyStore

logger = logging.getLogger(__name__)


class DigestGenerator:
    """Generates data for daily/weekly digests."""

    def __init__(
        self,
        market_insights: MarketInsights,
        vector_store: ChromaPropertyStore,
    ):
        """
        Initialize digest generator.

        Args:
            market_insights: Market analytics engine
            vector_store: Property vector store
        """
        self.market_insights = market_insights
        self.vector_store = vector_store

    def generate_digest(
        self,
        user_prefs: UserPreferences,
        saved_searches: List[SavedSearch],
        digest_type: str = "daily",
    ) -> Dict[str, Any]:
        """
        Generate digest data for a user.

        Args:
            user_prefs: User preferences
            saved_searches: List of user's saved searches
            digest_type: 'daily' or 'weekly'

        Returns:
            Dictionary containing digest data suitable for DigestTemplate
        """
        # 1. Gather property highlights (Consumer focus)
        top_picks: list[dict[str, Any]] = []
        price_drop_properties: list[dict[str, Any]] = []

        # We'll use a set of seen property IDs to avoid duplicates across saved searches
        seen_ids = set()
        saved_search_data = []

        # For each saved search, find top matches
        for search in saved_searches:
            # Convert saved search to query
            query = search.to_query_string()

            # Use vector store to find matches
            # Note: In a real implementation, we would filter by 'created_at' for 'new' properties
            # or check a price history for 'price_drops'.
            # For this base implementation, we fetch top relevant results.
            try:
                # Construct filters from saved search
                filters = self._build_filters(search)

                results = self.vector_store.search(
                    query=query,
                    k=5,  # Fetch a few to filter
                    filter=filters,
                )

                match_count = len(results)
                saved_search_data.append(
                    {"id": search.id, "name": search.name, "new_matches": match_count}
                )

                for doc, _score in results:
                    prop_data = doc.metadata
                    prop_id = prop_data.get("id") or prop_data.get("url")  # Fallback ID

                    if prop_id and prop_id not in seen_ids:
                        seen_ids.add(prop_id)

                        # Add to top picks (simplified logic for now)
                        if len(top_picks) < 5:
                            top_picks.append(prop_data)

                        # Check for price drops (if data available)
                        # This assumes metadata might have 'price_drop' or similar field
                        # For now, we leave price_drop_properties empty unless we find explicit signals

            except Exception as e:
                logger.error(
                    "Error searching for saved search %s: %s",
                    sanitize_for_log(search.name),
                    sanitize_for_log(e),
                )
                saved_search_data.append({"id": search.id, "name": search.name, "new_matches": 0})
                continue

        # 2. Gather market stats (Consumer/Expert)
        # Aggregate stats from preferred cities or saved search cities
        cities = set(user_prefs.preferred_cities)
        for s in saved_searches:
            if s.city:
                cities.add(s.city)

        # Fallback to a default city if none specified
        if not cities:
            cities.add("New York")  # Example default

        # 3. Build Expert Section (if applicable)
        expert_data = None
        # Logic: If user has advanced preferences or explicit 'expert' flag (not yet in UserPrefs,
        # but implied by the task "Consumer/Expert"), we add it.
        # For now, we'll include it if they have saved searches (indicating active interest)
        # or if we want to showcase the feature.
        # Let's assume we always generate it, and the template decides to show it
        # or we pass it only if the user is an 'expert' (maybe determined by usage?).
        # For this task, let's include it for everyone to demonstrate the capability,
        # or check if we can infer 'expert' status.
        # The prompt says "Consumer/Expert" digest. Let's provide the data structure.

        expert_rows = []
        trending_cities = []

        for city in list(cities)[:3]:  # Limit to 3 cities
            try:
                # Market trends
                trend = self.market_insights.get_price_trend(city)
                if trend:
                    trending_cities.append(
                        {
                            "name": city,
                            "trend": trend.direction,
                            "change": f"{trend.change_percent:.1f}%",
                        }
                    )

                    expert_rows.append(
                        {
                            "City": city,
                            "Avg Price": f"${trend.average_price:,.0f}",
                            "Trend": f"{trend.direction} ({trend.change_percent:+.1f}%)",
                            "Inventory": "Normal",  # Placeholder or derived
                        }
                    )
            except Exception:
                pass

        if expert_rows:
            expert_data = {
                "market_table": expert_rows,
                "analysis": "Market shows mixed signals with stable inventory in major areas.",  # Dynamic generation could go here
            }

        # 4. Construct final payload
        return {
            "new_properties": len(top_picks),  # Placeholder count
            "price_drops": 0,  # Placeholder
            "avg_price": 0,  # Placeholder
            "total_properties": 1250,  # Placeholder global count
            "average_price": 0,  # Placeholder
            "trending_cities": trending_cities,
            "saved_searches": saved_search_data,
            "top_picks": top_picks,
            "price_drop_properties": price_drop_properties,
            "expert": expert_data,
        }

    def _build_filters(self, search: SavedSearch) -> Dict[str, Any]:
        """Build Chroma/VectorStore compatible filters from SavedSearch."""
        filters: Dict[str, Any] = {}
        conditions: list[Dict[str, Dict[str, Any]]] = []

        if search.city:
            conditions.append({"city": {"$eq": search.city}})

        if search.min_price:
            conditions.append({"price": {"$gte": search.min_price}})

        if search.max_price:
            conditions.append({"price": {"$lte": search.max_price}})

        if search.min_rooms:
            conditions.append({"rooms": {"$gte": search.min_rooms}})

        # Combine conditions
        if len(conditions) > 1:
            filters = {"$and": conditions}  # type: ignore[assignment]
        elif len(conditions) == 1:
            filters = conditions[0]  # type: ignore[assignment]

        return filters
