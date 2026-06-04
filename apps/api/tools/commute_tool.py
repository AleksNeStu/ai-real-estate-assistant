"""
Commute time analysis tool using OSRM (Open Source Routing Machine) public API.

Provides free commute time estimation without requiring an API key.
Supports car, bike, and foot travel modes with response caching and
graceful rate-limit handling.

Task #114: Commute and Accessibility Analysis
"""

import asyncio
import logging
import time
from typing import Any, ClassVar, Dict, List, Optional, Tuple

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OSRM client
# ---------------------------------------------------------------------------

_OSRM_BASE_URL = "https://router.project-osrm.org/route/v1"

# TTL-based cache entry
_CacheEntry = Tuple[float, Dict[str, Any]]  # (expires_at, data)


class OSRMCommuteClient:
    """
    Lightweight client for the public OSRM demo server.

    Supported profiles: ``car``, ``bike``, ``foot``.
    The public server is rate-limited and should NOT be used for heavy
    production workloads -- it is intended for prototyping and low-volume use.
    """

    PROFILES: ClassVar[Dict[str, str]] = {
        "car": "car",
        "driving": "car",
        "bike": "bike",
        "bicycling": "bike",
        "bicycle": "bike",
        "foot": "foot",
        "walking": "foot",
    }

    def __init__(
        self,
        base_url: str = _OSRM_BASE_URL,
        timeout_seconds: float = 10.0,
        cache_ttl_seconds: int = 300,
        max_cache_size: int = 512,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_cache_size = max_cache_size
        self._cache: Dict[str, _CacheEntry] = {}

    # -- public API ----------------------------------------------------------

    async def get_route(
        self,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        mode: str = "car",
    ) -> Dict[str, Any]:
        """
        Request a route from OSRM and return parsed result.

        Returns dict with keys: ``duration_seconds``, ``distance_km``,
        ``mode``, ``geometry`` (encoded polyline).
        """
        profile = self.PROFILES.get(mode.lower())
        if profile is None:
            raise ValueError(
                f"Unsupported mode '{mode}'. Supported: {', '.join(sorted(set(self.PROFILES.values())))}"
            )

        cache_key = f"{profile}:{float(origin_lat):.6f},{float(origin_lon):.6f}:{float(destination_lat):.6f},{float(destination_lon):.6f}"

        # Check cache
        now = time.monotonic()
        entry = self._cache.get(cache_key)
        if entry is not None and entry[0] > now:
            logger.debug("OSRM cache hit: %s", sanitize_for_log(cache_key))
            return entry[1]

        url = (
            f"{self.base_url}/{profile}"
            f"/{float(origin_lon):.6f},{float(origin_lat):.6f}"
            f";{float(destination_lon):.6f},{float(destination_lat):.6f}"
            "?overview=simplified&geometries=geojson"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.get(url)

            if resp.status_code == 429:
                logger.warning("OSRM rate limited; returning haversine estimate")
                return self._haversine_estimate(
                    origin_lat, origin_lon, destination_lat, destination_lon, mode
                )

            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != "Ok" or not data.get("routes"):
                logger.warning("OSRM returned no route for %s", sanitize_for_log(cache_key))
                return self._haversine_estimate(
                    origin_lat, origin_lon, destination_lat, destination_lon, mode
                )

            route = data["routes"][0]
            duration_seconds = int(route.get("duration", 0))
            distance_km = round(route.get("distance", 0) / 1000, 2)

            # Extract geometry (GeoJSON LineString coordinates)
            geometry: Optional[str] = None
            geom_obj = route.get("geometry")
            if isinstance(geom_obj, dict) and "coordinates" in geom_obj:
                # Store as stringified GeoJSON for downstream use
                import json as _json

                geometry = _json.dumps(geom_obj["coordinates"])

            result: Dict[str, Any] = {
                "duration_seconds": duration_seconds,
                "distance_km": distance_km,
                "mode": mode,
                "geometry": geometry,
                "data_source": "osrm",
            }

            # Store in cache (evict oldest entries if over limit)
            self._maybe_evict()
            self._cache[cache_key] = (now + self.cache_ttl_seconds, result)

            return result

        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("OSRM request failed (%s); falling back to haversine", exc)
            return self._haversine_estimate(
                origin_lat, origin_lon, destination_lat, destination_lon, mode
            )

    async def batch_routes(
        self,
        origins: List[Tuple[float, float]],
        destination_lat: float,
        destination_lon: float,
        mode: str = "car",
    ) -> List[Dict[str, Any]]:
        """Compute routes from multiple origins to one destination concurrently."""
        sem = asyncio.Semaphore(4)

        async def _fetch(
            origin: Tuple[float, float],
        ) -> Dict[str, Any]:
            async with sem:
                return await self.get_route(
                    origin[0], origin[1], destination_lat, destination_lon, mode
                )

        return list(await asyncio.gather(*[_fetch(o) for o in origins]))

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _haversine_estimate(
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        mode: str,
    ) -> Dict[str, Any]:
        """Fallback straight-line estimate using the Haversine formula."""
        import math

        R = 6371.0  # Earth radius in km
        lat1, lon1 = math.radians(origin_lat), math.radians(origin_lon)
        lat2, lon2 = math.radians(destination_lat), math.radians(destination_lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        distance_km = round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)

        # Apply a detour factor to make straight-line more realistic
        detour = 1.3 if mode in ("car", "driving") else 1.15
        distance_km = round(distance_km * detour, 2)

        speed_kmh: Dict[str, float] = {
            "car": 40.0,
            "driving": 40.0,
            "bike": 15.0,
            "bicycling": 15.0,
            "bicycle": 15.0,
            "foot": 5.0,
            "walking": 5.0,
        }
        speed = speed_kmh.get(mode, 30.0)
        duration_seconds = int((distance_km / speed) * 3600) if speed > 0 else 0

        return {
            "duration_seconds": duration_seconds,
            "distance_km": distance_km,
            "mode": mode,
            "geometry": None,
            "data_source": "haversine",
        }

    def _maybe_evict(self) -> None:
        """Evict expired entries; if still over limit drop oldest."""
        now = time.monotonic()
        # Drop expired
        self._cache = {k: v for k, v in self._cache.items() if v[0] > now}
        # If still over limit, drop oldest
        if len(self._cache) >= self.max_cache_size:
            sorted_keys = sorted(self._cache, key=lambda k: self._cache[k][0])
            for k in sorted_keys[: len(sorted_keys) // 4]:
                del self._cache[k]

    def clear_cache(self) -> None:
        """Clear the route cache."""
        self._cache.clear()


# Module-level singleton for reuse across requests
_client: Optional[OSRMCommuteClient] = None


def get_osrm_client() -> OSRMCommuteClient:
    """Return the module-level OSRM client (lazy singleton)."""
    global _client
    if _client is None:
        _client = OSRMCommuteClient()
    return _client


# ---------------------------------------------------------------------------
# LangChain tool input / output schemas
# ---------------------------------------------------------------------------


class CommuteAnalysisInput(BaseModel):
    """Input schema for the OSRM commute analysis tool."""

    origin_lat: float = Field(..., ge=-90, le=90, description="Origin latitude (property location)")
    origin_lon: float = Field(
        ..., ge=-180, le=180, description="Origin longitude (property location)"
    )
    destination_lat: float = Field(
        ..., ge=-90, le=90, description="Destination latitude (work / school)"
    )
    destination_lon: float = Field(
        ..., ge=-180, le=180, description="Destination longitude (work / school)"
    )
    mode: str = Field(
        default="car",
        description=(
            "Travel mode: 'car' (or 'driving'), 'bike' (or 'bicycling'), 'foot' (or 'walking')."
        ),
    )
    destination_name: Optional[str] = Field(
        default=None, description="Human-readable destination name"
    )


class MultiCommuteInput(BaseModel):
    """Input schema for multi-origin commute comparison."""

    origins: str = Field(
        description=(
            "Comma-separated list of 'lat,lon' pairs separated by '|'. "
            "Example: '52.22,21.01|52.23,21.02'"
        ),
        min_length=1,
    )
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lon: float = Field(..., ge=-180, le=180)
    mode: str = Field(default="car", description="Travel mode: car, bike, or foot")
    destination_name: Optional[str] = None


# ---------------------------------------------------------------------------
# LangChain tools
# ---------------------------------------------------------------------------


class CommuteTool(BaseTool):
    """
    Calculate commute time and distance between two points using OSRM.

    Uses the free public OSRM server (no API key required). Supports car,
    bike, and foot modes. Falls back to Haversine estimation when the OSRM
    service is unavailable or rate-limited.
    """

    name: str = "commute_analysis"
    description: str = (
        "Calculate commute time and distance between an origin and a destination. "
        "Supports car, bike, and foot travel modes. "
        "Input: origin and destination coordinates (lat, lon), travel mode. "
        "Returns: travel time in minutes, distance in km, and assessment."
    )
    args_schema: type[BaseModel] = CommuteAnalysisInput

    def _run(
        self,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        mode: str = "car",
        destination_name: Optional[str] = None,
    ) -> str:
        """Execute commute analysis (sync wrapper)."""
        client = get_osrm_client()
        result = asyncio.run(
            client.get_route(
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                destination_lat=destination_lat,
                destination_lon=destination_lon,
                mode=mode,
            )
        )
        return self._format_result(result, destination_name)

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        client = get_osrm_client()
        result = await client.get_route(
            origin_lat=kwargs["origin_lat"],
            origin_lon=kwargs["origin_lon"],
            destination_lat=kwargs["destination_lat"],
            destination_lon=kwargs["destination_lon"],
            mode=kwargs.get("mode", "car"),
        )
        return self._format_result(result, kwargs.get("destination_name"))

    @staticmethod
    def _format_result(result: Dict[str, Any], destination_name: Optional[str]) -> str:
        """Format OSRM result for agent consumption."""
        duration_min = result["duration_seconds"] // 60
        distance_km = result["distance_km"]
        mode = result["mode"]
        source = result.get("data_source", "osrm")

        dest_label = destination_name or "destination"

        # Assessment
        if duration_min < 15:
            assessment = "Excellent - very short commute"
        elif duration_min < 30:
            assessment = "Good - convenient commute"
        elif duration_min < 45:
            assessment = "Reasonable commute"
        elif duration_min < 60:
            assessment = "Long commute - consider carefully"
        else:
            assessment = "Very long commute - may impact quality of life"

        return (
            f"Commute to {dest_label}:\n"
            f"- Duration: {duration_min} minutes\n"
            f"- Distance: {distance_km} km\n"
            f"- Mode: {mode}\n"
            f"- Assessment: {assessment}\n"
            f"- Data source: {source}"
        )


class MultiOriginCommuteTool(BaseTool):
    """
    Compare commute times from multiple origins to a single destination.

    Useful for ranking properties by accessibility to a workplace or school.
    """

    name: str = "multi_origin_commute"
    description: str = (
        "Compare commute times from multiple locations to one destination. "
        "Input: origins as 'lat,lon' pairs separated by '|', destination coordinates, mode. "
        "Returns: ranked list of origins by travel time."
    )
    args_schema: type[BaseModel] = MultiCommuteInput

    def _run(
        self,
        origins: str,
        destination_lat: float,
        destination_lon: float,
        mode: str = "car",
        destination_name: Optional[str] = None,
    ) -> str:
        """Execute multi-origin commute comparison (sync wrapper)."""
        parsed = self._parse_origins(origins)
        client = get_osrm_client()
        results = asyncio.run(client.batch_routes(parsed, destination_lat, destination_lon, mode))
        return self._format_results(results, parsed, destination_name, mode)

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        parsed = self._parse_origins(kwargs["origins"])
        client = get_osrm_client()
        results = await client.batch_routes(
            parsed,
            kwargs["destination_lat"],
            kwargs["destination_lon"],
            kwargs.get("mode", "car"),
        )
        return self._format_results(
            results, parsed, kwargs.get("destination_name"), kwargs.get("mode", "car")
        )

    @staticmethod
    def _parse_origins(origins: str) -> List[Tuple[float, float]]:
        """Parse 'lat,lon|lat,lon' string into list of tuples."""
        result: List[Tuple[float, float]] = []
        for pair in origins.split("|"):
            parts = pair.strip().split(",")
            if len(parts) == 2:
                try:
                    result.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    continue
        return result

    @staticmethod
    def _format_results(
        results: List[Dict[str, Any]],
        origins: List[Tuple[float, float]],
        destination_name: Optional[str],
        mode: str,
    ) -> str:
        """Format batch results as ranked list."""
        dest_label = destination_name or "destination"

        # Pair origin coords with results and sort by duration
        paired = list(zip(origins, results, strict=True))
        paired.sort(key=lambda x: x[1]["duration_seconds"])

        lines = [
            f"Commute comparison to {dest_label} (mode: {mode}):",
            "",
            f"{'Rank':<5} {'Origin':<30} {'Duration':<12} {'Distance':<10}",
            f"{'-' * 5} {'-' * 30} {'-' * 12} {'-' * 10}",
        ]

        for rank, (origin, res) in enumerate(paired, 1):
            duration_min = res["duration_seconds"] // 60
            dur_text = f"{duration_min} min"
            dist_text = f"{res['distance_km']} km"
            origin_label = f"({origin[0]:.4f}, {origin[1]:.4f})"
            lines.append(f"{rank:<5} {origin_label:<30} {dur_text:<12} {dist_text:<10}")

        if paired:
            fastest = paired[0][1]["duration_seconds"] // 60
            slowest = paired[-1][1]["duration_seconds"] // 60
            lines.append("")
            lines.append(f"Fastest: {fastest} min | Slowest: {slowest} min")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Utility function for direct (non-tool) usage
# ---------------------------------------------------------------------------


async def calculate_commute(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
    mode: str = "car",
) -> Dict[str, Any]:
    """
    Calculate commute time between two points using OSRM.

    Convenience function for use outside the LangChain agent framework
    (e.g. from API endpoints).

    Returns dict with: duration_seconds, distance_km, mode, data_source.
    """
    client = get_osrm_client()
    return await client.get_route(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        destination_lat=destination_lat,
        destination_lon=destination_lon,
        mode=mode,
    )
