"""Tests for the official Polish noise register (GIOŚ).

The answers the client reads were recorded live on 2026-11-23 from
``dane.gios.gov.pl`` and are held in
``tests/fixtures/neighborhood/gios_noise.json``: the first page of the
roads, of the railways and of the industry of the Małopolskie voivodeship,
and the empty answer the pages after them carry.

The levels the tests assert are the ones that recording holds.
"""

from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from data.adapters.gios_noise import (
    GIOS_NOISE_ATTRIBUTION,
    GiosNoiseClient,
    quietness_score,
)
from data.adapters.noise_adapter import NoiseAdapter
from tests.fixtures.neighborhood.loader import gios_noise_get, gios_noise_nearest

# The recorded measurement point of the roads, the nearest to Kraków.
ROAD = gios_noise_nearest()["droga"]
ROAD_LAT = float(ROAD["coordWgs84Y"])
ROAD_LON = float(ROAD["coordWgs84X"])
ROAD_DB = float(ROAD["wynikPomiaru"])

# A point far from every recorded measurement.
NOWHERE = (0.0, -140.0)


@pytest.fixture
def client() -> Iterator[GiosNoiseClient]:
    """A client whose network is the recorded answer."""
    with patch("requests.get", gios_noise_get()):
        yield GiosNoiseClient()


# The suite keeps every test away from the register; this file is the one
# that reads it, so the stub of the suite is undone here.
_REAL_GET = GiosNoiseClient._get


@pytest.fixture(autouse=True)
def the_register_is_readable(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(GiosNoiseClient, "_get", _REAL_GET)
    yield


class TestTheVoivodeship:
    def test_it_finds_the_voivodeship_of_a_place(self, client):
        assert client.voivodeships(50.0614, 19.9366)[0] == "MAŁOPOLSKIE"
        assert client.voivodeships(52.2297, 21.0122)[0] == "MAZOWIECKIE"
        assert client.voivodeships(54.3520, 18.6466)[0] == "POMORSKIE"
        assert client.voivodeships(51.1079, 17.0385)[0] == "DOLNOŚLĄSKIE"
        assert client.voivodeships(52.4064, 16.9252)[0] == "WIELKOPOLSKIE"
        assert client.voivodeships(50.2649, 19.0238)[0] == "ŚLĄSKIE"

    def test_a_place_on_a_border_is_asked_its_neighbours_too(self, client):
        candidates = client.voivodeships(50.0614, 19.9366)

        assert len(candidates) > 1
        assert candidates[0] == "MAŁOPOLSKIE"


class TestTheMeasurement:
    def test_it_reads_the_measurement_of_the_point(self, client):
        measurement = client.measurement(ROAD_LAT, ROAD_LON)

        assert measurement is not None
        assert measurement.category == "Droga"
        assert measurement.decibels == pytest.approx(ROAD_DB)
        assert measurement.place == "Niepołomice"
        assert measurement.point_code == ROAD["kodPunktuPomiarowego"]
        assert measurement.distance_km == pytest.approx(0.0, abs=0.01)

    def test_it_carries_the_period_the_level_was_measured_in(self, client):
        measurement = client.measurement(ROAD_LAT, ROAD_LON)

        assert measurement is not None
        assert measurement.period == ROAD["pora"]
        assert measurement.measured_from == ROAD["dataOd"]
        assert measurement.measured_to == ROAD["dataDo"]

    def test_it_names_the_source(self, client):
        measurement = client.measurement(ROAD_LAT, ROAD_LON)

        assert measurement is not None
        assert measurement.attribution == GIOS_NOISE_ATTRIBUTION
        assert "dane.gios.gov.pl" in measurement.attribution

    def test_a_place_the_register_does_not_cover_has_no_measurement(self, client):
        assert client.measurement(*NOWHERE) is None

    def test_the_records_are_read_once(self, client):
        """The records of a category are cached, so a second place is free."""
        get = MagicMock(side_effect=gios_noise_get())
        with patch("requests.get", get):
            client.measurement(ROAD_LAT, ROAD_LON)
            first = len(get.call_args_list)
            client.measurement(ROAD_LAT, ROAD_LON)

        assert first > 0
        assert len(get.call_args_list) == first


class TestTheQuietness:
    def test_the_quietest_level_is_the_best_score(self):
        assert quietness_score(40.0) == 100.0

    def test_the_loudest_level_is_the_worst_score(self):
        assert quietness_score(80.0) == 0.0

    def test_a_level_between_the_two_is_between_the_scores(self):
        # 62.2 dB is 22.2 above the quiet end, and the scale runs 40 dB to 80 dB.
        assert quietness_score(62.2) == pytest.approx(44.5)

    def test_a_level_below_the_scale_is_the_best_score(self):
        assert quietness_score(10.0) == 100.0

    def test_a_level_above_the_scale_is_the_worst_score(self):
        assert quietness_score(120.0) == 0.0


class TestTheAdapter:
    def test_the_official_register_is_the_source(self, client):
        adapter = NoiseAdapter(gios_client=client)

        result = adapter.estimate_noise_level(ROAD_LAT, ROAD_LON)

        assert result.data_source == "gios_noise_register"
        assert result.estimated_db == pytest.approx(ROAD_DB)
        assert result.confidence == 1.0

    def test_the_answer_carries_the_attribution(self, client):
        adapter = NoiseAdapter(gios_client=client)

        result = adapter.estimate_noise_level(ROAD_LAT, ROAD_LON)

        assert result.attribution == GIOS_NOISE_ATTRIBUTION
        assert result.measured_place == "Niepołomice"
        assert result.measured_category == "Droga"
        assert result.measured_at == ROAD["dataOd"]

    def test_the_level_becomes_the_score(self, client):
        adapter = NoiseAdapter(gios_client=client)

        result = adapter.estimate_noise_level(ROAD_LAT, ROAD_LON)

        assert result.score == pytest.approx(44.5, abs=0.05)

    def test_the_measurement_point_is_the_noise_source(self, client):
        adapter = NoiseAdapter(gios_client=client)

        result = adapter.estimate_noise_level(ROAD_LAT, ROAD_LON)

        assert len(result.noise_sources) == 1
        source = result.noise_sources[0]
        assert source.type == NoiseAdapter.NOISE_TYPE_ROAD
        assert source.name == "Niepołomice"
        assert source.distance_m == pytest.approx(0.0, abs=10.0)

    def test_the_estimate_is_the_fallback_where_the_register_has_nothing(self, client):
        adapter = NoiseAdapter(gios_client=client)

        with patch.object(client, "measurement", return_value=None):
            with patch.object(NoiseAdapter, "get_nearby_noise_sources", return_value=[]):
                with patch.object(NoiseAdapter, "calculate_noise_score", return_value=95.0):
                    result = adapter.estimate_noise_level(*NOWHERE)

        assert result.data_source == "overpass_api"
        assert result.attribution is None

    def test_a_register_that_cannot_be_read_falls_back_too(self, client):
        adapter = NoiseAdapter(gios_client=client)

        with patch.object(client, "measurement", side_effect=RuntimeError("no answer")):
            with patch.object(NoiseAdapter, "get_nearby_noise_sources", return_value=[]):
                with patch.object(NoiseAdapter, "calculate_noise_score", return_value=95.0):
                    result = adapter.estimate_noise_level(*NOWHERE)

        assert result.data_source == "overpass_api"
