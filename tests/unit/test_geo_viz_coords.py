from ui.geo_viz import get_property_coords
from data.schemas import Property, PropertyCollection


def test_get_property_coords_prefers_lat_lon():
    p = Property(city="Warsaw", latitude=52.23, longitude=21.01, price=5000)
    lat, lon = get_property_coords(p)
    assert (lat, lon) == (52.23, 21.01)


def test_get_property_coords_falls_back_to_city_center():
    # No lat/lon: expect city center fallback (approx)
    p = Property(city="Krakow", price=4000)
    lat, lon = get_property_coords(p)
    # Krakow center from CITY_COORDINATES is (50.0647, 19.9450)
    assert abs(lat - 50.0647) < 0.1
    assert abs(lon - 19.9450) < 0.1

