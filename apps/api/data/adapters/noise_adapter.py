"""
Noise level adapter for estimating environmental noise from OpenStreetMap.

This adapter uses the Overpass API to query OpenStreetMap for noise sources
and estimates noise levels based on proximity to roads, railways, airports,
and industrial areas.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


@dataclass
class NoiseSource:
    """
    Represents a source of noise near a location.

    Attributes:
        id: Unique identifier for the noise source
        type: Type of noise source (road, railway, airport, industrial)
        name: Optional name of the noise source
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        distance_m: Distance from the query point in meters
        severity: Severity score 0-1 (higher = more noise impact)
        tags: Original OSM tags for reference
    """

    id: str
    type: str
    name: Optional[str]
    latitude: float
    longitude: float
    distance_m: float
    severity: float
    tags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "distance_m": round(self.distance_m, 1),
            "severity": round(self.severity, 2),
        }


@dataclass
class NoiseResult:
    """
    Result of a noise level estimation.

    Attributes:
        score: Quietness score 0-100 (higher = quieter/lower noise)
        estimated_db: Estimated decibel level (40-80 range)
        noise_sources: List of detected noise sources
        data_source: Source of the data (e.g., "overpass_api")
        confidence: Confidence score 0-1 based on data quality
        query_latitude: Query point latitude
        query_longitude: Query point longitude
    """

    score: float
    estimated_db: float
    noise_sources: List[NoiseSource]
    data_source: str
    confidence: float
    query_latitude: float
    query_longitude: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "score": round(self.score, 1),
            "estimated_db": round(self.estimated_db, 1),
            "noise_sources": [source.to_dict() for source in self.noise_sources],
            "data_source": self.data_source,
            "confidence": round(self.confidence, 2),
            "query_latitude": self.query_latitude,
            "query_longitude": self.query_longitude,
        }


class NoiseAdapter:
    """
    Adapter for estimating noise levels using OpenStreetMap data.

    Uses the Overpass API to detect noise sources and calculate a quietness score.
    Higher scores indicate quieter areas (less noise).

    Noise sources detected:
    - Major roads: motorway, trunk, primary, secondary highways
    - Railways: rail, light_rail, subway tracks
    - Airports: aerodromes, helipads
    - Industrial: industrial and commercial land use areas

    Environment variables:
        OVERPASS_API_URL: Custom Overpass API endpoint (optional)
    """

    # Overpass API default endpoint
    DEFAULT_API_URL: str = "https://overpass-api.de/api/interpreter"

    # Noise source type classifications
    NOISE_TYPE_ROAD = "road"
    NOISE_TYPE_RAILWAY = "railway"
    NOISE_TYPE_AIRPORT = "airport"
    NOISE_TYPE_INDUSTRIAL = "industrial"

    # OSM tags for noise sources
    ROAD_HIGHWAY_TAGS = ["motorway", "trunk", "primary", "secondary"]
    RAILWAY_TAGS = ["rail", "light_rail", "subway", "tram", "narrow_gauge"]
    AIRPORT_TAGS = ["aerodrome", "aeroway", "helipad", "heliport"]
    INDUSTRIAL_LANDUSE_TAGS = ["industrial", "commercial"]

    # Severity scores for different noise sources (0-1)
    ROAD_SEVERITY = {
        "motorway": 1.0,
        "trunk": 0.8,
        "primary": 0.6,
        "secondary": 0.4,
    }
    RAILWAY_SEVERITY = {
        "rail": 0.9,
        "light_rail": 0.7,
        "subway": 0.6,
        "tram": 0.5,
        "narrow_gauge": 0.4,
    }
    AIRPORT_SEVERITY = 1.0
    INDUSTRIAL_SEVERITY = 0.5

    # Base quietness score (no noise sources)
    BASE_SCORE = 95.0

    # Distance thresholds in meters
    NEARBY_THRESHOLD = 500
    AIRPORT_THRESHOLD = 2000

    # Penalties for noise sources
    PENALTY_MAJOR_ROAD_NEAR = 45.0  # Major road <100m
    PENALTY_MAJOR_ROAD_MEDIUM = 25.0  # Major road 100-200m
    PENALTY_MINOR_ROAD_FAR = 10.0  # Minor road >200m
    PENALTY_RAILWAY_NEAR = 15.0  # Railway <200m
    PENALTY_AIRPORT_NEAR = 20.0  # Airport <2km
    PENALTY_INDUSTRIAL_NEAR = 10.0  # Industrial <500m

    # Distance thresholds for penalties
    DISTANCE_NEAR = 100
    DISTANCE_MEDIUM = 200

    def __init__(self, api_url: Optional[str] = None) -> None:
        """
        Initialize the noise adapter.

        Args:
            api_url: Optional custom Overpass API URL
        """
        url_from_env = os.getenv("OVERPASS_API_URL")
        self._api_url: str = api_url or url_from_env or self.DEFAULT_API_URL
        self._timeout = 30

    def estimate_noise_level(self, latitude: float, longitude: float) -> NoiseResult:
        """
        Estimate noise level for a given location.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            NoiseResult with score, estimated decibels, and noise sources
        """
        try:
            # Get nearby noise sources
            noise_sources = self.get_nearby_noise_sources(latitude, longitude)

            # Calculate noise score
            score = self.calculate_noise_score(latitude, longitude)

            # Estimate decibels based on noise sources
            estimated_db = self._estimate_decibels(noise_sources)

            # Calculate confidence based on data completeness
            confidence = self._calculate_confidence(noise_sources)

            return NoiseResult(
                score=score,
                estimated_db=estimated_db,
                noise_sources=noise_sources,
                data_source="overpass_api",
                confidence=confidence,
                query_latitude=latitude,
                query_longitude=longitude,
            )

        except Exception as e:
            logger.error("Failed to estimate noise level: %s", sanitize_for_log(e))
            # Return default result on error
            return NoiseResult(
                score=50.0,
                estimated_db=55.0,
                noise_sources=[],
                data_source="overpass_api",
                confidence=0.0,
                query_latitude=latitude,
                query_longitude=longitude,
            )

    def get_nearby_noise_sources(
        self, latitude: float, longitude: float, radius_m: int = 500
    ) -> List[NoiseSource]:
        """
        Get noise sources near a location.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_m: Search radius in meters (default 500m)

        Returns:
            List of NoiseSource objects sorted by distance
        """
        noise_sources: List[NoiseSource] = []

        # Query for different types of noise sources
        noise_sources.extend(self._query_roads(latitude, longitude, radius_m))
        noise_sources.extend(self._query_railways(latitude, longitude, radius_m))
        noise_sources.extend(self._query_airports(latitude, longitude))
        noise_sources.extend(self._query_industrial(latitude, longitude, radius_m))

        # Sort by distance
        noise_sources.sort(key=lambda s: s.distance_m)

        return noise_sources

    def calculate_noise_score(self, latitude: float, longitude: float) -> float:
        """
        Calculate noise score (0-100, higher = quieter).

        Scoring logic:
        - Base score: 95 (no noise sources)
        - Penalties reduce the score based on noise source proximity and type

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Noise score 0-100 (higher = quieter)
        """
        noise_sources = self.get_nearby_noise_sources(latitude, longitude)
        score = self.BASE_SCORE

        # Group noise sources by type and find closest of each type
        roads = [s for s in noise_sources if s.type == self.NOISE_TYPE_ROAD]
        railways = [s for s in noise_sources if s.type == self.NOISE_TYPE_RAILWAY]
        airports = [s for s in noise_sources if s.type == self.NOISE_TYPE_AIRPORT]
        industrials = [s for s in noise_sources if s.type == self.NOISE_TYPE_INDUSTRIAL]

        # Apply road penalties
        if roads:
            closest_road = min(roads, key=lambda r: r.distance_m)
            if closest_road.severity >= 0.8:  # Major road (motorway, trunk)
                if closest_road.distance_m < self.DISTANCE_NEAR:
                    score -= self.PENALTY_MAJOR_ROAD_NEAR
                elif closest_road.distance_m < self.DISTANCE_MEDIUM:
                    score -= self.PENALTY_MAJOR_ROAD_MEDIUM
            else:  # Minor road
                if closest_road.distance_m > self.DISTANCE_MEDIUM:
                    score -= self.PENALTY_MINOR_ROAD_FAR
                else:
                    score -= self.PENALTY_MAJOR_ROAD_NEAR * 0.5

        # Apply railway penalty
        if railways:
            closest_railway = min(railways, key=lambda r: r.distance_m)
            if closest_railway.distance_m < self.DISTANCE_MEDIUM:
                score -= self.PENALTY_RAILWAY_NEAR

        # Apply airport penalty
        if airports:
            closest_airport = min(airports, key=lambda a: a.distance_m)
            if closest_airport.distance_m < self.AIRPORT_THRESHOLD:
                score -= self.PENALTY_AIRPORT_NEAR

        # Apply industrial penalty
        if industrials:
            closest_industrial = min(industrials, key=lambda i: i.distance_m)
            if closest_industrial.distance_m < self.NEARBY_THRESHOLD:
                score -= self.PENALTY_INDUSTRIAL_NEAR

        # Ensure score is within valid range
        return max(0.0, min(100.0, score))

    def _query_roads(self, lat: float, lon: float, radius_m: int) -> List[NoiseSource]:
        """Query for major roads near the location."""
        noise_sources: List[NoiseSource] = []

        # Build tag filters for roads
        tag_filters = " | ".join(f'["{tag}"]' for tag in self.ROAD_HIGHWAY_TAGS)

        query = f"""
            [out:json][timeout:25];
            (
              way{tag_filters}(around:{radius_m},{lat},{lon});
            );
            out tags center;
            """

        try:
            response = requests.get(
                self._api_url,
                params={"data": query},
                timeout=self._timeout,
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])

            for element in elements:
                tags = element.get("tags", {})
                highway_type = tags.get("highway", "")

                if not highway_type or highway_type not in self.ROAD_HIGHWAY_TAGS:
                    continue

                # Get coordinates
                coords = self._extract_coordinates(element)
                if not coords:
                    continue

                distance = self._calculate_distance(lat, lon, coords["lat"], coords["lon"])
                severity = self.ROAD_SEVERITY.get(highway_type, 0.5)

                noise_sources.append(
                    NoiseSource(
                        id=f"road_{element.get('id', '')}",
                        type=self.NOISE_TYPE_ROAD,
                        name=self._get_road_name(tags),
                        latitude=coords["lat"],
                        longitude=coords["lon"],
                        distance_m=distance,
                        severity=severity,
                        tags=tags,
                    )
                )

        except requests.RequestException as e:
            logger.error("Failed to query roads: %s", sanitize_for_log(e))

        return noise_sources

    def _query_railways(self, lat: float, lon: float, radius_m: int) -> List[NoiseSource]:
        """Query for railways near the location."""
        noise_sources: List[NoiseSource] = []

        # Build tag filters for railways
        tag_filters = " | ".join(f'["{tag}"]' for tag in self.RAILWAY_TAGS)

        query = f"""
            [out:json][timeout:25];
            (
              way{tag_filters}(around:{radius_m},{lat},{lon});
            );
            out tags center;
            """

        try:
            response = requests.get(
                self._api_url,
                params={"data": query},
                timeout=self._timeout,
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])

            for element in elements:
                tags = element.get("tags", {})
                railway_type = tags.get("railway", "")

                if not railway_type:
                    continue

                # Get coordinates
                coords = self._extract_coordinates(element)
                if not coords:
                    continue

                distance = self._calculate_distance(lat, lon, coords["lat"], coords["lon"])
                severity = self.RAILWAY_SEVERITY.get(railway_type, 0.5)

                noise_sources.append(
                    NoiseSource(
                        id=f"railway_{element.get('id', '')}",
                        type=self.NOISE_TYPE_RAILWAY,
                        name=self._get_railway_name(tags),
                        latitude=coords["lat"],
                        longitude=coords["lon"],
                        distance_m=distance,
                        severity=severity,
                        tags=tags,
                    )
                )

        except requests.RequestException as e:
            logger.error("Failed to query railways: %s", sanitize_for_log(e))

        return noise_sources

    def _query_airports(self, lat: float, lon: float) -> List[NoiseSource]:
        """Query for airports near the location."""
        noise_sources: List[NoiseSource] = []

        # Use larger radius for airports (2km)
        query = f"""
            [out:json][timeout:25];
            (
              way["aeroway"="aerodrome"](around:{self.AIRPORT_THRESHOLD},{lat},{lon});
              way["aeroway"="helipad"](around:{self.AIRPORT_THRESHOLD},{lat},{lon});
              node["aeroway"="aerodrome"](around:{self.AIRPORT_THRESHOLD},{lat},{lon});
              node["aeroway"="helipad"](around:{self.AIRPORT_THRESHOLD},{lat},{lon});
            );
            out tags center;
            """

        try:
            response = requests.get(
                self._api_url,
                params={"data": query},
                timeout=self._timeout,
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])

            for element in elements:
                tags = element.get("tags", {})

                # Get coordinates
                coords = self._extract_coordinates(element)
                if not coords:
                    continue

                distance = self._calculate_distance(lat, lon, coords["lat"], coords["lon"])

                noise_sources.append(
                    NoiseSource(
                        id=f"airport_{element.get('id', '')}",
                        type=self.NOISE_TYPE_AIRPORT,
                        name=tags.get("name") or tags.get("aeroway"),
                        latitude=coords["lat"],
                        longitude=coords["lon"],
                        distance_m=distance,
                        severity=self.AIRPORT_SEVERITY,
                        tags=tags,
                    )
                )

        except requests.RequestException as e:
            logger.error("Failed to query airports: %s", sanitize_for_log(e))

        return noise_sources

    def _query_industrial(self, lat: float, lon: float, radius_m: int) -> List[NoiseSource]:
        """Query for industrial areas near the location."""
        noise_sources: List[NoiseSource] = []

        # Build tag filters for industrial/commercial areas
        tag_filters = " | ".join(f'["landuse"="{tag}"]' for tag in self.INDUSTRIAL_LANDUSE_TAGS)

        query = f"""
            [out:json][timeout:25];
            (
              way{tag_filters}(around:{radius_m},{lat},{lon});
              relation{tag_filters}(around:{radius_m},{lat},{lon});
            );
            out tags center;
            """

        try:
            response = requests.get(
                self._api_url,
                params={"data": query},
                timeout=self._timeout,
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])

            for element in elements:
                tags = element.get("tags", {})

                # Get coordinates
                coords = self._extract_coordinates(element)
                if not coords:
                    continue

                distance = self._calculate_distance(lat, lon, coords["lat"], coords["lon"])

                noise_sources.append(
                    NoiseSource(
                        id=f"industrial_{element.get('id', '')}",
                        type=self.NOISE_TYPE_INDUSTRIAL,
                        name=tags.get("name") or tags.get("landuse"),
                        latitude=coords["lat"],
                        longitude=coords["lon"],
                        distance_m=distance,
                        severity=self.INDUSTRIAL_SEVERITY,
                        tags=tags,
                    )
                )

        except requests.RequestException as e:
            logger.error("Failed to query industrial areas: %s", sanitize_for_log(e))

        return noise_sources

    def _extract_coordinates(self, element: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Extract coordinates from an OSM element.

        Args:
            element: OSM element from Overpass response

        Returns:
            Dict with 'lat' and 'lon' or None
        """
        if "lat" in element and "lon" in element:
            return {"lat": element["lat"], "lon": element["lon"]}
        elif "center" in element:
            return {"lat": element["center"]["lat"], "lon": element["center"]["lon"]}
        return None

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points in meters using Haversine formula.

        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates

        Returns:
            Distance in meters
        """
        import math

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

    def _estimate_decibels(self, noise_sources: List[NoiseSource]) -> float:
        """
        Estimate decibel level based on noise sources.

        Base level: 40dB (quiet rural)
        Add contributions from noise sources based on severity and distance

        Args:
            noise_sources: List of detected noise sources

        Returns:
            Estimated decibel level (40-80 range)
        """
        base_db = 40.0

        for source in noise_sources:
            # Distance attenuation factor (0-1)
            distance_factor = max(0, 1 - (source.distance_m / 1000))

            # Contribution based on severity and distance
            contribution = source.severity * 20 * distance_factor

            # Apply type-specific adjustments
            if source.type == self.NOISE_TYPE_AIRPORT:
                # Airports have significant impact even at distance
                contribution *= 1.5
            elif source.type == self.NOISE_TYPE_RAILWAY:
                # Railways have intermittent but loud noise
                contribution *= 1.2

            base_db += contribution

        # Clamp to reasonable range
        return max(40.0, min(80.0, base_db))

    def _calculate_confidence(self, noise_sources: List[NoiseSource]) -> float:
        """
        Calculate confidence score based on data quality.

        Higher confidence when:
        - More noise sources detected (better OSM coverage)
        - Sources have names (verified data)

        Args:
            noise_sources: List of detected noise sources

        Returns:
            Confidence score 0-1
        """
        if not noise_sources:
            # Could mean truly quiet area or poor OSM coverage
            return 0.5

        # Count named sources (higher quality data)
        named_count = sum(1 for s in noise_sources if s.name)

        # Base confidence on source count
        confidence = min(0.9, 0.3 + (len(noise_sources) * 0.1))

        # Boost if sources have names
        if named_count > 0:
            confidence = min(0.95, confidence + 0.1)

        return round(confidence, 2)

    def _get_road_name(self, tags: Dict[str, str]) -> Optional[str]:
        """Extract road name from OSM tags."""
        return tags.get("name") or tags.get("ref")

    def _get_railway_name(self, tags: Dict[str, str]) -> Optional[str]:
        """Extract railway name from OSM tags."""
        return tags.get("name") or tags.get("railway")


# Singleton instance for reuse
_default_adapter: Optional[NoiseAdapter] = None


def get_noise_adapter() -> NoiseAdapter:
    """Get or create the default noise adapter instance."""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = NoiseAdapter()
    return _default_adapter
