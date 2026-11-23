"""
Neighborhood quality index tools.

Provides neighborhood quality scoring based on safety, schools, amenities,
walkability, green space, air quality, noise level, and public transport.

Every score this tool returns is a measurement of named map features. A
factor that could not be measured - no coordinates and no place the map
can resolve, a provider that refused the query, a place that holds none
of the features asked for - comes back as no score, with the reason in the
details. A number with nothing behind it is worse than a hole: a hole says
the answer is missing, and a number says the answer is known.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)

# The radius each factor is measured in, when the place is a point.
SCHOOLS_RADIUS_M = 1000
AMENITIES_RADIUS_M = 500
WALKABILITY_RADIUS_M = 500
GREEN_SPACE_RADIUS_M = 1000
SAFETY_RADIUS_M = 1500

# How many of a feature per 10,000 residents make a place good to live
# in. A count on its own means nothing: the same number of schools is a
# different fact in a village and in a capital, so the counts measured
# inside a named place are scaled by the residents the boundary claims.
# The points are the tool's own scoring function; the counts they are
# read with are the measurement.
SCHOOLS_PER_10K: Tuple[Tuple[float, float], ...] = (
    (0.0, 20.0),
    (1.0, 40.0),
    (2.0, 55.0),
    (3.0, 70.0),
    (5.0, 85.0),
    (8.0, 95.0),
)
AMENITIES_PER_10K: Tuple[Tuple[float, float], ...] = (
    (0.0, 25.0),
    (2.0, 45.0),
    (5.0, 65.0),
    (10.0, 82.0),
    (20.0, 95.0),
)
GREEN_SPACES_PER_10K: Tuple[Tuple[float, float], ...] = (
    (0.0, 25.0),
    (0.2, 45.0),
    (0.5, 65.0),
    (1.0, 82.0),
    (2.0, 95.0),
)
STOPS_PER_10K: Tuple[Tuple[float, float], ...] = (
    (0.0, 25.0),
    (0.5, 45.0),
    (1.5, 65.0),
    (3.0, 82.0),
    (6.0, 95.0),
)
SAFETY_SERVICES_PER_10K: Tuple[Tuple[float, float], ...] = (
    (0.0, 40.0),
    (0.1, 55.0),
    (0.3, 70.0),
    (0.6, 85.0),
    (1.2, 95.0),
)
# The walkability of a named place is the same three parts as the
# walkability around a point: the variety of what is there, how much of
# it there is per resident, and whether the daily needs are covered.
POI_DENSITY_PER_10K: Tuple[Tuple[float, float], ...] = (
    (0.0, 0.0),
    (5.0, 40.0),
    (15.0, 70.0),
    (30.0, 90.0),
    (50.0, 100.0),
)
ESSENTIAL_PER_10K: Tuple[Tuple[float, float], ...] = (
    (0.0, 0.0),
    (0.2, 30.0),
    (0.5, 55.0),
    (1.0, 75.0),
    (2.0, 90.0),
)


class NeighborhoodQualityInput(BaseModel):
    """Input for neighborhood quality index calculation."""

    property_id: str = Field(description="Property ID to analyze", min_length=1)
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")
    city: Optional[str] = Field(None, description="City name for data enrichment")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")
    # New optional parameters (Task #40)
    custom_weights: Optional[Dict[str, float]] = Field(
        None, description="Custom weights for scoring factors (must sum to 1.0)"
    )
    compare_to_city_average: bool = Field(
        True, description="Include comparison to city average scores"
    )
    include_pois: bool = Field(True, description="Include nearby POIs for map visualization")


class NeighborhoodQualityResult(BaseModel):
    """
    Result from neighborhood quality index calculation.

    A factor that could not be measured carries no score. The reason it
    carries none is in `components_without_data`, and the components that
    were measured say in their own details which map features they came
    from.
    """

    property_id: str
    overall_score: Optional[float] = None
    # Core factors
    safety_score: Optional[float] = None
    schools_score: Optional[float] = None
    amenities_score: Optional[float] = None
    walkability_score: Optional[float] = None
    green_space_score: Optional[float] = None
    # New factors (Task #40)
    air_quality_score: Optional[float] = None
    noise_level_score: Optional[float] = None
    public_transport_score: Optional[float] = None
    # Detailed breakdown
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    factor_details: Optional[Dict[str, Any]] = None
    # The factors that could not be measured, and why
    components_without_data: Dict[str, str] = Field(default_factory=dict)
    # City comparison
    city_comparison: Optional[Dict[str, Any]] = None
    # POIs for map
    nearby_pois: Optional[Dict[str, List[Dict[str, Any]]]] = None
    # Metadata
    data_sources: List[str] = Field(default_factory=list)
    data_freshness: Optional[Dict[str, str]] = None
    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None


@dataclass
class Measurement:
    """One factor of the index: the score, and the map features behind it."""

    score: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _Place:
    """
    Where the measurement is taken: a point on the map, or a named place.

    The two are not interchangeable. Around a point the factors are
    measured in a radius; inside a named place they are measured within
    the boundary the name carries. Either way the answer says which.
    """

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    # The named place, resolved to a boundary the provider knows.
    place_name: Optional[str] = None
    population: Optional[int] = None
    center: Optional[Tuple[float, float]] = None
    pois: Optional[Any] = None
    reason: Optional[str] = None

    @property
    def is_point(self) -> bool:
        """Whether the place is a point the radius queries can use."""
        return self.latitude is not None and self.longitude is not None


def _point_coordinates(place: _Place) -> Tuple[float, float]:
    """
    The coordinates of a point place.

    The place knows whether it is a point, but a reader of the code does not:
    this is where the coordinates are read as the numbers they are.

    Args:
        place: The place the measurement is taken at.

    Returns:
        The latitude and the longitude.

    Raises:
        ValueError: When the place carries no coordinates. A caller that has
            already checked `is_point` never reaches it.
    """
    if place.latitude is None or place.longitude is None:
        raise ValueError("the place carries no coordinates")
    return place.latitude, place.longitude


def _measurement_point(place: _Place) -> Optional[Tuple[float, float]]:
    """
    The point a measurement is taken at.

    A point place is measured at its own coordinates; a named place is
    measured at the centre of its boundary, because the centre is a real
    point on the map.

    Args:
        place: The place the measurement is taken at.

    Returns:
        The latitude and the longitude, or None when the place carries
        neither its own coordinates nor a centre.
    """
    if place.latitude is not None and place.longitude is not None:
        return place.latitude, place.longitude
    return place.center


def _unavailable(reason: str, **extra: Any) -> Measurement:
    """No score, and the reason there is none."""
    details: Dict[str, Any] = {"data_source": "unavailable", "reason": reason}
    details.update(extra)
    return Measurement(score=None, details=details)


def _reason(value: Any, fallback: str) -> str:
    """A reason a reader can read, whatever the adapter answered with."""
    return value if isinstance(value, str) and value else fallback


def _score_from_points(value: float, points: Tuple[Tuple[float, float], ...]) -> float:
    """
    Read a score off a curve, interpolating between the points it names.

    The curve is the tool's own: it says how many of a feature per
    resident make a place good, and it is a scoring function, not a
    measurement. The measurement is the count the curve is read with.
    """
    if value <= points[0][0]:
        return points[0][1]
    for (low_value, low_score), (high_value, high_score) in zip(points, points[1:], strict=False):
        if value <= high_value:
            span = high_value - low_value
            if span <= 0:
                return high_score
            ratio = (value - low_value) / span
            return low_score + ratio * (high_score - low_score)
    return points[-1][1]


def _feature_names(
    pois: Optional[Dict[str, List[Dict[str, Any]]]],
    category: str,
    radius_m: int,
) -> List[str]:
    """The names of the features a count was taken from, so the count can be read back."""
    if not pois or not isinstance(pois, dict):
        return []
    names: List[str] = []
    for poi in pois.get(category) or []:
        if not isinstance(poi, dict):
            continue
        distance = poi.get("distance_m")
        if distance is not None and distance > radius_m:
            continue
        name = poi.get("name")
        if name:
            names.append(str(name))
    return names[:25]


class NeighborhoodQualityIndexTool(BaseTool):
    """
    Tool for calculating enhanced neighborhood quality index.

    Calculates comprehensive neighborhood quality score (0-100) based on 8 factors:
    - Safety (15%): Crime data, police stations, emergency services
    - Schools (15%): Nearby educational institutions
    - Amenities (15%): Shops, restaurants, services
    - Walkability (15%): POI density and diversity
    - Green Space (10%): Parks, forests, recreational areas
    - Air Quality (10%): AQI from WAQI/GIOS APIs
    - Noise Level (10%): Estimated from road/railway proximity
    - Public Transport (10%): Bus/tram/metro accessibility
    """

    name: str = "neighborhood_quality_index"
    description: str = (
        "Calculate a comprehensive neighborhood quality score (0-100) "
        "based on safety, schools, amenities, walkability, green space, "
        "air quality, noise level, and public transport. "
        "Input should include property_id and optionally latitude/longitude. "
        "Returns detailed score breakdown, city comparison, and nearby POIs."
    )
    args_schema: type[NeighborhoodQualityInput] = NeighborhoodQualityInput

    # Score weights (rebalanced for 8 factors - Task #40)
    WEIGHT_SAFETY: ClassVar[float] = 0.15
    WEIGHT_SCHOOLS: ClassVar[float] = 0.15
    WEIGHT_AMENITIES: ClassVar[float] = 0.15
    WEIGHT_WALKABILITY: ClassVar[float] = 0.15
    WEIGHT_GREEN_SPACE: ClassVar[float] = 0.10
    WEIGHT_AIR_QUALITY: ClassVar[float] = 0.10
    WEIGHT_NOISE_LEVEL: ClassVar[float] = 0.10
    WEIGHT_PUBLIC_TRANSPORT: ClassVar[float] = 0.10

    # Default weights for validation
    DEFAULT_WEIGHTS: ClassVar[Dict[str, float]] = {
        "safety": 0.15,
        "schools": 0.15,
        "amenities": 0.15,
        "walkability": 0.15,
        "green_space": 0.10,
        "air_quality": 0.10,
        "noise_level": 0.10,
        "public_transport": 0.10,
    }

    # ------------------------------------------------------------------
    # The factors, one by one. Each one answers the same two questions:
    # what was measured, and where does the measurement come from.
    # ------------------------------------------------------------------

    @staticmethod
    def _measure_schools(
        place: _Place,
        pois: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> Measurement:
        """The schools score: how many schools the map holds where the place is."""
        if place.is_point:
            count, error = NeighborhoodQualityIndexTool._count_at_point(
                place, "count_schools", SCHOOLS_RADIUS_M
            )
            if error is not None or count is None:
                return _unavailable(error or "the provider could not be asked for the count")
            return Measurement(
                score=NeighborhoodQualityIndexTool._schools_from_count(count),
                details={
                    "data_source": "osm_overpass_api",
                    "measured_at": "the point",
                    "radius_m": SCHOOLS_RADIUS_M,
                    "feature_count": count,
                    "unit": "schools",
                    "features": _feature_names(pois, "schools", SCHOOLS_RADIUS_M),
                },
            )

        area_pois = place.pois
        if area_pois is None:
            return _unavailable(place.reason or "the named place could not be resolved")
        count = len(area_pois.schools)
        if count == 0:
            return _unavailable(
                "the place holds no school",
                measured_at=place.place_name,
                unit="schools",
            )
        score, error = NeighborhoodQualityIndexTool._per_resident_score(
            count, place.population, SCHOOLS_PER_10K
        )
        if error is not None:
            return _unavailable(error, measured_at=place.place_name, feature_count=count)
        return Measurement(
            score=score,
            details={
                "data_source": "osm_overpass_area",
                "measured_at": place.place_name,
                "feature_count": count,
                "unit": "schools per 10,000 residents",
                "per_10k": round(count / (place.population or 1) * 10000, 2),
                "population": place.population,
                "features": [
                    str(poi.get("name")) for poi in area_pois.schools[:25] if poi.get("name")
                ],
            },
        )

    @staticmethod
    def _measure_amenities(
        place: _Place,
        pois: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> Measurement:
        """The amenities score: how many everyday places the map holds where the place is."""
        if place.is_point:
            count, error = NeighborhoodQualityIndexTool._count_at_point(
                place, "count_amenities", AMENITIES_RADIUS_M
            )
            if error is not None or count is None:
                return _unavailable(error or "the provider could not be asked for the count")
            return Measurement(
                score=NeighborhoodQualityIndexTool._amenities_from_count(count),
                details={
                    "data_source": "osm_overpass_api",
                    "measured_at": "the point",
                    "radius_m": AMENITIES_RADIUS_M,
                    "feature_count": count,
                    "unit": "amenities",
                    "features": _feature_names(pois, "amenities", AMENITIES_RADIUS_M),
                },
            )

        area_pois = place.pois
        if area_pois is None:
            return _unavailable(place.reason or "the named place could not be resolved")
        count = len(area_pois.amenities)
        if count == 0:
            return _unavailable(
                "the place holds no everyday amenity",
                measured_at=place.place_name,
                unit="amenities",
            )
        score, error = NeighborhoodQualityIndexTool._per_resident_score(
            count, place.population, AMENITIES_PER_10K
        )
        if error is not None:
            return _unavailable(error, measured_at=place.place_name, feature_count=count)
        return Measurement(
            score=score,
            details={
                "data_source": "osm_overpass_area",
                "measured_at": place.place_name,
                "feature_count": count,
                "unit": "amenities per 10,000 residents",
                "per_10k": round(count / (place.population or 1) * 10000, 2),
                "population": place.population,
                "features": [
                    str(poi.get("name")) for poi in area_pois.amenities[:25] if poi.get("name")
                ],
            },
        )

    @staticmethod
    def _measure_green_space(
        place: _Place,
        pois: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> Measurement:
        """The green space score: how much green the map holds where the place is."""
        if place.is_point:
            count, error = NeighborhoodQualityIndexTool._count_at_point(
                place, "count_green_spaces", GREEN_SPACE_RADIUS_M
            )
            if error is not None or count is None:
                return _unavailable(error or "the provider could not be asked for the count")
            return Measurement(
                score=NeighborhoodQualityIndexTool._green_space_from_count(count),
                details={
                    "data_source": "osm_overpass_api",
                    "measured_at": "the point",
                    "radius_m": GREEN_SPACE_RADIUS_M,
                    "feature_count": count,
                    "unit": "green_spaces",
                    "features": _feature_names(pois, "green_spaces", GREEN_SPACE_RADIUS_M),
                },
            )

        area_pois = place.pois
        if area_pois is None:
            return _unavailable(place.reason or "the named place could not be resolved")
        count = len(area_pois.green_spaces)
        if count == 0:
            return _unavailable(
                "the place holds no green space",
                measured_at=place.place_name,
                unit="green_spaces",
            )
        score, error = NeighborhoodQualityIndexTool._per_resident_score(
            count, place.population, GREEN_SPACES_PER_10K
        )
        if error is not None:
            return _unavailable(error, measured_at=place.place_name, feature_count=count)
        return Measurement(
            score=score,
            details={
                "data_source": "osm_overpass_area",
                "measured_at": place.place_name,
                "feature_count": count,
                "unit": "green spaces per 10,000 residents",
                "per_10k": round(count / (place.population or 1) * 10000, 2),
                "population": place.population,
                "features": [
                    str(poi.get("name")) for poi in area_pois.green_spaces[:25] if poi.get("name")
                ],
            },
        )

    @staticmethod
    def _measure_walkability(
        place: _Place,
        pois: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> Measurement:
        """The walkability score: what is within reach, and how varied it is."""
        if place.is_point:
            latitude, longitude = _point_coordinates(place)
            try:
                from data.adapters.neighborhood_adapter import get_neighborhood_adapter

                adapter = get_neighborhood_adapter()
                score = round(
                    float(
                        adapter.calculate_walkability(
                            latitude, longitude, radius_m=WALKABILITY_RADIUS_M
                        )
                    ),
                    1,
                )
            except Exception as e:
                logger.warning("Walkability score calculation failed: %s", sanitize_for_log(e))
                return _unavailable(
                    "the provider could not be asked what is within reach: {0}".format(
                        sanitize_for_log(e)
                    )
                )
            features = _feature_names(pois, "all", WALKABILITY_RADIUS_M)
            return Measurement(
                score=score,
                details={
                    "data_source": "osm_overpass_api",
                    "measured_at": "the point",
                    "radius_m": WALKABILITY_RADIUS_M,
                    "feature_count": len(features),
                    "unit": "POIs of every kind",
                    "features": features,
                },
            )

        area_pois = place.pois
        if area_pois is None:
            return _unavailable(place.reason or "the named place could not be resolved")
        total = len(area_pois.all)
        if total == 0:
            return _unavailable(
                "the place holds nothing at all",
                measured_at=place.place_name,
                unit="POIs of every kind",
            )

        amenity_types = {
            poi.get("amenity") or poi.get("shop")
            for poi in area_pois.amenities
            if poi.get("amenity") or poi.get("shop")
        }
        diversity_score = min(100.0, len(amenity_types) * 10.0)

        essential_tags = {"supermarket", "pharmacy", "hospital", "clinic", "bank"}
        essential_count = sum(
            1 for poi in area_pois.amenities if poi.get("amenity") in essential_tags
        )

        if not place.population:
            return _unavailable(
                "the boundary carries no population, so the counts cannot be scaled",
                measured_at=place.place_name,
                feature_count=total,
            )
        per_10k = total / place.population * 10000
        essential_per_10k = essential_count / place.population * 10000
        density_score = _score_from_points(per_10k, POI_DENSITY_PER_10K)
        essential_score = _score_from_points(essential_per_10k, ESSENTIAL_PER_10K)
        score = diversity_score * 0.3 + density_score * 0.4 + essential_score * 0.3

        return Measurement(
            score=round(score, 1),
            details={
                "data_source": "osm_overpass_area",
                "measured_at": place.place_name,
                "feature_count": total,
                "unit": "POIs of every kind, per 10,000 residents",
                "per_10k": round(per_10k, 2),
                "population": place.population,
                "distinct_amenity_types": len(amenity_types),
                "essential_amenities": essential_count,
                "features": [str(poi.get("name")) for poi in area_pois.all[:25] if poi.get("name")],
            },
        )

    @staticmethod
    def _measure_safety(place: _Place) -> Measurement:
        """The safety score: the police and emergency services the map holds."""
        if place.is_point:
            try:
                from data.adapters.safety_adapter import get_safety_adapter

                adapter = get_safety_adapter()
                result = adapter.get_safety_score(
                    place.latitude,
                    place.longitude,
                    place.city,
                    place.neighborhood,
                    radius_m=SAFETY_RADIUS_M,
                )
                score = round(result.score, 1)
                details = {
                    "raw_value": result.police_stations_nearby + result.emergency_services_nearby,
                    "unit": "safety services",
                    "normalized_score": score,
                    "data_source": result.data_source,
                    "confidence": result.confidence,
                    "measured_at": "the point",
                    "radius_m": SAFETY_RADIUS_M,
                    "police_stations_nearby": result.police_stations_nearby,
                    "emergency_services_nearby": result.emergency_services_nearby,
                    "features": [poi.name for poi in result.pois if poi.name][:25],
                }
            except Exception as e:
                logger.warning("Safety score calculation failed: %s", sanitize_for_log(e))
                return _unavailable(
                    "the provider could not be asked for the safety services: {0}".format(
                        sanitize_for_log(e)
                    )
                )

            return Measurement(score=score, details=details)

        try:
            from data.adapters.safety_adapter import get_safety_adapter

            if not place.place_name:
                return _unavailable(place.reason or "no place was named")

            adapter = get_safety_adapter()
            area_safety = adapter.fetch_safety_pois_in_area(place.place_name)
        except Exception as e:
            logger.warning("Safety services could not be counted: %s", sanitize_for_log(e))
            return _unavailable(
                "the safety services of the place could not be counted: {0}".format(
                    sanitize_for_log(e)
                )
            )

        if area_safety.error:
            return _unavailable(
                "the safety services of the place could not be counted: {0}".format(
                    _reason(area_safety.error, "the place could not be resolved")
                ),
                measured_at=place.place_name,
            )

        police = sum(1 for poi in area_safety.pois if poi.type == "police")
        emergency = len(area_safety.pois) - police
        if not area_safety.pois:
            return _unavailable(
                "the place holds no police station and no emergency service",
                measured_at=place.place_name,
                police_stations_nearby=0,
                emergency_services_nearby=0,
            )
        if not place.population:
            return _unavailable(
                "the boundary carries no population, so the counts cannot be scaled",
                measured_at=place.place_name,
                police_stations_nearby=police,
                emergency_services_nearby=emergency,
            )

        per_10k = (police + emergency) / place.population * 10000
        score = _score_from_points(per_10k, SAFETY_SERVICES_PER_10K)
        return Measurement(
            score=round(score, 1),
            details={
                "data_source": "osm_overpass_area",
                "measured_at": place.place_name,
                "feature_count": len(area_safety.pois),
                "unit": "safety services per 10,000 residents",
                "per_10k": round(per_10k, 2),
                "population": place.population,
                "police_stations_nearby": police,
                "emergency_services_nearby": emergency,
                "features": [poi.name for poi in area_safety.pois if poi.name][:25],
            },
        )

    @staticmethod
    def _measure_air_quality(place: _Place) -> Measurement:
        """The air quality score: the station the provider reads for the place."""
        # A named place is measured at the centre of its boundary: the
        # centre is a real point on the map, and the answer says so.
        measurement_point = _measurement_point(place)
        if measurement_point is None:
            return _unavailable(
                "the boundary carries no centre, so no air quality station can be read",
                measured_at=place.place_name,
            )
        latitude, longitude = measurement_point

        try:
            from data.adapters.air_quality_adapter import get_air_quality_adapter

            adapter = get_air_quality_adapter()
            result = adapter.get_aqi_score(latitude, longitude, place.city)
            score = round(result.score, 1)
            details = {
                "raw_value": result.aqi_value,
                "unit": "AQI",
                "normalized_score": score,
                "data_source": result.data_source,
                "confidence": result.confidence,
                "pm25": result.pm25,
                "pm10": result.pm10,
                "station_name": result.station_name,
                # The register's terms ask for the source to be named, so the
                # attribution travels with the measurement.
                "attribution": result.attribution,
                "official_index": result.official_index,
                "official_category": result.official_category,
            }
        except Exception as e:
            logger.warning("Air quality calculation failed: %s", sanitize_for_log(e))
            return _unavailable(
                "the air quality provider could not be read: {0}".format(sanitize_for_log(e))
            )

        if not place.is_point:
            details["measured_at"] = "the centre of {0}".format(place.place_name)
        return Measurement(score=score, details=details)

    @staticmethod
    def _measure_noise(place: _Place) -> Measurement:
        """The noise score: what is loud around the place."""
        measurement_point = _measurement_point(place)
        if measurement_point is None:
            return _unavailable(
                "noise is measured around a point, and the boundary carries no centre",
                measured_at=place.place_name,
            )
        latitude, longitude = measurement_point

        try:
            from data.adapters.noise_adapter import get_noise_adapter

            adapter = get_noise_adapter()
            result = adapter.estimate_noise_level(latitude, longitude)
            score = round(result.score, 1)
            measured = result.data_source == adapter.GIOS_DATA_SOURCE
            details: Dict[str, Any] = {
                "raw_value": result.estimated_db,
                "unit": "dB (measured)" if measured else "dB (estimated)",
                "normalized_score": score,
                "data_source": result.data_source,
                "confidence": result.confidence,
                "noise_sources_count": len(result.noise_sources),
                "features": [
                    getattr(source, "name", None)
                    for source in result.noise_sources
                    if getattr(source, "name", None)
                ][:25],
            }
            if getattr(result, "attribution", None):
                details["attribution"] = result.attribution
            if getattr(result, "measured_at", None):
                details["measured_at"] = result.measured_at
            if getattr(result, "measured_place", None):
                details["measured_place"] = result.measured_place
            measurement_distance = getattr(result, "measurement_distance_km", None)
            if measurement_distance is not None:
                details["measurement_distance_km"] = round(measurement_distance, 2)
        except Exception as e:
            logger.warning("Noise level calculation failed: %s", sanitize_for_log(e))
            return _unavailable(
                "the noise sources could not be read: {0}".format(sanitize_for_log(e))
            )

        if not place.is_point:
            details["measured_at"] = "the centre of {0}".format(place.place_name)
        return Measurement(score=score, details=details)

    @staticmethod
    def _measure_transport(place: _Place) -> Measurement:
        """The public transport score: the stops the map holds where the place is."""
        if place.is_point:
            latitude, longitude = _point_coordinates(place)
            try:
                from data.adapters.transport_adapter import get_transport_adapter

                adapter = get_transport_adapter()
                result = adapter.get_full_result(latitude, longitude)
                score = round(float(result.score), 1)
                details = {
                    "raw_value": result.total_stops,
                    "unit": "stops",
                    "normalized_score": score,
                    "data_source": result.data_source,
                    "confidence": result.confidence,
                    "measured_at": "the point",
                    "stops_by_type": result.stops_by_type,
                    "features": [stop.name for stop in result.stops if stop.name][:25],
                }
            except Exception as e:
                logger.warning("Transport calculation failed: %s", sanitize_for_log(e))
            else:
                return Measurement(score=score, details=details)

            # The richer answer could not be read. The adapter still has
            # its own score, which it computes from the same stops, so
            # the factor is still a measurement - it just cannot name
            # the stops it was taken from. The count is asked for on its
            # own, so the reader still knows how many stops the score
            # was taken from.
            try:
                from data.adapters.transport_adapter import get_transport_adapter

                adapter = get_transport_adapter()
                score = round(
                    float(adapter.calculate_accessibility_score(latitude, longitude)),
                    1,
                )
            except Exception as e:
                logger.warning("Transport calculation failed: %s", sanitize_for_log(e))
                return _unavailable(
                    "the transport stops could not be counted: {0}".format(sanitize_for_log(e))
                )

            count: Optional[int] = None
            try:
                counted = adapter.count_stops(latitude, longitude)
                if isinstance(counted, int) and not isinstance(counted, bool):
                    count = counted
            except Exception as e:
                logger.warning("The transport stops could not be counted: %s", sanitize_for_log(e))

            return Measurement(
                score=score,
                details={
                    "data_source": "osm_overpass_api",
                    "measured_at": "the point",
                    "unit": "stops",
                    "feature_count": count,
                    "features": [],
                    "stops_listed": False,
                    "note": "the adapter's own accessibility score; the stops could not be listed",
                },
            )

        try:
            from data.adapters.transport_adapter import get_transport_adapter

            if not place.place_name:
                return _unavailable(place.reason or "no place was named")

            adapter = get_transport_adapter()
            stops, error = adapter.fetch_transport_pois_in_area(place.place_name)
        except Exception as e:
            logger.warning("Transport stops could not be counted: %s", sanitize_for_log(e))
            return _unavailable(
                "the transport stops of the place could not be counted: {0}".format(
                    sanitize_for_log(e)
                )
            )

        if error:
            return _unavailable(
                "the transport stops of the place could not be counted: {0}".format(
                    _reason(error, "the place could not be resolved")
                ),
                measured_at=place.place_name,
            )
        if not stops:
            return _unavailable(
                "the place holds no transport stop",
                measured_at=place.place_name,
                unit="stops",
            )
        if not place.population:
            return _unavailable(
                "the boundary carries no population, so the counts cannot be scaled",
                measured_at=place.place_name,
                feature_count=len(stops),
            )

        per_10k = len(stops) / place.population * 10000
        score = _score_from_points(per_10k, STOPS_PER_10K)
        return Measurement(
            score=round(score, 1),
            details={
                "data_source": "osm_overpass_area",
                "measured_at": place.place_name,
                "feature_count": len(stops),
                "unit": "stops per 10,000 residents",
                "per_10k": round(per_10k, 2),
                "population": place.population,
                "stops_by_type": NeighborhoodQualityIndexTool._stops_by_type(stops),
                "features": [stop.name for stop in stops if stop.name][:25],
            },
        )

    # ------------------------------------------------------------------
    # The helpers the factors share
    # ------------------------------------------------------------------

    @staticmethod
    def _count_at_point(
        place: _Place,
        method_name: str,
        radius_m: int,
    ) -> Tuple[Optional[int], Optional[str]]:
        """Ask the adapter how many features of a kind lie around the point."""
        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            count = getattr(adapter, method_name)(
                place.latitude, place.longitude, radius_m=radius_m
            )
            return int(count), None
        except Exception as e:
            logger.warning("%s failed: %s", method_name, sanitize_for_log(e))
            return None, "the provider could not be asked for the {0} nearby: {1}".format(
                method_name.replace("count_", "").replace("_", " "),
                sanitize_for_log(e),
            )

    @staticmethod
    def _per_resident_score(
        count: int,
        population: Optional[int],
        curve: Tuple[Tuple[float, float], ...],
    ) -> Tuple[Optional[float], Optional[str]]:
        """Read a count of features per resident off a curve."""
        if not population:
            return None, (
                "the boundary carries no population, so the count of {0} cannot be scaled".format(
                    count
                )
            )
        per_10k = count / population * 10000
        return round(_score_from_points(per_10k, curve), 1), None

    @staticmethod
    def _schools_from_count(count: int) -> float:
        """The schools score of a neighbourhood: how many schools are within a kilometre."""
        if count == 0:
            return 30.0
        if count <= 2:
            return 30.0 + (count * 10)
        if count <= 5:
            return 50.0 + ((count - 2) * 10)
        return min(95.0, 70.0 + ((count - 5) * 5))

    @staticmethod
    def _amenities_from_count(count: int) -> float:
        """The amenities score of a neighbourhood: how many everyday places are within 500 m."""
        if count == 0:
            return 40.0
        if count <= 5:
            return 40.0 + (count * 4)
        if count <= 15:
            return 60.0 + ((count - 5) * 2)
        if count <= 30:
            return 80.0 + ((count - 15) * 1)
        return min(98.0, 85.0 + ((count - 30) * 0.5))

    @staticmethod
    def _green_space_from_count(count: int) -> float:
        """The green space score of a neighbourhood: how much green is within a kilometre."""
        if count == 0:
            return 30.0
        if count == 1:
            return 50.0
        if count <= 3:
            return 65.0 + (count - 2) * 7.5
        if count <= 5:
            return 80.0 + (count - 4) * 5
        return min(98.0, 85.0 + (count - 6) * 2)

    @staticmethod
    def _stops_by_type(stops: List[Any]) -> Dict[str, int]:
        """How many stops of every kind the place holds."""
        counts: Dict[str, int] = {}
        for stop in stops:
            kind = getattr(stop, "type", "unknown")
            counts[kind] = counts.get(kind, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # The named place: resolved to a boundary the provider knows
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_named_place(city: Optional[str], neighborhood: Optional[str]) -> _Place:
        """
        Resolve the place the caller named to a boundary the provider knows.

        The most specific name is tried first: a district is a smaller
        answer than the city it belongs to, and a smaller answer is the
        one the caller asked for. When the most specific name cannot be
        resolved the next one is tried, and the answer says which place
        was measured - a measurement of the city is not a measurement of
        the district, and the reader has to be able to tell.
        """
        place = _Place(city=city, neighborhood=neighborhood)

        names = [name for name in (neighborhood, city) if name]
        if not names:
            place.reason = "no place was named and no coordinates were given"
            return place

        last_reason = "the named place could not be resolved to a boundary"
        for name in names:
            try:
                from data.adapters.neighborhood_adapter import get_neighborhood_adapter

                adapter = get_neighborhood_adapter()
                area_pois = adapter.fetch_pois_in_area(name)
            except Exception as e:
                logger.warning(
                    "The place %s could not be measured: %s",
                    sanitize_for_log(name),
                    sanitize_for_log(e),
                )
                last_reason = "the place could not be measured: {0}".format(sanitize_for_log(e))
                continue

            if area_pois.error:
                last_reason = _reason(area_pois.error, "the place could not be resolved")
                continue

            if not isinstance(getattr(area_pois, "schools", None), list):
                last_reason = "the place could not be measured"
                continue

            place.place_name = name
            place.pois = area_pois
            place.reason = None
            if area_pois.area is not None:
                place.population = area_pois.area.population
                place.center = area_pois.area.center
            if not place.population:
                place.population = NeighborhoodQualityIndexTool._population_of_city(city)
            return place

        place.reason = last_reason
        return place

    @staticmethod
    def _population_of_city(city: Optional[str]) -> Optional[int]:
        """
        The residents of a city, from the averages the repository already keeps.

        A boundary that carries no population tag can still be scaled when
        the city it belongs to is one this project knows. The number comes
        from the project's own city table, and the answer says which scale
        was used.
        """
        if not city:
            return None
        try:
            from data.city_averages import get_city_average

            data = get_city_average(city)
            population = data.get("population")
            if isinstance(population, int):
                return population
        except Exception as e:
            logger.warning(
                "The population of %s is unknown: %s", sanitize_for_log(city), sanitize_for_log(e)
            )
        return None

    # ------------------------------------------------------------------
    # The index as a whole
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_weights(custom_weights: Optional[Dict[str, float]]) -> Dict[str, float]:
        """
        Validate and return weights dictionary.

        Ensures weights sum to 1.0 and contain valid keys.
        """
        if custom_weights is None:
            return NeighborhoodQualityIndexTool.DEFAULT_WEIGHTS.copy()

        # Validate keys
        valid_keys = set(NeighborhoodQualityIndexTool.DEFAULT_WEIGHTS.keys())
        provided_keys = set(custom_weights.keys())

        if not provided_keys.issubset(valid_keys):
            invalid = provided_keys - valid_keys
            logger.warning("Invalid weight keys: %s", sanitize_for_log(invalid))

        # Validate sum
        total = sum(custom_weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning("Weights sum to %s, normalizing to 1.0", sanitize_for_log(total))
            if total > 0:
                custom_weights = {k: v / total for k, v in custom_weights.items()}
            else:
                return NeighborhoodQualityIndexTool.DEFAULT_WEIGHTS.copy()

        # Merge with defaults for any missing keys
        weights = NeighborhoodQualityIndexTool.DEFAULT_WEIGHTS.copy()
        weights.update(custom_weights)

        return weights

    @staticmethod
    def calculate(
        property_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        custom_weights: Optional[Dict[str, float]] = None,
        compare_to_city_average: bool = True,
        include_pois: bool = True,
    ) -> NeighborhoodQualityResult:
        """
        Calculate enhanced neighborhood quality index.

        Calculates 8 factor scores with configurable weights:
        - Safety (15%): Enhanced with real data
        - Schools (15%): OSM school count
        - Amenities (15%): OSM POI count
        - Walkability (15%): POI density/diversity
        - Green Space (10%): OSM parks count
        - Air Quality (10%): WAQI API data
        - Noise Level (10%): OSM road/railway proximity
        - Public Transport (10%): OSM stop count

        A place given by coordinates is measured around that point; a
        place given by name is measured inside the boundary the name
        carries. A factor that cannot be measured is left without a
        score, and the overall score is the weighted average of the
        factors that were measured - never the weight of a missing
        factor spent on a number nobody measured.

        Returns NeighborhoodQualityResult with all scores, city comparison, and POIs.
        """

        # Validate and get weights
        weights = NeighborhoodQualityIndexTool._validate_weights(custom_weights)

        if latitude is not None and longitude is not None:
            place = _Place(
                latitude=latitude,
                longitude=longitude,
                city=city,
                neighborhood=neighborhood,
            )
        else:
            place = NeighborhoodQualityIndexTool._resolve_named_place(city, neighborhood)

        # The POIs the counts are read from, so that every score can be
        # traced back to the features behind it.
        pois = NeighborhoodQualityIndexTool._fetch_traceable_pois(place)

        measurements: Dict[str, Measurement] = {
            "safety": NeighborhoodQualityIndexTool._measure_safety(place),
            "schools": NeighborhoodQualityIndexTool._measure_schools(place, pois),
            "amenities": NeighborhoodQualityIndexTool._measure_amenities(place, pois),
            "walkability": NeighborhoodQualityIndexTool._measure_walkability(place, pois),
            "green_space": NeighborhoodQualityIndexTool._measure_green_space(place, pois),
            "air_quality": NeighborhoodQualityIndexTool._measure_air_quality(place),
            "noise_level": NeighborhoodQualityIndexTool._measure_noise(place),
            "public_transport": NeighborhoodQualityIndexTool._measure_transport(place),
        }

        # The factors that were measured, and the ones that were not.
        all_scores = {
            name: measurement.score
            for name, measurement in measurements.items()
            if measurement.score is not None
        }
        components_without_data = {
            name: measurement.details.get("reason", "not measured")
            for name, measurement in measurements.items()
            if measurement.score is None
        }

        # The weighted average of what was measured. The weights of the
        # factors that were not measured are left unspent.
        measured_weight = sum(weights.get(name, 0.0) for name in all_scores)
        overall_score: Optional[float] = None
        if all_scores and measured_weight > 0:
            overall_score = (
                sum(score * weights.get(name, 0.0) for name, score in all_scores.items())
                / measured_weight
            )

        # Build score breakdown with weights
        score_breakdown = {
            "{0}_weighted".format(name): round(score * weights.get(name, 0.0) / measured_weight, 2)
            for name, score in all_scores.items()
        }

        # Build factor details
        factor_details: Dict[str, Any] = {}
        for name, measurement in measurements.items():
            details: Dict[str, Any] = {
                "normalized_score": measurement.score,
                "weight": weights.get(name, 0.0),
                "weighted_score": score_breakdown.get("{0}_weighted".format(name)),
                "measured": measurement.score is not None,
            }
            details.update(measurement.details)
            if measurement.score is None:
                details["data_source"] = measurement.details.get("data_source", "unavailable")
                details["confidence"] = 0.0
            factor_details[name] = details

        # City comparison
        city_comparison = None
        if compare_to_city_average:
            city_comparison = NeighborhoodQualityIndexTool._get_city_comparison(city, all_scores)

        # Nearby POIs
        nearby_pois = None
        if include_pois:
            nearby_pois = NeighborhoodQualityIndexTool._fetch_nearby_pois(place, pois)

        # Data sources
        data_sources = ["osm_overpass_api"]
        if place.is_point:
            data_sources.append("geographic_coordinates")
        else:
            data_sources.append("osm_overpass_area")
        air_quality_source = measurements["air_quality"].details.get("data_source")
        if air_quality_source == "gios":
            data_sources.append("gios_air_quality_api")
        elif air_quality_source == "waqi":
            data_sources.append("waqi_air_quality_api")
        noise_source = measurements["noise_level"].details.get("data_source")
        if noise_source == "gios_noise_register":
            data_sources.append("gios_noise_register_api")

        # Data freshness
        now = datetime.utcnow().isoformat()
        data_freshness = {
            "neighborhood_data": now,
            "air_quality": now,
        }

        return NeighborhoodQualityResult(
            property_id=property_id,
            overall_score=round(overall_score, 1) if overall_score is not None else None,
            safety_score=measurements["safety"].score,
            schools_score=measurements["schools"].score,
            amenities_score=measurements["amenities"].score,
            walkability_score=measurements["walkability"].score,
            green_space_score=measurements["green_space"].score,
            air_quality_score=measurements["air_quality"].score,
            noise_level_score=measurements["noise_level"].score,
            public_transport_score=measurements["public_transport"].score,
            score_breakdown=score_breakdown,
            factor_details=factor_details,
            components_without_data=components_without_data,
            city_comparison=city_comparison,
            nearby_pois=nearby_pois,
            data_sources=data_sources,
            data_freshness=data_freshness,
            latitude=latitude,
            longitude=longitude,
            city=city,
            neighborhood=neighborhood,
        )

    @staticmethod
    def _fetch_traceable_pois(
        place: _Place,
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        The POIs around the point, so that every count can be read back.

        The counts come from the adapter, which asks the provider one
        question per factor. This is the one question that brings the
        features themselves, and it is what lets a score name the places
        it was taken from.
        """
        if not place.is_point:
            return None
        latitude, longitude = _point_coordinates(place)
        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            pois = adapter.fetch_pois_within_radius(
                latitude, longitude, radius_m=GREEN_SPACE_RADIUS_M
            )
            if not isinstance(pois, dict):
                return None
            return pois
        except Exception as e:
            logger.warning("The traceable POIs could not be read: %s", sanitize_for_log(e))
            return None

    @staticmethod
    def _get_city_comparison(
        city: Optional[str],
        scores: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        """
        Get comparison to city average scores.

        Returns city comparison data or None if city not found.
        """
        if not city or not scores:
            return None

        try:
            from data.city_averages import compare_to_city

            comparison = compare_to_city(city, scores)
            if not comparison:
                return None

            # Calculate overall percentile
            overall_percentile = int(
                sum(c["percentile"] for c in comparison.values()) / len(comparison)
            )

            # Identify better/worse factors
            better_than = [f for f, c in comparison.items() if c["better_than_average"]]
            worse_than = [f for f, c in comparison.items() if not c["better_than_average"]]

            return {
                "city_name": city.title(),
                "city_average_score": sum(c["city_average"] for c in comparison.values())
                / len(comparison),
                "percentile": overall_percentile,
                "better_than": better_than,
                "worse_than": worse_than,
                "factor_comparison": comparison,
            }

        except Exception as e:
            logger.warning("City comparison failed: %s", sanitize_for_log(e))
            return None

    @staticmethod
    def _fetch_nearby_pois(
        place: _Place,
        pois: Optional[Dict[str, List[Dict[str, Any]]]],
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        Fetch nearby POIs for map visualization.

        Returns categorized POIs or None if coordinates missing.
        """
        if not place.is_point:
            return None

        latitude, longitude = _point_coordinates(place)

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter
            from data.adapters.safety_adapter import get_safety_adapter
            from data.adapters.transport_adapter import get_transport_adapter

            # Fetch POIs from multiple adapters
            neighborhood_adapter = get_neighborhood_adapter()
            transport_adapter = get_transport_adapter()
            safety_adapter = get_safety_adapter()

            # The POIs the counts were read from, when they could be read.
            if pois is None:
                pois = neighborhood_adapter.fetch_pois_within_radius(
                    latitude, longitude, radius_m=GREEN_SPACE_RADIUS_M
                )

            # Get transport stops
            transport_result = transport_adapter.calculate_accessibility_score(latitude, longitude)  # type: ignore[attr-defined]

            # Get safety POIs
            safety_pois = safety_adapter.get_police_stations(
                latitude, longitude, radius_m=SAFETY_RADIUS_M
            )

            # Format for response
            def format_poi(poi: Dict[str, Any], category: str) -> Dict[str, Any]:
                return {
                    "id": str(poi.get("id", "")),
                    "name": poi.get("name"),
                    "type": poi.get("amenity") or poi.get("type") or "unknown",
                    "category": category,
                    "latitude": poi.get("latitude"),
                    "longitude": poi.get("longitude"),
                    "distance_m": poi.get("distance_m"),
                }

            nearby_pois = {
                "schools": [format_poi(p, "school") for p in pois.get("schools", [])],
                "amenities": [format_poi(p, "amenity") for p in pois.get("amenities", [])],
                "green_spaces": [
                    format_poi(p, "green_space") for p in pois.get("green_spaces", [])
                ],
                "transport_stops": [
                    {
                        "id": str(s.id),
                        "name": s.name,
                        "type": s.type,
                        "category": "transport",
                        "latitude": s.latitude,
                        "longitude": s.longitude,
                        "distance_m": s.distance_m,
                    }
                    for s in transport_result.stops[:20]  # type: ignore[attr-defined]  # Limit to 20
                ],
                "police_stations": [
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "type": p.type,
                        "category": "safety",
                        "latitude": p.latitude,
                        "longitude": p.longitude,
                        "distance_m": p.distance_m,
                    }
                    for p in safety_pois
                ],
            }

            return nearby_pois

        except Exception as e:
            logger.warning("Failed to fetch nearby POIs: %s", sanitize_for_log(e))
            return None

    def _run(
        self,
        property_id: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
        custom_weights: Optional[Dict[str, float]] = None,
        compare_to_city_average: bool = True,
        include_pois: bool = True,
    ) -> str:
        """Execute neighborhood quality calculation."""
        try:
            result = self.calculate(
                property_id=property_id,
                latitude=latitude,
                longitude=longitude,
                city=city,
                neighborhood=neighborhood,
                custom_weights=custom_weights,
                compare_to_city_average=compare_to_city_average,
                include_pois=include_pois,
            )

            def line(key: str, label: str, score: Optional[float], weight: str) -> str:
                if score is None:
                    return "- {0:<17} no score - {1}".format(
                        label,
                        result.components_without_data.get(key, "not measured"),
                    )
                return "- {0:<17} {1:.1f}/100 (Weight: {2})".format(label, score, weight)

            # Format result for display
            formatted = """
Neighborhood Quality Index for Property {result.property_id}:

=== OVERALL SCORE: {overall} ===

Core Factor Scores:
{core}

Environmental & Transport Scores:
{environment}

Score Breakdown (Weighted):
""".format(
                result=result,
                overall=(
                    "{0:.1f}/100".format(result.overall_score)
                    if result.overall_score is not None
                    else "not measured"
                ),
                core="\n".join(
                    [
                        line("safety", "Safety:", result.safety_score, "15%"),
                        line("schools", "Schools:", result.schools_score, "15%"),
                        line("amenities", "Amenities:", result.amenities_score, "15%"),
                        line("walkability", "Walkability:", result.walkability_score, "15%"),
                        line("green_space", "Green Space:", result.green_space_score, "10%"),
                    ]
                ),
                environment="\n".join(
                    [
                        line("air_quality", "Air Quality:", result.air_quality_score, "10%"),
                        line("noise_level", "Noise Level:", result.noise_level_score, "10%"),
                        line(
                            "public_transport",
                            "Public Transport:",
                            result.public_transport_score,
                            "10%",
                        ),
                    ]
                ),
            )

            for key, value in result.score_breakdown.items():
                formatted += "- {0}: {1:.2f}\n".format(key.replace("_", " ").title(), value)

            # City comparison
            if result.city_comparison:
                formatted += """
City Comparison (vs {city}):
- Percentile: {percentile}th
- Better than average: {better}
- Below average: {worse}
""".format(
                    city=result.city_comparison.get("city_name", "City"),
                    percentile=result.city_comparison.get("percentile", "N/A"),
                    better=", ".join(result.city_comparison.get("better_than", [])) or "None",
                    worse=", ".join(result.city_comparison.get("worse_than", [])) or "None",
                )

            formatted += """
Data Sources: {sources}
Location: {city}, {neighborhood}
Coordinates: {latitude}, {longitude}

Rating: {rating}
""".format(
                sources=", ".join(result.data_sources),
                city=result.city or "Unknown",
                neighborhood=result.neighborhood or "Unknown",
                latitude=result.latitude if result.latitude is not None else "N/A",
                longitude=result.longitude if result.longitude is not None else "N/A",
                rating=(
                    NeighborhoodQualityIndexTool._get_rating_label(result.overall_score)
                    if result.overall_score is not None
                    else "not measured"
                ),
            )
            return formatted.strip()

        except Exception as e:
            return "Error calculating neighborhood quality: {0}".format(str(e))

    @staticmethod
    def _get_rating_label(score: float) -> str:
        """Get human-readable rating label."""
        if score >= 85:
            return "Excellent - Highly desirable neighborhood"
        elif score >= 70:
            return "Good - Above average quality"
        elif score >= 55:
            return "Fair - Average neighborhood"
        elif score >= 40:
            return "Poor - Below average quality"
        else:
            return "Very Poor - Significant concerns"

    async def _arun(self, **kwargs: Any) -> str:
        """Async version."""
        return self._run(**kwargs)
