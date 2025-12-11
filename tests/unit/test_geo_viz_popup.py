from ui.geo_viz import _create_property_popup
from data.schemas import Property, PropertyType, ListingType


def test_popup_includes_listing_type_and_currency_rent():
    p = Property(city="Warsaw", price=5000, rooms=2, property_type=PropertyType.APARTMENT, listing_type=ListingType.RENT, currency="PLN")
    html = _create_property_popup(p)
    assert "Listing:" in html
    assert "PLN" in html
    assert "/month" in html


def test_popup_includes_listing_type_sale_without_month():
    p = Property(city="Krakow", price=95000, rooms=3, property_type=PropertyType.APARTMENT, listing_type=ListingType.SALE, currency="PLN")
    html = _create_property_popup(p)
    assert "Listing:" in html
    assert "PLN" in html
    assert "/month" not in html

