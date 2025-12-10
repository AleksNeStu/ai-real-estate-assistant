import pytest
from data.schemas import Property, PropertyType


class TestGlobalSchema:
    def test_property_extended_fields(self):
        prop = Property(
            id="test#1",
            title="Modern apartment",
            description="Nice flat",
            country="Poland",
            region="Mazowieckie",
            city="Warsaw",
            district="Śródmieście",
            latitude=52.2297,
            longitude=21.0122,
            property_type=PropertyType.APARTMENT,
            rooms=3,
            bathrooms=1,
            area_sqm=60,
            price=6000,
            currency="PLN",
        )
        assert prop.country == "Poland"
        assert prop.region == "Mazowieckie"
        assert prop.city == "Warsaw"
        assert prop.district == "Śródmieście"
        assert prop.latitude == pytest.approx(52.2297)
        assert prop.longitude == pytest.approx(21.0122)
        assert prop.currency == "PLN"
        assert prop.price_per_sqm == pytest.approx(100.0)  # 6000/60

    def test_price_per_sqm_uses_price_when_no_eur(self):
        prop = Property(city="Krakow", area_sqm=50, price=5000)
        assert prop.price_per_sqm == pytest.approx(100.0)

