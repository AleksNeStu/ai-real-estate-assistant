from datetime import datetime, timedelta
from analytics.market_insights import MarketInsights
from data.schemas import Property, PropertyCollection, PropertyType


def _make_series(city, base, months):
    now = datetime.now()
    props = []
    for i in range(months):
        dt = now - timedelta(days=30*(months-i))
        price = base + i*50
        props.append(Property(city=city, area_sqm=50, price=price, property_type=PropertyType.APARTMENT, scraped_at=dt))
    return props


def test_get_cities_yoy_latest_rows():
    warsaw = _make_series("Warsaw", 5000, 14)
    krakow = _make_series("Krakow", 4000, 14)
    props = warsaw + krakow
    coll = PropertyCollection(properties=props, total_count=len(props))
    insights = MarketInsights(coll)
    df = insights.get_cities_yoy(["Warsaw","Krakow"])
    assert set(df['city'].tolist()) == {"Warsaw","Krakow"}
    assert 'yoy_pct' in df.columns

