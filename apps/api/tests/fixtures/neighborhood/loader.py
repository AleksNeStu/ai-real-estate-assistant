"""Loader for the recorded neighbourhood provider responses (TaskMaster #92).

The JSON files next to this module hold the providers' own answers, recorded
live on 2026-11-19:

* ``overpass.json``  - the OpenStreetMap Overpass API, one entry per request
  shape the adapters issue (plus the same tag sets written as valid Overpass
  QL, and the provider's rate-limit answer).
* ``waqi_keyless.json`` - the WAQI adapter's OWN keyless answer. It is not an
  upstream payload: no WAQI token exists in this project, so the upstream
  endpoint was never called.

The helpers here turn a recorded entry into a ``requests``-shaped response, so
a test can stub the network boundary and exercise the adapter's own parsing.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from unittest.mock import Mock

import requests

FIXTURE_DIR = Path(__file__).resolve().parent
OVERPASS_FIXTURE = FIXTURE_DIR / "overpass.json"
WAQI_FIXTURE = FIXTURE_DIR / "waqi_keyless.json"


def load_overpass_entries() -> Dict[str, Any]:
    """Return every recorded Overpass response, keyed by request shape."""
    payload = json.loads(OVERPASS_FIXTURE.read_text(encoding="utf-8"))
    entries: Dict[str, Any] = payload["responses"]
    return entries


def load_overpass_meta() -> Dict[str, Any]:
    """Return the header of the Overpass fixture (provider, URL shape, date)."""
    payload = json.loads(OVERPASS_FIXTURE.read_text(encoding="utf-8"))
    meta: Dict[str, Any] = payload["_meta"]
    return meta


def load_overpass(name: str) -> Dict[str, Any]:
    """Return one recorded Overpass response.

    Args:
        name: The request shape, e.g. ``valid_query_transport_stops``.

    Returns:
        The recorded entry: status, note, query and body.

    Raises:
        KeyError: When the fixture holds no such entry.
    """
    entries = load_overpass_entries()
    if name not in entries:
        raise KeyError(f"No recorded Overpass response named {name!r}")
    entry: Dict[str, Any] = entries[name]
    return entry


def load_overpass_body(name: str) -> Any:
    """Return the recorded provider body (parsed JSON, or the raw text)."""
    return load_overpass(name)["body"]


def load_waqi_keyless() -> Dict[str, Any]:
    """Return the WAQI adapter's own keyless answer."""
    payload = json.loads(WAQI_FIXTURE.read_text(encoding="utf-8"))
    answer: Dict[str, Any] = payload
    return answer


def recorded_response(entry: Dict[str, Any]) -> Mock:
    """Turn a recorded entry into a ``requests``-shaped response.

    The response carries the recorded status code, so a recorded HTTP 400 or
    429 raises on ``raise_for_status()`` exactly as the provider's answer did.
    """
    body = entry["body"]
    response = Mock()
    response.status_code = entry["status"]

    if isinstance(body, str):
        response.text = body
        response.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
    else:
        response.json.return_value = body
        response.text = json.dumps(body)

    if entry["status"] >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"{entry['status']} Error for url: {OVERPASS_FIXTURE.name}",
            response=response,
        )
    else:
        response.raise_for_status.return_value = None

    return response


def overpass_get(resolver: Any) -> Callable[..., Mock]:
    """Build a ``requests.get`` replacement that serves recorded answers.

    Args:
        resolver: Either a mapping of a query substring to the name of the
            recorded response that answers it, or a callable that takes the
            outgoing query and returns that name.

    Returns:
        A callable with the ``requests.get`` signature.
    """
    if callable(resolver):

        def _resolve(query: str) -> str:
            return str(resolver(query))

    else:

        def _resolve(query: str) -> str:
            for marker, entry_name in resolver.items():
                if marker in query:
                    return str(entry_name)
            raise AssertionError(f"No recorded response configured for query: {query[:120]}")

    def _get(url: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Mock:
        query = (params or {}).get("data", "")
        return recorded_response(load_overpass(_resolve(query)))

    return _get


GIOS_FIXTURE = FIXTURE_DIR / "gios.json"


def load_gios_payload() -> Dict[str, Any]:
    """Return the whole recorded GIOŚ payload."""
    return json.loads(GIOS_FIXTURE.read_text(encoding="utf-8"))


def load_gios(name: str) -> Dict[str, Any]:
    """Return one recorded GIOŚ response.

    Args:
        name: The name of the recorded entry, e.g. ``data_pm25``.

    Returns:
        The recorded entry: status and body.

    Raises:
        KeyError: When the fixture holds no such entry.
    """
    responses = load_gios_payload()["responses"]
    if name not in responses:
        raise KeyError(f"No recorded GIOŚ response named {name!r}")
    return responses[name]


def load_gios_body(name: str) -> Any:
    """Return the recorded GIOŚ body."""
    return load_gios(name)["body"]


def gios_station() -> Dict[str, Any]:
    """Return the station the recording is about."""
    return load_gios_payload()["station"]


def gios_sensor_ids() -> Dict[str, Any]:
    """Return the sensors of the recorded station, by pollutant code."""
    return load_gios_payload()["sensor_ids"]


def gios_get(
    resolver: Optional[Callable[[str, Dict[str, Any]], str]] = None,
) -> Callable[..., Mock]:
    """Build a ``requests.get`` replacement that serves the recorded GIOŚ answers.

    The recorded station list is one page of the real list — the page that
    carries the Kraków stations — and the pages after it are recorded as the
    empty answers the client reads after them.

    Args:
        resolver: Optional callable that takes the outgoing URL and the
            parameters and returns the name of the recorded response that
            answers it. The default routes every request the way the
            adapter's own requests are shaped.

    Returns:
        A callable with the ``requests.get`` signature.
    """
    sensors = gios_sensor_ids()
    pm25_id = str(sensors.get("PM2.5"))
    pm10_id = str(sensors.get("PM10"))

    def _default(url: str, params: Dict[str, Any]) -> str:
        if "/station/findAll" in url:
            return "stations_page_0" if int(params.get("page", 0)) == 0 else "stations_page_empty"
        if "/station/sensors/" in url:
            return "sensors_station"
        if "/data/getData/" in url:
            if pm25_id in url:
                return "data_pm25"
            if pm10_id in url:
                return "data_pm10"
            raise AssertionError(f"No recorded answer for URL: {url}")
        if "/aqindex/getIndex/" in url:
            return "index_station"
        raise AssertionError(f"No recorded answer for URL: {url}")

    def _get(url: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Mock:
        name = resolver(url, params or {}) if resolver else _default(url, params or {})
        response = Mock()
        response.status_code = 200
        response.json.return_value = load_gios_body(name)
        response.text = json.dumps(load_gios_body(name), ensure_ascii=False)
        response.raise_for_status.return_value = None
        return response

    return _get


def query_shape(query: str) -> str:
    """Name the request shape a query belongs to, whatever its spelling."""
    if 'way["highway"~' in query:
        return "noise_roads"
    if 'way["railway"~' in query:
        return "noise_railways"
    if 'way["landuse"~"^(industrial' in query:
        return "noise_industrial"
    if 'way["aeroway"="aerodrome"]' in query:
        return "noise_airports"
    if 'node["amenity"~"^(police' in query:
        return "safety_pois"
    if 'node["highway"="bus_stop"]' in query:
        return "transport_stops"
    if "school" in query and "restaurant" in query:
        return "neighborhood_pois"
    if "school" in query:
        return "neighborhood_schools"
    if "restaurant" in query:
        return "neighborhood_amenities"
    if "park" in query:
        return "neighborhood_green_spaces"
    raise AssertionError(f"No recorded answer for query: {query[:160]}")


# What the provider answered when the adapter asked with its own query.
ANSWER_FOR_ADAPTER_QUERY = {
    "noise_roads": "adapter_query_noise_roads",
    "noise_railways": "adapter_query_noise_railways",
    "noise_industrial": "adapter_query_noise_industrial",
    "noise_airports": "adapter_query_noise_airports",
    "safety_pois": "adapter_query_safety_pois",
    "transport_stops": "adapter_query_transport_stops",
    "neighborhood_pois": "adapter_query_neighborhood_pois",
    "neighborhood_schools": "adapter_query_neighborhood_schools",
    "neighborhood_amenities": "adapter_query_neighborhood_amenities",
    "neighborhood_green_spaces": "adapter_query_neighborhood_green_spaces",
}

# The same tag sets, written as valid Overpass QL: the answers the adapters
# are mapped against.
VALID_FOR_ADAPTER_QUERY = {
    "noise_roads": "valid_query_noise_roads",
    "noise_railways": "valid_query_noise_railways",
    "noise_industrial": "valid_query_noise_industrial",
    "noise_airports": "valid_query_noise_airports",
    "safety_pois": "valid_query_safety_pois",
    "transport_stops": "valid_query_transport_stops",
    "neighborhood_pois": "valid_query_neighborhood_pois",
    "neighborhood_schools": "valid_query_neighborhood_schools",
    "neighborhood_amenities": "valid_query_neighborhood_amenities",
    "neighborhood_green_spaces": "valid_query_neighborhood_green_spaces",
}


def adapter_query_answer(query: str) -> str:
    """Name the recorded answer for a query the adapter itself builds."""
    return ANSWER_FOR_ADAPTER_QUERY[query_shape(query)]


def valid_query_answer(query: str) -> str:
    """Name the recorded answer for the same tag set in valid Overpass QL."""
    return VALID_FOR_ADAPTER_QUERY[query_shape(query)]
