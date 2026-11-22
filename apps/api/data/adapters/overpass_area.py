"""
The named place: resolved to its boundary, and measured inside it.

A neighbourhood index is asked for a city or a district, and it is asked
for it often without coordinates. The radius queries the adapters own
need a point, and a point invented from the name - a hash dressed as a
measurement - is the failure this module exists to prevent.

Overpass resolves a NAME to the boundary that carries the name, and it
counts the features inside that boundary. So a named place is measured
where it stands, and the measurement carries the boundary it was taken
in. When the place cannot be resolved, or holds none of the features
asked for, the answer is no score and the reason - never a number.

The module owns three things: the filters that can resolve a place, the
query that measures inside the resolved place, and the facts the place
itself carries - its residents and its centre - because a count without a
scale is not a measurement.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from core.security_utils import sanitize_for_log
from data.adapters.overpass_query import (
    build_area_query,
    element_statement,
    tag_regex_filter,
)

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://overpass-api.de/api/interpreter"

# A tag group: the key a feature hangs on, the values of that key and the
# element types the provider answers with. The shape the neighbourhood
# adapter already uses for its radius queries.
TagGroup = Tuple[str, Sequence[str], Sequence[str]]

# The filter that resolved a place, and the facts that place carries.
# Both are per place name and both are stable for the life of the
# process: the provider's answer to the same place does not change
# between two measurements taken seconds apart.
_FILTERS_BY_PLACE: Dict[str, str] = {}
_FACTS_BY_PLACE: Dict[str, "ResolvedArea"] = {}


def area_filters(place_name: str) -> List[str]:
    """
    The filters that can resolve a place name to a boundary, in the order they are tried.

    The first is the common one: an administrative boundary that carries
    the name. The second is the same boundary under its English name,
    because a caller writes "Belgrade" where the map writes "Beograd". The
    third is a place that is not an administrative boundary at all - a
    district, a quarter - which the provider can only answer when the
    place is mapped as a closed way.
    """
    escaped = place_name.replace("\\", "\\\\").replace('"', '\\"')
    return [
        'area["name"="{0}"]["boundary"="administrative"]'.format(escaped),
        'area["name:en"="{0}"]["boundary"="administrative"]'.format(escaped),
        (
            'area["name"="{0}"]["place"~"^(neighbourhood|neighborhood|suburb|quarter|borough)$"]'
        ).format(escaped),
    ]


@dataclass
class ResolvedArea:
    """The boundary a named place resolved to, and what the boundary carries."""

    place_name: str
    filter: str
    area_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    center: Optional[Tuple[float, float]] = None

    @property
    def population(self) -> Optional[int]:
        """
        The residents the boundary claims, read from its own tag.

        A count of amenities is not a measurement without a scale: the
        same number of schools means something very different in a
        village and in a capital. The population tag is the scale the map
        itself carries, and when it is absent the count cannot be
        normalised - which is a reason to return no score, not a reason
        to invent one.
        """
        raw = self.tags.get("population") or self.tags.get("population:total")
        if not raw:
            return None
        try:
            return int(str(raw).replace(" ", "").replace(";", ""))
        except (TypeError, ValueError):
            return None


@dataclass
class AreaMeasurement:
    """What a named place holds, counted inside its own boundary."""

    place_name: str
    elements: List[Dict[str, Any]] = field(default_factory=list)
    area: Optional[ResolvedArea] = None
    error: Optional[str] = None
    query: Optional[str] = None

    @property
    def resolved(self) -> bool:
        """Whether the place was resolved to a boundary the provider knows."""
        return self.area is not None and self.area.area_id is not None


def measure_in_area(
    place_name: str,
    groups: Sequence[TagGroup],
    api_url: Optional[str] = None,
    timeout: int = 60,
) -> AreaMeasurement:
    """
    Count the features of every tag group inside the place the caller named.

    The groups are the adapter's own - a key, the values of that key and
    the element types the provider answers with - so the counts are the
    same counts the radius queries would have produced, only taken inside
    a boundary instead of around a point.

    Every filter that could resolve the place is tried in turn. The
    provider answers a query it cannot parse, or a place it does not
    know, with an error rather than with data; the next filter is tried
    and the last error is carried in the result, so that the caller can
    say what went wrong instead of inventing a number.
    """
    filters = _FILTERS_BY_PLACE.get(place_name)
    candidates = [filters] if filters else area_filters(place_name)

    last_error: Optional[str] = None
    for area_filter in candidates:
        query = build_area_query(area_filter, _statements(groups))
        body, error = _get(query, api_url, timeout)
        if body is None:
            last_error = error
            continue

        elements = [
            element
            for element in body.get("elements", [])
            if element.get("type") != "area" and element.get("tags")
        ]

        facts = load_area_facts(place_name, area_filter, api_url=api_url)
        if not elements and facts.area_id is None:
            # The provider answered, but it knows no boundary under this
            # name: the next filter may still name the same place in the
            # spelling the map uses.
            last_error = "the provider holds no boundary named {0!r}".format(place_name)
            continue

        _FILTERS_BY_PLACE[place_name] = area_filter
        facts.filter = area_filter
        return AreaMeasurement(
            place_name=place_name,
            elements=elements,
            area=facts,
            query=query,
        )

    return AreaMeasurement(
        place_name=place_name,
        error=last_error
        or "the place {0!r} could not be resolved to a boundary".format(place_name),
    )


def load_area_facts(
    place_name: str,
    area_filter: str,
    api_url: Optional[str] = None,
    timeout: int = 30,
) -> ResolvedArea:
    """
    Read the facts the boundary itself carries: its id, its tags, its centre.

    The measurement needs the scale the boundary claims - how many people
    live in it, where its middle is - and the boundary is the only place
    that knows. The answer is best effort by design: when the provider
    does not print the boundary, the measurement still stands and only
    the facts are missing.
    """
    cached = _FACTS_BY_PLACE.get(place_name)
    if cached is not None and cached.filter == area_filter:
        return cached

    query = ("[out:json][timeout:30];\n{area_filter}->.searchArea;\nout tags center;").format(
        area_filter=area_filter
    )

    area = ResolvedArea(place_name=place_name, filter=area_filter)
    body, _error = _get(query, api_url, timeout)
    if body:
        for element in body.get("elements", []):
            if element.get("type") != "area":
                continue
            area.area_id = str(element.get("id", ""))
            area.tags = dict(element.get("tags") or {})
            center = element.get("center") or {}
            if "lat" in center and "lon" in center:
                area.center = (float(center["lat"]), float(center["lon"]))
            break

    _FACTS_BY_PLACE[place_name] = area
    return area


def _statements(groups: Sequence[TagGroup]) -> List[str]:
    """The statements that count every group inside the area."""
    statements: List[str] = []
    for key, values, element_types in groups:
        for element_type in element_types:
            statements.append(
                element_statement(
                    element_type,
                    tag_regex_filter(key, values),
                    "area.searchArea",
                )
            )
    return statements


def _get(
    query: str,
    api_url: Optional[str],
    timeout: int,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Ask the provider, and answer with the body or with the reason there is none."""
    url = api_url or os.getenv("OVERPASS_API_URL") or DEFAULT_API_URL
    try:
        response = requests.get(url, params={"data": query}, timeout=timeout)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            return None, "the provider's answer was not a document"
        return body, None
    except requests.RequestException as exc:
        logger.warning("Overpass area query failed: %s", sanitize_for_log(exc))
        return None, "the provider refused the query: {0}".format(sanitize_for_log(exc))
    except Exception as exc:
        logger.warning("Overpass area answer could not be read: %s", sanitize_for_log(exc))
        return None, "the provider's answer could not be read: {0}".format(sanitize_for_log(exc))
