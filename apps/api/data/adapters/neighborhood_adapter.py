"""
Neighborhood data adapter for fetching POI data from OpenStreetMap.

This adapter fetches Points of Interest (POI) data for neighborhood quality
scoring, including schools, amenities, green spaces, and walkability metrics.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


class NeighborhoodAdapter:
    """
    Adapter for fetching neighborhood quality data from OpenStreetMap.

    Uses the Overpass API to query for:
    - Schools (education)
    - Amenities (shops, restaurants, services)
    - Green spaces (parks, forests)
    - Walkability (street density, POI proximity)

    Environment variables:
        OVERPASS_API_URL: Custom Overpass API endpoint (optional)
    """

    # Overpass API default endpoint
    DEFAULT_API_URL: str = "https://overpass-api.de/api/interpreter"

    # POI categories for neighborhood scoring
    SCHOOL_TAGS = ["school", "kindergarten", "university", "college"]
    AMENITY_TAGS = [
        "restaurant",
        "cafe",
        "shop",
        "supermarket",
        "pharmacy",
        "hospital",
        "clinic",
        "bank",
        "atm",
        "fuel",
        "post_office",
    ]
    GREEN_SPACE_TAGS = [
        "park",
        "garden",
        "forest",
        "grass",
        "meadow",
        "recreation_ground",
    ]

    def __init__(self, api_url: Optional[str] = None) -> None:
        """
        Initialize the neighborhood adapter.

        Args:
            api_url: Optional custom Overpass API URL
        """
        import os

        url_from_env = os.getenv("OVERPASS_API_URL")
        self._api_url: str = api_url or url_from_env or self.DEFAULT_API_URL
        self._timeout = 30

    def fetch_pois_within_radius(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 1000,
        poi_tags: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch Points of Interest within a radius of coordinates.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters (default 1000m = 1km)
            poi_tags: List of POI tags to filter by (default: all categories)

        Returns:
            Dictionary with POI counts by category and raw data
            {
                "schools": [...],
                "amenities": [...],
                "green_spaces": [...],
                "all": [...]
            }
        """
        if poi_tags is None:
            poi_tags = self.SCHOOL_TAGS + self.AMENITY_TAGS + self.GREEN_SPACE_TAGS

        # Build Overpass QL query
        query = self._build_radius_query(latitude, longitude, radius_m, poi_tags)

        try:
            response = requests.get(
                self._api_url,
                params={"data": query},
                timeout=self._timeout,
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])

            # Categorize POIs
            result: Dict[str, List[Dict[str, Any]]] = {
                "schools": [],
                "amenities": [],
                "green_spaces": [],
                "all": [],
            }

            for element in elements:
                tags = element.get("tags", {})
                if not tags:
                    continue

                poi_data = self._parse_poi_element(element)

                # Categorize by type
                if self._is_school(tags):
                    result["schools"].append(poi_data)
                elif self._is_green_space(tags):
                    result["green_spaces"].append(poi_data)
                elif self._is_amenity(tags):
                    result["amenities"].append(poi_data)

                result["all"].append(poi_data)

            logger.info(
                "Found %s POIs within %sm: %s schools, %s amenities, %s green spaces",
                len(result["all"]),
                sanitize_for_log(radius_m),
                len(result["schools"]),
                len(result["amenities"]),
                len(result["green_spaces"]),
            )

            return result

        except requests.RequestException as e:
            logger.error("Overpass API request failed: %s", sanitize_for_log(e))
            return {
                "schools": [],
                "amenities": [],
                "green_spaces": [],
                "all": [],
            }
        except Exception as e:
            logger.error("Failed to parse POI data: %s", sanitize_for_log(e))
            return {
                "schools": [],
                "amenities": [],
                "green_spaces": [],
                "all": [],
            }

    def count_schools(self, latitude: float, longitude: float, radius_m: int = 1000) -> int:
        """
        Count schools within radius.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters

        Returns:
            Number of schools found
        """
        pois = self.fetch_pois_within_radius(latitude, longitude, radius_m, self.SCHOOL_TAGS)
        return len(pois.get("schools", []))

    def count_amenities(self, latitude: float, longitude: float, radius_m: int = 500) -> int:
        """
        Count amenities within radius.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters (default 500m for walkability)

        Returns:
            Number of amenities found
        """
        pois = self.fetch_pois_within_radius(latitude, longitude, radius_m, self.AMENITY_TAGS)
        return len(pois.get("amenities", []))

    def count_green_spaces(self, latitude: float, longitude: float, radius_m: int = 1000) -> int:
        """
        Count green spaces within radius.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters

        Returns:
            Number of parks/green spaces found
        """
        pois = self.fetch_pois_within_radius(latitude, longitude, radius_m, self.GREEN_SPACE_TAGS)
        return len(pois.get("green_spaces", []))

    def calculate_walkability(
        self, latitude: float, longitude: float, radius_m: int = 500
    ) -> float:
        """
        Calculate walkability score based on POI density.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters

        Returns:
            Walkability score 0-100 based on:
            - Amenity count (more = better)
            - POI diversity (different types = better)
            - Proximity to daily needs
        """
        pois = self.fetch_pois_within_radius(latitude, longitude, radius_m)

        amenities = pois.get("amenities", [])
        total_pois = len(pois.get("all", []))

        if total_pois == 0:
            return 40.0  # Low walkability for areas with no POIs

        # Calculate amenity diversity (unique amenity types)
        amenity_types = set()
        for poi in amenities:
            amenity = poi.get("amenity") or poi.get("shop")
            if amenity:
                amenity_types.add(amenity)

        diversity_score = min(100, len(amenity_types) * 10)

        # Density score (more POIs in smaller area = better)
        # 500m radius = ~0.78 km²
        area_km2 = 3.14159 * (radius_m / 1000) ** 2
        density = total_pois / area_km2 if area_km2 > 0 else 0

        # Density scoring (20 POIs/km² = 100 points)
        density_score = min(100, density * 5)

        # Essential amenities check (grocery, pharmacy, etc.)
        essential_tags = ["supermarket", "pharmacy", "hospital", "clinic", "bank"]
        essential_count = sum(1 for poi in amenities if poi.get("amenity") in essential_tags)
        essential_score = min(100, essential_count * 25)

        # Weighted average
        walkability = diversity_score * 0.3 + density_score * 0.4 + essential_score * 0.3

        return round(walkability, 1)

    def _build_radius_query(
        self, lat: float, lon: float, radius_m: int, poi_tags: List[str]
    ) -> str:
        """
        Build Overpass QL query for POIs within radius.

        Args:
            lat: Center latitude
            lon: Center longitude
            radius_m: Search radius in meters
            poi_tags: List of POI tags to search for

        Returns:
            Overpass QL query string
        """
        # Build tag filters
        tag_filters = " | ".join(f'["{tag}"]' for tag in poi_tags)

        query = f"""
            [out:json][timeout:25];
            (
              node{tag_filters}(around:{radius_m},{lat},{lon});
              way{tag_filters}(around:{radius_m},{lat},{lon});
            );
            out tags center;
            """

        return query.strip()

    def _parse_poi_element(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse an OSM element into POI data.

        Args:
            element: OSM element from Overpass response

        Returns:
            Dictionary with POI data
        """
        tags = element.get("tags", {})

        # Get coordinates
        if "lat" in element and "lon" in element:
            lat = element["lat"]
            lon = element["lon"]
        elif "center" in element:
            lat = element["center"]["lat"]
            lon = element["center"]["lon"]
        else:
            lat = None
            lon = None

        return {
            "id": element.get("id"),
            "type": element.get("type"),
            "name": tags.get("name"),
            "amenity": tags.get("amenity"),
            "shop": tags.get("shop"),
            "leisure": tags.get("leisure"),
            "landuse": tags.get("landuse"),
            "latitude": lat,
            "longitude": lon,
            "tags": tags,
        }

    def _is_school(self, tags: Dict[str, str]) -> bool:
        """Check if tags represent a school."""
        amenity = tags.get("amenity", "")
        return amenity in self.SCHOOL_TAGS

    def _is_amenity(self, tags: Dict[str, str]) -> bool:
        """Check if tags represent a daily amenity."""
        amenity = tags.get("amenity", "")
        shop = tags.get("shop", "")
        return amenity in self.AMENITY_TAGS or shop in self.AMENITY_TAGS

    def _is_green_space(self, tags: Dict[str, str]) -> bool:
        """Check if tags represent a green space."""
        leisure = tags.get("leisure", "")
        landuse = tags.get("landuse", "")
        return (
            leisure in self.GREEN_SPACE_TAGS
            or landuse in self.GREEN_SPACE_TAGS
            or tags.get("boundary") == "national_park"
        )


# Singleton instance for reuse
_default_adapter: Optional[NeighborhoodAdapter] = None


def get_neighborhood_adapter() -> NeighborhoodAdapter:
    """Get or create the default neighborhood adapter instance."""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = NeighborhoodAdapter()
    return _default_adapter
