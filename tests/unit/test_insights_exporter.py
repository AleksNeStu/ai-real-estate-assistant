from analytics.market_insights import MarketInsights
from data.schemas import Property, PropertyCollection, PropertyType
from utils.exporters import InsightsExporter


def _sample_props():
    return [
        Property(city="Warsaw", area_sqm=50, price=5000, property_type=PropertyType.APARTMENT),
        Property(city="Krakow", area_sqm=55, price=4400, property_type=PropertyType.APARTMENT),
    ]


def test_export_city_indices_csv_contains_columns():
    coll = PropertyCollection(properties=_sample_props(), total_count=2)
    insights = MarketInsights(coll)
    exp = InsightsExporter(insights)
    csv = exp.export_city_indices_csv()
    assert "city" in csv and "avg_price" in csv


def test_export_monthly_index_json_structure_empty_when_no_timestamps():
    coll = PropertyCollection(properties=_sample_props(), total_count=2)
    insights = MarketInsights(coll)
    exp = InsightsExporter(insights)
    js = exp.export_monthly_index_json("Warsaw")
    assert "monthly_index" in js

