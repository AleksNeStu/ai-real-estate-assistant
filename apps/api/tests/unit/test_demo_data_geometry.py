"""The demo catalogue has to look like a city, not like a scatter.

The comparable search scores the distance between two listings. While the
generator scattered the listings around the centre of the CITY, two listings of
one district stood seven kilometres apart, scored nothing for the location and
left the CMA without a single comparable. A listing belongs to its district.
"""

import math

from alembic.demo_data_generator import (
    CITIES,
    DISTRICT_CENTRES,
    district_centre,
    listing_coordinates,
)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance - the measure the comparable search uses."""
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def test_every_district_of_every_city_has_a_centre():
    """No district falls back to the centre of its city."""
    for city, city_data in CITIES.items():
        for district in city_data["districts"]:
            assert district in DISTRICT_CENTRES[city], f"{city} / {district} has no centre"


def test_a_listing_stays_inside_its_district():
    """A listing stands near the centre of its district, not at the edge of the city."""
    for city, city_data in CITIES.items():
        for district in city_data["districts"]:
            centre_lat, centre_lng = district_centre(city, district)
            for _ in range(50):
                lat, lng = listing_coordinates(city, district)
                assert _distance_km(centre_lat, centre_lng, lat, lng) < 2.0


def test_two_listings_of_one_district_stand_close_to_each_other():
    """Neighbours of one district are neighbours on the map as well."""
    for city, city_data in CITIES.items():
        for district in city_data["districts"]:
            for _ in range(50):
                lat1, lng1 = listing_coordinates(city, district)
                lat2, lng2 = listing_coordinates(city, district)
                assert _distance_km(lat1, lng1, lat2, lng2) < 3.0


def test_the_districts_of_one_city_stay_apart():
    """The map shows districts as clusters, not as one blob."""
    for city, city_data in CITIES.items():
        centres = [district_centre(city, district) for district in city_data["districts"]]
        for index, (lat1, lng1) in enumerate(centres):
            for lat2, lng2 in centres[index + 1 :]:
                assert _distance_km(lat1, lng1, lat2, lng2) > 0.5
