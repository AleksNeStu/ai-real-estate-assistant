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
from db.property_transaction_repo import known_external_ids


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
