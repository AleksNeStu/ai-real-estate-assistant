"""
Neighborhood quality index tools.

Provides neighborhood quality scoring based on safety, schools, amenities,
walkability, green space, air quality, noise level, and public transport.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from core.security_utils import sanitize_for_log

logger = logging.getLogger(__name__)


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
    """Result from neighborhood quality index calculation."""

    property_id: str
    overall_score: float
    # Core factors
    safety_score: float
    schools_score: float
    amenities_score: float
    walkability_score: float
    green_space_score: float
    # New factors (Task #40)
    air_quality_score: Optional[float] = None
    noise_level_score: Optional[float] = None
    public_transport_score: Optional[float] = None
    # Detailed breakdown
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    factor_details: Optional[Dict[str, Any]] = None
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

    @staticmethod
    def _mock_safety_score(city: Optional[str], neighborhood: Optional[str]) -> float:
        """
        Mock safety score based on city/neighborhood (Phase 1).

        In production, this would call crime data APIs.
        Returns score 0-100.
        """
        # Demo: base score with some variation by city
        city_scores: Dict[str, float] = {
            "warsaw": 75.0,
            "krakow": 78.0,
            "wroclaw": 76.0,
            "poznan": 80.0,
            "gdansk": 77.0,
            "madrid": 72.0,
            "barcelona": 68.0,
            "london": 70.0,
            "berlin": 82.0,
            "paris": 65.0,
        }

        if city:
            base = city_scores.get(city.lower(), 70.0)
        else:
            base = 70.0

        # Add some variation for demo purposes
        seed = f"{city}:{neighborhood or 'unknown'}".encode()
        hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
        variation = (hash_val % 21) - 10  # -10 to +10

        return max(0, min(100, round(base + variation, 1)))

    @staticmethod
    def _calculate_safety_score(
        latitude: Optional[float],
        longitude: Optional[float],
        city: Optional[str] = None,
        neighborhood: Optional[str] = None,
    ) -> Tuple[float, Optional[Dict[str, Any]]]:
        """
        Calculate safety score using SafetyAdapter.

        Uses OSM data for police/emergency services with city fallback.
        Returns (score 0-100, details dict).
        """
        if latitude is None or longitude is None:
            # Use mock for city-only estimates
            score = NeighborhoodQualityIndexTool._mock_safety_score(city, neighborhood)
            return score, {"data_source": "city_estimate", "confidence": 0.3}

        try:
            from data.adapters.safety_adapter import get_safety_adapter

            adapter = get_safety_adapter()
            result = adapter.get_safety_score(
                latitude, longitude, city, neighborhood, radius_m=1500
            )

            details = {
                "raw_value": result.police_stations_nearby + result.emergency_services_nearby,
                "unit": "safety_pois",
                "normalized_score": result.score,
                "data_source": result.data_source,
                "confidence": result.confidence,
                "police_stations_nearby": result.police_stations_nearby,
                "emergency_services_nearby": result.emergency_services_nearby,
            }

            return round(result.score, 1), details

        except Exception as e:
            logger.warning("Safety score calculation failed: %s", sanitize_for_log(e))
            score = NeighborhoodQualityIndexTool._mock_safety_score(city, neighborhood)
            return score, {"data_source": "fallback", "confidence": 0.2, "error": str(e)}

    @staticmethod
    def _calculate_schools_score(latitude: Optional[float], longitude: Optional[float]) -> float:
        """
        Calculate schools score based on nearby school count.

        Uses OSM/Overpass data with mock fallback.
        Returns score 0-100.
        """
        if latitude is None or longitude is None:
            return 60.0  # Default middle score

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            school_count = adapter.count_schools(latitude, longitude, radius_m=1000)

            # Score based on school count (0-10+ schools within 1km)
            # 0-1 schools = 30, 2-3 = 50, 4-5 = 70, 6+ = 85+
            if school_count == 0:
                score = 30.0
            elif school_count <= 2:
                score = 30.0 + (school_count * 10)
            elif school_count <= 5:
                score = 50.0 + ((school_count - 2) * 10)
            else:
                score = min(95.0, 70.0 + ((school_count - 5) * 5))

            return round(score, 1)

        except Exception as e:
            # Fallback to mock on error
            logger.warning("Schools score calculation failed, using mock: %s", e)
            seed = f"{latitude:.4f},{longitude:.4f}".encode()
            hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
            score = 50 + (hash_val % 51)  # 50-100 range
            return float(score)

    @staticmethod
    def _calculate_amenities_score(latitude: Optional[float], longitude: Optional[float]) -> float:
        """
        Calculate amenities score based on nearby POI count.

        Uses OSM/Overpass data with mock fallback.
        Returns score 0-100.
        """
        if latitude is None or longitude is None:
            return 65.0

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            amenity_count = adapter.count_amenities(latitude, longitude, radius_m=500)

            # Score based on amenity count within 500m
            # 0-5 = 40, 6-15 = 60, 16-30 = 80, 31+ = 95+
            if amenity_count == 0:
                score = 40.0
            elif amenity_count <= 5:
                score = 40.0 + (amenity_count * 4)
            elif amenity_count <= 15:
                score = 60.0 + ((amenity_count - 5) * 2)
            elif amenity_count <= 30:
                score = 80.0 + ((amenity_count - 15) * 1)
            else:
                score = min(98.0, 85.0 + ((amenity_count - 30) * 0.5))

            return round(score, 1)

        except Exception as e:
            # Fallback to mock on error
            logger.warning("Amenities score calculation failed, using mock: %s", e)
            seed = f"amenities:{latitude:.4f},{longitude:.4f}".encode()
            hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
            score = 55 + (hash_val % 46)
            return float(score)

    @staticmethod
    def _calculate_walkability_score(
        latitude: Optional[float], longitude: Optional[float]
    ) -> float:
        """
        Calculate walkability score based on POI density and diversity.

        Uses OSM/Overpass data with mock fallback.
        Returns score 0-100.
        """
        if latitude is None or longitude is None:
            return 60.0

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            score = adapter.calculate_walkability(latitude, longitude, radius_m=500)

            return round(score, 1)

        except Exception as e:
            # Fallback to mock on error
            logger.warning("Walkability score calculation failed, using mock: %s", e)
            seed = f"walk:{latitude:.4f},{longitude:.4f}".encode()
            hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
            score = 45 + (hash_val % 56)
            return float(score)

    @staticmethod
    def _calculate_green_space_score(
        latitude: Optional[float], longitude: Optional[float]
    ) -> float:
        """
        Calculate green space score based on nearby parks/forests.

        Uses OSM/Overpass data with mock fallback.
        Returns score 0-100.
        """
        if latitude is None or longitude is None:
            return 55.0

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter

            adapter = get_neighborhood_adapter()
            green_count = adapter.count_green_spaces(latitude, longitude, radius_m=1000)

            # Score based on green spaces within 1km
            # 0 = 30, 1 = 50, 2-3 = 65, 4-5 = 80, 6+ = 90+
            if green_count == 0:
                score = 30.0
            elif green_count == 1:
                score = 50.0
            elif green_count <= 3:
                score = 65.0 + (green_count - 2) * 7.5
            elif green_count <= 5:
                score = 80.0 + (green_count - 4) * 5
            else:
                score = min(98.0, 85.0 + (green_count - 6) * 2)

            return round(score, 1)

        except Exception as e:
            # Fallback to mock on error
            logger.warning("Green space score calculation failed, using mock: %s", e)
            seed = f"green:{latitude:.4f},{longitude:.4f}".encode()
            hash_val = int(hashlib.sha256(seed).hexdigest()[:8], 16)
            score = 40 + (hash_val % 61)
            return float(score)

    @staticmethod
    def _calculate_air_quality_score(
        latitude: Optional[float],
        longitude: Optional[float],
        city: Optional[str] = None,
    ) -> Tuple[float, Optional[Dict[str, Any]]]:
        """
        Calculate air quality score using AirQualityAdapter.

        Uses WAQI API with city fallback.
        Returns (score 0-100, details dict).
        """
        if latitude is None or longitude is None:
            # Return city-based estimate
            return 60.0, {"data_source": "city_estimate", "confidence": 0.3}

        try:
            from data.adapters.air_quality_adapter import get_air_quality_adapter

            adapter = get_air_quality_adapter()
            result = adapter.get_aqi_score(latitude, longitude, city)

            details = {
                "raw_value": result.aqi_value,
                "unit": "AQI",
                "normalized_score": result.score,
                "data_source": result.data_source,
                "confidence": result.confidence,
                "pm25": result.pm25,
                "pm10": result.pm10,
                "station_name": result.station_name,
            }

            return round(result.score, 1), details

        except Exception as e:
            logger.warning("Air quality calculation failed: %s", sanitize_for_log(e))
            return 60.0, {"data_source": "fallback", "confidence": 0.2, "error": str(e)}

    @staticmethod
    def _calculate_noise_score(
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Tuple[float, Optional[Dict[str, Any]]]:
        """
        Calculate noise level/quietness score using NoiseAdapter.

        Uses OSM data to estimate noise from roads, railways, airports.
        Returns (score 0-100 where higher = quieter, details dict).
        """
        if latitude is None or longitude is None:
            return 65.0, {"data_source": "default", "confidence": 0.3}

        try:
            from data.adapters.noise_adapter import get_noise_adapter

            adapter = get_noise_adapter()
            result = adapter.estimate_noise_level(latitude, longitude)

            details = {
                "raw_value": result.estimated_db,
                "unit": "dB (estimated)",
                "normalized_score": result.score,
                "data_source": result.data_source,
                "confidence": result.confidence,
                "noise_sources_count": len(result.noise_sources),
            }

            return round(result.score, 1), details

        except Exception as e:
            logger.warning("Noise level calculation failed: %s", sanitize_for_log(e))
            return 65.0, {"data_source": "fallback", "confidence": 0.2, "error": str(e)}

    @staticmethod
    def _calculate_transport_score(
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Tuple[float, Optional[Dict[str, Any]]]:
        """
        Calculate public transport accessibility using TransportAdapter.

        Uses OSM Overpass to count bus/tram/metro stops.
        Returns (score 0-100, details dict).
        """
        if latitude is None or longitude is None:
            return 55.0, {"data_source": "default", "confidence": 0.3}

        try:
            from data.adapters.transport_adapter import get_transport_adapter

            adapter = get_transport_adapter()
            result = adapter.get_full_result(latitude, longitude)

            details = {
                "raw_value": result.total_stops,
                "unit": "stops",
                "normalized_score": result.score,
                "data_source": result.data_source,
                "confidence": result.confidence,
                "stops_by_type": result.stops_by_type,
            }

            return round(result.score, 1), details

        except Exception as e:
            logger.warning("Transport calculation failed: %s", sanitize_for_log(e))
            return 55.0, {"data_source": "fallback", "confidence": 0.2, "error": str(e)}

    @staticmethod
    def _get_city_comparison(
        city: Optional[str],
        scores: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        """
        Get comparison to city average scores.

        Returns city comparison data or None if city not found.
        """
        if not city:
            return None

        try:
            from data.city_averages import compare_to_city

            comparison = compare_to_city(city, scores)

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
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Optional[Dict[str, List[Dict[str, Any]]]]:
        """
        Fetch nearby POIs for map visualization.

        Returns categorized POIs or None if coordinates missing.
        """
        if latitude is None or longitude is None:
            return None

        try:
            from data.adapters.neighborhood_adapter import get_neighborhood_adapter
            from data.adapters.safety_adapter import get_safety_adapter
            from data.adapters.transport_adapter import get_transport_adapter

            # Fetch POIs from multiple adapters
            neighborhood_adapter = get_neighborhood_adapter()
            transport_adapter = get_transport_adapter()
            safety_adapter = get_safety_adapter()

            # Get neighborhood POIs
            pois = neighborhood_adapter.fetch_pois_within_radius(latitude, longitude, radius_m=1000)

            # Get transport stops
            transport_result = transport_adapter.calculate_accessibility_score(latitude, longitude)  # type: ignore[attr-defined]

            # Get safety POIs
            safety_pois = safety_adapter.get_police_stations(latitude, longitude, radius_m=2000)

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

        Returns NeighborhoodQualityResult with all scores, city comparison, and POIs.
        """

        # Validate and get weights
        weights = NeighborhoodQualityIndexTool._validate_weights(custom_weights)

        # Calculate individual component scores
        safety_score, safety_details = NeighborhoodQualityIndexTool._calculate_safety_score(
            latitude, longitude, city, neighborhood
        )
        schools_score = NeighborhoodQualityIndexTool._calculate_schools_score(latitude, longitude)
        amenities_score = NeighborhoodQualityIndexTool._calculate_amenities_score(
            latitude, longitude
        )
        walkability_score = NeighborhoodQualityIndexTool._calculate_walkability_score(
            latitude, longitude
        )
        green_space_score = NeighborhoodQualityIndexTool._calculate_green_space_score(
            latitude, longitude
        )

        # Calculate new factor scores (Task #40)
        air_quality_score, air_quality_details = (
            NeighborhoodQualityIndexTool._calculate_air_quality_score(latitude, longitude, city)
        )
        noise_level_score, noise_details = NeighborhoodQualityIndexTool._calculate_noise_score(
            latitude, longitude
        )
        public_transport_score, transport_details = (
            NeighborhoodQualityIndexTool._calculate_transport_score(latitude, longitude)
        )

        # Build scores dict for city comparison
        all_scores = {
            "safety": safety_score,
            "schools": schools_score,
            "amenities": amenities_score,
            "walkability": walkability_score,
            "green_space": green_space_score,
            "air_quality": air_quality_score,
            "noise_level": noise_level_score,
            "public_transport": public_transport_score,
        }

        # Calculate weighted overall score
        overall_score = sum(all_scores[key] * weights.get(key, 0) for key in all_scores)

        # Build score breakdown with weights
        score_breakdown = {
            "safety_weighted": round(safety_score * weights.get("safety", 0.15), 2),
            "schools_weighted": round(schools_score * weights.get("schools", 0.15), 2),
            "amenities_weighted": round(amenities_score * weights.get("amenities", 0.15), 2),
            "walkability_weighted": round(walkability_score * weights.get("walkability", 0.15), 2),
            "green_space_weighted": round(green_space_score * weights.get("green_space", 0.10), 2),
            "air_quality_weighted": round(air_quality_score * weights.get("air_quality", 0.10), 2),
            "noise_level_weighted": round(noise_level_score * weights.get("noise_level", 0.10), 2),
            "public_transport_weighted": round(
                public_transport_score * weights.get("public_transport", 0.10), 2
            ),
        }

        # Build factor details
        factor_details = {
            "safety": {
                "normalized_score": safety_score,
                "weight": weights.get("safety", 0.15),
                "weighted_score": score_breakdown["safety_weighted"],
                "data_source": safety_details.get("data_source", "unknown")
                if safety_details
                else "unknown",
                "confidence": safety_details.get("confidence", 0.5) if safety_details else 0.5,
                "police_stations_nearby": safety_details.get("police_stations_nearby", 0)
                if safety_details
                else 0,
                "emergency_services_nearby": safety_details.get("emergency_services_nearby", 0)
                if safety_details
                else 0,
            },
            "schools": {
                "normalized_score": schools_score,
                "weight": weights.get("schools", 0.15),
                "weighted_score": score_breakdown["schools_weighted"],
                "data_source": "osm_overpass_api",
                "confidence": 0.8 if latitude and longitude else 0.3,
            },
            "amenities": {
                "normalized_score": amenities_score,
                "weight": weights.get("amenities", 0.15),
                "weighted_score": score_breakdown["amenities_weighted"],
                "data_source": "osm_overpass_api",
                "confidence": 0.8 if latitude and longitude else 0.3,
            },
            "walkability": {
                "normalized_score": walkability_score,
                "weight": weights.get("walkability", 0.15),
                "weighted_score": score_breakdown["walkability_weighted"],
                "data_source": "osm_overpass_api",
                "confidence": 0.8 if latitude and longitude else 0.3,
            },
            "green_space": {
                "normalized_score": green_space_score,
                "weight": weights.get("green_space", 0.10),
                "weighted_score": score_breakdown["green_space_weighted"],
                "data_source": "osm_overpass_api",
                "confidence": 0.8 if latitude and longitude else 0.3,
            },
            "air_quality": {
                "normalized_score": air_quality_score,
                "weight": weights.get("air_quality", 0.10),
                "weighted_score": score_breakdown["air_quality_weighted"],
                **(air_quality_details or {}),
            },
            "noise_level": {
                "normalized_score": noise_level_score,
                "weight": weights.get("noise_level", 0.10),
                "weighted_score": score_breakdown["noise_level_weighted"],
                **(noise_details or {}),
            },
            "public_transport": {
                "normalized_score": public_transport_score,
                "weight": weights.get("public_transport", 0.10),
                "weighted_score": score_breakdown["public_transport_weighted"],
                **(transport_details or {}),
            },
        }

        # City comparison
        city_comparison = None
        if compare_to_city_average:
            city_comparison = NeighborhoodQualityIndexTool._get_city_comparison(city, all_scores)

        # Nearby POIs
        nearby_pois = None
        if include_pois:
            nearby_pois = NeighborhoodQualityIndexTool._fetch_nearby_pois(latitude, longitude)

        # Data sources
        data_sources = ["osm_overpass_api"]
        if latitude and longitude:
            data_sources.append("geographic_coordinates")
        if air_quality_details and air_quality_details.get("data_source") == "waqi_api":
            data_sources.append("waqi_air_quality_api")

        # Data freshness
        now = datetime.utcnow().isoformat()
        data_freshness = {
            "neighborhood_data": now,
            "air_quality": now,
        }

        return NeighborhoodQualityResult(
            property_id=property_id,
            overall_score=round(overall_score, 1),
            safety_score=round(safety_score, 1),
            schools_score=round(schools_score, 1),
            amenities_score=round(amenities_score, 1),
            walkability_score=round(walkability_score, 1),
            green_space_score=round(green_space_score, 1),
            air_quality_score=round(air_quality_score, 1),
            noise_level_score=round(noise_level_score, 1),
            public_transport_score=round(public_transport_score, 1),
            score_breakdown=score_breakdown,
            factor_details=factor_details,
            city_comparison=city_comparison,
            nearby_pois=nearby_pois,
            data_sources=data_sources,
            data_freshness=data_freshness,
            latitude=latitude,
            longitude=longitude,
            city=city,
            neighborhood=neighborhood,
        )

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

            # Format result for display
            formatted = f"""
Neighborhood Quality Index for Property {result.property_id}:

=== OVERALL SCORE: {result.overall_score:.1f}/100 ===

Core Factor Scores:
- Safety:           {result.safety_score:.1f}/100 (Weight: 15%)
- Schools:          {result.schools_score:.1f}/100 (Weight: 15%)
- Amenities:        {result.amenities_score:.1f}/100 (Weight: 15%)
- Walkability:      {result.walkability_score:.1f}/100 (Weight: 15%)
- Green Space:      {result.green_space_score:.1f}/100 (Weight: 10%)

Environmental & Transport Scores:
- Air Quality:      {result.air_quality_score:.1f}/100 (Weight: 10%)
- Noise Level:      {result.noise_level_score:.1f}/100 (Weight: 10%)
- Public Transport: {result.public_transport_score:.1f}/100 (Weight: 10%)

Score Breakdown (Weighted):
"""

            for key, value in result.score_breakdown.items():
                formatted += f"- {key.replace('_', ' ').title()}: {value:.2f}\n"

            # City comparison
            if result.city_comparison:
                formatted += f"""
City Comparison (vs {result.city_comparison.get("city_name", "City")}):
- Percentile: {result.city_comparison.get("percentile", "N/A")}th
- Better than average: {", ".join(result.city_comparison.get("better_than", [])) or "None"}
- Below average: {", ".join(result.city_comparison.get("worse_than", [])) or "None"}
"""

            formatted += f"""
Data Sources: {", ".join(result.data_sources)}
Location: {result.city or "Unknown"}, {result.neighborhood or "Unknown"}
Coordinates: {result.latitude or "N/A"}, {result.longitude or "N/A"}

Rating: {self._get_rating_label(result.overall_score)}
"""
            return formatted.strip()

        except Exception as e:
            return f"Error calculating neighborhood quality: {str(e)}"

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
