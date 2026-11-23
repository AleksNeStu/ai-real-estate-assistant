"""
Air Quality adapter for fetching air quality data.

The default source is the official Polish register of air quality, published
by GIOŚ (Główny Inspektorat Ochrony Środowiska) as open data: the stations
of the State Environmental Monitoring, their measurements and their official
index, with no key and no registration. WAQI stays as the fallback for a
deployment that holds a token for it, and the city averages stay as the last
resort.

A deployment without a WAQI key used to answer with a city average — a
number that came from nowhere. It now answers with a measurement the state
publishes, and names the source, which the service's terms require.
"""

import ipaddress
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests

from data.adapters.gios_air_quality import (
    GIOS_API_URL,
    GIOS_ATTRIBUTION,
    GiosAirQualityClient,
    us_aqi_from_concentrations,
)
from utils.sanitization import redact_sensitive_data, sanitize_for_logging

logger = logging.getLogger(__name__)

ALLOWED_API_DOMAINS = {"api.waqi.info"}


# City average AQI values for Poland (fallback data)
# Source: Historical air quality data for major Polish cities
CITY_AQI_AVERAGES: Dict[str, Dict[str, Any]] = {
    "warsaw": {"aqi": 65, "pm25": 18.5, "pm10": 28.0},
    "krakow": {"aqi": 75, "pm25": 22.0, "pm10": 35.0},
    "lodz": {"aqi": 70, "pm25": 20.0, "pm10": 30.0},
    "wroclaw": {"aqi": 55, "pm25": 15.0, "pm10": 24.0},
    "poznan": {"aqi": 50, "pm25": 14.0, "pm10": 22.0},
    "gdansk": {"aqi": 45, "pm25": 12.0, "pm10": 20.0},
    "szczecin": {"aqi": 48, "pm25": 13.0, "pm10": 21.0},
    "katowice": {"aqi": 80, "pm25": 25.0, "pm10": 40.0},
}


@dataclass
class AirQualityStation:
    """
    Represents an air quality monitoring station.

    Attributes:
        station_id: Unique station identifier
        name: Station name
        latitude: Station latitude
        longitude: Station longitude
        aqi: Current AQI value
        distance_km: Distance from query location in km
    """

    station_id: str
    name: Optional[str]
    latitude: float
    longitude: float
    aqi: int
    distance_km: float


@dataclass
class AirQualityResult:
    """
    Result of an air quality query.

    Attributes:
        score: Normalized score 0-100 (higher is better)
        aqi_value: Raw AQI value (lower is better, 0-500 scale)
        pm25: PM2.5 concentration in µg/m³
        pm10: PM10 concentration in µg/m³
        data_source: Source of the data (gios, waqi, fallback)
        confidence: Confidence score 0-1 (1.0 = direct measurement)
        station_name: Name of the monitoring station
        attribution: Who published the measurement, when the source asks to
            be named
        official_index: The source's own index value, when it publishes one
        official_category: The source's own name for that value
    """

    score: float
    aqi_value: Optional[int]
    pm25: Optional[float]
    pm10: Optional[float]
    data_source: str
    confidence: float
    station_name: Optional[str]
    attribution: Optional[str] = None
    official_index: Optional[int] = None
    official_category: Optional[str] = None


class AirQualityAdapter:
    """
    Adapter for fetching air quality data.

    The default source is the official Polish register published by GIOŚ; WAQI
    is the fallback for a deployment that holds a token for it, and the city
    averages are the last resort.

    Environment variables:
        WAQI_API_KEY: API key for WAQI (free tier available at https://aqicn.org/data-platform/token/)
        AIR_QUALITY_CACHE_TTL: Cache TTL in seconds (default: 3600)

    Attributes:
        _api_key: WAQI API key
        _cache_ttl: Time-to-live for cached results
        _timeout: HTTP request timeout
        _gios: The client of the official register
    """

    # WAQI API endpoint
    API_URL: str = "https://api.waqi.info"

    # Default cache TTL (1 hour)
    DEFAULT_CACHE_TTL: int = 3600

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
        timeout: int = 30,
        gios_client: Optional[GiosAirQualityClient] = None,
    ) -> None:
        """
        Initialize the air quality adapter.

        Args:
            api_key: Optional WAQI API key (falls back to environment variable)
            cache_ttl: Optional cache TTL in seconds
            timeout: HTTP request timeout in seconds
            gios_client: Optional client of the official register (a test
                hands its own in)
        """
        import os

        self._api_key: Optional[str] = api_key or os.getenv("WAQI_API_KEY")
        ttl_env = os.getenv("AIR_QUALITY_CACHE_TTL")
        self._cache_ttl: int = cache_ttl or int(ttl_env) if ttl_env else self.DEFAULT_CACHE_TTL
        self._timeout: int = timeout
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._gios: GiosAirQualityClient = gios_client or GiosAirQualityClient(timeout=timeout)

        if not self._api_key:
            logger.info(
                "WAQI_API_KEY not configured. Air quality data comes from the official "
                "register (GIOŚ), and the city averages are the last resort."
            )

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(f"Rejected non-HTTPS URL: {parsed.scheme}")
        if parsed.hostname not in ALLOWED_API_DOMAINS:
            raise ValueError(f"Hostname not in allowlist: {parsed.hostname}")
        import socket

        try:
            resolved = socket.getaddrinfo(parsed.hostname, None)[0][4][0]
            addr = ipaddress.ip_address(resolved)
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                raise ValueError(f"Rejected private/internal IP: {resolved}")
        except socket.gaierror:
            pass

    def get_nearest_station(self, lat: float, lon: float) -> Optional[AirQualityStation]:
        """
        Find the nearest air quality monitoring station.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate

        Returns:
            AirQualityStation if found, None otherwise
        """
        if not self._api_key:
            logger.debug("No API key available for station lookup")
            return None

        cache_key = f"station:{lat}:{lon}"
        cached_result = self._get_station_from_cache(cache_key)
        if cached_result:
            return cached_result

        url = f"{self.API_URL}/feed/geo:{lat};{lon}/"
        params = {"token": self._api_key}

        try:
            self._validate_url(url)
            response = requests.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "ok":
                logger.warning(
                    f"WAQI API returned status: {sanitize_for_logging(data.get('status'))}"
                )
                return None

            station_data = data.get("data", {})
            if not station_data:
                logger.debug("No station data in response")
                return None

            # Extract station information
            station_id = str(station_data.get("idx", ""))
            name = station_data.get("city", {}).get("name")
            station_lat = float(station_data.get("city", {}).get("geo", [0, 0])[0])
            station_lon = float(station_data.get("city", {}).get("geo", [0, 0])[1])
            aqi = station_data.get("aqi", 0)

            # Calculate distance (simplified, assumes small distances)
            distance_km = self._haversine_distance(lat, lon, station_lat, station_lon)

            station = AirQualityStation(
                station_id=station_id,
                name=name,
                latitude=station_lat,
                longitude=station_lon,
                aqi=aqi,
                distance_km=distance_km,
            )

            self._put_in_cache(cache_key, station)
            logger.info(
                f"Found station '{sanitize_for_logging(name)}' {distance_km:.2f}km away with AQI {aqi}"
            )

            return station

        except requests.RequestException as e:
            logger.error(f"WAQI API request failed: {sanitize_for_logging(e)}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse WAQI response: {sanitize_for_logging(e)}")
            return None

    def get_aqi_score(self, lat: float, lon: float, city: Optional[str] = None) -> AirQualityResult:
        """
        Get air quality score for a location.

        The official register is read first: it needs no key, it is the state
        that publishes the measurements, and its terms ask for the source to
        be named — so the answer names it. WAQI answers only when the
        deployment holds a token for it and the register has nothing.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            city: City name for fallback data (optional)

        Returns:
            AirQualityResult with score and measurements
        """
        # The official register, which needs no key.
        gios_result = self._fetch_from_gios(lat, lon)
        if gios_result:
            return gios_result

        # WAQI, for a deployment that holds a token for it.
        if self._api_key:
            api_result = self._fetch_from_api(lat, lon)
            if api_result:
                return api_result

        # Fallback to city averages
        return self._get_fallback_result(city)

    def _fetch_from_gios(self, lat: float, lon: float) -> Optional[AirQualityResult]:
        """
        Fetch the air quality measurement from the official register.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate

        Returns:
            AirQualityResult if the register holds a measurement, None otherwise
        """
        try:
            measurement = self._gios.measurement(lat, lon)
        except Exception as exc:  # noqa: BLE001 - the fallback chain is the point
            logger.warning("GIOŚ could not be read: %s", sanitize_for_logging(exc))
            return None

        if measurement is None:
            return None

        aqi = us_aqi_from_concentrations(measurement.pm25, measurement.pm10)
        if aqi is None:
            return None

        return AirQualityResult(
            score=self._calculate_aqi_score(aqi),
            aqi_value=aqi,
            pm25=measurement.pm25,
            pm10=measurement.pm10,
            data_source="gios",
            confidence=1.0,
            station_name=measurement.station.name,
            attribution=measurement.attribution or GIOS_ATTRIBUTION,
            official_index=measurement.index_value,
            official_category=measurement.index_category,
        )

    def _fetch_from_api(self, lat: float, lon: float) -> Optional[AirQualityResult]:
        """
        Fetch air quality data from WAQI API.

        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate

        Returns:
            AirQualityResult if successful, None otherwise
        """
        cache_key = f"aqi:{lat}:{lon}"
        cached_result = self._get_aqi_result_from_cache(cache_key)
        if cached_result:
            return cached_result

        url = f"{self.API_URL}/feed/geo:{float(lat):.6f};{float(lon):.6f}/"
        params = {"token": self._api_key}

        try:
            self._validate_url(url)
            response = requests.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "ok":
                logger.warning(
                    f"WAQI API returned status: {sanitize_for_logging(data.get('status'))}"
                )
                return None

            station_data = data.get("data", {})
            if not station_data:
                return None

            aqi = station_data.get("aqi")
            station_name = station_data.get("city", {}).get("name")

            # Extract PM2.5 and PM10 from iaqi (individual air quality indices)
            iaqi = station_data.get("iaqi", {})
            pm25_data = iaqi.get("pm25", {})
            pm10_data = iaqi.get("pm10", {})

            pm25 = pm25_data.get("v") if pm25_data else None
            pm10 = pm10_data.get("v") if pm10_data else None

            result = AirQualityResult(
                score=self._calculate_aqi_score(aqi),
                aqi_value=aqi,
                pm25=pm25,
                pm10=pm10,
                data_source="waqi",
                confidence=1.0,  # High confidence for direct measurements
                station_name=station_name,
            )

            self._put_in_cache(cache_key, result)
            logger.info(
                f"WAQI data for {sanitize_for_logging(redact_sensitive_data(station_name))}: AQI={aqi}, PM2.5={pm25}, PM10={pm10}"
            )

            return result

        except requests.RequestException as e:
            logger.error(f"WAQI API request failed: {sanitize_for_logging(e)}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse WAQI response: {sanitize_for_logging(e)}")
            return None

    def _get_fallback_result(self, city: Optional[str]) -> AirQualityResult:
        """
        Get fallback air quality data using city averages.

        Args:
            city: City name (optional)

        Returns:
            AirQualityResult with city average data and reduced confidence
        """
        # Handle None or empty city
        if not city:
            logger.info("Using default air quality (no city provided): AQI=50")
            return AirQualityResult(
                score=self._calculate_aqi_score(50),
                aqi_value=50,
                pm25=14.0,
                pm10=22.0,
                data_source="fallback",
                confidence=0.3,
                station_name="Unknown (default)",
            )

        city_key = city.lower().strip()
        city_data = CITY_AQI_AVERAGES.get(city_key)

        if city_data:
            aqi = city_data["aqi"]
            pm25 = city_data["pm25"]
            pm10 = city_data["pm10"]
            logger.info(f"Using city average for {sanitize_for_logging(city)}: AQI={aqi}")
        else:
            # Default to moderate air quality
            aqi = 50
            pm25 = 14.0
            pm10 = 22.0
            logger.info(
                f"Using default air quality for unknown city '{sanitize_for_logging(city)}': AQI={aqi}"
            )

        return AirQualityResult(
            score=self._calculate_aqi_score(aqi),
            aqi_value=aqi,
            pm25=pm25,
            pm10=pm10,
            data_source="fallback",
            confidence=0.5,  # Reduced confidence for fallback data
            station_name=f"{city.title()} (average)",
        )

    def _calculate_aqi_score(self, aqi_value: Optional[int]) -> float:
        """
        Calculate normalized air quality score from AQI value.

        Score is inverted: lower AQI (better air quality) = higher score.
        Uses the US AQI scale where:
        - 0-50: Good (score 90-100)
        - 51-100: Moderate (score 70-89)
        - 101-150: Unhealthy for sensitive groups (score 50-69)
        - 151-200: Unhealthy (score 30-49)
        - 201-300: Very unhealthy (score 10-29)
        - 301+: Hazardous (score 0-9)

        Args:
            aqi_value: AQI value (0-500 scale)

        Returns:
            Normalized score 0-100 (higher is better)
        """
        if aqi_value is None:
            return 50.0  # Neutral score if no data

        if aqi_value <= 50:
            # Good: 90-100
            return 90.0 + (50 - aqi_value) * 0.2
        elif aqi_value <= 100:
            # Moderate: 70-89
            return 89.0 - (aqi_value - 50) * 0.38
        elif aqi_value <= 150:
            # Unhealthy for sensitive: 50-69
            return 69.0 - (aqi_value - 100) * 0.38
        elif aqi_value <= 200:
            # Unhealthy: 30-49
            return 49.0 - (aqi_value - 150) * 0.38
        elif aqi_value <= 300:
            # Very unhealthy: 10-29
            return 29.0 - (aqi_value - 200) * 0.19
        else:
            # Hazardous: 0-9
            return max(0.0, 9.0 - (aqi_value - 300) * 0.09)

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.

        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point

        Returns:
            Distance in kilometers
        """
        import math

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Differences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine formula
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in km
        radius = 6371.0

        return radius * c

    def _get_from_cache(self, key: str) -> Any:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if valid, None otherwise
        """
        import time

        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value
            else:
                # Remove expired entry
                del self._cache[key]
        return None

    def _get_station_from_cache(self, key: str) -> Optional[AirQualityStation]:
        """
        Get AirQualityStation from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached AirQualityStation if valid, None otherwise
        """
        import time

        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value  # type: ignore[no-any-return]
            else:
                # Remove expired entry
                del self._cache[key]
        return None

    def _get_aqi_result_from_cache(self, key: str) -> Optional[AirQualityResult]:
        """
        Get AirQualityResult from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached AirQualityResult if valid, None otherwise
        """
        import time

        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value  # type: ignore[no-any-return]
            else:
                # Remove expired entry
                del self._cache[key]
        return None

    def _put_in_cache(self, key: str, value: Any) -> None:
        """
        Put value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        import time

        self._cache[key] = (value, time.time())

    def get_status(self) -> Dict[str, Any]:
        """
        Get adapter status information.

        Returns:
            Dictionary with status information
        """
        return {
            "adapter": "AirQualityAdapter",
            "api_configured": bool(self._api_key),
            "cache_ttl": self._cache_ttl,
            "cache_size": len(self._cache),
            "api_endpoint": self.API_URL,
            "default_source": "gios",
            "default_source_endpoint": GIOS_API_URL,
        }


# Singleton instance for reuse
_default_adapter: Optional[AirQualityAdapter] = None


def get_air_quality_adapter() -> AirQualityAdapter:
    """Get or create the default air quality adapter instance."""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = AirQualityAdapter()
    return _default_adapter
