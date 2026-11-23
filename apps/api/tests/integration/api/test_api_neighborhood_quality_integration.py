"""
The neighborhood quality index, through the API.

The endpoint answers eight factors and the POIs they were read from. The
providers are stubbed here: this test is about the route, the tool and the
answer the route gives - the map itself is the unit suite's business.

The stubs answer a point in Warsaw, so the answer is read off the stubs and
not off a live provider.
"""

from contextlib import contextmanager
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from api.main import app
from config.settings import get_settings
from data.adapters.air_quality_adapter import AirQualityAdapter, AirQualityResult
from data.adapters.neighborhood_adapter import NeighborhoodAdapter
from data.adapters.noise_adapter import NoiseAdapter, NoiseResult
from data.adapters.safety_adapter import SafetyAdapter, SafetyPOI, SafetyResult
from data.adapters.transport_adapter import (
    TransportAdapter,
    TransportResult,
    TransportStop,
)
from tools.neighborhood_tools import NeighborhoodQualityIndexTool

client = TestClient(app)

# A point in Warsaw, the city the district belongs to.
POINT = {
    "property_id": "p1",
    "latitude": 52.2297,
    "longitude": 21.0122,
    "city": "Warsaw",
    "neighborhood": "Śródmieście",
}


def _features():
    """The features the counts were read from."""
    return {
        "schools": [
            {
                "id": "1",
                "name": "Szkoła Podstawowa nr 1",
                "amenity": "school",
                "latitude": 52.23,
                "longitude": 21.01,
                "distance_m": 120.0,
            }
        ],
        "amenities": [
            {
                "id": "2",
                "name": "Kawiarnia",
                "amenity": "cafe",
                "latitude": 52.231,
                "longitude": 21.013,
                "distance_m": 80.0,
            }
        ],
        "green_spaces": [
            {
                "id": "3",
                "name": "Park Śródmieście",
                "amenity": "park",
                "latitude": 52.229,
                "longitude": 21.009,
                "distance_m": 200.0,
            }
        ],
    }


def _providers():
    """The five providers, answered from the fixtures above."""
    neighborhood = Mock(spec=NeighborhoodAdapter)
    neighborhood.count_schools.return_value = 4
    neighborhood.count_amenities.return_value = 12
    neighborhood.calculate_walkability.return_value = 70.0
    neighborhood.count_green_spaces.return_value = 3
    neighborhood.fetch_pois_within_radius.return_value = _features()

    safety = Mock(spec=SafetyAdapter)
    safety.get_safety_score.return_value = SafetyResult(
        score=75.0,
        police_stations_nearby=2,
        emergency_services_nearby=1,
        lighting_score=None,
        pois=[],
        data_source="osm_overpass_api",
        confidence=0.8,
    )
    safety.get_police_stations.return_value = [
        SafetyPOI(
            id="7",
            name="Komisariat",
            type="police",
            latitude=52.228,
            longitude=21.008,
            distance_m=300.0,
        )
    ]

    air_quality = Mock(spec=AirQualityAdapter)
    air_quality.get_aqi_score.return_value = AirQualityResult(
        score=70.0,
        aqi_value=None,
        pm25=None,
        pm10=None,
        data_source="fallback",
        confidence=0.3,
        station_name=None,
    )

    noise = Mock(spec=NoiseAdapter)
    noise.estimate_noise_level.return_value = NoiseResult(
        score=65.0,
        estimated_db=50.0,
        noise_sources=[],
        data_source="fallback",
        confidence=0.3,
        query_latitude=POINT["latitude"],
        query_longitude=POINT["longitude"],
    )

    transport = Mock(spec=TransportAdapter)
    transport.count_stops.return_value = 4
    # The adapter answers with the whole result, so the stops it found can
    # be named: the tool reads the score from it and the stops from it too.
    transport_result = TransportResult(
        score=60.0,
        total_stops=4,
        stops_by_type={"bus": 3, "tram": 1, "metro": 0, "train": 0, "light_rail": 0},
        stops=[
            TransportStop(
                id="9",
                name="Przystanek",
                type="bus",
                latitude=52.2295,
                longitude=21.011,
                distance_m=150.0,
            )
        ],
        data_source="overpass",
        confidence=0.7,
    )
    transport.get_full_result.return_value = transport_result
    transport.calculate_accessibility_score.return_value = transport_result

    return neighborhood, safety, air_quality, noise, transport


@contextmanager
def _stubbed_providers(**overrides):
    """Patch every provider the tool asks, so no request leaves the machine."""
    neighborhood, safety, air_quality, noise, transport = _providers()
    neighborhood = overrides.get("neighborhood", neighborhood)
    safety = overrides.get("safety", safety)
    air_quality = overrides.get("air_quality", air_quality)
    noise = overrides.get("noise", noise)
    transport = overrides.get("transport", transport)
    with (
        patch(
            "data.adapters.neighborhood_adapter.get_neighborhood_adapter",
            return_value=neighborhood,
        ),
        patch(
            "data.adapters.safety_adapter.get_safety_adapter",
            return_value=safety,
        ),
        patch(
            "data.adapters.air_quality_adapter.get_air_quality_adapter",
            return_value=air_quality,
        ),
        patch(
            "data.adapters.noise_adapter.get_noise_adapter",
            return_value=noise,
        ),
        patch(
            "data.adapters.transport_adapter.get_transport_adapter",
            return_value=transport,
        ),
    ):
        yield


def test_a_point_is_answered_with_the_factors_and_the_pois_they_came_from():
    """The eight factors, the overall score, and the POIs the counts came from."""
    key = get_settings().api_access_key

    with _stubbed_providers():
        response = client.post(
            "/api/v1/tools/neighborhood-quality",
            json=POINT,
            headers={"X-API-Key": key},
        )

    assert response.status_code == 200
    body = response.json()

    assert body["property_id"] == "p1"
    assert body["latitude"] == POINT["latitude"]
    assert body["longitude"] == POINT["longitude"]

    # Every factor the tool measured carries a score.
    assert body["safety_score"] == 75.0
    assert body["schools_score"] is not None
    assert body["amenities_score"] is not None
    assert body["walkability_score"] == 70.0
    assert body["green_space_score"] is not None
    assert body["air_quality_score"] == 70.0
    assert body["noise_level_score"] == 65.0
    assert body["public_transport_score"] == 60.0
    assert 0 <= body["overall_score"] <= 100

    # The factors say where their numbers came from.
    schools = body["factor_details"]["schools"]
    assert schools["data_source"] == "osm_overpass_api"
    assert schools["unit"] == "schools"
    assert schools["normalized_score"] == body["schools_score"]
    assert schools["weight"] == 0.15

    # The POIs the map holds, for the map on the page.
    assert body["nearby_pois"]["schools"][0]["name"] == "Szkoła Podstawowa nr 1"
    assert body["nearby_pois"]["green_spaces"][0]["name"] == "Park Śródmieście"

    # A point is measured at the point.
    assert "geographic_coordinates" in body["data_sources"]


def test_a_factor_the_map_cannot_answer_is_answered_without_a_score():
    """The provider is down: the endpoint answers with the factor left open.

    The answer is 200 - the factor carries no score, and the reason it
    carries none is named. The endpoint answered 400 before: the response
    model asked for a number the map had not given.
    """
    neighborhood, safety, air_quality, noise, transport = _providers()
    neighborhood.count_schools.side_effect = RuntimeError("the provider is down")

    key = get_settings().api_access_key
    with _stubbed_providers(
        neighborhood=neighborhood,
        safety=safety,
        air_quality=air_quality,
        noise=noise,
        transport=transport,
    ):
        response = client.post(
            "/api/v1/tools/neighborhood-quality",
            json=POINT,
            headers={"X-API-Key": key},
        )

    assert response.status_code == 200
    body = response.json()

    # The factor nobody could measure carries no score.
    assert body["schools_score"] is None
    # The factors that could be measured still carry theirs.
    assert body["amenities_score"] is not None
    assert body["safety_score"] == 75.0
    # And the reason is in the answer.
    assert (
        "the provider could not be asked for the schools nearby"
        in (body["components_without_data"]["schools"])
    )


def test_a_factor_the_map_cannot_answer_carries_no_score_and_says_why():
    """The provider is down: the factor is left without a number, and the reason is named.

    The tool measures what it can and leaves the rest without a score - the
    weight of a factor nobody measured is never spent on a number.
    """
    neighborhood, safety, air_quality, noise, transport = _providers()
    for method in ("count_schools", "count_amenities", "count_green_spaces"):
        getattr(neighborhood, method).side_effect = RuntimeError("the provider is down")

    with _stubbed_providers(
        neighborhood=neighborhood,
        safety=safety,
        air_quality=air_quality,
        noise=noise,
        transport=transport,
    ):
        result = NeighborhoodQualityIndexTool.calculate(
            property_id="p1",
            latitude=POINT["latitude"],
            longitude=POINT["longitude"],
            city=POINT["city"],
        )

    # The three counts the provider refused are left without a score.
    assert result.schools_score is None
    assert result.amenities_score is None
    assert result.green_space_score is None

    # The reason is named, and it names the provider that refused.
    assert (
        "the provider could not be asked for the schools nearby"
        in (result.components_without_data["schools"])
    )
    assert "the provider is down" in result.components_without_data["schools"]

    # The factors that could be measured still are.
    assert result.safety_score == 75.0
    assert result.air_quality_score == 70.0
    assert result.noise_level_score == 65.0
    assert result.public_transport_score == 60.0
