from datetime import datetime, timedelta
from analytics.market_insights import MarketInsights
from data.schemas import Property, PropertyCollection, PropertyType


def test_monthly_index_moving_average_and_anomaly():
    now = datetime.now()
    props = []
    # 11 normal months around 5000
    for i in range(11):
        props.append(Property(city="Warsaw", area_sqm=50, price=5000 + (i % 3)*50, property_type=PropertyType.APARTMENT, scraped_at=now - timedelta(days=30*(11-i))))
    # 1 outlier month
    props.append(Property(city="Warsaw", area_sqm=50, price=8000, property_type=PropertyType.APARTMENT, scraped_at=now))

    coll = PropertyCollection(properties=props, total_count=len(props))
    insights = MarketInsights(coll)
    df = insights.get_monthly_price_index(city="Warsaw", window=3, detect_anomalies=True, z_threshold=2.0)
    assert 'avg_price_ma' in df.columns
    assert 'anomaly' in df.columns
    # Expect at least one anomaly (the outlier)
    assert df['anomaly'].any()

