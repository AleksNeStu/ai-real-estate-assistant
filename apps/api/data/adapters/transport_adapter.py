"""
Transport data adapter for fetching public transport accessibility from OpenStreetMap.

This adapter fetches public transport stop data for accessibility scoring,
including bus stops, tram stops, metro stations, and railway stations.
"""

import logging
import math
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from core.security_utils import sanitize_for_log
from utils.sanitization import sanitize_for_logging

logger = logging.getLogger(__name__)


@dataclass
class TransportStop:
    """
    Represents a public transport stop/station.

    Attributes:
        id: OSM element ID
        name: Stop/station name (if available)
        type: Transport type (bus, tram, metro, train, light_rail)
        latitude: Stop latitude
        longitude: Stop longitude
        distance_m: Distance from search center in meters (optional)
    """

    id: str
    name: Optional[str]
    type: str
    latitude: float
    longitude: float
    distance_m: Optional[float] = None


@dataclass
class TransportResult:
    """
    Result of a transport accessibility query.

    Attributes:
        score: Accessibility score 0-100
        total_stops: Total number of stops found
        stops_by_type: Count of stops by transport type
        stops: List of transport stop details
        data_source: Data source identifier
        confidence: Confidence score 0-1 based on data quality
    """

    score: float
    total_stops: int
    stops_by_type: Dict[str, int]
    stops: List[TransportStop]
    data_source: str
    confidence: float


class TransportAdapter:
    """
    Adapter for fetching public transport accessibility data from OpenStreetMap.

    Uses the Overpass API to query for:
    - Bus stops (public_transport=platform, highway=bus_stop)
    - Tram stops (railway=tram_stop, public_transport=platform)
    - Metro/subway entrances (railway=subway_entrance)
    - Railway stations (railway=station)
    - Light rail stops (railway=light_rail)

    Environment variables:
        OVERPASS_API_URL: Custom Overpass API endpoint (optional)

    Example:
        >>> adapter = TransportAdapter()
        >>> result = adapter.calculate_accessibility_score(52.2297, 21.0122)
        >>> print(f"Accessibility score: {result.score}")
        >>> print(f"Total stops: {result.total_stops}")
    """

    # Overpass API default endpoint
    DEFAULT_API_URL: str = "https://overpass-api.de/api/interpreter"

    # Transport stop tags for Overpass queries
    TRANSPORT_TAGS = [
        "bus_stop",  # highway=bus_stop
        "tram_stop",  # railway=tram_stop
        "subway_entrance",  # railway=subway_entrance
        "station",  # railway=station
        "light_rail",  # railway=light_rail
    ]

    # Mapping from OSM tags to normalized transport types
    TYPE_MAPPING = {
        "highway=bus_stop": "bus",
        "railway=tram_stop": "tram",
        "railway=subway_entrance": "metro",
        "railway=station": "train",
        "railway=light_rail": "light_rail",
        "public_transport=stop_position": "bus",  # Generic, defaults to bus
    }

    def __init__(self, api_url: Optional[str] = None) -> None:
        """
        Initialize the transport adapter.

        Args:
            api_url: Optional custom Overpass API URL
        """
        url_from_env = os.getenv("OVERPASS_API_URL")
        self._api_url: str = api_url or url_from_env or self.DEFAULT_API_URL
        self._timeout = 30

    def fetch_transport_pois(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 1000,
    ) -> List[TransportStop]:
        """
        Fetch public transport stops within a radius of coordinates.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters (default 1000m = 1km)

        Returns:
            List of TransportStop objects
        """
        # Build Overpass QL query for transport stops
        query = self._build_transport_query(latitude, longitude, radius_m)

        try:
            response = requests.get(
                self._api_url,
                params={"data": query},
                timeout=self._timeout,
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])

            # Parse transport stops
            stops = []
            for element in elements:
                stop = self._parse_transport_stop(element, latitude, longitude)
                if stop:
                    stops.append(stop)

            logger.info(
                "Found %s transport stops within %sm of (%s, %s)",
                len(stops),
                sanitize_for_log(radius_m),
                sanitize_for_log(latitude),
                sanitize_for_log(longitude),
            )

            return stops

        except requests.RequestException as e:
            logger.error(
                "Overpass API request failed: %s", sanitize_for_log(sanitize_for_logging(e))
            )
            return []
        except Exception as e:
            logger.error(
                "Failed to parse transport data: %s", sanitize_for_log(sanitize_for_logging(e))
            )
            return []

    def count_stops(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 500,
    ) -> int:
        """
        Count total transport stops within radius.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters (default 500m for walkability)

        Returns:
            Number of stops found
        """
        stops = self.fetch_transport_pois(latitude, longitude, radius_m)
        return len(stops)

    def get_stop_types(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 500,
    ) -> Dict[str, int]:
        """
        Count stops by transport type within radius.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters

        Returns:
            Dictionary with transport type counts
            {
                "bus": 5,
                "tram": 2,
                "metro": 1,
                "train": 0,
                "light_rail": 0
            }
        """
        stops = self.fetch_transport_pois(latitude, longitude, radius_m)

        # Count by type
        type_counts: Dict[str, int] = {
            "bus": 0,
            "tram": 0,
            "metro": 0,
            "train": 0,
            "light_rail": 0,
        }

        for stop in stops:
            if stop.type in type_counts:
                type_counts[stop.type] += 1

        return type_counts

    def calculate_accessibility_score(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 500,
    ) -> float:
        """
        Calculate public transport accessibility score.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters

        Returns:
            Accessibility score 0-100 based on:
            - Number of stops (more = better)
            - Transport diversity (multiple types = better)
            - Proximity to high-capacity transport (metro/train)
        """
        stops = self.fetch_transport_pois(latitude, longitude, radius_m)

        if not stops:
            return 20.0  # Poor accessibility baseline

        # Base score from stop count
        total_stops = len(stops)
        base_score = self._calculate_base_score(total_stops)

        # Calculate diversity bonus
        type_counts = self.get_stop_types(latitude, longitude, radius_m)
        diversity_score = self._calculate_diversity_bonus(type_counts)

        # Calculate high-capacity transport bonus
        capacity_bonus = self._calculate_capacity_bonus(type_counts)

        # Combine scores
        final_score = base_score + diversity_score + capacity_bonus

        # Cap at 100
        return round(min(100.0, final_score), 1)

    def get_full_result(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 500,
    ) -> TransportResult:
        """
        Get complete transport accessibility result.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters

        Returns:
            TransportResult with score, counts, and stop details
        """
        stops = self.fetch_transport_pois(latitude, longitude, radius_m)
        type_counts = self.get_stop_types(latitude, longitude, radius_m)
        score = self.calculate_accessibility_score(latitude, longitude, radius_m)

        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(stops, type_counts)

        return TransportResult(
            score=score,
            total_stops=len(stops),
            stops_by_type=type_counts,
            stops=stops,
            data_source="overpass",
            confidence=confidence,
        )

    def _build_transport_query(
        self,
        lat: float,
        lon: float,
        radius_m: int,
    ) -> str:
        """
        Build Overpass QL query for transport stops within radius.

        Args:
            lat: Center latitude
            lon: Center longitude
            radius_m: Search radius in meters

        Returns:
            Overpass QL query string
        """
        # Build query for various public transport tags
        query = f"""
            [out:json][timeout:25];
            (
              # Bus stops
              node["highway"="bus_stop"](around:{radius_m},{lat},{lon});
              way["highway"="bus_stop"](around:{radius_m},{lat},{lon});
              # Tram stops
              node["railway"="tram_stop"](around:{radius_m},{lat},{lon});
              way["railway"="tram_stop"](around:{radius_m},{lat},{lon});
              # Subway/metro entrances
              node["railway"="subway_entrance"](around:{radius_m},{lat},{lon});
              # Railway stations
              node["railway"="station"](around:{radius_m},{lat},{lon});
              way["railway"="station"](around:{radius_m},{lat},{lon});
              # Light rail
              node["railway"="light_rail"](around:{radius_m},{lat},{lon});
              way["railway"="light_rail"](around:{radius_m},{lat},{lon});
              # Generic public transport stops
              node["public_transport"="stop_position"](around:{radius_m},{lat},{lon});
              way["public_transport"="stop_position"](around:{radius_m},{lat},{lon});
              node["public_transport"="platform"](around:{radius_m},{lat},{lon});
              way["public_transport"="platform"](around:{radius_m},{lat},{lon});
            );
            out tags center;
            """

        return query.strip()

    def _parse_transport_stop(
        self,
        element: Dict[str, Any],
        center_lat: float,
        center_lon: float,
    ) -> Optional[TransportStop]:
        """
        Parse an OSM element into a TransportStop.

        Args:
            element: OSM element from Overpass response
            center_lat: Center latitude for distance calculation
            center_lon: Center longitude for distance calculation

        Returns:
            TransportStop object or None if parsing fails
        """
        tags = element.get("tags", {})
        if not tags:
            return None

        # Get coordinates
        if "lat" in element and "lon" in element:
            lat = element["lat"]
            lon = element["lon"]
        elif "center" in element:
            lat = element["center"]["lat"]
            lon = element["center"]["lon"]
        else:
            return None

        # Determine transport type
        transport_type = self._determine_transport_type(tags)

        # Get name
        name = tags.get("name") or tags.get("ref")

        # Calculate distance
        distance_m = self._calculate_distance(center_lat, center_lon, lat, lon)

        return TransportStop(
            id=str(element.get("id", "")),
            name=name,
            type=transport_type,
            latitude=lat,
            longitude=lon,
            distance_m=distance_m,
        )

    def _determine_transport_type(self, tags: Dict[str, str]) -> str:
        """
        Determine transport type from OSM tags.

        Args:
            tags: OSM element tags

        Returns:
            Normalized transport type string
        """
        # Check specific mappings first
        for tag_key, tag_value in tags.items():
            tag_str = f"{tag_key}={tag_value}"
            if tag_str in self.TYPE_MAPPING:
                return self.TYPE_MAPPING[tag_str]

        # Fallback logic
        if tags.get("railway") == "subway_entrance":
            return "metro"
        elif tags.get("railway") == "station":
            return "train"
        elif tags.get("highway") == "bus_stop":
            return "bus"
        elif tags.get("railway") == "tram_stop":
            return "tram"
        elif tags.get("railway") == "light_rail":
            return "light_rail"
        elif tags.get("public_transport") in ["stop_position", "platform"]:
            # Try to infer from other tags
            if tags.get("bus") == "yes":
                return "bus"
            elif tags.get("tram") == "yes":
                return "tram"
            elif tags.get("subway") == "yes":
                return "metro"
            elif tags.get("train") == "yes":
                return "train"
            else:
                return "bus"  # Default to bus for generic stops

        # Default fallback
        return "bus"

    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.

        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate

        Returns:
            Distance in meters
        """
        # Earth radius in meters
        earth_radius = 6371000

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        # Haversine formula
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return earth_radius * c

    def _calculate_base_score(self, total_stops: int) -> float:
        """
        Calculate base score from total stop count.

        Scoring logic:
        - 0 stops: 20 (poor)
        - 1-2 stops: 40
        - 3-5 stops: 60
        - 6-10 stops: 80
        - 11+ stops: 95

        Args:
            total_stops: Number of stops found

        Returns:
            Base score 0-95
        """
        if total_stops == 0:
            return 20.0
        elif total_stops <= 2:
            return 40.0
        elif total_stops <= 5:
            return 60.0
        elif total_stops <= 10:
            return 80.0
        else:
            return 95.0

    def _calculate_diversity_bonus(self, type_counts: Dict[str, int]) -> float:
        """
        Calculate bonus for transport type diversity.

        Args:
            type_counts: Dictionary of stop counts by type

        Returns:
            Bonus score 0-10
        """
        # Count non-zero types
        present_types = sum(1 for count in type_counts.values() if count > 0)

        if present_types <= 1:
            return 0.0
        elif present_types == 2:
            return 3.0
        elif present_types == 3:
            return 5.0
        elif present_types == 4:
            return 7.0
        else:
            return 10.0

    def _calculate_capacity_bonus(self, type_counts: Dict[str, int]) -> float:
        """
        Calculate bonus for high-capacity transport access.

        High-capacity transport (metro, train, light_rail) provides
        better connectivity than local bus/tram.

        Args:
            type_counts: Dictionary of stop counts by type

        Returns:
            Bonus score 0-5
        """
        bonus = 0.0

        if type_counts.get("metro", 0) > 0:
            bonus += 3.0
        if type_counts.get("train", 0) > 0:
            bonus += 2.0
        if type_counts.get("light_rail", 0) > 0:
            bonus += 1.5

        return round(min(5.0, bonus), 1)

    def _calculate_confidence(
        self,
        stops: List[TransportStop],
        type_counts: Dict[str, int],
    ) -> float:
        """
        Calculate confidence score based on data quality.

        Args:
            stops: List of transport stops
            type_counts: Stop counts by type

        Returns:
            Confidence score 0-1
        """
        if not stops:
            return 0.5  # Low confidence for empty results

        # Check for named stops (higher quality)
        named_ratio = sum(1 for s in stops if s.name) / len(stops)
        name_score = named_ratio * 0.3

        # Check for diversity
        type_diversity = sum(1 for count in type_counts.values() if count > 0)
        diversity_score = min(type_diversity / 5, 1.0) * 0.2

        # Base confidence for having data
        base_score = 0.5

        confidence = base_score + name_score + diversity_score

        return round(min(1.0, confidence), 2)


# Singleton instance for reuse
_default_adapter: Optional[TransportAdapter] = None


def get_transport_adapter() -> TransportAdapter:
    """Get or create the default transport adapter instance."""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = TransportAdapter()
    return _default_adapter
