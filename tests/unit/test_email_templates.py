from notifications.email_templates import (
    PriceDropTemplate,
    NewPropertyTemplate,
    DigestTemplate,
    TestEmailTemplate,
    MarketUpdateTemplate,
)
from data.schemas import Property, PropertyType


def make_prop(pid: str, city: str, price: float, rooms: float) -> Property:
    return Property(
        id=pid,
        city=city,
        price=price,
        rooms=rooms,
        bathrooms=1,
        area_sqm=55,
        property_type=PropertyType.APARTMENT,
        has_parking=True,
        has_balcony=True,
        is_furnished=True,
    )


def test_price_drop_template_render():
    p = make_prop("p1", "Krakow", 900, 2)
    subject, html = PriceDropTemplate.render({
        "property": p,
        "old_price": 1000,
        "new_price": 900,
        "percent_drop": 10.0,
        "savings": 100,
    }, user_name="Alex")
    assert "Price Drop" in subject
    assert "Krakow" in subject
    assert "You Save" in html


def test_new_property_template_render_multiple():
    props = [
        make_prop("p1", "Krakow", 900, 2),
        make_prop("p2", "Warsaw", 1200, 3),
        make_prop("p3", "Gdansk", 800, 2),
    ]
    subject, html = NewPropertyTemplate.render("Family Flats", props, max_display=2, user_name="Alex")
    assert "New Properties" in subject
    assert "Family Flats" in subject
    assert "and 1 more" in html


def test_digest_template_render():
    subject, html = DigestTemplate.render("daily", {
        "new_properties": 5,
        "price_drops": 2,
        "avg_price": 950,
        "total_properties": 120,
        "average_price": 980,
        "trending_cities": ["Krakow", "Warsaw"],
        "saved_searches": [{"name": "Center", "new_matches": 3}],
    }, user_name="Alex")
    assert "Real Estate Digest" in subject
    assert "Trending Cities" in html
    assert "Your Saved Searches" in html


def test_test_email_template_render():
    subject, html = TestEmailTemplate.render(user_name="Alex")
    assert "Test Email" in subject
    assert "Manage Notification Preferences" in html


def test_market_update_template_render():
    subject, html = MarketUpdateTemplate.render({
        "title": "Q4 Trends",
        "summary": "Overview of Q4 market movements",
        "insights": [{"icon": "•", "text": "Avg price up 3%"}],
    }, user_name="Alex")
    assert "Market Update" in subject
    assert "Key Insights" in html

