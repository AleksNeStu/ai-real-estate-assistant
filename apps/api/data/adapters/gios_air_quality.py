"""
The official Polish air quality register (GIOŚ).

GIOŚ — Główny Inspektorat Ochrony Środowiska, the Chief Inspectorate of
Environmental Protection — publishes the measurements of the State
Environmental Monitoring (Państwowy Monitoring Środowiska) through an open
API. There is no key, no registration and no licence: the stations with their
coordinates, the sensors on each station, the hourly measurement of each
sensor and the official air quality index of each station are all published
as JSON.

The service's terms require that a user of the data names the source, so
every measurement this module produces carries the attribution.

The endpoints, read live on 2026-11-23:

    GET {base}/station/findAll?page=N&size=100
    GET {base}/station/sensors/{stationId}
    GET {base}/data/getData/{sensorId}
    GET {base}/aqindex/getIndex/{stationId}

The API answers with Polish keys, and the values are the official ones: a
concentration in µg/m³, and the Polish index from 1 (bardzo dobry) to 6
(bardzo zły). The US AQI is not published, so the score this module produces
is computed from the concentrations with the EPA breakpoints — the same scale
the other adapter of this project uses, so a score means the same thing
whichever source answered.

The rate limits are published with the service: the station list is limited
to two requests a minute, the measurements to fifteen hundred. The station
list is therefore cached for a day and the sensors for a day too; only the
measurements are fetched per question, and those are cached for an hour.
"""

import logging
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import requests

from utils.sanitization import sanitize_for_logging

logger = logging.getLogger(__name__)

# The API's root.
GIOS_API_URL = "https://api.gios.gov.pl/pjp-api/v1/rest"

# The only host this adapter talks to.
GIOS_ALLOWED_HOST = "api.gios.gov.pl"

# The attribution the service's terms require.
GIOS_ATTRIBUTION = "GIOŚ — Państwowy Monitoring Środowiska (api.gios.gov.pl)"

# How far a station may be from the place and still be its station.
GIOS_STATION_RADIUS_KM = 50.0

# How long the station list and the sensors of a station are cached.
GIOS_CATALOGUE_TTL_SECONDS = 86400

# How long a measurement is cached.
GIOS_MEASUREMENT_TTL_SECONDS = 3600

# The EPA breakpoints for the US AQI, applied to the 24-hour mean of the
# hourly measurements so that a concentration means the same thing here as it
# does on the other side of the map.
#
# (concentration low, concentration high, AQI low, AQI high)
PM25_BREAKPOINTS: Tuple[Tuple[float, float, int, int], ...] = (
    (0.0, 9.0, 0, 50),
    (9.1, 35.4, 51, 100),
    (35.5, 55.4, 101, 150),
    (55.5, 125.4, 151, 200),
    (125.5, 225.4, 201, 300),
    (225.5, 325.4, 301, 500),
)

PM10_BREAKPOINTS: Tuple[Tuple[float, float, int, int], ...] = (
    (0.0, 54.0, 0, 50),
    (55.0, 154.0, 51, 100),
    (155.0, 254.0, 101, 150),
    (255.0, 354.0, 151, 200),
    (355.0, 424.0, 201, 300),
    (425.0, 504.0, 301, 500),
)


@dataclass
class GiosStation:
    """One station of the register."""

    station_id: int
    name: str
    latitude: float
    longitude: float
    city: Optional[str] = None
    code: Optional[str] = None


@dataclass
class GiosMeasurement:
    """What the register says about the air at one station."""

    station: GiosStation
    pm25: Optional[float] = None
    pm10: Optional[float] = None
    index_value: Optional[int] = None
    index_category: Optional[str] = None
    measured_at: Optional[str] = None
    attribution: str = GIOS_ATTRIBUTION


def us_aqi(concentration: Optional[float], breakpoints: Sequence[Any]) -> Optional[int]:
    """
    The US AQI of a concentration, from the EPA breakpoints.

    Args:
        concentration: The concentration in µg/m³, or None.
        breakpoints: The breakpoint table of the pollutant.

    Returns:
        The AQI, or None when there is no concentration to convert.
    """
    if concentration is None:
        return None

    for low, high, aqi_low, aqi_high in breakpoints:
        if low <= concentration <= high:
            if high == low:
                return aqi_low
            position = (concentration - low) / (high - low)
            return int(round(aqi_low + position * (aqi_high - aqi_low)))

    # Above the table the index is open: the last band runs to its ceiling.
    _, _, aqi_low, aqi_high = breakpoints[-1]
    return aqi_high


def us_aqi_from_concentrations(pm25: Optional[float], pm10: Optional[float]) -> Optional[int]:
    """The AQI of the worse of the two dust fractions."""
    values = [
        value
        for value in (
            us_aqi(pm25, PM25_BREAKPOINTS),
            us_aqi(pm10, PM10_BREAKPOINTS),
        )
        if value is not None
    ]
    return max(values) if values else None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """The great circle distance between two points, in kilometres."""
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(a))


class GiosAirQualityClient:
    """
    Reads the official register.

    The client is safe to share: the station list and the sensors are cached
    (the list may be fetched twice a minute), and the measurements are cached
    for an hour (they are published hourly).
    """

    def __init__(
        self,
        base_url: str = GIOS_API_URL,
        timeout: int = 30,
        catalogue_ttl: int = GIOS_CATALOGUE_TTL_SECONDS,
        measurement_ttl: int = GIOS_MEASUREMENT_TTL_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._catalogue_ttl = catalogue_ttl
        self._measurement_ttl = measurement_ttl
        self._stations: Optional[List[GiosStation]] = None
        self._stations_at: float = 0.0
        self._sensors: Dict[int, List[Dict[str, Any]]] = {}
        self._sensors_at: Dict[int, float] = {}
        self._measurements: Dict[str, Tuple[GiosMeasurement, float]] = {}

    # -- the network ----------------------------------------------------

    def _validate_url(self, url: str) -> None:
        """Refuse anything that is not the register's own host."""
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(f"Rejected non-HTTPS URL: {parsed.scheme}")
        if parsed.hostname != GIOS_ALLOWED_HOST:
            raise ValueError(f"Hostname not in allowlist: {parsed.hostname}")

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """One request to the register, or None when it does not answer."""
        url = f"{self._base_url}{path}"
        try:
            self._validate_url(url)
            response = requests.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except ValueError as exc:
            logger.warning("GIOŚ request refused: %s", sanitize_for_logging(exc))
        except requests.RequestException as exc:
            logger.warning("GIOŚ request failed: %s", sanitize_for_logging(exc))
        except (KeyError, TypeError) as exc:
            logger.warning("GIOŚ answer could not be read: %s", sanitize_for_logging(exc))
        return None

    # -- the catalogue --------------------------------------------------

    def stations(self) -> List[GiosStation]:
        """Every station of the register, cached for a day."""
        now = time.time()
        if self._stations is not None and now - self._stations_at < self._catalogue_ttl:
            return self._stations

        stations: List[GiosStation] = []
        page = 0
        total_pages = 1
        while page < total_pages:
            body = self._get("/station/findAll", {"page": page, "size": 100})
            if not body:
                break
            total_pages = int(body.get("totalPages") or 1)
            for entry in body.get("Lista stacji pomiarowych") or []:
                station = self._parse_station(entry)
                if station is not None:
                    stations.append(station)
            page += 1

        if stations:
            self._stations = stations
            self._stations_at = now
            logger.info("GIOŚ register: %d stations", len(stations))
        return stations

    @staticmethod
    def _parse_station(entry: Dict[str, Any]) -> Optional[GiosStation]:
        """One station out of the register's own shape."""
        try:
            return GiosStation(
                station_id=int(entry["Identyfikator stacji"]),
                name=str(entry.get("Nazwa stacji") or ""),
                latitude=float(entry["WGS84 φ N"]),
                longitude=float(entry["WGS84 λ E"]),
                city=entry.get("Nazwa miasta"),
                code=entry.get("Kod stacji"),
            )
        except (KeyError, TypeError, ValueError):
            return None

    def nearest_station(self, lat: float, lon: float) -> Optional[GiosStation]:
        """The station nearest to a place, when one is close enough to stand in for it."""
        stations = self.stations()
        if not stations:
            return None

        nearest: Optional[GiosStation] = None
        nearest_distance = GIOS_STATION_RADIUS_KM
        for station in stations:
            distance = _haversine_km(lat, lon, station.latitude, station.longitude)
            if distance < nearest_distance:
                nearest = station
                nearest_distance = distance
        return nearest

    def sensors(self, station_id: int) -> List[Dict[str, Any]]:
        """The sensors of a station, cached for a day."""
        now = time.time()
        cached_at = self._sensors_at.get(station_id)
        if cached_at is not None and now - cached_at < self._catalogue_ttl:
            return self._sensors.get(station_id, [])

        body = self._get(f"/station/sensors/{station_id}")
        if not body:
            return []
        sensors = list(body.get("Lista stanowisk pomiarowych dla podanej stacji") or [])
        self._sensors[station_id] = sensors
        self._sensors_at[station_id] = now
        return sensors

    # -- the measurement ------------------------------------------------

    def _sensor_id(self, sensors: Sequence[Dict[str, Any]], code: str) -> Optional[int]:
        """The sensor of a station that measures a given pollutant."""
        for sensor in sensors:
            if str(sensor.get("Wskaźnik - kod") or "").strip().upper() == code:
                try:
                    return int(sensor["Identyfikator stanowiska"])
                except (KeyError, TypeError, ValueError):
                    return None
        return None

    def _mean_concentration(self, sensor_id: int, hours: int = 24) -> Optional[float]:
        """The mean of the last hours of one sensor's measurements."""
        body = self._get(f"/data/getData/{sensor_id}", {"size": 100})
        if not body:
            return None
        values: List[float] = []
        for entry in body.get("Lista danych pomiarowych") or []:
            value = entry.get("Wartość")
            if value is None:
                continue
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
        if not values:
            return None
        recent = values[:hours]
        return sum(recent) / len(recent)

    def _index(self, station_id: int) -> Tuple[Optional[int], Optional[str]]:
        """The official index of a station: its value and its category."""
        body = self._get(f"/aqindex/getIndex/{station_id}")
        if not body:
            return None, None
        index = body.get("AqIndex") or {}
        value = index.get("Wartość indeksu")
        category = index.get("Nazwa kategorii indeksu")
        try:
            value = int(value) if value is not None else None
        except (TypeError, ValueError):
            value = None
        return value, category

    def measurement(self, lat: float, lon: float) -> Optional[GiosMeasurement]:
        """
        What the register says about the air at a place.

        Args:
            lat: Latitude of the place.
            lon: Longitude of the place.

        Returns:
            The measurement, or None when the register holds no station close
            enough to the place or holds no reading for it.
        """
        cache_key = f"{float(lat):.4f}:{float(lon):.4f}"
        now = time.time()
        cached = self._measurements.get(cache_key)
        if cached is not None and now - cached[1] < self._measurement_ttl:
            return cached[0]

        station = self.nearest_station(lat, lon)
        if station is None:
            return None

        sensors = self.sensors(station.station_id)
        pm25_sensor = self._sensor_id(sensors, "PM2.5")
        pm10_sensor = self._sensor_id(sensors, "PM10")

        pm25 = self._mean_concentration(pm25_sensor) if pm25_sensor else None
        pm10 = self._mean_concentration(pm10_sensor) if pm10_sensor else None
        index_value, index_category = self._index(station.station_id)

        if pm25 is None and pm10 is None and index_value is None:
            return None

        measurement = GiosMeasurement(
            station=station,
            pm25=pm25,
            pm10=pm10,
            index_value=index_value,
            index_category=index_category,
            attribution=GIOS_ATTRIBUTION,
        )
        self._measurements[cache_key] = (measurement, now)
        return measurement
