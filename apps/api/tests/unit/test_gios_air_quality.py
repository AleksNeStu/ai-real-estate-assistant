"""Tests for the official Polish air quality register (GIOŚ).

The answers the client reads were recorded live on 2026-11-23 from
``api.gios.gov.pl`` and are held in
``tests/fixtures/neighborhood/gios.json``: the page of the station list that
carries the Kraków stations, the sensors of one station, the hourly
measurements of its PM2.5 and PM10 sensors, and the official index of the
station.

The readings the tests assert are the ones that recording holds: the mean of
the last twenty-four hourly measurements of each sensor, and the official
index of 2 - "Umiarkowany".
"""

from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from data.adapters.air_quality_adapter import AirQualityAdapter
from data.adapters.gios_air_quality import (
    GIOS_ATTRIBUTION,
    GiosAirQualityClient,
    us_aqi,
    us_aqi_from_concentrations,
)
from tests.fixtures.neighborhood.loader import gios_get, gios_sensor_ids, gios_station

# The Kraków station of the recording.
STATION = gios_station()
STATION_LAT = float(STATION["WGS84 φ N"])
STATION_LON = float(STATION["WGS84 λ E"])

# The readings the recording holds.
PM25_MEAN = 10.541666666666666
PM10_MEAN = 14.129166666666665
OFFICIAL_INDEX = 2
OFFICIAL_CATEGORY = "Umiarkowany"


@pytest.fixture
def client() -> Iterator[GiosAirQualityClient]:
    """A client whose network is the recorded answer."""
    with patch("requests.get", gios_get()):
        yield GiosAirQualityClient()


# The suite keeps every test away from the register; this file is the one
# that reads it, so the stub of the suite is undone here.
_REAL_GET = GiosAirQualityClient._get


@pytest.fixture(autouse=True)
def the_register_is_readable(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(GiosAirQualityClient, "_get", _REAL_GET)
    yield


class TestTheConversionToAnIndex:
    def test_a_concentration_at_the_floor_of_a_band_is_the_floor_of_the_index(self):
        assert us_aqi(0.0, ((0.0, 9.0, 0, 50),)) == 0

    def test_a_concentration_at_the_ceiling_of_a_band_is_the_ceiling_of_the_index(self):
        assert us_aqi(9.0, ((0.0, 9.0, 0, 50),)) == 50

    def test_a_concentration_inside_a_band_is_inside_the_index(self):
        # 35.4 µg/m³ of PM2.5 is the top of the 51-100 band.
        assert us_aqi(35.4, ((0.0, 9.0, 0, 50), (9.1, 35.4, 51, 100))) == 100

    def test_the_bands_do_not_leave_a_gap(self):
        # 35.5 µg/m³ is the first of the next band, so it is not the same index.
        assert (
            us_aqi(35.5, ((0.0, 9.0, 0, 50), (9.1, 35.4, 51, 100), (35.5, 55.4, 101, 150))) == 101
        )

    def test_a_concentration_above_the_table_is_the_ceiling_of_the_index(self):
        assert us_aqi(5000.0, ((0.0, 9.0, 0, 50),)) == 50

    def test_no_concentration_is_no_index(self):
        assert us_aqi(None, ((0.0, 9.0, 0, 50),)) is None

    def test_the_index_is_the_worse_of_the_two_dust_fractions(self):
        # A fine dust reading is worse than a coarse one, so it is the answer.
        aqi = us_aqi_from_concentrations(pm25=35.5, pm10=10.0)

        assert aqi == 101

    def test_neither_fraction_is_no_index(self):
        assert us_aqi_from_concentrations(None, None) is None


class TestTheCatalogue:
    def test_it_reads_the_stations_of_the_register(self, client):
        stations = client.stations()

        assert stations
        assert any(station.city == "Kraków" for station in stations)

    def test_the_stations_carry_their_coordinates(self, client):
        station = client.nearest_station(STATION_LAT, STATION_LON)

        assert station is not None
        assert station.name == "Kraków, Aleja Krasińskiego"
        assert station.latitude == pytest.approx(STATION_LAT)
        assert station.longitude == pytest.approx(STATION_LON)

    def test_a_place_without_a_station_has_none(self, client):
        # A point in the middle of the Pacific, far from every Polish station.
        assert client.nearest_station(0.0, -140.0) is None

    def test_the_station_list_is_read_once(self, client):
        """The list may be fetched twice a minute, so it is cached for a day."""
        get = MagicMock(side_effect=gios_get())
        with patch("requests.get", get):
            client.stations()
            first = len(get.call_args_list)
            client.stations()

        assert first > 0
        assert len(get.call_args_list) == first


class TestTheMeasurement:
    def test_it_reads_the_readings_of_the_station(self, client):
        measurement = client.measurement(STATION_LAT, STATION_LON)

        assert measurement is not None
        assert measurement.pm25 == pytest.approx(PM25_MEAN)
        assert measurement.pm10 == pytest.approx(PM10_MEAN)

    def test_it_carries_the_official_index(self, client):
        measurement = client.measurement(STATION_LAT, STATION_LON)

        assert measurement is not None
        assert measurement.index_value == OFFICIAL_INDEX
        assert measurement.index_category == OFFICIAL_CATEGORY

    def test_it_names_the_source(self, client):
        measurement = client.measurement(STATION_LAT, STATION_LON)

        assert measurement is not None
        assert measurement.attribution == GIOS_ATTRIBUTION
        assert "GIOŚ" in measurement.attribution

    def test_a_place_without_a_station_has_no_measurement(self, client):
        assert client.measurement(0.0, -140.0) is None


class TestTheAdapter:
    def test_the_official_register_is_the_source(self, client):
        adapter = AirQualityAdapter(gios_client=client)

        result = adapter.get_aqi_score(STATION_LAT, STATION_LON)

        assert result.data_source == "gios"
        assert result.pm25 == pytest.approx(PM25_MEAN)
        assert result.pm10 == pytest.approx(PM10_MEAN)

    def test_the_answer_carries_the_attribution(self, client):
        adapter = AirQualityAdapter(gios_client=client)

        result = adapter.get_aqi_score(STATION_LAT, STATION_LON)

        assert result.attribution == GIOS_ATTRIBUTION
        assert result.station_name == "Kraków, Aleja Krasińskiego"

    def test_the_answer_carries_the_official_index(self, client):
        adapter = AirQualityAdapter(gios_client=client)

        result = adapter.get_aqi_score(STATION_LAT, STATION_LON)

        assert result.official_index == OFFICIAL_INDEX
        assert result.official_category == OFFICIAL_CATEGORY

    def test_the_reading_becomes_an_index(self, client):
        adapter = AirQualityAdapter(gios_client=client)

        result = adapter.get_aqi_score(STATION_LAT, STATION_LON)

        # PM2.5 of 10.54 µg/m³ is the 54th of the US AQI; PM10 of 14.13 is the
        # 13th, and the worse of the two is the answer.
        assert result.aqi_value == 54

    def test_the_register_answers_before_the_keyed_source(self, client):
        adapter = AirQualityAdapter(api_key="a-token", gios_client=client)

        with patch.object(adapter, "_fetch_from_api") as waqi:
            result = adapter.get_aqi_score(STATION_LAT, STATION_LON)

        assert result.data_source == "gios"
        waqi.assert_not_called()

    def test_the_keyed_source_answers_when_the_register_has_nothing(self, client):
        adapter = AirQualityAdapter(api_key="a-token", gios_client=client)

        with patch.object(adapter, "_fetch_from_api") as waqi:
            waqi.return_value = adapter._get_fallback_result("Kraków")
            result = adapter.get_aqi_score(0.0, -140.0)

        assert result.data_source == "fallback"
        waqi.assert_called_once()

    def test_a_place_the_register_does_not_cover_falls_back(self, client):
        adapter = AirQualityAdapter(gios_client=client)

        result = adapter.get_aqi_score(0.0, -140.0, "Kraków")

        assert result.data_source == "fallback"
        assert result.confidence == 0.5

    def test_the_status_names_the_default_source(self, client):
        adapter = AirQualityAdapter(gios_client=client)

        status = adapter.get_status()

        assert status["default_source"] == "gios"
        assert "api.gios.gov.pl" in status["default_source_endpoint"]

    def test_the_sensor_of_a_pollutant_is_the_one_that_measures_it(self, client):
        sensors = client.sensors(int(STATION["Identyfikator stacji"]))

        codes = {sensor.get("Wskaźnik - kod") for sensor in sensors}
        assert "PM2.5" in codes
        assert "PM10" in codes
        assert gios_sensor_ids()["PM2.5"] in {
            sensor.get("Identyfikator stanowiska") for sensor in sensors
        }
