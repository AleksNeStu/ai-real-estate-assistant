"""
Google Routes API client for commute time calculations.

This module provides integration with Google Routes API to calculate
commute times between properties and destinations.

TASK-021: Commute Time Analysis
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from config.settings import get_settings
from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


@dataclass
class CommuteTimeResult:
    """Result from commute time calculation."""

    property_id: str
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    destination_name: Optional[str]
    duration_seconds: int
    duration_text: str
    distance_meters: int
    distance_text: str
    mode: str
    polyline: Optional[str]  # Encoded polyline for route visualization
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None


class CommuteTimeClient:
    """
    Client for Google Routes API commute time calculations.

    Supports:
    - Single property commute calculation
    - Batch property ranking by commute time
    - Multiple travel modes (driving, walking, bicycling, transit)
    - Route polyline for visualization
    """

    # Google Routes API endpoints
    ROUTES_BASE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

    # Travel modes supported by Google Routes API
    TRAVEL_MODES = {
        "driving": "DRIVE",
        "walking": "WALK",
        "bicycling": "BICYCLE",
        "transit": "TRANSIT",
    }

    # Routing preferences
    ROUTING_PREFERENCES = {
        "driving": "TRAFFIC_AWARE",
        "walking": "TRAFFIC_UNAWARE",
        "bicycling": "TRAFFIC_UNAWARE",
        "transit": "TRANSIT_AWARE",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
        cache_enabled: bool = True,
    ):
        """
        Initialize the commute time client.

        Args:
            api_key: Google Routes API key. If None, uses GOOGLE_ROUTES_API_KEY from settings.
            timeout_seconds: Request timeout in seconds.
            cache_enabled: Enable response caching to reduce API calls.
        """
        settings = get_settings()
        self.api_key = api_key or settings.google_routes_api_key
        self.enabled = settings.google_routes_enabled
        self.timeout_seconds = timeout_seconds
        self.cache_enabled = cache_enabled
        self._cache: Dict[str, CommuteTimeResult] = {}

        if not self.api_key and self.enabled:
            logger.warning(
                "GOOGLE_ROUTES_API_KEY not set. Commute time calculations will be disabled."
            )
            self.enabled = False

    def _get_cache_key(
        self,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        mode: str,
        departure_time: Optional[datetime],
    ) -> str:
        """Generate cache key for commute calculation."""
        time_part = departure_time.isoformat() if departure_time else "now"
        return f"{origin_lat:.6f},{origin_lon:.6f}_{destination_lat:.6f},{destination_lon:.6f}_{mode}_{time_part}"

    async def get_commute_time(
        self,
        property_id: str,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        mode: str = "transit",
        destination_name: Optional[str] = None,
        departure_time: Optional[datetime] = None,
    ) -> CommuteTimeResult:
        """
        Calculate commute time between two coordinates.

        Args:
            property_id: Property ID for the origin.
            origin_lat: Origin latitude.
            origin_lon: Origin longitude.
            destination_lat: Destination latitude.
            destination_lon: Destination longitude.
            mode: Travel mode - 'driving', 'walking', 'bicycling', or 'transit'.
            destination_name: Optional destination name for display.
            departure_time: Optional departure time for transit scheduling.

        Returns:
            CommuteTimeResult with duration, distance, and route information.

        Raises:
            ValueError: If mode is invalid or coordinates are invalid.
            httpx.HTTPError: If API request fails.
        """
        if not self.enabled:
            logger.warning("Google Routes API is disabled. Returning mock commute data.")
            return self._mock_commute_result(
                property_id=property_id,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                destination_lat=destination_lat,
                destination_lon=destination_lon,
                destination_name=destination_name,
                mode=mode,
                departure_time=departure_time,
            )

        # Validate mode
        if mode not in self.TRAVEL_MODES:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of: {', '.join(self.TRAVEL_MODES.keys())}"
            )

        # Check cache
        if self.cache_enabled:
            cache_key = self._get_cache_key(
                origin_lat, origin_lon, destination_lat, destination_lon, mode, departure_time
            )
            if cache_key in self._cache:
                logger.debug("Cache hit for commute calculation: %s", sanitize_for_log(cache_key))
                result = self._cache[cache_key]
                # Update property_id and destination_name for cached results
                result.property_id = property_id
                result.destination_name = destination_name
                return result

        # Build request
        travel_mode = self.TRAVEL_MODES[mode]
        routing_preference = self.ROUTING_PREFERENCES[mode]

        request_body = {
            "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lon}}},
            "destination": {
                "location": {"latLng": {"latitude": destination_lat, "longitude": destination_lon}}
            },
            "travelMode": travel_mode,
            "routingPreference": routing_preference,
            "computeAlternativeRoutes": False,
            "routeModifiers": {
                "avoidTolls": False,
                "avoidHighways": False,
                "avoidFerries": False,
            },
        }

        # Add departure time for transit mode
        if mode == "transit" and departure_time:
            request_body["departureTime"] = departure_time.isoformat()

        # Make API request
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key or "",
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline,.routes.travelAdvisory",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.ROUTES_BASE_URL,
                    json=request_body,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()

                # Parse response
                if not data.get("routes"):
                    raise ValueError("No routes found in API response")

                route = data["routes"][0]

                # Extract duration (in seconds)
                duration_str = route.get("duration", "")
                duration_seconds = self._parse_duration(duration_str)

                # Extract distance
                distance_meters = route.get("distanceMeters", 0)

                # Extract polyline
                polyline_obj = route.get("polyline", {})
                polyline = polyline_obj.get("encodedPolyline") if polyline_obj else None

                result = CommuteTimeResult(
                    property_id=property_id,
                    origin_lat=origin_lat,
                    origin_lon=origin_lon,
                    destination_lat=destination_lat,
                    destination_lon=destination_lon,
                    destination_name=destination_name,
                    duration_seconds=duration_seconds,
                    duration_text=self._format_duration(duration_seconds),
                    distance_meters=distance_meters,
                    distance_text=self._format_distance(distance_meters),
                    mode=mode,
                    polyline=polyline,
                    departure_time=departure_time,
                )

                # Cache result
                if self.cache_enabled and cache_key:
                    self._cache[cache_key] = result

                return result

        except httpx.HTTPStatusError as e:
            logger.error(
                "Google Routes API error: %s - %s",
                sanitize_for_log(e.response.status_code),
                sanitize_for_log(e.response.text),
            )
            raise
        except httpx.RequestError as e:
            logger.error("Google Routes API request failed: %s", sanitize_for_log(e))
            raise

    async def rank_properties_by_commute(
        self,
        property_ids: List[str],
        properties_lat_lon: Dict[str, tuple[float, float]],
        destination_lat: float,
        destination_lon: float,
        mode: str = "transit",
        destination_name: Optional[str] = None,
        departure_time: Optional[datetime] = None,
    ) -> List[CommuteTimeResult]:
        """
        Rank multiple properties by commute time to destination.

        Args:
            property_ids: List of property IDs to rank.
            properties_lat_lon: Mapping of property_id to (lat, lon) tuples.
            destination_lat: Destination latitude.
            destination_lon: Destination longitude.
            mode: Travel mode - 'driving', 'walking', 'bicycling', or 'transit'.
            destination_name: Optional destination name for display.
            departure_time: Optional departure time for transit scheduling.

        Returns:
            List of CommuteTimeResult sorted by duration (shortest first).
        """
        results = []

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent API calls

        async def fetch_commute_time(property_id: str) -> Optional[CommuteTimeResult]:
            try:
                if property_id not in properties_lat_lon:
                    logger.warning(
                        "Property %s not found in coordinates mapping",
                        sanitize_for_log(property_id),
                    )
                    return None

                lat, lon = properties_lat_lon[property_id]
                async with semaphore:
                    return await self.get_commute_time(
                        property_id=property_id,
                        origin_lat=lat,
                        origin_lon=lon,
                        destination_lat=destination_lat,
                        destination_lon=destination_lon,
                        mode=mode,
                        destination_name=destination_name,
                        departure_time=departure_time,
                    )
            except Exception as e:
                logger.error(
                    "Failed to calculate commute time for property %s: %s",
                    sanitize_for_log(property_id),
                    sanitize_for_log(e),
                )
                return None

        # Fetch commute times concurrently
        tasks = [fetch_commute_time(pid) for pid in property_ids]
        commute_results = await asyncio.gather(*tasks)

        # Filter out None results and sort by duration
        for result in commute_results:
            if result:
                results.append(result)

        results.sort(key=lambda r: r.duration_seconds)
        return results

    def _parse_duration(self, duration_str: str) -> int:
        """Parse duration string from Google API and convert to seconds."""
        # Google returns duration like "3600s" or "1h30m15s"
        if not duration_str:
            return 0

        try:
            # Remove 's' suffix and convert to int
            if duration_str.endswith("s"):
                return int(float(duration_str[:-1]))
            return int(float(duration_str))
        except (ValueError, IndexError):
            logger.warning("Could not parse duration: %s", sanitize_for_log(duration_str))
            return 0

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human-readable text."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours}h"

    def _format_distance(self, meters: int) -> str:
        """Format distance in meters to human-readable text."""
        if meters < 1000:
            return f"{meters}m"
        else:
            km = round(meters / 1000, 1)
            return f"{km}km"

    def _mock_commute_result(
        self,
        property_id: str,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        destination_name: Optional[str],
        mode: str,
        departure_time: Optional[datetime] = None,
    ) -> CommuteTimeResult:
        """
        Generate a mock commute result when API is disabled.

        Uses simple Haversine distance calculation to estimate commute time.
        """
        import math

        # Calculate distance using Haversine formula
        R = 6371000  # Earth's radius in meters
        lat1_rad = math.radians(origin_lat)
        lat2_rad = math.radians(destination_lat)
        delta_lat = math.radians(destination_lat - origin_lat)
        delta_lon = math.radians(destination_lon - origin_lon)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance_meters = int(R * c)

        # Estimate duration based on mode
        speed_kmh = {
            "driving": 40,  # Average city driving speed
            "walking": 5,
            "bicycling": 15,
            "transit": 25,  # Average including transfers
        }.get(mode, 25)

        duration_seconds = int((distance_meters / 1000) / speed_kmh * 3600)

        return CommuteTimeResult(
            property_id=property_id,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            destination_name=destination_name,
            duration_seconds=duration_seconds,
            duration_text=self._format_duration(duration_seconds),
            distance_meters=distance_meters,
            distance_text=self._format_distance(distance_meters),
            mode=mode,
            polyline=None,  # No polyline for mock data
            departure_time=departure_time,
        )

    def clear_cache(self) -> None:
        """Clear the commute time cache."""
        self._cache.clear()
        logger.info("Commute time cache cleared")
