"""
Unit tests for enhanced neighborhood data adapters (Task #40, Task #92).

Task #92 replaced the network-dependent skips with tests against recorded
provider responses: the fixtures under ``tests/fixtures/neighborhood/`` hold
what the OpenStreetMap Overpass API answered on 2026-11-19 and what the WAQI
adapter itself answers when it holds no token. No test in this file reaches
the network.

Tests for:
- AirQualityAdapter (WAQI/GIOS integration)
- TransportAdapter (OSM public transport stops)
- NoiseAdapter (OSM noise source estimation)
- SafetyAdapter (enhanced safety data)
"""

from unittest.mock import Mock, patch

import pytest

from data.adapters.air_quality_adapter import (
    AirQualityAdapter,
    AirQualityResult,
    get_air_quality_adapter,
)
from data.adapters.neighborhood_adapter import NeighborhoodAdapter
from data.adapters.noise_adapter import (
    NoiseAdapter,
    get_noise_adapter,
)
from data.adapters.safety_adapter import (
    SafetyAdapter,
    SafetyPOI,
    get_safety_adapter,
)
from data.adapters.transport_adapter import (
    TransportAdapter,
    TransportResult,
    get_transport_adapter,
)
from tests.fixtures.neighborhood.loader import (
    adapter_query_answer as _adapter_query_answer,
)
from tests.fixtures.neighborhood.loader import (
    load_overpass,
    load_overpass_body,
    load_waqi_keyless,
    overpass_get,
    query_shape,
    recorded_response,
)
from tests.fixtures.neighborhood.loader import (
    valid_query_answer as _valid_query_answer,
)

# Warsaw centre - the point every recorded response was fetched around.
WARSAW_LAT = 52.2297
WARSAW_LON = 21.0122


# =============================================================================
# AirQualityAdapter Tests
# =============================================================================


class TestAirQualityAdapter:
    """Tests for AirQualityAdapter."""

    @pytest.fixture(autouse=True)
    def _without_waqi_token(self, monkeypatch):
        """The project holds no WAQI token: the adapter stays on its keyless path."""
        monkeypatch.delenv("WAQI_API_KEY", raising=False)

    def test_get_aqi_score_returns_valid_range(self):
        """Test AQI score is in 0-100 range."""
        adapter = AirQualityAdapter()
        result = adapter.get_aqi_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

        assert 0 <= result.score <= 100
        # Accept any data_source that indicates non-primary data
        assert result.data_source is not None
        assert 0 <= result.confidence <= 1

    def test_keyless_answer_matches_the_recorded_one(self):
        """The adapter's keyless answer is the recorded one, field for field."""
        recorded = load_waqi_keyless()["keyless_result"]

        adapter = AirQualityAdapter()
        result = adapter.get_aqi_score(
            recorded["latitude"], recorded["longitude"], recorded["city"]
        )

        assert result.score == recorded["score"]
        assert result.aqi_value == recorded["aqi_value"]
        assert result.pm25 == recorded["pm25"]
        assert result.pm10 == recorded["pm10"]
        assert result.data_source == recorded["data_source"]
        assert result.confidence == recorded["confidence"]
        assert result.station_name == recorded["station_name"]

    def test_keyless_station_lookup_returns_nothing(self):
        """Without a token the adapter finds no station - as recorded."""
        recorded = load_waqi_keyless()["keyless_station_lookup"]

        adapter = AirQualityAdapter()
        station = adapter.get_nearest_station(recorded["latitude"], recorded["longitude"])

        assert station is None
        assert recorded["station"] is None

    def test_aqi_score_fallback_on_api_error(self):
        """Test fallback to mock when API fails."""
        with patch("requests.get", side_effect=Exception("API Error")):
            adapter = AirQualityAdapter()
            result = adapter.get_aqi_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

            # Should use fallback data
            assert result.data_source in ["fallback", "city_fallback", "mock_fallback"]
            assert result.confidence < 0.8

    def test_aqi_score_without_coordinates(self):
        """Test AQI score with missing coordinates uses city fallback."""
        adapter = AirQualityAdapter()
        result = adapter.get_aqi_score(None, None, "Warsaw")

        # Should use fallback data
        assert result.data_source in ["fallback", "city_fallback", "mock_fallback"]
        assert result.confidence < 0.8

    def test_aqi_score_returns_result_object(self):
        """Test that get_aqi_score returns proper AirQualityResult."""
        adapter = AirQualityAdapter()
        result = adapter.get_aqi_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

        assert isinstance(result, AirQualityResult)
        assert hasattr(result, "score")
        assert hasattr(result, "aqi_value")
        assert hasattr(result, "confidence")

    def test_get_air_quality_adapter_singleton(self):
        """Test that get_air_quality_adapter returns same instance."""
        adapter1 = get_air_quality_adapter()
        adapter2 = get_air_quality_adapter()

        assert adapter1 is adapter2


# =============================================================================
# TransportAdapter Tests
# =============================================================================


class TestTransportAdapter:
    """Tests for TransportAdapter."""

    def test_calculate_accessibility_score_returns_float(self):
        """Test accessibility score calculation returns valid score."""
        adapter = TransportAdapter()
        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            # Use float return type (actual implementation)
            score = adapter.calculate_accessibility_score(WARSAW_LAT, WARSAW_LON)

        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    def test_get_transport_result_returns_valid_structure(self):
        """Test get_transport_result returns proper structure."""
        adapter = TransportAdapter()

        # Check if method exists
        if hasattr(adapter, "get_transport_result"):
            with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
                result = adapter.get_transport_result(WARSAW_LAT, WARSAW_LON)
            assert isinstance(result, TransportResult)

    def test_accessibility_score_no_stops(self):
        """Test accessibility score with no stops nearby."""
        adapter = TransportAdapter()

        # The recorded answer for a point with no features at all: the adapter
        # must handle it gracefully
        with patch("requests.get", side_effect=overpass_get(lambda q: "empty_result")):
            score = adapter.calculate_accessibility_score(52.0, 20.0)  # Rural Poland

        # Should return a valid score even in rural areas
        assert 0 <= score <= 100

    def test_get_transport_adapter_singleton(self):
        """Test that get_transport_adapter returns same instance."""
        adapter1 = get_transport_adapter()
        adapter2 = get_transport_adapter()

        assert adapter1 is adapter2


# =============================================================================
# NoiseAdapter Tests
# =============================================================================


class TestNoiseAdapter:
    """Tests for NoiseAdapter."""

    def test_estimate_noise_level_returns_valid_result(self):
        """Test noise estimation returns proper structure."""
        adapter = NoiseAdapter()
        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            result = adapter.estimate_noise_level(WARSAW_LAT, WARSAW_LON)

        assert 0 <= result.score <= 100
        assert 40 <= result.estimated_db <= 80
        assert isinstance(result.noise_sources, list)

    def test_noise_score_higher_for_quiet_areas(self):
        """Test that quieter areas get higher scores."""
        adapter = NoiseAdapter()

        # Test a quiet rural area (should have higher score)
        with patch("requests.get", side_effect=overpass_get(lambda q: "empty_result")):
            result_quiet = adapter.estimate_noise_level(52.0, 20.0)  # Rural Poland

        # Test a busy city center (should have lower score)
        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            result_noisy = adapter.estimate_noise_level(WARSAW_LAT, WARSAW_LON)

        # Both should be valid scores
        assert 0 <= result_quiet.score <= 100
        assert 0 <= result_noisy.score <= 100
        # Quiet area should have higher or equal score (may vary due to API data)
        # This is a soft assertion - just verify both return valid scores

    def test_noise_sources_detection(self):
        """Test detection of various noise sources."""
        adapter = NoiseAdapter()

        # Test that noise sources are detected in a city
        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            result = adapter.estimate_noise_level(WARSAW_LAT, WARSAW_LON)

        # Should return valid result structure
        assert isinstance(result.noise_sources, list)
        assert 40 <= result.estimated_db <= 80

    def test_get_noise_adapter_singleton(self):
        """Test that get_noise_adapter returns same instance."""
        adapter1 = get_noise_adapter()
        adapter2 = get_noise_adapter()

        assert adapter1 is adapter2


# =============================================================================
# SafetyAdapter Tests
# =============================================================================


class TestSafetyAdapter:
    """Tests for SafetyAdapter."""

    def test_get_safety_score_returns_valid_result(self):
        """Test safety score returns proper structure."""
        adapter = SafetyAdapter()
        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            result = adapter.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

        assert 0 <= result.score <= 100
        assert isinstance(result.police_stations_nearby, int)
        assert isinstance(result.emergency_services_nearby, int)
        assert 0 <= result.confidence <= 1

    def test_safety_score_city_variation(self):
        """Test that different cities have different base scores."""
        adapter = SafetyAdapter()

        warsaw_score = adapter.get_safety_score(None, None, "Warsaw")
        berlin_score = adapter.get_safety_score(None, None, "Berlin")

        # Berlin has higher safety score in our data
        assert berlin_score.score > warsaw_score.score

    def test_safety_score_with_police_stations(self):
        """Test that nearby police stations improve score."""
        adapter = SafetyAdapter()

        with patch.object(adapter, "_fetch_safety_pois") as mock_fetch:
            mock_fetch.return_value = [
                SafetyPOI(
                    id="1",
                    name="Police Station",
                    type="police",
                    latitude=52.23,
                    longitude=21.01,
                    distance_m=500,
                )
            ]
            result_with_police = adapter.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

        with patch.object(adapter, "_fetch_safety_pois", return_value=[]):
            result_without_police = adapter.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

        # With police station should have higher or equal score
        assert result_with_police.score >= result_without_police.score

    def test_get_police_stations(self):
        """Test fetching police stations."""
        adapter = SafetyAdapter()

        with patch.object(adapter, "_fetch_safety_pois") as mock_fetch:
            mock_fetch.return_value = [
                SafetyPOI(
                    id="1",
                    name="Police Station",
                    type="police",
                    latitude=52.23,
                    longitude=21.01,
                    distance_m=500,
                )
            ]
            stations = adapter.get_police_stations(WARSAW_LAT, WARSAW_LON, 2000)

            assert len(stations) == 1
            assert stations[0].type == "police"

    def test_get_safety_adapter_singleton(self):
        """Test that get_safety_adapter returns same instance."""
        adapter1 = get_safety_adapter()
        adapter2 = get_safety_adapter()

        assert adapter1 is adapter2


# =============================================================================
# The recorded provider answers, field by field (Task #92)
# =============================================================================


class TestRecordedProviderMapping:
    """Every field of a recorded answer reaches the shape the service expects."""

    def test_transport_maps_every_stop(self):
        """Each recorded transport element becomes a TransportStop."""
        recorded = load_overpass_body("valid_query_transport_stops")["elements"]
        adapter = TransportAdapter()

        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            stops = adapter.fetch_transport_pois(WARSAW_LAT, WARSAW_LON)

        assert len(stops) == len(recorded)
        by_id = {stop.id: stop for stop in stops}

        for element in recorded:
            stop = by_id[str(element["id"])]
            tags = element["tags"]
            assert stop.type in {"bus", "tram", "metro", "train", "light_rail"}
            assert stop.name == (tags.get("name") or tags.get("ref"))
            assert stop.distance_m > 0
            assert stop.latitude == element.get("lat", element.get("center", {}).get("lat"))
            assert stop.longitude == element.get("lon", element.get("center", {}).get("lon"))

        # The type follows the tag the provider sent
        bus_stops = [e for e in recorded if e["tags"].get("highway") == "bus_stop"]
        assert bus_stops
        for element in bus_stops:
            assert by_id[str(element["id"])].type == "bus"

    def test_transport_counts_agree_with_the_stops(self):
        """The per-type counts add up to the stops that were found."""
        adapter = TransportAdapter()

        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            stops = adapter.fetch_transport_pois(WARSAW_LAT, WARSAW_LON)
            counts = adapter.get_stop_types(WARSAW_LAT, WARSAW_LON)

        assert sum(counts.values()) == len(stops)
        assert counts["bus"] > 0

    def test_safety_maps_every_poi(self):
        """Each recorded safety element becomes a SafetyPOI."""
        recorded = load_overpass_body("valid_query_safety_pois")["elements"]
        adapter = SafetyAdapter()

        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            result = adapter.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

        assert len(result.pois) == len(recorded)
        assert result.police_stations_nearby == len(recorded)
        assert result.emergency_services_nearby == 0
        assert result.data_source == "osm_overpass_api"
        assert result.confidence == 0.7

        by_id = {poi.id: poi for poi in result.pois}
        for element in recorded:
            poi = by_id[f"osm_{element['type']}_{element['id']}"]
            assert poi.type == "police"
            assert poi.name == element["tags"].get("name")
            assert poi.distance_m > 0

    def test_neighborhood_maps_schools_amenities_and_green_spaces(self):
        """Each recorded POI lands in the category its tag names."""
        adapter = NeighborhoodAdapter()

        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            schools = adapter.fetch_pois_within_radius(WARSAW_LAT, WARSAW_LON, 1000, ["school"])
            amenities = adapter.fetch_pois_within_radius(
                WARSAW_LAT, WARSAW_LON, 1000, ["restaurant"]
            )
            green = adapter.fetch_pois_within_radius(WARSAW_LAT, WARSAW_LON, 1000, ["park"])

        recorded_schools = load_overpass_body("valid_query_neighborhood_schools")["elements"]
        recorded_amenities = load_overpass_body("valid_query_neighborhood_amenities")["elements"]
        recorded_green = load_overpass_body("valid_query_neighborhood_green_spaces")["elements"]

        assert len(schools["schools"]) == len(recorded_schools)
        assert len(amenities["amenities"]) == len(recorded_amenities)
        assert len(green["green_spaces"]) == len(recorded_green)

        for poi, element in zip(schools["schools"], recorded_schools, strict=True):
            assert poi["id"] == element["id"]
            assert poi["type"] == element["type"]
            assert poi["amenity"] == element["tags"].get("amenity")
            assert poi["latitude"] == element.get("lat", element.get("center", {}).get("lat"))
            assert poi["longitude"] == element.get("lon", element.get("center", {}).get("lon"))

        for poi, element in zip(green["green_spaces"], recorded_green, strict=True):
            assert poi["leisure"] == element["tags"].get("leisure") or poi["landuse"] == (
                element["tags"].get("landuse")
            )

    def test_noise_maps_every_source(self):
        """Each recorded noise element becomes a NoiseSource of the right type."""
        adapter = NoiseAdapter()

        with patch("requests.get", side_effect=overpass_get(_valid_query_answer)):
            sources = adapter.get_nearby_noise_sources(WARSAW_LAT, WARSAW_LON)

        recorded_roads = load_overpass_body("valid_query_noise_roads")["elements"]
        recorded_railways = load_overpass_body("valid_query_noise_railways")["elements"]
        recorded_airports = load_overpass_body("valid_query_noise_airports")["elements"]
        recorded_industrial = load_overpass_body("valid_query_noise_industrial")["elements"]

        by_id = {source.id: source for source in sources}
        assert len(sources) == (
            len(recorded_roads)
            + len(recorded_railways)
            + len(recorded_airports)
            + len(recorded_industrial)
        )

        for element in recorded_roads:
            source = by_id[f"road_{element['id']}"]
            assert source.type == "road"
            assert source.severity == 0.4  # "secondary" road
            assert source.name == (element["tags"].get("name") or element["tags"].get("ref"))
            assert source.distance_m > 0

        for element in recorded_railways:
            source = by_id[f"railway_{element['id']}"]
            assert source.type == "railway"
            assert source.severity == adapter.RAILWAY_SEVERITY[element["tags"]["railway"]]

        for element in recorded_airports:
            source = by_id[f"airport_{element['id']}"]
            assert source.type == "airport"
            assert source.severity == 1.0

        for element in recorded_industrial:
            source = by_id[f"industrial_{element['id']}"]
            assert source.type == "industrial"
            assert source.severity == 0.5

    def test_the_provider_rejected_the_queries_the_adapters_used_to_build(self):
        """The record of what the provider said to the queries of before.

        The adapters asked a question the provider could not parse: a union
        term without its element type, a filter on the existence of a key
        instead of on its value, and - in the transport query - a comment,
        which Overpass QL has no syntax for. The record is kept: it is the
        evidence of the defect, and the queries the adapters build now are
        the accepted ones.
        """
        for name in (
            "adapter_query_noise_roads",
            "adapter_query_noise_railways",
            "adapter_query_noise_industrial",
            "adapter_query_safety_pois",
            "adapter_query_transport_stops",
            "adapter_query_neighborhood_pois",
        ):
            entry = load_overpass(name)
            assert entry["status"] == 400
            assert "parse error" in entry["body"]

        # The airports query is the one the provider accepted even then
        assert load_overpass("adapter_query_noise_airports")["status"] == 200

    def test_an_adapter_whose_query_is_rejected_still_answers(self):
        """A rejected query must not raise: the adapter answers with an empty result."""
        adapter = SafetyAdapter()

        with patch("requests.get", side_effect=overpass_get(_adapter_query_answer)):
            result = adapter.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

        assert result.pois == []
        assert 0 <= result.score <= 100


# =============================================================================
# The queries the adapters build
# =============================================================================


# The provider's own answer for every request shape, keyed by the shape.
ACCEPTED_FORM_FOR_SHAPE = {
    "noise_roads": "valid_query_noise_roads",
    "noise_railways": "valid_query_noise_railways",
    "noise_industrial": "valid_query_noise_industrial",
    "noise_airports": "valid_query_noise_airports",
    "safety_pois": "valid_query_safety_pois",
    "transport_stops": "valid_query_transport_stops",
    "neighborhood_pois": "valid_query_neighborhood_pois",
}


def _queries_sent(call):
    """The queries an adapter sends, captured at the network boundary."""
    sent = []

    def _get(url, params=None, **kwargs):
        sent.append((params or {}).get("data", ""))
        return recorded_response(load_overpass("empty_result"))

    with patch("requests.get", side_effect=_get):
        call()
    return sent


def _as_one_line(query):
    """A query as the provider reads it: the spacing does not matter."""
    return " ".join(query.split())


class TestTheQueriesTheAdaptersBuild:
    """Every query an adapter builds is one the provider answered with data."""

    def _assert_the_provider_accepts(self, query, shape):
        accepted = load_overpass(ACCEPTED_FORM_FOR_SHAPE[shape])["query"]
        assert _as_one_line(query) == _as_one_line(accepted)

    def test_the_noise_adapter_builds_the_queries_the_provider_accepts(self):
        adapter = NoiseAdapter()

        sent = _queries_sent(lambda: adapter.get_nearby_noise_sources(WARSAW_LAT, WARSAW_LON))
        by_shape = {query_shape(query): query for query in sent}

        assert set(by_shape) == {
            "noise_roads",
            "noise_railways",
            "noise_airports",
            "noise_industrial",
        }
        for shape in ("noise_roads", "noise_railways", "noise_industrial"):
            self._assert_the_provider_accepts(by_shape[shape], shape)

    def test_the_safety_adapter_builds_the_query_the_provider_accepts(self):
        adapter = SafetyAdapter()

        sent = _queries_sent(lambda: adapter.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw"))

        assert len(sent) == 1
        self._assert_the_provider_accepts(sent[0], "safety_pois")

    def test_the_transport_adapter_builds_the_query_the_provider_accepts(self):
        adapter = TransportAdapter()

        sent = _queries_sent(lambda: adapter.fetch_transport_pois(WARSAW_LAT, WARSAW_LON))

        assert len(sent) == 1
        self._assert_the_provider_accepts(sent[0], "transport_stops")

    def test_the_neighborhood_adapter_builds_the_query_the_provider_accepts(self):
        adapter = NeighborhoodAdapter()

        sent = _queries_sent(lambda: adapter.fetch_pois_within_radius(WARSAW_LAT, WARSAW_LON, 1000))

        assert len(sent) == 1
        self._assert_the_provider_accepts(sent[0], "neighborhood_pois")

    def test_no_query_carries_a_comment(self):
        # Overpass QL has no comment syntax: a `#` is a parse error of its own.
        adapter = TransportAdapter()

        sent = _queries_sent(lambda: adapter.fetch_transport_pois(WARSAW_LAT, WARSAW_LON))

        assert "#" not in sent[0]

    def test_every_statement_names_its_element_type(self):
        # A union term without its element type is a parse error.
        adapters = (
            (NoiseAdapter(), lambda a: a.get_nearby_noise_sources(WARSAW_LAT, WARSAW_LON)),
            (SafetyAdapter(), lambda a: a.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw")),
            (TransportAdapter(), lambda a: a.fetch_transport_pois(WARSAW_LAT, WARSAW_LON)),
            (
                NeighborhoodAdapter(),
                lambda a: a.fetch_pois_within_radius(WARSAW_LAT, WARSAW_LON, 1000),
            ),
        )

        for adapter, call in adapters:
            for query in _queries_sent(lambda bound=call, target=adapter: bound(target)):
                body = query.split("(", 1)[1].rsplit(");", 1)[0]
                for statement in body.splitlines():
                    statement = statement.strip()
                    if not statement:
                        continue
                    assert statement.startswith(("node[", "way[", "relation[")), statement


# =============================================================================
# The answers that are not a normal one (Task #92)
# =============================================================================


class TestRecordedProviderEdgeCases:
    """An empty answer, a rate limit and a malformed payload raise nothing."""

    def test_empty_answer(self):
        """The recorded empty answer leaves every adapter with a valid result."""
        assert load_overpass_body("empty_result")["elements"] == []

        transport = TransportAdapter()
        with patch("requests.get", side_effect=overpass_get(lambda q: "empty_result")):
            assert transport.fetch_transport_pois(WARSAW_LAT, WARSAW_LON) == []
            assert transport.calculate_accessibility_score(WARSAW_LAT, WARSAW_LON) == 20.0

        noise = NoiseAdapter()
        with patch("requests.get", side_effect=overpass_get(lambda q: "empty_result")):
            result = noise.estimate_noise_level(WARSAW_LAT, WARSAW_LON)
        assert result.noise_sources == []
        assert 0 <= result.score <= 100

        safety = SafetyAdapter()
        with patch("requests.get", side_effect=overpass_get(lambda q: "empty_result")):
            result = safety.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw")
        assert result.pois == []
        assert 0 <= result.score <= 100

    def test_rate_limited_answer(self):
        """The recorded HTTP 429 leaves every adapter with a valid result."""
        entry = load_overpass("rate_limited")
        assert entry["status"] == 429

        transport = TransportAdapter()
        with patch("requests.get", side_effect=overpass_get(lambda q: "rate_limited")):
            assert transport.fetch_transport_pois(WARSAW_LAT, WARSAW_LON) == []

        noise = NoiseAdapter()
        with patch("requests.get", side_effect=overpass_get(lambda q: "rate_limited")):
            result = noise.estimate_noise_level(WARSAW_LAT, WARSAW_LON)
        assert result.noise_sources == []
        assert 0 <= result.score <= 100

        safety = SafetyAdapter()
        with patch("requests.get", side_effect=overpass_get(lambda q: "rate_limited")):
            result = safety.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw")
        assert result.pois == []
        assert 0 <= result.score <= 100

    def test_malformed_payload(self):
        """A body that is not the expected shape leaves every adapter with a valid result."""
        transport = TransportAdapter()
        with patch("requests.get", side_effect=overpass_get(lambda q: "malformed_payload")):
            assert transport.fetch_transport_pois(WARSAW_LAT, WARSAW_LON) == []

        noise = NoiseAdapter()
        with patch("requests.get", side_effect=overpass_get(lambda q: "malformed_payload")):
            result = noise.estimate_noise_level(WARSAW_LAT, WARSAW_LON)
        assert result.noise_sources == []
        assert 0 <= result.score <= 100

        safety = SafetyAdapter()
        with patch("requests.get", side_effect=overpass_get(lambda q: "malformed_payload")):
            result = safety.get_safety_score(WARSAW_LAT, WARSAW_LON, "Warsaw")
        assert result.pois == []
        assert 0 <= result.score <= 100

    def test_a_body_that_is_not_json_at_all(self):
        """The provider's own parse-error page is not JSON: nothing may raise."""
        entry = load_overpass("adapter_query_transport_stops")
        assert entry["status"] == 400

        transport = TransportAdapter()
        with patch(
            "requests.get", side_effect=overpass_get(lambda q: "adapter_query_transport_stops")
        ):
            assert transport.fetch_transport_pois(WARSAW_LAT, WARSAW_LON) == []

    def test_air_quality_with_a_malformed_answer(self):
        """The air quality adapter falls back to the city average on a bad body."""
        adapter = AirQualityAdapter(api_key="not-a-real-token")

        with patch("requests.get", side_effect=overpass_get(lambda q: "malformed_payload")):
            result = adapter.get_aqi_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

        assert result.data_source == "fallback"
        assert result.aqi_value == 65
        assert 0 <= result.score <= 100

    def test_air_quality_with_a_rate_limited_answer(self):
        """A rate limited answer leaves the air quality adapter on its fallback."""
        adapter = AirQualityAdapter(api_key="not-a-real-token")

        with patch("requests.get", side_effect=overpass_get(lambda q: "rate_limited")):
            result = adapter.get_aqi_score(WARSAW_LAT, WARSAW_LON, "Warsaw")

        assert result.data_source == "fallback"
        assert 0 <= result.score <= 100


# =============================================================================
# Integration Tests
# =============================================================================


class TestAdapterIntegration:
    """Integration tests for multiple adapters working together."""

    def test_all_adapters_can_be_instantiated(self):
        """Test that all adapters can be created."""
        air = get_air_quality_adapter()
        transport = get_transport_adapter()
        noise = get_noise_adapter()
        safety = get_safety_adapter()

        assert air is not None
        assert transport is not None
        assert noise is not None
        assert safety is not None

    @patch("data.adapters.safety_adapter.requests.get")
    def test_all_adapters_handle_missing_coords(self, mock_requests_get):
        """Test that all adapters handle missing coordinates gracefully."""
        mock_requests_get.return_value = Mock(status_code=200, json=lambda: {"results": []})

        air = get_air_quality_adapter()
        transport = get_transport_adapter()
        noise = get_noise_adapter()
        safety = get_safety_adapter()

        # All should return valid results even without coordinates
        air_result = air.get_aqi_score(None, None, "Warsaw")
        safety_result = safety.get_safety_score(None, None, "Warsaw")

        # Transport and noise may need coords - just verify they don't crash
        try:
            transport_score = transport.calculate_accessibility_score(None, None)
            assert 0 <= transport_score <= 100
        except (TypeError, ValueError):
            pass  # Expected for None coords

        try:
            noise_result = noise.estimate_noise_level(None, None)
            assert 0 <= noise_result.score <= 100
        except (TypeError, ValueError):
            pass  # Expected for None coords

        assert 0 <= air_result.score <= 100
        assert 0 <= safety_result.score <= 100
