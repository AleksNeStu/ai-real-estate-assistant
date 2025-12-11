from analytics.market_insights import MarketInsights
from data.schemas import Property, PropertyCollection, PropertyType
from utils.exporters import InsightsExporter


def test_generate_digest_markdown_has_sections():
    props = [
        Property(city="Warsaw", area_sqm=50, price=5000, property_type=PropertyType.APARTMENT),
        Property(city="Krakow", area_sqm=55, price=4400, property_type=PropertyType.APARTMENT),
    ]
    coll = PropertyCollection(properties=props, total_count=len(props))
    insights = MarketInsights(coll)
    exp = InsightsExporter(insights)
    md = exp.generate_digest_markdown()
    assert "# Expert Digest" in md
    assert "## City Price Indices" in md
    assert "## YoY — Top Gainers" in md
    assert "## YoY — Top Decliners" in md

