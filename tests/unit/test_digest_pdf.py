from analytics.market_insights import MarketInsights
from data.schemas import Property, PropertyCollection, PropertyType
from utils.exporters import InsightsExporter


def test_generate_digest_pdf_starts_with_pdf_header():
    props = [
        Property(city="Warsaw", area_sqm=50, price=5000, property_type=PropertyType.APARTMENT),
        Property(city="Krakow", area_sqm=55, price=4400, property_type=PropertyType.APARTMENT),
    ]
    coll = PropertyCollection(properties=props, total_count=len(props))
    insights = MarketInsights(coll)
    exp = InsightsExporter(insights)
    buf = exp.generate_digest_pdf()
    data = buf.getvalue()
    assert data[:4] == b"%PDF"

