"""Tests for measuring how the registered prices moved.

A forecast needs a rate. A rate nobody measured is a constant wearing a
forecast's clothes, so the service measures it — and refuses to when the sales
cannot carry the claim.
"""

from datetime import date, timedelta

from data.rcn.rcn_models import RCNAddress, RCNTransaction
from services.rcn_valuation import appreciation_from_transactions

TODAY = date(2026, 11, 21)


def _sale(price_per_sqm: float, days_ago: int, number: str = "1") -> RCNTransaction:
    area = 50.0
    return RCNTransaction(
        external_id=f"sale-{number}-{days_ago}",
        teryt="1261",
        address=RCNAddress(city="KRAKÓW", street="TOPOLOWA", number=number),
        area_sqm=area,
        price=price_per_sqm * area,
        transaction_date=TODAY - timedelta(days=days_ago),
        market="rynekWtorny",
        rooms=2,
        floor=3,
    )


def _rising_sales() -> list[RCNTransaction]:
    """Eight sales over two years, the newer ones 10% dearer per year."""
    sales = []
    for index in range(8):
        older = index < 4
        days_ago = 700 - index * 50 if older else 250 - (index - 4) * 50
        base = 14000.0 if older else 14000.0 * 1.10 ** ((700 - days_ago) / 365.25)
        sales.append(_sale(base, days_ago, number=str(index)))
    return sales


class TestAppreciation:
    def test_measures_the_rate_the_sales_moved_at(self):
        trend = appreciation_from_transactions(_rising_sales(), "Topolowa, Kraków")

        assert trend is not None
        # The newer half is dearer than the older one; the rate is positive.
        assert trend.annual_rate > 0
        assert 0.05 < trend.annual_rate < 0.16
        assert trend.sample_size == 8
        assert trend.comparison_area == "Topolowa, Kraków"

    def test_says_the_period_it_measured_over(self):
        trend = appreciation_from_transactions(_rising_sales())

        assert trend is not None
        assert trend.period_end > trend.period_start
        assert trend.median_late > trend.median_early

    def test_refuses_when_there_are_too_few_sales(self):
        sales = [_sale(14000.0, 600 - index * 60, number=str(index)) for index in range(5)]

        assert appreciation_from_transactions(sales) is None

    def test_refuses_when_the_sales_are_too_close_in_time(self):
        # Eight sales, but all within a few weeks of each other.
        sales = [_sale(14000.0 + index, 30 + index, number=str(index)) for index in range(8)]

        assert appreciation_from_transactions(sales) is None

    def test_refuses_a_rate_no_market_produced(self):
        # The newer sales are ten times the older ones: that is not a trend.
        sales = []
        for index in range(8):
            older = index < 4
            days_ago = 700 - index * 50 if older else 250 - (index - 4) * 50
            base = 1000.0 if older else 100000.0
            sales.append(_sale(base, days_ago, number=str(index)))

        assert appreciation_from_transactions(sales) is None

    def test_describes_itself_for_a_reader(self):
        trend = appreciation_from_transactions(_rising_sales(), "Kraków")

        assert trend is not None
        described = trend.describe()
        assert "rose" in described
        assert "8 sales" in described
