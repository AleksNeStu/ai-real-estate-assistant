"""
The official Polish noise register (GIOŚ).

GIOŚ — Główny Inspektorat Ochrony Środowiska, the Chief Inspectorate of
Environmental Protection — publishes the results of the State Environmental
Monitoring (Państwowy Monitoring Środowiska) through an open API. There is
no key, no registration and no licence: the measurement points of the roads,
the railways, the industry and the airports, with the level in decibels and
the period it was measured in, are published as JSON.

The service's terms require that a user of the data names the source, so
every measurement this module produces carries the attribution.

The endpoint, read live on 2026-11-23:

    GET {base}/pomiar-halasu-w-srodowisku
        ?kategoria=Droga|Kolej|Przemysl|Lotnisko
        &wojewodztwo=<one of the sixteen>
        &dataOd=YYYY-MM-DD&dataDo=YYYY-MM-DD
        &numerStrony=N&liczbaElementowNaStronie=50

The answer carries the total number of records for the query and one page of
them. A page holds at most fifty records, and the records of a page are
ordered by their point code, so a place is not necessarily on the first page:
the client reads as many pages as it needs and stops as soon as a point
close enough to the place has been seen.

The register is a map of the whole country and not a lookup by coordinates,
so the client first decides which voivodeship the place is in — the
voivodeship whose centre is nearest — and asks that one. A place on a
voivodeship's boundary is asked twice: the second voivodeship answers when
the first holds nothing close enough.

The levels are the register's own: a level in decibels for a named period
("Dzień 16h" — the day at 16:00, "Noc 8h" — the night at 8:00). They are
not averaged into a single number here; the level and the period travel with
the measurement, and the quietness score is derived from the level.
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
GIOS_NOISE_URL = "https://dane.gios.gov.pl/api/halas/v1"

# The only host this adapter talks to.
GIOS_NOISE_ALLOWED_HOST = "dane.gios.gov.pl"

# The attribution the service's terms require.
GIOS_NOISE_ATTRIBUTION = "Source: Chief Inspectorate of Environmental Protection / dane.gios.gov.pl"

# The kinds of source the register knows.
GIOS_NOISE_CATEGORY_ROAD = "Droga"
GIOS_NOISE_CATEGORY_RAILWAY = "Kolej"
GIOS_NOISE_CATEGORY_INDUSTRIAL = "Przemysł"
GIOS_NOISE_CATEGORY_AIRPORT = "Lotnisko"

# The categories that are asked for first. The airports hold thousands of
# points — a grid around every runway — so they are asked for only when
# nothing else covers the place.
GIOS_NOISE_CATEGORIES: Tuple[str, ...] = (
    GIOS_NOISE_CATEGORY_ROAD,
    GIOS_NOISE_CATEGORY_RAILWAY,
    GIOS_NOISE_CATEGORY_INDUSTRIAL,
)

# How far a measurement point may be from the place and still speak for it.
GIOS_NOISE_COVER_RADIUS_KM = 10.0

# How close a point has to be to end the reading of a category early.
GIOS_NOISE_STOP_RADIUS_KM = 3.0

# How many pages of a category are read at most.
GIOS_NOISE_MAX_PAGES = 4

# How many records a page holds. The service refuses more.
GIOS_NOISE_PAGE_SIZE = 50

# How long the records of a category are cached.
GIOS_NOISE_CATALOGUE_TTL_SECONDS = 86400

# The window of the measurements that are read: the last two years. The
# register measures each point once every two years, so a shorter window
# leaves a place without a measurement and a longer one only adds pages.
GIOS_NOISE_WINDOW_YEARS = 2

# The voivodeships, with the box that holds them. The boxes overlap near the
# voivodeships' borders, so the voivodeship of a place is the one whose
# centre is nearest.
GIOS_VOIVODESHIPS: Dict[str, Tuple[float, float, float, float]] = {
    "DOLNOŚLĄSKIE": (50.80, 51.70, 14.10, 17.80),
    "KUJAWSKO-POMORSKIE": (52.50, 53.55, 16.90, 19.90),
    "LUBELSKIE": (50.30, 52.30, 21.80, 24.20),
    "LUBUSKIE": (51.40, 52.90, 14.60, 17.20),
    "ŁÓDZKIE": (50.80, 52.05, 18.00, 20.30),
    "MAŁOPOLSKIE": (48.90, 50.45, 19.40, 21.10),
    "MAZOWIECKIE": (50.85, 53.55, 20.60, 24.10),
    "OPOLSKIE": (49.90, 51.05, 17.20, 18.95),
    "PODKARPACKIE": (49.40, 50.90, 20.95, 23.20),
    "PODLASKIE": (52.60, 53.95, 22.00, 24.70),
    "POMORSKIE": (53.85, 54.85, 16.10, 19.80),
    "ŚLĄSKIE": (49.85, 51.00, 17.95, 19.80),
    "ŚWIĘTOKRZYSKIE": (50.55, 51.60, 19.80, 21.40),
    "WARMIŃSKO-MAZURSKIE": (53.10, 54.40, 18.90, 22.85),
    "WIELKOPOLSKIE": (51.35, 53.05, 15.85, 18.95),
    "ZACHODNIOPOMORSKIE": (52.65, 54.25, 14.35, 17.25),
}

# How many voivodeships are asked at most: the nearest one, and the two
# that border it — a place near a border is in the wrong one.
GIOS_NOISE_VOIVODESHIP_CANDIDATES = 3


@dataclass
class GiosNoiseMeasurement:
    """What the register says about the noise at one place."""

    category: str
    place: str
    latitude: float
    longitude: float
    decibels: float
    period: str
    measured_from: str
    measured_to: str
    point_code: str
    distance_km: float
    attribution: str = GIOS_NOISE_ATTRIBUTION


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """The great circle distance between two points, in kilometres."""
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(a))


def quietness_score(decibels: float) -> float:
    """
    The quietness score of a level in decibels.

    The scale is the one the neighbourhood index uses: 100 is the quietest
    and 0 the loudest, and 40 dB is the quiet end of it (a rural night) and
    80 dB the loud one (a motorway next to the window).

    Args:
        decibels: The level in dB, as the register publishes it.

    Returns:
        The score, from 0 to 100.
    """
    return max(0.0, min(100.0, 100.0 - (decibels - 40.0) * 2.5))


class GiosNoiseClient:
    """
    Reads the official register.

    The client is safe to share: the records of a category are cached for a
    day, and the cache grows — a second place in the same voivodeship reads
    only the pages the first place did not need.
    """

    def __init__(
        self,
        base_url: str = GIOS_NOISE_URL,
        timeout: int = 30,
        catalogue_ttl: int = GIOS_NOISE_CATALOGUE_TTL_SECONDS,
        window_years: int = GIOS_NOISE_WINDOW_YEARS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._catalogue_ttl = catalogue_ttl
        self._window_years = window_years
        self._records: Dict[Tuple[str, str], Tuple[List[Dict[str, Any]], int, bool, float]] = {}

    # -- the network ----------------------------------------------------

    def _validate_url(self, url: str) -> None:
        """Refuse anything that is not the register's own host."""
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(f"Rejected non-HTTPS URL: {parsed.scheme}")
        if parsed.hostname != GIOS_NOISE_ALLOWED_HOST:
            raise ValueError(f"Hostname not in allowlist: {parsed.hostname}")

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """One request to the register, or None when it does not answer."""
        url = f"{self._base_url}{path}"
        try:
            self._validate_url(url)
        except ValueError as exc:
            logger.warning("GIOŚ noise request refused: %s", sanitize_for_logging(exc))
            return None

        try:
            response = requests.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
            body = response.json()
            return body if isinstance(body, dict) else None
        except requests.RequestException as exc:
            logger.warning("GIOŚ noise request failed: %s", sanitize_for_logging(exc))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("GIOŚ noise answer could not be read: %s", sanitize_for_logging(exc))
        return None

    # -- the place ------------------------------------------------------

    def voivodeships(self, lat: float, lon: float) -> List[str]:
        """
        The voivodeships a place may be in, the nearest one first.

        Args:
            lat: Latitude of the place.
            lon: Longitude of the place.

        Returns:
            The names of the voivodeships, nearest centre first.
        """
        ranked = sorted(
            GIOS_VOIVODESHIPS.items(),
            key=lambda item: _haversine_km(
                lat,
                lon,
                (item[1][0] + item[1][1]) / 2,
                (item[1][2] + item[1][3]) / 2,
            ),
        )
        return [name for name, _ in ranked[:GIOS_NOISE_VOIVODESHIP_CANDIDATES]]

    # -- the records ----------------------------------------------------

    def _window(self) -> Tuple[str, str]:
        """The window of the measurements that are read."""
        now = time.gmtime()
        data_to = time.strftime("%Y-%m-%d", now)
        data_from = time.strftime(
            "%Y-%m-%d", time.gmtime(time.mktime(now) - self._window_years * 365 * 86400)
        )
        return data_from, data_to

    def _records_for(
        self, voivodeship: str, category: str, lat: float, lon: float
    ) -> List[Dict[str, Any]]:
        """
        The measurement records of one category, read as far as they are needed.

        The read stops as soon as a point close enough to the place has been
        seen, and the records that were read are kept: the next place in the
        same voivodeship reads only the pages this one did not need.

        Args:
            voivodeship: The voivodeship to ask.
            category: The kind of source to ask for.
            lat: Latitude of the place.
            lon: Longitude of the place.

        Returns:
            The records the register holds for the query.
        """
        key = (voivodeship, category)
        now = time.time()
        cached = self._records.get(key)
        if cached is None or now - cached[3] >= self._catalogue_ttl:
            cached = ([], 0, False, now)
        records, pages, exhausted, _ = cached

        data_from, data_to = self._window()
        while pages < GIOS_NOISE_MAX_PAGES and not exhausted:
            # A point close enough to the place ends the reading: the pages
            # that were read already answer the question.
            if self._nearest_distance(records, lat, lon) <= GIOS_NOISE_STOP_RADIUS_KM:
                break
            body = self._get(
                "/pomiar-halasu-w-srodowisku",
                {
                    "numerStrony": pages,
                    "liczbaElementowNaStronie": GIOS_NOISE_PAGE_SIZE,
                    "kategoria": category,
                    "wojewodztwo": voivodeship,
                    "dataOd": data_from,
                    "dataDo": data_to,
                },
            )
            if body is None:
                break
            data = body.get("dane") or {}
            page_rows = list(data.get("strona") or [])
            records.extend(page_rows)
            pages += 1
            try:
                total = int(data.get("liczbaRekordow") or 0)
            except (TypeError, ValueError):
                total = 0
            if not page_rows or len(records) >= total:
                exhausted = True
                break

        self._records[key] = (records, pages, exhausted, now)
        return records

    @staticmethod
    def _nearest_distance(records: Sequence[Dict[str, Any]], lat: float, lon: float) -> float:
        """The distance to the record of the list that is nearest to a place."""
        nearest = float("inf")
        for record in records:
            try:
                record_lat = float(record["coordWgs84Y"])
                record_lon = float(record["coordWgs84X"])
            except (KeyError, TypeError, ValueError):
                continue
            distance = _haversine_km(lat, lon, record_lat, record_lon)
            if distance < nearest:
                nearest = distance
        return nearest

    def _nearest_measurement(
        self, voivodeship: str, category: str, lat: float, lon: float
    ) -> Optional[GiosNoiseMeasurement]:
        """The measurement point of a category that is nearest to a place."""
        records = self._records_for(voivodeship, category, lat, lon)
        nearest: Optional[GiosNoiseMeasurement] = None
        nearest_distance = float("inf")
        for record in records:
            try:
                record_lat = float(record["coordWgs84Y"])
                record_lon = float(record["coordWgs84X"])
                decibels = float(record["wynikPomiaru"])
            except (KeyError, TypeError, ValueError):
                continue
            distance = _haversine_km(lat, lon, record_lat, record_lon)
            if distance >= nearest_distance:
                continue
            nearest_distance = distance
            nearest = GiosNoiseMeasurement(
                category=str(record.get("kategoria") or category),
                place=str(record.get("miejscowosc") or ""),
                latitude=record_lat,
                longitude=record_lon,
                decibels=decibels,
                period=str(record.get("pora") or ""),
                measured_from=str(record.get("dataOd") or ""),
                measured_to=str(record.get("dataDo") or ""),
                point_code=str(record.get("kodPunktuPomiarowego") or ""),
                distance_km=distance,
                attribution=GIOS_NOISE_ATTRIBUTION,
            )
        return nearest

    # -- the measurement ------------------------------------------------

    def measurement(self, lat: float, lon: float) -> Optional[GiosNoiseMeasurement]:
        """
        What the register says about the noise at a place.

        Args:
            lat: Latitude of the place.
            lon: Longitude of the place.

        Returns:
            The measurement of the point nearest to the place, or None when
            the register holds no point close enough to it.
        """
        for voivodeship in self.voivodeships(lat, lon):
            nearest: Optional[GiosNoiseMeasurement] = None
            for category in GIOS_NOISE_CATEGORIES:
                candidate = self._nearest_measurement(voivodeship, category, lat, lon)
                if candidate is None:
                    continue
                if nearest is None or candidate.distance_km < nearest.distance_km:
                    nearest = candidate

            if nearest is None or nearest.distance_km > GIOS_NOISE_COVER_RADIUS_KM:
                # Nothing of the usual kinds covers the place: an airport may.
                airport = self._nearest_measurement(
                    voivodeship, GIOS_NOISE_CATEGORY_AIRPORT, lat, lon
                )
                if airport is not None and (
                    nearest is None or airport.distance_km < nearest.distance_km
                ):
                    nearest = airport

            if nearest is not None and nearest.distance_km <= GIOS_NOISE_COVER_RADIUS_KM:
                return nearest
        return None
