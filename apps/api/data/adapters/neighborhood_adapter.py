"""
Neighborhood data adapter for fetching POI data from OpenStreetMap.

This adapter fetches Points of Interest (POI) data for neighborhood quality
scoring, including schools, amenities, green spaces, and walkability metrics.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from core.security_utils import sanitize_for_log
from data.adapters.overpass_area import (
    AreaMeasurement,
    ResolvedArea,
    measure_in_area,
)
from data.adapters.overpass_query import build_query, element_statement, tag_regex_filter

logger = logging.getLogger(__name__)


@dataclass
class AreaPois:
    """The POIs inside a named place, and the boundary they were counted in."""

    place_name: str
    schools: List[Dict[str, Any]] = field(default_factory=list)
    amenities: List[Dict[str, Any]] = field(default_factory=list)
    green_spaces: List[Dict[str, Any]] = field(default_factory=list)
    all: List[Dict[str, Any]] = field(default_factory=list)
    area: Optional[ResolvedArea] = None
    error: Optional[str] = None


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

    # The key a POI hangs on, the values of that key, and the element types
    # the provider answers with. The groups overlap on purpose: a
    # `supermarket` is an amenity and a shop, and a `forest` is a leisure
    # ground and a landuse.
    QUERY_TAG_GROUPS = [
        ("amenity", ["school", "kindergarten", "university", "college"], ("node", "way")),
        (
            "amenity",
            [
                "restaurant",
                "cafe",
                "supermarket",
                "pharmacy",
                "hospital",
                "clinic",
                "bank",
                "atm",
                "fuel",
                "post_office",
            ],
            ("node", "way"),
        ),
        ("shop", ["shop", "supermarket", "convenience", "bakery"], ("node",)),
        (
            "leisure",
            ["park", "garden", "forest", "grass", "meadow", "recreation_ground"],
            ("node", "way"),
        ),
        ("landuse", ["forest", "grass", "meadow", "recreation_ground"], ("node",)),
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
            result: Dict[str, List[Dict[str, Any]]] = self._categorise(
                elements, latitude, longitude
            )

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

    def fetch_pois_in_area(self, place_name: str) -> AreaPois:
        """
        Fetch the POIs inside a place the caller NAMED.

        The radius query above needs a point. A named place - a city, a
        district - has a boundary of its own, and the provider counts
        inside a boundary, so the place can be measured where it stands
        instead of being reduced to a point nobody gave.

        When the place cannot be resolved the result carries the reason
        and no POIs: an unmeasured place is worth saying out loud, and
        worth more than a number with nothing behind it.
        """
        measurement: AreaMeasurement = measure_in_area(
            place_name,
            self.QUERY_TAG_GROUPS,
            api_url=self._api_url,
        )

        if measurement.error:
            logger.warning(
                "The place %s could not be measured: %s",
                sanitize_for_log(place_name),
                sanitize_for_log(measurement.error),
            )
            return AreaPois(
                place_name=place_name,
                area=measurement.area,
                error=measurement.error,
            )

        categorised = self._categorise(measurement.elements, None, None)
        return AreaPois(
            place_name=place_name,
            schools=categorised["schools"],
            amenities=categorised["amenities"],
            green_spaces=categorised["green_spaces"],
            all=categorised["all"],
            area=measurement.area,
        )

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
        # A POI is a VALUE of a tag - `amenity=school`, `leisure=park`,
        # `landuse=forest` - and the key it hangs on differs per category.
        # One statement per key and per element type, each with the values
        # of that key: a union term names its element type every time, and
        # a filter on the existence of a key matches every tag of that name
        # rather than the value the category is about.
        around = f"{radius_m},{lat},{lon}"
        statements: List[str] = []
        for key, values, element_types in self.QUERY_TAG_GROUPS:
            if not set(values) & set(poi_tags):
                continue
            for element_type in element_types:
                statements.append(
                    element_statement(
                        element_type,
                        tag_regex_filter(key, values),
                        around,
                    )
                )

        return build_query(statements)

    def _categorise(
        self,
        elements: List[Dict[str, Any]],
        center_lat: Optional[float],
        center_lon: Optional[float],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Sort the elements the provider answered with into the categories the index scores.

        The distance is kept with every POI, because a count is only
        traceable to the features behind it when the reader can see which
        of them lie inside the radius the count was taken in.
        """
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

            poi_data = self._parse_poi_element(element, center_lat, center_lon)

            # Categorize by type
            if self._is_school(tags):
                result["schools"].append(poi_data)
            elif self._is_green_space(tags):
                result["green_spaces"].append(poi_data)
            elif self._is_amenity(tags):
                result["amenities"].append(poi_data)

            result["all"].append(poi_data)

        return result

    def _parse_poi_element(
        self,
        element: Dict[str, Any],
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Parse an OSM element into POI data.

        Args:
            element: OSM element from Overpass response
            center_lat: The point the query was made around, when there was one
            center_lon: The point the query was made around, when there was one

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

        distance_m: Optional[float] = None
        if center_lat is not None and center_lon is not None and lat is not None:
            distance_m = round(_distance_m(center_lat, center_lon, lat, lon), 1)

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
            "distance_m": distance_m,
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


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """The distance between two points, in metres."""
    radius = 6371000.0  # the Earth's radius
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_neighborhood_adapter() -> NeighborhoodAdapter:
    """Get or create the default neighborhood adapter instance."""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = NeighborhoodAdapter()
    return _default_adapter
