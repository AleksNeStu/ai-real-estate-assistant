"""
Overpass API adapter for fetching property data from OpenStreetMap.

This adapter uses the Overpass API to query OpenStreetMap for building/property
data. It's a demo implementation that shows how to build a portal adapter.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from core.security_utils import sanitize_for_log
from data.adapters.base import (
    ExternalSourceAdapter,
    PortalFetchResult,
    PortalFilter,
    with_retry,
)

logger = logging.getLogger(__name__)


class OverpassAdapter(ExternalSourceAdapter):
    """
    Adapter for fetching property data via Overpass API (OpenStreetMap).

    This is a demo adapter that shows how to fetch geographic/building data.
    In production, you would implement specific portal APIs (e.g., Otodom, Idealista).

    Environment variables:
        OVERPASS_API_URL: Custom Overpass API endpoint (optional, defaults to public)
    """

    name = "overpass"
    display_name = "OpenStreetMap (Overpass)"
    requires_api_key = False
    api_key_env_var = ""
    rate_limit_requests = 10
    rate_limit_window = 60

    # Overpass API default endpoint
    DEFAULT_API_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Overpass adapter."""
        super().__init__(api_key)
        import os

        self._api_url = os.getenv("OVERPASS_API_URL", self.DEFAULT_API_URL)

    def _get_base_url(self) -> str:
        """Return base URL for OpenStreetMap."""
        return "https://www.openstreetmap.org"

    @with_retry(max_tries=3, max_time=60)
    def fetch(self, filters: PortalFilter) -> PortalFetchResult:
        """
        Fetch properties from OpenStreetMap via Overpass API.

        Queries for buildings in the specified city and extracts property
        information. Automatically retries on transient failures.

        Args:
            filters: Search filters including city, price range, etc.

        Returns:
            PortalFetchResult with fetched properties
        """
        result = PortalFetchResult(
            success=False, source=self.name, source_type="portal", filters=filters
        )

        if not filters.city:
            result.add_error("City filter is required for Overpass queries")
            return result

        try:
            # Build Overpass QL query
            query = self._build_overpass_query(filters)

            # Execute query
            response = requests.get(
                self._api_url,
                params={"data": query},
                timeout=30,
            )
            response.raise_for_status()

            # Parse response
            data = response.json()

            # Extract properties from OSM elements
            properties = self._parse_osm_response(data, filters)

            result.success = True
            result.properties = properties
            result.count = len(properties)
            result.metadata = {
                "query": query,
                "osm_elements_count": len(data.get("elements", [])),
            }

            logger.info(
                "Fetched %s properties from Overpass for %s",
                len(properties),
                sanitize_for_log(filters.city),
            )

        except requests.RequestException as e:
            result.add_error(f"Overpass API request failed: {str(e)}")
        except Exception as e:
            result.add_error(f"Failed to parse Overpass response: {str(e)}")

        return result

    def _build_overpass_query(self, filters: PortalFilter) -> str:
        """Build Overpass QL query based on filters."""
        # Search for buildings with address info in the city
        city = (filters.city or "").replace("'", "\\'")

        query = f"""
            [out:json][timeout:25];
            area["name"="{city}"]->.searchArea;
            (
              way["building"](area.searchArea);
              relation["building"](area.searchArea);
            );
            out body center;
            """

        return query.strip()

    def _parse_osm_response(
        self, data: Dict[str, Any], filters: PortalFilter
    ) -> List[Dict[str, Any]]:
        """Parse Overpass API response into property dictionaries."""
        properties = []
        elements = data.get("elements", [])

        for element in elements[: filters.limit]:
            try:
                tags = element.get("tags", {})
                if not tags:
                    continue

                # Extract address information
                addr = self._extract_address(tags)
                if not addr.get("city"):
                    addr["city"] = filters.city or "Unknown"

                # Build property dict
                prop = {
                    "id": f"overpass_{element.get('id', '')}",
                    "title": tags.get("name", f"Property in {addr.get('city', 'Unknown')}"),
                    "city": addr.get("city"),
                    "neighborhood": addr.get("suburb") or addr.get("district"),
                    "address": addr.get("full"),
                    "latitude": element.get("center", {}).get("lat") or element.get("lat"),
                    "longitude": element.get("center", {}).get("lon") or element.get("lon"),
                    "property_type": self._normalize_property_type(
                        tags.get("building"), tags.get("amenity")
                    ),
                    "listing_type": filters.listing_type or "rent",
                    # Generate estimated values for demo purposes
                    "price": self._estimate_price(tags, filters),
                    "currency": "EUR",
                    "rooms": self._estimate_rooms(tags.get("building")),
                    "bathrooms": 1.0,
                    "area_sqm": self._estimate_area(tags),
                    "year_built": self._parse_year(tags.get("start_date")),
                    "source_url": self._build_osm_url(str(element.get("id")), element.get("type")),
                    "source_platform": "overpass",
                    "has_parking": tags.get("parking") is not None,
                    "has_garden": tags.get("garden") is not None,
                }

                properties.append(prop)

            except Exception as e:
                logger.warning(
                    "Failed to parse OSM element %s: %s",
                    sanitize_for_log(element.get("id")),
                    sanitize_for_log(e),
                )
                continue

        return properties

    def _extract_address(self, tags: Dict[str, str]) -> Dict[str, Optional[str]]:
        """Extract address information from OSM tags."""
        addr: Dict[str, Optional[str]] = {}

        # Get address components
        city = tags.get("addr:city")
        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        postcode = tags.get("addr:postcode")
        suburb = tags.get("addr:suburb")
        district = tags.get("addr:district")

        addr["city"] = city
        addr["street"] = street
        addr["housenumber"] = housenumber
        addr["postcode"] = postcode
        addr["suburb"] = suburb
        addr["district"] = district

        # Build full address
        parts = []
        if street:
            if housenumber:
                parts.append(f"{street} {housenumber}")
            else:
                parts.append(street)
        if postcode:
            parts.append(postcode)
        if city:
            parts.append(city)

        addr["full"] = ", ".join(parts) if parts else "Unknown address"

        return addr

    def _normalize_property_type(self, building_type: Optional[str], amenity: Optional[str]) -> str:
        """Normalize OSM building type to property type enum."""
        if not building_type:
            return "apartment"

        building_lower = building_type.lower()

        if building_lower in ["apartments", "residential"]:
            return "apartment"
        elif building_lower in ["house", "detached", "semidetached_house"]:
            return "house"
        elif building_lower in ["commercial", "retail", "office"]:
            return "other"
        else:
            return "apartment"

    def _estimate_price(self, tags: Dict[str, str], filters: PortalFilter) -> float:
        """Estimate price based on building characteristics."""
        import random

        # Base price by city
        base_prices: Dict[str, float] = {
            "warsaw": 2500,
            "krakow": 2200,
            "wroclaw": 2000,
            "poznan": 2100,
            "gdansk": 2000,
        }

        city_lower = (tags.get("addr:city") or "").lower()
        base: float = base_prices.get(city_lower, 1800)

        # Adjust by building type
        building = tags.get("building", "").lower()
        if building in ["house", "detached"]:
            base *= 1.5
        elif building == "apartments":
            base *= 1.0

        # Add random variation
        base = base * random.uniform(0.8, 1.2)

        # Apply filters
        if filters.min_price:
            base = max(base, filters.min_price)
        if filters.max_price:
            base = min(base, filters.max_price)

        return round(base, 2)

    def _estimate_rooms(self, building_type: Optional[str]) -> float:
        """Estimate number of rooms based on building type."""
        if not building_type:
            return 2.0

        building_lower = building_type.lower()

        if building_lower in ["house", "detached", "semidetached_house"]:
            return 4.0
        elif building_lower == "apartments":
            return 2.0
        else:
            return 2.0

    def _estimate_area(self, tags: Dict[str, str]) -> float:
        """Estimate area based on building characteristics."""
        import random

        building = tags.get("building", "").lower()

        if building in ["house", "detached"]:
            return round(random.uniform(80, 200), 1)
        elif building == "apartments":
            return round(random.uniform(30, 120), 1)
        else:
            return round(random.uniform(50, 100), 1)

    def _parse_year(self, year_str: Optional[str]) -> int:
        """Parse year from OSM start_date tag."""
        if not year_str:
            return 2000
        try:
            return int(year_str)
        except (ValueError, TypeError):
            return 2000

    def _build_osm_url(self, osm_id: str, osm_type: Any) -> str:
        """Build OpenStreetMap browse URL for an element."""
        type_str = str(osm_type) if osm_type else "node"
        if type_str == "way":
            return f"https://www.openstreetmap.org/way/{osm_id}"
        elif type_str == "relation":
            return f"https://www.openstreetmap.org/relation/{osm_id}"
        else:
            return f"https://www.openstreetmap.org/{type_str}/{osm_id}"

    def normalize_property(self, raw_property: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a raw OSM property to internal schema.

        The fetch method already normalizes, so this returns the input as-is.
        """
        return raw_property
