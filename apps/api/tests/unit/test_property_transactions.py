"""Tests for the storage of the registered sales.

The rows live in the database and the sessions that read them are opened by
the code under test, so both are exercised here: the session a tool opens when
it runs outside a request, the repository's own rules, and the row's own
description of itself.
"""

from datetime import date

import pytest
from sqlalchemy import text

from db.database import standalone_session
from db.models import PropertyTransaction
from db.property_transaction_repo import (
    has_sales_of_cities,
    known_external_ids,
    transactions_for,
)


class TestTheSessionOfItsOwn:
    async def test_it_opens_a_session_and_closes_it(self, monkeypatch):
        monkeypatch.setattr("db.database.get_database_url", lambda: "sqlite+aiosqlite:///:memory:")

        async with standalone_session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1

    async def test_the_session_is_closed_when_the_work_raises(self, monkeypatch):
        monkeypatch.setattr("db.database.get_database_url", lambda: "sqlite+aiosqlite:///:memory:")

        with pytest.raises(RuntimeError):
            async with standalone_session():
                raise RuntimeError("the work failed")


class TestTheKnownRows:
    async def test_no_municipalities_means_nothing_is_known(self, db_session):
        assert await known_external_ids(db_session, []) == set()


class TestTheStoredRow:
    def test_it_says_what_it_is(self):
        row = PropertyTransaction(
            external_id="11562464",
            city="KRAKÓW",
            street="TOPOLOWA",
            number="47",
            area_sqm=50.0,
            price_brutto=650000.0,
            transaction_date=date(2026, 3, 27),
        )

        text_repr = repr(row)

        assert "TOPOLOWA" in text_repr
        assert "KRAKÓW" in text_repr
        assert "650000.0" in text_repr


class TestTheSalesOfACity:
    """The register's own typos must not become the evidence."""

    async def test_a_deed_dated_in_the_future_is_not_a_sale(self, db_session):
        """The demo's register holds rows dated 3021 - a typo in the deed.

        The read is ordered by date descending, so such a row would sit at the
        top of the result set and count against the limit the real sales
        share.
        """
        db_session.add(
            PropertyTransaction(
                external_id="typed-in-the-future",
                city="KRAKÓW",
                city_norm="KRAKOW",
                street="TOPOLOWA",
                street_norm="TOPOLOWA",
                number="47",
                area_sqm=50.0,
                price_brutto=650000.0,
                transaction_date=date(3021, 12, 2),
            )
        )
        db_session.add(
            PropertyTransaction(
                external_id="a-real-sale",
                city="KRAKÓW",
                city_norm="KRAKOW",
                street="TOPOLOWA",
                street_norm="TOPOLOWA",
                number="48",
                area_sqm=50.0,
                price_brutto=640000.0,
                transaction_date=date(2026, 3, 27),
            )
        )
        await db_session.commit()

        sales = await transactions_for(db_session, "KRAKOW")

        assert [sale.external_id for sale in sales] == ["a-real-sale"]

    async def test_a_sale_of_today_is_a_sale(self, db_session):
        """The bound is today, and a sale of today is inside it."""
        db_session.add(
            PropertyTransaction(
                external_id="sold-today",
                city="KRAKÓW",
                city_norm="KRAKOW",
                street="TOPOLOWA",
                street_norm="TOPOLOWA",
                number="49",
                area_sqm=50.0,
                price_brutto=620000.0,
                transaction_date=date.today(),
            )
        )
        await db_session.commit()

        sales = await transactions_for(db_session, "KRAKOW")

        assert [sale.external_id for sale in sales] == ["sold-today"]


class TestWhetherTheRegisterIsHeld:
    """The capability endpoint asks the register whether it is held at all.

    The question is asked of the database and not of a list of cities: a
    deployment holds the register when the ingest stored a sale of a city the
    site knows. The read stops at the first row - it asks for the existence
    of a sale, not for the sales themselves.
    """

    async def test_a_deployment_that_stored_no_sale_holds_no_register(self, db_session):
        assert await has_sales_of_cities(db_session, ["KRAKOW"]) is False

    async def test_a_deployment_that_stored_a_sale_holds_the_register(self, db_session):
        db_session.add(
            PropertyTransaction(
                external_id="a-sale-of-krakow",
                city="KRAKOW",
                city_norm="KRAKOW",
                street="TOPOLOWA",
                street_norm="TOPOLOWA",
                number="47",
                area_sqm=50.0,
                price_brutto=650000.0,
                transaction_date=date(2026, 3, 27),
            )
        )
        await db_session.commit()

        assert await has_sales_of_cities(db_session, ["KRAKOW"]) is True

    async def test_no_city_means_nothing_is_held(self, db_session):
        assert await has_sales_of_cities(db_session, []) is False

    async def test_a_sale_of_another_city_does_not_count(self, db_session):
        db_session.add(
            PropertyTransaction(
                external_id="a-sale-of-szczecin",
                city="SZCZECIN",
                city_norm="SZCZECIN",
                street="PANCERNA",
                street_norm="PANCERNA",
                number="3",
                area_sqm=40.0,
                price_brutto=400000.0,
                transaction_date=date(2026, 3, 27),
            )
        )
        await db_session.commit()

        assert await has_sales_of_cities(db_session, ["KRAKOW"]) is False
        assert await has_sales_of_cities(db_session, ["SZCZECIN"]) is True

    async def test_a_deed_dated_in_the_future_is_not_a_sale(self, db_session):
        # The bound is today: a deed dated in the future is a typo, and a
        # typo is not a sale the register holds.
        db_session.add(
            PropertyTransaction(
                external_id="typed-in-the-future",
                city="KRAKOW",
                city_norm="KRAKOW",
                street="TOPOLOWA",
                street_norm="TOPOLOWA",
                number="47",
                area_sqm=50.0,
                price_brutto=650000.0,
                transaction_date=date(3021, 12, 2),
            )
        )
        await db_session.commit()

        assert await has_sales_of_cities(db_session, ["KRAKOW"]) is False
