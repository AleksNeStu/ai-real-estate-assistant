import pandas as pd
from analytics.market_insights import MarketInsights
from data.schemas import Property, PropertyCollection, PropertyType


def _props_for_cities():
    return [
        Property(city="Warsaw", area_sqm=50, price=5000, property_type=PropertyType.APARTMENT, latitude=52.23, longitude=21.01),
        Property(city="Warsaw", area_sqm=60, price=6600, property_type=PropertyType.APARTMENT, latitude=52.24, longitude=21.02),
        Property(city="Krakow", area_sqm=55, price=4400, property_type=PropertyType.APARTMENT, latitude=50.06, longitude=19.94),
        Property(city="Krakow", area_sqm=45, price=3600, property_type=PropertyType.APARTMENT, latitude=50.07, longitude=19.95),
    ]


def test_city_price_indices_basic():
    coll = PropertyCollection(properties=_props_for_cities(), total_count=4)
    insights = MarketInsights(coll)
    df = insights.get_city_price_indices()
    cities = set(df['city'].tolist())
    assert {'Warsaw','Krakow'} == cities
    warsaw = df[df['city']=='Warsaw'].iloc[0]
    assert warsaw['count'] == 2
    assert round(warsaw['avg_price'], 2) == round((5000+6600)/2, 2)


def test_filter_by_geo_radius_selects_close_points():
    coll = PropertyCollection(properties=_props_for_cities(), total_count=4)
    insights = MarketInsights(coll)
    df = insights.filter_by_geo_radius(52.23, 21.01, 5.0)
    assert df['city'].nunique() == 1
    assert df['city'].iloc[0] == 'Warsaw'

