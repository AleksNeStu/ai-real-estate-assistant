"""Tests for valuing a flat from the registered sales."""

from datetime import date

import pytest

from data.rcn.rcn_models import RCNAddress, RCNTransaction
from services.rcn_valuation import (
    ValuationSubject,
    normalize_text,
    select_comparables,
    value_transactions,
)

TODAY = date(2026, 11, 21)


def _sale(
    street="TOPOLOWA",
    city="KRAKÓW",
    area=50.0,
    price=650000.0,
    days_ago=90,
    market="rynekWtorny",
    rooms=2,
    floor=3,
    number="47",
):
    return RCNTransaction(
        external_id=f"{street}-{number}-{days_ago}",
        teryt="1261",
        address=RCNAddress(city=city, street=street, number=number),
        area_sqm=area,
        price=price,
        transaction_date=TODAY - __import__("datetime").timedelta(days=days_ago),
        market=market,
        rooms=rooms,
        floor=floor,
        deed_reference="1234/2026",
    )


class TestNormalizeText:
    def test_folds_case_and_diacritics(self):
        assert normalize_text("Kraków") == "KRAKOW"
        assert normalize_text("  topolowa ") == "TOPOLOWA"


class TestSelectComparables:
    def test_takes_the_street_it_was_asked_for(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        sales = [
            _sale(street="TOPOLOWA", days_ago=30 + index, number=str(index)) for index in range(10)
        ] + [
            _sale(street="RACIBORSKA", days_ago=30 + index, number=str(index))
            for index in range(10)
        ]

        selected, _ = select_comparables(sales, subject, TODAY)

        assert len(selected) == 10
        assert all(sale.address.street == "TOPOLOWA" for sale in selected)

    def test_takes_only_the_secondary_market(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        sales = [
            _sale(days_ago=30),
            _sale(days_ago=60),
            _sale(days_ago=90),
            _sale(days_ago=120),
            _sale(days_ago=150),
            _sale(days_ago=180, market="rynekPierwotny"),
        ]

        selected, _ = select_comparables(sales, subject, TODAY)

        assert all(sale.market == "rynekWtorny" for sale in selected)

    def test_leaves_out_the_deeds_older_than_the_window(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50, months=12)
        sales = [_sale(days_ago=30), _sale(days_ago=400)]

        selected, _ = select_comparables(sales, subject, TODAY)

        assert len(selected) == 1

    def test_widens_the_window_when_there_are_too_few_sales(self):
        subject = ValuationSubject(city="Kraków", area_sqm=50, months=6)
        sales = [_sale(days_ago=200), _sale(days_ago=260)]

        selected, notes = select_comparables(sales, subject, TODAY)

        assert len(selected) == 2
        assert any("widened" in note for note in notes)

    def test_falls_back_to_the_city_when_the_street_holds_nothing(self):
        subject = ValuationSubject(city="Kraków", street="Nieistniejaca", area_sqm=50)

        selected, notes = select_comparables([_sale()], subject, TODAY)

        assert len(selected) == 1
        assert any("fell back to the whole city" in note for note in notes)

    def test_widens_the_area_when_nothing_matches_the_size(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        sales = [_sale(area=120.0)]

        selected, notes = select_comparables(sales, subject, TODAY)

        assert len(selected) == 1
        assert any("widened to every size" in note for note in notes)

    def test_a_thin_street_falls_back_to_the_city(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        sales = [_sale(street="TOPOLOWA")] + [
            _sale(street="RACIBORSKA", days_ago=30 + index, number=str(index))
            for index in range(10)
        ]

        selected, notes = select_comparables(sales, subject, TODAY)

        # The whole city: the one sale on the street plus the ten elsewhere.
        assert len(selected) == 11
        assert any("fell back to the whole city" in note for note in notes)

    def test_ignores_a_city_that_sold_nothing(self):
        subject = ValuationSubject(city="Gdańsk", street="Długa", area_sqm=50)

        selected, notes = select_comparables([_sale()], subject, TODAY)

        assert selected == []
        assert notes


class TestValueTransactions:
    def test_values_a_flat_from_its_neighbours(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        sales = [
            _sale(area=50.0, price=650000.0, days_ago=30),
            _sale(area=48.0, price=600000.0, days_ago=60),
            _sale(area=52.0, price=700000.0, days_ago=90),
            _sale(area=49.0, price=640000.0, days_ago=120),
            _sale(area=51.0, price=660000.0, days_ago=150),
        ]

        result = value_transactions(sales, subject, TODAY)

        assert result.sample_size == 5
        assert result.price_per_sqm_median == pytest.approx(13000.0)
        assert result.estimate == pytest.approx(650000.0)
        low, estimate, high = result.low, result.estimate, result.high
        assert low is not None and estimate is not None and high is not None
        assert low <= estimate <= high
        assert result.currency == "PLN"
        assert result.source == "rcn"
        assert result.confidence == "low"

    def test_the_result_says_what_it_rests_on(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        sales = [_sale(days_ago=30), _sale(days_ago=60)]

        result = value_transactions(sales, subject, TODAY)

        assert result.comparison_area == "Topolowa, Kraków"
        assert result.period_start is not None and result.period_end is not None
        assert any("registered sale" in note for note in result.notes)
        assert all("based on" not in note.lower() for note in result.notes) is False

    def test_a_thin_sample_says_so(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)

        result = value_transactions([_sale()], subject, TODAY)

        assert result.confidence == "low"
        assert result.sample_size == 1

    def test_no_sales_means_no_number(self):
        subject = ValuationSubject(city="Gdańsk", street="Długa", area_sqm=50)

        result = value_transactions([_sale()], subject, TODAY)

        assert result.estimate is None
        assert result.has_value is False
        assert result.sample_size == 0
        assert result.comparables == []

    def test_the_comparables_are_the_sales_behind_the_number(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        sales = [_sale(days_ago=30, number="47"), _sale(days_ago=60, number="48")]

        result = value_transactions(sales, subject, TODAY)

        assert len(result.comparables) == 2
        assert result.comparables[0].deed_reference == "1234/2026"
        assert result.comparables[0].price_per_sqm == pytest.approx(
            result.comparables[0].price / result.comparables[0].area_sqm
        )

    def test_an_outlier_does_not_move_the_median(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        sales = [
            _sale(area=50.0, price=650000.0, days_ago=30),
            _sale(area=50.0, price=660000.0, days_ago=60),
            _sale(area=50.0, price=640000.0, days_ago=90),
            _sale(area=50.0, price=9000000.0, days_ago=120),
        ]

        result = value_transactions(sales, subject, TODAY)

        # Four sales: the median is the mean of the two middle prices per square
        # metre (13 000 and 13 200), not the 180 000 the outlier carries.
        assert result.price_per_sqm_median == pytest.approx(13100.0)


class TestTheQuartiles:
    def test_one_sale_has_no_spread(self):
        from services.rcn_valuation import _quantiles

        low, median, high = _quantiles([13100.0])

        assert (low, median, high) == (13100.0, 13100.0, 13100.0)

    def test_no_sale_has_no_quartiles(self):
        from services.rcn_valuation import _quantiles

        assert _quantiles([]) == (None, None, None)


class TestTheConfidence:
    def test_a_thick_comparison_is_high_confidence(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        sales = [_sale(days_ago=30 + index, number=str(index)) for index in range(20)]

        result = value_transactions(sales, subject, TODAY)

        assert result.sample_size == 20
        assert result.confidence == "high"


class TestTheAreaBand:
    def test_a_flat_without_an_area_has_no_size_band(self):
        from services.rcn_valuation import _filter_by_area, _size_band

        subject = ValuationSubject(city="Kraków")

        assert _filter_by_area([_sale()], subject) == []
        assert _size_band(subject) == "any size"


class TestTheEdgesOfTheComparison:
    def test_an_address_without_a_city_matches_everything(self):
        subject = ValuationSubject(city="", street="")

        selected, _ = select_comparables([_sale(days_ago=30)], subject, TODAY)

        assert len(selected) == 1

    def test_a_market_that_sold_nothing_is_named(self):
        subject = ValuationSubject(city="Kraków", market="rynekNowy")
        sales = [_sale(days_ago=30 + index, number=str(index)) for index in range(10)]

        _selected, notes = select_comparables(sales, subject, TODAY)

        assert any("every registered sale was used" in note for note in notes)

    def test_deeds_older_than_the_window_leave_no_comparison(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        # Older than the widest window the comparison will open.
        sales = [_sale(days_ago=2200, number=str(index)) for index in range(3)]

        selected, notes = select_comparables(sales, subject, TODAY)

        assert selected == []
        assert any("No sales of flats are registered" in note for note in notes)

    def test_the_comparison_narrows_to_the_flats_with_the_same_rooms(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50, rooms=2)
        sales = [_sale(days_ago=30 + index, number=str(index), rooms=2) for index in range(10)] + [
            _sale(days_ago=30 + index, number=f"b{index}", rooms=3) for index in range(10)
        ]

        selected, notes = select_comparables(sales, subject, TODAY)

        assert len(selected) == 10
        assert all(sale.rooms == 2 for sale in selected)
        assert any("Flats with 2 rooms." in note for note in notes)

    def test_the_window_widens_when_the_city_holds_too_little(self):
        subject = ValuationSubject(city="Kraków", street="Topolowa", area_sqm=50)
        # Seven sales inside the window and five older ones, all on another
        # street: the comparison rests on the city, and the city holds too
        # little until the window opens.
        recent = [
            _sale(street="RACIBORSKA", days_ago=30 + index, number=f"r{index}")
            for index in range(7)
        ]
        older = [
            _sale(street="RACIBORSKA", days_ago=700 + index, number=f"o{index}")
            for index in range(5)
        ]

        selected, notes = select_comparables(recent + older, subject, TODAY)

        # The window opens until the city holds enough sales: the seven recent
        # ones and the five that are older than the first window.
        assert len(selected) == 12
        assert any("window was widened" in note for note in notes)
