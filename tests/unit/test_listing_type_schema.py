from data.schemas import Property, ListingType


def test_property_listing_type_default_rent():
    p = Property(city="Warsaw", price=5000, rooms=2)
    assert p.listing_type == ListingType.RENT


def test_property_listing_type_assignment_sale():
    p = Property(city="Krakow", price=95000, rooms=3, listing_type=ListingType.SALE)
    assert p.listing_type == ListingType.SALE
