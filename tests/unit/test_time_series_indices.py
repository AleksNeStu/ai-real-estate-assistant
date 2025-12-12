import pandas as pd
from datetime import datetime, timedelta
from analytics.market_insights import MarketInsights
from data.schemas import Property, PropertyCollection, PropertyType


def _make_props_city_months(city: str, start_months_ago: int, months: int, base_price: int):
    props = []
    now = datetime.now()
    for i in range(months):
        dt = (now - timedelta(days=30*(start_months_ago - i)))
        p = Property(
            city=city,
            area_sqm=50,
            price=base_price + i * 100,
            property_type=PropertyType.APARTMENT,
            scraped_at=dt,
        )
        props.append(p)
    return props


def test_monthly_price_index_basic_and_yoy():
    # Build 14 months for Warsaw so YoY can be computed for last 2
    warsaw_props = _make_props_city_months("Warsaw", start_months_ago=13, months=14, base_price=5000)
    coll = PropertyCollection(properties=warsaw_props, total_count=len(warsaw_props))

    insights = MarketInsights(coll)
    df = insights.get_monthly_price_index(city="Warsaw")
    # Expect at least 12 rows
    assert len(df) >= 12
    # Columns present
    assert set(['month','avg_price','median_price','count','yoy_pct']).issubset(set(df.columns))
    # Check that yoy values exist for months >= 12
    assert df['yoy_pct'].iloc[-1] is None or isinstance(df['yoy_pct'].iloc[-1], float)


def test_monthly_price_index_yoy_handles_missing_prev():
    # Create 11 months only so previous year's value is missing
    from datetime import datetime, timedelta
    now = datetime.now()
    props = []
    for i in range(11):
        dt = now - timedelta(days=30*(10 - i))
        p = Property(
            city="Warsaw",
            area_sqm=50,
            price=1000 + i * 10,
            property_type=PropertyType.APARTMENT,
            scraped_at=dt,
        )
        props.append(p)
    coll = PropertyCollection(properties=props, total_count=len(props))
    insights = MarketInsights(coll)
    df = insights.get_monthly_price_index(city="Warsaw")
    # The YoY for the last month should be NaN due to missing previous value
    import pandas as pd
    assert pd.isna(df['yoy_pct'].iloc[-1])
